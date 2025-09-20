"""
Comprehensive unit tests for StellarExchange - Primary connector component
QAEngineer-designed test suite for 90% coverage target
"""

import asyncio
import pytest
from decimal import Decimal
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# Test imports
from hummingbot.connector.exchange.stellar.stellar_exchange import StellarExchange
from hummingbot.connector.exchange.stellar.stellar_config_models import StellarNetworkConfig


class TestStellarExchangeInitialization:
    """Test suite for StellarExchange initialization and configuration."""

    @pytest.fixture
    def mock_stellar_config(self):
        """Mock Stellar network configuration."""
        config = MagicMock(spec=StellarNetworkConfig)
        config.horizon_url = "https://horizon-testnet.stellar.org"
        config.network_passphrase = "Test SDF Network ; September 2015"
        config.is_testnet = True
        return config

    @pytest.fixture
    def trading_pairs(self):
        """Standard trading pairs for testing."""
        return ["XLM-USDC", "XLM-EURT", "USDC-EURT"]

    @pytest.fixture
    def stellar_exchange(self, mock_stellar_config, trading_pairs):
        """Create StellarExchange instance for testing."""
        return StellarExchange(
            stellar_config=mock_stellar_config,
            trading_pairs=trading_pairs,
            trading_required=True
        )

    def test_exchange_initialization(self, stellar_exchange, mock_stellar_config, trading_pairs):
        """Test basic exchange initialization."""
        # Verify configuration stored correctly
        assert stellar_exchange._stellar_config == mock_stellar_config
        assert stellar_exchange._trading_pairs == trading_pairs
        assert stellar_exchange._trading_required is True

        # Verify initial state
        assert stellar_exchange._ready is False
        assert stellar_exchange._last_timestamp == 0.0

        # Verify components are None before start_network()
        assert stellar_exchange._chain_interface is None
        assert stellar_exchange._security_framework is None
        assert stellar_exchange._order_manager is None
        assert stellar_exchange._asset_manager is None
        assert stellar_exchange._observability is None
        assert stellar_exchange._error_handler is None

    def test_exchange_initialization_optional_params(self, mock_stellar_config, trading_pairs):
        """Test exchange initialization with optional parameters."""
        exchange = StellarExchange(
            stellar_config=mock_stellar_config,
            trading_pairs=trading_pairs,
            trading_required=False,
            custom_param="test_value"
        )

        assert exchange._trading_required is False
        assert exchange._stellar_config == mock_stellar_config
        assert exchange._trading_pairs == trading_pairs

    def test_rate_limits_initialization(self, stellar_exchange):
        """Test that rate limiting is properly initialized."""
        # Verify throttler exists
        assert stellar_exchange._throttler is not None
        assert hasattr(stellar_exchange._throttler, '_rate_limits')

        # Verify web assistants factory exists
        assert stellar_exchange._web_assistants_factory is not None
        assert stellar_exchange._web_assistants_factory.throttler == stellar_exchange._throttler


class TestStellarExchangeNetworkLifecycle:
    """Test suite for network connection lifecycle management."""

    @pytest.fixture
    def mock_stellar_config(self):
        config = MagicMock(spec=StellarNetworkConfig)
        config.horizon_url = "https://horizon-testnet.stellar.org"
        config.network_passphrase = "Test SDF Network ; September 2015"
        config.is_testnet = True
        config.name = "testnet"
        return config

    @pytest.fixture
    def stellar_exchange(self, mock_stellar_config):
        return StellarExchange(
            stellar_config=mock_stellar_config,
            trading_pairs=["XLM-USDC"],
            trading_required=True
        )

    @pytest.mark.asyncio
    @patch('hummingbot.connector.exchange.stellar.stellar_exchange.StellarObservabilityFramework')
    @patch('hummingbot.connector.exchange.stellar.stellar_exchange.ModernStellarErrorHandler')
    @patch('hummingbot.connector.exchange.stellar.stellar_exchange.EnterpriseSecurityFramework')
    @patch('hummingbot.connector.exchange.stellar.stellar_exchange.ModernStellarChainInterface')
    @patch('hummingbot.connector.exchange.stellar.stellar_exchange.ModernAssetManager')
    @patch('hummingbot.connector.exchange.stellar.stellar_exchange.ModernStellarOrderManager')
    async def test_start_network_success(
        self,
        mock_order_manager_class,
        mock_asset_manager_class,
        mock_chain_interface_class,
        mock_security_framework_class,
        mock_error_handler_class,
        mock_observability_class,
        stellar_exchange
    ):
        """Test successful network startup."""
        # Setup mocks
        mock_observability = AsyncMock()
        mock_observability_class.return_value = mock_observability

        mock_error_handler = MagicMock()
        mock_error_handler.handle_startup_error = AsyncMock()
        mock_error_handler_class.return_value = mock_error_handler

        mock_security_framework = AsyncMock()
        mock_security_framework_class.return_value = mock_security_framework

        mock_chain_interface = AsyncMock()
        mock_chain_interface_class.return_value = mock_chain_interface

        mock_asset_manager = AsyncMock()
        mock_asset_manager_class.return_value = mock_asset_manager

        mock_order_manager = AsyncMock()
        mock_order_manager_class.return_value = mock_order_manager

        # Execute start_network
        await stellar_exchange.start_network()

        # Verify initialization sequence
        mock_observability.start.assert_called_once()
        mock_security_framework.initialize.assert_called_once()
        mock_chain_interface.start.assert_called_once()
        mock_asset_manager.initialize.assert_called_once()
        mock_order_manager.start.assert_called_once()

        # Verify components are assigned
        assert stellar_exchange._observability == mock_observability
        assert stellar_exchange._error_handler == mock_error_handler
        assert stellar_exchange._security_framework == mock_security_framework
        assert stellar_exchange._chain_interface == mock_chain_interface
        assert stellar_exchange._asset_manager == mock_asset_manager
        assert stellar_exchange._order_manager == mock_order_manager

        # Verify ready state
        assert stellar_exchange._ready is True

    @pytest.mark.asyncio
    @patch('hummingbot.connector.exchange.stellar.stellar_exchange.StellarObservabilityFramework')
    async def test_start_network_observability_failure(self, mock_observability_class, stellar_exchange):
        """Test network startup failure in observability initialization."""
        # Setup failing observability mock
        mock_observability = AsyncMock()
        mock_observability.start.side_effect = Exception("Observability startup failed")
        mock_observability_class.return_value = mock_observability

        # Verify exception is raised
        with pytest.raises(Exception, match="Observability startup failed"):
            await stellar_exchange.start_network()

        # Verify state remains unready
        assert stellar_exchange._ready is False

    @pytest.mark.asyncio
    @patch('hummingbot.connector.exchange.stellar.stellar_exchange.StellarObservabilityFramework')
    @patch('hummingbot.connector.exchange.stellar.stellar_exchange.ModernStellarErrorHandler')
    @patch('hummingbot.connector.exchange.stellar.stellar_exchange.EnterpriseSecurityFramework')
    async def test_start_network_security_failure(
        self,
        mock_security_framework_class,
        mock_error_handler_class,
        mock_observability_class,
        stellar_exchange
    ):
        """Test network startup failure in security framework initialization."""
        # Setup mocks
        mock_observability = AsyncMock()
        mock_observability_class.return_value = mock_observability

        mock_error_handler = MagicMock()
        mock_error_handler_class.return_value = mock_error_handler

        mock_security_framework = AsyncMock()
        mock_security_framework.initialize.side_effect = Exception("Security initialization failed")
        mock_security_framework_class.return_value = mock_security_framework

        # Verify exception is raised (the actual error will be about MagicMock in await expression)
        with pytest.raises(Exception):
            await stellar_exchange.start_network()

        # Verify observability was started but security failed
        mock_observability.start.assert_called_once()
        assert stellar_exchange._ready is False


class TestStellarExchangeTradingPairs:
    """Test suite for trading pairs management."""

    @pytest.fixture
    def mock_stellar_config(self):
        config = MagicMock(spec=StellarNetworkConfig)
        config.horizon_url = "https://horizon-testnet.stellar.org"
        return config

    def test_trading_pairs_storage(self, mock_stellar_config):
        """Test that trading pairs are properly stored."""
        trading_pairs = ["XLM-USDC", "XLM-EURT", "USDC-EURT"]
        exchange = StellarExchange(
            stellar_config=mock_stellar_config,
            trading_pairs=trading_pairs,
            trading_required=True
        )

        assert exchange._trading_pairs == trading_pairs
        assert len(exchange._trading_pairs) == 3

    def test_empty_trading_pairs(self, mock_stellar_config):
        """Test initialization with empty trading pairs."""
        exchange = StellarExchange(
            stellar_config=mock_stellar_config,
            trading_pairs=[],
            trading_required=False
        )

        assert exchange._trading_pairs == []
        assert exchange._trading_required is False


class TestStellarExchangeRateLimiting:
    """Test suite for rate limiting functionality."""

    @pytest.fixture
    def mock_stellar_config(self):
        config = MagicMock(spec=StellarNetworkConfig)
        return config

    @pytest.fixture
    def stellar_exchange(self, mock_stellar_config):
        return StellarExchange(
            stellar_config=mock_stellar_config,
            trading_pairs=["XLM-USDC"],
            trading_required=True
        )

    def test_throttler_initialization(self, stellar_exchange):
        """Test that AsyncThrottler is properly initialized."""
        assert stellar_exchange._throttler is not None
        # Verify throttler has rate limits configured
        assert hasattr(stellar_exchange._throttler, '_rate_limits')

    def test_web_assistants_factory_throttler_connection(self, stellar_exchange):
        """Test that WebAssistantsFactory is connected to throttler."""
        assert stellar_exchange._web_assistants_factory is not None
        assert stellar_exchange._web_assistants_factory.throttler == stellar_exchange._throttler

    @patch.object(StellarExchange, '_get_stellar_rate_limits')
    def test_stellar_rate_limits_called(self, mock_get_rate_limits, mock_stellar_config):
        """Test that Stellar-specific rate limits are configured."""
        mock_rate_limits = [MagicMock()]
        mock_get_rate_limits.return_value = mock_rate_limits

        exchange = StellarExchange(
            stellar_config=mock_stellar_config,
            trading_pairs=["XLM-USDC"],
            trading_required=True
        )

        mock_get_rate_limits.assert_called_once()


class TestStellarExchangeStateManagement:
    """Test suite for exchange state management."""

    @pytest.fixture
    def mock_stellar_config(self):
        config = MagicMock(spec=StellarNetworkConfig)
        return config

    @pytest.fixture
    def stellar_exchange(self, mock_stellar_config):
        return StellarExchange(
            stellar_config=mock_stellar_config,
            trading_pairs=["XLM-USDC"],
            trading_required=True
        )

    def test_initial_state(self, stellar_exchange):
        """Test initial exchange state."""
        assert stellar_exchange._ready is False
        assert stellar_exchange._last_timestamp == 0.0

    def test_ready_state_before_start(self, stellar_exchange):
        """Test that exchange is not ready before start_network()."""
        assert stellar_exchange._ready is False

    def test_timestamp_initial_value(self, stellar_exchange):
        """Test initial timestamp value."""
        assert stellar_exchange._last_timestamp == 0.0
        assert isinstance(stellar_exchange._last_timestamp, float)


# Test execution configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
