"""
Log Monitoring Module
Performs efficient recent-log inspections (tail concept), keyword pattern matching,
and configures the application logging framework.
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from config_manager import config_manager


def setup_logger(
    log_file: Optional[Path] = None,
    log_level: str = "INFO"
) -> logging.Logger:
    """
    Configures the project logging handler to output to both logs/monitor.log
    and the terminal.
    """
    target_path = log_file or config_manager.log_path
    target_path.parent.mkdir(parents=True, exist_ok=True)

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logger = logging.getLogger("server_monitor")
    logger.setLevel(numeric_level)

    # Avoid duplicate handlers on re-initialization
    if not logger.handlers:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # File Handler (logs/monitor.log)
        file_handler = logging.FileHandler(str(target_path), encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


class LogMonitor:
    """Scans configured log files for error and warning keywords."""

    def __init__(self):
        self.logger = setup_logger()

    @staticmethod
    def read_tail_lines(file_path: Path, max_lines: int = 100) -> List[str]:
        """
        Reads the last `max_lines` from a file efficiently without loading
        the entire file into memory (tail concept).
        """
        if not file_path.exists():
            return []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                # For typical log files, reading lines from seek near end or simple slice
                # If file is smaller than 2MB, readlines then slice
                f.seek(0, os.SEEK_END)
                file_size = f.tell()

                # If large file (> 1MB), seek to last 64KB
                buffer_size = 65536
                if file_size > buffer_size:
                    f.seek(file_size - buffer_size, os.SEEK_SET)
                    lines = f.readlines()
                    # First line might be partial
                    return lines[1:][-max_lines:]
                else:
                    f.seek(0, os.SEEK_SET)
                    lines = f.readlines()
                    return lines[-max_lines:]
        except (PermissionError, OSError) as e:
            raise e

    def scan_file(
        self,
        file_path_str: str,
        keywords: Optional[List[str]] = None,
        max_lines: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Scans a specific log file for specified keywords.
        Returns matching log anomalies.
        """
        resolved_path = config_manager.resolve_path(file_path_str)
        target_keywords = keywords or config_manager.error_keywords
        regex_pattern = re.compile(
            r"\b(" + "|".join(re.escape(k) for k in target_keywords) + r")\b",
            re.IGNORECASE,
        )

        if not resolved_path.exists():
            self.logger.debug(f"Log file not found: {resolved_path} (skipping)")
            return []

        anomalies = []
        try:
            lines = self.read_tail_lines(resolved_path, max_lines=max_lines)
            for idx, line in enumerate(lines, 1):
                clean_line = line.strip()
                if not clean_line:
                    continue

                match = regex_pattern.search(clean_line)
                if match:
                    matched_kw = match.group(1).upper()
                    # Determine severity
                    if matched_kw in ("CRITICAL", "FAILED", "FATAL"):
                        severity = "CRITICAL"
                    elif matched_kw in ("ERROR", "TIMEOUT"):
                        severity = "ERROR"
                    else:
                        severity = "WARNING"

                    anomalies.append(
                        {
                            "source": str(resolved_path.name),
                            "file_path": str(resolved_path),
                            "severity": severity,
                            "keyword": matched_kw,
                            "message": clean_line[:300],  # truncate excessively long lines
                        }
                    )
        except PermissionError:
            self.logger.warning(
                f"Permission denied accessing log file: {resolved_path}. Try running with proper log group permissions."
            )
        except Exception as e:
            self.logger.error(f"Error reading log file {resolved_path}: {e}")

        return anomalies

    def scan_all_logs(self) -> List[Dict[str, Any]]:
        """Scans all configured log files and aggregates anomalies."""
        files = config_manager.logs_to_monitor
        max_lines = config_manager.max_lines_to_read
        keywords = config_manager.error_keywords
        all_events = []

        for log_file in files:
            events = self.scan_file(log_file, keywords=keywords, max_lines=max_lines)
            all_events.extend(events)

        return all_events


# Singleton instance
log_monitor = LogMonitor()
