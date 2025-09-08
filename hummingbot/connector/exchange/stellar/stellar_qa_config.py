"""
QA Metrics Collection Configuration

Provides centralized configuration and factory for QA metrics collection,
allowing seamless switching between original and optimized implementations
based on configuration or runtime conditions.

QA_ID: REQ-CONFIG-001, REQ-PERF-003
"""

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING, Union

from .stellar_logging import get_stellar_logger, LogCategory

if TYPE_CHECKING:
    from .stellar_qa_metrics import StellarQAMetricsCollector
    from .stellar_qa_metrics_optimized import OptimizedStellarQAMetricsCollector

CollectorType = Union["StellarQAMetricsCollector", "OptimizedStellarQAMetricsCollector"]


class QACollectorMode(Enum):
    """QA metrics collector operation modes."""

    ORIGINAL = "original"
    OPTIMIZED = "optimized"
    AUTO = "auto"


class QAPerformanceProfile(Enum):
    """Performance profiles for QA metrics collection."""

    DEVELOPMENT = "development"  # Fast feedback, less accuracy
    PRODUCTION = "production"  # Balanced performance and accuracy
    HIGH_ACCURACY = "high_accuracy"  # Maximum accuracy, slower
    BENCHMARK = "benchmark"  # For performance testing


@dataclass
class QAMetricsConfig:
    """Configuration for QA metrics collection."""

    # Core Settings
    collector_mode: QACollectorMode = QACollectorMode.AUTO
    performance_profile: QAPerformanceProfile = QAPerformanceProfile.PRODUCTION

    # Performance Settings
    max_workers: int = 4
    cache_ttl_seconds: float = 300.0
    batch_size: int = 10
    incremental_threshold: float = 60.0

    # Collection Settings
    collect_coverage: bool = True
    collect_test_metrics: bool = True
    collect_quality_metrics: bool = True
    collect_compliance_metrics: bool = True

    # Timeouts and Limits
    subprocess_timeout: float = 120.0
    lightweight_test_timeout: float = 30.0
    max_file_size_mb: float = 10.0

    # Caching Settings
    enable_file_caching: bool = True
    enable_incremental_updates: bool = True
    cache_directory: Optional[str] = None

    # Monitoring Settings
    enable_performance_logging: bool = True
    log_cache_effectiveness: bool = False
    log_execution_time: bool = True

    # Quality Thresholds
    critical_module_thresholds: Dict[str, float] = field(
        default_factory=lambda: {
            "stellar_security_manager": 95.0,
            "stellar_chain_interface": 90.0,
            "stellar_network_manager": 90.0,
            "stellar_order_manager": 90.0,
            "stellar_exchange": 85.0,
            "stellar_soroban_manager": 85.0,
            "stellar_security": 95.0,
        }
    )

    # Auto-selection Criteria
    auto_selection_rules: Dict[str, Any] = field(
        default_factory=lambda: {
            "file_count_threshold": 50,  # Use optimized if >50 files
            "memory_limit_mb": 512,  # Switch to optimized if memory usage > 512MB
            "execution_time_threshold": 30.0,  # Switch to optimized if execution > 30s
            "concurrent_requests_threshold": 2,  # Use optimized if >2 concurrent requests
        }
    )


class QAConfigManager:
    """Manages QA metrics configuration and collector instantiation."""

    def __init__(self, config_path: Optional[Path] = None):
        self.logger = get_stellar_logger()
        self.config_path = config_path or self._get_default_config_path()
        self._config: Optional[QAMetricsConfig] = None
        self._runtime_stats = {
            "collector_switches": 0,
            "performance_degradations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

    def _get_default_config_path(self) -> Path:
        """Get default configuration file path."""
        project_root = self._find_project_root()
        return project_root / "config" / "qa_metrics_config.json"

    def _find_project_root(self) -> Path:
        """Find project root directory."""
        current = Path(__file__).parent
        while current.parent != current:
            if (current / "setup.py").exists() or (current / ".git").exists():
                return current
            current = current.parent
        return Path.cwd()

    @property
    def config(self) -> QAMetricsConfig:
        """Get current configuration, loading from file if needed."""
        if self._config is None:
            self._config = self.load_config()
        return self._config

    def load_config(self) -> QAMetricsConfig:
        """Load configuration from file or create default."""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r") as f:
                    config_data = json.load(f)

                # Convert string enums back to enum objects
                if "collector_mode" in config_data:
                    config_data["collector_mode"] = QACollectorMode(config_data["collector_mode"])
                if "performance_profile" in config_data:
                    config_data["performance_profile"] = QAPerformanceProfile(
                        config_data["performance_profile"]
                    )

                config = QAMetricsConfig(**config_data)
                self.logger.info(
                    f"Loaded QA metrics configuration from {self.config_path}",
                    category=LogCategory.CONFIGURATION,
                )
                return config
            else:
                config = QAMetricsConfig()
                self.save_config(config)
                self.logger.info(
                    f"Created default QA metrics configuration at {self.config_path}",
                    category=LogCategory.CONFIGURATION,
                )
                return config

        except Exception as e:
            self.logger.error(
                f"Failed to load QA metrics configuration: {e}", category=LogCategory.ERROR_HANDLING
            )
            return QAMetricsConfig()  # Fallback to defaults

    def save_config(self, config: Optional[QAMetricsConfig] = None):
        """Save configuration to file."""
        config = config or self.config

        try:
            # Ensure config directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert to dictionary for JSON serialization
            config_dict = {
                "collector_mode": config.collector_mode.value,
                "performance_profile": config.performance_profile.value,
                "max_workers": config.max_workers,
                "cache_ttl_seconds": config.cache_ttl_seconds,
                "batch_size": config.batch_size,
                "incremental_threshold": config.incremental_threshold,
                "collect_coverage": config.collect_coverage,
                "collect_test_metrics": config.collect_test_metrics,
                "collect_quality_metrics": config.collect_quality_metrics,
                "collect_compliance_metrics": config.collect_compliance_metrics,
                "subprocess_timeout": config.subprocess_timeout,
                "lightweight_test_timeout": config.lightweight_test_timeout,
                "max_file_size_mb": config.max_file_size_mb,
                "enable_file_caching": config.enable_file_caching,
                "enable_incremental_updates": config.enable_incremental_updates,
                "cache_directory": config.cache_directory,
                "enable_performance_logging": config.enable_performance_logging,
                "log_cache_effectiveness": config.log_cache_effectiveness,
                "log_execution_time": config.log_execution_time,
                "critical_module_thresholds": config.critical_module_thresholds,
                "auto_selection_rules": config.auto_selection_rules,
            }

            with open(self.config_path, "w") as f:
                json.dump(config_dict, f, indent=2)

            self.logger.info(
                f"Saved QA metrics configuration to {self.config_path}", category=LogCategory.CONFIG
            )

        except Exception as e:
            self.logger.error(
                f"Failed to save QA metrics configuration: {e}", category=LogCategory.ERROR_HANDLING
            )

    def get_collector_mode(self) -> QACollectorMode:
        """Determine which collector mode to use based on configuration and runtime conditions."""
        config_mode = self.config.collector_mode

        if config_mode == QACollectorMode.AUTO:
            return self._auto_select_collector_mode()
        else:
            return config_mode

    def _auto_select_collector_mode(self) -> QACollectorMode:
        """Automatically select collector mode based on runtime conditions."""
        rules = self.config.auto_selection_rules

        try:
            # Check file count
            project_root = self._find_project_root()
            stellar_files = list(
                (project_root / "hummingbot/connector/exchange/stellar").glob("*.py")
            )
            if len(stellar_files) > rules.get("file_count_threshold", 50):
                self.logger.debug(
                    f"Auto-selecting optimized collector due to file count ({len(stellar_files)})",
                    category=LogCategory.CONFIGURATION,
                )
                return QACollectorMode.OPTIMIZED

            # Check available memory
            import psutil

            memory_usage_mb = psutil.Process().memory_info().rss / 1024 / 1024
            if memory_usage_mb > rules.get("memory_limit_mb", 512):
                self.logger.debug(
                    f"Auto-selecting optimized collector due to memory usage ({memory_usage_mb:.1f}MB)",
                    category=LogCategory.CONFIGURATION,
                )
                return QACollectorMode.OPTIMIZED

            # Check for development environment
            if os.getenv("QA_DEVELOPMENT_MODE", "false").lower() == "true":
                self.logger.debug(
                    "Auto-selecting optimized collector for development mode",
                    category=LogCategory.CONFIGURATION,
                )
                return QACollectorMode.OPTIMIZED

            # Default to optimized for better performance
            return QACollectorMode.OPTIMIZED

        except Exception as e:
            self.logger.warning(
                f"Failed to auto-select collector mode: {e}, defaulting to optimized",
                category=LogCategory.CONFIGURATION,
            )
            return QACollectorMode.OPTIMIZED

    def create_collector(self) -> CollectorType:
        """Create and configure a QA metrics collector based on current configuration."""
        collector_mode = self.get_collector_mode()

        try:
            if collector_mode == QACollectorMode.ORIGINAL:
                from .stellar_qa_metrics import StellarQAMetricsCollector

                collector = StellarQAMetricsCollector()
                self.logger.info(
                    "Created original QA metrics collector", category=LogCategory.CONFIGURATION
                )
            else:  # OPTIMIZED
                from .stellar_qa_metrics_optimized import OptimizedStellarQAMetricsCollector

                collector = OptimizedStellarQAMetricsCollector(max_workers=self.config.max_workers)

                # Configure optimized collector
                collector.cache.default_ttl = self.config.cache_ttl_seconds
                collector.batch_size = self.config.batch_size
                collector.incremental_threshold = self.config.incremental_threshold

                self.logger.info(
                    f"Created optimized QA metrics collector (workers: {self.config.max_workers})",
                    category=LogCategory.CONFIGURATION,
                )

            # Apply common configuration
            if hasattr(collector, "critical_modules"):
                collector.critical_modules = self.config.critical_module_thresholds

            self._runtime_stats["collector_switches"] += 1
            return collector

        except Exception as e:
            self.logger.error(
                f"Failed to create QA metrics collector: {e}", category=LogCategory.ERROR_HANDLING
            )
            raise

    def update_performance_profile(self, profile: QAPerformanceProfile):
        """Update performance profile and adjust settings accordingly."""
        self.config.performance_profile = profile

        # Adjust settings based on profile
        if profile == QAPerformanceProfile.DEVELOPMENT:
            self.config.cache_ttl_seconds = 600.0  # 10 minutes
            self.config.subprocess_timeout = 60.0
            self.config.enable_incremental_updates = True
            self.config.max_workers = 6

        elif profile == QAPerformanceProfile.PRODUCTION:
            self.config.cache_ttl_seconds = 300.0  # 5 minutes
            self.config.subprocess_timeout = 120.0
            self.config.enable_incremental_updates = True
            self.config.max_workers = 4

        elif profile == QAPerformanceProfile.HIGH_ACCURACY:
            self.config.cache_ttl_seconds = 60.0  # 1 minute
            self.config.subprocess_timeout = 300.0
            self.config.enable_incremental_updates = False
            self.config.max_workers = 2

        elif profile == QAPerformanceProfile.BENCHMARK:
            self.config.cache_ttl_seconds = 0.0  # No cache
            self.config.subprocess_timeout = 600.0
            self.config.enable_incremental_updates = False
            self.config.max_workers = 8

        self.save_config()
        self.logger.info(
            f"Updated performance profile to {profile.value}", category=LogCategory.CONFIGURATION
        )

    def get_runtime_stats(self) -> Dict[str, int]:
        """Get runtime statistics."""
        return self._runtime_stats.copy()

    def reset_runtime_stats(self):
        """Reset runtime statistics."""
        self._runtime_stats = {
            "collector_switches": 0,
            "performance_degradations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }


# Global configuration manager
_config_manager: Optional[QAConfigManager] = None


def get_qa_config_manager() -> QAConfigManager:
    """Get global QA configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = QAConfigManager()
    return _config_manager


def get_qa_collector() -> CollectorType:
    """Get configured QA metrics collector instance."""
    return get_qa_config_manager().create_collector()


def configure_qa_metrics(
    mode: Optional[QACollectorMode] = None, profile: Optional[QAPerformanceProfile] = None, **kwargs
) -> QAMetricsConfig:
    """Configure QA metrics collection settings."""
    config_manager = get_qa_config_manager()
    config = config_manager.config

    if mode:
        config.collector_mode = mode

    if profile:
        config_manager.update_performance_profile(profile)

    # Apply additional configuration
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)

    config_manager.save_config(config)
    return config
