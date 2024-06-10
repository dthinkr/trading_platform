import asyncio
from structures import OrderType, TraderType, TradeDirection
from main_platform.custom_logger import setup_custom_logger
from .base_trader import BaseTrader

logger = setup_custom_logger(__name__)


class InformedTrader(BaseTrader):
    def __init__(
        self,
        activity_frequency: int,
        settings: dict,
        settings_informed: dict,
        informed_time_plan: dict,
        informed_state: dict,
        get_signal_informed: callable,
        get_order_to_match: callable,
    ):
        super().__init__(trader_type=TraderType.INFORMED)
        self.activity_frequency = activity_frequency
        self.settings = settings
        self.settings_informed = settings_informed
        self.informed_time_plan = informed_time_plan
        self.informed_state = informed_state
        self.get_signal_informed = get_signal_informed
        self.get_order_to_match = get_order_to_match
        self.next_sleep_time = activity_frequency
        self.initialize_inventory(settings_informed)

    def initialize_inventory(self, settings_informed: dict) -> None:
        if settings_informed["direction"] == TradeDirection.BUY:
            self.shares = 0
            self.cash = 1e6
        elif settings_informed["direction"] == TradeDirection.SELL:
            self.shares = settings_informed["inv"]
            self.cash = 0
        else:
            raise ValueError(f"Invalid direction: {settings_informed['direction']}")

    def get_remaining_time(self) -> float:
        return self.settings_informed["total_seconds"] - self.get_elapsed_time()

    def get_best_opposite_price(self, order_side: OrderType) -> float:
        if order_side == OrderType.BID:
            asks = self.order_book.get("asks", [])
            if asks:
                return min(ask["x"] for ask in asks)
            else:
                return float("inf")
        elif order_side == OrderType.ASK:
            bids = self.order_book.get("bids", [])
            if bids:
                return max(bid["x"] for bid in bids)
            else:
                return 2000 # magic number

    def calculate_sleep_time(self, remaining_time: float) -> float:
        # buying case
        if self.settings_informed["direction"] == TradeDirection.BUY:
            if self.shares >= self.settings_informed["inv"]:
                # target reached
                return remaining_time
            else:
                # calculate time
                shares_needed = self.settings_informed["inv"] - self.shares
                return (
                    remaining_time
                    / max(shares_needed, 1)
                    * self.settings_informed["trade_intensity"]
                )

        # selling case
        elif self.settings_informed["direction"] == TradeDirection.SELL:
            if self.shares == 0:
                # all sold
                return remaining_time
            else:
                # calculate time
                return (
                    remaining_time
                    / max(self.shares, 1)
                    * self.settings_informed["trade_intensity"]
                )

        # default case
        return remaining_time

    async def act(self) -> None:
        remaining_time = self.get_remaining_time()
        if remaining_time <= 0:
            return

        trade_direction = self.settings_informed["direction"]
        order_side = (
            OrderType.BID if trade_direction == TradeDirection.BUY else OrderType.ASK
        )
        price = self.get_best_opposite_price(order_side)

        await self.post_new_order(1, price, order_side)

        self.next_sleep_time = self.calculate_sleep_time(remaining_time)

    async def run(self) -> None:
        while not self._stop_requested.is_set():
            try:
                await self.act()
                print(  f"Action: {'Buying' if self.settings_informed['direction'] == TradeDirection.BUY else 'Selling'}, "
                        f"Inventory: {self.shares} shares, "
                        f"Cash: ${self.cash:,.2f}, "
                        f"Sleep Time: {self.next_sleep_time:.2f} seconds"
                )

                await asyncio.sleep(self.next_sleep_time)
            except asyncio.CancelledError:
                logger.info("Run method cancelled, performing cleanup...")
                await self.clean_up()
                raise
            except Exception as e:
                logger.error(f"An error occurred in InformedTrader run loop: {e}")
                break
