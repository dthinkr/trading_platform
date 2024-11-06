from typing import Dict, Set, Optional
from .data_models import TraderRole, TradingParameters
from .trader_manager import TraderManager
from utils import setup_custom_logger
from fastapi import HTTPException
import random
import asyncio

class SessionHandler:
    def __init__(self):
        # maps for tracking sessions and users
        self.trader_managers: Dict[str, TraderManager] = {}
        self.active_users: Dict[str, Set[str]] = {}  # session -> usernames
        self.user_sessions: Dict[str, str] = {}  # username -> session
        self.trader_to_session_lookup: Dict[str, str] = {}  # trader -> session
        self.user_roles: Dict[str, TraderRole] = {}  # username -> role
        self.session_locks = {}
        self.session_ready_traders: Dict[str, Set[str]] = {}  # session -> ready traders
        self.user_historical_sessions: Dict[str, Set[str]] = {}  # username -> past sessions
        
    async def assign_role_and_goal(self, gmail_username: str, params: TradingParameters) -> tuple[TraderRole, int]:
        """assign role and goal based on total users"""
        # if role exists, keep it
        if gmail_username in self.user_roles:
            role = self.user_roles[gmail_username]
            # find goal for role
            goals = [g for g in params.predefined_goals if (g != 0) == (role == TraderRole.INFORMED)]
            goal = abs(random.choice(goals))
            if params.allow_random_goals and role == TraderRole.INFORMED:
                goal *= random.choice([-1, 1])
            return role, goal
        
        # count users for position
        total_active_users = sum(len(users) for users in self.active_users.values())
        position = total_active_users % len(params.predefined_goals)
        
        # set role and goal
        goal = params.predefined_goals[position]
        role = TraderRole.INFORMED if goal != 0 else TraderRole.SPECULATOR
        
        # store role
        self.user_roles[gmail_username] = role
        
        # random sign if enabled
        if role == TraderRole.INFORMED and params.allow_random_goals:
            goal *= random.choice([-1, 1])
            
        return role, goal

    async def find_or_create_session(self, gmail_username: str, params: TradingParameters) -> tuple[str, str, TraderRole, int]:
        """find session and assign role or make new one"""
        trader_id = f"HUMAN_{gmail_username}"
        max_retries = 4
        retry_count = 0
        
        # get existing role if any
        existing_role = self.user_roles.get(gmail_username)
        
        while retry_count < max_retries:
            # look at current sessions
            for session_id, manager in self.trader_managers.items():
                if manager.trading_session.trading_started:
                    continue
                    
                session_users = self.active_users[session_id]
                if len(session_users) >= len(params.predefined_goals):
                    continue
                    
                # count roles
                informed_count = sum(1 for u in session_users if self.user_roles.get(u) == TraderRole.INFORMED)
                speculator_count = len(session_users) - informed_count
                
                # get needed numbers
                total_required = len(params.predefined_goals)
                required_informed = sum(1 for g in params.predefined_goals if g != 0)
                required_speculators = total_required - required_informed
                
                # pick role
                if existing_role:
                    role = existing_role
                    can_join = (
                        (role == TraderRole.INFORMED and informed_count < required_informed) or
                        (role == TraderRole.SPECULATOR and speculator_count < required_speculators)
                    )
                else:
                    # assign based on needs
                    if informed_count < required_informed:
                        role = TraderRole.INFORMED
                        can_join = True
                    elif speculator_count < required_speculators:
                        role = TraderRole.SPECULATOR
                        can_join = True
                    else:
                        can_join = False
                
                if can_join:
                    # pick goal
                    if role == TraderRole.INFORMED:
                        goal_candidates = [g for g in params.predefined_goals if g != 0]
                        goal = abs(random.choice(goal_candidates))
                        if params.allow_random_goals:
                            goal *= random.choice([-1, 1])
                    else:
                        goal = 0
                    
                    # save role
                    self.user_roles[gmail_username] = role
                    
                    try:
                        trader_id = await manager.add_human_trader(gmail_username, role=role, goal=goal)
                        self.trader_to_session_lookup[trader_id] = session_id
                        self.active_users[session_id].add(gmail_username)
                        self.user_sessions[gmail_username] = session_id
                        return session_id, trader_id, role, goal
                    except Exception:
                        continue
                
            await asyncio.sleep(0.5)
            retry_count += 1
        
        # make new session if needed
        # pick first role
        if not existing_role:
            first_goal = params.predefined_goals[0]
            role = TraderRole.INFORMED if first_goal != 0 else TraderRole.SPECULATOR
            self.user_roles[gmail_username] = role
            if role == TraderRole.INFORMED and params.allow_random_goals:
                first_goal *= random.choice([-1, 1])
        else:
            role = existing_role
            if role == TraderRole.INFORMED:
                goal_candidates = [g for g in params.predefined_goals if g != 0]
                first_goal = abs(random.choice(goal_candidates))
                if params.allow_random_goals:
                    first_goal *= random.choice([-1, 1])
            else:
                first_goal = 0
                
        session_id, trader_id = await self._create_new_session(gmail_username, role, first_goal, params)
        return session_id, trader_id, role, first_goal

    def get_trader_manager(self, trader_id: str) -> Optional[TraderManager]:
        """get manager for trader"""
        if trader_id not in self.trader_to_session_lookup:
            return None
        session_id = self.trader_to_session_lookup[trader_id]
        return self.trader_managers.get(session_id) 

    async def can_join_session(self, gmail_username: str, params: TradingParameters) -> bool:
        """check if user can join"""
        try:
            # check current session
            if gmail_username in self.user_sessions:
                session_id = self.user_sessions[gmail_username]
                if session_id in self.trader_managers:
                    trader_manager = self.trader_managers[session_id]
                    if not trader_manager.trading_session.trading_started:
                        return True
                        
            # check count
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
        """get role or none"""
        return self.user_roles.get(gmail_username)

    async def assign_user_goal(self, gmail_username: str, params: TradingParameters) -> int:
        """assign goal based on role"""
        role = self.user_roles.get(gmail_username)
        if not role:
            raise ValueError("User must have a role before assigning goal")
            
        # get index from count
        current_users = len(self.active_users.get(self.user_sessions.get(gmail_username, ''), set()))
        goal_index = current_users - 1  # -1 since current_users starts at 1
        
        # get from list
        if goal_index < len(params.predefined_goals):
            goal = params.predefined_goals[goal_index]
            
            # set role from goal
            if goal != 0:
                self.user_roles[gmail_username] = TraderRole.INFORMED
                # random flip if allowed
                if params.allow_random_goals:
                    goal *= random.choice([-1, 1])
            else:
                self.user_roles[gmail_username] = TraderRole.SPECULATOR
                
            return goal
        else:
            raise ValueError(f"No goal defined for trader {goal_index + 1}")

    def get_historical_sessions_count(self, username: str) -> int:
        """get past session count"""
        return len(self.user_historical_sessions.get(username, set()))

    def record_session_for_user(self, username: str, session_id: str):
        """add to history"""
        if username not in self.user_historical_sessions:
            self.user_historical_sessions[username] = set()
        self.user_historical_sessions[username].add(session_id)

    async def mark_trader_ready(self, trader_id: str, session_id: str) -> bool:
        """mark ready and check all"""
        if session_id not in self.session_ready_traders:
            self.session_ready_traders[session_id] = set()
        
        self.session_ready_traders[session_id].add(trader_id)
        
        trader_manager = self.trader_managers.get(session_id)
        if trader_manager:
            num_required_traders = len(trader_manager.params.predefined_goals)
            return len(self.session_ready_traders[session_id]) >= num_required_traders
        return False

    async def validate_and_assign_role(self, gmail_username: str, params: TradingParameters) -> tuple[str, str, TraderRole, int]:
        """check and assign session"""
        can_join = await self.can_join_session(gmail_username, params)
        if not can_join:
            raise HTTPException(
                status_code=403,
                detail="Maximum number of allowed sessions reached"
            )
        
        # find and assign
        return await self.find_or_create_session(gmail_username, params)

    async def reset_state(self):
        """reset everything"""
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
        """remove from session"""
        if session_id not in self.active_users:
            self.active_users[session_id] = set()
        
        self.active_users[session_id].discard(gmail_username)
        
        if gmail_username in self.user_sessions:
            del self.user_sessions[gmail_username]
            
        trader_id = f"HUMAN_{gmail_username}"
        if trader_id in self.trader_to_session_lookup:
            del self.trader_to_session_lookup[trader_id]

    def add_user_to_session(self, gmail_username: str, session_id: str):
        """add to session"""
        if session_id not in self.active_users:
            self.active_users[session_id] = set()
        self.active_users[session_id].add(gmail_username)

    async def _create_new_session(self, gmail_username: str, role: TraderRole, goal: int, params: TradingParameters) -> tuple[str, str]:
        """make new session"""
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