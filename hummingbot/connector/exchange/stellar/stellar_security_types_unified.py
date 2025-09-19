"""
Unified Security Types Module
Canonical definitions for all security-related types and configurations.

This module consolidates duplicate security type definitions across the codebase
to establish a single source of truth while maintaining semantic clarity.
"""

from dataclasses import dataclass, field
from enum import auto, Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

try:
    from pydantic import BaseModel, Field
except ImportError:
    # Fallback for environments without Pydantic
    class BaseModel:
        pass

    def Field(**kwargs):
        return kwargs.get("default")


class SecurityEnvironment(Enum):
    """Security environments for deployment contexts."""

    DEVELOPMENT = auto()
    TESTING = auto()
    STAGING = auto()
    PRODUCTION = auto()


class SecurityHardeningLevel(Enum):
    """Security hardening levels for threat mitigation."""

    MINIMAL = "minimal"
    STANDARD = "standard"
    ENHANCED = "enhanced"
    MAXIMUM = "maximum"


class SecurityProvider(Enum):
    """Supported enterprise security providers."""

    LOCAL = "local"
    HSM_AWS = "hsm_aws"
    HSM_AZURE = "hsm_azure"
    HSM_THALES = "hsm_thales"
    MPC = "mpc"
    HARDWARE_WALLET = "hardware_wallet"


class KeyStoreType(Enum):
    """Types of key storage backends."""

    MEMORY = "memory"
    FILE = "file"
    HSM = "hsm"
    VAULT = "vault"
    HARDWARE_WALLET = "hardware_wallet"


class HardwareWalletType(Enum):
    """Supported hardware wallet types."""

    LEDGER = "ledger"
    TREZOR = "trezor"
    KEEPKEY = "keepkey"


@dataclass
class NetworkSecurityConfig:
    """Network-level security configuration (formerly SecurityConfig in config_models)."""

    verify_certificates: bool = True
    min_tls_version: str = "1.2"
    request_signing_enabled: bool = True
    algorithm: str = "ed25519"


@dataclass
class EnterpriseSecurityConfig:
    """Enterprise security provider configuration (formerly SecurityConfig in security)."""

    provider: SecurityProvider
    config: Dict[str, Any]
    backup_providers: List[SecurityProvider] = field(default_factory=list)


@dataclass
class GeneralSecurityConfig:
    """General security settings (formerly SecurityConfig in security_types)."""

    security_environment: SecurityEnvironment = SecurityEnvironment.DEVELOPMENT
    hardening_level: SecurityHardeningLevel = SecurityHardeningLevel.STANDARD
    require_hardware_security: bool = False
    key_derivation_iterations: int = 100000
    session_timeout_minutes: int = 30
    max_failed_attempts: int = 3
    enable_audit_logging: bool = True
    encryption_algorithm: str = "AES-256-GCM"
    backup_enabled: bool = True


@dataclass
class UnifiedSecurityConfig:
    """Unified security configuration combining all security aspects."""

    network: NetworkSecurityConfig = field(default_factory=NetworkSecurityConfig)
    enterprise: Optional[EnterpriseSecurityConfig] = None
    general: GeneralSecurityConfig = field(default_factory=GeneralSecurityConfig)

    def get_effective_security_level(self) -> SecurityHardeningLevel:
        """Get the effective security level considering environment and configuration."""
        env_level = self.general.security_environment

        if env_level == SecurityEnvironment.PRODUCTION:
            return max(self.general.hardening_level, SecurityHardeningLevel.ENHANCED)
        elif env_level == SecurityEnvironment.STAGING:
            return max(self.general.hardening_level, SecurityHardeningLevel.STANDARD)
        else:
            return self.general.hardening_level


# Pydantic version for config management compatibility
class NetworkSecurityConfigModel(BaseModel):
    """Pydantic model for network security configuration."""

    verify_certificates: bool = Field(default=True, description="Verify SSL certificates")
    min_tls_version: str = Field(default="1.2", description="Minimum TLS version")
    request_signing_enabled: bool = Field(default=True, description="Enable request signing")
    algorithm: str = Field(default="ed25519", description="Signing algorithm")


# Protocol definitions for type checking
@runtime_checkable
class SecurityProviderProtocol(Protocol):
    """Protocol for security provider implementations."""

    async def sign_transaction(self, transaction: Any) -> bytes:
        """Sign a transaction using the security provider."""
        ...

    async def get_public_key(self, key_id: str) -> bytes:
        """Get public key for a given key identifier."""
        ...


@runtime_checkable
class KeyStoreProtocol(Protocol):
    """Protocol for key storage implementations."""

    async def store_key(self, key_id: str, key_data: bytes) -> bool:
        """Store a key securely."""
        ...

    async def retrieve_key(self, key_id: str) -> Optional[bytes]:
        """Retrieve a key by identifier."""
        ...

    async def delete_key(self, key_id: str) -> bool:
        """Delete a key by identifier."""
        ...


# Backward compatibility aliases (to be deprecated)
# These allow existing code to continue working during the transition

# DEPRECATED: Use SecurityEnvironment instead
SecurityLevel = SecurityEnvironment

# DEPRECATED: Use specific config types instead
# This ensures existing code continues to work during migration


class SecurityConfigCompat:
    """Backward compatibility wrapper for SecurityConfig usage."""

    def __init__(self, **kwargs):
        # Support all legacy parameter patterns found in existing code
        self._params = kwargs

        # Common attributes from existing usage patterns
        self.security_level = kwargs.get("security_level", SecurityEnvironment.DEVELOPMENT)
        self.require_hardware_security = kwargs.get("require_hardware_security", False)
        self.verify_certificates = kwargs.get("verify_certificates", True)
        self.provider = kwargs.get("provider", SecurityProvider.LOCAL)
        self.config = kwargs.get("config", {})
        self.backup_providers = kwargs.get("backup_providers", [])

        # Additional compatibility attributes
        self.min_tls_version = kwargs.get("min_tls_version", "1.2")
        self.request_signing_enabled = kwargs.get("request_signing_enabled", True)
        self.algorithm = kwargs.get("algorithm", "ed25519")
        self.key_derivation_iterations = kwargs.get("key_derivation_iterations", 100000)
        self.session_timeout_minutes = kwargs.get("session_timeout_minutes", 30)
        self.max_failed_attempts = kwargs.get("max_failed_attempts", 3)
        self.enable_audit_logging = kwargs.get("enable_audit_logging", True)
        self.encryption_algorithm = kwargs.get("encryption_algorithm", "AES-256-GCM")
        self.backup_enabled = kwargs.get("backup_enabled", True)


# Use compatibility wrapper as default SecurityConfig
SecurityConfig = SecurityConfigCompat

# Legacy imports for backward compatibility
__all__ = [
    # New canonical types
    "SecurityEnvironment",
    "SecurityHardeningLevel",
    "SecurityProvider",
    "KeyStoreType",
    "HardwareWalletType",
    "NetworkSecurityConfig",
    "EnterpriseSecurityConfig",
    "GeneralSecurityConfig",
    "UnifiedSecurityConfig",
    "NetworkSecurityConfigModel",
    # Protocols
    "SecurityProviderProtocol",
    "KeyStoreProtocol",
    # Backward compatibility aliases
    "SecurityLevel",  # Use SecurityEnvironment instead
    "SecurityConfig",  # Use UnifiedSecurityConfig instead
]
