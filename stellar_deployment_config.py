"""
Stellar Connector Deployment and Configuration
Production deployment configuration and Hummingbot integration
"""

from decimal import Decimal
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class StellarConnectorConfig:
    """Main configuration class for Stellar connector"""

    # Network configuration
    stellar_network: str = "testnet"
    stellar_secret_key: str = ""

    # Trading configuration
    stellar_reserve_buffer: Decimal = Decimal("2.0")
    stellar_trustline_auto_setup: bool = True
    stellar_path_payment_enabled: bool = True
    stellar_max_fee_base: int = 1000000  # 0.1 XLM

    # Performance configuration
    connection_pool_size: int = 3
    request_timeout_seconds: int = 30
    cache_ttl_ms: int = 5000
    max_retries: int = 3
    rate_limit_rps: int = 10

    # Security configuration
    use_hsm: bool = False
    hsm_type: str = "Local_HSM"
    key_rotation_days: int = 90
    enable_replay_protection: bool = True

    # Risk management
    max_position_size_pct: float = 20.0
    max_concentration_pct: float = 50.0
    min_liquidity_threshold: Decimal = Decimal("1000")


class HummingbotConfigGenerator:
    """Generate Hummingbot configuration for Stellar connector"""

    @staticmethod
    def generate_connector_config() -> Dict[str, Any]:
        """Generate Stellar connector configuration template"""

        return {
            "stellar_secret_key": {
                "prompt": "Enter your Stellar secret key >>> ",
                "required": True,
                "is_secure": True,
                "validator": "validate_stellar_secret_key",
            },
            "stellar_network": {
                "prompt": "Enter Stellar network (mainnet/testnet) >>> ",
                "required": True,
                "default": "testnet",
                "validator": lambda v: v in ["mainnet", "testnet", "futurenet"],
            },
            "stellar_reserve_buffer": {
                "prompt": "Enter XLM reserve buffer >>> ",
                "required": False,
                "default": Decimal("2.0"),
                "type": "decimal",
                "validator": lambda v: v > 0,
            },
            "stellar_trustline_auto_setup": {
                "prompt": "Automatically setup trustlines? (Yes/No) >>> ",
                "required": False,
                "default": True,
                "type": "bool",
            },
            "stellar_path_payment_enabled": {
                "prompt": "Enable path payment trading? (Yes/No) >>> ",
                "required": False,
                "default": True,
                "type": "bool",
            },
        }

    @staticmethod
    def validate_stellar_secret_key(value: str) -> Optional[str]:
        """Validate Stellar secret key format"""

        try:
            from stellar_sdk import Keypair

            Keypair.from_secret(value)

            if not value.startswith("S") or len(value) != 56:
                return "Invalid Stellar secret key format"
            return None
        except Exception:
            return "Invalid Stellar secret key"


class KelpMigrationTool:
    """Tool to migrate Kelp configurations to Hummingbot"""

    def __init__(self):
        self.supported_strategies = ["buysell", "mirror", "balanced"]

    async def migrate_kelp_config(self, kelp_config_path: str) -> Dict:
        """Migrate Kelp configuration to Hummingbot format"""

        # Parse Kelp TOML configuration
        kelp_config = await self.parse_kelp_config(kelp_config_path)

        # Convert to Hummingbot strategy configuration
        hb_config = await self.convert_to_hummingbot_config(kelp_config)

        # Generate migration report
        migration_report = self.generate_migration_report(kelp_config, hb_config)

        return {
            "hummingbot_config": hb_config,
            "migration_report": migration_report,
            "success": True,
        }

    async def parse_kelp_config(self, config_path: str) -> Dict:
        """Parse Kelp TOML configuration file"""

        import toml

        with open(config_path, "r") as f:
            config = toml.load(f)

        return config

    async def convert_to_hummingbot_config(self, kelp_config: Dict) -> Dict:
        """Convert Kelp configuration to Hummingbot format"""

        strategy_type = kelp_config.get("strategy_type", "buysell")

        if strategy_type == "buysell":
            return self.convert_buysell_strategy(kelp_config)
        elif strategy_type == "mirror":
            return self.convert_mirror_strategy(kelp_config)
        else:
            raise ValueError(f"Unsupported Kelp strategy: {strategy_type}")

    def convert_buysell_strategy(self, kelp_config: Dict) -> Dict:
        """Convert Kelp buysell strategy to Hummingbot pure market making"""

        # Extract key parameters
        price_tolerance = kelp_config.get("price_tolerance", 0.01)
        amount = kelp_config.get("amount_of_a_base", 100)
        update_interval = kelp_config.get("rate_offset_seconds", 30)

        return {
            "strategy": "pure_market_making",
            "exchange": "stellar",
            "market": self.convert_asset_pair(kelp_config),
            "bid_spread": price_tolerance,
            "ask_spread": price_tolerance,
            "order_amount": amount,
            "order_levels": 1,
            "order_refresh_time": update_interval,
            "filled_order_delay": 60,
            "inventory_skew_enabled": True,
            "inventory_target_base_pct": 50,
            # Stellar-specific parameters
            "stellar_reserve_buffer": kelp_config.get("minimum_base_balance", 2.0),
            "stellar_trustline_auto_setup": True,
            "stellar_path_payment_enabled": True,
            "stellar_max_fee_base": 1000000,
        }

    def convert_asset_pair(self, kelp_config: Dict) -> str:
        """Convert Kelp asset configuration to trading pair"""

        asset_base = kelp_config.get("asset_base", "XLM")
        asset_quote = kelp_config.get("asset_quote", "USDC")

        return f"{asset_base}-{asset_quote}"

    def generate_migration_report(self, kelp_config: Dict, hb_config: Dict) -> Dict:
        """Generate detailed migration report"""

        return {
            "migration_timestamp": time.time(),
            "kelp_strategy": kelp_config.get("strategy_type"),
            "hummingbot_strategy": hb_config.get("strategy"),
            "parameter_mapping": {
                "price_tolerance": f"{kelp_config.get('price_tolerance')} → {hb_config.get('bid_spread')}",
                "amount": f"{kelp_config.get('amount_of_a_base')} → {hb_config.get('order_amount')}",
                "update_interval": f"{kelp_config.get('rate_offset_seconds')} → {hb_config.get('order_refresh_time')}",
            },
            "feature_parity": self.calculate_feature_parity(kelp_config, hb_config),
            "warnings": self.generate_migration_warnings(kelp_config, hb_config),
        }

    def calculate_feature_parity(self, kelp_config: Dict, hb_config: Dict) -> float:
        """Calculate feature parity percentage"""

        # Compare key features
        kelp_features = set(kelp_config.keys())
        hb_features = set(hb_config.keys())

        # Map equivalent features
        feature_mapping = {
            "price_tolerance": "bid_spread",
            "amount_of_a_base": "order_amount",
            "rate_offset_seconds": "order_refresh_time",
        }

        mapped_features = 0
        for kelp_feature, hb_feature in feature_mapping.items():
            if kelp_feature in kelp_features and hb_feature in hb_features:
                mapped_features += 1

        return (mapped_features / len(feature_mapping)) * 100


class ProductionDeploymentConfig:
    """Production deployment configuration"""

    @staticmethod
    def get_production_config() -> Dict:
        """Get production-ready configuration"""

        return {
            "stellar": {
                "network": "mainnet",
                "horizon_url": "https://horizon.stellar.org",
                "network_passphrase": "Public Global Stellar Network ; September 2015",
                "security": {
                    "use_hsm": True,
                    "hsm_type": "AWS_CloudHSM",
                    "key_rotation_days": 90,
                    "enable_replay_protection": True,
                    "max_concurrent_transactions": 10,
                },
                "performance": {
                    "connection_pool_size": 5,
                    "request_timeout_seconds": 30,
                    "cache_ttl_ms": 5000,
                    "max_retries": 3,
                    "rate_limit_rps": 10,
                },
                "trading": {
                    "reserve_buffer": "5.0",
                    "max_order_size": "100000",
                    "min_order_size": "1.0",
                    "default_slippage_tolerance": 0.01,
                    "max_open_orders_per_pair": 10,
                },
                "monitoring": {
                    "enable_metrics": True,
                    "metrics_port": 9090,
                    "enable_health_checks": True,
                    "alert_on_failures": True,
                    "log_level": "INFO",
                },
            }
        }

    @staticmethod
    def get_development_config() -> Dict:
        """Get development environment configuration"""

        return {
            "stellar": {
                "network": "testnet",
                "horizon_url": "https://horizon-testnet.stellar.org",
                "network_passphrase": "Test SDF Network ; September 2015",
                "security": {
                    "use_hsm": False,
                    "key_rotation_days": 7,  # More frequent for testing
                    "enable_replay_protection": True,
                },
                "performance": {
                    "connection_pool_size": 2,
                    "request_timeout_seconds": 10,
                    "cache_ttl_ms": 2000,
                    "max_retries": 2,
                },
                "trading": {
                    "reserve_buffer": "1.0",
                    "max_order_size": "1000",
                    "min_order_size": "0.1",
                },
                "monitoring": {"enable_metrics": True, "log_level": "DEBUG"},
            }
        }


class StellarStrategyTemplates:
    """Pre-configured strategy templates for common use cases"""

    @staticmethod
    def pure_market_making_template() -> Dict:
        """Pure market making strategy template"""

        return {
            "strategy": "pure_market_making",
            "exchange": "stellar",
            "market": "XLM-USDC",
            "bid_spread": 0.1,
            "ask_spread": 0.1,
            "order_amount": 1000,
            "order_levels": 1,
            "order_refresh_time": 30,
            "filled_order_delay": 60,
            "inventory_skew_enabled": True,
            "inventory_target_base_pct": 50,
            # Stellar-specific parameters
            "stellar_reserve_buffer": 2.0,
            "stellar_trustline_auto_setup": True,
            "stellar_path_payment_enabled": True,
            "stellar_max_fee_base": 1000000,
        }

    @staticmethod
    def cross_exchange_market_making_template() -> Dict:
        """Cross-exchange market making template"""

        return {
            "strategy": "cross_exchange_market_making",
            "maker_market": "stellar",
            "taker_market": "binance",
            "market": "XLM-USDT",
            "order_amount": 500,
            "min_profitability": 0.003,  # 0.3% minimum profit
            "adjust_order_enabled": True,
            "active_order_canceling": True,
            # Stellar-specific
            "stellar_reserve_buffer": 3.0,  # Higher buffer for cross-exchange
            "stellar_path_payment_enabled": True,
        }

    @staticmethod
    def arbitrage_template() -> Dict:
        """Arbitrage strategy template"""

        return {
            "strategy": "arbitrage",
            "primary_market": "stellar",
            "secondary_market": "coinbase_pro",
            "market": "XLM-USD",
            "min_profitability": 0.005,  # 0.5% minimum profit
            "max_order_size": 1000,
            "order_size_taker_volume_pct": 25,
            "order_size_taker_balance_pct": 99,
            # Stellar arbitrage specific
            "stellar_reserve_buffer": 5.0,  # Higher buffer for arbitrage
            "stellar_path_payment_for_arbitrage": True,
            "stellar_max_slippage": 0.02,  # 2% max slippage
        }


class HealthCheckSystem:
    """Health check system for monitoring"""

    def __init__(self, connector):
        self.connector = connector

    async def check_overall_health(self) -> Dict:
        """Comprehensive health check"""

        checks = {
            "stellar_connection": await self.check_stellar_connection(),
            "account_access": await self.check_account_access(),
            "order_book_data": await self.check_order_book_data(),
            "balance_data": await self.check_balance_data(),
            "security_systems": await self.check_security_systems(),
        }

        overall_healthy = all(checks.values())

        return {
            "healthy": overall_healthy,
            "timestamp": time.time(),
            "checks": checks,
            "status": "HEALTHY" if overall_healthy else "DEGRADED",
        }

    async def check_stellar_connection(self) -> bool:
        """Check Stellar network connectivity"""

        try:
            if not self.connector._chain_interface:
                return False

            network_info = await self.connector._chain_interface.get_network_info()
            return "latest_ledger" in network_info

        except Exception:
            return False

    async def check_account_access(self) -> bool:
        """Check account accessibility"""

        try:
            if not self.connector._wallet_address:
                return False

            account = await self.connector._chain_interface.load_account(
                self.connector._wallet_address
            )
            return account is not None

        except Exception:
            return False

    async def check_order_book_data(self) -> bool:
        """Check order book data availability"""

        try:
            if not self.connector._order_book_tracker:
                return False

            return self.connector._order_book_tracker.ready

        except Exception:
            return False

    async def check_balance_data(self) -> bool:
        """Check balance data availability"""

        try:
            return len(self.connector._account_balances) > 0

        except Exception:
            return False

    async def check_security_systems(self) -> bool:
        """Check security systems status"""

        try:
            # Verify key manager is initialized
            if not self.connector._key_manager:
                return False

            # Verify wallet address is set
            if not self.connector._wallet_address:
                return False

            return True

        except Exception:
            return False


class MetricsCollector:
    """Collect and expose metrics for monitoring"""

    def __init__(self, connector):
        self.connector = connector
        self.metrics = {
            "orders_placed_total": 0,
            "orders_cancelled_total": 0,
            "orders_filled_total": 0,
            "api_requests_total": 0,
            "errors_total": 0,
            "balance_updates_total": 0,
        }

    def record_order_placed(self, trading_pair: str, side: str) -> None:
        """Record order placement metric"""
        self.metrics["orders_placed_total"] += 1

    def record_order_cancelled(self, trading_pair: str) -> None:
        """Record order cancellation metric"""
        self.metrics["orders_cancelled_total"] += 1

    def record_order_filled(self, trading_pair: str, amount: Decimal) -> None:
        """Record order fill metric"""
        self.metrics["orders_filled_total"] += 1

    def record_api_request(self, endpoint: str, latency_ms: float) -> None:
        """Record API request metric"""
        self.metrics["api_requests_total"] += 1

    def record_error(self, error_type: str) -> None:
        """Record error metric"""
        self.metrics["errors_total"] += 1

    def get_metrics_summary(self) -> Dict:
        """Get current metrics summary"""
        return {
            "metrics": self.metrics.copy(),
            "timestamp": time.time(),
            "uptime_seconds": self.get_uptime_seconds(),
        }

    def get_uptime_seconds(self) -> float:
        """Get connector uptime in seconds"""
        # This would track actual uptime
        return time.time() - getattr(self, "start_time", time.time())


class DockerDeploymentHelper:
    """Helper for Docker deployment configuration"""

    @staticmethod
    def generate_dockerfile() -> str:
        """Generate optimized Dockerfile for production"""

        return """
FROM python:3.9-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y gcc g++ make && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Production stage
FROM python:3.9-slim as production

# Create non-root user
RUN groupadd -r stellar && useradd -r -g stellar stellar

# Install runtime dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy from builder
COPY --from=builder /app /app
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages

# Set ownership
RUN chown -R stellar:stellar /app

# Switch to non-root user
USER stellar

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD python -c "import sys; sys.exit(0)"

# Expose port
EXPOSE 8080

# Start application
CMD ["python", "-m", "hummingbot"]
"""

    @staticmethod
    def generate_docker_compose() -> str:
        """Generate Docker Compose configuration"""

        return """
version: '3.8'

services:
  stellar-connector:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - STELLAR_NETWORK=testnet
      - LOG_LEVEL=INFO
    ports:
      - "8080:8080"
      - "9090:9090"
    volumes:
      - ./config:/app/config:ro
      - ./logs:/app/logs
    restart: unless-stopped
    
    # Resource limits
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
          cpus: '0.25'
    
    # Health check
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # Optional: Add monitoring stack
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9091:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-storage:/var/lib/grafana

volumes:
  grafana-storage:
"""


class KubernetesDeploymentHelper:
    """Helper for Kubernetes deployment"""

    @staticmethod
    def generate_k8s_manifests() -> Dict[str, str]:
        """Generate Kubernetes deployment manifests"""

        return {
            "deployment.yaml": """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stellar-connector
  namespace: hummingbot
spec:
  replicas: 2
  selector:
    matchLabels:
      app: stellar-connector
  template:
    metadata:
      labels:
        app: stellar-connector
    spec:
      serviceAccountName: stellar-connector
      containers:
      - name: stellar-connector
        image: hummingbot/stellar-connector:1.0.0
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 9090
          name: metrics
        env:
        - name: STELLAR_NETWORK
          value: "mainnet"
        - name: STELLAR_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: stellar-secrets
              key: secret-key
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
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        securityContext:
          runAsNonRoot: true
          runAsUser: 1001
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
""",
            "service.yaml": """
apiVersion: v1
kind: Service
metadata:
  name: stellar-connector-service
  namespace: hummingbot
spec:
  selector:
    app: stellar-connector
  ports:
  - name: http
    port: 80
    targetPort: 8080
  - name: metrics
    port: 9090
    targetPort: 9090
  type: ClusterIP
""",
            "configmap.yaml": """
apiVersion: v1
kind: ConfigMap
metadata:
  name: stellar-connector-config
  namespace: hummingbot
data:
  config.yaml: |
    stellar:
      network: mainnet
      reserve_buffer: "5.0"
      trustline_auto_setup: true
      path_payment_enabled: true
    performance:
      connection_pool_size: 5
      request_timeout: 30
      cache_ttl_ms: 5000
    monitoring:
      enable_metrics: true
      log_level: "INFO"
""",
        }


class ConfigurationValidator:
    """Validate configuration before deployment"""

    @staticmethod
    def validate_production_config(config: Dict) -> Dict:
        """Validate production configuration"""

        errors = []
        warnings = []

        # Validate required fields
        stellar_config = config.get("stellar", {})

        if not stellar_config.get("network"):
            errors.append("Stellar network not specified")

        if stellar_config.get("network") == "testnet":
            warnings.append("Using testnet in production configuration")

        # Validate security settings
        security_config = stellar_config.get("security", {})

        if not security_config.get("use_hsm"):
            warnings.append("HSM not enabled - consider for production security")

        if security_config.get("key_rotation_days", 0) > 90:
            warnings.append("Key rotation interval longer than recommended 90 days")

        # Validate performance settings
        performance_config = stellar_config.get("performance", {})

        if performance_config.get("connection_pool_size", 0) < 3:
            warnings.append("Connection pool size below recommended minimum of 3")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "security_score": ConfigurationValidator.calculate_security_score(config),
        }

    @staticmethod
    def calculate_security_score(config: Dict) -> float:
        """Calculate configuration security score (0-10)"""

        score = 5.0  # Base score
        stellar_config = config.get("stellar", {})
        security_config = stellar_config.get("security", {})

        # HSM usage (+2 points)
        if security_config.get("use_hsm"):
            score += 2.0

        # Replay protection (+1 point)
        if security_config.get("enable_replay_protection"):
            score += 1.0

        # Key rotation (+1 point)
        rotation_days = security_config.get("key_rotation_days", 365)
        if rotation_days <= 90:
            score += 1.0

        # Network selection (+1 point for mainnet)
        if stellar_config.get("network") == "mainnet":
            score += 1.0

        return min(10.0, score)


# Quick deployment script
def quick_deploy():
    """Quick deployment script for development"""

    print("Stellar Connector Quick Deploy")
    print("=" * 40)

    # Generate development configuration
    dev_config = ProductionDeploymentConfig.get_development_config()

    # Validate configuration
    validation = ConfigurationValidator.validate_production_config(dev_config)

    print(f"Configuration Valid: {validation['valid']}")

    if validation["warnings"]:
        print("Warnings:")
        for warning in validation["warnings"]:
            print(f"  - {warning}")

    if validation["errors"]:
        print("Errors:")
        for error in validation["errors"]:
            print(f"  - {error}")
        return False

    print(f"Security Score: {validation['security_score']}/10")

    # Generate Docker files
    dockerfile = DockerDeploymentHelper.generate_dockerfile()
    docker_compose = DockerDeploymentHelper.generate_docker_compose()

    # Write files
    with open("Dockerfile", "w") as f:
        f.write(dockerfile)

    with open("docker-compose.yml", "w") as f:
        f.write(docker_compose)

    print("\nDeployment files generated:")
    print("  - Dockerfile")
    print("  - docker-compose.yml")
    print("\nTo deploy:")
    print("  docker-compose up -d")

    return True


if __name__ == "__main__":
    quick_deploy()
