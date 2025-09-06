"""
Stellar Key Derivation and Storage System
Main interface for hierarchical deterministic wallets and key derivation.
"""

import asyncio
import secrets
import time
from typing import Dict, List, Optional, Any, Tuple

from stellar_sdk import Keypair

from .stellar_logging import get_stellar_logger, LogCategory
from .stellar_security_types import SecurityLevel
from .stellar_key_derivation_types import (
    DerivationType,
    KeyDerivationAlgorithm,
    DerivationPath,
    MasterSeed,
    ExtendedKey,
    DerivationConfig,
    KeyDerivationResult,
)
from .stellar_key_derivation_core import SecureKeyDerivation
from .stellar_key_derivation_manager import HierarchicalKeyManager


# Main API - expose the key classes
__all__ = [
    "DerivationType",
    "KeyDerivationAlgorithm", 
    "DerivationPath",
    "MasterSeed",
    "ExtendedKey",
    "DerivationConfig",
    "KeyDerivationResult",
    "SecureKeyDerivation",
    "HierarchicalKeyManager",
    "generate_bip39_mnemonic",
    "validate_derivation_path",
    "benchmark_key_derivation",
]


# Utility functions for key derivation

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
        word_index = int.from_bytes(entropy[i:i+2], 'big') % 2048
        words.append(f"word{word_index:04d}")  # Placeholder words
    
    return " ".join(words)


def validate_derivation_path(path_str: str) -> bool:
    """Validate BIP-44 derivation path format."""
    try:
        DerivationPath.from_string(path_str)
        return True
    except (ValueError, IndexError):
        return False


async def benchmark_key_derivation(iterations: int = 1000) -> Dict[str, Any]:
    """Benchmark key derivation performance."""
    logger = get_stellar_logger()
    derivation = SecureKeyDerivation(SecurityLevel.DEVELOPMENT)
    
    logger.info(
        f"Starting key derivation benchmark with {iterations} iterations",
        category=LogCategory.PERFORMANCE,
        iterations=iterations,
    )

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
        _ = derivation.derive_path(master_key, path)
        child_key_times.append(time.time() - child_start)

    total_time = time.time() - start_time

    results = {
        "total_time": total_time,
        "master_key_time": master_key_time,
        "average_child_key_time": (
            sum(child_key_times) / len(child_key_times) if child_key_times else 0
        ),
        "child_keys_derived": len(child_key_times),
        "keys_per_second": len(child_key_times) / total_time if total_time > 0 else 0,
    }

    logger.info(
        "Key derivation benchmark completed",
        category=LogCategory.PERFORMANCE,
        **results,
    )

    return results


# Convenience factory functions

def create_hd_wallet_manager(security_level: SecurityLevel = SecurityLevel.PRODUCTION) -> HierarchicalKeyManager:
    """Create a new hierarchical deterministic wallet manager."""
    return HierarchicalKeyManager(security_level)


def create_key_derivation_engine(security_level: SecurityLevel = SecurityLevel.PRODUCTION) -> SecureKeyDerivation:
    """Create a new secure key derivation engine.""" 
    return SecureKeyDerivation(security_level)


def derive_stellar_account(
    mnemonic: str, 
    account_index: int = 0,
    passphrase: str = "",
    security_level: SecurityLevel = SecurityLevel.PRODUCTION
) -> Keypair:
    """Derive a Stellar account keypair from mnemonic phrase."""
    derivation = SecureKeyDerivation(security_level)
    master_seed = derivation.seed_from_mnemonic(mnemonic, passphrase)
    master_key = derivation.derive_master_key(master_seed)
    
    path = DerivationPath(account=account_index)
    derived_key = derivation.derive_path(master_key, path)
    
    stellar_keypair = derivation.derive_stellar_keypair(derived_key)
    if not stellar_keypair:
        raise RuntimeError("Failed to derive Stellar keypair")
    
    return stellar_keypair


def create_deterministic_accounts(
    entropy_bits: int = 256,
    account_count: int = 10,
    security_level: SecurityLevel = SecurityLevel.PRODUCTION
) -> List[Tuple[int, Keypair, DerivationPath]]:
    """Create multiple deterministic accounts from random entropy."""
    derivation = SecureKeyDerivation(security_level)
    master_seed = derivation.generate_master_seed(entropy_bits)
    master_key = derivation.derive_master_key(master_seed)
    
    accounts = []
    for account_index in range(account_count):
        path = DerivationPath(account=account_index)
        derived_key = derivation.derive_path(master_key, path)
        stellar_keypair = derivation.derive_stellar_keypair(derived_key)
        
        if not stellar_keypair:
            raise RuntimeError(f"Failed to derive keypair for account {account_index}")
            
        accounts.append((account_index, stellar_keypair, path))
    
    return accounts