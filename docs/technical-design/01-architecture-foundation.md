# Stellar SDEX Connector: Architecture & Technical Foundation

> **Part 1 of 7** - Technical Design Document v3.0
> Split from: `stellar_sdex_tdd_v3.md` (Lines 1-608)

## Executive Summary

**Document Purpose**: Final production-ready technical blueprint for implementing a Stellar DEX connector within the Hummingbot ecosystem, incorporating all critical architectural improvements and modern development patterns.

**Core Architecture Decision**: Direct Hummingbot client connector implementation (Python-based) with modern SDK integration and enterprise-grade security.

**Key Enhancements in v3.0**:
- ✅ Latest Stellar Python SDK (v8.x) integration patterns
- ✅ Modern Hummingbot connector patterns (AsyncThrottler, WebAssistants)
- ✅ Enhanced Soroban smart contract integration
- ✅ Comprehensive SEP standards support
- ✅ Production-grade monitoring and observability
- ✅ Advanced error handling and resilience patterns

---

## 1. Architecture Overview

### 1.1 Integration Strategy

**Selected Approach**: Direct Hummingbot Client Connector with Modern Patterns

**Enhanced Integration Pattern**:
```
Hummingbot Client ←→ Modern Stellar Connector (Python) ←→ Stellar Network
                        ↓
                   [Throttling, WebAssistants, Monitoring]
                        ↓
               [Horizon API + Soroban RPC + SEP Services]
```

**Modern Architecture Benefits**:
- Latest Hummingbot patterns (v1.27+) integration
- Advanced API rate limiting and connection management
- Comprehensive error handling and resilience
- Production-grade monitoring and observability
- Full Soroban smart contract support

### 1.2 Connector Classification

**Type**: Advanced Hybrid CLOB/AMM with Smart Contract Integration
- **Primary**: Central Limit Order Book operations via Horizon API
- **Secondary**: AMM pool interactions via Soroban smart contracts
- **Tertiary**: Path payment routing with multi-hop optimization
- **Quaternary**: SEP-compliant cross-border payment capabilities

### 1.3 Enhanced Core Components

1. **Modern Stellar Chain Interface** - AsyncIO-based with latest SDK patterns
2. **Web Assistant Factory** - Modern connection management and rate limiting
3. **Enhanced Security Framework** ✅ **IMPLEMENTED** - HSM + MPC + Hardware wallet support + Development security
4. **Soroban Contract Manager** - Smart contract interaction layer
5. **SEP Standards Integration** - Authentication, deposits, payments
6. **Advanced Order Manager** - Lifecycle management with monitoring
7. **Performance Optimizer** - Connection pooling and request batching
8. **Observability Framework** - Comprehensive metrics and tracing

---

## 2. Modern Technical Implementation

### 2.1 Latest Stellar SDK Integration

**Enhanced Stellar Chain Interface** with modern patterns:

```python
from stellar_sdk import ServerAsync, SorobanServer, TransactionBuilder, Claimant
from stellar_sdk.sep import stellar_web_authentication
from stellar_sdk.liquidity_pool_asset import LiquidityPoolAsset
from stellar_sdk.operation import LiquidityPoolDeposit, LiquidityPoolWithdraw
from stellar_sdk.contract import Contract
from stellar_sdk.soroban import SorobanServer
import aiohttp
from asyncio import Semaphore

class ModernStellarChainInterface:
    """Enhanced Stellar chain interface with modern SDK patterns"""

    def __init__(self, config: StellarNetworkConfig):
        # Modern async server setup
        self.session_pool = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=50)
        )
        self.request_semaphore = Semaphore(10)  # Limit concurrent requests

        # Latest SDK integration
        self.horizon_server = ServerAsync(
            horizon_url=config.horizon_url,
            client=self.session_pool
        )
        self.soroban_server = SorobanServer(
            rpc_url=config.soroban_rpc_url,
            client=self.session_pool
        )

        # Network configuration
        self.network_passphrase = config.network_passphrase
        self.keypair: Optional[Keypair] = None

        # Modern performance optimization
        self._connection_pool = ConnectionPool()
        self._request_batcher = RequestBatcher()

    async def connect(self) -> bool:
        """Enhanced connection with health checks"""
        try:
            async with self.request_semaphore:
                # Horizon health check
                horizon_info = await self.horizon_server.fetch_base_fee()

                # Soroban health check
                network_info = await self.soroban_server.get_network()

                self.logger.info(f"Connected to Stellar network: {network_info}")
                return True

        except Exception as e:
            self.logger.error(f"Failed to connect to Stellar network: {e}")
            return False

    async def get_account_with_caching(self, address: str) -> Account:
        """Account retrieval with intelligent caching"""
        cache_key = f"account:{address}"

        # Check cache first (4-second TTL for ledger-aware caching)
        if cached_account := await self._cache.get(cache_key):
            return cached_account

        async with self.request_semaphore:
            account = await self.horizon_server.accounts().account_id(address).call()

            # Cache with ledger-aware expiry
            await self._cache.set(cache_key, account, ttl=4)
            return account

    async def submit_transaction_with_retry(self, transaction: Transaction) -> Dict:
        """Enhanced transaction submission with retry logic"""
        max_retries = 3
        backoff_multiplier = 1.5

        for attempt in range(max_retries):
            try:
                async with self.request_semaphore:
                    response = await self.horizon_server.submit_transaction(transaction)

                    # Success metrics
                    self._metrics.record_transaction_success()
                    return response

            except BadRequestError as e:
                if self._is_sequence_error(e):
                    # Handle sequence number collision
                    await self._handle_sequence_collision(transaction)
                    continue
                raise
            except Exception as e:
                if attempt == max_retries - 1:
                    self._metrics.record_transaction_failure(str(e))
                    raise

                # Exponential backoff
                await asyncio.sleep(backoff_multiplier ** attempt)
```

### 2.2 Modern Hummingbot Integration Patterns

**Enhanced Connector with Latest Patterns**:

```python
from hummingbot.connector.exchange_base import ExchangeBase
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
from hummingbot.core.web_assistant.ws_assistant import WSAssistant
from hummingbot.connector.utils.web_utils import build_api_factory
from stellar_sdk.exceptions import BadRequestError, NotFoundError
from hummingbot.core.network_iterator import NetworkStatus

# Modern rate limiting configuration
STELLAR_RATE_LIMITS = [
    RateLimit(limit_id="horizon_api", limit=100, time_interval=1),  # 100/second
    RateLimit(limit_id="soroban_rpc", limit=50, time_interval=1),   # 50/second
    RateLimit(limit_id="sep_services", limit=20, time_interval=1),  # 20/second
]

class ModernStellarExchange(ExchangeBase):
    """Modern Hummingbot Stellar connector with latest patterns"""

    def __init__(self, **kwargs):
        # Modern Hummingbot patterns
        self._throttler = AsyncThrottler(rate_limits=STELLAR_RATE_LIMITS)
        self._web_assistants_factory = WebAssistantsFactory(
            throttler=self._throttler,
            auth=StellarAuthentication()
        )

        # Enhanced error handler
        self._error_handler = ModernStellarErrorHandler()

        # Performance monitoring
        self._metrics_collector = StellarMetricsCollector()

        # Modern connection management
        self._connection_manager = ModernConnectionManager(
            web_assistants_factory=self._web_assistants_factory
        )

        super().__init__(**kwargs)

    async def start_network(self) -> None:
        """Enhanced network startup with modern patterns"""

        # Initialize modern web assistant
        self._ws_assistant: WSAssistant = await self._web_assistants_factory.get_ws_assistant()

        # Start enhanced chain interface
        await self._chain_interface.connect()

        # Initialize modern order tracking
        await self._start_modern_order_tracking()

        # Start enhanced user stream
        await self._start_enhanced_user_stream()

        # Initialize SEP services
        await self._initialize_sep_services()

        self._metrics_collector.record_startup_success()

    def classify_error(self, error: Exception) -> NetworkStatus:
        """Enhanced Stellar-specific error classification"""
        if isinstance(error, BadRequestError):
            error_str = str(error)

            # Stellar-specific error handling
            if "op_underfunded" in error_str:
                return NetworkStatus.NOT_CONNECTED  # Insufficient balance
            elif "op_no_trust" in error_str:
                return NetworkStatus.NOT_CONNECTED  # Missing trustline
            elif "op_no_destination" in error_str:
                return NetworkStatus.NOT_CONNECTED  # Invalid destination
            elif "tx_bad_seq" in error_str:
                return NetworkStatus.UNKNOWN_ERROR  # Sequence issue, retry

        elif isinstance(error, NotFoundError):
            return NetworkStatus.NOT_CONNECTED  # Account/asset not found

        return super().classify_error(error)
```

### 2.3 Enhanced Soroban Smart Contract Integration

**Comprehensive Soroban Contract Manager**:

```python
from stellar_sdk.soroban import SorobanServer
from stellar_sdk.contract import Contract
from stellar_sdk.operation import InvokeHostFunction

class SorobanContractManager:
    """Advanced Soroban smart contract integration"""

    def __init__(self, soroban_server: SorobanServer):
        self.soroban_server = soroban_server
        self.known_contracts = {}
        self.contract_cache = {}

    async def initialize_amm_contracts(self):
        """Initialize known AMM contract addresses"""
        # Popular Stellar AMM contracts
        self.known_contracts.update({
            "stellar_amm": "CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQAHRG3FRNQR",
            "aquarius_amm": "CAQCFVLOBK5GIULPNZRGATJJMIZL5BSP7X5ZYHAJDANTGR4ZTDDPA7WP"
        })

    async def swap_exact_in(
        self,
        contract_address: str,
        token_a: str,
        token_b: str,
        amount_in: int,
        min_amount_out: int
    ) -> Dict:
        """Execute exact input swap via Soroban contract"""

        contract = Contract(contract_address)

        # Build contract invocation
        operation = InvokeHostFunction(
            host_function=contract.call(
                "swap_exact_tokens_for_tokens",
                amount_in,
                min_amount_out,
                [token_a, token_b],
                self.keypair.public_key,
                int(time.time()) + 300  # 5 minute deadline
            ),
            source_account=self.keypair.public_key
        )

        # Submit transaction
        return await self._submit_contract_transaction(operation)

    async def get_liquidity_pools(self) -> List[Dict]:
        """Retrieve available liquidity pools from multiple AMMs"""
        pools = []

        for amm_name, contract_address in self.known_contracts.items():
            try:
                amm_pools = await self._get_amm_pools(contract_address)
                pools.extend(amm_pools)
            except Exception as e:
                self.logger.warning(f"Failed to get pools from {amm_name}: {e}")

        return pools

    async def estimate_swap_output(
        self,
        contract_address: str,
        token_in: str,
        token_out: str,
        amount_in: int
    ) -> int:
        """Estimate swap output using contract simulation"""

        contract = Contract(contract_address)

        # Simulate contract call
        simulation_result = await self.soroban_server.simulate_transaction(
            contract.call("get_amounts_out", amount_in, [token_in, token_out])
        )

        return simulation_result.results[0].value[-1]  # Last amount in path
```

### 2.4 SEP Standards Integration

**Comprehensive SEP Support Framework**:

```python
from stellar_sdk.sep import stellar_web_authentication
from stellar_sdk.sep.stellar_web_authentication import build_challenge_transaction

class SEPServicesManager:
    """Comprehensive SEP standards integration"""

    def __init__(self, chain_interface: ModernStellarChainInterface):
        self.chain_interface = chain_interface
        self.sep10_domains = {}  # Known SEP-10 authentication domains
        self.sep24_anchors = {}  # Known SEP-24 deposit/withdrawal anchors

    async def authenticate_sep10(self, domain: str, account: str) -> str:
        """SEP-10 authentication flow"""

        # Get challenge transaction
        challenge = await self._request_challenge(domain, account)

        # Sign challenge
        signed_challenge = self.chain_interface.keypair.sign(challenge)

        # Submit signed challenge
        token = await self._submit_challenge_response(domain, signed_challenge)

        return token

    async def initiate_sep24_deposit(
        self,
        anchor_domain: str,
        asset_code: str,
        amount: Decimal
    ) -> Dict:
        """SEP-24 deposit initiation"""

        # Authenticate with anchor
        token = await self.authenticate_sep10(anchor_domain, self.chain_interface.keypair.public_key)

        # Initiate deposit
        deposit_info = await self._request_deposit(
            anchor_domain, asset_code, amount, token
        )

        return deposit_info

    async def process_sep31_payment(
        self,
        receiving_anchor: str,
        asset: str,
        amount: Decimal,
        destination_country: str
    ) -> Dict:
        """SEP-31 cross-border payment processing"""

        # Get receiving anchor info
        anchor_info = await self._get_anchor_info(receiving_anchor)

        # Create payment transaction
        payment_tx = await self._create_sep31_transaction(
            anchor_info, asset, amount, destination_country
        )

        return payment_tx
```

### 2.5 Advanced Performance Optimization

**Production-Grade Performance Framework**:

```python
import aiohttp
from asyncio import Semaphore, create_task
from collections import defaultdict
import time

class PerformanceOptimizer:
    """Advanced performance optimization for Stellar operations"""

    def __init__(self):
        # Connection pooling
        self.session_pools = {}
        self.request_semaphores = defaultdict(lambda: Semaphore(10))

        # Request batching
        self.batch_queue = defaultdict(list)
        self.batch_timers = {}

        # Caching with ledger awareness
        self.cache_store = {}
        self.cache_ttls = {
            "account_data": 4,      # Just under ledger close time
            "orderbook": 1,         # High frequency updates
            "asset_metadata": 3600, # Static data
            "network_info": 300     # Network parameters
        }

    async def batch_account_requests(self, addresses: List[str]) -> Dict[str, Account]:
        """Batch multiple account requests for efficiency"""

        if len(addresses) == 1:
            # Single request, no batching needed
            account = await self.chain_interface.get_account(addresses[0])
            return {addresses[0]: account}

        # Batch multiple requests
        tasks = [
            create_task(self.chain_interface.get_account(addr))
            for addr in addresses
        ]

        accounts = await asyncio.gather(*tasks)
        return dict(zip(addresses, accounts))

    async def optimize_order_book_fetching(self, trading_pairs: List[str]) -> Dict:
        """Optimize order book fetching with parallel requests"""

        # Group by server endpoint for connection reuse
        grouped_requests = self._group_requests_by_server(trading_pairs)

        # Execute groups in parallel
        results = {}
        for server, pairs in grouped_requests.items():
            server_results = await self._fetch_orderbooks_from_server(server, pairs)
            results.update(server_results)

        return results

    def get_cache_key(self, operation: str, *args) -> str:
        """Generate cache key with operation context"""
        return f"{operation}:{':'.join(str(arg) for arg in args)}"

    async def cached_operation(self, cache_type: str, key: str, operation_func, *args):
        """Execute operation with intelligent caching"""

        cache_key = self.get_cache_key(cache_type, key)

        # Check cache
        if cache_key in self.cache_store:
            cached_item = self.cache_store[cache_key]
            if time.time() - cached_item['timestamp'] < self.cache_ttls[cache_type]:
                return cached_item['data']

        # Cache miss, execute operation
        result = await operation_func(*args)

        # Store in cache
        self.cache_store[cache_key] = {
            'data': result,
            'timestamp': time.time()
        }

        return result
```

### 2.6 Enhanced Security Architecture

**Enterprise-Grade Security Framework**: ✅ **FULLY IMPLEMENTED**

```python
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from stellar_sdk.memo import HashMemo, TextMemo, IdMemo
import hvac  # HashiCorp Vault client

class EnterpriseSecurityFramework:
    """Enhanced security framework with modern standards"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.hsm_client = self._initialize_hsm()
        self.mpc_client = self._initialize_mpc() if config.use_mpc else None
        self.vault_client = self._initialize_vault() if config.use_vault else None

    def _initialize_hsm(self):
        """Initialize HSM client with multiple provider support"""
        if self.config.hsm_provider == "aws":
            return AWSCloudHSMClient(self.config.hsm_config)
        elif self.config.hsm_provider == "azure":
            return AzureKeyVaultClient(self.config.hsm_config)
        elif self.config.hsm_provider == "thales":
            return ThalesHSMClient(self.config.hsm_config)
        else:
            return LocalHSMClient(self.config.hsm_config)

    def _initialize_mpc(self):
        """Initialize Multi-Party Computation client"""
        return MPCClient(
            threshold=self.config.mpc_threshold,
            parties=self.config.mpc_parties
        )

    async def sign_transaction_secure(
        self,
        transaction: Transaction,
        key_id: str
    ) -> Transaction:
        """Enhanced transaction signing with multiple security layers"""

        # Pre-signing validation
        await self._validate_transaction_security(transaction)

        # Sign based on security level
        if self.config.security_level == "maximum" and self.mpc_client:
            # MPC signing for maximum security
            signature = await self.mpc_client.sign_transaction(
                transaction.hash(), key_id
            )
        elif self.hsm_client:
            # HSM signing for high security
            signature = await self.hsm_client.sign(
                transaction.hash(), key_id
            )
        else:
            # Encrypted local signing for development
            signature = await self._sign_with_encrypted_key(
                transaction, key_id
            )

        transaction.sign_hash_base64(signature)

        # Post-signing validation
        await self._validate_signed_transaction(transaction)

        return transaction

    async def validate_hardware_wallet(self, wallet_type: str) -> bool:
        """Hardware wallet integration validation"""

        supported_wallets = ["ledger", "trezor", "keepkey"]

        if wallet_type.lower() not in supported_wallets:
            return False

        # Test hardware wallet connection
        hw_client = HardwareWalletClient(wallet_type)
        return await hw_client.test_connection()

    async def implement_sep10_enhanced_auth(
        self,
        domain: str,
        account: str,
        client_domain: str = None
    ) -> str:
        """Enhanced SEP-10 authentication with additional security"""

        # Get challenge with enhanced parameters
        challenge = await stellar_web_authentication.get_challenge(
            server=self.chain_interface.horizon_server,
            server_account_id=await self._get_server_signing_key(domain),
            home_domain=domain,
            web_auth_domain=client_domain,
            client_account_id=account
        )

        # Sign challenge with secure key management
        signed_challenge = await self.sign_transaction_secure(
            challenge, account
        )

        # Submit and get token
        token = await stellar_web_authentication.verify_challenge(
            challenge_transaction=signed_challenge,
            server_account_id=await self._get_server_signing_key(domain),
            home_domain=domain,
            web_auth_domain=client_domain
        )

        return token
```

---

## Related Documents

This document is part of the Stellar SDEX Connector Technical Design v3.0 series:

1. **[01-architecture-foundation.md](./01-architecture-foundation.md)** - Architecture & Technical Foundation ⭐ *You are here*
2. [02-security-framework.md](./02-security-framework.md) - Security Framework
3. [03-monitoring-observability.md](./03-monitoring-observability.md) - Monitoring & Observability
4. [04-order-management.md](./04-order-management.md) - Order Management & Trading Logic
5. [05-asset-management.md](./05-asset-management.md) - Asset Management & Risk
6. [06-deployment-operations.md](./06-deployment-operations.md) - Production Deployment & Operations
7. [07-implementation-guide.md](./07-implementation-guide.md) - Implementation Guide & Checklists

**Cross-References:**
- `stellar_sdex_checklist_v3.md` - Implementation roadmap
- `PROJECT_STATUS.md` - Current project status
- `PHASE_1_COMPLETION_REPORT.md` - Phase 1 achievements