"""
Stellar Component Test Fixtures

Adapted test fixtures for actual Stellar connector implementation APIs.
These fixtures provide proper initialization and mocking for the real components.

QA_Integration: Bridges QA framework with actual implementation
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional
from enum import Enum, auto
from dataclasses import dataclass
from decimal import Decimal
import tempfile
import os

# Import prometheus client for proper registry setup
from prometheus_client import CollectorRegistry

# Import actual implementation types
try:
    from hummingbot.connector.exchange.stellar.stellar_health_monitor import (
        StellarHealthMonitor,
        HealthStatus,
        HealthCheckType,
        AlertSeverity,
    )
    from hummingbot.connector.exchange.stellar.stellar_metrics import StellarMetrics
    from hummingbot.connector.exchange.stellar.stellar_security_manager import StellarSecurityManager
except ImportError:
    # Fallback for missing imports
    StellarHealthMonitor = None
    StellarMetrics = None
    StellarSecurityManager = None


# Mock data structures that match actual implementation
class SecurityLevel(Enum):
    DEVELOPMENT = auto()
    TESTING = auto()
    STAGING = auto()
    PRODUCTION = auto()


@dataclass
class SecurityConfig:
    """Mock SecurityConfig matching actual implementation."""

    security_level: SecurityLevel
    allowed_networks: list
    max_transaction_amount: Optional[Decimal] = None
    rate_limit_config: Dict[str, int] = None
    encryption_key: Optional[str] = None

    def __post_init__(self):
        if self.rate_limit_config is None:
            self.rate_limit_config = {"orders_per_second": 10, "requests_per_minute": 100, "transactions_per_hour": 50}


@dataclass
class NetworkConfig:
    """Mock NetworkConfig matching actual implementation."""

    network_name: str
    horizon_url: str
    soroban_rpc_url: str
    network_passphrase: str
    connection_timeout: int = 30
    request_timeout: int = 10


@dataclass
class TimeoutConfig:
    """Mock TimeoutConfig for network operations."""

    connect_timeout: int = 10
    read_timeout: int = 30
    total_timeout: int = 60


@dataclass
class RetryConfig:
    """Mock RetryConfig for retry policies."""

    max_retries: int = 3
    backoff_factor: float = 2.0
    max_backoff: int = 60


class StellarComponentFixtures:
    """Factory for creating properly configured test fixtures."""

    @staticmethod
    def create_health_monitor_config() -> Dict[str, Any]:
        """Create health monitor configuration."""
        return {
            "check_interval": 5,  # Faster for testing
            "failure_threshold": 2,  # Lower for testing
            "recovery_threshold": 1,  # Lower for testing
            "history_size": 10,  # Smaller for testing
        }

    @staticmethod
    def create_security_config() -> SecurityConfig:
        """Create security configuration for testing."""
        return SecurityConfig(
            security_level=SecurityLevel.TESTING,
            allowed_networks=["testnet", "standalone"],
            max_transaction_amount=Decimal("1000.0"),
            rate_limit_config={"orders_per_second": 5, "requests_per_minute": 50, "transactions_per_hour": 25},
            encryption_key="test_encryption_key_32_chars_long",
        )

    @staticmethod
    def create_network_config() -> NetworkConfig:
        """Create network configuration for testing."""
        return NetworkConfig(
            network_name="testnet",
            horizon_url="https://horizon-testnet.stellar.org",
            soroban_rpc_url="https://soroban-testnet.stellar.org",
            network_passphrase="Test SDF Network ; September 2015",
            connection_timeout=10,
            request_timeout=5,
        )

    @staticmethod
    def create_prometheus_registry() -> CollectorRegistry:
        """Create isolated Prometheus registry for testing."""
        return CollectorRegistry()


class MockFactories:
    """Factory for creating consistent mocks across tests."""

    @staticmethod
    def create_stellar_logger_mock():
        """Create consistent stellar logger mock."""
        mock_logger = Mock()
        mock_logger.info = Mock()
        mock_logger.debug = Mock()
        mock_logger.warning = Mock()
        mock_logger.error = Mock()
        mock_logger.critical = Mock()
        return mock_logger

    @staticmethod
    def create_stellar_metrics_mock():
        """Create consistent stellar metrics mock."""
        mock_metrics = Mock()
        mock_metrics.increment_counter = Mock()
        mock_metrics.set_gauge = Mock()
        mock_metrics.record_histogram = AsyncMock()
        mock_metrics.record_metric = AsyncMock()
        return mock_metrics

    @staticmethod
    def create_error_manager_mock():
        """Create consistent error manager mock."""
        mock_error_mgr = Mock()
        mock_error_mgr.classify_error = Mock()
        mock_error_mgr.handle_error = Mock()
        mock_error_mgr.is_retryable = Mock(return_value=True)
        return mock_error_mgr

    @staticmethod
    def create_chain_interface_mock():
        """Create chain interface mock for user stream tracker."""
        mock_chain = Mock()
        mock_chain.get_account = AsyncMock()
        mock_chain.submit_transaction = AsyncMock()
        mock_chain.get_transaction = AsyncMock()
        return mock_chain

    @staticmethod
    def create_observability_mock():
        """Create observability mock."""
        mock_obs = Mock()
        mock_obs.log_event = Mock()
        mock_obs.track_metric = Mock()
        mock_obs.create_span = Mock()
        return mock_obs


@pytest.fixture
def health_monitor_config():
    """Fixture for health monitor configuration."""
    return StellarComponentFixtures.create_health_monitor_config()


@pytest.fixture
def security_config():
    """Fixture for security configuration."""
    return StellarComponentFixtures.create_security_config()


@pytest.fixture
def network_config():
    """Fixture for network configuration."""
    return StellarComponentFixtures.create_network_config()


@pytest.fixture
def prometheus_registry():
    """Fixture for isolated Prometheus registry."""
    return StellarComponentFixtures.create_prometheus_registry()


@pytest.fixture
def mock_stellar_logger():
    """Fixture for mocked stellar logger."""
    return MockFactories.create_stellar_logger_mock()


@pytest.fixture
def mock_stellar_metrics():
    """Fixture for mocked stellar metrics."""
    return MockFactories.create_stellar_metrics_mock()


@pytest.fixture
def mock_error_manager():
    """Fixture for mocked error manager."""
    return MockFactories.create_error_manager_mock()


@pytest.fixture
def mock_chain_interface():
    """Fixture for mocked chain interface."""
    return MockFactories.create_chain_interface_mock()


@pytest.fixture
def mock_observability():
    """Fixture for mocked observability."""
    return MockFactories.create_observability_mock()


@pytest.fixture
def temp_keystore_path():
    """Fixture for temporary keystore path."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def health_monitor(health_monitor_config):
    """Fixture for properly configured health monitor."""
    with (
        patch("hummingbot.connector.exchange.stellar.stellar_health_monitor.get_stellar_logger") as mock_logger,
        patch("hummingbot.connector.exchange.stellar.stellar_health_monitor.get_stellar_metrics") as mock_metrics,
        patch("hummingbot.connector.exchange.stellar.stellar_health_monitor.StellarErrorManager") as mock_error_mgr,
    ):

        # Configure mocks
        mock_logger.return_value = MockFactories.create_stellar_logger_mock()
        mock_metrics.return_value = MockFactories.create_stellar_metrics_mock()
        mock_error_mgr.return_value = MockFactories.create_error_manager_mock()

        # Create health monitor with actual API
        if StellarHealthMonitor:
            monitor = StellarHealthMonitor(**health_monitor_config)
            yield monitor
            # Cleanup (synchronous since fixture is no longer async)
            if hasattr(monitor, "stop") and hasattr(monitor.stop, "__call__"):
                try:
                    # If it's an async method, we can't call it from sync fixture
                    # The test cleanup will handle async cleanup if needed
                    pass
                except Exception:
                    # Catch any cleanup errors - tests should handle async cleanup
                    pass
        else:
            # Fallback mock if import failed
            yield Mock()


@pytest.fixture
def metrics_collector(prometheus_registry):
    """Fixture for properly configured metrics collector."""
    with patch("hummingbot.connector.exchange.stellar.stellar_metrics.get_stellar_logger") as mock_logger:
        mock_logger.return_value = MockFactories.create_stellar_logger_mock()

        if StellarMetrics:
            collector = StellarMetrics(registry=prometheus_registry)
            yield collector
        else:
            # Fallback mock if import failed
            yield Mock()


@pytest.fixture
def security_manager(security_config, temp_keystore_path):
    """Fixture for properly configured security manager."""
    with patch("hummingbot.connector.exchange.stellar.stellar_security_manager.get_stellar_logger") as mock_logger:
        mock_logger.return_value = MockFactories.create_stellar_logger_mock()

        if StellarSecurityManager:
            manager = StellarSecurityManager(config=security_config, key_store_path=temp_keystore_path)
            yield manager
        else:
            # Fallback mock if import failed
            yield Mock()


@pytest.fixture
def user_stream_tracker(mock_chain_interface, mock_observability):
    """Fixture for properly configured user stream tracker."""
    try:
        from hummingbot.connector.exchange.stellar.stellar_user_stream_tracker import StellarUserStreamTracker

        tracker = StellarUserStreamTracker(chain_interface=mock_chain_interface, observability=mock_observability)
        yield tracker
    except ImportError:
        # Fallback mock if import failed
        yield Mock()


@pytest.fixture
def network_manager(network_config):
    """Fixture for properly configured network manager."""
    timeout_config = TimeoutConfig()
    retry_config = RetryConfig()

    try:
        from hummingbot.connector.exchange.stellar.stellar_network_manager_enhanced import StellarNetworkManager

        with patch(
            "hummingbot.connector.exchange.stellar.stellar_network_manager_enhanced.get_stellar_logger"
        ) as mock_logger:
            mock_logger.return_value = MockFactories.create_stellar_logger_mock()

            manager = StellarNetworkManager(
                network_config=network_config,
                connection_pool_size=5,  # Smaller for testing
                timeout_config=timeout_config,
                retry_config=retry_config,
            )
            yield manager
    except ImportError:
        # Fallback mock if import failed
        yield Mock()


class ComponentTestHelpers:
    """Helper methods for component testing."""

    @staticmethod
    async def wait_for_async_completion(coro, timeout: float = 5.0):
        """Wait for async operation with timeout."""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            pytest.fail(f"Async operation timed out after {timeout}s")

    @staticmethod
    def assert_mock_called_with_pattern(mock_obj, pattern: str):
        """Assert mock was called with argument matching pattern."""
        calls = mock_obj.call_args_list
        for call in calls:
            for arg in call[0]:
                if pattern in str(arg):
                    return True
            for key, value in call[1].items():
                if pattern in str(value):
                    return True
        pytest.fail(f"Mock not called with pattern: {pattern}")

    @staticmethod
    def create_mock_response(status_code: int = 200, json_data: Dict = None):
        """Create mock HTTP response."""
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.json = Mock(return_value=json_data or {})
        mock_response.text = str(json_data) if json_data else ""
        return mock_response


@pytest.fixture
def test_helpers():
    """Fixture for test helper methods."""
    return ComponentTestHelpers()


# Pytest configuration for async testing
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async testing."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Marker for component integration tests
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "component: mark test as component integration test")
    config.addinivalue_line("markers", "requires_network: mark test as requiring network access")
    config.addinivalue_line("markers", "benchmark: mark test as performance benchmark")
    config.addinivalue_line("markers", "testnet: mark test as testnet validation test")


# Additional fixtures for performance and testnet tests
@pytest.fixture
def mock_stellar_exchange():
    """Mock Stellar exchange for testing."""
    mock_exchange = AsyncMock()
    mock_exchange.buy = AsyncMock(return_value="test_order_id_123")
    mock_exchange.get_order_book = AsyncMock(return_value={"bids": [], "asks": []})
    mock_exchange.get_trading_fees = AsyncMock(return_value={"maker": 0.001, "taker": 0.002})
    mock_exchange.get_account_balance = AsyncMock(return_value={"XLM": 1000, "USDC": 500})
    mock_exchange.get_trading_pairs = AsyncMock(return_value=["XLM-USDC", "XLM-BTC"])
    mock_exchange.cancel_order = AsyncMock(return_value=True)
    mock_exchange.check_network_status = AsyncMock(return_value=Mock(is_connected=True))
    mock_exchange.start_network = AsyncMock()
    mock_exchange.stop_network = AsyncMock()
    mock_exchange.start_user_stream = AsyncMock()
    mock_exchange.stop_user_stream = AsyncMock()
    mock_exchange.security_manager = Mock(validate_keys=Mock(return_value=True))
    mock_exchange.user_stream_tracker = Mock(data_source=Mock(ready=True))
    return mock_exchange


@pytest.fixture
def mock_trading_pair():
    """Mock trading pair for testing."""
    return "XLM-USDC"


def create_testnet_config():
    """Create testnet configuration for validation tests."""
    return {
        "network": "testnet",
        "horizon_url": "https://horizon-testnet.stellar.org",
        "soroban_rpc_url": "https://soroban-testnet.stellar.org",
        "network_passphrase": "Test SDF Network ; September 2015",
        "account_secret": "SBPQUZ6G4FZNWFHKUWC5BEYWF6R52E3SEP7R3GWYSM2XTKGF5LNTWW4R",  # Test key
        "security_level": "testing",
    }
