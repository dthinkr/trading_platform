import asyncio
import aio_pika
import json
import uuid
from structures.structures import OrderType, ActionType, TraderType
import os

from main_platform.custom_logger import setup_custom_logger
from main_platform.utils import (CustomEncoder)

rabbitmq_url = os.getenv('RABBITMQ_URL', 'amqp://localhost')

logger = setup_custom_logger(__name__)


class BaseTrader:
    orders: list = None
    order_book: dict = None
    active_orders: list = None
    cash = 0
    shares = 0

    def __init__(self, trader_type: TraderType, cash=0, shares=0):

        self.initial_shares = shares
        self.initial_cash = cash
        self.cash = cash
        self.shares = shares

        self._stop_requested = asyncio.Event()  # this one we need only for traders which should be kept active in loop. For instance human traders don't need that
        self.trader_type = trader_type.value
        self.id = str(uuid.uuid4())
        logger.info(f"Trader of type {self.trader_type} created with UUID: {self.id}")
        self.connection = None
        self.channel = None
        self.trading_session_uuid = None
        self.trader_queue_name = f'trader_{self.id}'  # unique queue name based on Trader's UUID
        logger.info(f"Trader queue name: {self.trader_queue_name}")
        self.queue_name = None
        self.broadcast_exchange_name = None
        self.trading_system_exchange = None

        # PNL BLOCK
        self.DInv = []
        self.transaction_prices = []
        self.transaction_relevant_mid_prices = []  # Mid prices relevant to each transaction
        self.general_mid_prices = []  # All mid prices from the trading system
        self.sum_cost = 0
        self.sum_dinv = 0
        self.sum_mid_executions = 0
        self.current_pnl = 0

        # END PNL BLOCK

    def update_mid_price(self, new_mid_price):

        self.general_mid_prices.append(new_mid_price)

    def update_data_for_pnl(self, dinv: float, transaction_price: float) -> None:
        relevant_mid_price = self.general_mid_prices[-1] if self.general_mid_prices else transaction_price

        # Update lists
        self.DInv.append(dinv)
        self.transaction_prices.append(transaction_price)
        self.transaction_relevant_mid_prices.append(relevant_mid_price)  # Store relevant mid_price for this transaction

        # Update running totals
        self.sum_cost += dinv * (transaction_price - relevant_mid_price)
        self.sum_dinv += dinv
        self.sum_mid_executions += relevant_mid_price * dinv

        self.current_pnl = relevant_mid_price * self.sum_dinv - self.sum_mid_executions - self.sum_cost

    def get_current_pnl(self, use_latest_general_mid_price=True):

        if use_latest_general_mid_price and self.general_mid_prices:
            latest_mid_price = self.general_mid_prices[-1]
            pnl_adjusted = latest_mid_price * self.sum_dinv - self.sum_mid_executions - self.sum_cost
            return pnl_adjusted
        return self.current_pnl

    @property
    def delta_cash(self):
        return self.cash - self.initial_cash

    async def initialize(self):
        self.connection = await aio_pika.connect_robust(rabbitmq_url)
        self.channel = await self.connection.channel()
        await self.channel.declare_queue(self.trader_queue_name, auto_delete=True)

    async def clean_up(self):
        self._stop_requested.set()
        try:
            # Close the channel and connection
            if self.channel:
                await self.channel.close()
                logger.info(f"Trader {self.id} channel closed")
            if self.connection:
                await self.connection.close()
                logger.info(f"Trader {self.id} connection closed")

        except Exception as e:
            logger.error(f"An error occurred during Trader cleanup: {e}")

    async def connect_to_session(self, trading_session_uuid):
        self.trading_session_uuid = trading_session_uuid
        self.queue_name = f'trading_system_queue_{self.trading_session_uuid}'
        self.trader_queue_name = f'trader_{self.id}'  # unique queue name based on Trader's UUID

        self.broadcast_exchange_name = f'broadcast_{self.trading_session_uuid}'

        # Subscribe to group messages
        broadcast_exchange = await self.channel.declare_exchange(self.broadcast_exchange_name,
                                                                 aio_pika.ExchangeType.FANOUT,
                                                                 auto_delete=True)
        broadcast_queue = await self.channel.declare_queue("", auto_delete=True)
        await broadcast_queue.bind(broadcast_exchange)
        await broadcast_queue.consume(self.on_message_from_system)

        # For individual messages
        self.trading_system_exchange = await self.channel.declare_exchange(self.queue_name,
                                                                           aio_pika.ExchangeType.DIRECT,
                                                                           auto_delete=True)
        trader_queue = await self.channel.declare_queue(
            self.trader_queue_name,
            auto_delete=True
        )  # Declare a unique queue for this Trader
        await trader_queue.bind(self.trading_system_exchange, routing_key=self.trader_queue_name)
        await trader_queue.consume(self.on_message_from_system)

        await self.register()  # Register with the trading system

    async def register(self):
        message = {
            'type': ActionType.REGISTER.value,
            'action': ActionType.REGISTER.value,
            'trader_type': self.trader_type
        }

        await self.send_to_trading_system(message)

    async def send_to_trading_system(self, message):
        # front end design means human traders' own_orders will alaways be empty
        message['trader_id'] = self.id
        await self.trading_system_exchange.publish(
            aio_pika.Message(body=json.dumps(message, cls=CustomEncoder).encode()),
            routing_key=self.queue_name  # Use the dynamic queue_name
        )

    async def on_message_from_system(self, message):
        """Process incoming messages from trading system.
        For BaseTrader it updates order book and inventory if needed.

        """
        try:

            json_message = json.loads(message.body.decode())

            action_type = json_message.get('type')
            data = json_message
            if data.get('mid_price'):
                self.update_mid_price(data['mid_price'])
            if data.get('new_transactions'):
                self.update_inventory(data['new_transactions'])
            if not data:
                logger.error('no data from trading system')
                return
            order_book = data.get('order_book')
            if order_book:
                self.order_book = order_book
            active_orders = data.get('active_orders')
            if active_orders:
                self.active_orders = active_orders
                own_orders = [order for order in active_orders if order['trader_id'] == self.id]
                # lets convert the order list to a dictionary with keys as order ids
                self.orders = own_orders

            handler = getattr(self, f'handle_{action_type}', None)
            if handler:
                await handler(data)
            else:
                logger.error(f"Invalid message format: {message}")
            await self.post_processing_server_message(data)

        except json.JSONDecodeError:
            logger.error(f"Error decoding message: {message}")

    def update_inventory(self, new_transactions):
        """
        new transactions come in format:
         [{'id': 'aa5b7bd0-6bd1-49ab-ab24-fbd46b3d437a', 'price': 1999.0, 'type': 'ask', 'amount': 1.0}, {'id': 'e5712c5d-dc58-4092-b369-b9306f2f0527', 'price': 1999.0, 'type': 'bid', 'amount': 1.0}]

        and we need to update self.shares and self.cash accordingly
        """
        for transaction in new_transactions:

            if transaction['type'] == 'ask':
                self.shares -= transaction['amount']
                d_inv = -transaction['amount']
                self.cash += transaction['price'] * transaction['amount']
            else:
                self.shares += transaction['amount']
                d_inv = transaction['amount']
                self.cash -= transaction['price'] * transaction['amount']
            self.update_data_for_pnl(d_inv, transaction['price'])
        if self.trader_type == TraderType.HUMAN.value:
            logger.info(f"Trader {self.id} updated inventory: shares: {self.shares}, cash: {self.cash}")

    async def post_processing_server_message(self, json_message):
        """for BaseTrader it is not implemented. For human trader we send updated info back to client.
        For other market maker types we need do some reactions on updated market if needed.
        """
        pass

    async def post_new_order(self,
                             amount, price, order_type: OrderType
                             ):
        new_order = {
            "action": ActionType.POST_NEW_ORDER.value,
            "amount": amount,
            "price": price,
            "order_type": order_type.value,
        }
        await self.send_to_trading_system(new_order)
        logger.debug(f"Trader {self.id} posted new {order_type} order: {new_order}")

    async def send_cancel_order_request(self, order_id: uuid.UUID):
        if not order_id:
            logger.error(f"Order ID is not provided")
            return
        if not self.orders:
            logger.error(f"Trader {self.id} has no active orders")
            return
        if order_id not in [order['id'] for order in self.orders]:
            logger.error(f"Trader {self.id} has no order with ID {order_id}")
            return

        cancel_order_request = {
            "action": ActionType.CANCEL_ORDER.value,  # Assuming you have an ActionType Enum
            "trader_id": self.id,
            "order_id": order_id
        }

        await self.send_to_trading_system(cancel_order_request)
        logger.info(f"Trader {self.id} sent cancel order request: {cancel_order_request}")

    async def run(self):
        # Placeholder method for compatibility with the trading system
        logger.info(f"trader {self.id} is waiting")
        pass

    async def handle_closure(self, data):
        """Handle closure messages from the trading system."""
        logger.critical(
            f"Trader {self.id}: type: {self.trader_type}. Closure signal received. Preparing to stop trading activities.")

        self._stop_requested.set()
        await self.clean_up()

    async def handle_stop_trading(self, data):
        """Handle stop trading messages from the trading system."""
        logger.critical(
            f"Trader {self.id}: type: {self.trader_type}. Stop trading signal received. Preparing to stop trading activities.")

        await self.send_to_trading_system({
            "action": 'inventory_report',
            "trader_id": self.id,
            "shares": self.shares,
            "cash": self.cash
        })
        self._stop_requested.set()
