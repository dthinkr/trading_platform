"""
LLM Monitor - Periodically adjusts a heuristic trader's parameters.

The LLM does NOT trade directly. It observes how the trader is performing
and tunes speed, order size, and aggression every few seconds.
"""
import asyncio
import os
import json
import httpx
import yaml
from typing import Dict, List
from datetime import datetime
from pathlib import Path

from utils.utils import setup_custom_logger

logger = setup_custom_logger(__name__)

SPEED_FACTORS = {
    "much_faster": 0.4,
    "faster": 0.7,
    "unchanged": 1.0,
    "slower": 1.4,
    "much_slower": 2.0,
}

MONITOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "adjust_parameters",
            "description": "Adjust the trading algorithm's parameters based on current performance and market conditions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "speed": {
                        "type": "string",
                        "enum": ["much_faster", "faster", "unchanged", "slower", "much_slower"],
                        "description": "Adjust trading speed. faster = shorter sleep between trades, slower = longer sleep.",
                    },
                    "order_size": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                        "description": "Number of shares per order (1-5).",
                    },
                    "aggression": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "0.0 = fully passive limit orders, 1.0 = fully aggressive market-crossing orders.",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Brief explanation of why these adjustments are being made.",
                    },
                },
                "required": ["speed", "order_size", "aggression", "reasoning"],
            },
        },
    }
]

DEFAULT_SYSTEM_PROMPT = """You are monitoring an algorithmic trading agent that is executing a buy/sell program by splitting orders over time. Your job is to adjust its parameters every few seconds based on performance.

You can adjust:
1. SPEED: How fast the agent trades. "faster" shortens the sleep between trades, "slower" lengthens it.
2. ORDER SIZE: How many shares per order (1-5).
3. AGGRESSION: 0.0 = passive limit orders only, 1.0 = aggressive market-crossing orders only.

Guidelines:
- If behind schedule, increase speed or aggression to catch up.
- If ahead of schedule, slow down to get better prices (lower VWAP for buyer, higher for seller).
- If the spread is wide, prefer passive orders (lower aggression) to avoid paying the spread.
- If the spread is tight, aggressive orders cost little extra.
- If recent trades moved the price against you (market impact), slow down and reduce order size.
- If recent trades had minimal impact, you can safely speed up.
- Use "unchanged" for speed if the current pace is appropriate."""


def _load_monitor_templates() -> Dict:
    yaml_path = Path(__file__).parent.parent / "config" / "agentic_prompts.yaml"
    if yaml_path.exists():
        with open(yaml_path) as f:
            data = yaml.safe_load(f) or {}
        return data.get("monitor_templates", {})
    return {}


class LLMMonitor:
    """Monitors a heuristic trader and adjusts its parameters via LLM."""

    def __init__(self, trader, params: dict):
        self.trader = trader
        self.api_key = params.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")
        self.model = params.get("monitor_model", "anthropic/claude-haiku-4.5")
        self.base_url = "https://openrouter.ai/api/v1"
        self.monitor_interval = params.get("monitor_interval", 7.0)
        self.decision_log: List[Dict] = []
        self._stop_requested = asyncio.Event()

        # Load prompt from template or use default
        templates = _load_monitor_templates()
        template_name = params.get("monitor_template", "informed_monitor_default")
        template = templates.get(template_name, {})
        self.system_prompt = template.get("prompt", DEFAULT_SYSTEM_PROMPT)

    # ---- state building ----

    def build_monitor_state(self) -> str:
        trader = self.trader
        elapsed = trader.get_elapsed_time()
        remaining = trader.get_remaining_time()

        # Current parameters
        sleep_time = trader.next_sleep_time
        speed_factor = trader.speed_factor
        order_mult = trader.order_multiplier
        passive = trader.use_passive_orders

        # Progress
        filled = len(trader.filled_orders)
        total_filled_amount = sum(o["amount"] for o in trader.filled_orders) if trader.filled_orders else 0
        goal = trader.goal * order_mult
        progress_pct = (total_filled_amount / goal * 100) if goal > 0 else 100
        target_pct = trader.target_progress * 100

        if progress_pct < target_pct - 5:
            pace = "BEHIND SCHEDULE"
        elif progress_pct > target_pct + 5:
            pace = "AHEAD OF SCHEDULE"
        else:
            pace = "ON TRACK"

        # Market
        from core.data_models import OrderType
        best_bid = trader.get_best_price(OrderType.BID)
        best_ask = trader.get_best_price(OrderType.ASK)
        spread = trader.calculate_spread(best_bid, best_ask)

        # VWAP (computed from filled orders)
        filled_value = sum(o.get("price", 0) * o.get("amount", 1) for o in trader.filled_orders) if trader.filled_orders else 0
        vwap = filled_value / total_filled_amount if total_filled_amount > 0 else 0

        # Recent fills and market impact
        recent_fills = trader.filled_orders[-10:] if trader.filled_orders else []
        fills_str = self._format_recent_fills(recent_fills, best_bid, best_ask)

        # Previous decisions
        decisions_str = self._format_decisions(self.decision_log[-5:])

        return f"""=== TIME ===
Elapsed: {int(elapsed)}s | Remaining: {int(remaining)}s

=== CURRENT PARAMETERS ===
Sleep interval: {sleep_time:.1f}s | Speed factor: {speed_factor:.2f} | Order size: {order_mult} | Passive orders: {passive}

=== PROGRESS ===
Filled: {total_filled_amount}/{goal} ({progress_pct:.0f}%) | Target: {target_pct:.0f}% | {pace}

=== MARKET ===
Bid: {best_bid} | Ask: {best_ask} | Spread: {spread} | VWAP: {vwap:.2f}

=== RECENT TRADES (last 10) ===
{fills_str}

=== PREVIOUS ADJUSTMENTS (last 5) ===
{decisions_str}"""

    def _format_recent_fills(self, fills: list, best_bid, best_ask) -> str:
        if not fills:
            return "No trades yet."
        lines = []
        for f in fills[-10:]:
            price = f.get("price", "?")
            amount = f.get("amount", 1)
            lines.append(f"  {amount}@{price}")
        return "\n".join(lines)

    def _format_decisions(self, decisions: list) -> str:
        if not decisions:
            return "No adjustments yet."
        lines = []
        for d in decisions:
            adj = d.get("adjustments", {})
            lines.append(
                f"  speed={adj.get('speed', '?')} size={adj.get('order_size', '?')} "
                f"aggr={adj.get('aggression', '?')} | {adj.get('reasoning', '')[:60]}"
            )
        return "\n".join(lines)

    # ---- LLM interaction ----

    async def call_llm(self, market_state: str) -> Dict:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"{market_state}\n\nDecide your parameter adjustments."},
        ]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "tools": MONITOR_TOOLS,
                        "tool_choice": "required",
                        "temperature": 0.3,
                        "max_tokens": 300,
                    },
                )

                if resp.status_code != 200:
                    return {"error": f"API {resp.status_code}"}

                data = resp.json()
                if "error" in data:
                    return {"error": data["error"]}

                tool_calls = data["choices"][0]["message"].get("tool_calls", [])
                if not tool_calls:
                    return {"error": "No tool call returned"}

                tc = tool_calls[0]
                try:
                    args = json.loads(tc["function"].get("arguments", "{}"))
                except json.JSONDecodeError:
                    args = {}
                return {"args": args}

        except Exception as e:
            logger.error(f"[Monitor:{self.trader.id}] LLM call error: {e}")
            return {"error": str(e)}

    # ---- parameter application ----

    def apply_adjustments(self, adjustments: Dict) -> None:
        trader = self.trader

        # Speed (sets speed_factor, applied inside calculate_sleep_time)
        speed = adjustments.get("speed", "unchanged")
        factor = SPEED_FACTORS.get(speed, 1.0)
        trader.speed_factor = max(0.2, min(3.0, trader.speed_factor * factor))

        # Order size
        new_size = adjustments.get("order_size", trader.order_multiplier)
        trader.order_multiplier = max(1, min(5, int(new_size)))

        # Aggression (0.0 = passive, 1.0 = aggressive)
        aggression = adjustments.get("aggression")
        if aggression is not None:
            trader.use_passive_orders = aggression < 0.7
            trader.informed_share_passive = max(0.0, min(1.0, 1.0 - aggression))
            trader.num_passive_to_keep = int(
                trader.informed_share_passive * trader.goal * trader.order_multiplier
            )

    # ---- main loop ----

    async def run(self) -> None:
        # Wait for trading to start
        while not hasattr(self.trader, "start_time") or self.trader.start_time is None:
            if self._stop_requested.is_set():
                return
            await asyncio.sleep(0.5)

        # Wait a bit before first adjustment to let the trader establish baseline
        await asyncio.sleep(self.monitor_interval)

        while not self._stop_requested.is_set():
            try:
                remaining = self.trader.get_remaining_time()
                if remaining < 3:
                    break

                state = self.build_monitor_state()

                if not self.api_key:
                    logger.warning(f"[Monitor:{self.trader.id}] No API key, skipping")
                    await asyncio.sleep(self.monitor_interval)
                    continue

                result = await self.call_llm(state)

                if "error" in result:
                    logger.error(f"[Monitor:{self.trader.id}] {result['error']}")
                else:
                    adjustments = result.get("args", {})
                    self.apply_adjustments(adjustments)
                    self.decision_log.append({
                        "timestamp": datetime.now().isoformat(),
                        "adjustments": adjustments,
                        "state_snapshot": {
                            "speed_factor": self.trader.speed_factor,
                            "sleep_time": self.trader.next_sleep_time,
                            "order_multiplier": self.trader.order_multiplier,
                            "use_passive": self.trader.use_passive_orders,
                        },
                    })
                    logger.info(
                        f"[Monitor:{self.trader.id}] Adjusted: "
                        f"speed={adjustments.get('speed')} size={adjustments.get('order_size')} "
                        f"aggr={adjustments.get('aggression')} | {adjustments.get('reasoning', '')[:80]}"
                    )

                await asyncio.sleep(self.monitor_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Monitor:{self.trader.id}] Error: {e}")
                await asyncio.sleep(self.monitor_interval)

        self._save_log()

    def stop(self):
        self._stop_requested.set()

    # ---- logging ----

    def _save_log(self):
        logs_dir = Path(__file__).parent.parent / "logs" / "monitor"
        logs_dir.mkdir(parents=True, exist_ok=True)

        market_id = getattr(self.trader, "trading_market_uuid", "unknown")
        filepath = logs_dir / f"{market_id}_{self.trader.id}.json"

        data = {
            "trader_id": self.trader.id,
            "model": self.model,
            "monitor_interval": self.monitor_interval,
            "total_decisions": len(self.decision_log),
            "decisions": self.decision_log,
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"[Monitor:{self.trader.id}] Saved {len(self.decision_log)} decisions to {filepath}")
