
import random

import numpy as np

import datetime
import random


settings = {'levels_n': 10,  # int
            'initial_price': 2000,  # this implies a spread of 5bps
            'stack_max_size': 2,  # int
            'time_thresh': 1000,  # int how much to wait for a stack reset
            'n_updates_session': 900,  # if a session is 15min, then an update every 1secs
            'warmup_periods': 100,  # how may period we run the noise trader before starting
            'alphas_ewma': [0., .5, .95, .98]
            # other settings...
            }

settings_informed = {'inv': 100}

informed_state = {'inv': settings_informed['inv'], 'outstanding_orders': {'bid': {}, 'ask': {}}}


def get_informed_time_plan(settings_informed,settings):
    n_updates = settings['n_updates_session']
    inv_to_sell = settings_informed['inv']
    shares_per_period = inv_to_sell / n_updates # how many shares should sell in each time update

    if shares_per_period < 1 :
        time_periods_to_wait = int(round(1 / shares_per_period))
        time_periods_to_sell = list(np.arange(1, n_updates, time_periods_to_wait))
        shares_each_period = [1] * len(time_periods_to_sell)
    else:
        shares_each_period = int(-(-shares_per_period // 1))
        periods_needed = int(inv_to_sell / shares_each_period)
        time_periods_to_sell = list(np.arange(1, periods_needed + 1, 1))
        shares_each_period = [shares_each_period] * periods_needed

    informed_time_plan = {'period': time_periods_to_sell , 'shares': shares_each_period}
    return informed_time_plan


settings_informed.update(get_informed_time_plan(settings_informed, settings))


def get_signal_informed(informed_state, settings_informed, time):
    # time is the time count from to 100 to 1000 (100 warmup + sessions)
    time_count = time - settings['warmup_periods'] + 1

    current_inv = informed_state['inv']

    times_to_sell = settings_informed['period']
    shares_to_sell = settings_informed['shares']

    if time_count in times_to_sell:
        action = 1
        which = (time_count == np.array(times_to_sell))
        shares = int(np.array(shares_to_sell)[which])
        informed_state['inv'] = current_inv - shares  # update inventory of informed trader
    else:
        action = 0
        shares = 0

    signal_informed = [action, shares]

    return signal_informed

def get_informed_order(book, message, signal_informed, informed_state,settings_informed, settings):

    # the informed trader can only sell (if init_inv>0) or buy (if init_inv<0)
    action = signal_informed[0]
    num_shares = signal_informed[1]
    if action == 1 and settings_informed['inv'] > 0:
        price = book[ind_bid_price[0]]
        order = {'bid': {price: [num_shares]}, 'ask': {}}
    if action == 1 and settings_informed['inv'] < 0:
        price = book[ind_ask_price[0]]
        order = {'bid': {}, 'ask': {price: [num_shares]}}
    if action == 0:
        order = {}

    return order


