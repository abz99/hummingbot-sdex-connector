# Stellar Hummingbot Connector - Production Observability

This directory contains the complete production observability stack for the Stellar Hummingbot Connector, implementing **Phase 4: Production Hardening** requirements.

## 🎯 Overview

The production observability framework provides comprehensive monitoring, alerting, and visibility into the Stellar connector's performance, health, and business metrics.

### Key Components

- **Prometheus** - Metrics collection and storage
- **Grafana** - Visualization and dashboards  
- **Alertmanager** - Alert routing and notifications
- **Loki** - Log aggregation and analysis
- **Jaeger** - Distributed tracing
- **Node Exporter** - System metrics
- **cAdvisor** - Container metrics

## 🚀 Quick Start

### 1. Start Observability Stack

```bash
# Start all observability services
cd observability/
docker-compose -f docker-compose.observability.yml up -d

# Verify services are running
docker-compose -f docker-compose.observability.yml ps
```

### 2. Access Dashboards

- **Grafana**: http://localhost:3000 (admin/stellar-admin-2024)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093
- **Jaeger**: http://localhost:16686

### 3. Import Grafana Dashboard

1. Open Grafana (http://localhost:3000)
2. Go to Dashboards → Import
3. Upload `grafana/dashboards/stellar-connector-dashboard.json`
4. Configure Prometheus data source: http://prometheus:9090

## 📊 Monitoring Architecture

### Metrics Collection

The observability framework collects 50+ production metrics across multiple categories:

#### Network Metrics
- Request rates and latencies
- Error rates by endpoint
- Active connections
- Circuit breaker states

#### Trading Metrics  
- Order placement and fill rates
- Trading volume and spreads
- Account balances
- Arbitrage opportunities

#### System Metrics
- CPU, memory, disk utilization
- Health check status
- Cache performance
- Concurrent operations

#### Business Metrics
- Profit/loss tracking
- Trading session duration
- Market opportunity detection

### Alert Rules

**Critical Alerts** (immediate notification):
- System down
- High error rates (>10%)
- Circuit breaker open
- Health check failures
- Security events

**Warning Alerts** (standard notification):
- High latency (>5s)
- Low account balance
- Resource exhaustion (>80%)
- Low cache hit rates

**Info Alerts** (daily digest):
- Trading volume spikes
- New trading pairs
- Performance insights

### Health Checks

Automated health monitoring for:
- **System Resources** - CPU, memory, disk usage
- **Stellar Network** - Network connectivity
- **Database** - Connection health
- **Metrics System** - Observability stack health

## 🔧 Configuration

### Prometheus Configuration

Located in `prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'stellar-connector'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 5s
```

### Alert Rules

Located in `prometheus/stellar_alerts.yml`:

```yaml
groups:
  - name: stellar_connector_critical
    rules:
      - alert: StellarConnectorDown
        expr: up{job="stellar-connector"} == 0
        for: 1m
```

### Notification Channels

Configure in `alerting/alertmanager.yml`:

- **Email** - ops-team@stellar-hummingbot.com
- **Slack** - #ops-critical, #ops-warnings
- **PagerDuty** - Critical alerts only

## 📈 Dashboard Features

The Grafana dashboard provides:

### System Overview
- System uptime and health status
- Resource utilization trends
- Active connections

### Performance Monitoring  
- API response times (P50, P95)
- Request rates and error rates
- Circuit breaker status

### Trading Analytics
- Order placement rates
- Trading volume by pair
- Account balance monitoring
- Spread analysis

### Operational Insights
- Alert firing rates
- Cache performance
- Background task status

## 🔍 Usage Examples

### Starting the Observability System

```python
from hummingbot.connector.exchange.stellar.stellar_observability import (
    start_production_observability
)

# Start with custom configuration
observability = await start_production_observability(
    metrics_port=8000,
    pushgateway_url="http://localhost:9091",
    alert_webhook_url="http://localhost:5000/webhook"
)
```

### Custom Metrics

```python
from hummingbot.connector.exchange.stellar.stellar_metrics import (
    get_stellar_metrics,
    MetricDefinition,
    MetricType
)

metrics = get_stellar_metrics()

# Create custom metric
custom_metric = metrics.create_custom_metric(
    MetricDefinition(
        name="my_custom_metric",
        description="Custom business metric",
        metric_type=MetricType.COUNTER,
        labels=["trading_pair", "strategy"]
    )
)

# Record metric
custom_metric.labels(trading_pair="XLM_USDC", strategy="market_making").inc()
```

### Operation Monitoring

```python
from hummingbot.connector.exchange.stellar.stellar_observability import (
    get_stellar_observability
)

observability = get_stellar_observability()

# Monitor operation performance
async with observability.observe_operation("place_order"):
    result = await place_order(...)
    # Automatically records duration and success/failure
```

### Custom Health Checks

```python
def check_custom_component() -> HealthCheckResult:
    try:
        # Perform health check logic
        response_time = check_component_health()
        
        return HealthCheckResult(
            component="custom_component",
            status=HealthCheckStatus.HEALTHY,
            response_time=response_time,
            message="Component is operational"
        )
    except Exception as e:
        return HealthCheckResult(
            component="custom_component", 
            status=HealthCheckStatus.UNHEALTHY,
            response_time=0.0,
            message=f"Component error: {e}"
        )

# Register health check
observability.add_health_check("custom_component", check_custom_component)
```

### Custom Alert Rules

```python
from hummingbot.connector.exchange.stellar.stellar_observability import (
    AlertRule,
    AlertLevel
)

# Create custom alert rule
custom_alert = AlertRule(
    name="custom_business_alert",
    description="Custom business condition exceeded",
    metric_name="my_custom_metric",
    threshold=1000.0,
    comparison="gt",
    duration=300,  # 5 minutes
    level=AlertLevel.WARNING
)

# Add to observability system
observability.add_alert_rule(custom_alert)
```

## 🔧 Troubleshooting

### Common Issues

1. **Metrics not appearing in Grafana**
   - Verify Prometheus is scraping: http://localhost:9090/targets
   - Check connector metrics endpoint: http://localhost:8000/metrics
   - Verify Grafana data source configuration

2. **Alerts not firing**
   - Check alert rule syntax in Prometheus: http://localhost:9090/alerts
   - Verify Alertmanager configuration: http://localhost:9093
   - Check notification channel credentials

3. **High resource usage**
   - Adjust metrics retention in `prometheus.yml`
   - Reduce scrape intervals for non-critical metrics
   - Configure log rotation for container logs

### Log Locations

- **Prometheus**: `/var/log/prometheus/`
- **Grafana**: `/var/log/grafana/`
- **Alertmanager**: `/var/log/alertmanager/`
- **Container logs**: `docker logs <container_name>`

### Performance Tuning

```yaml
# prometheus.yml - Optimize for high-load environments
global:
  scrape_interval: 30s     # Reduce frequency
  evaluation_interval: 30s

storage:
  tsdb:
    retention.time: 7d     # Reduce retention
    retention.size: 5GB
```

## 📚 Integration with Connector

### Automatic Metrics Collection

The observability framework automatically integrates with:

- **Network Layer** - API request metrics
- **Trading Engine** - Order and execution metrics  
- **Security Manager** - Security event tracking
- **Health Monitor** - Component health metrics
- **Performance Optimizer** - Resource utilization

### Structured Logging

All logs include correlation IDs for request tracing:

```python
from hummingbot.connector.exchange.stellar.stellar_logging import (
    correlation_id,
    get_stellar_logger
)

logger = get_stellar_logger()

# Set correlation ID for request tracing
correlation_id.set("req_12345")

# Log with automatic correlation ID inclusion
logger.info("Order placed", 
           category=LogCategory.TRADING,
           order_id=order.id,
           amount=order.amount)
```

## 🔒 Security Considerations

- **Metric Data** - Contains no sensitive information
- **Alert Channels** - Use encrypted communication
- **Dashboard Access** - Implement authentication 
- **Log Data** - Exclude secrets and keys
- **Network Security** - Use VPN for production access

## 📋 Maintenance

### Regular Tasks

- **Weekly**: Review alert rules and thresholds
- **Monthly**: Analyze dashboard usage and optimize
- **Quarterly**: Update observability stack versions
- **Yearly**: Review retention policies and storage

### Backup and Recovery

```bash
# Backup Grafana dashboards
docker exec stellar-grafana grafana-cli admin export-dashboard

# Backup Prometheus data
docker run --rm -v prometheus_data:/data ubuntu tar czf /backup/prometheus.tar.gz /data

# Backup Alertmanager configuration
cp alerting/alertmanager.yml /backup/
```

## 🎯 Production Readiness

This observability framework implements enterprise-grade monitoring with:

✅ **Comprehensive Metrics** - 50+ production metrics  
✅ **Real-time Alerting** - Multi-channel notifications  
✅ **Visual Dashboards** - Executive and operational views  
✅ **Health Monitoring** - Automated health checks  
✅ **Performance Tracking** - SLA monitoring and reporting  
✅ **Security Monitoring** - Security event tracking  
✅ **Scalable Architecture** - Container-based deployment  
✅ **High Availability** - Redundant and resilient design  

The system is ready for production deployment and provides complete visibility into the Stellar Hummingbot Connector's operations.