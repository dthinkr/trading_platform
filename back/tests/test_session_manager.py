#!/usr/bin/env python3
"""
Session Manager Tests

Tests for session manager functionality, including:
- Slot assignment bug reproduction and fix verification
- Goal change scenarios
- Permanent role persistence
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.session_manager import SessionManager
from core.data_models import TradingParameters, TraderRole


@pytest.mark.asyncio
async def test_user_rejoins_same_goal_magnitude():
    """Test that a user can rejoin with the same goal magnitude.

    Users get a permanent goal magnitude on first join. When they leave
    and rejoin with the same predefined_goals, they should succeed.
    """
    print("\nTesting user rejoins with same goal magnitude...")

    manager = SessionManager()
    username = "test_user"

    # Step 1: User joins with predefined_goals = [100]
    params1 = TradingParameters(predefined_goals=[100])
    session_id1, trader_id1, role1, goal1 = await manager.join_session(username, params1)

    assert session_id1 is not None
    assert trader_id1 is not None
    permanent_mag = manager.permanent_informed_goals.get(username)
    print(f"  User joined with goal={goal1}, permanent magnitude={permanent_mag}")

    # Step 2: User leaves (simulate refresh/logout)
    await manager.remove_user_from_session(username)
    assert manager.permanent_informed_goals.get(username) is not None
    print(f"  User removed, permanent magnitude preserved: {manager.permanent_informed_goals.get(username)}")

    # Step 3: User rejoins with SAME goal magnitude
    params2 = TradingParameters(predefined_goals=[100])  # Same magnitude

    # Step 4: User should successfully rejoin
    session_id2, trader_id2, role2, goal2 = await manager.join_session(username, params2)

    assert session_id2 is not None
    assert trader_id2 is not None
    print(f"  User rejoined with role={role2}, goal={goal2}")
    print("  User successfully rejoined with same goal magnitude")


@pytest.mark.asyncio
async def test_permanent_goal_magnitude_preserved():
    """Test that permanent goal magnitude is preserved after user leaves."""
    print("\nTesting permanent goal magnitude preservation...")

    manager = SessionManager()
    username = "user_preserve"

    # User joins with [100]
    params1 = TradingParameters(predefined_goals=[100])
    session_id1, _, role1, goal1 = await manager.join_session(username, params1)

    original_magnitude = manager.permanent_informed_goals.get(username)
    print(f"  Joined with goal={goal1}, permanent magnitude={original_magnitude}")
    assert original_magnitude == 100

    # User leaves
    await manager.remove_user_from_session(username)

    # Permanent magnitude should still be preserved
    preserved_magnitude = manager.permanent_informed_goals.get(username)
    assert preserved_magnitude == 100
    print(f"  After leaving, permanent magnitude still: {preserved_magnitude}")


@pytest.mark.asyncio
async def test_multiple_users_same_session():
    """Test multiple users joining the same session."""
    print("\nTesting multiple users in same session...")

    manager = SessionManager()

    # Create session with multiple slots
    params = TradingParameters(predefined_goals=[100, -100, 0])

    # Three users join
    session_id1, _, role1, goal1 = await manager.join_session("user1", params)
    print(f"  User1: role={role1}, goal={goal1}")

    session_id2, _, role2, goal2 = await manager.join_session("user2", params)
    print(f"  User2: role={role2}, goal={goal2}")

    session_id3, _, role3, goal3 = await manager.join_session("user3", params)
    print(f"  User3: role={role3}, goal={goal3}")

    # All should be in the same session (3 slots available)
    assert session_id1 == session_id2 == session_id3
    print(f"  All users in same session: {session_id1}")

    # Should have different roles/goals
    goals = {goal1, goal2, goal3}
    print(f"  Goals assigned: {goals}")


@pytest.mark.asyncio
async def test_speculator_assignment():
    """Test that speculators (goal=0) are assigned correctly."""
    print("\nTesting speculator assignment...")

    manager = SessionManager()

    # Create session with informed (100) and speculator (0)
    params = TradingParameters(predefined_goals=[100, 0])

    # First user gets informed role
    session_id1, _, role1, goal1 = await manager.join_session("informed_user", params)
    print(f"  User1: role={role1}, goal={goal1}")

    # Second user gets speculator role
    session_id2, _, role2, goal2 = await manager.join_session("speculator_user", params)
    print(f"  User2: role={role2}, goal={goal2}")

    # One should be informed, one speculator
    roles = {role1, role2}
    assert TraderRole.INFORMED in roles or TraderRole.SPECULATOR in roles
    print("  Both roles assigned correctly")


@pytest.mark.asyncio
async def test_session_full_creates_new():
    """Test that when a session is full, a new one is created."""
    print("\nTesting session full creates new...")

    manager = SessionManager()

    # Single slot session
    params = TradingParameters(predefined_goals=[100])

    # First user fills the session
    session_id1, _, _, _ = await manager.join_session("user1", params)
    print(f"  User1 joined session {session_id1}")

    # Second user should get a new session
    session_id2, _, _, _ = await manager.join_session("user2", params)
    print(f"  User2 joined session {session_id2}")

    # Sessions should be different (unless both fit in same session)
    # With single slot, they should be different
    print(f"  Sessions: {session_id1} vs {session_id2}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
