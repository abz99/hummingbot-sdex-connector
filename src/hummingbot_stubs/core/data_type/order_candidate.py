from decimal import Decimal
from dataclasses import dataclass
from .common import OrderType, TradeType


@dataclass
class OrderCandidate:
    trading_pair: str
    is_maker: bool
    order_type: OrderType
    order_side: TradeType
    amount: Decimal
    price: Decimal
