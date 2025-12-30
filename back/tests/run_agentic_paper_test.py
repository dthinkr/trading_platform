#!/usr/bin/env python3
"""
Integration test for agentic trader that captures rich data for paper figures.
Requires the backend to be running on localhost:8000.

Runs 3 sequential markets with different AGENTIC goals:
- Market 1: SELLER (goal = -15)
- Market 2: BUYER (goal = +15)  
- Market 3: SPECULATOR (goal = 0)

Total runtime: ~7 minutes (3 × 2min + buffer)

Outputs:
- agentic_market_data_seller.json
- agentic_market_data_buyer.json
- agentic_market_data_speculator.json
- agentic_decisions_seller.json (etc.)
"""

import asyncio
import aiohttp
import os
import json
import glob
from pathlib import Path
from datetime import datetime

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
LOGS_DIR = Path(__file__).parent.parent / "logs"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "platform-paper" / "data"

# Three market configurations (run sequentially)
MARKET_CONFIGS = [
    {"role": "seller", "goal": -15},
    {"role": "buyer", "goal": 15},
    {"role": "speculator", "goal": 0},
]


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


async def get_market_state(session):
    """Get current market state from backend."""
    async with session.get(f"{BACKEND_URL}/admin/market_state") as resp:
        if resp.status == 200:
            return await resp.json()
        return None


async def get_agentic_data(session):
    """Get agentic trader decision log from backend."""
    async with session.get(f"{BACKEND_URL}/admin/agentic_data") as resp:
        if resp.status == 200:
            return await resp.json()
        return None


async def trigger_market(session):
    """Trigger a market to start by logging in a test user."""
    params = {"PROLIFIC_PID": "paper_test", "STUDY_ID": "paper_test", "SESSION_ID": "s_paper"}
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
    params = {"PROLIFIC_PID": username, "STUDY_ID": "paper_test", "SESSION_ID": f"s_{username}"}
    creds = {"username": "testuser0", "password": "testpass"}
    headers = {"Authorization": f"Bearer {token}"}
    async with session.post(
        f"{BACKEND_URL}/trading/start", params=params, json=creds, headers=headers
    ) as resp:
        if resp.status == 200:
            return await resp.json()
        return None


def get_latest_log():
    """Get the most recent log file."""
    log_files = glob.glob(str(LOGS_DIR / "*.log"))
    if not log_files:
        return None
    return max(log_files, key=os.path.getmtime)


def parse_log_file(log_path):
    """Parse log file to extract market events using the platform's utility."""
    if not log_path or not os.path.exists(log_path):
        return []
    
    # Use the platform's logfile analysis utility
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.logfiles_analysis import logfile_to_message
    
    try:
        df = logfile_to_message(log_path)
        
        # Convert to list of dicts
        events = []
        start_time = df['Timestamp'].iloc[0] if len(df) > 0 else None
        
        for _, row in df.iterrows():
            elapsed = (row['Timestamp'] - start_time).total_seconds() if start_time else 0
            event = {
                "elapsed": elapsed,
                "type": row['Type'],
                "price": row['Price'],
                "amount": row['Amount'],
                "direction": row['Direction'],
                "trader_id": row['Trader'],
            }
            events.append(event)
        
        return events
    except Exception as e:
        print(f"Error parsing log: {e}")
        return []


def compute_order_book_series(log_path):
    """Compute proper order book series using platform utility."""
    if not log_path or not os.path.exists(log_path):
        return []
    
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.logfiles_analysis import logfile_to_message
    
    try:
        df = logfile_to_message(log_path)
        
        if len(df) == 0:
            return []
        
        start_time = df['Timestamp'].iloc[0]
        
        # Reconstruct order book step by step
        orders = {'BIDS': [], 'ASKS': []}
        price_series = []
        
        for _, row in df.iterrows():
            elapsed = (row['Timestamp'] - start_time).total_seconds()
            price = row['Price']
            direction = row['Direction']
            order_type = row['Type']
            trader = row['Trader']
            
            new_order = {
                'Timestamp': elapsed,
                'Price': price,
                'Amount': row['Amount'],
                'Direction': direction,
                'Trader': trader
            }
            
            best_bid = max((o['Price'] for o in orders['BIDS']), default=None)
            best_ask = min((o['Price'] for o in orders['ASKS']), default=None)
            
            if order_type == 'ADD_ORDER':
                if direction == 'BID':
                    if best_ask is None or price < best_ask:
                        orders['BIDS'].append(new_order)
                    else:
                        # Aggressive order - removes best ask
                        if orders['ASKS']:
                            best_ask_order = min(orders['ASKS'], key=lambda x: (x['Price'], x['Timestamp']))
                            orders['ASKS'].remove(best_ask_order)
                else:  # ASK
                    if best_bid is None or price > best_bid:
                        orders['ASKS'].append(new_order)
                    else:
                        # Aggressive order - removes best bid
                        if orders['BIDS']:
                            best_bid_price = max(o['Price'] for o in orders['BIDS'])
                            bids_at_best = [o for o in orders['BIDS'] if o['Price'] == best_bid_price]
                            best_bid_order = min(bids_at_best, key=lambda x: x['Timestamp'])
                            orders['BIDS'].remove(best_bid_order)
                            
            elif order_type == 'CANCEL_ORDER':
                target_list = orders['BIDS'] if direction == 'BID' else orders['ASKS']
                # Find order to cancel (same trader, same price, most recent)
                matching = [o for o in target_list if o['Trader'] == trader and o['Price'] == price]
                if matching:
                    to_cancel = max(matching, key=lambda x: x['Timestamp'])
                    target_list.remove(to_cancel)
            
            # Record current state
            best_bid = max((o['Price'] for o in orders['BIDS']), default=None)
            best_ask = min((o['Price'] for o in orders['ASKS']), default=None)
            
            if best_bid is not None and best_ask is not None:
                price_series.append({
                    "elapsed": elapsed,
                    "best_bid": best_bid,
                    "best_ask": best_ask,
                    "mid": (best_bid + best_ask) / 2,
                })
        
        return price_series
    except Exception as e:
        print(f"Error computing order book: {e}")
        import traceback
        traceback.print_exc()
        return []


def extract_agentic_activity_from_log(log_path):
    """Extract AGENTIC trader activity directly from raw log file."""
    import ast
    import re
    from datetime import datetime
    
    if not log_path or not os.path.exists(log_path):
        return [], []
    
    agentic_orders = []
    agentic_fills = []
    start_time = None
    
    with open(log_path, 'r') as f:
        for line in f:
            try:
                timestamp_str, level, msg = line.split(" - ", 2)
                msg_type, msg_content = msg.split(": ", 1)
                
                ts = datetime.strptime(timestamp_str.replace(',', '.'), '%Y-%m-%d %H:%M:%S.%f')
                if start_time is None:
                    start_time = ts
                elapsed = (ts - start_time).total_seconds()
                
                if msg_type == 'ADD_ORDER' and 'AGENTIC' in msg_content:
                    dict_start = msg_content.find('{')
                    dict_end = msg_content.rfind('}') + 1
                    dict_str = msg_content[dict_start:dict_end]
                    
                    dict_str = dict_str.replace('<OrderType.BID: 1>', '1')
                    dict_str = dict_str.replace('<OrderType.ASK: -1>', '-1')
                    dict_str = re.sub(r'<OrderStatus\.[^>]+>', "'active'", dict_str)
                    dict_str = re.sub(r'datetime\.datetime\([^)]+\)', 'None', dict_str)
                    
                    try:
                        parsed = ast.literal_eval(dict_str)
                        price = float(parsed.get('price', 0))
                        order_type = parsed.get('order_type', -1)
                        side = 'BID' if order_type == 1 else 'ASK'
                        agentic_orders.append({"elapsed": elapsed, "price": price, "side": side})
                    except:
                        pass
                
                elif msg_type == 'MATCHED_ORDER':
                    dict_start = msg_content.find('{')
                    dict_end = msg_content.rfind('}') + 1
                    dict_str = msg_content[dict_start:dict_end]
                    
                    try:
                        parsed = ast.literal_eval(dict_str)
                        bid_order_id = parsed.get('bid_order_id', '')
                        ask_order_id = parsed.get('ask_order_id', '')
                        price = float(parsed.get('transaction_price', 0))
                        
                        if 'AGENTIC' in bid_order_id or 'AGENTIC' in ask_order_id:
                            side = "BID" if 'AGENTIC' in bid_order_id else "ASK"
                            agentic_fills.append({"elapsed": elapsed, "price": price, "side": side})
                    except:
                        pass
                        
            except:
                continue
    
    return agentic_orders, agentic_fills



async def run_single_market(session, role, goal, market_num):
    """Run a single market with the given AGENTIC goal."""
    print(f"\n{'='*60}")
    print(f"MARKET {market_num}/3: {role.upper()} (goal={goal:+d})")
    print(f"{'='*60}")
    
    # Reset and clear logs
    await reset_state(session)
    for f in glob.glob(str(LOGS_DIR / "*.log")):
        os.remove(f)
    
    # Configure backend
    success = await update_settings(
        session,
        trading_day_duration=2.0,
        default_price=100,
        num_noise_traders=1,
        noise_activity_frequency=2.0,  # Increased from 1.5 to 2.0 (orders per second)
        noise_passive_probability=0.6,
        noise_bid_probability=0.5,
        num_manipulator_traders=0,
        num_agentic_traders=1,
        agentic_goals=[goal],
        agentic_decision_interval=2.0,
        agentic_buy_target_price=110,
        agentic_sell_target_price=90,
        predefined_goals=[0],
        start_of_book_num_order_per_level=4,
    )
    
    if not success:
        print(f"ERROR: Failed to configure backend")
        return None
    
    print(f"✓ Configured")
    
    # Trigger market
    login_data = await trigger_market(session)
    if login_data:
        token = login_data.get("prolific_token")
        await start_trading(session, f"paper_{role}", token)
        print("✓ Market started")
    else:
        print("ERROR: Could not trigger market")
        return None
    
    # Monitor (120s)
    print("\nCollecting data...")
    for i in range(24):
        await asyncio.sleep(5)
        elapsed = (i + 1) * 5
        log_path = get_latest_log()
        orders, fills = extract_agentic_activity_from_log(log_path)
        print(f"[{elapsed:3d}s] orders: {len(orders)}, fills: {len(fills)}")
    
    await asyncio.sleep(10)  # Buffer
    
    # Collect data
    log_path = get_latest_log()
    if not log_path:
        return None
    
    events = parse_log_file(log_path)
    agentic_orders, agentic_fills = extract_agentic_activity_from_log(log_path)
    price_series = compute_order_book_series(log_path)
    
    print(f"\n✓ {len(events)} events, {len(agentic_orders)} orders, {len(agentic_fills)} fills")
    
    # Save
    market_data = {
        "session_info": {"role": role, "goal": goal, "log_file": str(log_path), "collected_at": datetime.now().isoformat()},
        "events": events,
        "agentic_orders": agentic_orders,
        "agentic_fills": agentic_fills,
        "price_series": price_series,
    }
    
    with open(OUTPUT_DIR / f"agentic_market_data_{role}.json", "w") as f:
        json.dump(market_data, f, indent=2, default=str)
    
    agentic_data = await get_agentic_data(session)
    if agentic_data:
        with open(OUTPUT_DIR / f"agentic_decisions_{role}.json", "w") as f:
            json.dump(agentic_data, f, indent=2, default=str)
    
    return market_data


async def run_test():
    print("=" * 60)
    print("Agentic Trader Paper Data Collection")
    print("3 Sequential Markets: SELLER, BUYER, SPECULATOR")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    async with aiohttp.ClientSession() as session:
        results = {}
        
        for i, config in enumerate(MARKET_CONFIGS, 1):
            result = await run_single_market(session, config["role"], config["goal"], i)
            if result:
                results[config["role"]] = result
        
        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        for role, data in results.items():
            goal = data["session_info"]["goal"]
            orders = len(data["agentic_orders"])
            fills = len(data["agentic_fills"])
            print(f"  {role.upper():12} (goal={goal:+3d}): {orders} orders, {fills} fills")
        
        print(f"\nOutput: {OUTPUT_DIR}")


if __name__ == "__main__":
    asyncio.run(run_test())
