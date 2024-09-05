import pytest
from unittest.mock import AsyncMock, patch
from traders import NoiseTrader
from structures import TraderType, ActionType


@pytest.fixture
def noise_trader_settings():
    return {
        "id": "1",
        "settings": {"initial": 100},
        "settings_noise": {
            "step": 1,
            "levels_n": 5,
            "pr_passive": 0.5,
            "pr_cancel": 0.1,
            "pr_bid": 0.5,
        },
    }


@pytest.fixture
def noise_trader(noise_trader_settings):
    return NoiseTrader(**noise_trader_settings)


def test_initialization(noise_trader):
    assert noise_trader.settings["initial"] == 100
    assert noise_trader.trader_type == TraderType.NOISE
    assert noise_trader.step == 1
    assert noise_trader.initial_value == 100


def test_cooling_interval(noise_trader):
    target = 5.0
    interval = noise_trader.cooling_interval(target)
    assert interval >= 0, "Interval should be non-negative"


@pytest.mark.asyncio
async def test_act_with_no_active_orders(noise_trader):
    noise_trader.order_book = {"bids": [], "asks": []}
    noise_trader.process_order = AsyncMock()
    await noise_trader.act()
    noise_trader.process_order.assert_awaited()


@pytest.mark.asyncio
async def test_process_order_add_order(noise_trader):
    noise_trader.post_new_order = AsyncMock()
    order = {
        "action_type": ActionType.POST_NEW_ORDER.value,
        "order_type": "ask",
        "price": 100,
        "amount": 1,
    }
    await noise_trader.process_order(order)
    noise_trader.post_new_order.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_order_cancel_order(noise_trader):
    noise_trader.orders = [{"id": "1", "order_type": "ask"}]
    noise_trader.send_cancel_order_request = AsyncMock()
    with patch("random.choice", return_value={"id": "1"}):
        await noise_trader.cancel_random_order()
    noise_trader.send_cancel_order_request.assert_awaited_once_with("1")
