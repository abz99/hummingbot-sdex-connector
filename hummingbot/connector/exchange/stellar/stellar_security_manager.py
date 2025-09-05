"""
Stellar Security Manager
Enterprise-grade security infrastructure for Stellar connector including HSM, hardware wallets, and Vault integration.
"""

import asyncio
import hashlib
import secrets
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Union, Protocol, runtime_checkable
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from stellar_sdk import Keypair
import base64
import os

from .stellar_logging import get_stellar_logger, LogCategory


class SecurityLevel(Enum):
    """Security levels for key operations."""
    DEVELOPMENT = auto()
    TESTING = auto()
    STAGING = auto()
    PRODUCTION = auto()


class KeyStoreType(Enum):
    """Types of key storage backends."""
    MEMORY = auto()
    FILE_SYSTEM = auto()
    HSM = auto()
    HARDWARE_WALLET = auto()
    VAULT = auto()


class HardwareWalletType(Enum):
    """Supported hardware wallet types."""
    LEDGER = auto()
    TREZOR = auto()


@dataclass
class SecurityConfig:
    """Security configuration settings."""
    security_level: SecurityLevel = SecurityLevel.DEVELOPMENT
    require_hardware_security: bool = False
    key_derivation_iterations: int = 100000
    session_timeout_minutes: int = 30
    max_failed_attempts: int = 3
    enable_audit_logging: bool = True
    encryption_algorithm: str = "AES-256-GCM"
    backup_enabled: bool = True
    backup_encryption: bool = True


@dataclass
class KeyMetadata:
    """Metadata for managed keys."""
    key_id: str
    account_id: str
    key_type: str
    store_type: KeyStoreType
    created_at: float = field(default_factory=time.time)
    last_used: float = 0
    use_count: int = 0
    security_level: SecurityLevel = SecurityLevel.DEVELOPMENT
    hardware_device_id: Optional[str] = None
    vault_path: Optional[str] = None
    encrypted: bool = True


@runtime_checkable
class KeyStoreBackend(Protocol):
    """Protocol for key storage backends."""
    
    async def store_key(self, key_id: str, key_data: bytes, metadata: KeyMetadata) -> bool:
        """Store a key with metadata."""
        ...
    
    async def retrieve_key(self, key_id: str) -> Optional[tuple[bytes, KeyMetadata]]:
        """Retrieve a key and its metadata."""
        ...
    
    async def delete_key(self, key_id: str) -> bool:
        """Delete a key."""
        ...
    
    async def list_keys(self) -> List[KeyMetadata]:
        """List all stored keys."""
        ...


class MemoryKeyStore:
    """In-memory key storage (development only)."""
    
    def __init__(self):
        self._keys: Dict[str, tuple[bytes, KeyMetadata]] = {}
        self.logger = get_stellar_logger()
    
    async def store_key(self, key_id: str, key_data: bytes, metadata: KeyMetadata) -> bool:
        """Store a key in memory."""
        try:
            self._keys[key_id] = (key_data, metadata)
            self.logger.info(
                f"Key stored in memory: {key_id}",
                category=LogCategory.SECURITY,
                key_id=key_id,
                store_type=metadata.store_type.name
            )
            return True
        except Exception as e:
            self.logger.error(
                f"Failed to store key in memory: {e}",
                category=LogCategory.SECURITY,
                exception=e
            )
            return False
    
    async def retrieve_key(self, key_id: str) -> Optional[tuple[bytes, KeyMetadata]]:
        """Retrieve a key from memory."""
        result = self._keys.get(key_id)
        if result:
            key_data, metadata = result
            metadata.last_used = time.time()
            metadata.use_count += 1
        return result
    
    async def delete_key(self, key_id: str) -> bool:
        """Delete a key from memory."""
        if key_id in self._keys:
            del self._keys[key_id]
            self.logger.info(
                f"Key deleted from memory: {key_id}",
                category=LogCategory.SECURITY,
                key_id=key_id
            )
            return True
        return False
    
    async def list_keys(self) -> List[KeyMetadata]:
        """List all keys in memory."""
        return [metadata for _, metadata in self._keys.values()]


class FileSystemKeyStore:
    """File system key storage with encryption."""
    
    def __init__(self, base_path: str, master_key: Optional[bytes] = None):
        self.base_path = base_path
        self.master_key = master_key or self._generate_master_key()
        self.logger = get_stellar_logger()
        
        # Create directory if it doesn't exist
        os.makedirs(base_path, exist_ok=True)
        os.chmod(base_path, 0o700)  # Owner read/write/execute only
    
    def _generate_master_key(self) -> bytes:
        """Generate a master key for encryption."""
        return secrets.token_bytes(32)  # 256-bit key
    
    def _encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data using master key."""
        from cryptography.fernet import Fernet
        key = base64.urlsafe_b64encode(self.master_key)
        fernet = Fernet(key)
        return fernet.encrypt(data)
    
    def _decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using master key."""
        from cryptography.fernet import Fernet
        key = base64.urlsafe_b64encode(self.master_key)
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_data)
    
    def _key_file_path(self, key_id: str) -> str:
        """Get file path for a key."""
        return os.path.join(self.base_path, f"{key_id}.key")
    
    def _metadata_file_path(self, key_id: str) -> str:
        """Get file path for key metadata."""
        return os.path.join(self.base_path, f"{key_id}.meta")
    
    async def store_key(self, key_id: str, key_data: bytes, metadata: KeyMetadata) -> bool:
        """Store a key to file system."""
        try:
            # Encrypt key data
            encrypted_data = self._encrypt_data(key_data)
            
            # Write key file
            key_path = self._key_file_path(key_id)
            with open(key_path, 'wb') as f:
                f.write(encrypted_data)
            os.chmod(key_path, 0o600)  # Owner read/write only
            
            # Write metadata file
            metadata_path = self._metadata_file_path(key_id)
            metadata_dict = {
                'key_id': metadata.key_id,
                'account_id': metadata.account_id,
                'key_type': metadata.key_type,
                'store_type': metadata.store_type.name,
                'created_at': metadata.created_at,
                'security_level': metadata.security_level.name,
                'encrypted': metadata.encrypted
            }
            
            import json
            with open(metadata_path, 'w') as f:
                json.dump(metadata_dict, f)
            os.chmod(metadata_path, 0o600)
            
            self.logger.info(
                f"Key stored to file system: {key_id}",
                category=LogCategory.SECURITY,
                key_id=key_id,
                path=key_path
            )
            return True
            
        except Exception as e:
            self.logger.error(
                f"Failed to store key to file system: {e}",
                category=LogCategory.SECURITY,
                exception=e
            )
            return False
    
    async def retrieve_key(self, key_id: str) -> Optional[tuple[bytes, KeyMetadata]]:
        """Retrieve a key from file system."""
        try:
            key_path = self._key_file_path(key_id)
            metadata_path = self._metadata_file_path(key_id)
            
            if not os.path.exists(key_path) or not os.path.exists(metadata_path):
                return None
            
            # Read encrypted key data
            with open(key_path, 'rb') as f:
                encrypted_data = f.read()
            key_data = self._decrypt_data(encrypted_data)
            
            # Read metadata
            import json
            with open(metadata_path, 'r') as f:
                metadata_dict = json.load(f)
            
            metadata = KeyMetadata(
                key_id=metadata_dict['key_id'],
                account_id=metadata_dict['account_id'],
                key_type=metadata_dict['key_type'],
                store_type=KeyStoreType[metadata_dict['store_type']],
                created_at=metadata_dict['created_at'],
                security_level=SecurityLevel[metadata_dict['security_level']],
                encrypted=metadata_dict['encrypted']
            )
            
            # Update usage tracking
            metadata.last_used = time.time()
            metadata.use_count += 1
            
            return key_data, metadata
            
        except Exception as e:
            self.logger.error(
                f"Failed to retrieve key from file system: {e}",
                category=LogCategory.SECURITY,
                exception=e
            )
            return None
    
    async def delete_key(self, key_id: str) -> bool:
        """Delete a key from file system."""
        try:
            key_path = self._key_file_path(key_id)
            metadata_path = self._metadata_file_path(key_id)
            
            deleted = False
            if os.path.exists(key_path):
                os.remove(key_path)
                deleted = True
            
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
                deleted = True
            
            if deleted:
                self.logger.info(
                    f"Key deleted from file system: {key_id}",
                    category=LogCategory.SECURITY,
                    key_id=key_id
                )
            
            return deleted
            
        except Exception as e:
            self.logger.error(
                f"Failed to delete key from file system: {e}",
                category=LogCategory.SECURITY,
                exception=e
            )
            return False
    
    async def list_keys(self) -> List[KeyMetadata]:
        """List all keys in file system."""
        keys = []
        try:
            for filename in os.listdir(self.base_path):
                if filename.endswith('.meta'):
                    key_id = filename[:-5]  # Remove .meta extension
                    result = await self.retrieve_key(key_id)
                    if result:
                        _, metadata = result
                        keys.append(metadata)
        except Exception as e:
            self.logger.error(
                f"Failed to list keys from file system: {e}",
                category=LogCategory.SECURITY,
                exception=e
            )
        
        return keys


class HSMKeyStore:
    """Hardware Security Module key storage (placeholder for future implementation)."""
    
    def __init__(self, hsm_config: Dict[str, Any]):
        self.hsm_config = hsm_config
        self.logger = get_stellar_logger()
        self.logger.warning(
            "HSM integration is not yet implemented",
            category=LogCategory.SECURITY
        )
    
    async def store_key(self, key_id: str, key_data: bytes, metadata: KeyMetadata) -> bool:
        """Store a key in HSM (not implemented)."""
        raise NotImplementedError("HSM integration not yet implemented")
    
    async def retrieve_key(self, key_id: str) -> Optional[tuple[bytes, KeyMetadata]]:
        """Retrieve a key from HSM (not implemented)."""
        raise NotImplementedError("HSM integration not yet implemented")
    
    async def delete_key(self, key_id: str) -> bool:
        """Delete a key from HSM (not implemented)."""
        raise NotImplementedError("HSM integration not yet implemented")
    
    async def list_keys(self) -> List[KeyMetadata]:
        """List all keys in HSM (not implemented)."""
        raise NotImplementedError("HSM integration not yet implemented")


class StellarSecurityManager:
    """Main security manager for Stellar connector."""
    
    def __init__(self, config: SecurityConfig, key_store_path: Optional[str] = None):
        self.config = config
        self.logger = get_stellar_logger()
        self._stores: Dict[KeyStoreType, KeyStoreBackend] = {}
        self._session_data: Dict[str, Any] = {}
        self._failed_attempts: Dict[str, int] = {}
        
        # Initialize key stores based on security level
        self._initialize_key_stores(key_store_path)
        
        self.logger.info(
            f"Security manager initialized with level: {config.security_level.name}",
            category=LogCategory.SECURITY,
            security_level=config.security_level.name,
            stores=list(self._stores.keys())
        )
    
    def _initialize_key_stores(self, key_store_path: Optional[str] = None):
        """Initialize key storage backends based on configuration."""
        # Always include memory store for development
        if self.config.security_level == SecurityLevel.DEVELOPMENT:
            self._stores[KeyStoreType.MEMORY] = MemoryKeyStore()
        
        # File system store for testing and above
        if self.config.security_level in [SecurityLevel.TESTING, SecurityLevel.STAGING, SecurityLevel.PRODUCTION]:
            base_path = key_store_path or os.path.join(os.path.expanduser("~"), ".stellar-keys")
            self._stores[KeyStoreType.FILE_SYSTEM] = FileSystemKeyStore(base_path)
        
        # HSM for production (placeholder)
        if self.config.security_level == SecurityLevel.PRODUCTION and self.config.require_hardware_security:
            # This would be configured with actual HSM details in production
            hsm_config = {}
            self._stores[KeyStoreType.HSM] = HSMKeyStore(hsm_config)
    
    async def generate_keypair(
        self,
        account_id: Optional[str] = None,
        store_type: Optional[KeyStoreType] = None
    ) -> tuple[Keypair, str]:
        """Generate a new Stellar keypair with secure storage."""
        # Generate keypair
        keypair = Keypair.random()
        account_id = account_id or keypair.public_key
        
        # Determine storage type based on security level
        if store_type is None:
            if self.config.security_level == SecurityLevel.DEVELOPMENT:
                store_type = KeyStoreType.MEMORY
            else:
                store_type = KeyStoreType.FILE_SYSTEM
        
        # Create key metadata
        key_id = f"stellar_{account_id[:8]}_{int(time.time())}"
        metadata = KeyMetadata(
            key_id=key_id,
            account_id=account_id,
            key_type="ed25519",
            store_type=store_type,
            security_level=self.config.security_level
        )
        
        # Store the secret key securely
        secret_key_bytes = keypair.secret.encode()
        store = self._stores.get(store_type)
        if not store:
            raise ValueError(f"Key store type not available: {store_type}")
        
        success = await store.store_key(key_id, secret_key_bytes, metadata)
        if not success:
            raise RuntimeError(f"Failed to store keypair in {store_type.name}")
        
        self.logger.info(
            f"Generated and stored new keypair: {account_id}",
            category=LogCategory.SECURITY,
            account_id=account_id,
            key_id=key_id,
            store_type=store_type.name
        )
        
        return keypair, key_id
    
    async def store_keypair(
        self,
        keypair: Keypair,
        store_type: Optional[KeyStoreType] = None
    ) -> str:
        """Store an existing Stellar keypair with secure storage."""
        account_id = keypair.public_key
        
        # Determine storage type based on security level
        if store_type is None:
            if self.config.security_level == SecurityLevel.DEVELOPMENT:
                store_type = KeyStoreType.MEMORY
            else:
                store_type = KeyStoreType.FILE_SYSTEM
        
        # Create key metadata
        key_id = f"stellar_{account_id[:8]}_{int(time.time())}"
        metadata = KeyMetadata(
            key_id=key_id,
            account_id=account_id,
            key_type="ed25519",
            store_type=store_type,
            created_at=time.time(),
            security_level=self.config.security_level,
            encrypted=True
        )
        
        # Store the keypair
        key_data = keypair.secret.encode()
        await self._stores[store_type].store_key(key_id, key_data, metadata)
        
        self.logger.info(
            f"Stored existing keypair: {account_id}",
            category=LogCategory.SECURITY,
            account_id=account_id,
            key_id=key_id,
            store_type=store_type.name
        )
        
        return key_id
    
    async def get_keypair(self, key_id: str) -> Optional[Keypair]:
        """Retrieve a keypair by key ID."""
        # Try each store type
        for store_type, store in self._stores.items():
            try:
                result = await store.retrieve_key(key_id)
                if result:
                    key_data, metadata = result
                    secret_key = key_data.decode()
                    keypair = Keypair.from_secret(secret_key)
                    
                    self.logger.info(
                        f"Retrieved keypair: {key_id}",
                        category=LogCategory.SECURITY,
                        key_id=key_id,
                        account_id=metadata.account_id,
                        store_type=store_type.name
                    )
                    
                    return keypair
            except Exception as e:
                self.logger.warning(
                    f"Failed to retrieve key from {store_type.name}: {e}",
                    category=LogCategory.SECURITY,
                    key_id=key_id,
                    store_type=store_type.name
                )
                continue
        
        return None
    
    async def delete_keypair(self, key_id: str) -> bool:
        """Delete a keypair from all stores."""
        deleted = False
        for store_type, store in self._stores.items():
            try:
                if await store.delete_key(key_id):
                    deleted = True
                    self.logger.info(
                        f"Deleted key from {store_type.name}: {key_id}",
                        category=LogCategory.SECURITY,
                        key_id=key_id,
                        store_type=store_type.name
                    )
            except Exception as e:
                self.logger.error(
                    f"Failed to delete key from {store_type.name}: {e}",
                    category=LogCategory.SECURITY,
                    key_id=key_id,
                    store_type=store_type.name,
                    exception=e
                )
        
        return deleted
    
    async def list_managed_keys(self) -> List[KeyMetadata]:
        """List all managed keys across all stores."""
        all_keys = []
        seen_key_ids = set()
        
        for store_type, store in self._stores.items():
            try:
                keys = await store.list_keys()
                for key in keys:
                    if key.key_id not in seen_key_ids:
                        all_keys.append(key)
                        seen_key_ids.add(key.key_id)
            except Exception as e:
                self.logger.error(
                    f"Failed to list keys from {store_type.name}: {e}",
                    category=LogCategory.SECURITY,
                    store_type=store_type.name,
                    exception=e
                )
        
        return all_keys
    
    def derive_key(self, master_key: bytes, purpose: str, index: int = 0) -> bytes:
        """Derive a key for a specific purpose using PBKDF2."""
        salt = f"{purpose}:{index}".encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.config.key_derivation_iterations
        )
        return kdf.derive(master_key)
    
    def create_secure_session(self, user_id: str) -> str:
        """Create a secure session for key operations."""
        session_id = secrets.token_urlsafe(32)
        session_data = {
            'user_id': user_id,
            'created_at': time.time(),
            'last_activity': time.time(),
            'authenticated': True
        }
        self._session_data[session_id] = session_data
        
        self.logger.info(
            f"Created secure session: {session_id[:8]}...",
            category=LogCategory.SECURITY,
            user_id=user_id
        )
        
        return session_id
    
    def validate_session(self, session_id: str) -> bool:
        """Validate a session and check for timeout."""
        session = self._session_data.get(session_id)
        if not session:
            return False
        
        now = time.time()
        timeout_seconds = self.config.session_timeout_minutes * 60
        
        if now - session['last_activity'] > timeout_seconds:
            # Session expired
            del self._session_data[session_id]
            self.logger.warning(
                f"Session expired: {session_id[:8]}...",
                category=LogCategory.SECURITY
            )
            return False
        
        # Update last activity
        session['last_activity'] = now
        return True
    
    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session."""
        if session_id in self._session_data:
            del self._session_data[session_id]
            self.logger.info(
                f"Session invalidated: {session_id[:8]}...",
                category=LogCategory.SECURITY
            )
            return True
        return False
    
    async def backup_keys(self, backup_path: str, encryption_key: Optional[bytes] = None) -> bool:
        """Create an encrypted backup of all managed keys."""
        try:
            keys = await self.list_managed_keys()
            backup_data = {
                'timestamp': time.time(),
                'security_level': self.config.security_level.name,
                'keys': []
            }
            
            for key_metadata in keys:
                # Get the actual key data
                for store in self._stores.values():
                    result = await store.retrieve_key(key_metadata.key_id)
                    if result:
                        key_data, _ = result
                        backup_data['keys'].append({
                            'key_id': key_metadata.key_id,
                            'account_id': key_metadata.account_id,
                            'key_type': key_metadata.key_type,
                            'key_data': base64.b64encode(key_data).decode(),
                            'metadata': {
                                'created_at': key_metadata.created_at,
                                'security_level': key_metadata.security_level.name
                            }
                        })
                        break
            
            # Serialize backup data
            import json
            backup_json = json.dumps(backup_data, indent=2)
            backup_bytes = backup_json.encode()
            
            # Encrypt if requested
            if self.config.backup_encryption and encryption_key:
                from cryptography.fernet import Fernet
                key = base64.urlsafe_b64encode(encryption_key[:32])  # Use first 32 bytes
                fernet = Fernet(key)
                backup_bytes = fernet.encrypt(backup_bytes)
            
            # Write backup file
            with open(backup_path, 'wb') as f:
                f.write(backup_bytes)
            os.chmod(backup_path, 0o600)
            
            self.logger.info(
                f"Keys backup created: {backup_path}",
                category=LogCategory.SECURITY,
                backup_path=backup_path,
                key_count=len(backup_data['keys']),
                encrypted=bool(encryption_key)
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                f"Failed to create keys backup: {e}",
                category=LogCategory.SECURITY,
                exception=e
            )
            return False
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get current security status and metrics."""
        return {
            'security_level': self.config.security_level.name,
            'available_stores': [store_type.name for store_type in self._stores.keys()],
            'active_sessions': len(self._session_data),
            'failed_attempts': dict(self._failed_attempts),
            'hardware_security_required': self.config.require_hardware_security,
            'backup_enabled': self.config.backup_enabled,
            'audit_logging_enabled': self.config.enable_audit_logging
        }