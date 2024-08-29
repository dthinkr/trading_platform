import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from enum import Enum, IntEnum
from typing import Optional
from uuid import UUID, uuid4

from mongoengine import (
    BooleanField,
    DateTimeField,
    DictField,
    Document,
    FloatField,
    IntField,
    ListField,
    UUIDField,
    StringField,
)
from pydantic import BaseModel, ConfigDict, Field


class StrEnum(str, Enum):
    pass


def now():
    """It is actually from utils.py but we need structures there so we do it here to avoid circular deps"""
    return datetime.now(timezone.utc)


GOALS = [-10, 0, 10]  # for now let's try a naive hardcoded approach to the goals

executor = ThreadPoolExecutor()


class TradeDirection(str, Enum):
    BUY = "buy"
    SELL = "sell"


class TraderCreationData(BaseModel):
    num_human_traders: int = Field(
        default=6,
        title="Number of Human Traders",
        description="model_parameter",
        ge=0,
    )
    num_noise_traders: int = Field(
        default=1,
        title="Number of Noise Traders",
        description="model_parameter",
        ge=0,
    )
    num_informed_traders: int = Field(
        default=1,
        title="Number of Informed Traders",
        description="model_parameter",
        ge=0,
    )
    num_simple_order_traders: int = Field(
        default=0,
        title="Number of Simple Order Traders",
        description="model_parameter",
        ge=0,
    )
    start_of_book_num_order_per_level: int = Field(
        default=5,
        title="Orders per Level at Book Start",
        description="model_parameter",
        ge=0,
    )
    trading_day_duration: int = Field(
        default=1,
        title="Trading Day Duration",
        description="model_parameter",
        gt=0,
    )
    step: int = Field(
        default=1,
        title="Step for New Orders",
        description="model_parameter",
    )
    noise_activity_frequency: float = Field(
        default=1.0,
        title="Activity Frequency",
        description="noise_parameter",
        gt=0,
    )
    max_order_amount: int = Field(
        default=9,
        title="Order Amount",
        description="noise_parameter",
    )
    noise_passive_probability: float = Field(
        default=0.7,
        title="Passive Order Probability",
        description="noise_parameter",
    )
    noise_cancel_probability: float = Field(
        default=0.1,
        title="Cancel Order Probability",
        description="noise_parameter",
    )
    noise_bid_probability: float = Field(
        default=0.5,
        title="Bid Order Probability",
        description="noise_parameter",
    )
    informed_trade_intensity: float = Field(
        default=0.4,
        title="Trade Intensity",
        description="informed_parameter",
    )
    informed_urgency_factor: float = Field(
        default=3,
        title="Urgency Factor",
        description="informed_parameter",
    )
    informed_trade_direction: TradeDirection = Field(
        default=TradeDirection.SELL,
        title="Trade Direction",
        description="informed_parameter",
    )
    informed_edge: int = Field(
        default=2,
        title="Informed Edge",
        description="informed_parameter",
    )
    informed_order_book_levels: int = Field(
        default=3,
        title="Informed Order Book Levels",
        description="informed_parameter",
    )
    informed_order_book_depth: int = Field(
        default=10,
        title="Informed Order Book Depth",
        description="informed_parameter",
    )
    initial_cash: float = Field(
        default=100000,
        title="Initial Cash",
        description="human_parameter",
    )
    initial_stocks: int = Field(
        default=100,
        title="Initial Stocks",
        description="human_parameter",
    )
    depth_book_shown: int = Field(
        default=4,
        title="Depth Book Shown",
        description="human_parameter",
    )
    order_book_levels: int = Field(
        default=5,
        title="Order Book Levels",
        description="model_parameter",
    )
    default_price: int = Field(
        default=2000,
        title="Default Price",
        description="model_parameter",
    )

    num_rounds: int = Field(
        default=3,
        title="Number of Rounds (Placeholder, not used yet)",
        description="human_parameter",
        ge=0,
    )
    conversion_rate: float = Field(
        default=42.52,
        title="Lira-GBP Conversion Rate",
        description="model_parameter",
        gt=0,
    )
    cancel_time: int = Field(
        default=1,
        title="Seconds Locked Until Cancelation (Placeholder, not used yet)",
        description="human_parameter",
        gt=0,
    )

    def dump_params_by_description(self) -> dict:
        """Dump parameters into a dict of dict indexed by description."""
        result = {}
        for field_name, field_info in self.model_fields.items():
            description = field_info.description
            if description not in result:
                result[description] = {}
            result[description][field_name] = getattr(self, field_name)
        return result


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
    POST_NEW_ORDER = "add_order"
    CANCEL_ORDER = "cancel_order"
    UPDATE_BOOK_STATUS = "update_book_status"
    REGISTER = "register_me"


class OrderType(IntEnum):
    ASK = -1  # the price a seller is willing to accept for a security
    BID = 1  # the price a buyer is willing to pay for a security


# let's write an inverse correspondence between the order type and the string
str_to_order_type = {"ask": OrderType.ASK, "bid": OrderType.BID}


class OrderStatus(str, Enum):
    BUFFERED = "buffered"
    ACTIVE = "active"
    EXECUTED = "executed"
    CANCELLED = "cancelled"


class TraderType(str, Enum):
    NOISE = "NOISE"
    MARKET_MAKER = "MARKET_MAKER"
    INFORMED = "INFORMED"
    HUMAN = "HUMAN"
    INITIAL_ORDER_BOOK = "INITIAL_ORDER_BOOK"
    SIMPLE_ORDER = "SIMPLE_ORDER"


class Order(BaseModel):
    id: Optional[str] = None  # Make id optional
    status: OrderStatus
    amount: float = 1
    price: float
    order_type: OrderType
    timestamp: datetime = Field(default_factory=now)
    session_id: str
    trader_id: str

    class ConfigDict:
        use_enum_values = True


class TransactionModel(Document):
    id = UUIDField(primary_key=True, default=uuid.uuid4, binary=False)
    trading_session_id = StringField(required=True)
    bid_order_id = StringField(required=False)
    ask_order_id = StringField(required=False)
    timestamp = DateTimeField(default=datetime.now)
    price = FloatField(required=True)

    async def save_async(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(executor, self.save)


class Message(Document):
    trading_session_id = UUIDField(required=True, binary=False)
    content = DictField(required=True)
    timestamp = DateTimeField(default=datetime.now)
    matched_orders = DictField(required=False)
