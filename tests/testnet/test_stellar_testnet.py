"""Testnet validation tests for Stellar Hummingbot Connector."""

import pytest
import pytest_asyncio
import asyncio
from decimal import Decimal

from stellar_sdk import Server, Keypair, Network
from hummingbot.connector.exchange.stellar.stellar_exchange import StellarExchange
from tests.fixtures.stellar_component_fixtures import create_testnet_config

# Skip all testnet tests as they require live network connectivity
pytestmark = pytest.mark.skip(reason="Testnet tests require live network connectivity - skipped in CI")


class TestStellarTestnetValidation:
    """Testnet validation tests."""

    @pytest.fixture
    def testnet_config(self):
        """Create testnet configuration."""
        return create_testnet_config()

    @pytest_asyncio.fixture
    async def testnet_exchange(self, testnet_config):
        """Create testnet exchange instance."""
        trading_pairs = ["XLM-USDC", "XLM-BTC"]  # Standard testnet pairs
        exchange = StellarExchange(testnet_config, trading_pairs)
        await exchange.start_network()
        yield exchange
        await exchange.stop_network()

    @pytest.mark.testnet
    @pytest.mark.skip(reason="Testnet tests require live network connectivity - skipped in CI")
    @pytest.mark.asyncio
    async def test_testnet_connectivity(self, testnet_exchange):
        """Test basic testnet connectivity."""
        status = await testnet_exchange.check_network_status()
        assert status.is_connected is True

    @pytest.mark.testnet
    @pytest.mark.skip(reason="Testnet tests require live network connectivity - skipped in CI")
    @pytest.mark.asyncio
    async def test_account_balance_retrieval(self, testnet_exchange):
        """Test account balance retrieval on testnet."""
        balances = await testnet_exchange.get_account_balance()
        assert isinstance(balances, dict)
        assert len(balances) > 0

    @pytest.mark.testnet
    @pytest.mark.asyncio
    async def test_trading_pair_data(self, testnet_exchange):
        """Test trading pair data on testnet."""
        trading_pairs = await testnet_exchange.get_trading_pairs()
        assert len(trading_pairs) > 0

        # Test specific trading pair
        order_book = await testnet_exchange.get_order_book("XLM-USDC")
        assert "bids" in order_book
        assert "asks" in order_book

    @pytest.mark.testnet
    @pytest.mark.asyncio
    async def test_order_creation_testnet(self, testnet_exchange):
        """Test order creation on testnet."""
        try:
            order_id = await testnet_exchange.buy(
                trading_pair="XLM-USDC", amount=Decimal("10"), order_type="LIMIT", price=Decimal("0.1")
            )
            assert order_id is not None

            # Cancel the test order
            cancel_result = await testnet_exchange.cancel_order(order_id)
            assert cancel_result is True

        except Exception as e:
            # Allow for insufficient balance errors in testnet
            if "insufficient" not in str(e).lower():
                raise

    @pytest.mark.testnet
    @pytest.mark.asyncio
    async def test_soroban_contract_interaction(self, testnet_exchange):
        """Test Soroban contract interaction on testnet."""
        if hasattr(testnet_exchange, "soroban_manager"):
            health = await testnet_exchange.soroban_manager.check_health()
            assert health.get("status") in ["healthy", "degraded"]

    @pytest.mark.testnet
    @pytest.mark.asyncio
    async def test_path_payment_simulation(self, testnet_exchange):
        """Test path payment simulation on testnet."""
        if hasattr(testnet_exchange, "path_payment_engine"):
            paths = await testnet_exchange.path_payment_engine.find_paths(
                source_asset="XLM", dest_asset="USDC", amount=Decimal("100")
            )
            assert isinstance(paths, list)

    @pytest.mark.testnet
    @pytest.mark.asyncio
    async def test_fee_calculation_accuracy(self, testnet_exchange):
        """Test fee calculation accuracy on testnet."""
        fees = await testnet_exchange.get_trading_fees()
        assert isinstance(fees, dict)
        assert "maker_percent_fee_decimal" in fees
        assert "taker_percent_fee_decimal" in fees

    @pytest.mark.testnet
    @pytest.mark.asyncio
    async def test_real_time_data_stream(self, testnet_exchange):
        """Test real-time data streaming on testnet."""
        # Start user stream
        await testnet_exchange.start_user_stream()

        # Wait a bit for connection
        await asyncio.sleep(2)

        # Check stream status
        stream_status = testnet_exchange.user_stream_tracker.data_source.ready
        assert stream_status is not False

        # Stop stream
        await testnet_exchange.stop_user_stream()

    @pytest.mark.testnet
    @pytest.mark.asyncio
    async def test_security_validation(self, testnet_exchange):
        """Test security features on testnet."""
        # Test rate limiting
        security_manager = testnet_exchange.security_manager
        assert security_manager is not None

        # Test key validation
        key_valid = security_manager.validate_keys()
        assert key_valid is True

    @pytest.mark.testnet
    @pytest.mark.asyncio
    async def test_network_resilience(self, testnet_exchange):
        """Test network resilience and recovery."""
        # Test connection recovery
        original_status = await testnet_exchange.check_network_status()
        assert original_status.is_connected

        # Simulate brief disconnection and recovery
        await testnet_exchange.stop_network()
        await asyncio.sleep(1)
        await testnet_exchange.start_network()

        # Verify recovery
        recovered_status = await testnet_exchange.check_network_status()
        assert recovered_status.is_connected
