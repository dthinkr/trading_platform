"""
Simulate 100 lab users joining with 4 treatments, market_sizes=[25,25,25,25].
Verifies:
1. Block assignment: first 25 → T0, next 25 → T1, etc.
2. Cohort assignment: treatment_group determines cohort
3. Session creation: each cohort gets its own session
4. Market start: when all 25 in a cohort are ready, market starts
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.lab_auth import generate_lab_tokens, validate_lab_token, LAB_TOKENS
from core.session_manager import SessionManager
from core.data_models import TradingParameters


def test_block_assignment():
    """Test that tokens are assigned in blocks, not round-robin."""
    LAB_TOKENS.clear()
    tokens = generate_lab_tokens(100, num_treatments=4)

    # Validate each token and check treatment_group
    groups = {0: [], 1: [], 2: [], 3: []}
    for i, token in enumerate(tokens):
        is_valid, user = validate_lab_token(token)
        assert is_valid, f"Token {i} invalid"
        tg = user["treatment_group"]
        groups[tg].append(i + 1)  # participant_index

    print("=== Block Assignment ===")
    for g, members in groups.items():
        print(f"  T{g}: participants {members[0]}-{members[-1]} (count={len(members)})")
        assert len(members) == 25, f"T{g} has {len(members)} members, expected 25"

    # Verify blocks are sequential
    assert groups[0] == list(range(1, 26)), "T0 should be participants 1-25"
    assert groups[1] == list(range(26, 51)), "T1 should be participants 26-50"
    assert groups[2] == list(range(51, 76)), "T2 should be participants 51-75"
    assert groups[3] == list(range(76, 101)), "T3 should be participants 76-100"
    print("  ✓ Block assignment correct\n")


async def test_full_lab_flow():
    """Simulate 100 users joining sessions with market_sizes=[25,25,25,25]."""
    LAB_TOKENS.clear()

    # Generate 100 tokens with 4 treatments
    tokens = generate_lab_tokens(100, num_treatments=4)

    # Setup session manager like the real experiment
    sm = SessionManager()
    sm.update_market_sizes([25, 25, 25, 25])

    params = TradingParameters(predefined_goals=[0])

    # Validate all tokens first to get user info
    users = []
    for token in tokens:
        is_valid, user = validate_lab_token(token)
        users.append(user)

    print("=== Full Lab Flow (100 users, 4 treatments, market_sizes=[25,25,25,25]) ===\n")

    # Register treatment groups (simulating what endpoints.py does on login)
    for user in users:
        tg = user["treatment_group"]
        username = user["gmail_username"]
        if tg is not None:
            sm.user_treatment_groups[username] = tg

    # Simulate all 100 users joining sessions
    sessions_by_cohort = {}
    for i, user in enumerate(users):
        username = user["gmail_username"]
        result = await sm.join_session(username, params)
        session_id, trader_id, role, goal = result

        cohort = sm.user_cohorts.get(username)
        if cohort not in sessions_by_cohort:
            sessions_by_cohort[cohort] = {"session": session_id, "users": []}
        sessions_by_cohort[cohort]["users"].append(username)

    print("  Cohort assignments:")
    for cohort_id in sorted(sessions_by_cohort.keys()):
        info = sessions_by_cohort[cohort_id]
        print(f"    Cohort {cohort_id}: {len(info['users'])} users, session={info['session'][:40]}...")
        assert len(info['users']) == 25, f"Cohort {cohort_id} has {len(info['users'])} users, expected 25"

    assert len(sessions_by_cohort) == 4, f"Expected 4 cohorts, got {len(sessions_by_cohort)}"
    print(f"  ✓ 4 cohorts created, 25 users each\n")

    # Verify treatment → cohort mapping
    print("  Treatment → Cohort mapping:")
    for user in users:
        username = user["gmail_username"]
        tg = user["treatment_group"]
        cohort = sm.user_cohorts[username]
        assert tg == cohort, f"User {username}: treatment_group={tg} but cohort={cohort}"
    print("    ✓ All users in correct cohort matching their treatment group\n")

    # Simulate marking users ready, cohort by cohort
    print("  Market start simulation:")
    for cohort_id in sorted(sessions_by_cohort.keys()):
        cohort_users = sessions_by_cohort[cohort_id]["users"]

        for j, username in enumerate(cohort_users):
            can_start, info = await sm.mark_user_ready(username)

            if j < 24:
                assert not can_start, f"Cohort {cohort_id}, user {j+1}/25: should NOT start yet"
            else:
                assert can_start, f"Cohort {cohort_id}, user {j+1}/25: should start"
                print(f"    Cohort {cohort_id} (T{cohort_id}): market started after {j+1} users ready")

    print("  ✓ All 4 markets started correctly when 25th user in each cohort clicked ready\n")

    # Summary
    print("=== SUMMARY ===")
    print("  ✓ 100 tokens generated with block assignment (25 per treatment)")
    print("  ✓ 4 cohorts created matching treatment groups")
    print("  ✓ Each cohort waits for 25 users before starting")
    print("  ✓ Markets start when all users in cohort are ready")
    print("  ✓ Lab experiment flow validated")


if __name__ == "__main__":
    print()
    test_block_assignment()
    asyncio.run(test_full_lab_flow())
    print()
