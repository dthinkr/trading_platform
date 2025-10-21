import asyncio
import random
from core.data_models import OrderType, TraderType
from .base_trader import BaseTrader


class SpoofingTrader(BaseTrader):
    def __init__(self, id: str, params: dict):
        super().__init__(trader_type=TraderType.SPOOFING, id=id)
        self.params = params
        self.cash = float('inf')
        self.shares = float('inf')
        
        # hardcoded spoofing parameters
        self.spoof_interval = 30   # x seconds between cycles
        self.spoof_duration = 10   # y seconds to keep orders
        self.spoof_side = "bid"  # "bid", "ask", or "both"
        self.spoof_imb = 0.5    # imbalance -> to be set 
        
        #self.active_spoof_orders = []


    async def place_spoof_orders(self):
        """place spoofing orders on one or both sides"""
        if not self.order_book:
            return
        
        step = self.params.get("step", 1)
        
        if self.spoof_side == "both":
            side = random.choice(["bid", "ask"])
        else:
            side = self.spoof_side
        
        if side == "bid" and self.order_book.get("bids"):
            best_bid = self.order_book["bids"][0]["x"]
            price = best_bid
            ask_size = self.order_book['asks'][0]['y']
            bid_size = self.order_book['bids'][0]['y']

            bid_size_to_be = int((self.spoof_imb + 1) / (1 - self.spoof_imb) *  ask_size)
            spoof_amount = int(max(0,bid_size_to_be - bid_size))
            if spoof_amount > 0:
                for i in range(spoof_amount):
                    await self.post_new_order(1, price, OrderType.BID)
                        
        if side == "ask" and self.order_book.get("asks"):
            best_ask = self.order_book["asks"][0]["x"]
            price = best_ask
            ask_size = self.order_book['asks'][0]['y']
            bid_size = self.order_book['bids'][0]['y']

            ask_size_to_be = int((self.spoof_imb + 1) / (1 - self.spoof_imb) *  bid_size)
            spoof_amount = int(max(0,ask_size_to_be - ask_size))
            if spoof_amount > 0:
                for i in range(spoof_amount):
                    await self.post_new_order(1, price, OrderType.ASK)    
            

    async def cancel_spoof_orders(self):
        """cancel all active spoofing orders"""
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

                # keep them in book for duration
                await asyncio.sleep(self.spoof_duration)

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

