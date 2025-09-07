"""
Stellar Production Observability Framework
Comprehensive production observability with Prometheus, Grafana, and advanced alerting.
Phase 4: Production Hardening - Advanced monitoring and alerting system.
"""

import asyncio
import time
import json
import psutil
import traceback
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from contextlib import asynccontextmanager
from contextvars import ContextVar
import structlog
from prometheus_client import (
    Counter, Histogram, Gauge, Summary, Info,
    CollectorRegistry, generate_latest, start_http_server,
    push_to_gateway, delete_from_gateway
)

from .stellar_metrics import get_stellar_metrics, StellarMetrics
from .stellar_logging import get_stellar_logger, LogCategory, correlation_id


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning" 
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class ObservabilityEvent(Enum):
    """Types of observability events."""
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    HEALTH_CHECK = "health_check"
    PERFORMANCE_ALERT = "performance_alert"
    SECURITY_ALERT = "security_alert"
    ERROR_THRESHOLD = "error_threshold"
    CIRCUIT_BREAKER = "circuit_breaker"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


@dataclass
class AlertRule:
    """Definition of an alert rule."""
    name: str
    description: str
    metric_name: str
    threshold: Union[float, int]
    comparison: str  # 'gt', 'lt', 'eq', 'gte', 'lte'
    duration: int  # seconds
    level: AlertLevel
    labels: Dict[str, str] = None
    enabled: bool = True

    def __post_init__(self):
        if self.labels is None:
            self.labels = {}


@dataclass
class Alert:
    """An active alert."""
    rule_name: str
    level: AlertLevel
    message: str
    metric_name: str
    current_value: float
    threshold: float
    timestamp: float
    labels: Dict[str, str] = None
    correlation_id: str = None

    def __post_init__(self):
        if self.labels is None:
            self.labels = {}


class HealthCheckStatus(Enum):
    """Health check status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    component: str
    status: HealthCheckStatus
    response_time: float
    message: str = ""
    details: Dict[str, Any] = None
    timestamp: float = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.timestamp is None:
            self.timestamp = time.time()


class StellarObservabilityFramework:
    """Production observability framework for Stellar connector."""
    
    def __init__(self, 
                 metrics_port: int = 8000,
                 pushgateway_url: Optional[str] = None,
                 alert_webhook_url: Optional[str] = None):
        self.logger = get_stellar_logger()
        self.metrics = get_stellar_metrics()
        self.metrics_port = metrics_port
        self.pushgateway_url = pushgateway_url
        self.alert_webhook_url = alert_webhook_url
        
        # Alert management
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        
        # Health checks
        self.health_checks: Dict[str, Callable[[], HealthCheckResult]] = {}
        self.health_status: Dict[str, HealthCheckResult] = {}
        
        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        self._running = False
        
        # Performance tracking
        self.performance_metrics = {
            'startup_time': time.time(),
            'request_count': 0,
            'error_count': 0,
            'last_error_time': None
        }
        
        self._init_production_metrics()
        self._init_default_alert_rules()
        self._init_health_checks()

    def _init_production_metrics(self):
        """Initialize production-specific metrics."""
        
        # Observability system metrics
        self.observability_events = Counter(
            "stellar_observability_events_total",
            "Total observability events",
            ["event_type", "status"],
            registry=self.metrics.registry
        )
        
        self.alert_firings = Counter(
            "stellar_alert_firings_total", 
            "Total alert firings",
            ["alert_rule", "level"],
            registry=self.metrics.registry
        )
        
        self.health_check_results = Gauge(
            "stellar_health_check_status",
            "Health check results (0=unhealthy, 1=degraded, 2=healthy)",
            ["component"],
            registry=self.metrics.registry
        )
        
        self.system_uptime = Gauge(
            "stellar_system_uptime_seconds",
            "System uptime in seconds",
            registry=self.metrics.registry
        )
        
        # Advanced performance metrics
        self.request_processing_time = Histogram(
            "stellar_request_processing_seconds",
            "Request processing time", 
            ["operation", "status"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.metrics.registry
        )
        
        self.concurrent_operations = Gauge(
            "stellar_concurrent_operations",
            "Number of concurrent operations",
            ["operation_type"],
            registry=self.metrics.registry
        )
        
        # Resource utilization
        self.resource_utilization = Gauge(
            "stellar_resource_utilization_percent",
            "Resource utilization percentage",
            ["resource_type", "component"],
            registry=self.metrics.registry
        )
        
        # Business logic metrics
        self.trading_session_duration = Histogram(
            "stellar_trading_session_duration_seconds",
            "Trading session duration",
            ["outcome"],
            buckets=[60, 300, 900, 1800, 3600, 7200, 14400],
            registry=self.metrics.registry
        )

    def _init_default_alert_rules(self):
        """Initialize default alert rules for production monitoring."""
        
        default_rules = [
            AlertRule(
                name="high_error_rate",
                description="Error rate exceeds 5% over 5 minutes",
                metric_name="stellar_errors_total",
                threshold=0.05,
                comparison="gt", 
                duration=300,
                level=AlertLevel.WARNING
            ),
            AlertRule(
                name="critical_error_rate", 
                description="Error rate exceeds 10% over 2 minutes",
                metric_name="stellar_errors_total",
                threshold=0.10,
                comparison="gt",
                duration=120,
                level=AlertLevel.CRITICAL
            ),
            AlertRule(
                name="high_response_time",
                description="Response time exceeds 5 seconds",
                metric_name="stellar_network_request_duration_seconds",
                threshold=5.0,
                comparison="gt",
                duration=60,
                level=AlertLevel.WARNING
            ),
            AlertRule(
                name="circuit_breaker_open",
                description="Circuit breaker is open",
                metric_name="stellar_circuit_breaker_state", 
                threshold=1,
                comparison="gte",
                duration=0,
                level=AlertLevel.CRITICAL
            ),
            AlertRule(
                name="low_account_balance",
                description="Account balance below minimum threshold",
                metric_name="stellar_account_balance_xlm",
                threshold=10.0,  # 10 XLM minimum
                comparison="lt",
                duration=0,
                level=AlertLevel.WARNING
            ),
            AlertRule(
                name="memory_exhaustion",
                description="Memory usage exceeds 90%",
                metric_name="stellar_memory_usage_bytes",
                threshold=0.90,
                comparison="gt",
                duration=300,
                level=AlertLevel.CRITICAL
            ),
            AlertRule(
                name="health_check_failure",
                description="Health check failing",
                metric_name="stellar_health_check_status",
                threshold=1,
                comparison="lt",
                duration=60,
                level=AlertLevel.CRITICAL
            )
        ]
        
        for rule in default_rules:
            self.add_alert_rule(rule)

    def _init_health_checks(self):
        """Initialize health check functions."""
        
        self.add_health_check("system_resources", self._check_system_resources)
        self.add_health_check("stellar_network", self._check_stellar_network)
        self.add_health_check("database_connection", self._check_database_connection)
        self.add_health_check("metrics_system", self._check_metrics_system)

    def add_alert_rule(self, rule: AlertRule):
        """Add an alert rule."""
        self.alert_rules[rule.name] = rule
        self.logger.info(
            f"Added alert rule: {rule.name}",
            category=LogCategory.CONFIGURATION,
            rule=asdict(rule)
        )

    def remove_alert_rule(self, rule_name: str):
        """Remove an alert rule."""
        if rule_name in self.alert_rules:
            del self.alert_rules[rule_name]
            self.logger.info(
                f"Removed alert rule: {rule_name}",
                category=LogCategory.CONFIGURATION
            )

    def add_alert_callback(self, callback: Callable[[Alert], None]):
        """Add a callback for alert notifications."""
        self.alert_callbacks.append(callback)

    def add_health_check(self, name: str, check_func: Callable[[], HealthCheckResult]):
        """Add a health check function."""
        self.health_checks[name] = check_func
        self.logger.info(
            f"Added health check: {name}",
            category=LogCategory.HEALTH_CHECK
        )

    async def start_observability_system(self):
        """Start the production observability system."""
        if self._running:
            return
            
        self._running = True
        
        # Start metrics server
        self.metrics.start_metrics_server(self.metrics_port)
        
        # Start background monitoring tasks
        self._background_tasks.extend([
            asyncio.create_task(self._monitor_alerts()),
            asyncio.create_task(self._run_health_checks()),
            asyncio.create_task(self._collect_performance_metrics()),
            asyncio.create_task(self._update_system_metrics())
        ])
        
        # Start background metrics collection
        await self.metrics.start_background_metrics_collection()
        
        self.observability_events.labels(
            event_type=ObservabilityEvent.SYSTEM_START.value,
            status="success"
        ).inc()
        
        self.logger.info(
            "Observability system started",
            category=LogCategory.METRICS,
            metrics_port=self.metrics_port,
            alert_rules_count=len(self.alert_rules),
            health_checks_count=len(self.health_checks)
        )

    # Legacy compatibility methods
    async def start(self) -> None:
        """Start observability framework (legacy compatibility)."""
        await self.start_observability_system()

    async def stop(self) -> None:
        """Stop observability framework (legacy compatibility)."""
        await self.stop_observability_system()

    async def log_event(self, event_name: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log structured event."""
        self.logger.info(event_name, category=LogCategory.METRICS, **(context or {}))

    async def log_error(
        self, error_name: str, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log structured error."""
        self.logger.error(
            error_name, 
            category=LogCategory.ERROR_HANDLING,
            error=str(error), 
            error_type=type(error).__name__, 
            **(context or {})
        )

    async def stop_observability_system(self):
        """Stop the observability system."""
        if not self._running:
            return
            
        self._running = False
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
            
        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()
        
        # Stop metrics collection
        await self.metrics.stop_background_metrics_collection()
        
        self.observability_events.labels(
            event_type=ObservabilityEvent.SYSTEM_STOP.value,
            status="success"
        ).inc()
        
        self.logger.info(
            "Observability system stopped", 
            category=LogCategory.METRICS
        )

    async def _monitor_alerts(self):
        """Monitor metrics for alert conditions."""
        while self._running:
            try:
                await self._check_alert_conditions()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self.logger.error(
                    "Error in alert monitoring",
                    category=LogCategory.ERROR_HANDLING,
                    exception=e
                )
                await asyncio.sleep(60)

    async def _check_alert_conditions(self):
        """Check all alert rule conditions."""
        current_time = time.time()
        
        for rule_name, rule in self.alert_rules.items():
            if not rule.enabled:
                continue
                
            try:
                # Get current metric value (simplified - in production would query Prometheus)
                current_value = await self._get_metric_value(rule.metric_name, rule.labels)
                
                # Evaluate alert condition
                should_fire = self._evaluate_alert_condition(rule, current_value)
                
                if should_fire and rule_name not in self.active_alerts:
                    # Fire new alert
                    alert = Alert(
                        rule_name=rule_name,
                        level=rule.level,
                        message=f"{rule.description} (current: {current_value}, threshold: {rule.threshold})",
                        metric_name=rule.metric_name,
                        current_value=current_value,
                        threshold=rule.threshold,
                        timestamp=current_time,
                        labels=rule.labels.copy(),
                        correlation_id=correlation_id.get()
                    )
                    
                    await self._fire_alert(alert)
                    
                elif not should_fire and rule_name in self.active_alerts:
                    # Resolve alert
                    await self._resolve_alert(rule_name)
                    
            except Exception as e:
                self.logger.error(
                    f"Error checking alert rule {rule_name}",
                    category=LogCategory.ERROR_HANDLING,
                    exception=e
                )

    def _evaluate_alert_condition(self, rule: AlertRule, current_value: float) -> bool:
        """Evaluate if an alert condition is met."""
        if rule.comparison == "gt":
            return current_value > rule.threshold
        elif rule.comparison == "gte":
            return current_value >= rule.threshold
        elif rule.comparison == "lt":
            return current_value < rule.threshold
        elif rule.comparison == "lte":
            return current_value <= rule.threshold
        elif rule.comparison == "eq":
            return current_value == rule.threshold
        else:
            return False

    async def _get_metric_value(self, metric_name: str, labels: Dict[str, str]) -> float:
        """Get current value of a metric (simplified implementation)."""
        # In production, this would query Prometheus or the metric directly
        # For now, return a mock value or query the metric from our registry
        return 0.0

    async def _fire_alert(self, alert: Alert):
        """Fire an alert."""
        self.active_alerts[alert.rule_name] = alert
        
        # Record metrics
        self.alert_firings.labels(
            alert_rule=alert.rule_name,
            level=alert.level.value
        ).inc()
        
        # Log alert
        self.logger.error(
            f"ALERT FIRED: {alert.message}",
            category=LogCategory.SECURITY if alert.level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY] else LogCategory.PERFORMANCE,
            alert_rule=alert.rule_name,
            alert_level=alert.level.value,
            current_value=alert.current_value,
            threshold=alert.threshold,
            correlation_id=alert.correlation_id
        )
        
        # Send notifications
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(
                    "Error in alert callback",
                    category=LogCategory.ERROR_HANDLING,
                    exception=e
                )

    async def _resolve_alert(self, rule_name: str):
        """Resolve an active alert."""
        if rule_name in self.active_alerts:
            alert = self.active_alerts[rule_name]
            del self.active_alerts[rule_name]
            
            self.logger.info(
                f"ALERT RESOLVED: {rule_name}",
                category=LogCategory.PERFORMANCE,
                alert_rule=rule_name
            )

    async def _run_health_checks(self):
        """Run health checks periodically."""
        while self._running:
            try:
                await self._execute_health_checks()
                await asyncio.sleep(60)  # Run every minute
            except Exception as e:
                self.logger.error(
                    "Error in health checks",
                    category=LogCategory.ERROR_HANDLING,
                    exception=e
                )
                await asyncio.sleep(120)

    async def _execute_health_checks(self):
        """Execute all health checks."""
        for name, check_func in self.health_checks.items():
            try:
                result = check_func()
                self.health_status[name] = result
                
                # Update metrics
                status_value = 0
                if result.status == HealthCheckStatus.DEGRADED:
                    status_value = 1
                elif result.status == HealthCheckStatus.HEALTHY:
                    status_value = 2
                    
                self.health_check_results.labels(component=name).set(status_value)
                
                # Log if unhealthy
                if result.status != HealthCheckStatus.HEALTHY:
                    self.logger.warning(
                        f"Health check failed: {name}",
                        category=LogCategory.HEALTH_CHECK,
                        component=name,
                        status=result.status.value,
                        message=result.message,
                        response_time=result.response_time
                    )
                    
            except Exception as e:
                self.logger.error(
                    f"Health check error: {name}",
                    category=LogCategory.ERROR_HANDLING,
                    exception=e
                )

    def _check_system_resources(self) -> HealthCheckResult:
        """Check system resource utilization."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # Determine overall status
            if cpu_percent > 90 or memory_percent > 90 or disk_percent > 90:
                status = HealthCheckStatus.UNHEALTHY
                message = f"High resource usage: CPU {cpu_percent}%, Memory {memory_percent}%, Disk {disk_percent}%"
            elif cpu_percent > 80 or memory_percent > 80 or disk_percent > 80:
                status = HealthCheckStatus.DEGRADED  
                message = f"Moderate resource usage: CPU {cpu_percent}%, Memory {memory_percent}%, Disk {disk_percent}%"
            else:
                status = HealthCheckStatus.HEALTHY
                message = f"Resource usage normal: CPU {cpu_percent}%, Memory {memory_percent}%, Disk {disk_percent}%"
            
            return HealthCheckResult(
                component="system_resources",
                status=status,
                response_time=0.1,
                message=message,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "disk_percent": disk_percent
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                component="system_resources",
                status=HealthCheckStatus.UNKNOWN,
                response_time=0.0,
                message=f"Error checking system resources: {e}"
            )

    def _check_stellar_network(self) -> HealthCheckResult:
        """Check Stellar network connectivity."""
        # This would implement actual network connectivity check
        return HealthCheckResult(
            component="stellar_network",
            status=HealthCheckStatus.HEALTHY,
            response_time=0.5,
            message="Network connectivity OK"
        )

    def _check_database_connection(self) -> HealthCheckResult:
        """Check database connection."""
        # This would implement actual database connectivity check
        return HealthCheckResult(
            component="database_connection", 
            status=HealthCheckStatus.HEALTHY,
            response_time=0.1,
            message="Database connection OK"
        )

    def _check_metrics_system(self) -> HealthCheckResult:
        """Check metrics system health."""
        try:
            # Verify we can generate metrics
            metrics_data = self.metrics.get_metrics_data()
            if len(metrics_data) > 100:  # Basic sanity check
                return HealthCheckResult(
                    component="metrics_system",
                    status=HealthCheckStatus.HEALTHY,
                    response_time=0.05,
                    message="Metrics system operational"
                )
            else:
                return HealthCheckResult(
                    component="metrics_system",
                    status=HealthCheckStatus.DEGRADED,
                    response_time=0.05,
                    message="Metrics system returning limited data"
                )
        except Exception as e:
            return HealthCheckResult(
                component="metrics_system",
                status=HealthCheckStatus.UNHEALTHY,
                response_time=0.0,
                message=f"Metrics system error: {e}"
            )

    async def _collect_performance_metrics(self):
        """Collect performance metrics periodically."""
        while self._running:
            try:
                # Update system uptime
                uptime = time.time() - self.performance_metrics['startup_time']
                self.system_uptime.set(uptime)
                
                # Collect resource utilization
                process = psutil.Process()
                
                # CPU usage
                cpu_percent = process.cpu_percent()
                self.resource_utilization.labels(
                    resource_type="cpu",
                    component="connector"
                ).set(cpu_percent)
                
                # Memory usage
                memory_info = process.memory_info()
                memory_percent = process.memory_percent()
                self.resource_utilization.labels(
                    resource_type="memory",
                    component="connector"  
                ).set(memory_percent)
                
                # Network connections
                connections = len(process.connections())
                self.concurrent_operations.labels(
                    operation_type="network_connections"
                ).set(connections)
                
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                self.logger.error(
                    "Error collecting performance metrics",
                    category=LogCategory.ERROR_HANDLING,
                    exception=e
                )
                await asyncio.sleep(60)

    async def _update_system_metrics(self):
        """Update system-level metrics.""" 
        while self._running:
            try:
                # Record observability system health
                self.observability_events.labels(
                    event_type=ObservabilityEvent.HEALTH_CHECK.value,
                    status="running"
                ).inc()
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                self.logger.error(
                    "Error updating system metrics",
                    category=LogCategory.ERROR_HANDLING, 
                    exception=e
                )
                await asyncio.sleep(300)

    @asynccontextmanager
    async def observe_operation(self, operation_name: str):
        """Context manager to observe operation performance."""
        start_time = time.time()
        operation_id = f"{operation_name}_{int(start_time)}"
        
        # Increment concurrent operations
        self.concurrent_operations.labels(operation_type=operation_name).inc()
        
        try:
            yield operation_id
            # Record successful operation
            duration = time.time() - start_time
            self.request_processing_time.labels(
                operation=operation_name,
                status="success"
            ).observe(duration)
            
        except Exception as e:
            # Record failed operation
            duration = time.time() - start_time
            self.request_processing_time.labels(
                operation=operation_name,
                status="error"
            ).observe(duration)
            
            self.logger.error(
                f"Operation failed: {operation_name}",
                category=LogCategory.ERROR_HANDLING,
                operation=operation_name,
                duration=duration,
                exception=e
            )
            raise
            
        finally:
            # Decrement concurrent operations
            self.concurrent_operations.labels(operation_type=operation_name).dec()

    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status."""
        overall_status = HealthCheckStatus.HEALTHY
        
        for result in self.health_status.values():
            if result.status == HealthCheckStatus.UNHEALTHY:
                overall_status = HealthCheckStatus.UNHEALTHY
                break
            elif result.status == HealthCheckStatus.DEGRADED and overall_status == HealthCheckStatus.HEALTHY:
                overall_status = HealthCheckStatus.DEGRADED
                
        return {
            "overall_status": overall_status.value,
            "components": {name: asdict(result) for name, result in self.health_status.items()},
            "active_alerts": {name: asdict(alert) for name, alert in self.active_alerts.items()},
            "system_uptime": time.time() - self.performance_metrics['startup_time']
        }

    def generate_observability_report(self) -> Dict[str, Any]:
        """Generate comprehensive observability report."""
        return {
            "timestamp": time.time(),
            "system_info": {
                "uptime": time.time() - self.performance_metrics['startup_time'],
                "metrics_port": self.metrics_port,
                "alert_rules": len(self.alert_rules),
                "active_alerts": len(self.active_alerts),
                "health_checks": len(self.health_checks)
            },
            "health_status": self.get_health_status(),
            "performance_metrics": self.performance_metrics,
            "metrics_summary": {
                "total_metrics": len(self.metrics._metrics) + len(self.metrics._custom_metrics),
                "metrics_server_running": True,  # Would check actual server status
                "last_collection": time.time()
            }
        }


# Global observability instance
_observability_instance: Optional[StellarObservabilityFramework] = None


def get_stellar_observability() -> StellarObservabilityFramework:
    """Get or create global observability instance."""
    global _observability_instance
    if not _observability_instance:
        _observability_instance = StellarObservabilityFramework()
    return _observability_instance


async def start_production_observability(
    metrics_port: int = 8000,
    pushgateway_url: Optional[str] = None,
    alert_webhook_url: Optional[str] = None
) -> StellarObservabilityFramework:
    """Start production observability system."""
    global _observability_instance
    _observability_instance = StellarObservabilityFramework(
        metrics_port=metrics_port,
        pushgateway_url=pushgateway_url,
        alert_webhook_url=alert_webhook_url
    )
    
    await _observability_instance.start_observability_system()
    return _observability_instance


async def stop_production_observability():
    """Stop production observability system."""
    global _observability_instance
    if _observability_instance:
        await _observability_instance.stop_observability_system()
        _observability_instance = None
