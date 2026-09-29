"""
Database Module for SQLite storage of metrics, incidents, logs, and services.
"""

import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from config_manager import config_manager


from contextlib import contextmanager

class DatabaseManager:
    """Manages SQLite connections and table operations for server monitoring."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config_manager.db_path
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def get_connection(self):
        """Yields a database connection with dictionary-like row factory and closes it on exit."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        """Initializes SQLite schema and creates all required tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. System Metrics Table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    cpu REAL NOT NULL,
                    memory REAL NOT NULL,
                    disk REAL NOT NULL,
                    load_average REAL NOT NULL,
                    process_count INTEGER NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )

            # 2. Network Metrics Table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS network_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    host TEXT NOT NULL,
                    reachable INTEGER NOT NULL,
                    latency REAL,
                    status TEXT NOT NULL
                )
                """
            )

            # 3. Port Checks Table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS port_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    host TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    is_open INTEGER NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )

            # 4. Service Status Table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS service_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    service TEXT NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )

            # 5. Incidents Table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    incident_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    message TEXT NOT NULL,
                    recovery_attempted INTEGER NOT NULL DEFAULT 0,
                    recovery_status TEXT NOT NULL DEFAULT 'N/A'
                )
                """
            )

            # 6. Log Events Table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS log_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL
                )
                """
            )

            # Create indices for fast dashboard queries
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_sys_time ON system_metrics(timestamp)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_inc_time ON incidents(timestamp)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_log_time ON log_events(timestamp)"
            )

            conn.commit()

    @staticmethod
    def current_iso_timestamp() -> str:
        """Returns the current UTC ISO timestamp string."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # ---------------- INSERTION METHODS ---------------- #

    def save_system_metrics(
        self,
        cpu: float,
        memory: float,
        disk: float,
        load_average: float,
        process_count: int,
        status: str,
        timestamp: Optional[str] = None
    ) -> int:
        """Inserts system resource utilization metrics."""
        ts = timestamp or self.current_iso_timestamp()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO system_metrics (timestamp, cpu, memory, disk, load_average, process_count, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (ts, round(cpu, 2), round(memory, 2), round(disk, 2), round(load_average, 2), process_count, status),
            )
            conn.commit()
            return cursor.lastrowid

    def save_network_metric(
        self,
        host: str,
        reachable: bool,
        latency: Optional[float],
        status: str,
        timestamp: Optional[str] = None
    ) -> int:
        """Inserts network ping result."""
        ts = timestamp or self.current_iso_timestamp()
        latency_val = round(latency, 2) if latency is not None else None
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO network_metrics (timestamp, host, reachable, latency, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (ts, host, 1 if reachable else 0, latency_val, status),
            )
            conn.commit()
            return cursor.lastrowid

    def save_port_check(
        self,
        host: str,
        port: int,
        is_open: bool,
        status: str,
        timestamp: Optional[str] = None
    ) -> int:
        """Inserts TCP port availability check."""
        ts = timestamp or self.current_iso_timestamp()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO port_checks (timestamp, host, port, is_open, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (ts, host, port, 1 if is_open else 0, status),
            )
            conn.commit()
            return cursor.lastrowid

    def save_service_status(
        self,
        service: str,
        status: str,
        timestamp: Optional[str] = None
    ) -> int:
        """Inserts systemd service status."""
        ts = timestamp or self.current_iso_timestamp()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO service_status (timestamp, service, status)
                VALUES (?, ?, ?)
                """,
                (ts, service, status),
            )
            conn.commit()
            return cursor.lastrowid

    def save_incident(
        self,
        incident_type: str,
        severity: str,
        resource: str,
        message: str,
        recovery_attempted: bool = False,
        recovery_status: str = "N/A",
        timestamp: Optional[str] = None
    ) -> int:
        """Inserts detected incident record."""
        ts = timestamp or self.current_iso_timestamp()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO incidents (
                    timestamp, incident_type, severity, resource, message,
                    recovery_attempted, recovery_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ts,
                    incident_type,
                    severity.upper(),
                    resource,
                    message,
                    1 if recovery_attempted else 0,
                    recovery_status,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def save_log_event(
        self,
        source: str,
        severity: str,
        message: str,
        timestamp: Optional[str] = None
    ) -> int:
        """Inserts anomalous log event."""
        ts = timestamp or self.current_iso_timestamp()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO log_events (timestamp, source, severity, message)
                VALUES (?, ?, ?, ?)
                """,
                (ts, source, severity.upper(), message),
            )
            conn.commit()
            return cursor.lastrowid

    # ---------------- QUERY METHODS FOR DASHBOARD ---------------- #

    def get_recent_system_metrics(self, hours: Optional[int] = 24, limit: int = 1000) -> List[Dict[str, Any]]:
        """Retrieves system metrics for dashboard charts."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if hours:
                query = """
                    SELECT * FROM system_metrics
                    WHERE timestamp >= datetime('now', ?)
                    ORDER BY timestamp ASC
                    LIMIT ?
                """
                cursor.execute(query, (f"-{hours} hours", limit))
            else:
                query = "SELECT * FROM system_metrics ORDER BY timestamp ASC LIMIT ?"
                cursor.execute(query, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_latest_system_metric(self) -> Optional[Dict[str, Any]]:
        """Retrieves the single most recent system metric."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM system_metrics ORDER BY timestamp DESC, id DESC LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_latest_service_statuses(self) -> List[Dict[str, Any]]:
        """Retrieves the latest status for each monitored service."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Uses subquery to find latest record per service
            cursor.execute(
                """
                SELECT s1.* FROM service_status s1
                INNER JOIN (
                    SELECT service, MAX(id) as max_id
                    FROM service_status
                    GROUP BY service
                ) s2 ON s1.id = s2.max_id
                ORDER BY s1.service ASC
                """
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_latest_network_metrics(self) -> List[Dict[str, Any]]:
        """Retrieves the latest network reachability result for each host."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT n1.* FROM network_metrics n1
                INNER JOIN (
                    SELECT host, MAX(id) as max_id
                    FROM network_metrics
                    GROUP BY host
                ) n2 ON n1.id = n2.max_id
                ORDER BY n1.host ASC
                """
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_latest_port_checks(self) -> List[Dict[str, Any]]:
        """Retrieves the latest status for each checked TCP port."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT p1.* FROM port_checks p1
                INNER JOIN (
                    SELECT host, port, MAX(id) as max_id
                    FROM port_checks
                    GROUP BY host, port
                ) p2 ON p1.id = p2.max_id
                ORDER BY p1.port ASC
                """
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_incidents(
        self,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieves incident history with optional severity filtering."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if severity and severity.upper() != "ALL":
                cursor.execute(
                    """
                    SELECT * FROM incidents
                    WHERE severity = ?
                    ORDER BY timestamp DESC, id DESC
                    LIMIT ?
                    """,
                    (severity.upper(), limit),
                )
            else:
                cursor.execute(
                    "SELECT * FROM incidents ORDER BY timestamp DESC, id DESC LIMIT ?",
                    (limit,),
                )
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_log_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves anomalous log events."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM log_events ORDER BY timestamp DESC, id DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]


# Singleton instance
db_manager = DatabaseManager()
