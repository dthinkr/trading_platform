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
                
                amount_key = "'amount': "
                start_index = msg_content.index(amount_key) + len(amount_key)
                end_index = msg_content.index(',', start_index)
                amount_str = msg_content[start_index:end_index].strip()  # Extract and strip whitespace
                amount = float(amount_str)
                
                price_key = "'price': "
                start_index = msg_content.index(price_key) + len(price_key)
                end_index = msg_content.index(',', start_index)
                price_str = msg_content[start_index:end_index].strip()  # Extract and strip whitespace
                price = float(price_str)
                
                direction_key = "<OrderType."
                start_index = msg_content.index(direction_key) + len(direction_key)
                end_index = msg_content.index(':', start_index)
                direction_str = msg_content[start_index:end_index].strip()  # Extract and strip whitespace
                direction = (direction_str)
                
                trader_key = "'trader_id': "
                start_index = msg_content.index(trader_key) + len(trader_key)
                end_index = msg_content.index(',', start_index)
                trader_str = msg_content[start_index:end_index].strip()  # Extract and strip whitespace
                trader_type = (trader_str)
                
                price_save.append(price)
                amount_save.append(amount)
                direction_save.append(direction)
                trader_save.append(trader_type)
                timestamp_save.append(timestamp_str)
                type_save.append(msg_type)
    
            if msg_type == 'CANCEL_ORDER':
                
                amount_key = "'amount': "
                start_index = msg_content.index(amount_key) + len(amount_key)
                end_index = msg_content.index(',', start_index)
                amount_str = msg_content[start_index:end_index].strip()  # Extract and strip whitespace
                amount = float(amount_str)
                
                price_key = "'price': "
                start_index = msg_content.index(price_key) + len(price_key)
                end_index = msg_content.index(',', start_index)
                price_str = msg_content[start_index:end_index].strip()  # Extract and strip whitespace
                price = float(price_str)
                
                
                direction_key = "'order_type': "
                start_index = msg_content.index(direction_key) + len(direction_key)
                end_index = msg_content.index('}', start_index)
                direction_str = msg_content[start_index:end_index].strip()  # Extract and strip whitespace
                direction = 'BID' if float(direction_str) == 1 else 'ASK'
                
                trader_key = "'trader_id': "
                start_index = msg_content.index(trader_key) + len(trader_key)
                end_index = msg_content.index(',', start_index)
                trader_str = msg_content[start_index:end_index].strip()  # Extract and strip whitespace
                trader_type = (trader_str)
            
                price_save.append(price)
                amount_save.append(amount)
                direction_save.append(direction)
                trader_save.append(trader_type)
                timestamp_save.append(timestamp_str)
                type_save.append(msg_type)
                
    df = pd.DataFrame({'Timestamp': timestamp_save,
                  'Price': price_save,
                  'Amount': amount,
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
    
    for index, row in message_df.iterrows():
        timestamp = row['Timestamp']
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
                                                        'Amount': order_to_remove['Amount']})
                        
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
                                                        'Amount': order_to_remove['Amount']})
            
        elif order_type == 'CANCEL_ORDER':
            if direction == 'BID':
                order_to_cancel = get_random_order(orders['BIDS'], trader)
                orders['BIDS'].remove(order_to_cancel)
                total_cancellations +=1
            else:
                order_to_cancel = get_random_order(orders['ASKS'], trader)
                orders['ASKS'].remove(order_to_cancel)
                total_cancellations +=1
        
        
        
        
    all_metrics = {'Total_Orders': message_df.shape[0],
                   'Total_Trades': total_trades,
                   'Total_Cancellations': total_cancellations}
    
    for trader in trades_by_human:
        trades_human_i = trades_by_human[trader]
        all_amounts = []
        all_prices = []
        
        for trade in trades_human_i:
            all_amounts.append(trade['Amount'])
            all_prices.append(trade['Price'])
        
        total_trades_trader_i = sum(all_amounts)
        trader_i_vwap = sum(all_prices) / total_trades_trader_i if total_trades_trader_i > 0 else 0
        
        all_metrics[trader] = {'Trades': total_trades_trader_i, 'VWAP': trader_i_vwap}
    
    return message_df, all_metrics

if __name__ == '__main__':
    location = '/Users/marioljonuzaj/Downloads/'
    logfile_name = location + 'SESSION_1729076783_trading.log'  # Replace with your log file path
    session_id = logfile_name.split('/')[-1].split('_trading')[0]
    
    message_df, all_metrics = order_book_contruction(logfile_name)
    
    output_message_file = location  + session_id + '_' + 'message_book.csv'
    message_df.to_csv(output_message_file, index=False)
    
    output_metrics_file = location  + session_id + '_' + ' metrics.json'

    # Save the dictionary to a JSON file
    with open(output_metrics_file, 'w') as json_file:
        json.dump(all_metrics, json_file, indent=4)

    
    
    


