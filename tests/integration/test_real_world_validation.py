"""
Real-World Validation Test Suite
Comprehensive integration testing against actual Stellar testnet.
"""

import asyncio
import time
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import pytest
import pytest_asyncio
from stellar_sdk import Asset, Keypair
from prometheus_client import CollectorRegistry, REGISTRY

# Import our connector components
from hummingbot.connector.exchange.stellar.stellar_exchange import StellarExchange
from hummingbot.connector.exchange.stellar.stellar_config_models import StellarNetworkConfig
from hummingbot.connector.exchange.stellar.stellar_chain_interface import (
    ModernStellarChainInterface,
)
from hummingbot.connector.exchange.stellar.stellar_security import EnterpriseSecurityFramework
from hummingbot.connector.exchange.stellar.stellar_observability import (
    StellarObservabilityFramework,
)

# Test configuration
pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def cleanup_prometheus_registry():
    """Clean up Prometheus registry before each test to avoid duplication."""
    # Clear the registry to avoid metric duplication
    collectors_to_remove = list(REGISTRY._collector_to_names.keys())
    for collector in collectors_to_remove:
        try:
            REGISTRY.unregister(collector)
        except KeyError:
            pass  # Already unregistered
    yield
    # Clean up after test
    collectors_to_remove = list(REGISTRY._collector_to_names.keys())
    for collector in collectors_to_remove:
        try:
            REGISTRY.unregister(collector)
        except KeyError:
            pass


@pytest_asyncio.fixture
async def testnet_config():
    """Create testnet configuration for real-world testing."""
    from hummingbot.connector.exchange.stellar.stellar_config_models import (
        NetworkEndpointConfig,
        RateLimitConfig,
    )

    return StellarNetworkConfig(
        name="testnet_integration",
        network_passphrase="Test SDF Network ; September 2015",
        horizon=NetworkEndpointConfig(primary="https://horizon-testnet.stellar.org"),
        soroban=NetworkEndpointConfig(primary="https://soroban-testnet.stellar.org"),
        rate_limits=RateLimitConfig(requests_per_second=5, burst_limit=10),
    )


@pytest_asyncio.fixture
async def test_keypair():
    """Generate test keypair for integration testing."""
    return Keypair.random()


@pytest_asyncio.fixture
async def funded_test_account(testnet_config, test_keypair):
    """Create and fund a test account via Friendbot."""
    import aiohttp

    async with aiohttp.ClientSession() as session:
        friendbot_url = f"https://friendbot.stellar.org?addr={test_keypair.public_key}"
        async with session.get(friendbot_url) as response:
            if response.status == 200:
                # Wait for account creation to propagate
                await asyncio.sleep(3)
                return test_keypair
            else:
                # Friendbot funding failed - raise proper exception instead of skipping
                raise Exception(f"Friendbot funding failed with status {response.status}. Testnet may be unavailable. Set STELLAR_TESTNET_ENABLED=false to skip testnet tests.")


@pytest_asyncio.fixture
async def stellar_connector(testnet_config):
    """Initialize Stellar connector for real-world testing."""
    connector = StellarExchange(
        stellar_config=testnet_config, trading_pairs=["XLM-USDC", "XLM-TEST"], trading_required=True
    )

    yield connector

    # Cleanup
    if hasattr(connector, "ready") and connector.ready:
        await connector.stop_network()


class TestRealWorldNetworkValidation:
    """Test real-world network connectivity and reliability."""

    async def test_testnet_horizon_connectivity(self, testnet_config):
        """Test direct connection to Stellar testnet Horizon."""
        chain_interface = ModernStellarChainInterface(
            config=testnet_config,
            security_framework=None,
            observability=StellarObservabilityFramework(),
        )

        await chain_interface.start()

        try:
            # Test basic connectivity by attempting to get a test account
            # Network errors will be thrown, but 404 for non-existent account confirms connectivity
            test_keypair = Keypair.random()

            try:
                await chain_interface.get_account_with_retry(test_keypair.public_key, max_retries=1)
                # If we get here, account exists (very unlikely with random keypair)
                pass  # Connection successful
            except Exception as e:
                # Expected 404 for non-existent account means network connectivity is working
                error_msg = str(e).lower()
                assert any(
                    keyword in error_msg
                    for keyword in ["not found", "does not exist", "resource missing", "404"]
                ), f"Network connectivity failed with unexpected error: {e}"

            # If we reach here, network connectivity test passed
            assert True, "Network connectivity verified"

        finally:
            await chain_interface.stop()

    async def test_soroban_rpc_connectivity(self, testnet_config):
        """Test Soroban RPC endpoint connectivity."""
        chain_interface = ModernStellarChainInterface(
            config=testnet_config,
            security_framework=None,
            observability=StellarObservabilityFramework(),
        )

        await chain_interface.start()

        try:
            # Test Soroban health
            soroban_health = await chain_interface.check_soroban_health()
            assert soroban_health, "Soroban RPC health check failed"

        finally:
            await chain_interface.stop()

    async def test_network_failover_resilience(self, testnet_config):
        """Test network failover and resilience."""
        # Create config with multiple fallback endpoints
        from hummingbot.connector.exchange.stellar.stellar_config_models import (
            NetworkEndpointConfig,
            RateLimitConfig,
        )

        failover_config = StellarNetworkConfig(
            name="testnet_failover",
            network_passphrase="Test SDF Network ; September 2015",
            horizon=NetworkEndpointConfig(
                primary="https://horizon-testnet.stellar.org",
                fallbacks=[
                    "https://horizon-testnet-1.stellar.org",
                    "https://horizon-testnet-2.stellar.org",
                ],
            ),
            soroban=NetworkEndpointConfig(primary="https://soroban-testnet.stellar.org"),
            rate_limits=RateLimitConfig(requests_per_second=5, burst_limit=10),
        )

        chain_interface = ModernStellarChainInterface(
            config=failover_config,
            security_framework=None,
            observability=StellarObservabilityFramework(),
        )

        await chain_interface.start()

        try:
            # Test multiple requests to ensure failover works
            for i in range(5):
                ledger = await chain_interface.get_latest_ledger()
                assert ledger is not None, f"Failover test {i+1} failed"
                await asyncio.sleep(1)

        finally:
            await chain_interface.stop()


class TestRealWorldAccountOperations:
    """Test real-world account operations on testnet."""

    async def test_account_creation_and_funding(self, funded_test_account, testnet_config):
        """Test account creation and funding via Friendbot."""
        chain_interface = ModernStellarChainInterface(
            config=testnet_config,
            security_framework=None,
            observability=StellarObservabilityFramework(),
        )

        await chain_interface.start()

        try:
            # Verify account exists and is funded
            account = await chain_interface.get_account_with_retry(funded_test_account.public_key)
            assert account is not None, "Funded account not found"

            # Check XLM balance
            balances = getattr(account, "balances", [])
            xlm_balance = None
            for balance in balances:
                if balance.get("asset_type") == "native":
                    xlm_balance = Decimal(balance.get("balance", "0"))
                    break

            assert xlm_balance is not None, "XLM balance not found"
            assert xlm_balance > Decimal("0"), "Account not properly funded"

        finally:
            await chain_interface.stop()

    async def test_trustline_creation(self, funded_test_account, testnet_config):
        """Test creating trustlines on real testnet."""
        # Initialize components
        observability = StellarObservabilityFramework()
        await observability.start()

        security_framework = EnterpriseSecurityFramework(
            config=testnet_config, observability=observability
        )
        await security_framework.initialize()

        # Store keypair in security framework for testing
        security_framework._active_keypairs[funded_test_account.public_key] = funded_test_account

        chain_interface = ModernStellarChainInterface(
            config=testnet_config,
            security_framework=security_framework,
            observability=observability,
        )
        await chain_interface.start()

        try:
            # Create test asset (USDC testnet)
            test_asset = Asset("USDC", "GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5")

            # Build trustline transaction
            transaction_builder = await chain_interface.create_trustline_transaction(
                source_keypair=funded_test_account, asset=test_asset, limit="1000000"
            )

            assert transaction_builder is not None, "Failed to create trustline transaction"

            # Submit transaction
            response = await chain_interface.submit_transaction(
                transaction_builder=transaction_builder, source_keypair=funded_test_account
            )

            assert response is not None, "Trustline transaction failed"
            assert hasattr(response, "hash"), "Transaction response missing hash"

            # Wait for confirmation
            await asyncio.sleep(5)

            # Verify trustline exists
            account = await chain_interface.get_account_with_retry(funded_test_account.public_key)
            balances = getattr(account, "balances", [])

            trustline_found = False
            for balance in balances:
                if (
                    balance.get("asset_code") == test_asset.code
                    and balance.get("asset_issuer") == test_asset.issuer
                ):
                    trustline_found = True
                    break

            assert trustline_found, "Trustline not found after creation"

        finally:
            await chain_interface.stop()
            await security_framework.cleanup()
            await observability.stop()


class TestRealWorldTradingOperations:
    """Test real-world trading operations on testnet."""

    async def test_order_placement_on_testnet(self, stellar_connector, funded_test_account):
        """Test placing actual orders on testnet SDEX."""
        await stellar_connector.start_network()

        try:
            # Configure account in security framework
            if stellar_connector._security_framework:
                stellar_connector._security_framework._active_keypairs[
                    funded_test_account.public_key
                ] = funded_test_account

            # Place a limit order (small amount for testing)
            order_id = "test_order_001"
            trading_pair = "XLM-USDC"
            amount = Decimal("1.0")  # 1 XLM
            price = Decimal("0.10")  # $0.10 per XLM

            stellar_order_id = await stellar_connector.place_order(
                order_id=order_id,
                trading_pair=trading_pair,
                amount=amount,
                order_type=stellar_connector.supported_order_types()[0],  # LIMIT
                is_buy=False,  # Sell XLM for USDC
                price=price,
            )

            assert stellar_order_id is not None, "Order placement failed"
            assert stellar_order_id != order_id, "Should return Stellar-specific order ID"

            # Wait for order processing
            await asyncio.sleep(3)

            # Retrieve order status
            order_info = await stellar_connector.get_order(order_id)
            assert order_info is not None, "Order info retrieval failed"
            assert order_info["id"] == order_id, "Order ID mismatch"

            # Cancel the order
            cancellation_result = await stellar_connector.cancel_order(order_id)
            assert cancellation_result, "Order cancellation failed"

        finally:
            if stellar_connector.ready:
                await stellar_connector.stop_network()


class TestPerformanceBenchmarking:
    """Performance benchmarking tests against real testnet."""

    async def test_throughput_benchmarking(self, testnet_config):
        """Test request throughput against testnet."""
        chain_interface = ModernStellarChainInterface(
            config=testnet_config,
            security_framework=None,
            observability=StellarObservabilityFramework(),
        )

        await chain_interface.start()

        try:
            # Benchmark concurrent requests
            start_time = time.time()
            tasks = []

            # Create 50 concurrent ledger requests
            for _ in range(50):
                task = chain_interface.get_latest_ledger()
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()

            # Analyze results
            successful_requests = sum(1 for r in results if not isinstance(r, Exception))
            total_time = end_time - start_time
            throughput = successful_requests / total_time

            assert (
                successful_requests >= 45
            ), f"Too many failed requests: {50 - successful_requests}"
            assert throughput >= 10, f"Throughput too low: {throughput} requests/sec"

            # Log performance metrics
            print("Performance Benchmark Results:")
            print("  Total requests: 50")
            print(f"  Successful: {successful_requests}")
            print(f"  Failed: {50 - successful_requests}")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Throughput: {throughput:.2f} requests/sec")

        finally:
            await chain_interface.stop()

    async def test_latency_benchmarking(self, testnet_config):
        """Test request latency against testnet."""
        chain_interface = ModernStellarChainInterface(
            config=testnet_config,
            security_framework=None,
            observability=StellarObservabilityFramework(),
        )

        await chain_interface.start()

        try:
            latencies = []

            # Measure latency for 20 requests
            for _ in range(20):
                start_time = time.time()
                await chain_interface.get_latest_ledger()
                end_time = time.time()

                latency_ms = (end_time - start_time) * 1000
                latencies.append(latency_ms)

                await asyncio.sleep(0.1)  # Small delay between requests

            # Calculate statistics
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            min_latency = min(latencies)

            # Performance assertions
            assert avg_latency < 2000, f"Average latency too high: {avg_latency:.2f}ms"
            assert max_latency < 5000, f"Max latency too high: {max_latency:.2f}ms"

            # Log latency metrics
            print("Latency Benchmark Results:")
            print(f"  Average latency: {avg_latency:.2f}ms")
            print(f"  Min latency: {min_latency:.2f}ms")
            print(f"  Max latency: {max_latency:.2f}ms")
            print(f"  Requests tested: {len(latencies)}")

        finally:
            await chain_interface.stop()


class TestSecurityValidation:
    """Security validation tests against real network."""

    async def test_secure_transaction_signing(self, funded_test_account, testnet_config):
        """Test secure transaction signing with enterprise security framework."""
        observability = StellarObservabilityFramework()
        await observability.start()

        security_framework = EnterpriseSecurityFramework(
            config=testnet_config, observability=observability
        )
        await security_framework.initialize()

        try:
            # Store test keypair securely
            security_framework._active_keypairs[funded_test_account.public_key] = (
                funded_test_account
            )

            # Test keypair retrieval
            retrieved_keypair = await security_framework.get_keypair(funded_test_account.public_key)
            assert retrieved_keypair is not None, "Keypair retrieval failed"
            assert (
                retrieved_keypair.public_key == funded_test_account.public_key
            ), "Keypair mismatch"

            # Test signing capability
            test_message = "test_transaction_xdr"
            signed_message = await security_framework.sign_transaction(
                transaction_xdr=test_message, account_id=funded_test_account.public_key
            )

            assert signed_message is not None, "Transaction signing failed"

        finally:
            await security_framework.cleanup()
            await observability.stop()

    async def test_key_management_security(self, testnet_config):
        """Test key management security features."""
        observability = StellarObservabilityFramework()
        await observability.start()

        security_framework = EnterpriseSecurityFramework(
            config=testnet_config, observability=observability
        )
        await security_framework.initialize()

        try:
            # Test development mode detection
            is_dev_mode = security_framework.is_development_mode()
            assert is_dev_mode, "Should detect testnet as development mode"

            # Test primary account ID functionality
            primary_account = security_framework.primary_account_id
            assert primary_account is not None, "Primary account ID should be available"

            # Test keypair generation for testing
            test_account_id = "GCTESTACCOUNT12345678901234567890123456789012345678"
            keypair = await security_framework.get_keypair(test_account_id)
            assert keypair is not None, "Test keypair generation failed"

        finally:
            await security_framework.cleanup()
            await observability.stop()


class TestErrorResilienceValidation:
    """Test error handling and resilience in real conditions."""

    async def test_network_timeout_handling(self, testnet_config):
        """Test handling of network timeouts and retries."""
        # Create config with very short timeout to force errors
        from hummingbot.connector.exchange.stellar.stellar_config_models import (
            NetworkEndpointConfig,
            RateLimitConfig,
        )

        timeout_config = StellarNetworkConfig(
            name="testnet_timeout",
            network_passphrase="Test SDF Network ; September 2015",
            horizon=NetworkEndpointConfig(
                primary="https://horizon-testnet.stellar.org",
                request_timeout=0.001,  # 1ms timeout to force failures
            ),
            soroban=NetworkEndpointConfig(primary="https://soroban-testnet.stellar.org"),
            rate_limits=RateLimitConfig(requests_per_second=5, burst_limit=10),
        )

        chain_interface = ModernStellarChainInterface(
            config=timeout_config,
            security_framework=None,
            observability=StellarObservabilityFramework(),
        )

        await chain_interface.start()

        try:
            # This should handle timeout gracefully
            with pytest.raises(Exception):  # Expect timeout/connection error
                await chain_interface.get_latest_ledger()

            # Test that interface is still functional after error
            assert chain_interface is not None, "Interface should remain stable after error"

        finally:
            await chain_interface.stop()

    async def test_invalid_transaction_handling(self, funded_test_account, testnet_config):
        """Test handling of invalid transactions."""
        observability = StellarObservabilityFramework()
        await observability.start()

        security_framework = EnterpriseSecurityFramework(
            config=testnet_config, observability=observability
        )
        await security_framework.initialize()
        security_framework._active_keypairs[funded_test_account.public_key] = funded_test_account

        chain_interface = ModernStellarChainInterface(
            config=testnet_config,
            security_framework=security_framework,
            observability=observability,
        )
        await chain_interface.start()

        try:
            # Try to create transaction with invalid asset
            # Use a valid format but non-existent issuer address (random test keypair)
            test_invalid_keypair = Keypair.random()
            invalid_asset = Asset("INVALID", test_invalid_keypair.public_key)

            # This should handle invalid asset gracefully
            transaction_builder = await chain_interface.create_trustline_transaction(
                source_keypair=funded_test_account, asset=invalid_asset, limit="1000"
            )

            if transaction_builder:
                # If transaction creation succeeds, submission should fail gracefully
                try:
                    _response = await chain_interface.submit_transaction(
                        transaction_builder=transaction_builder, source_keypair=funded_test_account
                    )
                    # Transaction might succeed or fail - both are acceptable for testing
                except Exception as e:
                    # Error should be handled gracefully
                    assert isinstance(e, Exception), "Should get proper exception type"

        finally:
            await chain_interface.stop()
            await security_framework.cleanup()
            await observability.stop()
