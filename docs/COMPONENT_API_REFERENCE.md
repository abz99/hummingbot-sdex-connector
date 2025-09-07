# Stellar Connector Component API Reference

**Generated:** 2025-09-07  
**Purpose:** QA Framework Integration - Actual Implementation APIs  
**Scope:** Top 5 Critical Components for Testing  

## Overview

This document provides the **actual API specifications** for the Stellar connector components to enable proper QA framework integration. These APIs differ significantly from our original test assumptions and require test adapter development.

---

## 🏥 **1. StellarHealthMonitor**

**File:** `stellar_health_monitor.py` (680 lines)  
**Purpose:** Advanced connection health monitoring with alerting and automatic recovery  

### Constructor

```python
class StellarHealthMonitor:
    def __init__(
        self,
        check_interval: int = 30,        # Health check interval in seconds
        failure_threshold: int = 3,      # Failures before marking unhealthy
        recovery_threshold: int = 2,     # Successes needed for recovery
        history_size: int = 100,        # Number of results to keep in history
    ):
```

### Key Methods

```python
# Core health checking
async def check_health(self) -> Dict[str, Any]:
    """Perform comprehensive health check of all endpoints."""

async def start(self) -> None:
    """Start the health monitoring background loop."""

async def stop(self) -> None:
    """Stop health monitoring and cleanup."""

async def check_endpoint_health(self, url: str) -> Optional[HealthCheckResult]:
    """Check health of specific endpoint."""

# Configuration and status
def add_endpoint(self, url: str, check_type: HealthCheckType) -> None:
    """Add endpoint to monitoring."""

def get_endpoint_status(self, url: str) -> Optional[EndpointHealth]:
    """Get current status of endpoint."""

def get_all_statuses(self) -> Dict[str, EndpointHealth]:
    """Get status of all monitored endpoints."""
```

### Dependencies

```python
from .stellar_logging import get_stellar_logger
from .stellar_metrics import get_stellar_metrics  
from .stellar_error_classification import StellarErrorManager
```

### Data Classes

```python
@dataclass
class HealthCheckResult:
    endpoint: str
    check_type: HealthCheckType
    status: HealthStatus
    response_time: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EndpointHealth:
    url: str
    check_type: HealthCheckType
    current_status: HealthStatus = HealthStatus.UNKNOWN
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    # ... additional fields
```

### Test Integration Requirements

```python
# For testing, need to:
1. Mock internal dependencies: get_stellar_logger(), get_stellar_metrics()
2. Mock StellarErrorManager for error handling
3. Mock HTTP calls for endpoint health checks
4. Set up proper asyncio context for async methods
```

---

## 📊 **2. StellarMetrics**

**File:** `stellar_metrics.py` (509 lines)  
**Purpose:** Comprehensive metrics collection using Prometheus  

### Constructor

```python
class StellarMetrics:
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Initialize metrics collector.
        
        Args:
            registry: Prometheus CollectorRegistry instance (NOT dict!)
        """
```

### Key Methods

```python
# Metric recording
async def record_metric(
    self,
    name: str,
    value: float,
    labels: Optional[Dict[str, str]] = None
) -> None:
    """Record a metric value."""

async def record_histogram(
    self,
    name: str, 
    value: float,
    labels: Optional[Dict[str, str]] = None
) -> None:
    """Record histogram metric."""

def increment_counter(
    self,
    name: str,
    labels: Optional[Dict[str, str]] = None,
    amount: float = 1.0
) -> None:
    """Increment counter metric."""

def set_gauge(
    self,
    name: str,
    value: float,
    labels: Optional[Dict[str, str]] = None
) -> None:
    """Set gauge metric value."""

# Metric retrieval
async def get_metrics(self) -> str:
    """Get all metrics in Prometheus format."""

async def get_histogram_metrics(self) -> str:
    """Get histogram metrics."""

def get_metric_value(self, name: str) -> Optional[float]:
    """Get current value of specific metric."""

# Background collection
async def start_collection(self) -> None:
    """Start background metric collection."""

async def stop_collection(self) -> None:
    """Stop background collection."""
```

### Dependencies

```python
from prometheus_client import (
    Counter, Histogram, Gauge, Summary, Info,
    CollectorRegistry, generate_latest
)
from .stellar_logging import get_stellar_logger
```

### Critical Test Requirements

```python
# For testing, MUST provide:
1. Proper CollectorRegistry instance (not dict!)
   registry = CollectorRegistry()
   metrics = StellarMetrics(registry)

2. Mock get_stellar_logger() internal dependency
3. Handle Prometheus client metric registration
4. Async context for collection methods
```

---

## 🔐 **3. StellarSecurityManager**

**File:** `stellar_security_manager.py` (564 lines)  
**Purpose:** Enterprise-grade security infrastructure  

### Constructor

```python
class StellarSecurityManager:
    def __init__(
        self, 
        config: SecurityConfig,               # Required SecurityConfig object
        key_store_path: Optional[str] = None  # Path for file-based key storage
    ):
```

### Key Methods

```python
# Key management
def get_keypair(self, key_id: str) -> Optional[Keypair]:
    """Retrieve keypair by ID."""

def store_keypair(
    self,
    key_id: str,
    keypair: Keypair,
    metadata: Optional[KeyMetadata] = None
) -> bool:
    """Store keypair securely."""

def delete_keypair(self, key_id: str) -> bool:
    """Delete keypair from storage."""

def list_keys(self) -> List[str]:
    """List available key IDs."""

# Security validation
def validate_transaction(self, transaction_xdr: str) -> ValidationResult:
    """Validate transaction for security compliance."""

def check_rate_limit(self, operation: str, user_id: str) -> bool:
    """Check if operation is within rate limits."""

def sanitize_data(self, data: Any) -> Any:
    """Sanitize data for logging/storage."""

# Session management
def create_session(self, user_id: str) -> str:
    """Create secure session."""

def validate_session(self, session_id: str) -> bool:
    """Validate session is active and valid."""

def destroy_session(self, session_id: str) -> None:
    """Destroy session."""
```

### Dependencies

```python
from .stellar_security_types import (
    SecurityLevel, SecurityConfig, KeyStoreType, KeyMetadata
)
from .stellar_keystores import MemoryKeyStore, FileSystemKeyStore, HSMKeyStore
from .stellar_security_validation import (
    SecurityValidator, RateLimiter, ValidationLevel
)
```

### Required Data Structures

```python
@dataclass
class SecurityConfig:
    security_level: SecurityLevel
    allowed_networks: List[str]
    max_transaction_amount: Optional[Decimal]
    rate_limit_config: Dict[str, int]
    encryption_key: Optional[str]
    # ... additional security fields

class SecurityLevel(Enum):
    DEVELOPMENT = auto()
    TESTING = auto() 
    STAGING = auto()
    PRODUCTION = auto()
```

### Test Integration Requirements

```python
# For testing, need to:
1. Create proper SecurityConfig object with all required fields
2. Mock key store backends (Memory, FileSystem, HSM)
3. Mock SecurityValidator and RateLimiter
4. Provide test encryption keys and network configurations
```

---

## 🌐 **4. StellarUserStreamTracker**

**File:** `stellar_user_stream_tracker.py` (358 lines)  
**Purpose:** Real-time user data streaming and WebSocket management  

### Constructor

```python
class StellarUserStreamTracker:
    def __init__(
        self,
        chain_interface,      # Required: StellarChainInterface instance
        observability        # Required: Observability/logging instance
    ):
```

### Key Methods

```python
# Stream lifecycle
async def start(self) -> None:
    """Start user stream tracking."""

async def stop(self) -> None:
    """Stop user stream tracking."""

# Data streaming
async def get_account_updates(self, account_id: str) -> AsyncIterator[Dict]:
    """Get real-time account updates."""

async def get_transaction_stream(self, account_id: str) -> AsyncIterator[Dict]:
    """Get transaction stream for account."""

async def get_order_updates(self) -> AsyncIterator[Dict]:
    """Get order book updates."""

# Connection management
def is_connected(self) -> bool:
    """Check if stream is connected."""

async def reconnect(self) -> None:
    """Reconnect to stream."""

def get_connection_stats(self) -> Dict[str, Any]:
    """Get connection statistics."""
```

### Dependencies

```python
# Required constructor arguments:
from .stellar_chain_interface import StellarChainInterface
from .stellar_observability import ObservabilityManager
```

### Test Integration Requirements

```python
# For testing, need to:
1. Mock StellarChainInterface instance
2. Mock ObservabilityManager instance  
3. Mock WebSocket connections
4. Handle async streaming patterns
5. Mock Stellar Horizon streaming endpoints
```

---

## 📡 **5. StellarNetworkManager**

**File:** `stellar_network_manager_enhanced.py` (681 lines)  
**Purpose:** Enhanced network connection management with failover  

### Constructor

```python
class StellarNetworkManager:
    def __init__(
        self,
        network_config: NetworkConfig,      # Network configuration
        connection_pool_size: int = 10,     # HTTP connection pool size
        timeout_config: TimeoutConfig = None, # Request timeout configuration
        retry_config: RetryConfig = None    # Retry policy configuration
    ):
```

### Key Methods

```python
# Network operations
async def get_account(self, account_id: str) -> AccountResponse:
    """Get account information."""

async def submit_transaction(self, transaction_xdr: str) -> TransactionResponse:
    """Submit transaction to network."""

async def get_transaction(self, transaction_hash: str) -> TransactionResponse:
    """Get transaction details."""

# Connection management
async def start(self) -> None:
    """Start network manager."""

async def stop(self) -> None:
    """Stop network manager and cleanup connections."""

def get_connection_stats(self) -> Dict[str, Any]:
    """Get connection pool statistics."""

# Network health
async def check_network_health(self) -> NetworkHealthStatus:
    """Check health of all network endpoints."""

def get_current_network(self) -> str:
    """Get currently active network."""

async def switch_network(self, network_name: str) -> bool:
    """Switch to different network."""
```

### Dependencies

```python
from .stellar_network_types import (
    NetworkConfig, TimeoutConfig, RetryConfig, NetworkHealthStatus
)
from .stellar_connection_pool import ConnectionPoolManager
from .stellar_error_classification import NetworkErrorHandler
```

### Test Integration Requirements

```python
# For testing, need to:
1. Create NetworkConfig with proper network endpoints
2. Mock HTTP connection pools and requests
3. Mock Stellar network responses
4. Handle async network operations
5. Mock timeout and retry configurations
```

---

## 🧪 **Test Adapter Development Guide**

Based on this API analysis, our QA framework needs these adaptations:

### **1. Constructor Pattern Changes**

**Original Test Assumption:**
```python
# Our tests assumed simple dict config
component = StellarHealthMonitor(config_dict)
```

**Actual Implementation:**
```python  
# Actual APIs require specific parameters
health_monitor = StellarHealthMonitor(
    check_interval=30,
    failure_threshold=3, 
    recovery_threshold=2,
    history_size=100
)

metrics = StellarMetrics(registry=CollectorRegistry())

security_manager = StellarSecurityManager(
    config=SecurityConfig(
        security_level=SecurityLevel.TESTING,
        allowed_networks=['testnet'],
        # ... other required fields
    )
)
```

### **2. Dependency Injection Requirements**

All components require proper dependency mocking:

```python
# Mock internal dependencies
@patch('hummingbot.connector.exchange.stellar.stellar_health_monitor.get_stellar_logger')
@patch('hummingbot.connector.exchange.stellar.stellar_health_monitor.get_stellar_metrics')
@patch('hummingbot.connector.exchange.stellar.stellar_health_monitor.StellarErrorManager')
def test_health_monitor_initialization(mock_error_mgr, mock_metrics, mock_logger):
    # Test with proper mocks
    health_monitor = StellarHealthMonitor()
    assert health_monitor is not None
```

### **3. Async Testing Patterns**

Most operations are async and require proper test setup:

```python
@pytest.mark.asyncio
async def test_async_operations():
    # Proper async testing context
    health_monitor = StellarHealthMonitor()
    result = await health_monitor.check_health()
    assert result is not None
```

### **4. Prometheus Registry Setup**

Metrics require proper registry setup:

```python  
from prometheus_client import CollectorRegistry

def test_metrics_initialization():
    registry = CollectorRegistry()  # Not a dict!
    metrics = StellarMetrics(registry=registry)
    assert metrics is not None
```

---

## 🎯 **Next Steps for QA Integration**

1. **Create Component Test Fixtures** - Build proper initialization for each component
2. **Develop Mock Factories** - Create reusable mocks for internal dependencies  
3. **Adapt Test Skeletons** - Modify our QA tests to use actual APIs
4. **Build Integration Tests** - Create component interaction tests
5. **Establish Coverage Baseline** - Measure current test coverage

The next phase will focus on creating adapted test fixtures that work with these actual implementation APIs.