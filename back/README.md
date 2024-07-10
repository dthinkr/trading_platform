# Short intro

The fastapi that launches the system is in `client_connector` subfolder.

To launch it you need to do:

```bash
uvicorn client_connector.main:app --reload
```

the endpoint to launch the trading system is `http://localhost:8000/trading/initiate`
and it will return you the human trader id.
Using this trader id you can connect using websockets to
`ws://localhost:8000/trader/{trader_id}`

The fastapi (in client_connector/main.py) launches the TraderManager (from client_connector/trader_manager.py) which is responsible for launching the trading_session and creating and managing the traders.

The code for trading_session in `main_platform/trading_platform.py`
The code for single traders is in folder `traders`
There we have:

- base_trader.py - Where the BaseTrader class is located
- human_trader.py - Where the HumanTrader subclass of BaseTrader is located
- noise_trader.py - Where the NoiseTrader subclass of BaseTrader is located. The noise trader is a prototype. It actually should be based on
  external code  (located in external_traders/noise_trader.py) but for now it is a simple random trader.

the folder `structures` contain the dataclasses used in the project. I want to keep all the structure definitions in one place.

# Main Changes

## July 4 2024

1. Noise Trader Behavior:
   - Enhanced to override existing orders when sending a new one

2. Order Book State:
   - Implemented controlled function $M: \text{Parameters} \rightarrow \text{Order Book State}$
   - [Book initializer](https://github.com/dthinkr/trader_london/blob/e84347657ed0f6794a7484a7164dd34e27c0042e/traders/book_initializer.py) now sets the initial order book state 

3. Default Price:
   - Removed hard-coded default price (2000)
   - Price is now a configurable parameter throughout the system

4. Informed Trader Behavior:
   - Orders now based on best bid plus an edge parameter: $\text{Order Price} = \text{Best Bid} + \text{Informed Edge}$
   - Order execution logic: - If $\text{Best Bid} + \text{Informed Edge} \geq \text{Top Ask}$, send order

Additional Notes:
- Some recent changes to the informed trader were reverted due to conflicts
- Database connection requires further optimization for deployment
- #2 the Book initializer is necessary because it handles the order book intialization. 
- #4 Informed does not always send order. Potentially, this could lead to it not finishing its task, but such likelihood is rare, whcih can be studied. 

Extra Changes:

1. Timer and agents now do not act until the order book is initialized. 
2. The timer in the frontend is no longer a mock and can sync with the backend. 