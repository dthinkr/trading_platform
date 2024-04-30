import aio_pika
import json
import uuid
from pydantic import ValidationError

from main_platform.custom_logger import setup_custom_logger
from typing import List, Dict
from structures import OrderStatus, OrderType, TransactionModel, Order, TraderType, Message
import asyncio
import pandas as pd
import os
from main_platform.utils import CustomEncoder, now, if_active
from asyncio import Lock, Event
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# setting mongodb
from mongoengine import connect

connect('trader', host='localhost', port=27017)


rabbitmq_url = os.getenv('RABBITMQ_URL', 'amqp://localhost')
logger = setup_custom_logger(__name__)


class TradingSession:
    duration: int
    active: bool
    start_time: datetime
    transactions = List[TransactionModel]
    all_orders = Dict[uuid.UUID, Dict]


    def __init__(self, duration, default_price=1000, default_spread=10, punishing_constant=1):
        self.active = False
        self.duration = duration
        self.default_price = default_price

        self.default_spread = default_spread
        self.punishing_constant = punishing_constant

        self._stop_requested = asyncio.Event()

        self.id = str(uuid.uuid4())

        self.creation_time = now()
        self.all_orders = {}


        self.broadcast_exchange_name = f'broadcast_{self.id}'
        self.queue_name = f'trading_system_queue_{self.id}'
        self.trader_exchange = None

        self.connected_traders = {}
        self.trader_responses = {}
        self.release_task = None
        self.lock = Lock()
        self.release_event = Event()
        self.current_price = 0 # handling non-defined attribute

    @property
    def current_time(self):
        return datetime.now(timezone.utc)

    @property
    def transactions(self):
        # Fetch all TransactionModel objects that have the current TradingSession's ID
        transactions = TransactionModel.objects(trading_session_id=self.id)
        # Convert each transaction document into a dictionary for easier serialization
        return [transaction.to_mongo().to_dict() for transaction in transactions]

    @property
    def mid_price(self) -> float:
        return self.current_price or self.default_price

    def get_closure_price(self, shares: int, order_type: int) -> float:
        return self.mid_price + order_type * shares * self.default_spread * self.punishing_constant

    def get_params(self):
        return {
            "id": self.id,
            "duration": self.duration,
            "creation_time": self.creation_time,
            "active": self.active,
            "start_time": self.start_time,
            "end_time": self.start_time + timedelta(minutes=self.duration),
            "connected_traders": self.connected_traders,
        }

    @property
    def active_orders(self):
        return {k: v for k, v in self.all_orders.items() if v['status'] == OrderStatus.ACTIVE}

    @property
    def order_book(self):
        active_orders_df = pd.DataFrame(list(self.active_orders.values()))
        # Initialize empty order book
        order_book = {'bids': [], 'asks': []}
        if active_orders_df.empty:
            return order_book

        active_bids = active_orders_df[(active_orders_df['order_type'] == OrderType.BID.value)]
        active_asks = active_orders_df[(active_orders_df['order_type'] == OrderType.ASK.value)]
        if not active_bids.empty:
            bids_grouped = active_bids.groupby('price').amount.sum().reset_index().sort_values(by='price',
                                                                                               ascending=False)
            order_book['bids'] = bids_grouped.rename(columns={'price': 'x', 'amount': 'y'}).to_dict('records')

        # Aggregate and format asks if there are any
        if not active_asks.empty:
            asks_grouped = active_asks.groupby('price').amount.sum().reset_index().sort_values(by='price')
            order_book['asks'] = asks_grouped.rename(columns={'price': 'x', 'amount': 'y'}).to_dict('records')

        return order_book

    @property
    def transaction_price(self):
        """Returns the price of last transaction. If there are no transactions, returns None."""
        if not self.transactions or len(self.transactions) == 0:
            return None
        transactions = [{'price': t['price'], 'timestamp': t['timestamp'].timestamp()} for t in self.transactions]
        # sort by timestamp
        transactions.sort(key=lambda x: x['timestamp'])
        return transactions[-1]['price']

    async def initialize(self):
        self.start_time = now()
        self.active = True
        self.connection = await aio_pika.connect_robust(rabbitmq_url)
        self.channel = await self.connection.channel()

        await self.channel.declare_exchange(self.broadcast_exchange_name, aio_pika.ExchangeType.FANOUT,
                                            auto_delete=True)
        self.trader_exchange = await self.channel.declare_exchange(self.queue_name, aio_pika.ExchangeType.DIRECT,
                                                                   auto_delete=True)
        trader_queue = await self.channel.declare_queue(self.queue_name, auto_delete=True)
        await trader_queue.bind(self.trader_exchange)  # bind the queue to the exchange
        await trader_queue.consume(self.on_individual_message)  # Assuming you have a method named on_individual_message

        await trader_queue.purge()

    async def clean_up(self):
        """
        This one is mostly used for closing connections and channels opened by a trading session.
        At this stage we also dump existing transactions and orders from the memory. In the future, we'll probably
        dump them to a database.
        """
        # Signal the run loop to stop
        self._stop_requested.set()
        self.active = False
        try:
            # Unbind the queue from the exchange (optional, as auto_delete should handle this)
            trader_queue = await self.channel.get_queue(self.queue_name)
            await trader_queue.unbind(self.trader_exchange)

            # Close the channel and connection
            await self.channel.close()
            logger.info(f"Trading System {self.id} channel closed")
            await self.connection.close()
            logger.info(f"Trading System {self.id} connection closed")
            #     dump transactions and orders to files
            # await dump_transactions_to_csv(self.transactions, generate_file_name(self.id, "transactions"))
            # Dump all_orders to CSV
            # await dump_orders_to_csv(self.all_orders, generate_file_name(self.id, "all_orders"))
        except Exception as e:
            logger.error(f"An error occurred during cleanup: {e}")

    def get_active_orders_to_broadcast(self):
        # TODO. PHILIPP. It's not optimal but we'll rewrite it anyway when we convert form in-memory to DB
        active_orders_df = pd.DataFrame(list(self.active_orders.values()))
        # lets keep only id, trader_id, order_type, amount, price
        if active_orders_df.empty:
            return []
        active_orders_df = active_orders_df[['id', 'trader_id', 'order_type', 'amount', 'price', 'timestamp']]
        # TODO: PHILIPP:  I dont like that we don't use structure order type but hardcode it here.
        active_orders_df['order_type'] = active_orders_df['order_type'].map({-1: 'ask', 1: 'bid'})

        # convert to list of dicts
        res = active_orders_df.to_dict('records')
        return res

    async def send_broadcast(self, message: dict):
        # TODO: PHILIPP: let's think how to make this more efficient but for simplicity
        # TODO we inject the current order book, active orders and transaction history into every broadcasted message
        # TODO: also important thing: we now send all active orders to everyone. We may think about possiblity to
        # TODO: send only to the trader who own them. But not now let's keep it simple.
        # let's set default type if type is emp[ty
        message['type'] = message.get('type', 'update')

        if message.get('type') == 'closure':
            pass  # TODO. PHILIPP. Should we inject some info here?
        else:
            spread, midpoint = self.get_spread()
            message.update({
                # TODO: PHILIPP: we need to think about the type of the message. it's hardcoded for now
                'order_book': self.order_book,
                'active_orders': self.get_active_orders_to_broadcast(),
                'history': self.transactions,
                'spread': spread,
                'midpoint': midpoint,
                'transaction_price': self.transaction_price,
            })
            message_document = Message(
                trading_session_id=self.id,  # Assuming self.id is the UUID of the TradingSession
                content=message
            )
            message_document.save()

        exchange = await self.channel.get_exchange(self.broadcast_exchange_name)
        await exchange.publish(
            aio_pika.Message(body=json.dumps(message, cls=CustomEncoder).encode()),
            routing_key=''  # routing_key is typically ignored in FANOUT exchanges
        )

    async def send_message_to_trader(self, trader_id, message):


        # TODO. PHILIPP. IT largely overlap with broadcast. We need to refactor that moving to _injection method
        transactions = [{'price': t['price'], 'timestamp': t['timestamp'].timestamp()} for t in self.transactions]
        # sort by timestamp
        transactions.sort(key=lambda x: x['timestamp'])
        # if not empty return the last one for current price
        if transactions:
            current_price = transactions[-1]['price']
        else:
            current_price = None
        spread, mid_price = self.get_spread()
        message.update({
            'type': 'update',  # TODO: PHILIPP: we need to think about the type of the message. it's hardcoded for now
            'order_book': self.order_book,
            'active_orders': self.get_active_orders_to_broadcast(),
            'transaction_history': self.transactions,
            'spread': spread,
            'mid_price': mid_price,

            'current_price': current_price,
        })
        await self.trader_exchange.publish(
            aio_pika.Message(body=json.dumps(message, cls=CustomEncoder).encode()),
            routing_key=f'trader_{trader_id}'
        )

    @property
    def list_active_orders(self):
        """ Returns a list of all active orders. When we switch to real DB or mongo, we won't need it anymore."""
        return list(self.active_orders.values())

    def get_file_name(self):
        # todo: rename this to get_message_file_name
        """Returns file name for messages which is a trading platform id + datetime of creation with _ as spaces"""
        return f"{self.id}_{self.creation_time.strftime('%Y-%m-%d_%H-%M-%S')}"

    def place_order(self, order_dict: Dict):
        """ This one is called by handle_add_order, and is the one that actually places the order in the system.
        It adds automatically - we do all the validation (whether a trader allowed to place an order, etc) in the
        handle_add_order method.
        It doesn't make much sense to decouple handle_add_order with the actualy place_order now, but theoretically
        we may need this later if we want more speed for some traders that will be merged into trading platform (if the rabbitMQ solution won't be fast enough for simluation purposes).
        """
        order_id = order_dict['id']
        order_dict.update({
            'status': OrderStatus.ACTIVE.value,
        })
        self.all_orders[order_id] = order_dict
        return order_dict



    def get_spread(self):
        """
        Returns the spread and the midpoint. If there are no overlapping orders, returns None, None.
        """
        asks = [order for order in self.active_orders.values() if order['order_type'] == OrderType.ASK.value]
        bids = [order for order in self.active_orders.values() if order['order_type'] == OrderType.BID.value]

        # Sort by price (lowest first for asks), and then by timestamp (oldest first - FIFO)
        asks.sort(key=lambda x: (x['price'], x['timestamp']))
        # Sort by price (highest first for bids), and then by timestamp (oldest first)
        bids.sort(key=lambda x: (-x['price'], x['timestamp']))

        # Calculate the spread
        if asks and bids:
            lowest_ask = asks[0]['price']
            highest_bid = bids[0]['price']
            spread = lowest_ask - highest_bid
            mid_price = (lowest_ask + highest_bid) / 2
            return spread, mid_price
        else:
            logger.info("No overlapping orders.")
            return None, None


    def create_transaction(self, bid, ask, transaction_price):
        # Change the status to 'EXECUTED'
        self.all_orders[ask['id']]['status'] = OrderStatus.EXECUTED.value
        self.all_orders[bid['id']]['status'] = OrderStatus.EXECUTED.value

        # Create a transaction object with automatic id and timestamp generation
        transaction = TransactionModel(
            trading_session_id=self.id,  # Assuming session_id is the UUID of the TradingSession
            bid_order_id=bid['id'],
            ask_order_id=ask['id'],
            price=transaction_price
        )
        transaction.save()

        # Append to self.transactions



        # Log the transaction creation
        logger.info(f"Transaction created: {transaction}")

        # Return trader IDs involved in the transaction for further processing
        return ask['trader_id'], bid['trader_id'], transaction

    async def clear_orders(self):
        """ this goes through order book trying to execute orders """
        # TODO. PHILIPP. At this stage we don't need to return anything but for LOBSTER format later we may needed so let's keep it for now
        res = {'transactions': [], 'removed_active_orders': []}
        # Separate active orders into asks and bids
        asks = [order for order in self.active_orders.values() if order['order_type'] == OrderType.ASK.value]
        bids = [order for order in self.active_orders.values() if order['order_type'] == OrderType.BID.value]

        # Sort by price (lowest first for asks), and then by timestamp (oldest first - FIFO)
        # TODO: remember that this is FIFO. We need to adjust the rule (or make it adjustable in the config) if we want
        asks.sort(key=lambda x: (x['price'], x['timestamp']))
        # Sort by price (highest first for bids), and then by timestamp (oldest first)
        bids.sort(key=lambda x: (-x['price'], x['timestamp']))

        # Calculate the spread
        # TODO. Philipp. We actually already have this method above. We need to refactor it. We need a separate method
        # because we also return spread to traders in broadcast messages.
        if asks and bids:
            lowest_ask = asks[0]['price']
            highest_bid = bids[0]['price']
            spread = lowest_ask - highest_bid
        else:
            logger.info("No overlapping orders.")
            return res

        # Check if any transactions are possible
        if spread > 0:
            logger.info(
                f"No overlapping orders. Spread is positive: {spread}. Lowest ask: {lowest_ask}, highest bid: {highest_bid}")
            return res

        # Filter the bids and asks that could be involved in a transaction
        viable_asks = [ask for ask in asks if ask['price'] <= highest_bid]
        viable_bids = [bid for bid in bids if bid['price'] >= lowest_ask]

        transactions = []
        participated_traders = set()
        traders_to_transactions_lookup = defaultdict(list)
        # Create transactions
        while viable_asks and viable_bids:
            ask = viable_asks.pop(0)
            bid = viable_bids.pop(0)

            transaction_price = (ask['price'] + bid['price']) / 2  # Mid-price
            ask_trader_type = self.connected_traders[ask['trader_id']]['trader_type']
            ask_trader_id = ask.get('trader_id')
            bid_trader_id = bid.get('trader_id')
            if ask_trader_type == TraderType.HUMAN.value and ask_trader_id == bid_trader_id:
                logger.warning(f'Blocking self-execution for trader {ask_trader_id}')
                return res
            ask_trader_id, bid_trader_id, transaction = self.create_transaction(bid, ask, transaction_price)

            # No need to append the transaction to self.transactions here as it's handled within create_transaction

            # Process involved trader IDs as needed (e.g., logging, updating trader states)
            participated_traders.add(ask_trader_id)
            participated_traders.add(bid_trader_id)

            # we  need to get the trader_in_transcation_lookup and if it's
            # not there we need to create it.
            # let's not add the entire transaction here, just the order id, price, type of order, amount - so they can correclty update the inventory
            traders_to_transactions_lookup[ask['trader_id']].append(
                {'id': ask['id'], 'price': ask['price'], 'type': 'ask', 'amount': ask['amount']})
            traders_to_transactions_lookup[bid['trader_id']].append(
                {'id': bid['id'], 'price': bid['price'], 'type': 'bid', 'amount': bid['amount']})

            transactions.append(transaction)

        # if transactions are not empty (so there are new transactions) let's form subgroup_broadcast message
        # that will contain to_whom (traders who participated in transactions) and the list of transactions and add them to res
        if transactions:
            res['subgroup_broadcast'] = traders_to_transactions_lookup

        return res

    @if_active
    async def handle_add_order(self, data: dict):
        """
        that is called automatically on the incoming message if type of a message is 'add_order'.
        it returns the dict with respond=True to signalize that (ideally) we need to ping back the trader who sent the
        message that everything is ok (it's not needed in the current implementation and perhaps we can get rid of this later because it also increase the info load)

        """

        try:
            order = Order(status=OrderStatus.BUFFERED.value,
                          session_id=self.id,
                          **data)

            # Place the order
            self.place_order(order.model_dump())  # Converting order to dict for compatibility

        except ValidationError as e:
            # Handle validation errors, e.g., log them or send a message back to the trader
            logger.critical(f"Order validation failed: {e}")
        # lets clear them now
        resp = await self.clear_orders()
        subgroup_data = resp.pop('subgroup_broadcast', None)
        if subgroup_data:
            await self.send_message_to_subgroup(subgroup_data)
        return dict(respond=True, **resp)

    async def send_message_to_subgroup(self, message):
        for trader_id, transaction_list in message.items():
            await self.send_message_to_trader(trader_id, {'type': 'update', 'new_transactions': transaction_list})

    @if_active
    async def handle_cancel_order(self, data: dict):
        order_id = data.get('order_id')
        trader_id = data.get('trader_id')

        # Ensure order_id is a valid UUID
        try:
            order_id = uuid.UUID(order_id)
        except ValueError:
            logger.warning(f"Invalid order ID format: {order_id}.")
            return {"status": "failed", "reason": "Invalid order ID format"}

        async with self.lock:
            # Check if the order exists and belongs to the trader
            if order_id not in self.active_orders:
                return {"status": "failed", "reason": "Order not found"}

            existing_order = self.active_orders[order_id]

            if existing_order['trader_id'] != trader_id:
                logger.warning(f"Trader {trader_id} does not own order {order_id}.")
                return {"status": "failed", "reason": "Trader does not own the order"}

            if existing_order['status'] != OrderStatus.ACTIVE.value:
                logger.warning(f"Order {order_id} is not active and cannot be canceled.")
                return {"status": "failed", "reason": "Order is not active"}

            # Cancel the order
            self.all_orders[order_id]['status'] = OrderStatus.CANCELLED.value
            self.all_orders[order_id]['cancellation_timestamp'] = now()

            return {"status": "cancel success", "order": order_id, "respond": True}

    @if_active
    async def handle_register_me(self, msg_body):
        trader_id = msg_body.get('trader_id')
        trader_type = msg_body.get('trader_type')
        self.connected_traders[trader_id] = {'trader_type': trader_type, }
        self.trader_responses[trader_id] = False

        logger.info(f"Trader type  {trader_type} id {trader_id} connected.")
        logger.info(f"Total connected traders: {len(self.connected_traders)}")
        return dict(respond=True, trader_id=trader_id, message="Registered successfully", individual=True)


    async def on_individual_message(self, message):
        incoming_message = json.loads(message.body.decode())
        logger.info(f"TS {self.id} received message: {incoming_message}")
        action = incoming_message.pop('action', None)
        trader_id = incoming_message.get('trader_id', None)  # Assuming the trader_id is part of the message
        if incoming_message is None:
            logger.critical(f"Invalid message format: {message}")

        if action:
            handler_method = getattr(self, f"handle_{action}", None)
            if handler_method:

                result = await handler_method(incoming_message)
                if result and result.pop('respond', None) and trader_id:
                    await self.send_message_to_trader(trader_id, result)
                    #         TODO.PHILIPP. IMPORTANT! let's at this stage also send a broadcast message to all traders with updated info.
                    # IT IS FAR from optimal but for now we keep it simple. We'll refactor it later.
                    if not result.get('individual', False):
                        await self.send_broadcast(message=dict(text="book is updated"))



            else:
                logger.warning(f"No handler method found for action: {action}")
        else:
            logger.warning(f"No action found in message: {incoming_message}")
    async def close_existing_book(self):
        """we create a counteroffer on behalf of the platform with a get_closure_price price. and then we
        create a transaction out of it."""
        for order_id, order in self.active_orders.items():
            platform_order_type = OrderType.ASK.value if order['order_type'] == OrderType.BID.value else OrderType.BID.value
            closure_price = self.get_closure_price(order['amount'], order['order_type'])
            platform_order = Order(trader_id=self.id,
                                      order_type=platform_order_type,
                                      amount=order['amount'],
                                      price=closure_price,
                                      status=OrderStatus.BUFFERED.value,
                                      session_id=self.id,
                                      )

            self.place_order(platform_order.model_dump())
            if order['order_type'] == OrderType.BID.value:
                self.create_transaction(order, platform_order.model_dump(), closure_price)
            else:
                self.create_transaction( platform_order.model_dump(),order, closure_price)

        await self.send_broadcast(message=dict(text="book is updated"))



    async def handle_inventory_report(self, data: dict):
        # Handle received inventory report from a trader
        trader_id = data.get('trader_id')
        self.trader_responses[trader_id] = True
        trader_type = self.connected_traders[trader_id]['trader_type']
        logger.info(f'Trader ({trader_type}):  {trader_id} has reported back their inventory: {data}')
        shares = data.get('shares', 0)
        # if shares is positive than we need to sell them. to do this we first handle_add_order
        # on behalf of this trader at the closure_price and then put the opposite order to buy
        # the same amount of shares at the same price. We need to do this for each trader who has positive shares
        if shares != 0:

            trader_order_type = OrderType.ASK.value if shares > 0 else OrderType.BID.value
            platform_order_type = OrderType.BID.value if shares > 0 else OrderType.ASK.value
            shares=abs(shares)
            closure_price = self.get_closure_price(shares, trader_order_type)

            proto_order = dict(amount=shares,
                               price=closure_price,
                               status=OrderStatus.BUFFERED.value,
                               session_id=self.id,

                               )
            trader_order = Order(trader_id=trader_id,
                                 order_type=trader_order_type,
                                 **proto_order
                                 )
            platform_order = Order(trader_id=self.id,
                                   order_type=platform_order_type,
                                   **proto_order
                                   )
            self.place_order(platform_order.model_dump())
            self.place_order(trader_order.model_dump())
            # let's create a transaction. it should be a bit different depending on type
            if trader_order_type == OrderType.BID.value:
                self.create_transaction( trader_order.model_dump(), platform_order.model_dump(), closure_price)
            else:
                self.create_transaction(platform_order.model_dump(), trader_order.model_dump(), closure_price)

            traders_to_transactions_lookup = defaultdict(list)
            trader_order = trader_order.model_dump()
            traders_to_transactions_lookup[trader_id].append(
                {'id': trader_order['id'], 'price': trader_order['price'],
                 'type': 'ask' if trader_order['order_type'] == OrderType.ASK.value else 'bid',
                 'amount': trader_order['amount']})

            await self.send_message_to_subgroup(traders_to_transactions_lookup)

        # mid_price + x * spread * const)

    async def wait_for_traders(self):
        while not all(self.trader_responses.values()):
            await asyncio.sleep(1)  # Check every second
        logger.info('All traders have reported back their inventories.')

    async def run(self):
        try:
            while not self._stop_requested.is_set():
                current_time = now()
                if current_time - self.start_time > timedelta(
                        minutes=self.duration
                ):
                    logger.critical('Time limit reached, stopping...')
                    self.active = False # here we stop accepting all incoming requests on placing new orders, cancelling etc.
                    await self.close_existing_book()
                    await self.send_broadcast({"type": "stop_trading"})
                    # Wait for each of the traders to report back their inventories
                    await self.wait_for_traders()
                    await self.send_broadcast({"type": "closure"})

                    break
                await asyncio.sleep(1)
            logger.critical('Exited the run loop.')
        except asyncio.CancelledError:
            logger.info('Run method cancelled, performing cleanup of trading session...')

            raise

        except Exception as e:
            # Handle the exception here
            logger.error(f"Exception in trading session run: {e}")
            # Optionally re-raise the exception if you want it to be propagated
            raise
        finally:
            await self.clean_up()
