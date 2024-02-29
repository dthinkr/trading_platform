from .base_trader import BaseTrader
from external_traders.noise_trader import get_signal_noise, settings_noise, settings, get_noise_rule_unif
from main_platform.utils import convert_to_book_format, convert_to_noise_state, convert_to_trader_actions
import asyncio
import random
import uuid
from structures import OrderType, TraderType, ORDER_AMOUNT, SIGMOID_PARAMS
import logging
import httpx
import numpy as np
logger = logging.getLogger(__name__)

class NoiseTrader(BaseTrader):

    def __init__(self, activity_frequency: int, starting_price=None, step=None, number_of_steps=None ):
        super().__init__(trader_type=TraderType.NOISE)  # Assuming "NOISE" is a valid TraderType
        # self.id=None
        self.activity_frequency = activity_frequency
        self.starting_price = starting_price
        self.step = step
        self.number_of_steps = number_of_steps
        self.active_orders = []

    async def warm_up(self, starting_price, step, number_of_steps, number_of_warmup_orders):
        # Initialize with warm-up specific parameters
        self.starting_price = starting_price
        self.step = step
        self.number_of_steps = number_of_steps

        for _ in range(number_of_warmup_orders):
            print('WE ARE IN WARM UP', _)
            await self.act()

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
        

    async def observe(self):
        """TODO: can be removed once data types for self.orders and self.order_book are decided
        """
        async with httpx.AsyncClient() as client:
            response = await client.get('http://localhost:8000/active_orders')
            if response.status_code == 200:
                orders_data = response.json()
                if orders_data.get("status") == "success" and "data" in orders_data:
                    self.active_orders = list(orders_data["data"].values())

    async def act(self):
        """
        bridge to external noise trader class
        """
        book_format = convert_to_book_format(self.active_orders)
        noise_state = convert_to_noise_state(self.active_orders) #TODO: change to self.orders
        signal_noise = get_signal_noise(signal_state=None, settings_noise=settings_noise)
        noise_orders = get_noise_rule_unif(book_format, signal_noise, noise_state, settings_noise, settings)
        orders = convert_to_trader_actions(noise_orders)
        """return value of orders:
        [
            {'action_type': 'add_order', 'order_type': 'ask', 'price': 49, 'amount': 2}, 
            {'action_type': 'cancel_order', 'order_type': 'ask', 'price': 53.5}
        ]
        """
        if self.starting_price and self.step and self.number_of_steps:
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
    
    async def run(self):
        while not self._stop_requested.is_set():
            try:
                await self.observe()
                await self.act()
                await asyncio.sleep(self.sigmoid(self.activity_frequency))
            except asyncio.CancelledError:
                logger.info('Run method cancelled, performing cleanup of noise trader...')
                await self.clean_up()
                raise
            except Exception as e:
                logger.error(f"An error occurred in NoiseTrader run loop: {e}")
                break