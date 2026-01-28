import math
import random
from core.data_models import OrderType, TraderType
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

    def normalise_weights(self, raw_weights: list, levels:int) -> list:
        if raw_weights is None or len(raw_weights) == 0:
            return [1] * levels

        # Truncate if too many
        weights = raw_weights[:levels]

        # Extend if too few (repeat last value)
        if len(weights) < levels:
            weights += [weights[-1]] * (levels - len(weights))

        return weights

    async def initialize_order_book(self) -> None:
        default_price = self.trader_creation_data["default_price"]
        step = self.trader_creation_data["step"]
        levels = self.trader_creation_data["order_book_levels"]
        orders_per_level = self.trader_creation_data["start_of_book_num_order_per_level"]

        total_orders = levels * orders_per_level
        bid_prices = [default_price - step * i for i in range(1,levels+1)]
        ask_prices = [default_price + step * i for i in range(1,levels+1)]

        # Post bid orders
        for price in bid_prices:
            await self.post_new_order(1.0, price, OrderType.BID)

        # Post ask orders
        for price in ask_prices:
            await self.post_new_order(1.0, price, OrderType.ASK)
        
        remaining = total_orders - levels
        raw_weights = self.trader_creation_data.get("depth_weights")
        weights = self.normalise_weights(raw_weights, levels)

        extra_bid_prices = random.choices(bid_prices, weights=weights, k=remaining)

        for price in extra_bid_prices:
            await self.post_new_order(1.0, price, OrderType.BID)

        extra_ask_prices = random.choices(ask_prices, weights=weights, k=remaining)
        
        for price in extra_ask_prices:
            await self.post_new_order(1.0, price, OrderType.ASK)


    async def run(self) -> None:
        pass

    async def post_processing_server_message(self, json_message) -> None:
        pass
