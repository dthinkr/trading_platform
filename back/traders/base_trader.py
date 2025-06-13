import asyncio
import aio_pika
import json
import uuid
from core.data_models import OrderType, ActionType, TraderType, ThrottleConfig
import os
from abc import abstractmethod

from utils.utils import CustomEncoder

rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://localhost")

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
        self.connection = None
        self.channel = None
        self.trading_market_uuid = None
        self.trader_queue_name = f"trader_{self.id}"
        self.queue_name = None
        self.broadcast_exchange_name = None
        self.trading_system_exchange = None

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
        self.connection = await aio_pika.connect_robust(rabbitmq_url)
        self.channel = await self.connection.channel()
        if hasattr(self, 'params'):
            # Get throttle config for this trader type
            self.throttle_config = self.params.get('throttle_settings', {}).get(self.trader_type, None)
            if self.throttle_config:
                self.throttle_config = ThrottleConfig(**self.throttle_config)
            else:
                self.throttle_config = ThrottleConfig()  # Default no throttling

    async def clean_up(self):
        self._stop_requested.set()
        try:
            if self.channel:
                await self.channel.close()
            if self.connection:
                await self.connection.close()
        except Exception:
            pass

    async def connect_to_market(self, trading_market_uuid):
        print(f"Trader {self.id}: Connecting to market {trading_market_uuid}")
        if not self.channel:
            await self.initialize()

        self.trading_market_uuid = trading_market_uuid
        self.queue_name = f"trading_system_queue_{self.trading_market_uuid}"
        self.trader_queue_name = f"trader_{self.id}"

        self.broadcast_exchange_name = f"broadcast_{self.trading_market_uuid}"
        print(f"Trader {self.id}: Set up queue names - queue: {self.queue_name}, trader_queue: {self.trader_queue_name}")

        broadcast_exchange = await self.channel.declare_exchange(
            self.broadcast_exchange_name, aio_pika.ExchangeType.FANOUT, auto_delete=True
        )
        broadcast_queue = await self.channel.declare_queue("", auto_delete=True)
        await broadcast_queue.bind(broadcast_exchange)
        await broadcast_queue.consume(self.on_message_from_system)

        self.trading_system_exchange = await self.channel.declare_exchange(
            self.queue_name, aio_pika.ExchangeType.DIRECT, auto_delete=True
        )
        trader_queue = await self.channel.declare_queue(
            self.trader_queue_name, auto_delete=True
        )
        await trader_queue.bind(
            self.trading_system_exchange, routing_key=self.trader_queue_name
        )
        await trader_queue.consume(self.on_message_from_system)

    async def register(self):
        if not self.trading_system_exchange:
            await self.connect_to_market(self.trading_market_uuid)

        message = {
            "type": ActionType.REGISTER.value,
            "action": ActionType.REGISTER.value,
            "trader_type": self.trader_type,
        }

        await self.send_to_trading_system(message)


    async def register(self):
        message = {
            "type": ActionType.REGISTER.value,
            "action": ActionType.REGISTER.value,
            "trader_type": self.trader_type,
        }

        await self.send_to_trading_system(message)

    async def send_to_trading_system(self, message):
        message["trader_id"] = self.id
        print(f"Trader {self.id}: Sending message to trading system: {message}")
        if not self.trading_system_exchange:
            print(f"Trader {self.id}: ERROR - trading_system_exchange is None!")
            return
        await self.trading_system_exchange.publish(
            aio_pika.Message(body=json.dumps(message, cls=CustomEncoder).encode()),
            routing_key=self.queue_name,
        )
        print(f"Trader {self.id}: Message sent successfully")

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

    async def on_message_from_system(self, message):
        try:
            json_message = json.loads(message.body.decode())
            action_type = json_message.get("type")
            data = json_message

            if action_type == "transaction_update":
                transactions = data.get("transactions", [])
                self.update_filled_orders(transactions)

            if data.get("midpoint"):
                self.update_mid_price(data["midpoint"])
            if not data:
                return
            order_book = data.get("order_book")
            if order_book:
                print(f"Trader {self.id}: Received order_book update: {order_book}")
                self.order_book = order_book
            else:
                print(f"Trader {self.id}: No order_book in message: {data.keys()}")
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

        except json.JSONDecodeError:
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
