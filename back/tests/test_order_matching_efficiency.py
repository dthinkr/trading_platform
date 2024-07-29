import pytest
import asyncio
import time
import random
import logging
from main_platform.trading_platform import TradingSession
from structures import OrderType, TraderType
from traders.base_trader import BaseTrader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GREEN = "\033[92m"
BLUE = "\033[94m"
RESET = "\033[0m"

pytestmark = pytest.mark.asyncio(scope="module")

async def create_random_orders(trader, num_orders):
    orders = []
    for _ in range(num_orders):
        order_type = random.choice([OrderType.BID, OrderType.ASK])
        amount = 1
        price = random.randint(1900, 2100)
        orders.append((amount, price, order_type))
    return orders

async def test_order_creation_and_processing_efficiency(capsys):
    num_traders = 10
    num_orders_per_trader = 10
    duration = 1

    trading_session = None
    traders = []
    try:
        trading_session = TradingSession(duration=duration, default_price=2000)
        await trading_session.initialize()
        logger.info("Trading session initialized")

        traders = [BaseTrader(TraderType.NOISE, cash=10000, shares=100) for _ in range(num_traders)]
        for trader in traders:
            await trader.initialize()
            await trader.connect_to_session(trading_session.id)
        logger.info(f"{num_traders} traders initialized and connected")

        trading_session.set_initialization_complete()
        await trading_session.start_trading()
        logger.info("Trading session started")

        order_creation_tasks = [create_random_orders(trader, num_orders_per_trader) for trader in traders]
        all_orders = await asyncio.gather(*order_creation_tasks)
        total_orders = sum(len(orders) for orders in all_orders)
        logger.info(f"Created {total_orders} orders")

        start_time = time.time()
        for trader, orders in zip(traders, all_orders):
            for amount, price, order_type in orders:
                await trader.post_new_order(amount, price, order_type)
        end_time = time.time()

        total_time = end_time - start_time
        orders_per_second = total_orders / total_time

        with capsys.disabled():
            print(f"\n{GREEN}Order Creation and Processing Efficiency Results:{RESET}")
            print(f"{BLUE}Total time:{RESET} {total_time:.2f} seconds")
            print(f"{BLUE}Orders created and processed per second:{RESET} {GREEN}{orders_per_second:.2f}{RESET}")
            print(f"{BLUE}Required seconds per order:{RESET} {GREEN}{total_time / total_orders:.4f}{RESET}")
            print(f"{BLUE}Total orders created:{RESET} {total_orders}")

        assert orders_per_second > 0, "Orders per second should be positive"
        assert total_orders > 0, "There should be at least one order created"
        logger.info("Assertions passed")

    finally:
        if trading_session:
            await trading_session.clean_up()
        for trader in traders:
            await trader.clean_up()
        logger.info("Cleanup completed")

# async def test_order_matching_consistency(capsys):
#     duration = 1
#     trading_session = None
#     traders = []
    
#     predefined_orders = [
#         (1, 2000, OrderType.ASK),
#         (1, 1999, OrderType.ASK),
#         (1, 1998, OrderType.ASK),
#         (1, 2001, OrderType.BID),
#         (1, 2002, OrderType.BID),
#         (1, 2003, OrderType.BID),
#     ]
    
#     try:
#         trading_session = TradingSession(duration=duration, default_price=2000)
#         await trading_session.initialize()
#         logger.info("Trading session initialized")

#         trader = BaseTrader(TraderType.NOISE, cash=10000, shares=100)
#         await trader.initialize()
#         await trader.connect_to_session(trading_session.id)
#         logger.info("Trader initialized and connected")

#         trading_session.set_initialization_complete()
#         await trading_session.start_trading()
#         logger.info("Trading session started")

#         with capsys.disabled():
#             print(f"\n{GREEN}Order Matching Consistency Test Results:{RESET}")
            
#             for i, (amount, price, order_type) in enumerate(predefined_orders, 1):
#                 await trader.post_new_order(amount, price, order_type)
#                 order_book = await trading_session.get_order_book_snapshot()
                
#                 print(f"\n{BLUE}After posting order {i} ({order_type.name} @ {price}):{RESET}")
#                 print(order_book)
#                 print(f"Bids: {order_book['bids']}")
#                 print(f"Asks: {order_book['asks']}")

#         await asyncio.sleep(0.5)  # Allow some time for order processing

#         final_order_book = await trading_session.get_order_book_snapshot()
        
#         with capsys.disabled():
#             print(f"\n{GREEN}Final Order Book:{RESET}")
#             print(f"Bids: {final_order_book['bids']}")
#             print(f"Asks: {final_order_book['asks']}")

#     finally:
#         if trading_session:
#             await trading_session.clean_up()
#         await trader.clean_up()
#         logger.info("Cleanup completed")

@pytest.fixture(autouse=True)
async def cleanup_tasks():
    yield
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await asyncio.sleep(0.1)

@pytest.fixture(autouse=True)
async def close_aio_pika_connections():
    yield
    from aio_pika.connection import Connection
    for conn in list(Connection.INSTANCES):
        await conn.close()
    await asyncio.sleep(0.1)