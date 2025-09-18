"""
Stellar Enterprise Features Module

This module provides enterprise-grade features for the Stellar Hummingbot Connector,
organized into three tiers by business value and functionality:

- security/: Enterprise security features (Vault, hardware wallets, hardening)
- trading/: Advanced trading and DeFi features (liquidity management, yield farming)
- infrastructure/: Development and operational tools (testing, optimization)

Usage:
    from stellar.enterprise import get_enterprise_features, is_feature_enabled

    # Check if enterprise features are available
    if is_feature_enabled('vault_integration'):
        vault = get_feature('vault_integration')
        # Use vault for secure key management
"""

from .core import (
    EnterpriseFeatureConfig,
    StellarEnterpriseFeatureRegistry,
    initialize_enterprise_features,
    get_enterprise_features,
    is_feature_enabled,
    get_feature,
    FeatureTier,
    FeatureStatus
)

# Re-export the enterprise features framework for easy access
__all__ = [
    # Core framework
    "EnterpriseFeatureConfig",
    "StellarEnterpriseFeatureRegistry",
    "initialize_enterprise_features",
    "get_enterprise_features",
    "is_feature_enabled",
    "get_feature",

    # Enums
    "FeatureTier",
    "FeatureStatus",
]

# Version information
__version__ = "1.0.0"
__author__ = "Hummingbot Enterprise Team"