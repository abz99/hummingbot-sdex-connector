"""
Unified Observability and Health Types Module
Canonical definitions for observability, alerting, and health monitoring types.

This module consolidates duplicate observability-related types across the codebase
to establish a single source of truth while maintaining semantic clarity.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import auto, Enum
from typing import Any, Dict, List, Optional, Union

try:
    from pydantic import BaseModel, Field
except ImportError:
    # Fallback for environments without Pydantic
    class BaseModel:
        pass

    def Field(**kwargs):
        return kwargs.get("default")


# =============================================================================
# ALERT SYSTEM TYPES
# =============================================================================


class AlertSeverity(Enum):
    """Unified alert severity levels for all monitoring systems."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    EMERGENCY = "emergency"  # Highest severity for production incidents


class AlertCategory(Enum):
    """Categories of alerts for better organization."""

    HEALTH = "health"
    PERFORMANCE = "performance"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    SYSTEM = "system"
    BUSINESS = "business"


class AlertStatus(Enum):
    """Current status of an alert."""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class UnifiedAlert:
    """Unified alert structure for all monitoring systems."""

    id: str
    severity: AlertSeverity
    category: AlertCategory
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Context information
    source_component: Optional[str] = None
    endpoint: Optional[str] = None
    metric_name: Optional[str] = None
    current_value: Optional[float] = None
    threshold: Optional[float] = None

    # Alert management
    status: AlertStatus = AlertStatus.ACTIVE
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    # Metadata and labels
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None

    # Rule-based alerts
    rule_name: Optional[str] = None
    duration: Optional[int] = None  # seconds the condition has been true


@dataclass
class AlertRule:
    """Definition of an alert rule for monitoring."""

    name: str
    description: str
    category: AlertCategory
    severity: AlertSeverity

    # Rule conditions
    metric_name: str
    threshold: Union[float, int]
    comparison: str  # 'gt', 'lt', 'eq', 'gte', 'lte'
    duration: int  # seconds condition must be true

    # Configuration
    enabled: bool = True
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# HEALTH CHECK TYPES
# =============================================================================


class HealthStatus(Enum):
    """Unified health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class HealthCheckType(Enum):
    """Types of health checks supported."""

    # Network endpoints
    HORIZON_API = "horizon_api"
    SOROBAN_RPC = "soroban_rpc"
    CORE_NODE = "core_node"
    FRIENDBOT = "friendbot"

    # System components
    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"

    # Business logic
    TRADING = "trading"
    LIQUIDITY = "liquidity"
    SECURITY = "security"

    # Generic
    COMPONENT = "component"
    CUSTOM = "custom"


@dataclass
class UnifiedHealthCheckResult:
    """Unified health check result structure."""

    # Basic information
    component: str
    check_type: HealthCheckType
    status: HealthStatus
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Performance metrics
    response_time: float = 0.0

    # Status details
    message: str = ""
    error_message: Optional[str] = None

    # Context information
    endpoint: Optional[str] = None
    version: Optional[str] = None

    # Detailed information
    details: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # For numeric timestamp compatibility
    @property
    def timestamp_float(self) -> float:
        """Get timestamp as float for backward compatibility."""
        return self.timestamp.timestamp()


@dataclass
class EndpointHealth:
    """Health tracking for monitored endpoints."""

    url: str
    check_type: HealthCheckType
    current_status: HealthStatus = HealthStatus.UNKNOWN

    # Failure tracking
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None

    # Statistics
    total_checks: int = 0
    total_failures: int = 0
    avg_response_time: float = 0.0

    # Recent results for trend analysis
    recent_results: List[UnifiedHealthCheckResult] = field(default_factory=list)
    max_recent_results: int = 100

    def add_result(self, result: UnifiedHealthCheckResult) -> None:
        """Add a new health check result and update statistics."""
        self.recent_results.append(result)

        # Keep only recent results
        if len(self.recent_results) > self.max_recent_results:
            self.recent_results = self.recent_results[-self.max_recent_results :]

        # Update statistics
        self.total_checks += 1
        self.current_status = result.status

        if result.status == HealthStatus.HEALTHY:
            self.consecutive_successes += 1
            self.consecutive_failures = 0
            self.last_success = result.timestamp
        else:
            self.consecutive_failures += 1
            self.consecutive_successes = 0
            self.last_failure = result.timestamp
            self.total_failures += 1

        # Update average response time
        total_time = self.avg_response_time * (self.total_checks - 1) + result.response_time
        self.avg_response_time = total_time / self.total_checks

    def get_success_rate(self, window_minutes: int = 60) -> float:
        """Get success rate over time window."""
        if not self.recent_results:
            return 0.0

        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        recent = [r for r in self.recent_results if r.timestamp > cutoff]

        if not recent:
            return 0.0

        successes = sum(1 for r in recent if r.status == HealthStatus.HEALTHY)
        return successes / len(recent)


# =============================================================================
# BACKWARD COMPATIBILITY ALIASES
# =============================================================================

# Health Monitor compatibility
Alert = UnifiedAlert
HealthCheckResult = UnifiedHealthCheckResult

# Observability compatibility
AlertLevel = AlertSeverity
HealthCheckStatus = HealthStatus

# Create compatibility wrappers for different field names


class HealthMonitorAlertCompat:
    """Backward compatibility for health monitor Alert class."""

    def __init__(
        self,
        id: str,
        severity: AlertSeverity,
        title: str,
        message: str,
        endpoint: Optional[str] = None,
        check_type: Optional[HealthCheckType] = None,
        **kwargs,
    ):
        self.alert = UnifiedAlert(
            id=id,
            severity=severity,
            category=AlertCategory.HEALTH,
            title=title,
            message=message,
            endpoint=endpoint,
            source_component=str(check_type) if check_type else None,
            **kwargs,
        )

    def __getattr__(self, name):
        return getattr(self.alert, name)


class ObservabilityAlertCompat:
    """Backward compatibility for observability Alert class."""

    def __init__(
        self,
        rule_name: str,
        level: AlertSeverity,
        message: str,
        metric_name: str,
        current_value: float,
        threshold: float,
        **kwargs,
    ):
        self.alert = UnifiedAlert(
            id=f"{rule_name}_{int(time.time())}",
            severity=level,
            category=AlertCategory.PERFORMANCE,
            title=rule_name,
            message=message,
            metric_name=metric_name,
            current_value=current_value,
            threshold=threshold,
            rule_name=rule_name,
            **kwargs,
        )

    def __getattr__(self, name):
        return getattr(self.alert, name)


class HealthCheckResultCompat:
    """Backward compatibility for different HealthCheckResult field names."""

    def __init__(
        self,
        component: Optional[str] = None,
        endpoint: Optional[str] = None,
        check_type: Optional[HealthCheckType] = None,
        status: Optional[HealthStatus] = None,
        response_time: float = 0.0,
        message: str = "",
        **kwargs,
    ):
        # Determine component name
        comp = component or endpoint or "unknown"

        self.result = UnifiedHealthCheckResult(
            component=comp,
            check_type=check_type or HealthCheckType.CUSTOM,
            status=status or HealthStatus.UNKNOWN,
            response_time=response_time,
            message=message,
            endpoint=endpoint,
            **kwargs,
        )

    def __getattr__(self, name):
        # Map old field names to new ones
        if name == "timestamp" and hasattr(self.result, "timestamp_float"):
            return self.result.timestamp_float
        return getattr(self.result, name)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # New unified types
    "AlertSeverity",
    "AlertCategory",
    "AlertStatus",
    "UnifiedAlert",
    "AlertRule",
    "HealthStatus",
    "HealthCheckType",
    "UnifiedHealthCheckResult",
    "EndpointHealth",
    # Backward compatibility aliases
    "Alert",  # -> UnifiedAlert
    "AlertLevel",  # -> AlertSeverity
    "HealthCheckResult",  # -> UnifiedHealthCheckResult
    "HealthCheckStatus",  # -> HealthStatus
    # Compatibility wrappers
    "HealthMonitorAlertCompat",
    "ObservabilityAlertCompat",
    "HealthCheckResultCompat",
]
