import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from traders import InformedTrader
from structures import TraderType, OrderType

@pytest.fixture
def informed_trader_settings():
    # Assuming get_informed_state is a function that initializes the informed_state
    # For testing, you can mock it or provide a fixed dictionary
    informed_state = {"inv": 1}  # Example initial state

    return {
        "activity_frequency": 10,
        "settings": {
            "initial_price": 100,
            "n_updates_session": 10,
            "warmup_periods": 2,
        },
        "settings_informed": {"inv": 1, "direction": "sell"},  # Added 'direction' for completeness
        "informed_time_plan": {"period": [10, 20, 30]},  # Example time plan
        "informed_state": informed_state,
        "get_signal_informed": MagicMock(return_value=[1, 100]),  # Mock as before
        # Assuming get_order_to_match should return a realistic order dict based on the signal
        # For a sell signal, it might return a bid order to be matched with an ask
        "get_order_to_match": MagicMock(return_value={"bid": {100: [1]}, "ask": {}}),
    }

@pytest.fixture
def informed_trader(informed_trader_settings):
    return InformedTrader(**informed_trader_settings)

def test_initialization(informed_trader):
    assert informed_trader.activity_frequency == 10
    assert informed_trader.settings["initial_price"] == 100
    assert informed_trader.trader_type == TraderType.INFORMED
    # Test the initialization of informed_state and settings_informed
    assert informed_trader.informed_state == {"inv": 1}
    assert informed_trader.settings_informed["direction"] == "sell"

@pytest.mark.asyncio
async def test_act_generates_orders(informed_trader):
    informed_trader.post_new_order = AsyncMock()
    await informed_trader.act()
    # Verify post_new_order was called with the correct parameters
    # Since the mock get_order_to_match returns a bid order, we expect an ask order to be posted
    informed_trader.post_new_order.assert_awaited_with(1, 100, OrderType.ASK)