"""
Stellar Test Account Types
Types, enums, and data classes for test account management system.
"""

import time
from dataclasses import dataclass, field
from enum import auto, Enum
from typing import Any, Dict, List, Optional

from stellar_sdk import Keypair

from .stellar_network_manager import StellarNetwork


class TestAccountType(Enum):
    """Types of test accounts."""

    BASIC = auto()
    FUNDED = auto()
    MULTISIG = auto()
    ISSUER = auto()
    DISTRIBUTOR = auto()
    ANCHOR = auto()
    DEX_TRADER = auto()


class AccountStatus(Enum):
    """Test account status."""

    CREATED = auto()
    FUNDED = auto()
    ACTIVE = auto()
    LOCKED = auto()
    EXPIRED = auto()
    ARCHIVED = auto()


@dataclass
class TestAccountConfig:
    """Configuration for test account creation."""

    account_type: TestAccountType
    initial_xlm_balance: float = 100.0
    custom_assets: List[Dict[str, Any]] = field(default_factory=list)
    trustlines: List[str] = field(default_factory=list)
    multisig_threshold: Optional[int] = None
    multisig_signers: List[str] = field(default_factory=list)
    expiry_hours: Optional[int] = 24
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=Dict[str, Any])


@dataclass
class TestAccount:
    """Represents a test account."""

    account_id: str
    keypair: Keypair
    account_type: TestAccountType
    network: StellarNetwork
    status: AccountStatus
    created_at: float = field(default_factory=time.time)
    last_used: float = 0
    xlm_balance: float = 0
    custom_assets: Dict[str, float] = field(default_factory=Dict[str, Any])
    trustlines: List[str] = field(default_factory=list)
    multisig_config: Optional[Dict[str, Any]] = None
    expiry_time: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=Dict[str, Any])
    usage_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "account_id": self.account_id,
            "secret_key": self.keypair.secret,  # Only for test environments
            "account_type": self.account_type.name,
            "network": self.network.value,
            "status": self.status.name,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "xlm_balance": self.xlm_balance,
            "custom_assets": self.custom_assets,
            "trustlines": self.trustlines,
            "multisig_config": self.multisig_config,
            "expiry_time": self.expiry_time,
            "tags": self.tags,
            "metadata": self.metadata,
            "usage_count": self.usage_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestAccount":
        """Create from dictionary."""
        keypair = Keypair.from_secret(data["secret_key"])
        return cls(
            account_id=data["account_id"],
            keypair=keypair,
            account_type=TestAccountType[data["account_type"]],
            network=StellarNetwork(data["network"]),
            status=AccountStatus[data["status"]],
            created_at=data["created_at"],
            last_used=data["last_used"],
            xlm_balance=data["xlm_balance"],
            custom_assets=data.get("custom_assets", {}),
            trustlines=data.get("trustlines", []),
            multisig_config=data.get("multisig_config"),
            expiry_time=data.get("expiry_time"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            usage_count=data.get("usage_count", 0),
        )

    @property
    def is_expired(self) -> bool:
        """Check if account has expired."""
        if not self.expiry_time:
            return False
        return time.time() > self.expiry_time

    @property
    def hours_until_expiry(self) -> Optional[float]:
        """Get hours until account expires."""
        if not self.expiry_time:
            return None
        remaining_seconds = self.expiry_time - time.time()
        return max(0, remaining_seconds / 3600)

    def touch(self) -> None:
        """Update last used time and usage count."""
        self.last_used = time.time()
        self.usage_count += 1
