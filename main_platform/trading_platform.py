import aio_pika
import json
import uuid

from main_platform.utils import ack_message
from main_platform.custom_logger import setup_custom_logger
from typing import List, Dict
from structures import OrderStatus, OrderType, TransactionModel, LobsterEventType
import asyncio
import pandas as pd

from main_platform.utils import (CustomEncoder,
                                 append_combined_data_to_csv,
                                 now,
                                 )
from asyncio import Lock, Event

logger = setup_custom_logger(__name__)


class TradingSession:
    transactions = List[TransactionModel]
    all_orders = Dict[uuid.UUID, Dict]
    buffered_orders = Dict[uuid.UUID, Dict]

    def __init__(self, buffer_delay=0, max_buffer_releases=None):
        """
        buffer_delay: The delay in seconds before the Trading System processes the buffered orders.
        """
        self._stop_requested = asyncio.Event()
        self.id = str(uuid.uuid4())
        self.max_buffer_releases = max_buffer_releases
        logger.critical(f"Max buffer releases: {self.max_buffer_releases}")
        self.buffer_release_count = 0
        self.buffer_release_time = None

        self.creation_time = now()
        self.all_orders = {}
        self.buffered_orders = {}
        self.transactions = []
        self.broadcast_exchange_name = f'broadcast_{self.id}'
        self.queue_name = f'trading_system_queue_{self.id}'
        self.trader_exchange = None
        logger.info(f"Trading System created with UUID: {self.id}. Buffer delay is: {buffer_delay} seconds")
        self.connected_traders = {}
        self.buffer_delay = buffer_delay

        self.release_task = None
        self.lock = Lock()
        self.release_event = Event()

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

    async def initialize(self):
        self.connection = await aio_pika.connect_robust("amqp://localhost")
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
            print(f"An error occurred during cleanup: {e}")

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

    async def send_broadcast(self, message):
        # TODO: PHILIPP: let's think how to make this more efficient but for simplicity
        # TODO we inject the current order book, active orders and transaction history into every broadcasted message
        # TODO: also important thing: we now send all active orders to everyone. We may think about possiblity to
        # TODO: send only to the trader who own them. But not now let's keep it simple.
        transactions = [{'price': t['price'], 'timestamp': t['timestamp'].timestamp()} for t in self.transactions]
        # sort by timestamp
        transactions.sort(key=lambda x: x['timestamp'])
        # if not empty return the last one for current price
        if transactions:
            current_price = transactions[-1]['price']
        else:
            current_price = None
        message.update({
            'type': 'update',  # TODO: PHILIPP: we need to think about the type of the message. it's hardcoded for now
            'order_book': self.order_book,
            'active_orders': self.get_active_orders_to_broadcast(),
            'history': self.transactions,
            'spread': self.get_spread(),
            'current_price': current_price
        })

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
        message.update({
            'type': 'update',  # TODO: PHILIPP: we need to think about the type of the message. it's hardcoded for now
            'order_book': self.order_book,
            'active_orders': self.get_active_orders_to_broadcast(),
            'transaction_history': self.transactions,
            'spread': self.get_spread(),
            'current_price': current_price
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

    async def place_order(self, order_dict: Dict, trader_id: uuid.UUID):
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



    async def handle_transaction_for_order(self, order_id, combined_data):
        clear_result = await self.clear_orders()  # Attempt to clear orders and process transactions

        # Initialize the container for transactions
        if clear_result is None:
            clear_result = {'transactions': [], 'removed_active_orders': []}
        transactions = clear_result['transactions']
        removed_order_ids = clear_result['removed_active_orders']

        # Handle transactions logging
        for transaction in transactions:
            # Determine the most recent order (ask or bid) based on the timestamp
            ask_order = self.all_orders[transaction['ask_order_id']]
            bid_order = self.all_orders[transaction['bid_order_id']]
            most_recent_order = ask_order if ask_order['timestamp'] > bid_order['timestamp'] else bid_order

            # Create and append the transaction message



        return combined_data  # Return the updated combined_data




    def check_counters(self):

        """ Checks if the buffer release count exceeds the limit. """
        logger.info(f'self.buffer_release_count {self.buffer_release_count}')
        if self.max_buffer_releases is not None and self.buffer_release_count >= self.max_buffer_releases:
            return True
        return False

    def get_spread(self):
        """ Returns the spread between the lowest ask and the highest bid. """
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
            return spread
        else:
            logger.info("No overlapping orders.")
            return None

    async def clear_orders(self):
        res = {'transactions': [], 'removed_active_orders': []}
        logger.info(f'Total amount of active orders: {len(self.active_orders)}')
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

        logger.info(f"Spread: {spread}")
        # Filter the bids and asks that could be involved in a transaction
        viable_asks = [ask for ask in asks if ask['price'] <= highest_bid]
        viable_bids = [bid for bid in bids if bid['price'] >= lowest_ask]
        logger.info(f'Viable asks: {len(viable_asks)}')
        logger.info(f'Viable bids: {len(viable_bids)}')
        to_remove = []
        transactions = []

        # Create transactions
        while viable_asks and viable_bids:
            ask = viable_asks.pop(0)
            bid = viable_bids.pop(0)

            # Change the status to 'EXECUTED' in the all_orders dictionary
            self.all_orders[ask['id']]['status'] = OrderStatus.EXECUTED.value
            self.all_orders[bid['id']]['status'] = OrderStatus.EXECUTED.value
            timestamp = now()

            # Create a transaction
            transaction_price = (ask['price'] + bid['price']) / 2  # Mid-price
            transaction = TransactionModel(
                id=uuid.uuid4(),
                bid_order_id=bid['id'],
                ask_order_id=ask['id'],
                timestamp=timestamp,
                price=transaction_price
            )
            logger.info(f"Transaction created: {transaction.model_dump()}")
            transactions.append(transaction.model_dump())

            to_remove.extend([str(ask['id']), str(bid['id'])])

        # Add transactions to self.transactions
        self.transactions.extend(transactions)

        # Log the number of cleared and transacted orders
        logger.info(f"Cleared {len(to_remove)} orders.")
        logger.info(f"Created {len(transactions)} transactions.")
        res['removed_active_orders'] = to_remove
        res['transactions'] = transactions
        return res

    async def handle_add_order(self, data: dict):
        """
        that is called automatically on the incoming message if type of a message is 'add_order'.
        it returns the dict with respond=True to signalize that (ideally) we need to ping back the trader who sent the
        message that everything is ok (it's not needed in the current implementation and perhaps we can get rid of this later because it also increase the info load)

        """
        # TODO: Validate the order. We don't need  to do an inventory validation because in the current design this is all done on the trader side.
        trader_id = data.get('trader_id')
        clean_order = {
            'id': uuid.uuid4(),
            'status': OrderStatus.BUFFERED.value,
            'for_execution_only': data.get('for_execution_only', False),
            'amount': data.get('amount'),
            'price': data.get('price'),
            'order_type': data.get('order_type'),
            'timestamp': now(),
            # we add the timestamp here but when we release an order out of the buffer we set a common tiestmap for them that points to the release time.
            'session_id': self.id,
            'trader_id': trader_id
        }
        if clean_order.get('amount',1)>1:
            logger.critical('Amount is more than 1. Temporarily we replace all amounts with 1.')
            # TODO. PHILIPP. IMPORTANT! It's a temporary solution  for now. Should be removed later
            clean_order['amount']  = 1

        resp = await  self.place_order(clean_order, trader_id)
        if resp:
            logger.critical(f'Total active orders: {len(self.active_orders)}')

        return dict(respond=True, **resp)

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
            timestamp = now()
            self.all_orders[order_id]['status'] = OrderStatus.CANCELLED.value

            # Create a combined row for the cancel event
            combined_row = self.register_message(existing_order, LobsterEventType.CANCELLATION_TOTAL)

            # Append the combined row to the CSV
            await append_combined_data_to_csv([combined_row], self.get_file_name())
            logger.info(f"Order {order_id} has been canceled for trader {trader_id}.")
            # Broadcast the cancellation, implementation may vary based on your system's logic
            await self.broadcast_order_cancellation(trader_id)
            return {"status": "cancel success", "order": order_id, "respond": True}

    async def broadcast_order_cancellation(self, trader_id):
        # Implementation for broadcasting order cancellation
        # Note: Make sure self.list_active_orders and self.buffered_orders reflect the current state after cancellation
        await self.send_broadcast(message=dict(message="Order is cancelled"))

    async def handle_update_book_status(self, order):
        """This one returns the most recent book to the trader who requested it.
        TODO: now we just stupidly pass all active orders. We need to filter them based on the trader_id, perhaps
        we'll generate a proper book (with prices-levels) here. but not now.
        """
        trader_id = order.get('trader_id')
        if trader_id:
            return {"status": "success", "respond": True, "orders": self.active_orders.values()}

    async def handle_register_me(self, msg_body):
        trader_id = msg_body.get('trader_id')
        self.connected_traders[trader_id] = {'trader_type': msg_body.get('trader_type'), }
        logger.info(f"Trader {trader_id} connected.")
        logger.info(f"Total connected traders: {len(self.connected_traders)}")

    @ack_message
    async def on_individual_message(self, message):

        incoming_message = json.loads(message.body.decode())
        logger.info(f"TS {self.id} received message: {incoming_message}")
        action = incoming_message.pop('action', None)
        trader_id = incoming_message.get('trader_id', None)  # Assuming the trader_id is part of the message

        handler_method = getattr(self, f"handle_{action}", None)
        if action:
            if handler_method:
                result = await handler_method(incoming_message)
                if result and result.pop('respond', None) and trader_id:
                    await self.send_message_to_trader(trader_id, result)

            else:
                logger.warning(f"No handler method found for action: {action}")
        else:
            logger.warning(f"No action found in message: {incoming_message}")

    async def run(self):
        """ Keeps system active. Stops if the buffer release limit is reached. """
        try:
            while not self._stop_requested.is_set():
                logger.info('Checking counters...')
                if self.check_counters():
                    logger.critical('Counter limit reached, stopping...')
                    break
                await asyncio.sleep(1)
            logger.critical('Exited the run loop.')
        except asyncio.CancelledError:
            logger.info('Run method cancelled, performing cleanup of trading session...')
            await self.clean_up()
            raise

        except Exception as e:
            # Handle the exception here
            logger.error(f"Exception in trading session run: {e}")
            # Optionally re-raise the exception if you want it to be propagated
            raise
