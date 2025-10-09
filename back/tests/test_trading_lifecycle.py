#!/usr/bin/env python3
"""Test role persistence across multiple markets"""

import asyncio
import aiohttp
import os
import random
from collections import defaultdict

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


async def login_user(session, username, study_id="test"):
    params = {"PROLIFIC_PID": username, "STUDY_ID": study_id, "SESSION_ID": f"s_{username}"}
    async with session.post(f"{BACKEND_URL}/user/login", params=params, 
                           json={"username": username, "password": "pass"}) as resp:
        if resp.status != 200:
            return None
        result = await resp.json()
        return result.get('data', {}).get('trader_id', f"HUMAN_{username}")


async def start_trading(session, username, study_id="test"):
    params = {"PROLIFIC_PID": username, "STUDY_ID": study_id, "SESSION_ID": f"s_{username}"}
    async with session.post(f"{BACKEND_URL}/trading/start", params=params,
                           json={"username": username, "password": "pass"}) as resp:
        return await resp.json() if resp.status == 200 else None


async def get_trader_info(session, trader_id):
    async with session.get(f"{BACKEND_URL}/trader_info/{trader_id}") as resp:
        return await resp.json() if resp.status == 200 else None


async def update_settings(session, **kwargs):
    async with session.post(f"{BACKEND_URL}/admin/update_persistent_settings", 
                           json={"settings": kwargs}) as resp:
        return resp.status == 200


async def test_role_persistence():
    """40 traders play 4 markets each to verify role/goal persistence"""
    
    async with aiohttp.ClientSession() as session:
        print("\n" + "="*80)
        print("40 Traders × 4 Markets - Role Persistence Test")
        print("="*80)
        
        # Config
        num_traders = 40
        num_markets = 4
        session_duration = 5
        
        print(f"\nSetup: {num_traders} traders, {num_markets} markets, {session_duration}s per market")
        
        await update_settings(session, 
                            predefined_goals=[100, 0, -100],
                            trading_day_duration=session_duration,
                            allow_random_goals=True)
        print("✓ Backend configured (3 per session, random goal flipping enabled)")
        
        # Login all traders
        usernames = [f"u{i}" for i in range(num_traders)]
        traders = []
        for u in usernames:
            tid = await login_user(session, u, study_id="persist")
            if tid:
                traders.append({'tid': tid, 'name': u})
        
        print(f"✓ {len(traders)} traders logged in\n")
        
        # Track assignments
        roles = defaultdict(list)
        goals = defaultdict(list)
        
        # Play markets
        for round_num in range(1, num_markets + 1):
            print(f"Market {round_num}/{num_markets}")
            random.shuffle(traders)
            
            for t in traders:
                await start_trading(session, t['name'], study_id="persist")
            
            await asyncio.sleep(session_duration + 2)
            
            placed = waiting = 0
            for t in traders:
                info = await get_trader_info(session, t['tid'])
                if info and info.get('status') == 'success':
                    data = info.get('data', {})
                    goal = data.get('goal', 'N/A')
                    role = 'SPEC' if goal == 0 else 'INF'
                    roles[t['name']].append(role)
                    goals[t['name']].append(goal)
                    placed += 1
                else:
                    roles[t['name']].append('WAIT')
                    goals[t['name']].append(None)
                    waiting += 1
            
            print(f"  Placed: {placed}, Waiting: {waiting}")
            
            if round_num < num_markets:
                await asyncio.sleep(3)
        
        # Analysis
        print("\n" + "="*80)
        print("Results")
        print("="*80)
        
        consistent = sum(1 for r in roles.values() 
                        if len(set(x for x in r if x in ['SPEC', 'INF'])) == 1)
        
        print(f"\nRole persistence: {consistent}/{len(traders)} traders consistent\n")
        
        # Show assignments
        print(f"{'Trader':<8} {'Role':<6} {'M1':<8} {'M2':<8} {'M3':<8} {'M4':<8}")
        print("-"*50)
        
        for t in traders[:20]:  # Show first 20
            name = t['name']
            r_list = roles[name]
            g_list = goals[name]
            
            role = next((r for r in r_list if r in ['SPEC', 'INF']), r_list[0] if r_list else 'N/A')
            g_str = [str(g) if g else 'WAIT' for g in g_list]
            
            print(f"{name:<8} {role:<6} {g_str[0]:<8} {g_str[1]:<8} {g_str[2]:<8} {g_str[3]:<8}")
        
        if len(traders) > 20:
            print(f"... ({len(traders)-20} more)")
        
        # Reset
        await update_settings(session, predefined_goals=[100, 0], trading_day_duration=0.5)
        print(f"\n{'='*80}")
        print("Done")
        print("="*80)


if __name__ == "__main__":
    asyncio.run(test_role_persistence())
