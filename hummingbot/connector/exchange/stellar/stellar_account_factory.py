"""
Stellar Account Factory
Core account creation and funding operations.
"""

import asyncio
import hashlib
import time
from typing import Any, Dict, Optional

from stellar_sdk import Asset, Keypair, Payment, Server, TransactionBuilder
from stellar_sdk.exceptions import NotFoundError

from .stellar_key_derivation import HierarchicalKeyManager
from .stellar_logging import get_stellar_logger, LogCategory
from .stellar_network_manager import StellarNetwork, StellarNetworkManager
from .stellar_security_types import SecurityLevel
from .stellar_test_account_types import (
    AccountStatus,
    TestAccount,
    TestAccountConfig,
    TestAccountType,
)


class StellarAccountFactory:
    """Factory for creating and configuring test accounts."""

    def __init__(
        self,
        network_manager: StellarNetworkManager,
        hd_manager: HierarchicalKeyManager,
        master_wallet_id: str,
    ):
        self.network_manager = network_manager
        self.hd_manager = hd_manager
        self.master_wallet_id = master_wallet_id
        self.logger = get_stellar_logger()
        self._account_counter = 0

    async def create_test_account(
        self,
        network: StellarNetwork,
        config: TestAccountConfig,
        account_name: Optional[str] = None,
    ) -> TestAccount:
        """Create a new test account with specified configuration."""
        try:
            # Generate keypair
            keypair = await self._generate_keypair(account_name, network)
            account_id = keypair.public_key

            # Create test account object
            test_account = TestAccount(
                account_id=account_id,
                keypair=keypair,
                account_type=config.account_type,
                network=network,
                status=AccountStatus.CREATED,
                custom_assets=dict(config.custom_assets),
                trustlines=list(config.trustlines),
                tags=list(config.tags),
                metadata=dict(config.metadata),
            )

            # Set expiry if specified
            if config.expiry_hours:
                test_account.expiry_time = time.time() + (config.expiry_hours * 3600)

            # Fund account on testnet/futurenet
            if network in [StellarNetwork.TESTNET, StellarNetwork.FUTURENET]:
                funded = await self._fund_test_account(test_account, config)
                if funded:
                    test_account.status = AccountStatus.FUNDED
                    test_account.xlm_balance = config.initial_xlm_balance

            # Configure specialized account types
            await self._configure_account_type(test_account, config)

            test_account.status = AccountStatus.ACTIVE

            self.logger.info(
                f"Created test account: {account_id[:8]}...",
                category=LogCategory.SECURITY,
                account_type=config.account_type.name,
                network=network.value,
                xlm_balance=test_account.xlm_balance,
            )

            return test_account

        except Exception as e:
            self.logger.error(
                f"Failed to create test account: {e}",
                category=LogCategory.SECURITY,
                exception=e,
            )
            raise

    async def _generate_keypair(
        self, account_name: Optional[str], network: StellarNetwork
    ) -> Keypair:
        """Generate keypair for test account."""
        if account_name:
            # Use named account for reproducibility
            return await self._get_named_account_keypair(account_name, network)
        else:
            # Generate new account from HD wallet
            keypair = self.hd_manager.get_account_keypair(
                self.master_wallet_id, self._account_counter
            )
            self._account_counter += 1
            return keypair

    async def _get_named_account_keypair(self, name: str, network: StellarNetwork) -> Keypair:
        """Generate deterministic keypair from name and network."""
        seed_material = f"{name}:{network.value}:stellar_test_account"
        seed_hash = hashlib.sha256(seed_material.encode()).digest()
        return Keypair.from_raw_ed25519_seed(seed_hash[:32])

    async def _fund_test_account(self, account: TestAccount, config: TestAccountConfig) -> bool:
        """Fund test account using friendbot."""
        try:
            # Get server for potential future use
            # server = self.network_manager.get_server(account.network)

            # Use friendbot to fund the account
            friendbot_url = self._get_friendbot_url(account.network)
            if not friendbot_url:
                return False

            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    friendbot_url, params={"addr": account.account_id}
                ) as response:
                    if response.status == 200:
                        self.logger.info(
                            "Successfully funded test account via friendbot",
                            category=LogCategory.SECURITY,
                            account_id=account.account_id[:8] + "...",
                            amount=config.initial_xlm_balance,
                        )
                        return True

        except Exception as e:
            self.logger.warning(
                f"Failed to fund test account: {e}",
                category=LogCategory.SECURITY,
                account_id=account.account_id[:8] + "...",
                exception=e,
            )

        return False

    async def _configure_account_type(
        self, account: TestAccount, config: TestAccountConfig
    ) -> None:
        """Configure account based on its type."""
        if config.account_type == TestAccountType.MULTISIG:
            await self._configure_multisig(account, config)
        elif config.account_type == TestAccountType.ISSUER:
            await self._setup_issuer_account(account, config)
        elif config.account_type == TestAccountType.DISTRIBUTOR:
            await self._setup_distributor_account(account, config)
        elif config.account_type == TestAccountType.DEX_TRADER:
            await self._setup_dex_trader_account(account, config)

    async def _configure_multisig(self, account: TestAccount, config: TestAccountConfig) -> None:
        """Configure multisignature settings."""
        if not config.multisig_signers or not config.multisig_threshold:
            return

        try:
            server = self.network_manager.get_server(account.network)
            account_obj = server.load_account(account.account_id)

            builder = TransactionBuilder(
                source_account=account_obj,
                network_passphrase=self.network_manager.get_network_passphrase(account.network),
                base_fee=100,
            )

            # Add signers
            for signer_key in config.multisig_signers:
                builder.append_set_options_op(signer=signer_key, signer_weight=1)

            # Set thresholds
            builder.append_set_options_op(
                low_threshold=config.multisig_threshold,
                med_threshold=config.multisig_threshold,
                high_threshold=config.multisig_threshold,
            )

            transaction = builder.build()
            transaction.sign(account.keypair)

            response = server.submit_transaction(transaction)

            account.multisig_config = {
                "threshold": config.multisig_threshold,
                "signers": config.multisig_signers,
                "transaction_hash": response["hash"],
            }

        except Exception as e:
            self.logger.error(
                f"Failed to configure multisig: {e}",
                category=LogCategory.SECURITY,
                account_id=account.account_id[:8] + "...",
                exception=e,
            )

    async def _setup_issuer_account(self, account: TestAccount, config: TestAccountConfig) -> None:
        """Set up asset issuer account."""
        account.metadata["issuer_assets"] = []
        for asset_config in config.custom_assets:
            asset_code = asset_config.get("code", "TEST")
            account.metadata["issuer_assets"].append(asset_code)

    async def _setup_distributor_account(
        self, account: TestAccount, config: TestAccountConfig
    ) -> None:
        """Set up asset distributor account."""
        account.metadata["distributor_role"] = True
        account.metadata["managed_assets"] = [
            asset_config.get("code", "TEST") for asset_config in config.custom_assets
        ]

    async def _setup_dex_trader_account(
        self, account: TestAccount, config: TestAccountConfig
    ) -> None:
        """Set up DEX trading account with trustlines."""
        account.metadata["dex_trader"] = True
        account.metadata["trading_pairs"] = config.trustlines

    def _get_friendbot_url(self, network: StellarNetwork) -> Optional[str]:
        """Get friendbot URL for network."""
        friendbot_urls = {
            StellarNetwork.TESTNET: "https://friendbot.stellar.org",
            StellarNetwork.FUTURENET: "https://friendbot-futurenet.stellar.org",
        }
        return friendbot_urls.get(network)
