"""
Simple test to run an agentic trader with a noise trader.
No humans, no frontend - just see if the agent achieves its goal.
"""
import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_models import TradingParameters
from core.trader_manager import TraderManager


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


def print_order_book(market):
    """Print the current order book state."""
    book = market.orchestrator.order_book_manager.order_book
    bids = sorted(book.bids.items(), key=lambda x: -x[0])[:5]  # Top 5 bids
    asks = sorted(book.asks.items(), key=lambda x: x[0])[:5]   # Top 5 asks
    
    print("\n  ORDER BOOK:")
    print("  " + "-" * 40)
    print("  ASKS (sellers):")
    for price, orders in reversed(asks):
        total_qty = sum(o.amount if hasattr(o, 'amount') else o.get('amount', 0) for o in orders)
        print(f"    {price:6.0f} | {total_qty:3.0f} shares")
    print("  " + "-" * 20)
    print("  BIDS (buyers):")
    for price, orders in bids:
        total_qty = sum(o.amount if hasattr(o, 'amount') else o.get('amount', 0) for o in orders)
        print(f"    {price:6.0f} | {total_qty:3.0f} shares")
    print("  " + "-" * 40)


async def run_test():
    print("=" * 60)
    print("Agentic Trader Integration Test")
    print("=" * 60)
    
    # Config: 1 noise trader + 1 agentic trader (buyer)
    params = TradingParameters(
        # Market settings
        trading_day_duration=1.0,  # 1 minute (60 seconds)
        default_price=100,
        
        # Noise trader
        num_noise_traders=1,
        noise_activity_frequency=2.0,  # More active
        noise_passive_probability=0.5,
        noise_bid_probability=0.5,
        
        # Agentic trader
        num_agentic_traders=1,
        agentic_model="anthropic/claude-haiku-4.5",
        agentic_goals=[10],  # Buy 10 shares
        agentic_decision_interval=5.0,  # Decide every 5 seconds
        agentic_buy_target_price=110,
        agentic_sell_target_price=90,
        
        # No humans needed
        predefined_goals=[],
        
        # Book initialization
        start_of_book_num_order_per_level=3,
    )
    
    print(f"\nConfig:")
    print(f"  - Duration: {params.trading_day_duration} min (60s)")
    print(f"  - Noise traders: {params.num_noise_traders}")
    print(f"  - Agentic traders: {params.num_agentic_traders}")
    print(f"  - Agentic goal: BUY {params.agentic_goals[0]} shares")
    print(f"  - Decision interval: {params.agentic_decision_interval}s")
    print()
    
    # Create trader manager
    manager = TraderManager(params, market_id="TEST_AGENTIC")
    
    print("Starting market...")
    
    # Run the market
    try:
        # Launch in background
        task = asyncio.create_task(manager.launch())
        
        # Monitor progress
        agentic = manager.agentic_traders[0] if manager.agentic_traders else None
        
        if not agentic:
            print("ERROR: No agentic trader created!")
            return
        
        print(f"\nAgentic trader: {agentic.id}")
        print(f"Goal: BUY {agentic.goal} shares")
        print(f"Initial cash: {agentic.cash}, shares: {agentic.shares}")
        
        # Wait and monitor for full duration
        duration_seconds = 60
        check_interval = 5
        last_decision_count = 0
        
        for i in range(duration_seconds // check_interval + 2):
            await asyncio.sleep(check_interval)
            
            elapsed = (i + 1) * check_interval
            progress = agentic.goal_progress
            vwap = agentic.get_vwap()
            decisions = len(agentic.decision_log)
            cash = agentic.cash
            shares = agentic.shares
            
            print(f"\n{'='*60}")
            print(f"[{elapsed:3d}s] Progress: {progress}/{agentic.goal} | VWAP: {vwap:.2f} | Cash: {cash:.0f} | Shares: {shares}")
            
            # Print order book
            print_order_book(manager.trading_market)
            
            # Print new LLM decisions
            if decisions > last_decision_count:
                for j in range(last_decision_count, decisions):
                    d = agentic.decision_log[j]
                    print(f"\n  LLM DECISION #{j+1}:")
                    print(f"    Action: {d['action']}")
                    print(f"    Args: {d.get('args', {})}")
                    print(f"    Result: {d.get('result', {})}")
                    print(f"    Goal progress: {d.get('goal_progress', 0)}")
                    print(f"    Current VWAP: {d.get('current_vwap', 0):.2f}")
                    print(f"    Current reward: {d.get('current_reward', 0):.2f}")
                last_decision_count = decisions
            
            # Check if market ended
            if not manager.trading_market.trading_started:
                print("\n⏱ Market ended!")
                break
        
        # Final summary
        print("\n" + "=" * 60)
        print("FINAL RESULTS")
        print("=" * 60)
        summary = agentic.get_performance_summary()
        for k, v in summary.items():
            print(f"  {k}: {v}")
        
        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await manager.cleanup()


if __name__ == "__main__":
    load_env()
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set in environment")
        sys.exit(1)
    
    print(f"API Key: {api_key[:10]}...")
    asyncio.run(run_test())
