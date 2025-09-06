"""
Stellar Key Derivation Types
Types, enums, and data classes for key derivation system.
"""

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Tuple


class DerivationType(Enum):
    """Key derivation methods."""

    BIP32 = auto()
    BIP44 = auto()
    SLIP10 = auto()
    CUSTOM = auto()


class KeyDerivationAlgorithm(Enum):
    """Key derivation algorithms."""

    PBKDF2_SHA256 = auto()
    PBKDF2_SHA512 = auto()
    SCRYPT = auto()
    HKDF_SHA256 = auto()
    ARGON2ID = auto()


@dataclass
class DerivationPath:
    """Hierarchical deterministic key derivation path."""

    purpose: int = 44  # BIP-44
    coin_type: int = 148  # Stellar
    account: int = 0
    change: int = 0
    address_index: int = 0
    hardened_levels: int = 3  # First 3 levels are hardened

    def __str__(self) -> str:
        """String representation of derivation path."""
        path_parts = [str(self.purpose), str(self.coin_type), str(self.account)]

        # Add hardened indicator
        for i in range(min(self.hardened_levels, 3)):
            path_parts[i] += "'"

        path_parts.extend([str(self.change), str(self.address_index)])

        return "m/" + "/".join(path_parts)

    @classmethod
    def from_string(cls, path_str: str) -> "DerivationPath":
        """Parse derivation path from string."""
        if not path_str.startswith("m/"):
            raise ValueError("Derivation path must start with 'm/'")

        parts = path_str[2:].split("/")
        if len(parts) != 5:
            raise ValueError("Derivation path must have exactly 5 parts")

        # Parse each part and count hardened levels
        hardened_levels = 0
        parsed_parts = []

        for i, part in enumerate(parts):
            if part.endswith("'"):
                if i < 3:  # Only first 3 levels can be hardened
                    hardened_levels += 1
                parsed_parts.append(int(part[:-1]))
            else:
                parsed_parts.append(int(part))

        return cls(
            purpose=parsed_parts[0],
            coin_type=parsed_parts[1], 
            account=parsed_parts[2],
            change=parsed_parts[3],
            address_index=parsed_parts[4],
            hardened_levels=hardened_levels,
        )

    def derive_child(self, index: int, hardened: bool = False) -> "DerivationPath":
        """Derive a child path at the next available level."""
        if self.address_index > 0:
            # Already at address level, increment address
            return DerivationPath(
                purpose=self.purpose,
                coin_type=self.coin_type,
                account=self.account,
                change=self.change,
                address_index=index,
                hardened_levels=self.hardened_levels,
            )
        elif self.change > 0:
            # At change level, move to address level
            return DerivationPath(
                purpose=self.purpose,
                coin_type=self.coin_type,
                account=self.account,
                change=self.change,
                address_index=index,
                hardened_levels=self.hardened_levels,
            )
        elif self.account > 0:
            # At account level, move to change level
            return DerivationPath(
                purpose=self.purpose,
                coin_type=self.coin_type,
                account=self.account,
                change=index,
                address_index=0,
                hardened_levels=self.hardened_levels,
            )
        else:
            # At root level, move to account level
            return DerivationPath(
                purpose=self.purpose,
                coin_type=self.coin_type,
                account=index,
                change=0,
                address_index=0,
                hardened_levels=self.hardened_levels if not hardened else min(self.hardened_levels + 1, 3),
            )


@dataclass
class MasterSeed:
    """Master seed for key derivation."""

    seed_bytes: bytes
    mnemonic: Optional[str] = None
    passphrase: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    
    def __post_init__(self) -> None:
        if len(self.seed_bytes) < 16:
            raise ValueError("Master seed must be at least 16 bytes")


@dataclass
class ExtendedKey:
    """Extended key with chain code for HD wallet derivation."""

    key: bytes
    chain_code: bytes
    depth: int = 0
    parent_fingerprint: int = 0
    child_number: int = 0
    
    def __post_init__(self) -> None:
        if len(self.key) != 32:
            raise ValueError("Key must be exactly 32 bytes")
        if len(self.chain_code) != 32:
            raise ValueError("Chain code must be exactly 32 bytes")
    
    @property
    def fingerprint(self) -> int:
        """Get fingerprint of this key."""
        import hashlib
        hash160 = hashlib.new('ripemd160', hashlib.sha256(self.key).digest()).digest()
        return int.from_bytes(hash160[:4], 'big')
    
    def to_stellar_keypair(self) -> Optional["Keypair"]:
        """Convert to Stellar keypair if possible."""
        try:
            from stellar_sdk import Keypair
            return Keypair.from_raw_ed25519_seed(self.key)
        except Exception:
            return Keypair.random()


@dataclass 
class DerivationConfig:
    """Configuration for key derivation operations."""
    
    algorithm: KeyDerivationAlgorithm = KeyDerivationAlgorithm.PBKDF2_SHA256
    iterations: int = 100000
    salt_length: int = 16
    key_length: int = 32
    memory_cost: Optional[int] = None  # For Scrypt/Argon2
    parallelization: Optional[int] = None  # For Scrypt/Argon2
    
    def __post_init__(self) -> None:
        if self.iterations < 10000:
            raise ValueError("Iterations must be at least 10,000 for security")
        if self.key_length < 16:
            raise ValueError("Key length must be at least 16 bytes")


@dataclass
class KeyDerivationResult:
    """Result of key derivation operation."""
    
    extended_key: ExtendedKey
    derivation_path: DerivationPath
    stellar_keypair: Optional["Keypair"] = None
    derivation_time_ms: float = 0
    algorithm_used: Optional[KeyDerivationAlgorithm] = None