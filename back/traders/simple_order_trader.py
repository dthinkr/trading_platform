import asyncio
from structures import OrderType, TraderType
from .base_trader import BaseTrader
from main_platform.custom_logger import setup_custom_logger

logger = setup_custom_logger(__name__)

class SimpleOrderTrader(BaseTrader):
    def __init__(self, id: str, orders: list):
        super().__init__(TraderType.SIMPLE_ORDER, id=id)
        self.orders_to_place = orders

    async def run(self):
        for order in self.orders_to_place:
            await self.post_new_order(order['amount'], order['price'], order['order_type'])
            logger.info(f"Trader {self.id} placed order: {order}")
            await asyncio.sleep(3)  # Wait for 3 seconds before placing the next order

    async def post_processing_server_message(self, json_message):
        pass