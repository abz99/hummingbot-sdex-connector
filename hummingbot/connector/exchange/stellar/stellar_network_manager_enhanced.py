"""
Enhanced Stellar Network Manager
Integrated multi-network configuration and connection management with all improvements.
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from stellar_sdk import Account, Asset, Keypair, Network, Server
from stellar_sdk.exceptions import ConnectionError as StellarConnectionError

from .stellar_asset_verification import DEFAULT_ASSET_DIRECTORIES, StellarAssetVerifier

# Import our enhanced modules
from .stellar_config_models import StellarConfigValidator, StellarMainConfig, StellarNetworkType
from .stellar_connection_manager import EndpointConfig, StellarConnectionManager
from .stellar_error_classification import ErrorContext, StellarErrorManager
from .stellar_health_monitor import HealthCheckType, HealthStatus, StellarHealthMonitor
from .stellar_logging import get_stellar_logger, LogCategory, with_correlation_id
from .stellar_metrics import get_stellar_metrics


class NetworkStatus(Enum):
    """Network connection status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class NetworkHealth:
    """Network health status with enhanced metrics."""

    status: NetworkStatus
    primary_healthy: bool
    fallback_count: int
    avg_response_time: float
    error_rate: float
    last_check: float = field(default_factory=time.time)
    endpoints_healthy: int = 0
    circuit_breakers_open: int = 0
    total_requests: int = 0
    successful_requests: int = 0


class EnhancedStellarNetworkManager:
    """
    Enhanced multi-network Stellar connection and configuration manager.
    Integrates all improvements: validation, logging, metrics, health monitoring, etc.
    """

    def __init__(
        self,
        config_path: str = "config/networks.yml",
        enable_health_monitoring: bool = True,
        enable_asset_verification: bool = True,
        enable_metrics: bool = True,
    ):
        # Configuration
        self.config_path = config_path
        self.enable_health_monitoring = enable_health_monitoring
        self.enable_asset_verification = enable_asset_verification
        self.enable_metrics = enable_metrics

        # Enhanced components
        self.logger = get_stellar_logger()
        self.metrics = get_stellar_metrics() if enable_metrics else None
        self.error_manager = StellarErrorManager()
        self.config_validator = StellarConfigValidator()

        # Network management
        self.validated_config: Optional[StellarMainConfig] = None
        self.active_network: Optional[StellarNetworkType] = None
        self.connection_manager: Optional[StellarConnectionManager] = None
        self.health_monitor: Optional[StellarHealthMonitor] = None
        self.asset_verifier: Optional[StellarAssetVerifier] = None

        # Stellar SDK integration
        self.servers: Dict[StellarNetworkType, Server] = {}
        self.health_status: Dict[StellarNetworkType, NetworkHealth] = {}

        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        self._running = False

        # Load and validate configuration
        self._load_and_validate_configuration()

    def _load_and_validate_configuration(self) -> None:
        """Load and validate network configuration."""
        with with_correlation_id() as logger:
            logger.info(
                f"Loading network configuration from {self.config_path}",
                category=LogCategory.CONFIGURATION,
            )

            try:
                # Load raw configuration
                config_path = Path(self.config_path)
                if not config_path.exists():
                    raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

                with open(config_path, "r") as file:
                    raw_config = yaml.safe_load(file)

                # Validate configuration using Pydantic models
                self.validated_config = self.config_validator.validate_config(raw_config)

                # Set active network
                self.active_network = self.validated_config.default_network

                logger.info(
                    "Configuration validated successfully",
                    category=LogCategory.CONFIGURATION,
                    networks=list(self.validated_config.networks.keys()),
                    default_network=self.active_network.value,
                )

                # Check for validation warnings
                warnings = self.config_validator.validate_network_connectivity(
                    self.validated_config
                )
                for warning in warnings:
                    logger.warning(warning, category=LogCategory.CONFIGURATION)

            except Exception as e:
                self.logger.error(
                    "Failed to load or validate configuration",
                    category=LogCategory.CONFIGURATION,
                    exception=e,
                )
                raise

    async def initialize(self) -> None:
        """Initialize the enhanced network manager."""
        if self._running:
            return

        self._running = True

        with with_correlation_id() as logger:
            logger.info(
                "Initializing enhanced Stellar network manager",
                category=LogCategory.NETWORK,
                networks=len(self.validated_config.networks),
                health_monitoring=self.enable_health_monitoring,
                asset_verification=self.enable_asset_verification,
            )

            try:
                # Initialize connection manager
                await self._initialize_connection_manager()

                # Initialize health monitoring
                if self.enable_health_monitoring:
                    await self._initialize_health_monitoring()

                # Initialize asset verification
                if self.enable_asset_verification:
                    await self._initialize_asset_verification()

                # Initialize Stellar SDK servers
                await self._initialize_stellar_servers()

                # Start background tasks
                if self.enable_metrics:
                    await self._start_background_tasks()

                logger.info(
                    "Network manager initialization completed", category=LogCategory.NETWORK
                )

            except Exception as e:
                logger.error(
                    "Network manager initialization failed",
                    category=LogCategory.NETWORK,
                    exception=e,
                )
                await self.cleanup()
                raise

    async def cleanup(self) -> None:
        """Clean up all resources."""
        if not self._running:
            return

        self._running = False

        with with_correlation_id() as logger:
            logger.info("Cleaning up network manager", category=LogCategory.NETWORK)

            # Cancel background tasks
            for task in self._background_tasks:
                task.cancel()

            if self._background_tasks:
                await asyncio.gather(*self._background_tasks, return_exceptions=True)
                self._background_tasks.clear()

            # Cleanup components
            if self.connection_manager:
                await self.connection_manager.stop()

            if self.health_monitor:
                await self.health_monitor.stop()

            if self.asset_verifier:
                await self.asset_verifier.__aexit__(None, None, None)

            if self.metrics:
                await self.metrics.stop_background_metrics_collection()

            logger.info("Network manager cleanup completed", category=LogCategory.NETWORK)

    async def _initialize_connection_manager(self) -> None:
        """Initialize the connection manager with all endpoints."""
        from .stellar_connection_manager import ConnectionProtocol, LoadBalanceStrategy

        self.connection_manager = StellarConnectionManager(
            load_balance_strategy=LoadBalanceStrategy.RESPONSE_TIME, enable_http2=True
        )

        # Add endpoint groups for each network
        for network_type, network_config in self.validated_config.networks.items():
            endpoints = []

            # Add Horizon endpoints
            horizon_config = network_config.horizon
            primary_endpoint = EndpointConfig(
                url=str(horizon_config.primary),
                priority=1,
                timeout=horizon_config.timeout,
                protocol=ConnectionProtocol.HTTP_2,
            )
            endpoints.append(primary_endpoint)

            for i, fallback_url in enumerate(horizon_config.fallbacks):
                fallback_endpoint = EndpointConfig(
                    url=str(fallback_url),
                    priority=i + 2,
                    timeout=horizon_config.timeout,
                    protocol=ConnectionProtocol.HTTP_2,
                )
                endpoints.append(fallback_endpoint)

            self.connection_manager.add_endpoint_group(f"horizon_{network_type.value}", endpoints)

            # Add Soroban endpoints
            soroban_endpoints = []
            soroban_config = network_config.soroban

            soroban_primary = EndpointConfig(
                url=str(soroban_config.primary),
                priority=1,
                timeout=soroban_config.timeout,
                protocol=ConnectionProtocol.HTTP_2,
            )
            soroban_endpoints.append(soroban_primary)

            for i, fallback_url in enumerate(soroban_config.fallbacks):
                soroban_fallback = EndpointConfig(
                    url=str(fallback_url),
                    priority=i + 2,
                    timeout=soroban_config.timeout,
                    protocol=ConnectionProtocol.HTTP_2,
                )
                soroban_endpoints.append(soroban_fallback)

            self.connection_manager.add_endpoint_group(
                f"soroban_{network_type.value}", soroban_endpoints
            )

        await self.connection_manager.start()

    async def _initialize_health_monitoring(self) -> None:
        """Initialize health monitoring for all endpoints."""
        self.health_monitor = StellarHealthMonitor(
            check_interval=self.validated_config.health_check_interval,
            failure_threshold=self.validated_config.max_retries,
            recovery_threshold=2,
        )

        # Add all endpoints for monitoring
        for network_type, network_config in self.validated_config.networks.items():
            # Monitor Horizon endpoints
            self.health_monitor.add_endpoint(
                str(network_config.horizon.primary), HealthCheckType.HORIZON_API
            )

            for fallback_url in network_config.horizon.fallbacks:
                self.health_monitor.add_endpoint(str(fallback_url), HealthCheckType.HORIZON_API)

            # Monitor Soroban endpoints
            self.health_monitor.add_endpoint(
                str(network_config.soroban.primary), HealthCheckType.SOROBAN_RPC
            )

            for fallback_url in network_config.soroban.fallbacks:
                self.health_monitor.add_endpoint(str(fallback_url), HealthCheckType.SOROBAN_RPC)

            # Monitor Friendbot if enabled
            if network_config.friendbot and network_config.friendbot.enabled:
                self.health_monitor.add_endpoint(
                    str(network_config.friendbot.url), HealthCheckType.FRIENDBOT
                )

        # Add failure/recovery callbacks
        self.health_monitor.add_failure_callback(self._on_endpoint_failure)
        self.health_monitor.add_recovery_callback(self._on_endpoint_recovery)

        await self.health_monitor.start()

    async def _initialize_asset_verification(self) -> None:
        """Initialize asset verification system."""
        self.asset_verifier = StellarAssetVerifier()
        await self.asset_verifier.__aenter__()

        # Add default asset directories
        for directory in DEFAULT_ASSET_DIRECTORIES:
            self.asset_verifier.add_asset_directory(directory)

        # Pre-verify well-known assets
        verification_tasks = []
        for network_name, assets in self.validated_config.well_known_assets.items():
            for asset_code, asset_config in assets.items():
                task = self.asset_verifier.verify_asset(
                    asset_config.code, asset_config.issuer, asset_config.domain
                )
                verification_tasks.append(task)

        if verification_tasks:
            results = await asyncio.gather(*verification_tasks, return_exceptions=True)
            verified_count = sum(
                1
                for result in results
                if not isinstance(result, Exception)
                and hasattr(result, "status")
                and result.status.name == "VERIFIED"
            )

            self.logger.info(
                f"Pre-verified {verified_count} well-known assets",
                category=LogCategory.SECURITY,
                total_assets=len(verification_tasks),
                verified_count=verified_count,
            )

    async def _initialize_stellar_servers(self) -> None:
        """Initialize Stellar SDK servers for each network."""
        for network_type, network_config in self.validated_config.networks.items():
            try:
                # Create server with primary Horizon endpoint
                server = Server(
                    horizon_url=str(network_config.horizon.primary),
                    client=None,  # Will use our connection manager eventually
                )

                self.servers[network_type] = server

                # Initialize network health status
                self.health_status[network_type] = NetworkHealth(
                    status=NetworkStatus.UNKNOWN,
                    primary_healthy=True,
                    fallback_count=len(network_config.horizon.fallbacks),
                    avg_response_time=0.0,
                    error_rate=0.0,
                )

                self.logger.info(
                    f"Initialized server for {network_type.value}",
                    category=LogCategory.NETWORK,
                    horizon_url=network_config.horizon.primary,
                )

            except Exception as e:
                self.logger.error(
                    f"Failed to initialize server for {network_type.value}",
                    category=LogCategory.NETWORK,
                    exception=e,
                )

    async def _start_background_tasks(self) -> None:
        """Start background monitoring and metrics tasks."""
        if self.metrics:
            self._background_tasks.append(asyncio.create_task(self._network_metrics_loop()))

            await self.metrics.start_background_metrics_collection()

    async def _network_metrics_loop(self) -> None:
        """Background task to collect network-specific metrics."""
        while self._running:
            try:
                # Update network health metrics
                for network_type, health in self.health_status.items():
                    if self.health_monitor:
                        # Get health summary for this network's endpoints
                        summary = self.health_monitor.get_health_summary()

                        self.metrics.set_endpoint_health(
                            network=network_type.value,
                            endpoint_type="network",
                            url="overall",
                            is_healthy=health.status == NetworkStatus.HEALTHY,
                        )

                # Update connection metrics
                if self.connection_manager:
                    stats = self.connection_manager.get_connection_stats()
                    for network_type in self.validated_config.networks:
                        self.metrics.set_active_connections(
                            network=network_type.value,
                            count=stats.get("total_active_connections", 0),
                        )

                await asyncio.sleep(30)  # Update every 30 seconds

            except Exception as e:
                self.logger.error(
                    "Error in network metrics loop", category=LogCategory.METRICS, exception=e
                )
                await asyncio.sleep(60)

    async def _on_endpoint_failure(self, endpoint: str, result) -> None:
        """Handle endpoint failure notifications."""
        self.logger.warning(
            f"Endpoint failure detected: {endpoint}",
            category=LogCategory.NETWORK,
            error_message=result.error_message,
        )

        # Update network health status
        await self._update_network_health()

        # Record metrics
        if self.metrics:
            # Determine network from endpoint
            network = self._determine_network_from_endpoint(endpoint)
            if network:
                self.metrics.record_network_error(
                    network=network.value,
                    endpoint_type="horizon" if "horizon" in endpoint else "soroban",
                    error_type="connection_failure",
                )

    async def _on_endpoint_recovery(self, endpoint: str, result) -> None:
        """Handle endpoint recovery notifications."""
        self.logger.info(f"Endpoint recovery detected: {endpoint}", category=LogCategory.NETWORK)

        # Update network health status
        await self._update_network_health()

    def _determine_network_from_endpoint(self, endpoint: str) -> Optional[StellarNetworkType]:
        """Determine network type from endpoint URL."""
        for network_type, network_config in self.validated_config.networks.items():
            if (
                str(network_config.horizon.primary) == endpoint
                or endpoint in [str(url) for url in network_config.horizon.fallbacks]
                or str(network_config.soroban.primary) == endpoint
                or endpoint in [str(url) for url in network_config.soroban.fallbacks]
            ):
                return network_type
        return None

    async def _update_network_health(self) -> None:
        """Update overall network health status."""
        if not self.health_monitor:
            return

        for network_type in self.validated_config.networks:
            health_summary = self.health_monitor.get_health_summary()

            # Update network health based on endpoint health
            network_health = self.health_status.get(network_type)
            if network_health:
                if health_summary["healthy_endpoints"] == health_summary["total_endpoints"]:
                    network_health.status = NetworkStatus.HEALTHY
                elif health_summary["healthy_endpoints"] > 0:
                    network_health.status = NetworkStatus.DEGRADED
                else:
                    network_health.status = NetworkStatus.DOWN

                network_health.endpoints_healthy = health_summary["healthy_endpoints"]
                network_health.last_check = time.time()

    # Public API methods

    async def switch_network(self, network: StellarNetworkType) -> None:
        """Switch to a different network."""
        if network not in self.validated_config.networks:
            raise ValueError(f"Network {network.value} is not configured")

        with with_correlation_id() as logger:
            logger.info(
                f"Switching from {self.active_network.value if self.active_network else 'none'} to {network.value}",
                category=LogCategory.NETWORK,
            )

            # Check network health before switching
            network_health = await self.check_network_health(network)
            if network_health.status == NetworkStatus.DOWN:
                logger.warning(
                    f"Switching to unhealthy network: {network.value}",
                    category=LogCategory.NETWORK,
                    health_status=network_health.status.value,
                )

            self.active_network = network

            logger.info(
                f"Network switched to {network.value}",
                category=LogCategory.NETWORK,
                health_status=network_health.status.value,
            )

    def get_server(self, network: Optional[StellarNetworkType] = None) -> Server:
        """Get Stellar SDK server for the specified network."""
        target_network = network or self.active_network

        if not target_network or target_network not in self.servers:
            raise ValueError(f"Server not available for network: {target_network}")

        return self.servers[target_network]

    def get_network_config(self, network: Optional[StellarNetworkType] = None):
        """Get configuration for the specified network."""
        target_network = network or self.active_network

        if not target_network or target_network not in self.validated_config.networks:
            raise ValueError(f"Configuration not available for network: {target_network}")

        return self.validated_config.networks[target_network]

    async def check_network_health(
        self, network: Optional[StellarNetworkType] = None
    ) -> NetworkHealth:
        """Check health of the specified network."""
        target_network = network or self.active_network

        if target_network not in self.health_status:
            return NetworkHealth(
                status=NetworkStatus.UNKNOWN,
                primary_healthy=False,
                fallback_count=0,
                avg_response_time=0.0,
                error_rate=1.0,
            )

        return self.health_status[target_network]

    async def verify_asset(
        self, asset_code: str, issuer: str, network: Optional[StellarNetworkType] = None
    ):
        """Verify an asset using the asset verification system."""
        if not self.asset_verifier:
            raise RuntimeError("Asset verification is not enabled")

        target_network = network or self.active_network

        with with_correlation_id() as logger:
            logger.info(
                f"Verifying asset {asset_code} on {target_network.value}",
                category=LogCategory.SECURITY,
                asset_code=asset_code,
                issuer=issuer[:8] + "...",
            )

            result = await self.asset_verifier.verify_asset(asset_code, issuer)

            # Record metrics
            if self.metrics:
                verification_success = result.status.name == "VERIFIED"
                self.metrics.record_network_request(
                    "asset_verification",
                    "stellar_toml",
                    "success" if verification_success else "error",
                    1.0,  # Duration would be tracked internally
                )

            return result

    async def fund_test_account(
        self, public_key: str, network: Optional[StellarNetworkType] = None
    ) -> bool:
        """Fund a test account using Friendbot (testnet/futurenet only)."""
        target_network = network or self.active_network
        network_config = self.get_network_config(target_network)

        if not network_config.friendbot or not network_config.friendbot.enabled:
            raise ValueError(f"Friendbot not available for network: {target_network.value}")

        if not self.connection_manager:
            raise RuntimeError("Connection manager not initialized")

        with with_correlation_id() as logger:
            logger.info(
                f"Funding test account on {target_network.value}",
                category=LogCategory.NETWORK,
                account=public_key[:8] + "...",
            )

            try:
                # Use connection manager to make friendbot request
                service_name = f"friendbot_{target_network.value}"

                # Add friendbot as endpoint if not already added
                if service_name not in self.connection_manager.endpoints:
                    friendbot_endpoints = [
                        EndpointConfig(url=str(network_config.friendbot.url), priority=1)
                    ]
                    self.connection_manager.add_endpoint_group(service_name, friendbot_endpoints)

                response = await self.connection_manager.request(
                    service_name, "GET", f"?addr={public_key}"
                )

                success = response.status == 200

                if success:
                    logger.info(
                        "Test account funded successfully",
                        category=LogCategory.NETWORK,
                        account=public_key[:8] + "...",
                    )
                else:
                    logger.warning(
                        "Test account funding failed",
                        category=LogCategory.NETWORK,
                        status_code=response.status,
                        account=public_key[:8] + "...",
                    )

                return success

            except Exception as e:
                logger.error(
                    "Error funding test account", category=LogCategory.NETWORK, exception=e
                )
                return False

    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the network manager."""
        status = {
            "running": self._running,
            "active_network": self.active_network.value if self.active_network else None,
            "configured_networks": (
                list(self.validated_config.networks.keys()) if self.validated_config else []
            ),
            "health_monitoring_enabled": self.enable_health_monitoring,
            "asset_verification_enabled": self.enable_asset_verification,
            "metrics_enabled": self.enable_metrics,
            "network_health": {},
            "connection_stats": {},
            "background_tasks": len(self._background_tasks),
        }

        # Add network health information
        for network_type, health in self.health_status.items():
            status["network_health"][network_type.value] = {
                "status": health.status.value,
                "primary_healthy": health.primary_healthy,
                "fallback_count": health.fallback_count,
                "avg_response_time": health.avg_response_time,
                "error_rate": health.error_rate,
                "endpoints_healthy": health.endpoints_healthy,
            }

        # Add connection statistics
        if self.connection_manager:
            status["connection_stats"] = self.connection_manager.get_connection_stats()

        # Add health monitor summary
        if self.health_monitor:
            status["health_monitor"] = self.health_monitor.get_health_summary()

        return status
