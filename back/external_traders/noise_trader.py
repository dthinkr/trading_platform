#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug  2 10:14:44 2023

@author: alessio
"""

import numpy as np
# import numba
import datetime
from main_platform.custom_logger import setup_custom_logger


logger = setup_custom_logger(__name__)


# I list quantities that will be needed in the experiments
# what is inside the place holder functions will be defined on a case by case basis


# the following will be the input

# settings will be defined and contain basic information

# price increments are in multiples of 1 and minimum spread is 1.
# Initial price is a settings and defines cost of transactions
# e.g. initial price =2000 means that the minimum spread is 1/2000= 5 basis points

settings = {'levels_n': 10,  # int
            'initial_price': 2000,  # this implies a spread of 5bps
            'stack_max_size': 2,  # int
            'time_thresh': 1000,  # int how much to wait for a stack reset
            'n_updates_session': 900,  # if a session is 15min, then an update every 1secs
            'warmup_periods': 100,  # how may period we run the noise trader before starting
            'alphas_ewma': [0., .5, .95, .98]
            # other settings...
            }

settings_market_maker = {'n_levels': 3,  # the number of levels at which to post orders
                         'inv_limit': 5,
                         # total number of shared allowed: this should be a function of the thickness of the book
                         }

settings_informed = {'inv': 100}

settings_noise = {'pr_order': 1,  # probability of a noise trader order arrival
                  'pr_passive': .7,  # probability of resting order
                  'pr_bid': .5,  # equal prob of bid or ask order }
                  'pr_cancel': .2,  # probability of an order cancellation
                  'levels_n': settings['levels_n'],  # it could be different
                  'max_size_level': 3  # the largest size in a level, after that will post on the next
                  }

# this might be extended, but for definiteness assume two predicitons models only
# models  = {'market_maker':'an sklearn fitted model for the market maker',
#            'together with feature_ind (int/bool) for ind in features_state',
#            'informed': 'an sklearn fitted model for the informed trader',
#            'together with feature_ind (int/bool) for ind in features_state'}

models = {'market_maker': {'model': None, 'feature_ind': None},
          'informed': {'model': None, 'feature_ind': None}}

# book: I provide the name of the columns for the sake a definiteness

# these are the entries
levels_n = int(settings['levels_n'])  # usually 10
cols_raw = ['ask_price', 'ask_size', 'bid_price', 'bid_size']
cols_book = [name + '_' + str(level) for level in range(1, 1 + levels_n) \
             for name in cols_raw]
cols_book

book = {'a 2d (or 1d) array of  shape (1, len(cols_book)) and types float'}

# message: I provide the name of the columns for the sake a definiteness

# these are the entries
cols_message = ['time', 'type', 'id', 'size', 'price', 'direction']

message = {'a 2d (or 1d) array of  shape (1, len(cols_messsage)) and types float'}

# state_count

# these are the entries
cols_state_count = ['count', 'time_delta']

# state_count      = {' a 1d array of shape (len(cols_state_count),)'}
state_count = np.array([0, 0])
# book_stack

# these are the entries
cols_book_stack = cols_book

book_stack = {"a 2d array of shape (settings['stack_max_size'],len(cols_book)) and types as book"}

# message_stack

# these are the entries
cols_message_stack = cols_message

message_stack = {"a 2d array of shape (settings['stack_max_size'],len(cols_message)) and types as book"}

# #book_of_stack
# cols_book_of_stack =
# book_of_stack      = {"a 2d array of shape (settings['stack_max_size'],len(cols_message)) and types as book"}


# features_state

# these are the entries
cols_features_state = {'they will vary: they are intermediate inputs not used by the interface'}

# features_state = {"a 1d array of shape (len(cols_features_state),) and type floats"}
n_features = 22  # This should be set to the actual number of features
n_alphas = 3  # This should be set to the actual number of alphas

features_state = np.zeros(n_alphas * n_features)
# signals state

# these are the entries
cols_signals_state = {'they will vary: they are intermediate inputs not used by the interface',
                      ' e.g. market_maker, informed'}

signals_state = {"a 1d array (or dictionary) of shape (len(cols_signals_state,) and type floats"}

# in theory a general trader state has inventory, outstanding order
market_maker_state = {'inv': 0, 'outstanding_orders': {'bid': {}, 'ask': {}}}

informed_state = {'inv': settings_informed['inv'], 'outstanding_orders': {'bid': {}, 'ask': {}}}

noise_state = {'inv': None, 'outstanding_orders': {'bid': {},
                                                   'ask': {}}}  # noise trader does not keep track if inventory but needs outstanding_orders for cancellations

# example of outstanding orders format: if needed use id, but not needed, it think.
# outstanding_orders = {'bid':{2003:4,2002:1}, 'ask': {2011:1,2016:2,2018:1}}
# new orders are in the same format as outstanding_orders
# queue: prices as key inside the key there is a size and an id
# bid_queue_dict = {bid_p[i]: [[bid_s[i]], [-1]] for i in range(len(bid_p))}
# ask_queue_dict = {ask_p[i]: [[ask_s[i]], [-1]] for i in range(len(ask_p))}
# example of bid_queue_dict format: i use -1 for noise and some integer for other traders
bid_queue_dict = {2003: [[4, 2], [-1, 2]], 2002: [[5], [-1]]}


# above, at bid price 2003 there is an order of size 4 for id -1
# and one of size 2 for id 2. Orders at given price are appended
# at price [5] there is a size of 5 for id -1


# functions that will be called by the interface


# call at the start to generate additional settings: can also be treated as global outside settings
# called only once so no need for performance
def get_ind_from_data(cols, name2search='bid_price'):
    ind_col = [i for i, x in enumerate(cols) if x[:len(name2search)] == name2search]

    return ind_col


ind_bid_price = get_ind_from_data(cols_book, name2search='bid_price')
ind_bid_size = get_ind_from_data(cols_book, name2search='bid_size')
ind_ask_price = get_ind_from_data(cols_book, name2search='ask_price')
ind_ask_size = get_ind_from_data(cols_book, name2search='ask_size')

cols_message = ['time', 'type', 'id', 'size', 'price', 'direction']

ind_time = get_ind_from_data(cols_message, name2search='time')
ind_type = get_ind_from_data(cols_message, name2search='type')
ind_id = get_ind_from_data(cols_message, name2search='id')
ind_size = get_ind_from_data(cols_message, name2search='size')
ind_price = get_ind_from_data(cols_message, name2search='price')
ind_direction = get_ind_from_data(cols_message, name2search='direction')

settings.update({'ind_bid_price': ind_bid_price, 'ind_bid_size': ind_bid_size,
                 'ind_ask_price': ind_ask_price, 'ind_ask_size': ind_ask_size,
                 'ind_time': ind_time, 'ind_type': ind_type, 'ind_id': ind_id,
                 'ind_size': ind_size, 'ind_price': ind_price, 'ind_direction': ind_direction})


# anything in settings could be used as "global variable" with no settings argument in functions

# call every time there is a book update

def get_state_count_update(state_count, book_stack, message_stack, settings):
    if state_count[0] > 0:
        time = message_stack[settings['ind_time']]
        state_count[1] = time[state_count[1]] - time[0]
    state_count[0] += 1
    return state_count


def get_stack_update_1(book, message, book_stack, message_stack, state_count, settings):
    time_thresh = settings['time_thresh']
    stack_max_size = settings['stack_max_size']
    count = state_count[0]
    time_delta = state_count[1]
    cond_reset = (time_delta >= time_thresh) or (count > stack_max_size)
    if cond_reset:
        count = 0
        time_delta = 0
        state_count = [0, 0]
    book_stack[count] = book
    message_stack[count] = message
    state_count = get_state_count_update(state_count, book_stack, message_stack, settings)
    return (book_stack, message_stack, state_count)


def get_stack_update(book, message, book_stack, message_stack, state_count, settings):
    # rolling stack
    time_thresh = settings['time_thresh']
    stack_max_size = settings['stack_max_size']
    count = state_count[0]
    time_delta = state_count[1]
    cond_increse = (count < stack_max_size)
    if cond_increse:
        book_stack[count] = book
        count += 1
        state_count = [count, 0]
    else:  # drop the first in stack and add new to the last
        book_stack[:count - 1] = book_stack[1:]
        book_stack[-1] = book
        message_stack[:count - 1] = message_stack[1:]
        message_stack[-1] = message
    return (book_stack, message_stack, state_count)


def get_should_update_1(state_count, settings):
    # this is just an example: same rule as for stack in this case
    time_thresh = settings['time_thresh']
    stack_max_size = settings['stack_max_size']
    count = state_count[0]
    time_delta = state_count[1]
    # cond_update    = (time_delta>= time_thresh) or (count>stack_max_size)
    cond_update = True  # always update
    return cond_update


def get_should_update(state_count, settings):
    # this is just an example: same rule as for stack in this case
    time_thresh = settings['time_thresh']
    stack_max_size = settings['stack_max_size']
    count = state_count[0]
    time_delta = state_count[1]
    cond_update = (count == stack_max_size)
    return cond_update


# only called if output of get_should_update is true


def transform_book(book_stack, settings):
    levels_n = settings['levels_n']
    book_of_stack = np.zeros((len(book_stack), levels_n))

    bid_p = book_stack[:, settings['ind_bid_price']]
    ask_p = book_stack[:, settings['ind_ask_price']]
    bid_s = book_stack[:, settings['ind_bid_size']]
    ask_s = book_stack[:, settings['ind_bid_size']]

    dbid_p = bid_p[1:] - bid_p[:-1]
    dask_p = bid_p[1:] - bid_p[:-1]

    cond_bid_1 = dbid_p >= 0
    cond_bid_2 = dbid_p <= 0

    cond_ask_1 = dask_p >= 0
    cond_ask_2 = dask_p <= 0

    bid_of = bid_s[1:] * cond_bid_1 - bid_s[:-1] * cond_bid_2
    ask_of = -(ask_s[1:] * cond_ask_2 - ask_s[:-1] * cond_ask_1)

    # cols_b_of    = ['bid_of_'+str(x) for x in range(1,1+levels_n)]
    # cols_a_of    = ['ask_of_'+str(x) for x in range(1,1+levels_n)]
    # cols_of      = cols_b_of+cols_a_of

    book_of_stack[1:] = bid_of + ask_of  # np.c_[bid_of,ask_of]
    return book_of_stack


def get_features_stack_update(features_stack, book, message, book_of, settings):
    # performs the update: i.e. compute the latest features based on stack
    return features_stack


def get_features_update(features_state, book_stack, message_stack, settings, cols_ft=None):
    features_state = list(features_state)
    alphas = settings['alphas_ewma']
    n_alphas = len(alphas)
    n_features = 22  # This should be set to the actual number of features
    n_alphas = 3  # This should be set to the actual number of alphas

    features_state = np.zeros(n_alphas * n_features)
    levels_n = settings['levels_n']
    ind_bid_price1 = settings['ind_bid_price'][0]
    ind_bid_price1 = settings['ind_bid_price'][0]
    ind_ask_price1 = settings['ind_ask_price'][0]

    bid_p1 = book_stack[-1, ind_bid_price1]
    ask_p1 = book_stack[-1, ind_ask_price1]
    bid_p1l = book_stack[-2, ind_bid_price1]
    ask_p1l = book_stack[-2, ind_ask_price1]

    mid = 0.5 * (bid_p1 + ask_p1)
    midl = 0.5 * (bid_p1l + ask_p1l)

    of = transform_book(book_stack, settings)[-1]  # if stack longer than 2, only use the latest
    of_abs = np.abs(of)
    dmid = 2 * (mid - midl) / (mid + midl)
    dmid_abs = np.abs(dmid)

    # signed_trd  =
    # trd         = np.abs(signed_trd)

    # features_new = np.r_[book_of,book_of_abs,dmid ,dmid_abs,signed_trd,trd ]

    features_new = np.r_[of, dmid, of_abs, dmid_abs]
    cols_features = None
    if cols_features is None:
        cols_of = ['of_' + str(level) for level in range(1, 1 + levels_n)]
        cols_dmid = ['dmid']
        cols_of_abs = [col_of + '_abs' for col_of in cols_of]
        cols_dmid_abs = ['dmid_abs']
        cols_features = cols_of + cols_dmid + cols_of_abs + cols_dmid_abs

    n_features = len(features_new)

    if features_state is None:  # no features have been computed so far
        features_state = np.zeros((n_alphas * len(features_new),))
        if cols_ft is not None:  # perform a check - only at the very beginning that we are computing the correct features
            cols_of = ['of_' + str(level) for level in range(1, 1 + levels_n)]
            cols_dmid = ['dmid']
            cols_of_abs = [col_of + '_abs' for col_of in cols_of]
            cols_dmid_abs = ['dmid_abs']
            cols_features = cols_of + cols_dmid + cols_of_abs + cols_dmid_abs
            col_features = [col_features + '_' + str(int(100 * alpha)) for alpha in alphas for col_features in
                            cols_features]
            if cols_ft != cols_features: raise Exception('features are not as expected: check settings')

    for i in range(n_alphas):
        alpha = alphas[i]

        ewma_block_i = features_state[(i * n_features):((i + 1) * n_features)]
        ewma_block_i = np.array(ewma_block_i)
        features_new = np.array(features_new)

        ewma_block_i = alpha * ewma_block_i + (1 - alpha) * features_new

        features_state[(i * n_features):((i + 1) * n_features)] = ewma_block_i

    # update features names with ewma

    return features_state


def ewma_update(ewma_val, x, alpha):
    ew
    for alpha in alphas:
        ewma_val = alpha * ewma_val + (1 - alpha) * x
    return ewma_val


def get_model_prediction(features, model, settings):
    """Its just a placeholder. SHould be replaced by the actual model prediction"""

    return np.random.uniform(0, 1)


def get_signal_update(features_state, models, settings):
    # example
    model_names = list(models.keys())
    signals_state = np.zeros((len(model_names),))
    for i, model_name in enumerate(model_names):
        model = models[model_name]
        features_ind = model['feature_ind']
        features = features_state[features_ind]
        model_fitted = model['model']
        signals_state[i] = get_model_prediction(features, model, settings)
    return signals_state


# call every time there is a book update

# unpack the signals

def get_signal_market_maker(signal_state, settings_market_maker):
    signal_market_maker = signal_state[0]  # better use some names and let signal_state be a dict
    return signal_market_maker


def get_signal_informed(signal_state, settings_informed):
    signal_market_maker = signal_state[1]  # better use some names and let signal_state be a dict
    return signal_informed


def get_signal_noise(signal_state, settings_noise):
    """It seems that this one is used to randomly generate events (posts: bids/asks and cancels).
    It returns a list of parameters that are used to generate the events.
    I personally would prefer for readability to have a function that returns a dict of parameters.
    It's unclear for me why we need signal_state here.
    """

    pr_order = settings_noise['pr_order']
    pr_bid = settings_noise['pr_bid']
    pr_passive = settings_noise['pr_passive']
    pr_cancel = settings_noise['pr_cancel']
    features_noise = np.random.rand(7)  # could be part of features state, but makes it more complex

    # is an order placed?
    event_order = pr_order >= features_noise[0]
    # is the order passive?
    event_passive = pr_passive >= features_noise[1]
    # is it on the bid?
    event_bid = pr_bid >= features_noise[2]
    # is an order cancelled?
    event_cancel = pr_cancel >= features_noise[3]
    # is cancel on bid?
    event_bid_cancel = pr_bid >= features_noise[4]
    # some random mumbers to choose depth if needed
    insert_depth = features_noise[5]
    cancel_depth = features_noise[6]

    signal = [event_order, event_passive, event_bid, event_cancel, event_bid_cancel, insert_depth, cancel_depth]
    return signal


def get_market_maker_order(book, message, signal_market_maker, market_maker_state,
                           settings_market_maker, settings):
    # do someting and get order in the following format
    # order = {'bid':{2003:4,2002:1}, 'ask': {2011:1,2016:2,2018:1}}
    # order = {'bid':{}, 'ask': {}}#no order
    # order = {'bid':{2003:4,2002:1}, 'ask': {}}#one side order
    return order


def get_order_to_match(book, message, signal_informed, informed_state,
                       settings_informed, settings):
    # do someting and get order in the following format
    # order = {'bid':{2003:4,2002:1}, 'ask': {2011:1,2016:2,2018:1}}
    # order = {'bid':{}, 'ask': {}}#no order
    # order = {'bid':{2003:4,2002:1}, 'ask': {}}#one side order
    return order


def get_noise_rule(book, signal_noise, noise_state, settings_noise, settings):
    """
       book - book state,
       signal_noise - an array of parameters that are used to generate the events.
       noise state - a dict with a key outstanding_orders that contains a list of outstanding orders for this specific trader
       settings_noise - a dict with parameters for noise trader
       settings - a dict with general parameters

       If book is provided, and signal noise and trader's current state (in noise_state), then
       it returns a list of orders to be placed (or cancelled if the quantity is negative).
       """
    price_name = ['ask', 'bid']

    max_size_level = settings_noise['max_size_level']

    event_order = signal_noise[0]
    event_passive =  signal_noise[1]
    event_bid = signal_noise[2]
    event_cancel = signal_noise[3]
    event_bid_cancel = signal_noise[4]

    cancel_depth = signal_noise[6]

    order = {'bid': {}, 'ask': {}}

    if event_order:

        ind_bid_price = settings['ind_bid_price']
        ind_bid_size = settings['ind_bid_size']
        ind_ask_price = settings['ind_ask_price']
        ind_ask_size = settings['ind_ask_size']

        ind_price = [ind_ask_price, ind_bid_price]
        ind_size = [ind_ask_size, ind_bid_size]

        event_bid_int = int(event_bid)

        if event_passive:
            # find the sizes and prices on the book
            book_size = book[ind_size[event_bid_int]]
            book_price = book[ind_price[event_bid_int]]
            price = get_noise_condition_price(book_price, book_size, max_size_level)

            if price >= 0:
                size = 1
                order[price_name[event_bid_int]].update({price: [size]})

        else:
            price = book[ind_price[event_bid_int][0]] + (
                    2 * event_bid_int - 1)  # price improve: if spread is small, then it aggresses
            size = 1
            order[price_name[event_bid_int]].update({price: [size]})
        price2cancel = None
        if event_cancel:  # there is also a cancel event, irrespective of the above
            # if there are outstanding orders, it cancels one at random
            outstanding_orders = noise_state['outstanding_orders']
            if event_bid_cancel:
                outstanding_bids = outstanding_orders['bid']
                L = len(outstanding_bids)
                if L > 0:  # this is almost always the case
                    ind_key = int(np.floor(cancel_depth * L))
                    outstanding_prices = list(outstanding_bids.keys())
                    price2cancel = outstanding_prices[ind_key]

            else:
                outstanding_asks = outstanding_orders['ask']
                L = len(outstanding_asks)
                if L > 0:  # this is almost always the case
                    ind_key = int(np.floor(cancel_depth * L))
                    outstanding_prices = list(outstanding_asks.keys())
                    price2cancel = outstanding_prices[ind_key]
            if price2cancel is not None:

                size2cancel = -1  # negative means cancellation
                event_bid_cancel_int = int(event_bid_cancel)

                if price2cancel not in order[price_name[event_bid_cancel_int]]:
                    order[price_name[event_bid_cancel_int]].update({price2cancel: [size2cancel]})
                else:  # amend the existing order
                    size_order_final = order[price_name[event_bid_cancel_int]][price2cancel][0] + size2cancel
                    if size_order_final != 0:
                        order[price_name[event_bid_cancel_int]][price2cancel][0] = size_order_final
                    else:
                        order[price_name[event_bid_cancel_int]].pop(price2cancel)  # delete, no order

    return order


def get_noise_rule_unif(book, signal_noise, noise_state, settings_noise, settings):
    # price_name     = ['ask_price','bid_price']
    # size_name      = ['ask_size','bid_size']
    price_name = ['ask', 'bid']
    price2cancel = None
    pr_order = settings_noise['pr_order']
    pr_bid = settings_noise['pr_bid']
    pr_passive = settings_noise['pr_passive']
    n_levels = settings_noise['levels_n']

    max_size_level = settings_noise['max_size_level']

    event_order = signal_noise[0]
    event_passive = signal_noise[1]
    event_bid = signal_noise[2]
    event_cancel = signal_noise[3]
    event_bid_cancel = signal_noise[4]

    cancel_depth = signal_noise[6]

    order = {'bid': {}, 'ask': {}}


    if event_order:

        ind_bid_price = settings['ind_bid_price']
        ind_bid_size = settings['ind_bid_size']
        ind_ask_price = settings['ind_ask_price']
        ind_ask_size = settings['ind_ask_size']

        ind_price = [ind_ask_price, ind_bid_price]
        ind_size = [ind_ask_size, ind_bid_size]

        n_levels = settings['levels_n']
        mid = (book[ind_ask_price[0]] + book[ind_bid_price[0]]) / 2
        edge = np.floor(np.random.rand(1) * n_levels) + 0.5*(1 + float(np.mod(mid,1)==0))

        event_bid_int = int(event_bid)
        if event_passive:
                price = int(mid + [-2 * event_bid_int +1] * edge)
                size = 1
                order[price_name[event_bid_int]].update({price: [size]})
        else:
                price = int(mid + (2*event_bid_int -1) * np.mod(mid,1))
                size = 2
                order[price_name[event_bid_int]].update({price: [size]})

        if event_cancel:  # there is also a cancel event, irrespective of the above
            # if there are outstanding orders, it cancels one at random
            outstanding_orders = noise_state['outstanding_orders']
            if event_bid_cancel:
                outstanding_bids = outstanding_orders['bid']
                L = len(outstanding_bids)
                if L > 0:  # this is almost always the case
                    ind_key = int(np.floor(cancel_depth * L))
                    outstanding_prices = list(outstanding_bids.keys())
                    price2cancel = outstanding_prices[ind_key]

            else:
                outstanding_asks = outstanding_orders['ask']
                L = len(outstanding_asks)
                if L > 0:  # this is almost always the case
                    ind_key = int(np.floor(cancel_depth * L))
                    outstanding_prices = list(outstanding_asks.keys())
                    price2cancel = outstanding_prices[ind_key]

            size2cancel = -1  # negative means cancellation
            event_bid_cancel_int = int(event_bid_cancel)

            if price2cancel not in order[price_name[event_bid_cancel_int]]:
                order[price_name[event_bid_cancel_int]].update({price2cancel: [size2cancel]})
            else:  # amend the existing order
                size_order_final = order[price_name[event_bid_cancel_int]][price2cancel][0] + size2cancel
                if size_order_final != 0:
                    order[price_name[event_bid_cancel_int]][price2cancel][0] = size_order_final
                else:
                    order[price_name[event_bid_cancel_int]].pop(price2cancel)  # delete, no order

    return order


def get_noise_order(book, signal_noise, noise_state,
                    settings_noise, settings):
    order = get_noise_rule(book, signal_noise, noise_state, settings_noise, settings)

    return order


# auxiliary: they can change and will be placed inside the other functions


# finds the first price at which there is a size less than max_size_level, else gives -1
# @numba.jit('float64(float64[:],float64[:], float64)', nopython=True)

def get_noise_condition_price(prices, sizes, max_size_level):

    # Zip the prices and sizes, then find the first pair where size is either zero or less than max_size_level
    for p, s in zip(prices, sizes):
        if s < max_size_level:
            return p  # return the price of the first such pair

    return -1  # if no such pair exists, return -1




# execution code
# this part updates the bid side of the order book using an ask price and size.
# @numba.jit(numba.types.Tuple((numba.float64[:], numba.float64, numba.float64))(numba.float64[:], numba.float64[:],
#                                                                                numba.float64, numba.float64),
#            nopython=True)
def get_exec_sell_trd(bid_prices, bid_sizes,
                      order_ask_price, order_ask_size):
    bid_sizes_new = bid_sizes
    i = 0
    n = len(bid_sizes)
    cond = order_ask_price <= bid_prices[i]
    if cond:
        exec_size = 0
        exec_price = 0
        order_ask_size_tot = order_ask_size
        order_ask_size_new = order_ask_size

        while cond:
            order_ask_size = order_ask_size_new  # size to execute at level i
            bid_size_i = bid_sizes[i] - order_ask_size  # size left on book at level i
            bid_sizes_new[i] = np.maximum(bid_size_i, 0)  # new size in book at level i
            order_ask_size_new = np.maximum(-bid_size_i, 0)  # residual size to execute at next level

            exec_price = exec_price \
                         + bid_prices[i] \
                         * (order_ask_size - order_ask_size_new)  # weighted sum pe exec price

            i += 1
            cond = (order_ask_price <= bid_prices[i]) & \
                   (order_ask_size_new > 0) & (i < n)
            # print(order_ask_size_new)
        exec_size = (order_ask_size_tot - order_ask_size_new)
        exec_price = exec_price / exec_size
    else:
        exec_size = np.nan
        exec_price = np.nan

    return (bid_sizes_new, exec_price, exec_size)


def get_insert_sell(ask_prices, ask_sizes,
                    order_ask_price, order_ask_size):
    ask_sizes_new = ask_sizes
    ask_prices_new = ask_prices
    n = len(ask_sizes)
    cond = order_ask_price in ask_prices
    if cond:
        ind_insertion = list(ask_prices).index(order_ask_price)
        ask_sizes_new[ind_insertion] += order_ask_size
    elif (order_ask_price < ask_prices[0]):  # need to modify the price with new insertion if price improves
        ask_prices_new = np.empty((n,))
        ask_sizes_new = np.empty((n,))
        ask_prices_new[0] = order_ask_price
        ask_prices_new[1:] = ask_prices[:-1]
        ask_sizes_new[0] = order_ask_size
        ask_sizes_new[1:] = ask_sizes[:-1]
    return (ask_prices_new, ask_sizes_new)


# running example


prices = np.array([10, 4, 6, 2, 3, 5, 6, 7, 1, 3]) + 0.
sizes = np.array([10, 4, 6, 2, 3, 5, 6, 7, 1, 3]) + 0.
max_size_level = 5


# some test for me, ignore



def get_book_message_init(best_bid, size, settings):
    levels_n = settings['levels_n']
    book = np.zeros((4 * levels_n,))
    # bid_price
    book[settings['ind_bid_price']] = np.linspace(best_bid, best_bid - 9, 10)
    # ask_price
    book[settings['ind_ask_price']] = np.linspace(best_bid + 1, best_bid + 10, 10)
    # bid_size
    book[settings['ind_bid_size']] = size * np.ones((levels_n,))
    # ask_size
    book[settings['ind_ask_size']] = size * np.ones((levels_n,))

    # message
    # cols_message     = ['time', 'type','id', 'size','price', 'direction']

    message = np.array([0, 2, 1, 1, best_bid, 1])
    return (book, message)


cond = True
iter_num = 0
max_iter = 1000

# initialise the book
best_bid = 2009
size = 1
book, message = get_book_message_init(best_bid, size, settings)

bid_p = book[settings['ind_bid_price']]
ask_p = book[settings['ind_ask_price']]
bid_s = book[settings['ind_bid_size']]
ask_s = book[settings['ind_ask_size']]

# id -1 as the book is initialised by noise traders
bid_queue_dict = {bid_p[i]: [[bid_s[i]], [-1]] for i in range(len(bid_p))}
ask_queue_dict = {ask_p[i]: [[ask_s[i]], [-1]] for i in range(len(ask_p))}

# initialise the noise_state
outstanding_bid_noise = {bid_p[i]: [bid_s[i]] for i in range(len(bid_p))}
outstanding_ask_noise = {ask_p[i]: [ask_s[i]] for i in range(len(ask_p))}
noise_state = {'outstanding_orders': {'bid': outstanding_bid_noise, 'ask': outstanding_ask_noise}}

book_stack = np.zeros((settings['stack_max_size'], len(cols_book)))
message_stack = np.zeros((settings['stack_max_size'], len(cols_message)))

state_count = np.array([0, 0])

tic = datetime.datetime.now()

while cond:
    book_stack, message_stack, state_count = get_stack_update(book, message,
                                                              book_stack, message_stack,
                                                              state_count, settings)

    cond_update_auxiliary_objects = get_should_update(state_count, settings)
    # if true run all the following processes
    if cond_update_auxiliary_objects:  # update features and signal
        features_state = get_features_update(features_state, book_stack, message_stack, settings)
        signals_state = get_signal_update(features_state, models, settings)

    # call each subscribed trader`

    signal_noise = get_signal_noise(signals_state, settings_noise)
    order_noise = get_noise_order(book, signal_noise, noise_state,
                                  settings_noise, settings)

    # put together all the orders: only one as we only have one trader

    orders = [order_noise, -1]  # only one order with id -1, the one of noise trader

    # do the matching here, modify
    # 1. book, message
    # it may leads to multiple updates, but only report the last one,
    # but in message to report the type as trade if there was one and include price and size
    # 2.bid_queue_dict, ask_queue_dict
    # 3. the state of all the traders, including the outstanding orders
    iter_num += 1
    cond = iter_num < max_iter