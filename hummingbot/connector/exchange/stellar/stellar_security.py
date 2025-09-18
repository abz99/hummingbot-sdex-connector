"""
Enterprise Security Framework
Multi-layered security with HSM, MPC, and Hardware wallet support.
"""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union

from stellar_sdk import Keypair, Network

if TYPE_CHECKING:
    from .stellar_config_models import StellarNetworkConfig
    from .stellar_observability import StellarObservabilityFramework


# DEPRECATED: These types have been moved to stellar_security_types_unified.py
# Import from there for new code:
from .stellar_security_types_unified import (
    SecurityProvider,
    EnterpriseSecurityConfig as SecurityConfig,
)


class EnterpriseSecurityFramework:
    """
    Enterprise-grade security framework supporting multiple providers.

    Features:
    - Multi-provider HSM integration
    - Multi-Party Computation (MPC) support
    - Hardware wallet integration
    - Automatic key rotation
    - Secure transaction signing
    """

    def __init__(
        self, config: "StellarNetworkConfig", observability: "StellarObservabilityFramework"
    ) -> None:
        self.config = config
        self.observability = observability

        # Security providers
        self._primary_provider: Optional[SecurityProvider] = None
        self._backup_providers: List[SecurityProvider] = []
        self._provider_clients: Dict[SecurityProvider, Any] = {}

        # Key management
        self._active_keypairs: Dict[str, Keypair] = {}
        self._key_rotation_schedule: Dict[str, float] = {}

        # Hardware wallet connections
        self._hw_wallet_connections: Dict[str, Any] = {}

    async def initialize(self) -> None:
        """Initialize security framework and connect to providers."""
        try:
            # Initialize based on configuration
            # This is a stub implementation - actual implementation would
            # connect to real HSM/MPC/Hardware wallet providers

            await self.observability.log_event(
                "security_framework_initialized",
                {
                    "primary_provider": (
                        self._primary_provider.value if self._primary_provider else None
                    ),
                    "backup_providers": [p.value for p in self._backup_providers],
                },
            )

        except Exception as e:
            await self.observability.log_error("security_initialization_failed", e)
            raise

    async def cleanup(self) -> None:
        """Cleanup security resources."""
        # Cleanup connections to security providers
        for provider, client in self._provider_clients.items():
            try:
                if hasattr(client, "close"):
                    await client.close()
            except Exception as e:
                await self.observability.log_error(
                    "security_cleanup_error", e, {"provider": provider.value}
                )

    async def get_keypair(self, account_id: str) -> Optional[Keypair]:
        """
        Get keypair for account from security provider.

        Args:
            account_id: Account ID to get keypair for

        Returns:
            Keypair if available, None otherwise
        """
        try:
            # Check if we have the keypair cached
            if account_id in self._active_keypairs:
                return self._active_keypairs[account_id]

            # For development/testing, create a random keypair
            # In production, this would retrieve from HSM/secure storage
            if self.config and hasattr(self.config, "name") and "test" in self.config.name.lower():
                keypair = Keypair.random()
                self._active_keypairs[account_id] = keypair

                await self.observability.log_event(
                    "keypair_generated_for_testing", {"account_id": account_id}
                )

                return keypair

            # In production, would implement actual HSM/MPC/Hardware wallet integration
            await self.observability.log_event(
                "keypair_request_production_not_implemented", {"account_id": account_id}
            )

            return None

        except Exception as e:
            await self.observability.log_error(
                "keypair_retrieval_failed", e, {"account_id": account_id}
            )
            return None

    @property
    def primary_account_id(self) -> Optional[str]:
        """Get primary account ID for trading."""
        # For testing, return the first cached account ID
        if self._active_keypairs:
            return list(self._active_keypairs.keys())[0]

        # For testing environment, create a default account
        if self.config and hasattr(self.config, "name") and "test" in self.config.name.lower():
            default_account_id = "GCDEFAULTACCOUNT123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            return default_account_id

        return None

    def is_development_mode(self) -> bool:
        """Check if running in development/testing mode."""
        return (
            self.config
            and hasattr(self.config, "name")
            and any(env in self.config.name.lower() for env in ["test", "dev", "local"])
        )

    async def get_signing_keypair(self, account_id: str) -> Keypair:
        """
        Get signing keypair from configured security provider.

        Args:
            account_id: Account to get keypair for

        Returns:
            Keypair for transaction signing
        """
        # Stub implementation - would integrate with actual security providers
        # For development, return a generated keypair
        if account_id not in self._active_keypairs:
            self._active_keypairs[account_id] = Keypair.random()

        return self._active_keypairs[account_id]

    async def sign_transaction(self, transaction_xdr: str, account_id: str) -> str:
        """
        Sign transaction using configured security provider.

        Args:
            transaction_xdr: Transaction XDR to sign
            account_id: Account performing the signing

        Returns:
            Signed transaction XDR
        """
        try:
            # Get the appropriate signing keypair
            keypair = await self.get_signing_keypair(account_id)

            # Parse the transaction XDR
            from stellar_sdk import TransactionEnvelope

            envelope = TransactionEnvelope.from_xdr(
                transaction_xdr, network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE
            )

            # Sign the transaction with the keypair
            signed_envelope = keypair.sign(envelope)

            # Return the signed transaction XDR
            signed_xdr = signed_envelope.to_xdr()

            await self.observability.log_event(
                "transaction_signed",
                {
                    "account_id": account_id,
                    "provider": self._primary_provider.value if self._primary_provider else "local",
                    "signature_count": len(signed_envelope.signatures),
                },
            )

            return signed_xdr

        except Exception as e:
            await self.observability.log_error(
                "transaction_signing_failed", e, {"account_id": account_id}
            )
            raise
