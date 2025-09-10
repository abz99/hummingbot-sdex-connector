"""
Stellar Liquidity Management System

This module provides comprehensive liquidity management for Stellar trading operations,
including inventory management, liquidity provision strategies, and cross-market optimization.

Author: Hummingbot
"""

import asyncio
import logging
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from stellar_sdk import (
    Account,
    Asset,
    Keypair,
    Network,
    Operation,
    Price,
    Server,
    TransactionBuilder,
    TransactionEnvelope,
)
from stellar_sdk.exceptions import BadRequestError, RequestException

from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.core.data_type.order_book import OrderBook
from hummingbot.core.utils.async_utils import safe_ensure_future
from hummingbot.logger import HummingbotLogger

from .stellar_amm_integration import LiquidityPool, StellarAMMIntegration, SwapQuote
from .stellar_yield_farming import StellarYieldFarming


class LiquidityStrategy(Enum):
    """Liquidity management strategies"""

    MARKET_MAKING = "market_making"
    INVENTORY_BALANCING = "inventory_balancing"
    CROSS_MARKET_ARBITRAGE = "cross_market_arbitrage"
    YIELD_OPTIMIZATION = "yield_optimization"
    RISK_MITIGATION = "risk_mitigation"


class InventoryTarget(Enum):
    """Target inventory levels"""

    MINIMAL = "minimal"
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    MAXIMUM = "maximum"


@dataclass
class AssetInventory:
    """Represents inventory for a single asset"""

    asset: Asset
    total_balance: Decimal
    available_balance: Decimal
    reserved_balance: Decimal
    target_balance: Decimal
    min_balance: Decimal
    max_balance: Decimal
    average_cost: Decimal
    unrealized_pnl: Decimal
    last_rebalance: float = field(default_factory=time.time)
    price_history: deque[Any] = field(default_factory=lambda: deque(maxlen=100))
    volatility: Decimal = field(default=Decimal("0"))

    @property
    def inventory_ratio(self) -> Decimal:
        """Current inventory as ratio of target"""
        if self.target_balance == 0:
            return Decimal("1")
        return self.total_balance / self.target_balance

    @property
    def needs_rebalancing(self) -> bool:
        """Check if inventory needs rebalancing"""
        return self.total_balance < self.min_balance or self.total_balance > self.max_balance


@dataclass
class LiquidityProvision:
    """Represents a liquidity provision operation"""

    id: str
    strategy: LiquidityStrategy
    base_asset: Asset
    quote_asset: Asset
    base_amount: Decimal
    quote_amount: Decimal
    target_spread: Decimal
    min_spread: Decimal
    max_position_size: Decimal
    inventory_skew: Decimal  # Bias towards buying/selling
    active: bool = True
    created_at: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)
    orders_placed: int = field(default=0)
    volume_traded: Decimal = field(default=Decimal("0"))
    pnl: Decimal = field(default=Decimal("0"))


@dataclass
class RebalanceRecommendation:
    """Recommendation for inventory rebalancing"""

    asset: Asset
    current_amount: Decimal
    target_amount: Decimal
    rebalance_amount: Decimal
    urgency: str  # "low", "medium", "high", "critical"
    strategy: LiquidityStrategy
    estimated_cost: Decimal
    expected_time: int  # seconds
    risk_score: Decimal
    confidence: Decimal


@dataclass
class LiquidityMetrics:
    """Comprehensive liquidity performance metrics"""

    total_inventory_value: Decimal
    inventory_turnover: Decimal
    average_spread_captured: Decimal
    fill_rate: Decimal
    inventory_variance: Decimal
    rebalance_frequency: Decimal
    gas_efficiency: Decimal
    risk_adjusted_return: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal
    uptime_percentage: Decimal
    order_fill_latency: Decimal


class StellarLiquidityManagement:
    """
    Advanced liquidity management system for Stellar:
    - Multi-asset inventory optimization
    - Cross-market liquidity provision
    - Automated rebalancing strategies
    - Risk-aware position sizing
    - Yield-enhanced liquidity management
    """

    _logger: Optional[HummingbotLogger] = None

    def __init__(
        self,
        server: Server,
        network: Network,
        source_account: Account,
        source_keypair: Keypair,
        amm_integration: StellarAMMIntegration,
        yield_farming: StellarYieldFarming,
        target_inventory: InventoryTarget = InventoryTarget.BALANCED,
        rebalance_threshold: Decimal = Decimal("0.2"),  # 20% deviation triggers rebalance
        max_inventory_skew: Decimal = Decimal("0.3"),  # 30% max skew
        risk_tolerance: Decimal = Decimal("0.05"),  # 5% risk tolerance
    ):
        self._server = server
        self._network = network
        self._source_account = source_account
        self._source_keypair = source_keypair
        self._amm_integration = amm_integration
        self._yield_farming = yield_farming
        self._target_inventory = target_inventory
        self._rebalance_threshold = rebalance_threshold
        self._max_inventory_skew = max_inventory_skew
        self._risk_tolerance = risk_tolerance

        # Inventory management
        self._inventories: Dict[str, AssetInventory] = {}
        self._liquidity_provisions: Dict[str, LiquidityProvision] = {}
        self._rebalance_queue: List[RebalanceRecommendation] = []

        # Market data and analysis
        self._price_feeds: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._volume_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._spread_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

        # Performance tracking
        self._metrics_history: deque[Any] = deque(maxlen=1440)  # 24 hours at 1-minute intervals
        self._trade_history: List[Dict] = []
        self._rebalance_history: List[Dict] = []

        # Background tasks
        self._inventory_monitor_task: Optional[asyncio.Task[None]] = None
        self._rebalance_task: Optional[asyncio.Task[None]] = None
        self._metrics_task: Optional[asyncio.Task[None]] = None

        # Configuration
        self._inventory_targets = {
            InventoryTarget.MINIMAL: Decimal("0.1"),
            InventoryTarget.CONSERVATIVE: Decimal("0.25"),
            InventoryTarget.BALANCED: Decimal("0.5"),
            InventoryTarget.AGGRESSIVE: Decimal("0.75"),
            InventoryTarget.MAXIMUM: Decimal("1.0"),
        }

        # Strategy weights
        self._strategy_weights = {
            LiquidityStrategy.MARKET_MAKING: Decimal("0.4"),
            LiquidityStrategy.INVENTORY_BALANCING: Decimal("0.3"),
            LiquidityStrategy.YIELD_OPTIMIZATION: Decimal("0.2"),
            LiquidityStrategy.RISK_MITIGATION: Decimal("0.1"),
        }

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._logger is None:
            cls._logger = logging.getLogger(__name__)
        return cls._logger

    async def initialize(self) -> None:
        """Initialize liquidity management system"""
        try:
            self.logger().info("Initializing Stellar liquidity management...")

            # Initialize inventory tracking
            await self._initialize_inventories()

            # Setup liquidity provisions
            await self._setup_liquidity_provisions()

            # Start background monitoring
            await self._start_monitoring()

            self.logger().info(
                f"Liquidity management initialized with {len(self._inventories)} assets"
            )

        except Exception as e:
            self.logger().error(f"Failed to initialize liquidity management: {e}")
            raise

    async def _initialize_inventories(self) -> None:
        """Initialize asset inventories from account balances"""
        try:
            # Get current account balances
            account_response = (
                await self._server.accounts().account_id(self._source_account.account_id).call()
            )

            for balance in account_response["balances"]:
                asset = self._parse_asset_from_balance(balance)
                if asset:
                    inventory = await self._create_inventory(asset, balance)
                    self._inventories[str(asset)] = inventory

        except Exception as e:
            self.logger().error(f"Failed to initialize inventories: {e}")
            raise

    def _parse_asset_from_balance(self, balance: Dict[str, Any]) -> Optional[Asset]:
        """Parse Stellar asset from balance record"""
        try:
            if balance["asset_type"] == "native":
                return Asset.native()
            elif (
                balance["asset_type"] == "credit_alphanum4"
                or balance["asset_type"] == "credit_alphanum12"
            ):
                return Asset(balance["asset_code"], balance["asset_issuer"])
            return None
        except Exception as e:
            self.logger().warning(f"Failed to parse asset from balance: {e}")
            return None

    async def _create_inventory(self, asset: Asset, balance: Dict[str, Any]) -> AssetInventory:
        """Create inventory object for asset"""
        try:
            total_balance = Decimal(balance["balance"])

            # Calculate target balances based on strategy
            base_target = total_balance * self._inventory_targets[self._target_inventory]

            inventory = AssetInventory(
                asset=asset,
                total_balance=total_balance,
                available_balance=total_balance,  # Will be updated with reserved amounts
                reserved_balance=Decimal("0"),
                target_balance=base_target,
                min_balance=base_target * Decimal("0.5"),  # 50% below target
                max_balance=base_target * Decimal("1.5"),  # 50% above target
                average_cost=Decimal("1.0"),  # Placeholder - would fetch historical cost
                unrealized_pnl=Decimal("0"),
            )

            # Initialize price history
            current_price = await self._get_asset_price(asset)
            if current_price:
                inventory.price_history.append(current_price)

            return inventory

        except Exception as e:
            self.logger().error(f"Failed to create inventory for {asset}: {e}")
            raise

    async def _get_asset_price(self, asset: Asset) -> Optional[Decimal]:
        """Get current price for asset in XLM"""
        try:
            if asset.is_native():
                return Decimal("1.0")  # XLM base price

            # Try to get price from orderbook or recent trades
            # This is a placeholder - real implementation would use market data
            return Decimal("1.0")

        except Exception as e:
            self.logger().warning(f"Failed to get price for {asset}: {e}")
            return None

    async def _setup_liquidity_provisions(self) -> None:
        """Setup initial liquidity provision strategies"""
        try:
            # Create market making provisions for major pairs
            major_assets = [
                inv.asset
                for inv in self._inventories.values()
                if inv.total_balance > Decimal("100")
            ]

            for i, base_asset in enumerate(major_assets):
                for quote_asset in major_assets[i + 1 :]:
                    provision = LiquidityProvision(
                        id=f"mm_{str(base_asset)}_{str(quote_asset)}",
                        strategy=LiquidityStrategy.MARKET_MAKING,
                        base_asset=base_asset,
                        quote_asset=quote_asset,
                        base_amount=self._inventories[str(base_asset)].total_balance
                        * Decimal("0.1"),
                        quote_amount=self._inventories[str(quote_asset)].total_balance
                        * Decimal("0.1"),
                        target_spread=Decimal("0.002"),  # 0.2% spread
                        min_spread=Decimal("0.001"),  # 0.1% minimum
                        max_position_size=Decimal("1000"),
                        inventory_skew=Decimal("0"),
                    )
                    self._liquidity_provisions[provision.id] = provision

        except Exception as e:
            self.logger().error(f"Failed to setup liquidity provisions: {e}")

    async def _start_monitoring(self) -> None:
        """Start background monitoring tasks"""
        self._inventory_monitor_task = safe_ensure_future(self._monitor_inventories())
        self._rebalance_task = safe_ensure_future(self._auto_rebalance_loop())
        self._metrics_task = safe_ensure_future(self._collect_metrics())

    async def _monitor_inventories(self) -> None:
        """Monitor inventory levels and market conditions"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                # Update all inventories
                await self._update_all_inventories()

                # Check for rebalancing needs
                await self._check_rebalance_needs()

                # Update liquidity provisions
                await self._update_liquidity_provisions()

            except Exception as e:
                self.logger().warning(f"Error in inventory monitoring: {e}")
                await asyncio.sleep(60)  # Longer delay on error

    async def _update_all_inventories(self) -> None:
        """Update all inventory levels and metrics"""
        try:
            # Get fresh account data
            account_response = (
                await self._server.accounts().account_id(self._source_account.account_id).call()
            )

            for balance in account_response["balances"]:
                asset = self._parse_asset_from_balance(balance)
                if asset and str(asset) in self._inventories:
                    inventory = self._inventories[str(asset)]

                    # Update balances
                    new_balance = Decimal(balance["balance"])
                    inventory.total_balance = new_balance
                    inventory.available_balance = new_balance - inventory.reserved_balance

                    # Update price and volatility
                    current_price = await self._get_asset_price(asset)
                    if current_price:
                        inventory.price_history.append(current_price)
                        inventory.volatility = self._calculate_volatility(inventory.price_history)

                    # Update unrealized PnL
                    if current_price:
                        inventory.unrealized_pnl = (
                            current_price - inventory.average_cost
                        ) * inventory.total_balance

        except Exception as e:
            self.logger().warning(f"Failed to update inventories: {e}")

    def _calculate_volatility(self, prices: deque[Any]) -> Decimal:
        """Calculate price volatility using standard deviation"""
        try:
            if len(prices) < 2:
                return Decimal("0")

            price_list = [float(p) for p in prices]
            returns = [
                (price_list[i] - price_list[i - 1]) / price_list[i - 1]
                for i in range(1, len(price_list))
            ]

            if len(returns) < 2:
                return Decimal("0")

            volatility = statistics.stdev(returns)
            return Decimal(str(volatility))

        except Exception as e:
            self.logger().warning(f"Failed to calculate volatility: {e}")
            return Decimal("0")

    async def _check_rebalance_needs(self) -> None:
        """Check which assets need rebalancing"""
        try:
            recommendations = []

            for inventory in self._inventories.values():
                if inventory.needs_rebalancing:
                    recommendation = await self._create_rebalance_recommendation(inventory)
                    if recommendation:
                        recommendations.append(recommendation)

            # Sort by urgency and add to queue
            recommendations.sort(
                key=lambda x: {"critical": 4, "high": 3, "medium": 2, "low": 1}[x.urgency],
                reverse=True,
            )

            for rec in recommendations:
                if rec not in self._rebalance_queue:
                    self._rebalance_queue.append(rec)

        except Exception as e:
            self.logger().warning(f"Error checking rebalance needs: {e}")

    async def _create_rebalance_recommendation(
        self, inventory: AssetInventory
    ) -> Optional[RebalanceRecommendation]:
        """Create rebalance recommendation for inventory"""
        try:
            rebalance_amount = inventory.target_balance - inventory.total_balance

            # Determine urgency
            deviation = abs(inventory.inventory_ratio - Decimal("1"))
            if deviation > Decimal("0.5"):
                urgency = "critical"
            elif deviation > Decimal("0.3"):
                urgency = "high"
            elif deviation > Decimal("0.2"):
                urgency = "medium"
            else:
                urgency = "low"

            # Estimate cost and time
            estimated_cost = abs(rebalance_amount) * Decimal("0.001")  # 0.1% estimated cost
            expected_time = 300  # 5 minutes estimate

            # Calculate risk and confidence
            risk_score = inventory.volatility * abs(rebalance_amount)
            confidence = Decimal("0.8")  # Base confidence

            return RebalanceRecommendation(
                asset=inventory.asset,
                current_amount=inventory.total_balance,
                target_amount=inventory.target_balance,
                rebalance_amount=rebalance_amount,
                urgency=urgency,
                strategy=LiquidityStrategy.INVENTORY_BALANCING,
                estimated_cost=estimated_cost,
                expected_time=expected_time,
                risk_score=risk_score,
                confidence=confidence,
            )

        except Exception as e:
            self.logger().warning(f"Failed to create rebalance recommendation: {e}")
            return None

    async def _update_liquidity_provisions(self) -> None:
        """Update liquidity provision strategies"""
        try:
            for provision in self._liquidity_provisions.values():
                if provision.active:
                    # Update inventory skew based on current balances
                    base_inventory = self._inventories.get(str(provision.base_asset))
                    quote_inventory = self._inventories.get(str(provision.quote_asset))

                    if base_inventory and quote_inventory:
                        # Calculate skew based on inventory ratios
                        base_ratio = base_inventory.inventory_ratio
                        quote_ratio = quote_inventory.inventory_ratio

                        skew = (base_ratio - quote_ratio) / (base_ratio + quote_ratio)
                        provision.inventory_skew = max(
                            min(skew, self._max_inventory_skew), -self._max_inventory_skew
                        )
                        provision.last_update = time.time()

        except Exception as e:
            self.logger().warning(f"Error updating liquidity provisions: {e}")

    async def _auto_rebalance_loop(self) -> None:
        """Main auto-rebalance execution loop"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute

                if self._rebalance_queue:
                    # Process highest priority rebalance
                    recommendation = self._rebalance_queue.pop(0)

                    if recommendation.urgency in ["critical", "high"]:
                        success = await self._execute_rebalance(recommendation)
                        if success:
                            self.logger().info(
                                f"Executed {recommendation.urgency} rebalance for {recommendation.asset}"
                            )

            except Exception as e:
                self.logger().warning(f"Error in auto-rebalance loop: {e}")
                await asyncio.sleep(300)

    async def _execute_rebalance(self, recommendation: RebalanceRecommendation) -> bool:
        """Execute a rebalance recommendation"""
        try:
            if recommendation.rebalance_amount > 0:
                # Need to acquire more of this asset
                return await self._acquire_asset(recommendation)
            else:
                # Need to reduce this asset
                return await self._reduce_asset(recommendation)

        except Exception as e:
            self.logger().error(f"Failed to execute rebalance: {e}")
            return False

    async def _acquire_asset(self, recommendation: RebalanceRecommendation) -> bool:
        """Acquire asset through various methods"""
        try:
            asset = recommendation.asset
            amount_needed = recommendation.rebalance_amount

            # Strategy 1: Direct swap through AMM
            if self._amm_integration:
                success = await self._acquire_via_amm(asset, amount_needed)
                if success:
                    return True

            # Strategy 2: Use yield farming rewards
            if self._yield_farming:
                success = await self._acquire_via_yield(asset, amount_needed)
                if success:
                    return True

            # Strategy 3: Market order (placeholder)
            # Would implement market order execution here

            return False

        except Exception as e:
            self.logger().error(f"Failed to acquire asset {recommendation.asset}: {e}")
            return False

    async def _acquire_via_amm(self, asset: Asset, amount: Decimal) -> bool:
        """Acquire asset through AMM swap"""
        try:
            # Find best asset to swap from
            best_swap_asset = None
            best_quote = None

            for inventory in self._inventories.values():
                if inventory.asset != asset and inventory.available_balance > amount:

                    quote = await self._amm_integration.get_swap_quote(
                        inventory.asset, asset, amount
                    )

                    if quote and (not best_quote or quote.price > best_quote.price):
                        best_quote = quote
                        best_swap_asset = inventory.asset

            if best_quote and best_swap_asset:
                tx_hash = await self._amm_integration.execute_swap(best_quote)
                if tx_hash:
                    # Update inventory tracking
                    await self._record_rebalance_trade(
                        best_swap_asset, asset, best_quote.input_amount, amount
                    )
                    return True

            return False

        except Exception as e:
            self.logger().error(f"Failed to acquire via AMM: {e}")
            return False

    async def _acquire_via_yield(self, asset: Asset, amount: Decimal) -> bool:
        """Acquire asset through yield farming strategies"""
        try:
            # Check if we have yield farming positions with this asset
            portfolio_summary = await self._yield_farming.get_portfolio_summary()

            for position in portfolio_summary.get("positions", []):
                if asset in [position.get("farm_assets", [])]:
                    # Consider partial exit to rebalance
                    # This is a simplified approach
                    pass

            return False  # Placeholder

        except Exception as e:
            self.logger().error(f"Failed to acquire via yield: {e}")
            return False

    async def _reduce_asset(self, recommendation: RebalanceRecommendation) -> bool:
        """Reduce asset holdings through various methods"""
        try:
            asset = recommendation.asset
            amount_to_reduce = abs(recommendation.rebalance_amount)

            # Strategy 1: Swap through AMM to most needed asset
            target_asset = await self._find_most_needed_asset()
            if target_asset and target_asset != asset:
                quote = await self._amm_integration.get_swap_quote(
                    asset, target_asset, amount_to_reduce
                )

                if quote:
                    tx_hash = await self._amm_integration.execute_swap(quote)
                    if tx_hash:
                        await self._record_rebalance_trade(
                            asset, target_asset, amount_to_reduce, quote.output_amount
                        )
                        return True

            # Strategy 2: Add to yield farming
            if self._yield_farming:
                # Find yield farm that accepts this asset
                opportunities = await self._yield_farming.get_best_opportunities()
                for opportunity in opportunities:
                    # Check if farm accepts this asset
                    # Simplified approach
                    pass

            return False

        except Exception as e:
            self.logger().error(f"Failed to reduce asset {recommendation.asset}: {e}")
            return False

    async def _find_most_needed_asset(self) -> Optional[Asset]:
        """Find the asset most in need of rebalancing"""
        try:
            max_deficit = Decimal("0")
            most_needed = None

            for inventory in self._inventories.values():
                if inventory.total_balance < inventory.target_balance:
                    deficit = inventory.target_balance - inventory.total_balance
                    if deficit > max_deficit:
                        max_deficit = deficit
                        most_needed = inventory.asset

            return most_needed

        except Exception as e:
            self.logger().warning(f"Failed to find most needed asset: {e}")
            return None

    async def _record_rebalance_trade(
        self, from_asset: Asset, to_asset: Asset, from_amount: Decimal, to_amount: Decimal
    ) -> None:
        """Record a rebalance trade in history"""
        try:
            trade_record = {
                "timestamp": time.time(),
                "type": "rebalance",
                "from_asset": str(from_asset),
                "to_asset": str(to_asset),
                "from_amount": float(from_amount),
                "to_amount": float(to_amount),
                "price": float(to_amount / from_amount) if from_amount > 0 else 0,
            }

            self._rebalance_history.append(trade_record)

            # Update inventory average costs
            if str(to_asset) in self._inventories:
                inventory = self._inventories[str(to_asset)]
                # Update average cost using weighted average
                total_value = (
                    inventory.average_cost * inventory.total_balance
                    + trade_record["price"] * to_amount
                )
                inventory.total_balance += to_amount
                inventory.average_cost = (
                    total_value / inventory.total_balance
                    if inventory.total_balance > 0
                    else trade_record["price"]
                )

        except Exception as e:
            self.logger().warning(f"Failed to record rebalance trade: {e}")

    async def _collect_metrics(self) -> None:
        """Collect comprehensive liquidity metrics"""
        while True:
            try:
                await asyncio.sleep(60)  # Collect every minute

                metrics = await self._calculate_current_metrics()
                self._metrics_history.append(metrics)

            except Exception as e:
                self.logger().warning(f"Error collecting metrics: {e}")
                await asyncio.sleep(300)

    async def _calculate_current_metrics(self) -> LiquidityMetrics:
        """Calculate current liquidity performance metrics"""
        try:
            # Calculate total inventory value
            total_value = Decimal("0")
            total_variance = Decimal("0")

            for inventory in self._inventories.values():
                current_price = await self._get_asset_price(inventory.asset) or Decimal("1")
                asset_value = inventory.total_balance * current_price
                total_value += asset_value

                # Calculate variance from target
                variance = abs(inventory.inventory_ratio - Decimal("1"))
                total_variance += variance

            # Calculate other metrics
            inventory_turnover = self._calculate_inventory_turnover()
            avg_spread = self._calculate_average_spread()
            fill_rate = self._calculate_fill_rate()
            rebalance_freq = (
                len(self._rebalance_history) / 24 if len(self._rebalance_history) > 0 else 0
            )

            return LiquidityMetrics(
                total_inventory_value=total_value,
                inventory_turnover=inventory_turnover,
                average_spread_captured=avg_spread,
                fill_rate=fill_rate,
                inventory_variance=total_variance,
                rebalance_frequency=Decimal(str(rebalance_freq)),
                gas_efficiency=self._calculate_gas_efficiency(),
                risk_adjusted_return=self._calculate_risk_adjusted_return(),
                sharpe_ratio=self._calculate_sharpe_ratio(),
                max_drawdown=self._calculate_max_drawdown(),
                uptime_percentage=Decimal("99.5"),  # Placeholder
                order_fill_latency=Decimal("2.5"),  # Placeholder
            )

        except Exception as e:
            self.logger().warning(f"Failed to calculate metrics: {e}")
            return LiquidityMetrics(
                total_inventory_value=Decimal("0"),
                inventory_turnover=Decimal("0"),
                average_spread_captured=Decimal("0"),
                fill_rate=Decimal("0"),
                inventory_variance=Decimal("0"),
                rebalance_frequency=Decimal("0"),
                gas_efficiency=Decimal("0"),
                risk_adjusted_return=Decimal("0"),
                sharpe_ratio=Decimal("0"),
                max_drawdown=Decimal("0"),
                uptime_percentage=Decimal("0"),
                order_fill_latency=Decimal("0"),
            )

    def _calculate_inventory_turnover(self) -> Decimal:
        """Calculate inventory turnover rate"""
        try:
            total_trades = len(self._trade_history) + len(self._rebalance_history)
            total_inventory = sum(inv.total_balance for inv in self._inventories.values())

            if total_inventory > 0:
                return Decimal(str(total_trades)) / total_inventory
            return Decimal("0")

        except Exception:
            return Decimal("0")

    def _calculate_average_spread(self) -> Decimal:
        """Calculate average spread captured"""
        try:
            if not self._spread_data:
                return Decimal("0")

            all_spreads = []
            for spreads in self._spread_data.values():
                all_spreads.extend(spreads)

            if all_spreads:
                avg_spread = sum(all_spreads) / len(all_spreads)
                return Decimal(str(avg_spread))

            return Decimal("0")

        except Exception:
            return Decimal("0")

    def _calculate_fill_rate(self) -> Decimal:
        """Calculate order fill rate"""
        try:
            total_orders = sum(prov.orders_placed for prov in self._liquidity_provisions.values())
            # Placeholder: would track actual fills vs orders
            filled_orders = total_orders * 0.85  # Assume 85% fill rate

            if total_orders > 0:
                return Decimal(str(filled_orders / total_orders))
            return Decimal("0")

        except Exception:
            return Decimal("0")

    def _calculate_gas_efficiency(self) -> Decimal:
        """Calculate gas efficiency ratio"""
        try:
            # Placeholder calculation
            return Decimal("0.95")  # 95% efficiency
        except Exception:
            return Decimal("0")

    def _calculate_risk_adjusted_return(self) -> Decimal:
        """Calculate risk-adjusted return"""
        try:
            total_pnl = sum(inv.unrealized_pnl for inv in self._inventories.values())
            total_risk = sum(
                inv.volatility * inv.total_balance for inv in self._inventories.values()
            )

            if total_risk > 0:
                return total_pnl / total_risk
            return Decimal("0")

        except Exception:
            return Decimal("0")

    def _calculate_sharpe_ratio(self) -> Decimal:
        """Calculate Sharpe ratio"""
        try:
            # Placeholder: would need return time series
            return Decimal("1.2")
        except Exception:
            return Decimal("0")

    def _calculate_max_drawdown(self) -> Decimal:
        """Calculate maximum drawdown"""
        try:
            # Placeholder: would need historical value series
            return Decimal("0.05")  # 5% max drawdown
        except Exception:
            return Decimal("0")

    async def get_inventory_summary(self) -> Dict[str, Any]:
        """Get comprehensive inventory summary"""
        try:
            total_value = Decimal("0")
            inventories = []

            for asset_str, inventory in self._inventories.items():
                current_price = await self._get_asset_price(inventory.asset) or Decimal("1")
                asset_value = inventory.total_balance * current_price
                total_value += asset_value

                inventories.append(
                    {
                        "asset": asset_str,
                        "total_balance": float(inventory.total_balance),
                        "available_balance": float(inventory.available_balance),
                        "reserved_balance": float(inventory.reserved_balance),
                        "target_balance": float(inventory.target_balance),
                        "inventory_ratio": float(inventory.inventory_ratio),
                        "needs_rebalancing": inventory.needs_rebalancing,
                        "current_value": float(asset_value),
                        "average_cost": float(inventory.average_cost),
                        "unrealized_pnl": float(inventory.unrealized_pnl),
                        "volatility": float(inventory.volatility),
                        "last_rebalance": inventory.last_rebalance,
                    }
                )

            return {
                "total_inventory_value": float(total_value),
                "total_assets": len(self._inventories),
                "assets_needing_rebalance": sum(
                    1 for inv in self._inventories.values() if inv.needs_rebalancing
                ),
                "inventories": inventories,
                "rebalance_queue_size": len(self._rebalance_queue),
                "last_updated": time.time(),
            }

        except Exception as e:
            self.logger().error(f"Failed to get inventory summary: {e}")
            return {}

    async def get_liquidity_provisions_status(self) -> Dict[str, Any]:
        """Get status of all liquidity provisions"""
        try:
            provisions = []
            total_volume = Decimal("0")
            total_pnl = Decimal("0")

            for provision in self._liquidity_provisions.values():
                total_volume += provision.volume_traded
                total_pnl += provision.pnl

                provisions.append(
                    {
                        "id": provision.id,
                        "strategy": provision.strategy.value,
                        "base_asset": str(provision.base_asset),
                        "quote_asset": str(provision.quote_asset),
                        "active": provision.active,
                        "target_spread": float(provision.target_spread),
                        "inventory_skew": float(provision.inventory_skew),
                        "orders_placed": provision.orders_placed,
                        "volume_traded": float(provision.volume_traded),
                        "pnl": float(provision.pnl),
                        "created_at": provision.created_at,
                        "last_update": provision.last_update,
                    }
                )

            return {
                "total_provisions": len(self._liquidity_provisions),
                "active_provisions": sum(
                    1 for p in self._liquidity_provisions.values() if p.active
                ),
                "total_volume_traded": float(total_volume),
                "total_pnl": float(total_pnl),
                "provisions": provisions,
                "last_updated": time.time(),
            }

        except Exception as e:
            self.logger().error(f"Failed to get provisions status: {e}")
            return {}

    async def get_rebalance_recommendations(self) -> List[Dict[str, Any]]:
        """Get current rebalance recommendations"""
        try:
            recommendations = []

            for rec in self._rebalance_queue:
                recommendations.append(
                    {
                        "asset": str(rec.asset),
                        "current_amount": float(rec.current_amount),
                        "target_amount": float(rec.target_amount),
                        "rebalance_amount": float(rec.rebalance_amount),
                        "urgency": rec.urgency,
                        "strategy": rec.strategy.value,
                        "estimated_cost": float(rec.estimated_cost),
                        "expected_time": rec.expected_time,
                        "risk_score": float(rec.risk_score),
                        "confidence": float(rec.confidence),
                    }
                )

            return recommendations

        except Exception as e:
            self.logger().error(f"Failed to get rebalance recommendations: {e}")
            return []

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        try:
            current_metrics = await self._calculate_current_metrics()

            # Historical metrics (last 24 hours)
            if self._metrics_history:
                avg_metrics = {
                    "avg_inventory_value": float(
                        sum(m.total_inventory_value for m in self._metrics_history)
                        / len(self._metrics_history)
                    ),
                    "avg_turnover": float(
                        sum(m.inventory_turnover for m in self._metrics_history)
                        / len(self._metrics_history)
                    ),
                    "avg_spread": float(
                        sum(m.average_spread_captured for m in self._metrics_history)
                        / len(self._metrics_history)
                    ),
                    "avg_fill_rate": float(
                        sum(m.fill_rate for m in self._metrics_history) / len(self._metrics_history)
                    ),
                }
            else:
                avg_metrics = {}

            return {
                "current": {
                    "total_inventory_value": float(current_metrics.total_inventory_value),
                    "inventory_turnover": float(current_metrics.inventory_turnover),
                    "average_spread_captured": float(current_metrics.average_spread_captured),
                    "fill_rate": float(current_metrics.fill_rate),
                    "inventory_variance": float(current_metrics.inventory_variance),
                    "rebalance_frequency": float(current_metrics.rebalance_frequency),
                    "risk_adjusted_return": float(current_metrics.risk_adjusted_return),
                    "sharpe_ratio": float(current_metrics.sharpe_ratio),
                    "max_drawdown": float(current_metrics.max_drawdown),
                    "uptime_percentage": float(current_metrics.uptime_percentage),
                },
                "averages_24h": avg_metrics,
                "trade_count": len(self._trade_history),
                "rebalance_count": len(self._rebalance_history),
                "last_updated": time.time(),
            }

        except Exception as e:
            self.logger().error(f"Failed to get performance metrics: {e}")
            return {}

    async def optimize_liquidity_allocation(self) -> Dict[str, Any]:
        """Optimize liquidity allocation across strategies"""
        try:
            # Analyze current performance of each strategy
            strategy_performance = {}

            for provision in self._liquidity_provisions.values():
                strategy = provision.strategy.value
                if strategy not in strategy_performance:
                    strategy_performance[strategy] = {
                        "volume": Decimal("0"),
                        "pnl": Decimal("0"),
                        "count": 0,
                    }

                strategy_performance[strategy]["volume"] += provision.volume_traded
                strategy_performance[strategy]["pnl"] += provision.pnl
                strategy_performance[strategy]["count"] += 1

            # Calculate optimal allocation
            total_capital = sum(inv.total_balance for inv in self._inventories.values())
            optimal_allocation = {}

            for strategy, performance in strategy_performance.items():
                if performance["count"] > 0:
                    avg_return = performance["pnl"] / performance["count"]
                    base_weight = self._strategy_weights.get(
                        LiquidityStrategy(strategy), Decimal("0.25")
                    )

                    # Adjust weight based on performance
                    performance_multiplier = max(
                        Decimal("0.5"), min(Decimal("2.0"), Decimal("1") + avg_return)
                    )
                    optimal_weight = base_weight * performance_multiplier

                    optimal_allocation[strategy] = float(optimal_weight * total_capital)

            # Generate reallocation recommendations
            recommendations = []
            current_allocation = {}

            for provision in self._liquidity_provisions.values():
                strategy = provision.strategy.value
                current_allocation[strategy] = current_allocation.get(strategy, 0) + float(
                    provision.base_amount + provision.quote_amount
                )

            for strategy, optimal_amount in optimal_allocation.items():
                current_amount = current_allocation.get(strategy, 0)
                difference = optimal_amount - current_amount

                if abs(difference) > 50:  # Minimum reallocation threshold
                    recommendations.append(
                        {
                            "strategy": strategy,
                            "current_allocation": current_amount,
                            "optimal_allocation": optimal_amount,
                            "reallocation_amount": difference,
                            "expected_improvement": abs(difference)
                            * 0.02,  # 2% improvement estimate
                        }
                    )

            return {
                "current_allocation": current_allocation,
                "optimal_allocation": optimal_allocation,
                "recommendations": recommendations,
                "total_capital": float(total_capital),
                "optimization_timestamp": time.time(),
            }

        except Exception as e:
            self.logger().error(f"Failed to optimize liquidity allocation: {e}")
            return {}

    async def shutdown(self) -> None:
        """Shutdown liquidity management system"""
        try:
            # Cancel all tasks
            tasks = [self._inventory_monitor_task, self._rebalance_task, self._metrics_task]

            for task in tasks:
                if task:
                    task.cancel()

            # Wait for tasks to complete
            valid_tasks = [t for t in tasks if t is not None]
            if valid_tasks:
                await asyncio.gather(*valid_tasks, return_exceptions=True)

            # Clear data structures
            self._inventories.clear()
            self._liquidity_provisions.clear()
            self._rebalance_queue.clear()

            self.logger().info("Liquidity management system shutdown complete")

        except Exception as e:
            self.logger().error(f"Error during liquidity management shutdown: {e}")
