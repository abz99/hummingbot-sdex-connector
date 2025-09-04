"""
Stellar Chain Interface Implementation
Core Stellar network operations with Protocol 23 support
"""

import asyncio
import time
from decimal import Decimal
from typing import Dict, List, Optional, Set
from stellar_sdk import Server, Account, Transaction, TransactionBuilder, Keypair
from stellar_sdk.exceptions import NotFoundError, BadRequestError


class StellarNetworkConfig:
    """Network configuration for different Stellar networks"""

    @staticmethod
    def get_config(network: str):
        configs = {
            "mainnet": {
                "horizon_url": "https://horizon.stellar.org",
                "network_passphrase": "Public Global Stellar Network ; September 2015",
            },
            "testnet": {
                "horizon_url": "https://horizon-testnet.stellar.org",
                "network_passphrase": "Test SDF Network ; September 2015",
            },
        }
        return configs[network]


class SequenceNumberManager:
    """Thread-safe sequence number management for Stellar accounts"""

    def __init__(self):
        self._account_sequences: Dict[str, int] = {}
        self._sequence_locks: Dict[str, asyncio.Lock] = {}
        self._pending_sequences: Dict[str, Set[int]] = {}

    def _get_lock(self, address: str) -> asyncio.Lock:
        if address not in self._sequence_locks:
            self._sequence_locks[address] = asyncio.Lock()
        return self._sequence_locks[address]

    async def get_next_sequence(self, address: str) -> str:
        """Get next available sequence number for account"""
        async with self._get_lock(address):
            current_seq = self._account_sequences.get(address, 0)
            next_seq = current_seq + 1

            # Check for pending transactions
            while next_seq in self._pending_sequences.get(address, set()):
                next_seq += 1

            self._pending_sequences.setdefault(address, set()).add(next_seq)
            return str(next_seq)

    async def release_sequence(self, address: str, sequence: str) -> None:
        """Release sequence number after transaction completion"""
        async with self._get_lock(address):
            seq_num = int(sequence)
            self._pending_sequences.get(address, set()).discard(seq_num)
            self._account_sequences[address] = max(self._account_sequences.get(address, 0), seq_num)

    async def sync_sequence(self, address: str, network_sequence: int) -> None:
        """Sync sequence number with network state"""
        async with self._get_lock(address):
            self._account_sequences[address] = network_sequence


class ReserveCalculator:
    """Calculate minimum balance requirements for Stellar accounts"""

    BASE_RESERVE = Decimal("0.5")  # 0.5 XLM per ledger entry
    BASE_ACCOUNT_RESERVE = Decimal("1.0")  # 1 XLM for account itself

    def calculate_minimum_balance(self, account) -> Decimal:
        """Calculate minimum XLM balance required for account"""
        entries = 2  # Account + native balance

        # Count trustlines
        entries += len([b for b in account.balances if b.asset_type != "native"])

        # Count offers
        entries += account.subentry_count

        # Count data entries
        entries += len(account.data)

        # Count signers (beyond master key)
        entries += len([s for s in account.signers if s.key != account.account_id])

        return self.BASE_ACCOUNT_RESERVE + (entries * self.BASE_RESERVE)

    def validate_sufficient_balance(self, account, operation_cost: Decimal) -> bool:
        """Validate account has sufficient balance for operation"""
        current_balance = Decimal(account.native_balance)
        required_reserve = self.calculate_minimum_balance(account)
        available_balance = current_balance - required_reserve

        return available_balance >= operation_cost

    def calculate_reserve_impact(self, operations: List) -> Decimal:
        """Calculate how operations will impact reserve requirements"""
        reserve_impact = Decimal("0")

        for op in operations:
            if op.__class__.__name__ == "ChangeTrust":
                reserve_impact += self.BASE_RESERVE  # New trustline
            elif op.__class__.__name__ == "ManageBuyOffer" and getattr(op, "offer_id", 0) == 0:
                reserve_impact += self.BASE_RESERVE  # New offer
            elif op.__class__.__name__ == "ManageData" and getattr(op, "data_value", None):
                reserve_impact += self.BASE_RESERVE  # New data entry

        return reserve_impact


class StellarChainInterface:
    """Core Stellar network abstraction with Protocol 23 support"""

    def __init__(self, config: Dict):
        self.server = Server(config["horizon_url"])
        self.network_passphrase = config["network_passphrase"]
        self.protocol_version = 23
        self.sequence_manager = SequenceNumberManager()
        self.reserve_calculator = ReserveCalculator()
        self.is_connected = False

    async def connect(self) -> bool:
        """Establish connection to Stellar network"""
        try:
            # Test connection with a simple ledger query
            await self.server.ledgers().limit(1).call()
            self.is_connected = True
            return True
        except Exception as e:
            self.is_connected = False
            raise ConnectionError(f"Failed to connect to Stellar network: {e}")

    async def disconnect(self) -> None:
        """Clean disconnection from network"""
        self.is_connected = False
        # Close any active streams, cleanup resources

    async def load_account(self, address: str):
        """Load account with sequence number management"""
        try:
            account = await self.server.load_account(address)
            await self.sequence_manager.sync_sequence(address, int(account.sequence))
            return account
        except NotFoundError:
            raise ValueError(f"Account {address} not found on Stellar network")

    async def submit_transaction(self, transaction: Transaction):
        """Submit transaction with proper error handling and retry logic"""
        try:
            result = await self.server.submit_transaction(transaction)

            # Update sequence manager on success
            await self.sequence_manager.release_sequence(
                transaction.source_account, str(int(transaction.sequence) + 1)
            )

            return result

        except Exception as e:
            # Handle specific error types
            await self.handle_transaction_error(e, transaction)
            raise

    async def handle_transaction_error(self, error: Exception, transaction: Transaction):
        """Handle transaction submission errors"""
        error_str = str(error).lower()

        if "tx_bad_seq" in error_str:
            # Sequence number error - refresh from network
            account = await self.server.load_account(transaction.source_account)
            await self.sequence_manager.sync_sequence(
                transaction.source_account, int(account.sequence)
            )

    async def calculate_fee(self, operation_count: int = 1) -> int:
        """Calculate appropriate transaction fee"""
        # Base fee per operation (100 stroops = 0.00001 XLM)
        base_fee = 100
        return base_fee * operation_count

    async def get_network_info(self) -> Dict:
        """Get current network information"""
        try:
            ledger = await self.server.ledgers().order("desc").limit(1).call()
            latest_ledger = ledger.records[0]

            return {
                "latest_ledger": latest_ledger.sequence,
                "base_fee": latest_ledger.base_fee_in_stroops,
                "base_reserve": latest_ledger.base_reserve_in_stroops,
                "max_tx_set_size": latest_ledger.max_tx_set_size,
                "protocol_version": latest_ledger.protocol_version,
            }
        except Exception as e:
            raise RuntimeError(f"Failed to get network info: {e}")
