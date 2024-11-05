from typing import Dict, Set, Optional
from .data_models import TraderRole, TradingParameters
from .trader_manager import TraderManager
from utils import setup_custom_logger
from fastapi import HTTPException
import random

class SessionHandler:
    def __init__(self):
        # Maps for tracking sessions and users
        self.trader_managers: Dict[str, TraderManager] = {}
        self.active_users: Dict[str, Set[str]] = {}  # session -> usernames
        self.user_sessions: Dict[str, str] = {}  # username -> session
        self.trader_to_session_lookup: Dict[str, str] = {}  # trader -> session
        self.user_roles: Dict[str, TraderRole] = {}  # username -> role
        self.session_locks = {}
        self.session_ready_traders: Dict[str, Set[str]] = {}  # session -> ready traders
        self.user_historical_sessions: Dict[str, Set[str]] = {}  # username -> past sessions
        
    async def find_or_create_session(self, gmail_username: str, role: TraderRole, params: TradingParameters) -> tuple[str, str]:
        """Find available session or create new one"""
        trader_id = f"HUMAN_{gmail_username}"
        
        goal = await self.assign_user_goal(gmail_username, params)
        num_required_traders = len(params.predefined_goals)

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
            if (len(self.active_users[session_id]) < num_required_traders 
                and not manager.trading_session.trading_started):
                
                if role == TraderRole.INFORMED:
                    if manager.informed_trader is not None:
                        continue
                else:  # Speculator
                    if (manager.informed_trader is None and 
                        len(self.active_users[session_id]) == num_required_traders - 1):
                        continue
                        
                try:
                    trader_id = await manager.add_human_trader(
                        gmail_username, 
                        role=role,
                        goal=goal
                    )
                    self.trader_to_session_lookup[trader_id] = session_id
                    self.active_users[session_id].add(gmail_username)
                    self.user_sessions[gmail_username] = session_id
                    return session_id, trader_id
                except Exception as e:
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
                goal=goal
            )
            
            self.trader_to_session_lookup[trader_id] = session_id
            self.active_users[session_id].add(gmail_username)
            self.user_sessions[gmail_username] = session_id
            
            return session_id, trader_id
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error creating trading session: {str(e)}"
            )

    def get_trader_manager(self, trader_id: str) -> Optional[TraderManager]:
        """Get manager for trader"""
        if trader_id not in self.trader_to_session_lookup:
            return None
        session_id = self.trader_to_session_lookup[trader_id]
        return self.trader_managers.get(session_id) 

    async def can_join_session(self, gmail_username: str, params: TradingParameters) -> bool:
        """Check if user can join new session"""
        try:
            # Check current session
            if gmail_username in self.user_sessions:
                session_id = self.user_sessions[gmail_username]
                if session_id in self.trader_managers:
                    trader_manager = self.trader_managers[session_id]
                    if not trader_manager.trading_session.trading_started:
                        return True
                        
            # Check session count
            active_session_count = sum(
                1 for session_users in self.active_users.values()
                if gmail_username in session_users
            )
            
            return active_session_count < params.max_sessions_per_human
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error checking session limits: {str(e)}"
            )

    async def determine_user_role(self, gmail_username: str) -> TraderRole:
        """Get or assign trader role"""
        if gmail_username in self.user_roles:
            return self.user_roles[gmail_username]
            
        role = random.choice([TraderRole.INFORMED, TraderRole.SPECULATOR])
        self.user_roles[gmail_username] = role
        return role

    async def assign_user_goal(self, gmail_username: str, params: TradingParameters) -> int:
        """Assign goal based on role"""
        role = self.user_roles.get(gmail_username)
        if not role:
            raise ValueError("User must have a role before assigning goal")
            
        if role == TraderRole.INFORMED:
            non_zero_goals = [g for g in params.predefined_goals if g != 0]
            if non_zero_goals:
                goal = abs(random.choice(non_zero_goals))
                if params.allow_random_goals:
                    goal *= random.choice([-1, 1])
            else:
                goal = 100
        else:
            goal = 0
            
        return goal

    def get_historical_sessions_count(self, username: str) -> int:
        """Get user's past session count"""
        return len(self.user_historical_sessions.get(username, set()))

    def record_session_for_user(self, username: str, session_id: str):
        """Add session to user history"""
        if username not in self.user_historical_sessions:
            self.user_historical_sessions[username] = set()
        self.user_historical_sessions[username].add(session_id)

    async def mark_trader_ready(self, trader_id: str, session_id: str) -> bool:
        """Mark trader ready and check if all ready"""
        if session_id not in self.session_ready_traders:
            self.session_ready_traders[session_id] = set()
        
        self.session_ready_traders[session_id].add(trader_id)
        
        trader_manager = self.trader_managers.get(session_id)
        if trader_manager:
            num_required_traders = len(trader_manager.params.predefined_goals)
            return len(self.session_ready_traders[session_id]) >= num_required_traders
        return False

    async def validate_and_assign_role(self, gmail_username: str, params: TradingParameters) -> tuple[str, str, TraderRole, int]:
        """Validate join request and assign role"""
        can_join = await self.can_join_session(gmail_username, params)
        if not can_join:
            raise HTTPException(
                status_code=403,
                detail="Maximum number of allowed sessions reached"
            )
            
        role = await self.determine_user_role(gmail_username)
        session_id, trader_id = await self.find_or_create_session(gmail_username, role, params)
        
        trader_manager = self.get_trader_manager(trader_id)
        trader = trader_manager.traders[trader_id]
        goal = trader.goal
        
        return session_id, trader_id, role, goal

    async def reset_state(self):
        """Reset all state and cleanup"""
        try:
            session_ids = list(self.trader_managers.keys())
            
            for session_id in session_ids:
                trader_manager = self.trader_managers[session_id]
                try:
                    await trader_manager.cleanup()
                except Exception:
                    pass

            self.trader_managers.clear()
            self.active_users.clear()
            self.user_sessions.clear()
            self.trader_to_session_lookup.clear()
            self.user_roles.clear()
            self.session_locks.clear()
            self.session_ready_traders.clear()
            self.user_historical_sessions.clear()  
            
            return True
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error resetting state: {str(e)}"
            )

    def remove_user_from_session(self, gmail_username: str, session_id: str):
        """Remove user from session"""
        if session_id not in self.active_users:
            self.active_users[session_id] = set()
        
        self.active_users[session_id].discard(gmail_username)
        
        if gmail_username in self.user_sessions:
            del self.user_sessions[gmail_username]
            
        trader_id = f"HUMAN_{gmail_username}"
        if trader_id in self.trader_to_session_lookup:
            del self.trader_to_session_lookup[trader_id]

    def add_user_to_session(self, gmail_username: str, session_id: str):
        """Add user to session"""
        if session_id not in self.active_users:
            self.active_users[session_id] = set()
        self.active_users[session_id].add(gmail_username)