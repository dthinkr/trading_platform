import asyncio
import random
from datetime import datetime
from structures import OrderType, TraderType, str_to_order_type
from main_platform.custom_logger import setup_custom_logger
from main_platform.utils import convert_to_book_format_new
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
        book = convert_to_book_format_new(self.order_book)

        #     # PNL BLOCK
        # self.DInv = []
        # self.transaction_prices = []
        # self.transaction_relevant_mid_prices = []  # Mid prices relevant to each transaction
        # self.general_mid_prices = []  # All mid prices from the trading system
        # self.sum_cost = 0
        # self.sum_dinv = 0
        # self.sum_mid_executions = 0
        # self.current_pnl = 0


        # print(f"DInv: {self.DInv}, transaction_prices: {self.transaction_prices}, transaction_relevant_mid_prices: {self.transaction_relevant_mid_prices}, general_mid_prices: {self.general_mid_prices}, sum_cost: {self.sum_cost}, sum_dinv: {self.sum_dinv}, sum_mid_executions: {self.sum_mid_executions}, current_pnl: {self.current_pnl}")

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
                        await self.post_new_order(amount, price, str_to_order_type[order_type])
                        # logging
                        logger.critical(
                            "INFORMED MATCHING %s AT %s AMOUNT %s AT TIME %s",
                            order_type,
                            price,
                            amount,
                            elapsed_time_sec,
                        )
        except Exception as e:
            print(e)

    async def run(self) -> None:
        """
        trades at each step.
        """
        while not self._stop_requested.is_set():
            try:
                await self.act()
                print("InformedTrader run method")
                # print(f'i have {self.shares} shares and {self.cash} cash')
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
