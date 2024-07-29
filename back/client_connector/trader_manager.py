"""
This file is for the trader manager: it is needed for connecting, launching and managing human traders connections.
Upon the request of a client, it launches new trading sessions and/or helps finding the existing traders and return their ids back to clients
so they can communicate with them.
"""

from structures import TraderCreationData, OrderType, ActionType, TraderType
from typing import List
from traders import HumanTrader, NoiseTrader, InformedTrader, BookInitializer
from external_traders.informed_naive import get_signal_informed, get_order_to_match, settings_informed, update_settings_informed
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

        # Prepare settings
        settings = self._prepare_settings(params)
        settings_noise = self._prepare_noise_settings(params, settings)
        updated_settings_informed, informed_time_plan, informed_state = self._prepare_informed_settings(params, settings_noise)

        # Create traders with descriptive names
        self.noise_traders = self._create_noise_traders(n_noise_traders, params, settings, settings_noise)
        self.informed_traders = self._create_informed_traders(n_informed_traders, params, settings, updated_settings_informed, informed_time_plan, informed_state)
        self.human_traders = self._create_human_traders(n_human_traders, cash, shares)

        self.traders = {t.id: t for t in self.noise_traders + self.informed_traders + self.human_traders + [self.book_initializer]}
        self.trading_session = TradingSession(duration=params['trading_day_duration'], default_price=params.get('default_price'))

    def _create_book_initializer(self, params):
        return BookInitializer(id="BOOK_INITIALIZER", trader_creation_data=params)

    def _prepare_settings(self, params):
        return {
            'levels_n': params.get('order_book_levels'),
            'initial': params.get('default_price'),
            'step': params.get('step')
        }

    def _prepare_noise_settings(self, params, settings):
        return {
            'levels_n': settings['levels_n'],
            'pr_passive': params.get('passive_order_probability'),
            'pr_cancel': 0.1,
            'pr_bid': 0.5,
            'step': settings['step']
        }

    def _prepare_informed_settings(self, params, settings_noise):
        settings_informed['time_period_in_min'] = params.get('trading_day_duration')
        settings_informed['trade_intensity'] = params.get('trade_intensity_informed')
        settings_informed['direction'] = params.get('trade_direction_informed')
        settings_informed['NoiseTrader_frequency_activity'] = params.get('activity_frequency')
        settings_informed['pr_passive'] = settings_noise['pr_passive']
        return update_settings_informed(settings_informed)

    def _create_noise_traders(self, n_noise_traders, params, settings, settings_noise):
        return [NoiseTrader(
            id=f"NOISE_{i+1}",
            activity_frequency=params.get('activity_frequency'),
            order_amount=params.get('order_amount'),
            settings=settings,
            settings_noise=settings_noise
        ) for i in range(n_noise_traders)]

    def _create_informed_traders(self, n_informed_traders, params, settings, updated_settings_informed, informed_time_plan, informed_state):
        return [InformedTrader(
            id=f"INFORMED_{i+1}",
            activity_frequency=params.get('activity_frequency'),
            default_price=params.get('default_price'),
            informed_edge=params.get('informed_edge'),
            settings=settings,
            settings_informed=updated_settings_informed,
            informed_time_plan=informed_time_plan,
            informed_state=informed_state,
            get_signal_informed=get_signal_informed,
            get_order_to_match=get_order_to_match
        ) for i in range(n_informed_traders)]

    def _create_human_traders(self, n_human_traders, cash, shares):
        return [HumanTrader(id=f"HUMAN_{i+1}", cash=cash, shares=shares) for i in range(n_human_traders)]


    async def launch(self):
        await self.trading_session.initialize()

        for trader_id, trader in self.traders.items():
            await trader.initialize()
            await trader.connect_to_session(trading_session_uuid=self.trading_session.id)

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