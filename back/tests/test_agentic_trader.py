"""Tests for Agentic Trader (goal-based VWAP optimization)"""
import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from traders import AgenticTrader, AgenticAdvisor
from core.data_models import TraderType


def load_env():
    from pathlib import Path
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k] = v


async def test_buyer_goal():
    """Test agentic trader with buying goal."""
    print("Testing buyer goal (goal=20)...")
    
    params = {
        "goal": 20,
        "initial_cash": 10000,
        "initial_shares": 0,
        "buy_target_price": 110,
    }
    trader = AgenticTrader(id="AGENTIC_BUYER", params=params)
    await trader.initialize()

    assert trader.goal == 20
    assert trader.trader_type == TraderType.AGENTIC.value
    
    prompt = trader.build_system_prompt()
    assert "BUYING" in prompt
    assert "Buy 20 shares" in prompt
    
    print(f"✓ Buyer created with goal={trader.goal}")


async def test_seller_goal():
    """Test agentic trader with selling goal."""
    print("\nTesting seller goal (goal=-15)...")
    
    params = {
        "goal": -15,
        "initial_cash": 0,
        "initial_shares": 20,
        "sell_target_price": 90,
    }
    trader = AgenticTrader(id="AGENTIC_SELLER", params=params)
    await trader.initialize()

    assert trader.goal == -15
    
    prompt = trader.build_system_prompt()
    assert "SELLING" in prompt
    assert "Sell 15 shares" in prompt
    
    print(f"✓ Seller created with goal={trader.goal}")


async def test_vwap_tracking():
    """Test VWAP calculation using platform's method."""
    print("\nTesting VWAP tracking...")
    
    params = {"goal": 10, "initial_cash": 10000, "initial_shares": 0}
    trader = AgenticTrader(id="VWAP_TEST", params=params)
    await trader.initialize()
    
    # Simulate filled orders using base class method
    # update_filled_orders calls update_data_for_pnl which populates transaction_prices
    trader.update_filled_orders([
        {"trader_id": "VWAP_TEST", "id": "1", "type": "bid", "price": 100, "amount": 5},
        {"trader_id": "VWAP_TEST", "id": "2", "type": "bid", "price": 102, "amount": 5},
    ])
    
    vwap = trader.get_vwap()  # Platform's VWAP
    expected = 101.0
    
    assert abs(vwap - expected) < 0.01
    assert trader.goal_progress == 10
    
    print(f"✓ VWAP calculated: {vwap}")


async def test_reward_calculation():
    """Test reward formula."""
    print("\nTesting reward calculation...")
    
    # Buyer - simulate 10 shares bought at VWAP 100
    params = {"goal": 10, "buy_target_price": 110}
    trader = AgenticTrader(id="REWARD_BUY", params=params)
    await trader.initialize()
    
    # Simulate filled orders
    trader.update_filled_orders([
        {"trader_id": "REWARD_BUY", "id": "1", "type": "bid", "price": 100, "amount": 10},
    ])
    
    # VWAP = 100, goal complete
    # pnl = (110 - 100) * 10 = 100
    # reward = max(0, 100 / 10) = 10
    reward = trader.get_current_reward(mid_price=100)
    assert abs(reward - 10) < 0.01
    print(f"✓ Buyer reward: {reward}")
    
    # Seller - simulate 10 shares sold at VWAP 105
    params = {"goal": -10, "sell_target_price": 90, "initial_shares": 20}
    trader = AgenticTrader(id="REWARD_SELL", params=params)
    await trader.initialize()
    
    # Simulate filled orders
    trader.update_filled_orders([
        {"trader_id": "REWARD_SELL", "id": "1", "type": "ask", "price": 105, "amount": 10},
    ])
    
    # VWAP = 105, goal complete
    # pnl = (105 - 90) * 10 = 150
    # reward = max(0, 150 / 10) = 15
    reward = trader.get_current_reward(mid_price=100)
    assert abs(reward - 15) < 0.01
    print(f"✓ Seller reward: {reward}")


async def test_decision_with_api():
    """Test actual decision (requires API key)."""
    print("\nTesting decision with API...")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("⚠ Skipping - no API key")
        return

    params = {
        "openrouter_api_key": api_key,
        "agentic_model": "anthropic/claude-haiku-4.5",
        "goal": 10,
        "initial_cash": 10000,
        "initial_shares": 0,
    }

    trader = AgenticTrader(id="API_TEST", params=params)
    await trader.initialize()

    trader.order_book = {
        "bids": [{"x": 99, "y": 10}, {"x": 98, "y": 20}],
        "asks": [{"x": 101, "y": 8}, {"x": 102, "y": 25}],
    }
    trader.price_history = [100, 100.5, 101, 100.8, 101.2]

    result = await trader.make_decision()

    print(f"✓ Decision: {result.get('action')} {result.get('args', {})}")


async def test_advisor_mode():
    """Test advisor class configuration."""
    print("\nTesting advisor class...")
    
    params = {
        "advice_for_human_id": "HUMAN_testuser",
    }
    advisor = AgenticAdvisor(id="ADVISOR_1", params=params)
    await advisor.initialize()

    assert advisor.advice_for_human_id == "HUMAN_testuser"
    assert advisor.current_advice is None
    assert advisor.human_trader_ref is None
    
    summary = advisor.get_performance_summary()
    assert summary["advisor_for"] == "HUMAN_testuser"
    assert summary["human_linked"] == False
    
    print(f"✓ Advisor configured for {advisor.advice_for_human_id}")


async def test_advisor_decision():
    """Test advisor decision (doesn't execute, just stores advice)."""
    print("\nTesting advisor decision...")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("⚠ Skipping - no API key")
        return

    params = {
        "openrouter_api_key": api_key,
        "agentic_model": "anthropic/claude-haiku-4.5",
        "advice_for_human_id": "HUMAN_testuser",
    }

    advisor = AgenticAdvisor(id="ADVISOR_TEST", params=params)
    await advisor.initialize()

    advisor.order_book = {
        "bids": [{"x": 99, "y": 10}, {"x": 98, "y": 20}],
        "asks": [{"x": 101, "y": 8}, {"x": 102, "y": 25}],
    }
    advisor.price_history = [100, 100.5, 101, 100.8, 101.2]
    
    # Mock a human trader ref with a goal
    class MockHuman:
        goal = 10
        goal_progress = 3
        cash = 5000
        shares = 5
        orders = []
        def get_vwap(self):
            return 100.5
    
    advisor.human_trader_ref = MockHuman()

    result = await advisor.make_decision()

    # In advisor mode, result should indicate advice was sent (not executed)
    assert result.get("result", {}).get("advisor_mode") == True
    assert advisor.current_advice is not None
    
    print(f"✓ Advisor decision: {result.get('action')} (advice stored, not executed)")


async def main():
    print("=" * 50)
    print("Agentic Trader Tests")
    print("=" * 50)

    load_env()

    try:
        await test_buyer_goal()
        await test_seller_goal()
        await test_vwap_tracking()
        await test_reward_calculation()
        await test_advisor_mode()
        await test_decision_with_api()
        await test_advisor_decision()

        print("\n" + "=" * 50)
        print("✓ All tests passed!")
        print("=" * 50)
    except Exception as e:
        print(f"\n✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
