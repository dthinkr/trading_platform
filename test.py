from external_traders.informed_naive import get_informed_time_plan, get_signal_informed, get_informed_order, settings_informed, informed_state, settings

first = get_informed_time_plan(settings_informed, settings)

print(f"the periods {first['period']}")
print(f"the period length {len(first['period'])}")
print(f"the amount of shares {first['shares']}")
print(f"the amount of shares length {len(first['shares'])}")

action_count = 0
for time in range(1000):
    second = get_signal_informed(informed_state, settings_informed, time)
    if second[0] == 1:  # Action taken
        action_count += 1
        if time < 100:
            print(f"Action during warm-up at time {time}: {second}")
        else:
            print(f"Action after warm-up at time {time}: {second}")

print(f"Total actions taken: {action_count}")