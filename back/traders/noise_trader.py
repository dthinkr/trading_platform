import asyncio
import random
import numpy as np
from core.data_models import OrderType, TraderType, ActionType
from .base_trader import BaseTrader
import math
import sys
import traceback
from datetime import datetime, timedelta


class NoiseTrader(BaseTrader):
    def __init__(self, id: str, params: dict):
        super().__init__(trader_type=TraderType.NOISE, id=id)
        self.params = params
        self.cash = math.inf
        self.shares = math.inf

        # Historical tracking
        self.historical_cancelled_orders = 0
        self.historical_placed_orders = 0
        self.historical_matched_orders = 0
        self.historical_matches_intended = 0
        self.action_counter = 0

        # Internal clock
        self.start_time = datetime.now()
        self.session_duration = timedelta(minutes=self.params["trading_day_duration"])
        self.activity_frequency = self.params["noise_activity_frequency"]
        print(f"My activity frequency: {self.activity_frequency}")
        self.target_actions = int(
            self.session_duration.total_seconds() * self.activity_frequency
        )

    @property
    def elapsed_time(self) -> float:
        """Returns the elapsed time in seconds since the trader was initialized."""
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def remaining_time(self) -> float:
        """Returns the remaining time in seconds until the end of the session."""
        return max(0, self.session_duration.total_seconds() - self.elapsed_time)

    @property
    def expected_actions(self) -> int:
        """Returns the expected number of actions based on elapsed time and activity frequency."""
        return int(self.elapsed_time * self.activity_frequency)

    def calculate_cooling_interval(self) -> float:
        """Dynamically calculate the cooling interval to match expected actions."""
        action_difference = self.expected_actions - self.action_counter

        if action_difference > 0:
            # We're behind, need to catch up
            return 0.1  # Minimum interval to catch up quickly
        elif action_difference < 0:
            # We're ahead, need to slow down
            return 2 / self.activity_frequency  # Wait for 2 expected intervals
        else:
            # We're on track
            return 1 / self.activity_frequency  # Normal interval

    async def cancel_orders(self, amt: int) -> None:
        if not self.orders:
            return

        orders_to_cancel = random.sample(self.orders, min(amt, len(self.orders)))
        for order in orders_to_cancel:
            await self.send_cancel_order_request(order["id"])
            self.historical_cancelled_orders += 1

    async def place_aggressive_orders(self, amt: int, side: str) -> None:
        remaining_amt = amt
        self.historical_matches_intended += amt
        opposite_side = "asks" if side == "bids" else "bids"
        price_levels = sorted(
            self.order_book[opposite_side],
            key=lambda x: x["x"],
            reverse=(side != "bids"),
        )

        for level in price_levels:
            price = level["x"]
            available_volume = level["y"]
            order_volume = min(remaining_amt, available_volume)
            if order_volume > 0:
                await self.post_new_order(
                    order_volume,
                    price,
                    OrderType.BID if side == "bids" else OrderType.ASK,
                )
                self.historical_placed_orders += order_volume
                self.historical_matched_orders += order_volume
                remaining_amt -= order_volume
            if remaining_amt == 0:
                break

    async def place_passive_orders(self, amt: int, side: str) -> None:
        order_book_levels = self.params["order_book_levels"]
        step = self.params["step"]

        best_bid = self.order_book["bids"][0]["x"]
        best_ask = self.order_book["asks"][0]["x"]
        midpoint = (best_bid + best_ask) // 2  # Integer midpoint

        for _ in range(amt):
            side = (
                "bids"
                if random.random() < self.params["noise_bid_probability"]
                else "asks"
            )
            if side == "bids":
                price = best_ask - random.randint(1, order_book_levels) * step
            else:
                price = best_bid + random.randint(1, order_book_levels) * step

            await self.post_new_order(
                1, price, OrderType.BID if side == "bids" else OrderType.ASK
            )
            self.historical_placed_orders += 1

    async def place_orders_on_empty_side(self, amt: int) -> None:
        order_book_levels = self.params["order_book_levels"]
        step = self.params["step"]
        default_price = self.params["default_price"]

        for i in range(amt):
            side = random.choice(["bids", "asks"])

            if side == "bids":
                price = default_price - random.randint(1, order_book_levels) * step
            else:
                price = default_price + random.randint(1, order_book_levels) * step

            await self.post_new_order(
                1, price, OrderType.BID if side == "bids" else OrderType.ASK
            )
            self.historical_placed_orders += 1

    async def act(self) -> None:
        if not self.order_book:
            return

        amt = random.randint(1, self.params["max_order_amount"])

        # Cancel orders
        if random.random() < self.params["noise_cancel_probability"]:
            await self.cancel_orders(amt)
            action = "cancel"

        # Place orders on empty side
        while not self.order_book["bids"] or not self.order_book["asks"]:
            await self.place_orders_on_empty_side(self.params["max_order_amount"])
            action = "empty_side"

        # Place orders
        amt = random.randint(1, self.params["max_order_amount"])
        side = (
            "bids" if random.random() < self.params["noise_bid_probability"] else "asks"
        )

        # Proceed with regular order placement
        if random.random() < self.params["noise_passive_probability"]:
            await self.place_passive_orders(amt, side)
            action = "non_executable"
        else:
            await self.place_aggressive_orders(amt, side)
            action = "executable"

        self.action_counter += 1

        # print(f"Action number: {self.action_counter}")
        # print(f"NoiseTrader {self.id} - Action: {action}, Amount: {amt}")
        # print(f"Historical Cancelled Orders: {self.historical_cancelled_orders}")
        # print(f"Historical Placed Orders: {self.historical_placed_orders}")
        # print(f"Historical Matched Orders: {self.historical_matched_orders}")
        # print(f"Historical Matches Intended: {self.historical_matches_intended}")
        # print(f"Elapsed Time: {self.elapsed_time}")
        # print(f"Remaining Time: {self.remaining_time}")
        # print("--------------------")

    async def run(self) -> None:
        while not self._stop_requested.is_set():
            try:
                await self.act()
                await asyncio.sleep(self.calculate_cooling_interval())
                # print(f"my {self.id} filled orders and my active orders are {self.filled_orders} and {self.orders}")
            except asyncio.CancelledError:
                await self.clean_up()
                raise
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = traceback.extract_tb(exc_tb)[-1][0]
                line_no = traceback.extract_tb(exc_tb)[-1][1]
                print(f"Error in NoiseTrader {self.id}: {e}")
                print(f"File: {fname}, Line: {line_no}")
                print("Traceback:")
                traceback.print_exc()
                break
