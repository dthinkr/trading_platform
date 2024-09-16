from .base_trader import BaseTrader
from starlette.websockets import WebSocketDisconnect, WebSocketState
import random
import json

from core.data_models import TraderType, OrderType
from utils import setup_custom_logger
import traceback

logger = setup_custom_logger(__name__)

class HumanTrader(BaseTrader):

    def __init__(self, id, cash, shares, goal, params, trading_session, *args, **kwargs):
        super().__init__(trader_type=TraderType.HUMAN, id=id, cash=cash, shares=shares, *args, **kwargs)
        self.id = id
        self.params = params
        self.goal = goal
        self.trading_session = trading_session
        self.websocket = None
        self.socket_status = False
        self.inventory = {
            "shares": 0,
            "cash": 1000,
        }

    def get_trader_params_as_dict(self):
        return {
            "id": self.id,
            "type": self.trader_type,
            "initial_cash": self.initial_cash,
            "initial_shares": self.initial_shares,
            "goal": self.goal,
            **self.params
        }

    async def post_processing_server_message(self, json_message):
        message_type = json_message.pop("type", None)
        if message_type:
            await self.send_message_to_client(message_type, **json_message)

    async def connect_to_socket(self, websocket):
        try:
            self.websocket = websocket
            self.socket_status = True
            
            if not self.channel:
                await self.initialize()
            
            if not self.trading_system_exchange:
                await self.connect_to_session(self.trading_session.id)
            
            await self.register()
        except Exception as e:
            traceback.print_exc()

    async def send_message_to_client(self, message_type, **kwargs):
        if not self.websocket:
            return
        if self.websocket.client_state != WebSocketState.CONNECTED:
            return
        if not self.socket_status:
            return

        trader_orders = self.orders or []
        order_book = self.order_book or {"bids": [], "asks": []}
        kwargs["trader_orders"] = trader_orders
        try:
            message = {
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
            await self.websocket.send_json(message)
        except WebSocketDisconnect:
            self.socket_status = False
        except Exception as e:
            traceback.print_exc()

    async def on_message_from_client(self, message):
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
        
        await self.post_new_order(amount, price, order_type)

    async def handle_cancel_order(self, data):
        order_uuid = data.get("id")

        if order_uuid in [order["id"] for order in self.orders]:
            await self.send_cancel_order_request(order_uuid)

    async def handle_closure(self, data):
        await self.post_processing_server_message(data)
        await super().handle_closure(data)
