from .base_trader import BaseTrader
from main_platform.utils import convert_to_book_format, convert_to_noise_state, convert_to_trader_actions
import asyncio
import random
from structures import OrderType, TraderType, ORDER_AMOUNT
import numpy as np

from main_platform.custom_logger import setup_custom_logger

logger = setup_custom_logger(__name__)

class NoiseTrader(BaseTrader):

    def __init__(self, activity_frequency: int, settings: dict, settings_noise: dict, 
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
                    logger.info(f"""POSTED {order['order_type']} AT {price} AMOUNT {ORDER_AMOUNT} * {order['amount']}""")
                
                elif order['action_type'] == 'cancel_order' and self.orders:
                    order_type = order['order_type']
                    matching_orders = [o for o in self.orders if o['order_type'] == order['order_type']]
                    if matching_orders:
                        order_id = random.choice(matching_orders)['id']
                        await self.send_cancel_order_request(order_id)
                        logger.info(f"""CANCELLED {order_type} ID {order_id[:10]}""")
        else:
            await self.post_new_order(ORDER_AMOUNT, self.settings['initial_price'], OrderType.ASK)
    
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