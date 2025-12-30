"""
Agentic Trading System - Goal-based trading with VWAP optimization.

Classes:
- AgenticBase: Shared LLM logic (prompts, API calls, market state)
- AgenticTrader: Autonomous trader that executes orders
- AgenticAdvisor: Advisor that helps humans without executing

llm behavior notes:
- llm tends to be aggressive (cross spread) when spread is wide, thinking passive orders won't fill
- llm is more passive (below best ask) when spread is tight

"""
import asyncio
import os
import json
import httpx
from typing import Dict, Any, List
from datetime import datetime
from abc import abstractmethod

from core.data_models import OrderType, TraderType
from .base_trader import PausingTrader
from utils.utils import setup_custom_logger

logger = setup_custom_logger(__name__)


ACTION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "place_order",
            "description": "Place a limit order for 1 share.",
            "parameters": {
                "type": "object",
                "properties": {
                    "price": {"type": "integer", "description": "Limit price for the order"},
                    "side": {"type": "string", "enum": ["buy", "sell"], "description": "Order side (only for speculators)"}
                },
                "required": ["price"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_order",
            "description": "Cancel an existing order by ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "Order ID to cancel"}
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "hold",
            "description": "Take no action this turn. Use when waiting for better prices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {"type": "string", "description": "Why you chose to hold"}
                },
                "required": ["reasoning"]
            }
        }
    }
]


# Tools for informed traders (no side parameter needed)
INFORMED_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "place_order",
            "description": "Place a limit order for 1 share.",
            "parameters": {
                "type": "object",
                "properties": {
                    "price": {"type": "integer", "description": "Limit price for the order"},
                    "reasoning": {"type": "string", "description": "Brief explanation for this price choice"}
                },
                "required": ["price"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_order",
            "description": "Cancel an existing order by ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "Order ID to cancel"},
                    "reasoning": {"type": "string", "description": "Brief explanation for cancelling"}
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "hold",
            "description": "Take no action this turn. Use when waiting for better prices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {"type": "string", "description": "Why you chose to hold"}
                },
                "required": ["reasoning"]
            }
        }
    }
]


# Tools for speculators (includes side parameter)
SPECULATOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "place_order",
            "description": "Place a limit order for 1 share. Specify side as 'buy' or 'sell'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "price": {"type": "integer", "description": "Limit price for the order"},
                    "side": {"type": "string", "enum": ["buy", "sell"], "description": "Order side: 'buy' or 'sell'"},
                    "reasoning": {"type": "string", "description": "Brief explanation for this trade"}
                },
                "required": ["price", "side"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_order",
            "description": "Cancel an existing order by ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "Order ID to cancel"},
                    "reasoning": {"type": "string", "description": "Brief explanation for cancelling"}
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "hold",
            "description": "Take no action this turn. Use when waiting for better prices or market conditions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {"type": "string", "description": "Why you chose to hold"}
                },
                "required": ["reasoning"]
            }
        }
    }
]


class AgenticBase(PausingTrader):
    """Base class for agentic traders/advisors with shared LLM logic."""

    def __init__(self, trader_type: TraderType, id: str, params: dict):
        super().__init__(trader_type=trader_type, id=id)
        self.params = params

        # LLM config
        self.api_key = params.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")
        self.model = params.get("agentic_model", "anthropic/claude-haiku-4.5")
        self.base_url = "https://openrouter.ai/api/v1"

        # Decision timing
        self.decision_interval = params.get("decision_interval", 10)
        self.last_decision_time = 0

        # Reward formula parameters
        self.buy_target_price = params.get("buy_target_price", 110)
        self.sell_target_price = params.get("sell_target_price", 90)
        self.penalty_multiplier_buy = params.get("penalty_multiplier_buy", 1.5)
        self.penalty_multiplier_sell = params.get("penalty_multiplier_sell", 0.5)

        # Tracking
        self.decision_log: List[Dict] = []
        self.price_history: List[float] = []
        self.initial_mid_price: float = None

    async def initialize(self):
        await super().initialize()
        if not self.api_key:
            logger.warning(f"[{self.id}] No OpenRouter API key configured.")

    @abstractmethod
    def get_effective_goal(self) -> int:
        """Get the goal to optimize for."""
        pass

    @abstractmethod
    def get_effective_state(self) -> Dict:
        """Get the state (goal, progress, cash, shares, orders) to use in prompts."""
        pass

    @abstractmethod
    def is_goal_complete(self) -> bool:
        """Check if the goal is complete."""
        pass

    @abstractmethod
    async def handle_decision(self, tool_name: str, args: Dict, mid_price: float) -> Dict:
        """Handle the LLM's decision (execute or advise)."""
        pass

    def build_system_prompt(self, is_advisor: bool = False) -> str:
        goal = self.get_effective_goal()
        
        prefix = "You are an AI ADVISOR helping a human trader. Suggest actions they should take.\n\n" if is_advisor else ""
        
        if goal > 0:
            return f"""{prefix}You are a trading agent with a BUYING goal.

YOUR OBJECTIVE: Buy {abs(goal)} shares at the lowest average price (VWAP).
CONSTRAINT: You can only place 1 share per order.

REWARD FORMULA:
- Reward = ({self.buy_target_price} - Your_VWAP) × 10
- VWAP = Total_Spent / Shares_Bought
- WARNING: Incomplete trades are penalized at {self.penalty_multiplier_buy}× mid price

STRATEGY TIPS:
- Place BUY orders at or below the best ask to get filled
- Lower buy prices = better VWAP = higher reward
- But don't wait too long - incomplete goal is heavily penalized
- Balance between getting good prices and completing your goal

You can only place BUY orders for 1 share at a time (the system knows your goal direction)."""

        elif goal < 0:
            return f"""{prefix}You are a trading agent with a SELLING goal.

YOUR OBJECTIVE: Sell {abs(goal)} shares at the highest average price (VWAP).
CONSTRAINT: You can only place 1 share per order.

REWARD FORMULA:
- Reward = (Your_VWAP - {self.sell_target_price}) × 10
- VWAP = Total_Received / Shares_Sold
- WARNING: Incomplete trades are penalized at {self.penalty_multiplier_sell}× mid price

STRATEGY TIPS:
- Place SELL orders at or above the best bid to get filled
- Higher sell prices = better VWAP = higher reward
- But don't wait too long - incomplete goal is heavily penalized
- Balance between getting good prices and completing your goal

You can only place SELL orders for 1 share at a time (the system knows your goal direction)."""

        else:
            return f"""{prefix}You are a SPECULATOR trading agent with no specific goal.

YOUR OBJECTIVE: Maximize profit (PnL) by buying low and selling high.
CONSTRAINT: You can only place 1 share per order.

PnL FORMULA:
- PnL = (Current_Mid_Price × Net_Shares) - Total_Cost
- Buy low, sell high to increase PnL
- Your PnL updates in real-time based on market prices

STRATEGY TIPS:
- Buy when you expect prices to rise (place BUY orders below best ask)
- Sell when you expect prices to fall (place SELL orders above best bid)
- Watch order book imbalance: + means buying pressure (prices may rise)
- Watch price trend: UP means momentum is bullish
- Be careful with inventory - don't accumulate too many shares in one direction
- You must specify 'side' as 'buy' or 'sell' when placing orders

You can place both BUY and SELL orders for 1 share at a time."""

    def get_time_info(self) -> Dict:
        """Get time information from base trader and params."""
        elapsed = self.get_elapsed_time()
        duration_minutes = self.params.get("trading_day_duration", 5)
        duration_seconds = duration_minutes * 60
        remaining = max(0, duration_seconds - elapsed)
        
        return {
            "elapsed": elapsed,
            "remaining": remaining,
            "duration": duration_seconds,
            "progress_pct": min(100, (elapsed / duration_seconds) * 100) if duration_seconds > 0 else 0,
        }

    def build_market_state(self, mid_price: float, mode_label: str = "") -> str:
        if not self.order_book:
            return "Market data not available."

        bids = self.order_book.get("bids", [])[:5]
        asks = self.order_book.get("asks", [])[:5]

        best_bid = bids[0]["x"] if bids else None
        best_ask = asks[0]["x"] if asks else None
        spread = (best_ask - best_bid) if (best_bid and best_ask) else None

        bid_vol = sum(l["y"] for l in bids)
        ask_vol = sum(l["y"] for l in asks)
        total = bid_vol + ask_vol
        imbalance = (bid_vol - ask_vol) / total if total > 0 else 0

        trend = "unknown"
        if len(self.price_history) >= 5:
            recent = sum(self.price_history[-5:]) / 5
            older = sum(self.price_history[-10:-5]) / 5 if len(self.price_history) >= 10 else recent
            if recent > older * 1.01:
                trend = "UP ↑"
            elif recent < older * 0.99:
                trend = "DOWN ↓"
            else:
                trend = "FLAT →"

        # Get effective state
        state = self.get_effective_state()
        goal = state["goal"]
        goal_progress = state["goal_progress"]
        cash = state["cash"]
        shares = state["shares"]
        orders = state["orders"]
        vwap = state["vwap"]
        avail_cash = state["avail_cash"]
        avail_shares = state["avail_shares"]
        pnl = state.get("pnl", 0)

        orders_str = "None"
        if orders:
            orders_str = ", ".join(f"{o['id']}: {o['amount']}@{o['price']}" for o in orders)

        # Build goal/progress section based on whether this is informed or speculator
        if goal != 0:
            # Informed trader - show goal progress with estimated reward
            goal_size = abs(goal)
            action_type = "BUY" if goal > 0 else "SELL"
            completed = goal_progress
            remaining = max(0, goal_size - completed)
            
            # Calculate estimated reward (includes penalty for incomplete trades)
            estimated_reward = self.get_current_reward(mid_price)
            
            goal_section = f"""=== GOAL PROGRESS {mode_label} ===
Goal: {action_type} {goal_size} shares
Completed: {completed}/{goal_size} ({remaining} remaining)
Current VWAP: {f'{vwap:.2f}' if vwap > 0 else 'N/A'}
Estimated Reward: {estimated_reward:.2f} (includes penalty for {remaining} incomplete)"""
        else:
            # Speculator - show PnL
            goal_section = f"""=== PERFORMANCE {mode_label} ===
Role: SPECULATOR (no goal, maximize PnL)
Current PnL: {pnl:.2f}
Net Position: {shares} shares"""

        # Get time info
        time_info = self.get_time_info()
        elapsed_min = int(time_info["elapsed"] // 60)
        elapsed_sec = int(time_info["elapsed"] % 60)
        remaining_min = int(time_info["remaining"] // 60)
        remaining_sec = int(time_info["remaining"] % 60)
        progress_pct = time_info["progress_pct"]

        # Calculate valid price range
        min_price, max_price = self._get_valid_price_range()

        return f"""=== TIME ===
Elapsed: {elapsed_min}:{elapsed_sec:02d} | Remaining: {remaining_min}:{remaining_sec:02d} ({progress_pct:.0f}% complete)

=== MARKET STATE ===
Best Bid: {best_bid} | Best Ask: {best_ask} | Spread: {spread}
Mid Price: {mid_price:.1f}
Valid Price Range: {min_price} to {max_price} (orders outside this range will be rejected)
Imbalance: {imbalance:+.2f} (+ = buying pressure)
Trend: {trend}

Order Book:
  Bids: {[(b['x'], b['y']) for b in bids]}
  Asks: {[(a['x'], a['y']) for a in asks]}

{goal_section}

=== RESOURCES {mode_label} ===
Cash: {cash:.0f} (available: {avail_cash:.0f})
Shares: {shares} (available: {avail_shares})

=== ACTIVE ORDERS {mode_label} ===
{orders_str}

{self._build_price_options_section(mid_price, goal, goal_progress, vwap)}

{self._build_recent_decisions_section()}"""

    async def call_llm(self, system_prompt: str, market_state: str) -> Dict:
        """Make LLM API call and return parsed tool call."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{market_state}\n\nDecide your action."}
        ]

        # Use appropriate tools based on goal
        goal = self.get_effective_goal()
        tools = SPECULATOR_TOOLS if goal == 0 else INFORMED_TOOLS

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
                        "tools": tools,
                        "tool_choice": "required",
                        "temperature": 0.3,
                        "max_tokens": 300
                    }
                )

                if resp.status_code != 200:
                    logger.error(f"[{self.id}] API error: {resp.status_code}")
                    return {"error": f"API {resp.status_code}"}

                data = resp.json()
                if "error" in data:
                    return {"error": data["error"]}

                msg = data["choices"][0]["message"]
                tool_calls = msg.get("tool_calls", [])

                if not tool_calls:
                    return {"tool_name": "hold", "args": {"reasoning": "No tool call"}}

                tc = tool_calls[0]
                tool_name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"].get("arguments", "{}"))
                except json.JSONDecodeError:
                    args = {}

                return {"tool_name": tool_name, "args": args}

        except Exception as e:
            logger.error(f"[{self.id}] LLM call error: {e}")
            return {"error": str(e)}

    async def make_decision(self) -> Dict:
        if not self.api_key:
            logger.warning(f"[{self.id}] No API key!")
            return {"error": "No API key"}

        bids = self.order_book.get("bids", [])
        asks = self.order_book.get("asks", [])
        if not bids or not asks:
            logger.debug(f"[{self.id}] No market data! bids={len(bids)}, asks={len(asks)}")
            return {"error": "No market data"}

        mid_price = (bids[0]["x"] + asks[0]["x"]) / 2

        if self.initial_mid_price is None:
            self.initial_mid_price = mid_price

        system_prompt = self.build_system_prompt(is_advisor=isinstance(self, AgenticAdvisor))
        market_state = self.build_market_state(mid_price, mode_label=self._get_mode_label())

        llm_result = await self.call_llm(system_prompt, market_state)
        
        if "error" in llm_result:
            logger.error(f"[{self.id}] LLM error: {llm_result['error']}")
            return llm_result

        tool_name = llm_result["tool_name"]
        args = llm_result["args"]
        logger.info(f"[{self.id}] LLM decided: {tool_name} {args}")

        return await self.handle_decision(tool_name, args, mid_price)

    def _get_mode_label(self) -> str:
        return ""

    def _get_valid_price_range(self) -> tuple:
        """Get valid price range based on current order book (best_bid - 5 to best_ask + 5)."""
        if not self.order_book:
            return (0, float('inf'))
        
        bids = self.order_book.get("bids", [])
        asks = self.order_book.get("asks", [])
        
        best_bid = bids[0]["x"] if bids else 95  # Default if no bids
        best_ask = asks[0]["x"] if asks else 105  # Default if no asks
        
        min_price = best_bid - 5
        max_price = best_ask + 5
        
        return (min_price, max_price)

    def _build_recent_decisions_section(self) -> str:
        """Build a summary of recent decisions with outcomes."""
        if not self.decision_log:
            return "=== RECENT DECISIONS ===\nNo decisions yet."
        
        # Get last 5 decisions
        recent = self.decision_log[-5:]
        lines = ["=== RECENT DECISIONS (last 5) ==="]
        
        for i, decision in enumerate(reversed(recent)):
            action = decision.get("action", "unknown")
            args = decision.get("args", {})
            result = decision.get("result", {})
            
            if action == "place_order":
                price = args.get("price", "?")
                side = result.get("side", "buy" if self.get_effective_goal() > 0 else "sell")
                order_id = result.get("order_id", "")
                
                # Check if this order is still pending or was filled
                if result.get("success"):
                    # Check if order_id is still in active orders
                    is_pending = any(o.get("id") == order_id for o in self.orders)
                    if is_pending:
                        status = "PENDING"
                    else:
                        status = "FILLED"
                else:
                    status = f"FAILED: {result.get('error', 'unknown')}"
                
                lines.append(f"  {i+1}. {side.upper()} @ {price} -> {status}")
                
            elif action == "cancel_order":
                order_id = args.get("order_id", "?")
                if result.get("success"):
                    lines.append(f"  {i+1}. CANCEL {order_id} -> SUCCESS")
                else:
                    lines.append(f"  {i+1}. CANCEL {order_id} -> FAILED")
                    
            elif action == "hold":
                reason = args.get("reasoning", "")[:30]
                lines.append(f"  {i+1}. HOLD ({reason})")
        
        return "\n".join(lines)

    def _build_price_options_section(self, mid_price: float, goal: int, goal_progress: int, current_vwap: float) -> str:
        """Show estimated VWAP/PnL for different price options."""
        min_price, max_price = self._get_valid_price_range()
        
        # Generate 5 price options around mid price
        prices = [int(mid_price) - 2, int(mid_price) - 1, int(mid_price), int(mid_price) + 1, int(mid_price) + 2]
        prices = [p for p in prices if min_price <= p <= max_price]
        
        if goal == 0:
            # Speculator: show PnL impact for buy/sell at each price
            lines = ["=== PRICE OPTIONS (PnL if mid moves ±2) ==="]
            for price in prices:
                buy_pnl = (mid_price + 2) - price  # profit if price rises
                sell_pnl = price - (mid_price - 2)  # profit if price falls
                lines.append(f"  BUY @ {price}: +{buy_pnl:.0f} if mid→{mid_price+2:.0f}")
                lines.append(f"  SELL @ {price}: +{sell_pnl:.0f} if mid→{mid_price-2:.0f}")
            return "\n".join(lines)
        
        # Informed trader: show VWAP and reward
        lines = ["=== PRICE OPTIONS (estimated if filled) ==="]
        
        goal_size = abs(goal)
        completed = abs(goal_progress)
        
        for price in prices:
            # Calculate what VWAP would be if this order fills
            if completed > 0 and current_vwap > 0:
                new_vwap = (current_vwap * completed + price) / (completed + 1)
            else:
                new_vwap = price
            
            # Calculate reward with this new VWAP
            remaining_after = max(0, goal_size - completed - 1)
            
            if goal > 0:  # Buyer
                if completed + 1 > 0:
                    expenditure = new_vwap * (completed + 1)
                else:
                    expenditure = 0
                penalty = remaining_after * mid_price * self.penalty_multiplier_buy
                penalized_vwap = (expenditure + penalty) / goal_size
                reward = self.buy_target_price - penalized_vwap
            else:  # Seller
                if completed + 1 > 0:
                    revenue = new_vwap * (completed + 1)
                else:
                    revenue = 0
                penalty = remaining_after * mid_price * self.penalty_multiplier_sell
                penalized_vwap = (revenue + penalty) / goal_size
                reward = penalized_vwap - self.sell_target_price
            
            lines.append(f"  Price {price}: VWAP={new_vwap:.1f}, Reward={reward:.1f}")
        
        return "\n".join(lines)

    async def on_book_updated(self, data: Dict[str, Any]):
        await super().on_book_updated(data)
        if self.order_book:
            bids = self.order_book.get("bids", [])
            asks = self.order_book.get("asks", [])
            if bids and asks:
                mid = (bids[0]["x"] + asks[0]["x"]) / 2
                self.price_history.append(mid)
                if len(self.price_history) > 100:
                    self.price_history = self.price_history[-100:]

    async def act(self) -> None:
        if not self.order_book:
            return

        if self.is_goal_complete():
            return

        now = asyncio.get_event_loop().time()
        if now - self.last_decision_time < self.decision_interval:
            return

        self.last_decision_time = now
        await self.make_decision()

    async def run(self) -> None:
        logger.info(f"[{self.id}] Starting run loop")
        while not self._stop_requested.is_set():
            try:
                await self.maybe_sleep()
                await self.act()
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                await self.clean_up()
                raise
            except Exception as e:
                logger.error(f"[{self.id}] Run error: {e}")
                await asyncio.sleep(5)

    async def post_processing_server_message(self, json_message: Dict[str, Any]):
        pass


class AgenticTrader(AgenticBase):
    """Autonomous trader that executes orders based on LLM decisions."""

    def __init__(self, id: str, params: dict):
        super().__init__(trader_type=TraderType.AGENTIC, id=id, params=params)

        # Goal: positive = buy, negative = sell
        self.goal = params.get("goal", 0)

        # Resources
        self.cash = params.get("initial_cash", 10000)
        self.shares = params.get("initial_shares", 0)
        self.initial_cash = self.cash
        self.initial_shares = self.shares

    def get_effective_goal(self) -> int:
        return self.goal

    def get_effective_state(self) -> Dict:
        return {
            "goal": self.goal,
            "goal_progress": self.goal_progress,  # From base class
            "cash": self.cash,
            "shares": self.shares,
            "orders": self.orders,
            "vwap": self.get_vwap(),  # Use platform's VWAP from base class
            "pnl": self.get_current_pnl(),  # From base class
            "avail_cash": self.get_available_cash(),
            "avail_shares": self.get_available_shares(),
        }

    def is_goal_complete(self) -> bool:
        # Speculators never "complete" - they keep trading
        if self.goal == 0:
            return False
        return abs(self.goal_progress) >= abs(self.goal)

    def get_current_reward(self, mid_price: float) -> float:
        """
        Calculate estimated reward for agentic trader.
        Unlike the shared function, this returns raw values (can be negative)
        so the agent can see the true impact of incomplete goals.
        """
        if self.goal == 0:
            # Speculator: reward is PnL
            return self.get_current_pnl()
        
        # Informed trader: VWAP-based reward with penalty
        goal_size = abs(self.goal)
        completed = abs(self.goal_progress)
        remaining = max(0, goal_size - completed)
        current_vwap = self.get_vwap()
        
        if self.goal > 0:  # Buyer
            # Penalize incomplete trades at higher price (1.5x mid)
            if completed > 0:
                expenditure = current_vwap * completed
            else:
                expenditure = 0
            penalty_cost = remaining * mid_price * self.penalty_multiplier_buy
            total_expenditure = expenditure + penalty_cost
            penalized_vwap = total_expenditure / goal_size if goal_size > 0 else 0
            
            # Reward formula: (target - penalized_vwap) - can be negative
            reward = (self.buy_target_price - penalized_vwap)
            
        else:  # Seller
            # Penalize incomplete trades at lower price (0.5x mid)
            if completed > 0:
                revenue = current_vwap * completed
            else:
                revenue = 0
            penalty_revenue = remaining * mid_price * self.penalty_multiplier_sell
            total_revenue = revenue + penalty_revenue
            penalized_vwap = total_revenue / goal_size if goal_size > 0 else 0
            
            # Reward formula: (penalized_vwap - target) - can be negative
            reward = (penalized_vwap - self.sell_target_price)
        
        return reward

    async def handle_decision(self, tool_name: str, args: Dict, mid_price: float) -> Dict:
        """Execute the action."""
        result = await self.execute_action(tool_name, args)

        decision = {
            "timestamp": datetime.now().isoformat(),
            "action": tool_name,
            "args": args,
            "result": result,
            "goal_progress": self.goal_progress,
            "current_vwap": self.get_vwap(),  # Platform's VWAP
            "current_reward": self.get_current_reward(mid_price)
        }
        self.decision_log.append(decision)
        return decision

    async def execute_action(self, tool_name: str, args: Dict) -> Dict:
        if tool_name == "place_order":
            price = args.get("price", 0)
            qty = 1  # Fixed to 1 share per order

            # Validate price is within allowed range (best_bid - 5 to best_ask + 5)
            min_price, max_price = self._get_valid_price_range()
            if price < min_price or price > max_price:
                return {"error": f"Price {price} out of range. Must be between {min_price} and {max_price}"}

            if self.goal > 0:
                # Informed buyer
                order_type = OrderType.BID
                side = "buy"
                avail = self.get_available_cash()
                if price * qty > avail:
                    return {"error": f"Insufficient cash. Need {price*qty}, have {avail}"}
            elif self.goal < 0:
                # Informed seller
                order_type = OrderType.ASK
                side = "sell"
                avail = self.get_available_shares()
                if qty > avail:
                    return {"error": f"Insufficient shares. Need {qty}, have {avail}"}
            else:
                # Speculator - must specify side
                side = args.get("side", "").lower()
                if side not in ["buy", "sell"]:
                    return {"error": "Speculator must specify 'side' as 'buy' or 'sell'"}
                
                if side == "buy":
                    order_type = OrderType.BID
                    avail = self.get_available_cash()
                    if price * qty > avail:
                        return {"error": f"Insufficient cash. Need {price*qty}, have {avail}"}
                else:
                    order_type = OrderType.ASK
                    avail = self.get_available_shares()
                    if qty > avail:
                        return {"error": f"Insufficient shares. Need {qty}, have {avail}"}

            order_id = await self.post_new_order(qty, price, order_type)
            if order_id:
                logger.info(f"[{self.id}] Placed {side} {qty}@{price}, id={order_id}")
                return {"success": True, "order_id": order_id, "side": side}
            return {"error": "Order failed"}

        elif tool_name == "cancel_order":
            order_id = args.get("order_id", "")
            success = await self.send_cancel_order_request(order_id)
            if success:
                logger.info(f"[{self.id}] Cancelled {order_id}")
                return {"success": True}
            return {"error": f"Cancel failed for {order_id}"}

        elif tool_name == "hold":
            reason = args.get("reasoning", "")[:50]
            logger.info(f"[{self.id}] Hold: {reason}")
            return {"success": True, "action": "hold"}

        return {"error": f"Unknown action: {tool_name}"}

    def get_performance_summary(self) -> Dict[str, Any]:
        mid = self.price_history[-1] if self.price_history else 100
        
        if self.goal == 0:
            # Speculator summary
            return {
                "role": "speculator",
                "goal": 0,
                "pnl": self.get_current_pnl(),
                "decisions": len(self.decision_log),
                "cash": self.cash,
                "shares": self.shares,
                "net_position": self.shares - self.initial_shares,
            }
        else:
            # Informed trader summary
            return {
                "role": "informed",
                "goal": self.goal,
                "goal_progress": self.goal_progress,
                "goal_complete": self.is_goal_complete(),
                "vwap": self.get_vwap(),
                "reward": self.get_current_reward(mid),
                "decisions": len(self.decision_log),
                "cash": self.cash,
                "shares": self.shares,
            }


class AgenticAdvisor(AgenticBase):
    """Advisor that helps humans without executing trades."""

    def __init__(self, id: str, params: dict):
        super().__init__(trader_type=TraderType.AGENTIC, id=id, params=params)

        # Human reference (set by trader_manager when human joins)
        self.human_trader_ref = None
        self.advice_for_human_id = params.get("advice_for_human_id", None)
        self.current_advice: Dict = None

    def set_human_trader_ref(self, human_trader):
        """Link this advisor to a human trader."""
        self.human_trader_ref = human_trader
        logger.info(f"[{self.id}] Linked to human trader: {human_trader.id}")

    def get_effective_goal(self) -> int:
        if self.human_trader_ref:
            return getattr(self.human_trader_ref, 'goal', 0) or 0
        return 0

    def get_effective_state(self) -> Dict:
        if not self.human_trader_ref:
            return {
                "goal": 0, "goal_progress": 0, "cash": 0, "shares": 0,
                "orders": [], "vwap": 0, "pnl": 0, "avail_cash": 0, "avail_shares": 0
            }

        human = self.human_trader_ref
        goal = getattr(human, 'goal', 0) or 0
        goal_progress = getattr(human, 'goal_progress', 0)
        cash = getattr(human, 'cash', 0)
        shares = getattr(human, 'shares', 0)
        orders = getattr(human, 'orders', [])
        vwap = getattr(human, 'get_vwap', lambda: 0)()
        pnl = getattr(human, 'get_current_pnl', lambda: 0)()

        # Calculate available resources
        avail_cash = cash
        avail_shares = shares
        for o in orders:
            if o.get('order_type') == 1:  # BID
                avail_cash -= o.get('price', 0) * o.get('amount', 0)
            else:  # ASK
                avail_shares -= o.get('amount', 0)

        return {
            "goal": goal,
            "goal_progress": goal_progress,
            "cash": cash,
            "shares": shares,
            "orders": orders,
            "vwap": vwap,
            "pnl": pnl,
            "avail_cash": avail_cash,
            "avail_shares": avail_shares,
        }

    def is_goal_complete(self) -> bool:
        if not self.human_trader_ref:
            return False
        goal = getattr(self.human_trader_ref, 'goal', 0) or 0
        progress = getattr(self.human_trader_ref, 'goal_progress', 0)
        return goal != 0 and progress >= abs(goal)

    def get_current_reward(self, mid_price: float) -> float:
        """Calculate reward for the human - VWAP for informed, PnL for speculators."""
        if not self.human_trader_ref:
            return 0
        
        goal = self.get_effective_goal()
        
        if goal == 0:
            # Speculator: reward is PnL
            return getattr(self.human_trader_ref, 'get_current_pnl', lambda: 0)()
        
        # Informed trader: VWAP-based reward with penalty (raw value, can be negative)
        state = self.get_effective_state()
        goal_size = abs(goal)
        completed = abs(state["goal_progress"])
        remaining = max(0, goal_size - completed)
        current_vwap = state["vwap"]
        
        if goal > 0:  # Buyer
            if completed > 0:
                expenditure = current_vwap * completed
            else:
                expenditure = 0
            penalty_cost = remaining * mid_price * self.penalty_multiplier_buy
            total_expenditure = expenditure + penalty_cost
            penalized_vwap = total_expenditure / goal_size if goal_size > 0 else 0
            reward = (self.buy_target_price - penalized_vwap)
        else:  # Seller
            if completed > 0:
                revenue = current_vwap * completed
            else:
                revenue = 0
            penalty_revenue = remaining * mid_price * self.penalty_multiplier_sell
            total_revenue = revenue + penalty_revenue
            penalized_vwap = total_revenue / goal_size if goal_size > 0 else 0
            reward = (penalized_vwap - self.sell_target_price)
        
        return reward

    def _get_mode_label(self) -> str:
        return "(HUMAN'S STATE)"

    async def handle_decision(self, tool_name: str, args: Dict, mid_price: float) -> Dict:
        """Store and broadcast advice (don't execute)."""
        # Validate and clamp price if it's a place_order action
        if tool_name == "place_order" and "price" in args:
            min_price, max_price = self._get_valid_price_range()
            original_price = args["price"]
            args["price"] = max(min_price, min(max_price, args["price"]))
            if args["price"] != original_price:
                logger.info(f"[{self.id}] Clamped advice price from {original_price} to {args['price']} (range: {min_price}-{max_price})")

        advice = {
            "timestamp": datetime.now().isoformat(),
            "action": tool_name,
            "args": args,
            "mid_price": mid_price,
            "reasoning": args.get("reasoning", ""),
        }
        self.current_advice = advice
        await self.broadcast_advice_to_human(advice)

        decision = {
            "timestamp": advice["timestamp"],
            "action": tool_name,
            "args": args,
            "result": {"advisor_mode": True, "advice_sent": True},
        }
        self.decision_log.append(decision)
        return decision

    async def broadcast_advice_to_human(self, advice: Dict):
        """Send advice to the human trader's frontend via websocket."""
        if not self.human_trader_ref:
            logger.warning(f"[{self.id}] No human trader reference!")
            return

        websocket = getattr(self.human_trader_ref, 'websocket', None)
        if not websocket:
            logger.warning(f"[{self.id}] Human has no websocket!")
            return

        # Check websocket state
        from starlette.websockets import WebSocketState
        if websocket.client_state != WebSocketState.CONNECTED:
            logger.debug(f"[{self.id}] Websocket not connected (state: {websocket.client_state})")
            return

        try:
            advice_message = {
                "type": "AI_ADVICE",
                "advisor_id": self.id,
                "advice": {
                    "action": advice["action"],
                    "price": advice["args"].get("price"),
                    "quantity": advice["args"].get("quantity", 1),
                    "order_id": advice["args"].get("order_id"),
                    "reasoning": advice.get("reasoning", ""),
                    "mid_price": advice.get("mid_price"),
                    "timestamp": advice["timestamp"],
                }
            }

            await websocket.send_json(advice_message)
            logger.info(f"[{self.id}] Sent advice: {advice['action']} @ {advice['args'].get('price')}")

        except Exception as e:
            logger.error(f"[{self.id}] Failed to broadcast advice: {e}")

    def get_performance_summary(self) -> Dict[str, Any]:
        return {
            "advisor_for": self.advice_for_human_id,
            "decisions": len(self.decision_log),
            "current_advice": self.current_advice,
            "human_linked": self.human_trader_ref is not None,
        }
