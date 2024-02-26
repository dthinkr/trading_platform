from json import JSONEncoder
from datetime import datetime
from functools import wraps
import aio_pika
from enum import Enum
from pprint import pprint
from enum import IntEnum
from uuid import UUID
from structures.structures import   ActionType, LobsterEventType
from collections import defaultdict
from typing import List, Dict
import pandas as pd
import numpy as np
import asyncio
import os
import csv
from main_platform.custom_logger import setup_custom_logger
from external_traders.noise_trader import settings
from pydantic import BaseModel
np.set_printoptions(floatmode='fixed', precision=0)

logger = setup_custom_logger(__name__)

dict_keys = type({}.keys())
dict_values = type({}.values())
DATA_PATH = 'data'
LOBSTER_MONEY_CONSTANT = 1
from datetime import timezone, datetime


def now():
    """
    Get the current time in UTC. the datetime.utcnow is a wrong one, because it is not parsed correctly by JS.
    We'll keep it here as a universal function to get the current time, if we later on need to change it to a different
    timezone, we can just do it here.
    """
    return datetime.now(timezone.utc)


class CustomEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, dict_keys):
            return list(obj)
        if isinstance(obj, dict_values):
            return list(obj)
        if isinstance(obj, UUID):
            return str(obj)
        return JSONEncoder.default(self, obj)


def ack_message(func):
    @wraps(func)
    async def wrapper(self, message: aio_pika.IncomingMessage):
        await func(self, message)
        await message.ack()

    return wrapper


def expand_dataframe(df, max_depth=10, step=1, reverse=False, default_price=0):
    """
    Expand a DataFrame to a specified max_depth.

    Parameters:
        df (DataFrame): DataFrame containing 'price' and 'amount' columns.
        max_depth (int, optional): Maximum length to which the DataFrame should be expanded. Default is 10.
        step (int, optional): Step to be used for incrementing the price levels. Default is 1.
        reverse (bool, optional): Whether to reverse the order of the DataFrame. Default is False.
        default_price (float, optional): Default starting price if DataFrame is empty. Default is 0.

    Returns:
        DataFrame: Expanded DataFrame.
    """

    # Check if DataFrame is empty
    if df.empty:
        df = pd.DataFrame({'price': [default_price], 'amount': [0]})

    # Sort the DataFrame based on 'price'
    df = df.sort_values('price', ascending=not reverse)

    # Sort the DataFrame based on 'price'
    df.sort_values('price', ascending=not reverse, inplace=True)

    # Calculate the number of additional rows needed
    additional_rows_count = max_depth - len(df)

    if additional_rows_count <= 0:
        return df.iloc[:max_depth]

    # Determine the direction of the step based on 'reverse'
    step_direction = -1 if reverse else 1

    # Generate additional elements for price levels
    last_price = df['price'].iloc[-1 if reverse else 0]
    existing_prices = set(df['price'].values)
    additional_price_elements = []

    i = 1
    while len(additional_price_elements) < additional_rows_count:
        new_price = last_price + i * step * step_direction
        if new_price not in existing_prices:
            additional_price_elements.append(new_price)
            existing_prices.add(new_price)
        i += 1
    # Generate additional elements for amount (all zeros)
    additional_amount_elements = [0] * additional_rows_count

    # Create a DataFrame for the additional elements
    df_additional = pd.DataFrame({'price': additional_price_elements, 'amount': additional_amount_elements})

    # Concatenate the original DataFrame with the additional elements
    df_expanded = pd.concat([df, df_additional]).reset_index(drop=True)

    # Sort the DataFrame based on 'price' if 'reverse' is True
    if reverse:
        df_expanded.sort_values('price', ascending=False, inplace=True)
        df_expanded.reset_index(drop=True, inplace=True)

    return df_expanded


def convert_to_book_format(active_orders, levels_n=10, default_price=2000):
    """ That's the OLD function for Lobster format. I keep it here for now but that all should be deeply rewritten"""
    # Create a DataFrame from the list of active orders

    if active_orders:
        df = pd.DataFrame(active_orders)
    else:
        # Create an empty DataFrame with default columns
        df = pd.DataFrame(columns=[field for field in OrderModel.__annotations__])
    df['price'] = df['price'].round(5)
    df = df.astype({"price": int, "amount": int})

    # Aggregate orders by price, summing the amounts
    df_asks = df[df['order_type'] == OrderType.ASK.value].groupby('price')['amount'].sum().reset_index().sort_values(
        by='price').head(
        levels_n)
    df_bids = df[df['order_type'] == OrderType.BID.value].groupby('price')['amount'].sum().reset_index().sort_values(
        by='price',
        ascending=False).head(
        levels_n)

    df_asks = expand_dataframe(df_asks, max_depth=10, step=1, reverse=False, default_price=default_price)
    df_bids = expand_dataframe(df_bids, max_depth=10, step=1, reverse=True, default_price=default_price - 1)

    ask_prices = df_asks['price'].tolist()

    ask_quantities = df_asks['amount'].tolist()
    bid_prices = df_bids['price'].tolist()

    bid_quantities = df_bids['amount'].tolist()

    # Interleave the lists using np.ravel and np.column_stack
    interleaved_array = np.ravel(np.column_stack((ask_prices, ask_quantities, bid_prices, bid_quantities)))
    interleaved_array = interleaved_array.astype(np.float64)
    return interleaved_array


def _append_combined_data_to_csv(combined_data, file_name):
    """ That's the OLD function for Lobster format. I keep it here for now but that all should be deeply rewritten"""
    try:
        csv_file_path = os.path.join(DATA_PATH, f"combined_{file_name}.csv")

        # Check if the file exists to decide if headers need to be written
        write_header = not os.path.exists(csv_file_path)

        with open(csv_file_path, 'a', newline='') as csvfile:
            lobster_message_fields = ['Trader type', 'Event Type', 'Order ID', 'Size', 'Price', 'Direction']

            # Adjust the book fields to interleave ask and bid data
            book_fields = []
            for i in range(1, 11):
                book_fields.extend([f"Ask_Price_{i}", f"Ask_Size_{i}", f"Bid_Price_{i}", f"Bid_Size_{i}"])

            header = ['Buffer Release Count', 'Original Timestamp', 'Buffer Release Timestamp',
                      'Parent Order ID'] + lobster_message_fields + book_fields  # Added 'Parent Order ID'

            writer = csv.writer(csvfile)

            # Write the header only if the file didn't exist
            if write_header:
                writer.writerow(header)

            # Write the data for each combined row
            for row in combined_data:
                buffer_release_count = row.get('buffer_release_count', 'N/A')
                original_timestamp = row.get('original_timestamp', 'N/A')
                buffer_release_timestamp = row.get('buffer_release_timestamp', 'N/A')
                parent_order_id = row.get('parent_id', '')  # Retrieve parent_order_id

                lobster_message = [row['message'][field] for field in lobster_message_fields]

                # Process the book record to match the header structure
                book_record = row['book_record']
                interleaved_book_record = []
                for i in range(0, len(book_record), 4):
                    interleaved_book_record.extend(book_record[i:i + 4])

                writer.writerow([buffer_release_count, original_timestamp, buffer_release_timestamp, parent_order_id
                                 ] + lobster_message + interleaved_book_record)
    except Exception as e:
        logger.critical(f"Error writing to CSV: {e}")


async def append_combined_data_to_csv(combined_data, file_name):
    """ That's the OLD function for Lobster format. I keep it here for now but that all should be deeply rewritten"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _append_combined_data_to_csv, combined_data, file_name)


def convert_active_orders_to_lobster_format(active_orders, levels_n=10):
    """ That's the OLD function for Lobster format. I keep it here for now but that all should be deeply rewritten"""
    # Create a DataFrame from the active orders
    df = pd.DataFrame(active_orders)

    # Separate bids and asks
    df_bids = df[df['order_type'] == 1]  # Assuming 1 for bids based on the IntEnum
    df_asks = df[df['order_type'] == -1]  # Assuming -1 for asks based on the IntEnum

    # Sort bids and asks
    df_bids = df_bids.sort_values(by=['price', 'timestamp'], ascending=[False, True])
    df_asks = df_asks.sort_values(by=['price', 'timestamp'], ascending=[True, True])

    # Take the top 'levels_n' levels
    df_bids = df_bids.head(levels_n)
    df_asks = df_asks.head(levels_n)

    # Create the LOBSTER format DataFrame
    lobster_columns = []
    for i in range(1, levels_n + 1):
        lobster_columns.extend([f'Ask Price {i}', f'Ask Size {i}', f'Bid Price {i}', f'Bid Size {i}'])

    df_lobster = pd.DataFrame(columns=lobster_columns)

    for i in range(levels_n):
        ask_price = df_asks['price'].iloc[i] if i < len(df_asks) else None
        ask_size = df_asks['amount'].iloc[i] if i < len(df_asks) else None
        bid_price = df_bids['price'].iloc[i] if i < len(df_bids) else None
        bid_size = df_bids['amount'].iloc[i] if i < len(df_bids) else None

        df_lobster.loc[0, f'Ask Price {i + 1}'] = ask_price
        df_lobster.loc[0, f'Ask Size {i + 1}'] = ask_size
        df_lobster.loc[0, f'Bid Price {i + 1}'] = bid_price
        df_lobster.loc[0, f'Bid Size {i + 1}'] = bid_size

    return df_lobster


def _append_order_books_to_csv(order_books, file_name):
    """ That's the OLD function for Lobster format. I keep it here for now but that all should be deeply rewritten"""
    csv_file_path = os.path.join(DATA_PATH, f"book_{file_name}.csv")

    # Check if the file exists to decide if headers need to be written
    write_header = not os.path.exists(csv_file_path)

    with open(csv_file_path, 'a', newline='') as csvfile:
        # Assume all order books have the same format, so use the first one to prepare header
        first_order_book = order_books[0][0]  # First element is the order book, second is the timestamp
        header = ["Timestamp"]
        for i in range(1, (len(first_order_book) // 4) + 1):
            header.extend([f"Ask_Price_{i}", f"Ask_Size_{i}", f"Bid_Price_{i}", f"Bid_Size_{i}"])

        writer = csv.writer(csvfile)

        # Write the header only if the file didn't exist
        if write_header:
            writer.writerow(header)

        # Write the book data with timestamp as a separate column for each record
        for order_book, timestamp in order_books:
            writer.writerow([timestamp] + list(order_book))


def _append_lobster_messages_to_csv(lobster_msgs, file_name):
    """ That's the OLD function for Lobster format. I keep it here for now but that all should be deeply rewritten"""
    csv_file_path = os.path.join(DATA_PATH, f"messages_{file_name}.csv")

    # Define the header (column names) for the LOBSTER-formatted CSV file
    fieldnames = ['Trader type', 'Time', 'Event Type', 'Order ID', 'Size', 'Price', 'Direction']

    # Check if the file exists to decide if headers need to be written
    write_header = not os.path.exists(csv_file_path)

    with open(csv_file_path, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Write the header only if the file didn't exist
        if write_header:
            writer.writeheader()

        # Write the data for each message
        for lobster_msg in lobster_msgs:
            writer.writerow(lobster_msg)


async def append_order_books_to_csv(order_books, file_name):
    """ That's the OLD function for Lobster format. I keep it here for now but that all should be deeply rewritten"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _append_order_books_to_csv, order_books, file_name)


async def append_lobster_messages_to_csv(lobster_msgs, file_name):
    """ That's the OLD function for Lobster format. I keep it here for now but that all should be deeply rewritten"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _append_lobster_messages_to_csv, lobster_msgs, file_name)


def create_lobster_message(order_dict, event_type: LobsterEventType, trader_type: int, timestamp: datetime):
    """ That's the OLD function for Lobster format. I keep it here for now but that all should be deeply rewritten"""
    """Creates a LOBSTER-formatted message dictionary."""

    lobster_message = {
        'Trader type': trader_type,
        'Time': timestamp.timestamp(),
        'Event Type': event_type,
        'Order ID': order_dict['id'],
        'Size': order_dict['amount'],
        'Price': order_dict['price'] * LOBSTER_MONEY_CONSTANT,
        'Direction': order_dict['order_type']  # Convert the string to its enum value
    }

    return lobster_message


def convert_to_noise_state(active_orders: List[Dict]) -> Dict:
    noise_state = {
        'outstanding_orders': {
            'bid': defaultdict(int),
            'ask': defaultdict(int)
        }
    }

    for order in active_orders:
        if order['status'] == 'active':
            order_type_value = order['order_type']
            order_type = OrderType(order_type_value).name.lower()

            price = order['price']
            amount = order['amount']
            noise_state['outstanding_orders'][order_type][price] += amount

    # Convert defaultdicts to regular dicts for easier use later
    noise_state['outstanding_orders']['bid'] = dict(noise_state['outstanding_orders']['bid'])
    noise_state['outstanding_orders']['ask'] = dict(noise_state['outstanding_orders']['ask'])

    return noise_state


def convert_to_trader_actions(response_dict):
    actions = []

    for order_type, order_details in response_dict.items():
        for price, size_list in order_details.items():
            size = size_list[0]
            action = {}
            if size > 0:
                action['action_type'] = ActionType.POST_NEW_ORDER.value
                action['order_type'] = order_type
                action['price'] = price
                action['amount'] = size
            elif size < 0:
                action['action_type'] = ActionType.CANCEL_ORDER.value
                action['order_type'] = order_type
                action['price'] = price
            if action:
                actions.append(action)

    return actions


def generate_file_name(session_uuid, file_type, extension='csv'):
    """
    Generate a filename for the given file type and session UUID.
    """
    # Format the current date and time to a string
    date_str = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    # Generate the filename
    file_name = f"{file_type}_{session_uuid}_{date_str}.{extension}"
    # Return the filename prefixed with the "data/" directory
    return f"{DATA_PATH}/{file_name}"
