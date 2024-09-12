# Short intro

The fastapi that launches the system is in `api` subfolder.

To launch it you need to do:

```bash
uvicorn api.endpoints:app --reload
```

the endpoint to launch the trading system is `http://localhost:8000/trading/initiate`
and it will return you the human trader id.
Using this trader id you can connect using websockets to
`ws://localhost:8000/trader/{trader_id}`

The fastapi (in api/main.py) launches the TraderManager (from api/trader_manager.py) which is responsible for launching the trading_session and creating and managing the traders.

The code for trading_session in `core/trading_platform.py`
The code for single traders is in folder `traders`
There we have:

- base_trader.py - Where the BaseTrader class is located
- human_trader.py - Where the HumanTrader subclass of BaseTrader is located
- noise_trader.py - Where the NoiseTrader subclass of BaseTrader is located. The noise trader is a prototype. It actually should be based on
  external code  (located in external_traders/noise_trader.py) but for now it is a simple random trader.

the folder `data_models` contain the dataclasses used in the project. I want to keep all the structure definitions in one place.