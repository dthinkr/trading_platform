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
        self.market_duration_c1 = self.params.get("manipulator_open_time",90)
        self.market_duration_c2 = self.params.get("manipulator_pause_time",20)
        self.market_duration_c3 = self.market_duration  - self.market_duration_c1 - self.market_duration_c2
        self.shares_to_open_input = self.params.get("manipulator_open_shares",20)
        self.shares_to_open = abs(self.shares_to_open_input)
        self.shares_to_close = self.shares_to_open
        self.random_direction_bool = self.params.get("manipulator_random_direction", False)
        self.open_trades = 0

        if self.random_direction_bool: 
            self.initial_direction = 'BID' if np.random.uniform(0,1,1)[0] <= 0.5 else 'ASK'
        else:
            self.initial_direction = 'BID' if self.shares_to_open_input >=0 else 'ASK'

        #print('I am in!!!')

    def count_open_trades(self):
        if self.initial_direction == 'BID':
            open_trades = sum(1 for order in self.filled_orders if order['type'] == 'bid')
        else:
            open_trades = sum(1 for order in self.filled_orders if order['type'] == 'ask')
        
        return open_trades

    async def place_aggressive_orders_cycle1(self):
        
        self.activity_frequency = self.market_duration_c1 / self.shares_to_open

        if self.initial_direction == 'BID':
            if not self.order_book['asks']:
                await asyncio.sleep(0.5)
                return
            else:
                best_ask = self.order_book["asks"][0]["x"]
                await self.post_new_order(1, best_ask, OrderType.BID)
        else:
            if not self.order_book['bids']:
                await asyncio.sleep(0.5)
                return
            else:
                best_bid = self.order_book["bids"][0]["x"]
                await self.post_new_order(1, best_bid, OrderType.ASK)

        #print('Open -- Trades:', len(self.filled_orders))

        await asyncio.sleep(self.activity_frequency)

    async def place_aggressive_orders_cycle3(self):
        
        self.activity_frequency = self.market_duration_c3 / self.open_trades

        if self.initial_direction == 'BID':
            if not self.order_book['bids']:
                await asyncio.sleep(0.5)
                return
            else:
                best_bid = self.order_book["bids"][0]["x"]
                await self.post_new_order(1, best_bid, OrderType.ASK)
        else:
            if not self.order_book['asks']:
                await asyncio.sleep(0.5)
                return
            else:
                best_ask = self.order_book["asks"][0]["x"]
                await self.post_new_order(1, best_ask, OrderType.BID)
        
        #print('Closing -- Trades:', len(self.filled_orders))

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
                #print(raw_elapsed)
                if raw_elapsed <= self.market_duration_c1:
                    await self.place_aggressive_orders_cycle1()
                elif raw_elapsed > self.market_duration_c1 and raw_elapsed <= (self.market_duration_c1 + self.market_duration_c2):
                    remaining = (self.market_duration_c1 + self.market_duration_c2) - raw_elapsed
                    if remaining >0:
                        await asyncio.sleep(remaining)
                else:
                    self.open_trades = self.count_open_trades()
                    if len(self.filled_orders) < 2* self.open_trades:
                        await self.place_aggressive_orders_cycle3()
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

