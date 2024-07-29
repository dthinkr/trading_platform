import asyncio
import time
import random
from main_platform.trading_platform import TradingSession
from structures import OrderType, TraderType
from traders.base_trader import BaseTrader
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def create_random_orders(trader, num_orders):
    orders = []
    for _ in range(num_orders):
        order_type = random.choice([OrderType.BID, OrderType.ASK])
        amount = random.randint(1, 10)
        price = random.randint(95, 105)
        orders.append((amount, price, order_type))
    return orders

async def run_benchmark(num_traders, num_orders_per_trader, duration):
    trading_session = None
    traders = []
    try:
        logger.info("Initializing trading session")
        trading_session = TradingSession(duration=duration, default_price=100)
        await trading_session.initialize()

        logger.info("Creating and initializing traders")
        traders = [BaseTrader(TraderType.NOISE, cash=10000, shares=100) for _ in range(num_traders)]
        for trader in traders:
            await trader.initialize()
            await trader.connect_to_session(trading_session.id)

        logger.info("Starting trading session")
        trading_session.set_initialization_complete()
        await trading_session.start_trading()

        logger.info("Creating orders")
        order_creation_tasks = [create_random_orders(trader, num_orders_per_trader) for trader in traders]
        all_orders = await asyncio.gather(*order_creation_tasks)
        total_orders = sum(len(orders) for orders in all_orders)

        logger.info(f"Total orders created: {total_orders}")

        # Post all orders and measure the time
        start_time = time.time()
        for trader, orders in zip(traders, all_orders):
            for amount, price, order_type in orders:
                await trader.post_new_order(amount, price, order_type)
        end_time = time.time()

        total_time = end_time - start_time
        orders_per_second = total_orders / total_time
        transactions = len(trading_session.transactions)
        transactions_per_second = transactions / total_time

        logger.info("Benchmark Results:")
        logger.info(f"Total time: {total_time:.2f} seconds")
        logger.info(f"Orders per second: {orders_per_second:.2f}")
        logger.info(f"Transactions per second: {transactions_per_second:.2f}")
        logger.info(f"Total transactions: {transactions}")
        logger.info(f"Total orders created: {total_orders}")
        logger.info(f"Final order book: {trading_session.order_book}")

    except Exception as e:
        logger.error(f"Error during benchmark: {e}", exc_info=True)
    finally:
        logger.info("Cleaning up")
        if trading_session:
            await trading_session.clean_up()
        for trader in traders:
            await trader.clean_up()

if __name__ == "__main__":
    num_traders = 10
    num_orders_per_trader = 100
    duration = 1  # minutes

    asyncio.run(run_benchmark(num_traders, num_orders_per_trader, duration))