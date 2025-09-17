"""
Stellar Configuration Models
Pydantic models for comprehensive configuration validation.
"""

from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, HttpUrl, ValidationInfo


class StellarNetworkType(str, Enum):
    """Stellar network types."""

    TESTNET = "testnet"
    FUTURENET = "futurenet"
    MAINNET = "mainnet"


class NetworkEndpointConfig(BaseModel):
    """Network endpoint configuration with validation."""

    primary: HttpUrl = Field(..., description="Primary endpoint URL")
    fallbacks: List[HttpUrl] = Field(default_factory=list, description="Fallback endpoint URLs")
    timeout: int = Field(default=30, ge=1, le=300, description="Request timeout in seconds")
    retry_count: int = Field(default=3, ge=1, le=10, description="Number of retries")


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""

    requests_per_second: int = Field(..., ge=1, le=10000, description="Requests per second limit")
    burst_limit: int = Field(..., ge=1, le=50000, description="Burst limit for requests")


class FriendbotConfig(BaseModel):
    """Friendbot configuration for test networks."""

    enabled: bool = Field(default=False, description="Whether friendbot is enabled")
    url: Optional[HttpUrl] = Field(None, description="Friendbot URL")
    funding_amount: Optional[int] = Field(None, ge=1, description="Funding amount in XLM")

    @field_validator("url")
    @classmethod
    def validate_url_if_enabled(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        if info.data.get("enabled", False) and not v:
            raise ValueError("Friendbot URL is required when enabled=True")
        return v


class AssetConfig(BaseModel):
    """Asset configuration with validation."""

    code: str = Field(..., min_length=1, max_length=12, description="Asset code")
    issuer: str = Field(..., min_length=56, max_length=56, description="Asset issuer public key")
    domain: str = Field(..., description="Asset domain")
    verified: bool = Field(default=False, description="Whether asset is verified")

    @field_validator("issuer")
    @classmethod
    def validate_stellar_public_key(cls, v: str) -> str:
        """Validate Stellar public key format."""
        if not v.startswith("G") or len(v) != 56:
            raise ValueError("Invalid Stellar public key format")
        return v


class StellarNetworkConfig(BaseModel):
    """Complete network configuration with validation."""

    name: str = Field(..., description="Network display name")
    network_passphrase: str = Field(..., description="Network passphrase")
    horizon: NetworkEndpointConfig = Field(..., description="Horizon API endpoints")
    core_nodes: List[str] = Field(default_factory=list, description="Core node endpoints")
    soroban: NetworkEndpointConfig = Field(..., description="Soroban RPC endpoints")
    history_archives: List[HttpUrl] = Field(
        default_factory=list, description="History archive URLs"
    )

    # Network characteristics
    base_fee: int = Field(default=100, ge=100, description="Base fee in stroops")
    base_reserve: int = Field(default=5000000, ge=5000000, description="Base reserve in stroops")
    max_tx_set_size: int = Field(default=1000, ge=1, description="Maximum transaction set size")
    ledger_version: int = Field(default=19, ge=1, description="Ledger version")

    # Assets
    native_asset: str = Field(default="XLM", description="Native asset code")
    fee_asset: str = Field(default="XLM", description="Fee asset code")

    # Rate limiting
    rate_limits: RateLimitConfig = Field(..., description="Rate limiting configuration")

    # Optional configurations
    friendbot: Optional[FriendbotConfig] = Field(None, description="Friendbot configuration")
    production: Optional[Dict[str, Any]] = Field(None, description="Production-specific settings")
    well_known_assets: Dict[str, AssetConfig] = Field(
        default_factory=dict, description="Well-known assets"
    )


class PerformanceConfig(BaseModel):
    """Performance configuration with validation."""

    connection_pool_size: int = Field(default=20, ge=1, le=1000, description="Connection pool size")
    max_concurrent_requests: int = Field(
        default=50, ge=1, le=1000, description="Max concurrent requests"
    )
    request_timeout: int = Field(default=30, ge=1, le=300, description="Request timeout")
    retry_backoff_base: int = Field(default=2, ge=1, le=10, description="Retry backoff base")
    max_retry_delay: int = Field(default=60, ge=1, le=600, description="Max retry delay")


class CacheConfig(BaseModel):
    """Caching configuration."""

    account_info_ttl: int = Field(
        default=30, ge=1, le=3600, description="Account info TTL in seconds"
    )
    order_book_ttl: int = Field(default=5, ge=1, le=300, description="Order book TTL in seconds")
    asset_info_ttl: int = Field(default=300, ge=1, le=7200, description="Asset info TTL in seconds")


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""

    failure_threshold: int = Field(default=5, ge=1, le=100, description="Failure threshold")
    recovery_timeout: int = Field(
        default=60, ge=1, le=3600, description="Recovery timeout in seconds"
    )
    half_open_max_calls: int = Field(default=3, ge=1, le=20, description="Half-open max calls")


class MonitoringConfig(BaseModel):
    """Monitoring and alerting configuration."""

    enabled: bool = Field(default=True, description="Enable monitoring")
    interval: int = Field(default=30, ge=1, le=3600, description="Health check interval in seconds")
    endpoints: List[str] = Field(default_factory=list, description="Endpoints to monitor")


class AlertConfig(BaseModel):
    """Alert configuration."""

    network_down_threshold: int = Field(
        default=3, ge=1, le=100, description="Network down threshold"
    )
    high_latency_threshold: int = Field(
        default=5000, ge=100, le=60000, description="High latency threshold in ms"
    )
    error_rate_threshold: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Error rate threshold (0-1)"
    )


class SecurityConfig(BaseModel):
    """Security configuration."""

    verify_certificates: bool = Field(default=True, description="Verify SSL certificates")
    min_tls_version: str = Field(default="1.2", description="Minimum TLS version")
    request_signing_enabled: bool = Field(default=True, description="Enable request signing")
    algorithm: str = Field(default="ed25519", description="Signing algorithm")


class AssetDirectoryConfig(BaseModel):
    """Asset directory configuration."""

    name: str = Field(..., description="Directory name")
    url: HttpUrl = Field(..., description="Directory URL")
    priority: int = Field(default=1, ge=1, le=100, description="Priority level")


class TradingPairsConfig(BaseModel):
    """Trading pairs configuration."""

    popular: List[str] = Field(default_factory=list, description="Popular trading pairs")
    supported: List[str] = Field(default_factory=list, description="Supported trading pairs")


class AMMLiquidityConfig(BaseModel):
    """AMM and liquidity configuration."""

    enabled: bool = Field(default=True, description="Enable AMM features")
    min_liquidity: int = Field(
        default=1000, ge=1, description="Minimum liquidity in XLM equivalent"
    )


class AMMConfig(BaseModel):
    """AMM configuration."""

    contracts: Dict[str, Dict[str, str]] = Field(
        default_factory=dict, description="AMM contracts by network"
    )
    rewards: AMMLiquidityConfig = Field(
        default_factory=AMMLiquidityConfig, description="Liquidity rewards config"
    )


class StellarMainConfig(BaseModel):
    """Main Stellar configuration with comprehensive validation."""

    default_network: StellarNetworkType = Field(
        default=StellarNetworkType.TESTNET, description="Default network"
    )
    auto_failover: bool = Field(default=True, description="Enable automatic failover")
    health_check_interval: int = Field(
        default=30, ge=1, le=3600, description="Health check interval"
    )
    max_retries: int = Field(default=3, ge=1, le=10, description="Maximum retries")
    timeout_seconds: int = Field(default=10, ge=1, le=300, description="Default timeout")

    # Network configurations
    networks: Dict[StellarNetworkType, StellarNetworkConfig] = Field(
        ..., description="Network configurations"
    )

    # Asset and trading configuration
    asset_directories: List[AssetDirectoryConfig] = Field(
        default_factory=list, description="Asset directories"
    )
    well_known_assets: Dict[str, Dict[str, AssetConfig]] = Field(
        default_factory=dict, description="Well-known assets by network"
    )
    trading_pairs: Dict[str, TradingPairsConfig] = Field(
        default_factory=dict, description="Trading pairs by network"
    )

    # AMM configuration
    amm: AMMConfig = Field(default_factory=AMMConfig, description="AMM configuration")

    # Performance and reliability
    performance: PerformanceConfig = Field(
        default_factory=PerformanceConfig, description="Performance settings"
    )
    cache: CacheConfig = Field(default_factory=CacheConfig, description="Cache settings")
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=CircuitBreakerConfig, description="Circuit breaker settings"
    )

    # Monitoring and security
    monitoring: MonitoringConfig = Field(
        default_factory=MonitoringConfig, description="Monitoring settings"
    )
    alerts: AlertConfig = Field(default_factory=AlertConfig, description="Alert settings")
    security: SecurityConfig = Field(
        default_factory=SecurityConfig, description="Security settings"
    )

    @field_validator("networks")
    @classmethod
    def validate_default_network_exists(
        cls, v: Dict[StellarNetworkType, StellarNetworkConfig], info: ValidationInfo
    ) -> Dict[StellarNetworkType, StellarNetworkConfig]:
        """Ensure default network exists in networks configuration."""
        default_network = info.data.get("default_network")
        if default_network and default_network not in v:
            raise ValueError(
                f"Default network '{default_network}' not found in networks configuration"
            )
        return v

    @field_validator("well_known_assets")
    @classmethod
    def validate_asset_networks(
        cls, v: Dict[str, Dict[str, AssetConfig]]
    ) -> Dict[str, Dict[str, AssetConfig]]:
        """Validate that asset networks exist in network configuration."""
        for network_name in v.keys():
            try:
                StellarNetworkType(network_name)
            except ValueError:
                raise ValueError(f"Unknown network '{network_name}' in well_known_assets")
        return v

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",  # Forbid extra fields not defined in model
    )


class StellarConfigValidator:
    """Configuration validator with enhanced error reporting."""

    @staticmethod
    def validate_config(config_dict: Dict[str, Any]) -> StellarMainConfig:
        """
        Validate configuration dictionary and return validated model.

        Args:
            config_dict: Raw configuration dictionary

        Returns:
            Validated StellarMainConfig instance

        Raises:
            ValueError: If configuration is invalid
        """
        try:
            # Extract stellar configuration
            if "stellar" not in config_dict:
                raise ValueError("Missing 'stellar' section in configuration")

            stellar_config = config_dict["stellar"]
            return StellarMainConfig(**stellar_config)

        except Exception as e:
            # Provide detailed error information
            error_details = []
            if hasattr(e, "errors"):
                for error in e.errors():
                    location = " -> ".join(str(loc) for loc in error["loc"])
                    error_details.append(f"{location}: {error['msg']}")

            if error_details:
                detailed_message = "Configuration validation errors:\n" + "\n".join(
                    f"  - {detail}" for detail in error_details
                )
            else:
                detailed_message = f"Configuration validation failed: {str(e)}"

            raise ValueError(detailed_message) from e

    @staticmethod
    def validate_network_connectivity(config: StellarMainConfig) -> List[str]:
        """
        Validate network connectivity requirements.

        Args:
            config: Validated configuration

        Returns:
            List of validation warnings
        """
        warnings = []

        for network_type, network_config in config.networks.items():
            # Check for production mainnet requirements
            if network_type == StellarNetworkType.MAINNET:
                if len(network_config.horizon.fallbacks) < 2:
                    warnings.append("Mainnet should have at least 2 fallback Horizon endpoints")

                if network_config.friendbot and network_config.friendbot.enabled:
                    warnings.append("Friendbot should not be enabled on mainnet")

            # Check for test network requirements
            elif network_type in [StellarNetworkType.TESTNET, StellarNetworkType.FUTURENET]:
                if not network_config.friendbot or not network_config.friendbot.enabled:
                    warnings.append(
                        f"{network_type.value} should have friendbot enabled for testing"
                    )

        return warnings
