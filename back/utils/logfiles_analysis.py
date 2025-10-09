#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 18 11:33:57 2024

@author: marioljonuzaj
"""

import pandas as pd
import numpy as np
import random
import json
from datetime import datetime

def logfile_to_message(logfile_name):
    log_file_path = logfile_name
    timestamp_save = []
    price_save = []
    amount_save = []
    direction_save = []
    trader_save = []
    type_save = []
    
    
    with open(log_file_path, 'r') as log_file:
        for line in log_file:
            timestamp_str, level, msg = line.split(" - ", 2)
            msg_type, msg_content = msg.split(": ", 1)
    
            if msg_type == 'ADD_ORDER':
                try:
                    # Use ast.literal_eval to safely parse the dictionary string
                    import ast
                    
                    # Extract the dictionary part from the message
                    dict_start = msg_content.find('{')
                    dict_end = msg_content.rfind('}') + 1
                    dict_str = msg_content[dict_start:dict_end]
                    
                    # Replace problematic enum representations with simple values
                    dict_str = dict_str.replace('<OrderType.BID: 1>', '1')
                    dict_str = dict_str.replace('<OrderType.ASK: -1>', '-1')
                    dict_str = dict_str.replace('<OrderStatus.BUFFERED: \'buffered\'>', '\'buffered\'')
                    dict_str = dict_str.replace('<OrderStatus.ACTIVE: \'active\'>', '\'active\'')
                    
                    # Remove datetime objects - we'll use timestamp strings instead
                    import re
                    dict_str = re.sub(r'datetime\.datetime\([^)]+\)', 'None', dict_str)
                    
                    try:
                        parsed_dict = ast.literal_eval(dict_str)
                        amount = float(parsed_dict.get('amount', 0))
                        price = float(parsed_dict.get('price', 0))
                    except (ValueError, SyntaxError) as e:
                        print(f"Failed to parse with ast.literal_eval: {e}")
                        print(f"Attempting to parse: {dict_str[:200]}...")
                        # Fallback to old string parsing method
                        amount_key = "'amount': "
                        start_index = msg_content.index(amount_key) + len(amount_key)
                        end_index = msg_content.index(',', start_index)
                        amount_str = msg_content[start_index:end_index].strip()
                        print(f"Extracting amount: '{amount_str}'")
                        amount = float(amount_str)
                        
                        price_key = "'price': "
                        start_index = msg_content.index(price_key) + len(price_key)
                        end_index = msg_content.index(',', start_index)
                        price_str = msg_content[start_index:end_index].strip()
                        print(f"Extracting price: '{price_str}'")
                        price = float(price_str)
                    
                    # Get direction and trader from parsed dict if available, otherwise use string parsing
                    if 'parsed_dict' in locals():
                        order_type_val = parsed_dict.get('order_type', 1)
                        if order_type_val == 1 or order_type_val == '1':
                            direction = 'BID'
                        elif order_type_val == -1 or order_type_val == '-1':
                            direction = 'ASK'
                        else:
                            direction = 'BID'  # Default
                        
                        trader_type = str(parsed_dict.get('trader_id', 'UNKNOWN')).strip('\'"')
                    else:
                        # Fallback string parsing
                        if "<OrderType." in msg_content:
                            direction_key = "<OrderType."
                            start_index = msg_content.index(direction_key) + len(direction_key)
                            end_index = msg_content.index(':', start_index)
                            direction_str = msg_content[start_index:end_index].strip()
                            direction = direction_str
                        else:
                            direction = 'UNKNOWN'
                        
                        trader_key = "'trader_id': "
                        start_index = msg_content.index(trader_key) + len(trader_key)
                        end_index = msg_content.index(',', start_index)
                        trader_str = msg_content[start_index:end_index].strip()
                        trader_type = trader_str.strip('\'"')
                    
                    price_save.append(price)
                    amount_save.append(amount)
                    direction_save.append(direction)
                    trader_save.append(trader_type)
                    timestamp_save.append(timestamp_str)
                    type_save.append(msg_type)
                except Exception as e:
                    # Skip malformed ADD_ORDER entries with debug info
                    print(f"Warning: Skipping malformed ADD_ORDER entry: {e}")
                    continue
    
            if msg_type == 'CANCEL_ORDER':
                try:
                    # Use the same improved parsing as ADD_ORDER
                    import ast
                    
                    # Extract the dictionary part from the message
                    dict_start = msg_content.find('{')
                    dict_end = msg_content.rfind('}') + 1
                    dict_str = msg_content[dict_start:dict_end]
                    
                    # Replace problematic enum representations with simple values
                    dict_str = dict_str.replace('<OrderType.BID: 1>', '1')
                    dict_str = dict_str.replace('<OrderType.ASK: -1>', '-1')
                    dict_str = dict_str.replace('<OrderStatus.BUFFERED: \'buffered\'>', '\'buffered\'')
                    dict_str = dict_str.replace('<OrderStatus.ACTIVE: \'active\'>', '\'active\'')
                    dict_str = dict_str.replace('<OrderStatus.CANCELLED: \'cancelled\'>', '\'cancelled\'')
                    
                    # Remove datetime objects
                    import re
                    dict_str = re.sub(r'datetime\.datetime\([^)]+\)', 'None', dict_str)
                    
                    try:
                        parsed_dict = ast.literal_eval(dict_str)
                        amount = float(parsed_dict.get('amount', 0))
                        price = float(parsed_dict.get('price', 0))
                        
                        # Get direction from parsed dict
                        order_type_val = parsed_dict.get('order_type', 1)
                        if order_type_val == 1 or order_type_val == '1':
                            direction = 'BID'
                        elif order_type_val == -1 or order_type_val == '-1':
                            direction = 'ASK'
                        else:
                            direction = 'BID'  # Default
                        
                        trader_type = str(parsed_dict.get('trader_id', 'UNKNOWN')).strip('\'"')
                        
                    except (ValueError, SyntaxError) as e:
                        print(f"Failed to parse CANCEL_ORDER with ast.literal_eval: {e}")
                        # Fallback to safer string parsing
                        amount_key = "'amount': "
                        start_index = msg_content.index(amount_key) + len(amount_key)
                        end_index = msg_content.index(',', start_index)
                        amount_str = msg_content[start_index:end_index].strip()
                        amount = float(amount_str)
                        
                        price_key = "'price': "
                        start_index = msg_content.index(price_key) + len(price_key)
                        end_index = msg_content.index(',', start_index)
                        price_str = msg_content[start_index:end_index].strip()
                        price = float(price_str)
                        
                        # Fix the direction parsing to be safer
                        if "<OrderType.BID" in msg_content:
                            direction = 'BID'
                        elif "<OrderType.ASK" in msg_content:
                            direction = 'ASK'
                        else:
                            direction = 'BID'  # Default
                        
                        trader_key = "'trader_id': "
                        start_index = msg_content.index(trader_key) + len(trader_key)
                        end_index = msg_content.index(',', start_index)
                        trader_str = msg_content[start_index:end_index].strip()
                        trader_type = trader_str.strip('\'"')
                
                except Exception as e:
                    print(f"Error parsing CANCEL_ORDER: {e}")
                    continue  # Skip this line
                    
                price_save.append(price)
                amount_save.append(amount)
                direction_save.append(direction)
                trader_save.append(trader_type)
                timestamp_save.append(timestamp_str)
                type_save.append(msg_type)
            
            elif msg_type == 'MATCHED_ORDER':
                try:
                    # MATCHED_ORDER has simpler format: {'bid_order_id': 'X', 'ask_order_id': 'Y', 'transaction_price': 100.0, 'amount': 1.0}
                    import ast
                    
                    dict_start = msg_content.find('{')
                    dict_end = msg_content.rfind('}') + 1
                    dict_str = msg_content[dict_start:dict_end]
                    
                    parsed_dict = ast.literal_eval(dict_str)
                    amount = float(parsed_dict.get('amount', 0))
                    price = float(parsed_dict.get('transaction_price', 0))
                    
                    # For matched orders, we can extract trader info from the order IDs
                    bid_order_id = parsed_dict.get('bid_order_id', '')
                    ask_order_id = parsed_dict.get('ask_order_id', '')
                    
                    # We'll record this as a transaction, using the bid trader as the primary trader
                    if '_' in bid_order_id:
                        trader_type = bid_order_id.split('_')[0]
                    else:
                        trader_type = 'UNKNOWN'
                    
                    direction = 'MATCHED'  # Special type for matched orders
                    
                    price_save.append(price)
                    amount_save.append(amount)
                    direction_save.append(direction)
                    trader_save.append(trader_type)
                    timestamp_save.append(timestamp_str)
                    type_save.append(msg_type)
                    
                except Exception as e:
                    print(f"Error parsing MATCHED_ORDER: {e}")
                    continue  # Skip this line
                
    df = pd.DataFrame({'Timestamp': timestamp_save,
                  'Price': price_save,
                  'Amount': amount_save,
                  'Direction': direction_save,
                  'Type' : type_save,
                  'Trader': trader_save})
                
    df['Timestamp'] = pd.to_datetime(df['Timestamp'].str.replace(',', '.'), format='%Y-%m-%d %H:%M:%S.%f')
    

    return df



def get_best_ask_order(orders):
    best_ask_order = min(orders['ASKS'], key=lambda x: (x['Price'], x['Timestamp']))    
    return best_ask_order
    

def get_best_bid_order(orders):
    best_bid_price = max(order['Price'] for order in orders['BIDS'])
    
    orders_to_check = []
    for order in orders['BIDS']:
        if order['Price'] == best_bid_price:
            orders_to_check.append(order)
    
    best_bid_order = min(orders_to_check, key=lambda x:  x['Timestamp'])    
    return best_bid_order


def get_random_order(orders,trader):
    random_orders = []
    for order in orders:
        if order['Trader'] == trader:
            random_orders.append(order)
    
    return_order = random.choice(random_orders)
    
    return return_order

def get_order_to_cancel(orders,trader,price):
    orders_trader = [order for order in orders if order['Trader'] ==trader]
    orders_at_price = [order for order in orders_trader if order['Price'] ==price] 

    if orders_at_price:
        order_to_cancel = max(orders_at_price, key=lambda order: order['Timestamp'])
        return order_to_cancel
    else:
        # No order found at the specified price for this trader
        return None
    
def order_book_contruction(logfile_name):
    message_df, all_metrics = process_logfile(logfile_name)
    return all_metrics
    
def process_logfile(logfile_name):
    message_df = logfile_to_message(logfile_name)
    all_traders = list(np.unique(message_df.Trader))
    
    trades_by_human = {}

    for trader in all_traders:
        if 'HUMAN' in trader:
            trades_by_human[trader] = []
                
    orders = {'BIDS': [],'ASKS': []}
    total_trades = 0
    total_cancellations = 0
    all_midprices = []
    all_best_bid_prices = []
    all_best_ask_prices = []

    start_time = message_df['Timestamp'].iloc[0]
    message_df['New_Timestamp'] = (message_df['Timestamp'] - start_time).dt.total_seconds()

    
    for index, row in message_df.iterrows():
        timestamp = row['New_Timestamp']
        price = row['Price']
        amount = row['Amount']
        direction = row['Direction']
        order_type = row['Type']
        trader = row['Trader']
        
        new_order = {'Timestamp':timestamp,
                     'Price': price,
                     'Amount':amount,
                     'Direction': direction,
                     'Trader':trader}
        
        best_bid_price = max((order['Price'] for order in orders['BIDS']), default=None)
        best_ask_price = min((order['Price'] for order in orders['ASKS']), default=None)


        if order_type =='ADD_ORDER':
            if direction == 'BID':
                if best_ask_price is None:
                    orders['BIDS'].append(new_order)    
                elif price < best_ask_price:
                    orders['BIDS'].append(new_order)
                else:
                    order_to_remove = get_best_ask_order(orders)
                    orders['ASKS'].remove(order_to_remove)
                    total_trades +=1
                    if trader in trades_by_human:
                        trades_by_human[trader].append({'Price': order_to_remove['Price'],
                                                        'Amount': order_to_remove['Amount'],
                                                        'Type': 'Buy'})
                    if order_to_remove['Trader'] in trades_by_human:
                        name_to_use = order_to_remove['Trader']
                        trades_by_human[name_to_use].append({'Price': order_to_remove['Price'],
                                                        'Amount': order_to_remove['Amount'],
                                                        'Type': 'Sell'})

                        
            else:
                if best_bid_price is None:
                    orders['ASKS'].append(new_order)
                elif price > best_bid_price:
                    orders['ASKS'].append(new_order)
                else:
                    order_to_remove = get_best_bid_order(orders)
                    orders['BIDS'].remove(order_to_remove)
                    total_trades +=1
                    if trader in trades_by_human:
                        trades_by_human[trader].append({'Price': order_to_remove['Price'],
                                                        'Amount': order_to_remove['Amount'],
                                                        'Type': 'Sell'})
                    if order_to_remove['Trader'] in trades_by_human:
                        name_to_use = order_to_remove['Trader']
                        trades_by_human[name_to_use].append({'Price': order_to_remove['Price'],
                                                        'Amount': order_to_remove['Amount'],
                                                        'Type': 'Buy'})
            
        elif order_type == 'CANCEL_ORDER':
            if direction == 'BID':
                order_to_cancel = get_order_to_cancel(orders['BIDS'], trader, price)
                if order_to_cancel:
                    orders['BIDS'].remove(order_to_cancel)
                    total_cancellations +=1
                else:
                    print(f"Warning: Could not find BID order to cancel for trader {trader} at price {price}")
            else:
                order_to_cancel = get_order_to_cancel(orders['ASKS'], trader, price)
                if order_to_cancel:
                    orders['ASKS'].remove(order_to_cancel)
                    total_cancellations +=1
                else:
                    print(f"Warning: Could not find ASK order to cancel for trader {trader} at price {price}")
        
        
        best_bid_price = max((order['Price'] for order in orders['BIDS']), default=None)
        best_ask_price = min((order['Price'] for order in orders['ASKS']), default=None)

        if (best_bid_price is not None) and (best_ask_price is not None):
            midprice = (best_bid_price + best_ask_price) / 2
            all_best_bid_prices.append(best_bid_price)
            all_best_ask_prices.append(best_ask_price)
            all_midprices.append(midprice)
      
        
    all_metrics = {'Total_Orders': message_df.shape[0],
                   'Total_Trades': total_trades,
                   'Total_Cancellations': total_cancellations,
                   'Initial_Midprice': all_midprices[0],
                   'Last_Midprice': all_midprices[-1]}
    
    
    for trader in trades_by_human:
        trades_human_i = trades_by_human[trader]
        all_amounts = []
        all_prices = []
        
        num_buy = 0
        num_sell = 0
        prices_buy = []
        prices_sell = []
        for trade in trades_human_i:
            all_amounts.append(trade['Amount'])
            all_prices.append(trade['Price'])
            if trade['Type'] == 'Buy':
                prices_buy.append(trade['Price'])
                num_buy +=1
            else:
                prices_sell.append(trade['Price'])
                num_sell +=1
        
        total_trades_trader_i = sum(all_amounts)
        trader_i_vwap = sum(all_prices) / total_trades_trader_i if total_trades_trader_i > 0 else 0
        
        if num_buy == num_sell:
            pnl = sum(prices_sell) - sum(prices_buy)
        elif num_buy > num_sell:
            pnl = sum(prices_sell) - sum(prices_buy) + (num_buy - num_sell) * all_midprices[0]
        else:
            pnl = sum(prices_sell) - sum(prices_buy) - (num_sell - num_buy) * all_midprices[0]
        
        all_metrics[trader] = {'Trades': total_trades_trader_i,
                               'VWAP': trader_i_vwap,
                               'PnL': pnl,
                               'Num_Sell': num_sell,
                               'Num_Buy': num_buy,
                               'Prices_Sell': prices_sell,
                               'Prices_Buy': prices_buy}
    
    return message_df, all_metrics

def is_jsonable(x):
    try:
        json.dumps(x)
        return True
    except (TypeError, OverflowError):
        return False

def calculate_trader_specific_metrics(trader_specific_metrics, general_metrics, trader_goal):
    """Calculate trader-specific metrics based on trading activity and goals."""
    # Store the original PnL
    original_pnl = trader_specific_metrics['PnL']
    
    # Calculate reward with scaling between 3 and 10 based on PnL
    if isinstance(original_pnl, (int, float)):
        max_pnl_possible = 100
        max_gbp_to_give = 10
        if original_pnl<0:
            reward = 0
        else:
            ratio = original_pnl/max_pnl_possible
            real_ratio = min(ratio,1)
            reward = real_ratio * max_gbp_to_give
        # # Clip PnL to [-100, 100] range
        # capped_pnl = max(min(original_pnl, 100), -100)
        # # Scale PnL from [-100, 100] to [0, 1]
        # normalized_pnl = (capped_pnl + 100) / 200
        # # Scale to [3, 10] range
        # reward = 3 + (normalized_pnl * 7)
    else:
        reward = '-'
    
    if trader_goal != 0:
        if trader_goal > 0:
            if trader_specific_metrics['Trades'] <= trader_goal:
                remaining_trades = abs(abs(trader_goal) - abs(trader_specific_metrics['Trades']))
                expenditure = trader_specific_metrics['VWAP'] * trader_specific_metrics['Trades']
                total_expenditure = expenditure + remaining_trades * general_metrics['Last_Midprice'] * 1.5
                penalized_vwap = total_expenditure/abs(trader_goal)
                slippage = general_metrics['Initial_Midprice'] - penalized_vwap
                slippage_scaled = (general_metrics['Initial_Midprice'] - penalized_vwap) / np.sqrt(abs(trader_goal))
            
                trader_specific_metrics.update({
                    'Remaining_Trades': remaining_trades,
                    'Penalized_VWAP': penalized_vwap,
                    'Slippage': slippage,
                    'Slippage_Scaled': slippage_scaled,
                    'PnL': original_pnl,  # Keep original PnL
                    'Reward': reward
                })
            else:
                remaining_trades = abs(trader_goal) - abs(trader_specific_metrics['Trades'])
                prices_buy = trader_specific_metrics['Prices_Buy'] 
                expenditure = sum(prices_buy[0:abs(trader_goal)])
                VWAP = expenditure / abs(trader_goal)
                trader_specific_metrics['VWAP'] = VWAP
                penalized_vwap = expenditure / abs(trader_goal)
                slippage = general_metrics['Initial_Midprice'] - penalized_vwap
                slippage_scaled = (general_metrics['Initial_Midprice'] - penalized_vwap) / np.sqrt(abs(trader_goal))

                trader_specific_metrics.update({
                    'Remaining_Trades': remaining_trades,
                    'Penalized_VWAP': penalized_vwap,
                    'Slippage': slippage,
                    'Slippage_Scaled': slippage_scaled,
                    'PnL': original_pnl,
                    'Reward': reward
                })
        else:
            if trader_specific_metrics['Trades'] <= abs(trader_goal):
                remaining_trades = abs(abs(trader_goal) - abs(trader_specific_metrics['Trades']))
                expenditure = trader_specific_metrics['VWAP'] * trader_specific_metrics['Trades']
                total_expenditure = expenditure + remaining_trades * general_metrics['Last_Midprice'] * 0.5
                penalized_vwap = total_expenditure/abs(trader_goal)
                slippage = penalized_vwap - general_metrics['Initial_Midprice']
                slippage_scaled = (penalized_vwap - general_metrics['Initial_Midprice']) / np.sqrt(abs(trader_goal))
            
                trader_specific_metrics.update({
                    'Remaining_Trades': remaining_trades,
                    'Penalized_VWAP': penalized_vwap,
                    'Slippage': slippage,
                    'Slippage_Scaled': slippage_scaled,
                    'PnL': original_pnl,
                    'Reward': reward
                })
            else:
                remaining_trades = abs(trader_specific_metrics['Trades']) - abs(trader_goal) 
                prices_sell = trader_specific_metrics['Prices_Sell'] 
                expenditure = sum(prices_sell[0:abs(trader_goal)])
                VWAP = expenditure / abs(trader_goal)
                trader_specific_metrics['VWAP'] = VWAP
                penalized_vwap = expenditure / abs(trader_goal)
                slippage = penalized_vwap - general_metrics['Initial_Midprice']
                slippage_scaled = (penalized_vwap - general_metrics['Initial_Midprice']) / np.sqrt(abs(trader_goal))

                trader_specific_metrics.update({
                    'Remaining_Trades': remaining_trades,
                    'Penalized_VWAP': penalized_vwap,
                    'Slippage': slippage,
                    'Slippage_Scaled': slippage_scaled,
                    'PnL': original_pnl,
                    'Reward': reward
                })

    else:
        trader_specific_metrics.update({
            'Remaining_Trades': abs(trader_specific_metrics['Num_Sell'] - trader_specific_metrics['Num_Buy']),
            'VWAP': '-',
            'Penalized_VWAP': '-',
            'Slippage': '-',
            'Slippage_Scaled': '-',
            'PnL': original_pnl,
            'Reward': reward
        })
    
    return trader_specific_metrics

if __name__ == '__main__':
    location = '/Users/marioljonuzaj/Documents/Python Projects/Trading Platform/2025/June/trading_platform/back/logs/'
    logfile_name = location + 'SESSION_1749199327_trading.log'
    market_id = logfile_name.split('/')[-1].split('_trading')[0]
    message_df = logfile_to_message(logfile_name)
    order_book_metrics = order_book_contruction(logfile_name)
        
    output_message_file = location  + market_id + '_' + 'message_book.csv'
    #message_df.to_csv(output_message_file, index=False)
    
    output_metrics_file = location  + market_id + '_' + ' metrics.json'
    
    




