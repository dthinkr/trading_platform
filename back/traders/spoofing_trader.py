import asyncio
import random
from core.data_models import OrderType, TraderType
from .base_trader import BaseTrader
import numpy as np


class SpoofingTrader(BaseTrader):
    def __init__(self, id: str, params: dict):
        super().__init__(trader_type=TraderType.SPOOFING, id=id)
        self.params = params
        self.cash = float('inf')
        self.shares = float('inf')
        
        # hardcoded spoofing parameters
        self.spoof_interval = 30   # x seconds between cycles
        self.spoof_duration = 30   # y seconds to keep orders
        self.spoof_imb = 0.5    # imbalance -> to be set 
        self.spoof_fake_min_order = 15  # minimum order if spoof_imb is already achieved
        self.spoof_real_min_order  = 6
        self.spoof_side = None
        self.step = self.params.get("step", 1)
        self.spoof_book_level = 2
        print(self.params)
        self.human_informed_goal = self.params.get('predefined_goals')[0]        
    
    def get_spoofer_position_in_queue(self, all_active_orders: list, best_price: float, fake_price: float, side: str, trader_id: str) -> int:
        
        prices_to_check = np.arange(min(best_price, fake_price),max(best_price, fake_price) + self.step,self.step).tolist()
        active_orders_at_price = [order for order in all_active_orders if order['price'] in prices_to_check]

        if side == 'bid':
            sorted_active_orders_at_price = sorted(active_orders_at_price, key=lambda x: (-x['price'], x['timestamp']))
        else:
            sorted_active_orders_at_price = sorted(active_orders_at_price, key=lambda x: (x['price'], x['timestamp']))

        positions = [i + 1 for i, order in enumerate(sorted_active_orders_at_price) if order['trader_id'] == trader_id]
        min_position = min(positions) if positions else None
        position_to_return = min_position
        return int(position_to_return) if position_to_return is not None else None
    
    async def place_spoof_orders(self) -> None:
        """place spoofing orders on one or both sides"""
        if not self.order_book:
            return
        
        # Guard against empty order book sides
        if not self.order_book.get("bids") or not self.order_book.get("asks"):
            return
        
        best_bid_size = self.order_book["bids"][0]["y"]
        best_ask_size = self.order_book["asks"][0]["y"]

        if self.human_informed_goal > 0:
            self.spoof_side = "bid"
        elif self.human_informed_goal < 0:
            self.spoof_side = "ask"
        else:
            self.spoof_side = random.choice(['bid','ask'])

        
        if self.spoof_side == "bid" and self.order_book.get("bids"):
            best_bid = self.order_book["bids"][0]["x"]
            best_ask = self.order_book["asks"][0]["x"]
            self.fake_price = best_bid -  (self.spoof_book_level - 1) * self.step
            self.real_price = best_ask

            ask_size = self.order_book['asks'][0]['y']
            bid_size = self.order_book['bids'][0]['y']

            #bid_size_to_be = int((self.spoof_imb + 1) / (1 - self.spoof_imb) *  ask_size)
            #spoof_amount = max(int(max(0,bid_size_to_be - bid_size)), self.spoof_min_order)
            spoof_amount = self.spoof_fake_min_order
            
            # send the real order
            for i in range(self.spoof_real_min_order):
                price = self.real_price + (i // 2) * self.step
                await self.post_new_order(1, price, OrderType.ASK)


            # send the fake orders
            if spoof_amount > 0:
                for _ in range(spoof_amount):
                    await self.post_new_order(1, self.fake_price, OrderType.BID)


        if self.spoof_side == "ask" and self.order_book.get("asks"):
            best_ask = self.order_book["asks"][0]["x"]
            best_bid = self.order_book["bids"][0]["x"]
            self.fake_price = best_ask + (self.spoof_book_level - 1) * self.step
            self.real_price = best_bid

            ask_size = self.order_book['asks'][0]['y']
            bid_size = self.order_book['bids'][0]['y']

            #ask_size_to_be = int((self.spoof_imb + 1) / (1 - self.spoof_imb) *  bid_size)
            #spoof_amount = max(int(max(0,ask_size_to_be - ask_size)), self.spoof_min_order)
            spoof_amount = self.spoof_fake_min_order


            # send the real order
            for i in range(self.spoof_real_min_order):
                price = self.real_price - (i // 2) * self.step
                await self.post_new_order(1, price, OrderType.BID)

            # send the fakes orders
            if spoof_amount > 0:
                for _ in range(spoof_amount):
                    await self.post_new_order(1, self.fake_price, OrderType.ASK)    
            

    def check_real_spoofing_order(self, trader_active_orders: list, side: str) -> bool:
        if side == 'bid':
            active_orders = [order for order in trader_active_orders if order['order_type'] == 1]
        else:
            active_orders = [order for order in trader_active_orders if order['order_type'] == -1]
        
        len_active_orders = len(active_orders)

        if len_active_orders == 0:
            return False
        else:
            return True
            

    async def check_spoofing_activity(self):
        # keep them in book for duration: spoof_duration
        spoofer_time_check = 0.2
        iterations = int(self.spoof_duration / spoofer_time_check)
        for i in range(iterations):
            await asyncio.sleep(spoofer_time_check)
            
            # Guard against empty order book
            if not self.order_book.get("bids") or not self.order_book.get("asks"):
                await self.cancel_spoof_orders()
                break
                
            if self.spoof_side == 'bid':
                best_price = self.order_book["bids"][0]["x"]
                is_active_real_order = self.check_real_spoofing_order(self.orders, 'ask')
            else:
                best_price = self.order_book["asks"][0]["x"]
                is_active_real_order = self.check_real_spoofing_order(self.orders, 'bid')

            position = self.get_spoofer_position_in_queue(self.active_orders_in_book, best_price, self.fake_price, self.spoof_side, self.id)

            if (position is not None and position<2) or not is_active_real_order:
                await self.cancel_spoof_orders()
                elapsed_time = (i + 1) * spoofer_time_check  # how much time has passed
                remaining_time = max(0, int(self.spoof_duration - elapsed_time))
                break
            else:
                remaining_time = 0
                    
        if remaining_time > 0:
            await asyncio.sleep(remaining_time)

    async def cancel_spoof_orders(self):
        """cancel all active spoofing orders"""
        if not self.orders:
            return
        
        for order in self.orders:
            order_id = order['id']
            await self.send_cancel_order_request(order_id)

    async def run(self):
        while not self._stop_requested.is_set():
            try:
                # wait before next spoof cycle
                await asyncio.sleep(self.spoof_interval)

                # place spoof orders
                await self.place_spoof_orders()

                await self.check_spoofing_activity()

                # cancel them
                await self.cancel_spoof_orders()  
                
            except asyncio.CancelledError:
                await self.cancel_spoof_orders()
                raise
            except Exception as e:
                print(f"spoofing trader error: {e}")
                break

    async def post_processing_server_message(self, json_message):
        pass

