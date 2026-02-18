# NOT CURRENTLY USED — Alternative supervisor pattern by Alessio.
# Simpler than LLMMonitor: only adjusts urgency (single dimension)
# via INCREASE_URGENCY / DECREASE_URGENCY / NO_CHANGE.
# Paired with UrgencyExecutionTrader for order execution.
# See llm_monitor.py for the active supervisor implementation.

from datetime import datetime
from core.data_models import TraderType
from typing import Dict
from .agentic_base import AgenticBase, TraderState


class SupervisorTrader(AgenticBase):
    """
    LLM supervisor that adjusts urgency of an execution trader.
    Does not place orders.
    """

    def __init__(self, id: str, params: dict, execution_trader):
        super().__init__(trader_type=TraderType.AGENTIC, id=id, params=params)
        self.execution_trader = execution_trader
        self.decision_multiplier = params.get("decision_multiplier", 2.0)

    # -------------------------
    # required abstract methods
    # -------------------------

    def get_effective_goal(self) -> int:
        return self.execution_trader.goal

    def get_effective_state(self) -> TraderState:
        return TraderState(
            goal=self.execution_trader.goal,
            goal_progress=sum(o["amount"] for o in self.execution_trader.filled_orders),
            cash=self.execution_trader.cash,
            shares=self.execution_trader.shares,
            orders=[],
            vwap=self.execution_trader.get_vwap(),
            pnl=0.0,
            avail_cash=0.0,
            avail_shares=0,
        )

    def is_goal_complete(self) -> bool:
        return (
            sum(o["amount"] for o in self.execution_trader.filled_orders)
            >= self.execution_trader.goal
        )

    # -------------------------
    # tools (override)
    # -------------------------

    @property
    def tools(self):
        return [
            {
                "type": "function",
                "function": {"name": "INCREASE_URGENCY", "description": "Increase execution speed"},
            },
            {
                "type": "function",
                "function": {"name": "DECREASE_URGENCY", "description": "Decrease execution speed"},
            },
            {
                "type": "function",
                "function": {"name": "NO_CHANGE", "description": "Keep execution speed unchanged"},
            },
        ]

    # -------------------------
    # decision application
    # -------------------------

    async def handle_decision(self, tool_name: str, args: Dict, mid_price: float) -> Dict:
        u_before = self.execution_trader.urgency

        if tool_name == "INCREASE_URGENCY":
            new_u = u_before * self.decision_multiplier
            new_u = min(new_u, 2.0)

        elif tool_name == "DECREASE_URGENCY":
            new_u = u_before / self.decision_multiplier
            new_u = max(new_u, 0.5)

        else:  # NO_CHANGE
            new_u = u_before

        self.execution_trader.set_urgency(new_u)

        decision = {
            "timestamp": datetime.now().isoformat(),
            "action": tool_name,
            "urgency_before": u_before,
            "urgency_after": self.execution_trader.urgency,
            "reasoning": args.get("reasoning", ""),
        }

        self.decision_log.append(decision)
        self._save_log()
        return decision
