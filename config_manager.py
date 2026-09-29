"""
Configuration Manager Module
Handles loading, validation, and safe retrieval of monitoring configuration.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

# Define the base directory of the project
BASE_DIR = Path(__file__).resolve().parent

DEFAULT_CONFIG: Dict[str, Any] = {
    "monitoring": {
        "interval_seconds": 300,
        "system": {
            "cpu_threshold_percent": 80.0,
            "memory_threshold_percent": 80.0,
            "disk_threshold_percent": 80.0,
            "load_threshold": 4.0
        },
        "network": {
            "timeout_seconds": 3,
            "latency_warning_threshold_ms": 100.0,
            "latency_critical_threshold_ms": 300.0,
            "hosts": ["8.8.8.8", "google.com"],
            "ports": [
                {"host": "127.0.0.1", "port": 22, "service_name": "SSH"},
                {"host": "127.0.0.1", "port": 80, "service_name": "HTTP"},
                {"host": "127.0.0.1", "port": 443, "service_name": "HTTPS"}
            ]
        },
        "services": {
            "auto_restart_enabled": True,
            "service_list": ["nginx", "ssh", "cron"]
        },
        "logs": {
            "files_to_monitor": [
                "/var/log/nginx/error.log",
                "/var/log/syslog",
                "logs/sample_app.log"
            ],
            "error_keywords": ["ERROR", "WARNING", "CRITICAL", "FAILED", "TIMEOUT"],
            "max_lines_to_read": 100
        }
    },
    "database": {
        "path": "data/monitoring.db"
    },
    "logging": {
        "file_path": "logs/monitor.log",
        "level": "INFO"
    }
}


class ConfigManager:
    """Manages application configuration loaded from a JSON file."""

    def __init__(self, config_file: str = "config/config.json"):
        self.config_path = self.resolve_path(config_file)
        self.config = self.load_config()

    @staticmethod
    def resolve_path(file_path: str) -> Path:
        """Resolves relative file paths against the project root directory."""
        path = Path(file_path)
        if not path.is_absolute():
            return (BASE_DIR / path).resolve()
        return path

    def load_config(self) -> Dict[str, Any]:
        """Loads configuration from JSON file or falls back to defaults."""
        if not self.config_path.exists():
            logging.warning(
                f"Config file not found at {self.config_path}. Using default configuration."
            )
            return DEFAULT_CONFIG.copy()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                return self._merge_defaults(loaded, DEFAULT_CONFIG)
        except Exception as e:
            logging.error(f"Failed to parse config file: {e}. Falling back to defaults.")
            return DEFAULT_CONFIG.copy()

    def _merge_defaults(self, loaded: dict, default: dict) -> dict:
        """Recursively merges loaded config with defaults to ensure all keys exist."""
        result = default.copy()
        for k, v in loaded.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = self._merge_defaults(v, result[k])
            else:
                result[k] = v
        return result

    @property
    def system_thresholds(self) -> Dict[str, float]:
        """Returns CPU, Memory, Disk, and Load thresholds."""
        return self.config["monitoring"]["system"]

    @property
    def network_config(self) -> Dict[str, Any]:
        """Returns network timeout, latency thresholds, hosts, and ports."""
        return self.config["monitoring"]["network"]

    @property
    def monitored_hosts(self) -> List[str]:
        """List of hosts to ping."""
        return self.config["monitoring"]["network"]["hosts"]

    @property
    def monitored_ports(self) -> List[Dict[str, Any]]:
        """List of ports to check."""
        return self.config["monitoring"]["network"]["ports"]

    @property
    def services_to_monitor(self) -> List[str]:
        """List of services to monitor."""
        return self.config["monitoring"]["services"]["service_list"]

    @property
    def is_auto_restart_enabled(self) -> bool:
        """Whether auto-restart is enabled for failed services."""
        return bool(self.config["monitoring"]["services"]["auto_restart_enabled"])

    @property
    def logs_to_monitor(self) -> List[str]:
        """List of log files to inspect."""
        return self.config["monitoring"]["logs"]["files_to_monitor"]

    @property
    def error_keywords(self) -> List[str]:
        """Keywords indicating log errors or warnings."""
        return self.config["monitoring"]["logs"]["error_keywords"]

    @property
    def max_lines_to_read(self) -> int:
        """Max recent lines to inspect per log file."""
        return self.config["monitoring"]["logs"].get("max_lines_to_read", 100)

    @property
    def db_path(self) -> Path:
        """Path to SQLite database."""
        return self.resolve_path(self.config["database"]["path"])

    @property
    def log_path(self) -> Path:
        """Path to application monitor.log."""
        return self.resolve_path(self.config["logging"]["file_path"])


# Singleton instance for quick access
config_manager = ConfigManager()
