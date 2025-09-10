"""
Stellar Security Types and Protocols
Core types, enums, and protocols for the Stellar security infrastructure.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import auto, Enum
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable


class SecurityLevel(Enum):
    """Security levels for key operations."""

    DEVELOPMENT = auto()
    TESTING = auto()
    STAGING = auto()
    PRODUCTION = auto()


class KeyStoreType(Enum):
    """Types of key storage backends."""

    MEMORY = auto()
    FILE_SYSTEM = auto()
    HSM = auto()
    HARDWARE_WALLET = auto()
    VAULT = auto()


class HardwareWalletType(Enum):
    """Supported hardware wallet types."""

    LEDGER = auto()
    TREZOR = auto()


@dataclass
class SecurityConfig:
    """Security configuration settings."""

    security_level: SecurityLevel = SecurityLevel.DEVELOPMENT
    require_hardware_security: bool = False
    key_derivation_iterations: int = 100000
    session_timeout_minutes: int = 30
    max_failed_attempts: int = 3
    enable_audit_logging: bool = True
    encryption_algorithm: str = "AES-256-GCM"
    backup_enabled: bool = True
    backup_encryption: bool = True


@dataclass
class KeyMetadata:
    """Metadata for managed keys."""

    key_id: str
    account_id: str
    key_type: str
    store_type: KeyStoreType
    created_at: float = field(default_factory=time.time)
    last_used: float = 0
    use_count: int = 0
    security_level: SecurityLevel = SecurityLevel.DEVELOPMENT
    hardware_device_id: Optional[str] = None
    vault_path: Optional[str] = None
    encrypted: bool = True


@runtime_checkable
class KeyStoreBackend(Protocol):
    """Protocol for key storage backends."""

    async def store_key(self, key_id: str, key_data: bytes, metadata: KeyMetadata) -> bool:
        """Store a key with metadata."""
        ...

    async def retrieve_key(self, key_id: str) -> Optional[Tuple[bytes, KeyMetadata]]:
        """Retrieve a key and its metadata."""
        ...

    async def delete_key(self, key_id: str) -> bool:
        """Delete a key."""
        ...

    async def list_keys(self) -> List[KeyMetadata]:
        """List all stored keys."""
        ...
