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
    ManipulatorTrader,
    BookInitializer,
    SimpleOrderTrader,
    SpoofingTrader,
    AgenticTrader,
    AgenticAdvisor,
)
from .trading_platform import TradingPlatform
import asyncio
import os
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
    human_informed_trader = None  # Track the human trader with INFORMED role in this market

    def __init__(self, params: TradingParameters, market_id: str = None):
        self.params = params
        self.tasks = []
        self.human_informed_trader = None  # Keep only for tracking human trader with INFORMED role
        self.human_traders = []
        
        params_dict = params.model_dump()  # Convert to dict for easier access
        
        # Create basic traders
        self.book_initializer = self._create_book_initializer(params)
        self.simple_order_traders = self._create_simple_order_traders(params_dict)  # Pass dict
        self.noise_traders = self._create_noise_traders(params.num_noise_traders, params_dict)  # Pass dict
        self.informed_traders = self._create_informed_traders(params.num_informed_traders, params_dict)  # Pass dict
        self.manipulator_traders = self._create_manipulator_traders(params.num_manipulator_traders, params_dict)  # Pass dict
        self.spoofing_traders = self._create_spoofing_traders(params.num_spoofing_traders, params_dict)  # Pass dict
        self.agentic_traders = self._create_agentic_traders(params.num_agentic_traders, params_dict)
        self.agentic_advisors = self._create_agentic_advisors(params_dict)

        # Combine all traders into one dict
        self.traders = {
            t.id: t
            for t in self.noise_traders
            + self.informed_traders
            + self.manipulator_traders
            + self.spoofing_traders
            + self.agentic_traders
            + self.agentic_advisors
            + [self.book_initializer]
            + self.simple_order_traders
        }
        
        # Create trading market
        # Use provided market_id or generate one with timestamp
        if market_id is None:
            current_timestamp = int(time.time())
            market_id = f"MARKET_{current_timestamp}"
        
        self.trading_market = TradingPlatform(
            market_id=market_id,
            duration=params.trading_day_duration,
            default_price=params.default_price,
            params=params_dict  # Pass dict
        )

    def _create_simple_order_traders(self, params: dict):
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

    def _create_book_initializer(self, params: TradingParameters):
        return BookInitializer(id="BOOK_INITIALIZER", trader_creation_data=params.model_dump())

    def _create_noise_traders(self, n_noise_traders: int, params: dict):
        return [
            NoiseTrader(
                id=f"NOISE_{i+1}",
                params=params,
            )
            for i in range(n_noise_traders)
        ]

    def _create_informed_traders(self, n_informed_traders: int, params: dict):
        if n_informed_traders <= 0:
            return []
            
        traders = [
            InformedTrader(
                id=f"INFORMED_{i+1}",
                params=params,
            )
            for i in range(n_informed_traders)
        ]
        
        return traders

    def _create_manipulator_traders(self, n_manipulator_traders: int, params: dict):
        if n_manipulator_traders <= 0:
            return []
            
        traders = [
            ManipulatorTrader(
                id=f"MANIPULATOR_{i+1}",
                params=params,
            )
            for i in range(n_manipulator_traders)
        ]

        return traders
        
    
    def _create_spoofing_traders(self, n_spoofing_traders: int, params: dict):
        return [
            SpoofingTrader(
                id=f"SPOOFING_{i+1}",
                params=params,
            )
            for i in range(n_spoofing_traders)
        ]

    def _create_agentic_traders(self, n_agentic_traders: int, params: dict):
        """Create autonomous agentic traders."""
        if n_agentic_traders <= 0:
            return []
        
        # Get agentic goals from params (can be a list or single value)
        agentic_goals = params.get("agentic_goals", [20])  # Default: buy 20 shares
        if not isinstance(agentic_goals, list):
            agentic_goals = [agentic_goals]
        
        traders = []
        for i in range(n_agentic_traders):
            # Cycle through goals if fewer goals than traders
            goal = agentic_goals[i % len(agentic_goals)]
            
            agentic_params = {
                **params,
                "openrouter_api_key": os.getenv("OPENROUTER_API_KEY"),
                "agentic_model": params.get("agentic_model", "anthropic/claude-haiku-4.5"),
                "decision_interval": params.get("agentic_decision_interval", 5.0),
                "goal": goal,
                "initial_cash": params.get("initial_cash", 100000),
                "initial_shares": params.get("initial_stocks", 0),
                # Reward formula params
                "buy_target_price": params.get("agentic_buy_target_price", 110),
                "sell_target_price": params.get("agentic_sell_target_price", 90),
            }
            
            traders.append(
                AgenticTrader(
                    id=f"AGENTIC_{i+1}",
                    params=agentic_params,
                )
            )
        
        return traders

    def _create_agentic_advisors(self, params: dict):
        """Create agentic advisors for humans (1:1 mapping)."""
        advisor_for_humans = params.get("agentic_advisor_for_humans", [])
        if not isinstance(advisor_for_humans, list):
            advisor_for_humans = [advisor_for_humans] if advisor_for_humans else []
        
        if not advisor_for_humans:
            return []
        
        advisors = []
        for i, human_id in enumerate(advisor_for_humans):
            advisor_params = {
                **params,
                "openrouter_api_key": os.getenv("OPENROUTER_API_KEY"),
                "agentic_model": params.get("agentic_model", "anthropic/claude-haiku-4.5"),
                "decision_interval": params.get("agentic_decision_interval", 5.0),
                "advice_for_human_id": human_id,
                # Reward formula params (for prompt building)
                "buy_target_price": params.get("agentic_buy_target_price", 110),
                "sell_target_price": params.get("agentic_sell_target_price", 90),
            }
            
            advisors.append(
                AgenticAdvisor(
                    id=f"ADVISOR_{i+1}",
                    params=advisor_params,
                )
            )
        
        return advisors

    def link_advisors_to_humans(self):
        """Link agentic advisors to their target human traders after humans join."""
        for advisor in self.agentic_advisors:
            human_id = advisor.advice_for_human_id
            if not human_id:
                continue
            # Try to find the human trader
            if human_id in self.traders:
                advisor.set_human_trader_ref(self.traders[human_id])
            else:
                # Try with HUMAN_ prefix
                prefixed_id = f"HUMAN_{human_id}"
                if prefixed_id in self.traders:
                    advisor.set_human_trader_ref(self.traders[prefixed_id])

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
        
        # Create advisor for this human if enabled
        if self.params.agentic_advisor_enabled:
            await self._create_advisor_for_human(new_trader)
        
        # Link any agentic advisors waiting for this human
        self.link_advisors_to_humans()
        
        return trader_id

    async def _create_advisor_for_human(self, human_trader):
        """Create and start an agentic advisor for a human trader."""
        params_dict = self.params.model_dump()
        advisor_params = {
            **params_dict,
            "openrouter_api_key": os.getenv("OPENROUTER_API_KEY"),
            "agentic_model": params_dict.get("agentic_model", "anthropic/claude-haiku-4.5"),
            "decision_interval": params_dict.get("agentic_decision_interval", 5.0),
            "advice_for_human_id": human_trader.id,
            "buy_target_price": params_dict.get("agentic_buy_target_price", 110),
            "sell_target_price": params_dict.get("agentic_sell_target_price", 90),
        }
        
        advisor_id = f"ADVISOR_{human_trader.id}"
        advisor = AgenticAdvisor(id=advisor_id, params=advisor_params)
        
        # Initialize and link
        await advisor.initialize()
        advisor.set_human_trader_ref(human_trader)
        
        # Store reference on human for easy access
        human_trader.advisor = advisor
        
        # Add to tracking lists
        self.agentic_advisors.append(advisor)
        self.traders[advisor_id] = advisor
        
        # Start the advisor's run loop
        asyncio.create_task(advisor.run())
        
        logger.info(f"Created advisor {advisor_id} for {human_trader.id}")

    async def set_trader_goal(self, trader_id: str, goal: int):
        """give trader a new goal"""
        trader = self.traders.get(trader_id)
        if trader and isinstance(trader, HumanTrader):
            trader.goal = goal
            return True
        return False

    async def launch(self):
        await self.trading_market.initialize()

        for trader_id, trader in self.traders.items():
            await trader.initialize()

            if not isinstance(trader, HumanTrader):
                await trader.connect_to_market(
                    trading_market_uuid=self.trading_market.id,
                    trading_market=self.trading_market
                )
                
                # Register AI trader with the trading platform
                await self.trading_market.handle_register_me({
                    "trader_id": trader.id,
                    "trader_type": trader.trader_type,
                    "gmail_username": None,
                    "trader_instance": trader
                })

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

        trading_market_task = asyncio.create_task(self.trading_market.run())
        trader_tasks = [asyncio.create_task(i.run()) for i in self.traders.values()]

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
