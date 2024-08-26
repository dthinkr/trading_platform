import pytest
import time_machine
from httpx import AsyncClient
from client_connector.main import app
from structures import TraderCreationData, OrderStatus, OrderType
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, PropertyMock
from main_platform import TradingSession

@pytest.mark.asyncio
async def test_accelerated_experiment():
    params = TraderCreationData(
        default_price=1000,
        trade_intensity_informed=0.2,
        trading_day_duration=5,
        num_noise_traders=2,
        activity_frequency=1,
        order_amount=100,
        step=1,
        order_book_levels=5,
        passive_order_probability=0.5
    )

    start_time = datetime(2023, 4, 1, 0, 0, 0)  # Use a fixed start time for consistency

    with time_machine.travel(start_time, tick=False) as traveller:
        # Initialize the TradingSession
        session = TradingSession(duration=params.trading_day_duration, default_price=params.default_price)
        session.connection = AsyncMock()
        session.channel = AsyncMock()
        
        with patch("aio_pika.connect_robust", return_value=session.connection), patch(
            "main_platform.trading_platform.now", return_value=start_time.isoformat() + "Z"
        ):
            await session.initialize()
            session.connection.channel.assert_awaited()
            session.channel.declare_exchange.assert_awaited()
            assert session.active is True
            assert session.start_time == start_time.isoformat() + "Z"

        # Simulate order placement
        for i in range(5):  # Place 5 orders
            order_dict = {
                "id": f"test_order_{i}",
                "order_type": OrderType.BID.value if i % 2 == 0 else OrderType.ASK.value,
                "amount": 100,
                "price": params.default_price + (i * 10),
                "status": OrderStatus.BUFFERED.value,
            }
            placed_order = session.place_order(order_dict)
            assert placed_order["status"] == OrderStatus.ACTIVE.value
            assert session.order_book.all_orders[f"test_order_{i}"] == placed_order

        # Accelerate time
        traveller.shift(timedelta(minutes=params.trading_day_duration))
        
        # Simulate the run method's time check
        with patch('main_platform.trading_platform.now', return_value=start_time + timedelta(minutes=params.trading_day_duration)):
            # Call the run method directly, but don't wait for it to complete
            run_task = asyncio.create_task(session.run())
            # Wait a short time to allow the run method to process
            await asyncio.sleep(0.1)
            # Cancel the run task as we don't need it to continue running
            run_task.cancel()

        # Check if the session is finished
        assert session.is_finished

        # Get the order book snapshot
        order_book_snapshot = await session.get_order_book_snapshot()
        assert len(order_book_snapshot["bids"]) > 0, "Expect bids in the order book"
        assert len(order_book_snapshot["asks"]) > 0, "Expect asks in the order book"

        # Check the spread
        spread, _ = session.order_book.get_spread()
        assert spread is not None, "Expect a valid spread"

        # Clean up
        await session.clean_up()
        session.channel.close.assert_awaited()
        session.connection.close.assert_awaited()
        assert session.active is False

        print(f"\nTotal orders placed: {len(session.order_book.all_orders)}")
        print(f"Final spread: {spread}")
        print(f"Session finished: {session.is_finished}")