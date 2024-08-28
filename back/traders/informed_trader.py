import asyncio
from structures import OrderType, TraderType, TradeDirection

from .base_trader import BaseTrader
from .noise_trader import NoiseTrader


class InformedTrader(BaseTrader):
    def __init__(
        self,
        id: str,
        params: dict,
        noise_trader: NoiseTrader
    ):
        super().__init__(trader_type=TraderType.INFORMED, id=id)
        self.default_price = params.get("default_price", 2000)
        self.informed_edge = params.get("informed_edge", 5)
        self.next_sleep_time = params.get("noise_activity_frequency", 1)
        self.noise_trader = noise_trader
        self.params = params
        self.goal = self.initialize_inventory(params)
        self.aggressive_orders_count = 0
        self.total_orders_count = 0
        self.passive_orders = {}
        self.informed_order_book_levels = params.get("informed_order_book_levels", 3)
        self.informed_order_book_depth = params.get("informed_order_book_depth", 10)

    def initialize_inventory(self, params: dict) -> None:
        expected_noise_amount_per_action = (1 + params['max_order_amount']) / 2
        expected_noise_number_of_actions = params["trading_day_duration"] * 60 / params["noise_activity_frequency"]
        expected_noise_volume = expected_noise_amount_per_action * expected_noise_number_of_actions * (1 - params["noise_passive_probability"])
        x = params["informed_trade_intensity"]
        
        expected_informed_volume = int((x / (1 - x)) * expected_noise_volume)

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

    async def act(self) -> None:
        remaining_time = self.get_remaining_time()
        if remaining_time <= 0:
            return

        trade_direction = self.params["informed_trade_direction"]
        order_side = OrderType.BID if trade_direction == TradeDirection.BUY else OrderType.ASK
        
        top_bid = self.get_best_price(OrderType.BID)
        top_ask = self.get_best_price(OrderType.ASK)
        
        if self.should_place_aggressive_order(order_side, top_bid, top_ask):
            order_placed = await self.place_aggressive_order(order_side, top_bid, top_ask)
            self.aggressive_orders_count += 1
            self.total_orders_count += 1
        else:
            self.total_orders_count += 1

        self.next_sleep_time = self.calculate_sleep_time(remaining_time)

        print(f"Informed Trader Goal: {self.goal}, Aggressive Orders: {self.aggressive_orders_count}, Total Orders: {self.total_orders_count}")

        # if trade_direction == TradeDirection.BUY:
        #     sold_amount = self.shares
        #     to_sell_amount = self.goal - self.shares
        # else:  # TradeDirection.SELL
        #     sold_amount = self.goal - self.shares
        #     to_sell_amount = self.shares

    def should_place_aggressive_order(self, order_side: OrderType, top_bid: float, top_ask: float) -> bool:
        if order_side == OrderType.BID:
            proposed_price = top_bid + self.informed_edge
            return proposed_price >= top_ask
        else:  # OrderType.ASK
            proposed_price = top_ask - self.informed_edge
            return top_bid + self.informed_edge >= proposed_price

    async def place_aggressive_order(self, order_side: OrderType, top_bid: float, top_ask: float) -> bool:
        if order_side == OrderType.BID:
            proposed_price = top_bid + self.informed_edge
        else:  # OrderType.ASK
            proposed_price = top_ask - self.informed_edge
        
        await self.post_new_order(1, proposed_price, order_side)
        return True

    def get_best_price(self, order_side: OrderType) -> float:
        if order_side == OrderType.BID:
            bids = self.order_book.get("bids", [])
            return max(bid["x"] for bid in bids) if bids else self.default_price
        elif order_side == OrderType.ASK:
            asks = self.order_book.get("asks", [])
            return min(ask["x"] for ask in asks) if asks else float("inf")

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
