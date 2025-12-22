#!/usr/bin/env python3
"""Analyze Market 3 timing to understand early stop"""

import re
from datetime import datetime

log_file = "../attachements/COHORT0_SESSION_1766401381_036eb923_trading_market3.log"

with open(log_file) as f:
    lines = f.readlines()

def extract_time(line):
    match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})', line)
    if match:
        return datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S,%f')
    return None

first_ts = extract_time(lines[0])
last_ts = extract_time(lines[-1])

print(f"First event: {first_ts}")
print(f"Last event: {last_ts}")
print(f"Duration: {(last_ts - first_ts).total_seconds():.1f} seconds")

# Find human first order
for line in lines:
    if 'HUMAN_' in line and 'ADD_ORDER' in line:
        human_ts = extract_time(line)
        print(f"Human first order: {human_ts}")
        print(f"Delay from start: {(human_ts - first_ts).total_seconds():.1f}s")
        break

print(f"\nTotal lines: {len(lines)}")
