"""
Stellar Key Derivation Manager
High-level wallet and key management interface.
"""

from typing import Any, Dict, List, Optional

from stellar_sdk import Keypair

from .stellar_key_derivation_core import SecureKeyDerivation
from .stellar_key_derivation_types import (
    DerivationPath,
    ExtendedKey,
    MasterSeed,
)
from .stellar_logging import get_stellar_logger, LogCategory
from .stellar_security_types import SecurityLevel


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
        passphrase: str = "",
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
            from_mnemonic=bool(mnemonic),
        )

        return master_seed

    def get_account_keypair(
        self, wallet_id: str, account_index: int = 0, change: int = 0, address_index: int = 0
    ) -> Keypair:
        """Get keypair for specific account path."""
        if wallet_id not in self._master_seeds:
            raise ValueError(f"Wallet not found: {wallet_id}")

        master_seed = self._master_seeds[wallet_id]
        path = DerivationPath(account=account_index, change=change, address_index=address_index)

        key_id = f"{wallet_id}:{path}"

        # Check cache first
        if key_id not in self._derived_keys:
            master_key = self.derivation.derive_master_key(master_seed)
            derived_key = self.derivation.derive_path(master_key, path)
            self._derived_keys[key_id] = derived_key

        derived_key = self._derived_keys[key_id]
        stellar_keypair = self.derivation.derive_stellar_keypair(derived_key)

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
            "wallet_id": wallet_id,
            "created_at": master_seed.created_at,
            "has_mnemonic": bool(master_seed.mnemonic),
            "has_passphrase": bool(master_seed.passphrase),
            "seed_length": len(master_seed.seed_bytes),
        }

    def delete_wallet(self, wallet_id: str) -> bool:
        """Delete a wallet from memory."""
        if wallet_id in self._master_seeds:
            del self._master_seeds[wallet_id]

            # Remove cached derived keys
            keys_to_remove = [
                key for key in self._derived_keys.keys() if key.startswith(f"{wallet_id}:")
            ]
            for key in keys_to_remove:
                del self._derived_keys[key]

            self.logger.info(
                f"Deleted HD wallet: {wallet_id}",
                category=LogCategory.SECURITY,
                wallet_id=wallet_id,
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

            accounts.append(
                {
                    "account_index": account_index,
                    "public_key": keypair.public_key,
                    "derivation_path": str(path),
                    "address": keypair.public_key,  # In Stellar, public key is the address
                }
            )

        return accounts
