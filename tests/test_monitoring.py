"""
Unit Tests for Linux Server Monitoring & Incident Alert System
Tests configuration, database operations, threshold evaluation, network probes, and log parsing.
"""

import os
import socket
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config_manager import ConfigManager
from database import DatabaseManager
from log_monitor import LogMonitor
from network_monitor import NetworkMonitor


class TestConfigManager(unittest.TestCase):
    """Tests loading and validation of monitoring configuration."""

    def test_default_config_loading(self):
        cm = ConfigManager()
        self.assertIn("monitoring", cm.config)
        self.assertIn("cpu_threshold_percent", cm.system_thresholds)
        self.assertGreaterEqual(cm.system_thresholds["cpu_threshold_percent"], 0)
        self.assertTrue(len(cm.monitored_hosts) > 0)
        self.assertTrue(len(cm.monitored_ports) > 0)
        self.assertTrue(len(cm.services_to_monitor) > 0)

    def test_path_resolution(self):
        resolved = ConfigManager.resolve_path("logs/monitor.log")
        self.assertTrue(resolved.is_absolute())


class TestDatabaseManager(unittest.TestCase):
    """Tests SQLite table initialization and data persistence."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_monitoring.db"
        self.db = DatabaseManager(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_and_retrieve_system_metrics(self):
        row_id = self.db.save_system_metrics(
            cpu=45.5,
            memory=60.2,
            disk=72.0,
            load_average=1.2,
            process_count=180,
            status="OK",
        )
        self.assertIsInstance(row_id, int)

        metrics = self.db.get_recent_system_metrics(hours=1)
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0]["cpu"], 45.5)
        self.assertEqual(metrics[0]["status"], "OK")

    def test_save_and_filter_incidents(self):
        self.db.save_incident(
            incident_type="Test Warning",
            severity="WARNING",
            resource="Memory",
            message="High memory test",
        )
        self.db.save_incident(
            incident_type="Test Critical",
            severity="CRITICAL",
            resource="Disk",
            message="Disk full test",
        )

        all_incidents = self.db.get_incidents(severity="ALL")
        self.assertEqual(len(all_incidents), 2)

        critical_incidents = self.db.get_incidents(severity="CRITICAL")
        self.assertEqual(len(critical_incidents), 1)
        self.assertEqual(critical_incidents[0]["resource"], "Disk")

    def test_save_service_and_network_metrics(self):
        self.db.save_service_status(service="nginx", status="active")
        services = self.db.get_latest_service_statuses()
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0]["service"], "nginx")
        self.assertEqual(services[0]["status"], "active")

        self.db.save_network_metric(host="8.8.8.8", reachable=True, latency=15.2, status="UP")
        nets = self.db.get_latest_network_metrics()
        self.assertEqual(len(nets), 1)
        self.assertEqual(nets[0]["host"], "8.8.8.8")
        self.assertEqual(nets[0]["reachable"], 1)


class TestNetworkMonitor(unittest.TestCase):
    """Tests socket port probes and reachability functions."""

    def setUp(self):
        self.nm = NetworkMonitor(timeout=1)

    def test_check_closed_port(self):
        # Port 65530 is typically unused and closed locally
        result = self.nm.check_port(host="127.0.0.1", port=65530, service_name="Unused")
        self.assertFalse(result["is_open"])
        self.assertEqual(result["status"], "CLOSED")

    def test_check_open_port(self):
        # Bind a temporary local listening socket
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind(("127.0.0.1", 0))  # 0 lets OS assign an open ephemeral port
        port = server_sock.getsockname()[1]
        server_sock.listen(1)

        try:
            result = self.nm.check_port(host="127.0.0.1", port=port, service_name="TestSocket")
            self.assertTrue(result["is_open"])
            self.assertEqual(result["status"], "OPEN")
        finally:
            server_sock.close()


class TestLogMonitor(unittest.TestCase):
    """Tests log scanning and keyword extraction."""

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(mode="w+", delete=False, encoding="utf-8")
        self.temp_file.write("2026-09-29 10:00:00 [INFO] System running normally\n")
        self.temp_file.write("2026-09-29 10:01:00 [WARNING] Disk space above 75%\n")
        self.temp_file.write("2026-09-29 10:02:00 [ERROR] Connection to database TIMEOUT\n")
        self.temp_file.write("2026-09-29 10:03:00 [CRITICAL] Core worker FAILED\n")
        self.temp_file.close()
        self.lm = LogMonitor()

    def tearDown(self):
        os.unlink(self.temp_file.name)

    def test_keyword_matching(self):
        events = self.lm.scan_file(
            file_path_str=self.temp_file.name,
            keywords=["ERROR", "WARNING", "CRITICAL", "FAILED", "TIMEOUT"],
        )
        self.assertEqual(len(events), 3)  # WARNING, ERROR (with TIMEOUT), CRITICAL (with FAILED)
        severities = [e["severity"] for e in events]
        self.assertIn("WARNING", severities)
        self.assertIn("ERROR", severities)
        self.assertIn("CRITICAL", severities)


if __name__ == "__main__":
    unittest.main()
