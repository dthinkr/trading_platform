import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from core import TradingPlatform
from core.data_models import OrderStatus, OrderType, Order
from datetime import datetime, timezone, timedelta
import uuid
import time
import random
import glob
import os

@pytest.fixture(autouse=True)
def cleanup_logs(market_id):
    yield  # This line allows the test to run
    # After the test is complete, remove the log files
    log_pattern = f"logs/{market_id}*.log"
    for log_file in glob.glob(log_pattern):
        try:
            os.remove(log_file)
            print(f"Removed log file: {log_file}")
        except Exception as e:
            print(f"Error removing log file {log_file}: {e}")

@pytest.fixture
def market_id():
    return f"TEST_{str(uuid.uuid4())}"

@pytest.fixture(autouse=True)
async def cleanup():
    yield
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await asyncio.sleep(0.1)  # Give a short time for tasks to complete cancellation

@pytest.mark.asyncio
async def test_initialize(market_id):
    market = TradingPlatform(market_id=market_id, duration=1, default_price=1000)

    with patch('core.trading_platform.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2023, 4, 1, tzinfo=timezone.utc)
        await market.initialize()

    assert market.active is True
    assert market.start_time == datetime(2023, 4, 1, tzinfo=timezone.utc)

@pytest.mark.asyncio
async def test_place_order(market_id):
    market = TradingPlatform(market_id=market_id, duration=1, default_price=1000)
    order_dict = {
        "id": "test_order_id",
        "order_type": OrderType.BID.value,
        "amount": 100,
        "price": 1000,
        "status": OrderStatus.BUFFERED.value,
        "trader_id": "test_trader",
        "market_id": market.id
    }
    order = Order(**order_dict)
    placed_order, _ = market.place_order(order.model_dump())
    assert placed_order["status"] == OrderStatus.ACTIVE.value

@pytest.mark.asyncio
async def test_order_book_empty(market_id):
    market = TradingPlatform(market_id=market_id, duration=1, default_price=1000)
    order_book_snapshot = await market.get_order_book_snapshot()
    assert order_book_snapshot == {
        "bids": [],
        "asks": [],
    }, "Order book should be empty initially"

@pytest.mark.asyncio
async def test_order_book_with_only_bids(market_id):
    market = TradingPlatform(market_id=market_id, duration=1, default_price=1000)
    market.place_order({
        "id": "bid_order_1",
        "order_type": OrderType.BID.value,
        "price": 1000,
        "amount": 10,
        "status": OrderStatus.ACTIVE.value,
        "trader_id": "test_trader",
        "market_id": market.id
    })
    market.place_order({
        "id": "bid_order_2",
        "order_type": OrderType.BID.value,
        "price": 1010,
        "amount": 5,
        "status": OrderStatus.ACTIVE.value,
        "trader_id": "test_trader",
        "market_id": market.id
    })
    order_book = await market.get_order_book_snapshot()
    assert order_book["asks"] == [], "Expect no asks in the order book"
    assert len(order_book["bids"]) == 2, "Expect two bids in the order book"
    assert order_book["bids"][0]["x"] == 1010, "The first bid should have the highest price"

@pytest.mark.asyncio
async def test_order_book_with_only_asks(market_id):
    market = TradingPlatform(market_id=market_id, duration=1, default_price=1000)
    market.place_order({
        "id": "ask_order_1",
        "order_type": OrderType.ASK.value,
        "price": 1020,
        "amount": 10,
        "status": OrderStatus.ACTIVE.value,
        "trader_id": "test_trader",
        "market_id": market.id
    })
    market.place_order({
        "id": "ask_order_2",
        "order_type": OrderType.ASK.value,
        "price": 1005,
        "amount": 5,
        "status": OrderStatus.ACTIVE.value,
        "trader_id": "test_trader",
        "market_id": market.id
    })
    order_book = await market.get_order_book_snapshot()
    assert order_book["bids"] == [], "Expect no bids in the order book"
    assert len(order_book["asks"]) == 2, "Expect two asks in the order book"
    assert order_book["asks"][0]["x"] == 1005, "The first ask should have the lowest price"

@pytest.mark.asyncio
async def test_order_book_with_bids_and_asks(market_id):
    market = TradingPlatform(market_id=market_id, duration=1, default_price=1000)
    market.place_order({
        "id": "bid_order",
        "order_type": OrderType.BID.value,
        "price": 1000,
        "amount": 10,
        "status": OrderStatus.ACTIVE.value,
        "trader_id": "test_trader",
        "market_id": market.id
    })
    market.place_order({
        "id": "ask_order",
        "order_type": OrderType.ASK.value,
        "price": 1020,
        "amount": 5,
        "status": OrderStatus.ACTIVE.value,
        "trader_id": "test_trader",
        "market_id": market.id
    })
    order_book = await market.get_order_book_snapshot()
    assert len(order_book["bids"]) == 1, "Expect one bid in the order book"
    assert len(order_book["asks"]) == 1, "Expect one ask in the order book"
    assert order_book["bids"][0]["x"] == 1000, "The bid price should match"
    assert order_book["asks"][0]["x"] == 1020, "The ask price should match"

@pytest.mark.asyncio
async def test_get_spread(market_id):
    market = TradingPlatform(market_id=market_id, duration=1, default_price=1000)
    market.place_order({
        "id": "ask_order",
        "order_type": OrderType.ASK.value,
        "price": 1010,
        "amount": 5,
        "status": OrderStatus.ACTIVE.value,
        "trader_id": "test_trader",
        "market_id": market.id
    })
    market.place_order({
        "id": "bid_order",
        "order_type": OrderType.BID.value,
        "price": 1000,
        "amount": 5,
        "status": OrderStatus.ACTIVE.value,
        "trader_id": "test_trader",
        "market_id": market.id
    })
    spread, _ = market.order_book_manager.get_spread()
    assert spread == 10

@pytest.mark.asyncio
async def test_clean_up(market_id):
    market = TradingPlatform(market_id=market_id, duration=1, default_price=1000)
    market._stop_requested = asyncio.Event()
    market._stop_requested.set()
    await market.clean_up()
    assert market.active is False

@pytest.mark.asyncio
async def test_handle_add_order(market_id):
    market = TradingPlatform(market_id=market_id, duration=1, default_price=1000)
    await market.initialize()
    
    order_data = {
        "trader_id": "test_trader",
        "order_type": OrderType.BID.value,
        "amount": 10,
        "price": 1000,
        "order_id": str(uuid.uuid4())
    }
    
    result = await market.handle_add_order(order_data, "test_trader")
    assert result["type"] == "ADDED_ORDER"
    assert result["respond"] is True

@pytest.mark.asyncio
async def test_run(market_id):
    market = TradingPlatform(market_id=market_id, duration=0.01, default_price=1000)  # Very short duration
    await market.initialize()
    await market.start_trading()
    
    # Run the market for a short time
    run_task = asyncio.create_task(market.run())
    await asyncio.sleep(0.1)  # Let it run briefly
    
    # Clean up
    market._stop_requested.set()
    await run_task
    
    assert market.is_finished is True

@pytest.mark.asyncio
async def test_matching_engine_performance(market_id):
    market = TradingPlatform(market_id=market_id, duration=1, default_price=1000)
    
    # Measure time to place many orders
    start_time = time.time()
    for i in range(100):
        order_dict = {
            "id": f"order_{i}",
            "order_type": OrderType.BID.value if i % 2 == 0 else OrderType.ASK.value,
            "amount": random.randint(1, 10),
            "price": random.randint(950, 1050),
            "status": OrderStatus.BUFFERED.value,
            "trader_id": f"trader_{i}",
            "market_id": market.id
        }
        market.place_order(order_dict)
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Should be able to place 100 orders in less than 1 second
    assert elapsed_time < 1.0, f"Placing 100 orders took {elapsed_time:.3f}s, should be < 1.0s"
    
    # Verify order book has orders
    order_book = await market.get_order_book_snapshot()
    total_orders = len(order_book["bids"]) + len(order_book["asks"])
    assert total_orders > 0, "Order book should have some orders after placing 100"