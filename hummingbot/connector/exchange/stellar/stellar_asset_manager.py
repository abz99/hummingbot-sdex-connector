"""
Modern Asset Manager with Automated Trustline Management
Enhanced asset operations and validation.
"""

import asyncio
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from .stellar_chain_interface import ModernStellarChainInterface
    from .stellar_observability import StellarObservabilityFramework
    from .stellar_security import EnterpriseSecurityFramework

from stellar_sdk import Asset


@dataclass
class AssetInfo:
    """Enhanced asset information."""

    asset: Asset
    issuer_domain: Optional[str] = None
    asset_type: Optional[str] = None
    verified: bool = False
    liquidity_score: Optional[float] = None
    risk_rating: Optional[str] = None


class ModernAssetManager:
    """
    Modern Asset Management with Automated Operations

    Features:
    - Automatic trustline creation
    - Asset registry integration
    - Enhanced validation
    - Liquidity assessment
    - Risk scoring
    """

    def __init__(
        self,
        chain_interface: "ModernStellarChainInterface",
        observability: "StellarObservabilityFramework",
        security_framework: Optional["EnterpriseSecurityFramework"] = None,
    ) -> None:
        self.chain_interface = chain_interface
        self.observability = observability
        self.security_framework = security_framework

        # Asset registry and caching
        self.asset_registry: Dict[str, AssetInfo] = {}
        self.trustline_cache: Dict[str, Dict] = {}

        # Asset directories
        self.asset_directories = [
            "https://api.stellarterm.com/directory",
            "https://stellar.expert/api/explorer/directory",
        ]

    async def initialize(self) -> None:
        """Initialize asset manager and load registries."""
        await self._load_asset_directories()
        await self.observability.log_event(
            "asset_manager_initialized", {"registered_assets": len(self.asset_registry)}
        )

    async def cleanup(self) -> None:
        """Cleanup asset manager resources."""
        self.asset_registry.clear()
        self.trustline_cache.clear()
        await self.observability.log_event("asset_manager_cleaned_up")

    async def ensure_trustline(
        self, account_id: str, asset: Asset, limit: Optional[str] = None
    ) -> bool:
        """
        Ensure trustline exists for asset.

        Args:
            account_id: Account that needs trustline
            asset: Asset to create trustline for
            limit: Optional trust limit (None for unlimited)

        Returns:
            True if trustline exists or was created
        """
        try:
            # Native XLM doesn't need trustline
            if asset.is_native():
                return True

            # Check if trustline already exists
            if await self._trustline_exists(account_id, asset):
                await self.observability.log_event(
                    "trustline_already_exists",
                    {
                        "account_id": account_id,
                        "asset_code": asset.code,
                        "asset_issuer": asset.issuer,
                    },
                )
                return True

            # Create trustline transaction
            keypair = await self._get_account_keypair(account_id)
            if not keypair:
                await self.observability.log_error(
                    "trustline_creation_failed",
                    ValueError("Account keypair not available"),
                    {"account_id": account_id},
                )
                return False

            transaction_builder = await self.chain_interface.create_trustline_transaction(
                source_keypair=keypair, asset=asset, limit=limit
            )

            # Submit transaction
            response = await self.chain_interface.submit_transaction(
                transaction_builder=transaction_builder, source_keypair=keypair
            )

            if response and hasattr(response, "hash"):
                # Update trustline cache
                cache_key = f"{account_id}:{asset.code}:{asset.issuer}"
                self.trustline_cache[cache_key] = {
                    "exists": True,
                    "limit": limit,
                    "transaction_hash": response.hash,
                }

                await self.observability.log_event(
                    "trustline_created_successfully",
                    {
                        "account_id": account_id,
                        "asset_code": asset.code,
                        "asset_issuer": asset.issuer,
                        "transaction_hash": response.hash,
                        "limit": limit,
                    },
                )
                return True
            else:
                await self.observability.log_error(
                    "trustline_creation_failed",
                    ValueError("Invalid transaction response"),
                    {"account_id": account_id, "asset_code": asset.code},
                )
                return False

        except Exception as e:
            await self.observability.log_error(
                "trustline_creation_failed",
                e,
                {
                    "account_id": account_id,
                    "asset_code": asset.code if hasattr(asset, "code") else "native",
                    "asset_issuer": asset.issuer if hasattr(asset, "issuer") else None,
                },
            )
            return False

    async def is_asset_supported(self, asset: Asset) -> bool:
        """
        Check if asset is supported for trading.

        Args:
            asset: Asset to check

        Returns:
            True if asset is supported
        """
        try:
            # Native XLM is always supported
            if asset.is_native():
                return True

            # Check if asset exists in registry
            asset_info = await self.validate_asset(asset)

            # For now, support all assets with valid format
            # In production, would check against verified asset lists
            return asset_info is not None and asset_info.asset is not None

        except Exception as e:
            await self.observability.log_error(
                "asset_support_check_failed",
                e,
                {"asset_code": asset.code if hasattr(asset, "code") else "native"},
            )
            return False

    async def validate_asset(self, asset: Asset) -> AssetInfo:
        """
        Validate asset and return enhanced information.

        Args:
            asset: Asset to validate

        Returns:
            Enhanced asset information
        """
        try:
            asset_key = self._get_asset_key(asset)

            if asset_key in self.asset_registry:
                return self.asset_registry[asset_key]

            # Validate asset format
            is_valid = self._validate_asset_format(asset)

            # Create new asset info with validation
            asset_info = AssetInfo(
                asset=asset,
                verified=is_valid,
                risk_rating="low" if asset.is_native() else "medium",
                liquidity_score=1.0 if asset.is_native() else 0.5,
            )

            self.asset_registry[asset_key] = asset_info

            await self.observability.log_event(
                "asset_validated",
                {
                    "asset_code": asset.code if hasattr(asset, "code") else "native",
                    "asset_issuer": asset.issuer if hasattr(asset, "issuer") else None,
                    "verified": is_valid,
                    "risk_rating": asset_info.risk_rating,
                },
            )

            return asset_info

        except Exception as e:
            await self.observability.log_error(
                "asset_validation_failed",
                e,
                {"asset_key": self._get_asset_key(asset) if asset else "unknown"},
            )
            # Return default asset info for error cases
            return AssetInfo(asset=asset, verified=False, risk_rating="high")

    async def get_account_balances(self, account_id: str) -> Dict[str, Decimal]:
        """
        Get account balances for all assets.

        Args:
            account_id: Account ID to get balances for

        Returns:
            Dictionary of asset codes to balances
        """
        try:
            account = await self.chain_interface.get_account_with_retry(account_id)
            if not account:
                return {}

            balances = {}
            for balance_data in getattr(account, "balances", []):
                asset_type = balance_data.get("asset_type", "native")

                if asset_type == "native":
                    balances["XLM"] = Decimal(balance_data.get("balance", "0"))
                else:
                    asset_code = balance_data.get("asset_code", "")
                    balances[asset_code] = Decimal(balance_data.get("balance", "0"))

            await self.observability.log_event(
                "account_balances_retrieved",
                {"account_id": account_id, "balance_count": len(balances)},
            )

            return balances

        except Exception as e:
            await self.observability.log_error(
                "balance_retrieval_failed", e, {"account_id": account_id}
            )
            return {}

    def _validate_asset_format(self, asset: Asset) -> bool:
        """Validate asset format and structure."""
        try:
            if asset.is_native():
                return True

            # Check asset code length (1-12 characters)
            if not asset.code or len(asset.code) == 0 or len(asset.code) > 12:
                return False

            # Check issuer format (valid Stellar public key)
            if not asset.issuer or len(asset.issuer) != 56:
                return False

            # Additional validation could be added here
            return True

        except Exception:
            return False

    async def _trustline_exists(self, account_id: str, asset: Asset) -> bool:
        """Check if trustline exists for asset."""
        try:
            # Check cache first
            cache_key = f"{account_id}:{asset.code}:{asset.issuer}"
            if cache_key in self.trustline_cache:
                return self.trustline_cache[cache_key].get("exists", False)

            # Fetch account data
            account = await self.chain_interface.get_account_with_retry(account_id)
            if not account:
                return False

            # Check balances for trustline
            for balance_data in getattr(account, "balances", []):
                asset_type = balance_data.get("asset_type", "native")

                if asset_type != "native":
                    balance_code = balance_data.get("asset_code", "")
                    balance_issuer = balance_data.get("asset_issuer", "")

                    if balance_code == asset.code and balance_issuer == asset.issuer:
                        # Cache the result
                        self.trustline_cache[cache_key] = {"exists": True}
                        return True

            # Cache negative result
            self.trustline_cache[cache_key] = {"exists": False}
            return False

        except Exception as e:
            await self.observability.log_error(
                "trustline_check_failed", e, {"account_id": account_id, "asset_code": asset.code}
            )
            return False

    async def _get_account_keypair(self, account_id: str):
        """Get keypair for account (security framework integration)."""
        try:
            if self.security_framework:
                keypair = await self.security_framework.get_keypair(account_id)
                if keypair:
                    await self.observability.log_event(
                        "account_keypair_retrieved", {"account_id": account_id, "status": "success"}
                    )
                    return keypair
                else:
                    await self.observability.log_event(
                        "account_keypair_not_found",
                        {"account_id": account_id, "status": "not_found"},
                    )
                    return None
            else:
                await self.observability.log_event(
                    "account_keypair_requested",
                    {"account_id": account_id, "status": "security_framework_not_configured"},
                )
                return None

        except Exception as e:
            await self.observability.log_error(
                "keypair_retrieval_error", e, {"account_id": account_id}
            )
            return None

    def _get_asset_key(self, asset: Asset) -> str:
        """Generate unique key for asset."""
        if asset.is_native():
            return "XLM:native"
        return f"{asset.code}:{asset.issuer}"

    async def _load_asset_directories(self) -> None:
        """Load asset information from directories."""
        try:
            # Load well-known assets
            well_known_assets = [
                # Native XLM
                ("XLM", None, True, "low", 1.0),
                # Common testnet assets
                (
                    "USDC",
                    "GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5",
                    True,
                    "low",
                    0.8,
                ),
                (
                    "EUR",
                    "GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5",
                    True,
                    "low",
                    0.7,
                ),
            ]

            for code, issuer, verified, risk, liquidity in well_known_assets:
                if issuer:
                    asset = Asset(code, issuer)
                else:
                    asset = Asset.native()

                asset_key = self._get_asset_key(asset)
                self.asset_registry[asset_key] = AssetInfo(
                    asset=asset, verified=verified, risk_rating=risk, liquidity_score=liquidity
                )

            await self.observability.log_event(
                "asset_directories_loaded", {"loaded_assets": len(well_known_assets)}
            )

        except Exception as e:
            await self.observability.log_error("asset_directory_loading_failed", e)
