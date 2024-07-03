import math
import random
from structures import OrderType, TraderType
from . import BaseTrader


class BookInitializer(BaseTrader):
    def __init__(self, trader_creation_data: dict) -> None:
        super().__init__(TraderType.INITIAL_ORDER_BOOK)
        self.trader_creation_data = trader_creation_data
        self.cash = math.inf
        self.shares = math.inf

    def generate_price(self, is_bid: bool) -> int:
        default_price = self.trader_creation_data["default_price"]
        step = self.trader_creation_data["step"]
        order_book_levels = self.trader_creation_data["order_book_levels"]

        max_price_deviation = step * order_book_levels
        price_deviation = int(random.expovariate(1 / (max_price_deviation / 3)))

        if is_bid:
            price = default_price - price_deviation
        else:
            price = default_price + price_deviation

        price = max(
            default_price - max_price_deviation,
            min(price, default_price + max_price_deviation),
        )
        price = round(price / step) * step

        return price

    def generate_order_type(self, index: int, total_orders: int) -> OrderType:
        if index < total_orders // 2:
            return OrderType.BID
        return OrderType.ASK

    async def initialize_order_book(self) -> None:
        order_book_levels = self.trader_creation_data["order_book_levels"]
        num_orders = order_book_levels * 10

        for i in range(num_orders):
            order_type = self.generate_order_type(i, num_orders)
            price = self.generate_price(order_type == OrderType.BID)
            amount = 1.0
            await self.post_new_order(amount, price, order_type)
        
        print(f"Order book initialization completed. {num_orders} orders placed.")

    async def run(self) -> None:
        pass

    async def post_processing_server_message(self, json_message) -> None:
        pass