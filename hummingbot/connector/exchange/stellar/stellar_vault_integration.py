"""
HashiCorp Vault Integration for Stellar Connector
Secure key management and secrets storage using HashiCorp Vault.
"""

import asyncio
import base64
import json
import time
from dataclasses import dataclass, field
from enum import auto, Enum
from typing import Any, Dict, List, Optional, Union

import aiohttp
from stellar_sdk import Keypair

from .stellar_logging import get_stellar_logger, LogCategory
from .stellar_security_manager import KeyMetadata, KeyStoreBackend, KeyStoreType, SecurityLevel


class VaultAuthMethod(Enum):
    """Vault authentication methods."""

    TOKEN = auto()
    USERPASS = auto()
    APPROLE = auto()
    KUBERNETES = auto()
    AWS = auto()
    AZURE = auto()


class VaultEngine(Enum):
    """Vault secret engines."""

    KV_V1 = "kv"
    KV_V2 = "kv-v2"
    TRANSIT = "transit"
    PKI = "pki"


@dataclass
class VaultConfig:
    """Vault configuration settings."""

    url: str
    auth_method: VaultAuthMethod
    mount_path: str = "stellar"
    engine_type: VaultEngine = VaultEngine.KV_V2
    token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    role_id: Optional[str] = None
    secret_id: Optional[str] = None
    namespace: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    verify_ssl: bool = True


@dataclass
class VaultToken:
    """Vault authentication token information."""

    token: str
    expires_at: float
    renewable: bool = False
    policies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class VaultKeyStore(KeyStoreBackend):
    """HashiCorp Vault key storage backend."""

    def __init__(self, config: VaultConfig):
        self.config = config
        self.logger = get_stellar_logger()
        self._session: Optional[aiohttp.ClientSession] = None
        self._token: Optional[VaultToken] = None
        self._authenticated = False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()

    async def initialize(self):
        """Initialize Vault connection."""
        connector = aiohttp.TCPConnector(verify_ssl=self.config.verify_ssl)
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout), connector=connector
        )

        # Authenticate
        await self._authenticate()

        self.logger.info(
            "Vault key store initialized",
            category=LogCategory.SECURITY,
            vault_url=self.config.url,
            mount_path=self.config.mount_path,
            auth_method=self.config.auth_method.name,
        )

    async def cleanup(self):
        """Cleanup Vault connection."""
        if self._session:
            await self._session.close()
            self._session = None

        self.logger.info("Vault key store cleaned up", category=LogCategory.SECURITY)

    async def _authenticate(self) -> bool:
        """Authenticate with Vault using configured method."""
        try:
            if self.config.auth_method == VaultAuthMethod.TOKEN:
                return await self._auth_token()
            elif self.config.auth_method == VaultAuthMethod.USERPASS:
                return await self._auth_userpass()
            elif self.config.auth_method == VaultAuthMethod.APPROLE:
                return await self._auth_approle()
            else:
                raise NotImplementedError(f"Auth method not implemented: {self.config.auth_method}")

        except Exception as e:
            self.logger.error(
                f"Vault authentication failed: {e}",
                category=LogCategory.SECURITY,
                auth_method=self.config.auth_method.name,
                exception=e,
            )
            return False

    async def _auth_token(self) -> bool:
        """Authenticate using direct token."""
        if not self.config.token:
            raise ValueError("Token required for TOKEN auth method")

        # Verify token
        headers = {"X-Vault-Token": self.config.token}
        if self.config.namespace:
            headers["X-Vault-Namespace"] = self.config.namespace

        async with self._session.get(
            f"{self.config.url}/v1/auth/token/lookup-self", headers=headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                token_data = data.get("data", {})

                # Calculate expiration
                ttl = token_data.get("ttl", 0)
                expires_at = time.time() + ttl if ttl > 0 else float("inf")

                self._token = VaultToken(
                    token=self.config.token,
                    expires_at=expires_at,
                    renewable=token_data.get("renewable", False),
                    policies=token_data.get("policies", []),
                )

                self._authenticated = True

                self.logger.info(
                    "Vault token authentication successful",
                    category=LogCategory.SECURITY,
                    policies=self._token.policies,
                    renewable=self._token.renewable,
                )

                return True
            else:
                error_text = await response.text()
                raise Exception(f"Token verification failed: {response.status} - {error_text}")

    async def _auth_userpass(self) -> bool:
        """Authenticate using username/password."""
        if not self.config.username or not self.config.password:
            raise ValueError("Username and password required for USERPASS auth method")

        auth_data = {"password": self.config.password}

        headers = {}
        if self.config.namespace:
            headers["X-Vault-Namespace"] = self.config.namespace

        async with self._session.post(
            f"{self.config.url}/v1/auth/userpass/login/{self.config.username}",
            json=auth_data,
            headers=headers,
        ) as response:
            if response.status == 200:
                data = await response.json()
                auth_info = data.get("auth", {})

                token = auth_info.get("client_token")
                if not token:
                    raise Exception("No token received from userpass auth")

                lease_duration = auth_info.get("lease_duration", 0)
                expires_at = time.time() + lease_duration if lease_duration > 0 else float("inf")

                self._token = VaultToken(
                    token=token,
                    expires_at=expires_at,
                    renewable=auth_info.get("renewable", False),
                    policies=auth_info.get("policies", []),
                    metadata=auth_info.get("metadata", {}),
                )

                self._authenticated = True

                self.logger.info(
                    "Vault userpass authentication successful",
                    category=LogCategory.SECURITY,
                    username=self.config.username,
                    policies=self._token.policies,
                )

                return True
            else:
                error_text = await response.text()
                raise Exception(f"Userpass authentication failed: {response.status} - {error_text}")

    async def _auth_approle(self) -> bool:
        """Authenticate using AppRole."""
        if not self.config.role_id or not self.config.secret_id:
            raise ValueError("Role ID and Secret ID required for APPROLE auth method")

        auth_data = {"role_id": self.config.role_id, "secret_id": self.config.secret_id}

        headers = {}
        if self.config.namespace:
            headers["X-Vault-Namespace"] = self.config.namespace

        async with self._session.post(
            f"{self.config.url}/v1/auth/approle/login", json=auth_data, headers=headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                auth_info = data.get("auth", {})

                token = auth_info.get("client_token")
                if not token:
                    raise Exception("No token received from approle auth")

                lease_duration = auth_info.get("lease_duration", 0)
                expires_at = time.time() + lease_duration if lease_duration > 0 else float("inf")

                self._token = VaultToken(
                    token=token,
                    expires_at=expires_at,
                    renewable=auth_info.get("renewable", False),
                    policies=auth_info.get("policies", []),
                    metadata=auth_info.get("metadata", {}),
                )

                self._authenticated = True

                self.logger.info(
                    "Vault AppRole authentication successful",
                    category=LogCategory.SECURITY,
                    role_id=self.config.role_id[:8] + "...",
                    policies=self._token.policies,
                )

                return True
            else:
                error_text = await response.text()
                raise Exception(f"AppRole authentication failed: {response.status} - {error_text}")

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Vault requests."""
        if not self._token:
            raise Exception("Not authenticated with Vault")

        headers = {"X-Vault-Token": self._token.token}
        if self.config.namespace:
            headers["X-Vault-Namespace"] = self.config.namespace

        return headers

    def _get_secret_path(self, key_id: str) -> str:
        """Get the full path for a secret in Vault."""
        if self.config.engine_type == VaultEngine.KV_V2:
            return f"{self.config.mount_path}/data/{key_id}"
        else:
            return f"{self.config.mount_path}/{key_id}"

    async def store_key(self, key_id: str, key_data: bytes, metadata: KeyMetadata) -> bool:
        """Store a key in Vault."""
        if not self._authenticated:
            raise Exception("Not authenticated with Vault")

        try:
            # Encode key data as base64
            encoded_key = base64.b64encode(key_data).decode()

            # Prepare secret data
            secret_data = {
                "key_data": encoded_key,
                "metadata": {
                    "key_id": metadata.key_id,
                    "account_id": metadata.account_id,
                    "key_type": metadata.key_type,
                    "store_type": metadata.store_type.name,
                    "created_at": metadata.created_at,
                    "security_level": metadata.security_level.name,
                    "encrypted": metadata.encrypted,
                },
            }

            # For KV v2, wrap in 'data' field
            if self.config.engine_type == VaultEngine.KV_V2:
                secret_data = {"data": secret_data}

            path = self._get_secret_path(key_id)
            headers = self._get_headers()

            async with self._session.post(
                f"{self.config.url}/v1/{path}", json=secret_data, headers=headers
            ) as response:
                if response.status in [200, 204]:
                    self.logger.info(
                        f"Key stored in Vault: {key_id}",
                        category=LogCategory.SECURITY,
                        key_id=key_id,
                        path=path,
                    )
                    return True
                else:
                    error_text = await response.text()
                    raise Exception(
                        f"Failed to store key in Vault: {response.status} - {error_text}"
                    )

        except Exception as e:
            self.logger.error(
                f"Failed to store key in Vault: {e}",
                category=LogCategory.SECURITY,
                key_id=key_id,
                exception=e,
            )
            return False

    async def retrieve_key(self, key_id: str) -> Optional[tuple[bytes, KeyMetadata]]:
        """Retrieve a key from Vault."""
        if not self._authenticated:
            raise Exception("Not authenticated with Vault")

        try:
            path = self._get_secret_path(key_id)
            headers = self._get_headers()

            async with self._session.get(
                f"{self.config.url}/v1/{path}", headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    # Extract secret data (handle KV v1 vs v2)
                    if self.config.engine_type == VaultEngine.KV_V2:
                        secret_data = data.get("data", {}).get("data", {})
                    else:
                        secret_data = data.get("data", {})

                    # Decode key data
                    encoded_key = secret_data.get("key_data")
                    if not encoded_key:
                        raise Exception("No key_data found in Vault secret")

                    key_data = base64.b64decode(encoded_key)

                    # Reconstruct metadata
                    meta_dict = secret_data.get("metadata", {})
                    metadata = KeyMetadata(
                        key_id=meta_dict.get("key_id", key_id),
                        account_id=meta_dict.get("account_id", ""),
                        key_type=meta_dict.get("key_type", "unknown"),
                        store_type=getattr(KeyStoreType, meta_dict.get("store_type", "VAULT")),
                        created_at=meta_dict.get("created_at", time.time()),
                        security_level=getattr(
                            SecurityLevel, meta_dict.get("security_level", "PRODUCTION")
                        ),
                        encrypted=meta_dict.get("encrypted", True),
                        vault_path=path,
                    )

                    # Update usage tracking
                    metadata.last_used = time.time()
                    metadata.use_count += 1

                    self.logger.info(
                        f"Key retrieved from Vault: {key_id}",
                        category=LogCategory.SECURITY,
                        key_id=key_id,
                        path=path,
                    )

                    return key_data, metadata

                elif response.status == 404:
                    return None
                else:
                    error_text = await response.text()
                    raise Exception(
                        f"Failed to retrieve key from Vault: {response.status} - {error_text}"
                    )

        except Exception as e:
            self.logger.error(
                f"Failed to retrieve key from Vault: {e}",
                category=LogCategory.SECURITY,
                key_id=key_id,
                exception=e,
            )
            return None

    async def delete_key(self, key_id: str) -> bool:
        """Delete a key from Vault."""
        if not self._authenticated:
            raise Exception("Not authenticated with Vault")

        try:
            path = self._get_secret_path(key_id)
            headers = self._get_headers()

            # For KV v2, we need to use the metadata endpoint to permanently delete
            if self.config.engine_type == VaultEngine.KV_V2:
                metadata_path = f"{self.config.mount_path}/metadata/{key_id}"
                async with self._session.delete(
                    f"{self.config.url}/v1/{metadata_path}", headers=headers
                ) as response:
                    success = response.status in [200, 204]
            else:
                async with self._session.delete(
                    f"{self.config.url}/v1/{path}", headers=headers
                ) as response:
                    success = response.status in [200, 204]

            if success:
                self.logger.info(
                    f"Key deleted from Vault: {key_id}",
                    category=LogCategory.SECURITY,
                    key_id=key_id,
                    path=path,
                )
                return True
            else:
                error_text = await response.text()
                raise Exception(
                    f"Failed to delete key from Vault: {response.status} - {error_text}"
                )

        except Exception as e:
            self.logger.error(
                f"Failed to delete key from Vault: {e}",
                category=LogCategory.SECURITY,
                key_id=key_id,
                exception=e,
            )
            return False

    async def list_keys(self) -> List[KeyMetadata]:
        """List all keys in Vault."""
        if not self._authenticated:
            raise Exception("Not authenticated with Vault")

        try:
            # For KV v2, use metadata endpoint
            if self.config.engine_type == VaultEngine.KV_V2:
                list_path = f"{self.config.mount_path}/metadata"
            else:
                list_path = self.config.mount_path

            headers = self._get_headers()

            async with self._session.request(
                "LIST", f"{self.config.url}/v1/{list_path}", headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    key_names = data.get("data", {}).get("keys", [])

                    keys = []
                    for key_name in key_names:
                        # Remove trailing slash if present
                        key_name = key_name.rstrip("/")

                        # Try to retrieve metadata for each key
                        result = await self.retrieve_key(key_name)
                        if result:
                            _, metadata = result
                            keys.append(metadata)

                    return keys

                elif response.status == 404:
                    return []
                else:
                    error_text = await response.text()
                    raise Exception(
                        f"Failed to list keys in Vault: {response.status} - {error_text}"
                    )

        except Exception as e:
            self.logger.error(
                f"Failed to list keys in Vault: {e}", category=LogCategory.SECURITY, exception=e
            )
            return []

    async def renew_token(self) -> bool:
        """Renew the Vault token if possible."""
        if not self._token or not self._token.renewable:
            return False

        try:
            headers = self._get_headers()

            async with self._session.post(
                f"{self.config.url}/v1/auth/token/renew-self", headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    auth_info = data.get("auth", {})

                    lease_duration = auth_info.get("lease_duration", 0)
                    self._token.expires_at = (
                        time.time() + lease_duration if lease_duration > 0 else float("inf")
                    )

                    self.logger.info(
                        "Vault token renewed successfully",
                        category=LogCategory.SECURITY,
                        new_expiry=self._token.expires_at,
                    )

                    return True
                else:
                    error_text = await response.text()
                    self.logger.error(
                        f"Failed to renew Vault token: {response.status} - {error_text}",
                        category=LogCategory.SECURITY,
                    )
                    return False

        except Exception as e:
            self.logger.error(
                f"Failed to renew Vault token: {e}", category=LogCategory.SECURITY, exception=e
            )
            return False

    def is_token_expired(self) -> bool:
        """Check if the current token is expired."""
        if not self._token:
            return True

        # Add 5-minute buffer before actual expiration
        buffer_time = 300
        return time.time() + buffer_time >= self._token.expires_at

    async def health_check(self) -> Dict[str, Any]:
        """Perform Vault health check."""
        try:
            async with self._session.get(f"{self.config.url}/v1/sys/health") as response:
                data = await response.json()

                health_status = {
                    "healthy": response.status == 200,
                    "initialized": data.get("initialized", False),
                    "sealed": data.get("sealed", True),
                    "standby": data.get("standby", False),
                    "version": data.get("version", "unknown"),
                    "authenticated": self._authenticated,
                    "token_expires_in": self._token.expires_at - time.time() if self._token else 0,
                }

                return health_status

        except Exception as e:
            return {"healthy": False, "error": str(e), "authenticated": False}


# Utility functions for Vault integration


def create_vault_config_from_env() -> VaultConfig:
    """Create Vault configuration from environment variables."""
    import os

    url = os.getenv("VAULT_ADDR", "http://localhost:8200")
    auth_method_str = os.getenv("VAULT_AUTH_METHOD", "token").upper()
    auth_method = VaultAuthMethod[auth_method_str]

    config = VaultConfig(
        url=url,
        auth_method=auth_method,
        mount_path=os.getenv("VAULT_MOUNT_PATH", "stellar"),
        token=os.getenv("VAULT_TOKEN"),
        username=os.getenv("VAULT_USERNAME"),
        password=os.getenv("VAULT_PASSWORD"),
        role_id=os.getenv("VAULT_ROLE_ID"),
        secret_id=os.getenv("VAULT_SECRET_ID"),
        namespace=os.getenv("VAULT_NAMESPACE"),
    )

    return config


async def test_vault_connectivity(config: VaultConfig) -> Dict[str, Any]:
    """Test Vault connectivity and authentication."""
    result = {
        "connection": False,
        "authentication": False,
        "health": {},
        "operations": {},
        "error": None,
    }

    try:
        async with VaultKeyStore(config) as vault:
            result["connection"] = True
            result["authentication"] = vault._authenticated

            # Health check
            result["health"] = await vault.health_check()

            # Test basic operations with a dummy key
            test_key_id = "test_connectivity_key"
            test_key_data = b"test_key_data_12345"

            from .stellar_security_manager import KeyMetadata, KeyStoreType

            test_metadata = KeyMetadata(
                key_id=test_key_id,
                account_id="test_account",
                key_type="test",
                store_type=KeyStoreType.VAULT,
                security_level=SecurityLevel.DEVELOPMENT,
            )

            # Test store
            store_success = await vault.store_key(test_key_id, test_key_data, test_metadata)
            result["operations"]["store"] = store_success

            if store_success:
                # Test retrieve
                retrieve_result = await vault.retrieve_key(test_key_id)
                result["operations"]["retrieve"] = retrieve_result is not None

                # Test delete
                delete_success = await vault.delete_key(test_key_id)
                result["operations"]["delete"] = delete_success

            result["success"] = all(
                [
                    result["connection"],
                    result["authentication"],
                    result["operations"].get("store", False),
                    result["operations"].get("retrieve", False),
                    result["operations"].get("delete", False),
                ]
            )

    except Exception as e:
        result["error"] = str(e)
        result["success"] = False

    return result
