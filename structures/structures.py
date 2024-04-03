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
    num_human_traders: int = Field(
        default=1,
        title="Number of Human Traders",
        description="Number of human traders",
        ge=0 
    )
    num_noise_traders: int = Field(
        default=1,
        title="Number of Noise Traders",
        description="Number of noise traders",
        ge=0
    )
    num_informed_traders: int = Field(
        default=0,
        title="Number of Informed Traders",
        description="Number of informed traders",
        ge=0
    )
    activity_frequency: float = Field(
        default=1.0,
        title="Activity Frequency",
        description="Frequency of noise traders' updates in seconds",
        gt=0
    )
    trading_day_duration: int = Field(
        default=100,
        title="Trading Day Duration",
        description="Duration of the trading day in minutes",
        gt=0
    )
    step: int = Field(
        default=1,
        title="Step for New Orders",
        description="Step for new orders",
        gt=0
    )
    noise_warm_ups: int = Field(
        default=10,
        title="Noise Warm Ups",
        description="Number of warm up periods for noise traders",
        gt=0
    )
    initial_cash: float = Field(
        default=100000,
        title="Initial Cash",
        description="Initial cash for each trader",

    )
    initial_stocks: int = Field(
        default=100,
        title="Initial Stocks",
        description="Initial stocks for each trader",

    )
    depth_book_shown: int = Field(
        default=5,
        title="Depth Book Shown",
        description="Depth of the book shown to the human traders",

    )

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
    id: UUID = Field(default_factory=uuid4)
    bid_order_id: UUID
    ask_order_id: UUID
    timestamp: datetime = Field(default_factory=now)
    price: float


ORDER_AMOUNT = 1