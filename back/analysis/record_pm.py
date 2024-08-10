from pymongo import MongoClient
import polars as pl
from typing import Dict, List
import numpy as np
import matplotlib.pyplot as plt
from . import load_config

CONFIG = load_config()

def get_data_from_mongodb(session_ids: List[str] = None) -> pl.DataFrame:
    client = MongoClient(CONFIG.MONGODB_HOST, CONFIG.MONGODB_PORT)
    db = client[CONFIG.DATASET]
    collection = db[CONFIG.COLLECTION_NAME]

    if session_ids:
        query = {"trading_session_id": {"$in": session_ids}}
    else:
        random_session = collection.aggregate([{"$sample": {"size": 1}}]).next()
        query = {"trading_session_id": random_session["trading_session_id"]}

    data = list(collection.find(query))
    return pl.DataFrame(data)

def filter_valid_data(run_data: pl.DataFrame) -> pl.DataFrame:
    return run_data.filter(
        (pl.col("content").struct.field("incoming_message").is_not_null())
        & (pl.col("content").struct.field("incoming_message").struct.field("order_type").is_in([1, -1]))
    ).with_columns(
        pl.when(pl.col("content").struct.field("incoming_message").struct.field("amount").eq(-1))
        .then(-1)
        .when(pl.col("content").struct.field("incoming_message").struct.field("amount") > 0)
        .then(pl.col("content").struct.field("incoming_message").struct.field("amount"))
        .otherwise(0)
        .alias("adjusted_amount")
    )

def calculate_order_book_imbalance(order_book: Dict[str, List[Dict[str, float]]]) -> float:
    if order_book is None:
        return None
    total_bid_volume = sum(bid['y'] for bid in order_book['bids'])
    total_ask_volume = sum(ask['y'] for ask in order_book['asks'])
    if total_bid_volume + total_ask_volume == 0:
        return 0
    return (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume)

def process_session(session_data: pl.DataFrame, window_size: int = CONFIG.ROLLING_WINDOW_SIZE) -> pl.DataFrame:
    filtered_data = filter_valid_data(session_data)

    preprocessed_data = filtered_data.with_columns([
        pl.col('timestamp').cast(pl.Datetime),
        ((pl.col('timestamp').cast(pl.Datetime) - pl.col('timestamp').cast(pl.Datetime).min()).dt.total_milliseconds() / 1e3).cast(pl.Float32).alias('seconds_into_session'),
        pl.col('content').struct.field('transaction_price').alias('transaction_price'),
        pl.col('content').struct.field('incoming_message').struct.field('price').alias('order_price'),
        pl.col('content').struct.field('incoming_message').struct.field('order_type').alias('order_type'),
        pl.col('content').struct.field('spread').alias('spread'),
        pl.col('content').struct.field('midpoint').alias('midpoint'),
        pl.col('content').struct.field('order_book').alias('order_book')
    ]).sort('seconds_into_session')

    cumulative_metrics = preprocessed_data.with_columns([
        pl.len().cum_sum().alias('total_messages'),
        (pl.col('adjusted_amount') != -1).cum_sum().alias('total_orders'),
        (pl.col('adjusted_amount') == -1).cum_sum().alias('total_cancellations'),
        (pl.col('order_type') == 1).cum_sum().alias('total_buy_orders'),
        (pl.col('order_type') == -1).cum_sum().alias('total_sell_orders'),
        pl.col('transaction_price').is_not_null().cum_sum().alias('num_trades'),
        (pl.col('transaction_price') * pl.col('adjusted_amount')).cum_sum().alias('total_volume'),
        pl.col('transaction_price').cum_max().alias('high_price'),
        pl.col('transaction_price').cum_min().alias('low_price'),
        (pl.col('transaction_price').cum_sum() / pl.col('transaction_price').is_not_null().cum_sum()).alias('avg_price'),
        pl.col('spread').rolling_mean(window_size=window_size).alias('avg_spread'),
        pl.col('midpoint').rolling_mean(window_size=window_size).alias('avg_midpoint')
    ])

    time_series_metrics = cumulative_metrics.with_columns([
        pl.col('order_book').map_elements(calculate_order_book_imbalance, return_dtype=pl.Float64).alias('order_book_imbalance'),
        (pl.when(pl.col('num_trades') > 0).then(pl.col('total_volume') / pl.col('num_trades')).otherwise(None)).alias('avg_trade_size'),
        (pl.col('num_trades') / pl.col('seconds_into_session')).alias('trade_frequency'),
        (pl.when(pl.col('avg_price') > 0).then((pl.col('high_price') - pl.col('low_price')) / pl.col('avg_price')).otherwise(None)).alias('price_range_percent'),
        (pl.when(pl.col('total_orders') > 0).then(pl.col('num_trades') / pl.col('total_orders')).otherwise(None)).alias('order_fill_rate'),
        (pl.when(pl.col('total_orders') > 0).then(pl.col('total_cancellations') / pl.col('total_orders')).otherwise(None)).alias('cancellation_rate'),
        (pl.col('num_trades') / pl.col('total_messages')).alias('trade_message_ratio'),
        pl.col('transaction_price').rolling_std(window_size=window_size).alias('price_volatility')
    ])

    columns_to_keep = [
        'timestamp', 'seconds_into_session', 'total_messages', 'total_orders', 'total_cancellations',
        'total_buy_orders', 'total_sell_orders', 'num_trades', 'total_volume', 'high_price', 'low_price',
        'avg_price', 'avg_spread', 'avg_midpoint', 'order_book_imbalance', 'avg_trade_size', 'trade_frequency',
        'price_range_percent', 'order_fill_rate', 'cancellation_rate', 'trade_message_ratio', 'price_volatility'
    ]

    return time_series_metrics.select(columns_to_keep)

def calculate_time_series_metrics(run_data: pl.DataFrame) -> Dict[str, pl.DataFrame]:
    grouped_data = run_data.group_by(['trading_session_id'])

    results = {}
    for group in grouped_data:
        session_id = group[0]
        # Change this line:
        session_id = session_id[0] if isinstance(session_id, tuple) else session_id
        session_data = group[1]
        session_metrics = process_session(session_data)
        results[session_id] = session_metrics.sort('seconds_into_session')

    return results

def get_time_series_metrics_for_sessions(session_ids: List[str] = None) -> Dict[str, pl.DataFrame]:
    run_data = get_data_from_mongodb(session_ids)
    return calculate_time_series_metrics(run_data)

def plot_session_metrics(session_data: pl.DataFrame, session_id: str) -> None:
    session_data_pd = session_data.to_pandas()
    fig, axs = plt.subplots(3, 2, figsize=(20, 15))
    fig.suptitle(f'Time Series Metrics for Session: {session_id}', fontsize=16)

    def safe_log(x):
        return np.log1p(np.abs(x)) * np.sign(x)

    def normalize(x):
        return (x - np.min(x)) / (np.max(x) - np.min(x))

    plots = [
        (safe_log, ['avg_price', 'high_price', 'low_price'], 'Price Metrics (Log Scale)'),
        (safe_log, ['total_orders', 'total_buy_orders', 'total_sell_orders'], 'Order Metrics (Log Scale)'),
        (safe_log, ['num_trades', 'total_volume'], 'Trade Metrics (Log Scale)'),
        (safe_log, ['avg_spread', 'avg_midpoint'], 'Order Book Metrics (Log Scale)'),
        (normalize, ['order_book_imbalance', 'order_fill_rate', 'cancellation_rate'], 'Derived Metrics 1 (Normalized)'),
        (None, ['price_volatility', 'trade_frequency', 'price_range_percent'], 'Derived Metrics 2')
    ]

    for i, (func, columns, title) in enumerate(plots):
        ax = axs[i // 2, i % 2]
        for col in columns:
            y_data = session_data_pd[col]
            if func is not None:
                y_data = func(y_data)
            elif col == 'price_volatility':
                y_data = safe_log(y_data)
            elif col == 'trade_frequency':
                y_data = safe_log(y_data)
            elif col == 'price_range_percent':
                y_data = normalize(y_data)
            ax.plot(session_data_pd['seconds_into_session'], y_data, label=col)
        ax.set_title(title)
        ax.legend()
        ax.set_xlabel('Seconds into Session')
        ax.tick_params(axis='x', rotation=45)

    plt.tight_layout()
    plt.savefig(f"{CONFIG.DATA_DIR}/figs/time_series_plot_{session_id}.png")
    plt.close()

if __name__ == "__main__":
    time_series_metrics = get_time_series_metrics_for_sessions()
    for session_id, metrics_df in time_series_metrics.items():
        output_path = f"{CONFIG.DATA_DIR}/time_series_metrics_{session_id}.csv"
        metrics_df.write_csv(output_path)
        plot_session_metrics(metrics_df, session_id)