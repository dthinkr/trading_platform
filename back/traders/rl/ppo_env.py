import gym
import numpy as np
from gym import spaces
from core.data_models import OrderType


class TradingEnvironment(gym.Env):
    def __init__(self, trading_session):
        super().__init__()
        self.trading_session = trading_session

        self.previous_portfolio_value = (
            self.trading_session.cash
            + self.trading_session.shares * self.trading_session.mid_price
        )

        # Define observation space
        self.observation_space = spaces.Dict(
            {
                "order_book": spaces.Dict(
                    {
                        "best_bid": spaces.Box(
                            low=0, high=np.inf, shape=(2,)
                        ),  # price, volume
                        "best_ask": spaces.Box(
                            low=0, high=np.inf, shape=(2,)
                        ),  # price, volume
                        "depth": spaces.Box(
                            low=0, high=np.inf, shape=(10, 2)
                        ),  # 5 levels each side
                    }
                ),
                "transactions": spaces.Dict(
                    {
                        "last_price": spaces.Box(low=0, high=np.inf, shape=(1,)),
                        "vwap": spaces.Box(low=0, high=np.inf, shape=(1,)),
                    }
                ),
                "market_stats": spaces.Dict(
                    {
                        "mid_price": spaces.Box(low=0, high=np.inf, shape=(1,)),
                        "spread": spaces.Box(low=0, high=np.inf, shape=(1,)),
                        "imbalance": spaces.Box(low=-1, high=1, shape=(1,)),
                    }
                ),
                "trader_state": spaces.Dict(
                    {
                        "cash": spaces.Box(low=-np.inf, high=np.inf, shape=(1,)),
                        "shares": spaces.Box(low=0, high=np.inf, shape=(1,)),
                        "unrealized_pnl": spaces.Box(
                            low=-np.inf, high=np.inf, shape=(1,)
                        ),
                    }
                ),
                "time": spaces.Dict(
                    {
                        "elapsed": spaces.Box(low=0, high=np.inf, shape=(1,)),
                        "remaining": spaces.Box(low=0, high=np.inf, shape=(1,)),
                    }
                ),
            }
        )

        # Define action space (0: do nothing, 1: buy, 2: sell)
        self.action_space = spaces.Discrete(3)

    def _get_observation(self):
        order_book = self.trading_session.get_order_book_snapshot()
        transactions = self.trading_session.get_transaction_history()

        obs = {
            "order_book": {
                "best_bid": np.array(
                    [order_book["bids"][0]["price"], order_book["bids"][0]["amount"]]
                ),
                "best_ask": np.array(
                    [order_book["asks"][0]["price"], order_book["asks"][0]["amount"]]
                ),
                "depth": np.array(
                    [
                        [level["price"], level["amount"]]
                        for level in order_book["bids"][:5] + order_book["asks"][:5]
                    ]
                ),
            },
            "transactions": {
                "last_price": np.array([self.trading_session.transaction_price or 0]),
                "vwap": np.array([self._calculate_vwap(transactions)]),
            },
            "market_stats": {
                "mid_price": np.array([self.trading_session.mid_price]),
                "spread": np.array([self.trading_session.order_book.get_spread()[0]]),
                "imbalance": np.array([self._calculate_imbalance(order_book)]),
            },
            "trader_state": {
                "cash": np.array([self.trading_session.cash]),
                "shares": np.array([self.trading_session.shares]),
                "unrealized_pnl": np.array([self._calculate_unrealized_pnl()]),
            },
            "time": {
                "elapsed": np.array([self.trading_session.get_elapsed_time()]),
                "remaining": np.array(
                    [
                        self.trading_session.duration * 60
                        - self.trading_session.get_elapsed_time()
                    ]
                ),
            },
        }
        return obs

    def _calculate_reward(self):
        portfolio_value_change = self._calculate_portfolio_value_change()
        transaction_cost = self._calculate_transaction_cost()
        holding_penalty = self._calculate_holding_penalty()
        inventory_penalty = self._calculate_inventory_penalty()

        reward = (
            portfolio_value_change
            - transaction_cost
            - holding_penalty
            - inventory_penalty
        )
        return reward

    def _calculate_vwap(self, transactions):
        if not transactions:
            return 0
        volume_price_sum = sum(t["price"] * t["amount"] for t in transactions)
        total_volume = sum(t["amount"] for t in transactions)
        return volume_price_sum / total_volume if total_volume > 0 else 0

    def _calculate_imbalance(self, order_book):
        bid_volume = sum(level["amount"] for level in order_book["bids"][:5])
        ask_volume = sum(level["amount"] for level in order_book["asks"][:5])
        total_volume = bid_volume + ask_volume
        return (bid_volume - ask_volume) / total_volume if total_volume > 0 else 0

    def _calculate_unrealized_pnl(self):
        current_price = self.trading_session.mid_price
        return self.trading_session.shares * (
            current_price - self.trading_session.average_entry_price
        )

    def _calculate_portfolio_value_change(self):
        current_value = (
            self.trading_session.cash
            + self.trading_session.shares * self.trading_session.mid_price
        )
        previous_value = self.previous_portfolio_value
        self.previous_portfolio_value = current_value
        return current_value - previous_value

    def _calculate_transaction_cost(self):
        return 0.001 * abs(self.last_action_shares * self.trading_session.mid_price)

    def _calculate_holding_penalty(self):
        return 0.0001 * abs(
            self.trading_session.shares * self.trading_session.mid_price
        )

    def _calculate_inventory_penalty(self):
        time_remaining = (
            self.trading_session.duration * 60 - self.trading_session.get_elapsed_time()
        )
        if time_remaining < 60:  # Last minute of trading
            return 0.001 * (self.trading_session.shares**2)
        return 0

    def step(self, action):
        # Execute the action
        if action == 1:  # Buy
            self.last_action_shares = 1
            self.trading_session.place_order(
                {
                    "trader_id": "rl_agent",
                    "order_type": OrderType.BID,
                    "amount": 1,
                    "price": self.trading_session.mid_price,
                }
            )
        elif action == 2:  # Sell
            self.last_action_shares = -1
            self.trading_session.place_order(
                {
                    "trader_id": "rl_agent",
                    "order_type": OrderType.ASK,
                    "amount": 1,
                    "price": self.trading_session.mid_price,
                }
            )
        else:
            self.last_action_shares = 0

        # Calculate reward
        reward = self._calculate_reward()

        # Get new observation
        obs = self._get_observation()

        # Check if the episode is done
        done = (
            self.trading_session.get_elapsed_time()
            >= self.trading_session.duration * 60
        )

        return obs, reward, done, {}

    def reset(self):
        # Reset the trading session
        self.trading_session.reset()
        self.previous_portfolio_value = (
            self.trading_session.cash
            + self.trading_session.shares * self.trading_session.mid_price
        )
        self.last_action_shares = 0
        return self._get_observation()
