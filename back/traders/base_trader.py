import asyncio
import json
import uuid
from core.data_models import OrderType, ActionType, TraderType, ThrottleConfig
import os
from abc import abstractmethod
from datetime import datetime

from utils.utils import CustomEncoder

class BaseTrader:
    orders: list = []
    order_book: dict = {}
    active_orders_in_book: list = []
    cash = 0
    shares = 0
    initial_cash = 0
    initial_shares = 0

    def __init__(self, trader_type: TraderType, id, cash=0, shares=0):
        self.initial_shares = shares
        self.initial_cash = cash
        self.cash = cash
        self.shares = shares
        self.initial_cash = cash
        self.initial_shares = shares

        self._stop_requested = asyncio.Event()
        self.trader_type = trader_type.value
        self.id = id
        
        # Direct reference to trading platform (no messaging)
        self.trading_platform = None
        
        # PNL BLOCK
        self.DInv = []
        self.transaction_prices = []
        self.transaction_relevant_mid_prices = []
        self.general_mid_prices = []
        self.sum_cost = 0
        self.sum_dinv = 0
        self.sum_mid_executions = 0
        self.current_pnl = 0

        self.start_time = asyncio.get_event_loop().time()

        self.filled_orders = []
        self.placed_orders = []

        # Basic goal tracking that can be overridden
        self.goal = 0
        self.goal_progress = 0

        # Update throttle tracking to use config from params
        self.last_order_time = 0
        self.orders_in_window = 0
        self.throttle_config = None  # Will be set when params are passed

    def get_elapsed_time(self) -> float:
        current_time = asyncio.get_event_loop().time()
        return current_time - self.start_time

    def calculate_goal_progress(self):
        """Calculate goal progress based on current shares"""
        if hasattr(self, 'goal') and self.goal != 0:
            self.goal_progress = self.shares - self.initial_shares
        return getattr(self, 'goal_progress', 0)

    def get_current_pnl(self) -> float:
        if not self.order_book:
            return 0.0
            
        # Calculate unrealized PnL using mid-market value
        bids = self.order_book.get("bids", [])
        asks = self.order_book.get("asks", [])
        
        if bids and asks:
            best_bid = max(bid["x"] for bid in bids)
            best_ask = min(ask["x"] for ask in asks)
            mid_price = (best_bid + best_ask) / 2
        else:
            mid_price = 100  # Default price if no order book
            
        # Unrealized PnL = change in shares * current mid price + change in cash
        unrealized_pnl = (self.shares - self.initial_shares) * mid_price + (self.cash - self.initial_cash)
        return round(unrealized_pnl, 2)

    def get_vwap(self) -> float:
        if not self.transaction_prices or not self.filled_orders:
            return 0.0
        
        total_value = sum(order["price"] * order["amount"] for order in self.filled_orders if order.get("price") and order.get("amount"))
        total_volume = sum(order["amount"] for order in self.filled_orders if order.get("amount"))
        
        return round(total_value / total_volume, 2) if total_volume > 0 else 0.0

    def update_mid_price(self, mid_price):
        self.general_mid_prices.append(mid_price)

    def update_filled_orders(self, transactions: list):
        for transaction in transactions:
            if transaction.get("trader_id") == self.id:
                self.filled_orders.append(transaction)
                self.transaction_prices.append(transaction["price"])
                self.update_inventory([transaction])

    def update_inventory(self, transactions_relevant_to_self: list) -> None:
        for transaction in transactions_relevant_to_self:
            if transaction["type"] == "bid":
                self.shares += transaction["amount"]
                self.cash -= transaction["price"] * transaction["amount"]
            elif transaction["type"] == "ask":
                self.shares -= transaction["amount"]
                self.cash += transaction["price"] * transaction["amount"]

    async def initialize(self):
        """Initialize the trader."""
        # Set up throttle config if available
        if hasattr(self, 'params') and self.params:
            # Get throttle config for this trader type
            self.throttle_config = self.params.get('throttle_settings', {}).get(self.trader_type, None)
            if self.throttle_config:
                self.throttle_config = ThrottleConfig(**self.throttle_config)
            else:
                self.throttle_config = ThrottleConfig()  # Default no throttling

    async def connect_to_market(self, trading_market_uuid: str):
        """Connect to trading market directly"""
        # This method will be called by the trader manager
        # to set the trading platform reference
        pass

    def set_trading_platform(self, platform):
        """Set direct reference to trading platform"""
        self.trading_platform = platform
        # Register with the platform for direct communication
        platform.register_trader(self.id, self)

    async def register(self):
        """Register with the trading platform"""
        if self.trading_platform:
            await self.trading_platform.handle_register_me(
                trader_id=self.id,
                trader_type=self.trader_type,
                gmail_username=getattr(self, 'gmail_username', None)
            )

    async def clean_up(self):
        """Clean up resources."""
        self._stop_requested.set()

    async def run(self):
        """Main loop for the trader."""
        while not self._stop_requested.is_set():
            try:
                await self.act()
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
            except Exception as e:
                print(f"Error in trader {self.id}: {e}")
                await asyncio.sleep(1)  # Wait longer on error

    @abstractmethod
    async def act(self):
        """The main action that the trader performs."""
        pass

    def is_throttled(self):
        """Check if the trader is throttled based on order frequency"""
        if not self.throttle_config:
            return False

        current_time = datetime.now().timestamp()
        
        # Check time-based throttling
        if current_time - self.last_order_time < self.throttle_config.min_time_between_orders:
            return True
        
        # Check frequency-based throttling
        window_start = current_time - self.throttle_config.time_window
        recent_orders = [order for order in self.placed_orders 
                        if order.get('timestamp', 0) > window_start]
        
        if len(recent_orders) >= self.throttle_config.max_orders_per_window:
            return True
            
        return False

    async def post_new_order(self, amount: int, price: int, order_type: OrderType, **kwargs):
        """Post a new order directly to the trading platform"""
        if not self.trading_platform:
            print(f"Trader {self.id}: No trading platform connected")
            return

        # Check if throttled
        if self.is_throttled():
            print(f"Trader {self.id}: Order throttled")
            return

        # Handle zero-amount orders for record-keeping
        is_record_keeping = amount == 0
        
        order_data = {
            "trader_id": self.id,
            "order_type": order_type.value,
            "amount": amount,
            "price": price,
            "order_id": str(uuid.uuid4()),
            "is_record_keeping": is_record_keeping,
            **kwargs
        }

        # Track placed order
        placed_order = {
            "id": order_data["order_id"],
            "trader_id": self.id,
            "amount": amount,
            "price": price,
            "type": order_type.value,
            "timestamp": datetime.now().timestamp()
        }
        self.placed_orders.append(placed_order)
        
        # Update throttling counters
        self.last_order_time = datetime.now().timestamp()

        try:
            # Call trading platform directly
            result = await self.trading_platform.add_order(order_data, self.id)
            return result
        except Exception as e:
            print(f"Error posting order for trader {self.id}: {e}")
            return None

    async def send_cancel_order_request(self, order_id: str):
        """Cancel an order directly through the trading platform"""
        if not self.trading_platform:
            print(f"Trader {self.id}: No trading platform connected")
            return

        try:
            result = await self.trading_platform.cancel_order(order_id, self.id)
            return result
        except Exception as e:
            print(f"Error cancelling order for trader {self.id}: {e}")
            return None

    # Optional handlers for specific events (can be overridden by subclasses)
    async def handle_TRADING_STARTED(self, data):
        """Handle trading start notification - can be overridden"""
        pass

    async def handle_closure(self, data):
        """Handle market closure - can be overridden"""
        pass

    @abstractmethod
    async def post_processing_server_message(self, json_message):
        """Process server messages - mainly for human traders"""
        pass
