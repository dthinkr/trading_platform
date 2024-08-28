import math
import random
from structures import OrderType, TraderType
from . import BaseTrader

class BookInitializer(BaseTrader):
    def __init__(self, id: str, trader_creation_data: dict) -> None:
        super().__init__(TraderType.INITIAL_ORDER_BOOK, id=id)
        self.trader_creation_data = trader_creation_data
        self.cash = math.inf
        self.shares = math.inf

    def generate_price(self, is_bid: bool, min_price: int, max_price: int) -> int:
        step = self.trader_creation_data["step"]
        price = random.randint(min_price, max_price)
        return round(price / step) * step

    async def initialize_order_book(self) -> None:
        default_price = self.trader_creation_data["default_price"]
        step = self.trader_creation_data["step"]
        order_book_levels = self.trader_creation_data["order_book_levels"]
        orders_per_level = self.trader_creation_data["start_of_book_num_order_per_level"]

        max_price_deviation = step * order_book_levels
        bid_prices = []
        ask_prices = []

        # Generate bid prices
        for _ in range(order_book_levels * orders_per_level):
            bid_price = self.generate_price(True, default_price - max_price_deviation, default_price - step)
            bid_prices.append(bid_price)

        # Generate ask prices
        for _ in range(order_book_levels * orders_per_level):
            ask_price = self.generate_price(False, default_price + step, default_price + max_price_deviation)
            ask_prices.append(ask_price)

        # Sort prices to ensure proper ordering
        bid_prices.sort(reverse=True)
        ask_prices.sort()

        # Post bid orders
        for price in bid_prices:
            await self.post_new_order(1.0, price, OrderType.BID)

        # Post ask orders
        for price in ask_prices:
            await self.post_new_order(1.0, price, OrderType.ASK)

    async def run(self) -> None:
        pass

    async def post_processing_server_message(self, json_message) -> None:
        pass