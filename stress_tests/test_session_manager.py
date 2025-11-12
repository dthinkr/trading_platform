#!/usr/bin/env python3
"""
Session Manager Tests

Tests for session manager functionality, including:
- Slot assignment bug reproduction and fix verification
- Goal change scenarios
- Permanent role persistence
"""

import sys
import os
import asyncio

# Change to back directory to run imports correctly
back_dir = os.path.join(os.path.dirname(__file__), '..', 'back')
os.chdir(back_dir)
sys.path.insert(0, back_dir)

from core.session_manager import SessionManager
from core.data_models import TradingParameters, TraderRole


async def test_slot_assignment_bug_reproduction():
    """Reproduce the bug where users can't join when predefined_goals changes."""
    
    print("=" * 70)
    print("TEST: Slot Assignment Bug Reproduction")
    print("=" * 70)
    
    manager = SessionManager()
    username = "test_user"
    
    # Step 1: User joins with predefined_goals = [100]
    print("\n1. User joins with predefined_goals = [100]")
    params1 = TradingParameters(predefined_goals=[100])
    
    try:
        session_id1, trader_id1, role1, goal1 = await manager.join_session(username, params1)
        print(f"   ✓ Successfully joined session {session_id1}")
        print(f"   Role: {role1}, Goal: {goal1}")
        print(f"   Permanent goal magnitude: {manager.permanent_informed_goals.get(username)}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False
    
    # Step 2: User leaves (simulate refresh/logout)
    print("\n2. User leaves session (simulate refresh)")
    await manager.remove_user_from_session(username)
    print(f"   ✓ User removed from session")
    print(f"   Permanent goal magnitude still: {manager.permanent_informed_goals.get(username)}")
    
    # Step 3: predefined_goals changes to [20]
    print("\n3. predefined_goals changes to [20]")
    params2 = TradingParameters(predefined_goals=[20])
    
    # Step 4: User tries to join again - THIS SHOULD FAIL WITH THE BUG (before fix)
    print("\n4. User tries to join again with new predefined_goals = [20]")
    print("   Expected: Should fail with 'No suitable slot available' (before fix)")
    
    try:
        session_id2, trader_id2, role2, goal2 = await manager.join_session(username, params2)
        print(f"   ✓ SUCCESS (after fix): Joined session {session_id2}")
        print(f"   Role: {role2}, Goal: {goal2}")
        return True
    except Exception as e:
        if "No suitable slot available" in str(e):
            print(f"   ✗ BUG REPRODUCED: {e}")
            return False
        else:
            print(f"   ✗ Different error: {e}")
            return False


async def test_goal_change_scenarios():
    """Test various scenarios when predefined_goals changes."""
    
    print("\n" + "=" * 70)
    print("TEST: Goal Change Scenarios")
    print("=" * 70)
    
    manager = SessionManager()
    username = "user_scenario"
    
    # Scenario: User joins with [100], goals change to [20], user rejoins
    print("\nScenario: User joins with [100], goals change to [20], user rejoins")
    params1 = TradingParameters(predefined_goals=[100])
    session_id1, _, role1, goal1 = await manager.join_session(username, params1)
    print(f"   ✓ Joined with goal={goal1}, permanent magnitude={manager.permanent_informed_goals.get(username)}")
    
    await manager.remove_user_from_session(username)
    
    params2 = TradingParameters(predefined_goals=[20])
    try:
        session_id2, _, role2, goal2 = await manager.join_session(username, params2)
        print(f"   ✓ SUCCESS: Rejoined with role={role2}, goal={goal2}")
        slots = manager.session_slots[session_id2]
        goal_magnitudes = [abs(s.goal) for s in slots]
        print(f"   Session slots have goal magnitudes: {goal_magnitudes}")
        return True
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        return False


async def test_multiple_users_different_goals():
    """Test multiple users with different permanent goal magnitudes."""
    
    print("\n" + "=" * 70)
    print("TEST: Multiple Users with Different Permanent Goals")
    print("=" * 70)
    
    manager = SessionManager()
    
    # User 1 joins with [100]
    print("\n1. User1 joins with predefined_goals = [100]")
    params1 = TradingParameters(predefined_goals=[100])
    await manager.join_session("user1", params1)
    await manager.remove_user_from_session("user1")
    print(f"   User1 permanent goal magnitude: {manager.permanent_informed_goals.get('user1')}")
    
    # User 2 joins with [20]
    print("\n2. User2 joins with predefined_goals = [20]")
    params2 = TradingParameters(predefined_goals=[20])
    await manager.join_session("user2", params2)
    await manager.remove_user_from_session("user2")
    print(f"   User2 permanent goal magnitude: {manager.permanent_informed_goals.get('user2')}")
    
    # Goals change to [50]
    print("\n3. Admin changes predefined_goals to [50]")
    
    # Both users try to join
    print("\n4. Both users try to join with new predefined_goals = [50]")
    params3 = TradingParameters(predefined_goals=[50])
    
    try:
        session_id3a, _, _, _ = await manager.join_session("user1", params3)
        print(f"   ✓ User1 joined session {session_id3a}")
        
        session_id3b, _, _, _ = await manager.join_session("user2", params3)
        print(f"   ✓ User2 joined session {session_id3b}")
        
        slots1 = manager.session_slots[session_id3a]
        slots2 = manager.session_slots[session_id3b]
        print(f"   User1 session slots: {[abs(s.goal) for s in slots1]}")
        print(f"   User2 session slots: {[abs(s.goal) for s in slots2]}")
        
        return True
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        return False


async def main():
    """Run all session manager tests."""
    print("=" * 70)
    print("SESSION MANAGER TESTS")
    print("=" * 70)
    
    results = []
    results.append(("Bug Reproduction", await test_slot_assignment_bug_reproduction()))
    results.append(("Goal Change Scenarios", await test_goal_change_scenarios()))
    results.append(("Multiple Users", await test_multiple_users_different_goals()))
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for name, success in results:
        print(f"{name}: {'✓ PASSED' if success else '✗ FAILED'}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

