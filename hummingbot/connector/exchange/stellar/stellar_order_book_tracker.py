"""
Stellar Order Book Tracker
Market data tracking and order book management.
"""

import asyncio
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

import aiohttp
from stellar_sdk import Asset

if TYPE_CHECKING:
    from .stellar_chain_interface import ModernStellarChainInterface
    from .stellar_observability import StellarObservabilityFramework


@dataclass
class OrderBookLevel:
    """Order book price level."""

    price: Decimal
    amount: Decimal
    timestamp: float


@dataclass
class StellarOrderBook:
    """Stellar order book data structure."""

    trading_pair: str
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    timestamp: float
    sequence: int = 0

    def get_best_bid(self) -> Optional[OrderBookLevel]:
        """Get best bid price."""
        return self.bids[0] if self.bids else None

    def get_best_ask(self) -> Optional[OrderBookLevel]:
        """Get best ask price."""
        return self.asks[0] if self.asks else None

    def get_spread(self) -> Optional[Decimal]:
        """Get bid-ask spread."""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()

        if best_bid and best_ask:
            return best_ask.price - best_bid.price
        return None

    def get_mid_price(self) -> Optional[Decimal]:
        """Get mid price between best bid and ask."""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()

        if best_bid and best_ask:
            return (best_bid.price + best_ask.price) / Decimal("2")
        return None


class StellarOrderBookTracker:
    """Market data tracking and order book management."""

    def __init__(
        self,
        chain_interface: "ModernStellarChainInterface",
        observability: "StellarObservabilityFramework",
    ) -> None:
        self.chain_interface = chain_interface
        self.observability = observability

        # Order book data
        self._order_books: Dict[str, StellarOrderBook] = {}
        self._tracked_pairs: set = set()

        # Streaming connections
        self._stream_sessions: Dict[str, aiohttp.ClientSession] = {}
        self._stream_tasks: Dict[str, asyncio.Task] = {}

        # Event handling
        self._update_handlers: List[Callable[[str, StellarOrderBook], None]] = []

        # Configuration
        self._update_interval = 1  # seconds
        self._max_depth = 20  # order book depth
        self._connected = False

        # Performance metrics
        self._last_update_times: Dict[str, float] = {}
        self._update_counts: Dict[str, int] = {}

    async def start(self):
        """Start order book tracker."""
        try:
            self._connected = True

            # Start tracking for existing pairs
            for trading_pair in self._tracked_pairs:
                await self._start_pair_tracking(trading_pair)

            await self.observability.log_event(
                "order_book_tracker_started", {"tracked_pairs": len(self._tracked_pairs)}
            )

        except Exception as e:
            await self.observability.log_error("order_book_tracker_start_failed", e)
            raise

    async def stop(self):
        """Stop order book tracker."""
        self._connected = False

        # Stop all tracking tasks
        for task in self._stream_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Close all sessions
        for session in self._stream_sessions.values():
            await session.close()

        self._stream_tasks.clear()
        self._stream_sessions.clear()

        await self.observability.log_event("order_book_tracker_stopped")

    async def add_trading_pair(self, trading_pair: str):
        """Add trading pair to track."""
        if trading_pair in self._tracked_pairs:
            return

        self._tracked_pairs.add(trading_pair)

        # Initialize empty order book
        self._order_books[trading_pair] = StellarOrderBook(
            trading_pair=trading_pair, bids=[], asks=[], timestamp=time.time()
        )

        # Start tracking if connected
        if self._connected:
            await self._start_pair_tracking(trading_pair)

        await self.observability.log_event(
            "trading_pair_added",
            {"trading_pair": trading_pair, "total_pairs": len(self._tracked_pairs)},
        )

    async def remove_trading_pair(self, trading_pair: str):
        """Remove trading pair from tracking."""
        if trading_pair not in self._tracked_pairs:
            return

        self._tracked_pairs.discard(trading_pair)

        # Stop tracking
        if trading_pair in self._stream_tasks:
            self._stream_tasks[trading_pair].cancel()
            del self._stream_tasks[trading_pair]

        if trading_pair in self._stream_sessions:
            await self._stream_sessions[trading_pair].close()
            del self._stream_sessions[trading_pair]

        # Remove order book data
        if trading_pair in self._order_books:
            del self._order_books[trading_pair]

        await self.observability.log_event(
            "trading_pair_removed",
            {"trading_pair": trading_pair, "total_pairs": len(self._tracked_pairs)},
        )

    def get_order_book(self, trading_pair: str) -> Optional[StellarOrderBook]:
        """Get current order book for trading pair."""
        return self._order_books.get(trading_pair)

    def get_all_order_books(self) -> Dict[str, StellarOrderBook]:
        """Get all tracked order books."""
        return self._order_books.copy()

    def add_update_handler(self, handler: Callable[[str, StellarOrderBook], None]) -> None:
        """Add order book update handler."""
        self._update_handlers.append(handler)

    def remove_update_handler(self, handler: Callable[[str, StellarOrderBook], None]):
        """Remove order book update handler."""
        if handler in self._update_handlers:
            self._update_handlers.remove(handler)

    async def _start_pair_tracking(self, trading_pair: str):
        """Start tracking for a specific trading pair."""
        if trading_pair in self._stream_tasks:
            return

        # Create session for this pair
        session = aiohttp.ClientSession()
        self._stream_sessions[trading_pair] = session

        # Start tracking task
        task = asyncio.create_task(self._track_pair_orderbook(trading_pair, session))
        self._stream_tasks[trading_pair] = task

    async def _track_pair_orderbook(self, trading_pair: str, session: aiohttp.ClientSession):
        """Track order book for a specific trading pair."""
        while self._connected:
            try:
                # Fetch order book data from Horizon API
                order_book = await self._fetch_order_book(trading_pair, session)

                if order_book:
                    # Update stored order book
                    self._order_books[trading_pair] = order_book
                    self._last_update_times[trading_pair] = time.time()
                    self._update_counts[trading_pair] = self._update_counts.get(trading_pair, 0) + 1

                    # Notify handlers
                    for handler in self._update_handlers:
                        try:
                            await handler(trading_pair, order_book)
                        except Exception as e:
                            await self.observability.log_error(
                                "order_book_handler_error",
                                e,
                                {"trading_pair": trading_pair, "handler": str(handler)},
                            )

                await asyncio.sleep(self._update_interval)

            except Exception as e:
                await self.observability.log_error(
                    "order_book_tracking_error", e, {"trading_pair": trading_pair}
                )
                await asyncio.sleep(5)  # Back off on errors

    async def _fetch_order_book(
        self, trading_pair: str, session: aiohttp.ClientSession
    ) -> Optional[StellarOrderBook]:
        """Fetch order book data from Horizon API."""
        try:
            # Parse trading pair to get assets
            # In real implementation, this would properly parse the trading pair
            # For now, this is a simplified stub

            horizon_url = self.chain_interface.config.horizon_urls[0]

            # Build order book URL (simplified)
            # Real implementation would construct proper Stellar asset pairs
            url = f"{horizon_url}/order_book"

            async with session.get(url, params={"limit": self._max_depth}) as response:

                if response.status == 200:
                    data = await response.json()

                    # Parse order book data (simplified implementation)
                    bids = []
                    asks = []

                    # In real implementation, parse actual Horizon API response
                    # For now, return empty order book

                    return StellarOrderBook(
                        trading_pair=trading_pair,
                        bids=bids,
                        asks=asks,
                        timestamp=time.time(),
                        sequence=data.get("sequence", 0),
                    )
                else:
                    await self.observability.log_error(
                        "order_book_fetch_failed",
                        Exception(f"HTTP {response.status}"),
                        {"trading_pair": trading_pair, "status": response.status},
                    )

        except Exception as e:
            await self.observability.log_error(
                "order_book_fetch_error", e, {"trading_pair": trading_pair}
            )

        return None

    def get_tracking_statistics(self) -> Dict[str, Any]:
        """Get order book tracking statistics."""
        return {
            "tracked_pairs": len(self._tracked_pairs),
            "active_streams": len(self._stream_tasks),
            "last_updates": self._last_update_times.copy(),
            "update_counts": self._update_counts.copy(),
            "connected": self._connected,
        }
