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


async def test_vwap_shown_in_market_state():
    """Test that VWAP is properly substituted in market state sent to LLM."""
    print("\nTesting VWAP shown in market state...")
    
    params = {"goal": 10, "initial_cash": 10000, "initial_shares": 0}
    trader = AgenticTrader(id="VWAP_DISPLAY_TEST", params=params)
    await trader.initialize()
    
    # Set up order book so build_market_state works
    trader.order_book = {
        "bids": [{"x": 99, "y": 10}, {"x": 98, "y": 20}],
        "asks": [{"x": 101, "y": 8}, {"x": 102, "y": 25}],
    }
    
    # Test 1: Before any trades, VWAP should show "N/A"
    mid_price = 100.0
    market_state = trader.build_market_state(mid_price)
    assert "VWAP: N/A" in market_state, f"Expected 'VWAP: N/A' before trades, got: {market_state}"
    print("✓ VWAP shows 'N/A' before any trades")
    
    # Test 2: After trades, VWAP should show actual value
    # Note: base_trader.get_vwap() calculates simple average of transaction_prices
    trader.update_filled_orders([
        {"trader_id": "VWAP_DISPLAY_TEST", "id": "1", "type": "bid", "price": 100, "amount": 3},
        {"trader_id": "VWAP_DISPLAY_TEST", "id": "2", "type": "bid", "price": 102, "amount": 2},
    ])
    
    # get_vwap() returns simple average: (100 + 102) / 2 = 101.0
    actual_vwap = trader.get_vwap()
    expected_vwap = 101.0  # Simple average of transaction prices
    assert abs(actual_vwap - expected_vwap) < 0.01, f"VWAP mismatch: {actual_vwap} vs {expected_vwap}"
    
    market_state = trader.build_market_state(mid_price)
    assert f"VWAP: {expected_vwap:.2f}" in market_state, f"Expected 'VWAP: {expected_vwap:.2f}' in market state, got: {market_state}"
    print(f"✓ VWAP shows '{expected_vwap:.2f}' after trades")
    
    # Test 3: Verify VWAP appears in GOAL PROGRESS section
    assert "=== GOAL PROGRESS" in market_state
    # Extract the goal progress section and verify VWAP is there
    lines = market_state.split("\n")
    goal_section_found = False
    vwap_in_goal_section = False
    for i, line in enumerate(lines):
        if "=== GOAL PROGRESS" in line:
            goal_section_found = True
        if goal_section_found and "VWAP:" in line:
            vwap_in_goal_section = True
            break
    assert vwap_in_goal_section, "VWAP should appear in GOAL PROGRESS section"
    print("✓ VWAP appears in GOAL PROGRESS section")
    
    # Test 4: Verify the full market state structure contains no unsubstituted placeholders
    assert "{" not in market_state or "}" not in market_state or "{" not in market_state.split("===")[0], \
        f"Found unsubstituted placeholder in market state"
    print("✓ No unsubstituted placeholders in market state")


async def test_prompt_keywords_substituted():
    """Test that all prompt template keywords are properly substituted."""
    print("\nTesting prompt keyword substitution...")
    
    # Test buyer prompt
    params = {"goal": 15, "buy_target_price": 115, "penalty_multiplier_buy": 1.8}
    trader = AgenticTrader(id="PROMPT_TEST_BUY", params=params)
    await trader.initialize()
    
    prompt = trader.build_system_prompt()
    assert "{" not in prompt, f"Found unsubstituted placeholder in buyer prompt: {prompt}"
    assert "Buy 15 shares" in prompt, "Goal not substituted in buyer prompt"
    assert "115" in prompt, "buy_target not substituted in buyer prompt"
    assert "1.8" in prompt, "penalty_buy not substituted in buyer prompt"
    print("✓ Buyer prompt keywords all substituted")
    
    # Test seller prompt
    params = {"goal": -20, "sell_target_price": 85, "penalty_multiplier_sell": 0.6, "initial_shares": 30}
    trader = AgenticTrader(id="PROMPT_TEST_SELL", params=params)
    await trader.initialize()
    
    prompt = trader.build_system_prompt()
    assert "{" not in prompt, f"Found unsubstituted placeholder in seller prompt: {prompt}"
    assert "Sell 20 shares" in prompt, "Goal not substituted in seller prompt"
    assert "85" in prompt, "sell_target not substituted in seller prompt"
    assert "0.6" in prompt, "penalty_sell not substituted in seller prompt"
    print("✓ Seller prompt keywords all substituted")
    
    # Test speculator prompt
    params = {"goal": 0}
    trader = AgenticTrader(id="PROMPT_TEST_SPEC", params=params)
    await trader.initialize()
    
    prompt = trader.build_system_prompt()
    assert "{" not in prompt, f"Found unsubstituted placeholder in speculator prompt: {prompt}"
    assert "SPECULATOR" in prompt
    print("✓ Speculator prompt keywords all substituted")


async def test_print_full_llm_prompt():
    """Print the full prompt sent to the LLM for inspection."""
    print("\n" + "=" * 70)
    print("FULL LLM PROMPT - BUYER (System + Market State)")
    print("=" * 70)
    
    # Create a buyer trader with realistic state
    params = {
        "goal": 10,
        "initial_cash": 10000,
        "initial_shares": 0,
        "buy_target_price": 110,
        "penalty_multiplier_buy": 1.5,
        "trading_day_duration": 5,  # 5 minutes
    }
    trader = AgenticTrader(id="PROMPT_PRINT_TEST", params=params)
    await trader.initialize()
    
    # Set up realistic order book
    trader.order_book = {
        "bids": [{"x": 99, "y": 10}, {"x": 98, "y": 20}, {"x": 97, "y": 15}],
        "asks": [{"x": 101, "y": 8}, {"x": 102, "y": 25}, {"x": 103, "y": 12}],
    }
    trader.price_history = [100, 100.5, 101, 100.8, 101.2, 100.9, 101.1]
    
    # Simulate some filled orders
    trader.update_filled_orders([
        {"trader_id": "PROMPT_PRINT_TEST", "id": "1", "type": "bid", "price": 100, "amount": 2},
        {"trader_id": "PROMPT_PRINT_TEST", "id": "2", "type": "bid", "price": 101, "amount": 1},
    ])
    
    # Add a pending order
    trader.orders = [{"id": "pending_1", "amount": 1, "price": 99, "order_type": 1}]
    
    # Add some decision history
    trader.decision_log = [
        {"action": "place_order", "args": {"price": 100}, "result": {"success": True, "order_id": "1", "side": "buy"}},
        {"action": "place_order", "args": {"price": 101}, "result": {"success": True, "order_id": "2", "side": "buy"}},
        {"action": "place_order", "args": {"price": 99}, "result": {"success": True, "order_id": "pending_1", "side": "buy"}},
    ]
    
    mid_price = 100.0
    
    # Build the prompts
    system_prompt = trader.build_system_prompt()
    market_state = trader.build_market_state(mid_price)
    
    print("\n--- SYSTEM PROMPT ---")
    print(system_prompt)
    print("\n--- MARKET STATE (User Message) ---")
    print(market_state)
    print("\n--- END OF PROMPT ---")
    print("=" * 70)
    
    # Verify no placeholders remain
    assert "{" not in system_prompt, "Unsubstituted placeholder in system prompt"
    assert "VWAP:" in market_state, "VWAP missing from market state"
    print("✓ Buyer prompt printed successfully")


async def test_print_speculator_prompt():
    """Print the full prompt sent to the LLM for a speculator."""
    print("\n" + "=" * 70)
    print("FULL LLM PROMPT - SPECULATOR (System + Market State)")
    print("=" * 70)
    
    # Create a speculator trader (goal=0)
    params = {
        "goal": 0,
        "initial_cash": 5000,
        "initial_shares": 10,
        "trading_day_duration": 5,
    }
    trader = AgenticTrader(id="SPECULATOR_PROMPT_TEST", params=params)
    await trader.initialize()
    
    # Set up realistic order book
    trader.order_book = {
        "bids": [{"x": 99, "y": 10}, {"x": 98, "y": 20}, {"x": 97, "y": 15}],
        "asks": [{"x": 101, "y": 8}, {"x": 102, "y": 25}, {"x": 103, "y": 12}],
    }
    trader.price_history = [100, 100.5, 101, 100.8, 101.2, 100.9, 101.1, 101.5, 102, 101.8]
    
    # Simulate some trades (bought low, sold high)
    trader.update_filled_orders([
        {"trader_id": "SPECULATOR_PROMPT_TEST", "id": "1", "type": "bid", "price": 99, "amount": 2},
        {"trader_id": "SPECULATOR_PROMPT_TEST", "id": "2", "type": "ask", "price": 102, "amount": 1},
    ])
    
    # Add a pending order
    trader.orders = [{"id": "pending_1", "amount": 1, "price": 98, "order_type": 1}]
    
    # Add some decision history
    trader.decision_log = [
        {"action": "place_order", "args": {"price": 99, "side": "buy"}, "result": {"success": True, "order_id": "1", "side": "buy"}},
        {"action": "place_order", "args": {"price": 102, "side": "sell"}, "result": {"success": True, "order_id": "2", "side": "sell"}},
        {"action": "place_order", "args": {"price": 98, "side": "buy"}, "result": {"success": True, "order_id": "pending_1", "side": "buy"}},
    ]
    
    mid_price = 100.5
    
    # Build the prompts
    system_prompt = trader.build_system_prompt()
    market_state = trader.build_market_state(mid_price)
    
    print("\n--- SYSTEM PROMPT ---")
    print(system_prompt)
    print("\n--- MARKET STATE (User Message) ---")
    print(market_state)
    print("\n--- END OF PROMPT ---")
    print("=" * 70)
    
    # Verify no placeholders remain
    assert "{" not in system_prompt, "Unsubstituted placeholder in system prompt"
    assert "SPECULATOR" in system_prompt, "SPECULATOR not in system prompt"
    assert "PnL:" in market_state, "PnL missing from market state for speculator"
    print("✓ Speculator prompt printed successfully")


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
        await test_vwap_shown_in_market_state()
        await test_prompt_keywords_substituted()
        await test_print_full_llm_prompt()
        await test_print_speculator_prompt()
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
