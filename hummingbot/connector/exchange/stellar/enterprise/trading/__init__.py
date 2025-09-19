"""
Stellar Enterprise Trading Features

This module provides advanced trading and DeFi features for professional use:

- liquidity_management: Advanced liquidity algorithms (1,147 lines)
- yield_farming: DeFi yield optimization strategies (1,116 lines)

Total: 2,263 lines of professional trading infrastructure

Usage:
    from stellar.enterprise.trading import LiquidityManager, YieldFarming

    # Advanced liquidity management
    liquidity_mgr = LiquidityManager(strategy_config)
    await liquidity_mgr.start_rebalancing()

    # DeFi yield optimization
    yield_farm = YieldFarming(risk_config)
    await yield_farm.optimize_yields()
"""

# Import trading modules
from .liquidity_management import (
    StellarLiquidityManagement,
    LiquidityStrategy,
    InventoryTarget,
    AssetInventory,
    LiquidityProvision
)
from .yield_farming import (
    StellarYieldFarming,
    YieldStrategy,
    FarmStatus,
    YieldFarm,
    YieldPosition
)

__all__ = [
    # Liquidity management
    "StellarLiquidityManagement",
    "LiquidityStrategy",
    "InventoryTarget",
    "AssetInventory",
    "LiquidityProvision",

    # Yield farming
    "StellarYieldFarming",
    "YieldStrategy",
    "FarmStatus",
    "YieldFarm",
    "YieldPosition",
]

# Trading tier metadata
TIER_INFO = {
    "name": "Advanced Trading & DeFi",
    "business_value": "HIGH",
    "total_lines": 2263,
    "modules": 2,
    "features": [
        "liquidity_management",
        "yield_farming"
    ]
}
