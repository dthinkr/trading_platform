from typing import Dict, Set, Optional, List
from collections import deque
from .data_models import TraderRole, TradingParameters
from .trader_manager import TraderManager
from utils import setup_custom_logger
from fastapi import HTTPException
import random
import asyncio
from datetime import datetime, timedelta

class MarketHandler:
    def __init__(self):
        # maps for tracking markets and users
        self.trader_managers: Dict[str, TraderManager] = {}
        self.active_users: Dict[str, Set[str]] = {}  # market -> usernames
        self.user_markets: Dict[str, str] = {}  # username -> market
        self.trader_to_market_lookup: Dict[str, str] = {}  # trader -> market
        self.user_roles: Dict[str, TraderRole] = {}  # username -> role
        self.market_locks = {}
        self.market_ready_traders: Dict[str, Set[str]] = {}  # market -> ready traders
        self.user_historical_markets: Dict[str, Set[str]] = {}  # username -> past markets
        self.last_market_creation: Optional[datetime] = None
        self.market_creation_cooldown = timedelta(seconds=2)  # 2 second cooldown
        self.waiting_traders = deque()  # Add trader queue
        self.market_goals: Dict[str, List[int]] = {}  # Track remaining goals per market
        
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

    async def find_or_create_market(self, gmail_username: str, params: TradingParameters) -> tuple[str, str, TraderRole, int]:
        """find market and assign role or make new one"""
        trader_id = f"HUMAN_{gmail_username}"
        required_traders = len(params.predefined_goals)
        
        # Add trader to waiting queue if not already in a market
        if trader_id not in self.trader_to_market_lookup:
            self.waiting_traders.append((gmail_username, trader_id))
        
        # Wait until we have enough traders to form a complete market
        while len(self.waiting_traders) < required_traders:
            await asyncio.sleep(0.5)  # Wait for more traders
            
            # Check if we're still in queue (handle edge cases like disconnects)
            if (gmail_username, trader_id) not in self.waiting_traders:
                raise HTTPException(
                    status_code=500,
                    detail="Trader removed from queue unexpectedly"
                )
        
        # If this trader is not in the first 'required_traders' positions, keep waiting
        first_batch = list(self.waiting_traders)[:required_traders]
        if (gmail_username, trader_id) not in first_batch:
            while (gmail_username, trader_id) in self.waiting_traders:
                await asyncio.sleep(0.5)
            raise HTTPException(
                status_code=500,
                detail="Trader queue position lost"
            )
        
        # If this is the first trader in queue, create market and assign all traders
        if self.waiting_traders[0] == (gmail_username, trader_id):
            # Create new market
            role = TraderRole.INFORMED if params.predefined_goals[0] != 0 else TraderRole.SPECULATOR
            goal = params.predefined_goals[0]
            if role == TraderRole.INFORMED and params.allow_random_goals:
                goal *= random.choice([-1, 1])
            
            market_id, first_trader_id = await self._create_new_market(gmail_username, role, goal, params)
            self.last_market_creation = datetime.now()
            
            # Assign remaining traders from the batch
            for i in range(1, required_traders):
                next_gmail, _ = self.waiting_traders[i]
                next_goal = params.predefined_goals[i]
                next_role = TraderRole.INFORMED if next_goal != 0 else TraderRole.SPECULATOR
                
                if next_role == TraderRole.INFORMED and params.allow_random_goals:
                    next_goal *= random.choice([-1, 1])
                
                next_trader_id = await self.trader_managers[market_id].add_human_trader(
                    next_gmail,
                    role=next_role,
                    goal=next_goal
                )
                
                self.trader_to_market_lookup[next_trader_id] = market_id
                self.active_users[market_id].add(next_gmail)
                self.user_markets[next_gmail] = market_id
                self.user_roles[next_gmail] = next_role
            
            # Remove the batch from queue
            for _ in range(required_traders):
                self.waiting_traders.popleft()
            
            return market_id, first_trader_id, role, goal
            
        # If not first trader, get our assignment from the batch
        position = first_batch.index((gmail_username, trader_id))
        goal = params.predefined_goals[position]
        role = TraderRole.INFORMED if goal != 0 else TraderRole.SPECULATOR
        
        if role == TraderRole.INFORMED and params.allow_random_goals:
            goal *= random.choice([-1, 1])
            
        # Market ID will be set by first trader
        while trader_id not in self.trader_to_market_lookup:
            await asyncio.sleep(0.1)
            
        market_id = self.trader_to_market_lookup[trader_id]
        return market_id, trader_id, role, goal

    def get_trader_manager(self, trader_id: str) -> Optional[TraderManager]:
        """get manager for trader"""
        if trader_id not in self.trader_to_market_lookup:
            return None
        market_id = self.trader_to_market_lookup[trader_id]
        return self.trader_managers.get(market_id) 

    async def can_join_market(self, gmail_username: str, params: TradingParameters) -> bool:
        """check if user can join"""
        try:
            # Check current market - allow if already in an unstarted market
            if gmail_username in self.user_markets:
                market_id = self.user_markets[gmail_username]
                if market_id in self.trader_managers:
                    trader_manager = self.trader_managers[market_id]
                    if not trader_manager.trading_market.trading_started:
                        return True
        
            # Get admin status from params
            admin_users = params.admin_users or []
            if gmail_username in admin_users:
                return True  # Always allow admin users
                    
            # Only check historical market count for non-admin users
            historical_markets_count = len(self.user_historical_markets.get(gmail_username, set()))
            print(f"historical_markets_count: {historical_markets_count}")
            return historical_markets_count < params.max_markets_per_human
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error checking market limits: {str(e)}"
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
        current_users = len(self.active_users.get(self.user_markets.get(gmail_username, ''), set()))
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

    def get_historical_markets_count(self, username: str) -> int:
        """get past market count"""
        return len(self.user_historical_markets.get(username, set()))

    def record_market_for_user(self, username: str, market_id: str):
        """add to history"""
        if username not in self.user_historical_markets:
            self.user_historical_markets[username] = set()
        self.user_historical_markets[username].add(market_id)

    async def mark_trader_ready(self, trader_id: str, market_id: str) -> bool:
        """mark ready and check all"""
        if market_id not in self.market_ready_traders:
            self.market_ready_traders[market_id] = set()
        
        self.market_ready_traders[market_id].add(trader_id)
        
        trader_manager = self.trader_managers.get(market_id)
        if trader_manager:
            num_required_traders = len(trader_manager.params.predefined_goals)
            return len(self.market_ready_traders[market_id]) >= num_required_traders
        return False

    async def validate_and_assign_role(self, gmail_username: str, params: TradingParameters) -> tuple[str, str, TraderRole, int]:
        """check and assign market"""
        can_join = await self.can_join_market(gmail_username, params)
        if not can_join:
            raise HTTPException(
                status_code=403,
                detail="Maximum number of allowed markets reached"
            )
        
        # find and assign
        return await self.find_or_create_market(gmail_username, params)

    async def reset_state(self):
        """reset everything"""
        try:
            market_ids = list(self.trader_managers.keys())
            
            for market_id in market_ids:
                trader_manager = self.trader_managers[market_id]
                try:
                    await trader_manager.cleanup()
                except Exception:
                    pass

            self.trader_managers.clear()
            self.active_users.clear()
            self.user_markets.clear()
            self.trader_to_market_lookup.clear()
            self.user_roles.clear()
            self.market_locks.clear()
            self.market_ready_traders.clear()
            self.user_historical_markets.clear()  
            self.waiting_traders.clear()
            self.market_goals.clear()
            
            return True
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error resetting state: {str(e)}"
            )

    def remove_user_from_market(self, gmail_username: str, market_id: str):
        """remove from market and record if market was started"""
        # Get trader manager to check if market was started
        trader_id = f"HUMAN_{gmail_username}"
        trader_manager = self.trader_managers.get(market_id)
        
        # Record market if it was started
        if trader_manager and trader_manager.trading_market.trading_started:
            if gmail_username not in self.user_historical_markets:
                self.user_historical_markets[gmail_username] = set()
            self.user_historical_markets[gmail_username].add(market_id)
        
        # Existing removal logic
        if market_id not in self.active_users:
            self.active_users[market_id] = set()
        
        self.active_users[market_id].discard(gmail_username)
        
        if gmail_username in self.user_markets:
            del self.user_markets[gmail_username]
            
        if trader_id in self.trader_to_market_lookup:
            del self.trader_to_market_lookup[trader_id]

    def add_user_to_market(self, gmail_username: str, market_id: str):
        """add to market"""
        if market_id not in self.active_users:
            self.active_users[market_id] = set()
        self.active_users[market_id].add(gmail_username)

    async def _create_new_market(self, gmail_username: str, role: TraderRole, goal: int, params: TradingParameters) -> tuple[str, str]:
        """make new market"""
        try:
            new_trader_manager = TraderManager(params)
            market_id = new_trader_manager.trading_market.id
            self.trader_managers[market_id] = new_trader_manager
            self.active_users[market_id] = set()
            
            trader_id = await new_trader_manager.add_human_trader(
                gmail_username, 
                role=role,
                goal=goal
            )
            
            # Remove immediate recording of market
            # Only record when trading actually starts
            
            self.trader_to_market_lookup[trader_id] = market_id
            self.active_users[market_id].add(gmail_username)
            self.user_markets[gmail_username] = market_id
            
            return market_id, trader_id
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error creating trading market: {str(e)}"
            )