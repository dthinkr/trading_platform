from typing import Dict, Set, List
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
import random
import time
from datetime import datetime, timedelta


class SessionState(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"


class RoleType(Enum):
    INFORMED = "informed"
    SPECULATOR = "speculator"


@dataclass
class User:
    id: str
    role: RoleType = None  # Role is initially None, assigned when joining first session
    goal: int = 0
    current_session: str = None
    historical_sessions: Set[str] = None
    cooldown_time: int = 0

    def __post_init__(self):
        if self.historical_sessions is None:
            self.historical_sessions = set()

    @property
    def is_available(self):
        return self.current_session is None and self.cooldown_time <= 0

    @property
    def is_new(self):
        """Check if user has never joined a session."""
        return not self.historical_sessions and self.role is None


@dataclass
class Session:
    id: str
    capacity: int = 3
    start_time: int = None
    duration: int = 20
    state: SessionState = SessionState.PENDING
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
        return not self.informed_locked and self.state == SessionState.PENDING


def simulate_fixed_traders():
    # Initialize fixed set of users with no roles
    users = {f"user_{i}": User(id=f"user_{i}") for i in range(1, 6)}

    sessions: Dict[str, Session] = {}
    all_historical_sessions: Set[str] = set()  # Track all session IDs ever created
    next_session_id = 1

    def create_session() -> Session:
        nonlocal next_session_id
        # Keep incrementing until we find an unused ID
        while f"session_{next_session_id}" in all_historical_sessions:
            next_session_id += 1

        session_id = f"session_{next_session_id}"
        next_session_id += 1

        session = Session(id=session_id)
        sessions[session_id] = session
        all_historical_sessions.add(session_id)  # Add to historical record
        print(f"Created session {session_id}")
        return session

    def assign_role(user: User, session: Session) -> RoleType:
        """Assign role to a new user based on session needs."""
        if not user.is_new:
            return user.role

        # If session needs informed and no other informed exists
        if session.needs_informed:
            user.role = RoleType.INFORMED
            user.goal = random.choice([-60, 60])  # Random positive or negative goal
        else:
            user.role = RoleType.SPECULATOR
            user.goal = 0

        print(f"Assigned {user.id} as {user.role.value} with goal {user.goal}")
        return user.role

    def try_join_session(user_id: str, session_id: str) -> bool:
        user = users[user_id]
        session = sessions[session_id]

        # Calculate remaining slots before role assignment
        remaining_slots = session.capacity - len(session.traders)

        # If user is new, assign role based on session needs
        if user.is_new:
            # If this is the last slot and we need an informed trader,
            # force this user to be informed
            if remaining_slots == 1 and not session.informed_locked:
                user.role = RoleType.INFORMED
                user.goal = random.choice([-60, 60])
                print(f"Forced {user.id} as informed (last slot) with goal {user.goal}")
            else:
                role = assign_role(user, session)
        else:
            role = user.role

        # Check if role is compatible with session
        if role == RoleType.INFORMED:
            if session.informed_locked:
                return False  # Reject if session already has an informed trader
            session.informed_locked = True  # Lock informed slot when assigned
        else:  # SPECULATOR
            # Don't allow speculator to join if they would block the informed slot
            if not session.informed_locked and remaining_slots <= 1:
                print(f"Rejected speculator {user.id} to reserve slot for informed trader")
                return False

        session.traders.add(user_id)
        user.current_session = session_id
        print(f"User {user_id} ({user.role.value}) joined session {session_id}")

        if len(session.traders) == session.capacity:
            start_session(session_id, current_time)

        return True

    def leave_session(user_id: str, current_time: int):
        user = users[user_id]
        if not user.current_session:
            return

        session = sessions[user.current_session]
        session.traders.remove(user_id)

        if user.role == RoleType.INFORMED:
            session.informed_locked = False

        user.historical_sessions.add(user.current_session)
        user.current_session = None
        user.cooldown_time = current_time + random.randint(5, 10)

        print(f"User {user_id} left session {session.id}")

        if session.state == SessionState.ACTIVE and not session.is_viable:
            terminate_session(session.id)

    def start_session(session_id: str, current_time: int):
        session = sessions[session_id]
        if not session.informed_locked:
            print(f"Cannot start session {session_id} without informed trader")
            return

        session.start_time = current_time
        session.state = SessionState.ACTIVE
        print(f"\nSession {session_id} started at time {current_time}")
        print("Traders:", {uid: users[uid].role.value for uid in session.traders})

    def terminate_session(session_id: str):
        session = sessions[session_id]
        print(f"\nTerminating session {session_id}")

        for trader_id in list(session.traders):
            leave_session(trader_id, current_time)

        session.state = SessionState.COMPLETED

    def validate_conditions():
        """Validate our two key conditions:
        1. Each active session has exactly one informed trader
        2. Users maintain consistent roles across sessions
        """
        violations = []

        # Check active sessions for informed trader count
        for session_id, session in sessions.items():
            if session.state == SessionState.ACTIVE:
                informed_count = sum(
                    1 for uid in session.traders if users[uid].role == RoleType.INFORMED
                )
                if informed_count != 1:
                    violations.append(
                        f"Violation: Session {session_id} has {informed_count} informed traders"
                    )

        # Check role consistency for all users
        for user_id, user in users.items():
            if user.role is not None:  # Skip unassigned users
                original_role = user.role
                sessions_participated = (
                    user.historical_sessions | {user.current_session}
                    if user.current_session
                    else user.historical_sessions
                )
                for session_id in sessions_participated:
                    if session_id and session_id in sessions:
                        if user_id in sessions[session_id].traders:
                            if user.role != original_role:
                                violations.append(
                                    f"Violation: User {user_id} changed role from {original_role} to {user.role}"
                                )

        return violations

    # Run simulation
    print("\nStarting long-term simulation...\n")

    current_time = 0
    max_time = 10000  # Much longer simulation time
    Session.duration = 50  # Moderate session length

    create_session()

    while current_time < max_time:
        # Update cooldowns
        for user in users.values():
            if user.cooldown_time > 0:
                user.cooldown_time -= 1

        # Create new session only if all existing sessions are either full or active
        all_sessions_busy = all(
            session.is_full or session.state != SessionState.PENDING
            for session in sessions.values()
        )
        if all_sessions_busy:
            create_session()

        # Random user actions
        for user_id, user in users.items():
            if user.current_session:
                # Increased chance to leave session
                if random.random() < 0.05:  # 5% chance to leave
                    leave_session(user_id, current_time)
            elif user.is_available:
                # Increased chance to join session
                if random.random() < 0.3:  # 30% chance to try joining when available
                    available_sessions = [
                        s.id
                        for s in sessions.values()
                        if s.state == SessionState.PENDING and not s.is_full
                    ]
                    if available_sessions:
                        oldest_session = min(available_sessions)
                        try_join_session(user_id, oldest_session)

        # Clean up completed sessions
        completed_sessions = [
            session_id
            for session_id, session in sessions.items()
            if session.state == SessionState.COMPLETED and not session.traders
        ]
        for session_id in completed_sessions:
            del sessions[session_id]

        # Check session completions
        for session in list(sessions.values()):
            if (
                session.state == SessionState.ACTIVE
                and current_time >= session.start_time + session.duration
            ):
                terminate_session(session.id)

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
        print(f"Total sessions created: {len(all_historical_sessions)}")
        print(
            f"Active sessions: {sum(1 for s in sessions.values() if s.state == SessionState.ACTIVE)}"
        )
        print("\nUser Activity Summary:")
        for user_id, user in users.items():
            print(f"{user_id} ({user.role.value if user.role else 'unassigned'}):")
            print(f"  Participated in {len(user.historical_sessions)} sessions")
            if len(user.historical_sessions) > 0:
                print(
                    f"  Average sessions per 1000 time units: {len(user.historical_sessions) * 1000 / max_time:.2f}"
                )
    else:
        print("✗ Found violations:")
        for violation in final_violations:
            print(violation)


if __name__ == "__main__":
    simulate_fixed_traders()
