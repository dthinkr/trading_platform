import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from traders import InformedTrader
from structures import TraderType, OrderType

@pytest.fixture
def informed_trader_settings():
    informed_state = {"inv": 1} 

    return {
        "activity_frequency": 10,
        "settings": {
            "initial_price": 100,
            "n_updates_session": 10,
            "warmup_periods": 2,
        },
        "settings_informed": {"inv": 1, "direction": "sell"}, 
        "informed_time_plan": {"period": [10, 20, 30]},
        "informed_state": informed_state,
        "get_signal_informed": MagicMock(return_value=[1, 100]),  
        "get_order_to_match": MagicMock(return_value={"bid": {100: [1]}, "ask": {}}),
    }

@pytest.fixture
def informed_trader(informed_trader_settings):
    return InformedTrader(**informed_trader_settings)

def test_initialization(informed_trader):
    assert informed_trader.activity_frequency == 10
    assert informed_trader.settings["initial_price"] == 100
    assert informed_trader.trader_type == TraderType.INFORMED
    assert informed_trader.informed_state == {"inv": 1}
    assert informed_trader.settings_informed["direction"] == "sell"

@pytest.mark.asyncio
async def test_act_generates_orders(informed_trader):
    informed_trader.post_new_order = AsyncMock()
    await informed_trader.act()
    informed_trader.post_new_order.assert_awaited_with(1, 100, OrderType.ASK)