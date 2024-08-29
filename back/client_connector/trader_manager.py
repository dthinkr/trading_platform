"""
This file is for the trader manager: it is needed for connecting, launching and managing human traders connections.
Upon the request of a client, it launches new trading sessions and/or helps finding the existing traders and return their ids back to clients
so they can communicate with them.
"""

from structures import TraderCreationData, OrderType, ActionType, TraderType
from typing import List
from traders import (
    HumanTrader,
    NoiseTrader,
    InformedTrader,
    BookInitializer,
    SimpleOrderTrader,
)
from main_platform import TradingSession
import asyncio
from main_platform.custom_logger import setup_custom_logger

logger = setup_custom_logger(__name__)


class TraderManager:
    params: TraderCreationData
    trading_system: TradingSession = None
    traders = {}
    human_traders = List[HumanTrader]
    noise_traders = List[NoiseTrader]
    informed_traders = List[InformedTrader]

    def __init__(self, params: TraderCreationData):
        self.params = params
        params = params.model_dump()
        self.tasks = []

        n_noise_traders = params.get("num_noise_traders", 1)
        n_informed_traders = params.get("num_informed_traders", 1)
        n_human_traders = params.get("num_human_traders", 1)

        cash = params.get("initial_cash", 0)
        shares = params.get("initial_stocks", 0)

        # Initialize traders
        self.book_initializer = self._create_book_initializer(params)

        self.simple_order_traders = self._create_simple_order_traders(params)

        # Create traders with descriptive names
        self.noise_traders = self._create_noise_traders(n_noise_traders, params)
        self.informed_traders = self._create_informed_traders(
            n_informed_traders, params
        )
        self.human_traders = self._create_human_traders(n_human_traders, cash, shares)

        self.traders = {
            t.id: t
            for t in self.noise_traders
            + self.informed_traders
            + self.human_traders
            + [self.book_initializer]
            + self.simple_order_traders
        }
        self.trading_session = TradingSession(
            duration=params["trading_day_duration"],
            default_price=params.get("default_price"),
        )

    def _create_simple_order_traders(self, params):
        traders = []
        num_traders = params["num_simple_order_traders"]
        for i in range(num_traders):
            if i % 2 == 0:  # Even-indexed traders place bids
                trader_orders = [
                    {"amount": 1, "price": 100 + i, "order_type": OrderType.BID},
                    {"amount": 1, "price": 101 + i, "order_type": OrderType.BID},
                    {"amount": 1, "price": 102 + i, "order_type": OrderType.BID},
                ]
            else:  # Odd-indexed traders place asks
                trader_orders = [
                    {"amount": 1, "price": 100 + i, "order_type": OrderType.ASK},
                    {"amount": 1, "price": 101 + i, "order_type": OrderType.ASK},
                    {"amount": 1, "price": 102 + i, "order_type": OrderType.ASK},
                ]
            traders.append(
                SimpleOrderTrader(id=f"SIMPLE_ORDER_{i+1}", orders=trader_orders)
            )
        return traders

    def _create_book_initializer(self, params):
        return BookInitializer(id="BOOK_INITIALIZER", trader_creation_data=params)

    def _create_noise_traders(self, n_noise_traders, params):
        return [
            NoiseTrader(
                id=f"NOISE_{i+1}",
                params=params,
            )
            for i in range(n_noise_traders)
        ]

    def _create_informed_traders(self, n_informed_traders, params):
        return [
            InformedTrader(
                id=f"INFORMED_{i+1}",
                params=params,
            )
            for i in range(n_informed_traders)
        ]

    def _create_human_traders(self, n_human_traders, cash, shares):
        return [
            HumanTrader(id=f"HUMAN_{i+1}", cash=cash, shares=shares)
            for i in range(n_human_traders)
        ]

    async def launch(self):
        await self.trading_session.initialize()

        for trader_id, trader in self.traders.items():
            await trader.initialize()
            await trader.connect_to_session(
                trading_session_uuid=self.trading_session.id
            )

        await self.book_initializer.initialize_order_book()

        self.trading_session.set_initialization_complete()

        await self.trading_session.start_trading()

        trading_session_task = asyncio.create_task(self.trading_session.run())
        trader_tasks = [asyncio.create_task(i.run()) for i in self.traders.values()]

        self.tasks.append(trading_session_task)
        self.tasks.extend(trader_tasks)

        await trading_session_task

    async def cleanup(self):
        await self.trading_session.clean_up()
        for trader in self.traders.values():
            await trader.clean_up()
        for task in self.tasks:
            task.cancel()  # Request cancellation of the task
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()  # Clear the list of tasks after cancellation

    def get_trader(self, trader_id):
        return self.traders.get(trader_id)

    def exists(self, trader_id):
        return trader_id in self.traders

    def get_params(self):
        params = self.params.model_dump()
        trading_session_params = self.trading_session.get_params()
        params.update(trading_session_params)
        return params
