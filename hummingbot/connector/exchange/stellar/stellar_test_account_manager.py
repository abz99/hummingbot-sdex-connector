"""
Stellar Test Account Manager - Refactored
Main interface for hierarchical test account management system.
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Union

from stellar_sdk import Keypair

from .stellar_account_factory import StellarAccountFactory
from .stellar_account_pool_manager import StellarAccountPoolManager
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


class StellarTestAccountManager:
    """Advanced test account management system - refactored."""

    def __init__(
        self,
        network_manager: StellarNetworkManager,
        storage_path: Optional[str] = None,
    ) -> None:
        self.network_manager = network_manager
        self.storage_path = storage_path or "test_accounts.json"
        self.logger = get_stellar_logger()

        # Core components
        self.hd_manager = HierarchicalKeyManager(SecurityLevel.DEVELOPMENT)
        self._master_wallet_id = "test_accounts_master"

        # Modular components
        self.account_factory = StellarAccountFactory(
            network_manager, self.hd_manager, self._master_wallet_id
        )
        self.pool_manager = StellarAccountPoolManager(self.account_factory)

        # Account storage
        self._accounts: Dict[str, TestAccount] = {}
        self._accounts_by_type: Dict[TestAccountType, List[str]] = {}
        self._accounts_by_network: Dict[StellarNetwork, List[str]] = {}

        # Initialize
        asyncio.create_task(self._initialize())

    async def _initialize(self) -> None:
        """Initialize the test account manager."""
        try:
            # Create master HD wallet for deterministic accounts
            self.hd_manager.create_wallet(self._master_wallet_id)

            # Load existing accounts
            await self._load_accounts()

            # Clean up expired accounts
            await self._cleanup_expired_accounts()

            self.logger.info(
                "Test account manager initialized",
                category=LogCategory.SECURITY,
                total_accounts=len(self._accounts),
                master_wallet_id=self._master_wallet_id,
            )

        except Exception as e:
            self.logger.error(
                f"Failed to initialize test account manager: {e}",
                category=LogCategory.SECURITY,
                exception=e,
            )

    # Main API methods

    async def create_test_account(
        self, network: StellarNetwork, config: TestAccountConfig, account_name: Optional[str] = None
    ) -> TestAccount:
        """Create a new test account."""
        account = await self.account_factory.create_test_account(network, config, account_name)

        # Store in local registry
        self._accounts[account.account_id] = account
        self._add_to_indices(account)

        # Save to storage
        await self._save_accounts()

        return account

    async def get_test_account(
        self,
        account_type: Optional[TestAccountType] = None,
        network: Optional[StellarNetwork] = None,
        tags: Optional[List[str]] = None,
        min_balance: float = 0.0,
    ) -> Optional[TestAccount]:
        """Get an available test account matching criteria."""
        # Filter available accounts
        available_accounts = [
            account
            for account in self._accounts.values()
            if account.status in [AccountStatus.ACTIVE, AccountStatus.FUNDED]
            and not account.is_expired
            and account.xlm_balance >= min_balance
        ]

        # Apply filters
        if account_type:
            available_accounts = [a for a in available_accounts if a.account_type == account_type]

        if network:
            available_accounts = [a for a in available_accounts if a.network == network]

        if tags:
            available_accounts = [
                a for a in available_accounts if any(tag in a.tags for tag in tags)
            ]

        if not available_accounts:
            return None

        # Select account and mark as in use
        account = available_accounts[0]
        account.touch()
        await self._save_accounts()

        return account

    def return_test_account(self, account_id: str) -> bool:
        """Return a test account (mark as available)."""
        if account_id not in self._accounts:
            return False

        account = self._accounts[account_id]
        account.last_used = time.time()

        # Try returning to pool first
        if self.pool_manager.return_pool_account(account_id):
            return True

        # Otherwise just update last used time
        asyncio.create_task(self._save_accounts())
        return True

    # Pool management interface

    async def create_account_pool(
        self,
        pool_name: str,
        network: StellarNetwork,
        config: TestAccountConfig,
        pool_size: int = 10,
        auto_refill: bool = True,
        min_available: int = 2,
    ) -> bool:
        """Create a pool of test accounts."""
        success = await self.pool_manager.create_account_pool(
            pool_name, network, config, pool_size, auto_refill, min_available
        )

        if success:
            # Add pool accounts to main registry
            pool_info = self.pool_manager.get_pool_accounts(pool_name)
            for account_id in pool_info.get("available_accounts", []) + pool_info.get(
                "in_use_accounts", []
            ):
                if account_id in self._accounts:
                    continue

                # Create minimal account entry (pool manages the details)
                account = TestAccount(
                    account_id=account_id,
                    keypair=Keypair.from_public_key(account_id),  # Placeholder
                    account_type=config.account_type,
                    network=network,
                    status=AccountStatus.ACTIVE,
                )
                account.tags.append(f"pool:{pool_name}")
                self._accounts[account_id] = account
                self._add_to_indices(account)

            await self._save_accounts()

        return success

    def get_pool_account(self, pool_name: str) -> Optional[TestAccount]:
        """Get account from pool."""
        account_id = self.pool_manager.get_pool_account(pool_name)
        if account_id and account_id in self._accounts:
            account = self._accounts[account_id]
            account.touch()
            return account
        return None

    # Account management

    async def refresh_account_balance(self, account_id: str) -> bool:
        """Refresh account balance from network."""
        if account_id not in self._accounts:
            return False

        account = self._accounts[account_id]

        try:
            server = self.network_manager.get_server(account.network)
            account_data = server.load_account(account_id)

            # Update XLM balance
            for balance in account_data.balances:
                if balance["asset_type"] == "native":
                    account.xlm_balance = float(balance["balance"])
                else:
                    # Update custom asset balances
                    asset_key = f"{balance['asset_code']}:{balance['asset_issuer']}"
                    account.custom_assets[asset_key] = float(balance["balance"])

            account.last_used = time.time()
            await self._save_accounts()

            self.logger.debug(
                f"Refreshed account balance: {account_id[:8]}...",
                category=LogCategory.SECURITY,
                xlm_balance=account.xlm_balance,
                custom_assets_count=len(account.custom_assets),
            )

            return True

        except Exception as e:
            self.logger.warning(
                f"Failed to refresh account balance: {e}",
                category=LogCategory.SECURITY,
                account_id=account_id[:8] + "...",
                exception=e,
            )
            return False

    def list_accounts(
        self,
        account_type: Optional[TestAccountType] = None,
        network: Optional[StellarNetwork] = None,
        status: Optional[AccountStatus] = None,
        include_expired: bool = False,
    ) -> List[TestAccount]:
        """List accounts with optional filtering."""
        accounts = list(self._accounts.values())

        if account_type:
            accounts = [a for a in accounts if a.account_type == account_type]

        if network:
            accounts = [a for a in accounts if a.network == network]

        if status:
            accounts = [a for a in accounts if a.status == status]

        if not include_expired:
            accounts = [a for a in accounts if not a.is_expired]

        return accounts

    def get_account_statistics(self) -> Dict[str, Any]:
        """Get comprehensive account statistics."""
        stats = {
            "total_accounts": len(self._accounts),
            "by_type": {},
            "by_network": {},
            "by_status": {},
            "expired_accounts": 0,
            "active_pools": len(self.pool_manager.list_pools()),
            "pool_statistics": self.pool_manager.get_pool_statistics(),
        }

        for account in self._accounts.values():
            # By type
            type_name = account.account_type.name
            stats["by_type"][type_name] = stats["by_type"].get(type_name, 0) + 1

            # By network
            network_name = account.network.value
            stats["by_network"][network_name] = stats["by_network"].get(network_name, 0) + 1

            # By status
            status_name = account.status.name
            stats["by_status"][status_name] = stats["by_status"].get(status_name, 0) + 1

            # Expired count
            if account.is_expired:
                stats["expired_accounts"] += 1

        return stats

    async def cleanup_expired_accounts(self) -> int:
        """Clean up expired accounts."""
        return await self._cleanup_expired_accounts()

    # Storage operations

    async def _load_accounts(self) -> None:
        """Load accounts from storage."""
        try:
            import aiofiles

            async with aiofiles.open(self.storage_path, "r") as f:
                data = json.loads(await f.read())

            for account_data in data.get("accounts", []):
                try:
                    account = TestAccount.from_dict(account_data)
                    self._accounts[account.account_id] = account
                    self._add_to_indices(account)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to load account: {e}",
                        category=LogCategory.SECURITY,
                        exception=e,
                    )

        except FileNotFoundError:
            # First run - no accounts file yet
            pass
        except Exception as e:
            self.logger.error(
                f"Failed to load accounts: {e}",
                category=LogCategory.SECURITY,
                exception=e,
            )

    async def _save_accounts(self) -> None:
        """Save accounts to storage."""
        try:
            data = {
                "accounts": [account.to_dict() for account in self._accounts.values()],
                "last_saved": time.time(),
            }

            import aiofiles

            async with aiofiles.open(self.storage_path, "w") as f:
                await f.write(json.dumps(data, indent=2))

        except Exception as e:
            self.logger.error(
                f"Failed to save accounts: {e}",
                category=LogCategory.SECURITY,
                exception=e,
            )

    async def _cleanup_expired_accounts(self) -> int:
        """Clean up expired accounts."""
        expired_count = 0
        expired_accounts = [
            account_id for account_id, account in self._accounts.items() if account.is_expired
        ]

        for account_id in expired_accounts:
            account = self._accounts[account_id]
            account.status = AccountStatus.EXPIRED
            expired_count += 1

        if expired_count > 0:
            await self._save_accounts()
            self.logger.info(
                f"Cleaned up {expired_count} expired accounts",
                category=LogCategory.SECURITY,
                expired_count=expired_count,
            )

        return expired_count

    def _add_to_indices(self, account: TestAccount) -> None:
        """Add account to search indices."""
        # By type
        if account.account_type not in self._accounts_by_type:
            self._accounts_by_type[account.account_type] = []
        if account.account_id not in self._accounts_by_type[account.account_type]:
            self._accounts_by_type[account.account_type].append(account.account_id)

        # By network
        if account.network not in self._accounts_by_network:
            self._accounts_by_network[account.network] = []
        if account.account_id not in self._accounts_by_network[account.network]:
            self._accounts_by_network[account.network].append(account.account_id)


# Utility configuration functions
def create_basic_test_config(
    initial_balance: float = 100.0,
    expiry_hours: int = 24,
    tags: Optional[List[str]] = None,
) -> TestAccountConfig:
    """Create basic test account configuration."""
    return TestAccountConfig(
        account_type=TestAccountType.BASIC,
        initial_xlm_balance=initial_balance,
        expiry_hours=expiry_hours,
        tags=tags or ["basic"],
    )


def create_dex_trader_config(
    initial_balance: float = 1000.0,
    trustlines: Optional[List[str]] = None,
    expiry_hours: int = 48,
) -> TestAccountConfig:
    """Create DEX trader account configuration."""
    return TestAccountConfig(
        account_type=TestAccountType.DEX_TRADER,
        initial_xlm_balance=initial_balance,
        trustlines=trustlines or [],
        expiry_hours=expiry_hours,
        tags=["dex", "trader"],
    )


def create_issuer_config(
    asset_code: str = "TEST",
    initial_balance: float = 500.0,
    expiry_hours: Optional[int] = None,
) -> TestAccountConfig:
    """Create asset issuer account configuration."""
    return TestAccountConfig(
        account_type=TestAccountType.ISSUER,
        initial_xlm_balance=initial_balance,
        custom_assets=[{"code": asset_code, "limit": "1000000"}],
        expiry_hours=expiry_hours,
        tags=["issuer", asset_code.lower()],
    )
