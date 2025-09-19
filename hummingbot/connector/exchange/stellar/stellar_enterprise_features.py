"""
Stellar Enterprise Features Framework
Modular enterprise feature activation and management system.

This module provides a unified framework for enabling and managing enterprise-grade
features in the Stellar connector while maintaining backward compatibility.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type, Union
import importlib
from pathlib import Path

from .stellar_logging import get_stellar_logger, LogCategory


class FeatureTier(Enum):
    """Enterprise feature tiers by business value."""

    CORE = "core"              # Always enabled core functionality
    SECURITY = "security"      # Enterprise security features
    TRADING = "trading"        # Advanced trading and DeFi features
    INFRASTRUCTURE = "infrastructure"  # Development and operations tools


class FeatureStatus(Enum):
    """Current status of enterprise features."""

    DISABLED = "disabled"
    ENABLED = "enabled"
    ERROR = "error"
    LOADING = "loading"


@dataclass
class FeatureDependency:
    """Feature dependency specification."""

    feature_id: str
    required: bool = True
    reason: str = ""


@dataclass
class FeatureDefinition:
    """Enterprise feature definition and metadata."""

    feature_id: str
    name: str
    description: str
    tier: FeatureTier
    module_path: str
    class_name: str

    # Dependencies and requirements
    dependencies: List[FeatureDependency] = field(default_factory=list)
    required_config: List[str] = field(default_factory=list)
    required_credentials: List[str] = field(default_factory=list)

    # Business metadata
    business_value: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    risk_level: str = "MEDIUM"     # LOW, MEDIUM, HIGH, CRITICAL

    # Technical metadata
    estimated_overhead_ms: int = 0
    memory_overhead_mb: int = 0

    # Status
    status: FeatureStatus = FeatureStatus.DISABLED
    last_error: Optional[str] = None


@dataclass
class EnterpriseFeatureConfig:
    """Configuration for enterprise features."""

    # Security Features (Tier 1)
    vault_integration_enabled: bool = False
    hardware_wallet_enabled: bool = False
    security_hardening_enabled: bool = False
    security_metrics_enabled: bool = False

    # Advanced Trading Features (Tier 2)
    liquidity_management_enabled: bool = False
    yield_farming_enabled: bool = False

    # Infrastructure Features (Tier 3)
    test_account_manager_enabled: bool = False
    load_testing_enabled: bool = False
    performance_optimizer_enabled: bool = False
    web_assistant_enabled: bool = False
    user_stream_tracker_enabled: bool = False

    # Configuration validation
    validate_on_startup: bool = True
    fail_fast_on_errors: bool = False

    def get_enabled_features(self) -> List[str]:
        """Get list of enabled feature IDs."""
        enabled = []
        for field_name, value in self.__dict__.items():
            if field_name.endswith('_enabled') and value:
                feature_id = field_name.replace('_enabled', '')
                enabled.append(feature_id)
        return enabled


class StellarEnterpriseFeatureRegistry:
    """Registry and manager for enterprise features."""

    def __init__(self, config: EnterpriseFeatureConfig):
        self.config = config
        self.logger = get_stellar_logger()
        self._features: Dict[str, FeatureDefinition] = {}
        self._loaded_modules: Dict[str, Any] = {}
        self._feature_instances: Dict[str, Any] = {}

        # Register all available enterprise features
        self._register_features()

    def _register_features(self) -> None:
        """Register all available enterprise features."""

        # Security Tier Features
        self._features["vault_integration"] = FeatureDefinition(
            feature_id="vault_integration",
            name="HashiCorp Vault Integration",
            description="Enterprise key management using HashiCorp Vault",
            tier=FeatureTier.SECURITY,
            module_path="stellar_vault_integration",
            class_name="StellarVaultIntegration",
            business_value="CRITICAL",
            risk_level="HIGH",
            required_config=["vault_url", "vault_auth_method"],
            required_credentials=["vault_token"],
            estimated_overhead_ms=50,
            memory_overhead_mb=25
        )

        self._features["hardware_wallet"] = FeatureDefinition(
            feature_id="hardware_wallet",
            name="Hardware Wallet Integration",
            description="Ledger and Trezor hardware wallet support",
            tier=FeatureTier.SECURITY,
            module_path="stellar_hardware_wallets",
            class_name="StellarHardwareWalletManager",
            business_value="HIGH",
            risk_level="MEDIUM",
            required_config=["supported_wallets"],
            estimated_overhead_ms=100,
            memory_overhead_mb=15
        )

        self._features["security_hardening"] = FeatureDefinition(
            feature_id="security_hardening",
            name="Security Hardening Framework",
            description="Production security controls and threat mitigation",
            tier=FeatureTier.SECURITY,
            module_path="stellar_security_hardening",
            class_name="StellarSecurityHardening",
            business_value="HIGH",
            risk_level="MEDIUM",
            required_config=["security_policy"],
            estimated_overhead_ms=25,
            memory_overhead_mb=10
        )

        self._features["security_metrics"] = FeatureDefinition(
            feature_id="security_metrics",
            name="Security Metrics & Monitoring",
            description="Security event monitoring and compliance reporting",
            tier=FeatureTier.SECURITY,
            module_path="stellar_security_metrics",
            class_name="StellarSecurityMetrics",
            business_value="HIGH",
            risk_level="LOW",
            dependencies=[FeatureDependency("security_hardening", required=False)],
            estimated_overhead_ms=15,
            memory_overhead_mb=20
        )

        # Trading Tier Features
        self._features["liquidity_management"] = FeatureDefinition(
            feature_id="liquidity_management",
            name="Advanced Liquidity Management",
            description="Professional liquidity management algorithms",
            tier=FeatureTier.TRADING,
            module_path="stellar_liquidity_management",
            class_name="StellarLiquidityManager",
            business_value="HIGH",
            risk_level="MEDIUM",
            dependencies=[FeatureDependency("yield_farming", required=False)],
            required_config=["liquidity_strategy", "risk_limits"],
            estimated_overhead_ms=75,
            memory_overhead_mb=50
        )

        self._features["yield_farming"] = FeatureDefinition(
            feature_id="yield_farming",
            name="DeFi Yield Farming",
            description="Automated yield optimization strategies",
            tier=FeatureTier.TRADING,
            module_path="stellar_yield_farming",
            class_name="StellarYieldFarming",
            business_value="MEDIUM",
            risk_level="HIGH",
            required_config=["yield_strategy", "max_risk_exposure"],
            estimated_overhead_ms=100,
            memory_overhead_mb=40
        )

        # Infrastructure Tier Features
        self._features["test_account_manager"] = FeatureDefinition(
            feature_id="test_account_manager",
            name="Test Account Manager",
            description="Automated test account management and funding",
            tier=FeatureTier.INFRASTRUCTURE,
            module_path="stellar_test_account_manager",
            class_name="StellarTestAccountManager",
            business_value="MEDIUM",
            risk_level="LOW",
            estimated_overhead_ms=10,
            memory_overhead_mb=5
        )

        self._features["load_testing"] = FeatureDefinition(
            feature_id="load_testing",
            name="Load Testing Framework",
            description="Performance and load testing capabilities",
            tier=FeatureTier.INFRASTRUCTURE,
            module_path="stellar_load_testing",
            class_name="StellarLoadTester",
            business_value="MEDIUM",
            risk_level="LOW",
            estimated_overhead_ms=0,  # Only active during testing
            memory_overhead_mb=30
        )

        self._features["performance_optimizer"] = FeatureDefinition(
            feature_id="performance_optimizer",
            name="Performance Optimizer",
            description="Runtime performance optimization and tuning",
            tier=FeatureTier.INFRASTRUCTURE,
            module_path="stellar_performance_optimizer",
            class_name="StellarPerformanceOptimizer",
            business_value="MEDIUM",
            risk_level="LOW",
            estimated_overhead_ms=-20,  # Negative overhead (optimization)
            memory_overhead_mb=15
        )

    async def initialize_features(self) -> Dict[str, FeatureStatus]:
        """Initialize and load enabled enterprise features."""
        results = {}
        enabled_features = self.config.get_enabled_features()

        self.logger.info(f"Initializing {len(enabled_features)} enterprise features...")

        for feature_id in enabled_features:
            if feature_id not in self._features:
                self.logger.warning(f"Unknown feature: {feature_id}")
                results[feature_id] = FeatureStatus.ERROR
                continue

            try:
                status = await self._load_feature(feature_id)
                results[feature_id] = status
                self._features[feature_id].status = status
            except Exception as e:
                self.logger.error(f"Failed to load feature {feature_id}: {e}")
                self._features[feature_id].status = FeatureStatus.ERROR
                self._features[feature_id].last_error = str(e)
                results[feature_id] = FeatureStatus.ERROR

                if self.config.fail_fast_on_errors:
                    raise

        return results

    async def _load_feature(self, feature_id: str) -> FeatureStatus:
        """Load and initialize a specific enterprise feature."""
        feature = self._features[feature_id]
        feature.status = FeatureStatus.LOADING

        # Validate dependencies
        for dependency in feature.dependencies:
            if dependency.required and dependency.feature_id not in self.config.get_enabled_features():
                raise ValueError(f"Required dependency {dependency.feature_id} not enabled for {feature_id}")

        # Load module
        try:
            module = importlib.import_module(f".{feature.module_path}", package=__package__)
            self._loaded_modules[feature_id] = module
        except ImportError as e:
            raise ImportError(f"Failed to import {feature.module_path}: {e}")

        # Get feature class
        if not hasattr(module, feature.class_name):
            raise AttributeError(f"Class {feature.class_name} not found in {feature.module_path}")

        feature_class = getattr(module, feature.class_name)

        # Initialize feature instance
        feature_instance = feature_class()

        # Initialize if it has an async initialize method
        if hasattr(feature_instance, 'initialize') and asyncio.iscoroutinefunction(feature_instance.initialize):
            await feature_instance.initialize()

        self._feature_instances[feature_id] = feature_instance

        self.logger.info(f"Successfully loaded enterprise feature: {feature.name}")
        return FeatureStatus.ENABLED

    def get_feature_status(self, feature_id: str) -> FeatureStatus:
        """Get current status of a feature."""
        if feature_id not in self._features:
            return FeatureStatus.ERROR
        return self._features[feature_id].status

    def get_enabled_features_info(self) -> List[Dict[str, Any]]:
        """Get information about all enabled features."""
        enabled_features = self.config.get_enabled_features()
        info = []

        for feature_id in enabled_features:
            if feature_id in self._features:
                feature = self._features[feature_id]
                info.append({
                    "feature_id": feature.feature_id,
                    "name": feature.name,
                    "description": feature.description,
                    "tier": feature.tier.value,
                    "status": feature.status.value,
                    "business_value": feature.business_value,
                    "overhead_ms": feature.estimated_overhead_ms,
                    "memory_mb": feature.memory_overhead_mb,
                    "last_error": feature.last_error
                })

        return info

    def get_feature_instance(self, feature_id: str) -> Optional[Any]:
        """Get loaded instance of a feature."""
        return self._feature_instances.get(feature_id)

    def get_total_overhead(self) -> Dict[str, float]:
        """Calculate total overhead of enabled features."""
        enabled_features = self.config.get_enabled_features()
        total_time_ms = 0
        total_memory_mb = 0

        for feature_id in enabled_features:
            if feature_id in self._features:
                feature = self._features[feature_id]
                total_time_ms += feature.estimated_overhead_ms
                total_memory_mb += feature.memory_overhead_mb

        return {
            "time_overhead_ms": total_time_ms,
            "memory_overhead_mb": total_memory_mb,
            "feature_count": len(enabled_features)
        }


# Global registry instance
_feature_registry: Optional[StellarEnterpriseFeatureRegistry] = None


def get_enterprise_features() -> Optional[StellarEnterpriseFeatureRegistry]:
    """Get the global enterprise features registry."""
    return _feature_registry


def initialize_enterprise_features(config: EnterpriseFeatureConfig) -> StellarEnterpriseFeatureRegistry:
    """Initialize the global enterprise features registry."""
    global _feature_registry
    _feature_registry = StellarEnterpriseFeatureRegistry(config)
    return _feature_registry


# Convenience functions for feature access
def is_feature_enabled(feature_id: str) -> bool:
    """Check if a feature is enabled and loaded."""
    registry = get_enterprise_features()
    if not registry:
        return False
    return registry.get_feature_status(feature_id) == FeatureStatus.ENABLED


def get_feature(feature_id: str) -> Optional[Any]:
    """Get instance of an enabled feature."""
    registry = get_enterprise_features()
    if not registry:
        return None
    return registry.get_feature_instance(feature_id)


# Export main classes and functions
__all__ = [
    "FeatureTier",
    "FeatureStatus",
    "EnterpriseFeatureConfig",
    "StellarEnterpriseFeatureRegistry",
    "initialize_enterprise_features",
    "get_enterprise_features",
    "is_feature_enabled",
    "get_feature"
]
