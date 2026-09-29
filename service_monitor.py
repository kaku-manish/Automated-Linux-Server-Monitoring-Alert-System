"""
Service Monitoring Module
Uses systemctl to inspect system service states (active, inactive, failed, unknown).
"""

import shutil
import subprocess
from typing import Any, Dict, List, Optional
from config_manager import config_manager


class ServiceMonitor:
    """Monitors Linux systemd services using systemctl."""

    def __init__(self):
        # Check if systemctl binary is present in PATH
        self.systemctl_available = shutil.which("systemctl") is not None

    def check_service(self, service_name: str) -> Dict[str, Any]:
        """
        Queries systemctl is-active to determine service health.
        Returns:
            dict: {
                "service": str,
                "status": "active" | "inactive" | "failed" | "unknown",
                "is_running": bool,
                "details": str
            }
        """
        if not self.systemctl_available:
            return {
                "service": service_name,
                "status": "unknown",
                "is_running": False,
                "details": "systemctl utility is not available on this platform/environment",
            }

        try:
            # Run 'systemctl is-active <service_name>'
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
            )
            raw_output = result.stdout.strip().lower()

            if result.returncode == 0 and raw_output == "active":
                return {
                    "service": service_name,
                    "status": "active",
                    "is_running": True,
                    "details": "Service is running normally",
                }
            elif raw_output in ("inactive", "failed", "activating", "deactivating"):
                return {
                    "service": service_name,
                    "status": raw_output,
                    "is_running": False,
                    "details": f"Service is currently {raw_output}",
                }
            else:
                # E.g. unknown unit or load error
                stderr_text = result.stderr.strip()
                status = "failed" if "failed" in raw_output else "unknown"
                return {
                    "service": service_name,
                    "status": status,
                    "is_running": False,
                    "details": stderr_text or raw_output or "Service not loaded or unit unknown",
                }

        except subprocess.TimeoutExpired:
            return {
                "service": service_name,
                "status": "unknown",
                "is_running": False,
                "details": "systemctl command timed out",
            }
        except FileNotFoundError:
            self.systemctl_available = False
            return {
                "service": service_name,
                "status": "unknown",
                "is_running": False,
                "details": "systemctl not found",
            }
        except Exception as e:
            return {
                "service": service_name,
                "status": "unknown",
                "is_running": False,
                "details": str(e),
            }

    def check_all_services(self, service_list: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Checks status for all monitored services."""
        targets = service_list or config_manager.services_to_monitor
        return [self.check_service(svc) for svc in targets]


# Singleton instance
service_monitor = ServiceMonitor()
