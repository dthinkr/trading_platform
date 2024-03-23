import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from traders import InformedTrader
from structures import TraderType


@pytest.fixture
def informed_trader_settings():
    return {
        "activity_frequency": 10,
        "settings": {
            "initial_price": 100,
            "n_updates_session": 10,
            "warmup_periods": 2,
        },
        "settings_informed": {"inv": 1},
        "informed_state": {},
        "trading_day_duration": 8,
        "get_informed_time_plan": MagicMock(return_value=[]),
        "get_signal_informed": MagicMock(return_value=[1, 100]),
        "get_informed_order": MagicMock(return_value={}),
    }


@pytest.fixture
def informed_trader(informed_trader_settings):
    return InformedTrader(**informed_trader_settings)


def test_initialization(informed_trader):
    assert informed_trader.activity_frequency == 10
    assert informed_trader.settings["initial_price"] == 100
    assert informed_trader.trader_type == TraderType.INFORMED


def test_get_best_bid_and_ask(informed_trader):
    informed_trader.active_orders = [
        {"order_type": "bid", "price": 101},
        {"order_type": "ask", "price": 105},
        {"order_type": "bid", "price": 102},
        {"order_type": "ask", "price": 104},
    ]
    best_bid, best_ask = informed_trader.get_best_bid_and_ask()
    assert best_bid["price"] == 102, "Expect the highest bid"
    assert best_ask["price"] == 104, "Expect the lowest ask"


@pytest.mark.asyncio
async def test_act_generates_orders(informed_trader):
    informed_trader.post_new_order = AsyncMock()
    await informed_trader.act()
    informed_trader.post_new_order.assert_awaited()
