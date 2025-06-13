"""
trader manager: connects and manages human traders

launches new trading markets when clients ask for them
helps find existing traders and returns their ids
"""

from .data_models import TradingParameters, OrderType, ActionType, TraderType, TraderRole
from typing import List, Optional
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
    human_informed_trader = None

    def __init__(self, params: TradingParameters):
        self.params = params
        self.trading_market = TradingPlatform(
            market_id=f"MARKET_{int(time.time())}",
            duration=params.trading_day_duration,
            default_price=params.default_price,
            default_spread=getattr(params, 'default_spread', 10),
            punishing_constant=getattr(params, 'punishing_constant', 1),
            params=params.model_dump(),
        )
        self.traders = {}
        self.human_traders = []
        self.noise_traders = []
        self.informed_traders = []
        self.human_informed_trader = None
        self.book_initializer = None
        self.tasks = []

        # Set up automated traders
        self._setup_noise_traders()
        self._setup_informed_traders() 
        self._setup_book_initializer()

    def _setup_noise_traders(self):
        """Set up noise traders"""
        for i in range(self.params.num_noise_traders):
            trader_id = f"NOISE_{i}"
            noise_trader = NoiseTrader(
                id=trader_id,
                initial_cash=self.params.initial_cash,
                initial_shares=self.params.initial_stocks,
                default_price=self.params.default_price,
                trading_market=self.trading_market,
                params=self.params.model_dump(),
            )
            self.traders[trader_id] = noise_trader
            self.noise_traders.append(noise_trader)

    def _setup_informed_traders(self):
        """Set up informed traders"""
        for i in range(self.params.num_informed_traders):
            trader_id = f"INFORMED_{i}"
            informed_trader = InformedTrader(
                id=trader_id,
                initial_cash=self.params.initial_cash,
                initial_shares=self.params.initial_stocks,
                default_price=self.params.default_price,
                trading_market=self.trading_market,
                params=self.params.model_dump(),
            )
            self.traders[trader_id] = informed_trader
            self.informed_traders.append(informed_trader)

    def _setup_book_initializer(self):
        """Set up book initializer"""
        self.book_initializer = BookInitializer(
            default_price=self.params.default_price,
            default_spread=self.params.default_spread,
            initial_depth=self.params.initial_depth,
            trading_market=self.trading_market,
            params=self.params.model_dump(),
        )
        trader_id = f"BOOK_INITIALIZER"
        self.traders[trader_id] = self.book_initializer

    async def add_human_trader(self, gmail_username: str, role: TraderRole, goal: Optional[int] = None) -> str:
        """Add human trader with specified role and goal"""
        trader_id = f"HUMAN_{gmail_username}"
        
        if trader_id in self.traders:
            return trader_id

        new_trader = HumanTrader(
            id=trader_id,
            cash=self.params.initial_cash,
            shares=self.params.initial_stocks,
            goal=goal,
            role=role,
            trading_market=self.trading_market,
            params=self.params.model_dump(),
            gmail_username=gmail_username
        )
        
        if role == TraderRole.INFORMED:
            # Allow multiple human informed traders
            self.human_informed_trader = new_trader

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

    def get_num_human_traders(self):
        return len(self.human_traders)

    def get_all_trader_ids(self):
        return list(self.traders.keys())

    def get_all_human_trader_ids(self):
        return [trader.id for trader in self.human_traders]

    def get_num_noise_traders(self):
        return len(self.noise_traders)

    def get_num_informed_traders(self):
        return len(self.informed_traders)

    def get_noise_trader_ids(self):
        return [trader.id for trader in self.noise_traders]

    def get_informed_trader_ids(self):
        return [trader.id for trader in self.informed_traders]

    def get_remaining_goals(self):
        """Get remaining goals that haven't been assigned to human traders"""
        assigned_goals = [trader.goal for trader in self.human_traders if trader.goal]
        remaining = [goal for goal in self.params.predefined_goals if goal not in assigned_goals]
        return remaining

    async def launch(self):
        await self.trading_market.initialize()

        # Connect all traders to the trading platform
        for trader_id, trader in self.traders.items():
            await trader.initialize()
            
            # Set up direct connection to trading platform
            trader.set_trading_platform(self.trading_market)
            
            # Connect non-human traders to market immediately
            if not isinstance(trader, HumanTrader):
                await trader.connect_to_market(self.trading_market.id)

        # Initialize the order book
        await self.book_initializer.initialize_order_book()

        self.trading_market.set_initialization_complete()

        # Wait for all required traders based on predefined_goals length
        num_required_traders = len(self.params.predefined_goals)
        
        # Check if any of the human traders is a Prolific user
        has_prolific_user = any("prolific" in trader.id.lower() for trader in self.human_traders)
        
        # Skip waiting if we have a Prolific user, otherwise wait for all required traders
        if not has_prolific_user:
            while len(self.human_traders) < num_required_traders:
                await asyncio.sleep(1)

        await self.trading_market.start_trading()

        # Start all trader tasks
        trading_market_task = asyncio.create_task(self.trading_market.run())
        trader_tasks = [asyncio.create_task(trader.run()) for trader in self.traders.values()]

        self.tasks.append(trading_market_task)
        self.tasks.extend(trader_tasks)

        await trading_market_task

    async def cleanup(self):
        await self.trading_market.clean_up()
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
        trading_market_params = self.trading_market.get_params()
        params.update(trading_market_params)
        return params
