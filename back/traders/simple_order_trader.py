import asyncio
from core.data_models import OrderType, TraderType
from .base_trader import BaseTrader
from utils import setup_custom_logger
import math

logger = setup_custom_logger(__name__)


class SimpleOrderTrader(BaseTrader):
    # for testing purposes
    def __init__(self, id: str, orders: list):
        super().__init__(TraderType.SIMPLE_ORDER, id=id)
        self.orders_to_place = orders
        self.cash = math.inf
        self.shares = math.inf
        self.all_orders_placed = False

    async def run(self):
        try:
            for order in self.orders_to_place:
                await self.post_new_order(
                    order["amount"], order["price"], order["order_type"]
                )
                print(
                    f"Placing order: price {order['price']}, type {order['order_type']}"
                )
                logger.info(f"Trader {self.id} placed order: {order}")
                await asyncio.sleep(3)

            self.all_orders_placed = True
            logger.info(f"Trader {self.id} has placed all orders")

            # Continue running and printing information
            while not self._stop_requested.is_set():
                print(f"Trader {self.id} status:")
                print(f"Cash: {self.cash}")
                print(f"Shares: {self.shares}")
                print(f"Filled orders: {self.filled_orders}")
                print(f"Placed orders: {self.placed_orders}")
                print("---")
                await asyncio.sleep(10)  # Print status every 10 seconds

        except Exception as e:
            logger.error(f"Error in SimpleOrderTrader {self.id}: {e}")
            print(f"Error in SimpleOrderTrader {self.id}: {e}")

    async def post_processing_server_message(self, json_message):
        pass
