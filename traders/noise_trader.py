import asyncio
import random
import numpy as np
from structures import OrderType, TraderType
from main_platform.utils import (
    convert_to_book_format,
    convert_to_noise_state,
    convert_to_trader_actions,
)
from main_platform.custom_logger import setup_custom_logger
from .base_trader import BaseTrader

logger = setup_custom_logger(__name__)


class NoiseTrader(BaseTrader):
    def __init__(
        self,
        activity_frequency: float,
        order_amount: int,
        settings: dict,
        settings_noise: dict,
        get_signal_noise: callable,
        get_noise_rule_unif: callable,
    ):
        """
        initializes the noise trader with settings and callable functions.
        """
        super().__init__(trader_type=TraderType.NOISE)

        self.activity_frequency = activity_frequency
        self.order_amount = order_amount
        self.settings = settings
        self.settings_noise = settings_noise
        self.get_signal_noise = get_signal_noise
        self.get_noise_rule_unif = get_noise_rule_unif
        self.current_variance = 5.0

    def cooling_interval(self, target: float) -> float:
        """
        adjusts cooling interval using a random process.
        """
        interval = np.random.exponential(target)
        return interval

    async def act(self) -> None:
        """
        generates action based on active orders in the market.
        """
        if not self.active_orders:
            await self.post_new_order(
                self.order_amount,
                self.settings["initial_price"],
                random.choice([OrderType.ASK, OrderType.BID]),
            )
            return

        book_format = convert_to_book_format(self.active_orders)
        noise_state = convert_to_noise_state(self.orders)
        signal_noise = self.get_signal_noise(
            signal_state=None, settings_noise=self.settings_noise
        )
        noise_orders = self.get_noise_rule_unif(
            book_format, signal_noise, noise_state, self.settings_noise, self.settings
        )
        orders = convert_to_trader_actions(noise_orders)

        bid_count, ask_count = 0, 0
        for order in self.active_orders:
            if order["order_type"] == OrderType.BID:
                bid_count += 1
            elif order["order_type"] == OrderType.ASK:
                ask_count += 1

        order_type_override = None
        order_type = None

        if bid_count == 0 and ask_count > 0:
            order_type = OrderType.BID
            order_type_override = OrderType.BID
        elif ask_count == 0 and bid_count > 0:
            order_type = OrderType.ASK
            order_type_override = OrderType.ASK

        logger.info(
            "NO %s IN THE MARKET, PUTTING %s TO BALANCE",
            order_type,
            order_type_override,
        )

        for order in orders:
            if order_type_override is not None:
                order["order_type"] = order_type_override

            await self.process_order(order)

    async def process_order(self, order) -> None:
        if order["action_type"] == "add_order":
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

        elif order["action_type"] == "cancel_order" and self.orders:
            matching_orders = [
                o for o in self.orders if o["order_type"] == order["order_type"]
            ]
            if matching_orders:
                order_id = random.choice(matching_orders)["id"]
                await self.send_cancel_order_request(order_id)
                logger.info("CANCELLED %s ID %s", order["order_type"], order_id[:10])

    async def warm_up(self, number_of_warmup_orders: int) -> None:
        """
        places warmup orders to poulate order book.
        """
        for _ in range(number_of_warmup_orders):
            await self.act()

    async def run(self) -> None:
        """
        trades at cooling intervals.
        """
        while not self._stop_requested.is_set():
            try:
                # print('im working: noise trader')
                await self.act()

                
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
