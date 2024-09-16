import asyncio
import json
import os
import uuid
from asyncio import Event, Lock
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import aio_pika
import polars as pl
from pydantic import ValidationError

from utils import setup_custom_logger, setup_trading_logger
from utils import CustomEncoder, if_active
from core.order_book import OrderBook

from uuid import UUID

from core.data_models import (
    Message,
    Order,
    OrderStatus,
    OrderType,
    TraderType,
    TransactionModel,
)

rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://localhost")
logger = setup_custom_logger(__name__)

class TradingSession:
    def __init__(
        self,
        session_id: str,
        duration: int,
        default_price: int,
        default_spread: int = 10,
        punishing_constant: int = 1,
        params: Dict = None,
    ):
        self.id = session_id
        self.duration = duration
        self.default_price = default_price
        self.default_spread = default_spread
        self.punishing_constant = punishing_constant
        self.active = False
        self.start_time = None
        self.creation_time = datetime.now(timezone.utc)
        self.order_book = OrderBook()
        self._last_transaction_price = None
        self.connected_traders = {}
        self.trader_responses = {}
        self._stop_requested = asyncio.Event()
        self.transaction_queue = asyncio.Queue()
        self.transaction_list = []
        self.initialization_complete = False
        self.trading_started = False
        self.release_event = Event()
        self.current_price = 0
        self.is_finished = False
        self.params = params
        self.broadcast_exchange_name = f"broadcast_{self.id}"
        self.queue_name = f"trading_system_queue_{self.id}"
        self.trader_exchange = None
        self.process_transactions_task = None
        self.trading_logger = setup_trading_logger(self.id)
        self.order_lock = asyncio.Lock()

    def place_order(self, order_dict: Dict) -> Dict:
        return self.order_book.place_order(order_dict)

    @property
    def current_time(self) -> datetime:
        return datetime.now(timezone.utc)

    @property
    def transactions(self) -> List[Dict]:
        return [transaction.to_dict() for transaction in self.transaction_list]
    
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
            "end_time": self.start_time + timedelta(minutes=self.duration)
            if self.start_time
            else None,
            "connected_traders": self.connected_traders,
        }

    @property
    def is_full(self):
        return len(self.connected_traders) >= self.params['num_human_traders']

    @property
    def transaction_price(self) -> Optional[float]:
        return self._last_transaction_price

    async def initialize(self) -> None:
        self.start_time = datetime.now(timezone.utc)
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
        await trader_queue.bind(self.trader_exchange)
        await trader_queue.consume(self.on_individual_message)
        await trader_queue.purge()

        self.process_transactions_task = asyncio.create_task(self.process_transactions())

    async def clean_up(self) -> None:
        self._stop_requested.set()
        self.active = False
        trader_queue = await self.channel.get_queue(self.queue_name)
        await trader_queue.unbind(self.trader_exchange)
        await self.channel.close()
        await self.connection.close()

        if self.process_transactions_task:
            self.process_transactions_task.cancel()
            try:
                await self.process_transactions_task
            except asyncio.CancelledError:
                pass

    async def get_order_book_snapshot(self) -> Dict:
        return self.order_book.get_order_book_snapshot()

    def get_transaction_history(self) -> List[Dict]:
        return self.transactions

    def get_active_orders_to_broadcast(self) -> List[Dict]:
        active_orders = list(self.order_book.active_orders.values())
        processed_orders = []
        
        for order in active_orders:
            processed_order = {
                "id": str(order["id"]),
                "trader_id": str(order["trader_id"]),
                "order_type": int(order["order_type"]),
                "amount": float(order["amount"]),
                "price": float(order["price"]),
                "timestamp": str(order["timestamp"])
            }
            processed_orders.append(processed_order)
        
        if not processed_orders:
            return []
        
        try:
            active_orders_df = pl.DataFrame(processed_orders)
            return active_orders_df.select(
                ["id", "trader_id", "order_type", "amount", "price", "timestamp"]
            ).to_dicts()
        except Exception as e:
            logger.error(f"Error creating DataFrame: {e}")
            logger.error(f"Problematic orders: {processed_orders}")
            return []
            
    async def send_broadcast(
        self, message: dict, message_type="BOOK_UPDATED", incoming_message=None
    ) -> None:
        # print(f"Entering send_broadcast method with message_type: {message_type}")
        
        if "type" not in message:
            message["type"] = message_type

        message.update(
            {
                "current_time": self.current_time.isoformat(),
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "duration": self.duration,
                "order_book": await self.get_order_book_snapshot(),
                "active_orders": self.get_active_orders_to_broadcast(),
                "history": self.get_transaction_history(),
                "spread": self.order_book.get_spread()[0],
                "midpoint": self.order_book.get_spread()[1],
                "transaction_price": self.transaction_price,
                "incoming_message": incoming_message,
                "informed_trader_progress": incoming_message.get("informed_trader_progress") if incoming_message else None,
            }
        )

        current_history = self.get_transaction_history()
        print(f"Current history: {current_history}")

        # If this is a filled order, add matched_orders to the message
        if message_type == "FILLED_ORDER" and incoming_message:
            message["matched_orders"] = incoming_message.get("matched_orders")

        exchange = await self.channel.get_exchange(self.broadcast_exchange_name)
        await exchange.publish(
            aio_pika.Message(body=json.dumps(message, cls=CustomEncoder).encode()),
            routing_key="",
        )

    async def create_transaction(
        self, bid: Dict, ask: Dict, transaction_price: float
    ) -> Tuple[str, str, TransactionModel]:
        bid_id, ask_id = bid["id"], ask["id"]

        transaction = TransactionModel(
            trading_session_id=self.id,
            bid_order_id=bid_id,
            ask_order_id=ask_id,
            price=transaction_price,
            informed_trader_progress=bid.get("informed_trader_progress") or ask.get("informed_trader_progress")
        )

        self.transaction_list.append(transaction)
        await self.transaction_queue.put(transaction)
        logger.info(f"Transaction enqueued: {transaction}")

        self._last_transaction_price = transaction_price

        transaction_details = {
            "type": "transaction_update",
            "transactions": [
                {
                    "id": order["id"],
                    "price": transaction_price,
                    "type": "ask" if order["order_type"] == OrderType.ASK else "bid",
                    "amount": order["amount"],
                    "trader_id": order["trader_id"],
                }
                for order in [ask, bid]
            ],
            "matched_orders": {
                "bid_order_id": str(bid_id),
                "ask_order_id": str(ask_id),
            },
        }

        exchange = await self.channel.get_exchange(self.broadcast_exchange_name)
        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(transaction_details, cls=CustomEncoder).encode()
            ),
            routing_key="",
        )

        return ask["trader_id"], bid["trader_id"], transaction
            
    async def process_transactions(self) -> None:
        try:
            while not self._stop_requested.is_set():
                try:
                    transaction = await asyncio.wait_for(self.transaction_queue.get(), timeout=0.1)
                    # No need to append to self.transaction_list here, as it's done in create_transaction
                    self.transaction_queue.task_done()
                    logger.info(f"Transaction processed: {transaction}")

                    self._last_transaction_price = transaction.price
                except asyncio.TimeoutError:
                    pass
        except asyncio.CancelledError:
            # Handle cancellation gracefully
            pass

    async def clear_orders(self) -> Dict:
        matched_orders = self.order_book.clear_orders()
        res = {"transactions": [], "removed_active_orders": []}

        for ask, bid, transaction_price in matched_orders:
            transaction = await self.create_transaction(bid, ask, transaction_price)
            res["transactions"].append(transaction)
            res["removed_active_orders"].extend([ask["id"], bid["id"]])

        return res

    @if_active
    async def handle_add_order(self, data: dict) -> Dict:
        async with self.order_lock:  # Add a lock to ensure sequential processing
            data["order_type"] = int(data["order_type"])
            informed_trader_progress = data.get("informed_trader_progress")
            order_id = data.get("order_id")
            if order_id:
                data["id"] = order_id

            order = Order(status=OrderStatus.BUFFERED.value, session_id=self.id, **data)
            order_dict = order.model_dump()

            if informed_trader_progress is not None:
                order_dict["informed_trader_progress"] = informed_trader_progress

            order_dict["id"] = str(order_dict["id"])

            # Log the add order event immediately
            self.trading_logger.info(f"ADD_ORDER: {order_dict}")

            placed_order, immediately_matched = self.order_book.place_order(order_dict)

            if immediately_matched:
                matched_orders = self.order_book.clear_orders()
                transactions = []
                for ask, bid, transaction_price in matched_orders:
                    transaction = await self.create_transaction(bid, ask, transaction_price)
                    transactions.append(transaction)

                    # Log the matched order event immediately after the match
                    match_data = {
                        "bid_order_id": str(bid["id"]),
                        "ask_order_id": str(ask["id"]),
                        "transaction_price": transaction_price,
                        "amount": min(bid["amount"], ask["amount"])
                    }
                    self.trading_logger.info(f"MATCHED_ORDER: {match_data}")

                return {
                    "transactions": transactions,
                    "type": "FILLED_ORDER",
                    "content": "F",
                    "respond": True,
                    "incoming_message": data,
                    "informed_trader_progress": informed_trader_progress,
                }
            else:
                return {
                    "type": "ADDED_ORDER",
                    "content": "A",
                    "respond": True,
                    "informed_trader_progress": informed_trader_progress,
                }      

    @if_active
    async def handle_cancel_order(self, data: dict) -> Dict:
        try:
            order_id = data.get("order_id")
            trader_id = data.get("trader_id")

            cancel_result = self.order_book.cancel_order(order_id)

            if cancel_result:
                self.trading_logger.info(f"CANCEL_ORDER: {data}")
                return {
                    "status": "cancel success",
                    "order_id": str(order_id),
                    "type": "ORDER_CANCELLED",
                    "respond": True,
                }

            return {
                "status": "failed",
                "reason": "Order not found or cancellation failed",
            }
        except Exception as e:
            print(f"Failed to send cancel order request: {e}")
            return {"status": "failed", "reason": str(e)}

    @if_active
    async def handle_register_me(self, msg_body: Dict) -> Dict:
        trader_id = msg_body.get("trader_id")
        trader_type = msg_body.get("trader_type")
        self.connected_traders[trader_id] = {
            "trader_type": trader_type,
        }
        self.trader_responses[trader_id] = False

        return {
            "respond": True,
            "trader_id": trader_id,
            "message": "Registered successfully",
            "individual": True,
        }

    async def on_individual_message(self, message: Dict) -> None:
        incoming_message = json.loads(message.body.decode())
        action = incoming_message.pop("action", None)
        trader_id = incoming_message.get("trader_id", None)

        if action:
            handler_method = getattr(self, f"handle_{action}", None)
            if handler_method:
                result = await handler_method(incoming_message)
                if result and result.pop("respond", None) and trader_id:
                    if not result.get("individual", False):
                        message_type = result.get("type", f"{action.upper()}")
                        await self.send_broadcast(
                            message=dict(text=f"{action} update processed"),
                            message_type=message_type,
                            incoming_message=result.get(
                                "incoming_message", incoming_message
                            ),
                        )

    async def close_existing_book(self) -> None:
        for order_id, order in self.order_book.active_orders.items():
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

        return {}

    def set_initialization_complete(self):
        self.initialization_complete = True

    async def start_trading(self):
        self.start_time = datetime.now(timezone.utc)
        self.active = True
        self.trading_started = True
        await self.send_broadcast(
            {"type": "TRADING_STARTED", "content": "Market is open"}
        )

    async def run(self) -> None:
        start_time = datetime.now(timezone.utc)
        while not self._stop_requested.is_set():
            current_time = datetime.now(timezone.utc)
            if self.start_time and current_time - self.start_time > timedelta(
                minutes=self.duration
            ):
                self.active = False
                await self.send_broadcast({"type": "stop_trading"})
                await asyncio.gather(
                    *[
                        self.handle_inventory_report({"trader_id": trader_id})
                        for trader_id in self.connected_traders
                    ]
                )
                await self.send_broadcast({"type": "closure"})
                self.is_finished = True  # new attribute that indicates if the trading session is finished
                break
            await asyncio.sleep(1)
        await self.clean_up()