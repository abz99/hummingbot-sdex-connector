"""
Stellar Account Pool Manager
Pool-based account allocation and management for high-throughput operations.
"""

import time
from typing import Dict, List, Optional, Any
from collections import defaultdict

from .stellar_logging import get_stellar_logger, LogCategory
from .stellar_test_account_types import (
    TestAccount,
    TestAccountConfig,
    TestAccountType,
    AccountStatus,
)
from .stellar_network_manager import StellarNetwork
from .stellar_account_factory import StellarAccountFactory


class StellarAccountPoolManager:
    """Manages pools of test accounts for efficient allocation."""

    def __init__(self, account_factory: StellarAccountFactory):
        self.account_factory = account_factory
        self.logger = get_stellar_logger()
        
        # Account pools
        self._account_pools: Dict[str, List[str]] = defaultdict(list)
        self._pool_configs: Dict[str, Dict[str, Any]] = {}
        self._accounts_in_use: Dict[str, str] = {}  # account_id -> pool_name
        
        # Pool statistics
        self._pool_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {
            "total_created": 0,
            "currently_available": 0,
            "currently_in_use": 0,
            "total_allocations": 0,
        })

    async def create_account_pool(
        self,
        pool_name: str,
        network: StellarNetwork,
        config: TestAccountConfig,
        pool_size: int = 10,
        auto_refill: bool = True,
        min_available: int = 2,
    ) -> bool:
        """Create a pool of test accounts for high-throughput testing."""
        try:
            if pool_name in self._pool_configs:
                raise ValueError(f"Pool already exists: {pool_name}")

            self._pool_configs[pool_name] = {
                "network": network,
                "config": config,
                "pool_size": pool_size,
                "auto_refill": auto_refill,
                "min_available": min_available,
                "created_at": time.time(),
            }

            # Create initial accounts for the pool
            created_accounts = []
            for i in range(pool_size):
                account_name = f"{pool_name}_account_{i:03d}"
                account = await self.account_factory.create_test_account(
                    network, config, account_name
                )
                created_accounts.append(account.account_id)

            self._account_pools[pool_name] = created_accounts
            self._pool_stats[pool_name]["total_created"] = pool_size
            self._pool_stats[pool_name]["currently_available"] = pool_size

            self.logger.info(
                f"Created account pool: {pool_name}",
                category=LogCategory.SECURITY,
                pool_size=pool_size,
                network=network.value,
                account_type=config.account_type.name,
            )

            return True

        except Exception as e:
            self.logger.error(
                f"Failed to create account pool {pool_name}: {e}",
                category=LogCategory.SECURITY,
                exception=e,
            )
            return False

    def get_pool_account(self, pool_name: str) -> Optional[str]:
        """Get an available account from the pool."""
        if pool_name not in self._account_pools:
            self.logger.warning(
                f"Pool not found: {pool_name}",
                category=LogCategory.SECURITY,
            )
            return None

        available_accounts = [
            account_id for account_id in self._account_pools[pool_name]
            if account_id not in self._accounts_in_use
        ]

        if not available_accounts:
            self.logger.warning(
                f"No available accounts in pool: {pool_name}",
                category=LogCategory.SECURITY,
                total_in_pool=len(self._account_pools[pool_name]),
                in_use=len([a for a in self._account_pools[pool_name] if a in self._accounts_in_use]),
            )
            return None

        # Get the first available account
        account_id = available_accounts[0]
        self._accounts_in_use[account_id] = pool_name

        # Update statistics
        self._pool_stats[pool_name]["currently_available"] -= 1
        self._pool_stats[pool_name]["currently_in_use"] += 1
        self._pool_stats[pool_name]["total_allocations"] += 1

        # Check if we need to refill the pool
        pool_config = self._pool_configs[pool_name]
        if (pool_config.get("auto_refill", False) and 
            len(available_accounts) - 1 < pool_config.get("min_available", 2)):
            # Schedule async refill (don't await to avoid blocking)
            import asyncio
            asyncio.create_task(self._refill_pool(pool_name))

        self.logger.debug(
            f"Allocated account from pool: {pool_name}",
            category=LogCategory.SECURITY,
            account_id=account_id[:8] + "...",
            remaining_available=len(available_accounts) - 1,
        )

        return account_id

    def return_pool_account(self, account_id: str) -> bool:
        """Return an account to its pool."""
        if account_id not in self._accounts_in_use:
            self.logger.warning(
                f"Account not found in use: {account_id[:8]}...",
                category=LogCategory.SECURITY,
            )
            return False

        pool_name = self._accounts_in_use[account_id]
        del self._accounts_in_use[account_id]

        # Update statistics
        self._pool_stats[pool_name]["currently_available"] += 1
        self._pool_stats[pool_name]["currently_in_use"] -= 1

        self.logger.debug(
            f"Returned account to pool: {pool_name}",
            category=LogCategory.SECURITY,
            account_id=account_id[:8] + "...",
        )

        return True

    async def _refill_pool(self, pool_name: str) -> None:
        """Refill a pool with additional accounts if needed."""
        try:
            if pool_name not in self._pool_configs:
                return

            pool_config = self._pool_configs[pool_name]
            available_count = len([
                account_id for account_id in self._account_pools[pool_name]
                if account_id not in self._accounts_in_use
            ])

            min_available = pool_config.get("min_available", 2)
            if available_count >= min_available:
                return  # No refill needed

            # Create additional accounts
            accounts_to_create = min_available - available_count
            current_size = len(self._account_pools[pool_name])

            for i in range(accounts_to_create):
                account_name = f"{pool_name}_refill_{current_size + i:03d}"
                account = await self.account_factory.create_test_account(
                    pool_config["network"],
                    pool_config["config"],
                    account_name
                )
                self._account_pools[pool_name].append(account.account_id)

            # Update statistics
            self._pool_stats[pool_name]["total_created"] += accounts_to_create
            self._pool_stats[pool_name]["currently_available"] += accounts_to_create

            self.logger.info(
                f"Refilled pool: {pool_name}",
                category=LogCategory.SECURITY,
                accounts_added=accounts_to_create,
                total_pool_size=len(self._account_pools[pool_name]),
            )

        except Exception as e:
            self.logger.error(
                f"Failed to refill pool {pool_name}: {e}",
                category=LogCategory.SECURITY,
                exception=e,
            )

    def get_pool_statistics(self, pool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics for pools."""
        if pool_name:
            if pool_name not in self._pool_stats:
                return {}
            
            stats = dict(self._pool_stats[pool_name])
            stats["pool_name"] = pool_name
            stats["pool_config"] = self._pool_configs.get(pool_name, {})
            return stats

        # Return all pool statistics
        all_stats = {}
        for pool_name in self._pool_stats:
            stats = dict(self._pool_stats[pool_name])
            stats["pool_config"] = self._pool_configs.get(pool_name, {})
            all_stats[pool_name] = stats

        return all_stats

    def list_pools(self) -> List[str]:
        """List all available pools."""
        return list(self._account_pools.keys())

    def get_pool_accounts(self, pool_name: str) -> Dict[str, Any]:
        """Get detailed information about accounts in a pool."""
        if pool_name not in self._account_pools:
            return {}

        pool_accounts = self._account_pools[pool_name]
        
        return {
            "pool_name": pool_name,
            "total_accounts": len(pool_accounts),
            "available_accounts": [
                account_id for account_id in pool_accounts
                if account_id not in self._accounts_in_use
            ],
            "in_use_accounts": [
                account_id for account_id in pool_accounts
                if account_id in self._accounts_in_use
            ],
            "pool_config": self._pool_configs.get(pool_name, {}),
            "statistics": self._pool_stats[pool_name],
        }

    async def cleanup_pool(self, pool_name: str) -> bool:
        """Clean up and remove a pool."""
        if pool_name not in self._account_pools:
            return False

        # Return all in-use accounts from this pool
        in_use_accounts = [
            account_id for account_id in self._account_pools[pool_name]
            if account_id in self._accounts_in_use
        ]
        
        for account_id in in_use_accounts:
            self.return_pool_account(account_id)

        # Remove pool data
        del self._account_pools[pool_name]
        del self._pool_configs[pool_name]
        if pool_name in self._pool_stats:
            del self._pool_stats[pool_name]

        self.logger.info(
            f"Cleaned up pool: {pool_name}",
            category=LogCategory.SECURITY,
            accounts_returned=len(in_use_accounts),
        )

        return True