import json
import polars as pl
from typing import Tuple
from analysis import load_config
from main_platform.utils import convert_to_book_format_new


def load_configuration() -> dict:
    return load_config()


def load_local_data(config: dict) -> Tuple[pl.DataFrame, pl.DataFrame]:
    df_ref = pl.read_csv(f"{config.DATA_DIR}/reference_data.csv")
    df_res = pl.read_csv(f"{config.DATA_DIR}/result_data.csv")
    return df_ref, df_res


def parse_and_transform_active_orders(active_orders: str) -> pl.DataFrame:
    orders_list = json.loads(active_orders)
    return pl.DataFrame(orders_list)


def lobster_book_transformation(df_res: pl.DataFrame) -> pl.DataFrame:
    active_orders_df = df_res["order_book"].str.json_decode()

    book_format_series = active_orders_df.map_elements(
        lambda ob: convert_to_book_format_new(ob)
        if ob
        else pl.DataFrame({"price": [], "amount": []}),
        return_dtype=pl.Object,
    )

    df_res = df_res.with_columns(book_format_series.alias("LOBSTER_BOOK"))
    return df_res


def lobster_message_time(df_res: pl.DataFrame) -> pl.DataFrame:
    if "Time" not in df_res.columns:
        df_res = df_res.with_columns(
            pl.col("timestamp")
            .str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M:%S.%f", strict=False)
            .alias("Time")
        )
    min_timestamps = (
        df_res.filter(pl.col("Time").is_not_null())
        .group_by("trading_session_id")
        .agg(pl.min("Time").alias("session_start"))
    )
    if "session_start" not in df_res.columns:
        df_res = df_res.join(min_timestamps, on="trading_session_id", how="left")
    if "Time" not in df_res.columns or df_res["Time"].dtype != pl.Float64:
        df_res = df_res.with_columns(
            (
                pl.when(
                    pl.col("Time").is_not_null() & pl.col("session_start").is_not_null()
                )
                .then(
                    (pl.col("Time") - pl.col("session_start"))
                    .dt.total_nanoseconds()
                    .cast(pl.Float64)
                    / 1e6
                    / 1e3
                )
                .otherwise(None)
                .alias("Time")
            )
        )
    return df_res


def lobster_message_type(df_res: pl.DataFrame, config: dict) -> pl.DataFrame:
    type_mapping = config.TYPE_MAPPING
    df_res = df_res.with_columns(
        pl.col("type")
        .map_elements(lambda x: type_mapping.get(x, None), return_dtype=pl.Int32)
        .alias("Event Type")
    )
    return df_res


def lobster_message_other(df_res: pl.DataFrame) -> pl.DataFrame:
    df_res = df_res.with_columns(
        [
            pl.col("id").alias("Order ID"),
            pl.col("order_trader_id").alias("Trader ID"),
            pl.col("order_amount").alias("Size"),
            pl.col("order_price").alias("Price"),
            pl.col("order_type").alias("Direction"),
        ]
    )
    return df_res


def prepare_data() -> Tuple[pl.DataFrame, pl.DataFrame]:
    config = load_configuration()
    df_ref, df_res = load_local_data(config)
    df_res = lobster_book_transformation(df_res)
    df_res = lobster_message_time(df_res)
    df_res = lobster_message_type(df_res, config)
    df_res = lobster_message_other(df_res)
    return df_ref, df_res


if __name__ == "__main__":
    df_ref, df_res = prepare_data()
    print(df_res)
