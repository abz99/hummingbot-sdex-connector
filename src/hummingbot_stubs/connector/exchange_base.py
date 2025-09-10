from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Set
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime


class OrderType(Enum):
    """Order types supported by exchanges."""
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    LIMIT_MAKER = "LIMIT_MAKER"


class TradeType(Enum):
    """Trade direction."""
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class TradingRule:
    """Trading rules for a trading pair."""
    trading_pair: str
    min_order_size: Decimal
    max_order_size: Decimal
    min_price_increment: Decimal
    min_base_amount_increment: Decimal
    min_quote_amount_increment: Decimal
    min_notional_size: Decimal = Decimal("0")


@dataclass
class OrderBookRow:
    """Order book price level."""
    price: Decimal
    amount: Decimal
    update_id: int


class OrderBook:
    """Order book representation."""

    def __init__(self, trading_pair: str):
        self.trading_pair = trading_pair
        self.bids: List[OrderBookRow] = []
        self.asks: List[OrderBookRow] = []
        self.last_diff_uid: int = 0

    def get_best_bid(self) -> Optional[OrderBookRow]:
        return self.bids[0] if self.bids else None

    def get_best_ask(self) -> Optional[OrderBookRow]:
        return self.asks[0] if self.asks else None


class ExchangeBase(ABC):
    """Base class for Hummingbot exchange connectors."""

    def __init__(self, trading_pairs: Optional[List[str]] = None, **kwargs: Any) -> None:
        self._trading_pairs = trading_pairs or []
        self._account_balances: Dict[str, Decimal] = {}
        self._trading_rules: Dict[str, TradingRule] = {}
        self._order_books: Dict[str, OrderBook] = {}
        self._in_flight_orders: Dict[str, Any] = {}
        self._last_timestamp = 0.0
        self._ready = False

    @property
    @abstractmethod
    def name(self) -> str:
        """Exchange connector name."""
        pass

    @property
    def order_books(self) -> Dict[str, OrderBook]:
        """Current order books."""
        return self._order_books

    @property
    def trading_rules(self) -> Dict[str, TradingRule]:
        """Trading rules for each pair."""
        return self._trading_rules

    @property
    def in_flight_orders(self) -> Dict[str, Any]:
        """Orders currently being processed."""
        return self._in_flight_orders

    @property
    def status_dict(self) -> Dict[str, bool]:
        """Connector status indicators."""
        return {
            "ready": self._ready,
            "network_connected": self._ready,
            "account_balance": len(self._account_balances) > 0,
            "trading_rule_initialized": len(self._trading_rules) > 0
        }

    @property
    def ready(self) -> bool:
        """Whether the connector is ready for trading."""
        return self._ready

    @property
    def trading_pairs(self) -> List[str]:
        """List of supported trading pairs."""
        return self._trading_pairs

    @abstractmethod
    def supported_order_types(self) -> List[OrderType]:
        """List of supported order types."""
        pass

    @abstractmethod
    async def start_network(self) -> None:
        """Start the connector's network connections."""
        pass

    @abstractmethod
    async def stop_network(self) -> None:
        """Stop the connector's network connections."""
        pass

    def get_balance(self, currency: str) -> Decimal:
        """Get balance for a specific currency."""
        return self._account_balances.get(currency, Decimal("0"))

    def get_available_balance(self, currency: str) -> Decimal:
        """Get available balance for trading."""
        return self.get_balance(currency)

    async def update_balances(self) -> None:
        """Update account balances from the exchange."""
        pass

    def current_timestamp(self) -> float:
        """Current timestamp in seconds."""
        return self._last_timestamp

    def tick(self, timestamp: float) -> None:
        """Update connector with current timestamp."""
        self._last_timestamp = timestamp
