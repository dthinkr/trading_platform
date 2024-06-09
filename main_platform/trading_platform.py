import asyncio
import json
import os
import uuid
from asyncio import Event, Lock
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import aio_pika
import polars as pl
from mongoengine import connect
from pydantic import ValidationError

from main_platform.custom_logger import setup_custom_logger
from main_platform.utils import CustomEncoder, if_active, now
from structures import (Message, Order, OrderStatus, OrderType, TraderType,
                        TransactionModel)

connect(host="mongodb://localhost:27017/trader?w=majority&wtimeoutMS=1000")

rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://localhost")
logger = setup_custom_logger(__name__)


class TradingSession:
    duration: int
    active: bool
    start_time: datetime
    transactions = List[TransactionModel]
    all_orders = Dict[uuid.UUID, Dict]

    def __init__(
        self,
        duration: int,
        default_price: int = 1000,
        default_spread: int = 10,
        punishing_constant: int = 1,
    ):
        self.active = False
        self.duration = duration
        self.default_price = default_price

        self.default_spread = default_spread
        self.punishing_constant = punishing_constant

        self._stop_requested = asyncio.Event()

        self.id = str(uuid.uuid4())

        self.creation_time = now()
        self.all_orders = {}

        self.broadcast_exchange_name = f"broadcast_{self.id}"
        self.queue_name = f"trading_system_queue_{self.id}"
        self.trader_exchange = None

        self.connected_traders = {}
        self.trader_responses = {}
        self.release_task = None
        self.lock = Lock()
        self.release_event = Event()
        self.current_price = 0  # handling non-defined attribute
        self.transaction_processor_task = None # handling non-defined attribute

        self.transaction_queue = asyncio.Queue()

    @property
    def current_time(self) -> datetime:
        return datetime.now(timezone.utc)

    @property
    def transactions(self) -> List[Dict]:
        transactions = TransactionModel.objects(trading_session_id=self.id)
        return [transaction.to_mongo().to_dict() for transaction in transactions]

    @property
    def mid_price(self) -> float:
        return self.current_price or self.default_price

    def get_closure_price(self, shares: int, order_type: OrderType) -> float:
        return (
            self.mid_price
            + order_type * shares * self.default_spread * self.punishing_constant
        )

    def get_params(self) -> Dict:
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
    def active_orders(self) -> Dict:
        return {
            k: v
            for k, v in self.all_orders.items()
            if v["status"] == OrderStatus.ACTIVE
        }

    @property
    def order_book(self) -> Dict:
        active_orders_df = pl.DataFrame(list(self.active_orders.values()))

        order_book = {"bids": [], "asks": []}
        if active_orders_df.height == 0:
            return order_book

        active_bids = active_orders_df.filter(pl.col("order_type") == OrderType.BID)
        active_asks = active_orders_df.filter(pl.col("order_type") == OrderType.ASK)

        if not active_bids.is_empty():
            bids_grouped = (
                active_bids.groupby("price")
                .agg([pl.col("amount").sum().alias("amount_sum")])
                .sort(by="price", descending=True)
            )
            order_book["bids"] = bids_grouped.rename(
                {"price": "x", "amount_sum": "y"}
            ).to_dicts()

        if not active_asks.is_empty():
            asks_grouped = (
                active_asks.groupby("price")
                .agg([pl.col("amount").sum().alias("amount_sum")])
                .sort(by="price")
            )
            order_book["asks"] = asks_grouped.rename(
                {"price": "x", "amount_sum": "y"}
            ).to_dicts()

        return order_book

    @property
    def transaction_price(self) -> Optional[float]:
        """Returns the price of last transaction. If there are no transactions, returns None."""
        if not self.transactions or len(self.transactions) == 0:
            return None
        transactions = [
            {"price": t["price"], "timestamp": t["timestamp"].timestamp()}
            for t in self.transactions
        ]
        # sort by timestamp
        transactions.sort(key=lambda x: x["timestamp"])
        return transactions[-1]["price"]

    async def initialize(self) -> None:
        self.start_time = now()
        self.active = True
        self.connection = await aio_pika.connect_robust(rabbitmq_url)
        self.channel = await self.connection.channel()

        await self.channel.declare_exchange(
            self.broadcast_exchange_name, aio_pika.ExchangeType.FANOUT, auto_delete=True
        )
        self.trader_exchange = await self.channel.declare_exchange(
            self.queue_name, aio_pika.ExchangeType.DIRECT, auto_delete=True
        )
        trader_queue = await self.channel.declare_queue(
            self.queue_name, auto_delete=True
        )
        await trader_queue.bind(self.trader_exchange)  # bind the queue to the exchange
        await trader_queue.consume(self.on_individual_message)

        await trader_queue.purge()

    async def clean_up(self) -> None:
        """
        This one is mostly used for closing connections and channels opened by a trading session.
        At this stage we also dump existing transactions and orders from the memory. In the future, we'll probably
        dump them to a database.
        """

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
        except Exception as e:
            logger.error(f"An error occurred during cleanup: {e}")

    def get_active_orders_to_broadcast(self) -> List[Dict]:
        # Convert the active orders dictionary to a Polars DataFrame
        active_orders_df = pl.DataFrame(list(self.active_orders.values()))

        # Check if the DataFrame is empty
        if active_orders_df.height == 0:
            return []

        # Select the necessary columns
        active_orders_df = active_orders_df.select(
            ["id", "trader_id", "order_type", "amount", "price", "timestamp"]
        )

        # Convert to list of dictionaries
        res = active_orders_df.to_dicts()
        return res

    async def send_broadcast(self, message: dict, message_type="BOOK_UPDATED", incoming_message=None) -> None:
        if "type" not in message:
            message["type"] = message_type  # Only set default if not specified

        spread, midpoint = self.get_spread()

        async with self.lock:  # acquire lock before accessing the order book
            order_book_snapshot = self.order_book

        message.update({
            "order_book": order_book_snapshot,
            "active_orders": self.get_active_orders_to_broadcast(),
            "history": self.transactions,
            "spread": spread,
            "midpoint": midpoint,
            "transaction_price": self.transaction_price,
            "incoming_message": incoming_message,
        })
        message_document = Message(trading_session_id=self.id, content=message)
        message_document.save()

        exchange = await self.channel.get_exchange(self.broadcast_exchange_name)
        await exchange.publish(
            aio_pika.Message(body=json.dumps(message, cls=CustomEncoder).encode()),
            routing_key="",  # routing_key is typically ignored in FANOUT exchanges
        )

    async def send_message_to_trader(self, trader_id: str, message: dict) -> None:
        transactions = [
            {"price": t["price"], "timestamp": t["timestamp"].timestamp()}
            for t in self.transactions
        ]
        transactions.sort(key=lambda x: x["timestamp"])
        if transactions:
            current_price = transactions[-1]["price"]
        else:
            current_price = None
        spread, mid_price = self.get_spread()

        async with self.lock:  # acquire lock before accessing the order book
            order_book_snapshot = self.order_book

        message.update(
            {
                "type": "a message to all",
                "order_book": order_book_snapshot,
                "active_orders": self.get_active_orders_to_broadcast(),
                "transaction_history": self.transactions,
                "spread": spread,
                "mid_price": mid_price,
                "current_price": current_price,
            }
        )

    @property
    def list_active_orders(self) -> List[Dict]:
        """Returns a list of all active orders. When we switch to real DB or mongo, we won't need it anymore."""
        return list(self.active_orders.values())

    def get_file_name(self) -> str:
        # todo: rename this to get_message_file_name
        """Returns file name for messages which is a trading platform id + datetime of creation with _ as spaces"""
        return f"{self.id}_{self.creation_time.strftime('%Y-%m-%d_%H-%M-%S')}"

    def place_order(self, order_dict: Dict) -> Dict:
        order_id = order_dict["id"]
        order_dict.update(
            {
                "status": OrderStatus.ACTIVE.value,
            }
        )
        self.all_orders[order_id] = order_dict
        return order_dict

    def get_spread(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Returns the spread and the midpoint. If there are no overlapping orders, returns None, None.
        """
        asks = [
            order
            for order in self.active_orders.values()
            if order["order_type"] == OrderType.ASK
        ]
        bids = [
            order
            for order in self.active_orders.values()
            if order["order_type"] == OrderType.BID
        ]

        # Sort by price (lowest first for asks), and then by timestamp (oldest first - FIFO)
        asks.sort(key=lambda x: (x["price"], x["timestamp"]))
        # Sort by price (highest first for bids), and then by timestamp (oldest first)
        bids.sort(key=lambda x: (-x["price"], x["timestamp"]))

        # Calculate the spread
        if asks and bids:
            lowest_ask = asks[0]["price"]
            highest_bid = bids[0]["price"]
            spread = lowest_ask - highest_bid
            mid_price = (lowest_ask + highest_bid) / 2
            return spread, mid_price
        else:
            logger.info("No overlapping orders.")
            return None, None

    async def create_transaction(self, bid: Dict, ask: Dict, transaction_price: float) -> Tuple[str, str, TransactionModel]:
        self.all_orders[ask["id"]]["status"] = OrderStatus.EXECUTED.value
        self.all_orders[bid["id"]]["status"] = OrderStatus.EXECUTED.value

        transaction = TransactionModel(
            trading_session_id=self.id,
            bid_order_id=bid["id"],
            ask_order_id=ask["id"],
            price=transaction_price,
        )

        await self.transaction_queue.put(transaction)
        logger.info(f"Transaction enqueued: {transaction}")

        # Send transaction details to both traders
        transaction_details = {
            "type": "transaction_update",
            "transactions": [
                {"id": ask["id"], "price": transaction_price, "type": "ask", "amount": ask["amount"]},
                {"id": bid["id"], "price": transaction_price, "type": "bid", "amount": bid["amount"]}
            ]
        }
        await self.send_message_to_trader(ask["trader_id"], transaction_details)
        await self.send_message_to_trader(bid["trader_id"], transaction_details)
        # print(f'sent transactions to traders, type is {transaction_details["type"]}')
        return ask["trader_id"], bid["trader_id"], transaction

    async def process_transactions(self) -> None:
        while True:
            transaction = await self.transaction_queue.get()
            await transaction.save_async()
            self.transaction_queue.task_done()
            logger.info(f"Transaction processed: {transaction}")

    async def clear_orders(self) -> Dict:
        res = {"transactions": [], "removed_active_orders": []}
        asks = [
            order
            for order in self.active_orders.values()
            if order["order_type"] == OrderType.ASK
        ]
        bids = [
            order
            for order in self.active_orders.values()
            if order["order_type"] == OrderType.BID
        ]

        asks.sort(key=lambda x: (x["price"], x["timestamp"]))
        bids.sort(key=lambda x: (-x["price"], x["timestamp"]))

        if asks and bids:
            lowest_ask = asks[0]["price"]
            highest_bid = bids[0]["price"]
            spread = lowest_ask - highest_bid
        else:
            logger.info("No overlapping orders.")
            return res

        if spread > 0:
            logger.info(
                f"No overlapping orders. Spread is positive: {spread}. Lowest ask: {lowest_ask}, highest bid: {highest_bid}"
            )
            return res

        viable_asks = [ask for ask in asks if ask["price"] <= highest_bid]
        viable_bids = [bid for bid in bids if bid["price"] >= lowest_ask]

        transactions = []
        participated_traders = set()
        traders_to_transactions_lookup = defaultdict(list)

        while viable_asks and viable_bids:
            ask = viable_asks.pop(0)
            bid = viable_bids.pop(0)

            transaction_price = (ask["price"] + bid["price"]) / 2
            ask_trader_type = self.connected_traders[ask["trader_id"]]["trader_type"]
            ask_trader_id = ask.get("trader_id")
            bid_trader_id = bid.get("trader_id")

            if (
                ask_trader_type == TraderType.HUMAN.value
                and ask_trader_id == bid_trader_id
            ):
                logger.warning(f"Blocking self-execution for trader {ask_trader_id}")
                return res

            ask_trader_id, bid_trader_id, transaction = await self.create_transaction(
                bid, ask, transaction_price
            )

            participated_traders.add(ask_trader_id)
            participated_traders.add(bid_trader_id)

            traders_to_transactions_lookup[ask["trader_id"]].append(
                {
                    "id": ask["id"],
                    "price": ask["price"],
                    "type": "ask",
                    "amount": ask["amount"],
                }
            )
            traders_to_transactions_lookup[bid["trader_id"]].append(
                {
                    "id": bid["id"],
                    "price": bid["price"],
                    "type": "bid",
                    "amount": bid["amount"],
                }
            )

            transactions.append(transaction)

        if transactions:
            res["subgroup_broadcast"] = traders_to_transactions_lookup

        return res

    async def handle_add_order(self, data: dict) -> Dict:
        data["order_type"] = int(data["order_type"])
        try:
            order = Order(status=OrderStatus.BUFFERED.value, session_id=self.id, **data)
            self.place_order(order.model_dump())
        except ValidationError as e:
            logger.critical(f"Order validation failed: {e}")
            return {"status": "failed", "reason": str(e), "type": "order_failed"}

        # Clear orders and prepare for response
        resp = await self.clear_orders()
        subgroup_data = resp.pop("subgroup_broadcast", None)
        if subgroup_data:
            await self.send_message_to_subgroup(subgroup_data)

        resp.update({"type": "NEW_ORDER_ADDED", "content": "A", "respond": True})
        return resp


    async def handle_cancel_order(self, data: dict) -> Dict:
        order_id = data.get("order_id")
        trader_id = data.get("trader_id")
        order_details = data.get("order_details")  # Ensure this key exists in the message

        try:
            order_id = uuid.UUID(order_id)
        except ValueError:
            logger.warning(f"Invalid order ID format: {order_id}.")
            return {"status": "failed", "reason": "Invalid order ID format"}

        async with self.lock:
            if order_id not in self.active_orders:
                return {"status": "failed", "reason": "Order not found"}

            existing_order = self.active_orders[order_id]
            if existing_order["trader_id"] != trader_id:
                return {"status": "failed", "reason": "Trader does not own the order"}

            if existing_order["status"] != OrderStatus.ACTIVE.value:
                return {"status": "failed", "reason": "Order is not active"}

            # Log the cancellation with details
            message_document = Message(
                trading_session_id=self.id,
                content={
                    "action": "order_cancelled",
                    "order_id": str(order_id),
                    "details": order_details  # Include negative amount and other details
                }
            )
            message_document.save()

            # Update order status
            self.all_orders[order_id]["status"] = OrderStatus.CANCELLED.value
            self.all_orders[order_id]["cancellation_timestamp"] = now()

            return {"status": "cancel success", "order": order_id, "type": "ORDER_CANCELLED", "respond": True}

    async def send_message_to_subgroup(self, message: Dict) -> None:
        for trader_id, transaction_list in message.items():
            await self.send_message_to_trader(
                trader_id,
                {"type": "a message to subgroup", "new_transactions": transaction_list},
            )

    @if_active
    async def handle_cancel_order(self, data: dict) -> Dict:
        order_id = data.get("order_id")
        trader_id = data.get("trader_id")

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

            if existing_order["trader_id"] != trader_id:
                logger.warning(f"Trader {trader_id} does not own order {order_id}.")
                return {"status": "failed", "reason": "Trader does not own the order"}

            if existing_order["status"] != OrderStatus.ACTIVE.value:
                logger.warning(
                    f"Order {order_id} is not active and cannot be canceled."
                )
                return {"status": "failed", "reason": "Order is not active"}

            # Cancel the order
            self.all_orders[order_id]["status"] = OrderStatus.CANCELLED.value
            self.all_orders[order_id]["cancellation_timestamp"] = now()

            return {"status": "cancel success", "order": order_id, "respond": True}

    @if_active
    async def handle_register_me(self, msg_body: Dict) -> Dict:
        trader_id = msg_body.get("trader_id")
        trader_type = msg_body.get("trader_type")
        self.connected_traders[trader_id] = {
            "trader_type": trader_type,
        }
        self.trader_responses[trader_id] = False

        logger.info(f"Trader type  {trader_type} id {trader_id} connected.")
        logger.info(f"Total connected traders: {len(self.connected_traders)}")
        return dict(
            respond=True,
            trader_id=trader_id,
            message="Registered successfully",
            individual=True,
        )

    async def on_individual_message(self, message: Dict) -> None:
        incoming_message = json.loads(message.body.decode())
        logger.info(f"TS {self.id} received message: {incoming_message}")
        action = incoming_message.pop("action", None)
        trader_id = incoming_message.get("trader_id", None)
        if incoming_message is None:
            logger.critical(f"Invalid message format: {message}")

        if action:
            handler_method = getattr(self, f"handle_{action}", None)
            if handler_method:
                result = await handler_method(incoming_message)
                if result and result.pop("respond", None) and trader_id:
                    await self.send_message_to_trader(trader_id, result)
                    # Check if the message is meant for individual or all traders
                    if not result.get("individual", False):
                        # Determine the appropriate message type based on the action
                        message_type = f"{action.upper()}"
                        await self.send_broadcast(
                            message=dict(text=f"{action} update processed"),
                            message_type=message_type,
                            incoming_message=incoming_message,
                        )

            else:
                logger.warning(f"No handler method found for action: {action}")
        else:
            logger.warning(f"No action found in message: {incoming_message}")

    async def close_existing_book(self) -> None:
        """we create a counteroffer on behalf of the platform with a get_closure_price price. and then we
        create a transaction out of it."""
        for order_id, order in self.active_orders.items():
            platform_order_type = (
                OrderType.ASK.value
                if order["order_type"] == OrderType.BID
                else OrderType.BID
            )
            closure_price = self.get_closure_price(order["amount"], order["order_type"])
            platform_order = Order(
                trader_id=self.id,
                order_type=platform_order_type,
                amount=order["amount"],
                price=closure_price,
                status=OrderStatus.BUFFERED.value,
                session_id=self.id,
            )

            self.place_order(platform_order.model_dump())
            if order["order_type"] == OrderType.BID:
                await self.create_transaction(
                    order, platform_order.model_dump(), closure_price
                )
            else:
                await self.create_transaction(
                    platform_order.model_dump(), order, closure_price
                )

        await self.send_broadcast(message=dict(text="book is updated"))

    async def handle_inventory_report(self, data: dict) -> Dict:
        trader_id = data.get("trader_id")
        self.trader_responses[trader_id] = True
        trader_type = self.connected_traders[trader_id]["trader_type"]
        logger.info(
            f"Trader ({trader_type}):  {trader_id} has reported back their inventory: {data}"
        )
        shares = data.get("shares", 0)

        if shares != 0:
            trader_order_type = OrderType.ASK if shares > 0 else OrderType.BID
            platform_order_type = OrderType.BID if shares > 0 else OrderType.ASK
            shares = abs(shares)
            closure_price = self.get_closure_price(shares, trader_order_type)

            proto_order = dict(
                amount=shares,
                price=closure_price,
                status=OrderStatus.BUFFERED.value,
                session_id=self.id,
            )
            trader_order = Order(
                trader_id=trader_id, order_type=trader_order_type, **proto_order
            )
            platform_order = Order(
                trader_id=self.id, order_type=platform_order_type, **proto_order
            )
            self.place_order(platform_order.model_dump())
            self.place_order(trader_order.model_dump())

            if trader_order_type == OrderType.BID:
                await self.create_transaction(
                    trader_order.model_dump(),
                    platform_order.model_dump(),
                    closure_price,
                )
            else:
                await self.create_transaction(
                    platform_order.model_dump(),
                    trader_order.model_dump(),
                    closure_price,
                )

            traders_to_transactions_lookup = defaultdict(list)
            trader_order = trader_order.model_dump()
            traders_to_transactions_lookup[trader_id].append(
                {
                    "id": trader_order["id"],
                    "price": trader_order["price"],
                    "type": trader_order["order_type"],
                    "amount": trader_order["amount"],
                }
            )

            await self.send_message_to_subgroup(traders_to_transactions_lookup)

    async def wait_for_traders(self) -> None:
        while not all(self.trader_responses.values()):
            await asyncio.sleep(1)  # Check every second
        logger.info("All traders have reported back their inventories.")

    async def run(self) -> None:
        try:
            while not self._stop_requested.is_set():
                self.transaction_processor_task = asyncio.create_task(
                    self.process_transactions()
                )
                current_time = now()
                if current_time - self.start_time > timedelta(minutes=self.duration):
                    logger.critical("Time limit reached, stopping...")
                    self.active = False  # here we stop accepting all incoming requests on placing new orders, cancelling etc.
                    await self.close_existing_book()
                    await self.send_broadcast({"type": "stop_trading"})
                    # Wait for each of the traders to report back their inventories
                    await self.wait_for_traders()
                    await self.send_broadcast({"type": "closure"})

                    break
                await asyncio.sleep(1)
            logger.critical("Exited the run loop.")
        except asyncio.CancelledError:
            logger.info(
                "Run method cancelled, performing cleanup of trading session..."
            )

            raise

        except Exception as e:
            # Handle the exception here
            logger.error(f"Exception in trading session run: {e}")
            # Optionally re-raise the exception if you want it to be propagated
            raise
        finally:
            await self.clean_up()
