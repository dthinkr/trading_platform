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
        self.spoof_interval = 5   # x seconds between cycles
        self.spoof_duration = 3   # y seconds to keep orders
        self.spoof_side = "both"  # "bid", "ask", or "both"
        self.spoof_levels = 3     # price levels to spoof
        self.spoof_amount = 10    # order size per level
        self.spoof_offset = 1     # steps from best price
        
        self.active_spoof_orders = []

    async def place_spoof_orders(self):
        """place spoofing orders on one or both sides"""
        if not self.order_book:
            return
        
        step = self.params.get("step", 1)
        sides = []
        
        if self.spoof_side == "both":
            sides = ["bid", "ask"]
        else:
            sides = [self.spoof_side]
        
        for side in sides:
            if side == "bid" and self.order_book.get("asks"):
                best_ask = self.order_book["asks"][0]["x"]
                for i in range(self.spoof_levels):
                    price = best_ask - (self.spoof_offset + i) * step
                    if price > 0:
                        order_id = await self.post_new_order(self.spoof_amount, price, OrderType.BID)
                        if order_id:
                            self.active_spoof_orders.append(order_id)
            
            elif side == "ask" and self.order_book.get("bids"):
                best_bid = self.order_book["bids"][0]["x"]
                for i in range(self.spoof_levels):
                    price = best_bid + (self.spoof_offset + i) * step
                    order_id = await self.post_new_order(self.spoof_amount, price, OrderType.ASK)
                    if order_id:
                        self.active_spoof_orders.append(order_id)

    async def cancel_spoof_orders(self):
        """cancel all active spoofing orders"""
        for order_id in self.active_spoof_orders:
            await self.send_cancel_order_request(order_id)
        self.active_spoof_orders = []

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

