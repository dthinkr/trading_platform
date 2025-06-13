import time
import uuid
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from .data_models import TradingParameters, TraderRole
from .market_handler import MarketHandler


@dataclass
class WaitingUser:
    """Represents a user waiting in a session"""
    username: str
    is_prolific: bool
    joined_at: float
    

@dataclass
class Session:
    """Represents a waiting room session"""
    session_id: str
    users: List[WaitingUser]
    created_at: float
    required_players: int
    
    @property
    def is_full(self) -> bool:
        return len(self.users) >= self.required_players
    
    @property
    def current_players(self) -> int:
        return len(self.users)
    
    @property
    def waiting_for(self) -> int:
        return max(0, self.required_players - len(self.users))


class WaitingRoom:
    """Manages waiting room sessions and user assignments"""
    
    def __init__(self, market_handler: MarketHandler):
        self.market_handler = market_handler
        self.sessions: Dict[str, Session] = {}
        self.user_to_session: Dict[str, str] = {}
        self.user_assignments: Dict[str, Dict] = {}  # Track completed assignments
        self.session_counter = 0
        
    async def join_waiting_room(self, username: str, is_prolific: bool, params: TradingParameters) -> Tuple[str, Dict]:
        """
        Join a user to the waiting room.
        Returns (session_id, session_data)
        """
        # Remove user from any existing session first
        self._remove_user_from_session(username)
        
        required_players = len(params.predefined_goals)
        
        # Find an existing session that needs players
        session_id = self._find_available_session(required_players)
        
        if session_id is None:
            # Create new session
            session_id = self._create_new_session(required_players)
        
        # Add user to session
        session = self.sessions[session_id]
        user = WaitingUser(
            username=username,
            is_prolific=is_prolific,
            joined_at=time.time()
        )
        
        session.users.append(user)
        self.user_to_session[username] = session_id
        
        print(f"Added {username} to {session_id}. Players: {session.current_players}/{session.required_players}")
        
        # Check if session is ready
        if session.is_full:
            return await self._start_session(session_id, params)
        else:
            return session_id, {
                "session_ready": False,
                "session_id": session_id,
                "current_players": session.current_players,
                "required_players": session.required_players,
                "waiting_for": session.waiting_for
            }
    
    def get_user_status(self, username: str, params: TradingParameters) -> Dict:
        """Get the current waiting room status for a user"""
        # Check if user has a completed assignment
        if username in self.user_assignments:
            assignment = self.user_assignments[username]
            return {
                "in_waiting_room": False,
                "assigned_to_market": True,
                "session_ready": True,
                "market_id": assignment["market_id"],
                "trader_id": assignment["trader_id"],
                "role": assignment["role"],
                "goal": assignment["goal"]
            }
        
        # Check if user is in an active session
        session_id = self.user_to_session.get(username)
        
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            return {
                "in_waiting_room": True,
                "assigned_to_market": False,
                "session_id": session_id,
                "current_players": session.current_players,
                "required_players": session.required_players,
                "waiting_for": session.waiting_for,
                "players": [u.username for u in session.users]
            }
        
        return {
            "in_waiting_room": False,
            "assigned_to_market": False
        }
    
    def remove_user(self, username: str) -> None:
        """Remove a user from any waiting room session"""
        self._remove_user_from_session(username)
    
    def _find_available_session(self, required_players: int) -> Optional[str]:
        """Find an existing session that needs players"""
        for session_id, session in self.sessions.items():
            if not session.is_full and session.required_players == required_players:
                return session_id
        return None
    
    def _create_new_session(self, required_players: int) -> str:
        """Create a new waiting room session"""
        self.session_counter += 1
        session_id = f"SESSION_{self.session_counter}"
        
        session = Session(
            session_id=session_id,
            users=[],
            created_at=time.time(),
            required_players=required_players
        )
        
        self.sessions[session_id] = session
        print(f"Created new session: {session_id}")
        return session_id
    
    async def _start_session(self, session_id: str, params: TradingParameters) -> Tuple[str, Dict]:
        """Start a session when it's full"""
        session = self.sessions[session_id]
        
        try:
            # Create market for this session
            market_id, assigned_traders = await self._assign_session_to_market(session, params)
            
            print(f"Session {session_id} ready! Assigned to market {market_id}")
            
            # Store assignments for later retrieval
            for trader in assigned_traders:
                self.user_assignments[trader["username"]] = {
                    "market_id": market_id,
                    "trader_id": trader["trader_id"],
                    "role": trader["role"],
                    "goal": trader["goal"],
                    "assigned_at": time.time()
                }
            
            # Clean up session
            self._cleanup_session(session_id)
            
            return session_id, {
                "session_ready": True,
                "session_id": session_id,
                "market_id": market_id,
                "assigned_traders": assigned_traders,
                "total_players": len(assigned_traders)
            }
            
        except Exception as e:
            print(f"Error starting session {session_id}: {str(e)}")
            raise e
    
    async def _assign_session_to_market(self, session: Session, params: TradingParameters) -> Tuple[str, List[Dict]]:
        """Assign all users in a session to a single trading market"""
        # Create unique market ID for this session
        market_id = f"MARKET_{session.session_id}_{uuid.uuid4().hex[:8]}"
        
        assigned_traders = []
        goals = params.predefined_goals.copy()
        
        print(f"Creating market {market_id} for session {session.session_id}")
        
        # First, assign all users and collect their assignments
        for i, user in enumerate(session.users):
            # Assign goal (cycle through available goals)
            goal = goals[i % len(goals)] if goals else 0
            
            # Determine role based on goal
            role = TraderRole.INFORMED if goal != 0 else TraderRole.SPECULATOR
            
            # Use market handler to create the trader assignment
            market_id_assigned, trader_id_assigned, role_assigned, goal_assigned = await self.market_handler.validate_and_assign_role(
                user.username, params, preferred_market_id=market_id, preferred_goal=goal
            )
            
            assigned_traders.append({
                "username": user.username,
                "trader_id": trader_id_assigned,
                "role": role_assigned.value if hasattr(role_assigned, 'value') else str(role_assigned),
                "goal": goal_assigned,
                "is_prolific": user.is_prolific
            })
            
            print(f"Assigned {user.username} to market {market_id_assigned} with goal {goal_assigned}")
        
        # Ensure the market is fully initialized before returning
        # Wait a moment for all traders to be properly created
        import asyncio
        await asyncio.sleep(0.1)  # Small delay to ensure market initialization
        
        # Verify all traders are actually created and accessible
        trader_manager = self.market_handler.get_trader_manager(assigned_traders[0]["trader_id"])
        if not trader_manager:
            raise Exception(f"Market {market_id} was not properly initialized")
        
        # Verify all traders exist in the market
        for trader_info in assigned_traders:
            trader = trader_manager.get_trader(trader_info["trader_id"])
            if not trader:
                raise Exception(f"Trader {trader_info['trader_id']} was not properly created in market {market_id}")
        
        print(f"Market {market_id} fully initialized with {len(assigned_traders)} traders")
        return market_id, assigned_traders
    
    def _remove_user_from_session(self, username: str) -> None:
        """Remove user from their current session"""
        session_id = self.user_to_session.get(username)
        
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            session.users = [u for u in session.users if u.username != username]
            
            # Clean up empty sessions
            if not session.users:
                del self.sessions[session_id]
                print(f"Removed empty session: {session_id}")
        
        if username in self.user_to_session:
            del self.user_to_session[username]
    
    def _cleanup_session(self, session_id: str) -> None:
        """Clean up a completed session"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            
            # Remove all users from user_to_session mapping
            for user in session.users:
                if user.username in self.user_to_session:
                    del self.user_to_session[user.username]
            
            # Remove the session
            del self.sessions[session_id]
            print(f"Cleaned up completed session: {session_id}")
    
    def get_all_sessions(self) -> List[Dict]:
        """Get all current sessions for monitoring"""
        return [
            {
                "session_id": session.session_id,
                "current_players": session.current_players,
                "required_players": session.required_players,
                "users": [u.username for u in session.users],
                "created_at": session.created_at
            }
            for session in self.sessions.values()
        ]
    
    def cleanup_stale_sessions(self, max_age_seconds: int = 3600) -> None:
        """Remove sessions that are too old"""
        current_time = time.time()
        stale_sessions = []
        
        for session_id, session in self.sessions.items():
            if current_time - session.created_at > max_age_seconds:
                stale_sessions.append(session_id)
        
        for session_id in stale_sessions:
            print(f"Cleaning up stale session: {session_id}")
            self._cleanup_session(session_id)
    
    def cleanup_stale_assignments(self, max_age_seconds: int = 7200) -> None:
        """Remove old user assignments (2 hours by default)"""
        current_time = time.time()
        stale_users = []
        
        for username, assignment in self.user_assignments.items():
            if current_time - assignment.get("assigned_at", 0) > max_age_seconds:
                stale_users.append(username)
        
        for username in stale_users:
            print(f"Cleaning up stale assignment for user: {username}")
            del self.user_assignments[username] 