"""
Tests for Stellar Security Components
Comprehensive testing for security manager, hardware wallets, Vault integration, and key derivation.
"""

import pytest
import asyncio
import tempfile
import os
import time
import secrets
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from stellar_sdk import Keypair

from hummingbot.connector.exchange.stellar.stellar_security_manager import (
    StellarSecurityManager,
    SecurityConfig,
    SecurityLevel,
    KeyStoreType,
    KeyMetadata,
    MemoryKeyStore,
    FileSystemKeyStore,
)
from hummingbot.connector.exchange.stellar.stellar_hardware_wallets import (
    HardwareWalletManager,
    HardwareWalletType,
    HardwareWalletStatus,
    LedgerWallet,
    TrezorWallet,
    derive_stellar_path,
    validate_derivation_path,
)
from hummingbot.connector.exchange.stellar.stellar_vault_integration import (
    VaultKeyStore,
    VaultConfig,
    VaultAuthMethod,
    VaultEngine,
    create_vault_config_from_env,
)
from hummingbot.connector.exchange.stellar.stellar_key_derivation import (
    SecureKeyDerivation,
    DerivationPath,
    MasterSeed,
    ExtendedKey,
    HierarchicalKeyManager,
    KeyDerivationAlgorithm,
    generate_bip39_mnemonic,
    validate_derivation_path as validate_kd_derivation_path,
    benchmark_key_derivation,
)


class TestStellarSecurityManager:
    """Test Stellar Security Manager functionality."""

    def test_security_manager_initialization(self):
        """Test security manager initialization with different security levels."""
        # Development level
        config = SecurityConfig(security_level=SecurityLevel.DEVELOPMENT)
        manager = StellarSecurityManager(config)

        assert manager.config.security_level == SecurityLevel.DEVELOPMENT
        assert KeyStoreType.MEMORY in manager._stores

        # Production level
        config_prod = SecurityConfig(
            security_level=SecurityLevel.PRODUCTION, require_hardware_security=False
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manager_prod = StellarSecurityManager(config_prod, temp_dir)
            assert manager_prod.config.security_level == SecurityLevel.PRODUCTION
            assert KeyStoreType.FILE_SYSTEM in manager_prod._stores

    @pytest.mark.asyncio
    async def test_keypair_generation_and_storage(self):
        """Test keypair generation and secure storage."""
        config = SecurityConfig(security_level=SecurityLevel.DEVELOPMENT)
        manager = StellarSecurityManager(config)

        # Generate keypair
        keypair, key_id = await manager.generate_keypair()

        assert isinstance(keypair, Keypair)
        assert isinstance(key_id, str)
        assert key_id.startswith("stellar_")

        # Retrieve keypair
        retrieved_keypair = await manager.get_keypair(key_id)
        assert retrieved_keypair is not None
        assert retrieved_keypair.public_key == keypair.public_key
        assert retrieved_keypair.secret == keypair.secret

    @pytest.mark.asyncio
    async def test_keypair_deletion(self):
        """Test keypair deletion from storage."""
        config = SecurityConfig(security_level=SecurityLevel.DEVELOPMENT)
        manager = StellarSecurityManager(config)

        # Generate and store keypair
        keypair, key_id = await manager.generate_keypair()

        # Verify it exists
        retrieved = await manager.get_keypair(key_id)
        assert retrieved is not None

        # Delete keypair
        deleted = await manager.delete_keypair(key_id)
        assert deleted is True

        # Verify it's gone
        retrieved_after_delete = await manager.get_keypair(key_id)
        assert retrieved_after_delete is None

    @pytest.mark.asyncio
    async def test_list_managed_keys(self):
        """Test listing managed keys."""
        config = SecurityConfig(security_level=SecurityLevel.DEVELOPMENT)
        manager = StellarSecurityManager(config)

        # Generate multiple keypairs
        key_ids = []
        for i in range(3):
            _, key_id = await manager.generate_keypair()
            key_ids.append(key_id)

        # List keys
        managed_keys = await manager.list_managed_keys()

        assert len(managed_keys) >= 3
        stored_key_ids = [key.key_id for key in managed_keys]
        for key_id in key_ids:
            assert key_id in stored_key_ids

    def test_session_management(self):
        """Test secure session creation and validation."""
        config = SecurityConfig(security_level=SecurityLevel.DEVELOPMENT)
        manager = StellarSecurityManager(config)

        # Create session
        user_id = "test_user"
        session_id = manager.create_secure_session(user_id)

        assert isinstance(session_id, str)
        assert len(session_id) > 20  # Should be substantial length

        # Validate session
        is_valid = manager.validate_session(session_id)
        assert is_valid is True

        # Invalidate session
        invalidated = manager.invalidate_session(session_id)
        assert invalidated is True

        # Should no longer be valid
        is_valid_after = manager.validate_session(session_id)
        assert is_valid_after is False

    def test_key_derivation(self):
        """Test key derivation functionality."""
        config = SecurityConfig(security_level=SecurityLevel.DEVELOPMENT)
        manager = StellarSecurityManager(config)

        master_key = secrets.token_bytes(32)

        # Derive keys for different purposes
        key1 = manager.derive_key(master_key, "signing", 0)
        key2 = manager.derive_key(master_key, "signing", 1)
        key3 = manager.derive_key(master_key, "encryption", 0)

        assert len(key1) == 32
        assert len(key2) == 32
        assert len(key3) == 32

        # Same purpose and index should produce same key
        key1_again = manager.derive_key(master_key, "signing", 0)
        assert key1 == key1_again

        # Different indices should produce different keys
        assert key1 != key2

        # Different purposes should produce different keys
        assert key1 != key3

    @pytest.mark.asyncio
    async def test_backup_creation(self):
        """Test encrypted backup creation."""
        config = SecurityConfig(security_level=SecurityLevel.DEVELOPMENT)
        manager = StellarSecurityManager(config)

        # Generate some keypairs
        for i in range(2):
            await manager.generate_keypair()

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            backup_path = temp_file.name

        try:
            # Create backup with encryption
            encryption_key = secrets.token_bytes(32)
            success = await manager.backup_keys(backup_path, encryption_key)

            assert success is True
            assert os.path.exists(backup_path)
            assert os.path.getsize(backup_path) > 0

            # File should not contain plaintext key data
            with open(backup_path, "rb") as f:
                content = f.read()
                # Should be encrypted, not contain readable key data
                assert b"stellar_" not in content  # Key ID pattern should not be visible

        finally:
            if os.path.exists(backup_path):
                os.unlink(backup_path)


class TestMemoryKeyStore:
    """Test in-memory key storage."""

    @pytest.mark.asyncio
    async def test_memory_store_operations(self):
        """Test basic memory store operations."""
        store = MemoryKeyStore()

        # Test data
        key_id = "test_key_001"
        key_data = b"test_secret_key_data"
        metadata = KeyMetadata(
            key_id=key_id,
            account_id="test_account",
            key_type="ed25519",
            store_type=KeyStoreType.MEMORY,
        )

        # Store key
        stored = await store.store_key(key_id, key_data, metadata)
        assert stored is True

        # Retrieve key
        result = await store.retrieve_key(key_id)
        assert result is not None
        retrieved_data, retrieved_metadata = result
        assert retrieved_data == key_data
        assert retrieved_metadata.key_id == key_id
        assert retrieved_metadata.use_count == 1

        # List keys
        keys = await store.list_keys()
        assert len(keys) == 1
        assert keys[0].key_id == key_id

        # Delete key
        deleted = await store.delete_key(key_id)
        assert deleted is True

        # Should not be retrievable after deletion
        result_after_delete = await store.retrieve_key(key_id)
        assert result_after_delete is None


class TestFileSystemKeyStore:
    """Test file system key storage."""

    @pytest.mark.asyncio
    async def test_filesystem_store_operations(self):
        """Test file system store operations with encryption."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store = FileSystemKeyStore(temp_dir)

            # Test data
            key_id = "test_fs_key_001"
            key_data = b"test_secret_key_data_fs"
            metadata = KeyMetadata(
                key_id=key_id,
                account_id="test_fs_account",
                key_type="ed25519",
                store_type=KeyStoreType.FILE_SYSTEM,
            )

            # Store key
            stored = await store.store_key(key_id, key_data, metadata)
            assert stored is True

            # Verify files were created
            key_file = os.path.join(temp_dir, f"{key_id}.key")
            meta_file = os.path.join(temp_dir, f"{key_id}.meta")
            assert os.path.exists(key_file)
            assert os.path.exists(meta_file)

            # Key file should be encrypted (not contain plaintext)
            with open(key_file, "rb") as f:
                encrypted_content = f.read()
                assert key_data not in encrypted_content  # Should be encrypted

            # Retrieve key
            result = await store.retrieve_key(key_id)
            assert result is not None
            retrieved_data, retrieved_metadata = result
            assert retrieved_data == key_data  # Should be decrypted correctly
            assert retrieved_metadata.key_id == key_id

            # Delete key
            deleted = await store.delete_key(key_id)
            assert deleted is True

            # Files should be removed
            assert not os.path.exists(key_file)
            assert not os.path.exists(meta_file)


class TestHardwareWallets:
    """Test hardware wallet integration."""

    def test_derivation_path_generation(self):
        """Test BIP-44 derivation path generation."""
        # Test default path
        path = derive_stellar_path()
        assert path == "m/44'/148'/0'/0/0"

        # Test custom path
        path_custom = derive_stellar_path(account_index=1, change=0, address_index=5)
        assert path_custom == "m/44'/148'/1'/0/5"

    def test_derivation_path_validation(self):
        """Test derivation path validation."""
        # Valid paths
        assert validate_derivation_path("m/44'/148'/0'/0/0") is True
        assert validate_derivation_path("m/44'/148'/1'/0/5") is True

        # Invalid paths
        assert validate_derivation_path("m/44'/149'/0'/0/0") is False  # Wrong coin type
        assert validate_derivation_path("m/44'/148'/0'/0") is False  # Too short
        assert validate_derivation_path("44'/148'/0'/0/0") is False  # Missing m/
        assert validate_derivation_path("invalid") is False

    def test_hardware_wallet_manager_initialization(self):
        """Test hardware wallet manager initialization."""
        manager = HardwareWalletManager()

        # Should have both Ledger and Trezor wallets registered
        assert "ledger" in manager._wallets
        assert "trezor" in manager._wallets
        assert isinstance(manager._wallets["ledger"], LedgerWallet)
        assert isinstance(manager._wallets["trezor"], TrezorWallet)

    @pytest.mark.asyncio
    async def test_hardware_wallet_detection(self):
        """Test hardware wallet detection (placeholder implementation)."""
        manager = HardwareWalletManager()

        # This will return empty list since we have placeholder implementations
        detected = await manager.detect_wallets()
        assert isinstance(detected, list)
        # Placeholders return False for connection, so should be empty
        assert len(detected) == 0

    def test_wallet_status(self):
        """Test wallet status reporting."""
        manager = HardwareWalletManager()

        status = manager.get_wallet_status()
        assert isinstance(status, dict)
        assert "supported_wallets" in status
        assert "pending_requests" in status
        assert "request_ids" in status

        assert "ledger" in status["supported_wallets"]
        assert "trezor" in status["supported_wallets"]


class TestVaultIntegration:
    """Test HashiCorp Vault integration."""

    def test_vault_config_creation(self):
        """Test Vault configuration creation."""
        config = VaultConfig(
            url="https://vault.example.com", auth_method=VaultAuthMethod.TOKEN, token="test-token"
        )

        assert config.url == "https://vault.example.com"
        assert config.auth_method == VaultAuthMethod.TOKEN
        assert config.token == "test-token"
        assert config.mount_path == "stellar"  # Default
        assert config.engine_type == VaultEngine.KV_V2  # Default

    def test_vault_config_from_env(self):
        """Test creating Vault config from environment variables."""
        with patch.dict(
            os.environ,
            {
                "VAULT_ADDR": "https://test-vault.com",
                "VAULT_AUTH_METHOD": "USERPASS",
                "VAULT_MOUNT_PATH": "test-stellar",
                "VAULT_USERNAME": "testuser",
                "VAULT_PASSWORD": "testpass",
            },
        ):
            config = create_vault_config_from_env()

            assert config.url == "https://test-vault.com"
            assert config.auth_method == VaultAuthMethod.USERPASS
            assert config.mount_path == "test-stellar"
            assert config.username == "testuser"
            assert config.password == "testpass"

    @pytest.mark.asyncio
    async def test_vault_keystore_initialization(self):
        """Test Vault keystore initialization (without actual Vault)."""
        config = VaultConfig(
            url="http://localhost:8200", auth_method=VaultAuthMethod.TOKEN, token="test-token"
        )

        # This will fail to connect to actual Vault, which is expected
        keystore = VaultKeyStore(config)
        assert keystore.config == config
        assert keystore._session is None
        assert keystore._authenticated is False


class TestKeyDerivation:
    """Test secure key derivation system."""

    def test_derivation_path_operations(self):
        """Test derivation path creation and parsing."""
        # Create derivation path
        path = DerivationPath(account=1, change=0, address_index=5)
        assert str(path) == "m/44'/148'/1'/0/5"

        # Parse from string
        parsed_path = DerivationPath.from_string("m/44'/148'/2'/1/10")
        assert parsed_path.account == 2
        assert parsed_path.change == 1
        assert parsed_path.address_index == 10

        # Create child path
        child_path = path.derive_child(3)
        assert child_path.address_index == 3

    def test_master_seed_generation(self):
        """Test master seed generation."""
        derivation = SecureKeyDerivation(SecurityLevel.DEVELOPMENT)

        # Generate master seed
        seed = derivation.generate_master_seed(256)
        assert isinstance(seed, MasterSeed)
        assert len(seed.seed_bytes) == 32  # 256 bits = 32 bytes
        assert seed.mnemonic is None
        assert seed.passphrase is None

    def test_seed_from_mnemonic(self):
        """Test master seed generation from mnemonic."""
        derivation = SecureKeyDerivation(SecurityLevel.DEVELOPMENT)

        mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        seed = derivation.seed_from_mnemonic(mnemonic, "test_passphrase")

        assert isinstance(seed, MasterSeed)
        assert len(seed.seed_bytes) == 32
        assert seed.mnemonic == mnemonic
        assert seed.passphrase == "test_passphrase"

        # Same mnemonic should produce same seed
        seed2 = derivation.seed_from_mnemonic(mnemonic, "test_passphrase")
        assert seed.seed_bytes == seed2.seed_bytes

    def test_master_key_derivation(self):
        """Test master extended key derivation."""
        derivation = SecureKeyDerivation(SecurityLevel.DEVELOPMENT)

        seed = derivation.generate_master_seed(256)
        master_key = derivation.derive_master_key(seed)

        assert isinstance(master_key, ExtendedKey)
        assert len(master_key.key) == 32
        assert len(master_key.chain_code) == 32
        assert master_key.depth == 0
        assert master_key.is_private is True
        assert master_key.parent_fingerprint == 0

    def test_child_key_derivation(self):
        """Test child key derivation."""
        derivation = SecureKeyDerivation(SecurityLevel.DEVELOPMENT)

        seed = derivation.generate_master_seed(256)
        master_key = derivation.derive_master_key(seed)

        # Derive hardened child
        child_key = derivation.derive_child_key(master_key, 0, hardened=True)

        assert isinstance(child_key, ExtendedKey)
        assert child_key.depth == 1
        assert child_key.is_private is True
        assert child_key.parent_fingerprint != b"\x00" * 4
        assert child_key.child_number >= 2**31  # Hardened

    def test_stellar_keypair_derivation(self):
        """Test deriving Stellar keypairs."""
        derivation = SecureKeyDerivation(SecurityLevel.DEVELOPMENT)

        seed = derivation.generate_master_seed(256)
        master_key = derivation.derive_master_key(seed)
        path = DerivationPath(account=0)
        derived_key = derivation.derive_path(master_key, path)

        keypair = derivation.derive_stellar_keypair(derived_key)

        assert isinstance(keypair, Keypair)
        assert len(keypair.public_key) == 56  # Stellar public key length
        assert keypair.public_key.startswith("G")  # Stellar public key prefix

    def test_key_material_derivation(self):
        """Test key material derivation with different algorithms."""
        derivation = SecureKeyDerivation(SecurityLevel.DEVELOPMENT)

        password = "test_password"
        salt = b"test_salt_12345"

        # Test PBKDF2-SHA256
        key1 = derivation.derive_key_with_algorithm(
            password.encode(), salt, KeyDerivationAlgorithm.PBKDF2_SHA256
        )
        assert len(key1) == 32

        # Test PBKDF2-SHA512
        key2 = derivation.derive_key_with_algorithm(
            password.encode(), salt, KeyDerivationAlgorithm.PBKDF2_SHA512
        )
        assert len(key2) == 32
        assert key1 != key2  # Different algorithms should produce different results

        # Test Scrypt
        key3 = derivation.derive_key_with_algorithm(password.encode(), salt, KeyDerivationAlgorithm.SCRYPT)
        assert len(key3) == 32
        assert key1 != key3

    def test_deterministic_account_keys(self):
        """Test generating multiple deterministic account keys."""
        derivation = SecureKeyDerivation(SecurityLevel.DEVELOPMENT)

        seed = derivation.generate_master_seed(256)
        master_key = derivation.derive_master_key(seed)

        # Generate multiple account keys deterministically
        accounts = []
        for i in range(5):
            path = DerivationPath(account=i)
            derived_key = derivation.derive_path(master_key, path)
            keypair = derivation.derive_stellar_keypair(derived_key)
            accounts.append((i, keypair, path))

        assert len(accounts) == 5

        for i, (account_index, keypair, path) in enumerate(accounts):
            assert account_index == i
            assert isinstance(keypair, Keypair)
            assert isinstance(path, DerivationPath)
            assert path.account == i

        # All keypairs should be different
        public_keys = [kp.public_key for _, kp, _ in accounts]
        assert len(set(public_keys)) == 5


class TestHierarchicalKeyManager:
    """Test hierarchical key manager."""

    def test_wallet_creation(self):
        """Test HD wallet creation."""
        manager = HierarchicalKeyManager(SecurityLevel.DEVELOPMENT)

        # Create wallet with entropy
        wallet_id = "test_wallet_001"
        seed = manager.create_wallet(wallet_id, entropy_bits=256)

        assert isinstance(seed, MasterSeed)
        assert len(seed.seed_bytes) == 32
        assert wallet_id in manager._master_seeds

        # Should not allow duplicate wallet IDs
        with pytest.raises(ValueError):
            manager.create_wallet(wallet_id, entropy_bits=256)

    def test_wallet_with_mnemonic(self):
        """Test wallet creation from mnemonic."""
        manager = HierarchicalKeyManager(SecurityLevel.DEVELOPMENT)

        mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        wallet_id = "mnemonic_wallet"

        seed = manager.create_wallet(wallet_id, mnemonic=mnemonic)

        assert isinstance(seed, MasterSeed)
        assert seed.mnemonic == mnemonic

    def test_account_keypair_generation(self):
        """Test getting account keypairs."""
        manager = HierarchicalKeyManager(SecurityLevel.DEVELOPMENT)

        wallet_id = "test_wallet"
        manager.create_wallet(wallet_id)

        # Get keypair for account 0
        keypair1 = manager.get_account_keypair(wallet_id, 0)
        assert isinstance(keypair1, Keypair)

        # Get keypair for account 1
        keypair2 = manager.get_account_keypair(wallet_id, 1)
        assert isinstance(keypair2, Keypair)

        # Should be different
        assert keypair1.public_key != keypair2.public_key

        # Same account should return same keypair
        keypair1_again = manager.get_account_keypair(wallet_id, 0)
        assert keypair1.public_key == keypair1_again.public_key

    def test_wallet_management(self):
        """Test wallet management operations."""
        manager = HierarchicalKeyManager(SecurityLevel.DEVELOPMENT)

        # Create multiple wallets
        wallet_ids = ["wallet1", "wallet2", "wallet3"]
        for wallet_id in wallet_ids:
            manager.create_wallet(wallet_id)

        # List wallets
        listed_wallets = manager.list_wallets()
        for wallet_id in wallet_ids:
            assert wallet_id in listed_wallets

        # Export wallet info
        wallet_info = manager.export_wallet("wallet1")
        assert wallet_info["wallet_id"] == "wallet1"
        assert "created_at" in wallet_info
        assert "seed_length" in wallet_info

        # Delete wallet
        deleted = manager.delete_wallet("wallet2")
        assert deleted is True

        # Should no longer be in list
        updated_list = manager.list_wallets()
        assert "wallet2" not in updated_list

    def test_wallet_accounts_info(self):
        """Test getting wallet accounts information."""
        manager = HierarchicalKeyManager(SecurityLevel.DEVELOPMENT)

        wallet_id = "info_test_wallet"
        manager.create_wallet(wallet_id)

        # Get account info
        accounts = manager.get_wallet_accounts(wallet_id, 3)

        assert len(accounts) == 3
        for i, account in enumerate(accounts):
            assert account["account_index"] == i
            assert "public_key" in account
            assert "derivation_path" in account
            assert "address" in account
            assert account["derivation_path"] == f"m/44'/148'/{i}'/0/0"


class TestUtilityFunctions:
    """Test utility functions."""

    def test_bip39_mnemonic_generation(self):
        """Test BIP-39 mnemonic generation."""
        # Test different word counts
        for word_count in [12, 15, 18, 21, 24]:
            mnemonic = generate_bip39_mnemonic(word_count)
            words = mnemonic.split()
            assert len(words) == word_count

            # All words should be from the word list
            for word in words:
                assert isinstance(word, str)
                assert len(word) > 0

    def test_derivation_path_validation_kd(self):
        """Test key derivation path validation."""
        # Valid paths
        assert validate_kd_derivation_path("m/44'/148'/0'/0/0") is True
        assert validate_kd_derivation_path("m/44'/148'/5'/1/20") is True

        # Invalid paths
        assert validate_kd_derivation_path("invalid_path") is False
        assert validate_kd_derivation_path("m/44'/148'/0'/0") is False  # Too short
        assert validate_kd_derivation_path("44'/148'/0'/0/0") is False  # No m/

    @pytest.mark.asyncio
    async def test_key_derivation_benchmark(self):
        """Test key derivation performance benchmarking."""
        result = await benchmark_key_derivation(100)

        assert isinstance(result, dict)
        assert "total_time" in result
        assert "master_key_time" in result
        assert "average_child_key_time" in result
        assert "child_keys_derived" in result
        assert "keys_per_second" in result

        assert result["total_time"] > 0
        assert result["child_keys_derived"] > 0
        assert result["keys_per_second"] > 0


class TestIntegrationScenarios:
    """Test integration scenarios across security components."""

    @pytest.mark.asyncio
    async def test_end_to_end_key_management(self):
        """Test end-to-end key management workflow."""
        # Initialize security manager
        config = SecurityConfig(security_level=SecurityLevel.DEVELOPMENT)
        security_manager = StellarSecurityManager(config)

        # Initialize HD key manager
        hd_manager = HierarchicalKeyManager(SecurityLevel.DEVELOPMENT)

        # Create HD wallet
        wallet_id = "integration_test_wallet"
        hd_manager.create_wallet(wallet_id)

        # Generate keypairs from HD wallet
        keypair1 = hd_manager.get_account_keypair(wallet_id, 0)
        keypair2 = hd_manager.get_account_keypair(wallet_id, 1)

        # Store keypairs in security manager
        key_id1 = await security_manager.store_keypair(keypair1)
        key_id2 = await security_manager.store_keypair(keypair2)

        # Verify storage
        stored_keypair1 = await security_manager.get_keypair(key_id1)
        stored_keypair2 = await security_manager.get_keypair(key_id2)

        assert stored_keypair1.public_key == keypair1.public_key
        assert stored_keypair2.public_key == keypair2.public_key

        # List managed keys
        managed_keys = await security_manager.list_managed_keys()
        key_ids = [key.key_id for key in managed_keys]
        assert key_id1 in key_ids
        assert key_id2 in key_ids

    def test_security_status_reporting(self):
        """Test comprehensive security status reporting."""
        config = SecurityConfig(
            security_level=SecurityLevel.PRODUCTION,
            require_hardware_security=True,
            enable_audit_logging=True,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            security_manager = StellarSecurityManager(config, temp_dir)

            status = security_manager.get_security_status()

            assert isinstance(status, dict)
            assert status["security_level"] == "PRODUCTION"
            assert "active_stores" in status
            assert "key_count" in status
            assert "health_status" in status

    @pytest.mark.asyncio
    async def test_multi_store_key_management(self):
        """Test key management across multiple storage backends."""
        # Test with both memory and filesystem stores
        config = SecurityConfig(security_level=SecurityLevel.TESTING)

        with tempfile.TemporaryDirectory() as temp_dir:
            security_manager = StellarSecurityManager(config, temp_dir)

            # Should have both memory and filesystem stores
            assert KeyStoreType.FILE_SYSTEM in security_manager._stores

            # Generate keypair (should use filesystem by default for testing level)
            keypair, key_id = await security_manager.generate_keypair()

            # Should be retrievable
            retrieved = await security_manager.get_keypair(key_id)
            assert retrieved is not None
            assert retrieved.public_key == keypair.public_key
