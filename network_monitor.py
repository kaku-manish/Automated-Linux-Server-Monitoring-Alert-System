"""
Network Monitoring Module
Performs ICMP ping reachability checks, latency measurement, and TCP port probes.
"""

import os
import re
import socket
import subprocess
import time
from typing import Any, Dict, List, Optional
from config_manager import config_manager


class NetworkMonitor:
    """Monitors host reachability, round-trip latency, and TCP port status."""

    def __init__(self, timeout: Optional[int] = None):
        self.default_timeout = timeout or config_manager.network_config.get("timeout_seconds", 3)

    def ping_host(self, host: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Pings a host once to measure reachability and round-trip latency in ms.
        Works across both Linux and Windows operating systems.
        Network errors or unreachable hosts will not crash the application.
        """
        timeout_sec = timeout or self.default_timeout
        is_windows = os.name == "nt"

        if is_windows:
            # -n 1: 1 packet, -w timeout in milliseconds
            cmd = ["ping", "-n", "1", "-w", str(int(timeout_sec * 1000)), host]
        else:
            # Linux: -c 1: 1 packet, -W timeout in seconds
            cmd = ["ping", "-c", "1", "-W", str(int(timeout_sec)), host]

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout_sec + 2,
            )
            stdout = result.stdout
            reachable = (result.returncode == 0)

            latency_ms = None
            if reachable:
                # Regex search for latency in stdout
                # Matches: "time=14.2 ms", "time=14ms", "time<1ms", "Time=20ms"
                match = re.search(r"time[=<]([0-9.]+)\s*ms", stdout, re.IGNORECASE)
                if match:
                    latency_ms = float(match.group(1))
                else:
                    # Linux summary format: rtt min/avg/max/mdev = 12.1/14.5/16.2/1.1 ms
                    summary_match = re.search(r"= [0-9.]+/([0-9.]+)/", stdout)
                    if summary_match:
                        latency_ms = float(summary_match.group(1))
                    else:
                        # Fallback to total wall-clock elapsed time
                        latency_ms = round((time.time() - start_time) * 1000, 2)

            status = "UP" if reachable else "DOWN"
            return {
                "host": host,
                "reachable": reachable,
                "latency_ms": round(latency_ms, 2) if latency_ms is not None else None,
                "status": status,
                "error": None if reachable else f"Ping failed with returncode {result.returncode}",
            }
        except subprocess.TimeoutExpired:
            return {
                "host": host,
                "reachable": False,
                "latency_ms": None,
                "status": "DOWN",
                "error": f"Ping request timed out after {timeout_sec}s",
            }
        except Exception as e:
            return {
                "host": host,
                "reachable": False,
                "latency_ms": None,
                "status": "DOWN",
                "error": str(e),
            }

    def check_port(self, host: str, port: int, service_name: str = "", timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Probes a TCP port using a socket connection.
        Returns OPEN or CLOSED status.
        """
        timeout_sec = timeout or self.default_timeout
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout_sec)

        try:
            # Resolve localhost or hostname if needed
            ip_target = host if host not in ("localhost", "127.0.0.1") else "127.0.0.1"
            res = sock.connect_ex((ip_target, int(port)))
            is_open = (res == 0)
            status = "OPEN" if is_open else "CLOSED"

            return {
                "host": host,
                "port": int(port),
                "service_name": service_name or f"Port-{port}",
                "is_open": is_open,
                "status": status,
                "error": None if is_open else f"Connection refused or timed out (errno: {res})",
            }
        except Exception as e:
            return {
                "host": host,
                "port": int(port),
                "service_name": service_name or f"Port-{port}",
                "is_open": False,
                "status": "CLOSED",
                "error": str(e),
            }
        finally:
            try:
                sock.close()
            except Exception:
                pass

    def check_all_hosts(self, hosts: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Checks reachability and latency for all configured hosts."""
        target_hosts = hosts or config_manager.monitored_hosts
        return [self.ping_host(host) for host in target_hosts]

    def check_all_ports(self, port_configs: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Checks TCP port availability for all configured ports."""
        configs = port_configs or config_manager.monitored_ports
        results = []
        for item in configs:
            results.append(
                self.check_port(
                    host=item.get("host", "127.0.0.1"),
                    port=item.get("port", 80),
                    service_name=item.get("service_name", ""),
                )
            )
        return results


# Singleton instance
network_monitor = NetworkMonitor()
