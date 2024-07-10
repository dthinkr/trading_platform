# files in this folder are responsible for connecting the trading system to the web interface via websockets
# and for handling the communication between the trading system and the web interface

The HumanTrader class will be moved to traderabbit/trader.py in the future or will subclass it.

The HumanTrader is basically a normal trader but with abilities to receive messages from the real human being via sockets,
and to send updates back.

## type of messages FROM user
The messages HumanTrader is able to receive from humans are:
1. human is connected
2. human is disconnected
3. putting an aggressive bid
4. putting an aggressive ask
5. putting a passive bid
6. putting a passive ask

"aggresive" ask or bid covers the spread at the best available price level (if any)
"passive" ask or bid is put at the best available price level (if any) but does not cover the spread

## type of messages TO user

The messages HumanTrader is able to send to humans are:
1. the current state of the order book
2. the current state of the trader's orders
3. the current state of the trader's balance
4. average price of the last 10 trades
