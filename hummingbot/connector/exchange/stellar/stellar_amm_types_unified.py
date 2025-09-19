"""
Unified AMM and DeFi Types Module
Canonical definitions for AMM, liquidity pools, and DeFi-related types.

This module consolidates duplicate AMM-related types across the codebase
to establish a single source of truth while maintaining semantic clarity.
"""

import time
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union

try:
    from stellar_sdk import Asset
except ImportError:
    # Fallback for environments without stellar-sdk
    Asset = Any

try:
    from pydantic import BaseModel, Field
except ImportError:
    # Fallback for environments without Pydantic
    class BaseModel:
        pass

    def Field(**kwargs):
        return kwargs.get('default')


# =============================================================================
# AMM PROTOCOL TYPES
# =============================================================================

class AMMType(Enum):
    """AMM protocol types supported."""

    CONSTANT_PRODUCT = "constant_product"  # Uniswap v2 style (x*y=k)
    STABLE_SWAP = "stable_swap"           # StableSwap for similar assets
    WEIGHTED_POOL = "weighted_pool"       # Balancer style weighted pools
    CONCENTRATED_LIQUIDITY = "concentrated_liquidity"  # Uniswap v3 style
    HYBRID = "hybrid"                     # Combined mechanisms


class LiquidityPoolStatus(Enum):
    """Liquidity pool operational status."""

    ACTIVE = "active"
    PAUSED = "paused"
    DEPRECATED = "deprecated"
    EMERGENCY_STOP = "emergency_stop"
    MIGRATING = "migrating"


class SwapStatus(Enum):
    """Status of swap operations."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


# =============================================================================
# LIQUIDITY POOL TYPES
# =============================================================================

@dataclass
class UnifiedLiquidityPool:
    """Unified liquidity pool representation."""

    # Core identification
    pool_id: str
    amm_type: AMMType = AMMType.CONSTANT_PRODUCT
    status: LiquidityPoolStatus = LiquidityPoolStatus.ACTIVE

    # Asset information
    asset_a: Union[Asset, str] = None
    asset_b: Union[Asset, str] = None
    token_a: Optional[str] = None  # For Soroban compatibility
    token_b: Optional[str] = None  # For Soroban compatibility

    # Liquidity data
    reserves_a: Decimal = Decimal("0")
    reserves_b: Decimal = Decimal("0")
    reserve_a: Optional[Decimal] = None  # Alias for Soroban compatibility
    reserve_b: Optional[Decimal] = None  # Alias for Soroban compatibility

    # Pool shares
    total_shares: Decimal = Decimal("0")
    total_supply: Optional[Decimal] = None  # Alias for Soroban compatibility

    # Economic metrics
    fee_bp: int = 30  # Fee in basis points (0.3% default)
    fee_rate: Optional[Decimal] = None  # Alternative fee representation
    volume_24h: Decimal = Decimal("0")
    total_value_locked: Decimal = Decimal("0")
    apy: Optional[Decimal] = None

    # Metadata
    last_updated: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Handle field aliases and normalization."""
        # Normalize reserve fields
        if self.reserve_a is not None and self.reserves_a == Decimal("0"):
            self.reserves_a = self.reserve_a
        if self.reserve_b is not None and self.reserves_b == Decimal("0"):
            self.reserves_b = self.reserve_b

        # Normalize total supply fields
        if self.total_supply is not None and self.total_shares == Decimal("0"):
            self.total_shares = self.total_supply

        # Normalize fee fields
        if self.fee_rate is not None and self.fee_bp == 30:
            self.fee_bp = int(self.fee_rate * 10000)

        # Handle string assets for Soroban compatibility
        if isinstance(self.asset_a, str):
            self.token_a = self.asset_a
        if isinstance(self.asset_b, str):
            self.token_b = self.asset_b

    @property
    def price_a_to_b(self) -> Decimal:
        """Current price of asset A in terms of asset B."""
        if self.reserves_a == 0:
            return Decimal("0")
        return self.reserves_b / self.reserves_a

    @property
    def price_b_to_a(self) -> Decimal:
        """Current price of asset B in terms of asset A."""
        if self.reserves_b == 0:
            return Decimal("0")
        return self.reserves_a / self.reserves_b

    @property
    def fee_decimal(self) -> Decimal:
        """Get fee as decimal (0.003 for 30bp)."""
        return Decimal(self.fee_bp) / Decimal("10000")

    def get_output_amount(self, input_amount: Decimal, input_asset_is_a: bool) -> Decimal:
        """Calculate output amount for constant product formula."""
        if self.amm_type != AMMType.CONSTANT_PRODUCT:
            raise NotImplementedError("Only constant product pools supported")

        fee_multiplier = Decimal("1") - self.fee_decimal

        if input_asset_is_a:
            input_reserve = self.reserves_a
            output_reserve = self.reserves_b
        else:
            input_reserve = self.reserves_b
            output_reserve = self.reserves_a

        if input_reserve == 0 or output_reserve == 0:
            return Decimal("0")

        # Constant product formula: (x + dx) * (y - dy) = x * y
        # dy = y * dx / (x + dx)
        input_after_fee = input_amount * fee_multiplier
        numerator = output_reserve * input_after_fee
        denominator = input_reserve + input_after_fee

        return numerator / denominator

    def calculate_price_impact(self, input_amount: Decimal, input_asset_is_a: bool) -> Decimal:
        """Calculate price impact for a trade."""
        if input_amount == 0:
            return Decimal("0")

        current_price = self.price_a_to_b if input_asset_is_a else self.price_b_to_a
        output_amount = self.get_output_amount(input_amount, input_asset_is_a)

        if output_amount == 0:
            return Decimal("1")  # 100% impact

        effective_price = output_amount / input_amount
        price_impact = abs(current_price - effective_price) / current_price

        return min(price_impact, Decimal("1"))  # Cap at 100%


# =============================================================================
# SWAP QUOTE TYPES
# =============================================================================

@dataclass
class UnifiedSwapQuote:
    """Unified swap quote representation."""

    # Input/output assets
    input_asset: Union[Asset, str]
    output_asset: Union[Asset, str]
    input_token: Optional[str] = None   # For Soroban compatibility
    output_token: Optional[str] = None  # For Soroban compatibility

    # Amounts
    input_amount: Decimal = Decimal("0")
    output_amount: Decimal = Decimal("0")
    minimum_received: Optional[Decimal] = None

    # Pricing information
    price: Decimal = Decimal("0")
    price_impact: Decimal = Decimal("0")
    fee: Decimal = Decimal("0")
    slippage: Decimal = Decimal("0.005")  # 0.5% default
    slippage_tolerance: Optional[Decimal] = None  # Alias

    # Route information
    pool_id: Optional[str] = None
    route: List[str] = field(default_factory=list)  # Pool IDs in route

    # Timing
    expiry: float = field(default_factory=lambda: time.time() + 300)  # 5 min default
    expires_at: Optional[float] = None  # Alias
    timestamp: float = field(default_factory=time.time)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Handle field aliases and normalization."""
        # Handle string assets for Soroban compatibility
        if isinstance(self.input_asset, str):
            self.input_token = self.input_asset
        if isinstance(self.output_asset, str):
            self.output_token = self.output_asset

        # Normalize slippage fields
        if self.slippage_tolerance is not None:
            self.slippage = self.slippage_tolerance

        # Normalize expiry fields
        if self.expires_at is not None:
            self.expiry = self.expires_at

        # Calculate minimum received if not set
        if self.minimum_received is None and self.output_amount > 0:
            slippage_factor = Decimal("1") - self.slippage
            self.minimum_received = self.output_amount * slippage_factor

        # Calculate price if not set
        if self.price == Decimal("0") and self.input_amount > 0 and self.output_amount > 0:
            self.price = self.output_amount / self.input_amount

    @property
    def is_expired(self) -> bool:
        """Check if quote has expired."""
        return time.time() > self.expiry

    @property
    def effective_price(self) -> Decimal:
        """Get effective price including fees and slippage."""
        if self.input_amount == 0:
            return Decimal("0")
        return self.output_amount / self.input_amount

    @property
    def age_seconds(self) -> float:
        """Get age of quote in seconds."""
        return time.time() - self.timestamp


# =============================================================================
# LIQUIDITY POSITION TYPES
# =============================================================================

@dataclass
class LiquidityPosition:
    """User's liquidity provider position."""

    pool_id: str
    shares: Decimal
    asset_a_amount: Decimal
    asset_b_amount: Decimal

    # Entry information
    entry_price_a: Decimal
    entry_price_b: Decimal
    entry_timestamp: float = field(default_factory=time.time)

    # Rewards and fees
    unclaimed_fees_a: Decimal = Decimal("0")
    unclaimed_fees_b: Decimal = Decimal("0")
    claimed_fees_total: Decimal = Decimal("0")

    # Performance tracking
    impermanent_loss: Optional[Decimal] = None
    total_return: Optional[Decimal] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def current_value_a(self) -> Decimal:
        """Current value of position in asset A terms."""
        return self.asset_a_amount + self.asset_b_amount / self.entry_price_a

    @property
    def entry_value_a(self) -> Decimal:
        """Entry value of position in asset A terms."""
        return self.asset_a_amount + (self.asset_b_amount / self.entry_price_a)

    def calculate_impermanent_loss(self, current_price_a: Decimal) -> Decimal:
        """Calculate impermanent loss vs holding."""
        if self.entry_price_a == 0:
            return Decimal("0")

        price_ratio = current_price_a / self.entry_price_a
        sqrt_ratio = price_ratio.sqrt() if hasattr(price_ratio, 'sqrt') else Decimal(float(price_ratio) ** 0.5)

        # IL = (2 * sqrt(price_ratio) / (1 + price_ratio)) - 1
        il = (2 * sqrt_ratio / (1 + price_ratio)) - 1
        return abs(il)


# =============================================================================
# BACKWARD COMPATIBILITY ALIASES
# =============================================================================

# AMM Integration compatibility
LiquidityPool = UnifiedLiquidityPool
SwapQuote = UnifiedSwapQuote

# Soroban compatibility wrappers


class SorobanLiquidityPoolCompat:
    """Backward compatibility for Soroban LiquidityPool."""

    def __init__(self, pool_id: str, token_a: str, token_b: str,
                 reserve_a: Decimal, reserve_b: Decimal, total_supply: Decimal,
                 fee_rate: Decimal, **kwargs):
        self.pool = UnifiedLiquidityPool(
            pool_id=pool_id,
            token_a=token_a,
            token_b=token_b,
            reserves_a=reserve_a,
            reserves_b=reserve_b,
            total_shares=total_supply,
            fee_rate=fee_rate,
            **kwargs
        )

    def __getattr__(self, name):
        # Map old field names to new ones
        field_mapping = {
            'token_a': 'token_a',
            'token_b': 'token_b',
            'reserve_a': 'reserves_a',
            'reserve_b': 'reserves_b',
            'total_supply': 'total_shares',
            'fee_rate': 'fee_decimal'
        }
        mapped_name = field_mapping.get(name, name)
        return getattr(self.pool, mapped_name)


class SorobanSwapQuoteCompat:
    """Backward compatibility for Soroban SwapQuote."""

    def __init__(self, input_token: str, output_token: str, input_amount: Decimal,
                 output_amount: Decimal, price_impact: Decimal, fee: Decimal,
                 route: List[str], expires_at: float, **kwargs):
        self.quote = UnifiedSwapQuote(
            input_asset=input_token,
            output_asset=output_token,
            input_amount=input_amount,
            output_amount=output_amount,
            price_impact=price_impact,
            fee=fee,
            route=route,
            expires_at=expires_at,
            **kwargs
        )

    def __getattr__(self, name):
        # Map old field names to new ones
        field_mapping = {
            'input_token': 'input_token',
            'output_token': 'output_token',
            'expires_at': 'expiry',
            'slippage_tolerance': 'slippage'
        }
        mapped_name = field_mapping.get(name, name)
        return getattr(self.quote, mapped_name)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # New unified types
    "AMMType",
    "LiquidityPoolStatus",
    "SwapStatus",
    "UnifiedLiquidityPool",
    "UnifiedSwapQuote",
    "LiquidityPosition",

    # Backward compatibility aliases
    "LiquidityPool",  # -> UnifiedLiquidityPool
    "SwapQuote",  # -> UnifiedSwapQuote

    # Compatibility wrappers
    "SorobanLiquidityPoolCompat",
    "SorobanSwapQuoteCompat",
]
