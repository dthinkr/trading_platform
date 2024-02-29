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

# Agent Specification

- Set of All Agents: $\mathcal{A}$

  - Noise Trader: $\mathcal{N} \in \mathcal{A}$
- Observation Space $O_{\mathcal{N}}$: $O_{\mathcal{N}} = [b_{a}, b_{b}, \Delta, v_{i}, \mathbb{P}_\mathcal{N}]$

  - $b_{a}$ and $b_{b}$ are the best ask and bid prices.
  - $\Delta$ is the price spread between the best ask and bid.
  - $v_{i}$ is the volume imbalance between buy and sell orders.
  - $\mathbb{P}_\mathcal{N}$ is the set of of active orders by $\mathcal{N}$, where $\mathbb{P}_\mathcal{N} \in \mathbb{P}$
- Parameter Space $P_{\mathcal{N}}$: $P_{\mathcal{N}} = [\nu_0, p_{0}, \delta_0, n_{0}]$

  - $\nu_0$ is the activity frequency of the trader.
    - at each step, $\nu_{t}=\phi(\nu_0)$, where $\phi$ is a stochastic process
  - $p_{0}$ is the starting price for trading actions.
  - $\delta_0$ is the price step for order placement.
  - $n_{0}$ is the number of steps for price adjustment.
- Action Space $A_{\mathcal{N}}$: $A_{\mathcal{N}} = \{ [\alpha, \tau, \pi, q], [c, \tau, \iota] \}$

  - $\alpha$ is add order action.
  - $\tau$ is the order type, ask or bid.
  - $\pi$ is the price of order.
  - $q$ is the quantity of order.
  - $c$ is a cancel action for an order.
  - $\iota$ is the ID of the order to be cancelled.
