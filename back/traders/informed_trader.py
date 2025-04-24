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
        # Order multiplier to increase trading volume
        self.order_multiplier = 1
        print(self.params)
        
        # Add random direction handling
        if params.get("informed_random_direction", False):
            # Randomly flip the direction with 50% probability
            if random.random() < 0.5:
                self.params["informed_trade_direction"] = (
                    TradeDirection.SELL 
                    if params["informed_trade_direction"] == TradeDirection.BUY 
                    else TradeDirection.BUY
                )
            
        self.goal = self.initialize_inventory(params)
        self.num_passive_to_keep = int(self.params["informed_share_passive"] * self.goal * self.order_multiplier)
        # Adjust sleep time to account for increased order volume
        self.next_sleep_time = params.get("trading_day_duration", 5) * 60 / (self.goal * self.order_multiplier)
        self.shares_traded = 0
        
        # Initialize outstanding_levels dictionary to track orders at different price levels
        self.outstanding_levels = {}

    @property
    def progress(self) -> float:
        if not self.filled_orders:
            return 0
        filled_amount = sum(order["amount"] for order in self.filled_orders)
        return filled_amount / (self.goal * self.order_multiplier) if self.goal > 0 else 1

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
                level_price = top_bid - (i * self.params["step"])
                if level_price > 0:  # Ensure price is positive
                    levels.append(level_price)
        else:  # OrderType.ASK
            for i in range(self.informed_order_book_levels):
                level_price = top_ask + (i * self.params["step"])
                levels.append(level_price)

        return levels

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
        if hasattr(self, 'outstanding_levels') and self.outstanding_levels:
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

        return await self.place_order(self.order_multiplier, proposed_price, order_side)

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
        sleep_time = max(0.5,(remaining_time - 5) / (goal - number_trades))
        return sleep_time
        
    async def manage_passive_aggresive_orders(self):
        if not self.use_passive_orders:
            return

        trade_direction = self.params["informed_trade_direction"]
        order_side = OrderType.BID if trade_direction == TradeDirection.BUY else OrderType.ASK
        
        # Get order placement levels
        #levels = self.order_placement_levels
        #print('order placement levels:',levels)
        
       
        # step one cancel orders that they are in level>self.informed_order_book_levels
        if order_side == OrderType.BID:
            top_bid_price = self.get_best_price(OrderType.BID)
            for order in self.orders:
                if top_bid_price - order['price'] >self.informed_order_book_levels:
                    order_id = order['id']
                    await self.send_cancel_order_request(order_id)
        else:
            top_ask_price = self.get_best_price(OrderType.ASK)
            for order in self.orders:
                if order['price'] - top_ask_price > self.informed_order_book_levels:
                    order_id = order['id']
                    await self.send_cancel_order_request(order_id)
        
        # calculate how many passive orders i need to send
        self.total_number_passive_orders = sum(order['amount'] for order in self.orders)
        self.number_trades = len(self.filled_orders)
        print('total goal', self.goal)
        print('number of trades', self.number_trades)
        
        if self.total_number_passive_orders < self.num_passive_to_keep:
            remaining_trades = max(self.goal - self.number_trades,0)
            if remaining_trades >= self.num_passive_to_keep:
                num_passive_order_to_send = self.num_passive_to_keep - self.total_number_passive_orders
            else:
                num_passive_order_to_send = max(remaining_trades -  self.total_number_passive_orders,0)
        else:
            num_passive_order_to_send = 0
       

        # if i fulfilled the goal
        # if goal fulfilled cancel all active orders
        # and do not send aggresive order

        flag_send_aggresive = True
        if self.number_trades >= (self.goal * self.order_multiplier):
            num_passive_order_to_send = 0
            flag_send_aggresive = False
            for order in self.orders:
                order_id = order['id']
                await self.send_cancel_order_request(order_id)

        if remaining_trades <= self.total_number_passive_orders:
            flag_send_aggresive = False


        print('num_passive_order_to_send',num_passive_order_to_send)
        # send passive orders at the top self.informed_order_book_levels levels
        if int(num_passive_order_to_send) > 0:
            for jj in range(int(num_passive_order_to_send)):
                if order_side == OrderType.BID:
                    level_to_send = random.randint(1,self.informed_order_book_levels)
                    top_ask_price = self.get_best_price(OrderType.ASK)
                    top_bid_price = self.get_best_price(OrderType.BID)
                    if top_ask_price is not None:
                        price_to_send = top_ask_price - level_to_send * self.params.get('step')
                    else:
                        price_to_send = top_bid_price + self.params.get('step') - level_to_send * self.params.get('step')
                    # Increase order amount by multiplier
                    amount = self.order_multiplier
                    await self.post_new_order(amount, price_to_send, order_side)
                    flag_send_aggresive = False
                else:
                    level_to_send = random.randint(1,self.informed_order_book_levels)
                    top_bid_price = self.get_best_price(OrderType.BID)
                    top_ask_price = self.get_best_price(OrderType.ASK)
                    if top_bid_price is not None:
                        price_to_send = top_bid_price + level_to_send * self.params.get('step')
                    else:
                        price_to_send = top_ask_price - self.params.get('step') + level_to_send * self.params.get('step')

                    # Increase order amount by multiplier
                    amount = self.order_multiplier
                    await self.post_new_order(amount, price_to_send, order_side)
                    flag_send_aggresive = False

        # last send aggresive order if needed
        top_bid_price = self.get_best_price(OrderType.BID)
        top_ask_price = self.get_best_price(OrderType.ASK)
            
        spread = self.calculate_spread(top_bid_price, top_ask_price)

        print('flag_send aggresive',flag_send_aggresive)
        if flag_send_aggresive:
            if order_side == OrderType.BID:
                if spread <= self.informed_edge:
                    price_to_send = top_ask_price
                    # Increase order amount by multiplier
                    amount = self.order_multiplier
                    await self.post_new_order(amount, price_to_send, order_side)
            else:
                if spread <= self.informed_edge:
                    price_to_send = top_bid_price
                    # Increase order amount by multiplier
                    amount = self.order_multiplier
                    await self.post_new_order(amount, price_to_send, order_side)
        
        self.number_trades = len(self.filled_orders)
        if self.number_trades >= (self.goal * self.order_multiplier):
            for order in self.orders:
                order_id = order['id']
                await self.send_cancel_order_request(order_id)



    async def check(self) -> None:
        remaining_time = self.get_remaining_time()
        self.number_trades = len(self.filled_orders)
        
        if remaining_time < 5 or (abs(self.goal * self.order_multiplier - self.number_trades) == 0):
            return

        trade_direction = self.params["informed_trade_direction"]
        order_side = OrderType.BID if trade_direction == TradeDirection.BUY else OrderType.ASK

        top_bid_price = self.get_best_price(OrderType.BID)
        top_ask_price = self.get_best_price(OrderType.ASK)
        
        if top_bid_price is None or top_ask_price is None:
            return
            
        spread = self.calculate_spread(top_bid_price, top_ask_price)

        if self.use_passive_orders:
            # Manage passive orders if enabled
            await self.manage_passive_aggresive_orders()
        else:
            # Original aggressive-only behavior
            if order_side == OrderType.BID:
                if spread <= self.informed_edge:
                    price_to_send = top_ask_price
                    # Increase order amount by multiplier
                    amount = self.order_multiplier
                    await self.post_new_order(amount, price_to_send, order_side)
                else:
                    return
            else:
                if spread <= self.informed_edge:
                    price_to_send = top_bid_price
                    # Increase order amount by multiplier
                    amount = self.order_multiplier
                    await self.post_new_order(amount, price_to_send, order_side)
                else:
                    return
        
        self.number_trades = sum(order['amount'] for order in self.filled_orders)
        # Adjust sleep time calculation to account for increased order volume
        self.next_sleep_time = self.calculate_sleep_time(remaining_time, self.number_trades, self.goal * self.order_multiplier)
        print('next sleep time', self.next_sleep_time)

    async def run(self) -> None:
        while not self._stop_requested.is_set():
            try:
                await self.check()
                await asyncio.sleep(self.next_sleep_time)
            except asyncio.CancelledError:
                print("Run method cancelled, performing cleanup...")
                break
            except Exception as e:
                print(f"An error occurred in InformedTrader run loop: {e}")
                traceback.print_exc()
                break

        await self.cancel_all_outstanding_orders()

    async def handle_TRADING_STARTED(self, data):
        """
        Reset the start_time when trading actually begins.
        """
        await super().handle_TRADING_STARTED(data)
