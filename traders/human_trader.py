from .base_trader import BaseTrader
from starlette.websockets import WebSocketDisconnect, WebSocketState
from pprint import pprint
import json

from structures import TraderType, OrderType
from main_platform.custom_logger import setup_custom_logger

logger = setup_custom_logger(__name__)


class HumanTrader(BaseTrader):
    websocket = None
    socket_status = False
    inventory = {'shares': 0, 'cash': 1000}  # TODO.PHILIPP. WRite something sensible here. placeholder for now.

    def __init__(self, *args, **kwargs):
        super().__init__(trader_type=TraderType.HUMAN, *args, **kwargs)

    async def post_processing_server_message(self, json_message):
        message_type = json_message.pop('type', None)
        if message_type:
            await self.send_message_to_client(message_type, **json_message)

    async def connect_to_socket(self, websocket):
        self.websocket = websocket
        self.socket_status = True
        await self.register()

    async def send_message_to_client(self, message_type, **kwargs):
        if not self.websocket or self.websocket.client_state != WebSocketState.CONNECTED:
            logger.warning("WebSocket is closed or not set yet. Skipping message send.")
            return

        if not self.socket_status:
            logger.warning("WebSocket is closed. Skipping message send.")
            return  # Skip sending the message or handle accordingly

        trader_orders = self.orders or []
        order_book = self.order_book or {'bids': [], 'asks': []}
        kwargs['trader_orders'] = trader_orders
        try:
            return await self.websocket.send_json(
                {"shares": self.shares,
                 "cash": self.cash,
                 'type': message_type,
                 'inventory': dict(shares=self.shares, cash=self.cash),
                 **kwargs,
                 'order_book': order_book
                 }
            )
        except WebSocketDisconnect:
            self.socket_status = False
            logger.warning("WebSocket is disconnected. Unable to send message.")

        except Exception as e:
            logger.error(f"An error occurred while sending a message: {e}")
            # Handle other potential exceptions

    async def on_message_from_client(self, message):
        """
        process  incoming messages from human client
        """
        try:
            json_message = json.loads(message)

            action_type = json_message.get('type')
            data = json_message.get('data')
            handler = getattr(self, f'handle_{action_type}', None)
            if handler:
                await handler(data)
            else:
                logger.critical(f"Do not recognice the type: {action_type}. Invalid message format: {message}")
        except json.JSONDecodeError:
            logger.critical(f"Error decoding message: {message}")

    async def handle_add_order(self, data):
        order_type = data.get('type')  # TODO: Philipp. This is a string. We need to convert it to an enum.
        # TODO. Philipp. We may rewrite a client so it will send us an enum instead of a string.
        if order_type == 'bid':
            order_type = OrderType.BID
        else:
            order_type = OrderType.ASK

        price = data.get('price')
        amount = data.get('amount',
                          1)  # TODO. Philipp. This is a placeholder. We need to get the amount from the client.
        await self.post_new_order(amount, price, order_type)

    async def handle_cancel_order(self, data):
        order_uuid = data.get('id')
        logger.info(f"Cancel order request received: {data}")

        if order_uuid in [order['id'] for order in self.orders]:
            await self.send_cancel_order_request(order_uuid)
        else:
            # Handle the case where the order UUID does not exist
            logger.warning(f"Order with UUID {order_uuid} not found.")
    async def handle_closure(self, data):
        await self.post_processing_server_message(data)
        await super().handle_closure(data)
