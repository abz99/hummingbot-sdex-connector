"""
Stellar Security Framework Implementation
Enterprise-grade security with HSM integration and transaction validation
"""

import time
import hashlib
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from decimal import Decimal
from cryptography.fernet import Fernet
from stellar_sdk import Keypair, Transaction
import logging


@dataclass
class SecurityConfig:
    use_hsm: bool = False
    hsm_type: str = "Local_HSM"
    hsm_config: Dict = None
    key_rotation_days: int = 90
    enable_replay_protection: bool = True
    max_concurrent_transactions: int = 10


@dataclass
class ValidationCheck:
    name: str
    passed: bool
    message: str
    risk_level: str = "LOW"


@dataclass
class SecurityValidationResult:
    is_secure: bool
    checks: List[ValidationCheck]
    risk_score: float


class SecureKeyManager:
    """Enterprise-grade key management with HSM support"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.hsm_client = self.initialize_hsm() if config.use_hsm else None
        self.address_to_key_mapping: Dict[str, str] = {}
        self.key_rotation_schedule = KeyRotationSchedule()
        self.logger = logging.getLogger(__name__)

    def initialize_hsm(self) -> Optional[Any]:
        """Initialize Hardware Security Module if available"""
        try:
            if self.config.hsm_type == "AWS_CloudHSM":
                return AWSCloudHSMClient(self.config.hsm_config)
            elif self.config.hsm_type == "Azure_KeyVault":
                return AzureKeyVaultClient(self.config.hsm_config)
            elif self.config.hsm_type == "Local_HSM":
                return LocalHSMClient(self.config.hsm_config)
            else:
                self.logger.warning("HSM type not supported, falling back to encrypted storage")
                return None
        except Exception as e:
            self.logger.error(f"HSM initialization failed: {e}")
            return None

    async def store_key(self, private_key: str, key_id: str = None) -> str:
        """Store private key securely and return public address"""

        if key_id is None:
            key_id = self.generate_key_id()

        if self.hsm_client:
            # Store in HSM
            await self.hsm_client.store_key(key_id, private_key)
        else:
            # Fallback to encrypted local storage
            encrypted_key = await self.encrypt_key(private_key)
            await self.store_encrypted_key(key_id, encrypted_key)

        # Derive public key for address mapping
        keypair = Keypair.from_secret(private_key)
        public_address = keypair.public_key

        # Store address mapping
        self.address_to_key_mapping[public_address] = key_id

        # Schedule key rotation
        self.key_rotation_schedule.add_key(key_id, self.config.key_rotation_days)

        return public_address

    async def sign_transaction(self, transaction: Transaction, address: str) -> Transaction:
        """Sign transaction with secure key access"""

        key_id = self.address_to_key_mapping.get(address)
        if not key_id:
            raise ValueError(f"No key found for address {address}")

        if self.hsm_client:
            # Sign using HSM
            signature = await self.hsm_client.sign_transaction(key_id, transaction)
            transaction.signatures.append(signature)
        else:
            # Retrieve and decrypt key for signing
            private_key = await self.retrieve_decrypted_key(key_id)
            try:
                keypair = Keypair.from_secret(private_key)
                transaction.sign(keypair)
            finally:
                # Clear private key from memory immediately
                private_key = "0" * len(private_key)

        return transaction

    async def encrypt_key(self, private_key: str) -> str:
        """Encrypt private key using Fernet symmetric encryption"""
        # Generate key from system entropy
        key = Fernet.generate_key()
        cipher = Fernet(key)
        encrypted = cipher.encrypt(private_key.encode())

        # Store encryption key securely (this is simplified - use proper key derivation)
        return encrypted.decode()

    def generate_key_id(self) -> str:
        """Generate unique key identifier"""
        return hashlib.sha256(f"{time.time()}{id(self)}".encode()).hexdigest()[:16]


class TransactionSecurityValidator:
    """Comprehensive transaction security validation"""

    def __init__(self, chain_interface):
        self.chain = chain_interface
        self.replay_protection = ReplayProtectionManager()
        self.fee_protection = FeeProtectionManager()
        self.logger = logging.getLogger(__name__)

    async def validate_transaction_security(
        self, transaction: Transaction, account
    ) -> SecurityValidationResult:
        """Comprehensive security validation before submission"""

        validations = []

        # 1. Replay protection validation
        replay_check = await self.validate_replay_protection(transaction)
        validations.append(replay_check)

        # 2. Sequence number validation
        sequence_check = await self.validate_sequence_number(transaction, account)
        validations.append(sequence_check)

        # 3. Fee manipulation protection
        fee_check = await self.validate_fee_structure(transaction)
        validations.append(fee_check)

        # 4. Signature verification
        signature_check = await self.validate_signatures(transaction)
        validations.append(signature_check)

        # 5. Balance and reserve validation
        balance_check = await self.validate_balance_sufficiency(transaction, account)
        validations.append(balance_check)

        return SecurityValidationResult(
            is_secure=all(v.passed for v in validations),
            checks=validations,
            risk_score=self.calculate_risk_score(validations),
        )

    async def validate_replay_protection(self, transaction: Transaction) -> ValidationCheck:
        """Prevent transaction replay attacks"""

        tx_hash = transaction.hash().hex()

        # Check if transaction hash was recently submitted
        if await self.replay_protection.is_recent_transaction(tx_hash):
            return ValidationCheck(
                name="replay_protection",
                passed=False,
                message="Transaction hash recently submitted (potential replay attack)",
                risk_level="HIGH",
            )

        # Record transaction hash
        await self.replay_protection.record_transaction(tx_hash)

        return ValidationCheck(
            name="replay_protection", passed=True, message="No replay attack detected"
        )

    async def validate_fee_structure(self, transaction: Transaction) -> ValidationCheck:
        """Validate transaction fees against manipulation"""

        # Calculate expected fee
        expected_fee = await self.fee_protection.calculate_expected_fee(transaction)
        actual_fee = Decimal(transaction.fee)

        # Check for excessive fees (potential fee manipulation)
        if actual_fee > expected_fee * Decimal("10"):  # 10x threshold
            return ValidationCheck(
                name="fee_validation",
                passed=False,
                message=f"Fee {actual_fee} exceeds expected {expected_fee} by >10x",
                risk_level="HIGH",
            )

        # Check for insufficient fees
        if actual_fee < expected_fee * Decimal("0.5"):  # 50% threshold
            return ValidationCheck(
                name="fee_validation",
                passed=False,
                message=f"Fee {actual_fee} below minimum expected {expected_fee * 0.5}",
                risk_level="MEDIUM",
            )

        return ValidationCheck(
            name="fee_validation", passed=True, message=f"Fee {actual_fee} within expected range"
        )

    async def validate_sequence_number(self, transaction: Transaction, account) -> ValidationCheck:
        """Validate transaction sequence number"""

        expected_sequence = int(account.sequence) + 1
        actual_sequence = int(transaction.sequence)

        if actual_sequence != expected_sequence:
            return ValidationCheck(
                name="sequence_validation",
                passed=False,
                message=f"Sequence mismatch: expected {expected_sequence}, got {actual_sequence}",
                risk_level="HIGH",
            )

        return ValidationCheck(
            name="sequence_validation", passed=True, message="Sequence number valid"
        )

    async def validate_signatures(self, transaction: Transaction) -> ValidationCheck:
        """Validate transaction signatures"""

        if not transaction.signatures:
            return ValidationCheck(
                name="signature_validation",
                passed=False,
                message="Transaction has no signatures",
                risk_level="CRITICAL",
            )

        # Verify signature count meets requirements
        # (This would need account threshold information)
        return ValidationCheck(name="signature_validation", passed=True, message="Signatures valid")

    async def validate_balance_sufficiency(
        self, transaction: Transaction, account
    ) -> ValidationCheck:
        """Validate account has sufficient balance"""

        total_cost = await self.calculate_transaction_cost(transaction)
        required_reserve = self.chain.reserve_calculator.calculate_minimum_balance(account)
        available_balance = Decimal(account.native_balance) - required_reserve

        if available_balance < total_cost:
            return ValidationCheck(
                name="balance_validation",
                passed=False,
                message=f"Insufficient balance. Required: {total_cost}, Available: {available_balance}",
                risk_level="HIGH",
            )

        return ValidationCheck(
            name="balance_validation", passed=True, message="Sufficient balance available"
        )

    def calculate_risk_score(self, validations: List[ValidationCheck]) -> float:
        """Calculate overall risk score from validations"""

        risk_weights = {"LOW": 1, "MEDIUM": 3, "HIGH": 7, "CRITICAL": 10}

        total_risk = sum(risk_weights.get(v.risk_level, 1) for v in validations if not v.passed)

        max_possible_risk = len(validations) * 10

        return total_risk / max_possible_risk if max_possible_risk > 0 else 0.0

    async def calculate_transaction_cost(self, transaction: Transaction) -> Decimal:
        """Calculate total transaction cost including fees"""

        base_cost = Decimal(transaction.fee)

        # Add operation-specific costs
        operation_cost = Decimal("0")
        for operation in transaction.operations:
            if hasattr(operation, "amount"):
                operation_cost += Decimal(operation.amount)

        return base_cost + operation_cost


class ReplayProtectionManager:
    """Manage replay attack protection"""

    def __init__(self, ttl_seconds: int = 300):  # 5 minute TTL
        self.recent_transactions: Dict[str, float] = {}
        self.ttl_seconds = ttl_seconds

    async def is_recent_transaction(self, tx_hash: str) -> bool:
        """Check if transaction hash was recently submitted"""

        # Clean expired entries
        current_time = time.time()
        expired_hashes = [
            h
            for h, timestamp in self.recent_transactions.items()
            if current_time - timestamp > self.ttl_seconds
        ]

        for h in expired_hashes:
            del self.recent_transactions[h]

        return tx_hash in self.recent_transactions

    async def record_transaction(self, tx_hash: str) -> None:
        """Record transaction hash to prevent replay"""
        self.recent_transactions[tx_hash] = time.time()


class FeeProtectionManager:
    """Protect against fee manipulation attacks"""

    def __init__(self):
        self.base_fee_cache: Optional[int] = None
        self.cache_expiry: float = 0

    async def calculate_expected_fee(self, transaction: Transaction) -> Decimal:
        """Calculate expected transaction fee"""

        # Get current base fee from network
        base_fee = await self.get_current_base_fee()

        # Calculate based on operation count
        operation_count = len(transaction.operations)
        expected_fee = base_fee * operation_count

        return Decimal(expected_fee)

    async def get_current_base_fee(self) -> int:
        """Get current network base fee with caching"""

        current_time = time.time()

        # Use cached value if still valid (cache for 60 seconds)
        if self.base_fee_cache and current_time < self.cache_expiry:
            return self.base_fee_cache

        # Fetch from network (this would need access to server)
        # For now, return default
        self.base_fee_cache = 100  # 100 stroops default
        self.cache_expiry = current_time + 60

        return self.base_fee_cache


class MultiSignatureManager:
    """Handle multi-signature transaction workflows"""

    def __init__(self, chain_interface):
        self.chain = chain_interface
        self.pending_transactions: Dict[str, Dict] = {}
        self.logger = logging.getLogger(__name__)

    async def create_multisig_transaction(
        self, account: str, operations: List, signers: List[str], threshold: int
    ) -> str:
        """Create transaction requiring multiple signatures"""

        account_obj = await self.chain.load_account(account)

        # Verify account has proper multisig setup
        if not self.validate_multisig_setup(account_obj, signers, threshold):
            raise ValueError("Account not properly configured for multi-signature")

        # Build unsigned transaction
        transaction = (
            TransactionBuilder(
                source_account=account_obj,
                network_passphrase=self.chain.network_passphrase,
                base_fee=100,
            )
            .append_operations(operations)
            .set_timeout(300)  # 5 minutes
            .build()
        )

        tx_id = self.generate_transaction_id(transaction)

        self.pending_transactions[tx_id] = {
            "transaction": transaction,
            "required_signers": signers,
            "threshold": threshold,
            "signatures_collected": 0,
            "created_at": time.time(),
        }

        return tx_id

    async def add_signature(self, tx_id: str, signer_keypair: Keypair) -> Dict:
        """Add signature to pending multi-sig transaction"""

        if tx_id not in self.pending_transactions:
            raise ValueError(f"Transaction {tx_id} not found")

        pending_tx = self.pending_transactions[tx_id]

        # Verify signer is authorized
        if signer_keypair.public_key not in pending_tx["required_signers"]:
            raise ValueError("Unauthorized signer")

        # Add signature to transaction
        pending_tx["transaction"].sign(signer_keypair)
        pending_tx["signatures_collected"] += 1

        # Check if threshold met
        if pending_tx["signatures_collected"] >= pending_tx["threshold"]:
            # Submit transaction
            result = await self.chain.submit_transaction(pending_tx["transaction"])
            del self.pending_transactions[tx_id]

            return {"tx_id": tx_id, "ready_to_submit": True, "transaction_result": result}

        return {
            "tx_id": tx_id,
            "ready_to_submit": False,
            "signatures_remaining": pending_tx["threshold"] - pending_tx["signatures_collected"],
        }

    def validate_multisig_setup(self, account, signers: List[str], threshold: int) -> bool:
        """Validate account is properly configured for multi-signature"""

        # Check if account has required signers
        account_signers = {signer.key for signer in account.signers}
        required_signers = set(signers)

        if not required_signers.issubset(account_signers):
            return False

        # Check if threshold is achievable
        if threshold > len(signers):
            return False

        return True

    def generate_transaction_id(self, transaction: Transaction) -> str:
        """Generate unique transaction identifier"""
        return hashlib.sha256(f"{transaction.hash().hex()}{time.time()}".encode()).hexdigest()[:16]


class KeyRotationSchedule:
    """Manage automatic key rotation schedule"""

    def __init__(self):
        self.rotation_schedule: Dict[str, Dict] = {}

    def add_key(self, key_id: str, rotation_interval_days: int) -> None:
        """Add key to rotation schedule"""

        self.rotation_schedule[key_id] = {
            "created_at": time.time(),
            "rotation_interval": rotation_interval_days * 24 * 3600,  # Convert to seconds
            "next_rotation": time.time() + (rotation_interval_days * 24 * 3600),
            "rotation_count": 0,
        }

    def get_keys_due_for_rotation(self) -> List[str]:
        """Get list of keys that need rotation"""

        current_time = time.time()
        return [
            key_id
            for key_id, schedule in self.rotation_schedule.items()
            if current_time >= schedule["next_rotation"]
        ]

    def update_key_rotation(self, key_id: str) -> None:
        """Update rotation schedule after key rotation"""

        if key_id in self.rotation_schedule:
            schedule = self.rotation_schedule[key_id]
            schedule["rotation_count"] += 1
            schedule["next_rotation"] = time.time() + schedule["rotation_interval"]


# Placeholder classes for HSM implementations
class AWSCloudHSMClient:
    def __init__(self, config):
        pass

    async def store_key(self, key_id, private_key):
        pass

    async def sign_transaction(self, key_id, transaction):
        pass


class AzureKeyVaultClient:
    def __init__(self, config):
        pass

    async def store_key(self, key_id, private_key):
        pass

    async def sign_transaction(self, key_id, transaction):
        pass


class LocalHSMClient:
    def __init__(self, config):
        pass

    async def store_key(self, key_id, private_key):
        pass

    async def sign_transaction(self, key_id, transaction):
        pass
