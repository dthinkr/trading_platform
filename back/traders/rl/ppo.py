import pandas as pd
import numpy as np
import gym
from gym import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from finrl.meta.preprocessor.yahoodownloader import YahooDownloader
from finrl.meta.preprocessor.preprocessors import FeatureEngineer


class SimpleStockTradingEnv(gym.Env):
    def __init__(self, df):
        super(SimpleStockTradingEnv, self).__init__()
        self.df = df
        self.current_step = 0
        self.stock_owned = 0
        self.cash_balance = 10000
        self.total_steps = len(df)

        self.action_space = spaces.Discrete(3)  # 0: hold, 1: buy, 2: sell
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(5,), dtype=np.float32
        )

    def reset(self):
        self.current_step = 0
        self.stock_owned = 0
        self.cash_balance = 10000
        return self._next_observation(), {}  # Return observation and empty info dict

    def _next_observation(self):
        obs = np.array(
            [
                self.df.loc[self.current_step, "open"],
                self.df.loc[self.current_step, "high"],
                self.df.loc[self.current_step, "low"],
                self.df.loc[self.current_step, "close"],
                self.stock_owned,
            ],
            dtype=np.float32,
        )
        return obs

    def step(self, action):
        current_price = self.df.loc[self.current_step, "close"]

        if action == 1:  # Buy
            shares_bought = self.cash_balance // current_price
            self.stock_owned += shares_bought
            self.cash_balance -= shares_bought * current_price
        elif action == 2:  # Sell
            self.cash_balance += self.stock_owned * current_price
            self.stock_owned = 0

        self.current_step += 1
        done = self.current_step >= self.total_steps - 1
        obs = self._next_observation()

        account_value = self.cash_balance + self.stock_owned * current_price
        reward = account_value - 10000  # Reward is the profit/loss

        return (
            obs,
            reward,
            done,
            False,
            {},
        )  # Return 5 values for compatibility with newer Gym versions

    def render(self, mode="human"):
        # Implement render method if needed
        pass


def main():
    # Download and preprocess data
    df = YahooDownloader(
        start_date="2010-01-01", end_date="2021-12-31", ticker_list=["AAPL"]
    ).fetch_data()

    fe = FeatureEngineer(
        use_technical_indicator=True,
        tech_indicator_list=["macd", "rsi_30", "cci_30", "dx_30"],
        use_turbulence=False,
        user_defined_feature=False,
    )

    processed = fe.preprocess_data(df)

    # Set up environment
    env = DummyVecEnv([lambda: SimpleStockTradingEnv(processed)])

    # Set up model
    model = PPO("MlpPolicy", env, verbose=1)

    # Train model
    model.learn(total_timesteps=10000)

    # Test model
    obs = env.reset()
    for i in range(len(processed)):
        action, _states = model.predict(obs)
        obs, rewards, dones, infos = env.step(action)
        if dones:
            break

    print("Training completed!")


if __name__ == "__main__":
    main()
