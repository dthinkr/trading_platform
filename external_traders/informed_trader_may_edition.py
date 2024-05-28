
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May  9 11:31:30 2024

@author: wenbin & mariol
"""

import numpy as np
from datetime import datetime
import time

settings = {
    "levels_n": 5,  # int
    "initial_price": 2000,  # this implies a spread of 5bps
}

# this settings are received by the platform
# we need:
# (1) time period of the round (e.g. 3 minutes)
# (2) trade intensity (e.g. she will trade 30% of the total orders)
# (3) to buy or sel
# (4) noise trader frequency activity
settings_informed = {'time_period_in_min': 5, 'NoiseTrader_frequency_activity': 1,
                     'trade_intensity': 0.10, 'direction': 'sell'}

# given that all the rest should run without any change

def update_settings_informed(settings_informed):
    settings_informed["total_seconds"] = settings_informed["time_period_in_min"] * 60
    settings_informed['seconds_to_complete_exec'] = settings_informed["total_seconds"] - 10
    settings_informed['noise_activity'] = int(settings_informed['total_seconds'] * settings_informed['NoiseTrader_frequency_activity'] )
    settings_informed['inv'] = int(settings_informed['noise_activity'] * settings_informed['trade_intensity'] / (1 - settings_informed['trade_intensity']))

    settings_informed["sn"] = settings_informed['seconds_to_complete_exec'] / settings_informed["inv"]


    if settings_informed["direction"] == "sell":
        informed_state = {"inv": settings_informed["inv"]}
    else:
        informed_state = {"inv": -settings_informed["inv"]}


    informed_state['time_to_sleep'] = settings_informed['sn']
    
    return settings_informed, informed_state


settings_informed, informed_state = update_settings_informed(settings_informed)

start_time = datetime.now()

def get_signal_informed(informed_state):
    # time here is the clock time measured by the platform
    # if this is not convenient, Wenbin propose something else

    if informed_state["inv"] != 0:
        action = 1
        shares = 1
    else:
        action = 0
        shares = 0

    signal_informed = [action, shares]

    return signal_informed



def get_time_to_sleep(settings_informed,informed_state,start_time):
    current_time = datetime.now()
    time_passed = (current_time - start_time).total_seconds()
    total_time_to_exec = settings_informed['seconds_to_complete_exec'] 
    time_remaining = total_time_to_exec - time_passed
    informed_state['time_to_sleep'] = time_remaining / informed_state['inv']
    return informed_state
    


def get_order_to_match(book, informed_state, settings_informed, start_time):
    # the informed trader can only sell (if init_inv>0) or buy (if init_inv<0)
    # print(signal_informed)

    # first goes to sleep and then sends the order
     
    informed_state = get_time_to_sleep(settings_informed,informed_state,start_time)
    time.sleep(informed_state['time_to_sleep'])
    
    action , num_shares = get_signal_informed(informed_state)

    if action == 1 and settings_informed["direction"] == "sell":
        price = book[2]  # best bid
        order = {"bid": {price: [num_shares]}, "ask": {}}

    if action == 1 and settings_informed["direction"] == "buy":
        price = book[0]  # best ask
        order = {"bid": {}, "ask": {price: [num_shares]}}

    if action == 0:
        order = {}

    return order
