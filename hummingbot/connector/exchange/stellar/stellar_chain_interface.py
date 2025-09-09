"""
Modern Stellar Chain Interface with Enhanced SDK v8.x Integration
Production-ready implementation with connection pooling and failover.
"""

import asyncio
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union

import aiohttp
from stellar_sdk import Account, Asset, Keypair, Network, ServerAsync, TransactionBuilder
from stellar_sdk.client.aiohttp_client import AiohttpClient

if TYPE_CHECKING:
    from .stellar_observability import StellarObservabilityFramework
    from .stellar_security import EnterpriseSecurityFramework


# Define StellarNetworkConfig for type checking
@dataclass
class StellarNetworkConfig:
    """Network configuration for Stellar."""

    horizon_url: str
    network_passphrase: str
    fallback_urls: List[str] = None

    def __post_init__(self) -> None:
        if self.fallback_urls is None:
            self.fallback_urls = []

    @property
    def horizon_urls(self) -> List[str]:
        """Get all horizon URLs (primary + fallbacks)."""
        return [self.horizon_url] + self.fallback_urls


@dataclass
class ConnectionPoolConfig:
    """Configuration for connection pool management."""

    max_connections: int = 50
    max_keepalive_connections: int = 10
    keepalive_timeout: int = 30
    timeout: int = 30


class ModernStellarChainInterface:
    """
    Enhanced Stellar Chain Interface with modern patterns.

    Features:
    - Connection pooling with aiohttp
    - Automatic failover between Horizon servers
    - Enhanced sequence number management
    - Comprehensive error handling
    - Real-time reserve calculations
    """

    def __init__(
        self,
        config: StellarNetworkConfig,
        security_framework: Optional["EnterpriseSecurityFramework"] = None,
        observability: Optional["StellarObservabilityFramework"] = None,
    ) -> None:
        self.config = config
        self.security_framework = security_framework
        self.observability = observability

        # Connection management
        self.session_pool: Optional[aiohttp.ClientSession] = None
        self.request_semaphore = asyncio.Semaphore(10)
        self._current_horizon_index = 0
        self._horizon_health_status: Dict[str, bool] = {}

        # Stellar SDK instances
        self.horizon_servers: List[ServerAsync] = []
        self.soroban_servers: List[Any] = []  # SorobanServer - to be implemented in Phase 3
        self.current_horizon: Optional[ServerAsync] = None
        self.current_soroban: Optional[Any] = None  # SorobanServer - to be implemented in Phase 3

        # Network configuration
        self.network_passphrase = config.network_passphrase
        self.network = Network(config.network_passphrase)

        # Account and sequence management
        self._account_sequences: Dict[str, int] = {}
        self._sequence_locks: Dict[str, asyncio.Lock] = {}
        self._reserve_cache: Dict[str, Decimal] = {}

    async def start(self) -> None:
        """Initialize connection pool and Stellar SDK clients."""
        try:
            # Initialize connection pool
            connector = aiohttp.TCPConnector(
                limit=ConnectionPoolConfig.max_connections,
                limit_per_host=ConnectionPoolConfig.max_keepalive_connections,
                keepalive_timeout=ConnectionPoolConfig.keepalive_timeout,
            )

            timeout = aiohttp.ClientTimeout(total=ConnectionPoolConfig.timeout)
            self.session_pool = aiohttp.ClientSession(connector=connector, timeout=timeout)

            # Initialize Horizon servers with failover
            for horizon_url in self.config.horizon_urls:
                aiohttp_client = AiohttpClient(session=self.session_pool)
                server = ServerAsync(horizon_url=horizon_url, client=aiohttp_client)
                self.horizon_servers.append(server)
                self._horizon_health_status[horizon_url] = True

            # Initialize Soroban servers (stub - implementation in Phase 3)
            # for soroban_url in self.config.soroban_rpc_urls:
            #     server = SorobanServer(
            #         rpc_url=soroban_url,
            #         client=self.session_pool
            #     )
            #     self.soroban_servers.append(server)

            # Set current active servers
            self.current_horizon = self.horizon_servers[0] if self.horizon_servers else None
            self.current_soroban = self.soroban_servers[0] if self.soroban_servers else None

            # Start health monitoring
            asyncio.create_task(self._monitor_server_health())

            await self.observability.log_event(
                "chain_interface_started",
                {
                    "horizon_servers": len(self.horizon_servers),
                    "soroban_servers": len(self.soroban_servers),
                    "network": self.config.network,
                },
            )

        except Exception as e:
            await self.observability.log_error("chain_interface_start_failed", e)
            raise

    async def stop(self) -> None:
        """Gracefully shutdown connection pool and cleanup resources."""
        if self.session_pool and not self.session_pool.closed:
            await self.session_pool.close()

        await self.observability.log_event("chain_interface_stopped")

    async def get_account_with_retry(
        self, account_id: str, max_retries: int = 3
    ) -> Optional[Account]:
        """
        Fetch account with automatic retry and failover.

        Args:
            account_id: Stellar account ID
            max_retries: Maximum retry attempts

        Returns:
            Account object or None if not found
        """
        for attempt in range(max_retries):
            try:
                async with self.request_semaphore:
                    if not self.current_horizon:
                        await self._switch_to_next_horizon()

                    if self.current_horizon is None:
                        return None

                    account_call_builder = self.current_horizon.accounts().account_id(account_id)
                    account = await account_call_builder.call()

                    # Update sequence number cache
                    sequence = int(account.sequence)
                    self._account_sequences[account_id] = sequence

                    return account

            except Exception as e:
                await self.observability.log_error(
                    "account_fetch_failed",
                    e,
                    {
                        "account_id": account_id,
                        "attempt": attempt,
                        "horizon_url": (
                            self.current_horizon.horizon_url if self.current_horizon else None
                        ),
                    },
                )

                if attempt < max_retries - 1:
                    await self._switch_to_next_horizon()
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                else:
                    raise

        return None

    async def get_next_sequence_number(self, account_id: str) -> str:
        """
        Get next sequence number with collision handling.

        Args:
            account_id: Stellar account ID

        Returns:
            Next sequence number as string
        """
        if account_id not in self._sequence_locks:
            self._sequence_locks[account_id] = asyncio.Lock()

        async with self._sequence_locks[account_id]:
            try:
                # Get current sequence from cache or fetch from network
                if account_id not in self._account_sequences:
                    account = await self.get_account_with_retry(account_id)
                    if not account:
                        raise ValueError(f"Account {account_id} not found")

                # Increment and return next sequence
                current_sequence = self._account_sequences[account_id]
                next_sequence = current_sequence + 1
                self._account_sequences[account_id] = next_sequence

                return str(next_sequence)

            except Exception as e:
                await self.observability.log_error(
                    "sequence_number_error", e, {"account_id": account_id}
                )
                raise

    async def calculate_minimum_balance(self, account: Account) -> Decimal:
        """
        Calculate minimum balance required for account.

        Args:
            account: Stellar account object

        Returns:
            Minimum balance in XLM
        """
        try:
            base_reserve = Decimal("0.5")  # Current Stellar base reserve
            account_reserve = Decimal("1.0")  # Base account reserve

            # Count account entries
            subentry_count = (
                len(getattr(account, "signers", []))
                - 1  # Signers (excluding master key)
                + len(getattr(account, "balances", []))
                - 1  # Trustlines (excluding native)
                + len(getattr(account, "data", {}))  # Data entries
                + len(getattr(account, "offers", []))  # Open offers
            )

            minimum_balance = account_reserve + (base_reserve * subentry_count)

            # Cache result
            account_id = getattr(account, "account_id", getattr(account, "id", ""))
            self._reserve_cache[account_id] = minimum_balance

            return minimum_balance

        except Exception as e:
            await self.observability.log_error(
                "reserve_calculation_failed",
                e,
                {"account_id": getattr(account, "account_id", getattr(account, "id", "unknown"))},
            )
            # Return conservative estimate
            return Decimal("5.0")

    async def _switch_to_next_horizon(self) -> None:
        """Switch to next healthy Horizon server."""
        if not self.horizon_servers:
            return

        self._current_horizon_index = (self._current_horizon_index + 1) % len(self.horizon_servers)
        self.current_horizon = self.horizon_servers[self._current_horizon_index]

        await self.observability.log_event(
            "horizon_server_switched",
            {
                "new_server": self.current_horizon.horizon_url,
                "server_index": self._current_horizon_index,
            },
        )

    async def _monitor_server_health(self) -> None:
        """Continuously monitor server health and update status."""
        while True:
            try:
                for i, server in enumerate(self.horizon_servers):
                    try:
                        # Simple health check - get network info
                        await server.root().call()
                        self._horizon_health_status[server.horizon_url] = True
                    except Exception:
                        self._horizon_health_status[server.horizon_url] = False

                        # Switch if current server is unhealthy
                        if server == self.current_horizon:
                            await self._switch_to_next_horizon()

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                await self.observability.log_error("health_monitor_error", e)
                await asyncio.sleep(60)  # Back off on errors

    # Additional methods for transaction building, submission, etc.
    # will be implemented in subsequent development phases
