#!/usr/bin/env python3
"""
fast integration test for agentic trader (~15s total).
requires backend running on localhost:8000.
"""
import asyncio
import aiohttp
import os
import glob
from pathlib import Path

# auto-detect if running against docker (with /api prefix) or local
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
LOGS_DIR = Path(__file__).parent.parent / "logs"

# test config - optimized for speed
DURATION = 0.25  # 15 seconds
GOAL = 3  # small goal
DECISION_INTERVAL = 1.0  # fast decisions


async def detect_api_prefix(session):
    """detect if backend uses /api prefix (docker) or not (local)."""
    # try without prefix first
    try:
        async with session.get(f"{BACKEND_URL}/admin/get_base_settings", timeout=aiohttp.ClientTimeout(total=2)) as resp:
            if resp.status == 200:
                return ""
    except:
        pass
    # try with /api prefix
    try:
        async with session.get(f"{BACKEND_URL}/api/admin/get_base_settings", timeout=aiohttp.ClientTimeout(total=2)) as resp:
            if resp.status == 200:
                return "/api"
    except:
        pass
    return ""


async def update_settings(session, prefix, **kwargs):
    async with session.post(f"{BACKEND_URL}{prefix}/admin/update_base_settings", json={"settings": kwargs}) as resp:
        return resp.status == 200


async def reset_state(session, prefix):
    async with session.post(f"{BACKEND_URL}{prefix}/test/reset_state") as resp:
        return resp.status == 200


async def trigger_market(session, prefix):
    params = {"PROLIFIC_PID": "test_agentic", "STUDY_ID": "agentic_test", "SESSION_ID": "s_agentic"}
    creds = {"username": "user1", "password": "password1"}  # default credentials
    async with session.post(f"{BACKEND_URL}{prefix}/user/login", params=params, json=creds) as resp:
        if resp.status == 200:
            return (await resp.json()).get("data", {})
        print(f"  login failed: {resp.status} - {await resp.text()}")
        return None


async def start_trading(session, prefix, username, token):
    params = {"PROLIFIC_PID": username, "STUDY_ID": "agentic_test", "SESSION_ID": f"s_{username}"}
    headers = {"Authorization": f"Bearer {token}"}
    async with session.post(f"{BACKEND_URL}{prefix}/trading/start", params=params, 
                           json={"username": "user1", "password": "password1"}, headers=headers) as resp:
        return resp.status == 200


def get_latest_log():
    log_files = glob.glob(str(LOGS_DIR / "*.log"))
    return max(log_files, key=os.path.getmtime) if log_files else None


def count_agentic_orders(log_path):
    if not log_path or not os.path.exists(log_path):
        return 0
    with open(log_path, "r") as f:
        return sum(1 for line in f if "trader_id': 'AGENTIC" in line and "ADD_ORDER" in line)


async def run_test():
    print(f"⚡ fast agentic test ({int(DURATION*60)}s, goal={GOAL})")
    
    for f in glob.glob(str(LOGS_DIR / "*.log")):
        os.remove(f)

    async with aiohttp.ClientSession() as session:
        prefix = await detect_api_prefix(session)
        print(f"  using prefix: '{prefix}'" if prefix else "  no api prefix")
        
        await reset_state(session, prefix)
        
        await update_settings(session, prefix,
            trading_day_duration=DURATION,
            default_price=100,
            num_noise_traders=1,
            noise_activity_frequency=3.0,
            num_manipulator_traders=0,
            num_agentic_traders=1,
            agentic_goals=[GOAL],
            agentic_decision_interval=DECISION_INTERVAL,
            predefined_goals=[0],
            start_of_book_num_order_per_level=3,
        )
        print("✓ configured")

        login_data = await trigger_market(session, prefix)
        if login_data:
            await start_trading(session, prefix, "test_agentic", login_data.get("prolific_token"))
            print("✓ market started")
        else:
            print("✗ failed to start market")
            return

        # monitor (duration + 5s buffer)
        total_wait = int(DURATION * 60) + 5
        for i in range(total_wait // 2):
            await asyncio.sleep(2)
            count = count_agentic_orders(get_latest_log())
            print(f"  [{(i+1)*2:2d}s] orders: {count}/{GOAL}")
            if count >= GOAL:
                print(f"✓ goal complete!")
                break

        # result
        final_count = count_agentic_orders(get_latest_log())
        status = "✓ PASS" if final_count >= GOAL else f"✗ FAIL ({final_count}/{GOAL})"
        print(f"\n{status}")


if __name__ == "__main__":
    asyncio.run(run_test())
