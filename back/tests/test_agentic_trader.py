"""Tests for Agentic Trader (template-based trading)"""
import asyncio
import os
import sys
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from traders import AgenticTrader, AgenticAdvisor
from traders.agentic_trader import list_templates, get_template
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


@pytest.mark.asyncio
async def test_template_loading():
    """Test that templates load correctly."""
    print("Testing template loading...")
    
    templates = list_templates()
    assert len(templates) >= 6, f"Expected at least 6 templates, got {len(templates)}"
    
    template_ids = [t["id"] for t in templates]
    assert "buyer_20_default" in template_ids
    assert "seller_20_default" in template_ids
    assert "speculator_default" in template_ids
    
    print(f"✓ Loaded {len(templates)} templates")


@pytest.mark.asyncio
async def test_buyer_goal():
    """Test agentic trader with buying goal from template."""
    print("\nTesting buyer goal (template: buyer_20_default)...")
    
    params = {
        "agentic_prompt_template": "buyer_20_default",
        "initial_cash": 10000,
        "initial_shares": 0,
    }
    trader = AgenticTrader(id="AGENTIC_BUYER", params=params)
    await trader.initialize()

    assert trader.goal == 20
    assert trader.trader_type == TraderType.AGENTIC.value
    assert trader.is_buyer
    
    prompt = trader.build_system_prompt()
    assert "BUYING" in prompt or "Buy" in prompt
    
    print(f"✓ Buyer created with goal={trader.goal}")


@pytest.mark.asyncio
async def test_seller_goal():
    """Test agentic trader with selling goal from template."""
    print("\nTesting seller goal (template: seller_20_default)...")
    
    params = {
        "agentic_prompt_template": "seller_20_default",
        "initial_cash": 0,
        "initial_shares": 20,
    }
    trader = AgenticTrader(id="AGENTIC_SELLER", params=params)
    await trader.initialize()

    assert trader.goal == -20
    assert trader.is_seller
    
    prompt = trader.build_system_prompt()
    assert "SELLING" in prompt or "Sell" in prompt
    
    print(f"✓ Seller created with goal={trader.goal}")


@pytest.mark.asyncio
async def test_vwap_tracking():
    """Test VWAP calculation using platform's method."""
    print("\nTesting VWAP tracking...")
    
    params = {"agentic_prompt_template": "buyer_20_default", "initial_cash": 10000, "initial_shares": 0}
    trader = AgenticTrader(id="VWAP_TEST", params=params)
    await trader.initialize()
    
    # Simulate filled orders using base class method
    trader.update_filled_orders([
        {"trader_id": "VWAP_TEST", "id": "1", "type": "bid", "price": 100, "amount": 5},
        {"trader_id": "VWAP_TEST", "id": "2", "type": "bid", "price": 102, "amount": 5},
    ])
    
    vwap = trader.get_vwap()
    expected = 101.0
    
    assert abs(vwap - expected) < 0.01
    assert trader.goal_progress == 10
    
    print(f"✓ VWAP calculated: {vwap}")


@pytest.mark.asyncio
async def test_reward_calculation():
    """Test reward formula."""
    print("\nTesting reward calculation...")
    
    # Buyer - simulate 10 shares bought at VWAP 100
    params = {"agentic_prompt_template": "buyer_20_default"}
    trader = AgenticTrader(id="REWARD_BUY", params=params)
    await trader.initialize()
    
    # Simulate filled orders (complete goal of 20)
    trader.update_filled_orders([
        {"trader_id": "REWARD_BUY", "id": "1", "type": "bid", "price": 100, "amount": 20},
    ])
    
    # VWAP = 100, goal complete, buy_target = 110
    # reward = 110 - 100 = 10
    reward = trader.get_current_reward(mid_price=100)
    assert abs(reward - 10) < 0.01
    print(f"✓ Buyer reward: {reward}")
    
    # Seller - simulate 20 shares sold at VWAP 105
    params = {"agentic_prompt_template": "seller_20_default", "initial_shares": 30}
    trader = AgenticTrader(id="REWARD_SELL", params=params)
    await trader.initialize()
    
    # Simulate filled orders
    trader.update_filled_orders([
        {"trader_id": "REWARD_SELL", "id": "1", "type": "ask", "price": 105, "amount": 20},
    ])
    
    # VWAP = 105, goal complete, sell_target = 90
    # reward = 105 - 90 = 15
    reward = trader.get_current_reward(mid_price=100)
    assert abs(reward - 15) < 0.01
    print(f"✓ Seller reward: {reward}")


@pytest.mark.asyncio
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
        "agentic_prompt_template": "buyer_20_default",
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


@pytest.mark.asyncio
async def test_vwap_shown_in_market_state():
    """Test that VWAP is properly substituted in market state sent to LLM."""
    print("\nTesting VWAP shown in market state...")
    
    params = {"agentic_prompt_template": "buyer_20_default", "initial_cash": 10000, "initial_shares": 0}
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
    assert "VWAP: N/A" in market_state, f"Expected 'VWAP: N/A' before trades"
    print("✓ VWAP shows 'N/A' before any trades")
    
    # Test 2: After trades, VWAP should show actual value
    trader.update_filled_orders([
        {"trader_id": "VWAP_DISPLAY_TEST", "id": "1", "type": "bid", "price": 100, "amount": 3},
        {"trader_id": "VWAP_DISPLAY_TEST", "id": "2", "type": "bid", "price": 102, "amount": 2},
    ])
    
    actual_vwap = trader.get_vwap()
    expected_vwap = 101.0
    assert abs(actual_vwap - expected_vwap) < 0.01
    
    market_state = trader.build_market_state(mid_price)
    assert f"VWAP: {expected_vwap:.2f}" in market_state
    print(f"✓ VWAP shows '{expected_vwap:.2f}' after trades")


@pytest.mark.asyncio
async def test_prompt_from_template():
    """Test that prompts come from templates correctly."""
    print("\nTesting prompt from template...")
    
    # Test buyer template
    params = {"agentic_prompt_template": "buyer_20_aggressive"}
    trader = AgenticTrader(id="PROMPT_TEST_BUY", params=params)
    await trader.initialize()
    
    prompt = trader.build_system_prompt()
    assert "AGGRESSIVE" in prompt, "Aggressive keyword not in buyer prompt"
    assert trader.goal == 20
    assert trader.decision_interval == 3.0  # Aggressive has faster interval
    print("✓ Buyer aggressive template loaded correctly")
    
    # Test speculator template
    params = {"agentic_prompt_template": "speculator_default"}
    trader = AgenticTrader(id="PROMPT_TEST_SPEC", params=params)
    await trader.initialize()
    
    prompt = trader.build_system_prompt()
    assert "SPECULATOR" in prompt
    assert trader.goal == 0
    print("✓ Speculator template loaded correctly")
    
    # Test conservative template
    params = {"agentic_prompt_template": "buyer_50_conservative"}
    trader = AgenticTrader(id="PROMPT_TEST_CONS", params=params)
    await trader.initialize()
    
    assert trader.goal == 50
    assert trader.decision_interval == 8.0  # Conservative has slower interval
    print("✓ Conservative template loaded correctly")


@pytest.mark.asyncio
async def test_print_full_llm_prompt():
    """Print the full prompt sent to the LLM for inspection."""
    print("\n" + "=" * 70)
    print("FULL LLM PROMPT - BUYER (System + Market State)")
    print("=" * 70)
    
    # Create a buyer trader with realistic state
    params = {
        "agentic_prompt_template": "buyer_20_default",
        "initial_cash": 10000,
        "initial_shares": 0,
        "trading_day_duration": 5,
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
    
    print("✓ Buyer prompt printed successfully")


@pytest.mark.asyncio
async def test_print_speculator_prompt():
    """Print the full prompt sent to the LLM for a speculator."""
    print("\n" + "=" * 70)
    print("FULL LLM PROMPT - SPECULATOR (System + Market State)")
    print("=" * 70)
    
    # Create a speculator trader (goal=0)
    params = {
        "agentic_prompt_template": "speculator_default",
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
    
    assert "SPECULATOR" in system_prompt
    print("✓ Speculator prompt printed successfully")


@pytest.mark.asyncio
async def test_advisor_mode():
    """Test advisor class configuration."""
    print("\nTesting advisor class...")
    
    params = {
        "agentic_prompt_template": "buyer_20_default",
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


@pytest.mark.asyncio
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
        "agentic_prompt_template": "buyer_20_default",
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
        def get_current_pnl(self):
            return 0
    
    advisor.human_trader_ref = MockHuman()

    result = await advisor.make_decision()

    # In advisor mode, result should indicate advice was sent (not executed)
    assert result.get("result", {}).get("advisor_mode") == True
    assert advisor.current_advice is not None
    
    print(f"✓ Advisor decision: {result.get('action')} (advice stored, not executed)")


async def main():
    print("=" * 50)
    print("Agentic Trader Tests (Template-based)")
    print("=" * 50)

    load_env()

    try:
        await test_template_loading()
        await test_buyer_goal()
        await test_seller_goal()
        await test_vwap_tracking()
        await test_reward_calculation()
        await test_vwap_shown_in_market_state()
        await test_prompt_from_template()
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
