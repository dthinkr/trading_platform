import asyncio
from structures import OrderType, TraderType, TradeDirection
from typing import List, Dict, Union

from .base_trader import BaseTrader
from .noise_trader import NoiseTrader

import random


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
        self.orders_placed = set()
        self.orders_filled = set()


    @property
    def outstanding_orders(self) -> dict:
        """
        Returns a dictionary of the outstanding orders,
        Also updates the orders_filled property.
        """
        outstanding_levels = {}
        outstanding_order_ids = set()
        
        for order in self.orders:
            price = order['price']
            if price not in outstanding_levels:
                outstanding_levels[price] = {'total_amount': 0, 'order_ids': []}
            outstanding_levels[price]['total_amount'] += order['amount']
            outstanding_levels[price]['order_ids'].append(order['id'])
            outstanding_order_ids.add(order['id'])
        
        # Update orders_filled
        newly_filled_orders = self.orders_placed - outstanding_order_ids
        self.orders_filled.update(newly_filled_orders)
        self.orders_placed = outstanding_order_ids
        
        return outstanding_levels

    @property
    def order_placement_levels(self) -> list:
        trade_direction = self.params["informed_trade_direction"]
        order_side = OrderType.BID if trade_direction == TradeDirection.BUY else OrderType.ASK
        
        top_bid = self.get_best_price(OrderType.BID)
        top_ask = self.get_best_price(OrderType.ASK)
        mid_price = int((top_bid + top_ask) / 2)
        
        levels = []
        if order_side == OrderType.BID:
            for i in range(self.informed_order_book_levels):
                level_price = mid_price - (i * self.informed_edge)
                if level_price > 0:  # Ensure price is positive
                    levels.append(level_price)
        else:  # OrderType.ASK
            for i in range(self.informed_order_book_levels):
                level_price = mid_price + (i * self.informed_edge)
                levels.append(level_price)
        
        return levels

    def initialize_inventory(self, params: dict) -> None:
        expected_noise_amount_per_action = (1 + params['max_order_amount']) / 2
        expected_noise_number_of_actions = params["trading_day_duration"] * 60 / params["noise_activity_frequency"]
        expected_noise_volume = expected_noise_amount_per_action * expected_noise_number_of_actions * (1 - params["noise_passive_probability"])
        x = params["informed_trade_intensity"]
        
        expected_informed_volume = int((x / (1 - x)) * expected_noise_volume) + self.informed_order_book_levels * self.informed_order_book_depth

        if params["informed_trade_direction"] == TradeDirection.BUY:
            goal = expected_informed_volume * params["default_price"]
            self.shares = 0
            self.cash = goal
            
        else:
            goal = expected_informed_volume
            self.shares = goal
            self.cash = 0
        
        return goal

    def get_remaining_time(self) -> float:
        return self.params["trading_day_duration"] * 60 - self.get_elapsed_time()

    def calculate_sleep_time(self, remaining_time: float) -> float:
        # buying case
        if self.params["informed_trade_direction"] == TradeDirection.BUY:
            if self.shares >= self.goal:
                # target reached
                return remaining_time
            else:
                # calculate time
                shares_needed = self.goal - self.shares
                return (
                    (remaining_time - 5)
                    / max(shares_needed, 1)
                )

        # selling case
        elif self.params["informed_trade_direction"] == TradeDirection.SELL:
            if self.shares == 0:
                # all sold
                return remaining_time
            else:
                # calculate time
                return (
                    remaining_time
                    / max(self.shares, 1)
                )

        # default case
        return remaining_time

    def should_place_aggressive_order(self, order_side: OrderType, top_bid: float, top_ask: float) -> bool:
        if order_side == OrderType.BID:
            proposed_price = top_bid + self.informed_edge
            return proposed_price >= top_ask
        else:  # OrderType.ASK
            proposed_price = top_ask - self.informed_edge
            return top_bid + self.informed_edge >= proposed_price

    async def place_aggressive_order(self, order_side: OrderType, top_bid: float, top_ask: float) -> str:
        if order_side == OrderType.BID:
            proposed_price = top_bid + self.informed_edge
        else:  # OrderType.ASK
            proposed_price = top_ask - self.informed_edge
        
        return await self.place_order(1, proposed_price, order_side)

    async def place_order(self, amount: int, price: float, order_side: OrderType) -> str:
        order_id = await self.post_new_order(amount, price, order_side)
        if order_id:
            self.orders_placed.add(order_id)
        return order_id

    async def cancel_order(self, order_ids: Union[str, List[str]]) -> Dict[str, bool]:
        if isinstance(order_ids, str):
            order_ids = [order_ids]
        
        for order_id in order_ids:
            await self.send_cancel_order_request(order_id)
            self.orders_placed.discard(order_id)


    def get_best_price(self, order_side: OrderType) -> float:
        if order_side == OrderType.BID:
            bids = self.order_book.get("bids", [])
            return max(bid["x"] for bid in bids) if bids else self.default_price
        elif order_side == OrderType.ASK:
            asks = self.order_book.get("asks", [])
            return min(ask["x"] for ask in asks) if asks else float("inf")

    async def manage_passive_orders(self):
        trade_direction = self.params["informed_trade_direction"]
        order_side = OrderType.BID if trade_direction == TradeDirection.BUY else OrderType.ASK

        # Cancel orders outside the price range
        for price, orders in self.outstanding_orders.items():
            if price not in self.order_placement_levels:
                await self.cancel_order(orders['order_ids'])

        # Place, adjust, or cancel orders on each level
        for level_price in self.order_placement_levels:
            existing_orders = self.outstanding_orders.get(level_price, {'total_amount': 0, 'order_ids': []})
            existing_amount = existing_orders['total_amount']

            print(f"Level price: {level_price}, existing amount: {existing_amount}")
            
            if existing_amount > self.informed_order_book_depth:
                # Too many orders, cancel excess orders
                excess_amount = existing_amount - self.informed_order_book_depth
                orders_to_cancel = random.sample(existing_orders['order_ids'], k=excess_amount)
                await self.cancel_order(orders_to_cancel)
            elif existing_amount < self.informed_order_book_depth:
                # Not enough orders, add more
                amount_to_add = self.informed_order_book_depth - existing_amount
                await self.place_order(amount_to_add, level_price, order_side)


    async def act(self) -> None:
        remaining_time = self.get_remaining_time()
        if remaining_time <= 0:
            return

        await self.manage_passive_orders()

        trade_direction = self.params["informed_trade_direction"]
        order_side = OrderType.BID if trade_direction == TradeDirection.BUY else OrderType.ASK
        
        top_bid = self.get_best_price(OrderType.BID)
        top_ask = self.get_best_price(OrderType.ASK)
        
        if self.should_place_aggressive_order(order_side, top_bid, top_ask):
            await self.place_aggressive_order(order_side, top_bid, top_ask)
        

        self.next_sleep_time = self.calculate_sleep_time(remaining_time)

        print(remaining_time)
        print(len(self.orders_filled))
        print(len(self.filled_orders))
        print(self.outstanding_orders.keys())

        # # Updated print statement
        # print(f"Desired levels: {self.order_placement_levels}")
        # print("Current orders:")
        # for level in self.order_placement_levels:
        #     orders = self.outstanding_orders.get(level, {'total_amount': 0, 'order_ids': []})
        #     print(f"  Level {level}: {orders['total_amount']} orders, IDs: {orders['order_ids']}")
        # print(f"Other levels: {[level for level in self.outstanding_orders if level not in self.order_placement_levels]}")

    async def run(self) -> None:
        while not self._stop_requested.is_set():
            try:
                remaining_time = self.get_remaining_time()
                if remaining_time <= 0:
                    break

                await self.act()

                await asyncio.sleep(min(self.next_sleep_time, remaining_time))
            except asyncio.CancelledError:
                print("Run method cancelled, performing cleanup...")
                break
            except Exception as e:
                print(f"An error occurred in InformedTrader run loop: {e}")
                break

        print("InformedTrader has stopped.")
