from .base_trader import BaseTrader
from main_platform.utils import convert_to_book_format, convert_to_noise_state, convert_to_trader_actions
import asyncio
import random
from structures import OrderType, TraderType, ORDER_AMOUNT
import numpy as np

from main_platform.custom_logger import setup_custom_logger

logger = setup_custom_logger(__name__)

class NoiseTrader(BaseTrader):

    def __init__(self, activity_frequency: float, settings: dict, settings_noise: dict,
                 get_signal_noise: callable, get_noise_rule_unif: callable):
        super().__init__(trader_type=TraderType.NOISE)

        self.activity_frequency = activity_frequency
        self.settings = settings
        self.settings_noise = settings_noise
        self.get_signal_noise = get_signal_noise
        self.get_noise_rule_unif = get_noise_rule_unif
        self.current_variance = 5.0

    def cooling_interval(self, target: float, initial_variance: float = 5.0, 
                         decay_rate: float = 0.9) -> float:
        if self.current_variance is None:
            self.current_variance = initial_variance
        interval = random.gauss(target, np.sqrt(self.current_variance))
        self.current_variance *= decay_rate  # Update the current variance
        return interval
    
    async def act(self):
        if not self.active_orders:
            await self.post_new_order(ORDER_AMOUNT, self.settings['initial_price'], OrderType.ASK)
            return

        book_format = convert_to_book_format(self.active_orders)
        noise_state = convert_to_noise_state(self.orders)
        signal_noise = self.get_signal_noise(signal_state=None, settings_noise=self.settings_noise)
        noise_orders = self.get_noise_rule_unif(book_format, signal_noise, noise_state, self.settings_noise, self.settings)
        orders = convert_to_trader_actions(noise_orders)

        bid_count, ask_count = 0, 0
        for order in self.active_orders:
            if order['order_type'] == 'bid':
                bid_count += 1
            elif order['order_type'] == 'ask':
                ask_count += 1
                
        order_type_override = None
        if bid_count == 0 and ask_count > 0:
            logger.critical("No bids in the market, placing bid to balance.")
            order_type_override = OrderType.BID
        elif ask_count == 0 and bid_count > 0:
            logger.critical("No asks in the market, placing ask to balance.")
            order_type_override = OrderType.ASK

        for order in orders:
            if order_type_override is not None:
                order['order_type'] = 'ask' if order_type_override == OrderType.ASK else 'bid'

            await self.process_order(order)

    async def process_order(self, order, book_format=None):
        if order['order_type'] == 'ask' or order['order_type'] == 'bid':
            order['price'] = self.adjust_order_price(order['order_type'], book_format, order['price'])

        if order['action_type'] == 'add_order':
            order_type = OrderType.ASK if order['order_type'] == 'ask' else OrderType.BID
            amount, price = ORDER_AMOUNT, order['price']
            for _ in range(order['amount']):
                await self.post_new_order(amount, price, order_type)
            logger.info(f"POSTED {order['order_type']} AT {price} AMOUNT {ORDER_AMOUNT} * {order['amount']}")
        elif order['action_type'] == 'cancel_order' and self.orders:
            matching_orders = [o for o in self.orders if o['order_type'] == order['order_type']]
            if matching_orders:
                order_id = random.choice(matching_orders)['id']
                await self.send_cancel_order_request(order_id)
                logger.info(f"CANCELLED {order['order_type']} ID {order_id[:10]}")

    def adjust_order_price(self, order_type, book_format, original_price):
        """ADJUSTS ORDER PRICE BASED ON MARKET CONDITION"""
        if order_type == OrderType.BID:
            highest_bid = max(book_format['bids'], key=lambda x: x['price'], default={'price': original_price})['price']
            new_price = highest_bid + self.settings['price_increment']
        elif order_type == OrderType.ASK:
            lowest_ask = min(book_format['asks'], key=lambda x: x['price'], default={'price': original_price})['price']
            new_price = lowest_ask - self.settings['price_increment']
        else:
            new_price = original_price
        return new_price

    async def warm_up(self, number_of_warmup_orders: int):
        for _ in range(number_of_warmup_orders):
            print(f' WARMING UP {_} ')
            await self.act()

    async def run(self):
        while not self._stop_requested.is_set():
            try:
                await self.act()

                await asyncio.sleep(self.cooling_interval(target=self.activity_frequency))
             
            except asyncio.CancelledError:
                logger.info('Run method cancelled, performing cleanup of noise trader...')
                await self.clean_up()
                raise
            except Exception as e:
                logger.error(f"An error occurred in NoiseTrader run loop: {e}")
                break
