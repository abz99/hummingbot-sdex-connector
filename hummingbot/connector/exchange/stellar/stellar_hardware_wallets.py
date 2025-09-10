"""
Stellar Hardware Wallet Integration
Support for Ledger and Trezor hardware wallets for enhanced security.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import auto, Enum
from typing import Any, Dict, List, Optional, Union

from stellar_sdk import Account, Keypair, TransactionEnvelope

from .stellar_logging import get_stellar_logger, LogCategory
from .stellar_security_manager import KeyMetadata, SecurityLevel


class HardwareWalletStatus(Enum):
    """Hardware wallet connection status."""

    DISCONNECTED = auto()
    CONNECTED = auto()
    LOCKED = auto()
    BUSY = auto()
    ERROR = auto()


class HardwareWalletType(Enum):
    """Supported hardware wallet types."""

    LEDGER = auto()
    TREZOR = auto()


@dataclass
class HardwareWalletInfo:
    """Information about a connected hardware wallet."""

    device_id: str
    wallet_type: HardwareWalletType
    firmware_version: str
    status: HardwareWalletStatus
    stellar_app_version: Optional[str] = None
    last_connected: float = 0
    connection_attempts: int = 0


@dataclass
class SigningRequest:
    """Request for hardware wallet signing."""

    request_id: str
    account_path: str
    transaction_envelope: TransactionEnvelope
    network_passphrase: str
    timestamp: float
    timeout_seconds: int = 60


class HardwareWalletInterface(ABC):
    """Abstract interface for hardware wallet implementations."""

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the hardware wallet."""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the hardware wallet."""
        pass

    @abstractmethod
    async def get_public_key(self, derivation_path: str) -> Optional[str]:
        """Get public key from hardware wallet."""
        pass

    @abstractmethod
    async def sign_transaction(
        self,
        derivation_path: str,
        transaction_envelope: TransactionEnvelope,
        network_passphrase: str,
    ) -> Optional[bytes]:
        """Sign transaction with hardware wallet."""
        pass

    @abstractmethod
    async def get_device_info(self) -> Optional[HardwareWalletInfo]:
        """Get device information."""
        pass


class LedgerWallet(HardwareWalletInterface):
    """Ledger hardware wallet implementation."""

    def __init__(self) -> None:
        self.logger = get_stellar_logger()
        self.device_info: Optional[HardwareWalletInfo] = None
        self._connection = None

        # Note: This is a placeholder implementation
        # In a real implementation, you would use the Ledger SDK
        self.logger.warning(
            "Ledger integration is a placeholder - requires Ledger SDK",
            category=LogCategory.SECURITY,
        )

    async def connect(self) -> bool:
        """Connect to Ledger device."""
        try:
            # Placeholder for actual Ledger connection logic
            # In real implementation:
            # from ledgerblue.comm import getDongle
            # self._connection = getDongle()

            self.device_info = HardwareWalletInfo(
                device_id="ledger_placeholder_001",
                wallet_type=HardwareWalletType.LEDGER,
                firmware_version="2.1.0",
                status=HardwareWalletStatus.CONNECTED,
                stellar_app_version="1.0.0",
                last_connected=time.time(),
            )

            self.logger.info(
                "Connected to Ledger device (placeholder)",
                category=LogCategory.SECURITY,
                device_id=self.device_info.device_id,
            )

            return False  # Return False since this is placeholder

        except Exception as e:
            self.logger.error(
                f"Failed to connect to Ledger device: {e}",
                category=LogCategory.SECURITY,
                exception=e,
            )
            return False

    async def disconnect(self) -> bool:
        """Disconnect from Ledger device."""
        try:
            if self._connection:
                # Placeholder for actual disconnection
                self._connection = None

            if self.device_info:
                self.device_info.status = HardwareWalletStatus.DISCONNECTED

            self.logger.info("Disconnected from Ledger device", category=LogCategory.SECURITY)

            return True

        except Exception as e:
            self.logger.error(
                f"Failed to disconnect from Ledger device: {e}",
                category=LogCategory.SECURITY,
                exception=e,
            )
            return False

    async def get_public_key(self, derivation_path: str) -> Optional[str]:
        """Get public key from Ledger device."""
        try:
            # Placeholder implementation
            # In real implementation, this would communicate with the Ledger device
            # to derive the public key at the specified path

            self.logger.warning(
                f"Ledger get_public_key not implemented: {derivation_path}",
                category=LogCategory.SECURITY,
            )

            return None

        except Exception as e:
            self.logger.error(
                f"Failed to get public key from Ledger: {e}",
                category=LogCategory.SECURITY,
                exception=e,
            )
            return None

    async def sign_transaction(
        self,
        derivation_path: str,
        transaction_envelope: TransactionEnvelope,
        network_passphrase: str,
    ) -> Optional[bytes]:
        """Sign transaction with Ledger device."""
        try:
            # Placeholder implementation
            # In real implementation, this would:
            # 1. Send transaction to Ledger for user approval
            # 2. Get signature from device
            # 3. Return the signature bytes

            self.logger.warning(
                f"Ledger sign_transaction not implemented: {derivation_path}",
                category=LogCategory.SECURITY,
            )

            return None

        except Exception as e:
            self.logger.error(
                f"Failed to sign transaction with Ledger: {e}",
                category=LogCategory.SECURITY,
                exception=e,
            )
            return None

    async def get_device_info(self) -> Optional[HardwareWalletInfo]:
        """Get Ledger device information."""
        return self.device_info


class TrezorWallet(HardwareWalletInterface):
    """Trezor hardware wallet implementation."""

    def __init__(self) -> None:
        self.logger = get_stellar_logger()
        self.device_info: Optional[HardwareWalletInfo] = None
        self._client = None

        # Note: This is a placeholder implementation
        # In a real implementation, you would use the Trezor SDK
        self.logger.warning(
            "Trezor integration is a placeholder - requires Trezor SDK",
            category=LogCategory.SECURITY,
        )

    async def connect(self) -> bool:
        """Connect to Trezor device."""
        try:
            # Placeholder for actual Trezor connection logic
            # In real implementation:
            # from trezorlib import stellar, ui
            # from trezorlib.client import TrezorClient
            # from trezorlib.transport import get_transport
            # transport = get_transport()
            # self._client = TrezorClient(transport, ui=ui.ClickUI())

            self.device_info = HardwareWalletInfo(
                device_id="trezor_placeholder_001",
                wallet_type=HardwareWalletType.TREZOR,
                firmware_version="2.4.3",
                status=HardwareWalletStatus.CONNECTED,
                stellar_app_version="1.2.0",
                last_connected=time.time(),
            )

            self.logger.info(
                "Connected to Trezor device (placeholder)",
                category=LogCategory.SECURITY,
                device_id=self.device_info.device_id,
            )

            return False  # Return False since this is placeholder

        except Exception as e:
            self.logger.error(
                f"Failed to connect to Trezor device: {e}",
                category=LogCategory.SECURITY,
                exception=e,
            )
            return False

    async def disconnect(self) -> bool:
        """Disconnect from Trezor device."""
        try:
            if self._client:
                # Placeholder for actual disconnection
                self._client = None

            if self.device_info:
                self.device_info.status = HardwareWalletStatus.DISCONNECTED

            self.logger.info("Disconnected from Trezor device", category=LogCategory.SECURITY)

            return True

        except Exception as e:
            self.logger.error(
                f"Failed to disconnect from Trezor device: {e}",
                category=LogCategory.SECURITY,
                exception=e,
            )
            return False

    async def get_public_key(self, derivation_path: str) -> Optional[str]:
        """Get public key from Trezor device."""
        try:
            # Placeholder implementation
            # In real implementation, this would use the Trezor library
            # to get the public key at the specified derivation path

            self.logger.warning(
                f"Trezor get_public_key not implemented: {derivation_path}",
                category=LogCategory.SECURITY,
            )

            return None

        except Exception as e:
            self.logger.error(
                f"Failed to get public key from Trezor: {e}",
                category=LogCategory.SECURITY,
                exception=e,
            )
            return None

    async def sign_transaction(
        self,
        derivation_path: str,
        transaction_envelope: TransactionEnvelope,
        network_passphrase: str,
    ) -> Optional[bytes]:
        """Sign transaction with Trezor device."""
        try:
            # Placeholder implementation
            # In real implementation, this would:
            # 1. Convert transaction to Trezor format
            # 2. Send to device for user approval
            # 3. Get signature from device
            # 4. Return the signature bytes

            self.logger.warning(
                f"Trezor sign_transaction not implemented: {derivation_path}",
                category=LogCategory.SECURITY,
            )

            return None

        except Exception as e:
            self.logger.error(
                f"Failed to sign transaction with Trezor: {e}",
                category=LogCategory.SECURITY,
                exception=e,
            )
            return None

    async def get_device_info(self) -> Optional[HardwareWalletInfo]:
        """Get Trezor device information."""
        return self.device_info


class HardwareWalletManager:
    """Manager for hardware wallet operations."""

    def __init__(self) -> None:
        self.logger = get_stellar_logger()
        self._wallets: Dict[str, HardwareWalletInterface] = {}
        self._signing_requests: Dict[str, SigningRequest] = {}

        # Initialize supported wallet types
        self._initialize_wallet_support()

    def _initialize_wallet_support(self) -> None:
        """Initialize hardware wallet support."""
        try:
            # Check for Ledger support
            ledger_wallet = LedgerWallet()
            self._wallets["ledger"] = ledger_wallet

            # Check for Trezor support
            trezor_wallet = TrezorWallet()
            self._wallets["trezor"] = trezor_wallet

            self.logger.info(
                f"Hardware wallet support initialized: {list(self._wallets.keys())}",
                category=LogCategory.SECURITY,
                supported_wallets=list(self._wallets.keys()),
            )

        except Exception as e:
            self.logger.error(
                f"Failed to initialize hardware wallet support: {e}",
                category=LogCategory.SECURITY,
                exception=e,
            )

    async def detect_wallets(self) -> List[HardwareWalletInfo]:
        """Detect connected hardware wallets."""
        detected_wallets = []

        for wallet_name, wallet in self._wallets.items():
            try:
                connected = await wallet.connect()
                if connected:
                    info = await wallet.get_device_info()
                    if info:
                        detected_wallets.append(info)

            except Exception as e:
                self.logger.warning(
                    f"Failed to detect {wallet_name} wallet: {e}",
                    category=LogCategory.SECURITY,
                    wallet_type=wallet_name,
                )

        self.logger.info(
            f"Detected {len(detected_wallets)} hardware wallets",
            category=LogCategory.SECURITY,
            wallet_count=len(detected_wallets),
        )

        return detected_wallets

    async def get_wallet_by_type(
        self, wallet_type: HardwareWalletType
    ) -> Optional[HardwareWalletInterface]:
        """Get wallet interface by type."""
        if wallet_type == HardwareWalletType.LEDGER:
            return self._wallets.get("ledger")
        elif wallet_type == HardwareWalletType.TREZOR:
            return self._wallets.get("trezor")
        else:
            return None

    async def get_public_key(
        self, wallet_type: HardwareWalletType, derivation_path: str
    ) -> Optional[str]:
        """Get public key from hardware wallet."""
        wallet = await self.get_wallet_by_type(wallet_type)
        if not wallet:
            return None

        try:
            public_key = await wallet.get_public_key(derivation_path)
            if public_key:
                self.logger.info(
                    f"Retrieved public key from {wallet_type.name}",
                    category=LogCategory.SECURITY,
                    wallet_type=wallet_type.name,
                    derivation_path=derivation_path,
                )
            return public_key

        except Exception as e:
            self.logger.error(
                f"Failed to get public key from {wallet_type.name}: {e}",
                category=LogCategory.SECURITY,
                wallet_type=wallet_type.name,
                exception=e,
            )
            return None

    async def sign_transaction(
        self,
        wallet_type: HardwareWalletType,
        derivation_path: str,
        transaction_envelope: TransactionEnvelope,
        network_passphrase: str,
    ) -> Optional[bytes]:
        """Sign transaction with hardware wallet."""
        wallet = await self.get_wallet_by_type(wallet_type)
        if not wallet:
            return None

        try:
            # Create signing request
            import secrets

            request_id = secrets.token_urlsafe(16)
            signing_request = SigningRequest(
                request_id=request_id,
                account_path=derivation_path,
                transaction_envelope=transaction_envelope,
                network_passphrase=network_passphrase,
                timestamp=time.time(),
            )
            self._signing_requests[request_id] = signing_request

            # Sign transaction
            signature = await wallet.sign_transaction(
                derivation_path, transaction_envelope, network_passphrase
            )

            # Clean up request
            del self._signing_requests[request_id]

            if signature:
                self.logger.info(
                    f"Transaction signed by {wallet_type.name}",
                    category=LogCategory.SECURITY,
                    wallet_type=wallet_type.name,
                    request_id=request_id,
                )

            return signature

        except Exception as e:
            self.logger.error(
                f"Failed to sign transaction with {wallet_type.name}: {e}",
                category=LogCategory.SECURITY,
                wallet_type=wallet_type.name,
                exception=e,
            )
            return None

    async def disconnect_all(self) -> None:
        """Disconnect all connected hardware wallets."""
        for wallet_name, wallet in self._wallets.items():
            try:
                await wallet.disconnect()
                self.logger.info(
                    f"Disconnected {wallet_name} wallet",
                    category=LogCategory.SECURITY,
                    wallet_type=wallet_name,
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to disconnect {wallet_name} wallet: {e}",
                    category=LogCategory.SECURITY,
                    wallet_type=wallet_name,
                    exception=e,
                )

    def get_pending_requests(self) -> List[SigningRequest]:
        """Get list of pending signing requests."""
        return list(self._signing_requests.values())

    def cancel_request(self, request_id: str) -> bool:
        """Cancel a pending signing request."""
        if request_id in self._signing_requests:
            del self._signing_requests[request_id]
            self.logger.info(
                f"Cancelled signing request: {request_id}",
                category=LogCategory.SECURITY,
                request_id=request_id,
            )
            return True
        return False

    def get_wallet_status(self) -> Dict[str, Any]:
        """Get status of all hardware wallets."""
        return {
            "supported_wallets": list(self._wallets.keys()),
            "pending_requests": len(self._signing_requests),
            "request_ids": list(self._signing_requests.keys()),
        }


# Utility functions for hardware wallet integration


def derive_stellar_path(account_index: int = 0, change: int = 0, address_index: int = 0) -> str:
    """
    Generate BIP-44 derivation path for Stellar.

    Stellar uses coin type 148.
    Path format: m/44'/148'/account'/change/address_index
    """
    return f"m/44'/148'/{account_index}'/{change}/{address_index}"


def validate_derivation_path(path: str) -> bool:
    """Validate BIP-44 derivation path for Stellar."""
    try:
        parts = path.split("/")
        if len(parts) != 6:
            return False

        if parts[0] != "m":
            return False

        if parts[1] != "44'":
            return False

        if parts[2] != "148'":  # Stellar coin type
            return False

        # Check that remaining parts are valid integers
        for i in range(3, 6):
            part = parts[i]
            if part.endswith("'"):
                part = part[:-1]
            int(part)  # Will raise ValueError if not valid

        return True

    except (ValueError, IndexError):
        return False


async def test_hardware_wallet_connection() -> Dict[str, Any]:
    """Test hardware wallet connectivity (for development/testing)."""
    manager = HardwareWalletManager()

    try:
        # Detect wallets
        detected = await manager.detect_wallets()

        # Test public key retrieval (if any wallets detected)
        test_results = {}
        for wallet_info in detected:
            test_path = derive_stellar_path(0, 0, 0)
            public_key = await manager.get_public_key(wallet_info.wallet_type, test_path)

            test_results[wallet_info.device_id] = {
                "wallet_type": wallet_info.wallet_type.name,
                "firmware_version": wallet_info.firmware_version,
                "test_path": test_path,
                "public_key_retrieved": public_key is not None,
            }

        return {
            "detected_wallets": len(detected),
            "test_results": test_results,
            "status": "success" if detected else "no_wallets_detected",
        }

    except Exception as e:
        return {"detected_wallets": 0, "test_results": {}, "status": "error", "error": str(e)}
    finally:
        await manager.disconnect_all()
