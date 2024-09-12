from pymongo import MongoClient, DESCENDING
import polars as pl
from typing import Dict, List
import numpy as np
import matplotlib.pyplot as plt
from utils import load_config
import io
import json
import csv
from fastapi.responses import JSONResponse

CONFIG = load_config()

def get_data_from_mongodb(
    session_ids: List[str] = None, limit: int = None
) -> pl.DataFrame:
    client = MongoClient(CONFIG.MONGODB_HOST, CONFIG.MONGODB_PORT)
    db = client[CONFIG.DATASET]
    collection = db[CONFIG.COLLECTION_NAME]

    if session_ids:
        query = {"trading_session_id": {"$in": session_ids}}
    else:
        # Get the most recent session ID
        latest_session = collection.find_one(sort=[("_id", DESCENDING)])
        query = {"trading_session_id": latest_session["trading_session_id"]}

    # Sort by _id in descending order to get the latest documents first
    cursor = collection.find(query).sort("_id", DESCENDING)

    # Apply limit if specified
    if limit:
        cursor = cursor.limit(limit)

    data = list(cursor)

    # Reverse the list to maintain chronological order
    data.reverse()

    return pl.DataFrame(data)

def process_message(
    message: Dict, order_book: Dict[str, Dict[int, int]], timestamp: float, message_type: str, informed_progress: float = None, matched_orders: Dict = None
) -> Dict:
    # Add debug print
    print(f"Processing message: {message}, type: {message_type}")

    price = message.get("price")
    size = message.get("amount")
    direction = message.get("order_type")

    # Convert to int only if the values are not None, otherwise keep as None
    price = int(price) if price is not None else None
    size = int(size) if size is not None else None
    direction = int(direction) if direction is not None else None

    if message_type == "ADDED_ORDER" and price is not None and size is not None and direction is not None:
        if direction == 1:  # Buy order
            if price not in order_book["bids"]:
                order_book["bids"][price] = 0
            order_book["bids"][price] += size
        elif direction == -1:  # Sell order
            if price not in order_book["asks"]:
                order_book["asks"][price] = 0
            order_book["asks"][price] += size

    bid_prices = sorted(order_book["bids"].keys(), reverse=True)
    ask_prices = sorted(order_book["asks"].keys())

    processed_message = {
        "seconds_into_session": timestamp,
        "source": message.get("trader_id", ""),
        "message_type": message_type,
        "incoming_message": f"{price},{size},{direction}" if all(v is not None for v in [price, size, direction]) else None,
        "price": price,
        "size": size,
        "direction": direction,
        "Event_Type": 1 if message_type == "ADDED_ORDER" else 0,
        "Ask_Price_1": ask_prices[0] if ask_prices else None,
        "Bid_Price_1": bid_prices[0] if bid_prices else None,
        "Midprice": (ask_prices[0] + bid_prices[0]) / 2 if ask_prices and bid_prices else None,
        "Ask_Prices": ask_prices,
        "Ask_Sizes": [order_book["asks"][p] for p in ask_prices],
        "Bid_Prices": bid_prices,
        "Bid_Sizes": [order_book["bids"][p] for p in bid_prices],
        "matched_bid_id": matched_orders.get("bid_order_id") if matched_orders else None,
        "matched_ask_id": matched_orders.get("ask_order_id") if matched_orders else None,
        "informed_trader_progress": informed_progress,
    }
    return processed_message

def process_session(session_data: pl.DataFrame) -> List[Dict]:
    order_book = {"bids": {}, "asks": {}}
    processed_messages = []
    filled_order_printed = False

    for row in session_data.iter_rows(named=True):
        message = row["content"].get("incoming_message", {})
        message_type = row["content"].get("type", "UNKNOWN")
        timestamp = (row["timestamp"] - session_data["timestamp"].min()).total_seconds()
        informed_progress = row["content"].get("informed_trader_progress")
        matched_orders = row["content"].get("matched_orders")

        if message_type == "FILLED_ORDER" and not filled_order_printed:
            print("FILLED_ORDER message found:")
            print(json.dumps(row["content"], indent=2, default=str))
            filled_order_printed = True

        processed_message = process_message(message, order_book, timestamp, message_type, informed_progress, matched_orders)
        
        # Only append messages with non-empty incoming_message
        if processed_message["incoming_message"]:
            processed_messages.append(processed_message)

    if not filled_order_printed:
        print("No FILLED_ORDER message found in the session data.")

    return processed_messages

def write_to_csv(data: List[Dict], output_file: str):
    with open(output_file, "w", newline="") as csvfile:
        fieldnames = [
            "seconds_into_session",
            "source",
            "message_type",
            "incoming_message",
            "price",
            "size",
            "direction",
            "Event_Type",
            "Ask_Price_1",
            "Bid_Price_1",
            "Midprice",
            "Ask_Prices",
            "Ask_Sizes",
            "Bid_Prices",
            "Bid_Sizes",
            "matched_bid_id",
            "matched_ask_id",
            "informed_trader_progress",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow(row)


def calculate_end_of_run_metrics(df: pl.DataFrame) -> Dict:
    # This is a placeholder function that returns an empty dictionary
    return {}


if __name__ == "__main__":
    run_data = get_data_from_mongodb()
    processed_data = process_session(run_data)
    df = pl.DataFrame(processed_data)
    print(df.head())
    output_file = f"{CONFIG.DATA_DIR}/message_book.csv"
    write_to_csv(processed_data, output_file)
    print(f"Message book data written to {output_file}")
