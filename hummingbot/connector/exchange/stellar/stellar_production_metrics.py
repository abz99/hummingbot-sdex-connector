"""
Stellar Production Metrics Framework
Advanced production-grade metrics collection and monitoring.
Phase 4: Production Hardening - Enhanced metrics and business KPIs.
"""

import asyncio
import json
import time
import traceback
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import psutil
import structlog
from prometheus_client import Counter, Gauge, Histogram, Info, Summary

from .stellar_logging import get_stellar_logger, LogCategory
from .stellar_metrics import get_stellar_metrics, StellarMetrics
from .stellar_observability import get_stellar_observability


class ProductionMetricType(Enum):
    """Types of production metrics."""

    BUSINESS_KPI = "business_kpi"
    TECHNICAL_HEALTH = "technical_health"
    PERFORMANCE_SLA = "performance_sla"
    CAPACITY_PLANNING = "capacity_planning"
    COST_OPTIMIZATION = "cost_optimization"
    COMPLIANCE_TRACKING = "compliance_tracking"
    ANOMALY_DETECTION = "anomaly_detection"
    PREDICTIVE_INSIGHT = "predictive_insight"


class AlertSeverity(Enum):
    """Production alert severity levels."""

    P0_CRITICAL = "p0_critical"  # System down, immediate response
    P1_HIGH = "p1_high"  # Major functionality impaired
    P2_MEDIUM = "p2_medium"  # Performance degraded
    P3_LOW = "p3_low"  # Minor issues or warnings
    P4_INFO = "p4_info"  # Informational alerts


@dataclass
class ProductionMetric:
    """Production-grade metric definition."""

    name: str
    metric_type: ProductionMetricType
    description: str
    labels: Dict[str, str]
    value: Union[float, int, str]
    timestamp: float
    source: str
    critical_threshold: Optional[float] = None
    warning_threshold: Optional[float] = None
    expected_range: Optional[Tuple[float, float]] = None
    business_impact: str = ""
    remediation_steps: List[str] = None

    def __post_init__(self):
        if self.remediation_steps is None:
            self.remediation_steps = []


@dataclass
class BusinessKPI:
    """Business Key Performance Indicator."""

    name: str
    current_value: float
    target_value: float
    trend: str  # 'improving', 'stable', 'declining'
    period: str  # 'hourly', 'daily', 'weekly', 'monthly'
    unit: str
    critical_threshold: float
    warning_threshold: float
    business_impact: str
    owner: str
    last_updated: float


class StellarProductionMetricsFramework:
    """Production-grade metrics framework for Stellar connector."""

    def __init__(self):
        self.logger = get_stellar_logger()
        self.base_metrics = get_stellar_metrics()
        self.observability = get_stellar_observability()

        # Production metrics storage
        self.production_metrics: Dict[str, ProductionMetric] = {}
        self.business_kpis: Dict[str, BusinessKPI] = {}
        self.metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

        # Performance tracking
        self.performance_baseline: Dict[str, float] = {}
        self.anomaly_detectors: Dict[str, Callable] = {}

        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        self._running = False
        self._collection_interval = 30  # seconds

        self._init_production_metrics()
        self._init_business_kpis()
        self._init_anomaly_detectors()

    def _init_production_metrics(self):
        """Initialize production-specific Prometheus metrics."""

        # Business KPI metrics
        self.trading_revenue_total = Counter(
            "stellar_trading_revenue_xlm_total",
            "Total trading revenue in XLM",
            ["strategy", "trading_pair", "time_period"],
            registry=self.base_metrics.registry,
        )

        self.trading_volume_24h = Gauge(
            "stellar_trading_volume_24h_xlm",
            "24-hour trading volume in XLM",
            ["trading_pair", "side"],
            registry=self.base_metrics.registry,
        )

        self.active_strategies = Gauge(
            "stellar_active_strategies_count",
            "Number of active trading strategies",
            ["strategy_type", "status"],
            registry=self.base_metrics.registry,
        )

        self.arbitrage_profit_total = Counter(
            "stellar_arbitrage_profit_xlm_total",
            "Total arbitrage profit in XLM",
            ["asset_pair", "exchange_pair"],
            registry=self.base_metrics.registry,
        )

        # Technical SLA metrics
        self.order_execution_sla = Histogram(
            "stellar_order_execution_seconds",
            "Order execution time SLA",
            ["order_type", "trading_pair", "sla_tier"],
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 300.0],
            registry=self.base_metrics.registry,
        )

        self.api_availability_sla = Gauge(
            "stellar_api_availability_percentage",
            "API availability SLA percentage",
            ["api_endpoint", "time_window"],
            registry=self.base_metrics.registry,
        )

        self.data_freshness_seconds = Gauge(
            "stellar_data_freshness_seconds",
            "Age of the latest data in seconds",
            ["data_source", "data_type"],
            registry=self.base_metrics.registry,
        )

        # Capacity planning metrics
        self.resource_saturation = Gauge(
            "stellar_resource_saturation_percentage",
            "Resource saturation percentage",
            ["resource_type", "instance", "capacity_tier"],
            registry=self.base_metrics.registry,
        )

        self.concurrent_user_sessions = Gauge(
            "stellar_concurrent_user_sessions",
            "Number of concurrent user sessions",
            ["session_type", "user_tier"],
            registry=self.base_metrics.registry,
        )

        self.throughput_peak_capacity = Gauge(
            "stellar_throughput_peak_capacity_ops_per_second",
            "Peak throughput capacity in operations per second",
            ["operation_type", "capacity_model"],
            registry=self.base_metrics.registry,
        )

        # Cost optimization metrics
        self.infrastructure_cost_hourly = Gauge(
            "stellar_infrastructure_cost_usd_per_hour",
            "Infrastructure cost per hour in USD",
            ["cost_center", "environment", "resource_type"],
            registry=self.base_metrics.registry,
        )

        self.transaction_fee_efficiency = Gauge(
            "stellar_transaction_fee_efficiency_percentage",
            "Transaction fee efficiency percentage",
            ["fee_strategy", "network_condition"],
            registry=self.base_metrics.registry,
        )

        # Compliance and audit metrics
        self.compliance_checks_total = Counter(
            "stellar_compliance_checks_total",
            "Total compliance checks performed",
            ["check_type", "result", "regulation"],
            registry=self.base_metrics.registry,
        )

        self.audit_events_total = Counter(
            "stellar_audit_events_total",
            "Total audit events logged",
            ["event_category", "severity", "user_type"],
            registry=self.base_metrics.registry,
        )

        # Anomaly detection metrics
        self.anomaly_scores = Histogram(
            "stellar_anomaly_scores",
            "Anomaly detection scores",
            ["detector_type", "metric_name"],
            buckets=[0.1, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 0.99],
            registry=self.base_metrics.registry,
        )

        self.model_prediction_accuracy = Gauge(
            "stellar_model_prediction_accuracy_percentage",
            "Machine learning model prediction accuracy",
            ["model_name", "prediction_type", "time_horizon"],
            registry=self.base_metrics.registry,
        )

        # User experience metrics
        self.user_journey_completion_rate = Gauge(
            "stellar_user_journey_completion_percentage",
            "User journey completion rate",
            ["journey_type", "user_segment"],
            registry=self.base_metrics.registry,
        )

        self.feature_adoption_rate = Gauge(
            "stellar_feature_adoption_percentage",
            "Feature adoption rate by users",
            ["feature_name", "user_cohort", "time_period"],
            registry=self.base_metrics.registry,
        )

    def _init_business_kpis(self):
        """Initialize business KPI definitions."""

        self.business_kpis = {
            "daily_trading_volume": BusinessKPI(
                name="Daily Trading Volume",
                current_value=0.0,
                target_value=10000.0,  # 10,000 XLM
                trend="stable",
                period="daily",
                unit="XLM",
                critical_threshold=1000.0,
                warning_threshold=5000.0,
                business_impact="Revenue generation and market presence",
                owner="trading_team",
                last_updated=time.time(),
            ),
            "order_fill_rate": BusinessKPI(
                name="Order Fill Rate",
                current_value=0.95,
                target_value=0.98,
                trend="improving",
                period="hourly",
                unit="percentage",
                critical_threshold=0.85,
                warning_threshold=0.90,
                business_impact="Trading efficiency and user satisfaction",
                owner="engineering_team",
                last_updated=time.time(),
            ),
            "api_uptime": BusinessKPI(
                name="API Uptime",
                current_value=0.999,
                target_value=0.9995,
                trend="stable",
                period="daily",
                unit="percentage",
                critical_threshold=0.995,
                warning_threshold=0.998,
                business_impact="Service reliability and user trust",
                owner="platform_team",
                last_updated=time.time(),
            ),
            "cost_per_transaction": BusinessKPI(
                name="Cost Per Transaction",
                current_value=0.001,
                target_value=0.0008,
                trend="declining",
                period="daily",
                unit="USD",
                critical_threshold=0.002,
                warning_threshold=0.0015,
                business_impact="Operational efficiency and profitability",
                owner="operations_team",
                last_updated=time.time(),
            ),
            "arbitrage_success_rate": BusinessKPI(
                name="Arbitrage Success Rate",
                current_value=0.75,
                target_value=0.80,
                trend="improving",
                period="hourly",
                unit="percentage",
                critical_threshold=0.60,
                warning_threshold=0.70,
                business_impact="Automated trading profitability",
                owner="algorithmic_trading_team",
                last_updated=time.time(),
            ),
        }

    def _init_anomaly_detectors(self):
        """Initialize anomaly detection algorithms."""

        self.anomaly_detectors = {
            "volume_anomaly": self._detect_volume_anomaly,
            "latency_anomaly": self._detect_latency_anomaly,
            "error_rate_anomaly": self._detect_error_rate_anomaly,
            "cost_anomaly": self._detect_cost_anomaly,
            "user_behavior_anomaly": self._detect_user_behavior_anomaly,
        }

    async def start_production_metrics_collection(self):
        """Start production metrics collection."""
        if self._running:
            return

        self._running = True

        # Start background collection tasks
        self._background_tasks.extend(
            [
                asyncio.create_task(self._collect_business_kpis()),
                asyncio.create_task(self._collect_technical_slas()),
                asyncio.create_task(self._collect_capacity_metrics()),
                asyncio.create_task(self._collect_cost_metrics()),
                asyncio.create_task(self._run_anomaly_detection()),
                asyncio.create_task(self._generate_predictive_insights()),
            ]
        )

        self.logger.info(
            "Production metrics collection started",
            category=LogCategory.METRICS,
            collection_interval=self._collection_interval,
            business_kpis=len(self.business_kpis),
            anomaly_detectors=len(self.anomaly_detectors),
        )

    async def stop_production_metrics_collection(self):
        """Stop production metrics collection."""
        if not self._running:
            return

        self._running = False

        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()

        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()

        self.logger.info("Production metrics collection stopped", category=LogCategory.METRICS)

    async def _collect_business_kpis(self):
        """Collect business KPI metrics."""
        while self._running:
            try:
                for kpi_name, kpi in self.business_kpis.items():
                    # Update KPI current value based on actual metrics
                    current_value = await self._calculate_kpi_value(kpi_name, kpi)
                    kpi.current_value = current_value
                    kpi.last_updated = time.time()

                    # Update trend analysis
                    kpi.trend = await self._calculate_kpi_trend(kpi_name, kpi)

                    # Record metrics
                    self._record_business_kpi_metrics(kpi_name, kpi)

                    # Check for KPI threshold violations
                    await self._check_kpi_thresholds(kpi_name, kpi)

                await asyncio.sleep(300)  # Collect every 5 minutes

            except Exception as e:
                self.logger.error(
                    "Error collecting business KPIs",
                    category=LogCategory.ERROR_HANDLING,
                    exception=e,
                )
                await asyncio.sleep(600)

    async def _collect_technical_slas(self):
        """Collect technical SLA metrics."""
        while self._running:
            try:
                # API Availability SLA
                availability = await self._calculate_api_availability()
                self.api_availability_sla.labels(api_endpoint="all", time_window="24h").set(
                    availability
                )

                # Data freshness
                for data_source in ["order_book", "price_feed", "account_data"]:
                    freshness = await self._calculate_data_freshness(data_source)
                    self.data_freshness_seconds.labels(
                        data_source=data_source, data_type="streaming"
                    ).set(freshness)

                await asyncio.sleep(60)  # Collect every minute

            except Exception as e:
                self.logger.error(
                    "Error collecting technical SLAs",
                    category=LogCategory.ERROR_HANDLING,
                    exception=e,
                )
                await asyncio.sleep(120)

    async def _collect_capacity_metrics(self):
        """Collect capacity planning metrics."""
        while self._running:
            try:
                # Resource saturation
                for resource_type in ["cpu", "memory", "network", "disk"]:
                    saturation = await self._calculate_resource_saturation(resource_type)
                    self.resource_saturation.labels(
                        resource_type=resource_type,
                        instance="main",
                        capacity_tier="production",
                    ).set(saturation)

                # Throughput capacity
                for operation in ["order_placement", "market_data", "settlement"]:
                    capacity = await self._calculate_throughput_capacity(operation)
                    self.throughput_peak_capacity.labels(
                        operation_type=operation, capacity_model="current"
                    ).set(capacity)

                await asyncio.sleep(120)  # Collect every 2 minutes

            except Exception as e:
                self.logger.error(
                    "Error collecting capacity metrics",
                    category=LogCategory.ERROR_HANDLING,
                    exception=e,
                )
                await asyncio.sleep(240)

    async def _collect_cost_metrics(self):
        """Collect cost optimization metrics."""
        while self._running:
            try:
                # Infrastructure cost tracking
                hourly_cost = await self._calculate_infrastructure_cost()
                self.infrastructure_cost_hourly.labels(
                    cost_center="trading",
                    environment="production",
                    resource_type="compute",
                ).set(hourly_cost)

                # Transaction fee efficiency
                fee_efficiency = await self._calculate_fee_efficiency()
                self.transaction_fee_efficiency.labels(
                    fee_strategy="adaptive", network_condition="normal"
                ).set(fee_efficiency)

                await asyncio.sleep(600)  # Collect every 10 minutes

            except Exception as e:
                self.logger.error(
                    "Error collecting cost metrics",
                    category=LogCategory.ERROR_HANDLING,
                    exception=e,
                )
                await asyncio.sleep(1200)

    async def _run_anomaly_detection(self):
        """Run anomaly detection algorithms."""
        while self._running:
            try:
                for detector_name, detector_func in self.anomaly_detectors.items():
                    try:
                        anomaly_score = await detector_func()
                        self.anomaly_scores.labels(
                            detector_type=detector_name, metric_name="composite"
                        ).observe(anomaly_score)

                        # Trigger alerts for high anomaly scores
                        if anomaly_score > 0.9:
                            await self._handle_anomaly_alert(detector_name, anomaly_score)

                    except Exception as e:
                        self.logger.warning(
                            f"Anomaly detector {detector_name} failed",
                            category=LogCategory.PERFORMANCE,
                            exception=e,
                        )

                await asyncio.sleep(180)  # Run every 3 minutes

            except Exception as e:
                self.logger.error(
                    "Error in anomaly detection",
                    category=LogCategory.ERROR_HANDLING,
                    exception=e,
                )
                await asyncio.sleep(360)

    async def _generate_predictive_insights(self):
        """Generate predictive insights and forecasts."""
        while self._running:
            try:
                # Volume prediction
                volume_prediction = await self._predict_trading_volume()
                self.model_prediction_accuracy.labels(
                    model_name="volume_forecast",
                    prediction_type="trading_volume",
                    time_horizon="1h",
                ).set(volume_prediction["accuracy"])

                # Cost prediction
                cost_prediction = await self._predict_operational_costs()
                self.model_prediction_accuracy.labels(
                    model_name="cost_forecast",
                    prediction_type="operational_cost",
                    time_horizon="24h",
                ).set(cost_prediction["accuracy"])

                await asyncio.sleep(900)  # Generate every 15 minutes

            except Exception as e:
                self.logger.error(
                    "Error generating predictive insights",
                    category=LogCategory.ERROR_HANDLING,
                    exception=e,
                )
                await asyncio.sleep(1800)

    async def _calculate_kpi_value(self, kpi_name: str, kpi: BusinessKPI) -> float:
        """Calculate current KPI value from underlying metrics."""
        try:
            if kpi_name == "daily_trading_volume":
                # Calculate from trading volume metrics
                return 5000.0  # Mock value - would calculate from actual metrics

            elif kpi_name == "order_fill_rate":
                # Calculate from order metrics
                return 0.95  # Mock value

            elif kpi_name == "api_uptime":
                # Calculate from uptime metrics
                return await self._calculate_api_availability() / 100

            elif kpi_name == "cost_per_transaction":
                # Calculate from cost and transaction metrics
                return 0.001  # Mock value

            elif kpi_name == "arbitrage_success_rate":
                # Calculate from arbitrage metrics
                return 0.75  # Mock value

            else:
                return kpi.current_value  # Keep existing value if unknown

        except Exception as e:
            self.logger.error(
                f"Error calculating KPI value for {kpi_name}",
                category=LogCategory.ERROR_HANDLING,
                exception=e,
            )
            return kpi.current_value

    async def _calculate_kpi_trend(self, kpi_name: str, kpi: BusinessKPI) -> str:
        """Calculate KPI trend based on historical data."""
        if kpi_name not in self.metric_history:
            return "stable"

        history = list(self.metric_history[kpi_name])
        if len(history) < 5:
            return "stable"

        # Simple trend calculation - would use more sophisticated analysis
        recent_avg = sum(history[-3:]) / 3
        older_avg = sum(history[-6:-3]) / 3

        if recent_avg > older_avg * 1.05:
            return "improving"
        elif recent_avg < older_avg * 0.95:
            return "declining"
        else:
            return "stable"

    def _record_business_kpi_metrics(self, kpi_name: str, kpi: BusinessKPI):
        """Record business KPI metrics to Prometheus."""
        # Store historical data
        self.metric_history[kpi_name].append(kpi.current_value)

        # Record to Prometheus (would create specific metrics for each KPI)
        # For now, log the KPI update
        self.logger.info(
            f"Business KPI updated: {kpi_name}",
            category=LogCategory.METRICS,
            current_value=kpi.current_value,
            target_value=kpi.target_value,
            trend=kpi.trend,
            achievement_percentage=(kpi.current_value / kpi.target_value) * 100,
        )

    async def _check_kpi_thresholds(self, kpi_name: str, kpi: BusinessKPI):
        """Check KPI threshold violations and trigger alerts."""
        if kpi.current_value <= kpi.critical_threshold:
            await self._trigger_kpi_alert(
                kpi_name, kpi, AlertSeverity.P0_CRITICAL, "Critical threshold violated"
            )
        elif kpi.current_value <= kpi.warning_threshold:
            await self._trigger_kpi_alert(
                kpi_name, kpi, AlertSeverity.P2_MEDIUM, "Warning threshold violated"
            )

    async def _trigger_kpi_alert(
        self, kpi_name: str, kpi: BusinessKPI, severity: AlertSeverity, message: str
    ):
        """Trigger KPI threshold alert."""
        alert_context = {
            "kpi_name": kpi_name,
            "current_value": kpi.current_value,
            "target_value": kpi.target_value,
            "threshold_type": severity.value,
            "business_impact": kpi.business_impact,
            "owner": kpi.owner,
            "trend": kpi.trend,
        }

        self.logger.error(
            f"KPI Alert: {kpi_name} - {message}",
            category=LogCategory.PERFORMANCE,
            severity=severity.value,
            **alert_context,
        )

        # Record alert metric
        self.audit_events_total.labels(
            event_category="kpi_threshold",
            severity=severity.value,
            user_type="system",
        ).inc()

    # Calculation methods (mock implementations)
    async def _calculate_api_availability(self) -> float:
        """Calculate API availability percentage."""
        return 99.9  # Mock value

    async def _calculate_data_freshness(self, data_source: str) -> float:
        """Calculate data freshness in seconds."""
        return 5.0  # Mock value

    async def _calculate_resource_saturation(self, resource_type: str) -> float:
        """Calculate resource saturation percentage."""
        if resource_type == "cpu":
            return psutil.cpu_percent()
        elif resource_type == "memory":
            return psutil.virtual_memory().percent
        else:
            return 50.0  # Mock value

    async def _calculate_throughput_capacity(self, operation: str) -> float:
        """Calculate throughput capacity in ops/sec."""
        return 100.0  # Mock value

    async def _calculate_infrastructure_cost(self) -> float:
        """Calculate infrastructure cost per hour."""
        return 5.0  # Mock value - $5/hour

    async def _calculate_fee_efficiency(self) -> float:
        """Calculate transaction fee efficiency percentage."""
        return 85.0  # Mock value

    # Anomaly detection methods
    async def _detect_volume_anomaly(self) -> float:
        """Detect trading volume anomalies."""
        return 0.2  # Mock anomaly score

    async def _detect_latency_anomaly(self) -> float:
        """Detect API latency anomalies."""
        return 0.1  # Mock anomaly score

    async def _detect_error_rate_anomaly(self) -> float:
        """Detect error rate anomalies."""
        return 0.05  # Mock anomaly score

    async def _detect_cost_anomaly(self) -> float:
        """Detect cost anomalies."""
        return 0.15  # Mock anomaly score

    async def _detect_user_behavior_anomaly(self) -> float:
        """Detect user behavior anomalies."""
        return 0.3  # Mock anomaly score

    async def _handle_anomaly_alert(self, detector_name: str, score: float):
        """Handle high anomaly score alert."""
        self.logger.warning(
            f"Anomaly detected: {detector_name}",
            category=LogCategory.PERFORMANCE,
            anomaly_score=score,
            detector=detector_name,
            threshold=0.9,
        )

    # Predictive analytics methods
    async def _predict_trading_volume(self) -> Dict[str, Any]:
        """Predict trading volume for next hour."""
        return {"predicted_volume": 8000.0, "accuracy": 0.85, "confidence": 0.9}

    async def _predict_operational_costs(self) -> Dict[str, Any]:
        """Predict operational costs for next 24 hours."""
        return {"predicted_cost": 120.0, "accuracy": 0.78, "confidence": 0.85}

    @asynccontextmanager
    async def track_business_operation(self, operation_name: str, business_context: Dict[str, Any]):
        """Context manager for tracking business operations."""
        start_time = time.time()
        operation_id = f"{operation_name}_{int(start_time)}"

        try:
            self.logger.info(
                f"Business operation started: {operation_name}",
                category=LogCategory.METRICS,
                operation_id=operation_id,
                **business_context,
            )

            yield operation_id

            # Record successful operation
            duration = time.time() - start_time
            self.logger.info(
                f"Business operation completed: {operation_name}",
                category=LogCategory.METRICS,
                operation_id=operation_id,
                duration=duration,
                status="success",
            )

        except Exception as e:
            # Record failed operation
            duration = time.time() - start_time
            self.logger.error(
                f"Business operation failed: {operation_name}",
                category=LogCategory.ERROR_HANDLING,
                operation_id=operation_id,
                duration=duration,
                status="error",
                exception=e,
            )
            raise

    def get_production_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive production metrics summary."""
        return {
            "timestamp": time.time(),
            "business_kpis": {
                name: {
                    "current_value": kpi.current_value,
                    "target_value": kpi.target_value,
                    "achievement_percentage": (kpi.current_value / kpi.target_value) * 100,
                    "trend": kpi.trend,
                    "status": (
                        "critical"
                        if kpi.current_value <= kpi.critical_threshold
                        else "warning" if kpi.current_value <= kpi.warning_threshold else "healthy"
                    ),
                }
                for name, kpi in self.business_kpis.items()
            },
            "collection_status": {
                "running": self._running,
                "active_tasks": len(self._background_tasks),
                "collection_interval": self._collection_interval,
                "anomaly_detectors": len(self.anomaly_detectors),
            },
            "system_health": {
                "cpu_usage": psutil.cpu_percent(),
                "memory_usage": psutil.virtual_memory().percent,
                "uptime": time.time() - (time.time() - 3600),  # Mock uptime
            },
        }


# Global production metrics instance
_production_metrics_instance: Optional[StellarProductionMetricsFramework] = None


def get_stellar_production_metrics() -> StellarProductionMetricsFramework:
    """Get or create global production metrics instance."""
    global _production_metrics_instance
    if not _production_metrics_instance:
        _production_metrics_instance = StellarProductionMetricsFramework()
    return _production_metrics_instance


async def start_production_metrics(collection_interval: int = 30):
    """Start production metrics collection."""
    metrics = get_stellar_production_metrics()
    metrics._collection_interval = collection_interval
    await metrics.start_production_metrics_collection()
    return metrics


async def stop_production_metrics():
    """Stop production metrics collection."""
    global _production_metrics_instance
    if _production_metrics_instance:
        await _production_metrics_instance.stop_production_metrics_collection()
        _production_metrics_instance = None
