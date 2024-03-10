from .base_trader import BaseTrader
import asyncio
from structures import OrderType, TraderType
from main_platform.custom_logger import setup_custom_logger
from datetime import datetime, timezone

logger = setup_custom_logger(__name__)

class InformedTrader(BaseTrader):

    def __init__(self, activity_frequency: int, settings: dict, settings_informed: dict, informed_state: dict, trading_day_duration: int,
                 get_informed_time_plan: callable, get_signal_informed: callable, get_informed_order: callable):
        super().__init__(trader_type=TraderType.INFORMED)
        self.activity_frequency = activity_frequency
        self.settings = settings
        self.settings_informed = settings_informed
        self.informed_state = informed_state
        self.trading_day_duration = trading_day_duration
        self.get_informed_time_plan = get_informed_time_plan
        self.get_signal_informed = get_signal_informed
        self.time_plan = self.get_informed_time_plan(self.settings_informed, self.settings)
        self.step_frequency = self.trading_day_duration * 60 / (self.settings['n_updates_session'] + self.settings['warmup_periods'])
        
        """"TODO REQUIRES A GLOBAL REFACTORING OF STEP-TIME MECHANISM.
                 MACHINE AGENTS CAN SHARE THE INTERNAL CLOCK OF THE TRADING PLATFORM
        """
        self.current_step = 0
        
    @property
    def current_time(self) -> datetime:
        return datetime.now(timezone.utc)
    
    def get_best_bid_and_ask(self) -> tuple:
        best_bid = None
        best_ask = None

        for order in self.active_orders:
            if order['order_type'] == 'bid':
                if best_bid is None or order['price'] > best_bid['price']:
                    best_bid = order
            elif order['order_type'] == 'ask':
                if best_ask is None or order['price'] < best_ask['price']:
                    best_ask = order

        return best_bid, best_ask

    def get_informed_order(self, signal_informed: list, settings_informed: dict) -> dict:
        action, num_shares = signal_informed[0], signal_informed[1]
        best_bid, best_ask = self.get_best_bid_and_ask()
        order = {}
        if action == 1: 
            if settings_informed['inv'] > 0:
                price = best_ask['price'] - 1 if best_ask else self.settings['initial_price']
                order = {'bid': {price: [num_shares]}, 'ask': {}}
            elif settings_informed['inv'] < 0:
                price = best_bid['price'] + 1 if best_bid else self.settings['initial_price']
                order = {'bid': {}, 'ask': {price: [num_shares]}}

        return order

    async def act(self):
        signal = self.get_signal_informed(self.informed_state, self.settings_informed, self.current_step)
        order_dict = self.get_informed_order(signal, self.settings_informed)

        for order_type, orders in order_dict.items():
            for price, amounts in orders.items():
                for amount in amounts:
                    msg = f"""POSTED {order_type} AT {price} AMOUNT {amount} 
                        AT STEP {self.current_step} AT TIME {self.current_time.strftime('%H:%M:%S')}"""
                    if order_type == 'bid':
                        await self.post_new_order(amount, price, OrderType.BID)
                        logger.critical(msg)
                    elif order_type == 'ask':
                        await self.post_new_order(amount, price, OrderType.ASK)
                        logger.critical(msg)

    async def run(self):
        while not self._stop_requested.is_set():
            try:
                await self.act()
                await asyncio.sleep(self.step_frequency)
                self.current_step += 1
            except asyncio.CancelledError:
                logger.info('Run method cancelled, performing cleanup of informed trader...')
                await self.clean_up()
                raise
            except Exception as e:
                logger.error(f"An error occurred in InformedTrader run loop: {e}")
                break