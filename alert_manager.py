"""
Alert Manager Module
Dispatches monitoring alerts to terminal, logs, SQLite, and optional SMTP email.
Includes duplicate suppression to prevent alert fatigue.
"""

import os
import smtplib
import time
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional
from database import db_manager
from log_monitor import setup_logger

logger = setup_logger()

# ANSI Color Codes for clear terminal alerts
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


class AlertManager:
    """Manages dispatching and deduplicating incident alerts across multiple channels."""

    def __init__(self, cooldown_seconds: int = 600):
        # Maps (incident_type, resource, severity) -> last_alerted_epoch_seconds
        self.recent_alerts: Dict[str, float] = {}
        self.cooldown_seconds = cooldown_seconds

    def should_suppress_duplicate(self, incident_type: str, resource: str, severity: str) -> bool:
        """
        Suppresses identical alerts if triggered within the cooldown window (default 10 min)
        to prevent alert flooding/fatigue.
        """
        key = f"{incident_type}:{resource}:{severity.upper()}"
        now = time.time()
        last_time = self.recent_alerts.get(key)

        if last_time and (now - last_time < self.cooldown_seconds):
            return True

        self.recent_alerts[key] = now
        return False

    def notify(
        self,
        incident_type: str,
        severity: str,
        resource: str,
        message: str,
        recovery_attempted: bool = False,
        recovery_status: str = "N/A",
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Orchestrates an alert notification:
        1. Checks deduplication
        2. Logs to monitor.log
        3. Saves incident to SQLite database
        4. Prints formatted terminal alert
        5. Attempts email dispatch if SMTP environment variables are present
        """
        severity_clean = severity.upper()
        ts_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # Deduplication check
        if not force and self.should_suppress_duplicate(incident_type, resource, severity_clean):
            logger.debug(f"Suppressed duplicate alert for {incident_type} on {resource}")
            return {
                "alerted": False,
                "suppressed": True,
                "incident_type": incident_type,
                "resource": resource,
            }

        # 1. Terminal Output with clear visual indicator
        color = RED if severity_clean == "CRITICAL" else (YELLOW if severity_clean == "WARNING" else CYAN)
        print(f"\n{color}{BOLD}>>> [ALERT - {severity_clean}] {incident_type.upper()}{RESET}")
        print(f"    Resource : {resource}")
        print(f"    Message  : {message}")
        print(f"    Timestamp: {ts_str}")
        if recovery_attempted:
            print(f"    Recovery : {recovery_status}")
        print("-" * 50)

        # 2. Python Logging to logs/monitor.log
        log_msg = f"[INCIDENT] [{severity_clean}] [{incident_type}] Resource: {resource} - {message} (Recovery: {recovery_status})"
        if severity_clean == "CRITICAL":
            logger.critical(log_msg)
        elif severity_clean == "WARNING":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        # 3. Save to SQLite database
        incident_id = db_manager.save_incident(
            incident_type=incident_type,
            severity=severity_clean,
            resource=resource,
            message=message,
            recovery_attempted=recovery_attempted,
            recovery_status=recovery_status,
        )

        # 4. Optional SMTP Email
        email_sent = self._send_email_if_configured(
            incident_type=incident_type,
            severity=severity_clean,
            resource=resource,
            message=message,
            recovery_status=recovery_status,
        )

        return {
            "alerted": True,
            "suppressed": False,
            "incident_id": incident_id,
            "incident_type": incident_type,
            "severity": severity_clean,
            "resource": resource,
            "email_sent": email_sent,
        }

    def _send_email_if_configured(
        self,
        incident_type: str,
        severity: str,
        resource: str,
        message: str,
        recovery_status: str,
    ) -> bool:
        """
        Sends an email alert via SMTP if environment variables are set.
        Safely returns False without error if not configured.
        """
        smtp_server = os.environ.get("SMTP_SERVER")
        smtp_port = os.environ.get("SMTP_PORT", "587")
        smtp_user = os.environ.get("SMTP_USERNAME")
        smtp_password = os.environ.get("SMTP_PASSWORD")
        alert_to = os.environ.get("ALERT_EMAIL_TO")

        if not (smtp_server and smtp_user and smtp_password and alert_to):
            logger.debug("SMTP environment variables not configured. Skipping email dispatch.")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[{severity}] Server Alert: {incident_type} on {resource}"
            msg["From"] = smtp_user
            msg["To"] = alert_to

            body_text = (
                f"ALERT NOTIFICATION\n"
                f"Severity: {severity}\n"
                f"Incident: {incident_type}\n"
                f"Resource: {resource}\n"
                f"Message: {message}\n"
                f"Recovery Status: {recovery_status}\n"
                f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n"
            )
            msg.attach(MIMEText(body_text, "plain"))

            with smtplib.SMTP(smtp_server, int(smtp_port), timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, alert_to.split(","), msg.as_string())

            logger.info(f"Successfully sent alert email to {alert_to}")
            return True
        except Exception as e:
            logger.error(f"Failed to send alert email: {e}")
            return False


# Singleton instance
alert_manager = AlertManager()
