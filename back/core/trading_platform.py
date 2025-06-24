import asyncio
import json
import os
from asyncio import Event
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import uuid

import polars as pl
from pydantic import ValidationError

from utils import setup_custom_logger, setup_trading_logger, CustomEncoder, if_active
from core.orderbook_manager import OrderBookManager
from core.transaction_manager import TransactionManager
from core.data_models import (
    Message,
    Order,
    OrderStatus,
    OrderType,
    TraderType,
    TransactionModel,
)

logger = setup_custom_logger(__name__)

class TradingPlatform:
    def __init__(
        self,
        market_id: str,
        duration: int,
        default_price: int,
        default_spread: int = 10,
        punishing_constant: int = 1,
        params: Dict = None,
    ):
        # Initialize attributes
        self.id = market_id
        self.duration = duration
        self.default_price = default_price
        self.default_spread = default_spread
        self.punishing_constant = punishing_constant
        self.params = params or {}
        
        # Set up trading components
        self.order_book_manager = OrderBookManager()
        self.transaction_manager = TransactionManager(market_id)
        self.connected_traders: Dict[str, Dict] = {}
        self.trader_responses: Dict[str, bool] = {}
        self.websockets = set()  # Store WebSocket connections for broadcasting
        
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
        
        # Set up task management
        self.process_transactions_task = None
        
        # Set up logging
        self.trading_logger = setup_trading_logger(self.id)

    async def initialize(self) -> None:
        """Initialize the trading platform."""
        self.start_time = datetime.now(timezone.utc)
        self.active = True
        self.process_transactions_task = asyncio.create_task(self.transaction_manager.process_transactions())

    async def clean_up(self) -> None:
        """Clean up resources when shutting down."""
        self._stop_requested.set()
        self.active = False
        

        
        # Cancel transaction processor
        if self.process_transactions_task:
            self.process_transactions_task.cancel()
            try:
                await self.process_transactions_task
            except asyncio.CancelledError:
                pass

    # WebSocket connection management
    def register_websocket(self, websocket):
        """Register a WebSocket connection for broadcasting."""
        self.websockets.add(websocket)
    
    def unregister_websocket(self, websocket):
        """Unregister a WebSocket connection."""
        self.websockets.discard(websocket)
    
    async def broadcast_to_websockets(self, message: dict) -> None:
        """Broadcast a message to all connected WebSockets."""
        if not self.websockets:
            return
        
        # Send message to all connected WebSockets
        disconnected = set()
        for websocket in self.websockets.copy():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send message to WebSocket: {e}")
                disconnected.add(websocket)
        
        # Remove disconnected WebSockets
        for websocket in disconnected:
            self.websockets.discard(websocket)

    async def handle_trader_message(self, message: dict) -> dict:
        """Handle messages from traders and route them to appropriate handlers."""
        action_type = message.get("type", message.get("action"))
        
        if action_type == "add_order":
            return await self.handle_add_order(message)
        elif action_type == "cancel_order":
            return await self.handle_cancel_order(message)
        elif action_type == "register_me":
            return await self.handle_register_me(message)
        elif action_type == "inventory_report":
            return await self.handle_inventory_report(message)
        else:
            logger.warning(f"Unknown trader message type: {action_type}")
            return {"status": "error", "message": "Unknown message type"}

    async def send_message_to_traders(self, message: dict, trader_list=None) -> None:
        """Send a message to all traders or a specific list of traders."""
        if trader_list is None:
            # Send to all connected traders
            trader_list = list(self.connected_traders.keys())
        
        for trader_id in trader_list:
            trader_info = self.connected_traders.get(trader_id)
            if trader_info and 'trader_instance' in trader_info:
                trader = trader_info['trader_instance']
                try:
                    await trader.on_message_from_system(message)
                except Exception as e:
                    logger.error(f"Failed to send message to trader {trader_id}: {e}")

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
        """Get the trading market parameters."""
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
        """Check if the trading market is full."""
        return len(self.connected_traders) >= len(self.params['predefined_goals'])

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

        await self.broadcast_to_websockets(message)
        
        # Also send to traders directly for processing
        await self.send_message_to_traders(message)
    
    async def create_transaction(
        self, bid: Dict, ask: Dict, transaction_price: float
    ) -> Tuple[str, str, TransactionModel]:
        ask_trader_id, bid_trader_id, transaction, transaction_details = await self.transaction_manager.create_transaction(bid, ask, transaction_price)

        # Broadcast transaction details via WebSocket
        await self.broadcast_to_websockets(transaction_details)
        
        # Also send transaction details to traders for processing
        await self.send_message_to_traders(transaction_details)

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

        # Special handling for zero-amount orders (for record-keeping only)
        is_record_keeping = data.get("is_record_keeping", False)
        if data.get("amount") == 0 and is_record_keeping:
            # Log the zero-amount order for record-keeping
            record_order = {
                "id": data.get("id", str(uuid.uuid4())),
                "trader_id": data.get("trader_id"),
                "order_type": data.get("order_type"),
                "price": data.get("price"),
                "amount": 0,
                "timestamp": datetime.now(timezone.utc).timestamp(),
                "is_record_keeping": True
            }
            
            # Log the record-keeping order
            self.trading_logger.info(f"RECORD_KEEPING_ORDER: {record_order}")
            
            # Return immediately without adding to the order book
            return {
                "type": "RECORD_KEEPING_ORDER",
                "content": "Record keeping order processed",
                "respond": True,
                "informed_trader_progress": informed_trader_progress,
            }

        order = Order(status=OrderStatus.BUFFERED.value, market_id=self.id, **data)
        order_dict = order.model_dump()

        if informed_trader_progress is not None:
            order_dict["informed_trader_progress"] = informed_trader_progress

        order_dict["id"] = str(order_dict["id"])

        # Log the add order event immediately
        self.trading_logger.info(f"ADD_ORDER: {order_dict}")

        placed_order, immediately_matched = self.order_book_manager.place_order(order_dict)

        if immediately_matched:
            matched_orders = self.order_book_manager.clear_orders()
            
            # Process matched orders immediately
            for ask, bid, transaction_price in matched_orders:
                await self.create_transaction(bid, ask, transaction_price)
                # Log the matched order events
                match_data = {
                    "bid_order_id": str(bid["id"]),
                    "ask_order_id": str(ask["id"]),
                    "transaction_price": transaction_price,
                    "amount": min(bid["amount"], ask["amount"])
                }
                self.trading_logger.info(f"MATCHED_ORDER: {match_data}")

        # Broadcast order book update to all clients
        await self.send_broadcast(
            message={"order_added": True},
            message_type="BOOK_UPDATED",
            incoming_message={"informed_trader_progress": informed_trader_progress}
        )

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
                
                # Broadcast order book update after cancellation
                await self.send_broadcast(
                    message={"order_cancelled": True, "order_id": str(order_id)},
                    message_type="BOOK_UPDATED"
                )
                
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

    async def handle_register_me(self, msg_body: Dict) -> Dict:
        """Handle registering a new trader."""
        trader_id = msg_body.get("trader_id")
        trader_type = msg_body.get("trader_type")
        gmail_username = msg_body.get("gmail_username")
        trader_instance = msg_body.get("trader_instance")  # Add trader instance
        
        self.connected_traders[trader_id] = {
            "trader_type": trader_type,
            "gmail_username": gmail_username,
            "trader_instance": trader_instance,
        }
        self.trader_responses[trader_id] = False

        return {
            "respond": True,
            "trader_id": trader_id,
            "message": "Registered successfully",
            "individual": True,
        }



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
                market_id=self.id,
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
        
        # Check if the trader is still in connected_traders
        if trader_id not in self.connected_traders:
            logger.warning(f"Received inventory report for unknown trader: {trader_id}")
            return {}

        trader_type = self.connected_traders[trader_id].get("trader_type")
        if not trader_type:
            logger.warning(f"Trader type not found for trader: {trader_id}")
            return {}

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
                market_id=self.id,
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
        """Start the trading market."""
        self.start_time = datetime.now(timezone.utc)
        self.active = True
        self.trading_started = True
        await self.send_broadcast(
            {"type": "TRADING_STARTED", "content": "Market is open"}
        )

    async def run(self) -> None:
        """Run the trading market."""
        start_time = datetime.now(timezone.utc)
        while not self._stop_requested.is_set():
            current_time = datetime.now(timezone.utc)
            if self._should_stop_trading(current_time):
                await self._end_trading_market()
                break
            
            # Send time updates for the countdown timer
            if self.start_time and self.active:
                remaining_time_seconds = max(0, (self.duration * 60) - (current_time - self.start_time).total_seconds())
                time_update = {
                    "type": "time_update",
                    "data": {
                        "remainingTime": remaining_time_seconds,
                        "dayOver": remaining_time_seconds <= 0,
                        "current_time": current_time.isoformat(),
                        "is_trading_started": self.trading_started
                    }
                }
                await self.broadcast_to_websockets(time_update)
                
            await asyncio.sleep(1)
        
        # Add delay before cleanup
        await asyncio.sleep(3)
        await self.clean_up()

    def _should_stop_trading(self, current_time: datetime) -> bool:
        """Check if the trading market should stop."""
        return (
            self.start_time
            and current_time - self.start_time > timedelta(minutes=self.duration)
        )

    async def _end_trading_market(self) -> None:
        """End the trading market and perform cleanup."""
        self.active = False
        await self.close_existing_book()
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
