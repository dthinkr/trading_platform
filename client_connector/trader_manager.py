"""
This file is for the trader manager: it is needed for connectingn, launching and managing human traders connections.
Upon the request  of a client, it lauchnes new trading sessions and/or helps finding the exsiting traders and return their ids back to clients
so they can communicate with them.
"""

import uuid
from typing import List
from traders import HumanTrader, NoiseTrader, BaseTrader
from main_platform import TradingSession
import logging
import asyncio

logger = logging.getLogger(__name__)


class TraderManager:
    trading_system: TradingSession = None
    traders = {}
    human_traders = List[HumanTrader]
    noise_traders = List[NoiseTrader]

    def __init__(self, params: dict):
        self.tasks = []
        n_noise_traders = params.get("n_noise_traders", 1)
        # TODO: we may start launching with more than one human trader later.
        # So far for debugging purposes we only need one human trader whose id we return to the client
        n_human_traders = 2
        activity_frequency = params.get("activity_frequency", 5)
        self.noise_traders = [NoiseTrader(activity_frequency=activity_frequency) for _ in range(n_noise_traders)]
        self.human_traders = [HumanTrader() for _ in range(n_human_traders)]
        self.traders = {t.id: t for t in self.noise_traders + self.human_traders}
        self.trading_session = TradingSession()

    async def launch(self):
        await self.trading_session.initialize()
        logger.info(f"Trading session UUID: {self.trading_session.id}")

        for trader_id, trader in self.traders.items():
            await trader.initialize()
            await trader.connect_to_session(trading_session_uuid=self.trading_session.id)
        for trader in self.noise_traders:
            await trader.warm_up(starting_price=50, step=0.5, number_of_steps=10, number_of_warmup_orders=10)
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
