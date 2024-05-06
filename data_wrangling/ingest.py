from pymongo import MongoClient
import polars as pl
import json
import uuid
import datetime
import duckdb
import os
import yaml
import tempfile

with open("data_wrangling/config.yaml", "r") as file:
    config = yaml.safe_load(file)

MD_TOKEN = config["MD_TOKEN"]
DATA_FILE = tempfile.NamedTemporaryFile(suffix=".parquet", delete=True).name

os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)


def handle_datetime(value):
    return value.isoformat() if isinstance(value, datetime.datetime) else value


def handle_bytes(value):
    return str(uuid.UUID(bytes=value)) if len(value) == 16 else value


def handle_json(value):
    return json.dumps(value, default=str) if isinstance(value, (dict, list)) else value


def flatten_item(item):
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


def ingest():
    client = duckdb.connect(f"md:?motherduck_token={MD_TOKEN}")

    # get latest motherduck timestamp
    table_exists = (
        client.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = 'trading_data'"
        ).fetchone()[0]
        > 0
    )
    latest_timestamp = None
    if table_exists:
        latest_timestamp = client.execute(
            "SELECT max(timestamp) FROM trading_data"
        ).fetchone()[0]

    mongo_client = MongoClient("localhost", 27017)

    # fetch mongo data from timestamp
    query = {}
    if latest_timestamp:
        query = {"timestamp": {"$gt": latest_timestamp}}
    data = list(mongo_client["trader"].message.find(query))

    flattened_data = [flatten_item(item) for item in data]
    df = pl.DataFrame(flattened_data)

    # Write DataFrame to Parquet
    df.write_parquet(DATA_FILE)

    if not df.is_empty():
        df.write_parquet(DATA_FILE)
        if table_exists:
            client.execute(
                f"INSERT INTO trading_data SELECT * FROM read_parquet('{DATA_FILE}')"
            )
        else:
            client.execute(
                f"CREATE TABLE trading_data AS SELECT * FROM read_parquet('{DATA_FILE}')"
            )
    else:
        print(f"No new data to ingest, latest timestamp: {latest_timestamp}")
