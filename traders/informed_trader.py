import asyncio
from structures import OrderType, TraderType, TradeDirection
from main_platform.custom_logger import setup_custom_logger
from .base_trader import BaseTrader

logger = setup_custom_logger(__name__)


class InformedTrader(BaseTrader):
    def __init__(
        self,
        activity_frequency: int,
        default_price: int,
        informed_edge: int,
        settings: dict,
        settings_informed: dict,
        informed_time_plan: dict,
        informed_state: dict,
        get_signal_informed: callable,
        get_order_to_match: callable,
    ):
        super().__init__(trader_type=TraderType.INFORMED)
        self.activity_frequency = activity_frequency
        self.default_price = default_price
        self.informed_edge = informed_edge
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
                    (remaining_time - 5)
                    / max(shares_needed, 1)
                    # * self.settings_informed["trade_intensity"]
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
                    # * self.settings_informed["trade_intensity"]
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
        
        top_bid = self.get_best_price(OrderType.BID)
        top_ask = self.get_best_price(OrderType.ASK)
        
        order_placed = False
        if order_side == OrderType.BID:
            proposed_price = top_bid + self.informed_edge
            if proposed_price >= top_ask:
                await self.post_new_order(1, proposed_price, order_side)
                order_placed = True
        else:  # OrderType.ASK
            proposed_price = top_ask - self.informed_edge
            if top_bid + self.informed_edge >= proposed_price:
                await self.post_new_order(1, proposed_price, order_side)
                order_placed = True

        self.next_sleep_time = self.calculate_sleep_time(remaining_time)

        # Print information about the trader's actions
        initial_inventory = self.settings_informed.get("inv", 0)
        if trade_direction == TradeDirection.BUY:
            sold_amount = self.shares
            to_sell_amount = initial_inventory - self.shares
        else:  # TradeDirection.SELL
            sold_amount = initial_inventory - self.shares
            to_sell_amount = self.shares

        print(f"Informed Trader: {'Buy' if trade_direction == TradeDirection.BUY else 'Sell'} | Traded: {sold_amount}/{initial_inventory} | Order: {'Y' if order_placed else 'N'}")
        print(f"Sleep: {self.next_sleep_time:.2f}s | Time left: {remaining_time:.2f}s")

    def get_best_price(self, order_side: OrderType) -> float:
        if order_side == OrderType.BID:
            bids = self.order_book.get("bids", [])
            return max(bid["x"] for bid in bids) if bids else self.default_price
        elif order_side == OrderType.ASK:
            asks = self.order_book.get("asks", [])
            return min(ask["x"] for ask in asks) if asks else float("inf")

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