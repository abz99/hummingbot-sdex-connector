"""
Stellar Test Account Manager
Advanced test account management system for development, testing, and staging environments.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Union, Tuple
from stellar_sdk import Keypair, Server, Account, TransactionBuilder, Payment, Asset
from stellar_sdk.exceptions import NotFoundError
import aiofiles

from .stellar_logging import get_stellar_logger, LogCategory
from .stellar_security_manager import StellarSecurityManager, SecurityConfig, SecurityLevel
from .stellar_key_derivation import HierarchicalKeyManager
from .stellar_network_manager import StellarNetwork, StellarNetworkManager


class TestAccountType(Enum):
    """Types of test accounts."""
    BASIC = auto()
    FUNDED = auto()
    MULTISIG = auto()
    ISSUER = auto()
    DISTRIBUTOR = auto()
    ANCHOR = auto()
    DEX_TRADER = auto()


class AccountStatus(Enum):
    """Test account status."""
    CREATED = auto()
    FUNDED = auto()
    ACTIVE = auto()
    LOCKED = auto()
    EXPIRED = auto()
    ARCHIVED = auto()


@dataclass
class TestAccountConfig:
    """Configuration for test account creation."""
    account_type: TestAccountType
    initial_xlm_balance: float = 100.0
    custom_assets: List[Dict[str, Any]] = field(default_factory=list)
    trustlines: List[str] = field(default_factory=list)
    multisig_threshold: Optional[int] = None
    multisig_signers: List[str] = field(default_factory=list)
    expiry_hours: Optional[int] = 24
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestAccount:
    """Represents a test account."""
    account_id: str
    keypair: Keypair
    account_type: TestAccountType
    network: StellarNetwork
    status: AccountStatus
    created_at: float = field(default_factory=time.time)
    last_used: float = 0
    xlm_balance: float = 0
    custom_assets: Dict[str, float] = field(default_factory=dict)
    trustlines: List[str] = field(default_factory=list)
    multisig_config: Optional[Dict[str, Any]] = None
    expiry_time: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    usage_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'account_id': self.account_id,
            'secret_key': self.keypair.secret,  # Only for test environments
            'account_type': self.account_type.name,
            'network': self.network.value,
            'status': self.status.name,
            'created_at': self.created_at,
            'last_used': self.last_used,
            'xlm_balance': self.xlm_balance,
            'custom_assets': self.custom_assets,
            'trustlines': self.trustlines,
            'multisig_config': self.multisig_config,
            'expiry_time': self.expiry_time,
            'tags': self.tags,
            'metadata': self.metadata,
            'usage_count': self.usage_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestAccount':
        """Create from dictionary."""
        keypair = Keypair.from_secret(data['secret_key'])
        return cls(
            account_id=data['account_id'],
            keypair=keypair,
            account_type=TestAccountType[data['account_type']],
            network=StellarNetwork(data['network']),
            status=AccountStatus[data['status']],
            created_at=data['created_at'],
            last_used=data['last_used'],
            xlm_balance=data['xlm_balance'],
            custom_assets=data.get('custom_assets', {}),
            trustlines=data.get('trustlines', []),
            multisig_config=data.get('multisig_config'),
            expiry_time=data.get('expiry_time'),
            tags=data.get('tags', []),
            metadata=data.get('metadata', {}),
            usage_count=data.get('usage_count', 0)
        )


class StellarTestAccountManager:
    """Advanced test account management system."""
    
    def __init__(
        self,
        network_manager: StellarNetworkManager,
        security_manager: Optional[StellarSecurityManager] = None,
        storage_path: Optional[str] = None
    ):
        self.network_manager = network_manager
        self.security_manager = security_manager
        self.storage_path = storage_path or "test_accounts.json"
        self.logger = get_stellar_logger()
        
        # Account storage
        self._accounts: Dict[str, TestAccount] = {}
        self._accounts_by_type: Dict[TestAccountType, List[str]] = {}
        self._accounts_by_network: Dict[StellarNetwork, List[str]] = {}
        
        # HD wallet for deterministic test accounts
        self.hd_manager = HierarchicalKeyManager(SecurityLevel.DEVELOPMENT)
        self._master_wallet_id = "test_accounts_master"
        
        # Account pools for different purposes
        self._account_pools: Dict[str, List[str]] = {
            'available': [],
            'in_use': [],
            'expired': []
        }
        
        # Initialize
        asyncio.create_task(self._initialize())
    
    async def _initialize(self):
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
                master_wallet_id=self._master_wallet_id
            )
            
        except Exception as e:
            self.logger.error(
                f"Failed to initialize test account manager: {e}",
                category=LogCategory.SECURITY,
                exception=e
            )
    
    async def create_test_account(
        self,
        network: StellarNetwork,
        config: TestAccountConfig,
        account_name: Optional[str] = None
    ) -> TestAccount:
        """Create a new test account."""
        try:
            # Generate keypair (deterministic if no name specified)
            if account_name:
                # Use named account for reproducibility
                keypair = await self._get_named_account_keypair(account_name, network)
            else:
                # Generate new account from HD wallet
                account_index = len(self._accounts)
                keypair = self.hd_manager.get_account_keypair(
                    self._master_wallet_id,
                    account_index
                )
            
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
                metadata=dict(config.metadata)
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
            
            # Configure multisig if needed
            if config.account_type == TestAccountType.MULTISIG:
                await self._configure_multisig(test_account, config)
            
            # Set up custom assets if needed
            if config.account_type == TestAccountType.ISSUER:
                await self._setup_issuer_account(test_account, config)
            
            # Store account
            self._accounts[account_id] = test_account
            self._add_to_indices(test_account)
            
            # Save to storage
            await self._save_accounts()
            
            self.logger.info(
                f"Created test account: {account_id}",
                category=LogCategory.SECURITY,
                account_id=account_id,
                account_type=config.account_type.name,
                network=network.value,
                funded=test_account.status == AccountStatus.FUNDED
            )
            
            return test_account
            
        except Exception as e:
            self.logger.error(
                f"Failed to create test account: {e}",
                category=LogCategory.SECURITY,
                exception=e
            )
            raise
    
    async def get_test_account(
        self,
        account_type: Optional[TestAccountType] = None,
        network: Optional[StellarNetwork] = None,
        tags: Optional[List[str]] = None,
        min_xlm_balance: float = 0.0
    ) -> Optional[TestAccount]:
        """Get an available test account matching criteria."""
        candidates = []
        
        for account in self._accounts.values():
            # Check if account matches criteria
            if account.status not in [AccountStatus.ACTIVE, AccountStatus.FUNDED]:
                continue
            
            if account_type and account.account_type != account_type:
                continue
            
            if network and account.network != network:
                continue
            
            if account.xlm_balance < min_xlm_balance:
                continue
            
            if tags:
                if not all(tag in account.tags for tag in tags):
                    continue
            
            # Check if account is expired
            if account.expiry_time and time.time() > account.expiry_time:
                account.status = AccountStatus.EXPIRED
                continue
            
            candidates.append(account)
        
        if not candidates:
            return None
        
        # Sort by last used (least recently used first)
        candidates.sort(key=lambda a: a.last_used)
        
        # Mark as active and update usage
        selected_account = candidates[0]
        selected_account.status = AccountStatus.ACTIVE
        selected_account.last_used = time.time()
        selected_account.usage_count += 1
        
        # Move to in-use pool
        if selected_account.account_id in self._account_pools['available']:
            self._account_pools['available'].remove(selected_account.account_id)
        self._account_pools['in_use'].append(selected_account.account_id)
        
        await self._save_accounts()
        
        self.logger.info(
            f"Retrieved test account: {selected_account.account_id}",
            category=LogCategory.SECURITY,
            account_id=selected_account.account_id,
            account_type=selected_account.account_type.name,
            usage_count=selected_account.usage_count
        )
        
        return selected_account
    
    async def return_test_account(self, account_id: str):
        """Return a test account to the available pool."""
        if account_id not in self._accounts:
            raise ValueError(f"Account not found: {account_id}")
        
        account = self._accounts[account_id]
        account.status = AccountStatus.FUNDED if account.xlm_balance > 0 else AccountStatus.CREATED
        
        # Move back to available pool
        if account_id in self._account_pools['in_use']:
            self._account_pools['in_use'].remove(account_id)
        if account_id not in self._account_pools['available']:
            self._account_pools['available'].append(account_id)
        
        await self._save_accounts()
        
        self.logger.info(
            f"Returned test account to pool: {account_id}",
            category=LogCategory.SECURITY,
            account_id=account_id
        )
    
    async def refresh_account_balance(self, account_id: str) -> bool:
        """Refresh account balance from network."""
        if account_id not in self._accounts:
            return False
        
        account = self._accounts[account_id]
        
        try:
            server = self.network_manager.get_server(account.network)
            account_data = await server.accounts().account_id(account_id).call()
            
            # Update XLM balance
            for balance in account_data.get('balances', []):
                if balance['asset_type'] == 'native':
                    account.xlm_balance = float(balance['balance'])
                else:
                    # Update custom asset balances
                    asset_code = balance['asset_code']
                    account.custom_assets[asset_code] = float(balance['balance'])
            
            await self._save_accounts()
            
            self.logger.debug(
                f"Refreshed balance for account: {account_id}",
                category=LogCategory.SECURITY,
                xlm_balance=account.xlm_balance,
                custom_assets=len(account.custom_assets)
            )
            
            return True
            
        except Exception as e:
            self.logger.warning(
                f"Failed to refresh account balance: {e}",
                category=LogCategory.SECURITY,
                account_id=account_id,
                exception=e
            )
            return False
    
    async def fund_account(self, account_id: str, xlm_amount: float = 100.0) -> bool:
        """Fund a test account using friendbot."""
        if account_id not in self._accounts:
            return False
        
        account = self._accounts[account_id]
        
        # Only fund on test networks
        if account.network not in [StellarNetwork.TESTNET, StellarNetwork.FUTURENET]:
            self.logger.warning(
                f"Cannot fund account on {account.network.value}",
                category=LogCategory.SECURITY,
                account_id=account_id
            )
            return False
        
        try:
            # Use network manager's friendbot functionality
            success = await self.network_manager.fund_test_account(account_id, account.network)
            
            if success:
                account.status = AccountStatus.FUNDED
                account.xlm_balance = xlm_amount  # Approximate, will be updated on refresh
                await self._save_accounts()
                
                self.logger.info(
                    f"Funded test account: {account_id}",
                    category=LogCategory.SECURITY,
                    account_id=account_id,
                    xlm_amount=xlm_amount
                )
            
            return success
            
        except Exception as e:
            self.logger.error(
                f"Failed to fund test account: {e}",
                category=LogCategory.SECURITY,
                account_id=account_id,
                exception=e
            )
            return False
    
    async def create_account_pool(
        self,
        pool_name: str,
        account_type: TestAccountType,
        network: StellarNetwork,
        count: int = 10,
        config: Optional[TestAccountConfig] = None
    ) -> List[TestAccount]:
        """Create a pool of test accounts for high-throughput testing."""
        if config is None:
            config = TestAccountConfig(account_type=account_type)
        
        accounts = []
        
        for i in range(count):
            try:
                account_name = f"{pool_name}_{i:03d}"
                account = await self.create_test_account(network, config, account_name)
                accounts.append(account)
                
                # Add to custom pool
                pool_key = f"pool_{pool_name}"
                if pool_key not in self._account_pools:
                    self._account_pools[pool_key] = []
                self._account_pools[pool_key].append(account.account_id)
                
            except Exception as e:
                self.logger.error(
                    f"Failed to create account {i} in pool {pool_name}: {e}",
                    category=LogCategory.SECURITY,
                    pool_name=pool_name,
                    account_index=i,
                    exception=e
                )
        
        self.logger.info(
            f"Created account pool: {pool_name}",
            category=LogCategory.SECURITY,
            pool_name=pool_name,
            account_count=len(accounts),
            account_type=account_type.name,
            network=network.value
        )
        
        return accounts
    
    async def get_pool_account(self, pool_name: str) -> Optional[TestAccount]:
        """Get an available account from a specific pool."""
        pool_key = f"pool_{pool_name}"
        
        if pool_key not in self._account_pools:
            return None
        
        pool_accounts = self._account_pools[pool_key]
        
        # Find available account in pool
        for account_id in pool_accounts:
            if account_id in self._accounts:
                account = self._accounts[account_id]
                if account.status in [AccountStatus.FUNDED, AccountStatus.CREATED]:
                    account.status = AccountStatus.ACTIVE
                    account.last_used = time.time()
                    account.usage_count += 1
                    await self._save_accounts()
                    return account
        
        return None
    
    def list_accounts(
        self,
        account_type: Optional[TestAccountType] = None,
        network: Optional[StellarNetwork] = None,
        status: Optional[AccountStatus] = None
    ) -> List[TestAccount]:
        """List accounts matching criteria."""
        accounts = []
        
        for account in self._accounts.values():
            if account_type and account.account_type != account_type:
                continue
            if network and account.network != network:
                continue
            if status and account.status != status:
                continue
            
            accounts.append(account)
        
        return accounts
    
    def get_account_statistics(self) -> Dict[str, Any]:
        """Get statistics about managed test accounts."""
        stats = {
            'total_accounts': len(self._accounts),
            'by_type': {},
            'by_network': {},
            'by_status': {},
            'pools': {},
            'total_xlm': 0.0,
            'expired_count': 0
        }
        
        # Count by type, network, status
        for account in self._accounts.values():
            # By type
            type_name = account.account_type.name
            stats['by_type'][type_name] = stats['by_type'].get(type_name, 0) + 1
            
            # By network
            network_name = account.network.value
            stats['by_network'][network_name] = stats['by_network'].get(network_name, 0) + 1
            
            # By status
            status_name = account.status.name
            stats['by_status'][status_name] = stats['by_status'].get(status_name, 0) + 1
            
            # Total XLM
            stats['total_xlm'] += account.xlm_balance
            
            # Expired accounts
            if account.expiry_time and time.time() > account.expiry_time:
                stats['expired_count'] += 1
        
        # Pool statistics
        for pool_name, account_ids in self._account_pools.items():
            stats['pools'][pool_name] = len(account_ids)
        
        return stats
    
    async def cleanup_expired_accounts(self) -> int:
        """Clean up expired accounts."""
        return await self._cleanup_expired_accounts()
    
    async def export_accounts(self, file_path: str, include_secrets: bool = False) -> bool:
        """Export accounts to file."""
        try:
            export_data = {
                'export_time': time.time(),
                'total_accounts': len(self._accounts),
                'accounts': []
            }
            
            for account in self._accounts.values():
                account_data = account.to_dict()
                if not include_secrets:
                    account_data.pop('secret_key', None)
                export_data['accounts'].append(account_data)
            
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(json.dumps(export_data, indent=2))
            
            self.logger.info(
                f"Exported accounts to: {file_path}",
                category=LogCategory.SECURITY,
                account_count=len(self._accounts),
                include_secrets=include_secrets
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                f"Failed to export accounts: {e}",
                category=LogCategory.SECURITY,
                exception=e
            )
            return False
    
    # Private methods
    
    async def _get_named_account_keypair(self, name: str, network: StellarNetwork) -> Keypair:
        """Get deterministic keypair for named account."""
        # Use name and network to create deterministic seed
        import hashlib
        seed_data = f"{name}:{network.value}".encode()
        seed_hash = hashlib.sha256(seed_data).digest()
        
        # Create keypair from seed
        return Keypair.from_raw_ed25519_seed(seed_hash[:32])
    
    async def _fund_test_account(self, account: TestAccount, config: TestAccountConfig) -> bool:
        """Fund test account using friendbot."""
        return await self.fund_account(account.account_id, config.initial_xlm_balance)
    
    async def _configure_multisig(self, account: TestAccount, config: TestAccountConfig):
        """Configure multisig for test account."""
        # This would implement multisig configuration
        # Placeholder for now
        account.multisig_config = {
            'threshold': config.multisig_threshold,
            'signers': config.multisig_signers
        }
    
    async def _setup_issuer_account(self, account: TestAccount, config: TestAccountConfig):
        """Set up account as asset issuer."""
        # This would implement asset issuance
        # Placeholder for now
        account.metadata['is_issuer'] = True
        account.metadata['issued_assets'] = config.custom_assets
    
    def _add_to_indices(self, account: TestAccount):
        """Add account to internal indices."""
        # By type
        if account.account_type not in self._accounts_by_type:
            self._accounts_by_type[account.account_type] = []
        self._accounts_by_type[account.account_type].append(account.account_id)
        
        # By network
        if account.network not in self._accounts_by_network:
            self._accounts_by_network[account.network] = []
        self._accounts_by_network[account.network].append(account.account_id)
        
        # Add to available pool
        self._account_pools['available'].append(account.account_id)
    
    async def _load_accounts(self):
        """Load accounts from storage."""
        try:
            async with aiofiles.open(self.storage_path, 'r') as f:
                content = await f.read()
                data = json.loads(content)
                
                for account_data in data.get('accounts', []):
                    try:
                        account = TestAccount.from_dict(account_data)
                        self._accounts[account.account_id] = account
                        self._add_to_indices(account)
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to load account: {e}",
                            category=LogCategory.SECURITY,
                            exception=e
                        )
                        
                self.logger.info(
                    f"Loaded {len(self._accounts)} test accounts from storage",
                    category=LogCategory.SECURITY,
                    storage_path=self.storage_path
                )
                        
        except FileNotFoundError:
            # First time - no accounts to load
            pass
        except Exception as e:
            self.logger.error(
                f"Failed to load accounts: {e}",
                category=LogCategory.SECURITY,
                exception=e
            )
    
    async def _save_accounts(self):
        """Save accounts to storage."""
        try:
            save_data = {
                'saved_at': time.time(),
                'total_accounts': len(self._accounts),
                'accounts': [account.to_dict() for account in self._accounts.values()]
            }
            
            async with aiofiles.open(self.storage_path, 'w') as f:
                await f.write(json.dumps(save_data, indent=2))
                
        except Exception as e:
            self.logger.error(
                f"Failed to save accounts: {e}",
                category=LogCategory.SECURITY,
                exception=e
            )
    
    async def _cleanup_expired_accounts(self) -> int:
        """Clean up expired accounts."""
        expired_count = 0
        current_time = time.time()
        
        accounts_to_remove = []
        
        for account_id, account in self._accounts.items():
            if account.expiry_time and current_time > account.expiry_time:
                account.status = AccountStatus.EXPIRED
                accounts_to_remove.append(account_id)
                expired_count += 1
        
        # Move expired accounts
        for account_id in accounts_to_remove:
            if account_id not in self._account_pools['expired']:
                self._account_pools['expired'].append(account_id)
            
            # Remove from other pools
            for pool_accounts in self._account_pools.values():
                if account_id in pool_accounts and pool_accounts != self._account_pools['expired']:
                    pool_accounts.remove(account_id)
        
        if expired_count > 0:
            await self._save_accounts()
            self.logger.info(
                f"Cleaned up {expired_count} expired accounts",
                category=LogCategory.SECURITY,
                expired_count=expired_count
            )
        
        return expired_count


# Utility functions for test account management

def create_basic_test_config(
    xlm_balance: float = 100.0,
    expiry_hours: int = 24,
    tags: Optional[List[str]] = None
) -> TestAccountConfig:
    """Create basic test account configuration."""
    return TestAccountConfig(
        account_type=TestAccountType.FUNDED,
        initial_xlm_balance=xlm_balance,
        expiry_hours=expiry_hours,
        tags=tags or ['automated_test']
    )


def create_dex_trader_config(
    xlm_balance: float = 1000.0,
    trading_assets: Optional[List[str]] = None
) -> TestAccountConfig:
    """Create configuration for DEX trading test account."""
    assets = trading_assets or ['USDC', 'BTC', 'ETH']
    
    return TestAccountConfig(
        account_type=TestAccountType.DEX_TRADER,
        initial_xlm_balance=xlm_balance,
        trustlines=assets,
        tags=['dex', 'trading', 'automated_test'],
        metadata={
            'purpose': 'dex_trading',
            'trading_assets': assets
        }
    )


def create_issuer_config(
    assets_to_issue: List[Dict[str, Any]],
    xlm_balance: float = 500.0
) -> TestAccountConfig:
    """Create configuration for asset issuer test account."""
    return TestAccountConfig(
        account_type=TestAccountType.ISSUER,
        initial_xlm_balance=xlm_balance,
        custom_assets=assets_to_issue,
        tags=['issuer', 'assets', 'automated_test'],
        metadata={
            'purpose': 'asset_issuance',
            'assets_to_issue': [asset['code'] for asset in assets_to_issue]
        }
    )


async def setup_test_environment(
    network_manager: StellarNetworkManager,
    network: StellarNetwork = StellarNetwork.TESTNET,
    account_count: int = 10
) -> StellarTestAccountManager:
    """Set up a complete test environment with pre-funded accounts."""
    # Create test account manager
    manager = StellarTestAccountManager(network_manager)
    
    # Wait for initialization
    await asyncio.sleep(1)
    
    # Create basic test accounts pool
    basic_config = create_basic_test_config()
    await manager.create_account_pool(
        'basic_test',
        TestAccountType.FUNDED,
        network,
        account_count,
        basic_config
    )
    
    # Create DEX trading accounts
    dex_config = create_dex_trader_config()
    await manager.create_account_pool(
        'dex_trading',
        TestAccountType.DEX_TRADER,
        network,
        3,
        dex_config
    )
    
    return manager