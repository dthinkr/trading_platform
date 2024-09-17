import asyncio
import json
import os
from asyncio import Event
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import aio_pika
import polars as pl
from pydantic import ValidationError

from utils import setup_custom_logger, setup_trading_logger, CustomEncoder, if_active
from core.orderbook_manager import OrderBookManager
from core.transaction_manager import TransactionManager
from core.rabbitmq_manager import RabbitMQManager
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

class TradingPlatform:
    def __init__(
        self,
        session_id: str,
        duration: int,
        default_price: int,
        default_spread: int = 10,
        punishing_constant: int = 1,
        params: Dict = None,
    ):
        # Initialize attributes
        self.id = session_id
        self.duration = duration
        self.default_price = default_price
        self.default_spread = default_spread
        self.punishing_constant = punishing_constant
        self.params = params or {}
        
        # Set up trading components
        self.order_book_manager = OrderBookManager()
        self.transaction_manager = TransactionManager(session_id)
        self.rabbitmq_manager = RabbitMQManager(rabbitmq_url)
        self.connected_traders: Dict[str, Dict] = {}
        self.trader_responses: Dict[str, bool] = {}
        
        # Set up asyncio components
        self._stop_requested = asyncio.Event()
        self.release_event: Event = Event()
        self.order_lock: asyncio.Lock = asyncio.Lock()
        
        # Initialize other attributes
        self.active = False
        self.start_time: Optional[datetime] = None
        self.creation_time = datetime.now(timezone.utc)
        self.initialization_complete = False
        self.trading_started = False
        self.current_price = 0
        self.is_finished = False
        
        # Set up RabbitMQ-related attributes
        self.broadcast_exchange_name = f"broadcast_{self.id}"
        self.queue_name = f"trading_system_queue_{self.id}"
        self.trader_exchange = None
        self.process_transactions_task = None
        
        # Set up logging
        self.trading_logger = setup_trading_logger(self.id)

    # Initialization and cleanup methods
    async def initialize(self) -> None:
        """Initialize the trading platform."""
        self.start_time = datetime.now(timezone.utc)
        self.active = True
        await self.rabbitmq_manager.initialize()
        await self._setup_rabbitmq()
        self.process_transactions_task = asyncio.create_task(self.transaction_manager.process_transactions())

    async def clean_up(self) -> None:
        """Clean up resources when shutting down."""
        self._stop_requested.set()
        self.active = False
        await self.rabbitmq_manager.clean_up()
        if self.process_transactions_task:
            self.process_transactions_task.cancel()
            try:
                await self.process_transactions_task
            except asyncio.CancelledError:
                pass

    # RabbitMQ setup and cleanup methods
    async def _setup_rabbitmq(self) -> None:
        """Set up RabbitMQ connections and exchanges."""
        await self.rabbitmq_manager.declare_exchange(self.broadcast_exchange_name, aio_pika.ExchangeType.FANOUT)
        self.trader_exchange = await self.rabbitmq_manager.declare_exchange(self.queue_name, aio_pika.ExchangeType.DIRECT)
        trader_queue = await self.rabbitmq_manager.declare_queue(self.queue_name)
        await self.rabbitmq_manager.bind_queue_to_exchange(self.queue_name, self.queue_name)
        await self.rabbitmq_manager.consume(self.queue_name, self.on_individual_message)

    # Order book methods
    def place_order(self, order_dict: Dict) -> Dict:
        """Place a new order in the order book."""
        return self.order_book_manager.place_order(order_dict)

    @property
    def current_time(self) -> datetime:
        """Get the current time."""
        return datetime.now(timezone.utc)

    @property
    def transactions(self) -> List[Dict]:
        """Get a list of transaction dictionaries."""
        return self.transaction_manager.transactions
    
    @property
    def mid_price(self) -> float:
        """Get the mid price."""
        return self.current_price or self.default_price

    def get_closure_price(self, shares: int, order_type: OrderType) -> float:
        """Calculate the closure price for a given order."""
        return (
            self.mid_price
            + order_type * shares * self.default_spread * self.punishing_constant
        )

    def get_params(self) -> Dict:
        """Get the trading session parameters."""
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
        """Check if the trading session is full."""
        return len(self.connected_traders) >= self.params['num_human_traders']

    @property
    def transaction_price(self) -> Optional[float]:
        """Get the last transaction price."""
        return self.transaction_manager.transaction_price

    async def get_order_book_snapshot(self) -> Dict:
        """Get a snapshot of the order book."""
        return self.order_book_manager.get_order_book_snapshot()

    def get_transaction_history(self) -> List[Dict]:
        """Get the transaction history."""
        return self.transactions

    def get_active_orders_to_broadcast(self) -> List[Dict]:
        """Get a list of active orders to broadcast."""
        return self.order_book_manager.get_active_orders_to_broadcast()

    async def send_broadcast(
        self, message: dict, message_type="BOOK_UPDATED", incoming_message=None
    ) -> None:
        
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
                "spread": self.order_book_manager.get_spread()[0],
                "midpoint": self.order_book_manager.get_spread()[1],
                "transaction_price": self.transaction_price,
                "incoming_message": incoming_message,
                "informed_trader_progress": incoming_message.get("informed_trader_progress") if incoming_message else None,
            }
        )

        current_history = self.get_transaction_history()

        if message_type == "FILLED_ORDER" and incoming_message:
            message["matched_orders"] = incoming_message.get("matched_orders")

        await self.rabbitmq_manager.publish(self.broadcast_exchange_name, message)
    
    async def create_transaction(
        self, bid: Dict, ask: Dict, transaction_price: float
    ) -> Tuple[str, str, TransactionModel]:
        ask_trader_id, bid_trader_id, transaction, transaction_details = await self.transaction_manager.create_transaction(bid, ask, transaction_price)

        logger.info(f"Transaction enqueued: {transaction}")

        # Use RabbitMQManager to publish the message
        await self.rabbitmq_manager.publish(
            self.broadcast_exchange_name,
            transaction_details,
            routing_key=""
        )

        return ask_trader_id, bid_trader_id, transaction


    async def clear_orders(self) -> Dict:
        """Clear matched orders from the order book."""
        matched_orders = self.order_book_manager.clear_orders()
        res = {"transactions": [], "removed_active_orders": []}

        for ask, bid, transaction_price in matched_orders:
            transaction = await self.create_transaction(bid, ask, transaction_price)
            res["transactions"].append(transaction)
            res["removed_active_orders"].extend([ask["id"], bid["id"]])

        return res

    @if_active
    async def handle_add_order(self, data: dict) -> Dict:
        """Handle adding a new order to the order book."""
        async with self.order_lock:
            return await self._process_add_order(data)

    async def _process_add_order(self, data: dict) -> Dict:
        """Process the addition of a new order."""
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

        placed_order, immediately_matched = self.order_book_manager.place_order(order_dict)

        if immediately_matched:
            matched_orders = self.order_book_manager.clear_orders()
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
        """Handle canceling an order."""
        try:
            order_id = data.get("order_id")
            trader_id = data.get("trader_id")

            cancel_result = self.order_book_manager.cancel_order(order_id)

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
            return {"status": "failed", "reason": str(e)}

    @if_active
    async def handle_register_me(self, msg_body: Dict) -> Dict:
        """Handle registering a new trader."""
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
        """Handle incoming messages from traders."""
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
        """Close the existing order book."""
        for order_id, order in self.order_book_manager.order_book.active_orders.items():
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
        """Handle inventory reports from traders."""
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
        """Set the initialization_complete flag."""
        self.initialization_complete = True

    async def start_trading(self):
        """Start the trading session."""
        self.start_time = datetime.now(timezone.utc)
        self.active = True
        self.trading_started = True
        await self.send_broadcast(
            {"type": "TRADING_STARTED", "content": "Market is open"}
        )

    async def run(self) -> None:
        """Run the trading session."""
        start_time = datetime.now(timezone.utc)
        while not self._stop_requested.is_set():
            current_time = datetime.now(timezone.utc)
            if self._should_stop_trading(current_time):
                await self._end_trading_session()
                break
            await asyncio.sleep(1)
        await self.clean_up()

    def _should_stop_trading(self, current_time: datetime) -> bool:
        """Check if the trading session should stop."""
        return (
            self.start_time
            and current_time - self.start_time > timedelta(minutes=self.duration)
        )

    async def _end_trading_session(self) -> None:
        """End the trading session and perform cleanup."""
        self.active = False
        await self.send_broadcast({"type": "stop_trading"})
        await self._handle_final_inventory_reports()
        await self.send_broadcast({"type": "closure"})
        self.is_finished = True

    async def _handle_final_inventory_reports(self) -> None:
        """Handle final inventory reports from all traders."""
        await asyncio.gather(
            *[
                self.handle_inventory_report({"trader_id": trader_id})
                for trader_id in self.connected_traders
            ]
        )