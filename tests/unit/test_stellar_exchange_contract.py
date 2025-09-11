"""
Stellar Exchange Contract Tests
Test the core StellarExchange connector contract and behavior.

QA_IDs: REQ-EXC-001, REQ-EXC-002, REQ-EXC-003, REQ-PERF-001, REQ-PERF-002
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from decimal import Decimal
from typing import Dict, Any, List
import time
import sys
from pathlib import Path

# Use stub imports for testing - path manipulation before imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from hummingbot_stubs.core.data_type.common import OrderType, TradeType, TokenAmount  # noqa: E402


class TestStellarExchangeInitialization:
    """Test exchange connector initialization and configuration validation.

    QA_ID: REQ-EXC-001 - Exchange connector initialization
    """

    @pytest.fixture
    def mock_stellar_config(self):
        """Mock Stellar network configuration."""
        return {
            "network": "testnet",
            "horizon_urls": ["https://horizon-testnet.stellar.org"],
            "soroban_rpc_urls": ["https://soroban-testnet.stellar.org"],
            "network_passphrase": "Test SDF Network ; September 2015",
            "base_fee": 100,
        }

    @pytest.fixture
    def mock_trading_pairs(self):
        """Mock trading pairs configuration."""
        return ["XLM-USDC", "XLM-AQUA"]

    @patch("hummingbot.connector.exchange.stellar.stellar_chain_interface.ModernStellarChainInterface")
    @patch("hummingbot.connector.exchange.stellar.stellar_order_manager.ModernStellarOrderManager")
    @pytest.mark.asyncio
    async def test_exchange_initialization_success(
        self, mock_order_manager, mock_chain_interface, mock_stellar_config, mock_trading_pairs
    ):
        """Test successful exchange initialization with valid configuration.

        QA_ID: REQ-EXC-001
        Acceptance Criteria: assert exchange.status == ConnectorStatus.CONNECTED
        """
        # Mock successful chain interface initialization
        mock_chain_instance = AsyncMock()
        mock_chain_instance.initialize.return_value = None
        mock_chain_instance.health_check.return_value = {"status": "healthy"}
        mock_chain_interface.return_value = mock_chain_instance

        # Mock successful order manager initialization
        mock_order_instance = AsyncMock()
        mock_order_instance.initialize.return_value = None
        mock_order_manager.return_value = mock_order_instance

        # Import after mocking to avoid import-time issues
        from hummingbot.connector.exchange.stellar.stellar_exchange import StellarExchange
        from hummingbot.core.data_type.common import ConnectorStatus

        # Initialize exchange
        exchange = StellarExchange(
            stellar_config=mock_stellar_config, trading_pairs=mock_trading_pairs, trading_required=True
        )

        # Verify initialization
        await exchange.start_network()

        # Assertions (QA requirement)
        assert exchange.status == ConnectorStatus.CONNECTED
        assert exchange.trading_pairs == mock_trading_pairs
        assert exchange.network_config == mock_stellar_config

        # Verify component initialization
        mock_chain_interface.assert_called_once()
        mock_order_manager.assert_called_once()
        mock_chain_instance.initialize.assert_called_once()

    @patch("hummingbot.connector.exchange.stellar.stellar_chain_interface.ModernStellarChainInterface")
    @pytest.mark.asyncio
    async def test_exchange_initialization_network_failure(self, mock_chain_interface, mock_stellar_config):
        """Test exchange initialization with network connection failure.

        QA_ID: REQ-EXC-001
        Acceptance Criteria: assert exchange.status == ConnectorStatus.DISCONNECTED
        """
        # Mock network connection failure
        mock_chain_instance = AsyncMock()
        mock_chain_instance.initialize.side_effect = ConnectionError("Network unreachable")
        mock_chain_interface.return_value = mock_chain_instance

        from hummingbot.connector.exchange.stellar.stellar_exchange import StellarExchange
        from hummingbot.core.data_type.common import ConnectorStatus

        exchange = StellarExchange(
            stellar_config=mock_stellar_config, trading_pairs=["XLM-USDC"], trading_required=True
        )

        # Expect initialization to fail gracefully
        with pytest.raises(ConnectionError):
            await exchange.start_network()

        assert exchange.status == ConnectorStatus.DISCONNECTED


class TestTradingPairValidation:
    """Test trading pair validation and normalization.

    QA_ID: REQ-EXC-002 - Trading pair validation
    """

    @pytest.fixture
    def exchange_instance(self):
        """Create mock exchange instance."""
        from hummingbot.connector.exchange.stellar.stellar_exchange import StellarExchange

        return StellarExchange(stellar_config={"network": "testnet"}, trading_pairs=[], trading_required=False)

    def test_trading_pair_validation_success(self, exchange_instance):
        """Test validation of properly formatted trading pairs.

        QA_ID: REQ-EXC-002
        Acceptance Criteria: assert 'XLM-USDC' in exchange.trading_pairs
        """
        valid_pairs = ["XLM-USDC", "XLM-AQUA", "USDC-AQUA"]

        # Test validation logic
        validated_pairs = exchange_instance._validate_trading_pairs(valid_pairs)

        # Assertions (QA requirement)
        assert "XLM-USDC" in validated_pairs
        assert len(validated_pairs) == len(valid_pairs)
        assert all(pair in validated_pairs for pair in valid_pairs)

    def test_trading_pair_validation_invalid_format(self, exchange_instance):
        """Test rejection of improperly formatted trading pairs."""
        invalid_pairs = ["XLM_USDC", "XLM/USDC", "XLMUSDC", ""]

        with pytest.raises(ValueError) as exc_info:
            exchange_instance._validate_trading_pairs(invalid_pairs)

        assert "Invalid trading pair format" in str(exc_info.value)

    def test_trading_pair_normalization(self, exchange_instance):
        """Test trading pair normalization to standard format."""
        input_pairs = ["xlm-usdc", "XLM-usdc", "Xlm-Usdc"]
        _expected = ["XLM-USDC"] * 3

        normalized = exchange_instance._normalize_trading_pairs(input_pairs)

        assert all(pair == "XLM-USDC" for pair in normalized)


class TestBalanceQuerying:
    """Test account balance querying functionality.

    QA_ID: REQ-EXC-003 - Balance querying accuracy
    """

    @pytest.fixture
    def mock_account_response(self):
        """Mock Horizon account response."""
        return {
            "balances": [
                {"asset_type": "native", "balance": "1000.0000000"},
                {
                    "asset_type": "credit_alphanum4",
                    "asset_code": "USDC",
                    "asset_issuer": "GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5",
                    "balance": "500.0000000",
                },
            ]
        }

    @patch("hummingbot.connector.exchange.stellar.stellar_chain_interface.ModernStellarChainInterface")
    @pytest.mark.asyncio
    async def test_balance_query_accuracy(self, mock_chain_interface, mock_account_response):
        """Test accurate balance retrieval for all supported assets.

        QA_ID: REQ-EXC-003
        Acceptance Criteria: assert balance.amount == Decimal('1000.0')
        """
        # Mock chain interface
        mock_chain_instance = AsyncMock()
        mock_chain_instance.get_account_balances.return_value = mock_account_response["balances"]
        mock_chain_interface.return_value = mock_chain_instance

        from hummingbot.connector.exchange.stellar.stellar_exchange import StellarExchange

        exchange = StellarExchange(
            stellar_config={"network": "testnet"}, trading_pairs=["XLM-USDC"], trading_required=False
        )
        exchange._chain_interface = mock_chain_instance

        # Query balances
        balances = await exchange.get_account_balances()

        # Assertions (QA requirement)
        xlm_balance = balances.get("XLM")
        usdc_balance = balances.get("USDC")

        assert xlm_balance is not None
        assert xlm_balance.amount == Decimal("1000.0")
        assert usdc_balance.amount == Decimal("500.0")

    @patch("hummingbot.connector.exchange.stellar.stellar_chain_interface.ModernStellarChainInterface")
    @pytest.mark.asyncio
    async def test_balance_query_network_error_handling(self, mock_chain_interface):
        """Test balance query error handling for network failures."""
        # Mock network error
        mock_chain_instance = AsyncMock()
        mock_chain_instance.get_account_balances.side_effect = ConnectionError("Network timeout")
        mock_chain_interface.return_value = mock_chain_instance

        from hummingbot.connector.exchange.stellar.stellar_exchange import StellarExchange

        exchange = StellarExchange(
            stellar_config={"network": "testnet"}, trading_pairs=["XLM-USDC"], trading_required=False
        )
        exchange._chain_interface = mock_chain_instance

        # Should handle error gracefully
        balances = await exchange.get_account_balances()

        # Should return empty dict or cached balances
        assert isinstance(balances, dict)

    @pytest.mark.asyncio
    async def test_balance_caching_mechanism(self):
        """Test balance caching to reduce API calls."""
        # Mock chain interface with call counting
        mock_chain_instance = AsyncMock()
        call_count = 0

        def mock_get_balances(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return [{"asset_type": "native", "balance": "1000.0"}]

        mock_chain_instance.get_account_balances.side_effect = mock_get_balances

        from hummingbot.connector.exchange.stellar.stellar_exchange import StellarExchange

        exchange = StellarExchange(
            stellar_config={"network": "testnet"}, trading_pairs=["XLM-USDC"], trading_required=False
        )
        exchange._chain_interface = mock_chain_instance
        exchange._balance_cache_ttl = 60  # 1 minute cache

        # First call should hit API
        await exchange.get_account_balances()
        assert call_count == 1

        # Second call within cache TTL should use cache
        await exchange.get_account_balances()
        assert call_count == 1  # No additional API call


@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Performance benchmark tests for exchange operations.

    QA_ID: REQ-PERF-001, REQ-PERF-002 - Performance SLA compliance
    """

    @pytest.fixture
    def performance_exchange(self):
        """Create exchange instance optimized for performance testing."""
        from hummingbot.connector.exchange.stellar.stellar_exchange import StellarExchange

        # Mock fast chain interface
        mock_chain = AsyncMock()
        mock_chain.place_order.return_value = {"success": True, "order_id": "test123"}

        exchange = StellarExchange(
            stellar_config={"network": "testnet"}, trading_pairs=["XLM-USDC"], trading_required=False
        )
        exchange._chain_interface = mock_chain

        return exchange

    @pytest.mark.asyncio
    async def test_order_placement_latency_sla(self, performance_exchange):
        """Test order placement latency meets SLA requirements.

        QA_ID: REQ-PERF-001
        Acceptance Criteria: assert percentile_95 < 2.0
        """
        latencies = []
        num_orders = 100

        # Simulate order placements and measure latency
        for i in range(num_orders):
            start_time = time.time()

            await performance_exchange.place_order(
                order_type=OrderType.LIMIT,
                trade_type=TradeType.BUY,
                symbol="XLM-USDC",
                amount=Decimal("100"),
                price=Decimal("0.1"),
            )

            end_time = time.time()
            latencies.append(end_time - start_time)

        # Calculate 95th percentile
        latencies.sort()
        percentile_95_index = int(0.95 * len(latencies))
        percentile_95 = latencies[percentile_95_index]

        # Assertions (QA requirement)
        assert percentile_95 < 2.0, f"95th percentile latency {percentile_95}s exceeds 2s SLA"

        # Additional performance metrics
        avg_latency = sum(latencies) / len(latencies)
        assert avg_latency < 1.0, f"Average latency {avg_latency}s exceeds 1s target"

    @pytest.mark.asyncio
    async def test_concurrent_operations_throughput(self, performance_exchange):
        """Test concurrent operation handling capacity.

        QA_ID: REQ-PERF-002
        Acceptance Criteria: assert success_rate >= 0.95 and avg_latency <= sla_threshold
        """
        concurrent_operations = 50
        sla_threshold = 3.0  # seconds

        # Create concurrent order placement tasks
        async def place_test_order(order_id: int):
            try:
                start_time = time.time()
                await performance_exchange.place_order(
                    order_type=OrderType.LIMIT,
                    trade_type=TradeType.BUY,
                    symbol="XLM-USDC",
                    amount=Decimal("10"),
                    price=Decimal("0.1"),
                )
                end_time = time.time()
                return {"success": True, "latency": end_time - start_time, "order_id": order_id}
            except Exception as e:
                return {"success": False, "error": str(e), "order_id": order_id}

        # Execute concurrent operations
        tasks = [place_test_order(i) for i in range(concurrent_operations)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze results
        successful_ops = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_ops = [r for r in results if not isinstance(r, dict) or not r.get("success")]

        success_rate = len(successful_ops) / len(results)
        latencies = [r["latency"] for r in successful_ops]
        avg_latency = sum(latencies) / len(latencies) if latencies else float("inf")

        # Assertions (QA requirement)
        assert success_rate >= 0.95, f"Success rate {success_rate} below 95% requirement"
        assert avg_latency <= sla_threshold, f"Average latency {avg_latency}s exceeds {sla_threshold}s SLA"

        # Performance diagnostics
        if failed_ops:
            failure_reasons = [r.get("error", "Unknown") for r in failed_ops]
            print(f"Failures: {len(failed_ops)}, Reasons: {set(failure_reasons)}")


class TestExchangeLifecycle:
    """Test exchange lifecycle management (start, stop, restart)."""

    @patch("hummingbot.connector.exchange.stellar.stellar_chain_interface.ModernStellarChainInterface")
    @patch("hummingbot.connector.exchange.stellar.stellar_order_manager.ModernStellarOrderManager")
    @pytest.mark.asyncio
    async def test_exchange_graceful_shutdown(self, mock_order_manager, mock_chain_interface):
        """Test graceful exchange shutdown with resource cleanup."""
        # Mock components
        mock_chain_instance = AsyncMock()
        mock_order_instance = AsyncMock()
        mock_chain_interface.return_value = mock_chain_instance
        mock_order_manager.return_value = mock_order_instance

        from hummingbot.connector.exchange.stellar.stellar_exchange import StellarExchange
        from hummingbot.core.data_type.common import ConnectorStatus

        exchange = StellarExchange(
            stellar_config={"network": "testnet"}, trading_pairs=["XLM-USDC"], trading_required=True
        )

        # Start and then stop exchange
        await exchange.start_network()
        await exchange.stop_network()

        # Verify graceful shutdown
        assert exchange.status == ConnectorStatus.DISCONNECTED
        mock_chain_instance.cleanup.assert_called_once()
        mock_order_instance.cleanup.assert_called_once()


# Test execution utilities
def create_mock_stellar_response(success: bool = True, **kwargs) -> Dict[str, Any]:
    """Utility to create standardized mock Stellar API responses."""
    base_response = {
        "successful": success,
        "hash": "test_transaction_hash_123",
        "ledger": 12345,
        "envelope_xdr": "test_xdr_envelope",
    }
    base_response.update(kwargs)
    return base_response


def assert_order_fields_complete(order) -> None:
    """Utility to verify order object has all required fields."""
    required_fields = ["order_id", "symbol", "amount", "price", "side", "status", "timestamp"]
    for field in required_fields:
        assert hasattr(order, field), f"Order missing required field: {field}"
        assert getattr(order, field) is not None, f"Order field {field} is None"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
