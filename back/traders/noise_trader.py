import asyncio
import random
import numpy as np
from structures import OrderType, TraderType, ActionType
from .base_trader import BaseTrader
import math


class NoiseTrader(BaseTrader):
    def __init__(
        self,
        id: str,
        noise_activity_frequency: float,
        max_order_amount: int,
        settings: dict,
        settings_noise: dict,
    ):
        super().__init__(trader_type=TraderType.NOISE, id=id)
        self.noise_activity_frequency = noise_activity_frequency
        self.max_order_amount = max_order_amount
        self.settings = settings
        self.settings_noise = settings_noise
        self.cash = math.inf
        self.shares = math.inf

        # Historical tracking
        self.historical_cancelled_orders = 0
        self.historical_placed_orders = 0
        self.historical_matched_orders = 0

    def cooling_interval(self, target: float) -> float:
        return np.random.gamma(shape=1, scale=1 / target)

    async def cancel_orders(self, amt):
        if not self.orders:
            return

        orders_to_cancel = random.sample(self.orders, min(amt, len(self.orders)))
        for order in orders_to_cancel:
            await self.send_cancel_order_request(order["id"])
            self.historical_cancelled_orders += 1

    async def place_aggressive_orders(self, amt):
        remaining_amt = amt
        side = random.choice(["bid", "ask"])
        opposite_side = "asks" if side == "bid" else "bids"
        price_levels = sorted(
            self.order_book[opposite_side],
            key=lambda x: x["x"],
            reverse=(side == "bid"),
        )

        for level in price_levels:
            price = level["x"]
            available_volume = level["y"]
            order_volume = min(remaining_amt, available_volume)
            if order_volume > 0:
                await self.post_new_order(
                    order_volume,
                    price,
                    OrderType.BID if side == "bid" else OrderType.ASK,
                )
                self.historical_placed_orders += order_volume
                self.historical_matched_orders += order_volume
                remaining_amt -= order_volume
            if remaining_amt == 0:
                break

    async def place_passive_orders(self, amt):
        levels_n = self.settings_noise["levels_n"]
        step = self.settings_noise["step"]

        best_bid = self.order_book["bids"][0]["x"]
        best_ask = self.order_book["asks"][0]["x"]
        midpoint = (best_bid + best_ask) // 2  # Integer midpoint

        for _ in range(amt):
            side = "bid" if random.random() < self.settings_noise["pr_bid"] else "ask"
            if side == "bid":
                price = midpoint - random.randint(1, levels_n) * step
            else:
                price = midpoint + random.randint(1, levels_n) * step

            await self.post_new_order(
                1, price, OrderType.BID if side == "bid" else OrderType.ASK
            )
            self.historical_placed_orders += 1

    async def place_orders_on_empty_side(self, amt):
        levels_n = self.settings_noise["levels_n"]
        step = self.settings_noise["step"]

        if not self.order_book["bids"]:
            side = "bid"
            base_price = (
                self.order_book["asks"][0]["x"]
                if self.order_book["asks"]
                else self.settings["default_price"]
            )
        elif not self.order_book["asks"]:
            side = "ask"
            base_price = (
                self.order_book["bids"][0]["x"]
                if self.order_book["bids"]
                else self.settings["default_price"]
            )
        else:
            return

        for _ in range(amt):
            if side == "bid":
                price = base_price - random.randint(1, levels_n) * step
            else:
                price = base_price + random.randint(1, levels_n) * step

            await self.post_new_order(
                1, price, OrderType.BID if side == "bid" else OrderType.ASK
            )
            self.historical_placed_orders += 1

    async def act(self) -> None:
        if not self.order_book:
            return

        amt = random.randint(1, self.max_order_amount)

        if not self.order_book["bids"] or not self.order_book["asks"]:
            await self.place_orders_on_empty_side(amt)
            action = "empty_side"

        rand_val = random.random()
        if rand_val < self.settings_noise["pr_cancel"]:
            await self.cancel_orders(amt)
            action = "cancel"

        random_val = random.random()
        if random_val < self.settings_noise["pr_passive"]:
            await self.place_passive_orders(amt)
            action = "non_executable"
        else:
            await self.place_aggressive_orders(amt)
            action = "executable"

        # print(f"NoiseTrader {self.id} - Action: {action}, Amount: {amt}")
        # print(f"Historical Cancelled Orders: {self.historical_cancelled_orders}")
        # print(f"Historical Placed Orders: {self.historical_placed_orders}")
        # print(f"Historical Matched Orders: {self.historical_matched_orders}")
        # print("--------------------")

    async def run(self) -> None:
        while not self._stop_requested.is_set():
            try:
                await self.act()
                await asyncio.sleep(
                    self.cooling_interval(target=self.noise_activity_frequency)
                )
            except asyncio.CancelledError:
                await self.clean_up()
                raise
            except Exception:
                break
