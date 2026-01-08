"""
Agentic Trading System - Template-based trading with configurable prompts.

Classes:
- AgenticBase: Shared LLM logic (prompts, API calls, market state)
- AgenticTrader: Autonomous trader that executes orders
- AgenticAdvisor: Advisor that helps humans without executing
"""
import asyncio
import os
import json
import httpx
import yaml
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime
from abc import abstractmethod
from pathlib import Path

from core.data_models import OrderType, TraderType
from .base_trader import PausingTrader
from utils.utils import setup_custom_logger

logger = setup_custom_logger(__name__)


# ============================================================================
# template loading
# ============================================================================

_TEMPLATES_CACHE: Optional[Dict] = None
_CONFIG_PATH = Path(__file__).parent.parent / "config" / "agentic_prompts.yaml"

def load_prompt_templates(force_reload: bool = False) -> Dict:
    """Load prompt templates from config file."""
    global _TEMPLATES_CACHE
    if _TEMPLATES_CACHE is not None and not force_reload:
        return _TEMPLATES_CACHE
    
    try:
        with open(_CONFIG_PATH, "r") as f:
            data = yaml.safe_load(f)
            _TEMPLATES_CACHE = data.get("templates", {})
            logger.info(f"Loaded {len(_TEMPLATES_CACHE)} agentic prompt templates")
            return _TEMPLATES_CACHE
    except Exception as e:
        logger.error(f"Failed to load prompt templates: {e}")
        # Return default template
        _TEMPLATES_CACHE = {
            "buyer_20_default": {
                "name": "Buyer (20 shares)",
                "goal": 20,
                "decision_interval": 5.0,
                "buy_target_price": 110,
                "sell_target_price": 90,
                "penalty_multiplier_buy": 1.5,
                "penalty_multiplier_sell": 0.5,
                "prompt": "You are a trading agent. Buy 20 shares at lowest VWAP."
            }
        }
        return _TEMPLATES_CACHE

def save_prompt_templates(yaml_content: str) -> int:
    """Save prompt templates from YAML content. Returns number of templates saved."""
    global _TEMPLATES_CACHE
    try:
        data = yaml.safe_load(yaml_content)
        if not data or "templates" not in data:
            raise ValueError("YAML must contain a 'templates' key")
        
        templates = data.get("templates", {})
        if not isinstance(templates, dict):
            raise ValueError("'templates' must be a dictionary")
        
        # Validate each template has required fields
        for tid, template in templates.items():
            if "name" not in template:
                template["name"] = tid
            if "goal" not in template:
                raise ValueError(f"Template '{tid}' missing required field 'goal'")
            if "prompt" not in template:
                raise ValueError(f"Template '{tid}' missing required field 'prompt'")
        
        # Save to file
        with open(_CONFIG_PATH, "w") as f:
            f.write(yaml_content)
        
        # Clear cache to force reload
        _TEMPLATES_CACHE = None
        load_prompt_templates(force_reload=True)
        
        logger.info(f"Saved {len(templates)} agentic prompt templates")
        return len(templates)
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML: {e}")
        raise ValueError(f"Invalid YAML: {e}")

def get_prompt_templates_yaml() -> str:
    """Get the raw YAML content of the templates file."""
    try:
        with open(_CONFIG_PATH, "r") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to read templates file: {e}")
        return "templates: {}\n"

def get_template(template_name: str) -> Dict:
    """Get a specific template by name."""
    templates = load_prompt_templates()
    if template_name not in templates:
        logger.warning(f"Template '{template_name}' not found, using first available")
        template_name = next(iter(templates.keys()))
    return templates[template_name]

def list_templates() -> List[Dict]:
    """List all available templates with their names."""
    templates = load_prompt_templates()
    return [{"id": k, "name": v.get("name", k)} for k, v in templates.items()]


# ============================================================================
# type definitions
# ============================================================================

class OrderLevel(TypedDict):
    x: float  # price
    y: int    # quantity


class OrderBook(TypedDict):
    bids: List[OrderLevel]
    asks: List[OrderLevel]


@dataclass
class TraderState:
    """unified state representation for traders/advisors."""
    goal: int
    goal_progress: int
    cash: float
    shares: int
    orders: List[Dict]
    vwap: float
    pnl: float
    avail_cash: float
    avail_shares: int


# ============================================================================
# tool definitions (compact)
# ============================================================================

def _make_tool(name: str, desc: str, params: Dict[str, Any], required: List[str]) -> Dict:
    """factory for openai-format tool definitions."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {"type": "object", "properties": params, "required": required}
        }
    }


def build_tools(goal: int) -> List[Dict]:
    """build tool list based on trader goal."""
    is_speculator = goal == 0
    
    # common params
    price_param = {"price": {"type": "integer", "description": "Limit price for the order"}}
    reason_param = {"reasoning": {"type": "string", "description": "Brief explanation"}}
    
    place_params = {**price_param, **reason_param}
    place_required = ["price"]
    
    if is_speculator:
        place_params["side"] = {"type": "string", "enum": ["buy", "sell"], "description": "Order side"}
        place_required.append("side")
    
    return [
        _make_tool("place_order", "Place a limit order for 1 share.", place_params, place_required),
        _make_tool("cancel_order", "Cancel an existing order by ID.", 
                   {"order_id": {"type": "string", "description": "Order ID to cancel"}, **reason_param}, 
                   ["order_id"]),
        _make_tool("hold", "Take no action this turn.", reason_param, ["reasoning"]),
    ]


# ============================================================================
# base class
# ============================================================================

class AgenticBase(PausingTrader):
    """base class for agentic traders/advisors with shared llm logic."""

    def __init__(self, trader_type: TraderType, id: str, params: dict):
        super().__init__(trader_type=trader_type, id=id)
        self.params = params

        # Load template
        template_name = params.get("agentic_prompt_template", "buyer_20_default")
        self.template = get_template(template_name)
        self.system_prompt = self.template.get("prompt", "")
        
        # llm config
        self.api_key = params.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")
        self.model = params.get("agentic_model", "anthropic/claude-haiku-4.5")
        self.base_url = "https://openrouter.ai/api/v1"

        # From template (with fallbacks)
        self.decision_interval = self.template.get("decision_interval", 5.0)
        self.buy_target_price = self.template.get("buy_target_price", 110)
        self.sell_target_price = self.template.get("sell_target_price", 90)
        self.penalty_multiplier_buy = self.template.get("penalty_multiplier_buy", 1.5)
        self.penalty_multiplier_sell = self.template.get("penalty_multiplier_sell", 0.5)
        
        self.last_decision_time = 0

        # tracking
        self.decision_log: List[Dict] = []
        self.price_history: List[float] = []
        self.initial_mid_price: Optional[float] = None
        
        # incremental log saving
        self._logs_dir = os.path.join(os.path.dirname(__file__), "..", "logs", "agentic")
        os.makedirs(self._logs_dir, exist_ok=True)

    async def initialize(self):
        await super().initialize()
        if not self.api_key:
            logger.warning(f"[{self.id}] No OpenRouter API key configured.")

    def _save_log(self):
        """Incrementally save decision log to file after each decision.
        
        File is named to match the market log: {market_id}.json
        Contains data for this trader (multiple traders append to same structure).
        """
        if not self.decision_log:
            return
        
        market_id = getattr(self, 'trading_market_uuid', None) or 'unknown'
        filename = f"{market_id}.json"
        filepath = os.path.join(self._logs_dir, filename)
        
        trader_data = {
            "trader_id": self.id,
            "goal": self.get_effective_goal(),
            "decision_log": self.decision_log,
            "price_history": self.price_history,
            "updated_at": datetime.now().isoformat(),
        }
        
        # Add performance summary if available
        if hasattr(self, 'get_performance_summary'):
            trader_data["performance"] = self.get_performance_summary()
        
        try:
            # Load existing data or create new structure
            existing_data = {"market_id": market_id, "traders": {}}
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    existing_data = json.load(f)
            
            # Update this trader's data
            existing_data["traders"][self.id] = trader_data
            existing_data["updated_at"] = datetime.now().isoformat()
            
            with open(filepath, "w") as f:
                json.dump(existing_data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"[{self.id}] Failed to save log: {e}")

    # ---- properties ----
    @property
    def is_buyer(self) -> bool:
        return self.get_effective_goal() > 0

    @property
    def is_seller(self) -> bool:
        return self.get_effective_goal() < 0

    @property
    def is_speculator(self) -> bool:
        return self.get_effective_goal() == 0

    @property
    def tools(self) -> List[Dict]:
        return build_tools(self.get_effective_goal())

    # ---- abstract methods ----
    @abstractmethod
    def get_effective_goal(self) -> int:
        pass

    @abstractmethod
    def get_effective_state(self) -> TraderState:
        pass

    @abstractmethod
    def is_goal_complete(self) -> bool:
        pass

    @abstractmethod
    async def handle_decision(self, tool_name: str, args: Dict, mid_price: float) -> Dict:
        pass

    def _get_mode_label(self) -> str:
        return ""

    # ---- reward calculation (shared) ----
    def get_current_reward(self, mid_price: float) -> float:
        """calculate reward - works for both trader and advisor."""
        state = self.get_effective_state()
        goal = state.goal
        
        if goal == 0:
            return state.pnl
        
        goal_size = abs(goal)
        completed = abs(state.goal_progress)
        remaining = max(0, goal_size - completed)
        vwap = state.vwap
        
        if goal > 0:  # buyer
            expenditure = vwap * completed if completed > 0 else 0
            penalty = remaining * mid_price * self.penalty_multiplier_buy
            penalized_vwap = (expenditure + penalty) / goal_size if goal_size > 0 else 0
            return self.buy_target_price - penalized_vwap
        else:  # seller
            revenue = vwap * completed if completed > 0 else 0
            penalty = remaining * mid_price * self.penalty_multiplier_sell
            penalized_vwap = (revenue + penalty) / goal_size if goal_size > 0 else 0
            return penalized_vwap - self.sell_target_price

    # ---- prompt building ----
    def build_system_prompt(self, is_advisor: bool = False) -> str:
        """Return the system prompt from template, with optional advisor prefix."""
        prefix = "You are an AI ADVISOR helping a human trader. Suggest actions.\n\n" if is_advisor else ""
        return prefix + self.system_prompt

    # ---- market state ----
    def _get_valid_price_range(self) -> tuple:
        if not self.order_book:
            return (0, float('inf'))
        bids = self.order_book.get("bids", [])
        asks = self.order_book.get("asks", [])
        best_bid = bids[0]["x"] if bids else 95
        best_ask = asks[0]["x"] if asks else 105
        return (best_bid - 5, best_ask + 5)

    def _get_time_info(self) -> Dict:
        elapsed = self.get_elapsed_time()
        duration = self.params.get("trading_day_duration", 5) * 60
        remaining = max(0, duration - elapsed)
        return {"elapsed": elapsed, "remaining": remaining, "progress_pct": min(100, elapsed / duration * 100) if duration > 0 else 0}

    def _get_trend(self) -> str:
        if len(self.price_history) < 5:
            return "unknown"
        recent = sum(self.price_history[-5:]) / 5
        older = sum(self.price_history[-10:-5]) / 5 if len(self.price_history) >= 10 else recent
        if recent > older * 1.01:
            return "UP ↑"
        elif recent < older * 0.99:
            return "DOWN ↓"
        return "FLAT →"

    def build_market_state(self, mid_price: float, mode_label: str = "") -> str:
        if not self.order_book:
            return "Market data not available."

        bids = self.order_book.get("bids", [])[:5]
        asks = self.order_book.get("asks", [])[:5]
        best_bid = bids[0]["x"] if bids else None
        best_ask = asks[0]["x"] if asks else None
        spread = (best_ask - best_bid) if (best_bid and best_ask) else None

        bid_vol, ask_vol = sum(l["y"] for l in bids), sum(l["y"] for l in asks)
        imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol) if (bid_vol + ask_vol) > 0 else 0

        state = self.get_effective_state()
        time_info = self._get_time_info()
        min_price, max_price = self._get_valid_price_range()

        # build goal/performance section
        if state.goal != 0:
            goal_size, completed = abs(state.goal), abs(state.goal_progress)
            action_type = "BUY" if state.goal > 0 else "SELL"
            vwap_str = f"{state.vwap:.2f}" if state.vwap > 0 else "N/A"
            reward_str = f"{self.get_current_reward(mid_price):.2f}"
            goal_section = f"""=== GOAL PROGRESS {mode_label} ===
Goal: {action_type} {goal_size} shares | Completed: {completed}/{goal_size}
VWAP: {vwap_str} | Est. Reward: {reward_str}"""
        else:
            goal_section = f"""=== PERFORMANCE {mode_label} ===
Role: SPECULATOR | PnL: {state.pnl:.2f} | Position: {state.shares} shares"""

        orders_str = ", ".join(f"{o['id']}: {o['amount']}@{o['price']}" for o in state.orders) or "None"
        
        return f"""=== TIME ===
Elapsed: {int(time_info['elapsed']//60)}:{int(time_info['elapsed']%60):02d} | Remaining: {int(time_info['remaining']//60)}:{int(time_info['remaining']%60):02d}

=== MARKET ===
Bid: {best_bid} | Ask: {best_ask} | Spread: {spread} | Mid: {mid_price:.1f}
Valid Range: {min_price}-{max_price} | Imbalance: {imbalance:+.2f} | Trend: {self._get_trend()}
Book: Bids {[(b['x'], b['y']) for b in bids]} | Asks {[(a['x'], a['y']) for a in asks]}

{goal_section}

=== RESOURCES {mode_label} ===
Cash: {state.cash:.0f} (avail: {state.avail_cash:.0f}) | Shares: {state.shares} (avail: {state.avail_shares})

=== ORDERS {mode_label} ===
{orders_str}

{self._build_recent_decisions()}"""

    def _build_recent_decisions(self) -> str:
        if not self.decision_log:
            return "=== RECENT ===\nNo decisions yet."
        
        lines = ["=== RECENT (last 5) ==="]
        for i, d in enumerate(reversed(self.decision_log[-5:])):
            action, args, result = d.get("action"), d.get("args", {}), d.get("result", {})
            if action == "place_order":
                status = "PENDING" if any(o.get("id") == result.get("order_id") for o in self.orders) else "FILLED"
                if not result.get("success"):
                    status = f"FAILED: {result.get('error', '')}"
                lines.append(f"  {i+1}. {result.get('side', 'buy').upper()} @ {args.get('price')} -> {status}")
            elif action == "cancel_order":
                lines.append(f"  {i+1}. CANCEL {args.get('order_id')} -> {'OK' if result.get('success') else 'FAIL'}")
            elif action == "hold":
                lines.append(f"  {i+1}. HOLD ({args.get('reasoning', '')[:30]})")
        return "\n".join(lines)

    # ---- llm interaction ----
    async def call_llm(self, system_prompt: str, market_state: str) -> Dict:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{market_state}\n\nDecide your action."}
        ]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"model": self.model, "messages": messages, "tools": self.tools, 
                          "tool_choice": "required", "temperature": 0.3, "max_tokens": 300}
                )

                if resp.status_code != 200:
                    return {"error": f"API {resp.status_code}"}

                data = resp.json()
                if "error" in data:
                    return {"error": data["error"]}

                tool_calls = data["choices"][0]["message"].get("tool_calls", [])
                if not tool_calls:
                    return {"tool_name": "hold", "args": {"reasoning": "No tool call"}}

                tc = tool_calls[0]
                try:
                    args = json.loads(tc["function"].get("arguments", "{}"))
                except json.JSONDecodeError:
                    args = {}
                return {"tool_name": tc["function"]["name"], "args": args}

        except Exception as e:
            logger.error(f"[{self.id}] LLM call error: {e}")
            return {"error": str(e)}

    async def make_decision(self) -> Dict:
        if not self.api_key:
            return {"error": "No API key"}

        bids = self.order_book.get("bids", [])
        asks = self.order_book.get("asks", [])
        if not bids or not asks:
            return {"error": "No market data"}

        mid_price = (bids[0]["x"] + asks[0]["x"]) / 2
        if self.initial_mid_price is None:
            self.initial_mid_price = mid_price

        llm_result = await self.call_llm(
            self.build_system_prompt(is_advisor=isinstance(self, AgenticAdvisor)),
            self.build_market_state(mid_price, self._get_mode_label())
        )
        
        if "error" in llm_result:
            logger.error(f"[{self.id}] LLM error: {llm_result['error']}")
            return llm_result

        logger.info(f"[{self.id}] LLM decided: {llm_result['tool_name']} {llm_result['args']}")
        return await self.handle_decision(llm_result["tool_name"], llm_result["args"], mid_price)

    # ---- event handlers ----
    async def on_book_updated(self, data: Dict[str, Any]):
        await super().on_book_updated(data)
        if self.order_book and (bids := self.order_book.get("bids")) and (asks := self.order_book.get("asks")):
            self.price_history.append((bids[0]["x"] + asks[0]["x"]) / 2)
            if len(self.price_history) > 100:
                self.price_history = self.price_history[-100:]

    async def act(self) -> None:
        if not self.order_book or self.is_goal_complete():
            return
        now = asyncio.get_event_loop().time()
        if now - self.last_decision_time >= self.decision_interval:
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


# ============================================================================
# agentictrader - executes orders
# ============================================================================

class AgenticTrader(AgenticBase):
    """autonomous trader that executes orders based on llm decisions."""

    def __init__(self, id: str, params: dict):
        super().__init__(trader_type=TraderType.AGENTIC, id=id, params=params)
        # Goal comes from template
        self.goal = self.template.get("goal", 0)
        self.cash = params.get("initial_cash", 10000)
        self.shares = params.get("initial_shares", 0)
        self.initial_cash = self.cash
        self.initial_shares = self.shares

    def get_effective_goal(self) -> int:
        return self.goal

    def get_effective_state(self) -> TraderState:
        return TraderState(
            goal=self.goal, goal_progress=self.goal_progress, cash=self.cash, shares=self.shares,
            orders=self.orders, vwap=self.get_vwap(), pnl=self.get_current_pnl(),
            avail_cash=self.get_available_cash(), avail_shares=self.get_available_shares()
        )

    def is_goal_complete(self) -> bool:
        return self.goal != 0 and abs(self.goal_progress) >= abs(self.goal)

    async def handle_decision(self, tool_name: str, args: Dict, mid_price: float) -> Dict:
        result = await self._execute_action(tool_name, args)
        decision = {
            "timestamp": datetime.now().isoformat(), "action": tool_name, "args": args,
            "result": result, "goal_progress": self.goal_progress,
            "current_vwap": self.get_vwap(), "current_reward": self.get_current_reward(mid_price)
        }
        self.decision_log.append(decision)
        self._save_log()  # incremental save
        return decision

    async def _execute_action(self, tool_name: str, args: Dict) -> Dict:
        handlers = {
            "place_order": self._handle_place_order,
            "cancel_order": self._handle_cancel_order,
            "hold": self._handle_hold,
        }
        handler = handlers.get(tool_name)
        return await handler(args) if handler else {"error": f"Unknown action: {tool_name}"}

    async def _handle_place_order(self, args: Dict) -> Dict:
        price, qty = args.get("price", 0), 1
        min_price, max_price = self._get_valid_price_range()
        
        if not (min_price <= price <= max_price):
            return {"error": f"Price {price} out of range ({min_price}-{max_price})"}

        if self.is_buyer:
            order_type, side, avail = OrderType.BID, "buy", self.get_available_cash()
            if price * qty > avail:
                return {"error": f"Insufficient cash: need {price*qty}, have {avail}"}
        elif self.is_seller:
            order_type, side, avail = OrderType.ASK, "sell", self.get_available_shares()
            if qty > avail:
                return {"error": f"Insufficient shares: need {qty}, have {avail}"}
        else:  # speculator
            side = args.get("side", "").lower()
            if side not in ["buy", "sell"]:
                return {"error": "Speculator must specify 'side'"}
            if side == "buy":
                order_type, avail = OrderType.BID, self.get_available_cash()
                if price * qty > avail:
                    return {"error": f"Insufficient cash: need {price*qty}, have {avail}"}
            else:
                order_type, avail = OrderType.ASK, self.get_available_shares()
                if qty > avail:
                    return {"error": f"Insufficient shares: need {qty}, have {avail}"}

        order_id = await self.post_new_order(qty, price, order_type)
        if order_id:
            logger.info(f"[{self.id}] Placed {side} {qty}@{price}, id={order_id}")
            return {"success": True, "order_id": order_id, "side": side}
        return {"error": "Order failed"}

    async def _handle_cancel_order(self, args: Dict) -> Dict:
        order_id = args.get("order_id", "")
        success = await self.send_cancel_order_request(order_id)
        if success:
            logger.info(f"[{self.id}] Cancelled {order_id}")
            return {"success": True}
        return {"error": f"Cancel failed for {order_id}"}

    async def _handle_hold(self, args: Dict) -> Dict:
        logger.info(f"[{self.id}] Hold: {args.get('reasoning', '')[:50]}")
        return {"success": True, "action": "hold"}

    def get_performance_summary(self) -> Dict[str, Any]:
        mid = self.price_history[-1] if self.price_history else 100
        base = {"decisions": len(self.decision_log), "cash": self.cash, "shares": self.shares}
        
        if self.is_speculator:
            return {**base, "role": "speculator", "goal": 0, "pnl": self.get_current_pnl(), 
                    "net_position": self.shares - self.initial_shares}
        return {**base, "role": "informed", "goal": self.goal, "goal_progress": self.goal_progress,
                "goal_complete": self.is_goal_complete(), "vwap": self.get_vwap(), 
                "reward": self.get_current_reward(mid)}


# ============================================================================
# agenticadvisor - advises humans
# ============================================================================

class AgenticAdvisor(AgenticBase):
    """advisor that helps humans without executing trades."""

    def __init__(self, id: str, params: dict):
        super().__init__(trader_type=TraderType.AGENTIC, id=id, params=params)
        self.human_trader_ref = None
        self.advice_for_human_id = params.get("advice_for_human_id")
        self.current_advice: Optional[Dict] = None

    def set_human_trader_ref(self, human_trader):
        self.human_trader_ref = human_trader
        logger.info(f"[{self.id}] Linked to human trader: {human_trader.id}")

    def get_effective_goal(self) -> int:
        return getattr(self.human_trader_ref, 'goal', 0) or 0 if self.human_trader_ref else 0

    def get_effective_state(self) -> TraderState:
        if not self.human_trader_ref:
            return TraderState(0, 0, 0, 0, [], 0, 0, 0, 0)
        
        h = self.human_trader_ref
        orders = getattr(h, 'orders', [])
        cash, shares = getattr(h, 'cash', 0), getattr(h, 'shares', 0)
        
        # calculate available resources
        avail_cash = cash - sum(o.get('price', 0) * o.get('amount', 0) for o in orders if o.get('order_type') == 1)
        avail_shares = shares - sum(o.get('amount', 0) for o in orders if o.get('order_type') != 1)
        
        return TraderState(
            goal=getattr(h, 'goal', 0) or 0, goal_progress=getattr(h, 'goal_progress', 0),
            cash=cash, shares=shares, orders=orders,
            vwap=getattr(h, 'get_vwap', lambda: 0)(), pnl=getattr(h, 'get_current_pnl', lambda: 0)(),
            avail_cash=avail_cash, avail_shares=avail_shares
        )

    def is_goal_complete(self) -> bool:
        if not self.human_trader_ref:
            return False
        goal = getattr(self.human_trader_ref, 'goal', 0) or 0
        progress = getattr(self.human_trader_ref, 'goal_progress', 0)
        return goal != 0 and abs(progress) >= abs(goal)

    def _get_mode_label(self) -> str:
        return "(HUMAN'S STATE)"

    async def handle_decision(self, tool_name: str, args: Dict, mid_price: float) -> Dict:
        # clamp price to valid range
        if tool_name == "place_order" and "price" in args:
            min_p, max_p = self._get_valid_price_range()
            args["price"] = max(min_p, min(max_p, args["price"]))

        advice = {
            "timestamp": datetime.now().isoformat(), "action": tool_name,
            "args": args, "mid_price": mid_price, "reasoning": args.get("reasoning", "")
        }
        self.current_advice = advice
        await self._broadcast_advice(advice)

        decision = {"timestamp": advice["timestamp"], "action": tool_name, "args": args,
                    "result": {"advisor_mode": True, "advice_sent": True}}
        self.decision_log.append(decision)
        self._save_log()  # incremental save
        return decision

    async def _broadcast_advice(self, advice: Dict):
        if not self.human_trader_ref:
            return
        
        websocket = getattr(self.human_trader_ref, 'websocket', None)
        if not websocket:
            return

        from starlette.websockets import WebSocketState
        if websocket.client_state != WebSocketState.CONNECTED:
            return

        try:
            await websocket.send_json({
                "type": "AI_ADVICE", "advisor_id": self.id,
                "advice": {
                    "action": advice["action"], "price": advice["args"].get("price"),
                    "quantity": advice["args"].get("quantity", 1), "order_id": advice["args"].get("order_id"),
                    "reasoning": advice.get("reasoning", ""), "mid_price": advice.get("mid_price"),
                    "timestamp": advice["timestamp"]
                }
            })
            logger.info(f"[{self.id}] Sent advice: {advice['action']} @ {advice['args'].get('price')}")
        except Exception as e:
            logger.error(f"[{self.id}] Failed to broadcast advice: {e}")

    def get_performance_summary(self) -> Dict[str, Any]:
        return {
            "advisor_for": self.advice_for_human_id, "decisions": len(self.decision_log),
            "current_advice": self.current_advice, "human_linked": self.human_trader_ref is not None
        }
