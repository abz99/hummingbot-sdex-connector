"""
Stellar AMM Integration Module

This module provides comprehensive integration with Stellar Automated Market Makers (AMMs),
including liquidity pool management, swap operations, and yield optimization strategies.

Author: Hummingbot
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from stellar_sdk import (
    Account,
    Asset,
    FeeBumpTransactionEnvelope,
    Keypair,
    Network,
    Operation,
    Price,
    Server,
    TransactionBuilder,
    TransactionEnvelope,
)
from stellar_sdk.exceptions import BadRequestError, RequestException
from stellar_sdk.operation import LiquidityPoolDeposit, LiquidityPoolWithdraw, PathPaymentStrictSend

from hummingbot.core.data_type.common import TradeType
from hummingbot.core.utils.async_utils import safe_ensure_future
from hummingbot.logger import HummingbotLogger


class AMMType(Enum):
    """AMM protocol types supported on Stellar"""

    CONSTANT_PRODUCT = "constant_product"
    STABLE_SWAP = "stable_swap"
    WEIGHTED_POOL = "weighted_pool"


class LiquidityPoolStatus(Enum):
    """Liquidity pool operational status"""

    ACTIVE = "active"
    PAUSED = "paused"
    DEPRECATED = "deprecated"
    EMERGENCY_STOP = "emergency_stop"


@dataclass
class LiquidityPool:
    """Represents a Stellar liquidity pool"""

    id: str
    asset_a: Asset
    asset_b: Asset
    reserves_a: Decimal
    reserves_b: Decimal
    total_shares: Decimal
    fee_bp: int  # Fee in basis points
    amm_type: AMMType
    status: LiquidityPoolStatus
    last_updated: float = field(default_factory=time.time)
    volume_24h: Decimal = field(default=Decimal("0"))
    apy: Decimal = field(default=Decimal("0"))
    total_value_locked: Decimal = field(default=Decimal("0"))

    @property
    def price_a_to_b(self) -> Decimal:
        """Current price of asset A in terms of asset B"""
        if self.reserves_a == 0:
            return Decimal("0")
        return self.reserves_b / self.reserves_a

    @property
    def price_b_to_a(self) -> Decimal:
        """Current price of asset B in terms of asset A"""
        if self.reserves_b == 0:
            return Decimal("0")
        return self.reserves_a / self.reserves_b


@dataclass
class SwapQuote:
    """AMM swap quote with pricing and impact information"""

    input_asset: Asset
    output_asset: Asset
    input_amount: Decimal
    output_amount: Decimal
    price: Decimal
    price_impact: Decimal
    fee: Decimal
    slippage: Decimal
    pool_id: str
    route: List[str]  # Pool IDs in swap route
    minimum_received: Decimal
    expiry: float

    @property
    def is_expired(self) -> bool:
        """Check if quote has expired"""
        return time.time() > self.expiry


@dataclass
class LiquidityPosition:
    """User's liquidity provider position"""

    pool_id: str
    shares: Decimal
    asset_a_amount: Decimal
    asset_b_amount: Decimal
    entry_price_a: Decimal
    entry_price_b: Decimal
    entry_timestamp: float
    rewards_earned: Decimal = field(default=Decimal("0"))
    impermanent_loss: Decimal = field(default=Decimal("0"))


class StellarAMMIntegration:
    """
    Comprehensive Stellar AMM integration with advanced features:
    - Multi-pool liquidity management
    - Optimized swap routing
    - Impermanent loss tracking
    - Yield farming integration
    - MEV protection
    """

    _logger: Optional[HummingbotLogger] = None

    def __init__(
        self,
        server: Server,
        network: Network,
        source_account: Account,
        source_keypair: Keypair,
        max_slippage: Decimal = Decimal("0.01"),  # 1%
        quote_expiry_seconds: int = 30,
        enable_mev_protection: bool = True,
    ):
        self._server = server
        self._network = network
        self._source_account = source_account
        self._source_keypair = source_keypair
        self._max_slippage = max_slippage
        self._quote_expiry_seconds = quote_expiry_seconds
        self._enable_mev_protection = enable_mev_protection

        # Pool management
        self._pools: Dict[str, LiquidityPool] = {}
        self._pool_update_tasks: Dict[str, asyncio.Task[None]] = {}
        self._positions: Dict[str, LiquidityPosition] = {}

        # Routing and optimization
        self._route_cache: Dict[str, List[str]] = {}
        self._price_cache: Dict[str, Tuple[Decimal, float]] = {}
        self._cache_ttl = 30  # seconds

        # Performance tracking
        self._swap_metrics = defaultdict(lambda: {"count": 0, "volume": Decimal("0")})
        self._liquidity_metrics = defaultdict(lambda: {"deposits": 0, "withdrawals": 0})

        # MEV protection
        self._pending_transactions: Set[str] = set()
        self._transaction_delays: Dict[str, float] = {}

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._logger is None:
            cls._logger = logging.getLogger(__name__)
        return cls._logger

    async def initialize(self) -> None:
        """Initialize AMM integration and discover available pools"""
        try:
            self.logger().info("Initializing Stellar AMM integration...")

            # Discover liquidity pools
            await self._discover_pools()

            # Start pool monitoring
            await self._start_pool_monitoring()

            # Load existing positions
            await self._load_positions()

            self.logger().info(f"AMM integration initialized with {len(self._pools)} pools")

        except Exception as e:
            self.logger().error(f"Failed to initialize AMM integration: {e}")
            raise

    async def _discover_pools(self) -> None:
        """Discover all available liquidity pools"""
        try:
            # Get all liquidity pools from Stellar
            pools_response = await self._server.liquidity_pools().limit(200).call()

            for pool_record in pools_response["_embedded"]["records"]:
                pool = await self._parse_pool_record(pool_record)
                if pool:
                    self._pools[pool.id] = pool

        except Exception as e:
            self.logger().error(f"Failed to discover pools: {e}")
            raise

    async def _parse_pool_record(self, pool_record: Dict[str, Any]) -> Optional[LiquidityPool]:
        """Parse Stellar pool record into LiquidityPool object"""
        try:
            pool_id = pool_record["id"]

            # Parse assets
            asset_a = (
                Asset.native()
                if pool_record["reserves"][0]["asset"] == "native"
                else Asset(
                    pool_record["reserves"][0]["asset"].split(":")[0],
                    pool_record["reserves"][0]["asset"].split(":")[1],
                )
            )

            asset_b = (
                Asset.native()
                if pool_record["reserves"][1]["asset"] == "native"
                else Asset(
                    pool_record["reserves"][1]["asset"].split(":")[0],
                    pool_record["reserves"][1]["asset"].split(":")[1],
                )
            )

            # Parse reserves and shares
            reserves_a = Decimal(pool_record["reserves"][0]["amount"])
            reserves_b = Decimal(pool_record["reserves"][1]["amount"])
            total_shares = Decimal(pool_record["total_shares"])

            # Parse fee (default to 30 bp for Stellar AMM)
            fee_bp = int(pool_record.get("fee_bp", 30))

            # Calculate additional metrics
            volume_24h = await self._calculate_pool_volume(pool_id)
            apy = await self._calculate_pool_apy(pool_id, reserves_a, reserves_b)
            tvl = await self._calculate_pool_tvl(asset_a, asset_b, reserves_a, reserves_b)

            return LiquidityPool(
                id=pool_id,
                asset_a=asset_a,
                asset_b=asset_b,
                reserves_a=reserves_a,
                reserves_b=reserves_b,
                total_shares=total_shares,
                fee_bp=fee_bp,
                amm_type=AMMType.CONSTANT_PRODUCT,
                status=LiquidityPoolStatus.ACTIVE,
                volume_24h=volume_24h,
                apy=apy,
                total_value_locked=tvl,
            )

        except Exception as e:
            self.logger().warning(f"Failed to parse pool record: {e}")
            return None

    async def _calculate_pool_volume(self, pool_id: str) -> Decimal:
        """Calculate 24h trading volume for pool"""
        # Implementation would aggregate trade operations
        # This is a placeholder for real volume calculation
        return Decimal("0")

    async def _calculate_pool_apy(
        self, pool_id: str, reserves_a: Decimal, reserves_b: Decimal
    ) -> Decimal:
        """Calculate annual percentage yield for pool"""
        # Implementation would use historical fee data
        # This is a placeholder for real APY calculation
        return Decimal("0")

    async def _calculate_pool_tvl(
        self, asset_a: Asset, asset_b: Asset, reserves_a: Decimal, reserves_b: Decimal
    ) -> Decimal:
        """Calculate total value locked in pool"""
        # Implementation would fetch asset prices and calculate USD value
        # This is a placeholder for real TVL calculation
        return reserves_a + reserves_b  # Simplified

    async def _start_pool_monitoring(self) -> None:
        """Start background tasks to monitor pool states"""
        for pool_id in self._pools:
            task = safe_ensure_future(self._monitor_pool(pool_id))
            self._pool_update_tasks[pool_id] = task

    async def _monitor_pool(self, pool_id: str) -> None:
        """Monitor individual pool for updates"""
        while True:
            try:
                await asyncio.sleep(10)  # Update every 10 seconds

                # Fetch updated pool data
                pool_response = (
                    await self._server.liquidity_pools().liquidity_pool_id(pool_id).call()
                )
                updated_pool = await self._parse_pool_record(pool_response)

                if updated_pool:
                    self._pools[pool_id] = updated_pool

            except Exception as e:
                self.logger().warning(f"Failed to update pool {pool_id}: {e}")
                await asyncio.sleep(30)  # Longer delay on error

    async def _load_positions(self) -> None:
        """Load user's existing liquidity positions"""
        try:
            # Fetch account's liquidity pool shares
            account_response = (
                await self._server.accounts().account_id(self._source_account.account_id).call()
            )

            for balance in account_response["balances"]:
                if balance["asset_type"] == "liquidity_pool_shares":
                    position = await self._create_position_from_balance(balance)
                    if position:
                        self._positions[position.pool_id] = position

        except Exception as e:
            self.logger().warning(f"Failed to load positions: {e}")

    async def _create_position_from_balance(
        self, balance: Dict[str, Any]
    ) -> Optional[LiquidityPosition]:
        """Create position object from account balance"""
        # Implementation would parse balance and create position
        # This is a placeholder
        return None

    async def get_swap_quote(
        self,
        input_asset: Asset,
        output_asset: Asset,
        input_amount: Decimal,
        max_slippage: Optional[Decimal] = None,
    ) -> Optional[SwapQuote]:
        """Get optimized swap quote with best routing"""
        try:
            slippage = max_slippage or self._max_slippage

            # Find optimal route
            route = await self._find_optimal_route(input_asset, output_asset, input_amount)
            if not route:
                return None

            # Calculate output amount and fees
            output_amount, total_fee, price_impact = await self._calculate_swap_output(
                route, input_asset, output_asset, input_amount
            )

            if output_amount <= 0:
                return None

            # Calculate price and minimum received
            price = output_amount / input_amount
            minimum_received = output_amount * (Decimal("1") - slippage)

            return SwapQuote(
                input_asset=input_asset,
                output_asset=output_asset,
                input_amount=input_amount,
                output_amount=output_amount,
                price=price,
                price_impact=price_impact,
                fee=total_fee,
                slippage=slippage,
                pool_id=route[0] if len(route) == 1 else "multi_hop",
                route=route,
                minimum_received=minimum_received,
                expiry=time.time() + self._quote_expiry_seconds,
            )

        except Exception as e:
            self.logger().error(f"Failed to get swap quote: {e}")
            return None

    async def _find_optimal_route(
        self, input_asset: Asset, output_asset: Asset, input_amount: Decimal
    ) -> List[str]:
        """Find optimal routing path for swap"""
        # Check cache first
        cache_key = f"{input_asset}_{output_asset}_{input_amount}"
        if cache_key in self._route_cache:
            cached_route, cache_time = self._route_cache[cache_key]
            if time.time() - cache_time < self._cache_ttl:
                return cached_route

        # Find direct pool
        direct_pool = self._find_direct_pool(input_asset, output_asset)
        if direct_pool:
            route = [direct_pool.id]
            self._route_cache[cache_key] = (route, time.time())
            return route

        # Find multi-hop route
        multi_hop_route = await self._find_multi_hop_route(input_asset, output_asset)
        if multi_hop_route:
            self._route_cache[cache_key] = (multi_hop_route, time.time())
            return multi_hop_route

        return []

    def _find_direct_pool(self, asset_a: Asset, asset_b: Asset) -> Optional[LiquidityPool]:
        """Find direct pool between two assets"""
        for pool in self._pools.values():
            if (pool.asset_a == asset_a and pool.asset_b == asset_b) or (
                pool.asset_a == asset_b and pool.asset_b == asset_a
            ):
                if pool.status == LiquidityPoolStatus.ACTIVE:
                    return pool
        return None

    async def _find_multi_hop_route(self, input_asset: Asset, output_asset: Asset) -> List[str]:
        """Find multi-hop routing path"""
        # Implementation would use graph algorithms to find optimal path
        # This is a simplified placeholder
        return []

    async def _calculate_swap_output(
        self, route: List[str], input_asset: Asset, output_asset: Asset, input_amount: Decimal
    ) -> Tuple[Decimal, Decimal, Decimal]:
        """Calculate swap output amount, fees, and price impact"""
        if len(route) == 1:
            return await self._calculate_single_hop_output(
                route[0], input_asset, output_asset, input_amount
            )
        else:
            return await self._calculate_multi_hop_output(
                route, input_asset, output_asset, input_amount
            )

    async def _calculate_single_hop_output(
        self, pool_id: str, input_asset: Asset, output_asset: Asset, input_amount: Decimal
    ) -> Tuple[Decimal, Decimal, Decimal]:
        """Calculate output for single hop swap"""
        pool = self._pools[pool_id]

        # Determine input/output reserves
        if pool.asset_a == input_asset:
            input_reserve = pool.reserves_a
            output_reserve = pool.reserves_b
        else:
            input_reserve = pool.reserves_b
            output_reserve = pool.reserves_a

        # Calculate output using constant product formula
        # Output = (input * output_reserve) / (input_reserve + input)
        # With fee: input_after_fee = input * (10000 - fee_bp) / 10000

        input_after_fee = (
            input_amount * (Decimal("10000") - Decimal(str(pool.fee_bp))) / Decimal("10000")
        )
        output_amount = (input_after_fee * output_reserve) / (input_reserve + input_after_fee)

        # Calculate fee
        fee = input_amount - input_after_fee

        # Calculate price impact
        price_before = output_reserve / input_reserve
        price_after = (output_reserve - output_amount) / (input_reserve + input_amount)
        price_impact = abs(price_after - price_before) / price_before

        return output_amount, fee, price_impact

    async def _calculate_multi_hop_output(
        self, route: List[str], input_asset: Asset, output_asset: Asset, input_amount: Decimal
    ) -> Tuple[Decimal, Decimal, Decimal]:
        """Calculate output for multi-hop swap"""
        # Implementation would chain multiple single-hop calculations
        # This is a placeholder
        return Decimal("0"), Decimal("0"), Decimal("0")

    async def execute_swap(self, quote: SwapQuote) -> Optional[str]:
        """Execute swap transaction based on quote"""
        try:
            if quote.is_expired:
                self.logger().warning("Quote expired, cannot execute swap")
                return None

            # MEV protection delay
            if self._enable_mev_protection:
                await self._apply_mev_protection()

            # Build swap transaction
            transaction = await self._build_swap_transaction(quote)
            if not transaction:
                return None

            # Sign and submit transaction
            transaction.sign(self._source_keypair)
            response = await self._server.submit_transaction(transaction)

            # Track transaction
            tx_hash = response["hash"]
            self._pending_transactions.add(tx_hash)

            # Update metrics
            self._swap_metrics[quote.pool_id]["count"] += 1
            self._swap_metrics[quote.pool_id]["volume"] += quote.input_amount

            self.logger().info(f"Swap executed: {tx_hash}")
            return tx_hash

        except Exception as e:
            self.logger().error(f"Failed to execute swap: {e}")
            return None

    async def _apply_mev_protection(self) -> None:
        """Apply MEV protection delay"""
        # Random delay between 1-5 seconds to avoid MEV
        import random

        delay = random.uniform(1.0, 5.0)
        await asyncio.sleep(delay)

    async def _build_swap_transaction(self, quote: SwapQuote) -> Optional[TransactionEnvelope]:
        """Build transaction for swap execution"""
        try:
            # Refresh account
            account_response = (
                await self._server.accounts().account_id(self._source_account.account_id).call()
            )
            account = Account.from_xdr(account_response["id"])

            # Build transaction
            builder = TransactionBuilder(
                source_account=account,
                network=self._network,
                base_fee=10000,  # Higher fee for priority
            )

            if len(quote.route) == 1:
                # Single hop swap
                operation = await self._build_single_hop_operation(quote)
            else:
                # Multi-hop swap
                operation = await self._build_multi_hop_operations(quote)

            if operation:
                if isinstance(operation, list):
                    for op in operation:
                        builder.append_operation(op)
                else:
                    builder.append_operation(operation)

                builder.set_timeout(30)  # 30 second timeout
                return builder.build()

            return None

        except Exception as e:
            self.logger().error(f"Failed to build swap transaction: {e}")
            return None

    async def _build_single_hop_operation(self, quote: SwapQuote) -> Optional[Operation]:
        """Build operation for single hop swap"""
        try:
            # Use PathPaymentStrictSend for swap
            return PathPaymentStrictSend(
                destination=self._source_account.account_id,
                send_asset=quote.input_asset,
                send_amount=str(quote.input_amount),
                dest_asset=quote.output_asset,
                dest_min=str(quote.minimum_received),
            )

        except Exception as e:
            self.logger().error(f"Failed to build single hop operation: {e}")
            return None

    async def _build_multi_hop_operations(self, quote: SwapQuote) -> Optional[List[Operation]]:
        """Build operations for multi-hop swap"""
        # Implementation would build chain of operations
        # This is a placeholder
        return None

    async def add_liquidity(
        self,
        pool_id: str,
        asset_a_amount: Decimal,
        asset_b_amount: Decimal,
        max_slippage: Optional[Decimal] = None,
    ) -> Optional[str]:
        """Add liquidity to pool"""
        try:
            pool = self._pools.get(pool_id)
            if not pool or pool.status != LiquidityPoolStatus.ACTIVE:
                self.logger().warning(f"Pool {pool_id} not available for liquidity addition")
                return None

            slippage = max_slippage or self._max_slippage

            # Calculate expected shares and minimum amounts
            expected_shares, min_a, min_b = await self._calculate_liquidity_amounts(
                pool, asset_a_amount, asset_b_amount, slippage
            )

            # Build and submit transaction
            transaction = await self._build_liquidity_deposit_transaction(
                pool, asset_a_amount, asset_b_amount, min_a, min_b
            )

            if not transaction:
                return None

            transaction.sign(self._source_keypair)
            response = await self._server.submit_transaction(transaction)

            # Track transaction and update position
            tx_hash = response["hash"]
            await self._update_position_after_deposit(
                pool_id, expected_shares, asset_a_amount, asset_b_amount
            )

            # Update metrics
            self._liquidity_metrics[pool_id]["deposits"] += 1

            self.logger().info(f"Liquidity added: {tx_hash}")
            return tx_hash

        except Exception as e:
            self.logger().error(f"Failed to add liquidity: {e}")
            return None

    async def _calculate_liquidity_amounts(
        self, pool: LiquidityPool, amount_a: Decimal, amount_b: Decimal, slippage: Decimal
    ) -> Tuple[Decimal, Decimal, Decimal]:
        """Calculate expected shares and minimum amounts for liquidity addition"""
        # Calculate expected shares based on pool ratios
        share_a = amount_a * pool.total_shares / pool.reserves_a
        share_b = amount_b * pool.total_shares / pool.reserves_b
        expected_shares = min(share_a, share_b)

        # Calculate minimum amounts with slippage
        min_a = amount_a * (Decimal("1") - slippage)
        min_b = amount_b * (Decimal("1") - slippage)

        return expected_shares, min_a, min_b

    async def _build_liquidity_deposit_transaction(
        self,
        pool: LiquidityPool,
        amount_a: Decimal,
        amount_b: Decimal,
        min_a: Decimal,
        min_b: Decimal,
    ) -> Optional[TransactionEnvelope]:
        """Build transaction for liquidity deposit"""
        try:
            # Refresh account
            account_response = (
                await self._server.accounts().account_id(self._source_account.account_id).call()
            )
            account = Account.from_xdr(account_response["id"])

            # Build transaction
            builder = TransactionBuilder(
                source_account=account, network=self._network, base_fee=10000
            )

            # Add liquidity pool deposit operation
            deposit_op = LiquidityPoolDeposit(
                liquidity_pool_id=pool.id,
                max_amount_a=str(amount_a),
                max_amount_b=str(amount_b),
                min_price=Price(int(min_b * 10000000), int(min_a * 10000000)),
                max_price=Price(int(amount_b * 10000000), int(amount_a * 10000000)),
            )

            builder.append_operation(deposit_op)
            builder.set_timeout(30)

            return builder.build()

        except Exception as e:
            self.logger().error(f"Failed to build liquidity deposit transaction: {e}")
            return None

    async def _update_position_after_deposit(
        self, pool_id: str, shares: Decimal, amount_a: Decimal, amount_b: Decimal
    ) -> None:
        """Update position tracking after liquidity deposit"""
        try:
            pool = self._pools[pool_id]

            if pool_id in self._positions:
                # Update existing position
                position = self._positions[pool_id]
                position.shares += shares
                position.asset_a_amount += amount_a
                position.asset_b_amount += amount_b
            else:
                # Create new position
                position = LiquidityPosition(
                    pool_id=pool_id,
                    shares=shares,
                    asset_a_amount=amount_a,
                    asset_b_amount=amount_b,
                    entry_price_a=pool.price_a_to_b,
                    entry_price_b=pool.price_b_to_a,
                    entry_timestamp=time.time(),
                )
                self._positions[pool_id] = position

        except Exception as e:
            self.logger().warning(f"Failed to update position after deposit: {e}")

    async def remove_liquidity(
        self, pool_id: str, shares_amount: Decimal, max_slippage: Optional[Decimal] = None
    ) -> Optional[str]:
        """Remove liquidity from pool"""
        try:
            pool = self._pools.get(pool_id)
            position = self._positions.get(pool_id)

            if not pool or not position:
                self.logger().warning(f"Pool or position not found for {pool_id}")
                return None

            if shares_amount > position.shares:
                self.logger().warning("Insufficient shares for withdrawal")
                return None

            slippage = max_slippage or self._max_slippage

            # Calculate expected amounts and minimums
            expected_a, expected_b, min_a, min_b = await self._calculate_withdrawal_amounts(
                pool, shares_amount, slippage
            )

            # Build and submit transaction
            transaction = await self._build_liquidity_withdrawal_transaction(
                pool, shares_amount, min_a, min_b
            )

            if not transaction:
                return None

            transaction.sign(self._source_keypair)
            response = await self._server.submit_transaction(transaction)

            # Update position
            await self._update_position_after_withdrawal(
                pool_id, shares_amount, expected_a, expected_b
            )

            # Update metrics
            self._liquidity_metrics[pool_id]["withdrawals"] += 1

            tx_hash = response["hash"]
            self.logger().info(f"Liquidity removed: {tx_hash}")
            return tx_hash

        except Exception as e:
            self.logger().error(f"Failed to remove liquidity: {e}")
            return None

    async def _calculate_withdrawal_amounts(
        self, pool: LiquidityPool, shares: Decimal, slippage: Decimal
    ) -> Tuple[Decimal, Decimal, Decimal, Decimal]:
        """Calculate expected and minimum withdrawal amounts"""
        # Calculate expected amounts based on share proportion
        share_percentage = shares / pool.total_shares
        expected_a = pool.reserves_a * share_percentage
        expected_b = pool.reserves_b * share_percentage

        # Calculate minimums with slippage
        min_a = expected_a * (Decimal("1") - slippage)
        min_b = expected_b * (Decimal("1") - slippage)

        return expected_a, expected_b, min_a, min_b

    async def _build_liquidity_withdrawal_transaction(
        self, pool: LiquidityPool, shares: Decimal, min_a: Decimal, min_b: Decimal
    ) -> Optional[TransactionEnvelope]:
        """Build transaction for liquidity withdrawal"""
        try:
            # Refresh account
            account_response = (
                await self._server.accounts().account_id(self._source_account.account_id).call()
            )
            account = Account.from_xdr(account_response["id"])

            # Build transaction
            builder = TransactionBuilder(
                source_account=account, network=self._network, base_fee=10000
            )

            # Add liquidity pool withdraw operation
            withdraw_op = LiquidityPoolWithdraw(
                liquidity_pool_id=pool.id,
                amount=str(shares),
                min_amount_a=str(min_a),
                min_amount_b=str(min_b),
            )

            builder.append_operation(withdraw_op)
            builder.set_timeout(30)

            return builder.build()

        except Exception as e:
            self.logger().error(f"Failed to build liquidity withdrawal transaction: {e}")
            return None

    async def _update_position_after_withdrawal(
        self, pool_id: str, shares: Decimal, amount_a: Decimal, amount_b: Decimal
    ) -> None:
        """Update position tracking after liquidity withdrawal"""
        try:
            position = self._positions[pool_id]

            # Update position
            position.shares -= shares
            position.asset_a_amount -= amount_a
            position.asset_b_amount -= amount_b

            # Remove position if fully withdrawn
            if position.shares <= 0:
                del self._positions[pool_id]

        except Exception as e:
            self.logger().warning(f"Failed to update position after withdrawal: {e}")

    async def get_pool_analytics(self, pool_id: str) -> Dict[str, Any]:
        """Get comprehensive pool analytics"""
        try:
            pool = self._pools.get(pool_id)
            if not pool:
                return {}

            # Calculate various metrics
            analytics = {
                "pool_id": pool_id,
                "assets": [str(pool.asset_a), str(pool.asset_b)],
                "reserves": [float(pool.reserves_a), float(pool.reserves_b)],
                "total_shares": float(pool.total_shares),
                "price_a_to_b": float(pool.price_a_to_b),
                "price_b_to_a": float(pool.price_b_to_a),
                "fee_bp": pool.fee_bp,
                "volume_24h": float(pool.volume_24h),
                "apy": float(pool.apy),
                "total_value_locked": float(pool.total_value_locked),
                "status": pool.status.value,
                "last_updated": pool.last_updated,
                "swap_count": self._swap_metrics[pool_id]["count"],
                "swap_volume": float(self._swap_metrics[pool_id]["volume"]),
                "liquidity_deposits": self._liquidity_metrics[pool_id]["deposits"],
                "liquidity_withdrawals": self._liquidity_metrics[pool_id]["withdrawals"],
            }

            # Add position info if exists
            if pool_id in self._positions:
                position = self._positions[pool_id]
                analytics["position"] = {
                    "shares": float(position.shares),
                    "asset_a_amount": float(position.asset_a_amount),
                    "asset_b_amount": float(position.asset_b_amount),
                    "entry_price_a": float(position.entry_price_a),
                    "entry_price_b": float(position.entry_price_b),
                    "entry_timestamp": position.entry_timestamp,
                    "rewards_earned": float(position.rewards_earned),
                    "impermanent_loss": float(position.impermanent_loss),
                }

            return analytics

        except Exception as e:
            self.logger().error(f"Failed to get pool analytics: {e}")
            return {}

    async def get_all_pools(self) -> List[Dict[str, Any]]:
        """Get information about all available pools"""
        return [await self.get_pool_analytics(pool_id) for pool_id in self._pools.keys()]

    async def get_positions_summary(self) -> Dict[str, Any]:
        """Get summary of all liquidity positions"""
        try:
            total_positions = len(self._positions)
            total_value = Decimal("0")
            total_rewards = Decimal("0")
            total_il = Decimal("0")

            for position in self._positions.values():
                pool = self._pools[position.pool_id]
                # Calculate current value (simplified)
                current_value = (
                    position.asset_a_amount * pool.price_a_to_b + position.asset_b_amount
                )
                total_value += current_value
                total_rewards += position.rewards_earned
                total_il += position.impermanent_loss

            return {
                "total_positions": total_positions,
                "total_value": float(total_value),
                "total_rewards": float(total_rewards),
                "total_impermanent_loss": float(total_il),
                "positions": [
                    {
                        "pool_id": pos.pool_id,
                        "shares": float(pos.shares),
                        "value": float(pos.asset_a_amount + pos.asset_b_amount),  # Simplified
                        "rewards": float(pos.rewards_earned),
                        "il": float(pos.impermanent_loss),
                    }
                    for pos in self._positions.values()
                ],
            }

        except Exception as e:
            self.logger().error(f"Failed to get positions summary: {e}")
            return {}

    async def shutdown(self) -> None:
        """Shutdown AMM integration and cleanup resources"""
        try:
            # Cancel all monitoring tasks
            for task in self._pool_update_tasks.values():
                task.cancel()

            # Wait for tasks to complete
            if self._pool_update_tasks:
                await asyncio.gather(*self._pool_update_tasks.values(), return_exceptions=True)

            # Clear data structures
            self._pools.clear()
            self._positions.clear()
            self._route_cache.clear()
            self._price_cache.clear()

            self.logger().info("AMM integration shutdown complete")

        except Exception as e:
            self.logger().error(f"Error during AMM shutdown: {e}")
