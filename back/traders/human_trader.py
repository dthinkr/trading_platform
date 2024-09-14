from .base_trader import BaseTrader
from starlette.websockets import WebSocketDisconnect, WebSocketState
import random
import json

from core.data_models import TraderType, OrderType
from utils import setup_custom_logger

logger = setup_custom_logger(__name__)

class HumanTrader(BaseTrader):
    websocket = None
    socket_status = False
    inventory = {
        "shares": 0,
        "cash": 1000,
    }

    def __init__(self, id, cash, shares, params, *args, **kwargs):
        super().__init__(trader_type=TraderType.HUMAN, id=id, cash=cash, shares=shares, *args, **kwargs)
        self.params = params
        self.goal = random.choice(params.get('goal', [-10, 0, 10]))

    def get_trader_params_as_dict(self):
        return {
            "id": self.id,
            "type": self.trader_type,
            "initial_cash": self.initial_cash,
            "initial_shares": self.initial_shares,
            "goal": self.goal,
            **self.params  # Include all parameters
        }

    async def post_processing_server_message(self, json_message):
        message_type = json_message.pop("type", None)
        if message_type:
            await self.send_message_to_client(message_type, **json_message)

    async def connect_to_socket(self, websocket):
        self.websocket = websocket
        self.socket_status = True
        await self.register()

    async def send_message_to_client(self, message_type, **kwargs):
        if (
            not self.websocket
            or self.websocket.client_state != WebSocketState.CONNECTED
        ):
            logger.warning("WebSocket is closed or not set yet. Skipping message send.")
            return

        if not self.socket_status:
            logger.warning("WebSocket is closed. Skipping message send.")
            return  # Skip sending the message or handle accordingly

        trader_orders = self.orders or []
        order_book = self.order_book or {"bids": [], "asks": []}
        kwargs["trader_orders"] = trader_orders
        try:
            return await self.websocket.send_json(
                {
                    "shares": self.shares,
                    "cash": self.cash,
                    "pnl": self.get_current_pnl(),
                    "type": message_type,
                    "inventory": dict(shares=self.shares, cash=self.cash),
                    **kwargs,
                    "order_book": order_book,
                    "initial_cash": self.initial_cash,
                    "initial_shares": self.initial_shares,
                    "sum_dinv": self.sum_dinv,
                    "vwap": self.get_vwap(),
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

            action_type = json_message.get("type")
            data = json_message.get("data")
            handler = getattr(self, f"handle_{action_type}", None)
            if handler:
                await handler(data)
            else:
                logger.critical(
                    f"Do not recognice the type: {action_type}. Invalid message format: {message}"
                )
        except json.JSONDecodeError:
            logger.critical(f"Error decoding message: {message}")

    async def handle_add_order(self, data):
        order_type = data.get("type")
        price = data.get("price")
        amount = data.get("amount", 1)
        
        logger.info(f"Adding new order: Type: {order_type}, Price: {price}, Amount: {amount}")
        
        await self.post_new_order(amount, price, order_type)
        logger.info(f"Order added successfully: Type: {order_type}, Price: {price}, Amount: {amount}")

    async def handle_cancel_order(self, data):
        order_uuid = data.get("id")
        logger.info(f"Cancel order request received: {data}")

        if order_uuid in [order["id"] for order in self.orders]:
            await self.send_cancel_order_request(order_uuid)
            logger.info(f"Order cancellation request sent for UUID: {order_uuid}")
        else:
            logger.warning(f"Order with UUID {order_uuid} not found. Cancellation failed.")

    async def handle_closure(self, data):
        logger.critical("Human trader is closing")
        await self.post_processing_server_message(data)
        await super().handle_closure(data)
