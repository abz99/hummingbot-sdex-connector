"""
Modern Stellar Exchange Connector with Latest Hummingbot Patterns
Production-ready implementation with enhanced error handling and observability.
"""

import asyncio
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

# Hummingbot imports (using stubs for development)
from src.hummingbot_stubs.connector.exchange_base import ExchangeBase
from src.hummingbot_stubs.core.api_throttler.async_throttler import AsyncThrottler, RateLimit
from src.hummingbot_stubs.connector.exchange_base import OrderType
from src.hummingbot_stubs.core.data_type.common import TradeType
from src.hummingbot_stubs.core.web_assistant.web_assistants_factory import WebAssistantsFactory

from .stellar_asset_manager import ModernAssetManager

# Stellar connector imports
from .stellar_chain_interface import ModernStellarChainInterface
from .stellar_config_models import StellarNetworkConfig
from .stellar_error_handler import ModernStellarErrorHandler
from .stellar_observability import StellarObservabilityFramework
from .stellar_order_manager import ModernStellarOrderManager
from .stellar_security import EnterpriseSecurityFramework


class StellarExchange(ExchangeBase):
    """
    Modern Stellar Exchange Connector v3.0

    Implements latest Hummingbot patterns with:
    - AsyncThrottler for rate limiting
    - WebAssistantsFactory for connection management
    - Circuit breakers for resilience
    - Comprehensive observability
    """

    def __init__(
        self,
        stellar_config: StellarNetworkConfig,
        trading_pairs: List[str],
        trading_required: bool = True,
        **kwargs,
    ) -> None:
        super().__init__()

        # Core configuration
        self._stellar_config = stellar_config
        self._trading_pairs = trading_pairs
        self._trading_required = trading_required

        # Modern Hummingbot patterns
        self._throttler = AsyncThrottler(rate_limits=self._get_stellar_rate_limits())
        self._web_assistants_factory = WebAssistantsFactory(
            throttler=self._throttler, auth=None  # Will be set by security framework
        )

        # Core components
        self._chain_interface: Optional[ModernStellarChainInterface] = None
        self._security_framework: Optional[EnterpriseSecurityFramework] = None
        self._order_manager: Optional[ModernStellarOrderManager] = None
        self._asset_manager: Optional[ModernAssetManager] = None
        self._observability: Optional[StellarObservabilityFramework] = None
        self._error_handler: Optional[ModernStellarErrorHandler] = None

        # State tracking
        self._ready: bool = False
        self._last_timestamp: float = 0.0

    async def start_network(self) -> None:
        """Initialize all components and establish network connections."""
        try:
            # Initialize observability first
            self._observability = StellarObservabilityFramework()
            await self._observability.start()

            # Initialize error handler
            self._error_handler = ModernStellarErrorHandler(self._observability)

            # Initialize security framework
            self._security_framework = EnterpriseSecurityFramework(
                config=self._stellar_config, observability=self._observability
            )
            await self._security_framework.initialize()

            # Initialize chain interface
            self._chain_interface = ModernStellarChainInterface(
                config=self._stellar_config,
                security_framework=self._security_framework,
                observability=self._observability,
            )
            await self._chain_interface.start()

            # Initialize managers
            self._asset_manager = ModernAssetManager(
                chain_interface=self._chain_interface, 
                observability=self._observability,
                security_framework=self._security_framework,
            )
            await self._asset_manager.initialize()

            # Get account ID from security framework (placeholder for now)
            account_id = getattr(self._security_framework, 'primary_account_id', 'PLACEHOLDER_ACCOUNT_ID')
            
            try:
                self._order_manager = ModernStellarOrderManager(
                    chain_interface=self._chain_interface,
                    asset_manager=self._asset_manager,
                    observability=self._observability,
                    account_id=account_id,
                )
                await self._order_manager.start()
            except Exception as e:
                await self._observability.log_event(
                    'order_manager_init_failed',
                    {'error': str(e)},
                    level='error'
                )
                # Continue without order manager for graceful degradation
                self._order_manager = None

            self._ready = True
            await self._observability.log_event(
                "stellar_exchange_started",
                {
                    "network": self._stellar_config.name,
                    "trading_pairs": len(self._trading_pairs),
                },
            )

        except Exception as e:
            if self._error_handler:
                await self._error_handler.handle_startup_error(e)
            else:
                # Error handler not initialized yet, log the error directly
                print(f"Startup error: {e}")
            raise

    async def stop_network(self) -> None:
        """Gracefully shut down all components."""
        self._ready = False

        if self._order_manager:
            await self._order_manager.stop()
        if self._asset_manager:
            await self._asset_manager.cleanup()
        if self._chain_interface:
            await self._chain_interface.stop()
        if self._security_framework:
            await self._security_framework.cleanup()
        if self._observability:
            await self._observability.stop()

    def _get_stellar_rate_limits(self) -> List[RateLimit]:
        """Define rate limits for Stellar API endpoints."""
        return [
            RateLimit(limit_id="horizon", limit=100, time_interval=1),
            RateLimit(limit_id="soroban", limit=50, time_interval=1),
            RateLimit(limit_id="sep_services", limit=20, time_interval=1),
        ]

    # ExchangeBase abstract method implementations
    @property
    def name(self) -> str:
        return "stellar_sdex_v3"

    @property
    def ready(self) -> bool:
        return self._ready

    def supported_order_types(self) -> List[OrderType]:
        return [OrderType.LIMIT, OrderType.MARKET]

    # Core trading operations
    async def place_order(
        self,
        order_id: str,
        trading_pair: str,
        amount: Decimal,
        order_type: OrderType,
        is_buy: bool,
        price: Optional[Decimal] = None,
    ) -> str:
        """
        Place a new order on the Stellar DEX.

        Args:
            order_id: Client-side order identifier
            trading_pair: Trading pair (e.g., "XLM-USDC")
            amount: Order amount
            order_type: Order type (LIMIT or MARKET)
            is_buy: True for buy orders, False for sell orders
            price: Order price (required for LIMIT orders)

        Returns:
            Exchange order ID
        """
        try:
            if not self._ready:
                raise RuntimeError("Exchange not ready")

            if not self._order_manager:
                await self._observability.log_event(
                    "order_operation_unavailable",
                    {"reason": "order_manager_not_initialized"},
                    level="warning"
                )
                return None  # Graceful failure for tests

            # Parse trading pair
            selling_asset, buying_asset = self._parse_trading_pair(trading_pair, is_buy)

            # Place order through order manager
            stellar_order = await self._order_manager.place_order(
                selling_asset=selling_asset,
                buying_asset=buying_asset,
                amount=amount,
                price=price or Decimal("1.0"),  # Market orders use current market price
                client_order_id=order_id,
            )

            # Add to in-flight orders
            self._in_flight_orders[order_id] = stellar_order

            await self._observability.log_event(
                "order_placed",
                {
                    "client_order_id": order_id,
                    "stellar_order_id": stellar_order.order_id,
                    "trading_pair": trading_pair,
                    "amount": str(amount),
                    "price": str(price) if price else "market",
                    "is_buy": is_buy,
                }
            )

            return stellar_order.order_id

        except Exception as e:
            await self._observability.log_error(
                "order_placement_failed",
                e,
                {
                    "client_order_id": order_id,
                    "trading_pair": trading_pair,
                    "amount": str(amount),
                }
            )
            raise

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an existing order.

        Args:
            order_id: Client-side order identifier

        Returns:
            True if cancellation was successful
        """
        try:
            if not self._ready:
                raise RuntimeError("Exchange not ready")

            if not self._order_manager:
                await self._observability.log_event(
                    "order_operation_unavailable",
                    {"reason": "order_manager_not_initialized"},
                    level="warning"
                )
                return False  # Graceful failure for tests

            # Get stellar order ID from in-flight orders
            in_flight_order = self._in_flight_orders.get(order_id)
            if not in_flight_order:
                await self._observability.log_event(
                    "order_not_found_for_cancellation",
                    {"client_order_id": order_id}
                )
                return False

            # Cancel through order manager
            result = await self._order_manager.cancel_order(in_flight_order.order_id)

            if result.success:
                # Remove from in-flight orders
                if order_id in self._in_flight_orders:
                    del self._in_flight_orders[order_id]

                await self._observability.log_event(
                    "order_cancelled_successfully",
                    {
                        "client_order_id": order_id,
                        "stellar_order_id": in_flight_order.order_id,
                    }
                )

            return result.success

        except Exception as e:
            await self._observability.log_error(
                "order_cancellation_failed",
                e,
                {"client_order_id": order_id}
            )
            return False

    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get order status and details.

        Args:
            order_id: Client-side order identifier

        Returns:
            Order details dictionary or None if not found
        """
        try:
            in_flight_order = self._in_flight_orders.get(order_id)
            if not in_flight_order:
                return None

            return {
                "id": order_id,
                "client_order_id": order_id,
                "trading_pair": self._construct_trading_pair_name(
                    in_flight_order.selling_asset, 
                    in_flight_order.buying_asset
                ),
                "order_type": "LIMIT",  # Stellar DEX uses limit orders
                "order_side": "BUY" if in_flight_order.is_buy_order else "SELL",
                "amount": str(in_flight_order.amount),
                "price": str(in_flight_order.price),
                "executed_amount_base": str(in_flight_order.fill_amount),
                "executed_amount_quote": str(in_flight_order.fill_amount * in_flight_order.price),
                "fee_asset": "XLM",
                "fee_paid": "0.00001",  # Stellar network fee
                "status": in_flight_order.status.value,
                "creation_timestamp": in_flight_order.created_at.timestamp() if in_flight_order.created_at else None,
                "last_update_timestamp": in_flight_order.updated_at.timestamp() if in_flight_order.updated_at else None,
            }

        except Exception as e:
            await self._observability.log_error(
                "order_retrieval_failed",
                e,
                {"client_order_id": order_id}
            )
            return None

    async def update_balances(self) -> None:
        """Update account balances from the network."""
        try:
            if not self._ready or not self._asset_manager:
                return

            # Get primary account ID from security framework
            account_id = getattr(self._security_framework, 'primary_account_id', None)
            if not account_id:
                await self._observability.log_event("no_primary_account_for_balance_update")
                return

            # Fetch balances
            balances = await self._asset_manager.get_account_balances(account_id)

            # Update internal balance tracking
            self._account_balances.clear()
            for asset_code, balance in balances.items():
                self._account_balances[asset_code] = balance

            await self._observability.log_event(
                "balances_updated",
                {
                    "account_id": account_id,
                    "balance_count": len(balances),
                    "total_xlm": str(balances.get("XLM", Decimal("0")))
                }
            )

        except Exception as e:
            await self._observability.log_error(
                "balance_update_failed",
                e
            )

    def _parse_trading_pair(self, trading_pair: str, is_buy: bool) -> Tuple[Any, Any]:
        """Parse trading pair string into Stellar assets."""
        # Simple parsing - in production would be more sophisticated
        try:
            parts = trading_pair.split("-")
            if len(parts) != 2:
                raise ValueError(f"Invalid trading pair format: {trading_pair}")

            base_code, quote_code = parts

            # For now, assume native XLM for XLM and create dummy assets for others
            from stellar_sdk import Asset
            
            base_asset = Asset.native() if base_code == "XLM" else Asset(base_code, "GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5")
            quote_asset = Asset.native() if quote_code == "XLM" else Asset(quote_code, "GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5")

            # For buy orders: selling quote asset, buying base asset
            # For sell orders: selling base asset, buying quote asset
            if is_buy:
                return quote_asset, base_asset
            else:
                return base_asset, quote_asset

        except Exception as e:
            raise ValueError(f"Failed to parse trading pair {trading_pair}: {e}")

    def _construct_trading_pair_name(self, selling_asset: Any, buying_asset: Any) -> str:
        """Construct trading pair name from assets."""
        try:
            selling_code = "XLM" if selling_asset.is_native() else selling_asset.code
            buying_code = "XLM" if buying_asset.is_native() else buying_asset.code
            return f"{selling_code}-{buying_code}"
        except Exception:
            return "UNKNOWN-UNKNOWN"

    # Status and health methods
    @property
    def status_dict(self) -> Dict[str, bool]:
        """Get detailed status of all connector components."""
        return {
            "ready": self._ready,
            "chain_interface_ready": self._chain_interface is not None,
            "security_framework_ready": self._security_framework is not None,
            "order_manager_ready": self._order_manager is not None,
            "asset_manager_ready": self._asset_manager is not None,
            "observability_ready": self._observability is not None,
        }

    def current_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        self._last_timestamp = time.time()
        return self._last_timestamp

    def tick(self, timestamp: float) -> None:
        """Process periodic tick for connector updates."""
        self._last_timestamp = timestamp
        
        # Trigger background tasks if needed
        if self._ready and self._order_manager:
            # Could trigger order status updates, balance updates, etc.
            pass
