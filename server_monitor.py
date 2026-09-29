#!/usr/bin/env python3
"""
Automated Linux Server Monitoring & Incident Alert System
Main Orchestrator Module.

Coordinates metrics collection, service checks, network probes, log analysis,
incident detection, automated recovery, database recording, and terminal reporting.
"""

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Ensure server-monitoring directory is in Python path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from alert_manager import alert_manager
from config_manager import config_manager
from database import db_manager
from log_monitor import log_monitor, setup_logger
from network_monitor import network_monitor
from recovery_manager import recovery_manager
from service_monitor import service_monitor
from system_monitor import system_monitor

logger = setup_logger()


class ServerMonitorOrchestrator:
    """Orchestrates the entire server monitoring, alerting, and auto-healing cycle."""

    def __init__(self):
        self.config = config_manager
        self.db = db_manager

    def run_cycle(self) -> Dict[str, Any]:
        """
        Executes a complete monitoring cycle in sequential order:
        1. Collect system metrics & processes
        2. Inspect configured system services
        3. Probe network connectivity & latency
        4. Test TCP port reachability
        5. Scan recent log entries
        6. Evaluate thresholds and detect incidents
        7. Trigger auto-recovery for degraded services
        8. Persist all findings to SQLite database
        9. Render clear terminal status report
        """
        start_time = datetime.now(timezone.utc)
        timestamp_str = start_time.strftime("%Y-%m-%d %H:%M:%S UTC")

        incidents_detected: List[Dict[str, Any]] = []
        overall_status = "HEALTHY"

        # ---------------- 1. System Metrics Collection ---------------- #
        sys_metrics = system_monitor.collect_all_metrics()
        cpu_pct = sys_metrics["cpu_percent"]
        mem_pct = sys_metrics["memory_percent"]
        disk_pct = sys_metrics["disk_percent"]
        load_avg = sys_metrics["load_1m"]
        proc_count = sys_metrics["process_count"]

        # Thresholds from config.json
        thresholds = self.config.system_thresholds
        cpu_limit = thresholds.get("cpu_threshold_percent", 80.0)
        mem_limit = thresholds.get("memory_threshold_percent", 80.0)
        disk_limit = thresholds.get("disk_threshold_percent", 80.0)
        load_limit = thresholds.get("load_threshold", 4.0)

        # Evaluate System Resource Incidents
        sys_status = "OK"
        if cpu_pct > cpu_limit:
            sev = "CRITICAL" if cpu_pct > 92 else "WARNING"
            incidents_detected.append(
                {
                    "type": "High CPU Utilization",
                    "severity": sev,
                    "resource": "CPU",
                    "message": f"CPU usage is {cpu_pct}% (threshold: {cpu_limit}%)",
                }
            )
            sys_status = sev

        if mem_pct > mem_limit:
            sev = "CRITICAL" if mem_pct > 92 else "WARNING"
            incidents_detected.append(
                {
                    "type": "High Memory Utilization",
                    "severity": sev,
                    "resource": "Memory",
                    "message": f"Memory usage is {mem_pct}% ({sys_metrics['memory_used_gb']}/{sys_metrics['memory_total_gb']} GB, threshold: {mem_limit}%)",
                }
            )
            sys_status = "CRITICAL" if sev == "CRITICAL" else (sys_status if sys_status == "CRITICAL" else sev)

        if disk_pct > disk_limit:
            sev = "CRITICAL" if disk_pct > 92 else "WARNING"
            incidents_detected.append(
                {
                    "type": "High Disk Utilization",
                    "severity": sev,
                    "resource": "Disk",
                    "message": f"Disk usage is {disk_pct}% ({sys_metrics['disk_used_gb']}/{sys_metrics['disk_total_gb']} GB, threshold: {disk_limit}%)",
                }
            )
            sys_status = "CRITICAL" if sev == "CRITICAL" else (sys_status if sys_status == "CRITICAL" else sev)

        if load_avg > load_limit:
            incidents_detected.append(
                {
                    "type": "Elevated System Load",
                    "severity": "WARNING",
                    "resource": "System Load",
                    "message": f"1-minute load average is {load_avg} (threshold: {load_limit})",
                }
            )
            if sys_status == "OK":
                sys_status = "WARNING"

        # Save system metrics to SQLite
        self.db.save_system_metrics(
            cpu=cpu_pct,
            memory=mem_pct,
            disk=disk_pct,
            load_average=load_avg,
            process_count=proc_count,
            status=sys_status,
            timestamp=timestamp_str,
        )

        # ---------------- 2. Service Monitoring & Auto-Recovery ---------------- #
        service_results = []
        for svc_name in self.config.services_to_monitor:
            svc_info = service_monitor.check_service(svc_name)
            svc_status = svc_info["status"]
            recovery_attempted = False
            recovery_status = "N/A"

            # Check if service is unhealthy
            if svc_status in ("inactive", "failed"):
                incident_msg = f"Service '{svc_name}' is currently {svc_status}"

                # Trigger Auto-Recovery if enabled
                if self.config.is_auto_restart_enabled:
                    logger.warning(f"Initiating auto-recovery for down service: {svc_name}")
                    rec_result = recovery_manager.attempt_service_recovery(svc_name)
                    recovery_attempted = rec_result["restart_attempted"]
                    recovery_status = (
                        "SUCCESS" if rec_result["restart_successful"] else f"FAILED ({rec_result['final_status']})"
                    )
                    # Update status if recovered
                    if rec_result["restart_successful"]:
                        svc_status = "active (recovered)"
                        svc_info["status"] = svc_status
                        svc_info["is_running"] = True

                incidents_detected.append(
                    {
                        "type": "Service Down",
                        "severity": "CRITICAL" if not recovery_attempted or "FAILED" in recovery_status else "WARNING",
                        "resource": f"Service: {svc_name}",
                        "message": incident_msg,
                        "recovery_attempted": recovery_attempted,
                        "recovery_status": recovery_status,
                    }
                )

            # Persist service status
            self.db.save_service_status(
                service=svc_name,
                status=svc_status,
                timestamp=timestamp_str,
            )
            service_results.append(svc_info)

        # ---------------- 3. Network Monitoring ---------------- #
        net_cfg = self.config.network_config
        lat_warn = net_cfg.get("latency_warning_threshold_ms", 100.0)
        lat_crit = net_cfg.get("latency_critical_threshold_ms", 300.0)

        network_results = []
        for host in self.config.monitored_hosts:
            net_info = network_monitor.ping_host(host)
            reachable = net_info["reachable"]
            lat = net_info["latency_ms"]
            status = net_info["status"]

            if not reachable:
                status = "DOWN"
                incidents_detected.append(
                    {
                        "type": "Host Unreachable",
                        "severity": "CRITICAL",
                        "resource": f"Network: {host}",
                        "message": f"Host {host} is unreachable via ICMP ping",
                    }
                )
            elif lat is not None:
                if lat > lat_crit:
                    status = "CRITICAL_LATENCY"
                    incidents_detected.append(
                        {
                            "type": "High Network Latency",
                            "severity": "CRITICAL",
                            "resource": f"Network: {host}",
                            "message": f"Latency to {host} is {lat} ms (critical limit: {lat_crit} ms)",
                        }
                    )
                elif lat > lat_warn:
                    status = "HIGH_LATENCY"
                    incidents_detected.append(
                        {
                            "type": "Elevated Network Latency",
                            "severity": "WARNING",
                            "resource": f"Network: {host}",
                            "message": f"Latency to {host} is {lat} ms (warning limit: {lat_warn} ms)",
                        }
                    )

            self.db.save_network_metric(
                host=host,
                reachable=reachable,
                latency=lat,
                status=status,
                timestamp=timestamp_str,
            )
            network_results.append(net_info)

        # ---------------- 4. Port Monitoring ---------------- #
        port_results = []
        for port_item in self.config.monitored_ports:
            p_host = port_item.get("host", "127.0.0.1")
            p_num = port_item.get("port", 80)
            p_name = port_item.get("service_name", "")

            port_info = network_monitor.check_port(p_host, p_num, p_name)
            is_open = port_info["is_open"]
            p_status = port_info["status"]

            if not is_open:
                # Ports like SSH (22) or Web (80) being closed is a notable incident
                incidents_detected.append(
                    {
                        "type": "Port Unavailable",
                        "severity": "WARNING",
                        "resource": f"Port: {p_host}:{p_num} ({p_name})",
                        "message": f"Port {p_num} ({p_name}) on {p_host} is closed or unreachable",
                    }
                )

            self.db.save_port_check(
                host=p_host,
                port=p_num,
                is_open=is_open,
                status=p_status,
                timestamp=timestamp_str,
            )
            port_results.append(port_info)

        # ---------------- 5. Log Monitoring ---------------- #
        log_events = log_monitor.scan_all_logs()
        for ev in log_events:
            self.db.save_log_event(
                source=ev["source"],
                severity=ev["severity"],
                message=ev["message"],
                timestamp=timestamp_str,
            )
            # Escalate critical log events to incidents
            if ev["severity"] in ("CRITICAL", "ERROR"):
                incidents_detected.append(
                    {
                        "type": "Log Error Detected",
                        "severity": ev["severity"],
                        "resource": f"Log: {ev['source']}",
                        "message": f"Pattern '{ev['keyword']}' matched: {ev['message'][:120]}",
                    }
                )

        # ---------------- 6. Incident Dispatch & Overall Status ---------------- #
        has_critical = any(inc["severity"] == "CRITICAL" for inc in incidents_detected)
        has_warning = any(inc["severity"] == "WARNING" for inc in incidents_detected)

        if has_critical:
            overall_status = "CRITICAL"
        elif has_warning:
            overall_status = "WARNING"
        else:
            overall_status = "HEALTHY"

        for inc in incidents_detected:
            alert_manager.notify(
                incident_type=inc["type"],
                severity=inc["severity"],
                resource=inc["resource"],
                message=inc["message"],
                recovery_attempted=inc.get("recovery_attempted", False),
                recovery_status=inc.get("recovery_status", "N/A"),
            )

        # ---------------- 7. Render Terminal Report ---------------- #
        self._print_terminal_report(
            timestamp=timestamp_str,
            sys_metrics=sys_metrics,
            thresholds=thresholds,
            services=service_results,
            network=network_results,
            ports=port_results,
            log_events=log_events,
            overall_status=overall_status,
        )

        return {
            "timestamp": timestamp_str,
            "overall_status": overall_status,
            "incidents_count": len(incidents_detected),
            "system_metrics": sys_metrics,
            "services": service_results,
            "network": network_results,
            "ports": port_results,
            "log_events": log_events,
        }

    def _print_terminal_report(
        self,
        timestamp: str,
        sys_metrics: dict,
        thresholds: dict,
        services: list,
        network: list,
        ports: list,
        log_events: list,
        overall_status: str,
    ) -> None:
        """Prints the clean formatted terminal summary requested in specifications."""
        cpu = sys_metrics["cpu_percent"]
        mem = sys_metrics["memory_percent"]
        disk = sys_metrics["disk_percent"]
        load = sys_metrics["load_1m"]

        cpu_tag = "[CRITICAL]" if cpu > 90 else ("[WARNING]" if cpu > thresholds.get("cpu_threshold_percent", 80) else "[OK]")
        mem_tag = "[CRITICAL]" if mem > 90 else ("[WARNING]" if mem > thresholds.get("memory_threshold_percent", 80) else "[OK]")
        disk_tag = "[CRITICAL]" if disk > 90 else ("[WARNING]" if disk > thresholds.get("disk_threshold_percent", 80) else "[OK]")
        load_tag = "[WARNING]" if load > thresholds.get("load_threshold", 4.0) else "[OK]"

        print("\n=============================================")
        print("LINUX SERVER MONITORING REPORT")
        print("=============================================")
        print(f"Timestamp: {timestamp}\n")

        print("SYSTEM HEALTH")
        print(f"CPU: {cpu}% {cpu_tag}")
        print(f"Memory: {mem}% {mem_tag}")
        print(f"Disk: {disk}% {disk_tag}")
        print(f"Load: {load} {load_tag}\n")

        print("SERVICES")
        if not services:
            print("No services configured")
        else:
            for s in services:
                status_str = s["status"]
                tag = "[OK]" if "active" in status_str else (
                    "[RECOVERED]" if "recovered" in status_str else (
                        "[UNKNOWN]" if status_str == "unknown" else "[CRITICAL]"
                    )
                )
                print(f"{s['service']}: {status_str} {tag}")
        print()

        print("NETWORK")
        if not network:
            print("No network hosts configured")
        else:
            for n in network:
                lat_str = f"{n['latency_ms']} ms" if n["latency_ms"] is not None else "TIMEOUT"
                tag = "[OK]" if n["reachable"] else "[CRITICAL]"
                print(f"{n['host']}: {n['status']} - {lat_str} {tag}")
        print()

        print("PORTS")
        if not ports:
            print("No ports configured")
        else:
            for p in ports:
                tag = "[OK]" if p["is_open"] else "[WARNING]"
                print(f"{p['port']} ({p['service_name']}): {p['status']} {tag}")
        print()

        print("LOG CHECK")
        critical_logs = [e for e in log_events if e["severity"] in ("CRITICAL", "ERROR")]
        if critical_logs:
            print(f"Found {len(critical_logs)} critical/error entries in monitored logs [WARNING]")
            for clog in critical_logs[:3]:
                print(f"  * [{clog['source']}] {clog['message'][:80]}")
        else:
            print("No critical errors found [OK]")
        print()

        print("OVERALL STATUS")
        print(f"{overall_status}")
        print("=============================================\n")


def main():
    """CLI entry point for server monitoring."""
    parser = argparse.ArgumentParser(
        description="Automated Linux Server Monitoring & Incident Alert System"
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run continuously in background daemon mode with configured interval",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Custom interval in seconds for continuous mode (overrides config.json)",
    )
    args = parser.parse_args()

    orchestrator = ServerMonitorOrchestrator()

    if args.daemon:
        interval = args.interval or config_manager.config["monitoring"]["interval_seconds"]
        logger.info(f"Starting monitoring service in daemon mode (interval: {interval}s)...")
        print(f"Monitoring service started. Running every {interval} seconds. Press Ctrl+C to stop.\n")
        try:
            while True:
                orchestrator.run_cycle()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user.")
            sys.exit(0)
    else:
        # Default single-run execution (ideal for cron or one-time checks)
        orchestrator.run_cycle()


if __name__ == "__main__":
    main()
