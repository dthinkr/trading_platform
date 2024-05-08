import numpy as np


settings = {'levels_n': 10,  # int
            'initial_price': 2000,  # this implies a spread of 5bps
            }

# this settings are received by the platform
# we need:
# (1) time period of the round (e.g. 3 minutes)
# (2) trade intensity (e.g. she will trade 30% of the total orders)
# (3) to buy or sell
# (4) noise trader frequency activity
settings_informed = {'time_period_in_min': 5, 'NoiseTrader_frequency_activity': 1,
                     'trade_intensity': 0.10, 'direction': 'sell'}

# given that all the rest should run without any change


settings_informed['total_seconds'] = settings_informed['time_period_in_min'] * 60
settings_informed['noise_activity'] = int(settings_informed['total_seconds'] * settings_informed['NoiseTrader_frequency_activity'] )

settings_informed['inv'] = int(settings_informed['noise_activity'] * settings_informed['trade_intensity'] / (1 - settings_informed['trade_intensity']))
settings_informed['sn'] = (settings_informed['total_seconds'] - 10) / settings_informed['inv']


time_plan = [settings_informed['sn']] * settings_informed['inv']
informed_time_plan = {'period': np.cumsum(time_plan)}


def get_informed_state(settings_informed):
    if settings_informed['direction'] == 'sell':
        informed_state = {'inv': settings_informed['inv']}
    else:
        informed_state = {'inv': -settings_informed['inv']}
    
    return informed_state

informed_state = get_informed_state(settings_informed)




def get_signal_informed(informed_state, settings_informed, informed_time_plan, time):
    # time here is the clock time measured by the platform
    # if this is not convenient, Wenbin propose something else
    
    times_to_act = informed_time_plan['period'].astype(int)
    
    if time in times_to_act and informed_state['inv'] !=0 :
        action = 1
        shares = 1
    else:
        action = 0
        shares = 0

    signal_informed = [action, shares]

    return signal_informed

def get_informed_order(book, informed_state,settings_informed, settings,time):

    # the informed trader can only sell (if init_inv>0) or buy (if init_inv<0)
    signal_informed = get_signal_informed(informed_state, settings_informed, informed_time_plan, time)
    action = signal_informed[0]
    num_shares = signal_informed[1]
    
    if action == 1 and settings_informed['direction'] == 'sell':
        price = book[ind_bid_price[0]]
        order = {'bid': {price: [num_shares]}, 'ask': {}}
        
    if action == 1 and settings_informed['direction'] == 'buy':
        price = book[ind_ask_price[0]]
        order = {'bid': {}, 'ask': {price: [num_shares]}}
        
    if action == 0:
        order = {}

    return order


# this function should be called if there is 
# a succesfull matching 
# else get_informed_order should be recalled to send new 
# order at the new best bid or ask
def update_informed_inv(informed_state):
    
    current_inv = informed_state['inv']
    
    if current_inv>0:
      informed_state['inv'] -= 1
    elif current_inv <0 :
      informed_state['inv'] += 1
     
    return informed_state


