import asyncio
from structures import OrderType, TraderType, TradeDirection
from main_platform.custom_logger import setup_custom_logger
from .base_trader import BaseTrader

logger = setup_custom_logger(__name__)


class InformedTrader(BaseTrader):
    def __init__(
        self,
        id: str,
        params: dict
    ):
        super().__init__(trader_type=TraderType.INFORMED, id=id)
        self.noise_activity_frequency = params.get("noise_activity_frequency", 1)
        self.default_price = params.get("default_price", 2000)
        self.informed_edge = params.get("informed_edge", 5)
        self.next_sleep_time = params.get("noise_activity_frequency", 1)
        self.initialize_inventory(params)

    def initialize_inventory(self, params: dict) -> None:
        print('informed intiialziing')
        if params["informed_trade_direction"] == TradeDirection.BUY:
            self.shares = 0
            self.cash = 1e6
        elif params["informed_trade_direction"] == TradeDirection.SELL:
            self.shares = 
            self.cash = 0
        else:
            raise ValueError(f"Invalid direction: {settings['direction']}")

    def get_remaining_time(self) -> float:
        return self.settings["total_seconds"] - self.get_elapsed_time()

    def calculate_sleep_time(self, remaining_time: float) -> float:
        # buying case
        if self.settings["informed_trade_direction"] == TradeDirection.BUY:
            if self.shares >= self.settings["inv"]:
                # target reached
                return remaining_time
            else:
                # calculate time
                shares_needed = self.settings["inv"] - self.shares
                return (
                    (remaining_time - 5)
                    / max(shares_needed, 1)
                )

        # selling case
        elif self.settings["informed_trade_direction"] == TradeDirection.SELL:
            if self.shares == 0:
                # all sold
                return remaining_time
            else:
                # calculate time
                return (
                    remaining_time
                    / max(self.shares, 1)
                )

        # default case
        return remaining_time

    async def act(self) -> None:
        remaining_time = self.get_remaining_time()
        if remaining_time <= 0:
            return

        trade_direction = self.settings["informed_trade_direction"]
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
        initial_inventory = self.settings.get("inv", 0)
        if trade_direction == TradeDirection.BUY:
            sold_amount = self.shares
            to_sell_amount = initial_inventory - self.shares
        else:  # TradeDirection.SELL
            sold_amount = initial_inventory - self.shares
            to_sell_amount = self.shares

        # print(f"Informed Trader: {'Buy' if trade_direction == TradeDirection.BUY else 'Sell'} | Traded: {sold_amount}/{initial_inventory} | Order: {'Y' if order_placed else 'N'}")
        # print(f"Sleep: {self.next_sleep_time:.2f}s | Time left: {remaining_time:.2f}s")

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
                remaining_time = self.get_remaining_time()
                if remaining_time <= 0:
                    # logger.info("Trading session has ended. Stopping InformedTrader.")
                    break

                # await self.act()
                # print(f"Action: {'Buying' if self.settings['direction'] == TradeDirection.BUY else 'Selling'}, "
                #       f"Inventory: {self.shares} shares, "
                #       f"Cash: ${self.cash:,.2f}, "
                #       f"Sleep Time: {self.next_sleep_time:.2f} seconds")

                await asyncio.sleep(min(self.next_sleep_time, remaining_time))
            except asyncio.CancelledError:
                logger.info("Run method cancelled, performing cleanup...")
                break
            except Exception as e:
                logger.error(f"An error occurred in InformedTrader run loop: {e}")
                break

        logger.info("InformedTrader has stopped.")
