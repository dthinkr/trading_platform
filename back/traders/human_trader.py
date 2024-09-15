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
        print(f"[HumanTrader {self.id}] Initialized with websocket: {self.websocket}")
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
        print(f"[HumanTrader {self.id}] Starting connect_to_socket")
        try:
            self.websocket = websocket
            print(f"[HumanTrader {self.id}] WebSocket object set: {self.websocket}")
            
            self.socket_status = True
            print(f"[HumanTrader {self.id}] Socket status set to: {self.socket_status}")
            
            if not self.trading_system_exchange:
                print(f"[HumanTrader {self.id}] Trading system exchange not set, connecting to session")
                try:
                    await self.connect_to_session(self.trading_session.id)
                    print(f"[HumanTrader {self.id}] Connected to session successfully")
                except Exception as e:
                    print(f"[HumanTrader {self.id}] Error connecting to session: {str(e)}")
                    traceback.print_exc()
            else:
                print(f"[HumanTrader {self.id}] Trading system exchange already set")
            
            try:
                await self.register()
                print(f"[HumanTrader {self.id}] Trader registered successfully")
            except Exception as e:
                print(f"[HumanTrader {self.id}] Error during registration: {str(e)}")
                traceback.print_exc()
            
            print(f"[HumanTrader {self.id}] connect_to_socket completed")
            print(f"[HumanTrader {self.id}] Final WebSocket state - websocket: {self.websocket}, socket_status: {self.socket_status}")
        except Exception as e:
            print(f"[HumanTrader {self.id}] Unexpected error in connect_to_socket: {str(e)}")
            traceback.print_exc()

    async def send_message_to_client(self, message_type, **kwargs):
        print(f"[HumanTrader {self.id}] Starting send_message_to_client: {message_type}")
        if not self.websocket:
            print(f"[HumanTrader {self.id}] WebSocket is not set")
            return
        if self.websocket.client_state != WebSocketState.CONNECTED:
            print(f"[HumanTrader {self.id}] WebSocket is not in CONNECTED state. Current state: {self.websocket.client_state}")
            return
        if not self.socket_status:
            print(f"[HumanTrader {self.id}] socket_status is False")
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
            print(f"[HumanTrader {self.id}] Attempting to send message: {message}")
            await self.websocket.send_json(message)
            print(f"[HumanTrader {self.id}] Message sent successfully")
        except WebSocketDisconnect:
            print(f"[HumanTrader {self.id}] WebSocketDisconnect occurred while sending message")
            self.socket_status = False
        except Exception as e:
            print(f"[HumanTrader {self.id}] Error while sending message: {str(e)}")
            traceback.print_exc()

    async def on_message_from_client(self, message):
        print(f"[HumanTrader {self.id}] Starting on_message_from_client: {message[:50]}...")
        """
        process  incoming messages from human client
        """
        try:
            json_message = json.loads(message)

            print(f"this is the json message we try to send {json_message}")

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
