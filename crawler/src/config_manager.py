"""
config_manager.py

Singleton configuration manager to load and provide configurations across modules.
"""

import json
import os

class ConfigManager:
    """
    Singleton class loading configurations from a JSON file.
    """
    _instance = None

    def __new__(cls, config_path=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config(config_path)
        return cls._instance

    def _load_config(self, path=None):
        """
        Load configuration from JSON file.

        Args:
            path (str): Path to config file. Defaults to '../config/config.json'.

        Raises:
            FileNotFoundError: If config file is missing.
        """
        if not path:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base_dir, "..", "config", "config.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

    def get(self, key, default=None):
        """
        Get configuration value.

        Args:
            key (str): Configuration key.
            default: Default value if key not found.

        Returns:
            Configuration value or default.
        """
        return self.config.get(key, default)

    def get_crawler_config(self, name):
        """
        Get specific crawler configuration.

        Args:
            name (str): Crawler name.

        Returns:
            dict: Crawler-specific configuration.
        """
        return self.config.get("crawlers", {}).get(name, {})
