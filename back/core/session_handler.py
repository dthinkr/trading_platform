from typing import Dict, Set, Optional
from .data_models import TraderRole, TradingParameters
from .trader_manager import TraderManager
from utils import setup_custom_logger
from fastapi import HTTPException
import random

logger = setup_custom_logger(__name__)

class SessionHandler:
    def __init__(self):
        self.trader_managers: Dict[str, TraderManager] = {}
        self.active_users: Dict[str, Set[str]] = {}  # session_id -> set of usernames
        self.user_sessions: Dict[str, str] = {}  # username -> session_id
        self.trader_to_session_lookup: Dict[str, str] = {}  # trader_id -> session_id
        self.user_roles: Dict[str, TraderRole] = {}  # username -> role
        self.session_locks = {}
        self.session_ready_traders: Dict[str, Set[str]] = {}  # session_id -> set of ready trader_ids
        self.user_historical_sessions: Dict[str, Set[str]] = {}  # username -> set of historical session_ids
        
    async def find_or_create_session(self, gmail_username: str, role: TraderRole, params: TradingParameters) -> tuple[str, str]:
        """Find an available session or create a new one"""
        trader_id = f"HUMAN_{gmail_username}"
        
        # Get goal based on role
        goal = await self.assign_user_goal(gmail_username, params)
        
        # Check existing session
        if gmail_username in self.user_sessions:
            session_id = self.user_sessions[gmail_username]
            if session_id in self.trader_managers:
                trader_manager = self.trader_managers[session_id]
                if not trader_manager.trading_session.trading_started:
                    self.active_users[session_id].add(gmail_username)
                    self.trader_to_session_lookup[trader_id] = session_id
                    return session_id, trader_id

        # Look for available session
        for session_id, manager in self.trader_managers.items():
            if (len(self.active_users[session_id]) < params.num_human_traders 
                and not manager.trading_session.trading_started):
                
                if role == TraderRole.INFORMED:
                    if manager.informed_trader is not None:
                        continue
                else:  # Speculator
                    if (manager.informed_trader is None and 
                        len(self.active_users[session_id]) == params.num_human_traders - 1):
                        continue
                        
                try:
                    trader_id = await manager.add_human_trader(
                        gmail_username, 
                        role=role,
                        goal=goal  # Pass the goal to trader manager
                    )
                    self.trader_to_session_lookup[trader_id] = session_id
                    self.active_users[session_id].add(gmail_username)
                    self.user_sessions[gmail_username] = session_id
                    return session_id, trader_id
                except Exception as e:
                    logger.error(f"Error adding trader to existing session: {str(e)}")
                    continue

        # Create new session
        try:
            new_trader_manager = TraderManager(params)
            session_id = new_trader_manager.trading_session.id
            self.trader_managers[session_id] = new_trader_manager
            self.active_users[session_id] = set()
            
            trader_id = await new_trader_manager.add_human_trader(
                gmail_username, 
                role=role,
                goal=goal  # Pass the goal to trader manager
            )
            
            self.trader_to_session_lookup[trader_id] = session_id
            self.active_users[session_id].add(gmail_username)
            self.user_sessions[gmail_username] = session_id
            
            return session_id, trader_id
            
        except Exception as e:
            logger.error(f"Error creating new session: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error creating trading session: {str(e)}"
            )

    def get_trader_manager(self, trader_id: str) -> Optional[TraderManager]:
        """Get trader manager for a given trader"""
        if trader_id not in self.trader_to_session_lookup:
            return None
        session_id = self.trader_to_session_lookup[trader_id]
        return self.trader_managers.get(session_id) 

    async def can_join_session(self, gmail_username: str, params: TradingParameters) -> bool:
        """Check if user can join a new session based on limits"""
        try:
            # Check if user is already in a session
            if gmail_username in self.user_sessions:
                session_id = self.user_sessions[gmail_username]
                if session_id in self.trader_managers:
                    trader_manager = self.trader_managers[session_id]
                    # Allow if their current session hasn't started
                    if not trader_manager.trading_session.trading_started:
                        return True
                        
            # Count active sessions for this user
            active_session_count = sum(
                1 for session_users in self.active_users.values()
                if gmail_username in session_users
            )
            
            # Check against max allowed sessions from params
            max_sessions = params.max_sessions_per_human
            return active_session_count < max_sessions
            
        except Exception as e:
            logger.error(f"Error checking session limits: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error checking session limits: {str(e)}"
            )

    async def determine_user_role(self, gmail_username: str) -> TraderRole:
        """Determine role for a trader before session assignment"""
        # Check if they already have a role
        if gmail_username in self.user_roles:
            return self.user_roles[gmail_username]
            
        # First-time traders have equal chance of being informed/speculator
        role = random.choice([TraderRole.INFORMED, TraderRole.SPECULATOR])
                
        # Remember their role
        self.user_roles[gmail_username] = role
        return role

    async def assign_user_goal(self, gmail_username: str, params: TradingParameters) -> int:
        """Assign a goal to a user based on their role"""
        role = self.user_roles.get(gmail_username)
        if not role:
            raise ValueError("User must have a role before assigning goal")
            
        if role == TraderRole.INFORMED:
            # Informed traders get non-zero goals
            non_zero_goals = [g for g in params.predefined_goals if g != 0]
            if non_zero_goals:
                # Get absolute value of the selected goal
                goal = abs(random.choice(non_zero_goals))
                # If random goals allowed, randomly flip sign
                if params.allow_random_goals:
                    goal *= random.choice([-1, 1])
            else:
                goal = 100  # fallback
        else:
            # Speculators get 0
            goal = 0
            
        return goal

    def get_historical_sessions_count(self, username: str) -> int:
        """Get count of historical sessions for a user"""
        return len(self.user_historical_sessions.get(username, set()))

    def record_session_for_user(self, username: str, session_id: str):
        """Record a session in user's history"""
        if username not in self.user_historical_sessions:
            self.user_historical_sessions[username] = set()
        self.user_historical_sessions[username].add(session_id)

    async def mark_trader_ready(self, trader_id: str, session_id: str) -> bool:
        """Mark a trader as ready to start"""
        if session_id not in self.session_ready_traders:
            self.session_ready_traders[session_id] = set()
        
        self.session_ready_traders[session_id].add(trader_id)
        
        # Check if all traders are ready
        trader_manager = self.trader_managers.get(session_id)
        if trader_manager:
            expected_traders = trader_manager.params.num_human_traders
            return len(self.session_ready_traders[session_id]) >= expected_traders
        return False

    async def validate_and_assign_role(self, gmail_username: str, params: TradingParameters) -> tuple[str, str, TraderRole, int]:
        """Validate user can join and assign role and goal"""
        # Check if they can join
        can_join = await self.can_join_session(gmail_username, params)
        if not can_join:
            raise HTTPException(
                status_code=403,
                detail="Maximum number of allowed sessions reached"
            )
            
        # Determine role
        role = await self.determine_user_role(gmail_username)
        
        # Find or create session and assign goal
        session_id, trader_id = await self.find_or_create_session(gmail_username, role, params)
        
        # Get assigned goal
        trader_manager = self.get_trader_manager(trader_id)
        trader = trader_manager.traders[trader_id]
        goal = trader.goal
        
        return session_id, trader_id, role, goal

    async def reset_state(self):
        """Reset all session state and clean up resources"""
        try:
            # Store all session IDs first since we'll be modifying the dict
            session_ids = list(self.trader_managers.keys())
            
            # Clean up each session
            for session_id in session_ids:
                trader_manager = self.trader_managers[session_id]
                try:
                    # Clean up trader manager resources
                    await trader_manager.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up trader manager for session {session_id}: {str(e)}")

            # Reset all internal state
            self.trader_managers.clear()
            self.active_users.clear()
            self.user_sessions.clear()
            self.trader_to_session_lookup.clear()
            self.user_roles.clear()
            self.session_locks.clear()
            self.session_ready_traders.clear()
            
            # Don't clear historical sessions as we might need that data
            # self.user_historical_sessions.clear()  
            
            logger.info("Successfully reset all session state")
            return True
            
        except Exception as e:
            logger.error(f"Error during state reset: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error resetting state: {str(e)}"
            )

    def remove_user_from_session(self, gmail_username: str, session_id: str):
        """Safely remove a user from a session"""
        try:
            # Initialize set if it doesn't exist
            if session_id not in self.active_users:
                self.active_users[session_id] = set()
            
            # Remove user from active users
            self.active_users[session_id].discard(gmail_username)
            
            # Clean up user session mapping
            if gmail_username in self.user_sessions:
                del self.user_sessions[gmail_username]
                
            # Clean up trader lookup
            trader_id = f"HUMAN_{gmail_username}"
            if trader_id in self.trader_to_session_lookup:
                del self.trader_to_session_lookup[trader_id]
                
        except Exception as e:
            logger.error(f"Error removing user {gmail_username} from session {session_id}: {str(e)}")

    def add_user_to_session(self, gmail_username: str, session_id: str):
        """Safely add a user to a session"""
        if session_id not in self.active_users:
            self.active_users[session_id] = set()
        self.active_users[session_id].add(gmail_username)