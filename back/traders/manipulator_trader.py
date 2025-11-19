import asyncio
import random
from core.data_models import OrderType, TraderType
from .base_trader import BaseTrader
import numpy as np


class ManipulatorTrader(BaseTrader):
    def __init__(self, id: str, params: dict):
        super().__init__(trader_type=TraderType.MANIPULATOR, id=id)
        self.params = params
        self.cash = float('inf')
        self.shares = float('inf')
        
        self.market_duration = self.params.get("trading_day_duration",3) * 60
        self.step = self.params.get("step", 1)
        self.market_duration_c1 = self.params.get("manipulator_buy_time",90)
        self.market_duration_c2 = self.market_duration  - self.market_duration_c1
        self.shares_to_buy = self.params.get("manipulator_buy_shares",20)
        self.shares_to_sell = self.shares_to_buy
        #print('I am in!!!')

    async def place_aggressive_orders_cycle1(self):
        
        self.activity_frequency = self.market_duration_c1 / self.shares_to_buy

        best_ask = self.order_book["asks"][0]["x"]
        await self.post_new_order(1, best_ask, OrderType.BID)
        #print('Buy -- Trades:', len(self.filled_orders))

        await asyncio.sleep(self.activity_frequency)

    async def place_aggressive_orders_cycle2(self):
        
        self.activity_frequency = self.market_duration_c2 / self.shares_to_buy

        best_bid = self.order_book["bids"][0]["x"]
        await self.post_new_order(1, best_bid, OrderType.ASK)
        #print('Sell -- Trades:', len(self.filled_orders))

        await asyncio.sleep(self.activity_frequency)

    async def cancel_all_orders(self):
        """cancel all active spoofing orders"""
        if not self.orders:
            return
        
        for order in self.orders:
            order_id = order['id']
            await self.send_cancel_order_request(order_id)

    async def run(self):
        while not self._stop_requested.is_set():
            try:
                current_time = asyncio.get_event_loop().time()
                raw_elapsed = current_time - self.start_time
                print(raw_elapsed)
                if raw_elapsed <= self.market_duration_c1:
                    await self.place_aggressive_orders_cycle1()
                else:
                    if len(self.filled_orders) < 2* self.shares_to_buy:
                        await self.place_aggressive_orders_cycle2()
                    else:
                        break

                
            except asyncio.CancelledError:
                await self.cancel_all_orders()
                raise
            except Exception as e:
                print(f"biinformed trader error: {e}")
                break

    async def post_processing_server_message(self, json_message):
        pass

