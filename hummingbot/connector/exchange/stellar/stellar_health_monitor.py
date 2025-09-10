"""
Stellar Health Monitor
Advanced connection health monitoring with alerting and automatic recovery.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import auto, Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

import aiohttp

from .stellar_error_classification import ErrorContext, StellarErrorManager
from .stellar_logging import get_stellar_logger, LogCategory, with_correlation_id
from .stellar_metrics import get_stellar_metrics


class HealthStatus(Enum):
    """Health status levels."""

    HEALTHY = auto()
    DEGRADED = auto()
    UNHEALTHY = auto()
    CRITICAL = auto()
    UNKNOWN = auto()


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()


class HealthCheckType(Enum):
    """Types of health checks."""

    HORIZON_API = auto()
    SOROBAN_RPC = auto()
    CORE_NODE = auto()
    FRIENDBOT = auto()
    CUSTOM = auto()


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    endpoint: str
    check_type: HealthCheckType
    status: HealthStatus
    response_time: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EndpointHealth:
    """Health tracking for an endpoint."""

    url: str
    check_type: HealthCheckType
    current_status: HealthStatus = HealthStatus.UNKNOWN
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    total_checks: int = 0
    total_failures: int = 0
    avg_response_time: float = 0.0
    recent_results: List[HealthCheckResult] = field(default_factory=list)

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


@dataclass
class Alert:
    """Health monitoring alert."""

    id: str
    severity: AlertSeverity
    title: str
    message: str
    endpoint: Optional[str] = None
    check_type: Optional[HealthCheckType] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False


class HealthCheckProvider:
    """Base class for health check providers."""

    async def check_health(
        self, endpoint: str, session: aiohttp.ClientSession
    ) -> HealthCheckResult:
        """Perform health check for an endpoint."""
        raise NotImplementedError


class HorizonHealthChecker(HealthCheckProvider):
    """Health checker for Horizon API endpoints."""

    async def check_health(
        self, endpoint: str, session: aiohttp.ClientSession
    ) -> HealthCheckResult:
        """Check Horizon API health."""
        start_time = time.time()

        try:
            async with session.get(f"{endpoint}/") as response:
                response_time = time.time() - start_time

                if response.status == 200:
                    data = await response.json()

                    # Check for expected Horizon response structure
                    if "horizon_version" in data and "core_version" in data:
                        return HealthCheckResult(
                            endpoint=endpoint,
                            check_type=HealthCheckType.HORIZON_API,
                            status=HealthStatus.HEALTHY,
                            response_time=response_time,
                            metadata={
                                "horizon_version": data.get("horizon_version"),
                                "core_version": data.get("core_version"),
                                "current_protocol_version": data.get("current_protocol_version"),
                            },
                        )
                    else:
                        return HealthCheckResult(
                            endpoint=endpoint,
                            check_type=HealthCheckType.HORIZON_API,
                            status=HealthStatus.DEGRADED,
                            response_time=response_time,
                            error_message="Unexpected response format",
                        )
                else:
                    return HealthCheckResult(
                        endpoint=endpoint,
                        check_type=HealthCheckType.HORIZON_API,
                        status=HealthStatus.UNHEALTHY,
                        response_time=response_time,
                        error_message=f"HTTP {response.status}",
                    )

        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                endpoint=endpoint,
                check_type=HealthCheckType.HORIZON_API,
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                error_message=str(e),
            )


class SorobanHealthChecker(HealthCheckProvider):
    """Health checker for Soroban RPC endpoints."""

    async def check_health(
        self, endpoint: str, session: aiohttp.ClientSession
    ) -> HealthCheckResult:
        """Check Soroban RPC health."""
        start_time = time.time()

        try:
            # Soroban RPC health check using getHealth method
            payload = {"jsonrpc": "2.0", "id": 1, "method": "getHealth"}

            async with session.post(
                endpoint, json=payload, headers={"Content-Type": "application/json"}
            ) as response:
                response_time = time.time() - start_time

                if response.status == 200:
                    data = await response.json()

                    if "result" in data and data["result"].get("status") == "healthy":
                        return HealthCheckResult(
                            endpoint=endpoint,
                            check_type=HealthCheckType.SOROBAN_RPC,
                            status=HealthStatus.HEALTHY,
                            response_time=response_time,
                            metadata=data.get("result", {}),
                        )
                    else:
                        return HealthCheckResult(
                            endpoint=endpoint,
                            check_type=HealthCheckType.SOROBAN_RPC,
                            status=HealthStatus.DEGRADED,
                            response_time=response_time,
                            error_message="Unhealthy status in response",
                        )
                else:
                    return HealthCheckResult(
                        endpoint=endpoint,
                        check_type=HealthCheckType.SOROBAN_RPC,
                        status=HealthStatus.UNHEALTHY,
                        response_time=response_time,
                        error_message=f"HTTP {response.status}",
                    )

        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                endpoint=endpoint,
                check_type=HealthCheckType.SOROBAN_RPC,
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                error_message=str(e),
            )


class FriendbotHealthChecker(HealthCheckProvider):
    """Health checker for Friendbot endpoints."""

    async def check_health(
        self, endpoint: str, session: aiohttp.ClientSession
    ) -> HealthCheckResult:
        """Check Friendbot health."""
        start_time = time.time()

        try:
            # Simple GET request to check if friendbot is responding
            async with session.get(endpoint) as response:
                response_time = time.time() - start_time

                # Friendbot typically returns 400 for GET without addr parameter
                # which is actually a healthy response
                if response.status in [200, 400]:
                    return HealthCheckResult(
                        endpoint=endpoint,
                        check_type=HealthCheckType.FRIENDBOT,
                        status=HealthStatus.HEALTHY,
                        response_time=response_time,
                    )
                else:
                    return HealthCheckResult(
                        endpoint=endpoint,
                        check_type=HealthCheckType.FRIENDBOT,
                        status=HealthStatus.UNHEALTHY,
                        response_time=response_time,
                        error_message=f"HTTP {response.status}",
                    )

        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                endpoint=endpoint,
                check_type=HealthCheckType.FRIENDBOT,
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                error_message=str(e),
            )


class StellarHealthMonitor:
    """Advanced health monitoring system for Stellar endpoints."""

    def __init__(
        self,
        check_interval: int = 30,
        failure_threshold: int = 3,
        recovery_threshold: int = 2,
        history_size: int = 100,
    ) -> None:
        self.logger = get_stellar_logger()
        self.metrics = get_stellar_metrics()
        self.error_manager = StellarErrorManager()

        # Configuration
        self.check_interval = check_interval
        self.failure_threshold = failure_threshold
        self.recovery_threshold = recovery_threshold
        self.history_size = history_size

        # Health tracking
        self.endpoint_health: Dict[str, EndpointHealth] = {}
        self.health_checkers: Dict[HealthCheckType, HealthCheckProvider] = {
            HealthCheckType.HORIZON_API: HorizonHealthChecker(),
            HealthCheckType.SOROBAN_RPC: SorobanHealthChecker(),
            HealthCheckType.FRIENDBOT: FriendbotHealthChecker(),
        }

        # Alerting
        self.alerts: Dict[str, Alert] = {}
        self.alert_handlers: List[Callable[[Alert], Awaitable[None]]] = []
        self.suppressed_alerts: Set[str] = set()

        # Background tasks
        self._monitoring_task: Optional[asyncio.Task[None]] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._running = False

        # Callbacks
        self.failure_callbacks: List[Callable[[str, HealthCheckResult], Awaitable[None]]] = []
        self.recovery_callbacks: List[Callable[[str, HealthCheckResult], Awaitable[None]]] = []

    async def start(self) -> None:
        """Start health monitoring."""
        if self._running:
            return

        self._running = True
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "StellarHealthMonitor/3.0.0"},
        )

        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

        self.logger.info(
            "Health monitoring started",
            category=LogCategory.HEALTH_CHECK,
            check_interval=self.check_interval,
        )

    async def stop(self) -> None:
        """Stop health monitoring."""
        if not self._running:
            return

        self._running = False

        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        if self._session:
            await self._session.close()

        self.logger.info("Health monitoring stopped", category=LogCategory.HEALTH_CHECK)

    def add_endpoint(self, url: str, check_type: HealthCheckType) -> None:
        """Add an endpoint for monitoring."""
        if url not in self.endpoint_health:
            self.endpoint_health[url] = EndpointHealth(url=url, check_type=check_type)

            self.logger.info(
                f"Added endpoint for monitoring: {url}",
                category=LogCategory.HEALTH_CHECK,
                check_type=check_type.name,
            )

    def remove_endpoint(self, url: str):
        """Remove an endpoint from monitoring."""
        if url in self.endpoint_health:
            del self.endpoint_health[url]

            # Clear related alerts
            alerts_to_remove = [
                alert_id for alert_id, alert in self.alerts.items() if alert.endpoint == url
            ]

            for alert_id in alerts_to_remove:
                del self.alerts[alert_id]

            self.logger.info(
                f"Removed endpoint from monitoring: {url}", category=LogCategory.HEALTH_CHECK
            )

    def add_alert_handler(self, handler: Callable[[Alert], Awaitable[None]]) -> None:
        """Add an alert handler."""
        self.alert_handlers.append(handler)

    def add_failure_callback(self, callback: Callable[[str, HealthCheckResult], Awaitable[None]]) -> None:
        """Add a callback for endpoint failures."""
        self.failure_callbacks.append(callback)

    def add_recovery_callback(self, callback: Callable[[str, HealthCheckResult], Awaitable[None]]) -> None:
        """Add a callback for endpoint recoveries."""
        self.recovery_callbacks.append(callback)

    async def check_endpoint_health(self, url: str) -> Optional[HealthCheckResult]:
        """Manually check health of a specific endpoint."""
        if url not in self.endpoint_health:
            return None

        endpoint_health = self.endpoint_health[url]
        checker = self.health_checkers.get(endpoint_health.check_type)

        if not checker:
            return None

        with with_correlation_id() as logger:
            logger.debug(
                f"Checking health for {url}",
                category=LogCategory.HEALTH_CHECK,
                check_type=endpoint_health.check_type.name,
            )

            result = await checker.check_health(url, self._session)
            await self._process_health_result(url, result)

            return result

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                # Check all endpoints concurrently
                tasks = [self.check_endpoint_health(url) for url in self.endpoint_health.keys()]

                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

                # Wait for next check interval
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                self.logger.error(
                    "Error in monitoring loop", category=LogCategory.HEALTH_CHECK, exception=e
                )
                await asyncio.sleep(min(self.check_interval, 60))

    async def _process_health_result(self, url: str, result: HealthCheckResult) -> None:
        """Process health check result and update tracking."""
        endpoint_health = self.endpoint_health[url]

        # Update statistics
        endpoint_health.total_checks += 1
        endpoint_health.recent_results.append(result)

        # Keep only recent results
        if len(endpoint_health.recent_results) > self.history_size:
            endpoint_health.recent_results = endpoint_health.recent_results[-self.history_size :]

        # Update average response time
        total_time = sum(r.response_time for r in endpoint_health.recent_results)
        endpoint_health.avg_response_time = total_time / len(endpoint_health.recent_results)

        # Update failure/success tracking
        old_status = endpoint_health.current_status

        if result.status == HealthStatus.HEALTHY:
            endpoint_health.consecutive_successes += 1
            endpoint_health.consecutive_failures = 0
            endpoint_health.last_success = result.timestamp

            # Check for recovery
            if (
                old_status != HealthStatus.HEALTHY
                and endpoint_health.consecutive_successes >= self.recovery_threshold
            ):
                endpoint_health.current_status = HealthStatus.HEALTHY
                await self._handle_recovery(url, result)

        else:
            endpoint_health.consecutive_failures += 1
            endpoint_health.consecutive_successes = 0
            endpoint_health.last_failure = result.timestamp
            endpoint_health.total_failures += 1

            # Determine new status
            if endpoint_health.consecutive_failures >= self.failure_threshold:
                if result.status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
                    endpoint_health.current_status = HealthStatus.UNHEALTHY
                else:
                    endpoint_health.current_status = HealthStatus.DEGRADED

                # Handle failure if status changed
                if old_status != endpoint_health.current_status:
                    await self._handle_failure(url, result)

        # Record metrics
        self.metrics.record_health_check(
            network="all",  # Would be network-specific in real implementation
            check_type=result.check_type.name.lower(),
            duration=result.response_time,
        )

        self.metrics.set_endpoint_health(
            network="all",
            endpoint_type=result.check_type.name.lower(),
            url=url,
            is_healthy=result.status == HealthStatus.HEALTHY,
        )

    async def _handle_failure(self, url: str, result: HealthCheckResult) -> None:
        """Handle endpoint failure."""
        endpoint_health = self.endpoint_health[url]

        with with_correlation_id() as logger:
            logger.warning(
                f"Endpoint failure detected: {url}",
                category=LogCategory.HEALTH_CHECK,
                consecutive_failures=endpoint_health.consecutive_failures,
                error_message=result.error_message,
                check_type=result.check_type.name,
            )

        # Create alert
        alert = Alert(
            id=f"failure_{url}_{int(time.time())}",
            severity=(
                AlertSeverity.ERROR
                if endpoint_health.current_status == HealthStatus.DEGRADED
                else AlertSeverity.CRITICAL
            ),
            title=f"Endpoint Failure: {url}",
            message=f"Endpoint {url} is {endpoint_health.current_status.name.lower()}. "
            f"Failed {endpoint_health.consecutive_failures} consecutive times. "
            f"Error: {result.error_message or 'Unknown error'}",
            endpoint=url,
            check_type=result.check_type,
            metadata={
                "consecutive_failures": endpoint_health.consecutive_failures,
                "response_time": result.response_time,
                "success_rate_1h": endpoint_health.get_success_rate(60),
            },
        )

        await self._send_alert(alert)

        # Call failure callbacks
        for callback in self.failure_callbacks:
            try:
                await callback(url, result)
            except Exception as e:
                self.logger.error(
                    "Error in failure callback", category=LogCategory.HEALTH_CHECK, exception=e
                )

    async def _handle_recovery(self, url: str, result: HealthCheckResult) -> None:
        """Handle endpoint recovery."""
        endpoint_health = self.endpoint_health[url]

        with with_correlation_id() as logger:
            logger.info(
                f"Endpoint recovery detected: {url}",
                category=LogCategory.HEALTH_CHECK,
                consecutive_successes=endpoint_health.consecutive_successes,
                check_type=result.check_type.name,
            )

        # Create recovery alert
        alert = Alert(
            id=f"recovery_{url}_{int(time.time())}",
            severity=AlertSeverity.INFO,
            title=f"Endpoint Recovery: {url}",
            message=f"Endpoint {url} has recovered and is now healthy. "
            f"Succeeded {endpoint_health.consecutive_successes} consecutive times.",
            endpoint=url,
            check_type=result.check_type,
            metadata={
                "consecutive_successes": endpoint_health.consecutive_successes,
                "response_time": result.response_time,
                "downtime_duration": self._calculate_downtime(endpoint_health),
            },
        )

        await self._send_alert(alert)

        # Call recovery callbacks
        for callback in self.recovery_callbacks:
            try:
                await callback(url, result)
            except Exception as e:
                self.logger.error(
                    "Error in recovery callback", category=LogCategory.HEALTH_CHECK, exception=e
                )

    async def _send_alert(self, alert: Alert) -> None:
        """Send alert to all registered handlers."""
        # Check if this type of alert is suppressed
        alert_key = f"{alert.endpoint}:{alert.check_type.name if alert.check_type else 'none'}"
        if alert_key in self.suppressed_alerts:
            return

        self.alerts[alert.id] = alert

        self.logger.info(
            f"Alert generated: {alert.title}",
            category=LogCategory.HEALTH_CHECK,
            severity=alert.severity.name,
            alert_id=alert.id,
        )

        # Send to all handlers
        for handler in self.alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                self.logger.error(
                    "Error in alert handler", category=LogCategory.HEALTH_CHECK, exception=e
                )

    def _calculate_downtime(self, endpoint_health: EndpointHealth) -> Optional[float]:
        """Calculate downtime duration in seconds."""
        if not endpoint_health.last_failure or not endpoint_health.last_success:
            return None

        if endpoint_health.last_success > endpoint_health.last_failure:
            return (endpoint_health.last_success - endpoint_health.last_failure).total_seconds()

        return None

    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary."""
        total_endpoints = len(self.endpoint_health)
        healthy_endpoints = sum(
            1
            for health in self.endpoint_health.values()
            if health.current_status == HealthStatus.HEALTHY
        )
        degraded_endpoints = sum(
            1
            for health in self.endpoint_health.values()
            if health.current_status == HealthStatus.DEGRADED
        )
        unhealthy_endpoints = sum(
            1
            for health in self.endpoint_health.values()
            if health.current_status == HealthStatus.UNHEALTHY
        )

        return {
            "total_endpoints": total_endpoints,
            "healthy_endpoints": healthy_endpoints,
            "degraded_endpoints": degraded_endpoints,
            "unhealthy_endpoints": unhealthy_endpoints,
            "overall_health_percentage": (healthy_endpoints / max(total_endpoints, 1)) * 100,
            "active_alerts": len([a for a in self.alerts.values() if not a.resolved]),
            "monitoring_running": self._running,
        }

    def get_endpoint_status(self, url: str) -> Optional[Dict[str, Any]]:
        """Get detailed status for a specific endpoint."""
        if url not in self.endpoint_health:
            return None

        health = self.endpoint_health[url]
        return {
            "url": url,
            "status": health.current_status.name,
            "check_type": health.check_type.name,
            "consecutive_failures": health.consecutive_failures,
            "consecutive_successes": health.consecutive_successes,
            "total_checks": health.total_checks,
            "total_failures": health.total_failures,
            "success_rate": (health.total_checks - health.total_failures)
            / max(health.total_checks, 1),
            "avg_response_time": health.avg_response_time,
            "last_success": health.last_success.isoformat() if health.last_success else None,
            "last_failure": health.last_failure.isoformat() if health.last_failure else None,
            "success_rate_1h": health.get_success_rate(60),
            "success_rate_24h": health.get_success_rate(1440),
        }

    def suppress_alerts(self, endpoint: str, check_type: Optional[HealthCheckType] = None):
        """Suppress alerts for an endpoint."""
        alert_key = f"{endpoint}:{check_type.name if check_type else 'none'}"
        self.suppressed_alerts.add(alert_key)

    def unsuppress_alerts(self, endpoint: str, check_type: Optional[HealthCheckType] = None):
        """Unsuppress alerts for an endpoint."""
        alert_key = f"{endpoint}:{check_type.name if check_type else 'none'}"
        self.suppressed_alerts.discard(alert_key)
