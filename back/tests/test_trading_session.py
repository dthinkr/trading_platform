import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from core import TradingSession
from core.data_models import OrderStatus, OrderType, Order
from datetime import datetime, timezone, timedelta
import uuid
import time
import random
import glob
import os

@pytest.fixture(autouse=True)
def cleanup_logs(session_id):
    yield  # This line allows the test to run
    # After the test is complete, remove the log files
    log_pattern = f"logs/{session_id}*.log"
    for log_file in glob.glob(log_pattern):
        try:
            os.remove(log_file)
            print(f"Removed log file: {log_file}")
        except Exception as e:
            print(f"Error removing log file {log_file}: {e}")

@pytest.fixture
def session_id():
    return f"TEST_{str(uuid.uuid4())}"

@pytest.fixture
def mock_aio_pika():
    with patch('core.trading_platform.aio_pika') as mock:
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_connection.channel.return_value = mock_channel
        
        async def mock_connect_robust(*args, **kwargs):
            return mock_connection

        mock.connect_robust = MagicMock(side_effect=mock_connect_robust)
        yield mock

@pytest.fixture(autouse=True)
async def cleanup():
    yield
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await asyncio.sleep(0.1)  # Give a short time for tasks to complete cancellation

@pytest.mark.asyncio
async def test_initialize(mock_aio_pika, session_id):
    session = TradingSession(session_id=session_id, duration=1, default_price=1000)

    with patch('core.trading_platform.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2023, 4, 1, tzinfo=timezone.utc)
        await session.initialize()

    assert session.active is True
    assert session.start_time == datetime(2023, 4, 1, tzinfo=timezone.utc)
    mock_aio_pika.connect_robust.assert_called_once()
    session.connection.channel.assert_awaited_once()
    session.channel.declare_exchange.assert_awaited()
    session.channel.declare_queue.assert_awaited()

@pytest.mark.asyncio
async def test_place_order(session_id):
    session = TradingSession(session_id=session_id, duration=1, default_price=1000)
    order_dict = {
        "id": "test_order_id",
        "order_type": OrderType.BID.value,
        "amount": 100,
        "price": 1000,
        "status": OrderStatus.BUFFERED.value,
        "trader_id": "test_trader",
        "session_id": session.id
    }
    order = Order(**order_dict)
    placed_order, _ = session.place_order(order.model_dump())
    assert placed_order["status"] == OrderStatus.ACTIVE.value

@pytest.mark.asyncio
async def test_order_book_empty(session_id):
    session = TradingSession(session_id=session_id, duration=1, default_price=1000)
    order_book_snapshot = await session.get_order_book_snapshot()
    assert order_book_snapshot == {
        "bids": [],
        "asks": [],
    }, "Order book should be empty initially"

@pytest.mark.asyncio
async def test_order_book_with_only_bids(session_id):
    session = TradingSession(session_id=session_id, duration=1, default_price=1000)
    session.place_order({
        "id": "bid_order_1",
        "order_type": OrderType.BID.value,
        "price": 1000,
        "amount": 10,
        "status": OrderStatus.ACTIVE.value,
        "trader_id": "test_trader",
        "session_id": session.id
    })
    session.place_order({
        "id": "bid_order_2",
        "order_type": OrderType.BID.value,
        "price": 1010,
        "amount": 5,
        "status": OrderStatus.ACTIVE.value,
        "trader_id": "test_trader",
        "session_id": session.id
    })
    order_book = await session.get_order_book_snapshot()
    assert order_book["asks"] == [], "Expect no asks in the order book"
    assert len(order_book["bids"]) == 2, "Expect two bids in the order book"
    assert order_book["bids"][0]["x"] == 1010, "The first bid should have the highest price"

@pytest.mark.asyncio
async def test_order_book_with_only_asks(session_id):
    session = TradingSession(session_id=session_id, duration=1, default_price=1000)
    session.place_order({
        "id": "ask_order_1",
        "order_type": OrderType.ASK.value,
        "price": 1020,
        "amount": 10,
        "status": OrderStatus.ACTIVE.value,
        "trader_id": "test_trader",
        "session_id": session.id
    })
    session.place_order({
        "id": "ask_order_2",
        "order_type": OrderType.ASK.value,
        "price": 1005,
        "amount": 5,
        "status": OrderStatus.ACTIVE.value,
        "trader_id": "test_trader",
        "session_id": session.id
    })
    order_book = await session.get_order_book_snapshot()
    assert order_book["bids"] == [], "Expect no bids in the order book"
    assert len(order_book["asks"]) == 2, "Expect two asks in the order book"
    assert order_book["asks"][0]["x"] == 1005, "The first ask should have the lowest price"

@pytest.mark.asyncio
async def test_order_book_with_bids_and_asks(session_id):
    session = TradingSession(session_id=session_id, duration=1, default_price=1000)
    session.place_order({
        "id": "bid_order",
        "order_type": OrderType.BID.value,
        "price": 1000,
        "amount": 10,
        "status": OrderStatus.ACTIVE.value,
        "trader_id": "test_trader",
        "session_id": session.id
    })
    session.place_order({
        "id": "ask_order",
        "order_type": OrderType.ASK.value,
        "price": 1020,
        "amount": 5,
        "status": OrderStatus.ACTIVE.value,
        "trader_id": "test_trader",
        "session_id": session.id
    })
    order_book = await session.get_order_book_snapshot()
    assert len(order_book["bids"]) == 1, "Expect one bid in the order book"
    assert len(order_book["asks"]) == 1, "Expect one ask in the order book"
    assert order_book["bids"][0]["x"] == 1000, "The bid price should match"
    assert order_book["asks"][0]["x"] == 1020, "The ask price should match"

@pytest.mark.asyncio
async def test_get_spread(session_id):
    session = TradingSession(session_id=session_id, duration=1, default_price=1000)
    session.place_order({
        "id": "ask_order",
        "order_type": OrderType.ASK.value,
        "price": 1010,
        "amount": 5,
        "status": OrderStatus.ACTIVE.value,
        "trader_id": "test_trader",
        "session_id": session.id
    })
    session.place_order({
        "id": "bid_order",
        "order_type": OrderType.BID.value,
        "price": 1000,
        "amount": 5,
        "status": OrderStatus.ACTIVE.value,
        "trader_id": "test_trader",
        "session_id": session.id
    })
    spread, _ = session.order_book.get_spread()
    assert spread == 10

@pytest.mark.asyncio
async def test_clean_up(session_id):
    session = TradingSession(session_id=session_id, duration=1, default_price=1000)
    session.connection = AsyncMock()
    session.channel = AsyncMock()
    session._stop_requested = asyncio.Event()
    session._stop_requested.set()
    await session.clean_up()
    session.channel.close.assert_awaited()
    session.connection.close.assert_awaited()
    assert session.active is False

@pytest.mark.asyncio
async def test_run(session_id):
    session = TradingSession(session_id=session_id, duration=1/60, default_price=1000)  # 1 second duration
    session.send_broadcast = AsyncMock()
    session.handle_inventory_report = AsyncMock()
    session.clean_up = AsyncMock()
    
    with patch('core.trading_platform.datetime') as mock_datetime:
        mock_datetime.now.side_effect = [
            datetime(2023, 4, 1, 0, 0, 0, tzinfo=timezone.utc),
            datetime(2023, 4, 1, 0, 0, 1, tzinfo=timezone.utc),
            datetime(2023, 4, 1, 0, 0, 2, tzinfo=timezone.utc),
        ]
        session.start_time = datetime(2023, 4, 1, 0, 0, 0, tzinfo=timezone.utc)
        await session.run()
    
    assert session.active is False
    assert session.is_finished is True
    session.send_broadcast.assert_awaited_with({"type": "closure"})
    session.clean_up.assert_awaited()

@pytest.mark.asyncio
async def test_matching_engine_performance(session_id):
    session = TradingSession(session_id=session_id, duration=1, default_price=1000)
    
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
            "session_id": session_id
        }
        orders.append(order)
    
    start_time = time.time()
    
    for order in orders:
        placed_order, matched = session.place_order(order)
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