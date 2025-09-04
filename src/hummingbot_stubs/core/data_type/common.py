from enum import Enum


class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class TradeType(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    OPEN = "OPEN"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
