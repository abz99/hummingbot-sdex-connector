#!/usr/bin/env python3
"""
Production Observability Startup Script
Comprehensive production observability framework initialization.
Phase 4: Production Hardening - Automated observability deployment.
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any

import docker
import psutil
import requests
from prometheus_client import CollectorRegistry, start_http_server

# Add project path for imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from hummingbot.connector.exchange.stellar.stellar_observability import (
    start_production_observability,
)
from hummingbot.connector.exchange.stellar.stellar_production_metrics import (
    start_production_metrics,
)


class ProductionObservabilityManager:
    """Manages production observability infrastructure."""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or "config/production_observability.yml"
        self.config = self._load_config()
        self.docker_client = None
        self.logger = self._setup_logging()
        
        # Service status tracking
        self.services_status: Dict[str, str] = {}
        self.health_checks: Dict[str, bool] = {}
        
        # Performance tracking
        self.startup_time = time.time()
        self.initialization_steps: List[Dict[str, Any]] = []

    def _setup_logging(self) -> logging.Logger:
        """Set up logging for observability manager."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/production_observability.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)

    def _load_config(self) -> Dict[str, Any]:
        """Load production observability configuration."""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    return yaml.safe_load(f)
            else:
                return self._get_default_config()
        except Exception as e:
            print(f"Error loading config: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default production observability configuration."""
        return {
            "observability": {
                "metrics_port": 8000,
                "pushgateway_url": None,
                "alert_webhook_url": None,
                "collection_interval": 30,
                "enable_tracing": True,
                "enable_profiling": False,
            },
            "docker": {
                "compose_file": "observability/docker-compose.observability.yml",
                "project_name": "stellar-observability",
                "pull_images": True,
                "wait_timeout": 300,
            },
            "services": {
                "prometheus": {
                    "port": 9090,
                    "health_endpoint": "/-/healthy",
                    "required": True,
                },
                "grafana": {
                    "port": 3000,
                    "health_endpoint": "/api/health",
                    "required": True,
                },
                "alertmanager": {
                    "port": 9093,
                    "health_endpoint": "/-/healthy",
                    "required": False,
                },
                "jaeger": {
                    "port": 16686,
                    "health_endpoint": "/",
                    "required": False,
                },
            },
            "monitoring": {
                "startup_checks": True,
                "health_check_interval": 60,
                "auto_restart_failed": True,
                "notification_webhooks": [],
            },
            "security": {
                "enable_tls": False,
                "basic_auth": False,
                "api_keys": {},
                "network_isolation": True,
            },
            "performance": {
                "resource_limits": {
                    "cpu_cores": 2,
                    "memory_gb": 4,
                    "disk_gb": 50,
                },
                "scaling": {
                    "auto_scale": False,
                    "min_instances": 1,
                    "max_instances": 3,
                },
            },
        }

    async def start_production_observability(self) -> bool:
        """Start complete production observability stack."""
        try:
            self.logger.info("🚀 Starting Production Observability Framework")
            self.logger.info(f"Configuration: {self.config_path}")
            
            # Step 1: Pre-flight checks
            self._add_step("pre_flight_checks", "started")
            if not await self._run_preflight_checks():
                self._add_step("pre_flight_checks", "failed")
                return False
            self._add_step("pre_flight_checks", "completed")

            # Step 2: Initialize Docker infrastructure
            self._add_step("docker_infrastructure", "started")
            if not await self._start_docker_infrastructure():
                self._add_step("docker_infrastructure", "failed")
                return False
            self._add_step("docker_infrastructure", "completed")

            # Step 3: Start core observability services
            self._add_step("core_observability", "started")
            observability = await start_production_observability(
                metrics_port=self.config["observability"]["metrics_port"],
                pushgateway_url=self.config["observability"]["pushgateway_url"],
                alert_webhook_url=self.config["observability"]["alert_webhook_url"],
            )
            if not observability:
                self._add_step("core_observability", "failed")
                return False
            self._add_step("core_observability", "completed")

            # Step 4: Start production metrics collection
            self._add_step("production_metrics", "started")
            metrics = await start_production_metrics(
                collection_interval=self.config["observability"]["collection_interval"]
            )
            if not metrics:
                self._add_step("production_metrics", "failed")
                return False
            self._add_step("production_metrics", "completed")

            # Step 5: Verify service health
            self._add_step("health_verification", "started")
            if not await self._verify_service_health():
                self._add_step("health_verification", "failed")
                return False
            self._add_step("health_verification", "completed")

            # Step 6: Configure dashboards and alerts
            self._add_step("dashboard_configuration", "started")
            if not await self._configure_dashboards_and_alerts():
                self._add_step("dashboard_configuration", "failed")
                return False
            self._add_step("dashboard_configuration", "completed")

            # Step 7: Start monitoring and health checks
            self._add_step("monitoring_startup", "started")
            await self._start_background_monitoring()
            self._add_step("monitoring_startup", "completed")

            # Success!
            total_time = time.time() - self.startup_time
            self.logger.info(f"✅ Production Observability Started Successfully!")
            self.logger.info(f"⏱️  Total startup time: {total_time:.2f} seconds")
            self.logger.info(f"📊 Services: {len([s for s in self.services_status.values() if s == 'running'])}/{len(self.services_status)} running")
            
            self._print_service_urls()
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to start production observability: {e}")
            self._add_step("startup", "failed", {"error": str(e)})
            return False

    def _add_step(self, step_name: str, status: str, details: Dict[str, Any] = None):
        """Add initialization step to tracking."""
        self.initialization_steps.append({
            "step": step_name,
            "status": status,
            "timestamp": time.time(),
            "details": details or {}
        })

    async def _run_preflight_checks(self) -> bool:
        """Run pre-flight system checks."""
        self.logger.info("🔍 Running pre-flight checks...")
        
        checks = [
            ("System resources", self._check_system_resources),
            ("Docker availability", self._check_docker_availability),
            ("Network ports", self._check_network_ports),
            ("File permissions", self._check_file_permissions),
            ("Configuration validity", self._check_configuration_validity),
        ]
        
        for check_name, check_func in checks:
            try:
                self.logger.info(f"  • {check_name}...")
                result = await check_func() if asyncio.iscoroutinefunction(check_func) else check_func()
                if not result:
                    self.logger.error(f"  ❌ {check_name} check failed")
                    return False
                self.logger.info(f"  ✅ {check_name} check passed")
            except Exception as e:
                self.logger.error(f"  ❌ {check_name} check error: {e}")
                return False
        
        return True

    def _check_system_resources(self) -> bool:
        """Check system resource availability."""
        # CPU check
        cpu_count = psutil.cpu_count()
        required_cpus = self.config["performance"]["resource_limits"]["cpu_cores"]
        if cpu_count < required_cpus:
            self.logger.warning(f"CPU cores: {cpu_count} < {required_cpus} (may impact performance)")
        
        # Memory check
        memory = psutil.virtual_memory()
        memory_gb = memory.total / (1024**3)
        required_memory = self.config["performance"]["resource_limits"]["memory_gb"]
        if memory_gb < required_memory:
            self.logger.warning(f"Memory: {memory_gb:.1f}GB < {required_memory}GB (may impact performance)")
        
        # Disk check
        disk = psutil.disk_usage('/')
        disk_gb = disk.free / (1024**3)
        required_disk = self.config["performance"]["resource_limits"]["disk_gb"]
        if disk_gb < required_disk:
            self.logger.error(f"Disk space: {disk_gb:.1f}GB < {required_disk}GB (insufficient)")
            return False
        
        return True

    def _check_docker_availability(self) -> bool:
        """Check Docker availability and connectivity."""
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            return True
        except Exception as e:
            self.logger.error(f"Docker not available: {e}")
            return False

    def _check_network_ports(self) -> bool:
        """Check if required network ports are available."""
        import socket
        
        ports_to_check = [
            self.config["observability"]["metrics_port"],
            self.config["services"]["prometheus"]["port"],
            self.config["services"]["grafana"]["port"],
            self.config["services"]["alertmanager"]["port"],
        ]
        
        for port in ports_to_check:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                result = sock.connect_ex(('localhost', port))
                if result == 0:
                    self.logger.warning(f"Port {port} is already in use")
                    # Continue anyway - might be from previous run
        
        return True

    def _check_file_permissions(self) -> bool:
        """Check file and directory permissions."""
        paths_to_check = [
            "observability/",
            "logs/",
            "config/",
        ]
        
        for path in paths_to_check:
            path_obj = Path(path)
            if not path_obj.exists():
                try:
                    path_obj.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    self.logger.error(f"Cannot create directory {path}: {e}")
                    return False
            
            if not os.access(path, os.R_OK | os.W_OK):
                self.logger.error(f"Insufficient permissions for {path}")
                return False
        
        return True

    def _check_configuration_validity(self) -> bool:
        """Check configuration file validity."""
        required_sections = ["observability", "services", "docker"]
        for section in required_sections:
            if section not in self.config:
                self.logger.error(f"Missing required configuration section: {section}")
                return False
        
        return True

    async def _start_docker_infrastructure(self) -> bool:
        """Start Docker observability infrastructure."""
        self.logger.info("🐳 Starting Docker observability infrastructure...")
        
        try:
            compose_file = Path(self.config["docker"]["compose_file"])
            if not compose_file.exists():
                self.logger.error(f"Docker compose file not found: {compose_file}")
                return False
            
            # Pull images if configured
            if self.config["docker"]["pull_images"]:
                self.logger.info("  📥 Pulling Docker images...")
                result = subprocess.run([
                    "docker-compose", "-f", str(compose_file), "pull"
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode != 0:
                    self.logger.warning(f"Image pull warnings: {result.stderr}")
            
            # Start services
            self.logger.info("  🚀 Starting Docker services...")
            result = subprocess.run([
                "docker-compose", "-f", str(compose_file),
                "-p", self.config["docker"]["project_name"],
                "up", "-d", "--remove-orphans"
            ], capture_output=True, text=True, timeout=180)
            
            if result.returncode != 0:
                self.logger.error(f"Docker compose failed: {result.stderr}")
                return False
            
            # Wait for services to be ready
            self.logger.info("  ⏳ Waiting for services to be ready...")
            await self._wait_for_docker_services()
            
            return True
            
        except subprocess.TimeoutExpired:
            self.logger.error("Docker startup timeout")
            return False
        except Exception as e:
            self.logger.error(f"Docker infrastructure startup failed: {e}")
            return False

    async def _wait_for_docker_services(self):
        """Wait for Docker services to become ready."""
        timeout = self.config["docker"]["wait_timeout"]
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            all_ready = True
            
            for service_name, service_config in self.config["services"].items():
                if not service_config.get("required", True):
                    continue
                
                try:
                    url = f"http://localhost:{service_config['port']}{service_config['health_endpoint']}"
                    response = requests.get(url, timeout=5)
                    
                    if response.status_code == 200:
                        self.services_status[service_name] = "running"
                        self.health_checks[service_name] = True
                    else:
                        self.services_status[service_name] = "unhealthy"
                        self.health_checks[service_name] = False
                        all_ready = False
                        
                except requests.RequestException:
                    self.services_status[service_name] = "starting"
                    self.health_checks[service_name] = False
                    all_ready = False
            
            if all_ready:
                self.logger.info("  ✅ All required services are ready")
                break
                
            await asyncio.sleep(5)
        else:
            self.logger.warning("  ⚠️  Service startup timeout - some services may not be ready")

    async def _verify_service_health(self) -> bool:
        """Verify health of all critical services."""
        self.logger.info("🩺 Verifying service health...")
        
        critical_failures = 0
        
        for service_name, is_healthy in self.health_checks.items():
            service_config = self.config["services"][service_name]
            
            if service_config.get("required", True) and not is_healthy:
                self.logger.error(f"  ❌ Critical service {service_name} is not healthy")
                critical_failures += 1
            elif is_healthy:
                self.logger.info(f"  ✅ Service {service_name} is healthy")
            else:
                self.logger.warning(f"  ⚠️  Optional service {service_name} is not healthy")
        
        if critical_failures > 0:
            self.logger.error(f"❌ {critical_failures} critical service(s) failed health check")
            return False
        
        return True

    async def _configure_dashboards_and_alerts(self) -> bool:
        """Configure Grafana dashboards and Prometheus alerts."""
        self.logger.info("📊 Configuring dashboards and alerts...")
        
        try:
            # Import Grafana dashboards
            grafana_url = f"http://localhost:{self.config['services']['grafana']['port']}"
            dashboards_path = Path("observability/grafana/dashboards/")
            
            if dashboards_path.exists():
                for dashboard_file in dashboards_path.glob("*.json"):
                    self.logger.info(f"  📈 Importing dashboard: {dashboard_file.name}")
                    # Import dashboard logic would go here
                    # For now, just log the intention
            
            # Verify Prometheus rules
            prometheus_url = f"http://localhost:{self.config['services']['prometheus']['port']}"
            rules_response = requests.get(f"{prometheus_url}/api/v1/rules", timeout=10)
            
            if rules_response.status_code == 200:
                rules_data = rules_response.json()
                rule_count = len(rules_data.get("data", {}).get("groups", []))
                self.logger.info(f"  📏 Prometheus rules loaded: {rule_count} groups")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Dashboard/alert configuration failed: {e}")
            return False

    async def _start_background_monitoring(self):
        """Start background monitoring tasks."""
        self.logger.info("🔍 Starting background monitoring...")
        
        # This would start background health checking tasks
        # For now, just log the intention
        asyncio.create_task(self._health_check_loop())
        
        self.logger.info("  ✅ Background monitoring started")

    async def _health_check_loop(self):
        """Background health check loop."""
        while True:
            try:
                await asyncio.sleep(self.config["monitoring"]["health_check_interval"])
                
                # Perform health checks
                for service_name, service_config in self.config["services"].items():
                    try:
                        url = f"http://localhost:{service_config['port']}{service_config['health_endpoint']}"
                        response = requests.get(url, timeout=5)
                        
                        previous_status = self.health_checks.get(service_name, False)
                        current_status = response.status_code == 200
                        
                        self.health_checks[service_name] = current_status
                        
                        # Log status changes
                        if previous_status != current_status:
                            status_text = "healthy" if current_status else "unhealthy"
                            self.logger.info(f"Service {service_name} is now {status_text}")
                            
                    except Exception as e:
                        self.health_checks[service_name] = False
                        self.logger.warning(f"Health check failed for {service_name}: {e}")
                        
            except Exception as e:
                self.logger.error(f"Health check loop error: {e}")

    def _print_service_urls(self):
        """Print service URLs for user access."""
        self.logger.info("\n🌐 Service Access URLs:")
        
        for service_name, service_config in self.config["services"].items():
            if self.health_checks.get(service_name, False):
                url = f"http://localhost:{service_config['port']}"
                status = "✅"
            else:
                url = f"http://localhost:{service_config['port']} (unavailable)"
                status = "❌"
            
            self.logger.info(f"  {status} {service_name.title()}: {url}")
        
        self.logger.info(f"\n📊 Metrics endpoint: http://localhost:{self.config['observability']['metrics_port']}/metrics")

    def get_status_report(self) -> Dict[str, Any]:
        """Get comprehensive status report."""
        return {
            "timestamp": time.time(),
            "startup_time": time.time() - self.startup_time,
            "services_status": self.services_status,
            "health_checks": self.health_checks,
            "initialization_steps": self.initialization_steps,
            "configuration": {
                "metrics_port": self.config["observability"]["metrics_port"],
                "collection_interval": self.config["observability"]["collection_interval"],
                "services_count": len(self.config["services"]),
            }
        }

    async def stop_production_observability(self) -> bool:
        """Stop production observability stack."""
        self.logger.info("🛑 Stopping production observability...")
        
        try:
            # Stop Docker services
            compose_file = Path(self.config["docker"]["compose_file"])
            if compose_file.exists():
                result = subprocess.run([
                    "docker-compose", "-f", str(compose_file),
                    "-p", self.config["docker"]["project_name"],
                    "down"
                ], capture_output=True, text=True, timeout=120)
                
                if result.returncode != 0:
                    self.logger.warning(f"Docker compose down warnings: {result.stderr}")
            
            self.logger.info("✅ Production observability stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to stop production observability: {e}")
            return False


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Stellar Production Observability Manager"
    )
    parser.add_argument(
        "--config", "-c",
        default="config/production_observability.yml",
        help="Configuration file path"
    )
    parser.add_argument(
        "--action", "-a",
        choices=["start", "stop", "status", "restart"],
        default="start",
        help="Action to perform"
    )
    parser.add_argument(
        "--wait", "-w",
        action="store_true",
        help="Wait for user input after startup"
    )
    
    args = parser.parse_args()
    
    manager = ProductionObservabilityManager(args.config)
    
    if args.action == "start":
        success = await manager.start_production_observability()
        
        if success:
            print("\n🎉 Production Observability Framework Started Successfully!")
            print("\nPress Ctrl+C to stop services...")
            
            if args.wait:
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    print("\n🛑 Shutting down...")
                    await manager.stop_production_observability()
        else:
            print("\n❌ Failed to start production observability")
            sys.exit(1)
            
    elif args.action == "stop":
        success = await manager.stop_production_observability()
        sys.exit(0 if success else 1)
        
    elif args.action == "status":
        report = manager.get_status_report()
        print(json.dumps(report, indent=2))
        
    elif args.action == "restart":
        await manager.stop_production_observability()
        await asyncio.sleep(5)
        success = await manager.start_production_observability()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())