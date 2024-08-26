import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from traders import InformedTrader
from structures import TraderType, OrderType, TradeDirection

@pytest.fixture
def informed_trader_settings():
    informed_state = {"inv": 1} 

    return {
        "id": "1",
        "noise_activity_frequency": 10,
        "default_price": 100,
        "informed_edge": 1,
        "settings": {
            "initial_price": 100,
            "n_updates_session": 10,
            "warmup_periods": 2,
        },
        "settings_informed": {
            "inv": 1,
            "direction": TradeDirection.SELL,
            "total_seconds": 300
        }, 
        "informed_time_plan": {"period": [10, 20, 30]},
        "informed_state": informed_state,
        "get_signal_informed": MagicMock(return_value=[1, 100]),  
        "get_order_to_match": MagicMock(return_value={"bid": {100: [1]}, "ask": {}}),
    }

@pytest.fixture
def informed_trader(informed_trader_settings):
    return InformedTrader(**informed_trader_settings)

def test_initialization(informed_trader):
    assert informed_trader.noise_activity_frequency == 10
    assert informed_trader.default_price == 100
    assert informed_trader.informed_edge == 1
    assert informed_trader.settings["initial_price"] == 100
    assert informed_trader.trader_type == TraderType.INFORMED
    assert informed_trader.informed_state == {"inv": 1}
    assert informed_trader.settings_informed["direction"] == TradeDirection.SELL
    assert informed_trader.shares == 1
    assert informed_trader.cash == 0

@pytest.mark.asyncio
async def test_act_generates_orders(informed_trader):
    informed_trader.post_new_order = AsyncMock()
    informed_trader.get_remaining_time = MagicMock(return_value=100)
    informed_trader.get_best_price = MagicMock(side_effect=[99, 101])  # top_bid, top_ask
    await informed_trader.act()
    informed_trader.post_new_order.assert_awaited_once_with(1, 100, OrderType.ASK)

@pytest.mark.asyncio
async def test_act_no_order_placed(informed_trader):
    informed_trader.post_new_order = AsyncMock()
    informed_trader.get_remaining_time = MagicMock(return_value=100)
    informed_trader.get_best_price = MagicMock(side_effect=[99, 102])  # top_bid, top_ask
    await informed_trader.act()
    informed_trader.post_new_order.assert_not_awaited()

def test_get_best_price(informed_trader):
    informed_trader.order_book = {
        "bids": [{"x": 98}, {"x": 99}],
        "asks": [{"x": 101}, {"x": 102}]
    }
    assert informed_trader.get_best_price(OrderType.BID) == 99
    assert informed_trader.get_best_price(OrderType.ASK) == 101

    # Test when order book is empty
    informed_trader.order_book = {"bids": [], "asks": []}
    assert informed_trader.get_best_price(OrderType.BID) == 100  # default_price
    assert informed_trader.get_best_price(OrderType.ASK) == float("inf")

def test_calculate_sleep_time(informed_trader):
    informed_trader.settings_informed["direction"] = TradeDirection.BUY
    informed_trader.shares = 0
    assert informed_trader.calculate_sleep_time(100) == 95

    informed_trader.settings_informed["direction"] = TradeDirection.SELL
    informed_trader.shares = 1
    assert informed_trader.calculate_sleep_time(100) == 100