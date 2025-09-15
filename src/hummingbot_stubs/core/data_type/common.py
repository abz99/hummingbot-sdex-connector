from enum import Enum
from typing import NamedTuple, Optional
from decimal import Decimal


class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    LIMIT_MAKER = "LIMIT_MAKER"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"


class TradeType(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    PENDING_CREATE = "PENDING_CREATE"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    PENDING_CANCEL = "PENDING_CANCEL"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    BOTH = "BOTH"


class PositionMode(Enum):
    HEDGE = "HEDGE"
    ONEWAY = "ONEWAY"


class ConnectorStatus(Enum):
    """Connector status enumeration."""
    NOT_CONNECTED = "NOT_CONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"


class TradeFee(NamedTuple):
    """Represents trading fees."""
    percent: Decimal
    percent_token: str
    flat_fees: Optional[Decimal] = None


class TokenAmount(NamedTuple):
    """Represents an amount of a token."""
    token: str
    amount: Decimal


class PriceSize(NamedTuple):
    """Represents a price and size pair."""
    price: Decimal
    size: Decimal
