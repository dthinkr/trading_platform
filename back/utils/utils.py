import asyncio
import functools
import json
import logging
import os
from datetime import datetime
from enum import Enum
from json import JSONEncoder
from types import SimpleNamespace
from uuid import UUID

import duckdb
import yaml
from bson import ObjectId
from mongoengine import QuerySet
from pymongo import MongoClient
from pydantic import BaseModel
from termcolor import colored

CUR_LEVEL = logging.CRITICAL

dict_keys = type({}.keys())
dict_values = type({}.values())

logger = setup_custom_logger(__name__)
config = load_config()

class CustomFormatter(logging.Formatter):
    COLORS = {
        "WARNING": "yellow",
        "INFO": "cyan",
        "DEBUG": "blue",
        "CRITICAL": "red",
        "ERROR": "red",
    }

    def format(self, record):
        log_message = super(CustomFormatter, self).format(record)
        return colored(log_message, self.COLORS.get(record.levelname))

def setup_custom_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(CUR_LEVEL)

    # Only create a stream handler
    ch = logging.StreamHandler()
    ch.setLevel(CUR_LEVEL)

    formatter = CustomFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)

    logger.addHandler(ch)

    return logger

def load_config() -> SimpleNamespace:
    with open("analysis/config.yaml", "r", encoding="utf-8") as file:
        config_data = yaml.safe_load(file)
    return SimpleNamespace(**config_data)

# YAML constructor for !python/tuple
def tuple_constructor(loader, node):
    return tuple(loader.construct_sequence(node))

yaml.SafeLoader.add_constructor("!python/tuple", tuple_constructor)

def if_active(func):
    @functools.wraps(func)
    def sync_wrapper(self, *args, **kwargs):
        if not self.active:
            logger.critical(
                f"{func.__name__} is skipped because the trading session is not active."
            )
            return None
        return func(self, *args, **kwargs)

    async def async_wrapper(self, *args, **kwargs):
        if not self.active:
            logger.critical(
                f"{func.__name__} is skipped because the trading session is not active."
            )
            return None
        return await func(self, *args, **kwargs)

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

class CustomEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (ObjectId, UUID, Enum)):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        if isinstance(obj, (dict_keys, dict_values)):
            return list(obj)
        if isinstance(obj, QuerySet):
            return [doc.to_mongo().to_dict() for doc in obj]
        return JSONEncoder.default(self, obj)

def delete_all_tables() -> None:
    con = duckdb.connect(f"md:{CONFIG.DATASET}?motherduck_token={CONFIG.MD_TOKEN}")
    mongo_client = MongoClient("localhost", 27017)

    con.execute(f"DROP TABLE IF EXISTS {CONFIG.TABLE_REF}")
    con.execute(f"DROP TABLE IF EXISTS {CONFIG.TABLE_RES}")

    tables_deleted = con.execute("SHOW TABLES").fetchall()
    if (CONFIG.TABLE_REF,) not in tables_deleted and (CONFIG.TABLE_RES,) not in tables_deleted:
        logger.info("DuckDB tables deleted successfully.")
    else:
        logger.error("Error: DuckDB tables not deleted.")

    db = mongo_client["trader"]
    db.message.drop()

    if "message" not in db.list_collection_names():
        logger.info("MongoDB collection deleted successfully.")
    else:
        logger.error("Error: MongoDB collection not deleted.")

    con.close()
    mongo_client.close()