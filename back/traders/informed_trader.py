import asyncio
import random
import traceback
from typing import List, Dict, Union

from core.data_models import OrderType, TraderType, TradeDirection
from .base_trader import BaseTrader


class InformedTrader(BaseTrader):
    def __init__(
        self,
        id: str,
        params: dict,
    ):
        super().__init__(trader_type=TraderType.INFORMED, id=id)
        self.default_price = params.get("default_price", 100)
        self.informed_edge = params.get("informed_edge", 2)
        self.params = params
        self.informed_order_book_levels = params.get("informed_order_book_levels", 3)
        self.informed_order_book_depth = params.get("informed_order_book_depth", 10)
        self.use_passive_orders = params.get("informed_use_passive_orders", False)
        
        # Add random direction handling
        if params.get("informed_random_direction", False):
            # Randomly flip the direction with 50% probability
            if random.random() < 0.5:
                self.params["informed_trade_direction"] = (
                    TradeDirection.SELL 
                    if params["informed_trade_direction"] == TradeDirection.BUY 
                    else TradeDirection.BUY
                )
            print(f'\033[91mInformed trader direction was randomly set to {self.params["informed_trade_direction"]}\033[0m')
            
        self.goal = self.initialize_inventory(params)
        self.next_sleep_time = params.get("trading_day_duration",5) * 60 / self.goal
        self.shares_traded = 0
        print(f'\033[91mInformed trader params are {self.params}\033[0m')

        

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
    def target_progress(self) -> float:
        return self.get_elapsed_time() / (self.params["trading_day_duration"] * 60)

    @property
    def order_placement_levels(self) -> list:
        trade_direction = self.params["informed_trade_direction"]
        order_side = (
            OrderType.BID if trade_direction == TradeDirection.BUY else OrderType.ASK
        )

        top_bid = self.get_best_price(OrderType.BID)
        top_ask = self.get_best_price(OrderType.ASK)
        
        # Return empty list if either price is None
        if top_bid is None or top_ask is None:
            return []

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

    def adjust_urgency(self):
        progress_difference = self.progress - self.target_progress
        
        if progress_difference < -0.05:  # Behind schedule
            self.urgency_factor = min(2.0, self.urgency_factor * 1.1)
        elif progress_difference > 0.05:  # Ahead of schedule
            self.urgency_factor = max(0.5, self.urgency_factor * 0.9)
        else:  # On track
            pass


    def initialize_inventory(self, params: dict) -> int:
        expected_noise_amount_per_action = (1 + params["max_order_amount"]) / 2
        expected_noise_number_of_actions = (
            params["trading_day_duration"] * 60 * params["noise_activity_frequency"]
        )
        expected_noise_volume = (
            expected_noise_amount_per_action
            * expected_noise_number_of_actions
            * (1 - params["noise_passive_probability"])
        )
        x = params["informed_trade_intensity"]

        goal = int((x / (1 - x)) * expected_noise_volume)

        if params["informed_trade_direction"] == TradeDirection.BUY:
            self.shares = 0
            self.cash = goal * params["default_price"] * 2
        else:
            self.shares = goal
            self.cash = 0

        return goal

    async def cancel_all_outstanding_orders(self):
        """Cancel all outstanding orders."""
        for orders in self.outstanding_levels.values():
            await self.cancel_order(orders["order_ids"])

    def get_remaining_time(self) -> float:
        return self.params["trading_day_duration"] * 60 - self.get_elapsed_time()


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
            return max(bid["x"] for bid in bids) if bids else None
        else:  # OrderType.ASK
            asks = self.order_book.get("asks", [])
            return min(ask["x"] for ask in asks) if asks else None

    def calculate_spread(self,top_bid_price, top_ask_price):
        if top_bid_price is None or top_ask_price is None:
            spread = float('Inf')
        else:
            spread = top_ask_price - top_bid_price
            
        return spread

    def calculate_sleep_time(self,remaining_time,number_trades,goal):
        sleep_time = max(1,(remaining_time - 5) / (goal - number_trades))
        return sleep_time
        
    
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

    async def check(self) -> None:
        remaining_time = self.get_remaining_time()
        self.number_trades = len(self.filled_orders)

        if remaining_time < 5 or (abs(self.goal - self.number_trades) == 0):
            return

        trade_direction = self.params["informed_trade_direction"]
        order_side = OrderType.BID if trade_direction == TradeDirection.BUY else OrderType.ASK

        top_bid_price = self.get_best_price(OrderType.BID)
        top_ask_price = self.get_best_price(OrderType.ASK)
        
        spread = self.calculate_spread(top_bid_price, top_ask_price)

        if self.use_passive_orders:
            # Manage passive orders if enabled
            await self.manage_passive_orders()
        else:
            # Original aggressive-only behavior
            if order_side == OrderType.BID:
                if spread <= self.informed_edge:
                    price_to_send = top_ask_price
                    amount = 1
                    await self.post_new_order(amount, price_to_send, order_side)
            else:
                if spread <= self.informed_edge:
                    price_to_send = top_bid_price
                    amount = 1
                    await self.post_new_order(amount, price_to_send, order_side)
        
        self.number_trades = sum(order['amount'] for order in self.filled_orders)
        self.next_sleep_time = self.calculate_sleep_time(remaining_time, self.number_trades, self.goal)

        #print(f'\033[91m total number of trades is {self.number_trades}\033[0m')
        #print(f'\033[91m self shares is {self.shares}\033[0m')
        #print(f'\033[91m self cash is {self.cash}\033[0m')
        

    async def run(self) -> None:
        while not self._stop_requested.is_set():
            try:
                await self.check()
                await asyncio.sleep(self.next_sleep_time)
                # print(f"my {self.id} filled orders and my active orders are {self.filled_orders} and {self.orders}")
            except asyncio.CancelledError:
                print("Run method cancelled, performing cleanup...")
                break
            except Exception as e:
                print(f"An error occurred in InformedTrader run loop: {e}")
                traceback.print_exc()
                break

        await self.cancel_all_outstanding_orders()