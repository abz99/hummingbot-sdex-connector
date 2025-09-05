from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from decimal import Decimal


class ExchangeBase(ABC):
    def __init__(self, trading_pairs: Optional[List[str]] = None, **kwargs: Any) -> None:
        self._trading_pairs = trading_pairs or []
        self._account_balances: Dict[str, Decimal] = {}

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    def order_books(self) -> Dict[str, Any]:
        return {}

    @property
    def trading_rules(self) -> Dict[str, Any]:
        return {}

    @property
    def in_flight_orders(self) -> Dict[str, Any]:
        return {}

    @property
    def status_dict(self) -> Dict[str, bool]:
        return {"ready": True}

    @property
    def ready(self) -> bool:
        return True

    @abstractmethod
    async def start_network(self) -> None:
        pass

    @abstractmethod
    async def stop_network(self) -> None:
        pass
