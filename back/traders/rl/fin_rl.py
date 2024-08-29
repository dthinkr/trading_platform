from __future__ import annotations

import gymnasium as gym
from gymnasium import spaces
import pandas as pd
import numpy as np
from finrl import config
from finrl.meta.preprocessor.yahoodownloader import YahooDownloader
from finrl.meta.preprocessor.preprocessors import FeatureEngineer, data_split
from finrl.meta.env_stock_trading.env_stocktrading import StockTradingEnv
from finrl.agents.stablebaselines3.models import DRLAgent
from stable_baselines3.common.vec_env import DummyVecEnv


class ModifiedStockTradingEnv(StockTradingEnv):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Change action space to Discrete
        self.action_space = spaces.Discrete(3 * self.stock_dim)

    def _sell_stock(self, index, action):
        if self.state[index + self.stock_dim + 1] > 0:
            # Sell only if the price is > 0 (no missing data in this particular date)
            # perform sell action based on the sign of the action
            if action == 2:
                # Sell all shares
                sell_num_shares = self.state[index + self.stock_dim + 1]
                sell_amount = (
                    self.state[index + 1]
                    * sell_num_shares
                    * (1 - self.sell_cost_pct[index])
                )
                # update balance
                self.state[0] += sell_amount
                self.state[index + self.stock_dim + 1] = 0
                self.cost += (
                    self.state[index + 1] * sell_num_shares * self.sell_cost_pct[index]
                )
                self.trades += 1
            else:
                # Hold shares
                pass
        else:
            # If we don't have any shares, do nothing
            pass

    def _buy_stock(self, index, action):
        if self.state[index + 1] > 0:
            # Buy only if the price is > 0 (no missing data in this particular date)
            # Determine the number of shares to buy based on the action
            if action == 1:
                # Buy shares with all available cash
                available_amount = self.state[0] // self.state[index + 1]
                # update balance
                buy_num_shares = min(available_amount, self.hmax)
                buy_amount = (
                    self.state[index + 1]
                    * buy_num_shares
                    * (1 + self.buy_cost_pct[index])
                )
                self.state[0] -= buy_amount
                self.state[index + self.stock_dim + 1] += buy_num_shares
                self.cost += (
                    self.state[index + 1] * buy_num_shares * self.buy_cost_pct[index]
                )
                self.trades += 1
            else:
                # Hold cash
                pass
        else:
            # If the price is not > 0, then we cannot buy
            pass

    def step(self, action):
        self.terminal = self.day >= len(self.df.index.unique()) - 1
        if self.terminal:
            return self.state, self.reward, self.terminal, False, {}

        else:
            # Convert the single action to a list of actions for each stock
            stock_actions = [action // 3, action % 3]

            begin_total_asset = self.state[0] + sum(
                np.array(self.state[1 : (self.stock_dim + 1)])
                * np.array(self.state[(self.stock_dim + 1) : (self.stock_dim * 2 + 1)])
            )

            # Perform actions for each stock
            for index, action in enumerate(stock_actions):
                self._sell_stock(index, action)
                self._buy_stock(index, action)

            # Update state
            self.day += 1
            self.data = self.df.loc[self.day, :]
            self.state = self._update_state()

            end_total_asset = self.state[0] + sum(
                np.array(self.state[1 : (self.stock_dim + 1)])
                * np.array(self.state[(self.stock_dim + 1) : (self.stock_dim * 2 + 1)])
            )
            self.reward = end_total_asset - begin_total_asset
            self.asset_memory.append(end_total_asset)

            self.reward = self.reward * self.reward_scaling

        return self.state, self.reward, self.terminal, False, {}


def main():
    # Download and preprocess the data
    df = YahooDownloader(
        start_date="2009-01-01",
        end_date="2021-01-01",
        ticker_list=["AAPL", "MSFT", "JPM"],
    ).fetch_data()

    fe = FeatureEngineer(
        use_technical_indicator=True,
        tech_indicator_list=config.INDICATORS,
        use_turbulence=False,
        user_defined_feature=False,
    )

    processed = fe.preprocess_data(df)

    # Split the data
    train = data_split(processed, "2009-01-01", "2020-01-01")
    trade = data_split(processed, "2020-01-01", "2021-01-01")

    # Set up the environment
    stock_dimension = len(train.tic.unique())
    state_space = 1 + 2 * stock_dimension + len(config.INDICATORS) * stock_dimension
    print(f"Stock Dimension: {stock_dimension}, State Space: {state_space}")

    env_kwargs = {
        "hmax": 100,
        "initial_amount": 1000000,
        "num_stock_shares": [0] * stock_dimension,
        "buy_cost_pct": [0.001] * stock_dimension,
        "sell_cost_pct": [0.001] * stock_dimension,
        "state_space": state_space,
        "stock_dim": stock_dimension,
        "tech_indicator_list": config.INDICATORS,
        "action_space": stock_dimension,
        "reward_scaling": 1e-4,
    }

    e_train_gym = ModifiedStockTradingEnv(df=train, **env_kwargs)
    env_train = DummyVecEnv([lambda: e_train_gym])

    # Set up the agent
    agent = DRLAgent(env=env_train)

    # Train the model
    model_ppo = agent.get_model("ppo")
    trained_ppo = agent.train_model(
        model=model_ppo, tb_log_name="ppo", total_timesteps=50000
    )

    # Trade using the trained model
    e_trade_gym = ModifiedStockTradingEnv(
        df=trade, turbulence_threshold=70, **env_kwargs
    )
    env_trade = DummyVecEnv([lambda: e_trade_gym])

    df_account_value, df_actions = DRLAgent.DRL_prediction(
        model=trained_ppo, environment=env_trade
    )

    print("Training and trading completed!")
    print(f"Final portfolio value: {df_account_value['account_value'].iloc[-1]:.2f}")


if __name__ == "__main__":
    main()
