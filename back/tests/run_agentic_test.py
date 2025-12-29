#!/usr/bin/env python3
"""
Integration test for agentic trader via the actual backend API.
Requires the backend to be running on localhost:8000.
"""

import asyncio
import aiohttp
import os
import glob
from pathlib import Path

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
LOGS_DIR = Path(__file__).parent.parent / "logs"


async def update_settings(session, **kwargs):
    """Update backend settings."""
    async with session.post(
        f"{BACKEND_URL}/admin/update_persistent_settings", json={"settings": kwargs}
    ) as resp:
        return resp.status == 200


async def reset_state(session):
    """Reset backend state for clean test."""
    async with session.post(f"{BACKEND_URL}/test/reset_state") as resp:
        return resp.status == 200


async def trigger_market(session):
    """Trigger a market to start by logging in a test user."""
    params = {"PROLIFIC_PID": "test_agentic", "STUDY_ID": "agentic_test", "SESSION_ID": "s_agentic"}
    creds = {"username": "testuser0", "password": "testpass"}
    async with session.post(
        f"{BACKEND_URL}/user/login", params=params, json=creds
    ) as resp:
        if resp.status == 200:
            data = await resp.json()
            return data.get("data", {})
        return None


async def start_trading(session, username, token):
    """Start trading for a user."""
    params = {"PROLIFIC_PID": username, "STUDY_ID": "agentic_test", "SESSION_ID": f"s_{username}"}
    creds = {"username": "testuser0", "password": "testpass"}
    headers = {"Authorization": f"Bearer {token}"}
    async with session.post(
        f"{BACKEND_URL}/trading/start", params=params, json=creds, headers=headers
    ) as resp:
        if resp.status == 200:
            return await resp.json()
        else:
            text = await resp.text()
            print(f"Start trading failed: {text}")
            return None


def get_latest_log():
    """Get the most recent log file."""
    log_files = glob.glob(str(LOGS_DIR / "*.log"))
    if not log_files:
        return None
    return max(log_files, key=os.path.getmtime)


def count_agentic_orders(log_path):
    """Count AGENTIC orders in log file."""
    if not log_path or not os.path.exists(log_path):
        return 0, []
    
    orders = []
    with open(log_path, "r") as f:
        for line in f:
            if "trader_id': 'AGENTIC" in line and "ADD_ORDER" in line:
                orders.append(line.strip())
    return len(orders), orders[-5:] if orders else []


async def run_test():
    print("=" * 60)
    print("Agentic Trader Integration Test (via Backend API)")
    print("=" * 60)

    # Clear old logs
    for f in glob.glob(str(LOGS_DIR / "*.log")):
        os.remove(f)
    print("✓ Cleared old log files")

    async with aiohttp.ClientSession() as session:
        # Reset state
        print("\nResetting backend state...")
        await reset_state(session)
        print("✓ State reset")

        # Configure backend for agentic test
        print("\nConfiguring backend...")
        success = await update_settings(
            session,
            # Market settings
            trading_day_duration=1.0,  # 1 minute
            default_price=100,
            # Noise trader
            num_noise_traders=1,
            noise_activity_frequency=2.0,
            noise_passive_probability=0.5,
            noise_bid_probability=0.5,
            # Disable manipulator for cleaner test
            num_manipulator_traders=0,
            # Agentic trader
            num_agentic_traders=1,
            agentic_goals=[10],  # Buy 10 shares
            agentic_decision_interval=2.0,  # Decide every 2 seconds
            agentic_buy_target_price=110,
            agentic_sell_target_price=90,
            # One human slot so we can trigger the market
            predefined_goals=[0],
            # Book initialization
            start_of_book_num_order_per_level=3,
        )

        if not success:
            print("ERROR: Failed to configure backend")
            return

        print("✓ Backend configured")
        print("\nConfig:")
        print("  - Duration: 1 min (60s)")
        print("  - Noise traders: 1")
        print("  - Agentic traders: 1")
        print("  - Agentic goal: BUY 10 shares")
        print("  - Decision interval: 2s")

        # Trigger market by starting trading
        print("\nTriggering market...")
        login_data = await trigger_market(session)
        if login_data:
            trader_id = login_data.get("trader_id")
            token = login_data.get("prolific_token")
            print(f"✓ Logged in as {trader_id}")
            result = await start_trading(session, "test_agentic", token)
            if result:
                print("✓ Trading started")
            else:
                print("WARNING: Could not start trading")
        else:
            print("WARNING: Could not trigger market via login")

        # Monitor progress via log file
        print("\nMonitoring agentic trader (60s + buffer)...")
        print("-" * 40)

        for i in range(14):  # Check every 5 seconds for ~70 seconds
            await asyncio.sleep(5)

            elapsed = (i + 1) * 5
            log_path = get_latest_log()
            count, recent = count_agentic_orders(log_path)

            print(f"\n[{elapsed:3d}s] AGENTIC orders: {count}/10")
            if recent:
                for order in recent[-2:]:
                    # Extract price from order
                    if "'price':" in order:
                        price_start = order.find("'price':") + 9
                        price_end = order.find(",", price_start)
                        price = order[price_start:price_end].strip()
                        print(f"  Latest: price={price}")

            if count >= 10:
                print("\n✓ Goal complete! Agent placed 10 orders.")
                break

        # Final summary
        print("\n" + "=" * 60)
        print("FINAL RESULTS")
        print("=" * 60)

        log_path = get_latest_log()
        if log_path:
            print(f"\nLog file: {log_path}")
            count, orders = count_agentic_orders(log_path)
            print(f"Total AGENTIC orders: {count}")

            if orders:
                print("\nLast 5 orders:")
                for order in orders:
                    if "'price':" in order:
                        price_start = order.find("'price':") + 9
                        price_end = order.find(",", price_start)
                        price = order[price_start:price_end].strip()
                        
                        id_start = order.find("'id': '") + 7
                        id_end = order.find("'", id_start)
                        order_id = order[id_start:id_end]
                        
                        print(f"  {order_id}: price={price}")
        else:
            print("No log file found")

        print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(run_test())
