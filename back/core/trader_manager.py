"""
This file is for the trader manager: it is needed for connecting, launching and managing human traders connections.
Upon the request of a client, it launches new trading sessions and/or helps finding the existing traders and return their ids back to clients
so they can communicate with them.
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

logger = setup_custom_logger(__name__)

class TraderManager:
    params: TradingParameters
    trading_system: TradingPlatform = None
    traders = {}
    human_traders = List[HumanTrader]
    noise_traders = List[NoiseTrader]
    informed_traders = List[InformedTrader]
    user_roles: dict  # Store user_roles in the instance

    def __init__(self, params: TradingParameters, user_roles: dict):
        self.params = params
        self.user_roles = user_roles  # Store user_roles in the instance
        
        # Remove the minimum 2 traders enforcement
        params = params.model_dump()
        self.tasks = []

        # Generate a new session ID
        current_timestamp = int(time.time())
        session_id = f"SESSION_{current_timestamp}"

        n_noise_traders = params.get("num_noise_traders", 1)
        n_informed_traders = params.get("num_informed_traders", 1)
        n_human_traders = params.get("num_human_traders", 2)  # Default to 2 if not specified

        cash = params.get("initial_cash", 0)
        shares = params.get("initial_stocks", 0)

        # Initialize traders
        self.book_initializer = self._create_book_initializer(params)
        self.simple_order_traders = self._create_simple_order_traders(params)
        self.noise_traders = self._create_noise_traders(n_noise_traders, params)
        self.informed_traders = self._create_informed_traders(n_informed_traders, params)
        self.human_traders = []  # Initialize as an empty list

        self.traders = {
            t.id: t
            for t in self.noise_traders
            + self.informed_traders
            + [self.book_initializer]
            + self.simple_order_traders
        }
        self.trading_session = TradingPlatform(
            session_id=session_id,  # Pass the new session ID here
            duration=params["trading_day_duration"],
            default_price=params.get("default_price"),
            params=params
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

    async def add_human_trader(self, uid):
        if len(self.human_traders) >= self.params.num_human_traders:
            raise ValueError("Session is full")
        
        trader_id = f"HUMAN_{uid}"
        
        # Check if trader already exists
        existing_trader = self.traders.get(trader_id)
        if existing_trader:
            return trader_id
            
        # Determine the goal based on number of traders and role
        if self.params.num_human_traders == 1:
            # Single trader is always a speculator
            goal = 0
        else:
            # Use existing role-based logic for multiple traders
            role = self.user_roles.get(uid, 'speculator')
            if role == 'informed':
                goal_index = len(self.human_traders) % len(self.params.human_goals)
                goal = self.params.human_goals[goal_index]
            else:
                goal = 0
        
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
            task.cancel()  # Request cancellation of the task
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()  # Clear the list of tasks after cancellation

    def get_trader(self, trader_id):
        trader = self.traders.get(trader_id)
        if trader and isinstance(trader, HumanTrader):
            # Ensure trader info includes goal progress
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
