"""
New TradingPlatform implementation using event-driven architecture.
This replaces the bloated 558-line God class with clean separation of concerns.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from .handlers import MarketOrchestrator
from .data_models import OrderType


class TradingPlatform:
    """Lightweight coordinator using event-driven architecture."""
    
    def __init__(
        self,
        market_id: str,
        duration: int,
        default_price: int,
        default_spread: int = 10,
        punishing_constant: int = 1,
        params: Dict = None,
    ):
        # Store basic configuration
        self.id = market_id
        self.duration = duration
        self.default_price = default_price
        self.default_spread = default_spread
        self.punishing_constant = punishing_constant
        self.params = params or {}
        
        # Create the orchestrator that handles all the complexity
        self.orchestrator = MarketOrchestrator(
            market_id, duration, default_price, default_spread, 
            punishing_constant, params
        )
        
        # State management
        self.active = False
        self.start_time: Optional[datetime] = None
        self.creation_time = datetime.now(timezone.utc)
        self.initialization_complete = False
        self.trading_started = False
        self.current_price = 0
        self.is_finished = False
        
        # Async components
        self._stop_requested = asyncio.Event()
        self.release_event = asyncio.Event()
        self.process_transactions_task = None
    
    # External interface methods (UNCHANGED - maintain compatibility)
    async def handle_trader_message(self, message: dict) -> dict:
        """Handle messages from traders - main entry point."""
        return await self.orchestrator.handle_trader_message(message)
    
    def register_websocket(self, websocket):
        """Register a WebSocket connection for broadcasting."""
        self.orchestrator.register_websocket(websocket)
    
    def unregister_websocket(self, websocket):
        """Unregister a WebSocket connection."""
        self.orchestrator.unregister_websocket(websocket)
    
    async def send_message_to_traders(self, message: dict, trader_list=None) -> None:
        """Send a message to all traders or a specific list of traders."""
        await self.orchestrator.broadcast_service.send_to_traders(message, trader_list)
    
    # Lifecycle methods
    async def initialize(self) -> None:
        """Initialize the trading platform."""
        self.start_time = datetime.now(timezone.utc)
        self.active = True
        self.orchestrator.active = True
        self.orchestrator.start_time = self.start_time
        
        # Start transaction processor
        self.process_transactions_task = asyncio.create_task(
            self.orchestrator.transaction_manager.process_transactions()
        )
    
    async def clean_up(self) -> None:
        """Clean up resources when shutting down."""
        self._stop_requested.set()
        self.active = False
        self.orchestrator.active = False
        
        # Cancel transaction processor
        if self.process_transactions_task:
            self.process_transactions_task.cancel()
            try:
                await self.process_transactions_task
            except asyncio.CancelledError:
                pass
    
    def set_initialization_complete(self):
        """Set the initialization_complete flag."""
        self.initialization_complete = True
        self.orchestrator.initialization_complete = True
    
    async def start_trading(self):
        """Start the trading market."""
        self.start_time = datetime.now(timezone.utc)
        self.active = True
        self.trading_started = True
        
        # Update orchestrator state
        self.orchestrator.active = True
        self.orchestrator.start_time = self.start_time
        self.orchestrator.trading_started = True
        
        # Broadcast trading started
        message = await self.orchestrator.broadcast_service.create_broadcast_message(
            "TRADING_STARTED",
            {"content": "Market is open"},
            self.start_time,
            self.duration
        )
        await self.orchestrator.broadcast_service.broadcast_to_websockets(message)
        await self.orchestrator.broadcast_service.send_to_traders(message)
    
    async def run(self) -> None:
        """Run the trading market."""
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
                        "remaining_time": remaining_time_seconds,  # Changed from remainingTime to remaining_time for consistency
                        "dayOver": remaining_time_seconds <= 0,
                        "current_time": current_time.isoformat(),
                        "is_trading_started": self.trading_started
                    }
                }
                await self.orchestrator.broadcast_service.broadcast_to_websockets(time_update)
                
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
        self.orchestrator.active = False
        
        await self.close_existing_book()
        
        # Broadcast stop trading
        message = await self.orchestrator.broadcast_service.create_broadcast_message(
            "stop_trading", {}, self.start_time, self.duration
        )
        await self.orchestrator.broadcast_service.broadcast_to_websockets(message)
        await self.orchestrator.broadcast_service.send_to_traders(message)
        
        await self._handle_final_inventory_reports()
        
        # Broadcast closure
        message = await self.orchestrator.broadcast_service.create_broadcast_message(
            "closure", {}, self.start_time, self.duration
        )
        await self.orchestrator.broadcast_service.broadcast_to_websockets(message)
        await self.orchestrator.broadcast_service.send_to_traders(message)
        
        self.is_finished = True
    
    async def close_existing_book(self) -> None:
        """Close the existing order book."""
        active_orders = self.orchestrator.order_book_manager.order_book.active_orders
        
        for order_id, order in active_orders.items():
            platform_order_type = (
                OrderType.ASK.value
                if order["order_type"] == OrderType.BID
                else OrderType.BID
            )
            closure_price = self.orchestrator.pricing_service.calculate_closure_price(
                order["amount"], order["order_type"]
            )
            
            from .data_models import Order, OrderStatus
            platform_order = Order(
                trader_id=self.id,
                order_type=platform_order_type,
                amount=order["amount"],
                price=closure_price,
                status=OrderStatus.BUFFERED.value,
                market_id=self.id,
            )
            
            # Place platform order
            await self.orchestrator.order_service.process_order(platform_order.model_dump())
            
            # Create transaction
            if order["order_type"] == OrderType.BID:
                await self.orchestrator.transaction_service.create_transaction(
                    order, platform_order.model_dump(), closure_price
                )
            else:
                await self.orchestrator.transaction_service.create_transaction(
                    platform_order.model_dump(), order, closure_price
                )
        
        # Broadcast book updated
        message = await self.orchestrator.broadcast_service.create_broadcast_message(
            "BOOK_UPDATED", {"text": "book is updated"}, self.start_time, self.duration
        )
        await self.orchestrator.broadcast_service.broadcast_to_websockets(message)
        await self.orchestrator.broadcast_service.send_to_traders(message)
    
    async def _handle_final_inventory_reports(self) -> None:
        """Handle final inventory reports from all traders."""
        connected_traders = self.orchestrator.trader_service.get_connected_traders()
        
        await asyncio.gather(
            *[
                self.handle_trader_message({
                    "type": "inventory_report",
                    "trader_id": trader_id,
                    "shares": 0,  # Default values for final report
                    "cash": 0
                })
                for trader_id in connected_traders
            ]
        )
    
    # Property methods for compatibility
    @property
    def current_time(self) -> datetime:
        """Get the current time."""
        return datetime.now(timezone.utc)
    
    @property
    def transactions(self) -> List[Dict]:
        """Get a list of transaction dictionaries."""
        return self.orchestrator.transaction_manager.transactions
    
    @property
    def mid_price(self) -> float:
        """Get the mid price."""
        return self.orchestrator.pricing_service.mid_price
    
    @property
    def is_full(self):
        """Check if the trading market is full."""
        connected_traders = self.orchestrator.trader_service.connected_traders
        return len(connected_traders) >= len(self.params.get('predefined_goals', []))
    
    @property
    def transaction_price(self) -> Optional[float]:
        """Get the last transaction price."""
        return self.orchestrator.transaction_manager.transaction_price
    
    @property
    def connected_traders(self) -> Dict[str, Dict]:
        """Get connected traders."""
        return self.orchestrator.trader_service.connected_traders
    
    @property
    def trader_responses(self) -> Dict[str, bool]:
        """Get trader responses."""
        return self.orchestrator.trader_service.trader_responses
    
    def get_closure_price(self, shares: int, order_type: OrderType) -> float:
        """Calculate the closure price for a given order."""
        return self.orchestrator.pricing_service.calculate_closure_price(shares, order_type)
    
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
    
    async def get_order_book_snapshot(self) -> Dict:
        """Get a snapshot of the order book."""
        return self.orchestrator.order_book_manager.get_order_book_snapshot()
    
    def get_transaction_history(self) -> List[Dict]:
        """Get the transaction history."""
        return self.transactions
    
    def get_active_orders_to_broadcast(self) -> List[Dict]:
        """Get a list of active orders to broadcast."""
        return self.orchestrator.order_book_manager.get_active_orders_to_broadcast()
    
    def place_order(self, order_dict: Dict) -> Dict:
        """Place a new order in the order book."""
        return self.orchestrator.order_book_manager.place_order(order_dict)
    
    async def send_broadcast(
        self, message: dict, message_type="BOOK_UPDATED", incoming_message=None
    ) -> None:
        """Send broadcast message."""
        broadcast_message = await self.orchestrator.broadcast_service.create_broadcast_message(
            message_type, message, self.start_time, self.duration, incoming_message
        )
        
        await self.orchestrator.broadcast_service.broadcast_to_websockets(broadcast_message)
        await self.orchestrator.broadcast_service.send_to_traders(broadcast_message)
    
    async def create_transaction(
        self, bid: Dict, ask: Dict, transaction_price: float
    ) -> Tuple[str, str, any]:
        """Create a transaction."""
        result = await self.orchestrator.transaction_service.create_transaction(bid, ask, transaction_price)
        
        # Broadcast transaction details
        await self.orchestrator.broadcast_service.broadcast_to_websockets(result.transaction_details)
        await self.orchestrator.broadcast_service.send_to_traders(result.transaction_details)
        
        return result.ask_trader_id, result.bid_trader_id, result.transaction
    
    async def clear_orders(self) -> Dict:
        """Clear matched orders from the order book."""
        matched_orders = self.orchestrator.order_book_manager.clear_orders()
        res = {"transactions": [], "removed_active_orders": []}
        
        for ask, bid, transaction_price in matched_orders:
            transaction = await self.create_transaction(bid, ask, transaction_price)
            res["transactions"].append(transaction)
            res["removed_active_orders"].extend([ask["id"], bid["id"]])
        
        return res


# For backward compatibility, we can alias the old methods
# These will be removed once all code is migrated
async def _handle_add_order_compat(self, data): return await self.handle_trader_message({**data, "type": "add_order"})
async def _handle_cancel_order_compat(self, data): return await self.handle_trader_message({**data, "type": "cancel_order"})
async def _handle_register_me_compat(self, data): return await self.handle_trader_message({**data, "type": "register_me"})
async def _handle_inventory_report_compat(self, data): return await self.handle_trader_message({**data, "type": "inventory_report"})

TradingPlatform.handle_add_order = _handle_add_order_compat
TradingPlatform.handle_cancel_order = _handle_cancel_order_compat
TradingPlatform.handle_register_me = _handle_register_me_compat
TradingPlatform.handle_inventory_report = _handle_inventory_report_compat 