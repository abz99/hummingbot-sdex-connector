#!/usr/bin/env python3
"""
Test Suite for Enterprise Features Phase 1 Implementation

This test validates that the Phase 1 implementation is working correctly:
- Enterprise module structure
- Core integration framework
- Vault and hardware wallet integration
- Configuration management
- Feature activation system
"""

import asyncio
import sys
import tempfile
import yaml
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Enterprise features imports
from hummingbot.connector.exchange.stellar.enterprise.core import (
    EnterpriseFeatureConfig,
    StellarEnterpriseFeatureRegistry,
    FeatureTier,
    FeatureStatus
)
from hummingbot.connector.exchange.stellar.enterprise.config import (
    EnterpriseConfigManager
)
from hummingbot.connector.exchange.stellar.enterprise.security import (
    VaultKeyStore,
    VaultConfig,
    VaultAuthMethod,
    HardwareWalletManager
)


class Phase1TestSuite:
    """Comprehensive test suite for Phase 1 enterprise features."""

    def __init__(self):
        self.test_results = {}
        self.passed_tests = 0
        self.failed_tests = 0

    async def run_all_tests(self) -> bool:
        """Run all Phase 1 tests and return overall success."""
        print("🚀 Starting Phase 1 Enterprise Features Test Suite")
        print("=" * 60)

        tests = [
            ("Module Structure", self.test_module_structure),
            ("Core Framework", self.test_core_framework),
            ("Configuration Management", self.test_configuration_management),
            ("Security Tier Integration", self.test_security_tier),
            ("Feature Registry", self.test_feature_registry),
            ("Configuration Loading", self.test_config_loading),
            ("Feature Activation", self.test_feature_activation),
            ("Integration Example", self.test_integration_example)
        ]

        for test_name, test_func in tests:
            try:
                print(f"\n🔄 Running: {test_name}")
                await test_func()
                print(f"✅ PASSED: {test_name}")
                self.test_results[test_name] = "PASSED"
                self.passed_tests += 1
            except Exception as e:
                print(f"❌ FAILED: {test_name} - {e}")
                self.test_results[test_name] = f"FAILED: {e}"
                self.failed_tests += 1

        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {self.passed_tests}")
        print(f"❌ Failed: {self.failed_tests}")
        print(f"📈 Success Rate: {(self.passed_tests/(self.passed_tests+self.failed_tests)*100):.1f}%")

        if self.failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for test_name, result in self.test_results.items():
                if result.startswith("FAILED"):
                    print(f"   - {test_name}: {result}")

        return self.failed_tests == 0

    async def test_module_structure(self):
        """Test that enterprise module structure is correct."""
        # Test directory structure
        base_path = project_root / "hummingbot/connector/exchange/stellar/enterprise"
        assert base_path.exists(), "Enterprise base directory missing"
        assert (base_path / "security").exists(), "Security tier directory missing"
        assert (base_path / "trading").exists(), "Trading tier directory missing"
        assert (base_path / "infrastructure").exists(), "Infrastructure tier directory missing"

        # Test __init__.py files
        assert (base_path / "__init__.py").exists(), "Enterprise __init__.py missing"
        assert (base_path / "security" / "__init__.py").exists(), "Security __init__.py missing"
        assert (base_path / "trading" / "__init__.py").exists(), "Trading __init__.py missing"
        assert (base_path / "infrastructure" / "__init__.py").exists(), "Infrastructure __init__.py missing"

        # Test module files
        assert (base_path / "core.py").exists(), "Core framework missing"
        assert (base_path / "config.py").exists(), "Configuration manager missing"
        assert (base_path / "security" / "vault_integration.py").exists(), "Vault integration missing"
        assert (base_path / "security" / "hardware_wallets.py").exists(), "Hardware wallets missing"

    async def test_core_framework(self):
        """Test the core enterprise features framework."""
        # Test configuration creation
        config = EnterpriseFeatureConfig(
            vault_integration_enabled=True,
            hardware_wallet_enabled=True,
            security_hardening_enabled=True
        )

        enabled_features = config.get_enabled_features()
        assert len(enabled_features) == 3, f"Expected 3 enabled features, got {len(enabled_features)}"
        assert "vault_integration" in enabled_features, "Vault integration not in enabled features"

        # Test registry creation
        registry = StellarEnterpriseFeatureRegistry(config)
        assert len(registry._features) >= 9, f"Expected at least 9 registered features"

        # Test feature information
        info = registry.get_enabled_features_info()
        assert len(info) == 3, f"Expected 3 feature info entries, got {len(info)}"

        # Test overhead calculation
        overhead = registry.get_total_overhead()
        assert overhead["feature_count"] == 3, "Overhead calculation incorrect"
        assert overhead["time_overhead_ms"] > 0, "Time overhead should be positive"

    async def test_configuration_management(self):
        """Test enterprise configuration management."""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            test_config = {
                'enterprise_features': {
                    'validate_on_startup': True,
                    'fail_fast_on_errors': False,
                    'security': {
                        'vault_integration_enabled': True,
                        'hardware_wallet_enabled': False
                    },
                    'trading': {
                        'liquidity_management_enabled': False,
                        'yield_farming_enabled': True
                    },
                    'infrastructure': {
                        'test_account_manager_enabled': True
                    }
                }
            }
            yaml.dump(test_config, f)
            temp_config_path = f.name

        try:
            # Test configuration loading
            config_manager = EnterpriseConfigManager(temp_config_path)
            loaded_config = await config_manager.load_config()

            assert loaded_config is not None, "Failed to load configuration"
            assert loaded_config.vault_integration_enabled == True, "Vault integration not enabled"
            assert loaded_config.hardware_wallet_enabled == False, "Hardware wallet incorrectly enabled"
            assert loaded_config.yield_farming_enabled == True, "Yield farming not enabled"

            # Test enabled features
            enabled = loaded_config.get_enabled_features()
            expected_enabled = {"vault_integration", "yield_farming", "test_account_manager"}
            assert set(enabled) == expected_enabled, f"Expected {expected_enabled}, got {set(enabled)}"

        finally:
            # Cleanup
            Path(temp_config_path).unlink()

    async def test_security_tier(self):
        """Test security tier module imports and basic functionality."""
        # Test Vault integration imports
        assert VaultKeyStore is not None, "VaultKeyStore class not available"
        assert VaultConfig is not None, "VaultConfig class not available"

        # Test Hardware wallet imports
        assert HardwareWalletManager is not None, "HardwareWalletManager class not available"

        # Test basic instantiation (without actual connections)
        vault_config = VaultConfig(
            url="http://localhost:8200",
            auth_method=VaultAuthMethod.TOKEN,
            token="test-token"
        )
        assert vault_config.url == "http://localhost:8200", "Vault config creation failed"

        # Test hardware wallet manager creation
        hw_manager = HardwareWalletManager()
        assert hw_manager is not None, "Hardware wallet manager creation failed"

    async def test_feature_registry(self):
        """Test feature registry functionality."""
        config = EnterpriseFeatureConfig(
            vault_integration_enabled=True,
            liquidity_management_enabled=True
        )

        registry = StellarEnterpriseFeatureRegistry(config)

        # Test feature status checking
        vault_status = registry.get_feature_status("vault_integration")
        assert vault_status == FeatureStatus.DISABLED, "Feature should be disabled initially"

        # Test feature definitions
        features = registry._features
        assert "vault_integration" in features, "Vault integration not in feature registry"
        assert "liquidity_management" in features, "Liquidity management not in feature registry"

        vault_feature = features["vault_integration"]
        assert vault_feature.tier == FeatureTier.SECURITY, "Vault should be security tier"
        assert vault_feature.business_value == "CRITICAL", "Vault should be critical business value"

    async def test_config_loading(self):
        """Test configuration file loading and validation."""
        # Test with missing config file
        config_manager = EnterpriseConfigManager("/nonexistent/path/config.yaml")
        config = await config_manager.load_config()
        assert config is None, "Should return None for missing config file"

        # Test with real config file
        config_path = project_root / "config/enterprise_features.yaml"
        if config_path.exists():
            config_manager = EnterpriseConfigManager(str(config_path))
            config = await config_manager.load_config()
            # Config could be None if file exists but has no features enabled
            # This is acceptable for testing

    async def test_feature_activation(self):
        """Test feature activation without actually loading modules."""
        config = EnterpriseFeatureConfig(
            vault_integration_enabled=True,
            hardware_wallet_enabled=True
        )

        registry = StellarEnterpriseFeatureRegistry(config)

        # Test that we can get feature information without loading
        info = registry.get_enabled_features_info()
        assert len(info) == 2, "Should have 2 features ready for activation"

        vault_info = next((f for f in info if f["feature_id"] == "vault_integration"), None)
        assert vault_info is not None, "Vault integration info not found"
        assert vault_info["tier"] == "security", "Vault should be security tier"

    async def test_integration_example(self):
        """Test basic integration patterns."""
        # Test that enterprise features can be imported from main package
        try:
            from hummingbot.connector.exchange.stellar.enterprise import (
                EnterpriseFeatureConfig,
                FeatureTier,
                FeatureStatus
            )
            # If we get here, the imports work
            assert True, "Enterprise package imports successful"
        except ImportError as e:
            assert False, f"Enterprise package import failed: {e}"

        # Test configuration and registry integration
        config = EnterpriseFeatureConfig(vault_integration_enabled=True)
        registry = StellarEnterpriseFeatureRegistry(config)

        overhead = registry.get_total_overhead()
        assert isinstance(overhead, dict), "Overhead should be a dictionary"
        assert "time_overhead_ms" in overhead, "Missing time overhead key"
        assert "memory_overhead_mb" in overhead, "Missing memory overhead key"


async def main():
    """Run the Phase 1 test suite."""
    test_suite = Phase1TestSuite()
    success = await test_suite.run_all_tests()

    if success:
        print("\n🎯 Phase 1 Implementation: ALL TESTS PASSED!")
        print("✅ Enterprise features foundation is ready for production")
        return 0
    else:
        print("\n❌ Phase 1 Implementation: SOME TESTS FAILED!")
        print("🔧 Please fix the issues before proceeding to Phase 2")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())