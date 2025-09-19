"""
Stellar Security Types and Protocols
Core types, enums, and protocols for the Stellar security infrastructure.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import auto, Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable, Tuple

# DEPRECATED: These types have been moved to stellar_security_types_unified.py
# Import from there for new code:
from .stellar_security_types_unified import (
    HardwareWalletType,
    KeyStoreType,
    SecurityConfig,
    SecurityLevel,
)


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
