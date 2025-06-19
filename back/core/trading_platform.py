import asyncio
import json
import os
from asyncio import Event
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Set
import uuid

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
        
        # Direct references to traders (no messaging needed)
        self.traders = {}  # trader_id -> trader_instance
        self.websocket_subscribers: Set = set()  # WebSocket connections for humans
        
        # Set up asyncio components
        self._stop_requested = asyncio.Event()
        self.order_lock: asyncio.Lock = asyncio.Lock()
        
        # Initialize other attributes
        self.active = False
        self.start_time: Optional[datetime] = None
        self.creation_time = datetime.now(timezone.utc)
        self.initialization_complete = False
        self.trading_started = False
        self.current_price = 0
        self.is_finished = False
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
    
    def register_trader(self, trader_id: str, trader_instance):
        """Register trader for direct communication"""
        self.traders[trader_id] = trader_instance
        self.connected_traders[trader_id] = {"trader_type": trader_instance.trader_type}
        
    def register_websocket(self, websocket):
        """Register WebSocket for human trader updates"""
        self.websocket_subscribers.add(websocket)
        
    def unregister_websocket(self, websocket):
        """Unregister WebSocket"""
        self.websocket_subscribers.discard(websocket)

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

    async def broadcast_to_websockets(self, message: dict) -> None:
        """Send message to all WebSocket connections"""
        if not self.websocket_subscribers:
            return
            
        # Create tasks for all websocket sends
        tasks = []
        for websocket in list(self.websocket_subscribers):  # Copy to avoid modification during iteration
            tasks.append(self._safe_websocket_send(websocket, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _safe_websocket_send(self, websocket, message):
        """Safely send message to websocket"""
        try:
            await websocket.send_json(message)
        except Exception:
            # Remove broken websocket
            self.websocket_subscribers.discard(websocket)

    async def notify_traders(self, message_type: str, data: dict = None) -> None:
        """Notify all automated traders directly with specific updates"""
        data = data or {}
        
        # Prepare common update data
        update_data = {
            "order_book": await self.get_order_book_snapshot(),
            "midpoint": self.order_book_manager.get_spread()[1],
            "active_orders": self.get_active_orders_to_broadcast(),
            **data
        }
        
        for trader_id, trader in self.traders.items():
            try:
                # Update trader's internal state directly
                if update_data.get("order_book"):
                    trader.order_book = update_data["order_book"]
                    
                if update_data.get("midpoint"):
                    trader.update_mid_price(update_data["midpoint"])
                    
                if update_data.get("active_orders"):
                    trader.active_orders_in_book = update_data["active_orders"]
                    own_orders = [order for order in update_data["active_orders"] if order["trader_id"] == trader_id]
                    trader.orders = own_orders
                
                # Handle specific message types
                if message_type == "TRADING_STARTED" and hasattr(trader, 'handle_TRADING_STARTED'):
                    await trader.handle_TRADING_STARTED(data)
                elif message_type == "transaction_update" and data.get("transactions"):
                    trader.update_filled_orders(data["transactions"])
                    
            except Exception as e:
                logger.error(f"Error notifying trader {trader_id}: {e}")

    async def send_broadcast(self, message_type: str, data: dict = None, **kwargs) -> None:
        """Send updates to all traders and WebSocket connections"""
        data = data or {}
        
        # Get order book data
        order_book_snapshot = await self.get_order_book_snapshot()
        active_orders = self.get_active_orders_to_broadcast()
        spread_info = self.order_book_manager.get_spread()
        
        # DEBUG: Print order book state
        print(f"\n=== ORDER BOOK DEBUG ({message_type}) ===")
        print(f"Bids: {order_book_snapshot.get('bids', [])}")
        print(f"Asks: {order_book_snapshot.get('asks', [])}")
        print(f"Active orders count: {len(active_orders)}")
        print(f"First few active orders: {active_orders[:3] if active_orders else 'None'}")
        print(f"Spread info: {spread_info}")
        print(f"WebSocket subscribers: {len(self.websocket_subscribers)}")
        print("===================================\n")
        
        # Create comprehensive message for WebSocket connections
        ws_message = {
            "type": message_type,
            "current_time": self.current_time.isoformat(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "duration": self.duration,
            "order_book": order_book_snapshot,
            "active_orders": active_orders,
            "history": self.get_transaction_history(),
            "spread": spread_info[0],
            "midpoint": spread_info[1],
            "transaction_price": self.transaction_price,
            **data,
            **kwargs
        }

        # Send to WebSocket connections (humans)
        await self.broadcast_to_websockets(ws_message)
        
        # Send to automated traders with direct updates
        await self.notify_traders(message_type, data)
    
    async def create_transaction(
        self, bid: Dict, ask: Dict, transaction_price: float
    ) -> Tuple[str, str, TransactionModel]:
        ask_trader_id, bid_trader_id, transaction, transaction_details = await self.transaction_manager.create_transaction(bid, ask, transaction_price)

        # Send transaction details via broadcast
        await self.send_broadcast(
            message_type="transaction_update",
            data={"transactions": [transaction_details]}
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
    async def add_order(self, order_data: dict, trader_id: str = None) -> Dict:
        """Add a new order to the order book."""
        async with self.order_lock:
            return await self._process_add_order(order_data, trader_id)

    async def _process_add_order(self, data: dict, trader_id: str = None) -> Dict:
        """Process the addition of a new order."""
        data["order_type"] = int(data["order_type"])
        informed_trader_progress = data.get("informed_trader_progress")
        order_id = data.get("order_id")
        if order_id:
            data["id"] = order_id

        # Ensure trader_id is set
        if trader_id:
            data["trader_id"] = trader_id

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

        # Send broadcast update
        await self.send_broadcast(
            message_type="ADDED_ORDER",
            data={"informed_trader_progress": informed_trader_progress}
        )

        return {
            "type": "ADDED_ORDER",
            "content": "Order added successfully",
            "respond": True,
            "informed_trader_progress": informed_trader_progress,
        }

    @if_active
    async def cancel_order(self, order_id: str, trader_id: str = None) -> Dict:
        """Cancel an order."""
        try:
            cancel_result = self.order_book_manager.cancel_order(order_id)

            if cancel_result:
                self.trading_logger.info(f"CANCEL_ORDER: {{'order_id': '{order_id}', 'trader_id': '{trader_id}'}}")
                
                # Send broadcast update
                await self.send_broadcast(message_type="ORDER_CANCELLED")
                
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

        await self.send_broadcast(message_type="book_updated")

    def set_initialization_complete(self):
        """Set the initialization_complete flag."""
        self.initialization_complete = True

    async def start_trading(self):
        """Start the trading market."""
        self.start_time = datetime.now(timezone.utc)
        self.active = True
        self.trading_started = True
        
        await self.send_broadcast(message_type="TRADING_STARTED", data={"content": "Market is open"})

    async def run(self) -> None:
        """Run the trading market."""
        start_time = datetime.now(timezone.utc)
        while not self._stop_requested.is_set():
            current_time = datetime.now(timezone.utc)
            if self._should_stop_trading(current_time):
                await self._end_trading_market()
                break
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
        await self.send_broadcast(message_type="stop_trading")
        await self.send_broadcast(message_type="closure")
        self.is_finished = True

    # Legacy methods for compatibility (can be removed later)
    async def handle_add_order(self, data: dict, trader_id: str = None) -> Dict:
        """Legacy wrapper - use add_order() instead"""
        return await self.add_order(data, trader_id)
        
    async def handle_cancel_order(self, data: dict, trader_id: str = None) -> Dict:
        """Legacy wrapper - use cancel_order() instead"""
        order_id = data.get("order_id")
        trader_id = trader_id or data.get("trader_id")
        return await self.cancel_order(order_id, trader_id)
        
    async def handle_register_me(self, trader_id: str, trader_type: str, gmail_username: str = None) -> Dict:
        """Legacy wrapper for registration"""
        # Registration is now handled automatically in register_trader()
        return {
            "respond": True,
            "trader_id": trader_id,
            "message": "Registered successfully",
            "individual": True,
        }
