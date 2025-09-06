"""
Stellar Network Manager
Multi-network configuration and connection management for Stellar networks.
"""

import asyncio
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
import yaml
import aiohttp
from stellar_sdk import Server, Network, Asset, Keypair
from stellar_sdk.exceptions import ConnectionError as StellarConnectionError
import logging

logger = logging.getLogger(__name__)


class StellarNetwork(Enum):
    """Supported Stellar networks."""

    TESTNET = "testnet"
    FUTURENET = "futurenet"
    MAINNET = "mainnet"


class NetworkStatus(Enum):
    """Network connection status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class NetworkEndpoint:
    """Network endpoint configuration."""

    url: str
    timeout: int = 30
    retry_count: int = 3
    last_check: float = 0
    is_healthy: bool = True
    response_time: float = 0
    error_count: int = 0


@dataclass
class NetworkHealth:
    """Network health status."""

    status: NetworkStatus
    primary_healthy: bool
    fallback_count: int
    avg_response_time: float
    error_rate: float
    last_check: float = field(default_factory=time.time)


@dataclass
class StellarNetworkConfig:
    """Complete network configuration."""

    name: str
    network_passphrase: str
    horizon_endpoints: List[NetworkEndpoint]
    core_nodes: List[str]
    soroban_endpoints: List[NetworkEndpoint]
    history_archives: List[str]
    base_fee: int
    base_reserve: int
    max_tx_set_size: int
    ledger_version: int
    native_asset: str
    rate_limits: Dict[str, int]
    friendbot: Optional[Dict[str, Any]] = None
    well_known_assets: Dict[str, Any] = field(default_factory=dict)


class StellarNetworkManager:
    """Multi-network Stellar connection and configuration manager."""

    def __init__(self, config_path: str = "config/networks.yml"):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.network_configs: Dict[StellarNetwork, StellarNetworkConfig] = {}
        self.active_network: Optional[StellarNetwork] = None
        self.servers: Dict[StellarNetwork, Server] = {}
        self.health_status: Dict[StellarNetwork, NetworkHealth] = {}

        # Connection management
        self._health_check_task: Optional[asyncio.Task] = None
        self._session: Optional[aiohttp.ClientSession] = None

        # Performance tracking
        self._request_counts: Dict[str, int] = {}
        self._error_counts: Dict[str, int] = {}

        # Load configuration on initialization
        self.load_configuration()

    def load_configuration(self) -> None:
        """Load network configuration from YAML file."""
        try:
            with open(self.config_path, "r") as file:
                self.config = yaml.safe_load(file)

            stellar_config = self.config.get("stellar", {})

            # Parse network configurations
            for network_name, network_data in stellar_config.get("networks", {}).items():
                try:
                    network_enum = StellarNetwork(network_name)
                    self.network_configs[network_enum] = self._parse_network_config(
                        network_name, network_data
                    )
                except ValueError:
                    logger.warning(f"Unknown network: {network_name}")
                    continue

            # Set default network
            default_network = stellar_config.get("default_network", "testnet")
            try:
                self.active_network = StellarNetwork(default_network)
            except ValueError:
                self.active_network = StellarNetwork.TESTNET
                logger.warning(f"Invalid default network: {default_network}, using testnet")

            logger.info(f"Loaded configuration for {len(self.network_configs)} networks")

        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            self._create_default_config()
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise

    def _parse_network_config(self, name: str, data: Dict[str, Any]) -> StellarNetworkConfig:
        """Parse network configuration from YAML data."""

        # Parse Horizon endpoints
        horizon_config = data.get("horizon", {})
        horizon_endpoints = [
            NetworkEndpoint(
                url=horizon_config.get("primary", ""),
                timeout=horizon_config.get("timeout", 30),
                retry_count=horizon_config.get("retry_count", 3),
            )
        ]

        # Add fallback endpoints
        for fallback_url in horizon_config.get("fallbacks", []):
            horizon_endpoints.append(
                NetworkEndpoint(
                    url=fallback_url,
                    timeout=horizon_config.get("timeout", 30),
                    retry_count=horizon_config.get("retry_count", 3),
                )
            )

        # Parse Soroban endpoints
        soroban_config = data.get("soroban", {})
        soroban_endpoints = [
            NetworkEndpoint(
                url=soroban_config.get("primary", ""), timeout=soroban_config.get("timeout", 20)
            )
        ]

        for fallback_url in soroban_config.get("fallbacks", []):
            soroban_endpoints.append(
                NetworkEndpoint(url=fallback_url, timeout=soroban_config.get("timeout", 20))
            )

        return StellarNetworkConfig(
            name=data.get("name", name.title()),
            network_passphrase=data["network_passphrase"],
            horizon_endpoints=horizon_endpoints,
            core_nodes=data.get("core_nodes", []),
            soroban_endpoints=soroban_endpoints,
            history_archives=data.get("history_archives", []),
            base_fee=data.get("base_fee", 100),
            base_reserve=data.get("base_reserve", 5000000),
            max_tx_set_size=data.get("max_tx_set_size", 1000),
            ledger_version=data.get("ledger_version", 19),
            native_asset=data.get("native_asset", "XLM"),
            rate_limits=data.get("rate_limits", {}),
            friendbot=data.get("friendbot"),
            well_known_assets=data.get("well_known_assets", {}),
        )

    async def initialize(self) -> None:
        """Initialize network manager."""
        self._session = aiohttp.ClientSession()

        # Create Server instances for each network
        for network, config in self.network_configs.items():
            if config.horizon_endpoints:
                primary_endpoint = config.horizon_endpoints[0]
                self.servers[network] = Server(
                    horizon_url=primary_endpoint.url, client=self._session
                )

        # Start health monitoring
        if (
            self.config.get("stellar", {})
            .get("monitoring", {})
            .get("health_checks", {})
            .get("enabled", True)
        ):
            interval = (
                self.config.get("stellar", {})
                .get("monitoring", {})
                .get("health_checks", {})
                .get("interval", 30)
            )
            self._health_check_task = asyncio.create_task(self._health_check_loop(interval))

        logger.info("Stellar Network Manager initialized")

    async def cleanup(self) -> None:
        """Cleanup network manager resources."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        if self._session:
            await self._session.close()

        logger.info("Stellar Network Manager cleaned up")

    def get_server(self, network: Optional[StellarNetwork] = None) -> Server:
        """Get Stellar Server instance for specified network."""
        target_network = network or self.active_network

        if target_network not in self.servers:
            raise ValueError(f"Server not available for network: {target_network}")

        return self.servers[target_network]

    def get_network_config(self, network: Optional[StellarNetwork] = None) -> StellarNetworkConfig:
        """Get network configuration."""
        target_network = network or self.active_network

        if target_network not in self.network_configs:
            raise ValueError(f"Configuration not available for network: {target_network}")

        return self.network_configs[target_network]

    def get_network_passphrase(self, network: Optional[StellarNetwork] = None) -> str:
        """Get network passphrase."""
        config = self.get_network_config(network)
        return config.network_passphrase

    def get_network_object(self, network: Optional[StellarNetwork] = None) -> Network:
        """Get Stellar SDK Network object."""
        passphrase = self.get_network_passphrase(network)
        return Network(passphrase)

    async def switch_network(self, network: StellarNetwork) -> None:
        """Switch to a different Stellar network."""
        if network not in self.network_configs:
            raise ValueError(f"Network not configured: {network}")

        # Check if network is healthy before switching
        health = await self.check_network_health(network)
        if health.status == NetworkStatus.DOWN:
            raise ConnectionError(f"Cannot switch to unhealthy network: {network}")

        old_network = self.active_network
        self.active_network = network

        logger.info(f"Switched from {old_network} to {network}")

    async def check_network_health(self, network: Optional[StellarNetwork] = None) -> NetworkHealth:
        """Check health of specified network."""
        target_network = network or self.active_network
        config = self.get_network_config(target_network)

        # Check primary Horizon endpoint
        primary_endpoint = config.horizon_endpoints[0]
        primary_healthy = await self._check_endpoint_health(primary_endpoint)

        # Check fallback endpoints
        fallback_healthy_count = 0
        total_response_times = []
        total_errors = 0

        for endpoint in config.horizon_endpoints[1:]:
            is_healthy = await self._check_endpoint_health(endpoint)
            if is_healthy:
                fallback_healthy_count += 1
            total_response_times.append(endpoint.response_time)
            total_errors += endpoint.error_count

        # Calculate overall health
        avg_response_time = (
            sum(total_response_times) / len(total_response_times) if total_response_times else 0
        )
        error_rate = total_errors / len(config.horizon_endpoints) if config.horizon_endpoints else 0

        # Determine status
        if primary_healthy and fallback_healthy_count >= len(config.horizon_endpoints) // 2:
            status = NetworkStatus.HEALTHY
        elif primary_healthy or fallback_healthy_count > 0:
            status = NetworkStatus.DEGRADED
        else:
            status = NetworkStatus.DOWN

        health = NetworkHealth(
            status=status,
            primary_healthy=primary_healthy,
            fallback_count=fallback_healthy_count,
            avg_response_time=avg_response_time,
            error_rate=error_rate,
        )

        self.health_status[target_network] = health
        return health

    async def _check_endpoint_health(self, endpoint: NetworkEndpoint) -> bool:
        """Check health of a single endpoint."""
        try:
            start_time = time.time()

            async with self._session.get(
                f"{endpoint.url}/", timeout=aiohttp.ClientTimeout(total=endpoint.timeout)
            ) as response:
                endpoint.response_time = (time.time() - start_time) * 1000  # ms
                endpoint.last_check = time.time()

                if response.status == 200:
                    endpoint.is_healthy = True
                    endpoint.error_count = 0
                    return True
                else:
                    endpoint.is_healthy = False
                    endpoint.error_count += 1
                    return False

        except Exception as e:
            endpoint.is_healthy = False
            endpoint.error_count += 1
            endpoint.response_time = endpoint.timeout * 1000  # Timeout as response time
            endpoint.last_check = time.time()
            logger.warning(f"Endpoint health check failed for {endpoint.url}: {e}")
            return False

    async def _health_check_loop(self, interval: int) -> None:
        """Background health check loop."""
        while True:
            try:
                for network in self.network_configs.keys():
                    await self.check_network_health(network)

                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(interval)

    async def get_account_balance(
        self, account_id: str, network: Optional[StellarNetwork] = None
    ) -> Dict[str, Any]:
        """Get account balance from specified network."""
        server = self.get_server(network)

        try:
            account = await server.accounts().account_id(account_id).call()
            return {
                "account_id": account_id,
                "balances": account.get("balances", []),
                "network": (network or self.active_network).value,
            }
        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            raise

    async def fund_test_account(
        self, account_id: str, network: Optional[StellarNetwork] = None
    ) -> bool:
        """Fund test account using friendbot (testnet/futurenet only)."""
        target_network = network or self.active_network
        config = self.get_network_config(target_network)

        if not config.friendbot or not config.friendbot.get("enabled"):
            raise ValueError(f"Friendbot not available for network: {target_network}")

        friendbot_url = config.friendbot["url"]

        try:
            async with self._session.get(f"{friendbot_url}?addr={account_id}") as response:
                if response.status == 200:
                    logger.info(f"Successfully funded test account: {account_id}")
                    return True
                else:
                    logger.error(f"Friendbot funding failed: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Error funding test account: {e}")
            return False

    def get_well_known_asset(
        self, asset_code: str, network: Optional[StellarNetwork] = None
    ) -> Optional[Asset]:
        """Get well-known asset for specified network."""
        target_network = network or self.active_network
        config = self.get_network_config(target_network)

        well_known_assets = self.config.get("stellar", {}).get("well_known_assets", {})
        network_assets = well_known_assets.get(target_network.value, {})

        asset_info = network_assets.get(asset_code)
        if not asset_info:
            return None

        if asset_code == config.native_asset:
            return Asset.native()
        else:
            return Asset(asset_info["code"], asset_info["issuer"])

    def get_supported_trading_pairs(self, network: Optional[StellarNetwork] = None) -> List[str]:
        """Get supported trading pairs for network."""
        target_network = network or self.active_network

        trading_pairs = self.config.get("stellar", {}).get("trading_pairs", {})
        network_pairs = trading_pairs.get(target_network.value, {})

        # Return popular pairs + supported pairs
        popular = network_pairs.get("popular", [])
        supported = network_pairs.get("supported", [])

        return list(set(popular + supported))

    def _create_default_config(self) -> None:
        """Create default configuration if config file doesn't exist."""
        default_config = {
            "stellar": {
                "default_network": "testnet",
                "networks": {
                    "testnet": {
                        "name": "Stellar Testnet",
                        "network_passphrase": "Test SDF Network ; September 2015",
                        "horizon": {
                            "primary": "https://horizon-testnet.stellar.org",
                            "timeout": 30,
                            "retry_count": 3,
                        },
                        "base_fee": 100,
                        "base_reserve": 5000000,
                        "native_asset": "XLM",
                        "friendbot": {"enabled": True, "url": "https://friendbot.stellar.org"},
                    }
                },
            }
        }

        self.config = default_config
        logger.info("Created default configuration")

    def get_network_statistics(self) -> Dict[str, Any]:
        """Get network statistics and health information."""
        stats = {
            "active_network": self.active_network.value if self.active_network else None,
            "configured_networks": list(network.value for network in self.network_configs.keys()),
            "health_status": {},
            "request_counts": self._request_counts.copy(),
            "error_counts": self._error_counts.copy(),
        }

        for network, health in self.health_status.items():
            stats["health_status"][network.value] = {
                "status": health.status.value,
                "primary_healthy": health.primary_healthy,
                "fallback_count": health.fallback_count,
                "avg_response_time": health.avg_response_time,
                "error_rate": health.error_rate,
                "last_check": health.last_check,
            }

        return stats
