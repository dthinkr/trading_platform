import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from enum import Enum, IntEnum
from typing import Optional, List, Dict
from uuid import UUID, uuid4
import random
from pydantic import BaseModel, ConfigDict, Field, field_validator

class StrEnum(str, Enum):
    pass

class TradeDirection(str, Enum):
    BUY = "buy"
    SELL = "sell"

class User(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    username: str
    is_admin: bool = False

class Trader(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    gmail_username: str  # Change this from user_id to gmail_username
    trading_session_id: UUID
    is_ready: bool = False

class TradingPlatform(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    status: str = "waiting"
    traders: List[UUID] = []

class UserRegistration(BaseModel):
    username: str
    password: str


class TradingParameters(BaseModel):
    num_human_traders: int = Field(
        default=1,
        title="Number of Human Traders",
        description="model_parameter",
        ge=1,  # Changed from ge=0 to ge=1 to ensure at least one human trader
    )
    human_goal_amount: int = Field(
        default=10,
        title="Human Goal Amount",
        description="human_parameter",
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
        default=3,
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
        default=1,
        title="Activity Frequency",
        description="noise_parameter",
        gt=0,
    )
    max_order_amount: int = Field(
        default=1,
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
        default=0.52,
        title="Trade Intensity",
        description="informed_parameter",
    )
    # informed_urgency_factor: float = Field(
    #     default=0,
    #     title="Urgency Factor",
    #     description="informed_parameter",
    # )
    informed_trade_direction: TradeDirection = Field(
        default=TradeDirection.BUY,
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
        default=2,
        title="Informed Order Book Depth",
        description="informed_parameter",
    )
    initial_cash: float = Field(
        default=100000,
        title="Initial Cash",
        description="human_parameter",
    )
    initial_stocks: int = Field(
        default=300,
        title="Initial Stocks",
        description="human_parameter",
    )
    depth_book_shown: int = Field(
        default=5,
        title="Depth Book Shown",
        description="human_parameter",
    )
    order_book_levels: int = Field(
        default=5,
        title="Order Book Levels",
        description="model_parameter",
    )
    default_price: int = Field(
        default=100,
        title="Default Price",
        description="model_parameter",
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

    max_sessions_per_human: int = Field(
        default=4,
        title="Max Sessions per Human",
        description="human_parameter",
        ge=1,
    )

    google_form_id: str = Field(
        default='1yDf7vd5wLaPhm30IiGKTkPw4s5spb3Xlm86Li81YDXI',
        title="Google Form ID",
        description="model_parameter",
    )

    admin_users: List[str] = Field(
        default=['venvoooo', 'asancetta', 'marjonuzaj'],
        title="Admin Users",
        description="model_parameter",
    )

    human_goals: List[int] = Field(
        default_factory=list,
        title="Human Goals",
        description="human_parameter",
    )

    @field_validator('num_human_traders', 'human_goal_amount')
    def ensure_integer(cls, v):
        return max(int(v), 1)  # Ensure at least 1 human trader

    @field_validator('human_goals')
    def validate_human_goals(cls, v, info):
        num_traders = info.data.get('num_human_traders', 2)
        if len(v) != num_traders:
            # Only generate new goals if they haven't been set
            return cls.generate_human_goals(num_traders, info.data.get('human_goal_amount', 60))
        return v

    @staticmethod
    def generate_human_goals(num_traders: int, goal_amount: int) -> List[int]:
        """
        Generate human goals with exactly one informed trader and the rest as speculators.
        This is a fallback method - goals should typically be set explicitly based on user roles.
        """
        goals = [0] * num_traders  # Initialize all traders as speculators
        if num_traders > 0:
            # Randomly select one trader to be informed
            informed_index = random.randrange(num_traders)
            # Randomly assign positive or negative goal to the informed trader
            goals[informed_index] = random.choice([goal_amount, -goal_amount])
        return goals

    def dump_params_by_description(self) -> dict:
        """Dump parameters into a dict of dict indexed by description."""
        result = {}
        for field_name, field_info in self.model_fields.items():
            description = field_info.description
            if description not in result:
                result[description] = {}
            result[description][field_name] = getattr(self, field_name)
        return result

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @classmethod
    def create_with_persistent_settings(cls, base_params: dict, persistent_settings: dict):
        merged_params = {**base_params, **persistent_settings}
        # Ensure num_human_traders is at least 2
        merged_params['num_human_traders'] = max(merged_params.get('num_human_traders', 2), 2)
        return cls(**merged_params)

    @classmethod
    def from_dict(cls, data: dict):
        converted_data = {}
        for field, value in data.items():
            if field in cls.model_fields:
                field_info = cls.model_fields[field]
                try:
                    if isinstance(value, str):
                        if field_info.annotation == int:
                            converted_data[field] = int(value)
                        elif field_info.annotation == float:
                            converted_data[field] = float(value)
                        elif field_info.annotation == bool:
                            converted_data[field] = value.lower() in ('true', '1', 'yes')
                        elif field_info.annotation == List[int]:
                            converted_data[field] = [int(v.strip()) for v in value.split(',')]
                        else:
                            converted_data[field] = value
                    else:
                        converted_data[field] = value
                except ValueError as e:
                    print(f"Error converting {field}: {str(e)}")
                    converted_data[field] = value
        return cls(**converted_data)


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
    timestamp: datetime = Field(default_factory=datetime.now)
    session_id: str
    trader_id: str  # This will now contain the Gmail username
    informed_trader_progress: Optional[str] = None  # New field

    class ConfigDict:
        use_enum_values = True

executor = ThreadPoolExecutor()

class TransactionModel:
    def __init__(self, trading_session_id, bid_order_id, ask_order_id, price, informed_trader_progress=None):
        self.id = uuid.uuid4()
        self.trading_session_id = trading_session_id
        self.bid_order_id = bid_order_id
        self.ask_order_id = ask_order_id
        self.timestamp = datetime.now(timezone.utc)
        self.price = price
        self.informed_trader_progress = informed_trader_progress

    def to_dict(self):
        return {
            "id": str(self.id),
            "trading_session_id": self.trading_session_id,
            "bid_order_id": self.bid_order_id,
            "ask_order_id": self.ask_order_id,
            "timestamp": self.timestamp.isoformat(),
            "price": self.price,
            "informed_trader_progress": self.informed_trader_progress
        }

class Message:
    def __init__(self, trading_session_id: str, content: Dict, message_type: str = "BOOK_UPDATED"):
        self.id: UUID = uuid4()
        self.trading_session_id: str = trading_session_id
        self.content: Dict = content
        self.timestamp: datetime = datetime.now(timezone.utc)
        self.type: str = message_type

    def to_dict(self) -> Dict:
        return {
            "id": str(self.id),
            "trading_session_id": self.trading_session_id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "type": self.type
        }

