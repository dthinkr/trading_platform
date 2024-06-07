import asyncio
import random
import numpy as np
import random
from structures import OrderType, TraderType, ActionType
from main_platform.utils import (
    convert_to_book_format_new,
    convert_to_noise_state,
    convert_to_trader_actions,
)
from main_platform.custom_logger import setup_custom_logger
from .base_trader import BaseTrader
import numpy as np

logger = setup_custom_logger(__name__)


class NoiseTrader(BaseTrader):
    def __init__(
        self,
        activity_frequency: float,
        order_amount: int,
        settings: dict,
        settings_noise: dict,
        #get_signal_noise: callable,
        #get_noise_rule_unif: callable,
    ):
        """
        initializes the noise trader with settings and callable functions.
        """
        super().__init__(trader_type=TraderType.NOISE)

        self.activity_frequency = activity_frequency
        self.order_amount = order_amount
        self.settings = settings
        self.settings_noise = settings_noise
        self.step = self.settings_noise['step']
        self.initial_value = self.settings['initial']
        #self.get_signal_noise = get_signal_noise
        #self.get_noise_rule_unif = get_noise_rule_unif
        # self.current_variance = 5.0
        

    def cooling_interval(self, target: float) -> float:
        """
        adjusts cooling interval using a random process.
        """
        interval = np.random.exponential(1/target)
        return interval

    def get_noise_order(self,book_format):
        order = {'bid': {}, 'ask': {}}
        levels_n = self.settings_noise['levels_n']
        step = self.settings_noise['step']
        pr_passive = self.settings_noise['pr_passive']
        pr_bid = self.settings_noise['pr_bid']
        pr_cancel = self.settings_noise['pr_cancel']

        pr_passive_signal = np.random.uniform(0,1) < pr_passive
        pr_bid_signal = np.random.uniform(0,1) < pr_bid
        pr_cancel_signal = np.random.uniform(0,1) < pr_cancel

        if pr_passive_signal:
            if pr_bid_signal:
                best_bid = book_format[2]
                prices_to_choose = [best_bid - i for i in range(step,step*levels_n)]
                price = random.choice(prices_to_choose)
                amount = self.order_amount
                order['bid'] = {price:[amount]}
            else:
                best_ask = book_format[0]
                prices_to_choose = [best_ask + i for i in range(step,step*levels_n)]
                price = random.choice(prices_to_choose)
                amount = self.order_amount
                order['ask'] = {price:[amount]}
        else:
            if pr_bid_signal:
                best_bid = book_format[2]
                price = best_bid + step
                amount = self.order_amount
                order['bid'] = {price:[amount]}
            else:
                best_ask = book_format[0]
                price = best_ask - step
                amount = self.order_amount
                order['ask'] = {price:[amount]}

        if pr_cancel_signal:
            direction_to_cancel = random.choice(['ask','bid'])
            order[direction_to_cancel][None] = [-1]
        

        return order



    async def act(self) -> None:
        """
        generates action based on active orders in the market.
        """
        
        if not self.order_book:
            await self.post_new_order(1,self.initial_value + self.step ,OrderType.ASK)
            await self.post_new_order(1,self.initial_value - self.step ,OrderType.BID)
            return

        book_format = convert_to_book_format_new(self.order_book)

        bid_count = len(self.order_book['bids'])
        ask_count = len(self.order_book['asks'])

        if bid_count == 0:
            best_ask = book_format[0]
            await self.post_new_order(1,best_ask - self.step ,OrderType.BID)

        if ask_count == 0:
            best_bid = book_format[2]
            await self.post_new_order(1,best_bid + self.step ,OrderType.ASK)
        
        
        # noise_state = convert_to_noise_state(self.orders)

        # signal_noise = self.get_signal_noise(
        #     signal_state=None, settings_noise=self.settings_noise
        # )
        
        # noise_orders = self.get_noise_rule_unif(
        #     book_format, signal_noise, noise_state, self.settings_noise, self.settings
        # )

        noise_orders = self.get_noise_order(book_format)
        # print(noise_orders)
        orders = convert_to_trader_actions(noise_orders)
        # print(orders)

        # bid_count = len(self.order_book['bids'])
        # ask_count = len(self.order_book['asks'])
        # order_type_override = None
        # order_type = None

        # if bid_count == 0 and ask_count > 0:
        #      order_type = OrderType.BID
        #      order_type_override = OrderType.BID
        # elif ask_count == 0 and bid_count > 0:
        #      order_type = OrderType.ASK
        #      order_type_override = OrderType.ASK

        # logger.info(
        #     "NO %s IN THE MARKET, PUTTING %s TO BALANCE",
        #     order_type,
        #     order_type_override,
        # )

        for order in orders:
            # if order_type_override is not None:
            #     order["order_type"] = order_type_override
            await self.process_order(order)
    

    async def process_order(self, order) -> None:
        if order["action_type"] == ActionType.POST_NEW_ORDER.value:
            order_type = order["order_type"]
            amount, price = self.order_amount, order["price"]
            for _ in range(order["amount"]):
                await self.post_new_order(amount, price, order_type)


            logger.info(
                "POSTED %s AT %s AMOUNT %s * %s",
                order["order_type"],
                price,
                self.order_amount,
                order["amount"],
            )

        elif order["action_type"] == ActionType.CANCEL_ORDER.value:
            await self.cancel_random_order()

    async def cancel_random_order(self) -> None:
            """
            Cancels a random existing order from the trader's order list.
            """
            if not self.orders:
                logger.info("No orders to cancel.")
                return

            # Select a random order to cancel
            order_to_cancel = random.choice(self.orders)
            order_id = order_to_cancel["id"]

            await self.send_cancel_order_request(order_id)
            logger.info(f"Canceled order ID {order_id[:10]}")

    async def warm_up(self, number_of_warmup_orders: int) -> None:
        """
        places warmup orders to poulate order book.
        """
        for _ in range(number_of_warmup_orders):
            await self.act()
            pass

    # async def post_orders_from_list(self):
    #     if self.order_index < len(self.order_list):
    #         await self.post_new_order(1, self.order_list[self.order_index][0], self.order_list[self.order_index][1])
    #         self.order_index += 1

    async def run(self) -> None:
        """
        trades at cooling intervals.
        """
        while not self._stop_requested.is_set():
            try:
                await self.act()
                #await self.post_orders_from_list()
                #await self.cancel_random_order()
                
                await asyncio.sleep(
                    self.cooling_interval(target=self.activity_frequency)
                )

            except asyncio.CancelledError:
                logger.info(
                    "Run method cancelled, performing cleanup of %s...",
                    self.trader_type,
                )
                await self.clean_up()
                raise
            except Exception as e:
                logger.error("An error occurred in NoiseTrader run loop: %s", e)
                break