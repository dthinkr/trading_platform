import asyncio
import json
import uuid
from core.data_models import OrderType, ActionType, TraderType, ThrottleConfig
import os
from abc import abstractmethod

from utils.utils import CustomEncoder, setup_custom_logger

logger = setup_custom_logger(__name__)

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
        self.trading_market_uuid = None

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

    def get_vwap(self):
        return (
            sum(self.transaction_prices) / len(self.transaction_prices)
            if self.transaction_prices
            else 0
        )

    def update_mid_price(self, new_mid_price):
        self.general_mid_prices.append(new_mid_price)

    def update_data_for_pnl(self, dinv: float, transaction_price: float) -> None:
        relevant_mid_price = (
            self.general_mid_prices[-1]
            if self.general_mid_prices
            else transaction_price
        )

        self.DInv.append(dinv)
        self.transaction_prices.append(transaction_price)
        self.transaction_relevant_mid_prices.append(relevant_mid_price)

        self.sum_cost += dinv * (transaction_price - relevant_mid_price)
        self.sum_dinv += dinv
        self.sum_mid_executions += relevant_mid_price * dinv

        self.current_pnl = (
            relevant_mid_price * self.sum_dinv - self.sum_mid_executions - self.sum_cost
        )

    def get_current_pnl(self, use_latest_general_mid_price=True):
        if use_latest_general_mid_price and self.general_mid_prices:
            latest_mid_price = self.general_mid_prices[-1]
            pnl_adjusted = (
                latest_mid_price * self.sum_dinv
                - self.sum_mid_executions
                - self.sum_cost
            )
            return pnl_adjusted
        return self.current_pnl

    @property
    def delta_cash(self):
        return self.cash - self.initial_cash

    async def initialize(self):
        if hasattr(self, 'params'):
            # Get throttle config for this trader type
            self.throttle_config = self.params.get('throttle_settings', {}).get(self.trader_type, None)
            if self.throttle_config:
                self.throttle_config = ThrottleConfig(**self.throttle_config)
            else:
                self.throttle_config = ThrottleConfig()  # Default no throttling

    async def clean_up(self):
        self._stop_requested.set()
        # No cleanup needed for WebSocket-based implementation

    async def connect_to_market(self, trading_market_uuid, trading_market=None):
        await self.initialize()
        self.trading_market_uuid = trading_market_uuid
        self.trading_market = trading_market
        # For WebSocket implementation, we store the trading market reference
        # The actual connection is handled via WebSocket in human_trader.py

    async def register(self):
        # For WebSocket implementation, registration is handled directly
        # by the trading platform when the trader connects
        pass

    async def send_to_trading_system(self, message):
        # For WebSocket implementation, send directly to trading platform
        message["trader_id"] = self.id
        if hasattr(self, 'trading_market') and self.trading_market:
            # Handle the message directly in the trading platform
            await self.trading_market.handle_trader_message(message)

    def check_if_relevant(self, transactions: list) -> list:
        transactions_relevant_to_self = []
        for transaction in transactions:
            if transaction["trader_id"] == self.id:
                transactions_relevant_to_self.append(transaction)
        return transactions_relevant_to_self

    def update_filled_orders(self, transactions):
        for transaction in transactions:
            if transaction["trader_id"] == self.id:
                filled_order = {
                    "id": transaction["id"],
                    "price": transaction["price"],
                    "amount": transaction["amount"],
                    "type": transaction["type"],
                    "timestamp": transaction.get("timestamp", None),
                }
                self.filled_orders.append(filled_order)

                self.update_inventory([transaction])
                self.update_goal_progress(transaction)  

                self.update_data_for_pnl(
                    transaction["amount"]
                    if transaction["type"] == "bid"
                    else -transaction["amount"],
                    transaction["price"],
                )

    async def on_message_from_system(self, data):
        """Handle messages from the trading platform directly (no RabbitMQ)."""
        try:
            action_type = data.get("type")

            if action_type == "transaction_update":
                transactions = data.get("transactions", [])
                self.update_filled_orders(transactions)

            if data.get("midpoint"):
                self.update_mid_price(data["midpoint"])
            if not data:
                return
            order_book = data.get("order_book")
            if order_book:
                self.order_book = order_book
            active_orders_in_book = data.get("active_orders")
            if active_orders_in_book:
                self.active_orders_in_book = active_orders_in_book
                own_orders = [
                    order for order in active_orders_in_book if order["trader_id"] == self.id
                ]
                self.orders = own_orders

            handler = getattr(self, f"handle_{action_type}", None)
            if handler:
                await handler(data)
            await self.post_processing_server_message(data)

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            pass

    def update_inventory(self, transactions_relevant_to_self: list) -> None:
        for transaction in transactions_relevant_to_self:
            if transaction["type"] == "bid":
                self.shares += transaction["amount"]
                self.cash -= transaction["price"] * transaction["amount"]
            elif transaction["type"] == "ask":
                self.shares -= transaction["amount"]
                self.cash += transaction["price"] * transaction["amount"]

    @abstractmethod
    async def post_processing_server_message(self, json_message):
        pass

    async def post_new_order(
        self, amount: int, price: int, order_type: OrderType
    ) -> str:
        # Only apply throttling if configured
        if self.throttle_config and self.throttle_config.order_throttle_ms > 0:
            current_time = asyncio.get_event_loop().time() * 1000  # Convert to milliseconds
            
            # Check if we're in a new window
            if current_time - self.last_order_time > self.throttle_config.order_throttle_ms:
                self.last_order_time = current_time
                self.orders_in_window = 0
                
            # Check if we've exceeded the order limit in this window
            if self.orders_in_window >= self.throttle_config.max_orders_per_window:
                return None  # Discard the order
                
            # Increment order count for this window
            self.orders_in_window += 1

        # Special handling for zero-amount orders (only for human traders)
        if amount == 0 and self.trader_type == TraderType.HUMAN.value:
            # Create a special zero-amount order for record-keeping purposes
            order_id = f"{self.id}_zero_amount_{len(self.placed_orders)}"
            new_order = {
                "action": ActionType.POST_NEW_ORDER.value,
                "amount": 0,
                "price": price,
                "order_type": order_type,
                "order_id": order_id,
                "is_record_keeping": True,  # Flag to indicate this is for record-keeping only
            }
            
            await self.send_to_trading_system(new_order)
            
            self.placed_orders.append({
                "order_ids": [order_id],
                "amount": 0,
                "price": price,
                "order_type": order_type,
                "timestamp": asyncio.get_event_loop().time(),
                "is_record_keeping": True,
            })
            
            return order_id

        # Original order posting logic
        if self.trader_type != TraderType.NOISE.value:
            if order_type == OrderType.BID:
                if self.cash < price * amount:
                    return None
            elif order_type == OrderType.ASK:
                if self.shares < amount:
                    return None

        placed_order_ids = []
        for i in range(int(amount)):
            order_id = f"{self.id}_{len(self.placed_orders)}_{i}"
            new_order = {
                "action": ActionType.POST_NEW_ORDER.value,
                "amount": 1,
                "price": price,
                "order_type": order_type,
                "order_id": order_id,
            }

            if self.trader_type == TraderType.INFORMED.value:
                new_order["informed_trader_progress"] = f"{self.number_trades} | {self.goal}"

            await self.send_to_trading_system(new_order)
            placed_order_ids.append(order_id)

        self.placed_orders.append(
            {
                "order_ids": placed_order_ids,
                "amount": amount,
                "price": price,
                "order_type": order_type,
                "timestamp": asyncio.get_event_loop().time(),
            }
        )

        return placed_order_ids[-1] if placed_order_ids else None

    async def send_cancel_order_request(self, order_id: uuid.UUID) -> bool:
        if not order_id:
            return False
        if not self.orders:
            return False
        if order_id not in [order["id"] for order in self.orders]:
            return False

        order_to_cancel = next(
            (order for order in self.orders if order["id"] == order_id), None
        )

        if self.trader_type != TraderType.NOISE.value:
            if order_to_cancel["order_type"] == OrderType.BID:
                self.cash += order_to_cancel["price"] * order_to_cancel["amount"]
            elif order_to_cancel["order_type"] == OrderType.ASK:
                self.shares += order_to_cancel["amount"]

        cancel_order_request = {
            "action": ActionType.CANCEL_ORDER.value,
            "trader_id": self.id,
            "order_id": order_id,
            "amount": -order_to_cancel["amount"],
            "price": order_to_cancel["price"],
            "order_type": order_to_cancel["order_type"],
        }

        try:
            await self.send_to_trading_system(cancel_order_request)
            return True
        except Exception:
            return False

    async def run(self):
        pass

    async def handle_closure(self, data):
        self._stop_requested.set()
        await self.clean_up()

    async def handle_stop_trading(self, data):
        await self.send_to_trading_system(
            {
                "action": "inventory_report",
                "trader_id": self.id,
                "shares": self.shares,
                "cash": self.cash,
            }
        )
        self._stop_requested.set()

    def update_goal_progress(self, transaction):
        """Update progress towards the trader's goal"""
        if self.goal == 0:  # No goal to track
            return
            
        amount = transaction.get('amount', 1)
        if transaction['type'] == 'bid':
            self.goal_progress += amount
        elif transaction['type'] == 'ask':
            self.goal_progress -= amount

    async def handle_TRADING_STARTED(self, data):
        """
        Reset the start_time when trading actually begins.
        This ensures that get_elapsed_time() returns the correct time since trading started.
        """
        self.start_time = asyncio.get_event_loop().time()
