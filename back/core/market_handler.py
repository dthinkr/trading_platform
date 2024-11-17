from typing import Dict, Set, Optional
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
        max_retries = 4
        retry_count = 0
        
        # get existing role if any
        existing_role = self.user_roles.get(gmail_username)
        
        while retry_count < max_retries:
            # Check recently created markets first
            current_time = datetime.now()
            recently_created = False
            if self.last_market_creation and (current_time - self.last_market_creation) < self.market_creation_cooldown:
                recently_created = True
                
            # Sort markets to prioritize recently created ones
            sorted_markets = sorted(
                self.trader_managers.items(),
                key=lambda x: x[1].trading_market.id,
                reverse=True
            )
            
            for market_id, manager in sorted_markets:
                if manager.trading_market.trading_started:
                    continue
                    
                market_users = self.active_users[market_id]
                
                # Get required traders count from goals
                total_required = len(params.predefined_goals)
                
                if len(market_users) >= total_required:
                    continue
                    
                # Pick role and goal based on position
                position = len(market_users)
                if position < len(params.predefined_goals):
                    goal = params.predefined_goals[position]
                    role = TraderRole.INFORMED if goal != 0 else TraderRole.SPECULATOR
                    
                    # Save role
                    self.user_roles[gmail_username] = role
                    
                    # Random flip if allowed
                    if role == TraderRole.INFORMED and params.allow_random_goals:
                        goal *= random.choice([-1, 1])
                        
                    try:
                        trader_id = await manager.add_human_trader(gmail_username, role=role, goal=goal)
                        self.trader_to_market_lookup[trader_id] = market_id
                        self.active_users[market_id].add(gmail_username)
                        self.user_markets[gmail_username] = market_id
                        return market_id, trader_id, role, goal
                    except Exception:
                        continue
            
            # Only create new market if not in cooldown period
            if not recently_created:
                # Create new market with first role/goal
                role = TraderRole.INFORMED if params.predefined_goals[0] != 0 else TraderRole.SPECULATOR
                goal = params.predefined_goals[0]
                
                if role == TraderRole.INFORMED and params.allow_random_goals:
                    goal *= random.choice([-1, 1])
                    
                self.user_roles[gmail_username] = role
                
                market_id, trader_id = await self._create_new_market(gmail_username, role, goal, params)
                self.last_market_creation = datetime.now()
                return market_id, trader_id, role, goal
                
            await asyncio.sleep(0.5)
            retry_count += 1
        
        # If all else fails, create new market
        role = TraderRole.INFORMED if params.predefined_goals[0] != 0 else TraderRole.SPECULATOR
        goal = params.predefined_goals[0]
        
        if role == TraderRole.INFORMED and params.allow_random_goals:
            goal *= random.choice([-1, 1])
            
        market_id, trader_id = await self._create_new_market(gmail_username, role, goal, params)
        self.last_market_creation = datetime.now()
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