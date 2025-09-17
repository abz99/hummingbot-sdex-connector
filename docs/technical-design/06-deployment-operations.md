# Stellar SDEX Connector: Production Deployment & Operations

> **Part 6 of 7** - Technical Design Document v3.0
> Split from: `stellar_sdex_tdd_v3.md` (Lines 1822-2473)

## Production Deployment & Operations

### 6.1 Container Orchestration

**Modern Deployment Configuration**:

```python
# Dockerfile - Production optimized
FROM python:3.11-slim as builder

# Security hardening
RUN apt-get update && apt-get install -y \
    gcc g++ make \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r stellar && useradd -r -g stellar stellar

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Security: Switch to non-root user
USER stellar

# Production runtime
FROM python:3.11-slim as production

RUN groupadd -r stellar && useradd -r -g stellar stellar
WORKDIR /app

# Copy only necessary files from builder
COPY --from=builder --chown=stellar:stellar /app /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

USER stellar

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import asyncio; from stellar_health_check import health_check; asyncio.run(health_check())" || exit 1

EXPOSE 8080
CMD ["python", "-m", "stellar_connector", "--config", "/app/config/production.yml"]
```

**Kubernetes Deployment Configuration**:

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stellar-connector
  namespace: hummingbot
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
  selector:
    matchLabels:
      app: stellar-connector
  template:
    metadata:
      labels:
        app: stellar-connector
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: stellar-connector
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
      containers:
      - name: stellar-connector
        image: stellar-connector:v3.0.0
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 9090
          name: metrics
        env:
        - name: STELLAR_NETWORK
          value: "mainnet"
        - name: LOG_LEVEL
          value: "INFO"
        - name: METRICS_ENABLED
          value: "true"
        envFrom:
        - secretRef:
            name: stellar-secrets
        - configMapRef:
            name: stellar-config
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        volumeMounts:
        - name: config
          mountPath: /app/config
          readOnly: true
        - name: keys
          mountPath: /app/keys
          readOnly: true
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: config
        configMap:
          name: stellar-config
      - name: keys
        secret:
          secretName: stellar-keys
          defaultMode: 0400
      - name: logs
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: stellar-connector-service
  namespace: hummingbot
  labels:
    app: stellar-connector
spec:
  selector:
    app: stellar-connector
  ports:
  - port: 80
    targetPort: 8080
    name: http
  - port: 9090
    targetPort: 9090
    name: metrics
  type: ClusterIP
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: stellar-connector
  namespace: hummingbot
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: stellar-connector
  namespace: hummingbot
spec:
  selector:
    matchLabels:
      app: stellar-connector
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
```

### 6.2 Production Configuration Management

**Advanced Configuration Framework**:

```python
import os
import yaml
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path

@dataclass
class ProductionConfig:
    """Production-grade configuration management"""

    # Network configuration
    stellar_network: str = "mainnet"
    horizon_urls: List[str] = None
    soroban_rpc_urls: List[str] = None
    fallback_urls: List[str] = None

    # Security configuration
    security_level: str = "high"  # low, medium, high, maximum
    hsm_provider: str = "aws"     # aws, azure, thales, local
    use_mpc: bool = False
    use_hardware_wallet: bool = False
    key_rotation_interval: int = 86400  # 24 hours

    # Performance configuration
    max_concurrent_requests: int = 50
    request_timeout: int = 30
    connection_pool_size: int = 100
    cache_ttl_seconds: int = 300
    batch_size: int = 10

    # Monitoring configuration
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    log_level: str = "INFO"
    prometheus_port: int = 9090
    health_check_port: int = 8080

    # Trading configuration
    max_active_orders: int = 100
    order_timeout_seconds: int = 300
    min_order_size: float = 1.0
    max_order_size: float = 1000000.0

    # Risk management
    max_daily_volume: float = 10000000.0
    position_limits: Dict[str, float] = None
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60

    def __post_init__(self):
        if self.horizon_urls is None:
            self.horizon_urls = self._get_default_horizon_urls()
        if self.soroban_rpc_urls is None:
            self.soroban_rpc_urls = self._get_default_soroban_urls()
        if self.position_limits is None:
            self.position_limits = {}

    def _get_default_horizon_urls(self) -> List[str]:
        """Get default Horizon URLs based on network"""
        if self.stellar_network == "mainnet":
            return [
                "https://horizon.stellar.org",
                "https://stellar-horizon.satoshipay.io",
                "https://horizon.stellar.lobstr.co"
            ]
        else:
            return ["https://horizon-testnet.stellar.org"]

    def _get_default_soroban_urls(self) -> List[str]:
        """Get default Soroban RPC URLs"""
        if self.stellar_network == "mainnet":
            return [
                "https://soroban-rpc.mainnet.stellar.gateway.fm",
                "https://rpc-mainnet.stellar.org"
            ]
        else:
            return ["https://soroban-testnet.stellar.org"]

    @classmethod
    def from_environment(cls) -> 'ProductionConfig':
        """Create configuration from environment variables"""

        config = cls()

        # Network settings
        config.stellar_network = os.getenv('STELLAR_NETWORK', config.stellar_network)

        # Security settings
        config.security_level = os.getenv('SECURITY_LEVEL', config.security_level)
        config.hsm_provider = os.getenv('HSM_PROVIDER', config.hsm_provider)
        config.use_mpc = os.getenv('USE_MPC', 'false').lower() == 'true'

        # Performance settings
        config.max_concurrent_requests = int(os.getenv('MAX_CONCURRENT_REQUESTS', str(config.max_concurrent_requests)))
        config.connection_pool_size = int(os.getenv('CONNECTION_POOL_SIZE', str(config.connection_pool_size)))

        # Monitoring settings
        config.metrics_enabled = os.getenv('METRICS_ENABLED', 'true').lower() == 'true'
        config.log_level = os.getenv('LOG_LEVEL', config.log_level)

        return config

    @classmethod
    def from_file(cls, config_path: str) -> 'ProductionConfig':
        """Load configuration from YAML file"""

        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)

        return cls(**config_data)

    def validate(self) -> bool:
        """Validate configuration for production deployment"""

        errors = []

        # Security validation
        if self.stellar_network == "mainnet" and self.security_level == "low":
            errors.append("Production deployment requires security_level >= 'medium'")

        # Network validation
        if not self.horizon_urls:
            errors.append("At least one Horizon URL must be configured")

        # Performance validation
        if self.max_concurrent_requests > 1000:
            errors.append("max_concurrent_requests should not exceed 1000 for stability")

        # Risk management validation
        if self.stellar_network == "mainnet" and not self.position_limits:
            errors.append("Position limits should be configured for mainnet")

        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")

        return True

class ConfigurationManager:
    """Advanced configuration management with hot reloading"""

    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._watchers = []
        self._last_modified = self.config_path.stat().st_mtime

    def _load_config(self) -> ProductionConfig:
        """Load configuration with environment override"""

        if self.config_path.exists():
            config = ProductionConfig.from_file(str(self.config_path))
        else:
            config = ProductionConfig.from_environment()

        config.validate()
        return config

    async def watch_for_changes(self, callback):
        """Watch configuration file for changes"""

        self._watchers.append(callback)

        while True:
            try:
                current_mtime = self.config_path.stat().st_mtime
                if current_mtime > self._last_modified:
                    # Configuration file changed
                    old_config = self.config
                    new_config = self._load_config()

                    # Notify watchers
                    for watcher in self._watchers:
                        await watcher(old_config, new_config)

                    self.config = new_config
                    self._last_modified = current_mtime

                await asyncio.sleep(5)  # Check every 5 seconds

            except Exception as e:
                logger.error(f"Error watching configuration: {e}")
                await asyncio.sleep(30)  # Back off on error
```

### 6.3 Advanced Monitoring & Alerting

**Production Monitoring Dashboard**:

```python
# monitoring/stellar_dashboard.py
from prometheus_client import CollectorRegistry, generate_latest
from prometheus_client.exposition import MetricsHandler
import asyncio
from aiohttp import web
import json

class StellarMonitoringDashboard:
    """Advanced monitoring dashboard for Stellar connector"""

    def __init__(self, connector, config):
        self.connector = connector
        self.config = config
        self.registry = CollectorRegistry()
        self.app = web.Application()
        self.setup_routes()

    def setup_routes(self):
        """Setup monitoring endpoints"""

        # Prometheus metrics
        self.app.router.add_get('/metrics', self.metrics_handler)

        # Health checks
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/ready', self.readiness_check)

        # Debug endpoints
        self.app.router.add_get('/debug/orders', self.debug_orders)
        self.app.router.add_get('/debug/connections', self.debug_connections)
        self.app.router.add_get('/debug/performance', self.debug_performance)

        # Configuration endpoints
        self.app.router.add_get('/config', self.get_config)

    async def metrics_handler(self, request):
        """Prometheus metrics endpoint"""

        metrics_data = generate_latest(self.registry)
        return web.Response(
            text=metrics_data.decode('utf-8'),
            content_type='text/plain; charset=utf-8'
        )

    async def health_check(self, request):
        """Comprehensive health check"""

        health_results = await self.connector.health_checker.run_all_health_checks()

        overall_status = "healthy"
        if any(result["status"] != "healthy" for result in health_results.values()):
            overall_status = "unhealthy"

        response_data = {
            "status": overall_status,
            "timestamp": time.time(),
            "version": "3.0.0",
            "checks": health_results
        }

        status_code = 200 if overall_status == "healthy" else 503

        return web.json_response(response_data, status=status_code)

    async def readiness_check(self, request):
        """Readiness check for Kubernetes"""

        ready = (
            self.connector.ready and
            self.connector._chain_interface.is_connected and
            len(self.connector.active_orders) < self.config.max_active_orders
        )

        response_data = {
            "ready": ready,
            "timestamp": time.time(),
            "active_orders": len(self.connector.active_orders),
            "max_orders": self.config.max_active_orders
        }

        status_code = 200 if ready else 503

        return web.json_response(response_data, status=status_code)

    async def debug_orders(self, request):
        """Debug endpoint for order information"""

        active_orders = self.connector.order_manager.get_active_orders()

        order_summary = []
        for order in active_orders:
            order_summary.append({
                "order_id": order.order_id,
                "trading_pair": order.trading_pair,
                "status": order.status.value,
                "amount": str(order.amount),
                "filled_amount": str(order.filled_amount),
                "created": order.created_timestamp,
                "age_seconds": time.time() - order.created_timestamp
            })

        return web.json_response({
            "active_orders_count": len(active_orders),
            "orders": order_summary
        })

    async def debug_connections(self, request):
        """Debug endpoint for connection information"""

        connection_info = {
            "stellar_connection": self.connector._chain_interface.is_connected,
            "horizon_servers": self.config.horizon_urls,
            "soroban_servers": self.config.soroban_rpc_urls,
            "active_connections": getattr(self.connector._connection_manager, 'active_connections', 0),
            "connection_pool_size": self.config.connection_pool_size
        }

        return web.json_response(connection_info)

    async def debug_performance(self, request):
        """Debug endpoint for performance metrics"""

        performance_data = {
            "api_metrics": self.connector.metrics_collector.get_metrics_summary(),
            "cache_stats": getattr(self.connector._cache_manager, 'get_stats', lambda: {})(),
            "circuit_breaker_states": {
                "order_submission": self.connector.order_manager.order_submission_cb.state.value,
                "order_cancellation": self.connector.order_manager.order_cancellation_cb.state.value
            }
        }

        return web.json_response(performance_data)

    async def get_config(self, request):
        """Get current configuration (sanitized)"""

        # Sanitize sensitive information
        config_dict = {
            "stellar_network": self.config.stellar_network,
            "security_level": self.config.security_level,
            "max_concurrent_requests": self.config.max_concurrent_requests,
            "metrics_enabled": self.config.metrics_enabled,
            "log_level": self.config.log_level
        }

        return web.json_response(config_dict)

    async def start_server(self):
        """Start monitoring server"""

        runner = web.AppRunner(self.app)
        await runner.setup()

        site = web.TCPSite(
            runner,
            '0.0.0.0',
            self.config.health_check_port
        )

        await site.start()

        print(f"Monitoring server started on port {self.config.health_check_port}")
```

**Grafana Dashboard Configuration**:

```json
{
  "dashboard": {
    "title": "Stellar SDEX Connector - Production Monitoring",
    "tags": ["stellar", "hummingbot", "trading"],
    "timezone": "utc",
    "panels": [
      {
        "title": "Order Volume",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(stellar_orders_placed_total[5m]) * 300",
            "legendFormat": "Orders/5min"
          }
        ]
      },
      {
        "title": "API Latency",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, stellar_api_latency_seconds)",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, stellar_api_latency_seconds)",
            "legendFormat": "50th percentile"
          }
        ]
      },
      {
        "title": "Active Orders",
        "type": "singlestat",
        "targets": [
          {
            "expr": "stellar_active_offers",
            "legendFormat": "Active Offers"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(stellar_network_errors_total[5m])",
            "legendFormat": "Errors/sec"
          }
        ]
      },
      {
        "title": "Transaction Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "stellar_transaction_success_rate",
            "legendFormat": "Success Rate"
          }
        ]
      },
      {
        "title": "Account Balances",
        "type": "table",
        "targets": [
          {
            "expr": "stellar_account_balance",
            "legendFormat": "{{asset}}"
          }
        ]
      },
      {
        "title": "Cache Hit Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "stellar_cache_hit_rate",
            "legendFormat": "{{cache_type}}"
          }
        ]
      },
      {
        "title": "System Health",
        "type": "table",
        "targets": [
          {
            "expr": "up{job=\"stellar-connector\"}",
            "legendFormat": "Service Status"
          }
        ]
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
```

---

## Related Documents

This document is part of the Stellar SDEX Connector Technical Design v3.0 series:

1. [01-architecture-foundation.md](./01-architecture-foundation.md) - Architecture & Technical Foundation
2. [02-security-framework.md](./02-security-framework.md) - Security Framework
3. [03-monitoring-observability.md](./03-monitoring-observability.md) - Monitoring & Observability
4. [04-order-management.md](./04-order-management.md) - Order Management & Trading Logic
5. [05-asset-management.md](./05-asset-management.md) - Asset Management & Risk
6. **[06-deployment-operations.md](./06-deployment-operations.md)** - Production Deployment & Operations ⭐ *You are here*
7. [07-implementation-guide.md](./07-implementation-guide.md) - Implementation Guide & Checklists

**Deployment-Specific References:**
- Kubernetes manifests and configurations
- Container security and optimization
- Production monitoring dashboards
- Configuration management patterns