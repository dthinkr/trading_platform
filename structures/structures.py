from enum import Enum, IntEnum, StrEnum
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone
import uuid
def now():
    """It is actually from utils.py but we need structures there so we do it here to avoid circular deps"""
    return datetime.now(timezone.utc)

class TraderCreationData(BaseModel):
    num_human_traders: int = Field(default=1, description="Number of human traders")
    num_noise_traders: int = Field(default=1, description="Number of noise traders")
    activity_frequency: float = Field(default=0.3, description="Frequency of noise traders' updates in seconds")
    trading_day_duration: int = Field(default=5, description="Duration of the trading day in minutes")
    step: int = Field(default=100, description="Step for new orders")


    class Config:
        json_schema_extra = {
            "example": {
                "max_short_shares": 100,
                "max_short_cash": 10000.0,
                "initial_cash": 1000.0,
                "initial_shares": 0,
                "trading_day_duration": 5,  # Representing 8 hours in minutes
                "max_active_orders": 5,
                "noise_trader_update_freq": 10,  # in seconds,
                "step": 100,
                "extra_info_treatment": False
            }
        }


class LobsterEventType(IntEnum):
    """For the LOBSTER data, the event type is an integer. This class maps the integer to a string.
    See the documentation at: https://lobsterdata.com/info/DataStructure.php
    """
    NEW_LIMIT_ORDER = 1
    CANCELLATION_PARTIAL = 2
    CANCELLATION_TOTAL = 3
    EXECUTION_VISIBLE = 4
    EXECUTION_HIDDEN = 5
    CROSS_TRADE = 6
    TRADING_HALT = 7


class ActionType(str, Enum):
    POST_NEW_ORDER = 'add_order'
    CANCEL_ORDER = 'cancel_order'
    UPDATE_BOOK_STATUS = 'update_book_status'
    REGISTER = 'register_me'


class OrderType(IntEnum):
    ASK = -1  #  the price a seller is willing to accept for a security
    BID = 1  # the price a buyer is willing to pay for a security


class OrderStatus(str, Enum):
    BUFFERED = 'buffered'
    ACTIVE = 'active'
    EXECUTED = 'executed'
    CANCELLED = 'cancelled'


class TraderType(str, Enum):
    NOISE = 'NOISE'
    MARKET_MAKER = 'MARKET_MAKER'
    INFORMED = 'INFORMED'
    HUMAN = 'HUMAN'
    # Philipp: expand this list to include new trader types if needed


class Order(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    status: OrderStatus
    amount: float = 1  # Assuming amount is a float, adjust the type as needed
    price: float  # Same assumption as for amount
    order_type: OrderType
    timestamp: datetime = Field(default_factory=now)
    session_id: str
    trader_id: str

    class Config:
        use_enum_values = True  # This ensures that enum values are used in serialization

class TransactionModel(BaseModel):
    id: uuid.UUID
    bid_order_id: uuid.UUID
    ask_order_id: uuid.UUID
    timestamp: datetime
    price: float

class TraderManagerParams(BaseModel):
    n_noise_traders: int = 1  # Default value if not provided
    n_human_traders: int = 1  # Default value if not provided
    activity_frequency: float = 1.3 # Default value if not provided in seconds
    noise_warm_ups: int = 100  # Default value if not provided

ORDER_AMOUNT = 1

SIGMOID_PARAMS = {
    'params': (-0.1, 0.1, 3),
    'mu': (0.1, 0.3),
    'cap': 10
}