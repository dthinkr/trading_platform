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

        # Sleep parameters
        self.sleep_duration = self.params.get("noise_sleep_duration", 0)
        self.sleep_interval = self.params.get("noise_sleep_interval", 60)
        self.last_sleep_time = 0
        self.total_sleep_time = 0
        
        # Internal clock
        self.start_time = datetime.now()
        print(f"[NOISE TRADER {self.id}] Initialized at {self.start_time.strftime('%H:%M:%S.%f')[:-3]}")
        self.market_duration = timedelta(minutes=self.params["trading_day_duration"])
        self.activity_frequency = self.params["noise_activity_frequency"]
        
        # Calculate expected number of sleep periods
        if self.sleep_duration > 0 and self.sleep_interval > 0:
            expected_sleep_count = int(self.market_duration.total_seconds() / self.sleep_interval)
            self.expected_total_sleep_time = expected_sleep_count * self.sleep_duration
        else:
            self.expected_total_sleep_time = 0
            
        self.target_actions = int(
            self.market_duration.total_seconds() * self.activity_frequency
        )

    @property
    def elapsed_time(self) -> float:
        """Returns the elapsed time in seconds since the trader was initialized."""
        if not isinstance(self.start_time, datetime):
            print(f"[NOISE TRADER {self.id}] Warning: start_time is not a datetime object in elapsed_time property")
            self.start_time = datetime.now()
        return (datetime.now() - self.start_time).total_seconds() - self.total_sleep_time

    @property
    def remaining_time(self) -> float:
        """Returns the remaining time in seconds until the end of the market."""
        # Add expected remaining sleep time to the calculation
        remaining_base_time = max(0, self.market_duration.total_seconds() - self.elapsed_time)
        
        # Calculate expected remaining sleep periods
        if self.sleep_duration > 0 and self.sleep_interval > 0:
            elapsed_with_sleep = self.elapsed_time + self.total_sleep_time
            total_expected_time = self.market_duration.total_seconds() + self.expected_total_sleep_time
            remaining_expected_time = max(0, total_expected_time - elapsed_with_sleep)
            return remaining_expected_time
        return remaining_base_time

    @property
    def expected_actions(self) -> int:
        """Returns the expected number of actions based on elapsed time and activity frequency."""
        return int(self.elapsed_time * self.activity_frequency)

    def calculate_cooling_interval(self) -> float:
        # """Dynamically calculate the cooling interval to match expected actions."""
        # action_difference = self.expected_actions - self.action_counter

        # if action_difference > 0:
        #     # We're behind, need to catch up
        #     return 0.1  # Minimum interval to catch up quickly
        # elif action_difference < 0:
        #     # We're ahead, need to slow down
        #     return 2 / self.activity_frequency  # Wait for 2 expected intervals
        # else:
        #     # We're on track
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
        default_price = self.params["default_price"]

        for _ in range(amt):
            if side == "bids":
                if self.order_book["asks"]:
                    best_ask = self.order_book["asks"][0]["x"]
                    price = best_ask - random.randint(1, order_book_levels) * step
                else:
                    price = default_price - random.randint(1, order_book_levels) * step
            else:
                if self.order_book["bids"]:
                    best_bid = self.order_book["bids"][0]["x"]
                    price = best_bid + random.randint(1, order_book_levels) * step
                else:
                    price = default_price + random.randint(1, order_book_levels) * step

            await self.post_new_order(
                1, price, OrderType.BID if side == "bids" else OrderType.ASK
            )
            self.historical_placed_orders += 1

    async def place_orders_on_empty_side(self, amt: int) -> None:
        order_book_levels = self.params["order_book_levels"]
        step = self.params["step"]
        default_price = self.params["default_price"]

        best_bid = self.order_book["bids"][0]["x"]
        best_ask = self.order_book["asks"][0]["x"]

        for i in range(amt):
            side = random.choice(["bids", "asks"])

            if side == "bids":
                price = best_ask - random.randint(1, order_book_levels) * step
            else:
                price = best_bid + random.randint(1, order_book_levels) * step

            await self.post_new_order(
                1, price, OrderType.BID if side == "bids" else OrderType.ASK
            )
            self.historical_placed_orders += 1

    async def act(self) -> None:
        if not self.order_book:
            return

        amt = random.randint(1, self.params["max_order_amount"])
        print(f"[NOISE TRADER {self.id}] Acting at time {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")

        # Cancel orders
        if random.random() < self.params["noise_cancel_probability"]:
            await self.cancel_orders(amt)
            action = "cancel"
            print(f"[NOISE TRADER {self.id}] Canceling {amt} orders")

        # Handle empty sides
        # if not self.order_book['bids'] or not self.order_book['asks']:
        #     empty_side = "bids" if not self.order_book['bids'] else "asks"
        #     await self.place_passive_orders(amt, empty_side)
        #     return

        pr_passive = self.params["noise_passive_probability"]
        pr_bid = self.params["noise_bid_probability"]
        if not self.order_book['bids']:
            pr_passive = 1
            pr_bid = 1

        if not self.order_book['asks']:
            pr_passive = 1
            pr_bid = 0


        # Place orders
        amt = random.randint(1, self.params["max_order_amount"])
        side = (
            "bids" if random.random() < pr_bid else "asks"
        )
        print(f"[NOISE TRADER {self.id}] Placing {amt} orders on {side} side")

        # Proceed with regular order placement
        if random.random() < pr_passive:
            await self.place_passive_orders(amt, side)
            action = "non_executable"
        else:
            await self.place_aggressive_orders(amt, side)
            action = "executable"

        self.action_counter += 1

    async def run(self) -> None:
        while not self._stop_requested.is_set():
            try:
                # Check if it's time to sleep
                try:
                    # Use raw elapsed time without subtracting sleep time
                    current_time = datetime.now()
                    raw_elapsed = (current_time - self.start_time).total_seconds()
                    print(f"[NOISE TRADER {self.id}] Current time: {current_time.strftime('%H:%M:%S.%f')[:-3]}, start_time: {self.start_time.strftime('%H:%M:%S.%f')[:-3]}, elapsed: {raw_elapsed:.2f}s")
                except TypeError as e:
                    print(f"[NOISE TRADER {self.id}] Error calculating time: {e}. start_time type: {type(self.start_time)}")
                    # Reset start_time and recalculate
                    self.start_time = datetime.now()
                    raw_elapsed = 0
                
                if (self.sleep_duration > 0 and 
                    self.sleep_interval > 0 and 
                    raw_elapsed - self.last_sleep_time >= self.sleep_interval):
                    
                    self.last_sleep_time = raw_elapsed
                    sleep_start_time = datetime.now()
                    
                    print(f"[NOISE TRADER {self.id}] Going to sleep at {sleep_start_time.strftime('%H:%M:%S.%f')[:-3]} for {self.sleep_duration} seconds")
                    
                    # Sleep for the specified duration
                    await asyncio.sleep(self.sleep_duration)
                    
                    # Track actual sleep time
                    actual_sleep_time = (datetime.now() - sleep_start_time).total_seconds()
                    self.total_sleep_time += actual_sleep_time
                    print(f"[NOISE TRADER {self.id}] Waking up at {datetime.now().strftime('%H:%M:%S.%f')[:-3]} after sleeping for {actual_sleep_time:.2f} seconds")
                else:
                    # Normal operation
                    await self.act()
                    cooling_interval = self.calculate_cooling_interval()
                    await asyncio.sleep(cooling_interval)
            except asyncio.CancelledError:
                await self.clean_up()
                raise
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = traceback.extract_tb(exc_tb)[-1][0]
                line_no = traceback.extract_tb(exc_tb)[-1][1]
                traceback.print_exc()
                break
