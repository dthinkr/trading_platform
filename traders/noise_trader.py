from .base_trader import BaseTrader
from main_platform.utils import convert_to_book_format, convert_to_noise_state, convert_to_trader_actions
import asyncio
import random
import uuid
from structures import OrderType, TraderType, ORDER_AMOUNT, SIGMOID_PARAMS
import logging
import numpy as np
import numba

logger = logging.getLogger(__name__)

class NoiseTrader(BaseTrader):

    def __init__(self, activity_frequency: int, settings: dict, settings_noise: dict, 
                 get_signal_noise: callable, get_noise_rule_unif: callable):
        super().__init__(trader_type=TraderType.NOISE)
        self.activity_frequency = activity_frequency
        self.settings = settings
        self.settings_noise = settings_noise
        self.get_signal_noise = get_signal_noise
        self.get_noise_rule_unif = get_noise_rule_unif

    @numba.jit
    def sigmoid(self, delta_t):
        """
        randomness
        """
        p = (-0.1, 0.1, 3)
        mu = random.gauss(0.1, 0.3)
        adjusted_delta_t = delta_t + mu
        l, u, g = p
        sigmoid_value = l + (u - l) / (1 + (u / l) * np.exp(-g * adjusted_delta_t))
        cap = u * 10
        return min(sigmoid_value, cap)

    async def act(self):
        """
        bridge to external noise trader class
        """
        if self.active_orders:
            book_format = convert_to_book_format(self.active_orders)
            noise_state = convert_to_noise_state(self.orders)
            signal_noise = self.get_signal_noise(signal_state=None, settings_noise=self.settings_noise)
            noise_orders = self.get_noise_rule_unif(book_format, signal_noise, noise_state, self.settings_noise, self.settings)
            orders = convert_to_trader_actions(noise_orders)
            """return value of orders:
            [
                {'action_type': 'add_order', 'order_type': 'ask', 'price': 49, 'amount': 2}, 
                {'action_type': 'cancel_order', 'order_type': 'ask', 'price': 53.5}
            ]
            """
            for order in orders:
                if order['action_type'] == 'add_order':
                    order_type = OrderType.ASK if order['order_type'] == 'ask' else OrderType.BID 
                    amount, price = ORDER_AMOUNT, order['price']
                    for i in range(order['amount']):
                        await self.post_new_order(amount, price, order_type)
                    logger.critical(f"""POSTED {order['order_type']} AT {price} AMOUNT {ORDER_AMOUNT} * {order['amount']}""")
                
                elif order['action_type'] == 'cancel_order' and self.orders:
                    order_type = order['order_type']
                    matching_orders = [o for o in self.orders if o['order_type'] == order['order_type']]
                    if matching_orders:
                        order_id = random.choice(matching_orders)['id']
                        await self.send_cancel_order_request(order_id)
                        logger.critical(f"""CANCELLED {order_type} ID {order_id[:10]}""")
        else:
            await self.post_new_order(ORDER_AMOUNT, self.settings['initial_price'], OrderType.ASK)
    async def warm_up(self, number_of_warmup_orders: int):
        for _ in range(number_of_warmup_orders):
            await self.act()

    async def run(self):
        while not self._stop_requested.is_set():
            try:
                await self.act()
                await asyncio.sleep(self.sigmoid(self.activity_frequency))
            except asyncio.CancelledError:
                logger.info('Run method cancelled, performing cleanup of noise trader...')
                await self.clean_up()
                raise
            except Exception as e:
                logger.error(f"An error occurred in NoiseTrader run loop: {e}")
                break