"""
Stellar Yield Farming Module

This module provides comprehensive yield farming strategies for Stellar DeFi protocols,
including liquidity mining, staking rewards, and automated yield optimization.

Author: Hummingbot
"""

import asyncio
import logging
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from stellar_sdk import (
    Account,
    Asset,
    Keypair,
    Network,
    Operation,
    Server,
    TransactionBuilder,
    TransactionEnvelope,
)
from stellar_sdk.exceptions import BadRequestError, BaseRequestError

from hummingbot.core.data_type.common import TradeType
from hummingbot.core.utils.async_utils import safe_ensure_future
from hummingbot.logger import HummingbotLogger

from ...stellar_amm_integration import LiquidityPool, LiquidityPosition, StellarAMMIntegration


class YieldStrategy(Enum):
    """Available yield farming strategies"""

    LIQUIDITY_MINING = "liquidity_mining"
    STAKING_REWARDS = "staking_rewards"
    LENDING_PROTOCOL = "lending_protocol"
    GOVERNANCE_REWARDS = "governance_rewards"
    COMPOUND_FARMING = "compound_farming"
    ARBITRAGE_FARMING = "arbitrage_farming"


class FarmStatus(Enum):
    """Yield farm operational status"""

    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    EMERGENCY_STOP = "emergency_stop"


@dataclass
class YieldFarm:
    """Represents a yield farming opportunity"""

    id: str
    name: str
    strategy: YieldStrategy
    status: FarmStatus
    underlying_assets: List[Asset]
    reward_assets: List[Asset]
    apy: Decimal
    tvl: Decimal
    minimum_deposit: Decimal
    lock_period: int  # seconds
    compound_frequency: int  # seconds between compounds
    risk_score: Decimal  # 0-10 risk rating
    auto_compound: bool
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    total_rewards_distributed: Decimal = field(default=Decimal("0"))
    participant_count: int = field(default=0)

    @property
    def daily_apy(self) -> Decimal:
        """Daily APY calculation"""
        return self.apy / Decimal("365")

    @property
    def is_active(self) -> bool:
        """Check if farm is currently active"""
        return self.status == FarmStatus.ACTIVE


@dataclass
class YieldPosition:
    """User's yield farming position"""

    farm_id: str
    deposited_amount: Decimal
    deposited_assets: Dict[str, Decimal]
    entry_timestamp: float
    last_compound_timestamp: float
    accumulated_rewards: Dict[str, Decimal]
    pending_rewards: Dict[str, Decimal]
    total_value: Decimal
    roi: Decimal = field(default=Decimal("0"))
    days_active: int = field(default=0)
    compound_count: int = field(default=0)

    @property
    def current_roi(self) -> Decimal:
        """Calculate current ROI percentage"""
        if self.deposited_amount == 0:
            return Decimal("0")
        return (self.total_value - self.deposited_amount) / self.deposited_amount * Decimal("100")

    @property
    def days_since_entry(self) -> int:
        """Days since position was opened"""
        return int((time.time() - self.entry_timestamp) / 86400)


@dataclass
class YieldOpportunity:
    """Represents a yield opportunity analysis"""

    farm_id: str
    expected_apy: Decimal
    expected_daily_rewards: Dict[str, Decimal]
    risk_adjusted_apy: Decimal
    optimal_allocation: Decimal
    compound_strategy: str
    time_to_breakeven: int  # days
    confidence_score: Decimal  # 0-1
    market_conditions: Dict[str, Any]


class StellarYieldFarming:
    """
    Comprehensive yield farming system for Stellar DeFi:
    - Multi-strategy yield optimization
    - Automated compounding
    - Risk-adjusted portfolio allocation
    - Real-time opportunity scanning
    - Gas optimization for compound operations
    """

    _logger: Optional[HummingbotLogger] = None

    def __init__(
        self,
        server: Server,
        network: Network,
        source_account: Account,
        source_keypair: Keypair,
        amm_integration: StellarAMMIntegration,
        auto_compound: bool = True,
        compound_threshold: Decimal = Decimal("1.0"),  # Min rewards to compound
        max_risk_score: Decimal = Decimal("7.0"),  # Max risk tolerance
        rebalance_frequency: int = 3600,  # Rebalance every hour
    ):
        self._server = server
        self._network = network
        self._source_account = source_account
        self._source_keypair = source_keypair
        self._amm_integration = amm_integration
        self._auto_compound = auto_compound
        self._compound_threshold = compound_threshold
        self._max_risk_score = max_risk_score
        self._rebalance_frequency = rebalance_frequency

        # Farm management
        self._farms: Dict[str, YieldFarm] = {}
        self._positions: Dict[str, YieldPosition] = {}
        self._opportunities: Dict[str, YieldOpportunity] = {}

        # Background tasks
        self._monitoring_tasks: Dict[str, asyncio.Task[None]] = {}
        self._compound_task: Optional[asyncio.Task[None]] = None
        self._opportunity_scanner_task: Optional[asyncio.Task[None]] = None

        # Performance tracking
        self._total_rewards_earned: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        self._compound_gas_spent: Decimal = Decimal("0")
        self._rebalance_history: List[Dict] = []

        # Strategy configuration
        self._strategy_weights = {
            YieldStrategy.LIQUIDITY_MINING: Decimal("0.4"),
            YieldStrategy.STAKING_REWARDS: Decimal("0.3"),
            YieldStrategy.LENDING_PROTOCOL: Decimal("0.2"),
            YieldStrategy.GOVERNANCE_REWARDS: Decimal("0.1"),
        }

        # Risk management
        self._max_allocation_per_farm = Decimal("0.25")  # 25% max per farm
        self._emergency_exit_loss_threshold = Decimal("0.1")  # 10% loss triggers exit

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._logger is None:
            cls._logger = logging.getLogger(__name__)
        return cls._logger

    async def initialize(self) -> None:
        """Initialize yield farming system"""
        try:
            self.logger().info("Initializing Stellar yield farming system...")

            # Discover available farms
            await self._discover_farms()

            # Load existing positions
            await self._load_positions()

            # Start background services
            await self._start_monitoring()
            await self._start_opportunity_scanner()

            if self._auto_compound:
                await self._start_auto_compound()

            self.logger().info(
                f"Yield farming initialized with {len(self._farms)} farms and {len(self._positions)} positions"
            )

        except Exception as e:
            self.logger().error(f"Failed to initialize yield farming: {e}")
            raise

    async def _discover_farms(self) -> None:
        """Discover available yield farming opportunities"""
        try:
            # Discover liquidity mining farms from AMM pools
            await self._discover_liquidity_mining_farms()

            # Discover staking opportunities
            await self._discover_staking_farms()

            # Discover lending protocol opportunities
            await self._discover_lending_farms()

            # Discover governance reward opportunities
            await self._discover_governance_farms()

        except Exception as e:
            self.logger().error(f"Failed to discover farms: {e}")
            raise

    async def _discover_liquidity_mining_farms(self) -> None:
        """Discover liquidity mining opportunities from AMM pools"""
        try:
            pools = await self._amm_integration.get_all_pools()

            for pool_data in pools:
                # Create yield farm for each high-APY pool
                if pool_data.get("apy", 0) > 5.0:  # 5% minimum APY
                    farm = YieldFarm(
                        id=f"lm_{pool_data['pool_id']}",
                        name=f"Liquidity Mining - {'/'.join(pool_data['assets'])}",
                        strategy=YieldStrategy.LIQUIDITY_MINING,
                        status=FarmStatus.ACTIVE,
                        underlying_assets=[
                            # Parse assets from pool data
                            (
                                Asset.native()
                                if asset == "native"
                                else Asset(asset.split(":")[0], asset.split(":")[1])
                            )
                            for asset in pool_data["assets"]
                        ],
                        reward_assets=[Asset.native()],  # Assume native token rewards
                        apy=Decimal(str(pool_data["apy"])),
                        tvl=Decimal(str(pool_data["total_value_locked"])),
                        minimum_deposit=Decimal("10"),  # $10 minimum
                        lock_period=0,  # No lock for LP
                        compound_frequency=3600,  # Compound hourly
                        risk_score=Decimal("5.0"),  # Medium risk
                        auto_compound=True,
                    )
                    self._farms[farm.id] = farm

        except Exception as e:
            self.logger().warning(f"Failed to discover liquidity mining farms: {e}")

    async def _discover_staking_farms(self) -> None:
        """Discover native asset staking opportunities"""
        try:
            # Example: Native XLM staking (if available)
            staking_farm = YieldFarm(
                id="stake_xlm_native",
                name="XLM Native Staking",
                strategy=YieldStrategy.STAKING_REWARDS,
                status=FarmStatus.ACTIVE,
                underlying_assets=[Asset.native()],
                reward_assets=[Asset.native()],
                apy=Decimal("4.5"),  # Example APY
                tvl=Decimal("1000000"),  # Example TVL
                minimum_deposit=Decimal("100"),  # 100 XLM minimum
                lock_period=7 * 24 * 3600,  # 7 day lock
                compound_frequency=24 * 3600,  # Compound daily
                risk_score=Decimal("2.0"),  # Low risk
                auto_compound=True,
            )
            self._farms[staking_farm.id] = staking_farm

        except Exception as e:
            self.logger().warning(f"Failed to discover staking farms: {e}")

    async def _discover_lending_farms(self) -> None:
        """Discover lending protocol yield opportunities"""
        try:
            # Example lending farm (hypothetical Stellar lending protocol)
            lending_farm = YieldFarm(
                id="lend_xlm_protocol",
                name="XLM Lending Protocol",
                strategy=YieldStrategy.LENDING_PROTOCOL,
                status=FarmStatus.ACTIVE,
                underlying_assets=[Asset.native()],
                reward_assets=[Asset.native()],
                apy=Decimal("6.8"),  # Example lending APY
                tvl=Decimal("500000"),
                minimum_deposit=Decimal("50"),
                lock_period=0,  # No lock for lending
                compound_frequency=6 * 3600,  # Compound every 6 hours
                risk_score=Decimal("4.0"),  # Medium-low risk
                auto_compound=True,
            )
            self._farms[lending_farm.id] = lending_farm

        except Exception as e:
            self.logger().warning(f"Failed to discover lending farms: {e}")

    async def _discover_governance_farms(self) -> None:
        """Discover governance participation rewards"""
        try:
            # Example governance farm
            governance_farm = YieldFarm(
                id="gov_stellar_voting",
                name="Stellar Governance Rewards",
                strategy=YieldStrategy.GOVERNANCE_REWARDS,
                status=FarmStatus.ACTIVE,
                underlying_assets=[Asset.native()],
                reward_assets=[Asset.native()],
                apy=Decimal("3.2"),  # Lower APY but low risk
                tvl=Decimal("2000000"),
                minimum_deposit=Decimal("1000"),  # Higher minimum for governance
                lock_period=30 * 24 * 3600,  # 30 day lock
                compound_frequency=7 * 24 * 3600,  # Compound weekly
                risk_score=Decimal("1.5"),  # Very low risk
                auto_compound=True,
            )
            self._farms[governance_farm.id] = governance_farm

        except Exception as e:
            self.logger().warning(f"Failed to discover governance farms: {e}")

    async def _load_positions(self) -> None:
        """Load existing yield farming positions"""
        try:
            # Load positions from account state
            # This is a placeholder - real implementation would parse account data
            pass

        except Exception as e:
            self.logger().warning(f"Failed to load positions: {e}")

    async def _start_monitoring(self) -> None:
        """Start monitoring tasks for all farms"""
        for farm_id in self._farms:
            task = safe_ensure_future(self._monitor_farm(farm_id))
            self._monitoring_tasks[farm_id] = task

    async def _monitor_farm(self, farm_id: str) -> None:
        """Monitor individual farm for updates"""
        while True:
            try:
                await asyncio.sleep(60)  # Monitor every minute

                farm = self._farms.get(farm_id)
                if not farm:
                    break

                # Update farm metrics
                await self._update_farm_metrics(farm)

                # Check for rebalancing opportunities
                await self._check_rebalancing_opportunity(farm_id)

                # Update yield opportunities
                await self._update_yield_opportunity(farm_id)

            except Exception as e:
                self.logger().warning(f"Error monitoring farm {farm_id}: {e}")
                await asyncio.sleep(300)  # Longer delay on error

    async def _update_farm_metrics(self, farm: YieldFarm) -> None:
        """Update farm metrics from on-chain data"""
        try:
            if farm.strategy == YieldStrategy.LIQUIDITY_MINING:
                # Update from AMM pool data
                pool_id = farm.id.replace("lm_", "")
                pool_analytics = await self._amm_integration.get_pool_analytics(pool_id)

                if pool_analytics:
                    farm.apy = Decimal(str(pool_analytics.get("apy", 0)))
                    farm.tvl = Decimal(str(pool_analytics.get("total_value_locked", 0)))
                    farm.last_updated = time.time()

            # Update other farm types based on their data sources
            # This would involve calling their respective APIs/contracts

        except Exception as e:
            self.logger().warning(f"Failed to update farm metrics: {e}")

    async def _check_rebalancing_opportunity(self, farm_id: str) -> None:
        """Check if rebalancing is needed for better yields"""
        try:
            if farm_id not in self._positions:
                return

            position = self._positions[farm_id]
            farm = self._farms[farm_id]

            # Simple rebalancing logic based on APY changes
            current_apy = farm.apy

            # Look for better opportunities
            better_farms = [
                f
                for f in self._farms.values()
                if (
                    f.apy > current_apy * Decimal("1.1")  # 10% better APY
                    and f.risk_score <= self._max_risk_score
                    and f.is_active
                )
            ]

            if better_farms and len(self._rebalance_history) == 0:  # Avoid frequent rebalancing
                best_farm = max(better_farms, key=lambda x: x.apy)
                await self._propose_rebalance(position, farm, best_farm)

        except Exception as e:
            self.logger().warning(f"Error checking rebalancing for {farm_id}: {e}")

    async def _propose_rebalance(
        self, position: YieldPosition, current_farm: YieldFarm, target_farm: YieldFarm
    ) -> None:
        """Propose a rebalancing operation"""
        try:
            rebalance_proposal = {
                "from_farm": current_farm.id,
                "to_farm": target_farm.id,
                "amount": position.deposited_amount,
                "current_apy": float(current_farm.apy),
                "target_apy": float(target_farm.apy),
                "expected_improvement": float(
                    (target_farm.apy - current_farm.apy) / current_farm.apy * 100
                ),
                "timestamp": time.time(),
            }

            # For now, just log the proposal
            # In a production system, this might queue the rebalance or notify the user
            self.logger().info(f"Rebalance opportunity: {rebalance_proposal}")

        except Exception as e:
            self.logger().warning(f"Error proposing rebalance: {e}")

    async def _update_yield_opportunity(self, farm_id: str) -> None:
        """Update yield opportunity analysis"""
        try:
            farm = self._farms[farm_id]

            # Calculate risk-adjusted APY
            risk_adjusted_apy = farm.apy * (Decimal("10") - farm.risk_score) / Decimal("10")

            # Calculate optimal allocation based on Kelly criterion
            optimal_allocation = await self._calculate_optimal_allocation(farm)

            # Estimate daily rewards
            daily_rewards = {}
            for asset in farm.reward_assets:
                daily_reward = optimal_allocation * farm.daily_apy / len(farm.reward_assets)
                daily_rewards[str(asset)] = daily_reward

            opportunity = YieldOpportunity(
                farm_id=farm_id,
                expected_apy=farm.apy,
                expected_daily_rewards=daily_rewards,
                risk_adjusted_apy=risk_adjusted_apy,
                optimal_allocation=optimal_allocation,
                compound_strategy="auto" if farm.auto_compound else "manual",
                time_to_breakeven=await self._calculate_breakeven_time(farm),
                confidence_score=await self._calculate_confidence_score(farm),
                market_conditions=await self._analyze_market_conditions(farm),
            )

            self._opportunities[farm_id] = opportunity

        except Exception as e:
            self.logger().warning(f"Error updating opportunity for {farm_id}: {e}")

    async def _calculate_optimal_allocation(self, farm: YieldFarm) -> Decimal:
        """Calculate optimal allocation using portfolio theory"""
        try:
            # Simple allocation based on risk-adjusted returns
            # In production, this would use more sophisticated portfolio optimization

            if farm.risk_score > self._max_risk_score:
                return Decimal("0")

            # Base allocation on APY and inverse risk
            base_allocation = farm.apy / Decimal("100")  # Convert percentage
            risk_adjustment = (Decimal("10") - farm.risk_score) / Decimal("10")

            optimal = base_allocation * risk_adjustment * self._max_allocation_per_farm
            return min(optimal, self._max_allocation_per_farm)

        except Exception as e:
            self.logger().warning(f"Error calculating optimal allocation: {e}")
            return Decimal("0")

    async def _calculate_breakeven_time(self, farm: YieldFarm) -> int:
        """Calculate time to break even on gas costs"""
        try:
            # Estimate gas costs for entry/exit
            estimated_gas = Decimal("0.1")  # Example: 0.1 XLM for transactions

            # Calculate daily earnings needed to break even
            daily_earnings = farm.daily_apy * self._max_allocation_per_farm

            if daily_earnings > 0:
                breakeven_days = int(estimated_gas / daily_earnings)
                return max(1, breakeven_days)  # At least 1 day

            return 999  # Very high if no earnings

        except Exception as e:
            self.logger().warning(f"Error calculating breakeven time: {e}")
            return 999

    async def _calculate_confidence_score(self, farm: YieldFarm) -> Decimal:
        """Calculate confidence score for yield prediction"""
        try:
            score = Decimal("0.5")  # Base score

            # Increase confidence for:
            # - Higher TVL (more liquidity)
            # - Longer time active
            # - Lower volatility

            if farm.tvl > Decimal("100000"):
                score += Decimal("0.2")
            if farm.tvl > Decimal("1000000"):
                score += Decimal("0.1")

            # Age factor (longer running = more confident)
            age_days = (time.time() - farm.created_at) / 86400
            if age_days > 30:
                score += Decimal("0.1")
            if age_days > 90:
                score += Decimal("0.1")

            return min(score, Decimal("1.0"))

        except Exception as e:
            self.logger().warning(f"Error calculating confidence score: {e}")
            return Decimal("0.5")

    async def _analyze_market_conditions(self, farm: YieldFarm) -> Dict[str, Any]:
        """Analyze current market conditions affecting yield"""
        try:
            conditions = {
                "market_trend": "neutral",
                "volatility": "medium",
                "liquidity": "good",
                "competition": "medium",
            }

            # Analyze based on TVL changes, volume, etc.
            if farm.tvl > Decimal("1000000"):
                conditions["liquidity"] = "excellent"
            elif farm.tvl < Decimal("50000"):
                conditions["liquidity"] = "poor"

            # Add more sophisticated market analysis here

            return conditions

        except Exception as e:
            self.logger().warning(f"Error analyzing market conditions: {e}")
            return {"market_trend": "unknown"}

    async def _start_opportunity_scanner(self) -> None:
        """Start background task to scan for new opportunities"""
        self._opportunity_scanner_task = safe_ensure_future(self._scan_opportunities())

    async def _scan_opportunities(self) -> None:
        """Continuously scan for new yield opportunities"""
        while True:
            try:
                await asyncio.sleep(self._rebalance_frequency)

                # Re-discover farms to find new opportunities
                await self._discover_farms()

                # Analyze all opportunities
                for farm_id in self._farms:
                    await self._update_yield_opportunity(farm_id)

                # Log best opportunities
                best_opportunities = await self.get_best_opportunities(limit=5)
                if best_opportunities:
                    self.logger().info(
                        f"Top yield opportunities: {[op['farm_id'] for op in best_opportunities]}"
                    )

            except Exception as e:
                self.logger().warning(f"Error in opportunity scanner: {e}")
                await asyncio.sleep(300)  # Longer delay on error

    async def _start_auto_compound(self) -> None:
        """Start automatic compounding task"""
        self._compound_task = safe_ensure_future(self._auto_compound_loop())

    async def _auto_compound_loop(self) -> None:
        """Main auto-compound loop"""
        while True:
            try:
                await asyncio.sleep(1800)  # Check every 30 minutes

                for position_id in self._positions:
                    await self._check_and_compound(position_id)

            except Exception as e:
                self.logger().warning(f"Error in auto-compound loop: {e}")
                await asyncio.sleep(900)  # 15 minute delay on error

    async def _check_and_compound(self, position_id: str) -> None:
        """Check if position should be compounded"""
        try:
            position = self._positions[position_id]
            farm = self._farms[position.farm_id]

            # Check if enough rewards accumulated
            total_pending = sum(position.pending_rewards.values())

            if (
                total_pending >= self._compound_threshold
                and time.time() - position.last_compound_timestamp >= farm.compound_frequency
            ):

                success = await self.compound_position(position.farm_id)
                if success:
                    self.logger().info(f"Auto-compounded position {position_id}")

        except Exception as e:
            self.logger().warning(f"Error checking compound for {position_id}: {e}")

    async def enter_farm(
        self, farm_id: str, amount: Decimal, assets: Optional[Dict[str, Decimal]] = None
    ) -> Optional[str]:
        """Enter a yield farm with specified amount"""
        try:
            farm = self._farms.get(farm_id)
            if not farm or not farm.is_active:
                self.logger().warning(f"Farm {farm_id} not available")
                return None

            if amount < farm.minimum_deposit:
                self.logger().warning(f"Amount {amount} below minimum {farm.minimum_deposit}")
                return None

            # Build transaction based on strategy
            transaction = await self._build_farm_entry_transaction(farm, amount, assets)
            if not transaction:
                return None

            # Sign and submit
            transaction.sign(self._source_keypair)
            response = await self._server.submit_transaction(transaction)

            # Create position tracking
            await self._create_position(farm_id, amount, assets or {})

            tx_hash = response["hash"]
            self.logger().info(f"Entered farm {farm_id}: {tx_hash}")
            return tx_hash

        except Exception as e:
            self.logger().error(f"Failed to enter farm {farm_id}: {e}")
            return None

    async def _build_farm_entry_transaction(
        self, farm: YieldFarm, amount: Decimal, assets: Dict[str, Decimal]
    ) -> Optional[TransactionEnvelope]:
        """Build transaction for farm entry"""
        try:
            # Refresh account
            account_response = (
                await self._server.accounts().account_id(self._source_account.account_id).call()
            )
            account = Account.from_xdr(account_response["id"])

            builder = TransactionBuilder(
                source_account=account, network=self._network, base_fee=10000
            )

            if farm.strategy == YieldStrategy.LIQUIDITY_MINING:
                # Add liquidity to pool
                pool_id = farm.id.replace("lm_", "")
                asset_a_amount = assets.get(str(farm.underlying_assets[0]), amount / 2)
                asset_b_amount = assets.get(str(farm.underlying_assets[1]), amount / 2)

                # Use AMM integration to add liquidity
                tx_hash = await self._amm_integration.add_liquidity(
                    pool_id, asset_a_amount, asset_b_amount
                )
                if tx_hash:
                    return None  # Transaction already submitted by AMM integration

            elif farm.strategy == YieldStrategy.STAKING_REWARDS:
                # Create staking operation (placeholder)
                # Real implementation would create appropriate staking operation
                pass

            elif farm.strategy == YieldStrategy.LENDING_PROTOCOL:
                # Create lending operation (placeholder)
                # Real implementation would interact with lending protocol
                pass

            # For other strategies, implement specific operations
            builder.set_timeout(30)
            return builder.build()

        except Exception as e:
            self.logger().error(f"Failed to build farm entry transaction: {e}")
            return None

    async def _create_position(
        self, farm_id: str, amount: Decimal, assets: Dict[str, Decimal]
    ) -> None:
        """Create position tracking"""
        try:
            position = YieldPosition(
                farm_id=farm_id,
                deposited_amount=amount,
                deposited_assets=assets,
                entry_timestamp=time.time(),
                last_compound_timestamp=time.time(),
                accumulated_rewards=defaultdict(lambda: Decimal("0")),
                pending_rewards=defaultdict(lambda: Decimal("0")),
                total_value=amount,
            )

            self._positions[farm_id] = position

        except Exception as e:
            self.logger().warning(f"Failed to create position: {e}")

    async def exit_farm(self, farm_id: str, amount: Optional[Decimal] = None) -> Optional[str]:
        """Exit yield farm position"""
        try:
            position = self._positions.get(farm_id)
            farm = self._farms.get(farm_id)

            if not position or not farm:
                self.logger().warning(f"Position or farm {farm_id} not found")
                return None

            # Default to full exit
            exit_amount = amount or position.deposited_amount

            if exit_amount > position.deposited_amount:
                self.logger().warning("Exit amount exceeds position size")
                return None

            # Build exit transaction
            transaction = await self._build_farm_exit_transaction(farm, position, exit_amount)
            if not transaction:
                return None

            # Sign and submit
            transaction.sign(self._source_keypair)
            response = await self._server.submit_transaction(transaction)

            # Update position
            await self._update_position_after_exit(farm_id, exit_amount)

            tx_hash = response["hash"]
            self.logger().info(f"Exited farm {farm_id}: {tx_hash}")
            return tx_hash

        except Exception as e:
            self.logger().error(f"Failed to exit farm {farm_id}: {e}")
            return None

    async def _build_farm_exit_transaction(
        self, farm: YieldFarm, position: YieldPosition, amount: Decimal
    ) -> Optional[TransactionEnvelope]:
        """Build transaction for farm exit"""
        try:
            # Implementation would build appropriate exit transaction
            # based on farm strategy

            if farm.strategy == YieldStrategy.LIQUIDITY_MINING:
                # Remove liquidity from pool
                pool_id = farm.id.replace("lm_", "")
                shares_to_remove = amount  # Simplified

                tx_hash = await self._amm_integration.remove_liquidity(pool_id, shares_to_remove)
                if tx_hash:
                    return None  # Transaction already submitted

            # Build transaction for other strategies
            account_response = (
                await self._server.accounts().account_id(self._source_account.account_id).call()
            )
            account = Account.from_xdr(account_response["id"])

            builder = TransactionBuilder(
                source_account=account, network=self._network, base_fee=10000
            )

            # Add strategy-specific exit operations
            builder.set_timeout(30)
            return builder.build()

        except Exception as e:
            self.logger().error(f"Failed to build farm exit transaction: {e}")
            return None

    async def _update_position_after_exit(self, farm_id: str, exit_amount: Decimal) -> None:
        """Update position after partial or full exit"""
        try:
            position = self._positions[farm_id]

            # Calculate exit ratio
            exit_ratio = exit_amount / position.deposited_amount

            # Update position
            position.deposited_amount -= exit_amount
            position.total_value -= exit_amount  # Simplified

            # Update deposited assets proportionally
            for asset, amount in position.deposited_assets.items():
                position.deposited_assets[asset] = amount * (Decimal("1") - exit_ratio)

            # Remove position if fully exited
            if position.deposited_amount <= 0:
                del self._positions[farm_id]

        except Exception as e:
            self.logger().warning(f"Failed to update position after exit: {e}")

    async def compound_position(self, farm_id: str) -> bool:
        """Compound rewards for a position"""
        try:
            position = self._positions.get(farm_id)
            farm = self._farms.get(farm_id)

            if not position or not farm:
                return False

            # Check if compounding is beneficial
            total_pending = sum(position.pending_rewards.values())
            if total_pending < self._compound_threshold:
                return False

            # Build compound transaction
            transaction = await self._build_compound_transaction(farm, position)
            if not transaction:
                return False

            # Sign and submit
            transaction.sign(self._source_keypair)
            response = await self._server.submit_transaction(transaction)

            # Update position
            await self._update_position_after_compound(farm_id, total_pending)

            self.logger().info(f"Compounded position {farm_id}: {response['hash']}")
            return True

        except Exception as e:
            self.logger().error(f"Failed to compound position {farm_id}: {e}")
            return False

    async def _build_compound_transaction(
        self, farm: YieldFarm, position: YieldPosition
    ) -> Optional[TransactionEnvelope]:
        """Build transaction for compounding rewards"""
        try:
            # Implementation would build compound transaction based on strategy
            # This is a placeholder for the actual compound logic

            account_response = (
                await self._server.accounts().account_id(self._source_account.account_id).call()
            )
            account = Account.from_xdr(account_response["id"])

            builder = TransactionBuilder(
                source_account=account, network=self._network, base_fee=10000
            )

            # Add strategy-specific compound operations
            # For liquidity mining: claim rewards and add to pool
            # For staking: claim and re-stake
            # etc.

            builder.set_timeout(30)
            return builder.build()

        except Exception as e:
            self.logger().error(f"Failed to build compound transaction: {e}")
            return None

    async def _update_position_after_compound(
        self, farm_id: str, compounded_amount: Decimal
    ) -> None:
        """Update position after compounding"""
        try:
            position = self._positions[farm_id]

            # Move pending rewards to accumulated
            for asset, amount in position.pending_rewards.items():
                position.accumulated_rewards[asset] += amount
                position.pending_rewards[asset] = Decimal("0")

            # Update position metrics
            position.deposited_amount += compounded_amount
            position.total_value += compounded_amount
            position.last_compound_timestamp = time.time()
            position.compound_count += 1

            # Track total rewards
            self._total_rewards_earned[farm_id] += compounded_amount

        except Exception as e:
            self.logger().warning(f"Failed to update position after compound: {e}")

    async def get_best_opportunities(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get best yield opportunities ranked by risk-adjusted returns"""
        try:
            opportunities = []

            for opportunity in self._opportunities.values():
                if opportunity.risk_adjusted_apy > 0:
                    opportunities.append(
                        {
                            "farm_id": opportunity.farm_id,
                            "expected_apy": float(opportunity.expected_apy),
                            "risk_adjusted_apy": float(opportunity.risk_adjusted_apy),
                            "optimal_allocation": float(opportunity.optimal_allocation),
                            "confidence_score": float(opportunity.confidence_score),
                            "time_to_breakeven": opportunity.time_to_breakeven,
                            "strategy": self._farms[opportunity.farm_id].strategy.value,
                            "risk_score": float(self._farms[opportunity.farm_id].risk_score),
                        }
                    )

            # Sort by risk-adjusted APY
            opportunities.sort(key=lambda x: x["risk_adjusted_apy"], reverse=True)
            return opportunities[:limit]

        except Exception as e:
            self.logger().error(f"Failed to get best opportunities: {e}")
            return []

    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary"""
        try:
            total_value = Decimal("0")
            total_rewards = Decimal("0")
            total_roi = Decimal("0")
            active_positions = len(self._positions)

            positions_summary = []

            for position in self._positions.values():
                farm = self._farms[position.farm_id]
                position_value = position.total_value
                position_rewards = sum(position.accumulated_rewards.values())

                total_value += position_value
                total_rewards += position_rewards

                positions_summary.append(
                    {
                        "farm_id": position.farm_id,
                        "farm_name": farm.name,
                        "strategy": farm.strategy.value,
                        "deposited": float(position.deposited_amount),
                        "current_value": float(position_value),
                        "rewards": float(position_rewards),
                        "roi": float(position.current_roi),
                        "days_active": position.days_since_entry,
                        "compound_count": position.compound_count,
                        "apy": float(farm.apy),
                    }
                )

            if active_positions > 0:
                total_roi = (
                    (total_value - sum(p.deposited_amount for p in self._positions.values()))
                    / sum(p.deposited_amount for p in self._positions.values())
                    * 100
                )

            return {
                "total_portfolio_value": float(total_value),
                "total_rewards_earned": float(total_rewards),
                "overall_roi": float(total_roi),
                "active_positions": active_positions,
                "compound_gas_spent": float(self._compound_gas_spent),
                "positions": positions_summary,
                "strategy_allocation": {
                    strategy.value: sum(
                        p.deposited_amount
                        for p in self._positions.values()
                        if self._farms[p.farm_id].strategy == strategy
                    )
                    for strategy in YieldStrategy
                },
                "last_updated": time.time(),
            }

        except Exception as e:
            self.logger().error(f"Failed to get portfolio summary: {e}")
            return {}

    async def optimize_portfolio(self) -> Dict[str, Any]:
        """Optimize current portfolio allocation"""
        try:
            # Get current portfolio
            current_summary = await self.get_portfolio_summary()

            # Get best opportunities
            opportunities = await self.get_best_opportunities(limit=20)

            # Calculate optimal allocation using Modern Portfolio Theory concepts
            optimal_allocation = {}
            total_capital = current_summary["total_portfolio_value"]

            for opportunity in opportunities:
                if opportunity["risk_adjusted_apy"] > 5.0:  # Minimum threshold
                    optimal_allocation[opportunity["farm_id"]] = min(
                        opportunity["optimal_allocation"] * total_capital,
                        total_capital * self._max_allocation_per_farm,
                    )

            # Generate rebalancing recommendations
            recommendations = []

            for farm_id, optimal_amount in optimal_allocation.items():
                current_position = self._positions.get(farm_id)
                current_amount = (
                    current_position.deposited_amount if current_position else Decimal("0")
                )

                difference = optimal_amount - current_amount

                if abs(difference) > Decimal("10"):  # Minimum rebalance threshold
                    recommendations.append(
                        {
                            "farm_id": farm_id,
                            "action": "increase" if difference > 0 else "decrease",
                            "current_amount": float(current_amount),
                            "optimal_amount": float(optimal_amount),
                            "difference": float(difference),
                            "expected_apy_improvement": 0,  # Calculate based on current vs optimal
                        }
                    )

            return {
                "current_allocation": {
                    pos.farm_id: float(pos.deposited_amount) for pos in self._positions.values()
                },
                "optimal_allocation": {k: float(v) for k, v in optimal_allocation.items()},
                "rebalancing_recommendations": recommendations,
                "expected_improvement": len(recommendations) * 2.5,  # Simplified
                "optimization_timestamp": time.time(),
            }

        except Exception as e:
            self.logger().error(f"Failed to optimize portfolio: {e}")
            return {}

    async def shutdown(self) -> None:
        """Shutdown yield farming system"""
        try:
            # Cancel all tasks
            tasks_to_cancel = []
            tasks_to_cancel.extend(self._monitoring_tasks.values())

            if self._compound_task:
                tasks_to_cancel.append(self._compound_task)

            if self._opportunity_scanner_task:
                tasks_to_cancel.append(self._opportunity_scanner_task)

            for task in tasks_to_cancel:
                task.cancel()

            # Wait for tasks to complete
            if tasks_to_cancel:
                await asyncio.gather(*tasks_to_cancel, return_exceptions=True)

            # Clear data
            self._farms.clear()
            self._positions.clear()
            self._opportunities.clear()

            self.logger().info("Yield farming system shutdown complete")

        except Exception as e:
            self.logger().error(f"Error during yield farming shutdown: {e}")
