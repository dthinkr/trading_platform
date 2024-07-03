"""
This file is for the trader manager: it is needed for connectingn, launching and managing human traders connections.
Upon the request  of a client, it lauchnes new trading sessions and/or helps finding the exsiting traders and return their ids back to clients
so they can communicate with them.
"""

import uuid

#from external_traders.noise_trader import get_signal_noise, settings_noise, get_noise_rule_unif, settings
from external_traders.informed_naive import get_signal_informed, get_order_to_match, settings_informed, update_settings_informed
from structures import TraderCreationData, OrderType, ActionType, TraderType
from typing import List
from traders import HumanTrader, NoiseTrader, InformedTrader, BookInitializer
import random
import math


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
        params=params.model_dump()
        # disabled as this is stored within db
        # logger.critical(f"TraderManager params: {params}")
        self.tasks = []
        n_noise_traders = params.get("num_noise_traders", 1)

        n_informed_traders = params.get("num_informed_traders", 1)

        cash = params.get("initial_cash", 0)
        shares = params.get("initial_stocks", 0)

        # initialize traders
        self.book_initializer = BookInitializer(params)

        # human traders
        n_human_traders = params.get("num_human_traders", 1)

        # noise trader
        settings = {}
        settings['levels_n'] = params.get('order_book_levels')
        settings['initial'] = params.get('default_price')
        settings['step'] = params.get('step')

        settings_noise = {}
        settings_noise['levels_n'] = settings['levels_n']
        settings_noise['pr_passive'] = params.get('passive_order_probability')
        settings_noise['pr_cancel'] = 0.1
        settings_noise['pr_bid'] = 0.5
        settings_noise['step'] = params.get('step')

        self.noise_traders = [NoiseTrader(activity_frequency=params.get('activity_frequency'),
                                          order_amount=params.get('order_amount'),
                                          settings = settings, 
                                          settings_noise=settings_noise) for _ in range(n_noise_traders)]

        # informed trader
        settings_informed['time_period_in_min'] = params.get('trading_day_duration')
        settings_informed['trade_intensity'] = params.get('trade_intensity_informed')
        settings_informed['direction'] = params.get('trade_direction_informed')
        settings_informed['NoiseTrader_frequency_activity'] = params.get('activity_frequency')
        settings_informed['pr_passive'] = settings_noise['pr_passive']
        updated_settings_informed, informed_time_plan, informed_state = update_settings_informed(settings_informed)
        # print(updated_settings_informed)

        self.informed_traders = [InformedTrader(activity_frequency=params.get('activity_frequency'),
                                                default_price=params.get('default_price'),
                                                informed_edge=params.get('informed_edge'),
                                                settings=settings, 
                                                settings_informed=updated_settings_informed, 
                                                informed_time_plan=informed_time_plan,
                                                informed_state=informed_state,
                                                get_signal_informed=get_signal_informed,
                                                get_order_to_match=get_order_to_match) for _ in range(n_informed_traders)]
                
        self.human_traders = [HumanTrader(cash=cash, shares=shares) for _ in range(n_human_traders)]

        self.traders = {t.id: t for t in self.noise_traders + self.informed_traders + self.human_traders + [self.book_initializer]}
        self.trading_session = TradingSession(duration=params['trading_day_duration'], default_price=params.get('default_price'))


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

    def get_trader(self, trader_uuid):
        return self.traders.get(trader_uuid)

    def exists(self, trader_uuid):
        return trader_uuid in self.traders

    def get_params(self):
        params = self.params.model_dump()
        trading_session_params = self.trading_session.get_params()
        params.update(trading_session_params)
        return params