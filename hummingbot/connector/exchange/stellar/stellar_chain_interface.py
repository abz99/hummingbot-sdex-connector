"""
Modern Stellar Chain Interface with Enhanced SDK v8.x Integration
Production-ready implementation with connection pooling and failover.
"""

import asyncio
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING, Union

import aiohttp
from stellar_sdk import Account, Asset, Keypair, Network, ServerAsync, TransactionBuilder
from stellar_sdk.client.aiohttp_client import AiohttpClient

if TYPE_CHECKING:
    from .stellar_observability import StellarObservabilityFramework
    from .stellar_security import EnterpriseSecurityFramework


from .stellar_config_models import StellarNetworkConfig


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
            horizon_urls = [str(self.config.horizon.primary)] + [str(url) for url in self.config.horizon.fallbacks]
            for horizon_url in horizon_urls:
                # AiohttpClient manages its own session internally
                aiohttp_client = AiohttpClient()
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

            if self.observability:
                    await self.observability.log_event(
                    "chain_interface_started",
                    {
                        "horizon_servers": len(self.horizon_servers),
                        "soroban_servers": len(self.soroban_servers),
                        "network": self.config.name,
                    },
                )

        except Exception as e:
            if self.observability:
                    await self.observability.log_error("chain_interface_start_failed", e)
            raise

    async def stop(self) -> None:
        """Gracefully shutdown connection pool and cleanup resources."""
        if self.session_pool and not self.session_pool.closed:
            await self.session_pool.close()

        if self.observability:
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
                if self.observability:
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
                if self.observability:
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
            if self.observability:
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
                if self.observability:
                    await self.observability.log_error("health_monitor_error", e)
                await asyncio.sleep(60)  # Back off on errors

    async def create_manage_offer_transaction(
        self,
        source_keypair: Keypair,
        selling_asset: Asset,
        buying_asset: Asset,
        amount: str,
        price: str,
        offer_id: Optional[int] = None,
    ) -> TransactionBuilder:
        """
        Create a manage offer transaction.
        
        Args:
            source_keypair: Account keypair for the transaction
            selling_asset: Asset being sold
            buying_asset: Asset being bought
            amount: Amount to sell
            price: Price ratio (selling/buying)
            offer_id: Existing offer ID to modify, or None for new offer
            
        Returns:
            TransactionBuilder ready for submission
        """
        try:
            source_account_id = source_keypair.public_key
            account = await self.get_account_with_retry(source_account_id)
            
            if not account:
                raise ValueError(f"Source account {source_account_id} not found")
                
            # Build transaction
            transaction_builder = (
                TransactionBuilder(
                    source_account=account,
                    network_passphrase=self.network_passphrase,
                    base_fee=100,  # Default base fee
                )
                .add_manage_sell_offer_op(
                    selling=selling_asset,
                    buying=buying_asset,
                    amount=amount,
                    price=price,
                    offer_id=offer_id,
                )
                .set_timeout(30)  # 30 second timeout
            )
            
            await self.observability.log_event(
                "manage_offer_transaction_created",
                {
                    "selling_asset": str(selling_asset),
                    "buying_asset": str(buying_asset),
                    "amount": amount,
                    "price": price,
                    "offer_id": offer_id,
                }
            )
            
            return transaction_builder
            
        except Exception as e:
            if self.observability:
                    await self.observability.log_error(
                "manage_offer_creation_failed",
                e,
                {
                    "selling_asset": str(selling_asset),
                    "buying_asset": str(buying_asset),
                    "amount": amount,
                    "price": price,
                }
            )
            raise

    async def submit_transaction(
        self,
        transaction_builder: TransactionBuilder,
        source_keypair: Keypair,
        max_retries: int = 3,
    ) -> Any:
        """
        Submit a transaction to the Stellar network with retry logic.
        
        Args:
            transaction_builder: Prepared transaction builder
            source_keypair: Keypair to sign the transaction
            max_retries: Maximum retry attempts
            
        Returns:
            Transaction response from Stellar network
        """
        for attempt in range(max_retries):
            try:
                async with self.request_semaphore:
                    if not self.current_horizon:
                        await self._switch_to_next_horizon()
                        
                    if self.current_horizon is None:
                        raise RuntimeError("No healthy Horizon servers available")
                    
                    # Sign and build the transaction
                    transaction = transaction_builder.build()
                    transaction.sign(source_keypair)
                    
                    # Submit to network
                    response = await self.current_horizon.submit_transaction(transaction)
                    
                    await self.observability.log_event(
                        "transaction_submitted_successfully",
                        {
                            "hash": response.hash,
                            "attempt": attempt + 1,
                            "horizon_url": self.current_horizon.horizon_url,
                        }
                    )
                    
                    return response
                    
            except Exception as e:
                if self.observability:
                    await self.observability.log_error(
                    "transaction_submission_failed",
                    e,
                    {
                        "attempt": attempt + 1,
                        "horizon_url": self.current_horizon.horizon_url if self.current_horizon else None,
                    }
                )
                
                if attempt < max_retries - 1:
                    await self._switch_to_next_horizon()
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                else:
                    raise
                    
        raise RuntimeError("Transaction submission failed after all retries")

    async def create_payment_transaction(
        self,
        source_keypair: Keypair,
        destination_account: str,
        asset: Asset,
        amount: str,
    ) -> TransactionBuilder:
        """
        Create a payment transaction.
        
        Args:
            source_keypair: Source account keypair
            destination_account: Destination account ID
            asset: Asset to send
            amount: Amount to send
            
        Returns:
            TransactionBuilder ready for submission
        """
        try:
            source_account_id = source_keypair.public_key
            account = await self.get_account_with_retry(source_account_id)
            
            if not account:
                raise ValueError(f"Source account {source_account_id} not found")
                
            transaction_builder = (
                TransactionBuilder(
                    source_account=account,
                    network_passphrase=self.network_passphrase,
                    base_fee=100,
                )
                .add_payment_op(
                    destination=destination_account,
                    asset=asset,
                    amount=amount,
                )
                .set_timeout(30)
            )
            
            await self.observability.log_event(
                "payment_transaction_created",
                {
                    "destination": destination_account,
                    "asset": str(asset),
                    "amount": amount,
                }
            )
            
            return transaction_builder
            
        except Exception as e:
            if self.observability:
                    await self.observability.log_error(
                "payment_creation_failed",
                e,
                {
                    "destination": destination_account,
                    "asset": str(asset),
                    "amount": amount,
                }
            )
            raise

    async def create_trustline_transaction(
        self,
        source_keypair: Keypair,
        asset: Asset,
        limit: Optional[str] = None,
    ) -> TransactionBuilder:
        """
        Create a trustline transaction.
        
        Args:
            source_keypair: Source account keypair
            asset: Asset to trust
            limit: Trust limit (None for unlimited)
            
        Returns:
            TransactionBuilder ready for submission
        """
        try:
            source_account_id = source_keypair.public_key
            account = await self.get_account_with_retry(source_account_id)
            
            if not account:
                raise ValueError(f"Source account {source_account_id} not found")
                
            transaction_builder = (
                TransactionBuilder(
                    source_account=account,
                    network_passphrase=self.network_passphrase,
                    base_fee=100,
                )
                .add_change_trust_op(
                    asset=asset,
                    limit=limit,
                )
                .set_timeout(30)
            )
            
            await self.observability.log_event(
                "trustline_transaction_created",
                {
                    "asset": str(asset),
                    "limit": limit,
                }
            )
            
            return transaction_builder
            
        except Exception as e:
            if self.observability:
                    await self.observability.log_error(
                "trustline_creation_failed",
                e,
                {
                    "asset": str(asset),
                    "limit": limit,
                }
            )
            raise

    async def check_soroban_health(self) -> bool:
        """Check Soroban RPC endpoint health."""
        try:
            if not self.config.soroban or not self.config.soroban.primary:
                return False

            # Use aiohttp to check Soroban health endpoint
            async with aiohttp.ClientSession() as session:
                health_url = f"{self.config.soroban.primary}/health"
                async with session.get(health_url, timeout=10) as response:
                    if response.status == 200:
                        if self.observability:
                            await self.observability.log_event("soroban_health_check_success", {"url": health_url})
                        return True
                    else:
                        if self.observability:
                            await self.observability.log_event("soroban_health_check_failed",
                                {"url": health_url, "status": response.status})
                        return False
        except Exception as e:
            if self.observability:
                await self.observability.log_error("soroban_health_check_error", e, {"endpoint": self.config.soroban.primary if self.config.soroban else "none"})
            return False

    async def get_latest_ledger(self) -> Optional[Dict[str, Any]]:
        """Get the latest ledger information."""
        try:
            if not self.current_horizon:
                return None

            # Use Stellar SDK to get ledgers
            ledgers_call = self.current_horizon.ledgers().order(desc=True).limit(1)
            response = await ledgers_call.call()

            if response and 'records' in response and len(response['records']) > 0:
                latest_ledger = response['records'][0]

                if self.observability:
                    await self.observability.log_event("latest_ledger_retrieved", {
                        "sequence": latest_ledger.get("sequence"),
                        "closed_at": latest_ledger.get("closed_at")
                    })

                return latest_ledger
            else:
                if self.observability:
                    await self.observability.log_event("latest_ledger_empty_response", {"response": response})
                return None

        except Exception as e:
            if self.observability:
                await self.observability.log_error("latest_ledger_fetch_failed", e, {})

            # Try failover if available
            if len(self.horizon_servers) > 1:
                await self._switch_to_next_horizon()
                # Retry once with next server
                try:
                    if self.current_horizon:
                        ledgers_call = self.current_horizon.ledgers().order(desc=True).limit(1)
                        response = await ledgers_call.call()
                        if response and 'records' in response and len(response['records']) > 0:
                            return response['records'][0]
                except Exception as retry_e:
                    if self.observability:
                        await self.observability.log_error("latest_ledger_retry_failed", retry_e, {})

            return None

    def get_network_info(self) -> Dict[str, Any]:
        """Get current network information."""
        return {
            "network_passphrase": self.network_passphrase,
            "current_horizon_url": self.current_horizon.horizon_url if self.current_horizon else None,
            "horizon_servers": [server.horizon_url for server in self.horizon_servers],
            "horizon_health": self._horizon_health_status,
            "active_server_index": self._current_horizon_index,
        }
