import pytest
from unittest.mock import AsyncMock, patch
from traders import NoiseTrader
from structures import TraderType

@pytest.fixture
def noise_trader_settings():
    return {
        "activity_frequency": 1.0,
        "order_amount": 10,  # Example new parameter
        "settings": {"initial_price": 100},
        "settings_noise": {},
        "get_signal_noise": lambda signal_state, settings_noise: {},
        "get_noise_rule_unif": lambda book_format, signal_noise, noise_state, settings_noise, settings: [],
    }

@pytest.fixture
def noise_trader(noise_trader_settings):
    return NoiseTrader(**noise_trader_settings)


def test_initialization(noise_trader):
    assert noise_trader.activity_frequency == 1.0
    assert noise_trader.settings["initial_price"] == 100
    assert noise_trader.current_variance == 5.0
    assert noise_trader.trader_type == TraderType.NOISE


def test_cooling_interval(noise_trader):
    target = 5.0
    interval = noise_trader.cooling_interval(target)
    assert interval >= 0, "Interval should be non-negative"


@pytest.mark.asyncio
async def test_act_with_no_active_orders(noise_trader):
    noise_trader.active_orders = []
    noise_trader.post_new_order = AsyncMock()
    await noise_trader.act()
    noise_trader.post_new_order.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_order_add_order(noise_trader):
    noise_trader.post_new_order = AsyncMock()
    order = {"action_type": "add_order", "order_type": "ask", "price": 100, "amount": 1}
    await noise_trader.process_order(order)
    noise_trader.post_new_order.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_order_cancel_order(noise_trader):
    noise_trader.orders = [{"id": "1", "order_type": "ask"}]
    noise_trader.send_cancel_order_request = AsyncMock()
    order = {"action_type": "cancel_order", "order_type": "ask"}
    with patch("random.choice", return_value={"id": "1"}):
        await noise_trader.process_order(order)
    noise_trader.send_cancel_order_request.assert_awaited_once_with("1")
