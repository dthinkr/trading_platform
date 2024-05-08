import asyncio
import datetime
import json
import os
import tempfile
import uuid

import duckdb
import polars as pl
import requests
import yaml
from prefect import flow, task
from pymongo import MongoClient

from analysis.parameterize import generate_and_store_parameters, plot_parameters
from main_platform.custom_logger import setup_custom_logger

# file
# file
with open("analysis/config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)
DATA_FILE = tempfile.NamedTemporaryFile(suffix=".parquet", delete=True).name
TABLE_RES = config["TABLE_RES"]
TABLE_REF = config["TABLE_REF"]
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

# log
logger = setup_custom_logger(__name__)

# cloud_db
MD_TOKEN = config["MD_TOKEN"]
con = duckdb.connect(f"md:?motherduck_token={MD_TOKEN}")
con.execute(
    f"CREATE TABLE IF NOT EXISTS {TABLE_REF} (session_id VARCHAR, trader_data STRING)"
)

# params
bounds = {
    "order_amount": (1, 10),
    "trade_intensity_informed": (0.05, 0.3),
}
resolution = 4


# helpers
def handle_datetime(value: datetime.datetime) -> str:
    return value.isoformat() if isinstance(value, datetime.datetime) else value


def handle_bytes(value: bytes) -> str:
    return str(uuid.UUID(bytes=value)) if len(value) == 16 else value


def handle_json(value: dict | list) -> str:
    return json.dumps(value, default=str) if isinstance(value, (dict, list)) else value


def flatten_item(item: dict) -> dict:
    flat_dict = {}
    for key, value in item.items():
        if key == "_id":
            flat_dict["id"] = str(value)
        elif key == "content":
            # handle nested structure
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if sub_key in ["order_book", "active_orders", "history"]:
                        flat_dict[sub_key] = handle_json(sub_value)
                    elif isinstance(sub_value, datetime.datetime):
                        flat_dict[sub_key] = handle_datetime(sub_value)
                    else:
                        flat_dict[sub_key] = sub_value
        else:
            if isinstance(value, datetime.datetime):
                flat_dict[key] = handle_datetime(value)
            elif isinstance(value, bytes):
                flat_dict[key] = handle_bytes(value)
            elif isinstance(value, (dict, list)):
                flat_dict[key] = handle_json(value)
            else:
                flat_dict[key] = value

    return flat_dict


# flows and tasks
@task
def write_to_duckdb(session_id: str, trader_data: dict) -> None:
    trader_data_string = json.dumps(trader_data)
    con.execute(
        "INSERT INTO session_parameter VALUES (?, ?)", (session_id, trader_data_string)
    )


def create_trading_session(trader_data: dict) -> dict:
    url = "http://localhost:8000/trading/initiate"
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, data=json.dumps(trader_data), headers=headers)
    return response.json()


@task
async def create_and_wait_session(trader_data: dict) -> None:
    session_info = create_trading_session(trader_data)
    session_id = session_info.get("data", {}).get("trading_session_uuid")
    logger.info("Trading Session %s Initiated", session_id)

    simulation_length = trader_data.get("trading_day_duration", 1)
    buffer_time = 0.05
    total_wait_time = (simulation_length + buffer_time) * 60

    await asyncio.sleep(total_wait_time)
    logger.info("Trading Session %s Completed", session_id)

    write_to_duckdb.fn(session_id, trader_data)


@task
def ingest() -> None:
    table_exists = (
        con.execute(
            f"SELECT count(*) FROM information_schema.tables WHERE table_name = '{TABLE_RES}'"
        ).fetchone()[0]
        > 0
    )
    latest_timestamp = None
    if table_exists:
        latest_timestamp = con.execute(
            f"SELECT max(timestamp) FROM {TABLE_RES}"
        ).fetchone()[0]
        if isinstance(latest_timestamp, str):
            latest_timestamp = datetime.datetime.strptime(
                latest_timestamp, "%Y-%m-%dT%H:%M:%S.%f"
            )

    mongo_client = MongoClient("localhost", 27017)

    # fetch mongo data from timestamp
    query = {}
    if latest_timestamp:
        query = {"timestamp": {"$gt": latest_timestamp}}
    data = list(mongo_client["trader"].message.find(query))

    flattened_data = [flatten_item(item) for item in data]
    df = pl.DataFrame(flattened_data)

    df.write_parquet(DATA_FILE)

    if not df.is_empty():
        df.write_parquet(DATA_FILE)
        if table_exists:
            con.execute(
                f"INSERT INTO {TABLE_RES} SELECT * FROM read_parquet('{DATA_FILE}')"
            )
            logger.info(
                f"Data ingested successfully, latest timestamp: {latest_timestamp}"
            )
        else:
            con.execute(
                f"CREATE TABLE {TABLE_RES} AS SELECT * FROM read_parquet('{DATA_FILE}')"
            )
            logger.info(
                f"Table created successfully, latest timestamp: {latest_timestamp}"
            )
    else:
        logger.info(f"No new data to ingest, latest timestamp: {latest_timestamp}")


@flow
async def run_trading_sessions(params: list[dict]) -> None:
    for trader_data in params:
        await create_and_wait_session(trader_data)


def main():
    params = generate_and_store_parameters(bounds=bounds, resolution=resolution)
    # plot_parameters(params)
    asyncio.run(run_trading_sessions(params))
    ingest()
    con.close()


if __name__ == "__main__":
    main()
