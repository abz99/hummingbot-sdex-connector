"""
Stellar Metrics Collection
Comprehensive metrics collection using Prometheus for monitoring and alerting.
"""

import asyncio
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import auto, Enum
from typing import Any, Dict, List, Optional, Union

from prometheus_client import (
    CollectorRegistry,
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    generate_latest,
    Histogram,
    Info,
    start_http_server,
    Summary,
)

from .stellar_logging import get_stellar_logger, LogCategory


class MetricType(Enum):
    """Types of metrics we collect."""

    COUNTER = auto()
    HISTOGRAM = auto()
    GAUGE = auto()
    SUMMARY = auto()
    INFO = auto()


@dataclass
class MetricDefinition:
    """Definition of a metric."""

    name: str
    description: str
    metric_type: MetricType
    labels: List[str] = None

    def __post_init__(self) -> None:
        if self.labels is None:
            self.labels = []


class StellarMetrics:
    """Comprehensive metrics collection for Stellar connector."""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.logger = get_stellar_logger()
        self.registry = registry or CollectorRegistry()
        self._metrics: Dict[str, Any] = {}
        self._custom_metrics: Dict[str, Any] = {}

        # Initialize core metrics
        self._init_core_metrics()

        # Start background tasks
        self._background_tasks: List[asyncio.Task] = []

    def _init_core_metrics(self) -> None:
        """Initialize core Stellar connector metrics."""

        # Network metrics
        self.network_requests_total = Counter(
            "stellar_network_requests_total",
            "Total number of network requests",
            ["network", "endpoint_type", "status"],
            registry=self.registry,
        )

        self.network_request_duration = Histogram(
            "stellar_network_request_duration_seconds",
            "Network request duration in seconds",
            ["network", "endpoint_type"],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0],
            registry=self.registry,
        )

        self.network_errors_total = Counter(
            "stellar_network_errors_total",
            "Total number of network errors",
            ["network", "endpoint_type", "error_type"],
            registry=self.registry,
        )

        self.active_connections = Gauge(
            "stellar_active_connections",
            "Number of active network connections",
            ["network"],
            registry=self.registry,
        )

        # Trading metrics
        self.orders_placed_total = Counter(
            "stellar_orders_placed_total",
            "Total number of orders placed",
            ["network", "trading_pair", "side", "status"],
            registry=self.registry,
        )

        self.order_fill_duration = Histogram(
            "stellar_order_fill_duration_seconds",
            "Time from order placement to fill",
            ["network", "trading_pair", "side"],
            buckets=[1, 5, 10, 30, 60, 300, 600, 1800],
            registry=self.registry,
        )

        self.trading_volume = Counter(
            "stellar_trading_volume_xlm",
            "Total trading volume in XLM equivalent",
            ["network", "trading_pair", "side"],
            registry=self.registry,
        )

        self.order_book_spread = Gauge(
            "stellar_order_book_spread_percent",
            "Current order book spread percentage",
            ["network", "trading_pair"],
            registry=self.registry,
        )

        # Account metrics
        self.account_balances = Gauge(
            "stellar_account_balance_xlm",
            "Account balance in XLM equivalent",
            ["network", "account_id", "asset_code"],
            registry=self.registry,
        )

        self.trustline_count = Gauge(
            "stellar_trustlines_total",
            "Number of trustlines per account",
            ["network", "account_id"],
            registry=self.registry,
        )

        # Health and performance metrics
        self.health_check_duration = Histogram(
            "stellar_health_check_duration_seconds",
            "Health check duration",
            ["network", "check_type"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
            registry=self.registry,
        )

        self.endpoint_health_status = Gauge(
            "stellar_endpoint_health_status",
            "Endpoint health status (1=healthy, 0=unhealthy)",
            ["network", "endpoint_type", "url"],
            registry=self.registry,
        )

        self.circuit_breaker_state = Gauge(
            "stellar_circuit_breaker_state",
            "Circuit breaker state (0=closed, 1=open, 2=half-open)",
            ["network", "endpoint"],
            registry=self.registry,
        )

        # Cache metrics
        self.cache_hits_total = Counter(
            "stellar_cache_hits_total",
            "Total number of cache hits",
            ["cache_type"],
            registry=self.registry,
        )

        self.cache_misses_total = Counter(
            "stellar_cache_misses_total",
            "Total number of cache misses",
            ["cache_type"],
            registry=self.registry,
        )

        self.cache_size = Gauge(
            "stellar_cache_size_items",
            "Number of items in cache",
            ["cache_type"],
            registry=self.registry,
        )

        # Error metrics
        self.errors_total = Counter(
            "stellar_errors_total",
            "Total number of errors by category",
            ["category", "severity", "operation"],
            registry=self.registry,
        )

        self.error_recovery_attempts = Counter(
            "stellar_error_recovery_attempts_total",
            "Total error recovery attempts",
            ["strategy", "success"],
            registry=self.registry,
        )

        # System metrics
        self.memory_usage_bytes = Gauge(
            "stellar_memory_usage_bytes",
            "Memory usage in bytes",
            ["component"],
            registry=self.registry,
        )

        self.cpu_usage_percent = Gauge(
            "stellar_cpu_usage_percent",
            "CPU usage percentage",
            ["component"],
            registry=self.registry,
        )

        # Business metrics
        self.profit_loss_xlm = Gauge(
            "stellar_profit_loss_xlm",
            "Realized profit/loss in XLM",
            ["network", "trading_pair", "strategy"],
            registry=self.registry,
        )

        self.arbitrage_opportunities = Counter(
            "stellar_arbitrage_opportunities_total",
            "Total arbitrage opportunities detected",
            ["network", "asset_pair", "executed"],
            registry=self.registry,
        )

        # QA and Testing metrics
        self.qa_test_coverage = Gauge(
            "stellar_qa_test_coverage_percentage",
            "Test coverage percentage by module",
            ["module", "coverage_type"],
            registry=self.registry,
        )

        self.qa_test_success_rate = Gauge(
            "stellar_qa_test_success_rate",
            "QA test success rate",
            ["test_suite", "test_type"],
            registry=self.registry,
        )

        self.qa_critical_module_coverage = Gauge(
            "stellar_qa_critical_module_coverage_percentage",
            "Critical module test coverage percentage",
            ["module", "threshold_type"],
            registry=self.registry,
        )

        self.qa_test_execution_duration = Histogram(
            "stellar_qa_test_execution_duration_seconds",
            "QA test execution duration in seconds",
            ["test_suite", "test_category"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry,
        )

        self.qa_test_failures_total = Counter(
            "stellar_qa_test_failures_total",
            "Total number of QA test failures",
            ["test_suite", "failure_type", "module"],
            registry=self.registry,
        )

        self.qa_code_quality_score = Gauge(
            "stellar_qa_code_quality_score",
            "Code quality score from static analysis",
            ["module", "metric_type"],
            registry=self.registry,
        )

        self.qa_requirements_compliance = Gauge(
            "stellar_qa_requirements_compliance_percentage",
            "Requirements compliance percentage",
            ["requirement_category", "priority"],
            registry=self.registry,
        )

        self.qa_security_compliance_score = Gauge(
            "stellar_qa_security_compliance_score",
            "Security compliance score",
            ["security_category", "requirement_level"],
            registry=self.registry,
        )

        # Store metrics for easy access
        self._metrics.update(
            {
                "network_requests_total": self.network_requests_total,
                "network_request_duration": self.network_request_duration,
                "network_errors_total": self.network_errors_total,
                "active_connections": self.active_connections,
                "orders_placed_total": self.orders_placed_total,
                "order_fill_duration": self.order_fill_duration,
                "trading_volume": self.trading_volume,
                "order_book_spread": self.order_book_spread,
                "account_balances": self.account_balances,
                "trustline_count": self.trustline_count,
                "health_check_duration": self.health_check_duration,
                "endpoint_health_status": self.endpoint_health_status,
                "circuit_breaker_state": self.circuit_breaker_state,
                "cache_hits_total": self.cache_hits_total,
                "cache_misses_total": self.cache_misses_total,
                "cache_size": self.cache_size,
                "errors_total": self.errors_total,
                "error_recovery_attempts": self.error_recovery_attempts,
                "memory_usage_bytes": self.memory_usage_bytes,
                "cpu_usage_percent": self.cpu_usage_percent,
                "profit_loss_xlm": self.profit_loss_xlm,
                "arbitrage_opportunities": self.arbitrage_opportunities,
                "qa_test_coverage": self.qa_test_coverage,
                "qa_test_success_rate": self.qa_test_success_rate,
                "qa_critical_module_coverage": self.qa_critical_module_coverage,
                "qa_test_execution_duration": self.qa_test_execution_duration,
                "qa_test_failures_total": self.qa_test_failures_total,
                "qa_code_quality_score": self.qa_code_quality_score,
                "qa_requirements_compliance": self.qa_requirements_compliance,
                "qa_security_compliance_score": self.qa_security_compliance_score,
            }
        )

    def create_custom_metric(self, definition: MetricDefinition) -> Any:
        """Create a custom metric."""
        if definition.name in self._custom_metrics:
            return self._custom_metrics[definition.name]

        if definition.metric_type == MetricType.COUNTER:
            metric = Counter(
                definition.name, definition.description, definition.labels, registry=self.registry
            )
        elif definition.metric_type == MetricType.HISTOGRAM:
            metric = Histogram(
                definition.name, definition.description, definition.labels, registry=self.registry
            )
        elif definition.metric_type == MetricType.GAUGE:
            metric = Gauge(
                definition.name, definition.description, definition.labels, registry=self.registry
            )
        elif definition.metric_type == MetricType.SUMMARY:
            metric = Summary(
                definition.name, definition.description, definition.labels, registry=self.registry
            )
        elif definition.metric_type == MetricType.INFO:
            metric = Info(definition.name, definition.description, registry=self.registry)
        else:
            raise ValueError(f"Unknown metric type: {definition.metric_type}")

        self._custom_metrics[definition.name] = metric
        return metric

    # Network metrics methods
    def record_network_request(
        self, network: str, endpoint_type: str, status: str, duration: float
    ) -> None:
        """Record a network request."""
        self.network_requests_total.labels(
            network=network, endpoint_type=endpoint_type, status=status
        ).inc()
        self.network_request_duration.labels(network=network, endpoint_type=endpoint_type).observe(
            duration
        )

    def record_network_error(self, network: str, endpoint_type: str, error_type: str) -> None:
        """Record a network error."""
        self.network_errors_total.labels(
            network=network, endpoint_type=endpoint_type, error_type=error_type
        ).inc()

    def set_active_connections(self, network: str, count: int) -> None:
        """Set the number of active connections."""
        self.active_connections.labels(network=network).set(count)

    # Trading metrics methods
    def record_order_placement(self, network: str, trading_pair: str, side: str, status: str) -> None:
        """Record an order placement."""
        self.orders_placed_total.labels(
            network=network, trading_pair=trading_pair, side=side, status=status
        ).inc()

    def record_order_fill(self, network: str, trading_pair: str, side: str, duration: float) -> None:
        """Record an order fill."""
        self.order_fill_duration.labels(
            network=network, trading_pair=trading_pair, side=side
        ).observe(duration)

    def record_trading_volume(self, network: str, trading_pair: str, side: str, volume_xlm: float) -> None:
        """Record trading volume."""
        self.trading_volume.labels(network=network, trading_pair=trading_pair, side=side).inc(
            volume_xlm
        )

    def set_order_book_spread(self, network: str, trading_pair: str, spread_percent: float) -> None:
        """Set the current order book spread."""
        self.order_book_spread.labels(network=network, trading_pair=trading_pair).set(
            spread_percent
        )

    # Account metrics methods
    def set_account_balance(
        self, network: str, account_id: str, asset_code: str, balance_xlm: float
    ):
        """Set account balance."""
        self.account_balances.labels(
            network=network, account_id=account_id, asset_code=asset_code
        ).set(balance_xlm)

    def set_trustline_count(self, network: str, account_id: str, count: int):
        """Set trustline count."""
        self.trustline_count.labels(network=network, account_id=account_id).set(count)

    # Health metrics methods
    def record_health_check(self, network: str, check_type: str, duration: float):
        """Record a health check."""
        self.health_check_duration.labels(network=network, check_type=check_type).observe(duration)

    def set_endpoint_health(self, network: str, endpoint_type: str, url: str, is_healthy: bool):
        """Set endpoint health status."""
        self.endpoint_health_status.labels(
            network=network, endpoint_type=endpoint_type, url=url
        ).set(1 if is_healthy else 0)

    def set_circuit_breaker_state(self, network: str, endpoint: str, state: int):
        """Set circuit breaker state (0=closed, 1=open, 2=half-open)."""
        self.circuit_breaker_state.labels(network=network, endpoint=endpoint).set(state)

    # Cache metrics methods
    def record_cache_hit(self, cache_type: str):
        """Record a cache hit."""
        self.cache_hits_total.labels(cache_type=cache_type).inc()

    def record_cache_miss(self, cache_type: str):
        """Record a cache miss."""
        self.cache_misses_total.labels(cache_type=cache_type).inc()

    def set_cache_size(self, cache_type: str, size: int):
        """Set cache size."""
        self.cache_size.labels(cache_type=cache_type).set(size)

    # Error metrics methods
    def record_error(self, category: str, severity: str, operation: str):
        """Record an error."""
        self.errors_total.labels(category=category, severity=severity, operation=operation).inc()

    def record_error_recovery(self, strategy: str, success: bool):
        """Record an error recovery attempt."""
        self.error_recovery_attempts.labels(strategy=strategy, success=str(success).lower()).inc()

    # System metrics methods
    def set_memory_usage(self, component: str, bytes_used: int):
        """Set memory usage."""
        self.memory_usage_bytes.labels(component=component).set(bytes_used)

    def set_cpu_usage(self, component: str, percent: float):
        """Set CPU usage."""
        self.cpu_usage_percent.labels(component=component).set(percent)

    # Business metrics methods
    def set_profit_loss(self, network: str, trading_pair: str, strategy: str, pnl_xlm: float):
        """Set profit/loss."""
        self.profit_loss_xlm.labels(
            network=network, trading_pair=trading_pair, strategy=strategy
        ).set(pnl_xlm)

    def record_arbitrage_opportunity(self, network: str, asset_pair: str, executed: bool):
        """Record an arbitrage opportunity."""
        self.arbitrage_opportunities.labels(
            network=network, asset_pair=asset_pair, executed=str(executed).lower()
        ).inc()

    # QA and Testing metrics methods
    def update_test_coverage(
        self, module: str, coverage_percentage: float, coverage_type: str = "line"
    ):
        """Update test coverage percentage for a module."""
        self.qa_test_coverage.labels(module=module, coverage_type=coverage_type).set(
            coverage_percentage
        )

        self.logger.debug(
            f"Updated test coverage for {module}: {coverage_percentage}%",
            category=LogCategory.METRICS,
            module=module,
            coverage=coverage_percentage,
            type=coverage_type,
        )

    def update_test_success_rate(
        self, test_suite: str, success_rate: float, test_type: str = "unit"
    ):
        """Update test success rate for a test suite."""
        self.qa_test_success_rate.labels(test_suite=test_suite, test_type=test_type).set(
            success_rate
        )

    def update_critical_module_coverage(
        self, module: str, coverage_percentage: float, threshold_type: str = "critical"
    ):
        """Update critical module coverage percentage."""
        self.qa_critical_module_coverage.labels(module=module, threshold_type=threshold_type).set(
            coverage_percentage
        )

    def record_test_execution(
        self, test_suite: str, duration_seconds: float, test_category: str = "unit"
    ):
        """Record test execution duration."""
        self.qa_test_execution_duration.labels(
            test_suite=test_suite, test_category=test_category
        ).observe(duration_seconds)

    def record_test_failure(self, test_suite: str, failure_type: str, module: str = "unknown"):
        """Record a test failure."""
        self.qa_test_failures_total.labels(
            test_suite=test_suite, failure_type=failure_type, module=module
        ).inc()

    def update_code_quality_score(self, module: str, score: float, metric_type: str = "complexity"):
        """Update code quality score for a module."""
        self.qa_code_quality_score.labels(module=module, metric_type=metric_type).set(score)

    def update_requirements_compliance(
        self, requirement_category: str, compliance_percentage: float, priority: str = "high"
    ):
        """Update requirements compliance percentage."""
        self.qa_requirements_compliance.labels(
            requirement_category=requirement_category, priority=priority
        ).set(compliance_percentage)

    def update_security_compliance(
        self, security_category: str, score: float, requirement_level: str = "mandatory"
    ):
        """Update security compliance score."""
        self.qa_security_compliance_score.labels(
            security_category=security_category, requirement_level=requirement_level
        ).set(score)

    def get_qa_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all QA metrics."""
        summary = {
            "coverage_metrics": {
                "overall_coverage": self.qa_test_coverage,
                "critical_module_coverage": self.qa_critical_module_coverage,
            },
            "quality_metrics": {
                "test_success_rate": self.qa_test_success_rate,
                "code_quality_score": self.qa_code_quality_score,
            },
            "compliance_metrics": {
                "requirements_compliance": self.qa_requirements_compliance,
                "security_compliance": self.qa_security_compliance_score,
            },
            "failure_metrics": {
                "test_failures": self.qa_test_failures_total,
                "execution_duration": self.qa_test_execution_duration,
            },
        }
        return summary

    @asynccontextmanager
    async def time_operation(self, metric_name: str, **labels):
        """Context manager to time operations."""
        if metric_name not in self._metrics:
            raise ValueError(f"Unknown metric: {metric_name}")

        metric = self._metrics[metric_name]
        start_time = time.time()

        try:
            yield
        finally:
            duration = time.time() - start_time
            if hasattr(metric, "labels"):
                metric.labels(**labels).observe(duration)
            else:
                metric.observe(duration)

    def get_metrics_data(self) -> str:
        """Get metrics data in Prometheus format."""
        return generate_latest(self.registry).decode("utf-8")

    def start_metrics_server(self, port: int = 8000) -> threading.Thread:
        """Start metrics server in a separate thread."""

        def run_server():
            start_http_server(port, registry=self.registry)

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()

        self.logger.info(
            f"Metrics server started on port {port}", category=LogCategory.METRICS, port=port
        )

        return thread

    async def start_background_metrics_collection(self):
        """Start background tasks for metrics collection."""
        self._background_tasks.append(asyncio.create_task(self._collect_system_metrics()))

        self.logger.info("Background metrics collection started", category=LogCategory.METRICS)

    async def stop_background_metrics_collection(self):
        """Stop background metrics collection."""
        for task in self._background_tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()

        self.logger.info("Background metrics collection stopped", category=LogCategory.METRICS)

    async def _collect_system_metrics(self):
        """Collect system-level metrics in the background."""
        import gc

        import psutil

        while True:
            try:
                # Memory usage
                process = psutil.Process()
                memory_info = process.memory_info()
                self.set_memory_usage("connector", memory_info.rss)

                # CPU usage
                cpu_percent = process.cpu_percent()
                self.set_cpu_usage("connector", cpu_percent)

                # Python GC stats
                gc_stats = gc.get_stats()
                for i, stat in enumerate(gc_stats):
                    self.set_memory_usage(f"gc_gen_{i}", stat.get("collections", 0))

                await asyncio.sleep(30)  # Collect every 30 seconds

            except Exception as e:
                self.logger.error(
                    "Error collecting system metrics", category=LogCategory.METRICS, exception=e
                )
                await asyncio.sleep(60)  # Wait longer on error


# Global metrics instance
_metrics_instance: Optional[StellarMetrics] = None


def get_stellar_metrics() -> StellarMetrics:
    """Get or create global metrics instance."""
    global _metrics_instance
    if not _metrics_instance:
        _metrics_instance = StellarMetrics()
    return _metrics_instance


def create_custom_metric(definition: MetricDefinition) -> Any:
    """Create a custom metric using the global instance."""
    return get_stellar_metrics().create_custom_metric(definition)
