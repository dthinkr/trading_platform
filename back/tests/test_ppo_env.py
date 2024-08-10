import unittest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import asyncio
import numpy as np
import gym
from traders.ppo_env import TradingEnvironment
from main_platform.trading_platform import TradingSession
from structures import OrderType, OrderStatus, Order

class TestTradingEnvironment(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.trading_session = TradingSession(
            duration=60,
            default_price=100,
            default_spread=10,
            punishing_constant=1
        )
        self.trading_session.order_book = MagicMock()
        self.trading_session.send_broadcast = AsyncMock()
        self.trading_session.create_transaction = AsyncMock()
        self.trading_session.place_order = MagicMock()
        self.trading_session.get_order_book_snapshot = MagicMock(return_value={
            'bids': [{'price': 100, 'amount': 10}] * 5,
            'asks': [{'price': 101, 'amount': 10}] * 5
        })
        self.trading_session.get_transaction_history = MagicMock(return_value=[
            {'price': 100, 'amount': 1},
            {'price': 101, 'amount': 1}
        ])
        
        # Mock the transaction_price property
        type(self.trading_session).transaction_price = PropertyMock(return_value=100.5)
        
        # Mock the mid_price property
        type(self.trading_session).mid_price = PropertyMock(return_value=100.5)
        
        self.trading_session.cash = 10000
        self.trading_session.shares = 100
        self.trading_session.get_elapsed_time = MagicMock(return_value=1800)
        self.trading_session.order_book.get_spread = MagicMock(return_value=(1, 100.5))
        self.trading_session.average_entry_price = 100

        # Mock the reset method
        self.trading_session.reset = MagicMock()

        self.env = TradingEnvironment(self.trading_session)

    async def test_initialization(self):
        self.assertIsInstance(self.env.observation_space, gym.spaces.Dict)
        self.assertIsInstance(self.env.action_space, gym.spaces.Discrete)
        self.assertEqual(self.env.action_space.n, 3)

    async def test_get_observation(self):
        obs = self.env._get_observation()
        self.assertIsInstance(obs, dict)
        self.assertEqual(set(obs.keys()), {'order_book', 'transactions', 'market_stats', 'trader_state', 'time'})
        
        np.testing.assert_array_equal(obs['order_book']['best_bid'], [100, 10])
        np.testing.assert_array_equal(obs['order_book']['best_ask'], [101, 10])
        self.assertEqual(obs['order_book']['depth'].shape, (10, 2))
        np.testing.assert_array_equal(obs['transactions']['last_price'], [100.5])
        np.testing.assert_array_equal(obs['market_stats']['mid_price'], [100.5])
        np.testing.assert_array_equal(obs['market_stats']['spread'], [1])
        np.testing.assert_array_equal(obs['trader_state']['cash'], [10000])
        np.testing.assert_array_equal(obs['trader_state']['shares'], [100])
        np.testing.assert_array_equal(obs['time']['elapsed'], [1800])

    async def test_step(self):
        # Set up initial conditions
        self.env.previous_portfolio_value = 20000
        self.trading_session.cash = 10000
        self.trading_session.shares = 100
        type(self.trading_session).mid_price = PropertyMock(return_value=100.5)

        print(f"Initial conditions:")
        print(f"Previous portfolio value: {self.env.previous_portfolio_value}")
        print(f"Cash: {self.trading_session.cash}")
        print(f"Shares: {self.trading_session.shares}")
        print(f"Initial mid_price: {self.trading_session.mid_price}")

        # Perform the step
        obs, reward, done, _ = self.env.step(1)  # Buy action

        print(f"\nAfter step:")
        print(f"Cash: {self.trading_session.cash}")
        print(f"Shares: {self.trading_session.shares}")
        print(f"Mid_price after step: {self.trading_session.mid_price}")

        # Check basic return types
        self.assertIsInstance(obs, dict)
        self.assertIsInstance(reward, float)
        self.assertIsInstance(done, bool)

        # Verify the order placement
        self.trading_session.place_order.assert_called_once_with({
            'trader_id': 'rl_agent',
            'order_type': OrderType.BID,
            'amount': 1,
            'price': 100.5,
        })

        # Calculate and check each component of the reward
        portfolio_value_change = (self.trading_session.cash + self.trading_session.shares * self.trading_session.mid_price) - self.env.previous_portfolio_value
        transaction_cost = 0.001 * 100.5
        holding_penalty = 0.0001 * self.trading_session.shares * self.trading_session.mid_price
        inventory_penalty = 0  # Assuming no inventory penalty in this case

        print(f"\nReward components:")
        print(f"Portfolio value change: {portfolio_value_change}")
        print(f"Transaction cost: {transaction_cost}")
        print(f"Holding penalty: {holding_penalty}")
        print(f"Inventory penalty: {inventory_penalty}")

        expected_reward = portfolio_value_change - transaction_cost - holding_penalty - inventory_penalty
        print(f"Expected reward: {expected_reward}")
        print(f"Actual reward: {reward}")

        # Compare with the actual reward
        self.assertAlmostEqual(reward, expected_reward, places=4)

        # If the assertion fails, print out the components for debugging
        if abs(reward - expected_reward) > 1e-4:
            print("\nReward calculation mismatch:")
            print(f"Difference: {abs(reward - expected_reward)}")
            
        # Additional checks
        self.assertAlmostEqual(portfolio_value_change, 150.5, places=4)
        self.assertAlmostEqual(transaction_cost, 0.1005, places=4)
        self.assertAlmostEqual(holding_penalty, 1.01505, places=4)
        self.assertAlmostEqual(expected_reward, 149.38445, places=4)

        print("\nObservation:")
        print(obs)
        
    async def test_reset(self):
        obs = self.env.reset()  # Remove await
        self.assertIsInstance(obs, dict)
        self.trading_session.reset.assert_called_once()
        self.assertEqual(self.env.previous_portfolio_value, 10000 + 100 * 100.5)
        self.assertEqual(self.env.last_action_shares, 0)


    def test_calculate_vwap(self):
        transactions = [
            {'price': 100, 'amount': 1},
            {'price': 101, 'amount': 2},
            {'price': 102, 'amount': 3}
        ]
        vwap = self.env._calculate_vwap(transactions)
        self.assertAlmostEqual(vwap, 101.3333, places=4)

    def test_calculate_imbalance(self):
        order_book = {
            'bids': [{'amount': 10}] * 5,
            'asks': [{'amount': 5}] * 5
        }
        imbalance = self.env._calculate_imbalance(order_book)
        self.assertAlmostEqual(imbalance, 0.3333, places=4)

    def test_calculate_unrealized_pnl(self):
        unrealized_pnl = self.env._calculate_unrealized_pnl()
        self.assertAlmostEqual(unrealized_pnl, 50, places=4)  # (100.5 - 100) * 100

    def test_calculate_portfolio_value_change(self):
        self.env.previous_portfolio_value = 20000
        value_change = self.env._calculate_portfolio_value_change()
        expected_change = (10000 + 100 * 100.5) - 20000
        self.assertAlmostEqual(value_change, expected_change, places=4)

if __name__ == '__main__':
    unittest.main()