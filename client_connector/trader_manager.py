"""
This file is for the trader manager: it is needed for connectingn, launching and managing human traders connections.
Upon the request  of a client, it lauchnes new trading sessions and/or helps finding the exsiting traders and return their ids back to clients
so they can communicate with them.
"""

import uuid

from external_traders.noise_trader import get_signal_noise, settings_noise, settings, get_noise_rule_unif
from external_traders.informed_naive import get_informed_time_plan, get_signal_informed, get_informed_order, settings_informed, informed_state
from structures import TraderCreationData
from typing import List
from traders import HumanTrader, NoiseTrader, InformedTrader

from main_platform import TradingSession
import logging
import asyncio

logger = logging.getLogger(__name__)


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
        logger.critical(f"TraderManager params: {params}")
        self.tasks = []
        n_noise_traders = params.get("num_noise_traders", 1)

        n_informed_traders = params.get("num_informed_traders", 1)

        cash= params.get("initial_cash", 0)
        shares= params.get("initial_stocks", 0)

        # TODO: we may start launching with more than one human trader later.
        # So far for debugging purposes we only need one human trader whose id we return to the client
        n_human_traders = params.get("num_human_traders", 1)
        activity_frequency = params.get("activity_frequency", 5)
        self.noise_warm_ups = params.get("noise_warm_ups", 10)

        self.noise_traders = [NoiseTrader(activity_frequency=activity_frequency, 
                                          settings=settings,
                                          settings_noise=settings_noise,
                                          get_signal_noise=get_signal_noise,
                                          get_noise_rule_unif=get_noise_rule_unif) for _ in range(n_noise_traders)]


        self.informed_traders = [InformedTrader(activity_frequency=activity_frequency, 
                                                settings=settings, 
                                                settings_informed=settings_informed, 
                                                informed_state=informed_state, 
                                                trading_day_duration=params.get('trading_day_duration', 5),
                                                get_informed_time_plan=get_informed_time_plan, 
                                                get_signal_informed=get_signal_informed,
                                                get_informed_order=get_informed_order) for _ in range(n_informed_traders)]
                
        self.human_traders = [HumanTrader(cash=cash, shares=shares) for _ in range(n_human_traders)]

        print(f'noise_traders: {self.noise_traders}')
        print(f'informed_traders: {self.informed_traders}')
        print(f'human_traders: {self.human_traders}')

        self.traders = {t.id: t for t in self.noise_traders + self.informed_traders + self.human_traders}

        print(f'traders: {self.traders}')

        self.trading_session = TradingSession(duration=params['trading_day_duration'])


    async def launch(self):
        await self.trading_session.initialize()
        logger.info(f"Trading session UUID: {self.trading_session.id}")

        for trader_id, trader in self.traders.items():
            await trader.initialize()
            await trader.connect_to_session(trading_session_uuid=self.trading_session.id)

        for trader in self.noise_traders:
            await trader.warm_up(number_of_warmup_orders=self.noise_warm_ups)

        await self.trading_session.send_broadcast({"content": "Market is open"})

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