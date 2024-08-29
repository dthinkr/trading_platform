import asyncio
import random
import traceback
from typing import List, Dict, Union

from structures import OrderType, TraderType, TradeDirection
from .base_trader import BaseTrader


class InformedTrader(BaseTrader):
    def __init__(
        self,
        id: str,
        params: dict,
    ):
        super().__init__(trader_type=TraderType.INFORMED, id=id)
        self.default_price = params.get("default_price", 2000)
        self.informed_edge = params.get("informed_edge", 5)
        self.next_sleep_time = params.get("noise_activity_frequency", 1)
        self.params = params

        self.informed_order_book_levels = params.get("informed_order_book_levels", 3)
        self.informed_order_book_depth = params.get("informed_order_book_depth", 10)

        self.goal = self.initialize_inventory(params)

    @property
    def outstanding_levels(self) -> dict:
        """
        Returns a dictionary of the outstanding orders, sorted by price from low to high.
        """
        outstanding_levels = {}

        for order in self.orders:
            price = order["price"]
            if price not in outstanding_levels:
                outstanding_levels[price] = {"total_amount": 0, "order_ids": []}
            outstanding_levels[price]["total_amount"] += order["amount"]
            outstanding_levels[price]["order_ids"].append(order["id"])

        return dict(sorted(outstanding_levels.items()))

    @property
    def progress(self) -> float:
        if not self.filled_orders:
            return 0
        filled_amount = sum(order["amount"] for order in self.filled_orders)
        return filled_amount / self.goal if self.goal > 0 else 1

    @property
    def order_placement_levels(self) -> list:
        trade_direction = self.params["informed_trade_direction"]
        order_side = (
            OrderType.BID if trade_direction == TradeDirection.BUY else OrderType.ASK
        )

        top_bid = self.get_best_price(OrderType.BID)
        top_ask = self.get_best_price(OrderType.ASK)
        mid_price = int((top_bid + top_ask) / 2)

        levels = []
        if order_side == OrderType.BID:
            for i in range(self.informed_order_book_levels):
                level_price = mid_price - (i * self.params["step"])
                if level_price > 0:  # Ensure price is positive
                    levels.append(level_price)
        else:  # OrderType.ASK
            for i in range(self.informed_order_book_levels):
                level_price = mid_price + (i * self.params["step"])
                levels.append(level_price)

        return levels

    def initialize_inventory(self, params: dict) -> int:
        expected_noise_amount_per_action = (1 + params["max_order_amount"]) / 2
        expected_noise_number_of_actions = (
            params["trading_day_duration"] * 60 / params["noise_activity_frequency"]
        )
        expected_noise_volume = (
            expected_noise_amount_per_action
            * expected_noise_number_of_actions
            * (1 - params["noise_passive_probability"])
        )
        x = params["informed_trade_intensity"]

        goal = int((x / (1 - x)) * expected_noise_volume)

        adjusted_inventory_accounting_for_passive_orders = (
            goal + self.informed_order_book_levels * self.informed_order_book_depth * 10
        )

        if params["informed_trade_direction"] == TradeDirection.BUY:
            self.shares = 0
            self.cash = (
                adjusted_inventory_accounting_for_passive_orders
                * params["default_price"]
            )
        else:
            self.shares = adjusted_inventory_accounting_for_passive_orders
            self.cash = 0

        return goal

    async def cancel_all_outstanding_orders(self):
        """Cancel all outstanding orders."""
        for orders in self.outstanding_levels.values():
            await self.cancel_order(orders["order_ids"])

    def get_remaining_time(self) -> float:
        return self.params["trading_day_duration"] * 60 - self.get_elapsed_time()

    def calculate_sleep_time(self, remaining_time: float) -> float:
        if self.progress >= 1:
            # Goal reached
            asyncio.create_task(self.cancel_all_outstanding_orders())
            return remaining_time

        urgency_factor = self.params["informed_urgency_factor"]
        remaining_amount = self.goal - (self.progress * self.goal)
        estimated_actions = max(1, remaining_amount / self.informed_order_book_depth)
        target_sleep_time = (remaining_time / estimated_actions) / urgency_factor
        randomness = random.uniform(0.8, 1.2)
        sleep_time = target_sleep_time * randomness

        return max(0.1, min(sleep_time, remaining_time))

    def should_place_aggressive_order(
        self, order_side: OrderType, top_bid: float, top_ask: float
    ) -> bool:
        if order_side == OrderType.BID:
            proposed_price = top_bid + self.informed_edge
            return proposed_price >= top_ask
        else:  # OrderType.ASK
            proposed_price = top_ask - self.informed_edge
            return top_bid + self.informed_edge >= proposed_price

    async def place_aggressive_order(
        self, order_side: OrderType, top_bid: float, top_ask: float
    ) -> str:
        if order_side == OrderType.BID:
            proposed_price = top_bid + self.informed_edge
        else:  # OrderType.ASK
            proposed_price = top_ask - self.informed_edge

        return await self.place_order(1, proposed_price, order_side)

    async def place_order(
        self, amount: int, price: float, order_side: OrderType
    ) -> str:
        order_id = await self.post_new_order(amount, price, order_side)
        return order_id

    async def cancel_order(self, order_ids: Union[str, List[str]]) -> None:
        if isinstance(order_ids, str):
            order_ids = [order_ids]

        for order_id in order_ids:
            await self.send_cancel_order_request(order_id)

    def get_best_price(self, order_side: OrderType) -> float:
        if order_side == OrderType.BID:
            bids = self.order_book.get("bids", [])
            return max(bid["x"] for bid in bids) if bids else self.default_price
        else:  # OrderType.ASK
            asks = self.order_book.get("asks", [])
            return min(ask["x"] for ask in asks) if asks else float("inf")

    async def manage_passive_orders(self):
        trade_direction = self.params["informed_trade_direction"]
        order_side = (
            OrderType.BID if trade_direction == TradeDirection.BUY else OrderType.ASK
        )

        # Cancel orders outside the price range
        for price, orders in self.outstanding_levels.items():
            if price not in self.order_placement_levels:
                await self.cancel_order(orders["order_ids"])

        # Place, adjust, or cancel orders on each level
        for level_price in self.order_placement_levels:
            existing_orders = self.outstanding_levels.get(
                level_price, {"total_amount": 0, "order_ids": []}
            )
            existing_amount = existing_orders["total_amount"]

            if existing_amount > self.informed_order_book_depth:
                # Too many orders, cancel excess orders
                excess_amount = int(existing_amount - self.informed_order_book_depth)
                if excess_amount > 0 and existing_orders["order_ids"]:
                    orders_to_cancel = random.sample(
                        existing_orders["order_ids"],
                        k=min(excess_amount, len(existing_orders["order_ids"])),
                    )
                    await self.cancel_order(orders_to_cancel)
            elif existing_amount < self.informed_order_book_depth:
                # Not enough orders, add more
                amount_to_add = int(self.informed_order_book_depth - existing_amount)
                if amount_to_add > 0:
                    await self.place_order(amount_to_add, level_price, order_side)

    async def act(self) -> None:
        remaining_time = self.get_remaining_time()
        if remaining_time <= 0:
            return

        await self.manage_passive_orders()

        trade_direction = self.params["informed_trade_direction"]
        order_side = (
            OrderType.BID if trade_direction == TradeDirection.BUY else OrderType.ASK
        )

        top_bid = self.get_best_price(OrderType.BID)
        top_ask = self.get_best_price(OrderType.ASK)

        if self.should_place_aggressive_order(order_side, top_bid, top_ask):
            await self.place_aggressive_order(order_side, top_bid, top_ask)

        self.next_sleep_time = self.calculate_sleep_time(remaining_time)

        print(
            "outstanding_levels: ",
            {
                level: data["total_amount"]
                for level, data in self.outstanding_levels.items()
            },
        )
        print(f"Desired levels: {self.order_placement_levels}")
        print(f"Next sleep time: {self.next_sleep_time}")
        print(f"Progress: {self.progress}")

    async def run(self) -> None:
        while not self._stop_requested.is_set():
            try:
                await self.act()
                await asyncio.sleep(
                    min(self.next_sleep_time, self.get_remaining_time())
                )
            except asyncio.CancelledError:
                print("Run method cancelled, performing cleanup...")
                break
            except Exception as e:
                print(f"An error occurred in InformedTrader run loop: {e}")
                traceback.print_exc()
                break

        print("InformedTrader has stopped.")
