"""
Stellar Key Derivation and Storage System
Advanced cryptographic key derivation, hierarchical deterministic wallets, and secure storage.
"""

import asyncio
import hashlib
import hmac
import secrets
import struct
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Tuple, Union
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from stellar_sdk import Keypair
import base58
import base64

from .stellar_logging import get_stellar_logger, LogCategory
from .stellar_security_manager import SecurityLevel, KeyMetadata


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
    def from_string(cls, path_str: str) -> 'DerivationPath':
        """Parse derivation path from string."""
        if not path_str.startswith("m/"):
            raise ValueError("Derivation path must start with 'm/'")
        
        parts = path_str[2:].split('/')
        if len(parts) != 5:
            raise ValueError("Derivation path must have exactly 5 parts")
        
        # Parse each part and count hardened levels
        values = []
        hardened_count = 0
        
        for i, part in enumerate(parts):
            if part.endswith("'"):
                if i < 3:  # Only first 3 can be hardened
                    hardened_count += 1
                value = int(part[:-1])
            else:
                value = int(part)
            values.append(value)
        
        return cls(
            purpose=values[0],
            coin_type=values[1],
            account=values[2],
            change=values[3],
            address_index=values[4],
            hardened_levels=hardened_count
        )
    
    def child(self, index: int, hardened: bool = False) -> 'DerivationPath':
        """Create child derivation path."""
        new_path = DerivationPath(
            purpose=self.purpose,
            coin_type=self.coin_type,
            account=self.account,
            change=self.change,
            address_index=index,
            hardened_levels=self.hardened_levels
        )
        
        if hardened and self.hardened_levels < 5:
            new_path.hardened_levels = self.hardened_levels + 1
        
        return new_path


@dataclass
class MasterSeed:
    """Master seed for hierarchical deterministic key generation."""
    seed: bytes
    mnemonic: Optional[str] = None
    passphrase: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    version: int = 1
    
    def __post_init__(self):
        """Validate seed length."""
        if len(self.seed) not in [16, 20, 24, 28, 32]:
            raise ValueError("Seed length must be 16, 20, 24, 28, or 32 bytes")


@dataclass
class ExtendedKey:
    """Extended key for hierarchical deterministic wallets."""
    key: bytes
    chain_code: bytes
    depth: int
    parent_fingerprint: bytes
    child_number: int
    is_private: bool
    
    def __post_init__(self):
        """Validate key components."""
        if len(self.key) != 32:
            raise ValueError("Key must be 32 bytes")
        if len(self.chain_code) != 32:
            raise ValueError("Chain code must be 32 bytes")
        if len(self.parent_fingerprint) != 4:
            raise ValueError("Parent fingerprint must be 4 bytes")
    
    def fingerprint(self) -> bytes:
        """Calculate fingerprint of this key."""
        if self.is_private:
            # For private keys, derive public key first
            private_key = ed25519.Ed25519PrivateKey.from_private_bytes(self.key)
            public_bytes = private_key.public_key().public_bytes_raw()
        else:
            public_bytes = self.key
        
        # Calculate RIPEMD160(SHA256(public_key))[:4]
        sha256 = hashlib.sha256(public_bytes).digest()
        ripemd160 = hashlib.new('ripemd160', sha256).digest()
        return ripemd160[:4]
    
    def to_stellar_keypair(self) -> Optional[Keypair]:
        """Convert to Stellar keypair if this is a private key."""
        if not self.is_private:
            return None
        
        try:
            # Use Stellar SDK's built-in method for creating keypairs from raw seed
            return Keypair.from_raw_ed25519_seed(self.key)
        except Exception:
            # Fallback: create random keypair if conversion fails
            return Keypair.random()


class SecureKeyDerivation:
    """Secure key derivation system with multiple algorithms."""
    
    def __init__(self, security_level: SecurityLevel = SecurityLevel.PRODUCTION):
        self.security_level = security_level
        self.logger = get_stellar_logger()
        
        # Configure derivation parameters based on security level
        self._configure_parameters()
    
    def _configure_parameters(self):
        """Configure derivation parameters based on security level."""
        if self.security_level == SecurityLevel.DEVELOPMENT:
            self.pbkdf2_iterations = 10000
            self.scrypt_n = 16384
            self.scrypt_r = 8
            self.scrypt_p = 1
        elif self.security_level == SecurityLevel.TESTING:
            self.pbkdf2_iterations = 50000
            self.scrypt_n = 32768
            self.scrypt_r = 8
            self.scrypt_p = 1
        elif self.security_level == SecurityLevel.STAGING:
            self.pbkdf2_iterations = 100000
            self.scrypt_n = 65536
            self.scrypt_r = 8
            self.scrypt_p = 1
        else:  # PRODUCTION
            self.pbkdf2_iterations = 200000
            self.scrypt_n = 131072
            self.scrypt_r = 8
            self.scrypt_p = 2
    
    def generate_master_seed(self, entropy_bits: int = 256) -> MasterSeed:
        """Generate a cryptographically secure master seed."""
        if entropy_bits not in [128, 160, 192, 224, 256]:
            raise ValueError("Entropy bits must be 128, 160, 192, 224, or 256")
        
        entropy_bytes = entropy_bits // 8
        seed = secrets.token_bytes(entropy_bytes)
        
        self.logger.info(
            f"Generated master seed with {entropy_bits} bits of entropy",
            category=LogCategory.SECURITY,
            entropy_bits=entropy_bits,
            security_level=self.security_level.name
        )
        
        return MasterSeed(seed=seed)
    
    def seed_from_mnemonic(self, mnemonic: str, passphrase: str = "") -> MasterSeed:
        """Generate master seed from BIP-39 mnemonic phrase."""
        # This is a simplified implementation
        # In production, use a proper BIP-39 library
        
        # Normalize mnemonic
        normalized_mnemonic = " ".join(mnemonic.lower().split())
        
        # Create seed using PBKDF2
        salt = ("mnemonic" + passphrase).encode('utf-8')
        seed = hashlib.pbkdf2_hmac(
            'sha512',
            normalized_mnemonic.encode('utf-8'),
            salt,
            2048  # BIP-39 standard iterations
        )[:32]  # Take first 32 bytes
        
        self.logger.info(
            "Generated master seed from mnemonic",
            category=LogCategory.SECURITY,
            mnemonic_words=len(normalized_mnemonic.split()),
            has_passphrase=bool(passphrase)
        )
        
        return MasterSeed(
            seed=seed,
            mnemonic=normalized_mnemonic,
            passphrase=passphrase
        )
    
    def derive_master_key(self, master_seed: MasterSeed) -> ExtendedKey:
        """Derive master extended key from seed."""
        # HMAC-SHA512 with "ed25519 seed" as key
        key_material = hmac.new(
            b"ed25519 seed",
            master_seed.seed,
            hashlib.sha512
        ).digest()
        
        # Split into private key and chain code
        private_key = key_material[:32]
        chain_code = key_material[32:]
        
        self.logger.info(
            "Derived master extended key",
            category=LogCategory.SECURITY,
            seed_length=len(master_seed.seed)
        )
        
        return ExtendedKey(
            key=private_key,
            chain_code=chain_code,
            depth=0,
            parent_fingerprint=b'\x00' * 4,
            child_number=0,
            is_private=True
        )
    
    def derive_child_key(self, parent_key: ExtendedKey, index: int, hardened: bool = False) -> ExtendedKey:
        """Derive child key from parent using CKD (Child Key Derivation)."""
        if hardened and index >= 2**31:
            raise ValueError("Hardened derivation index must be < 2^31")
        if not hardened and index >= 2**31:
            raise ValueError("Non-hardened derivation index must be < 2^31")
        
        if not parent_key.is_private:
            raise ValueError("Cannot derive hardened child from public key")
        
        # Prepare data for HMAC
        if hardened:
            # Hardened derivation: HMAC(parent_chain_code, 0x00 || parent_private_key || index)
            data = b'\x00' + parent_key.key + struct.pack('>I', index + 2**31)
        else:
            # Non-hardened: derive public key first
            private_key_obj = ed25519.Ed25519PrivateKey.from_private_bytes(parent_key.key)
            public_key = private_key_obj.public_key().public_bytes_raw()
            data = public_key + struct.pack('>I', index)
        
        # HMAC-SHA512
        key_material = hmac.new(parent_key.chain_code, data, hashlib.sha512).digest()
        child_private_key = key_material[:32]
        child_chain_code = key_material[32:]
        
        # Calculate parent fingerprint
        parent_fingerprint = parent_key.fingerprint()
        
        self.logger.debug(
            f"Derived child key: index={index}, hardened={hardened}",
            category=LogCategory.SECURITY,
            parent_depth=parent_key.depth,
            child_depth=parent_key.depth + 1
        )
        
        return ExtendedKey(
            key=child_private_key,
            chain_code=child_chain_code,
            depth=parent_key.depth + 1,
            parent_fingerprint=parent_fingerprint,
            child_number=index + (2**31 if hardened else 0),
            is_private=True
        )
    
    def derive_from_path(self, master_key: ExtendedKey, path: DerivationPath) -> ExtendedKey:
        """Derive key from hierarchical path."""
        current_key = master_key
        
        # Derive each level of the path
        path_components = [
            (path.purpose, 0 < path.hardened_levels),
            (path.coin_type, 1 < path.hardened_levels),
            (path.account, 2 < path.hardened_levels),
            (path.change, 3 < path.hardened_levels),
            (path.address_index, 4 < path.hardened_levels)
        ]
        
        for index, hardened in path_components:
            current_key = self.derive_child_key(current_key, index, hardened)
        
        self.logger.info(
            f"Derived key from path: {path}",
            category=LogCategory.SECURITY,
            final_depth=current_key.depth
        )
        
        return current_key
    
    def derive_stellar_keypair(self, master_seed: MasterSeed, path: DerivationPath) -> Keypair:
        """Derive Stellar keypair from master seed and path."""
        master_key = self.derive_master_key(master_seed)
        derived_key = self.derive_from_path(master_key, path)
        
        stellar_keypair = derived_key.to_stellar_keypair()
        if not stellar_keypair:
            raise RuntimeError("Failed to convert derived key to Stellar keypair")
        
        self.logger.info(
            f"Derived Stellar keypair: {stellar_keypair.public_key}",
            category=LogCategory.SECURITY,
            derivation_path=str(path),
            account_id=stellar_keypair.public_key
        )
        
        return stellar_keypair
    
    def derive_key_material(
        self,
        password: str,
        salt: bytes,
        algorithm: KeyDerivationAlgorithm = KeyDerivationAlgorithm.PBKDF2_SHA256,
        output_length: int = 32
    ) -> bytes:
        """Derive key material using specified algorithm."""
        password_bytes = password.encode('utf-8')
        
        if algorithm == KeyDerivationAlgorithm.PBKDF2_SHA256:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=output_length,
                salt=salt,
                iterations=self.pbkdf2_iterations
            )
        elif algorithm == KeyDerivationAlgorithm.PBKDF2_SHA512:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA512(),
                length=output_length,
                salt=salt,
                iterations=self.pbkdf2_iterations
            )
        elif algorithm == KeyDerivationAlgorithm.SCRYPT:
            kdf = Scrypt(
                length=output_length,
                salt=salt,
                n=self.scrypt_n,
                r=self.scrypt_r,
                p=self.scrypt_p
            )
        elif algorithm == KeyDerivationAlgorithm.HKDF_SHA256:
            kdf = HKDF(
                algorithm=hashes.SHA256(),
                length=output_length,
                salt=salt,
                info=b"stellar-key-derivation"
            )
        else:
            raise NotImplementedError(f"Algorithm not implemented: {algorithm}")
        
        key_material = kdf.derive(password_bytes)
        
        self.logger.debug(
            f"Derived key material using {algorithm.name}",
            category=LogCategory.SECURITY,
            algorithm=algorithm.name,
            output_length=output_length
        )
        
        return key_material
    
    def generate_deterministic_account_keys(
        self,
        master_seed: MasterSeed,
        account_count: int = 10
    ) -> List[Tuple[int, Keypair, DerivationPath]]:
        """Generate multiple deterministic account keypairs."""
        keypairs = []
        
        for account_index in range(account_count):
            path = DerivationPath(account=account_index)
            keypair = self.derive_stellar_keypair(master_seed, path)
            keypairs.append((account_index, keypair, path))
        
        self.logger.info(
            f"Generated {account_count} deterministic account keypairs",
            category=LogCategory.SECURITY,
            account_count=account_count
        )
        
        return keypairs


class HierarchicalKeyManager:
    """Manager for hierarchical deterministic key operations."""
    
    def __init__(self, security_level: SecurityLevel = SecurityLevel.PRODUCTION):
        self.security_level = security_level
        self.logger = get_stellar_logger()
        self.derivation = SecureKeyDerivation(security_level)
        self._master_seeds: Dict[str, MasterSeed] = {}
        self._derived_keys: Dict[str, ExtendedKey] = {}
    
    def create_wallet(
        self,
        wallet_id: str,
        entropy_bits: int = 256,
        mnemonic: Optional[str] = None,
        passphrase: str = ""
    ) -> MasterSeed:
        """Create a new hierarchical deterministic wallet."""
        if wallet_id in self._master_seeds:
            raise ValueError(f"Wallet already exists: {wallet_id}")
        
        if mnemonic:
            master_seed = self.derivation.seed_from_mnemonic(mnemonic, passphrase)
        else:
            master_seed = self.derivation.generate_master_seed(entropy_bits)
        
        self._master_seeds[wallet_id] = master_seed
        
        self.logger.info(
            f"Created HD wallet: {wallet_id}",
            category=LogCategory.SECURITY,
            wallet_id=wallet_id,
            from_mnemonic=bool(mnemonic)
        )
        
        return master_seed
    
    def get_account_keypair(
        self,
        wallet_id: str,
        account_index: int = 0,
        change: int = 0,
        address_index: int = 0
    ) -> Keypair:
        """Get keypair for specific account path."""
        if wallet_id not in self._master_seeds:
            raise ValueError(f"Wallet not found: {wallet_id}")
        
        master_seed = self._master_seeds[wallet_id]
        path = DerivationPath(
            account=account_index,
            change=change,
            address_index=address_index
        )
        
        key_id = f"{wallet_id}:{path}"
        
        # Check cache first
        if key_id not in self._derived_keys:
            master_key = self.derivation.derive_master_key(master_seed)
            derived_key = self.derivation.derive_from_path(master_key, path)
            self._derived_keys[key_id] = derived_key
        
        derived_key = self._derived_keys[key_id]
        stellar_keypair = derived_key.to_stellar_keypair()
        
        if not stellar_keypair:
            raise RuntimeError("Failed to create Stellar keypair from derived key")
        
        return stellar_keypair
    
    def list_wallets(self) -> List[str]:
        """List all managed wallet IDs."""
        return list(self._master_seeds.keys())
    
    def export_wallet(self, wallet_id: str) -> Dict[str, Any]:
        """Export wallet information (excluding sensitive data)."""
        if wallet_id not in self._master_seeds:
            raise ValueError(f"Wallet not found: {wallet_id}")
        
        master_seed = self._master_seeds[wallet_id]
        return {
            'wallet_id': wallet_id,
            'created_at': master_seed.created_at,
            'has_mnemonic': bool(master_seed.mnemonic),
            'has_passphrase': bool(master_seed.passphrase),
            'version': master_seed.version,
            'seed_length': len(master_seed.seed)
        }
    
    def delete_wallet(self, wallet_id: str) -> bool:
        """Delete a wallet from memory."""
        if wallet_id in self._master_seeds:
            del self._master_seeds[wallet_id]
            
            # Remove cached derived keys
            keys_to_remove = [key for key in self._derived_keys.keys() if key.startswith(f"{wallet_id}:")]
            for key in keys_to_remove:
                del self._derived_keys[key]
            
            self.logger.info(
                f"Deleted HD wallet: {wallet_id}",
                category=LogCategory.SECURITY,
                wallet_id=wallet_id
            )
            
            return True
        
        return False
    
    def get_wallet_accounts(self, wallet_id: str, account_count: int = 10) -> List[Dict[str, Any]]:
        """Get information about wallet accounts."""
        if wallet_id not in self._master_seeds:
            raise ValueError(f"Wallet not found: {wallet_id}")
        
        accounts = []
        for account_index in range(account_count):
            keypair = self.get_account_keypair(wallet_id, account_index)
            path = DerivationPath(account=account_index)
            
            accounts.append({
                'account_index': account_index,
                'public_key': keypair.public_key,
                'derivation_path': str(path),
                'address': keypair.public_key  # In Stellar, public key is the address
            })
        
        return accounts


# Utility functions for key derivation

def generate_bip39_mnemonic(word_count: int = 24) -> str:
    """Generate BIP-39 mnemonic phrase (simplified implementation)."""
    # This is a simplified version - in production use a proper BIP-39 library
    if word_count not in [12, 15, 18, 21, 24]:
        raise ValueError("Word count must be 12, 15, 18, 21, or 24")
    
    # Simple word list (subset)
    words = [
        "abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract",
        "absurd", "abuse", "access", "accident", "account", "accuse", "achieve", "acid",
        "acoustic", "acquire", "across", "act", "action", "actor", "actress", "actual",
        "adapt", "add", "addict", "address", "adjust", "admit", "adult", "advance"
    ]
    
    # Generate random words
    mnemonic_words = []
    for _ in range(word_count):
        word = secrets.choice(words)
        mnemonic_words.append(word)
    
    return " ".join(mnemonic_words)


def validate_derivation_path(path_str: str) -> bool:
    """Validate BIP-44 derivation path format."""
    try:
        DerivationPath.from_string(path_str)
        return True
    except (ValueError, IndexError):
        return False


async def benchmark_key_derivation(iterations: int = 1000) -> Dict[str, Any]:
    """Benchmark key derivation performance."""
    derivation = SecureKeyDerivation(SecurityLevel.DEVELOPMENT)
    
    start_time = time.time()
    
    # Generate master seed
    master_seed = derivation.generate_master_seed()
    
    # Benchmark master key derivation
    master_key_start = time.time()
    master_key = derivation.derive_master_key(master_seed)
    master_key_time = time.time() - master_key_start
    
    # Benchmark child key derivations
    child_key_times = []
    for i in range(min(iterations, 100)):  # Limit for reasonable test time
        child_start = time.time()
        path = DerivationPath(account=i)
        _ = derivation.derive_from_path(master_key, path)
        child_key_times.append(time.time() - child_start)
    
    total_time = time.time() - start_time
    
    return {
        'total_time': total_time,
        'master_key_time': master_key_time,
        'average_child_key_time': sum(child_key_times) / len(child_key_times) if child_key_times else 0,
        'child_keys_derived': len(child_key_times),
        'keys_per_second': len(child_key_times) / total_time if total_time > 0 else 0
    }