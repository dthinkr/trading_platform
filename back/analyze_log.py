#!/usr/bin/env python3
import os
import glob
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from utils.logfiles_analysis import logfile_to_message, process_logfile, calculate_vwap_reward

# Find latest log
logs = glob.glob('logs/SESSION_*.log')
latest = max(logs, key=os.path.getctime)
print(f"Log: {latest}\n")

# Get metrics using the proper function
msg_df, metrics = process_logfile(latest)

print(f"Total Orders: {metrics['Total_Orders']}")
print(f"Total Trades: {metrics['Total_Trades']}")
print(f"Initial Mid: {metrics['Initial_Midprice']}")
print(f"Last Mid: {metrics['Last_Midprice']}")

# AGENTIC orders
df = logfile_to_message(latest)
agentic = df[df['Trader'] == 'AGENTIC_1']
bids = agentic[agentic['Direction'] == 'BID']

print(f"\nAGENTIC_1 BID orders: {len(bids)}")
if len(bids) > 0:
    vwap = bids['Price'].mean()
    print(f"VWAP: {vwap:.2f}")
    
    # Use the reward function
    result = calculate_vwap_reward(
        goal=20,
        completed_trades=len(bids),
        current_vwap=vwap,
        mid_price=metrics['Last_Midprice']
    )
    print(f"\nReward calc:")
    print(f"  Completed: {len(bids)}")
    print(f"  Remaining: {result['remaining_trades']}")
    print(f"  Penalized VWAP: {result['penalized_vwap']:.2f}")
    print(f"  PnL: {result['pnl']:.2f}")
    print(f"  Reward: {result['reward']:.2f}")
