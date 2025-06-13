from .base_trader import BaseTrader
from starlette.websockets import WebSocketDisconnect, WebSocketState
import random
import json

from core.data_models import TraderType, OrderType
from utils import setup_custom_logger
import traceback

logger = setup_custom_logger(__name__)

class HumanTrader(BaseTrader):

    def __init__(self, id, cash=0, shares=0, goal=0, role=None, trading_market=None, params=None, gmail_username=None):
        super().__init__(TraderType.HUMAN, id, cash, shares)
        self.goal = goal
        self.role = role
        self.trading_market = trading_market
        self.params = params
        self.gmail_username = gmail_username
        self.websocket = None
        self.socket_status = False
        self.goal_progress = 0

    def get_trader_params_as_dict(self):
        return {
            "id": self.id,
            "type": self.trader_type,
            "initial_cash": self.initial_cash,
            "initial_shares": self.initial_shares,
            "goal": self.goal,
            "goal_progress": self.goal_progress,
            **self.params
        }

    async def post_processing_server_message(self, json_message):
        """Send updates to frontend via WebSocket"""
        message_type = json_message.pop("type", None)
        if message_type:
            await self.send_message_to_client(message_type, **json_message)

    async def connect_to_socket(self, websocket):
        try:
            self.websocket = websocket
            self.socket_status = True
            
            if not hasattr(self, 'trading_platform') or not self.trading_platform:
                logger.error(f"HumanTrader {self.id}: No trading platform connected")
                return
                
            # Register websocket with trading platform for updates
            self.trading_platform.register_websocket(websocket)
            
            await self.register()
        except Exception as e:
            logger.error(f"Error connecting human trader {self.id} to socket: {e}")
            traceback.print_exc()

    async def send_message_to_client(self, message_type, **kwargs):
        if not self.websocket:
            return
        if self.websocket.client_state != WebSocketState.CONNECTED:
            return
        if not self.socket_status:
            return

        order_book = self.order_book or {"bids": [], "asks": []}
        kwargs["trader_orders"] = self.orders
        try:
            message = {
                "shares": self.shares,
                "cash": self.cash,
                "pnl": self.get_current_pnl(),
                "type": message_type,
                "inventory": dict(shares=self.shares, cash=self.cash),
                "goal": self.goal,
                "goal_progress": self.goal_progress,
                **kwargs,
                "order_book": order_book,
                "initial_cash": self.initial_cash,
                "initial_shares": self.initial_shares,
                "sum_dinv": self.sum_dinv,
                "vwap": self.get_vwap(),
                "filled_orders": self.filled_orders,
                "placed_orders": self.placed_orders,
            }
            await self.websocket.send_json(message)
        except WebSocketDisconnect:
            self.socket_status = False
            # Unregister from trading platform
            if self.trading_platform:
                self.trading_platform.unregister_websocket(self.websocket)
        except Exception as e:
            logger.error(f"Error sending message to client {self.id}: {e}")
            traceback.print_exc()

    async def on_message_from_client(self, message):
        """Handle messages from frontend WebSocket"""
        try:
            json_message = json.loads(message)
            action_type = json_message.get("type")
            data = json_message.get("data")
            
            if action_type == "add_order":
                await self.handle_add_order(data)
            elif action_type == "cancel_order":
                await self.handle_cancel_order(data)
            else:
                logger.warning(f"Unknown message type: {action_type}")
                
        except json.JSONDecodeError:
            logger.critical(f"Error decoding message: {message}")

    async def handle_add_order(self, data):
        """Handle order placement from frontend"""
        order_type = data.get("type")
        price = data.get("price")
        amount = data.get("amount", 1)
        
        await self.post_new_order(amount, price, order_type)

    async def handle_cancel_order(self, data):
        """Handle order cancellation from frontend"""
        order_uuid = data.get("id")

        if order_uuid in [order["id"] for order in self.orders]:
            await self.send_cancel_order_request(order_uuid)

    async def handle_TRADING_STARTED(self, data):
        """
        Handle the TRADING_STARTED message by placing a zero-amount order.
        This ensures that human traders who don't trade still generate records.
        """
        # Get the current market price
        top_bid = None
        top_ask = None
        
        if self.order_book:
            bids = self.order_book.get("bids", [])
            asks = self.order_book.get("asks", [])
            
            if bids:
                top_bid = max(bid["x"] for bid in bids)
            if asks:
                top_ask = min(ask["x"] for ask in asks)
        
        # Use default price if order book is empty
        price = self.params.get("default_price", 100)
        if top_bid and top_ask:
            price = (top_bid + top_ask) // 2
        elif top_bid:
            price = top_bid
        elif top_ask:
            price = top_ask
            
        # Place a zero-amount order (this will be recorded but won't affect the market)
        # Use BID order type by default
        order_type = OrderType.BID
        await self.post_new_order(0, price, order_type)
        
        # Forward the message to the client
        await self.post_processing_server_message(data)

    async def act(self):
        """Human traders don't need to act automatically - they respond to WebSocket messages"""
        # Human traders are event-driven through WebSocket messages
        # This method is required by BaseTrader but doesn't need to do anything
        pass

    async def clean_up(self):
        """Clean up WebSocket connection"""
        if self.websocket and self.trading_platform:
            self.trading_platform.unregister_websocket(self.websocket)
        await super().clean_up()
