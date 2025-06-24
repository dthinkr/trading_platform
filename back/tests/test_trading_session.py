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
    spread, _ = market.order_book.get_spread()
    assert spread == 10

@pytest.mark.asyncio
async def test_clean_up(market_id):
    market = TradingPlatform(market_id=market_id, duration=1, default_price=1000)
    market._stop_requested = asyncio.Event()
    market._stop_requested.set()
    await market.clean_up()
    assert market.active is False

@pytest.mark.asyncio
async def test_run(market_id):
    market = TradingPlatform(market_id=market_id, duration=1/60, default_price=1000)  # 1 second duration
    market.send_broadcast = AsyncMock()
    market.handle_inventory_report = AsyncMock()
    market.clean_up = AsyncMock()
    
    with patch('core.trading_platform.datetime') as mock_datetime:
        mock_datetime.now.side_effect = [
            datetime(2023, 4, 1, 0, 0, 0, tzinfo=timezone.utc),
            datetime(2023, 4, 1, 0, 0, 1, tzinfo=timezone.utc),
            datetime(2023, 4, 1, 0, 0, 2, tzinfo=timezone.utc),
        ]
        market.start_time = datetime(2023, 4, 1, 0, 0, 0, tzinfo=timezone.utc)
        await market.run()
    
    assert market.active is False
    assert market.is_finished is True
    market.send_broadcast.assert_awaited_with({"type": "closure"})
    market.clean_up.assert_awaited()

@pytest.mark.asyncio
async def test_matching_engine_performance(market_id):
    market = TradingPlatform(market_id=market_id, duration=1, default_price=1000)
    
    num_orders = 200000 
    matched_count = 0
    
    orders = []
    for i in range(num_orders):
        if i % 2 == 0:
            order_type = OrderType.BID
            price = 1000 
        else:
            order_type = OrderType.ASK
            price = 1000 
        
        order = {
            "id": f"order_{i}",
            "trader_id": f"trader_{i % 100}",
            "order_type": order_type.value,
            "amount": 1,
            "price": price,
            "status": OrderStatus.ACTIVE.value,
            "market_id": market_id
        }
        orders.append(order)
    
    start_time = time.time()
    
    for order in orders:
        placed_order, matched = market.place_order(order)
        if matched:
            matched_count += 1
    
    end_time = time.time()
    
    elapsed_time = end_time - start_time
    orders_per_second = num_orders / elapsed_time
    
    match_rate = matched_count / num_orders
    
    print(f"\nPerformance Test Results:")
    print(f"Total orders: {num_orders}")
    print(f"Elapsed time: {elapsed_time:.2f} seconds")
    print(f"Orders per second: {orders_per_second:.2f}")
    print(f"Matched orders: {matched_count}")
    print(f"Match rate: {match_rate:.2%}")
    
    assert orders_per_second > 1000, "Matching engine processed less than 1000 orders per second"