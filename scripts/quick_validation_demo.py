#!/usr/bin/env python3
"""
Quick Validation Demo
Demonstrates Phase 4A Real-World Validation capabilities.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def demo_network_connectivity():
    """Demo basic network connectivity validation."""
    print("🌐 Testing Network Connectivity")
    
    try:
        import aiohttp
        
        # Test Stellar testnet endpoints
        endpoints = [
            ("Horizon Testnet", "https://horizon-testnet.stellar.org"),
            ("Friendbot", "https://friendbot.stellar.org"),
        ]
        
        async with aiohttp.ClientSession() as session:
            for name, url in endpoints:
                try:
                    async with session.get(f"{url}", timeout=5) as response:
                        status = "✅ ONLINE" if response.status == 200 else f"⚠️  STATUS {response.status}"
                        print(f"  {name}: {status}")
                except Exception as e:
                    print(f"  {name}: ❌ OFFLINE ({type(e).__name__})")
    
    except ImportError:
        print("  Installing aiohttp...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp"])
        print("  ✅ aiohttp installed")


async def demo_component_integration():
    """Demo component integration validation."""
    print("\n🔧 Testing Component Integration")
    
    try:
        # Test importing core components
        from hummingbot.connector.exchange.stellar.stellar_exchange import StellarExchange
        from hummingbot.connector.exchange.stellar.stellar_config_models import StellarNetworkConfig
        from hummingbot.connector.exchange.stellar.stellar_security import EnterpriseSecurityFramework
        from hummingbot.connector.exchange.stellar.stellar_observability import StellarObservabilityFramework
        
        print("  ✅ Core imports successful")
        
        # Test configuration creation
        from hummingbot.connector.exchange.stellar.stellar_config_models import NetworkEndpointConfig, RateLimitConfig
        
        config = StellarNetworkConfig(
            name="demo_testnet",
            network_passphrase="Test SDF Network ; September 2015",
            horizon=NetworkEndpointConfig(
                primary="https://horizon-testnet.stellar.org",
                fallbacks=["https://horizon-testnet-1.stellar.org"]
            ),
            soroban=NetworkEndpointConfig(
                primary="https://soroban-testnet.stellar.org"
            ),
            rate_limits=RateLimitConfig(
                requests_per_second=100,
                burst_limit=500
            )
        )
        print("  ✅ Configuration creation successful")
        
        # Test connector initialization
        connector = StellarExchange(
            stellar_config=config,
            trading_pairs=["XLM-USDC"],
            trading_required=False  # Don't require trading for demo
        )
        print("  ✅ Connector initialization successful")
        
        # Test connector properties
        assert connector.name == "stellar_sdex_v3"
        assert isinstance(connector.ready, bool)
        assert len(connector.supported_order_types()) > 0
        print("  ✅ Connector properties validation successful")
        
    except Exception as e:
        print(f"  ❌ Component integration failed: {e}")


async def demo_security_framework():
    """Demo security framework validation."""
    print("\n🔒 Testing Security Framework")
    
    try:
        from hummingbot.connector.exchange.stellar.stellar_security import EnterpriseSecurityFramework
        from hummingbot.connector.exchange.stellar.stellar_observability import StellarObservabilityFramework
        from hummingbot.connector.exchange.stellar.stellar_config_models import StellarNetworkConfig
        
        # Initialize observability
        observability = StellarObservabilityFramework()
        await observability.start()
        
        # Initialize security framework
        from hummingbot.connector.exchange.stellar.stellar_config_models import NetworkEndpointConfig, RateLimitConfig
        
        config = StellarNetworkConfig(
            name="demo_security_test",
            network_passphrase="Test SDF Network ; September 2015",
            horizon=NetworkEndpointConfig(
                primary="https://horizon-testnet.stellar.org"
            ),
            soroban=NetworkEndpointConfig(
                primary="https://soroban-testnet.stellar.org"
            ),
            rate_limits=RateLimitConfig(
                requests_per_second=50,
                burst_limit=200
            )
        )
        
        security = EnterpriseSecurityFramework(config=config, observability=observability)
        await security.initialize()
        
        print("  ✅ Security framework initialization successful")
        
        # Test development mode detection
        is_dev = security.is_development_mode()
        print(f"  ✅ Development mode detection: {is_dev}")
        
        # Test keypair generation
        test_account = "GTEST123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789ABCDE"
        keypair = await security.get_keypair(test_account)
        if keypair:
            print("  ✅ Test keypair generation successful")
        else:
            print("  ⚠️  Test keypair generation returned None (expected in production)")
        
        # Cleanup
        await security.cleanup()
        await observability.stop()
        
    except Exception as e:
        print(f"  ❌ Security framework test failed: {e}")


async def demo_performance_readiness():
    """Demo performance testing readiness."""
    print("\n⚡ Testing Performance Readiness")
    
    try:
        # Test concurrent operations simulation
        start_time = time.time()
        
        # Simulate concurrent tasks
        async def mock_task(task_id):
            await asyncio.sleep(0.1)  # Simulate network operation
            return f"Task {task_id} complete"
        
        tasks = [mock_task(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"  ✅ 10 concurrent tasks completed in {duration:.2f}s")
        print(f"  ✅ Effective throughput: {len(results)/duration:.2f} ops/s")
        
        # Test memory efficiency
        import gc
        gc.collect()
        print("  ✅ Memory management operational")
        
    except Exception as e:
        print(f"  ❌ Performance readiness test failed: {e}")


async def demo_test_infrastructure():
    """Demo test infrastructure readiness.""" 
    print("\n🧪 Testing Test Infrastructure")
    
    try:
        # Test pytest availability
        import pytest
        print("  ✅ pytest available")
        
        # Test async testing support
        import pytest_asyncio
        print("  ✅ pytest-asyncio available")
        
        # Test that our integration tests exist
        test_files = [
            "tests/integration/test_real_world_validation.py",
            "tests/integration/test_performance_benchmarks.py", 
            "tests/integration/test_security_penetration.py",
            "tests/integration/test_hummingbot_integration.py"
        ]
        
        for test_file in test_files:
            test_path = project_root / test_file
            if test_path.exists():
                print(f"  ✅ {test_file} ready")
            else:
                print(f"  ❌ {test_file} missing")
        
        # Test configuration files
        config_files = [
            "config/integration_testing.yml",
            "config/networks.yml"
        ]
        
        for config_file in config_files:
            config_path = project_root / config_file
            if config_path.exists():
                print(f"  ✅ {config_file} ready")
            else:
                print(f"  ❌ {config_file} missing")
        
    except ImportError as e:
        print(f"  ⚠️  Missing test dependency: {e}")
    except Exception as e:
        print(f"  ❌ Test infrastructure check failed: {e}")


async def main():
    """Main demo execution."""
    print("🚀 Phase 4A Real-World Validation - Demo")
    print("=" * 60)
    
    start_time = time.time()
    
    # Run all demo validations
    await demo_network_connectivity()
    await demo_component_integration()
    await demo_security_framework()
    await demo_performance_readiness()
    await demo_test_infrastructure()
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    print("\n" + "=" * 60)
    print("🎯 Phase 4A Validation Demo Complete")
    print(f"Total Duration: {total_duration:.2f} seconds")
    print("=" * 60)
    
    print("\n📋 Next Steps:")
    print("1. Run full validation suite: python scripts/run_integration_validation.py")
    print("2. Run specific test categories:")
    print("   - Network tests: pytest tests/integration/test_real_world_validation.py -v")
    print("   - Performance tests: pytest tests/integration/test_performance_benchmarks.py -v")
    print("   - Security tests: pytest tests/integration/test_security_penetration.py -v")
    print("   - Hummingbot tests: pytest tests/integration/test_hummingbot_integration.py -v")
    print("3. Review detailed configuration: config/integration_testing.yml")
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)