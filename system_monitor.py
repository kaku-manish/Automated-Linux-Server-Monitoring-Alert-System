"""
System Monitoring Module
Uses psutil to collect CPU, memory, disk, load, uptime, and top processes.
"""

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
import psutil


class SystemMonitor:
    """Collects operating system health metrics and top running processes."""

    def __init__(self):
        # Determine root disk path based on OS ('/' for Linux/Unix, anchor for Windows)
        self.root_path = "/" if os.name != "nt" else Path.cwd().anchor

    def get_cpu_metrics(self) -> Dict[str, Any]:
        """Collects overall CPU usage percentage and core counts."""
        try:
            # interval=1 allows psutil to accurately calculate CPU percentage over 1 second
            cpu_percent = psutil.cpu_percent(interval=1.0)
            logical_cores = psutil.cpu_count(logical=True) or 1
            physical_cores = psutil.cpu_count(logical=False) or 1
            return {
                "cpu_percent": float(cpu_percent),
                "logical_cores": logical_cores,
                "physical_cores": physical_cores,
            }
        except Exception as e:
            return {
                "cpu_percent": 0.0,
                "logical_cores": 1,
                "physical_cores": 1,
                "error": str(e),
            }

    def get_memory_metrics(self) -> Dict[str, Any]:
        """Collects RAM and swap usage."""
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            return {
                "memory_percent": float(mem.percent),
                "total_gb": round(mem.total / (1024**3), 2),
                "used_gb": round(mem.used / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "swap_percent": float(swap.percent),
            }
        except Exception as e:
            return {
                "memory_percent": 0.0,
                "total_gb": 0.0,
                "used_gb": 0.0,
                "available_gb": 0.0,
                "swap_percent": 0.0,
                "error": str(e),
            }

    def get_disk_metrics(self) -> Dict[str, Any]:
        """Collects primary disk usage."""
        try:
            usage = psutil.disk_usage(self.root_path)
            return {
                "disk_percent": float(usage.percent),
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "mount_point": self.root_path,
            }
        except Exception as e:
            return {
                "disk_percent": 0.0,
                "total_gb": 0.0,
                "used_gb": 0.0,
                "free_gb": 0.0,
                "mount_point": self.root_path,
                "error": str(e),
            }

    def get_system_load(self) -> Dict[str, Any]:
        """
        Retrieves 1, 5, and 15-minute system load averages.
        Handles platform differences gracefully.
        """
        try:
            if hasattr(os, "getloadavg"):
                load1, load5, load15 = os.getloadavg()
            elif hasattr(psutil, "getloadavg"):
                load1, load5, load15 = psutil.getloadavg()
            else:
                # Windows fallback estimation
                cpu = psutil.cpu_percent(interval=None)
                cores = psutil.cpu_count() or 1
                estimated = round((cpu / 100.0) * cores, 2)
                load1, load5, load15 = estimated, estimated, estimated

            return {
                "load_1m": round(load1, 2),
                "load_5m": round(load5, 2),
                "load_15m": round(load15, 2),
            }
        except Exception as e:
            return {
                "load_1m": 0.0,
                "load_5m": 0.0,
                "load_15m": 0.0,
                "error": str(e),
            }

    def get_uptime_and_boot(self) -> Dict[str, Any]:
        """Calculates system boot time and uptime in seconds and human-readable format."""
        try:
            boot_timestamp = psutil.boot_time()
            uptime_seconds = int(time.time() - boot_timestamp)

            days = uptime_seconds // 86400
            hours = (uptime_seconds % 86400) // 3600
            minutes = (uptime_seconds % 3600) // 60
            uptime_str = f"{days}d {hours}h {minutes}m"

            boot_dt = datetime.fromtimestamp(boot_timestamp, timezone.utc)
            boot_str = boot_dt.strftime("%Y-%m-%d %H:%M:%S UTC")

            return {
                "uptime_seconds": uptime_seconds,
                "uptime_str": uptime_str,
                "boot_time": boot_str,
            }
        except Exception as e:
            return {
                "uptime_seconds": 0,
                "uptime_str": "Unknown",
                "boot_time": "Unknown",
                "error": str(e),
            }

    def get_top_processes(self, limit: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieves top running processes by CPU and Memory usage.
        Safely ignores processes that terminate during iteration.
        """
        processes = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = proc.info
                # Default None values to 0.0
                cpu = float(info.get("cpu_percent") or 0.0)
                mem = float(info.get("memory_percent") or 0.0)
                processes.append(
                    {
                        "pid": info["pid"],
                        "name": info["name"] or "Unknown",
                        "cpu_percent": round(cpu, 1),
                        "memory_percent": round(mem, 1),
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception:
                continue

        top_cpu = sorted(processes, key=lambda x: x["cpu_percent"], reverse=True)[:limit]
        top_memory = sorted(processes, key=lambda x: x["memory_percent"], reverse=True)[:limit]

        return {
            "top_cpu": top_cpu,
            "top_memory": top_memory,
            "total_processes": len(processes),
        }

    def collect_all_metrics(self) -> Dict[str, Any]:
        """Collects comprehensive system performance metrics."""
        cpu = self.get_cpu_metrics()
        memory = self.get_memory_metrics()
        disk = self.get_disk_metrics()
        load = self.get_system_load()
        uptime = self.get_uptime_and_boot()
        procs = self.get_top_processes(limit=5)

        return {
            "cpu_percent": cpu["cpu_percent"],
            "logical_cores": cpu["logical_cores"],
            "memory_percent": memory["memory_percent"],
            "memory_used_gb": memory["used_gb"],
            "memory_total_gb": memory["total_gb"],
            "disk_percent": disk["disk_percent"],
            "disk_used_gb": disk["used_gb"],
            "disk_total_gb": disk["total_gb"],
            "load_1m": load["load_1m"],
            "load_5m": load["load_5m"],
            "load_15m": load["load_15m"],
            "process_count": procs["total_processes"],
            "uptime_seconds": uptime["uptime_seconds"],
            "uptime_str": uptime["uptime_str"],
            "boot_time": uptime["boot_time"],
            "top_cpu_processes": procs["top_cpu"],
            "top_memory_processes": procs["top_memory"],
        }


# Singleton instance
system_monitor = SystemMonitor()
