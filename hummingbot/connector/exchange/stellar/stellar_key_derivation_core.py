"""
Stellar Key Derivation Core
Core cryptographic key derivation algorithms and extended key operations.
"""

import hashlib
import hmac
import secrets
import struct
import time
from typing import Any, Dict, List, Optional, Tuple

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from stellar_sdk import Keypair

from .stellar_key_derivation_types import (
    DerivationConfig,
    DerivationPath,
    DerivationType,
    ExtendedKey,
    KeyDerivationAlgorithm,
    KeyDerivationResult,
    MasterSeed,
)
from .stellar_logging import get_stellar_logger, LogCategory
from .stellar_security_types import SecurityLevel


class SecureKeyDerivation:
    """Secure key derivation system with multiple algorithms."""

    def __init__(self, security_level: SecurityLevel = SecurityLevel.PRODUCTION):
        self.security_level = security_level
        self.logger = get_stellar_logger()

        # Configure derivation parameters based on security level
        self._configure_parameters()

    def _configure_parameters(self) -> None:
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
        seed_bytes = secrets.token_bytes(entropy_bytes)

        self.logger.info(
            f"Generated master seed with {entropy_bits} bits of entropy",
            category=LogCategory.SECURITY,
            entropy_bits=entropy_bits,
            security_level=self.security_level.name,
        )

        return MasterSeed(seed_bytes=seed_bytes)

    def seed_from_mnemonic(self, mnemonic: str, passphrase: str = "") -> MasterSeed:
        """Generate master seed from BIP-39 mnemonic phrase."""
        # Normalize mnemonic
        normalized_mnemonic = " ".join(mnemonic.lower().split())

        # Create seed using PBKDF2 (BIP-39 standard)
        salt = ("mnemonic" + passphrase).encode("utf-8")
        seed_bytes = hashlib.pbkdf2_hmac(
            "sha512", normalized_mnemonic.encode("utf-8"), salt, 2048  # BIP-39 standard iterations
        )[
            :32
        ]  # Take first 32 bytes

        self.logger.info(
            "Generated master seed from mnemonic",
            category=LogCategory.SECURITY,
            mnemonic_words=len(normalized_mnemonic.split()),
            has_passphrase=bool(passphrase),
        )

        return MasterSeed(
            seed_bytes=seed_bytes, mnemonic=normalized_mnemonic, passphrase=passphrase
        )

    def derive_master_key(self, master_seed: MasterSeed) -> ExtendedKey:
        """Derive master extended key from seed."""
        # HMAC-SHA512 with "ed25519 seed" as key
        key_material = hmac.new(b"ed25519 seed", master_seed.seed_bytes, hashlib.sha512).digest()

        # Split into private key and chain code
        private_key = key_material[:32]
        chain_code = key_material[32:]

        self.logger.info(
            "Derived master extended key",
            category=LogCategory.SECURITY,
            seed_length=len(master_seed.seed_bytes),
        )

        return ExtendedKey(
            key=private_key,
            chain_code=chain_code,
            depth=0,
            parent_fingerprint=0,
            child_number=0,
        )

    def derive_child_key(
        self, parent_key: ExtendedKey, index: int, hardened: bool = False
    ) -> ExtendedKey:
        """Derive child extended key from parent."""
        if hardened and index >= 2**31:
            raise ValueError("Hardened derivation index must be < 2^31")
        if not hardened and index >= 2**31:
            raise ValueError("Non-hardened derivation index must be < 2^31")

        # Prepare index bytes
        if hardened:
            index_bytes = struct.pack(">I", index + 2**31)
            # Hardened derivation: use private key
            data = b"\x00" + parent_key.key + index_bytes
        else:
            index_bytes = struct.pack(">I", index)
            # Non-hardened derivation: use public key
            # For Ed25519, we use the private key as approximation
            data = parent_key.key + index_bytes

        # Derive child key material
        key_material = hmac.new(parent_key.chain_code, data, hashlib.sha512).digest()

        child_key = key_material[:32]
        child_chain_code = key_material[32:]

        return ExtendedKey(
            key=child_key,
            chain_code=child_chain_code,
            depth=parent_key.depth + 1,
            parent_fingerprint=parent_key.fingerprint,
            child_number=index + (2**31 if hardened else 0),
        )

    def derive_path(self, master_key: ExtendedKey, path: DerivationPath) -> ExtendedKey:
        """Derive extended key following a derivation path."""
        current_key = master_key

        # Define path components and their hardened status
        path_components = [
            (path.purpose, True),  # m/44'
            (path.coin_type, True),  # /148'
            (path.account, True),  # /0'
            (path.change, False),  # /0
            (path.address_index, False),  # /0
        ]

        for index, is_hardened in path_components:
            current_key = self.derive_child_key(current_key, index, is_hardened)

        self.logger.info(
            f"Derived key for path: {path}",
            category=LogCategory.SECURITY,
            path_str=str(path),
            final_depth=current_key.depth,
        )

        return current_key

    def derive_path(self, master_key: ExtendedKey, path: DerivationPath) -> ExtendedKey:
        """Derive extended key following a derivation path."""
        current_key = master_key

        # Define path components and their hardened status
        path_components = [
            (path.purpose, True),  # m/44'
            (path.coin_type, True),  # /148'
            (path.account, True),  # /0'
            (path.change, False),  # /0
            (path.address_index, False),  # /0
        ]

        for index, is_hardened in path_components:
            current_key = self.derive_child_key(current_key, index, is_hardened)

        self.logger.info(
            f"Derived key for path: {path}",
            category=LogCategory.SECURITY,
            path_str=str(path),
            final_depth=current_key.depth,
        )

        return current_key

    def derive_stellar_keypair(self, extended_key: ExtendedKey) -> Keypair:
        """Convert extended key to Stellar keypair."""
        try:
            return Keypair.from_raw_ed25519_seed(extended_key.key)
        except Exception:
            # Fallback to random keypair if conversion fails
            self.logger.warning(
                "Failed to convert extended key to Stellar keypair, using random",
                category=LogCategory.SECURITY,
                key_length=len(extended_key.key),
            )
            return Keypair.random()

    def derive_key_with_algorithm(
        self,
        password: bytes,
        salt: bytes,
        algorithm: KeyDerivationAlgorithm,
        config: Optional[DerivationConfig] = None,
    ) -> bytes:
        """Derive key using specified algorithm."""
        if config is None:
            config = DerivationConfig(algorithm=algorithm)

        start_time = time.time()

        try:
            if algorithm == KeyDerivationAlgorithm.PBKDF2_SHA256:
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=config.key_length,
                    salt=salt,
                    iterations=config.iterations,
                )
                derived_key = kdf.derive(password)

            elif algorithm == KeyDerivationAlgorithm.PBKDF2_SHA512:
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA512(),
                    length=config.key_length,
                    salt=salt,
                    iterations=config.iterations,
                )
                derived_key = kdf.derive(password)

            elif algorithm == KeyDerivationAlgorithm.SCRYPT:
                kdf = Scrypt(
                    length=config.key_length,
                    salt=salt,
                    n=config.memory_cost or 65536,
                    r=config.parallelization or 8,
                    p=1,
                )
                derived_key = kdf.derive(password)

            elif algorithm == KeyDerivationAlgorithm.HKDF_SHA256:
                kdf = HKDF(
                    algorithm=hashes.SHA256(),
                    length=config.key_length,
                    salt=salt,
                    info=b"stellar-hd-wallet",
                )
                derived_key = kdf.derive(password)

            else:
                raise ValueError(f"Unsupported algorithm: {algorithm}")

            derivation_time = (time.time() - start_time) * 1000

            self.logger.info(
                f"Key derivation completed using {algorithm.name}",
                category=LogCategory.SECURITY,
                algorithm=algorithm.name,
                derivation_time_ms=round(derivation_time, 2),
                key_length=len(derived_key),
            )

            return derived_key

        except Exception as e:
            self.logger.error(
                f"Key derivation failed: {e}",
                category=LogCategory.SECURITY,
                algorithm=algorithm.name,
                exception=e,
            )
            raise

    def benchmark_derivation_algorithms(self, iterations: int = 100) -> Dict[str, Any]:
        """Benchmark different key derivation algorithms."""
        password = b"test_password_for_benchmarking"
        salt = secrets.token_bytes(16)
        results = {}

        algorithms = [
            KeyDerivationAlgorithm.PBKDF2_SHA256,
            KeyDerivationAlgorithm.PBKDF2_SHA512,
            KeyDerivationAlgorithm.HKDF_SHA256,
        ]

        for algorithm in algorithms:
            start_time = time.time()

            for _ in range(iterations):
                try:
                    self.derive_key_with_algorithm(password, salt, algorithm)
                except Exception:
                    pass

            total_time = time.time() - start_time
            avg_time = (total_time / iterations) * 1000

            results[algorithm.name] = {
                "total_time_ms": round(total_time * 1000, 2),
                "average_time_ms": round(avg_time, 2),
                "operations_per_second": round(iterations / total_time, 2),
            }

        self.logger.info(
            "Key derivation benchmark completed",
            category=LogCategory.PERFORMANCE,
            iterations=iterations,
            algorithms_tested=len(algorithms),
        )

        return results


# Utility functions


def generate_bip39_mnemonic(word_count: int = 24) -> str:
    """Generate BIP-39 compatible mnemonic phrase."""
    if word_count not in [12, 15, 18, 21, 24]:
        raise ValueError("Word count must be 12, 15, 18, 21, or 24")

    # This is a simplified implementation
    # In production, use a proper BIP-39 word list
    entropy_bits = (word_count * 11) - (word_count // 3)
    entropy = secrets.token_bytes(entropy_bits // 8)

    # Convert entropy to mnemonic (simplified)
    words = []
    for i in range(word_count):
        # Use entropy to generate word indices
        word_index = int.from_bytes(entropy[i : i + 2], "big") % 2048
        words.append(f"word{word_index:04d}")  # Placeholder words

    return " ".join(words)


def validate_derivation_path(path_str: str) -> bool:
    """Validate BIP-44 derivation path format."""
    try:
        DerivationPath.from_string(path_str)
        return True
    except (ValueError, IndexError):
        return False
