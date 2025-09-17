"""
Stellar Key Storage Implementations
Secure storage backends for cryptographic keys including memory, filesystem, and HSM.
"""

import base64
import json
import os
import secrets
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from .stellar_logging import get_stellar_logger, LogCategory
from .stellar_security_types import KeyMetadata, KeyStoreType, SecurityLevel


class MemoryKeyStore:
    """In-memory key storage (development only)."""

    def __init__(self) -> None:
        self._keys: Dict[str, Tuple[bytes, KeyMetadata]] = {}
        self.logger = get_stellar_logger()

    async def store_key(self, key_id: str, key_data: bytes, metadata: KeyMetadata) -> bool:
        """Store a key in memory."""
        try:
            self._keys[key_id] = (key_data, metadata)
            self.logger.info(
                f"Key stored in memory: {key_id}",
                category=LogCategory.SECURITY,
                key_id=key_id,
                store_type=metadata.store_type.name,
            )
            return True
        except Exception as e:
            self.logger.error(
                f"Failed to store key in memory: {e}", category=LogCategory.SECURITY, exception=e
            )
            return False

    async def retrieve_key(self, key_id: str) -> Optional[Tuple[bytes, KeyMetadata]]:
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
                f"Key deleted from memory: {key_id}", category=LogCategory.SECURITY, key_id=key_id
            )
            return True
        return False

    async def list_keys(self) -> List[KeyMetadata]:
        """List all keys in memory."""
        return [metadata for _, metadata in self._keys.values()]


class FileSystemKeyStore:
    """File system key storage with encryption."""

    def __init__(self, base_path: str, master_key: Optional[bytes] = None) -> None:
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
            with open(key_path, "wb") as f:
                f.write(encrypted_data)
            os.chmod(key_path, 0o600)  # Owner read/write only

            # Write metadata file
            metadata_path = self._metadata_file_path(key_id)
            metadata_dict = {
                "key_id": metadata.key_id,
                "account_id": metadata.account_id,
                "key_type": metadata.key_type,
                "store_type": metadata.store_type.name,
                "created_at": metadata.created_at,
                "security_level": metadata.security_level.name,
                "encrypted": metadata.encrypted,
            }

            with open(metadata_path, "w") as f:
                json.dump(metadata_dict, f)
            os.chmod(metadata_path, 0o600)

            self.logger.info(
                f"Key stored to file system: {key_id}",
                category=LogCategory.SECURITY,
                key_id=key_id,
                path=key_path,
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to store key to file system: {e}",
                category=LogCategory.SECURITY,
                exception=e,
            )
            return False

    async def retrieve_key(self, key_id: str) -> Optional[Tuple[bytes, KeyMetadata]]:
        """Retrieve a key from file system."""
        try:
            key_path = self._key_file_path(key_id)
            metadata_path = self._metadata_file_path(key_id)

            if not os.path.exists(key_path) or not os.path.exists(metadata_path):
                return None

            # Read encrypted key data
            with open(key_path, "rb") as f:
                encrypted_data = f.read()
            key_data = self._decrypt_data(encrypted_data)

            # Read metadata
            with open(metadata_path, "r") as f:
                metadata_dict = json.load(f)

            metadata = KeyMetadata(
                key_id=metadata_dict["key_id"],
                account_id=metadata_dict["account_id"],
                key_type=metadata_dict["key_type"],
                store_type=KeyStoreType[metadata_dict["store_type"]],
                created_at=metadata_dict["created_at"],
                security_level=SecurityLevel[metadata_dict["security_level"]],
                encrypted=metadata_dict["encrypted"],
            )

            # Update usage tracking
            metadata.last_used = time.time()
            metadata.use_count += 1

            return key_data, metadata

        except Exception as e:
            self.logger.error(
                f"Failed to retrieve key from file system: {e}",
                category=LogCategory.SECURITY,
                exception=e,
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
                    key_id=key_id,
                )

            return deleted

        except Exception as e:
            self.logger.error(
                f"Failed to delete key from file system: {e}",
                category=LogCategory.SECURITY,
                exception=e,
            )
            return False

    async def list_keys(self) -> List[KeyMetadata]:
        """List all keys in file system."""
        keys = []
        try:
            for filename in os.listdir(self.base_path):
                if filename.endswith(".meta"):
                    key_id = filename[:-5]  # Remove .meta extension
                    result = await self.retrieve_key(key_id)
                    if result:
                        _, metadata = result
                        keys.append(metadata)
        except Exception as e:
            self.logger.error(
                f"Failed to list keys from file system: {e}",
                category=LogCategory.SECURITY,
                exception=e,
            )

        return keys


class HSMKeyStore:
    """Hardware Security Module key storage (placeholder for future implementation)."""

    def __init__(self, hsm_config: Dict[str, Any]) -> None:
        self.hsm_config = hsm_config
        self.logger = get_stellar_logger()
        self.logger.warning("HSM integration is not yet implemented", category=LogCategory.SECURITY)

    async def store_key(self, key_id: str, key_data: bytes, metadata: KeyMetadata) -> bool:
        """Store a key in HSM (placeholder implementation)."""
        self.logger.warning(
            f"HSM store_key called for {key_id} - using placeholder",
            category=LogCategory.SECURITY,
            key_id=key_id,
        )
        # Placeholder: Return False to indicate HSM unavailable
        return False

    async def retrieve_key(self, key_id: str) -> Optional[Tuple[bytes, KeyMetadata]]:
        """Retrieve a key from HSM (placeholder implementation)."""
        self.logger.warning(
            f"HSM retrieve_key called for {key_id} - using placeholder",
            category=LogCategory.SECURITY,
            key_id=key_id,
        )
        # Placeholder: Return None to indicate key not found in HSM
        return None

    async def delete_key(self, key_id: str) -> bool:
        """Delete a key from HSM (placeholder implementation)."""
        self.logger.warning(
            f"HSM delete_key called for {key_id} - using placeholder",
            category=LogCategory.SECURITY,
            key_id=key_id,
        )
        # Placeholder: Return False to indicate deletion not performed
        return False

    async def list_keys(self) -> List[KeyMetadata]:
        """List all keys in HSM (placeholder implementation)."""
        self.logger.warning(
            "HSM list_keys called - using placeholder", category=LogCategory.SECURITY
        )
        # Placeholder: Return empty list since no HSM is configured
        return []
