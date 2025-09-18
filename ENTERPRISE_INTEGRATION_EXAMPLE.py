"""
Example: Enterprise Features Integration with Stellar Exchange
Demonstrates how to integrate enterprise features into the main connector.
"""

import asyncio
import yaml
from pathlib import Path
from typing import Any, Dict, Optional

# Import the enterprise features framework
from hummingbot.connector.exchange.stellar.stellar_enterprise_features import (
    EnterpriseFeatureConfig,
    StellarEnterpriseFeatureRegistry,
    initialize_enterprise_features,
    is_feature_enabled,
    get_feature
)


class EnterpriseEnabledStellarExchange:
    """
    Example of how the main StellarExchange would be enhanced with enterprise features.
    This shows the integration pattern without modifying the existing exchange.
    """

    def __init__(self, config_path: str = "config/enterprise_features.yaml"):
        self.config_path = config_path
        self.enterprise_config: Optional[EnterpriseFeatureConfig] = None
        self.feature_registry: Optional[StellarEnterpriseFeatureRegistry] = None

        # Core exchange components (existing)
        self._core_initialized = False
        self._enterprise_initialized = False

    async def initialize(self) -> None:
        """Initialize both core exchange and enterprise features."""

        # 1. Initialize core exchange functionality (existing code)
        await self._initialize_core_exchange()

        # 2. Load and initialize enterprise features
        await self._initialize_enterprise_features()

    async def _initialize_core_exchange(self) -> None:
        """Initialize the core Stellar exchange functionality."""
        print("🔄 Initializing core Stellar exchange...")

        # This would be the existing StellarExchange initialization
        # - Chain interface setup
        # - Order manager initialization
        # - Asset manager setup
        # - Error handler configuration
        # - Observability framework

        self._core_initialized = True
        print("✅ Core Stellar exchange initialized")

    async def _initialize_enterprise_features(self) -> None:
        """Load and initialize enterprise features based on configuration."""
        print("🏢 Initializing enterprise features...")

        try:
            # Load enterprise configuration
            self.enterprise_config = await self._load_enterprise_config()

            if not self.enterprise_config:
                print("ℹ️  No enterprise features configured")
                return

            # Initialize feature registry
            self.feature_registry = initialize_enterprise_features(self.enterprise_config)

            # Load enabled features
            feature_results = await self.feature_registry.initialize_features()

            # Report results
            self._report_feature_status(feature_results)

            # Configure feature integrations
            await self._configure_feature_integrations()

            self._enterprise_initialized = True
            print("✅ Enterprise features initialized")

        except Exception as e:
            print(f"❌ Failed to initialize enterprise features: {e}")
            if self.enterprise_config and self.enterprise_config.fail_fast_on_errors:
                raise

    async def _load_enterprise_config(self) -> Optional[EnterpriseFeatureConfig]:
        """Load enterprise features configuration from YAML file."""
        config_file = Path(self.config_path)

        if not config_file.exists():
            print(f"ℹ️  Enterprise config file not found: {self.config_path}")
            return None

        try:
            with open(config_file, 'r') as f:
                yaml_config = yaml.safe_load(f)

            # Extract feature flags from YAML
            features = yaml_config.get('enterprise_features', {})
            security = features.get('security', {})
            trading = features.get('trading', {})
            infrastructure = features.get('infrastructure', {})

            return EnterpriseFeatureConfig(
                # Security features
                vault_integration_enabled=security.get('vault_integration_enabled', False),
                hardware_wallet_enabled=security.get('hardware_wallet_enabled', False),
                security_hardening_enabled=security.get('security_hardening_enabled', False),
                security_metrics_enabled=security.get('security_metrics_enabled', False),

                # Trading features
                liquidity_management_enabled=trading.get('liquidity_management_enabled', False),
                yield_farming_enabled=trading.get('yield_farming_enabled', False),

                # Infrastructure features
                test_account_manager_enabled=infrastructure.get('test_account_manager_enabled', False),
                load_testing_enabled=infrastructure.get('load_testing_enabled', False),
                performance_optimizer_enabled=infrastructure.get('performance_optimizer_enabled', False),
                web_assistant_enabled=infrastructure.get('web_assistant_enabled', False),
                user_stream_tracker_enabled=infrastructure.get('user_stream_tracker_enabled', False),

                # Global settings
                validate_on_startup=features.get('validate_on_startup', True),
                fail_fast_on_errors=features.get('fail_fast_on_errors', False)
            )

        except Exception as e:
            print(f"❌ Failed to load enterprise config: {e}")
            return None

    def _report_feature_status(self, feature_results: Dict[str, Any]) -> None:
        """Report the status of enterprise feature initialization."""
        if not feature_results:
            return

        print("\n📊 Enterprise Features Status:")
        print("=" * 50)

        for feature_id, status in feature_results.items():
            status_icon = "✅" if status.value == "enabled" else "❌"
            print(f"{status_icon} {feature_id}: {status.value}")

        # Show overhead information
        if self.feature_registry:
            overhead = self.feature_registry.get_total_overhead()
            print(f"\n📈 Total Overhead:")
            print(f"   Time: {overhead['time_overhead_ms']}ms")
            print(f"   Memory: {overhead['memory_overhead_mb']}MB")
            print(f"   Features: {overhead['feature_count']}")

    async def _configure_feature_integrations(self) -> None:
        """Configure how enterprise features integrate with core exchange."""

        # Example: Vault Integration
        if is_feature_enabled('vault_integration'):
            vault = get_feature('vault_integration')
            if vault:
                print("🔐 Configuring Vault integration for key management...")
                # This would replace the default key manager with vault-backed storage
                # self._key_manager = VaultKeyManager(vault)

        # Example: Hardware Wallet Integration
        if is_feature_enabled('hardware_wallet'):
            hw_wallet = get_feature('hardware_wallet')
            if hw_wallet:
                print("🔒 Configuring hardware wallet integration...")
                # This would add hardware wallet as a signing option
                # self._signing_providers.append(hw_wallet)

        # Example: Security Hardening
        if is_feature_enabled('security_hardening'):
            hardening = get_feature('security_hardening')
            if hardening:
                print("🛡️  Applying security hardening policies...")
                # This would apply security policies to all components
                # await hardening.apply_security_policies(self)

        # Example: Liquidity Management
        if is_feature_enabled('liquidity_management'):
            liquidity_mgr = get_feature('liquidity_management')
            if liquidity_mgr:
                print("💰 Enabling advanced liquidity management...")
                # This would replace basic order management with advanced algorithms
                # self._order_manager = AdvancedOrderManager(liquidity_mgr)

        # Example: Performance Optimization
        if is_feature_enabled('performance_optimizer'):
            optimizer = get_feature('performance_optimizer')
            if optimizer:
                print("⚡ Applying performance optimizations...")
                # This would tune connection pools, caches, etc.
                # await optimizer.optimize_exchange(self)

    # Example: Enterprise feature usage in trading operations
    async def place_order_enterprise(self, order_data: Dict[str, Any]) -> str:
        """Example of how trading operations would use enterprise features."""

        # Use hardware wallet for signing if available
        if is_feature_enabled('hardware_wallet'):
            hw_wallet = get_feature('hardware_wallet')
            # Sign with hardware wallet
            signature = await hw_wallet.sign_transaction(order_data)
            order_data['signature'] = signature
            print("🔒 Order signed with hardware wallet")

        # Use advanced liquidity management if available
        if is_feature_enabled('liquidity_management'):
            liquidity_mgr = get_feature('liquidity_management')
            # Optimize order parameters
            optimized_order = await liquidity_mgr.optimize_order(order_data)
            order_data.update(optimized_order)
            print("💰 Order optimized with liquidity management")

        # Use security metrics for monitoring
        if is_feature_enabled('security_metrics'):
            security_metrics = get_feature('security_metrics')
            # Log security event
            await security_metrics.log_trading_event('order_placed', order_data)
            print("📊 Security event logged")

        # Place the order (this would be the core exchange logic)
        order_id = f"stellar_order_{len(order_data)}"
        print(f"✅ Order placed: {order_id}")

        return order_id

    async def get_enterprise_status(self) -> Dict[str, Any]:
        """Get comprehensive status of enterprise features."""
        if not self.feature_registry:
            return {"enterprise_enabled": False}

        return {
            "enterprise_enabled": True,
            "features": self.feature_registry.get_enabled_features_info(),
            "overhead": self.feature_registry.get_total_overhead(),
            "core_initialized": self._core_initialized,
            "enterprise_initialized": self._enterprise_initialized
        }


# Example usage and demonstration
async def main():
    """Demonstrate enterprise features integration."""
    print("🚀 Stellar Enterprise Features Integration Demo")
    print("=" * 60)

    # Initialize exchange with enterprise features
    exchange = EnterpriseEnabledStellarExchange()
    await exchange.initialize()

    print("\n" + "=" * 60)

    # Show enterprise status
    status = await exchange.get_enterprise_status()
    if status["enterprise_enabled"]:
        print(f"🏢 Enterprise Features: {len(status['features'])} enabled")
    else:
        print("🏢 Enterprise Features: Disabled")

    # Demonstrate enterprise-enhanced trading
    if status["enterprise_enabled"]:
        print("\n🔄 Demonstrating enterprise-enhanced order placement...")
        order_data = {
            "symbol": "XLM/USDC",
            "side": "buy",
            "amount": 100.0,
            "price": 0.12
        }
        order_id = await exchange.place_order_enterprise(order_data)
        print(f"📝 Order result: {order_id}")

    print("\n✅ Demo completed!")


if __name__ == "__main__":
    asyncio.run(main())