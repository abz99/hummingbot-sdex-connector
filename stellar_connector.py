"""
Hummingbot Stellar Exchange Connector
Main connector implementation for Hummingbot integration
"""

import asyncio
import time
from decimal import Decimal
from typing import Dict, List, Optional, Any
from hummingbot.connector.exchange_base import ExchangeBase
from hummingbot.connector.trading_rule import TradingRule
from hummingbot.core.data_type.order_book import OrderBook
from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.core.event.events import MarketEvent, AccountEvent
import logging


class StellarExchange(ExchangeBase):
    """Hummingbot exchange connector for Stellar DEX"""

    def __init__(
        self,
        stellar_secret_key: str,
        stellar_network: str = "testnet",
        trading_pairs: List[str] = None,
        trading_required: bool = True,
        **kwargs,
    ):
        self._stellar_secret_key = stellar_secret_key
        self._stellar_network = stellar_network

        # Initialize secure components
        from stellar_security import SecureKeyManager, SecurityConfig
        from stellar_chain_interface import StellarChainInterface, StellarNetworkConfig
        from stellar_order_manager import StellarOrderManager

        self._security_config = SecurityConfig()
        self._key_manager = SecureKeyManager(self._security_config)
        self._wallet_address = None  # Will be set after key storage

        # Stellar-specific components
        network_config = StellarNetworkConfig.get_config(stellar_network)
        self._chain_interface = StellarChainInterface(network_config)
        self._chain_interface.key_manager = self._key_manager

        # Order and market data management
        self._order_manager = None  # Initialized after wallet setup
        self._path_payment_engine = None
        self._pool_manager = None

        # Tracking components
        self._order_book_tracker: Optional[StellarOrderBookTracker] = None
        self._user_stream_tracker: Optional[StellarUserStreamTracker] = None

        # Performance components
        self._cache_manager = None
        self._connection_manager = None

        super().__init__(trading_pairs, trading_required, **kwargs)

    @property
    def name(self) -> str:
        return "stellar"

    @property
    def order_books(self) -> Dict[str, OrderBook]:
        return self._order_book_tracker.order_books if self._order_book_tracker else {}

    @property
    def trading_rules(self) -> Dict[str, TradingRule]:
        return self._trading_rules

    @property
    def in_flight_orders(self) -> Dict[str, Any]:
        return self._order_manager.in_flight_orders if self._order_manager else {}

    @property
    def status_dict(self) -> Dict[str, bool]:
        return {
            "account_balance": len(self._account_balances) > 0,
            "trading_rule_initialized": len(self._trading_rules) > 0,
            "order_books_initialized": (
                self._order_book_tracker.ready if self._order_book_tracker else False
            ),
            "user_stream_initialized": (
                self._user_stream_tracker.ready if self._user_stream_tracker else False
            ),
            "stellar_connection": self._chain_interface.is_connected,
            "wallet_initialized": self._wallet_address is not None,
        }

    @property
    def ready(self) -> bool:
        """Check if connector is ready for trading"""
        return all(self.status_dict.values())

    async def start_network(self) -> None:
        """Start network connections and data streams"""

        # Initialize wallet
        self._wallet_address = await self._key_manager.store_key(self._stellar_secret_key)

        # Initialize remaining components
        self._order_manager = StellarOrderManager(self._chain_interface, self._wallet_address)

        # Initialize Stellar connection
        await self._chain_interface.connect()

        # Start order book tracking
        if self._trading_pairs:
            self._order_book_tracker = StellarOrderBookTracker(
                self._chain_interface, self._trading_pairs
            )
            await self._order_book_tracker.start()

        # Start user stream tracking
        self._user_stream_tracker = StellarUserStreamTracker(
            self._chain_interface, self._wallet_address
        )
        await self._user_stream_tracker.start()

        # Initialize trading rules
        await self._update_trading_rules()

        # Update account balances
        await self._update_balances()

    async def stop_network(self) -> None:
        """Clean shutdown of network connections"""

        if self._order_book_tracker:
            await self._order_book_tracker.stop()

        if self._user_stream_tracker:
            await self._user_stream_tracker.stop()

        await self._chain_interface.disconnect()

    # Hummingbot interface methods

    async def create_order(
        self,
        trade_type: TradeType,
        order_id: str,
        trading_pair: str,
        amount: Decimal,
        order_type: OrderType,
        price: Decimal,
        **kwargs,
    ) -> str:
        """Create order (Hummingbot interface)"""

        if not self._order_manager:
            raise RuntimeError("Order manager not initialized")

        return await self._order_manager.create_order(
            trading_pair=trading_pair,
            order_type=order_type,
            trade_type=trade_type,
            amount=amount,
            price=price,
        )

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order (Hummingbot interface)"""

        if not self._order_manager:
            raise RuntimeError("Order manager not initialized")

        return await self._order_manager.cancel_order(order_id)

    async def get_order_book(self, trading_pair: str) -> OrderBook:
        """Get order book for trading pair"""

        if not self._order_book_tracker:
            raise RuntimeError("Order book tracker not initialized")

        return self._order_book_tracker.order_books.get(trading_pair)

    async def _update_trading_rules(self) -> None:
        """Update trading rules for all trading pairs"""

        if not self._trading_pairs:
            return

        for trading_pair in self._trading_pairs:
            rule = await self._create_trading_rule(trading_pair)
            self._trading_rules[trading_pair] = rule

    async def _create_trading_rule(self, trading_pair: str) -> TradingRule:
        """Create trading rule for specific pair"""

        base_asset, quote_asset = await self._order_manager.parse_trading_pair(trading_pair)

        # Stellar-specific trading constraints
        return TradingRule(
            trading_pair=trading_pair,
            min_order_size=Decimal("0.0000001"),  # 7 decimal precision
            max_order_size=Decimal("100000000"),  # Practical maximum
            min_price_increment=Decimal("0.0000001"),
            min_base_amount_increment=Decimal("0.0000001"),
            min_quote_amount_increment=Decimal("0.0000001"),
            min_notional_size=Decimal("1.0"),  # Minimum 1 XLM notional
            supports_limit_orders=True,
            supports_market_orders=False,  # Stellar doesn't have native market orders
            supports_stop_limit_orders=False,
        )

    async def _update_balances(self) -> None:
        """Update account balances"""

        try:
            account = await self._chain_interface.load_account(self._wallet_address)
            balances = {}

            for balance in account.balances:
                if balance.asset_type == "native":
                    symbol = "XLM"
                else:
                    symbol = balance.asset_code

                # Calculate available balance considering reserves
                if symbol == "XLM":
                    min_balance = (
                        self._chain_interface.reserve_calculator.calculate_minimum_balance(account)
                    )
                    available = max(Decimal("0"), Decimal(balance.balance) - min_balance)
                else:
                    available = Decimal(balance.balance)

                balances[symbol] = {"total": Decimal(balance.balance), "available": available}

            self._account_balances = balances

        except Exception as e:
            self.logger.error(f"Balance update failed: {e}")


class StellarOrderBookTracker:
    """Track Stellar order books with real-time updates"""

    def __init__(self, chain_interface, trading_pairs: List[str]):
        self.chain = chain_interface
        self.trading_pairs = trading_pairs
        self.order_books: Dict[str, OrderBook] = {}
        self.active_streams: Dict[str, Any] = {}
        self._ready = False
        self.logger = logging.getLogger(__name__)

    @property
    def ready(self) -> bool:
        return self._ready and len(self.order_books) == len(self.trading_pairs)

    async def start(self) -> None:
        """Start tracking order books for all trading pairs"""

        for trading_pair in self.trading_pairs:
            await self.start_tracking_pair(trading_pair)

        self._ready = True

    async def stop(self) -> None:
        """Stop all order book tracking"""

        for stream in self.active_streams.values():
            if hasattr(stream, "close"):
                stream.close()

        self.active_streams.clear()
        self._ready = False

    async def start_tracking_pair(self, trading_pair: str) -> None:
        """Start tracking specific trading pair"""

        base_asset, quote_asset = await self.parse_trading_pair(trading_pair)

        try:
            # Get initial order book snapshot
            orderbook_data = await self.chain.server.orderbook(
                selling=base_asset, buying=quote_asset
            ).call()

            # Convert to Hummingbot format
            order_book = OrderBook()
            self.update_order_book_from_stellar_data(order_book, orderbook_data)

            self.order_books[trading_pair] = order_book

            # Start streaming updates
            stream = self.chain.server.orderbook(selling=base_asset, buying=quote_asset).stream(
                on_message=lambda data: self.handle_order_book_stream_update(trading_pair, data),
                on_error=lambda error: self.handle_stream_error(trading_pair, error),
            )

            self.active_streams[trading_pair] = stream

        except Exception as e:
            self.logger.error(f"Failed to start tracking {trading_pair}: {e}")
            raise

    def update_order_book_from_stellar_data(
        self, order_book: OrderBook, stellar_data: Dict
    ) -> None:
        """Update order book with Stellar data"""

        from hummingbot.core.data_type.order_book_row import OrderBookRow

        # Process bids
        bids = []
        for bid in stellar_data.get("bids", []):
            bids.append(
                OrderBookRow(
                    price=Decimal(bid["price"]),
                    amount=Decimal(bid["amount"]),
                    update_id=int(time.time() * 1000),
                )
            )

        # Process asks
        asks = []
        for ask in stellar_data.get("asks", []):
            asks.append(
                OrderBookRow(
                    price=Decimal(ask["price"]),
                    amount=Decimal(ask["amount"]),
                    update_id=int(time.time() * 1000),
                )
            )

        # Apply updates (Stellar sends complete snapshots)
        order_book.apply_snapshot(bids, asks, int(time.time() * 1000))

    async def parse_trading_pair(self, trading_pair: str):
        """Parse trading pair string into Stellar Asset objects"""

        base_symbol, quote_symbol = trading_pair.split("-")

        # This would use the order manager's asset resolution
        # Simplified for now
        from stellar_sdk import Asset

        base_asset = Asset.native() if base_symbol == "XLM" else Asset(base_symbol, "ISSUER")
        quote_asset = Asset.native() if quote_symbol == "XLM" else Asset(quote_symbol, "ISSUER")

        return base_asset, quote_asset

    def handle_order_book_stream_update(self, trading_pair: str, data: Dict) -> None:
        """Handle real-time order book updates"""

        if trading_pair not in self.order_books:
            return

        try:
            order_book = self.order_books[trading_pair]
            self.update_order_book_from_stellar_data(order_book, data)

            # Emit update event
            self.trigger_event(
                MarketEvent.OrderBookEvent,
                {"trading_pair": trading_pair, "timestamp": time.time(), "connector": "stellar"},
            )

        except Exception as e:
            self.logger.error(f"Order book update failed for {trading_pair}: {e}")

    def handle_stream_error(self, trading_pair: str, error: Exception) -> None:
        """Handle streaming errors"""

        self.logger.error(f"Stream error for {trading_pair}: {error}")

        # Attempt to reconnect after delay
        asyncio.create_task(self.reconnect_stream(trading_pair))

    async def reconnect_stream(self, trading_pair: str) -> None:
        """Reconnect failed stream after delay"""

        await asyncio.sleep(5)  # Wait 5 seconds before reconnecting

        try:
            await self.start_tracking_pair(trading_pair)
            self.logger.info(f"Successfully reconnected stream for {trading_pair}")
        except Exception as e:
            self.logger.error(f"Failed to reconnect stream for {trading_pair}: {e}")


class StellarUserStreamTracker:
    """Track account-specific events from Stellar network"""

    def __init__(self, chain_interface, wallet_address: str):
        self.chain = chain_interface
        self.wallet_address = wallet_address
        self.account_stream: Optional[Any] = None
        self.offer_stream: Optional[Any] = None
        self._ready = False
        self.logger = logging.getLogger(__name__)

    @property
    def ready(self) -> bool:
        return self._ready

    async def start(self) -> None:
        """Start tracking user account events"""

        # Start account balance/state tracking
        self.account_stream = (
            self.chain.server.accounts()
            .for_account(self.wallet_address)
            .stream(
                on_message=self.handle_account_update, on_error=self.handle_account_stream_error
            )
        )

        # Start offer tracking for order status updates
        self.offer_stream = (
            self.chain.server.offers()
            .for_account(self.wallet_address)
            .stream(on_message=self.handle_offer_update, on_error=self.handle_offer_stream_error)
        )

        self._ready = True

    async def stop(self) -> None:
        """Stop tracking account events"""

        if self.account_stream and hasattr(self.account_stream, "close"):
            self.account_stream.close()

        if self.offer_stream and hasattr(self.offer_stream, "close"):
            self.offer_stream.close()

        self._ready = False

    def handle_account_update(self, account_data: Dict) -> None:
        """Handle account balance and state updates"""

        try:
            # Extract balance information
            balances = {}
            for balance in account_data.get("balances", []):
                if balance["asset_type"] == "native":
                    symbol = "XLM"
                else:
                    symbol = balance["asset_code"]

                balances[symbol] = {
                    "available": Decimal(balance["balance"]),
                    "total": Decimal(balance["balance"]),
                }

            # Calculate actual available XLM considering reserves
            if "XLM" in balances:
                account = self.parse_account_data(account_data)
                min_balance = self.chain.reserve_calculator.calculate_minimum_balance(account)
                available_xlm = max(Decimal("0"), balances["XLM"]["available"] - min_balance)
                balances["XLM"]["available"] = available_xlm

            # Emit balance update event
            self.emit_balance_update(balances)

        except Exception as e:
            self.logger.error(f"Account update handling failed: {e}")

    def handle_offer_update(self, offer_data: Dict) -> None:
        """Handle offer status updates"""

        try:
            stellar_offer_id = offer_data["id"]

            # Find corresponding Hummingbot order
            hb_order_id = self.find_hummingbot_order_by_stellar_id(stellar_offer_id)

            if hb_order_id:
                # Convert Stellar offer status to Hummingbot order status
                if "amount" in offer_data and Decimal(offer_data["amount"]) == 0:
                    status = "FILLED"
                else:
                    status = "OPEN"

                # Emit order update event
                self.emit_order_update(hb_order_id, status, offer_data)

        except Exception as e:
            self.logger.error(f"Offer update handling failed: {e}")

    def parse_account_data(self, account_data: Dict):
        """Parse account data from Stellar response"""

        # This would parse the account data structure
        # Simplified implementation
        class MockAccount:
            def __init__(self, data):
                self.balances = data.get("balances", [])
                self.subentry_count = data.get("subentry_count", 0)
                self.data = data.get("data", {})
                self.signers = data.get("signers", [])
                self.account_id = data.get("account_id", "")

        return MockAccount(account_data)

    def emit_balance_update(self, balances: Dict[str, Dict]) -> None:
        """Emit balance update event to Hummingbot"""

        # This would emit proper Hummingbot events
        # Implementation depends on Hummingbot event system
        pass

    def emit_order_update(self, order_id: str, status: str, stellar_data: Dict) -> None:
        """Emit order update event to Hummingbot"""

        # This would emit proper Hummingbot order update events
        # Implementation depends on Hummingbot event system
        pass

    def find_hummingbot_order_by_stellar_id(self, stellar_offer_id: str) -> Optional[str]:
        """Find Hummingbot order ID by Stellar offer ID"""

        # This would search through tracked orders to find matching Stellar offer ID
        # Implementation depends on order tracking system
        return None
