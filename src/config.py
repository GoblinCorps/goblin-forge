"""
Configuration Management

Loads and manages system configuration from YAML files and environment variables.

Configuration Files:
--------------------
- config/system_config.yaml : System-level settings (IB, database, logging, etc.)
- config/trading_params.yaml : Trading strategy parameters (indicators, thresholds, scoring)
- .env : Environment-specific variables (credentials, paths)

Usage:
------
from src.config import config

# Access configuration values
ib_host = config.ib.host
min_price = config.universe.min_price
sabr_weights = config.sabr20.weights

Environment Variables:
----------------------
All ${VAR_NAME:default} placeholders in YAML files are replaced with environment variables.
Priority: .env file > system environment > YAML defaults
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict
from dataclasses import dataclass, field
from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file
load_dotenv()


class ConfigDict(dict):
    """Dictionary with dot notation access."""

    def __getattr__(self, key: str) -> Any:
        try:
            value = self[key]
            if isinstance(value, dict):
                return ConfigDict(value)
            return value
        except KeyError:
            raise AttributeError(f"Configuration key '{key}' not found")

    def __setattr__(self, key: str, value: Any):
        self[key] = value


def load_yaml_config(filepath: Path) -> Dict[str, Any]:
    """
    Load YAML configuration file and replace environment variable placeholders.

    Parameters:
    -----------
    filepath : Path
        Path to YAML configuration file

    Returns:
    --------
    Dict[str, Any] : Parsed configuration dictionary
    """
    if not filepath.exists():
        logger.warning(f"Configuration file not found: {filepath}")
        return {}

    with open(filepath, 'r') as f:
        content = f.read()

    # Replace environment variable placeholders
    # Format: ${VAR_NAME:default_value}
    import re

    def replace_env_var(match):
        var_expr = match.group(1)
        if ':' in var_expr:
            var_name, default = var_expr.split(':', 1)
        else:
            var_name = var_expr
            default = ''

        value = os.getenv(var_name, default)

        # Convert string booleans to actual booleans
        if value.lower() in ('true', 'false'):
            return value.lower()

        return value

    content = re.sub(r'\$\{([^}]+)\}', replace_env_var, content)

    # Parse YAML
    config_dict = yaml.safe_load(content)

    return config_dict if config_dict else {}


@dataclass
class Config:
    """
    Main configuration class.

    Attributes:
    -----------
    system : ConfigDict
        System configuration (IB, database, logging, etc.)
    trading : ConfigDict
        Trading parameters (indicators, screening, SABR20, etc.)
    project_root : Path
        Project root directory
    """

    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    system: ConfigDict = field(default_factory=ConfigDict)
    trading: ConfigDict = field(default_factory=ConfigDict)

    def __post_init__(self):
        """Load configuration files on initialization."""
        self._load_configs()

    def _load_configs(self):
        """Load all configuration files."""
        config_dir = self.project_root / 'config'

        # Load system configuration
        system_config_path = config_dir / 'system_config.yaml'
        system_dict = load_yaml_config(system_config_path)
        self.system = ConfigDict(system_dict)

        # Load trading parameters
        trading_config_path = config_dir / 'trading_params.yaml'
        trading_dict = load_yaml_config(trading_config_path)
        self.trading = ConfigDict(trading_dict)

        logger.info("Configuration loaded successfully")
        logger.debug(f"Project root: {self.project_root}")

    def reload(self):
        """Reload all configuration files."""
        logger.info("Reloading configuration...")
        self._load_configs()

    # Convenience accessors for commonly used config sections

    @property
    def ib(self) -> ConfigDict:
        """Interactive Brokers configuration."""
        return self.system.ib

    @property
    def database(self) -> ConfigDict:
        """Database configuration."""
        return self.system.database

    @property
    def logging_config(self) -> ConfigDict:
        """Logging configuration."""
        return self.system.logging

    @property
    def storage(self) -> ConfigDict:
        """Storage configuration."""
        return self.system.storage

    @property
    def universe(self) -> ConfigDict:
        """Universe configuration."""
        return self.trading.universe

    @property
    def timeframes(self) -> ConfigDict:
        """Timeframe configuration."""
        return self.trading.timeframes

    @property
    def indicators(self) -> ConfigDict:
        """Indicator parameters."""
        return self.trading.indicators

    @property
    def sabr20(self) -> ConfigDict:
        """SABR20 scoring configuration."""
        return self.trading.sabr20

    @property
    def screening(self) -> ConfigDict:
        """Screening configuration."""
        return self.trading.screening

    @property
    def regime(self) -> ConfigDict:
        """Regime analysis configuration."""
        return self.trading.regime

    @property
    def performance(self) -> ConfigDict:
        """Performance targets."""
        return self.trading.performance

    def get(self, path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation path.

        Parameters:
        -----------
        path : str
            Dot-separated path (e.g., 'system.ib.host' or 'trading.universe.min_price')
        default : Any
            Default value if path not found

        Returns:
        --------
        Any : Configuration value or default

        Examples:
        ---------
        >>> config.get('system.ib.port')
        7497
        >>> config.get('trading.sabr20.weights.setup_strength')
        0.30
        """
        parts = path.split('.')

        # Determine root (system or trading)
        if parts[0] == 'system':
            current = self.system
            parts = parts[1:]
        elif parts[0] == 'trading':
            current = self.trading
            parts = parts[1:]
        else:
            # Try both
            try:
                return self.get(f'system.{path}', default)
            except (KeyError, AttributeError):
                try:
                    return self.get(f'trading.{path}', default)
                except (KeyError, AttributeError):
                    return default

        # Navigate path
        for part in parts:
            try:
                current = current[part]
            except (KeyError, TypeError):
                return default

        return current


# Global configuration instance
config = Config()


# Convenience function for external imports
def get_config() -> Config:
    """Get global configuration instance."""
    return config


if __name__ == '__main__':
    # Test configuration loading
    print("=== Configuration Test ===")
    print(f"Project root: {config.project_root}")
    print(f"IB host: {config.ib.host}")
    print(f"IB port: {config.ib.port}")
    print(f"Universe min price: {config.universe.min_price}")
    print(f"SABR20 setup strength weight: {config.sabr20.weights.setup_strength}")
    print(f"Database type: {config.database.type}")
    print("\n=== Using get() method ===")
    print(f"system.ib.host: {config.get('system.ib.host')}")
    print(f"trading.indicators.bollinger_bands.period: {config.get('trading.indicators.bollinger_bands.period')}")
    print(f"Non-existent key: {config.get('does.not.exist', 'DEFAULT')}")
