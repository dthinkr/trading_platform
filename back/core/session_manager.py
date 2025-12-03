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
from .treatment_manager import treatment_manager
from utils.utils import setup_custom_logger

logger = setup_custom_logger(__name__)


@dataclass
class RoleSlot:
    """A role slot in a session - SIMPLER approach."""
    goal: int
    role: TraderRole
    assigned_to: Optional[str] = None  # username who got this slot
    joined_at: Optional[datetime] = None
    
    @property
    def is_available(self) -> bool:
        return self.assigned_to is None


@dataclass
class WaitingUser:
    """Lightweight user waiting to join a market (kept for compatibility)."""
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
        # SIMPLER state management with RoleSlot
        self.session_slots: Dict[str, List[RoleSlot]] = {}     # session_id -> list of RoleSlot
        self.session_params: Dict[str, TradingParameters] = {} # session_id -> params
        self.active_markets: Dict[str, TraderManager] = {}     # market_id -> actual markets
        self.user_sessions: Dict[str, str] = {}                # username -> session_id
        
        # Keep historical tracking (needed for limits)
        self.user_historical_markets: Dict[str, Set[str]] = {}
        self.user_ready_status: Dict[str, bool] = {}  # username -> ready to start
        
        # Role persistence: Once assigned, role and goal magnitude stick
        self.permanent_speculators: Set[str] = set()  # username -> always SPECULATOR (goal=0)
        self.permanent_informed_goals: Dict[str, int] = {}  # username -> goal magnitude (e.g., 100)
        
        # Concurrency control: Lock for atomic session join operations
        self._session_join_lock = asyncio.Lock()
        
    # Backward compatibility properties
    @property
    def session_pools(self) -> Dict[str, List[WaitingUser]]:
        """Convert RoleSlot sessions to WaitingUser format for compatibility."""
        result = {}
        for session_id, slots in self.session_slots.items():
            users = []
            params = self.session_params.get(session_id)
            for slot in slots:
                if slot.assigned_to:
                    users.append(WaitingUser(
                        username=slot.assigned_to,
                        role=slot.role,
                        goal=slot.goal,
                        joined_at=slot.joined_at or datetime.now(timezone.utc),
                        session_id=session_id,
                        params=params or TradingParameters()
                    ))
            result[session_id] = users
        return result
    
    @property
    def user_permanent_roles(self) -> Dict[str, TraderRole]:
        """Backward compatibility: Convert set to dict format."""
        return {username: TraderRole.SPECULATOR for username in self.permanent_speculators}
        
    async def join_session(self, username: str, params: TradingParameters) -> Tuple[str, str, TraderRole, int]:
        """
        User joins a session pool. Fast and lightweight!
        SIMPLER VERSION: Uses RoleSlot for clearer logic.
        ATOMIC: Uses lock to prevent race conditions when multiple traders join simultaneously.
        
        Returns: (session_id, trader_id, role, goal)
        """
        # Check if user can join
        if not await self._can_user_join(username, params):
            raise Exception("Maximum number of allowed markets reached")
        
        # Remove user from any existing session first
        await self.remove_user_from_session(username)
        
        # ATOMIC SECTION: Lock to prevent race conditions
        # Multiple traders arriving simultaneously must join one at a time
        async with self._session_join_lock:
            # Find or create appropriate session
            session_id = self._find_or_create_session(username, params)
            
            # Assign user to a slot in that session
            role, goal = self._assign_user_to_slot(username, session_id, params)
            
            # Track user in session
            self.user_sessions[username] = session_id
        
        trader_id = f"HUMAN_{username}"
        
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
        base_params = session_users[0].params
        
        # Apply treatment based on first user's market count
        first_user = session_users[0].username
        market_count = len(self.user_historical_markets.get(first_user, set()))
        
        # Get treatment-modified params
        base_params_dict = base_params.model_dump()
        merged_params_dict = treatment_manager.get_merged_params(market_count, base_params_dict)
        
        # Create new TradingParameters with merged settings
        params = TradingParameters(**merged_params_dict)
        logger.info(f"Applied treatment {market_count} for session {session_id} (user {first_user})")
        
        # Create the heavy TraderManager (only now!)
        # Use session_id as market_id to ensure uniqueness
        trader_manager = TraderManager(params, market_id=session_id)
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
        
        # Clean up session pool - use the actual storage, not the property!
        if session_id in self.session_slots:
            del self.session_slots[session_id]
        if session_id in self.session_params:
            del self.session_params[session_id]
        
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
        
        # Find this user's info in the session
        user_info = next((u for u in session_users if u.username == username), None)
        
        params = session_users[0].params
        required_count = len(params.predefined_goals)
        ready_count = sum(1 for user in session_users if self.user_ready_status.get(user.username, False))
        
        result = {
            "status": SessionStatus.WAITING.value,
            "session_id": session_id,
            "current_users": len(session_users),
            "ready_count": ready_count,
            "total_needed": required_count,
            "users": [user.username for user in session_users]
        }
        
        # Add user-specific info if found
        if user_info:
            result["role"] = user_info.role
            result["goal"] = user_info.goal
            result["cash"] = params.initial_cash
            result["shares"] = params.initial_stocks
        
        return result
    
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
        
        # Clear all state (using new structures)
        self.session_slots.clear()
        self.session_params.clear()
        self.active_markets.clear()
        self.user_sessions.clear()
        self.user_ready_status.clear()
        # Keep user_historical_markets for limit tracking
        # Keep permanent_speculators for role consistency across sessions
        
        logger.info("Session manager state reset")

    def update_session_pool_goals(self, new_params: TradingParameters):
        """
        Update goals in waiting session pools after settings change.

        This method:
        1. Clears permanent role/goal memory (allows reassignment)
        2. Updates goals in waiting sessions (not active markets)
        3. Maintains role assignments but updates goal magnitudes

        Args:
            new_params: Updated TradingParameters with new predefined_goals
        """
        # Clear permanent role memory - users can be reassigned new goals
        self.permanent_speculators.clear()
        self.permanent_informed_goals.clear()
        logger.info("Cleared permanent role assignments - users will be reassigned on next join")

        # Update waiting sessions (skip active markets)
        updated_sessions = 0
        for session_id, slots in list(self.session_slots.items()):
            # Update session parameters
            self.session_params[session_id] = new_params

            # Recreate slots with new goals while preserving assignments
            old_assignments = {}
            for slot in slots:
                if slot.assigned_to:
                    old_assignments[slot.assigned_to] = {
                        'role': slot.role,
                        'joined_at': slot.joined_at
                    }

            # Recreate slots with new goals
            import random
            new_goals = new_params.predefined_goals.copy()
            random.shuffle(new_goals)

            new_slots = []
            for goal in new_goals:
                role = TraderRole.INFORMED if goal != 0 else TraderRole.SPECULATOR
                new_slots.append(RoleSlot(goal=goal, role=role))

            # Reassign users to matching role slots
            for username, assignment in old_assignments.items():
                assigned = False
                for slot in new_slots:
                    if slot.is_available and slot.role == assignment['role']:
                        slot.assigned_to = username
                        slot.joined_at = assignment['joined_at']
                        assigned = True
                        logger.info(f"Reassigned {username} to {slot.role.value} slot with new goal {slot.goal}")
                        break

                if not assigned:
                    logger.warning(f"Could not reassign {username} with role {assignment['role']} - no matching slots in new configuration")

            self.session_slots[session_id] = new_slots
            updated_sessions += 1
            logger.info(f"Updated session {session_id} with new goals {new_goals}")

        logger.info(f"Updated {updated_sessions} waiting sessions with new goal configuration")

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
    
    async def remove_user_from_session(self, username: str):
        """
        Remove user from any existing session (public method).
        Used when user logs in/refreshes to start fresh.
        SIMPLER: Just free up their slot.
        """
        current_session = self.user_sessions.get(username)
        if not current_session:
            return
        
        # Free up slot in session (if in waiting room)
        if current_session in self.session_slots:
            for slot in self.session_slots[current_session]:
                if slot.assigned_to == username:
                    slot.assigned_to = None
                    slot.joined_at = None
                    logger.info(f"Freed slot for {username} in session {current_session}")
            
            # Clean up empty sessions
            if all(slot.is_available for slot in self.session_slots[current_session]):
                del self.session_slots[current_session]
                if current_session in self.session_params:
                    del self.session_params[current_session]
                logger.info(f"Deleted empty session {current_session}")
        
        # Remove from active market (if in active trading session)
        # Note: This effectively abandons the trading session on refresh
        if current_session in self.active_markets:
            logger.info(f"User {username} abandoned active market {current_session} (e.g., via refresh)")
            # Note: We don't remove the entire market, just the user mapping
            # The market itself will continue with other traders or finish naturally
        
        # Remove session mapping (so user is no longer associated with this session)
        del self.user_sessions[username]
        
        # Remove ready status
        if username in self.user_ready_status:
            del self.user_ready_status[username]
        
        logger.info(f"Removed user {username} from session {current_session}")
    
    async def _remove_user_from_current_session(self, username: str):
        """Remove user from any existing session (internal use)."""
        await self.remove_user_from_session(username)
    
    def _create_session_slots(self, session_id: str, params: TradingParameters, required_goal_magnitude: Optional[int] = None):
        """
        Create role slots for a new session.
        
        Args:
            session_id: Unique session identifier
            params: Trading parameters with predefined_goals
            required_goal_magnitude: If provided, ensure this goal magnitude is included in slots
                                     (used when user has permanent goal magnitude not in predefined_goals)
        """
        import random
        
        # Shuffle goals to randomize assignment across sessions
        goals = params.predefined_goals.copy()
        
        # If a required goal magnitude is specified and not already in goals, add it
        if required_goal_magnitude is not None:
            goal_magnitudes = [abs(g) for g in goals]
            if required_goal_magnitude not in goal_magnitudes:
                # Add the required magnitude (use positive, will be flipped randomly if allow_random_goals)
                goals.append(required_goal_magnitude)
                logger.info(f"Added required goal magnitude {required_goal_magnitude} to session slots")
        
        random.shuffle(goals)
        
        slots = []
        for goal in goals:
            role = TraderRole.INFORMED if goal != 0 else TraderRole.SPECULATOR
            slots.append(RoleSlot(goal=goal, role=role))
        
        self.session_slots[session_id] = slots
        self.session_params[session_id] = params
        logger.info(f"Created session {session_id} with {len(slots)} slots (shuffled goals: {goals})")
    
    def _find_or_create_session(self, username: str, params: TradingParameters) -> str:
        """
        Find existing session with space or create new one.
        Respects permanent role assignments.
        """
        is_permanent_speculator = username in self.permanent_speculators
        permanent_goal_magnitude = self.permanent_informed_goals.get(username)
        
        # Try existing sessions
        for session_id, slots in self.session_slots.items():
            # Check if session has available slots
            available_slots = [s for s in slots if s.is_available]
            if not available_slots:
                continue
            
            # If permanent SPECULATOR, need a SPECULATOR slot
            if is_permanent_speculator:
                has_speculator_slot = any(s.role == TraderRole.SPECULATOR for s in available_slots)
                if has_speculator_slot:
                    return session_id
            # If permanent INFORMED, need an INFORMED slot with matching goal magnitude
            elif permanent_goal_magnitude is not None:
                has_matching_slot = any(
                    s.role == TraderRole.INFORMED and abs(s.goal) == permanent_goal_magnitude 
                    for s in available_slots
                )
                if has_matching_slot:
                    return session_id
            # New user can take any available slot
            else:
                return session_id
        
        # Create new session with unique ID
        import uuid
        timestamp = int(time.time())
        unique_suffix = str(uuid.uuid4())[:8]
        session_id = f"SESSION_{timestamp}_{unique_suffix}"
        
        # If user has permanent goal magnitude, ensure it's included in session slots
        required_goal_magnitude = None
        if permanent_goal_magnitude is not None:
            # Check if permanent magnitude is in current predefined_goals
            goal_magnitudes = [abs(g) for g in params.predefined_goals]
            if permanent_goal_magnitude not in goal_magnitudes:
                required_goal_magnitude = permanent_goal_magnitude
                logger.info(f"User {username} has permanent goal magnitude {permanent_goal_magnitude} not in predefined_goals {params.predefined_goals}, adding to session slots")
        
        self._create_session_slots(session_id, params, required_goal_magnitude=required_goal_magnitude)
        return session_id
    
    def _assign_user_to_slot(self, username: str, session_id: str, params: TradingParameters) -> Tuple[TraderRole, int]:
        """
        Assign user to an available slot in the session.
        Respects permanent role and goal magnitude.
        
        Returns: (role, goal)
        """
        import random
        
        slots = self.session_slots[session_id]
        is_permanent_speculator = username in self.permanent_speculators
        permanent_goal_magnitude = self.permanent_informed_goals.get(username)
        
        # Find suitable slot
        for slot in slots:
            if not slot.is_available:
                continue
            
            # If user is permanent SPECULATOR, only give SPECULATOR slots
            if is_permanent_speculator:
                if slot.role != TraderRole.SPECULATOR:
                    continue
            # If user is permanent INFORMED, only give INFORMED slots with matching magnitude
            elif permanent_goal_magnitude is not None:
                if slot.role != TraderRole.INFORMED or abs(slot.goal) != permanent_goal_magnitude:
                    continue
            
            # Assign this slot
            goal = slot.goal
            
            # For INFORMED traders, randomly flip goal direction if enabled
            if slot.role == TraderRole.INFORMED and params.allow_random_goals:
                goal = abs(goal) * random.choice([-1, 1])
                slot.goal = goal  # Update slot with flipped goal
            
            # Update slot assignment
            slot.assigned_to = username
            slot.joined_at = datetime.now(timezone.utc)
            
            # Record permanent role on first assignment
            if slot.role == TraderRole.SPECULATOR and username not in self.permanent_speculators:
                self.permanent_speculators.add(username)
                logger.info(f"User {username} assigned permanent SPECULATOR role (goal=0)")
            elif slot.role == TraderRole.INFORMED and username not in self.permanent_informed_goals:
                self.permanent_informed_goals[username] = abs(goal)
                logger.info(f"User {username} assigned permanent INFORMED role (|goal|={abs(goal)})")
            
            logger.info(f"Assigned {username} to slot with role {slot.role.value} and goal {goal}")
            return slot.role, goal
        
        raise Exception(f"No suitable slot available for {username} in session {session_id}") 