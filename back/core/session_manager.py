"""
Elegant Session Manager - Replaces complex market assignment with simple session pools.

This dramatically simplifies the architecture by:
1. Users join lightweight session pools (not heavy markets)
2. Markets only created when actually needed (on trading start)
3. Zero resource waste from zombie markets
4. Clear separation between waiting and active states
"""

import time
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from .data_models import TradingParameters, TraderRole
from .trader_manager import TraderManager
from utils.utils import setup_custom_logger

logger = setup_custom_logger(__name__)


@dataclass
class WaitingUser:
    """Lightweight user waiting to join a market."""
    username: str
    role: TraderRole
    goal: int
    joined_at: datetime
    session_id: str
    params: TradingParameters

    def to_trader_id(self) -> str:
        return f"HUMAN_{self.username}"


class SessionStatus(Enum):
    WAITING = "waiting"      # User in pool, waiting for others
    READY = "ready"          # Enough users, can start trading
    ACTIVE = "active"        # Market created and trading
    FINISHED = "finished"    # Market completed


class SessionManager:
    """
    Elegant session management with lazy market creation.
    
    Philosophy:
    - Fast user onboarding (lightweight sessions)
    - Markets created only when needed
    - Simple state management
    - Clear user experience
    """
    
    def __init__(self):
        # Simple state - just 3 dictionaries instead of 7!
        self.session_pools: Dict[str, List[WaitingUser]] = {}  # session_id -> users waiting
        self.active_markets: Dict[str, TraderManager] = {}     # market_id -> actual markets
        self.user_sessions: Dict[str, str] = {}                # username -> session_id
        
        # Keep historical tracking (needed for limits)
        self.user_historical_markets: Dict[str, Set[str]] = {}
        self.user_ready_status: Dict[str, bool] = {}  # username -> ready to start
        
    async def join_session(self, username: str, params: TradingParameters) -> Tuple[str, str, TraderRole, int]:
        """
        User joins a session pool. Fast and lightweight!
        
        Returns: (session_id, trader_id, role, goal)
        """
        # Check if user can join
        if not await self._can_user_join(username, params):
            raise Exception("Maximum number of allowed markets reached")
        
        # Remove user from any existing session first
        await self._remove_user_from_current_session(username)
        
        # Find or create appropriate session pool
        session_id, role, goal = await self._find_or_create_session_pool(username, params)
        
        # Create waiting user
        waiting_user = WaitingUser(
            username=username,
            role=role,
            goal=goal,
            joined_at=datetime.now(timezone.utc),
            session_id=session_id,
            params=params
        )
        
        # Add to session pool
        if session_id not in self.session_pools:
            self.session_pools[session_id] = []
        
        self.session_pools[session_id].append(waiting_user)
        self.user_sessions[username] = session_id
        
        trader_id = waiting_user.to_trader_id()
        
        logger.info(f"User {username} joined session {session_id} with role {role} and goal {goal}")
        
        return session_id, trader_id, role, goal
    
    async def mark_user_ready(self, username: str) -> Tuple[bool, Dict]:
        """
        Mark user as ready to start trading.
        
        Returns: (all_ready, status_info)
        """
        session_id = self.user_sessions.get(username)
        if not session_id:
            raise Exception(f"User {username} not in any session")
        
        self.user_ready_status[username] = True
        
        # Check if this session is ready to start
        session_users = self.session_pools.get(session_id, [])
        if not session_users:
            raise Exception(f"Session {session_id} not found")
        
        # Get session parameters from first user (all have same params)
        params = session_users[0].params
        required_count = len(params.predefined_goals)
        ready_count = sum(1 for user in session_users if self.user_ready_status.get(user.username, False))
        
        # Check for Prolific users (can start with 1)
        has_prolific = any("prolific" in user.username.lower() for user in session_users)
        can_start = ready_count >= required_count or (has_prolific and ready_count > 0)
        
        status_info = {
            "session_id": session_id,
            "ready_count": ready_count,
            "total_needed": required_count,
            "can_start": can_start,
            "status": SessionStatus.READY.value if can_start else SessionStatus.WAITING.value
        }
        
        return can_start, status_info
    
    async def start_trading_session(self, username: str) -> Tuple[str, TraderManager]:
        """
        Convert a session pool into an actual trading market.
        This is where the heavy lifting happens!
        
        Returns: (market_id, trader_manager)
        """
        session_id = self.user_sessions.get(username)
        if not session_id:
            raise Exception(f"User {username} not in any session")
        
        session_users = self.session_pools.get(session_id, [])
        if not session_users:
            raise Exception(f"Session {session_id} not found")
        
        # Check if already converted to market
        if session_id in self.active_markets:
            return session_id, self.active_markets[session_id]
        
        # NOW create the actual heavy market infrastructure
        logger.info(f"Converting session {session_id} to active market with {len(session_users)} users")
        
        # Use parameters from first user (all have same params for this session)
        params = session_users[0].params
        
        # Create the heavy TraderManager (only now!)
        trader_manager = TraderManager(params)
        market_id = trader_manager.trading_market.id
        
        # Add all human traders from the session pool
        for waiting_user in session_users:
            await trader_manager.add_human_trader(
                waiting_user.username,
                role=waiting_user.role,
                goal=waiting_user.goal
            )
            
            # Record in historical markets when trading starts
            if waiting_user.username not in self.user_historical_markets:
                self.user_historical_markets[waiting_user.username] = set()
            self.user_historical_markets[waiting_user.username].add(market_id)
        
        # Move from session pool to active market
        self.active_markets[market_id] = trader_manager
        
        # Clean up session pool
        del self.session_pools[session_id]
        for user in session_users:
            self.user_sessions[user.username] = market_id  # Update to market_id
        
        logger.info(f"Successfully created market {market_id} from session {session_id}")
        
        return market_id, trader_manager
    
    def get_session_status(self, username: str) -> Dict:
        """Get current status for a user."""
        session_id = self.user_sessions.get(username)
        if not session_id:
            return {"status": "not_found"}
        
        # Check if it's an active market
        if session_id in self.active_markets:
            trader_manager = self.active_markets[session_id]
            return {
                "status": SessionStatus.ACTIVE.value,
                "market_id": session_id,
                "trading_started": trader_manager.trading_market.trading_started,
                "is_finished": trader_manager.trading_market.is_finished
            }
        
        # It's a session pool
        session_users = self.session_pools.get(session_id, [])
        if not session_users:
            return {"status": "not_found"}
        
        params = session_users[0].params
        required_count = len(params.predefined_goals)
        ready_count = sum(1 for user in session_users if self.user_ready_status.get(user.username, False))
        
        return {
            "status": SessionStatus.WAITING.value,
            "session_id": session_id,
            "current_users": len(session_users),
            "ready_count": ready_count,
            "total_needed": required_count,
            "users": [user.username for user in session_users]
        }
    
    def get_trader_manager(self, username: str) -> Optional[TraderManager]:
        """Get trader manager for a user (only if market is active)."""
        session_id = self.user_sessions.get(username)
        if not session_id:
            return None
        
        return self.active_markets.get(session_id)
    
    def list_all_sessions(self) -> List[Dict]:
        """List all sessions and markets for admin monitoring."""
        sessions = []
        
        # Add waiting session pools
        for session_id, users in self.session_pools.items():
            if users:  # Only non-empty sessions
                params = users[0].params
                sessions.append({
                    "id": session_id,
                    "type": "session_pool",
                    "status": SessionStatus.WAITING.value,
                    "user_count": len(users),
                    "required_count": len(params.predefined_goals),
                    "users": [user.username for user in users]
                })
        
        # Add active markets
        for market_id, trader_manager in self.active_markets.items():
            sessions.append({
                "id": market_id,
                "type": "active_market",
                "status": SessionStatus.ACTIVE.value,
                "trading_started": trader_manager.trading_market.trading_started,
                "is_finished": trader_manager.trading_market.is_finished,
                "user_count": len(trader_manager.human_traders)
            })
        
        return sessions
    
    async def cleanup_finished_markets(self):
        """Clean up finished markets."""
        finished_markets = []
        
        for market_id, trader_manager in self.active_markets.items():
            if trader_manager.trading_market.is_finished:
                finished_markets.append(market_id)
                await trader_manager.cleanup()
        
        for market_id in finished_markets:
            del self.active_markets[market_id]
            # Remove user session mappings for this market
            users_to_remove = [username for username, session_id in self.user_sessions.items() 
                             if session_id == market_id]
            for username in users_to_remove:
                del self.user_sessions[username]
        
        logger.info(f"Cleaned up {len(finished_markets)} finished markets")
    
    async def reset_all(self):
        """Reset all state (for admin reset)."""
        # Cleanup active markets
        for trader_manager in self.active_markets.values():
            try:
                await trader_manager.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up trader manager: {e}")
        
        # Clear all state
        self.session_pools.clear()
        self.active_markets.clear()
        self.user_sessions.clear()
        self.user_ready_status.clear()
        # Keep user_historical_markets for limit tracking
        
        logger.info("Session manager state reset")
    
    # Private helper methods
    
    async def _can_user_join(self, username: str, params: TradingParameters) -> bool:
        """Check if user can join based on historical limits."""
        # Admin users can always join
        admin_users = params.admin_users or []
        if username in admin_users:
            return True
        
        # Check historical market count
        historical_count = len(self.user_historical_markets.get(username, set()))
        return historical_count < params.max_markets_per_human
    
    async def _remove_user_from_current_session(self, username: str):
        """Remove user from any existing session."""
        current_session = self.user_sessions.get(username)
        if not current_session:
            return
        
        # Remove from session pool
        if current_session in self.session_pools:
            self.session_pools[current_session] = [
                user for user in self.session_pools[current_session] 
                if user.username != username
            ]
            # Clean up empty session pools
            if not self.session_pools[current_session]:
                del self.session_pools[current_session]
        
        # Remove session mapping
        del self.user_sessions[username]
        
        # Remove ready status
        if username in self.user_ready_status:
            del self.user_ready_status[username]
    
    async def _find_or_create_session_pool(self, username: str, params: TradingParameters) -> Tuple[str, TraderRole, int]:
        """
        Find existing session pool or create new one.
        Much simpler than the original 120-line function!
        
        Returns: (session_id, role, goal)
        """
        required_count = len(params.predefined_goals)
        
        # Try to find existing session pool with space
        for session_id, users in self.session_pools.items():
            if len(users) < required_count:
                # Assign role based on position in this session
                position = len(users)
                goal = params.predefined_goals[position]
                role = TraderRole.INFORMED if goal != 0 else TraderRole.SPECULATOR
                
                # Apply random goal flip if enabled
                if role == TraderRole.INFORMED and params.allow_random_goals:
                    import random
                    goal *= random.choice([-1, 1])
                
                return session_id, role, goal
        
        # Create new session pool
        session_id = f"SESSION_{int(time.time())}"
        
        # First user gets first role/goal
        goal = params.predefined_goals[0]
        role = TraderRole.INFORMED if goal != 0 else TraderRole.SPECULATOR
        
        if role == TraderRole.INFORMED and params.allow_random_goals:
            import random
            goal *= random.choice([-1, 1])
        
        return session_id, role, goal 