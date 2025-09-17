# Stellar SDEX Connector: Monitoring & Observability

> **Part 3 of 7** - Technical Design Document v3.0
> Split from: `stellar_sdex_tdd_v3.md` (Lines 757-1071)

## Production-Grade Monitoring & Observability

### 4.1 Comprehensive Metrics Collection

**Advanced Metrics Framework**:

```python
from prometheus_client import Counter, Histogram, Gauge, Info
import time
from typing import Dict, Any

class StellarMetricsCollector:
    """Production-grade metrics collection for Stellar connector"""

    def __init__(self):
        # Order metrics
        self.orders_placed = Counter('stellar_orders_placed_total', 'Total orders placed', ['trading_pair', 'side'])
        self.orders_cancelled = Counter('stellar_orders_cancelled_total', 'Total orders cancelled', ['trading_pair'])
        self.orders_filled = Counter('stellar_orders_filled_total', 'Total orders filled', ['trading_pair'])

        # API metrics
        self.api_requests = Counter('stellar_api_requests_total', 'Total API requests', ['endpoint', 'status'])
        self.api_latency = Histogram('stellar_api_latency_seconds', 'API request latency', ['endpoint'])

        # Network metrics
        self.network_errors = Counter('stellar_network_errors_total', 'Network errors', ['error_type'])
        self.active_connections = Gauge('stellar_active_connections', 'Active network connections')

        # Trading metrics
        self.active_offers = Gauge('stellar_active_offers', 'Number of active offers')
        self.account_balance = Gauge('stellar_account_balance', 'Account balance', ['asset'])

        # Performance metrics
        self.transaction_success_rate = Gauge('stellar_transaction_success_rate', 'Transaction success rate')
        self.cache_hit_rate = Gauge('stellar_cache_hit_rate', 'Cache hit rate', ['cache_type'])

        # System info
        self.connector_info = Info('stellar_connector_info', 'Connector version and configuration')

    def record_order_placed(self, trading_pair: str, side: str):
        """Record order placement with context"""
        self.orders_placed.labels(trading_pair=trading_pair, side=side).inc()

    def record_api_request(self, endpoint: str, duration: float, status: str):
        """Record API request metrics"""
        self.api_requests.labels(endpoint=endpoint, status=status).inc()
        self.api_latency.labels(endpoint=endpoint).observe(duration)

    def update_system_health(self, health_data: Dict[str, Any]):
        """Update system health metrics"""
        self.active_connections.set(health_data.get('active_connections', 0))
        self.transaction_success_rate.set(health_data.get('success_rate', 0))

        for cache_type, hit_rate in health_data.get('cache_metrics', {}).items():
            self.cache_hit_rate.labels(cache_type=cache_type).set(hit_rate)
```

### 4.2 Advanced Logging Framework

**Structured Logging with Observability**:

```python
import structlog
from pythonjsonlogger import jsonlogger
import traceback

class StellarLogger:
    """Advanced structured logging for Stellar connector"""

    def __init__(self, component: str):
        self.component = component
        self.logger = structlog.get_logger(component)

        # Configure structured logging
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    def log_transaction_attempt(self, transaction_hash: str, operation_type: str, context: Dict):
        """Log transaction attempt with full context"""
        self.logger.info(
            "Transaction attempt",
            transaction_hash=transaction_hash,
            operation_type=operation_type,
            component=self.component,
            **context
        )

    def log_order_lifecycle(self, order_id: str, event: str, details: Dict):
        """Log order lifecycle events with tracing"""
        self.logger.info(
            f"Order {event}",
            order_id=order_id,
            event=event,
            component=self.component,
            timestamp=time.time(),
            **details
        )

    def log_performance_metrics(self, operation: str, duration: float, context: Dict):
        """Log performance metrics for analysis"""
        self.logger.info(
            "Performance metric",
            operation=operation,
            duration_seconds=duration,
            component=self.component,
            **context
        )

    def log_security_event(self, event_type: str, severity: str, details: Dict):
        """Log security events for monitoring"""
        self.logger.warning(
            "Security event",
            event_type=event_type,
            severity=severity,
            component=self.component,
            timestamp=time.time(),
            **details
        )

    def log_error_with_context(self, error: Exception, context: Dict):
        """Log errors with full context and stack trace"""
        self.logger.error(
            "Error occurred",
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            component=self.component,
            **context
        )
```

### 4.3 Health Check & Circuit Breaker Framework

**Advanced Resilience Patterns**:

```python
from enum import Enum
import asyncio
from typing import Callable, Optional

class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """Circuit breaker for Stellar API operations"""

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        expected_exception: Exception = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED

    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""

        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise Exception(f"Circuit breaker is OPEN, last failure: {self.last_failure_time}")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except self.expected_exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset"""
        return (
            time.time() - self.last_failure_time >= self.timeout
        )

    def _on_success(self):
        """Handle successful operation"""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED

    def _on_failure(self):
        """Handle failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN

class HealthChecker:
    """Comprehensive health checking for Stellar connector"""

    def __init__(self, chain_interface, metrics_collector):
        self.chain_interface = chain_interface
        self.metrics_collector = metrics_collector
        self.health_checks = {}

        # Register standard health checks
        self.register_health_check("stellar_connection", self._check_stellar_connection)
        self.register_health_check("account_access", self._check_account_access)
        self.register_health_check("api_responsiveness", self._check_api_responsiveness)
        self.register_health_check("transaction_capability", self._check_transaction_capability)

    def register_health_check(self, name: str, check_func: Callable):
        """Register a health check function"""
        self.health_checks[name] = check_func

    async def run_all_health_checks(self) -> Dict[str, Dict]:
        """Run all registered health checks"""
        results = {}

        for check_name, check_func in self.health_checks.items():
            start_time = time.time()
            try:
                result = await check_func()
                duration = time.time() - start_time

                results[check_name] = {
                    "status": "healthy" if result else "unhealthy",
                    "duration_seconds": duration,
                    "timestamp": time.time()
                }
            except Exception as e:
                results[check_name] = {
                    "status": "error",
                    "error": str(e),
                    "duration_seconds": time.time() - start_time,
                    "timestamp": time.time()
                }

        return results

    async def _check_stellar_connection(self) -> bool:
        """Check basic Stellar network connectivity"""
        try:
            await self.chain_interface.horizon_server.fetch_base_fee()
            return True
        except Exception:
            return False

    async def _check_account_access(self) -> bool:
        """Check account accessibility"""
        try:
            if not self.chain_interface.keypair:
                return False
            account = await self.chain_interface.get_account(
                self.chain_interface.keypair.public_key
            )
            return account is not None
        except Exception:
            return False

    async def _check_api_responsiveness(self) -> bool:
        """Check API response time"""
        start_time = time.time()
        try:
            await self.chain_interface.horizon_server.ledgers().limit(1).call()
            response_time = time.time() - start_time
            return response_time < 2.0  # 2 second threshold
        except Exception:
            return False

    async def _check_transaction_capability(self) -> bool:
        """Check transaction building capability (without submission)"""
        try:
            if not self.chain_interface.keypair:
                return False

            account = await self.chain_interface.get_account(
                self.chain_interface.keypair.public_key
            )

            # Build a test transaction (don't submit)
            transaction = (
                TransactionBuilder(
                    source_account=account,
                    network_passphrase=self.chain_interface.network_passphrase,
                    base_fee=100
                )
                .add_text_memo("Health check test")
                .set_timeout(30)
                .build()
            )

            return transaction is not None
        except Exception:
            return False
```

---

## Related Documents

This document is part of the Stellar SDEX Connector Technical Design v3.0 series:

1. [01-architecture-foundation.md](./01-architecture-foundation.md) - Architecture & Technical Foundation
2. [02-security-framework.md](./02-security-framework.md) - Security Framework
3. **[03-monitoring-observability.md](./03-monitoring-observability.md)** - Monitoring & Observability ⭐ *You are here*
4. [04-order-management.md](./04-order-management.md) - Order Management & Trading Logic
5. [05-asset-management.md](./05-asset-management.md) - Asset Management & Risk
6. [06-deployment-operations.md](./06-deployment-operations.md) - Production Deployment & Operations
7. [07-implementation-guide.md](./07-implementation-guide.md) - Implementation Guide & Checklists

**Monitoring-Specific References:**
- Production observability frameworks
- Prometheus metrics integration
- Health check patterns
- Circuit breaker implementations