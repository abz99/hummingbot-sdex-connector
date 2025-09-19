"""
Enterprise Configuration Management
Handles loading and validation of enterprise feature configurations.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from .core import EnterpriseFeatureConfig
from ..stellar_logging import get_stellar_logger


class EnterpriseConfigManager:
    """Manages enterprise feature configuration loading and validation."""

    def __init__(self, config_path: Optional[str] = None):
        self.logger = get_stellar_logger()
        self.config_path = config_path or self._get_default_config_path()

    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        # Try multiple locations in order of preference
        possible_paths = [
            "config/enterprise_features.yaml",
            "enterprise_features.yaml",
            os.path.expanduser("~/.hummingbot/enterprise_features.yaml"),
            "/etc/hummingbot/enterprise_features.yaml"
        ]

        for path in possible_paths:
            if Path(path).exists():
                return path

        # Return the first option as default (even if it doesn't exist)
        return possible_paths[0]

    async def load_config(self) -> Optional[EnterpriseFeatureConfig]:
        """Load enterprise features configuration from file."""
        config_file = Path(self.config_path)

        if not config_file.exists():
            self.logger.info(f"Enterprise config file not found: {self.config_path}")
            self.logger.info("Enterprise features will be disabled")
            return None

        try:
            with open(config_file, 'r') as f:
                yaml_config = yaml.safe_load(f)

            self.logger.info(f"Loading enterprise configuration from: {self.config_path}")
            return self._parse_yaml_config(yaml_config)

        except Exception as e:
            self.logger.error(f"Failed to load enterprise config: {e}")
            return None

    def _parse_yaml_config(self, yaml_config: Dict[str, Any]) -> EnterpriseFeatureConfig:
        """Parse YAML configuration into EnterpriseFeatureConfig."""
        features = yaml_config.get('enterprise_features', {})
        security = features.get('security', {})
        trading = features.get('trading', {})
        infrastructure = features.get('infrastructure', {})

        return EnterpriseFeatureConfig(
            # Security features
            vault_integration_enabled=security.get('vault_integration_enabled', False),
            hardware_wallet_enabled=security.get('hardware_wallet_enabled', False),
            security_hardening_enabled=security.get('security_hardening_enabled', False),
            security_metrics_enabled=security.get('security_metrics_enabled', False),

            # Trading features
            liquidity_management_enabled=trading.get('liquidity_management_enabled', False),
            yield_farming_enabled=trading.get('yield_farming_enabled', False),

            # Infrastructure features
            test_account_manager_enabled=infrastructure.get('test_account_manager_enabled', False),
            load_testing_enabled=infrastructure.get('load_testing_enabled', False),
            performance_optimizer_enabled=infrastructure.get('performance_optimizer_enabled', False),
            web_assistant_enabled=infrastructure.get('web_assistant_enabled', False),
            user_stream_tracker_enabled=infrastructure.get('user_stream_tracker_enabled', False),

            # Global settings
            validate_on_startup=features.get('validate_on_startup', True),
            fail_fast_on_errors=features.get('fail_fast_on_errors', False)
        )

    def save_config(self, config: EnterpriseFeatureConfig) -> bool:
        """Save enterprise configuration to file."""
        try:
            yaml_config = {
                'enterprise_features': {
                    'validate_on_startup': config.validate_on_startup,
                    'fail_fast_on_errors': config.fail_fast_on_errors,
                    'security': {
                        'vault_integration_enabled': config.vault_integration_enabled,
                        'hardware_wallet_enabled': config.hardware_wallet_enabled,
                        'security_hardening_enabled': config.security_hardening_enabled,
                        'security_metrics_enabled': config.security_metrics_enabled,
                    },
                    'trading': {
                        'liquidity_management_enabled': config.liquidity_management_enabled,
                        'yield_farming_enabled': config.yield_farming_enabled,
                    },
                    'infrastructure': {
                        'test_account_manager_enabled': config.test_account_manager_enabled,
                        'load_testing_enabled': config.load_testing_enabled,
                        'performance_optimizer_enabled': config.performance_optimizer_enabled,
                        'web_assistant_enabled': config.web_assistant_enabled,
                        'user_stream_tracker_enabled': config.user_stream_tracker_enabled,
                    }
                }
            }

            # Create directory if it doesn't exist
            config_file = Path(self.config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(config_file, 'w') as f:
                yaml.dump(yaml_config, f, default_flow_style=False, indent=2)

            self.logger.info(f"Enterprise configuration saved to: {self.config_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save enterprise config: {e}")
            return False

    def validate_environment(self, config: EnterpriseFeatureConfig) -> Dict[str, Any]:
        """Validate that required environment variables and dependencies are available."""
        validation_results = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "missing_env_vars": [],
            "missing_dependencies": []
        }

        # Check environment variables for enabled features
        if config.vault_integration_enabled:
            required_env = ["VAULT_TOKEN"]
            for env_var in required_env:
                if not os.getenv(env_var):
                    validation_results["missing_env_vars"].append(env_var)
                    validation_results["errors"].append(f"Missing required environment variable: {env_var}")

        # Check optional environment variables
        optional_env = {
            "VAULT_NAMESPACE": "vault_integration_enabled",
            "HW_WALLET_PIN": "hardware_wallet_enabled",
            "METRICS_API_KEY": "security_metrics_enabled"
        }

        for env_var, feature_flag in optional_env.items():
            if getattr(config, feature_flag) and not os.getenv(env_var):
                validation_results["warnings"].append(f"Optional environment variable not set: {env_var}")

        # Set overall validation status
        validation_results["valid"] = len(validation_results["errors"]) == 0

        return validation_results


# Global configuration manager instance
_config_manager: Optional[EnterpriseConfigManager] = None


def get_config_manager() -> EnterpriseConfigManager:
    """Get the global enterprise configuration manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = EnterpriseConfigManager()
    return _config_manager


def set_config_path(config_path: str) -> None:
    """Set a custom configuration file path."""
    global _config_manager
    _config_manager = EnterpriseConfigManager(config_path)


__all__ = [
    "EnterpriseConfigManager",
    "get_config_manager",
    "set_config_path"
]
