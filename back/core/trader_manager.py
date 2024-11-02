"""
trader manager: connects and manages human traders

launches new trading sessions when clients ask for them
helps find existing traders and returns their ids
"""

from .data_models import TradingParameters, OrderType, ActionType, TraderType
from typing import List
from traders import (
    HumanTrader,
    NoiseTrader,
    InformedTrader,
    BookInitializer,
    SimpleOrderTrader,
)
from core import TradingPlatform
import asyncio
from utils import setup_custom_logger
import time
import random

logger = setup_custom_logger(__name__)

class TraderManager:
    params: TradingParameters
    trading_system: TradingPlatform = None
    traders = {}
    human_traders = List[HumanTrader]
    noise_traders = List[NoiseTrader]
    informed_traders = List[InformedTrader]

    def __init__(self, params: TradingParameters, user_roles: dict = None):
        self.params = params
        self.tasks = []

        # grab current time for session id
        current_timestamp = int(time.time())
        session_id = f"SESSION_{current_timestamp}"

        # make params easier to use
        params_dict = params.model_dump()

        n_noise_traders = params_dict["num_noise_traders"]
        n_informed_traders = params_dict["num_informed_traders"]
        n_human_traders = params_dict["num_human_traders"]

        cash = params_dict["initial_cash"]
        shares = params_dict["initial_stocks"]

        # create all the traders we need
        self.book_initializer = self._create_book_initializer(params_dict)
        self.simple_order_traders = self._create_simple_order_traders(params_dict)
        self.noise_traders = self._create_noise_traders(n_noise_traders, params_dict)
        self.informed_traders = self._create_informed_traders(n_informed_traders, params_dict)
        self.human_traders = []  # start with no humans

        self.traders = {
            t.id: t
            for t in self.noise_traders
            + self.informed_traders
            + [self.book_initializer]
            + self.simple_order_traders
        }
        self.trading_session = TradingPlatform(
            session_id=session_id,
            duration=params_dict["trading_day_duration"],
            default_price=params_dict["default_price"],
            params=params_dict
        )

    def _create_simple_order_traders(self, params):
        traders = []
        num_traders = params["num_simple_order_traders"]
        for i in range(num_traders):
            if i % 2 == 0:  # even numbers do bids
                trader_orders = [
                    {"amount": 1, "price": 100 + i, "order_type": OrderType.BID},
                    {"amount": 1, "price": 101 + i, "order_type": OrderType.BID},
                    {"amount": 1, "price": 102 + i, "order_type": OrderType.BID},
                ]
            else:  # odd numbers do asks
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

    async def add_human_trader(self, uid, goal=None):
        if len(self.human_traders) >= self.params.num_human_traders:
            raise ValueError("Session is full")
        
        trader_id = f"HUMAN_{uid}"
        
        # check if they're already here
        existing_trader = self.traders.get(trader_id)
        if existing_trader:
            return trader_id
        
        # figure out their goal
        if goal is None:
            available_goals = self.params.predefined_goals
            if self.params.allow_random_goals:
                # grab a non-zero goal if we can
                non_zero_goals = [g for g in available_goals if g != 0]
                if non_zero_goals:
                    # flip a coin for positive/negative
                    magnitude = abs(random.choice(non_zero_goals))
                    goal = magnitude * random.choice([-1, 1])
                else:
                    # no non-zero goals? just pick whatever
                    goal = random.choice(available_goals)
            else:
                # stick to the script
                goal = random.choice(available_goals)
        
        new_trader = HumanTrader(
            id=trader_id,
            cash=self.params.initial_cash,
            shares=self.params.initial_stocks,
            goal=goal,
            trading_session=self.trading_session,
            params=self.params.model_dump(),
            gmail_username=uid
        )
        
        self.trading_session.connected_traders[trader_id] = {
            "trader_type": TraderType.HUMAN,
            "uid": uid,
            "trader": new_trader
        }
        self.traders[trader_id] = new_trader
        self.human_traders.append(new_trader)
        return trader_id

    async def set_trader_goal(self, trader_id: str, goal: int):
        """give trader a new goal"""
        trader = self.traders.get(trader_id)
        if trader and isinstance(trader, HumanTrader):
            trader.goal = goal
            return True
        return False

    async def launch(self):
        await self.trading_session.initialize()

        for trader_id, trader in self.traders.items():
            await trader.initialize()

            if not isinstance(trader, HumanTrader):
                await trader.connect_to_session(
                    trading_session_uuid=self.trading_session.id
                )

        await self.book_initializer.initialize_order_book()

        self.trading_session.set_initialization_complete()

        while len(self.human_traders) < self.params.num_human_traders:
            await asyncio.sleep(1)

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
            task.cancel()  # bye bye tasks
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()  # clean slate

    def get_trader(self, trader_id):
        trader = self.traders.get(trader_id)
        if trader and isinstance(trader, HumanTrader):
            # get their stats too
            trader_info = trader.get_trader_params_as_dict()
            return trader
        return trader

    def exists(self, trader_id):
        return trader_id in self.traders

    def get_params(self):
        params = self.params.model_dump()
        trading_session_params = self.trading_session.get_params()
        params.update(trading_session_params)
        return params
