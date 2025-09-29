#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 24 16:36:03 2025

@author: marioljonuzaj
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

folder = '/Users/marioljonuzaj/Library/CloudStorage/Dropbox/InformationDisseminatationProject/Paper1/Data/September_Data/'
filename1 = 'T1_OB.csv'
filename2 = 'T2_OB.csv'

df1 = pd.read_csv(folder + filename1,header=0)
df2 = pd.read_csv(folder + filename2,header=0)
markets_to_use = [1749824165,1750154144]


df1 = df1.loc[df1.Market == markets_to_use[0]].reset_index(drop=True)
df2 = df2.loc[df2.Market == markets_to_use[1]].reset_index(drop=True)


df1 = df1.loc[df1.Trader_IM != "'PLATFORM'"].reset_index(drop=True)
df1 = df1.loc[df1.Trader_IM != "'BOOK_INITIALIZER'"].reset_index(drop=True)


df2 = df2.loc[df2.Trader_IM != "'PLATFORM'"].reset_index(drop=True)
df2 = df2.loc[df2.Trader_IM != "'BOOK_INITIALIZER'"].reset_index(drop=True)


plt.figure(figsize=(8,6))
plt.step(df1['Time'],df1['Midprice'],label='Midprice')
plt.ylabel('Midprice')
plt.xlabel('Time (secs)')
plt.legend(fontsize=10,loc='lower right')
plt.tight_layout()
filename_to_save = "20_midprice.png"
folder_to_save = '/Users/marioljonuzaj/Library/CloudStorage/Dropbox/InformationDisseminatationProject/platform-paper/figs/'
plt.savefig(folder_to_save +'/'+ filename_to_save, dpi=300, bbox_inches='tight')
plt.show()




plt.figure(figsize=(8,6))
plt.step(df1['Time'],df1['Bid_Price_1'],label='Best Bid Price')
plt.step(df1['Time'],df1['Ask_Price_1'],label='Best Ask Price',color='red')
mask_buy = (df1['Trader_IM'] == "'HUMAN_'") & (df1['Trader_IM_Direction'] == "BID") 
mask_sell = (df1['Trader_IM'] == "'HUMAN_'") & (df1['Trader_IM_Direction'] == "ASK") 
plt.scatter(df1.loc[mask_buy, 'Time'], df1.loc[mask_buy, 'Trader_IM_Price'], color='green', 
            s=70, marker='^', label='Human Buy Order')
plt.scatter(df1.loc[mask_sell, 'Time'], df1.loc[mask_sell, 'Trader_IM_Price'], color='purple', 
            s=70, marker='v', label='Human Sell Order')
plt.ylabel('Price')
plt.xlabel('Time (secs)')
plt.legend(fontsize=10,loc='lower right')
plt.tight_layout()
filename_to_save = "20_orders.png"
folder_to_save = '/Users/marioljonuzaj/Library/CloudStorage/Dropbox/InformationDisseminatationProject/platform-paper/figs/'
plt.savefig(folder_to_save +'/'+ filename_to_save, dpi=300, bbox_inches='tight')
plt.show()



plt.figure(figsize=(8,6))
plt.step(df1['Time'],df1['Bid_Price_1'],label='Best Bid Price')
plt.step(df1['Time'],df1['Ask_Price_1'],label='Best Ask Price',color='red')
mask_buy_aggressive = (df1['Liquidity_Taker'] == "'HUMAN_'") & (df1['Trader_IM_Direction'] == "BID")
mask_buy_passive = (df1['Liquidity_Provider'] == "'HUMAN_'") & (df1['Trader_IM_Direction'] == "ASK")
mask_sell_aggressive = (df1['Liquidity_Taker'] == "'HUMAN_'") & (df1['Trader_IM_Direction'] == "ASK")
mask_sell_passive = (df1['Liquidity_Provider'] == "'HUMAN_'") & (df1['Trader_IM_Direction'] == "BID")

plt.scatter(df1.loc[mask_buy_aggressive, 'Time'], df1.loc[mask_buy_aggressive, 'Trader_IM_Price'], color='green', 
            s=70, marker='^', label='Human Buy Trade (Liquidity Taker)')
plt.scatter(df1.loc[mask_sell_aggressive, 'Time'], df1.loc[mask_sell_aggressive, 'Trader_IM_Price'], color='purple', 
            s=70, marker='v', label='Human Sell Trade (Liquidity Taker)')
plt.scatter(df1.loc[mask_buy_passive, 'Time'], df1.loc[mask_buy_passive, 'Trader_IM_Price'], color='green', 
            s=70, marker='s', label='Human Buy Trade (Liquidity Provider)')
plt.scatter(df1.loc[mask_sell_passive, 'Time'], df1.loc[mask_sell_passive, 'Trader_IM_Price'], color='purple', 
            s=70, marker='s', label='Human Sell Trade (Liquidity Provider)')
plt.ylabel('Price')
plt.xlabel('Time (secs)')
plt.legend(fontsize=10,loc='lower right')
plt.tight_layout()
filename_to_save = "20_trades.png"
folder_to_save = '/Users/marioljonuzaj/Library/CloudStorage/Dropbox/InformationDisseminatationProject/platform-paper/figs/'
plt.savefig(folder_to_save +'/'+ filename_to_save, dpi=300, bbox_inches='tight')
plt.show()




plt.figure(figsize=(8,6))
plt.step(df1['Time'],df1['Bid_Price_1'],label='Best Bid Price')
plt.step(df1['Time'],df1['Ask_Price_1'],label='Best Ask Price',color='red')
mask_buy_aggressive = (df1['Liquidity_Taker'] == "'INFORMED_1'") & (df1['Trader_IM_Direction'] == "BID")
mask_buy_passive = (df1['Liquidity_Provider'] == "'INFORMED_1'") & (df1['Trader_IM_Direction'] == "BID")

plt.scatter(df1.loc[mask_buy_aggressive, 'Time'], df1.loc[mask_buy_aggressive, 'Trader_IM_Price'], color='grey', 
            s=70, marker='^', label='Informed Buy Trade (Liquidity Taker)')
plt.scatter(df1.loc[mask_buy_passive, 'Time'], df1.loc[mask_buy_passive, 'Trader_IM_Price'], color='grey', 
            s=70, marker='s', label='Informed Buy Trade (Liquidity Provider)')
plt.ylabel('Price')
plt.xlabel('Time (secs)')
plt.legend(fontsize=10,loc='lower right')
plt.tight_layout()
filename_to_save = "20_informed_trades.png"
folder_to_save = '/Users/marioljonuzaj/Library/CloudStorage/Dropbox/InformationDisseminatationProject/platform-paper/figs/'
plt.savefig(folder_to_save +'/'+ filename_to_save, dpi=300, bbox_inches='tight')
plt.show()


human_buy = ((df1['Liquidity_Taker'] == "'HUMAN_'") & (df1['Trader_IM_Direction'] == "BID")) | ((df1['Liquidity_Provider'] == "'HUMAN_'") & (df1['Trader_IM_Direction'] == "ASK"))
human_sell = ((df1['Liquidity_Taker'] == "'HUMAN_'") & (df1['Trader_IM_Direction'] == "ASK")) | ((df1['Liquidity_Provider'] == "'HUMAN_'") & (df1['Trader_IM_Direction'] == "BID"))


trades = human_buy.replace({False:0,True:1}) + human_sell.replace({False:0,True:-1})
plt.step(df1['Time'],trades.cumsum())
plt.ylabel('Inventory')
plt.xlabel('Time (secs)')
plt.yticks(range(-16,4,2))
plt.axhline(y=0,color='black',linestyle='dashed')
plt.tight_layout()
filename_to_save = "20_inv.png"
folder_to_save = '/Users/marioljonuzaj/Library/CloudStorage/Dropbox/InformationDisseminatationProject/platform-paper/figs/'
plt.savefig(folder_to_save +'/'+ filename_to_save, dpi=300, bbox_inches='tight')
plt.show()



tb = df1['Bid_Size_1'] + df1['Bid_Size_2'] + df1['Bid_Size_3'] + df1['Bid_Size_4'] + df1['Bid_Size_5']
ta = df1['Ask_Size_1'] + df1['Ask_Size_2'] + df1['Ask_Size_3'] + df1['Ask_Size_4'] + df1['Ask_Size_5']

imb = (tb - ta) / (tb + ta)
plt.step(df1['Time'],imb,)
plt.ylabel('Top 5 OB Imbalance')
plt.xlabel('Time (secs)')
plt.ylim(-1,1)
plt.axhline(y=0,color='black',linestyle='dashed')
plt.tight_layout()
filename_to_save = "20_imb.png"
folder_to_save = '/Users/marioljonuzaj/Library/CloudStorage/Dropbox/InformationDisseminatationProject/platform-paper/figs/'
plt.savefig(folder_to_save +'/'+ filename_to_save, dpi=300, bbox_inches='tight')
plt.show()



df1['5Second'] = (df1.Time/5).astype(int)

def get_stats(x):
    sell_orders = (x['Trader_IM_Direction'] == 'ASK').sum()
    buy_orders = (x['Trader_IM_Direction'] == 'BID').sum()
    ofi = (buy_orders - sell_orders) / (buy_orders + sell_orders)
    sell_trades = ((x['Trader_IM_Direction'] == 'ASK') & (x['Aggressive_Order'] == 'Yes')).sum()
    buy_trades = ((x['Trader_IM_Direction'] == 'BID') & (x['Aggressive_Order'] == 'Yes')).sum()
    tfi = (buy_trades - sell_trades) / (buy_trades + sell_trades)
    return pd.Series({'sell_orders': sell_orders,'buy_orders': buy_orders, 'OFI': ofi,'TFI':tfi})


df1_stats = df1.groupby('5Second').apply(lambda x: get_stats(x)).reset_index()

plt.step(df1_stats['5Second'],df1_stats['OFI'])
plt.ylabel('OFI')
plt.xlabel('Time (5 secs)')
plt.ylim(-1.1,1.1)
plt.axhline(y=0,color='black',linestyle='dashed')
plt.tight_layout()
filename_to_save = "20_ofi.png"
folder_to_save = '/Users/marioljonuzaj/Library/CloudStorage/Dropbox/InformationDisseminatationProject/platform-paper/figs/'
plt.savefig(folder_to_save +'/'+ filename_to_save, dpi=300, bbox_inches='tight')
plt.show()

plt.step(df1_stats['5Second'],df1_stats['TFI'])
plt.ylabel('TFI')
plt.xlabel('Time (5 secs)')
plt.ylim(-1.1,1.1)
plt.axhline(y=0,color='black',linestyle='dashed')
plt.tight_layout()
filename_to_save = "20_tfi.png"
folder_to_save = '/Users/marioljonuzaj/Library/CloudStorage/Dropbox/InformationDisseminatationProject/platform-paper/figs/'
plt.savefig(folder_to_save +'/'+ filename_to_save, dpi=300, bbox_inches='tight')
plt.show()


#####################################
# df2 :  043


plt.figure(figsize=(8,6))
plt.step(df2['Time'],df2['Midprice'],label='Midprice')
plt.ylabel('Midprice')
plt.xlabel('Time (secs)')
plt.legend(fontsize=10,loc='lower right')
plt.tight_layout()
filename_to_save = "40_midprice.png"
folder_to_save = '/Users/marioljonuzaj/Library/CloudStorage/Dropbox/InformationDisseminatationProject/platform-paper/figs/'
plt.savefig(folder_to_save +'/'+ filename_to_save, dpi=300, bbox_inches='tight')
plt.show()


plt.figure(figsize=(8,6))
plt.step(df2['Time'],df2['Bid_Price_1'],label='Best Bid Price')
plt.step(df2['Time'],df2['Ask_Price_1'],label='Best Ask Price',color='red')
mask_buy = (df2['Trader_IM'] == "'HUMAN_'") & (df2['Trader_IM_Direction'] == "BID") 
mask_sell = (df2['Trader_IM'] == "'HUMAN_'") & (df2['Trader_IM_Direction'] == "ASK") 
plt.scatter(df2.loc[mask_buy, 'Time'], df2.loc[mask_buy, 'Trader_IM_Price'], color='green', 
            s=70, marker='^', label='Human Buy Order')
plt.scatter(df2.loc[mask_sell, 'Time'], df2.loc[mask_sell, 'Trader_IM_Price'], color='purple', 
            s=70, marker='v', label='Human Sell Order')
plt.ylabel('Price')
plt.xlabel('Time (secs)')
plt.legend(fontsize=10,loc='lower right')
plt.tight_layout()
filename_to_save = "40_orders.png"
folder_to_save = '/Users/marioljonuzaj/Library/CloudStorage/Dropbox/InformationDisseminatationProject/platform-paper/figs/'
plt.savefig(folder_to_save +'/'+ filename_to_save, dpi=300, bbox_inches='tight')
plt.show()



plt.figure(figsize=(8,6))
plt.step(df2['Time'],df2['Bid_Price_1'],label='Best Bid Price')
plt.step(df2['Time'],df2['Ask_Price_1'],label='Best Ask Price',color='red')
mask_buy_aggressive = (df2['Liquidity_Taker'] == "'HUMAN_'") & (df2['Trader_IM_Direction'] == "BID")
mask_buy_passive = (df2['Liquidity_Provider'] == "'HUMAN_'") & (df2['Trader_IM_Direction'] == "ASK")
mask_sell_aggressive = (df2['Liquidity_Taker'] == "'HUMAN_'") & (df2['Trader_IM_Direction'] == "ASK")
mask_sell_passive = (df2['Liquidity_Provider'] == "'HUMAN_'") & (df2['Trader_IM_Direction'] == "BID")

plt.scatter(df2.loc[mask_buy_aggressive, 'Time'], df2.loc[mask_buy_aggressive, 'Trader_IM_Price'], color='green', 
            s=70, marker='^', label='Human Buy Trade (Liquidity Taker)')
plt.scatter(df2.loc[mask_sell_aggressive, 'Time'], df2.loc[mask_sell_aggressive, 'Trader_IM_Price'], color='purple', 
            s=70, marker='v', label='Human Sell Trade (Liquidity Taker)')
plt.scatter(df2.loc[mask_buy_passive, 'Time'], df2.loc[mask_buy_passive, 'Trader_IM_Price'], color='green', 
            s=70, marker='s', label='Human Buy Trade (Liquidity Provider)')
plt.scatter(df2.loc[mask_sell_passive, 'Time'], df2.loc[mask_sell_passive, 'Trader_IM_Price'], color='purple', 
            s=70, marker='s', label='Human Sell Trade (Liquidity Provider)')
plt.ylabel('Price')
plt.xlabel('Time (secs)')
plt.legend(fontsize=10,loc='lower right')
plt.tight_layout()
filename_to_save = "40_trades.png"
folder_to_save = '/Users/marioljonuzaj/Library/CloudStorage/Dropbox/InformationDisseminatationProject/platform-paper/figs/'
plt.savefig(folder_to_save +'/'+ filename_to_save, dpi=300, bbox_inches='tight')
plt.show()



human_buy = ((df2['Liquidity_Taker'] == "'HUMAN_'") & (df2['Trader_IM_Direction'] == "BID")) | ((df2['Liquidity_Provider'] == "'HUMAN_'") & (df2['Trader_IM_Direction'] == "ASK"))
human_sell = ((df2['Liquidity_Taker'] == "'HUMAN_'") & (df2['Trader_IM_Direction'] == "ASK")) | ((df2['Liquidity_Provider'] == "'HUMAN_'") & (df2['Trader_IM_Direction'] == "BID"))


trades = human_buy.replace({False:0,True:1}) + human_sell.replace({False:0,True:-1})
plt.figure(figsize=(8,6))
plt.step(df2['Time'],trades.cumsum())
plt.ylabel('Inventory')
plt.xlabel('Time (secs)')
plt.axhline(y=0,color='black',linestyle='dashed')
plt.yticks(range(0,20,2))
plt.tight_layout()
filename_to_save = "40_inv.png"
folder_to_save = '/Users/marioljonuzaj/Library/CloudStorage/Dropbox/InformationDisseminatationProject/platform-paper/figs/'
plt.savefig(folder_to_save +'/'+ filename_to_save, dpi=300, bbox_inches='tight')
plt.show()



plt.figure(figsize=(8,6))
plt.step(df2['Time'],df2['Bid_Price_1'],label='Best Bid Price')
plt.step(df2['Time'],df2['Ask_Price_1'],label='Best Ask Price',color='red')
mask_buy_aggressive = (df2['Liquidity_Taker'] == "'INFORMED_1'") & (df2['Trader_IM_Direction'] == "BID")
mask_buy_passive = (df2['Liquidity_Provider'] == "'INFORMED_1'") & (df2['Trader_IM_Direction'] == "BID")

plt.scatter(df2.loc[mask_buy_aggressive, 'Time'], df2.loc[mask_buy_aggressive, 'Trader_IM_Price'], color='grey', 
            s=70, marker='^', label='Informed Buy Trade (Liquidity Taker)')
plt.scatter(df2.loc[mask_buy_passive, 'Time'], df2.loc[mask_buy_passive, 'Trader_IM_Price'], color='grey', 
            s=70, marker='s', label='Informed Buy Trade (Liquidity Provider)')
plt.ylabel('Price')
plt.xlabel('Time (secs)')
plt.legend(fontsize=10,loc='lower right')
plt.tight_layout()
filename_to_save = "40_informed_trades.png"
folder_to_save = '/Users/marioljonuzaj/Library/CloudStorage/Dropbox/InformationDisseminatationProject/platform-paper/figs/'
plt.savefig(folder_to_save +'/'+ filename_to_save, dpi=300, bbox_inches='tight')
plt.show()


tb = df2['Bid_Size_1'] + df2['Bid_Size_2'] + df2['Bid_Size_3'] + df2['Bid_Size_4'] + df2['Bid_Size_5']
ta = df2['Ask_Size_1'] + df2['Ask_Size_2'] + df2['Ask_Size_3'] + df2['Ask_Size_4'] + df2['Ask_Size_5']

imb = (tb - ta) / (tb + ta)
plt.figure(figsize=(8,6))
plt.step(df2['Time'],imb,)
plt.ylabel('Top 5 OB Imbalance')
plt.xlabel('Time (secs)')
plt.ylim(-1,1)
plt.axhline(y=0,color='black',linestyle='dashed')
plt.tight_layout()
filename_to_save = "40_imb.png"
folder_to_save = '/Users/marioljonuzaj/Library/CloudStorage/Dropbox/InformationDisseminatationProject/platform-paper/figs/'
plt.savefig(folder_to_save +'/'+ filename_to_save, dpi=300, bbox_inches='tight')
plt.show()




df2['5Second'] = (df2.Time/5).astype(int)

def get_stats(x):
    sell_orders = (x['Trader_IM_Direction'] == 'ASK').sum()
    buy_orders = (x['Trader_IM_Direction'] == 'BID').sum()
    ofi = (buy_orders - sell_orders) / (buy_orders + sell_orders)
    sell_trades = ((x['Trader_IM_Direction'] == 'ASK') & (x['Aggressive_Order'] == 'Yes')).sum()
    buy_trades = ((x['Trader_IM_Direction'] == 'BID') & (x['Aggressive_Order'] == 'Yes')).sum()
    tfi = (buy_trades - sell_trades) / (buy_trades + sell_trades)
    return pd.Series({'sell_orders': sell_orders,'buy_orders': buy_orders, 'OFI': ofi,'TFI':tfi})

df2_stats = df2.groupby('5Second').apply(lambda x: get_stats(x)).reset_index()

plt.figure(figsize=(8,6))
plt.step(df2_stats['5Second'],df2_stats['OFI'])
plt.ylabel('OFI')
plt.xlabel('Time (5 secs)')
plt.ylim(-1.1,1.1)
plt.axhline(y=0,color='black',linestyle='dashed')
plt.tight_layout()
filename_to_save = "40_ofi.png"
folder_to_save = '/Users/marioljonuzaj/Library/CloudStorage/Dropbox/InformationDisseminatationProject/platform-paper/figs/'
plt.savefig(folder_to_save +'/'+ filename_to_save, dpi=300, bbox_inches='tight')
plt.show()


plt.figure(figsize=(8,6))
plt.step(df2_stats['5Second'],df2_stats['TFI'])
plt.ylabel('TFI')
plt.xlabel('Time (5 secs)')
plt.ylim(-1.1,1.1)
plt.axhline(y=0,color='black',linestyle='dashed')
plt.tight_layout()
filename_to_save = "40_tfi.png"
folder_to_save = '/Users/marioljonuzaj/Library/CloudStorage/Dropbox/InformationDisseminatationProject/platform-paper/figs/'
plt.savefig(folder_to_save +'/'+ filename_to_save, dpi=300, bbox_inches='tight')
plt.show()


