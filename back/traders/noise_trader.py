import asyncio
import random
import numpy as np
from core.data_models import OrderType, TraderType, ActionType
from .base_trader import BaseTrader, PausingTrader
import math
import sys
import traceback
from datetime import datetime, timedelta


class NoiseTrader(PausingTrader):
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
        self.market_duration = timedelta(minutes=self.params["trading_day_duration"])
        self.activity_frequency = self.params["noise_activity_frequency"]
        self.target_actions = int(
            self.market_duration.total_seconds() * self.activity_frequency
        )
        self.step = self.params['step']
        self.order_book_levels = self.params["order_book_levels"]
        self.noise_choise_weights_passive = self.params['noise_pr_passive_weights']

        if len(self.noise_choise_weights_passive) < self.order_book_levels:
            min_val = min(self.noise_choise_weights_passive)
            self.noise_choise_weights_passive = self.noise_choise_weights_passive + [min_val] * (self.order_book_levels - len(self.noise_choise_weights_passive))
        
        # ============================================================
        # NEW STATE: smoothed mid reference
        # ============================================================
        self.best_bid_ref = self.params["default_price"] - self.step
        self.best_ask_ref = self.params["default_price"] + self.step
        
        # ============================================================
        # EMA parameters:
        self.noise_alpha = self.params["noise_alpha"]
        self.bias_thresh = self.params["noise_bias_thresh"]
        # ============================================================

        
        
    @property
    def elapsed_time(self) -> float:
        """Returns the elapsed time in seconds since the trader was initialized."""
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def remaining_time(self) -> float:
        """Returns the remaining time in seconds until the end of the market."""
        return max(0, self.market_duration.total_seconds() - self.elapsed_time)

    @property
    def expected_actions(self) -> int:
        """Returns the expected number of actions based on elapsed time and activity frequency."""
        return int(self.elapsed_time * self.activity_frequency)

    def calculate_cooling_interval(self) -> float:
        return 1 / self.activity_frequency 

    async def cancel_orders(self, amt: int) -> None:
        if not self.orders:
            return

        # Get unique prices available
        available_prices = list(set([order['price'] for order in self.orders]))

        prices_to_cancel = random.sample(available_prices, min(amt, len(available_prices)))
        #prices_to_cancel = random.choices(available_prices, weights= available_cancel_probs, k=min(amt, len(available_prices)))
        orders_to_cancel = []
        
        for price in prices_to_cancel:
            # Find all orders at this price level
            orders_at_price = [order for order in self.orders if order['price'] == price]
            
            if orders_at_price:
                # Pick the most recent order at this price level
                most_recent_order = max(orders_at_price, key=lambda order: datetime.strptime(order['timestamp'], '%Y-%m-%d %H:%M:%S.%f'))
                orders_to_cancel.append(most_recent_order)

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
                    #price = best_ask - random.randint(1, order_book_levels) * step // Previous Version
                    price = best_ask - random.choices(range(1,order_book_levels+1), weights=self.noise_choise_weights_passive, k=1)[0] * step
                else:
                    price = default_price - random.randint(1, order_book_levels) * step
            else:
                if self.order_book["bids"]:
                    best_bid = self.order_book["bids"][0]["x"]
                    #price = best_bid + random.randint(1, order_book_levels) * step // Previous Version
                    price = best_bid + random.choices(range(1,order_book_levels+1), weights=self.noise_choise_weights_passive, k=1)[0] * step
                else:
                    price = default_price + random.randint(1, order_book_levels) * step

            await self.post_new_order(
                1, price, OrderType.BID if side == "bids" else OrderType.ASK
            )
            self.historical_placed_orders += 1

    

    async def place_orders_on_empty_side(self, amt: int) -> None:
        order_book_levels = self.params["order_book_levels"]
        step = self.params["step"]
        #default_price = self.params["default_price"]

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

        ########new function
    async def place_tightening_passive_orders(self, amt: int, side: str, best_bid: float, best_ask: float) -> None:
        order_book_levels = self.params["order_book_levels"]
        step = self.params["step"]
    
        for _ in range(amt):
    
            if side == "bids":
                # --- tightening bid placement ---
                levels_to_ref = int(np.round((self.best_bid_ref - best_bid) / step))
                levels_to_spread = int((best_ask - step - best_bid) / step)
    
                max_levels_bid = min(levels_to_ref, levels_to_spread)
                max_levels_bid = max(1, max_levels_bid)
    
                level = random.choices(
                    range(1, max_levels_bid + 1),
                    weights=self.noise_choise_weights_passive[:max_levels_bid],
                    k=1
                )[0]
    
                price = best_bid + level * step
    
            else:
                # --- tightening ask placement ---
                levels_to_ref = int(np.round((best_ask - self.best_ask_ref) / step))
                levels_to_spread = int((best_ask - (best_bid + step)) / step)
    
                max_levels_ask = min(levels_to_ref, levels_to_spread)
                max_levels_ask = max(1, max_levels_ask)
    
                level = random.choices(
                    range(1, max_levels_ask + 1),
                    weights=self.noise_choise_weights_passive[:max_levels_ask],
                    k=1
                )[0]
    
                price = best_ask - level * step

            await self.post_new_order(
                1, price, OrderType.BID if side == "bids" else OrderType.ASK
            )
            self.historical_placed_orders += 1
    
    
    async def act(self) -> None:
        if not self.order_book:
            return

        pr_cancel = self.params["noise_cancel_probability"]
        max_order_amount = self.params["max_order_amount"]
        step = self.params['step']
        amt = random.randint(1, self.params["max_order_amount"])

        # Cancel orders
        if random.random() < pr_cancel:
            await self.cancel_orders(amt)

        pr_passive = self.params["noise_passive_probability"]
        pr_aggresive = 1 - pr_passive 
        pr_bid = self.params["noise_bid_probability"]

        bids = self.order_book["bids"]
        asks = self.order_book["asks"]

        alpha = self.noise_alpha
        bias_ticks = self.bias_thresh

        if not bids:
            pr_passive = 1
            pr_aggresive = 1 - pr_passive
            pr_bid = 1
        
        if not asks:
            pr_passive  = 1
            pr_aggresive = 1 - pr_passive
            pr_bid = 0


        # ------------------------------------------------------------
        # EMA update for best bid/ask refs
        # ------------------------------------------------------------
        if bids:
            best_bid = bids[0]["x"]
            self.best_bid_ref = (1 - alpha) * self.best_bid_ref + alpha * best_bid
        else:
            # since empty, keep the same
            best_bid = self.best_bid_ref - bias_ticks * step
        
        if asks:
            best_ask = asks[0]["x"]
            self.best_ask_ref = (1 - alpha) * self.best_ask_ref + alpha * best_ask
        else:
            # since empty, keep the same
            best_ask = self.best_ask_ref + bias_ticks * step
        
        # ------------------------------------------------------------
        # Spread condition trigger
        # ------------------------------------------------------------         
        spread_ticks = (best_ask - best_bid) / step
        tightening_mode = (spread_ticks >= bias_ticks)
    
        # ------------------------------------------------------------
        # Choose action + side randomly
        # ------------------------------------------------------------  
        side = "bids" if random.random() < pr_bid else "asks"

        if tightening_mode:
        
            if side == "asks":
                delta_price = best_ask - self.best_ask_ref
            else:
                delta_price = self.best_bid_ref - best_bid
        
            delta_ticks = max(1, delta_price / step)
        
            amt = int(round(max_order_amount * delta_ticks))
            await self.place_tightening_passive_orders(amt, side, best_bid, best_ask)
        else:
            # Normal behavior
            action = random.choices(["passive", "aggressive"],weights=[pr_passive, pr_aggresive],k=1)[0]
    
            if action == "passive":
                await self.place_passive_orders(amt, side)
            else:
                await self.place_aggressive_orders(amt, side)
    
        self.action_counter += 1
    

        action = random.choices(['passive','aggressive'], weights = [pr_passive,pr_aggresive],k=1)[0]
        amt = random.randint(1, self.params["max_order_amount"])
        side = ("bids" if random.random() < pr_bid else "asks")
        
        if action == 'passive':
            await self.place_passive_orders(amt,side)
        else:
            await self.place_aggressive_orders(amt,side)

        self.action_counter += 1



    async def run(self) -> None:
        while not self._stop_requested.is_set():
            try:
                # Check for sleep before acting
                await self.maybe_sleep()
                
                await self.act()
                await asyncio.sleep(self.calculate_cooling_interval())
            except asyncio.CancelledError:
                await self.clean_up()
                raise
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = traceback.extract_tb(exc_tb)[-1][0]
                line_no = traceback.extract_tb(exc_tb)[-1][1]
                traceback.print_exc()
                break
