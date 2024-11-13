from typing import Dict, Set, List
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
import random
import time
from datetime import datetime, timedelta


class MarketState(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"


class RoleType(Enum):
    INFORMED = "informed"
    SPECULATOR = "speculator"


@dataclass
class User:
    id: str
    role: RoleType = None  # Role is initially None, assigned when joining first market
    goal: int = 0
    current_market: str = None
    historical_markets: Set[str] = None
    cooldown_time: int = 0

    def __post_init__(self):
        if self.historical_markets is None:
            self.historical_markets = set()

    @property
    def is_available(self):
        return self.current_market is None and self.cooldown_time <= 0

    @property
    def is_new(self):
        """Check if user has never joined a market."""
        return not self.historical_markets and self.role is None


@dataclass
class Market:
    id: str
    capacity: int = 3
    start_time: int = None
    duration: int = 20
    state: MarketState = MarketState.PENDING
    informed_locked: bool = False
    traders: Set[str] = None
    min_traders: int = 2

    def __post_init__(self):
        if self.traders is None:
            self.traders = set()

    @property
    def is_full(self):
        return len(self.traders) >= self.capacity

    @property
    def is_viable(self):
        return len(self.traders) >= self.min_traders

    @property
    def needs_informed(self):
        return not self.informed_locked and self.state == MarketState.PENDING


def simulate_fixed_traders():
    # Initialize fixed set of users with no roles
    users = {f"user_{i}": User(id=f"user_{i}") for i in range(1, 6)}

    markets: Dict[str, Market] = {}
    all_historical_markets: Set[str] = set()  # Track all market IDs ever created
    next_market_id = 1

    def create_market() -> Market:
        nonlocal next_market_id
        # Keep incrementing until we find an unused ID
        while f"market_{next_market_id}" in all_historical_markets:
            next_market_id += 1

        market_id = f"market_{next_market_id}"
        next_market_id += 1

        market = Market(id=market_id)
        markets[market_id] = market
        all_historical_markets.add(market_id)  # Add to historical record
        print(f"Created market {market_id}")
        return market

    def assign_role(user: User, market: Market) -> RoleType:
        """Assign role to a new user based on market needs."""
        if not user.is_new:
            return user.role

        # If market needs informed and no other informed exists
        if market.needs_informed:
            user.role = RoleType.INFORMED
            user.goal = random.choice([-60, 60])  # Random positive or negative goal
        else:
            user.role = RoleType.SPECULATOR
            user.goal = 0

        print(f"Assigned {user.id} as {user.role.value} with goal {user.goal}")
        return user.role

    def try_join_market(user_id: str, market_id: str) -> bool:
        user = users[user_id]
        market = markets[market_id]

        # Calculate remaining slots before role assignment
        remaining_slots = market.capacity - len(market.traders)

        # If user is new, assign role based on market needs
        if user.is_new:
            # If this is the last slot and we need an informed trader,
            # force this user to be informed
            if remaining_slots == 1 and not market.informed_locked:
                user.role = RoleType.INFORMED
                user.goal = random.choice([-60, 60])
                print(f"Forced {user.id} as informed (last slot) with goal {user.goal}")
            else:
                role = assign_role(user, market)
        else:
            role = user.role

        # Check if role is compatible with market
        if role == RoleType.INFORMED:
            if market.informed_locked:
                return False  # Reject if market already has an informed trader
            market.informed_locked = True  # Lock informed slot when assigned
        else:  # SPECULATOR
            # Don't allow speculator to join if they would block the informed slot
            if not market.informed_locked and remaining_slots <= 1:
                print(f"Rejected speculator {user.id} to reserve slot for informed trader")
                return False

        market.traders.add(user_id)
        user.current_market = market_id
        print(f"User {user_id} ({user.role.value}) joined market {market_id}")

        if len(market.traders) == market.capacity:
            start_market(market_id, current_time)

        return True

    def leave_market(user_id: str, current_time: int):
        user = users[user_id]
        if not user.current_market:
            return

        market = markets[user.current_market]
        market.traders.remove(user_id)

        if user.role == RoleType.INFORMED:
            market.informed_locked = False

        user.historical_markets.add(user.current_market)
        user.current_market = None
        user.cooldown_time = current_time + random.randint(5, 10)

        print(f"User {user_id} left market {market.id}")

        if market.state == MarketState.ACTIVE and not market.is_viable:
            terminate_market(market.id)

    def start_market(market_id: str, current_time: int):
        market = markets[market_id]
        if not market.informed_locked:
            print(f"Cannot start market {market_id} without informed trader")
            return

        market.start_time = current_time
        market.state = MarketState.ACTIVE
        print(f"\nMarket {market_id} started at time {current_time}")
        print("Traders:", {uid: users[uid].role.value for uid in market.traders})

    def terminate_market(market_id: str):
        market = markets[market_id]
        print(f"\nTerminating market {market_id}")

        for trader_id in list(market.traders):
            leave_market(trader_id, current_time)

        market.state = MarketState.COMPLETED

    def validate_conditions():
        """Validate our two key conditions:
        1. Each active market has exactly one informed trader
        2. Users maintain consistent roles across markets
        """
        violations = []

        # Check active markets for informed trader count
        for market_id, market in markets.items():
            if market.state == MarketState.ACTIVE:
                informed_count = sum(
                    1 for uid in market.traders if users[uid].role == RoleType.INFORMED
                )
                if informed_count != 1:
                    violations.append(
                        f"Violation: Market {market_id} has {informed_count} informed traders"
                    )

        # Check role consistency for all users
        for user_id, user in users.items():
            if user.role is not None:  # Skip unassigned users
                original_role = user.role
                markets_participated = (
                    user.historical_markets | {user.current_market}
                    if user.current_market
                    else user.historical_markets
                )
                for market_id in markets_participated:
                    if market_id and market_id in markets:
                        if user_id in markets[market_id].traders:
                            if user.role != original_role:
                                violations.append(
                                    f"Violation: User {user_id} changed role from {original_role} to {user.role}"
                                )

        return violations

    # Run simulation
    print("\nStarting long-term simulation...\n")

    current_time = 0
    max_time = 10000  # Much longer simulation time
    Market.duration = 50  # Moderate market length

    create_market()

    while current_time < max_time:
        # Update cooldowns
        for user in users.values():
            if user.cooldown_time > 0:
                user.cooldown_time -= 1

        # Create new market only if all existing markets are either full or active
        all_markets_busy = all(
            market.is_full or market.state != MarketState.PENDING
            for market in markets.values()
        )
        if all_markets_busy:
            create_market()

        # Random user actions
        for user_id, user in users.items():
            if user.current_market:
                # Increased chance to leave market
                if random.random() < 0.05:  # 5% chance to leave
                    leave_market(user_id, current_time)
            elif user.is_available:
                # Increased chance to join market
                if random.random() < 0.3:  # 30% chance to try joining when available
                    available_markets = [
                        s.id
                        for s in markets.values()
                        if s.state == MarketState.PENDING and not s.is_full
                    ]
                    if available_markets:
                        oldest_market = min(available_markets)
                        try_join_market(user_id, oldest_market)

        # Clean up completed markets
        completed_markets = [
            market_id
            for market_id, market in markets.items()
            if market.state == MarketState.COMPLETED and not market.traders
        ]
        for market_id in completed_markets:
            del markets[market_id]

        # Check market completions
        for market in list(markets.values()):
            if (
                market.state == MarketState.ACTIVE
                and current_time >= market.start_time + market.duration
            ):
                terminate_market(market.id)

        # Validate conditions every 500 time units instead of 100
        if current_time % 500 == 0:
            violations = validate_conditions()
            if violations:
                print(f"\nTime {current_time} - Found violations:")
                for violation in violations:
                    print(violation)

        current_time += 1

    # Enhanced final statistics
    print("\nFinal Validation:")
    final_violations = validate_conditions()
    if not final_violations:
        print("✓ All conditions satisfied throughout simulation")
        print("\nFinal State Summary:")
        print(f"Total markets created: {len(all_historical_markets)}")
        print(
            f"Active markets: {sum(1 for s in markets.values() if s.state == MarketState.ACTIVE)}"
        )
        print("\nUser Activity Summary:")
        for user_id, user in users.items():
            print(f"{user_id} ({user.role.value if user.role else 'unassigned'}):")
            print(f"  Participated in {len(user.historical_markets)} markets")
            if len(user.historical_markets) > 0:
                print(
                    f"  Average markets per 1000 time units: {len(user.historical_markets) * 1000 / max_time:.2f}"
                )
    else:
        print("✗ Found violations:")
        for violation in final_violations:
            print(violation)


if __name__ == "__main__":
    simulate_fixed_traders()
