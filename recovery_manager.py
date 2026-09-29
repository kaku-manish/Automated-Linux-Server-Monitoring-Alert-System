"""
Auto-Recovery Manager Module
Attempts automated service restarts for down or failed whitelisted services.
"""

import logging
import shutil
import subprocess
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from config_manager import config_manager
from service_monitor import service_monitor


class RecoveryManager:
    """Handles automated healing and verification of failed system services."""

    def __init__(self):
        self.systemctl_available = shutil.which("systemctl") is not None

    def attempt_service_recovery(self, service_name: str) -> Dict[str, Any]:
        """
        Attempts to restart a failed service if auto-restart is enabled and the service
        is on the strict whitelist in config.json.
        Waits briefly and re-checks the service to verify recovery success.
        """
        allowed_services = config_manager.services_to_monitor
        auto_restart_on = config_manager.is_auto_restart_enabled
        failure_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # 1. Whitelist Security Check
        if service_name not in allowed_services:
            return {
                "service": service_name,
                "failure_time": failure_time,
                "restart_attempted": False,
                "restart_successful": False,
                "final_status": "blocked",
                "details": f"Service '{service_name}' is not in the allowed recovery whitelist",
            }

        # 2. Config Enabled Check
        if not auto_restart_on:
            return {
                "service": service_name,
                "failure_time": failure_time,
                "restart_attempted": False,
                "restart_successful": False,
                "final_status": "disabled",
                "details": "Auto-recovery is disabled in config.json",
            }

        # 3. Environment Check
        if not self.systemctl_available:
            return {
                "service": service_name,
                "failure_time": failure_time,
                "restart_attempted": False,
                "restart_successful": False,
                "final_status": "unavailable",
                "details": "systemctl command is not available to perform restart",
            }

        # 4. Attempt Restart via systemctl
        cmd = ["sudo", "systemctl", "restart", service_name]
        logging.info(f"Attempting auto-recovery: {' '.join(cmd)}")

        try:
            restart_proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15,
            )

            # Wait briefly for service to initialize
            time.sleep(2.0)

            # Re-verify service status
            verification = service_monitor.check_service(service_name)
            is_active = verification.get("is_running", False)
            final_status = verification.get("status", "unknown")

            success = (restart_proc.returncode == 0) and is_active

            details = (
                f"Service successfully restarted and verified active"
                if success
                else f"Restart executed (code {restart_proc.returncode}), verification status: {final_status}. {restart_proc.stderr.strip()}"
            )

            if success:
                logging.info(f"[RECOVERY SUCCESS] Service {service_name} restarted successfully.")
            else:
                logging.error(f"[RECOVERY FAILED] Failed to recover service {service_name}: {details}")

            return {
                "service": service_name,
                "failure_time": failure_time,
                "restart_attempted": True,
                "restart_successful": success,
                "final_status": final_status,
                "details": details,
            }

        except subprocess.TimeoutExpired:
            return {
                "service": service_name,
                "failure_time": failure_time,
                "restart_attempted": True,
                "restart_successful": False,
                "final_status": "timeout",
                "details": f"Command '{' '.join(cmd)}' timed out",
            }
        except Exception as e:
            return {
                "service": service_name,
                "failure_time": failure_time,
                "restart_attempted": True,
                "restart_successful": False,
                "final_status": "error",
                "details": str(e),
            }


# Singleton instance
recovery_manager = RecoveryManager()
