"""
Market Pipeline - Complete user-to-market flow management.
Combines constraint-based user queuing with market lifecycle management.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Set

from core.data_models import TradingParameters, TraderRole
from core.trader_manager import TraderManager


@dataclass
class UserProfile:
    """User with their trading constraints"""
    username: str
    is_prolific: bool
    joined_at: float
    preferred_role: Optional[str] = None
    preferred_goal: Optional[int] = None


@dataclass
class SessionTemplate:
    """Defines what a valid trading session looks like"""
    template_id: str
    requirements: Dict[Tuple[str, int], int]  # (role, goal) -> count needed
    total_players: int
    
    def __post_init__(self):
        # Validate that requirements match total_players
        if sum(self.requirements.values()) != self.total_players:
            raise ValueError(f"Requirements sum {sum(self.requirements.values())} != total_players {self.total_players}")


class MarketPipeline:
    """
    Complete trading pipeline from user queuing to market management.
    Handles constraint-based matching and market lifecycle.
    """
    
    def __init__(self):
        # === USER QUEUING ===
        # Multi-dimensional waiting pools: (role, goal) -> queue of users
        self.waiting_pools: Dict[Tuple[str, int], deque] = defaultdict(deque)
        # User tracking
        self.user_locations: Dict[str, Tuple[str, int]] = {}  # username -> (role, goal)
        # Templates for valid sessions
        self.session_templates: List[SessionTemplate] = []
        
        # === MARKET MANAGEMENT ===
        # Core mappings
        self.markets: Dict[str, TraderManager] = {}  # market_id -> TraderManager
        self.user_to_market: Dict[str, str] = {}     # username -> market_id
        self.trader_to_market: Dict[str, str] = {}   # trader_id -> market_id
        # State tracking
        self.ready_traders: Dict[str, Set[str]] = {}  # market_id -> ready trader_ids
        self.active_users: Dict[str, Set[str]] = {}   # market_id -> active usernames
    
    # ============================================================================
    # USER QUEUING & CONSTRAINT MATCHING
    # ============================================================================
    
    def set_session_templates_from_params(self, params: TradingParameters):
        """Generate session templates from trading parameters"""
        self.session_templates.clear()
        
        # Create template based on predefined goals
        requirements = {}
        for i, goal in enumerate(params.predefined_goals):
            role = "informed" if goal != 0 else "speculator"
            key = (role, goal)
            requirements[key] = requirements.get(key, 0) + 1
        
        template = SessionTemplate(
            template_id="default",
            requirements=requirements,
            total_players=len(params.predefined_goals)
        )
        
        self.session_templates.append(template)
        print(f"Pipeline template: {requirements} (total: {template.total_players})")
    
    async def join_queue(self, username: str, is_prolific: bool, params: TradingParameters) -> Tuple[bool, Dict]:
        """
        Add user to queue and attempt market formation.
        Returns (market_ready, market_data_or_status)
        """
        # Remove user from any existing pool first
        self._remove_user_from_pools(username)
        
        # Update session templates
        self.set_session_templates_from_params(params)
        template = self.session_templates[0]
        
        # Find the best pool for this user
        target_key = self._find_best_pool_for_user(template)
        if not target_key:
            return False, {"error": "No available slots in current session template"}
        
        role, goal = target_key
        
        # Add user to the appropriate pool
        user = UserProfile(
            username=username,
            is_prolific=is_prolific,
            joined_at=time.time()
        )
        
        self.waiting_pools[target_key].append(user)
        self.user_locations[username] = target_key
        
        print(f"User {username} -> pool ({role}, {goal}). Pool size: {len(self.waiting_pools[target_key])}")
        
        # Check if we can form a complete market
        market_data = self._try_form_market(template, params)
        if market_data:
            return True, market_data
        else:
            # Return current waiting status
            return False, self._get_waiting_status(template)
    
    def _find_best_pool_for_user(self, template: SessionTemplate) -> Optional[Tuple[str, int]]:
        """Find the pool that most needs users (has the largest deficit)"""
        best_key = None
        largest_deficit = -1
        
        for (role, goal), needed in template.requirements.items():
            current_count = len(self.waiting_pools[(role, goal)])
            deficit = needed - current_count
            
            if deficit > largest_deficit:
                largest_deficit = deficit
                best_key = (role, goal)
        
        return best_key if largest_deficit > 0 else None
    
    def _try_form_market(self, template: SessionTemplate, params: TradingParameters) -> Optional[Dict]:
        """Check constraints and form market if possible"""
        
        # Check if all requirements can be satisfied
        for (role, goal), needed in template.requirements.items():
            available = len(self.waiting_pools[(role, goal)])
            if available < needed:
                return None  # Can't satisfy this requirement
        
        # We can form a market! Use unix timestamp as market ID
        timestamp = int(time.time())
        market_id = f"MARKET_{timestamp}"
        
        market_users = []
        
        # Extract exactly the right number of users from each pool
        for (role, goal), needed in template.requirements.items():
            pool = self.waiting_pools[(role, goal)]
            
            for _ in range(needed):
                if pool:
                    user = pool.popleft()
                    
                    # Remove from user_locations
                    if user.username in self.user_locations:
                        del self.user_locations[user.username]
                    
                    market_users.append({
                        "username": user.username,
                        "trader_id": f"HUMAN_{user.username}",
                        "role": role,
                        "goal": goal,
                        "is_prolific": user.is_prolific,
                        "joined_at": user.joined_at
                    })
        
        market_data = {
            "market_ready": True,
            "market_id": market_id,
            "users": market_users,
            "template_used": template.template_id,
            "created_at": timestamp
        }
        
        print(f"Market {market_id} formed with {len(market_users)} players")
        print(f"Template satisfied: {template.requirements}")
        
        # Immediately create the market
        import asyncio
        asyncio.create_task(self._create_market_from_data(market_data, params))
        
        return market_data
    
    def _get_waiting_status(self, template: SessionTemplate) -> Dict:
        """Get current waiting room status"""
        pool_status = {}
        total_waiting = 0
        total_needed = 0
        
        for (role, goal), needed in template.requirements.items():
            current = len(self.waiting_pools[(role, goal)])
            pool_status[f"{role}_{goal}"] = {
                "current": current,
                "needed": needed,
                "waiting_for": max(0, needed - current)
            }
            total_waiting += current
            total_needed += needed
        
        return {
            "market_ready": False,
            "total_players": total_waiting,
            "required_players": total_needed,
            "waiting_for": total_needed - total_waiting,
            "pool_breakdown": pool_status,
            "template": template.requirements
        }
    
    def _remove_user_from_pools(self, username: str):
        """Remove user from any waiting pool they might be in"""
        if username in self.user_locations:
            key = self.user_locations[username]
            pool = self.waiting_pools[key]
            
            # Remove user from pool
            self.waiting_pools[key] = deque(
                user for user in pool if user.username != username
            )
            
            del self.user_locations[username]
            print(f"Removed {username} from pool {key}")
    
    def get_user_status(self, username: str) -> Dict:
        """Get status for a specific user"""
        if username in self.user_locations:
            role, goal = self.user_locations[username]
            pool_size = len(self.waiting_pools[(role, goal)])
            
            return {
                "in_waiting_room": True,
                "assigned_role": role,
                "assigned_goal": goal,
                "pool_size": pool_size,
                "position_in_pool": self._get_user_position_in_pool(username, (role, goal))
            }
        
        return {"in_waiting_room": False}
    
    def _get_user_position_in_pool(self, username: str, key: Tuple[str, int]) -> int:
        """Get user's position in their assigned pool"""
        pool = self.waiting_pools[key]
        for i, user in enumerate(pool):
            if user.username == username:
                return i + 1  # 1-indexed for user display
        return -1
    
    # ============================================================================
    # MARKET MANAGEMENT
    # ============================================================================
    
    async def _create_market_from_data(self, market_data: Dict, params: TradingParameters) -> str:
        """Create a trading market from market data"""
        market_id = market_data["market_id"]
        
        print(f"Creating market {market_id}")
        
        # Create trader manager with latest parameters
        trader_manager = TraderManager(params)
        trader_manager.trading_market.id = market_id
        
        # Add all human traders
        for user_data in market_data["users"]:
            username = user_data["username"]
            goal = user_data["goal"]
            role = TraderRole.INFORMED if goal != 0 else TraderRole.SPECULATOR
            trader_id = user_data["trader_id"]
            
            # Add the trader
            await trader_manager.add_human_trader(username, role, goal)
            
            # Update mappings
            self.user_to_market[username] = market_id
            self.trader_to_market[trader_id] = market_id
            
            print(f"  {username} -> {role.value} (goal: {goal})")
        
        # Initialize tracking structures
        self.markets[market_id] = trader_manager
        self.ready_traders[market_id] = set()
        self.active_users[market_id] = set()
        
        print(f"Market {market_id} ready with {len(market_data['users'])} traders")
        return market_id
    
    def get_trader_manager(self, trader_id: str) -> Optional[TraderManager]:
        """Get trader manager for a specific trader"""
        market_id = self.trader_to_market.get(trader_id)
        return self.markets.get(market_id) if market_id else None
    
    def get_market_for_user(self, username: str) -> Optional[str]:
        """Get market ID for a user"""
        return self.user_to_market.get(username)
    
    async def mark_trader_ready(self, trader_id: str) -> bool:
        """Mark trader as ready and check if market can start"""
        market_id = self.trader_to_market.get(trader_id)
        if not market_id or market_id not in self.markets:
            return False
        
        # Add to ready set
        self.ready_traders[market_id].add(trader_id)
        
        # Check if all traders are ready
        trader_manager = self.markets[market_id]
        required_count = len(trader_manager.human_traders)
        ready_count = len(self.ready_traders[market_id])
        
        print(f"Market {market_id}: {ready_count}/{required_count} traders ready")
        
        return ready_count >= required_count
    
    async def start_market(self, trader_id: str, params: TradingParameters) -> bool:
        """Start trading for a market"""
        market_id = self.trader_to_market.get(trader_id)
        if not market_id or market_id not in self.markets:
            print(f"No market found for trader {trader_id}")
            return False
        
        trader_manager = self.markets[market_id]
        
        # Update with latest parameters
        trader_manager.params = params
        
        # Update parameters for automated traders
        params_dict = params.model_dump()
        for trader in trader_manager.noise_traders + trader_manager.informed_traders:
            trader.params = params_dict
        
        # Update market parameters
        trader_manager.trading_market.params = params_dict
        
        print(f"Starting market {market_id}")
        print(f"  Noise: {len(trader_manager.noise_traders)}, Informed: {len(trader_manager.informed_traders)}")
        
        # Launch asynchronously
        import asyncio
        asyncio.create_task(trader_manager.launch())
        
        return True
    
    def add_active_user(self, username: str, market_id: str):
        """Track active user connection"""
        if market_id not in self.active_users:
            self.active_users[market_id] = set()
        self.active_users[market_id].add(username)
    
    def remove_active_user(self, username: str, market_id: str):
        """Remove user from active tracking"""
        if market_id in self.active_users:
            self.active_users[market_id].discard(username)
    
    def get_market_status(self, market_id: str) -> Dict:
        """Get detailed market status"""
        if market_id not in self.markets:
            return {"status": "not_found"}
        
        trader_manager = self.markets[market_id]
        
        return {
            "status": "trading" if trader_manager.trading_market.trading_started else "waiting",
            "market_id": market_id,
            "active_users": len(self.active_users.get(market_id, set())),
            "ready_traders": len(self.ready_traders.get(market_id, set())),
            "total_traders": len(trader_manager.human_traders),
            "trading_started": trader_manager.trading_market.trading_started,
            "noise_traders": len(trader_manager.noise_traders),
            "informed_traders": len(trader_manager.informed_traders)
        }
    
    # ============================================================================
    # CLEANUP & UTILITIES
    # ============================================================================
    
    def cleanup_old_users(self, max_age_seconds: int = 1800):
        """Remove users who have been waiting too long"""
        current_time = time.time()
        
        for key, pool in self.waiting_pools.items():
            # Remove old users
            fresh_users = deque()
            removed_count = 0
            
            for user in pool:
                if current_time - user.joined_at < max_age_seconds:
                    fresh_users.append(user)
                else:
                    removed_count += 1
                    if user.username in self.user_locations:
                        del self.user_locations[user.username]
            
            self.waiting_pools[key] = fresh_users
            
            if removed_count > 0:
                print(f"Cleaned up {removed_count} old users from pool {key}")
    
    async def cleanup_finished_markets(self):
        """Remove completed markets"""
        finished = []
        
        for market_id, trader_manager in self.markets.items():
            if hasattr(trader_manager.trading_market, 'is_finished') and trader_manager.trading_market.is_finished:
                finished.append(market_id)
        
        for market_id in finished:
            print(f"Cleaning up finished market: {market_id}")
            
            # Cleanup trader manager
            trader_manager = self.markets[market_id]
            try:
                await trader_manager.cleanup()
            except Exception as e:
                print(f"  Cleanup error: {e}")
            
            # Remove all references
            del self.markets[market_id]
            
            # Clean up tracking
            if market_id in self.ready_traders:
                del self.ready_traders[market_id]
            if market_id in self.active_users:
                del self.active_users[market_id]
            
            # Remove user mappings
            users_to_remove = [u for u, m in self.user_to_market.items() if m == market_id]
            for username in users_to_remove:
                del self.user_to_market[username]
            
            # Remove trader mappings
            traders_to_remove = [t for t, m in self.trader_to_market.items() if m == market_id]
            for trader_id in traders_to_remove:
                del self.trader_to_market[trader_id]
    
    async def reset_all(self):
        """Complete reset of pipeline"""
        market_ids = list(self.markets.keys())
        
        # Cleanup all markets
        for market_id in market_ids:
            trader_manager = self.markets[market_id]
            try:
                await trader_manager.cleanup()
            except Exception as e:
                print(f"Reset cleanup error for {market_id}: {e}")
        
        # Clear all state
        self.waiting_pools.clear()
        self.user_locations.clear()
        self.session_templates.clear()
        self.markets.clear()
        self.user_to_market.clear()
        self.trader_to_market.clear()
        self.ready_traders.clear()
        self.active_users.clear()
        
        print("Pipeline reset")
    
    def get_debug_info(self) -> Dict:
        """Debug information about pipeline state"""
        pool_info = {}
        for key, pool in self.waiting_pools.items():
            if pool:
                pool_info[str(key)] = [
                    {
                        "username": user.username,
                        "waiting_time": time.time() - user.joined_at,
                        "is_prolific": user.is_prolific
                    }
                    for user in pool
                ]
        
        return {
            "queuing": {
                "active_pools": pool_info,
                "total_waiting_users": sum(len(pool) for pool in self.waiting_pools.values()),
                "session_templates": [
                    {
                        "id": t.template_id,
                        "requirements": dict(t.requirements),
                        "total_players": t.total_players
                    }
                    for t in self.session_templates
                ]
            },
            "markets": {
                "total_markets": len(self.markets),
                "active_markets": [
                    {
                        "market_id": mid,
                        "status": self.get_market_status(mid)
                    }
                    for mid in self.markets.keys()
                ],
                "user_mappings": dict(self.user_to_market),
                "trader_mappings": dict(self.trader_to_market)
            }
        } 