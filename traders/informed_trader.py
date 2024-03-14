import asyncio
import random
from datetime import datetime
from structures import OrderType, TraderType
from main_platform.custom_logger import setup_custom_logger
from main_platform.utils import now
from .base_trader import BaseTrader

logger = setup_custom_logger(__name__)


class InformedTrader(BaseTrader):

    def __init__(
        self,
        activity_frequency: int,
        settings: dict,
        settings_informed: dict,
        informed_state: dict,
        trading_day_duration: int,
        get_informed_time_plan: callable,
        get_signal_informed: callable,
        get_informed_order: callable,
    ):
        """
        initializes the informed trader with settings and callable functions.
        """
        super().__init__(trader_type=TraderType.INFORMED)
        self.activity_frequency = activity_frequency
        self.settings = settings
        self.settings_informed = settings_informed
        self.informed_state = informed_state
        self.trading_day_duration = trading_day_duration
        self.get_informed_time_plan = get_informed_time_plan
        self.get_signal_informed = get_signal_informed
        self.time_plan = self.get_informed_time_plan(
            self.settings_informed, self.settings
        )
        self.step_frequency = (
            self.trading_day_duration
            * 60
            / (self.settings["n_updates_session"] + self.settings["warmup_periods"])
        )

        self.current_step = 0

    @property
    def current_time(self) -> datetime:
        """
        a temporary solution to map time to step.
        """
        return now()

    def get_best_bid_and_ask(self) -> tuple:
        """
        a helper function to decide on price.
        """
        best_bid = None
        best_ask = None

        for order in self.active_orders:
            if order["order_type"] == "bid":
                if best_bid is None or order["price"] > best_bid["price"]:
                    best_bid = order
            elif order["order_type"] == "ask":
                if best_ask is None or order["price"] < best_ask["price"]:
                    best_ask = order

        return best_bid, best_ask

    def get_informed_order(
        self, signal_informed: list, settings_informed: dict
    ) -> dict:
        """
        generates informed trader's orders.
        TODO
        THE PRICE SHOULD BE LEARNED FROM PROFITS AND LOSSES.
        """
        action, num_shares = signal_informed[0], signal_informed[1]
        best_bid, best_ask = self.get_best_bid_and_ask()
        order = {}
        price_variation = random.randint(1, 10)

        if action == 1:
            if settings_informed["inv"] > 0:
                price = (
                    (best_ask["price"] - price_variation)
                    if best_ask
                    else self.settings["initial_price"] - price_variation
                )
                order = {"bid": {price: [num_shares]}, "ask": {}}
            elif settings_informed["inv"] < 0:
                price = (
                    (best_bid["price"] + price_variation)
                    if best_bid
                    else self.settings["initial_price"] + price_variation
                )
                order = {"bid": {}, "ask": {price: [num_shares]}}

        return order

    async def act(self):
        """
        loads step-wise signal and generates orders.
        """
        signal = self.get_signal_informed(
            self.informed_state, self.settings_informed, self.current_step
        )
        order_dict = self.get_informed_order(signal, self.settings_informed)

        for order_type, orders in order_dict.items():
            for price, amounts in orders.items():
                for amount in amounts:
                    if order_type == "bid":
                        await self.post_new_order(amount, price, OrderType.BID)
                    elif order_type == "ask":
                        await self.post_new_order(amount, price, OrderType.ASK)
                    logger.info(
                        "POSTED %s AT %s AMOUNT %s AT STEP %s AT TIME %s",
                        order_type,
                        price,
                        amount,
                        self.current_step,
                        self.current_time.strftime("%H:%M:%S"),
                    )

    async def run(self):
        """
        trades at each step.
        """
        while not self._stop_requested.is_set():
            try:
                await self.act()
                await asyncio.sleep(self.step_frequency)
                self.current_step += 1
            except asyncio.CancelledError:
                logger.info(
                    "Run method cancelled, performing cleanup of %s...",
                    self.trader_type,
                )
                await self.clean_up()
                raise
            except Exception as e:
                logger.error("An error occurred in InformedTrader run loop: %s", e)
                break
