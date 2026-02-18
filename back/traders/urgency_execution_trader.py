# NOT CURRENTLY USED — Alternative execution trader by Alessio.
# Paired with SupervisorTrader: urgency controls pacing only,
# pricing and order logic stay deterministic (like InformedTrader).
# See llm_monitor.py + InformedTrader for the active approach.

import asyncio
from core.data_models import OrderType, TraderType, TradeDirection
from .base_trader import PausingTrader


class UrgencyExecutionTrader(PausingTrader):
    """
    Execution-only trader supervised by an external controller (e.g. LLM).

    Invariant:
    - Urgency affects ONLY execution pacing (wake-up timing).
    - Order size, pricing, and direction are unaffected by urgency.
    - In the final execution window, pacing reverts to the baseline
      informed-trader feasibility logic, ignoring urgency.
    """

    FINAL_WINDOW_SECONDS = 30  # revert to informed trader behavior

    def __init__(self, id: str, params: dict):
        super().__init__(trader_type=TraderType.INFORMED, id=id)

        self.params = params
        self.goal = self.initialize_inventory(params)
        self.order_multiplier = params.get("order_multiplier", 1)

        self.trade_direction = params["informed_trade_direction"]
        self.max_spread_ticks = params.get("max_spread_ticks", 5)
        self.step = params["step"]

        # urgency ∈ [0,1], controlled externally
        self.urgency = params.get("initial_urgency", 0.5)

        # pacing bounds
        self.min_sleep = params.get("min_sleep", 0.2)
        self.max_sleep = params.get("max_sleep", 3.0)

    # -------------------------
    # external control
    # -------------------------

    def set_urgency(self, urgency: float):
        #go no more than ten times slower or faster than InformedTrader
        self.urgency = min(max(urgency, 0.01), 10.0)

    # -------------------------
    # pacing logic
    # -------------------------

    def compute_next_sleep(self, remaining_time: float) -> float:
        """
        Compute next sleep time as a scaled version of the informed trader pacing.

        urgency = 1.0  -> baseline informed trader
        urgency = 0.5  -> sleep twice as long (slower)
        urgency = 2.0  -> sleep half as long (faster)
        """
        executed = sum(o["amount"] for o in self.filled_orders)

        baseline_sleep = self.calculate_sleep_time(
            remaining_time,
            executed,
            self.goal * self.order_multiplier,
        )

        # Scale sleep time inversely with urgency
        return baseline_sleep / max(self.urgency, 1e-6)

    # -------------------------
    # helpers
    # -------------------------

    def get_spread_ticks(self):
        bid = self.get_best_price(OrderType.BID)
        ask = self.get_best_price(OrderType.ASK)
        if bid is None or ask is None:
            return None
        return int((ask - bid) / self.step)

    def get_aggressive_price(self):
        if self.trade_direction == TradeDirection.BUY:
            return self.get_best_price(OrderType.ASK)
        else:
            return self.get_best_price(OrderType.BID)

    # -------------------------
    # execution
    # -------------------------

    async def execute_once(self):
        executed = sum(o["amount"] for o in self.filled_orders)

        if executed >= self.goal * self.order_multiplier:
            return

        price = self.get_aggressive_price()
        if price is None:
            return

        spread_ticks = self.get_spread_ticks()
        if spread_ticks is None or spread_ticks > self.max_spread_ticks:
            return  # market too wide → wait

        order_side = (
            OrderType.BID
            if self.trade_direction == TradeDirection.BUY
            else OrderType.ASK
        )

        await self.post_new_order(
            amount=self.order_multiplier,
            price=price,
            order_type=order_side,
        )

    # -------------------------
    # lifecycle
    # -------------------------

    async def run(self):
        while not self._stop_requested.is_set():
            try:
                await self.maybe_sleep()

                remaining_time = self.get_remaining_time()

                await self.execute_once()

                executed = sum(o["amount"] for o in self.filled_orders)
                if executed >= self.goal * self.order_multiplier:
                    for o in self.orders:
                        await self.send_cancel_order_request(o["id"])
                    break

                next_sleep = self.compute_next_sleep(remaining_time)
                await asyncio.sleep(next_sleep)

            except asyncio.CancelledError:
                break
            except Exception:
                break

        await self.cancel_all_outstanding_orders()
