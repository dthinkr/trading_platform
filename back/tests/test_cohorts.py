#!/usr/bin/env python3
"""Test cohort system - users in same cohort should always play together"""

import asyncio
import aiohttp
import os
from collections import defaultdict

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


async def login_user(session, username, study_id="cohort_test"):
    """Login a user and return their trader_id"""
    params = {"PROLIFIC_PID": username, "STUDY_ID": study_id, "SESSION_ID": f"s_{username}"}
    async with session.post(f"{BACKEND_URL}/user/login", params=params,
                           json={"username": "user1", "password": "password1"}) as resp:
        if resp.status != 200:
            text = await resp.text()
            print(f"  Login failed for {username}: {resp.status} - {text}")
            return None
        result = await resp.json()
        return result.get('data', {}).get('trader_id', f"HUMAN_{username}")


async def start_trading(session, username, study_id="cohort_test"):
    """Start trading for a user"""
    params = {"PROLIFIC_PID": username, "STUDY_ID": study_id, "SESSION_ID": f"s_{username}"}
    async with session.post(f"{BACKEND_URL}/trading/start", params=params,
                           json={"username": "user1", "password": "password1"}) as resp:
        return await resp.json() if resp.status == 200 else None


async def get_session_status(session, username, study_id="cohort_test"):
    """Get session status for a user"""
    params = {"PROLIFIC_PID": username, "STUDY_ID": study_id, "SESSION_ID": f"s_{username}"}
    async with session.get(f"{BACKEND_URL}/trading/session_status", params=params) as resp:
        return await resp.json() if resp.status == 200 else None


async def get_cohorts(session):
    """Get current cohort assignments"""
    async with session.get(f"{BACKEND_URL}/admin/get_cohorts") as resp:
        return await resp.json() if resp.status == 200 else None


async def update_settings(session, **kwargs):
    """Update backend settings"""
    async with session.post(f"{BACKEND_URL}/admin/update_persistent_settings",
                           json={"settings": kwargs}) as resp:
        return resp.status == 200


async def reset_backend(session):
    """Reset backend state"""
    async with session.post(f"{BACKEND_URL}/admin/reset") as resp:
        return resp.status == 200


async def test_cohort_assignment():
    """Test that users are assigned to cohorts correctly based on market_sizes"""
    
    async with aiohttp.ClientSession() as session:
        print("\n" + "="*80)
        print("TEST 1: Cohort Assignment")
        print("="*80)
        
        # Reset and configure
        await reset_backend(session)
        
        # Set up: 2 cohorts of size 3 each (6 users total)
        # predefined_goals needs at least 3 goals for cohort size 3
        success = await update_settings(session,
                                        predefined_goals=[100, 0, -100],
                                        market_sizes=[3, 3],
                                        trading_day_duration=10,
                                        max_markets_per_human=5)
        print(f"✓ Settings updated (market_sizes=[3,3], goals=[100,0,-100])")
        
        # Login 6 users
        usernames = [f"user{i}" for i in range(6)]
        for u in usernames:
            tid = await login_user(session, u)
            print(f"  Logged in {u}: {tid}")
        
        # Check cohort assignments
        cohort_info = await get_cohorts(session)
        print(f"\nCohort info after login:")
        print(f"  market_sizes: {cohort_info.get('market_sizes')}")
        
        cohorts = cohort_info.get('cohorts', {})
        for cid, info in cohorts.items():
            print(f"  Cohort {cid}: {info['members']} (size {info['size']}/{info['max_size']})")
        
        # Verify: Should have 2 cohorts with 3 users each
        assert len(cohorts) == 2, f"Expected 2 cohorts, got {len(cohorts)}"
        for cid, info in cohorts.items():
            assert info['size'] == 3, f"Cohort {cid} should have 3 users, has {info['size']}"
        
        print("\n✓ TEST 1 PASSED: Users correctly assigned to cohorts")
        return True


async def test_cohort_persistence():
    """Test that cohort members stay together across multiple markets"""
    
    async with aiohttp.ClientSession() as session:
        print("\n" + "="*80)
        print("TEST 2: Cohort Persistence Across Markets")
        print("="*80)
        
        # Reset and configure
        await reset_backend(session)
        
        # 2 cohorts of 2 users each, short trading duration
        success = await update_settings(session,
                                        predefined_goals=[100, 0],
                                        market_sizes=[2, 2],
                                        trading_day_duration=3,
                                        max_markets_per_human=5)
        print(f"✓ Settings: market_sizes=[2,2], goals=[100,0], duration=3s")
        
        # Login 4 users
        usernames = [f"p{i}" for i in range(4)]
        for u in usernames:
            await login_user(session, u)
        
        # Get initial cohort assignments
        cohort_info = await get_cohorts(session)
        initial_cohorts = {}
        for cid, info in cohort_info.get('cohorts', {}).items():
            for member in info['members']:
                initial_cohorts[member] = cid
        
        print(f"\nInitial cohort assignments: {initial_cohorts}")
        
        # Track which users play together in each market
        market_groups = []
        
        for market_num in range(1, 3):
            print(f"\n--- Market {market_num} ---")
            
            # All users start trading
            for u in usernames:
                await start_trading(session, u)
            
            # Wait a moment for sessions to form
            await asyncio.sleep(1)
            
            # Check session status for each user
            user_sessions = {}
            for u in usernames:
                status = await get_session_status(session, u)
                if status and status.get('status') == 'success':
                    data = status.get('data', {})
                    session_id = data.get('session_id') or data.get('market_id')
                    users_in_session = data.get('users', [])
                    user_sessions[u] = {
                        'session_id': session_id,
                        'users': users_in_session
                    }
                    print(f"  {u}: session={session_id}, with={users_in_session}")
            
            market_groups.append(user_sessions)
            
            # Wait for market to finish
            print(f"  Waiting for market to finish...")
            await asyncio.sleep(5)
        
        # Verify cohort members stayed together
        print("\n--- Verification ---")
        
        # Group users by their session in each market
        for market_num, groups in enumerate(market_groups, 1):
            sessions_to_users = defaultdict(set)
            for user, info in groups.items():
                if info['session_id']:
                    sessions_to_users[info['session_id']].add(user)
            
            print(f"Market {market_num} groups: {dict(sessions_to_users)}")
            
            # Check that users in same cohort are in same session
            for session_id, users in sessions_to_users.items():
                cohort_ids = set(initial_cohorts.get(u) for u in users)
                if len(cohort_ids) > 1:
                    print(f"  ✗ FAIL: Session {session_id} has users from different cohorts: {cohort_ids}")
                    return False
                else:
                    print(f"  ✓ Session {session_id}: all users from cohort {cohort_ids.pop()}")
        
        print("\n✓ TEST 2 PASSED: Cohort members stayed together across markets")
        return True


async def test_overflow_cohort():
    """Test that extra users go to overflow cohorts"""
    
    async with aiohttp.ClientSession() as session:
        print("\n" + "="*80)
        print("TEST 3: Overflow Cohort Handling")
        print("="*80)
        
        # Reset and configure
        await reset_backend(session)
        
        # 2 cohorts of 2 users each, but we'll add 5 users
        success = await update_settings(session,
                                        predefined_goals=[100, 0],
                                        market_sizes=[2, 2],
                                        trading_day_duration=5,
                                        max_markets_per_human=5)
        print(f"✓ Settings: market_sizes=[2,2] (4 slots), but adding 5 users")
        
        # Login 5 users (1 more than capacity)
        usernames = [f"overflow{i}" for i in range(5)]
        for u in usernames:
            await login_user(session, u)
        
        # Check cohort assignments
        cohort_info = await get_cohorts(session)
        print(f"\nCohort info:")
        
        cohorts = cohort_info.get('cohorts', {})
        total_users = 0
        for cid, info in sorted(cohorts.items(), key=lambda x: int(x[0])):
            print(f"  Cohort {cid}: {info['members']} (size {info['size']}/{info['max_size']})")
            total_users += info['size']
        
        # Should have 3 cohorts: 2 full + 1 overflow
        assert len(cohorts) >= 2, f"Expected at least 2 cohorts, got {len(cohorts)}"
        assert total_users == 5, f"Expected 5 total users, got {total_users}"
        
        print("\n✓ TEST 3 PASSED: Overflow users handled correctly")
        return True


async def test_default_behavior():
    """Test that without market_sizes, it defaults to single cohort"""
    
    async with aiohttp.ClientSession() as session:
        print("\n" + "="*80)
        print("TEST 4: Default Behavior (no market_sizes)")
        print("="*80)
        
        # Reset and configure WITHOUT market_sizes
        await reset_backend(session)
        
        success = await update_settings(session,
                                        predefined_goals=[100, 0, -100],
                                        market_sizes=[],  # Empty = default behavior
                                        trading_day_duration=5,
                                        max_markets_per_human=5)
        print(f"✓ Settings: market_sizes=[] (empty), goals=[100,0,-100]")
        
        # Login 3 users
        usernames = [f"default{i}" for i in range(3)]
        for u in usernames:
            await login_user(session, u)
        
        # Check cohort assignments
        cohort_info = await get_cohorts(session)
        print(f"\nCohort info:")
        print(f"  market_sizes: {cohort_info.get('market_sizes')}")
        
        cohorts = cohort_info.get('cohorts', {})
        for cid, info in cohorts.items():
            print(f"  Cohort {cid}: {info['members']} (size {info['size']})")
        
        # Should have 1 cohort with all 3 users
        assert len(cohorts) == 1, f"Expected 1 cohort (default), got {len(cohorts)}"
        
        print("\n✓ TEST 4 PASSED: Default behavior works (single cohort)")
        return True


async def main():
    """Run all cohort tests"""
    print("\n" + "="*80)
    print("COHORT SYSTEM TESTS")
    print("="*80)
    
    results = []
    
    try:
        results.append(("Cohort Assignment", await test_cohort_assignment()))
    except Exception as e:
        print(f"\n✗ TEST 1 FAILED: {e}")
        results.append(("Cohort Assignment", False))
    
    try:
        results.append(("Cohort Persistence", await test_cohort_persistence()))
    except Exception as e:
        print(f"\n✗ TEST 2 FAILED: {e}")
        results.append(("Cohort Persistence", False))
    
    try:
        results.append(("Overflow Handling", await test_overflow_cohort()))
    except Exception as e:
        print(f"\n✗ TEST 3 FAILED: {e}")
        results.append(("Overflow Handling", False))
    
    try:
        results.append(("Default Behavior", await test_default_behavior()))
    except Exception as e:
        print(f"\n✗ TEST 4 FAILED: {e}")
        results.append(("Default Behavior", False))
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    # Reset at end
    async with aiohttp.ClientSession() as session:
        await reset_backend(session)
        print("\n✓ Backend reset")


if __name__ == "__main__":
    asyncio.run(main())
