import asyncio
import random
from datetime import datetime
from structures import OrderType, TraderType
from main_platform.custom_logger import setup_custom_logger
from main_platform.utils import convert_to_book_format
from .base_trader import BaseTrader

logger = setup_custom_logger(__name__)


class InformedTrader(BaseTrader):
    def __init__(
        self,
        activity_frequency: int,
        settings: dict,
        settings_informed: dict,
        informed_time_plan: dict,
        informed_state: dict,
        get_signal_informed: callable,
        get_order_to_match: callable,
    ):
        """
        initializes the informed trader with settings and callable functions.
        """
        super().__init__(trader_type=TraderType.INFORMED)
        self.activity_frequency = activity_frequency
        self.settings = settings
        self.settings_informed = settings_informed
        self.informed_time_plan = informed_time_plan
        self.informed_state = informed_state
        self.get_signal_informed = get_signal_informed
        self.get_order_to_match = get_order_to_match

    async def act(self) -> None:
        """
        Loads signal and generates orders.
        """
        # prep the order book based on active orders
        book = convert_to_book_format(self.active_orders)

        elapsed_time_sec = int(self.get_elapsed_time())

        try:
            signal_informed = self.get_signal_informed(
                self.informed_state,
                self.settings_informed,
                self.informed_time_plan,
                elapsed_time_sec,
            )
            order_dict = self.get_order_to_match(
                book,
                signal_informed,
                self.informed_state,
                self.settings_informed,
                self.settings,
                elapsed_time_sec,
            )

            for order_type, orders in order_dict.items():
                for price, amounts in orders.items():
                    for amount in amounts:
                        # if the order to be matched is a bid, we send an ask order to match that bid
                        if order_type == OrderType.BID:
                            await self.post_new_order(amount, price, OrderType.ASK)
                        # if the order to be matched is an ask, we send a bid order to match that ask
                        elif order_type == OrderType.ASK:
                            await self.post_new_order(amount, price, OrderType.BID)
                        # logging
                        # logger.critical(
                        #     "MATCHING %s AT %s AMOUNT %s AT TIME %s",
                        #     order_type,
                        #     price,
                        #     amount,
                        #     elapsed_time_sec,
                        # )
        except Exception as e:
            print(e)

    async def run(self) -> None:
        """
        trades at each step.
        """
        while not self._stop_requested.is_set():
            try:
                await self.act()
                # print("InformedTrader run method")
                await asyncio.sleep(1)

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
