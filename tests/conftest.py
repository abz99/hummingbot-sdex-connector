"""
Global pytest configuration and fixtures for Stellar connector tests.
"""

import pytest
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import specific fixtures from our fixtures module
from tests.fixtures.stellar_component_fixtures import (  # noqa: E402
    SecurityLevel,
    SecurityConfig,
    NetworkConfig,
    TimeoutConfig,
    RetryConfig,
    StellarComponentFixtures,
    MockFactories,
    ComponentTestHelpers,
    health_monitor_config,
    security_config,
    network_config,
    prometheus_registry,
    mock_stellar_logger,
    mock_stellar_metrics,
    mock_error_manager,
    mock_chain_interface,
    mock_observability,
    temp_keystore_path,
    health_monitor,
    metrics_collector,
    security_manager,
    user_stream_tracker,
    network_manager,
    test_helpers,
    event_loop,
    pytest_configure,
    mock_stellar_exchange,
    mock_trading_pair,
    create_testnet_config,
)
