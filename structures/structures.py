from enum import Enum, IntEnum, StrEnum
from pydantic import BaseModel
from pydantic.fields import Field
from datetime import datetime
import uuid

class TraderCreationData(BaseModel):
    max_short_shares: int = Field(default=100, description="Maximum number of shares for shorting")
    max_short_cash: float = Field(default=10000.0, description="Maximum amount of cash for shorting")
    initial_cash: float = Field(default=1000.0, description="Initial amount of cash")
    initial_shares: int = Field(default=0, description="Initial amount of shares")
    trading_day_duration: int = Field(default=5, description="Duration of the trading day in minutes")
    max_active_orders: int = Field(default=5, description="Maximum amount of active orders")
    noise_trader_update_freq: int = Field(default=10, description="Frequency of noise traders' updates in seconds")
    step: int = Field(default=100, description="Step for new orders")
    extra_info_treatment: bool = Field(default=False, description="Extra info treatment")
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


class OrderModel(BaseModel):
    # id: uuid.UUID
    id: uuid.UUID
    amount: float
    price: float
    status: OrderStatus
    order_type: OrderType  # ask or bid
    timestamp: datetime
    # session_id: uuid.UUID
    session_id: str  # FOR TESTING. REMOVE LATER
    trader_id: uuid.UUID


class TransactionModel(BaseModel):
    id: uuid.UUID
    bid_order_id: uuid.UUID
    ask_order_id: uuid.UUID
    timestamp: datetime
    price: float

class TraderManagerParams(BaseModel):
    n_noise_traders: int = 1  # Default value if not provided
    n_human_traders: int = 1  # Default value if not provided
    activity_frequency: float = .3 # Default value if not provided in seconds
