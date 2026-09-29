# Automated Linux Server Monitoring & Incident Alert System

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Linux%20Ubuntu-orange.svg)](https://ubuntu.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![DevOps Level](https://img.shields.io/badge/DevOps%20Role-L1%20Junior%20to%20Mid-brightgreen.svg)](#interview-explanation)

A robust, lightweight, and production-grade Linux server monitoring, incident detection, automated healing, and visualization system. Built with Python 3, Linux system utilities (`systemctl`, `ping`, `/proc`), SQLite, and a modern Streamlit/Plotly web dashboard.

---

## 📑 Table of Contents

- [1. Project Overview](#1-project-overview)
- [2. Problem Statement](#2-problem-statement)
- [3. Key Features](#3-key-features)
- [4. System Architecture](#4-system-architecture)
- [5. Technology Stack](#5-technology-stack)
- [6. Directory Structure](#6-directory-structure)
- [7. Step-by-Step Installation](#7-step-by-step-installation)
- [8. Configuration Guide](#8-configuration-guide)
- [9. Running the System](#9-running-the-system)
  - [Manual Execution](#manual-execution)
  - [Background Daemon Mode](#background-daemon-mode)
  - [Streamlit Web Dashboard](#streamlit-web-dashboard)
- [10. Cron Automation](#10-cron-automation)
- [11. Testing & Validation](#11-testing--validation)
- [12. Demonstration Scenarios (Interview Walkthrough)](#12-demonstration-scenarios-interview-walkthrough)
- [13. How to Present this in a DevOps Interview](#13-how-to-present-this-in-a-devops-interview)
- [14. Troubleshooting Guide](#14-troubleshooting-guide)
- [15. Security & Best Practices](#15-security--best-practices)
- [16. Future Roadmap](#16-future-roadmap)
- [17. DevOps Interview Questions & Answers](#17-devops-interview-questions--answers)

---

## 1. Project Overview

In enterprise production environments, server downtime and silent performance degradation directly cause business loss. While enterprise suites like Prometheus, Datadog, or Grafana exist, understanding the **underlying operating system fundamentals**—CPU scheduling, virtual memory limits, disk I/O, socket connectivity, ICMP latency, systemd unit lifecycles, and log parsing—is the core prerequisite for any DevOps engineer.

This project delivers an end-to-end, zero-heavy-dependency monitoring system that:
1. Collects system metrics (CPU, RAM, Disk, System Load, Top Processes).
2. Monitors mission-critical services (`nginx`, `ssh`, `cron`) using `systemctl`.
3. Validates network connectivity and latency using ICMP ping.
4. Checks TCP port availability via raw socket connections.
5. Scans log files for error signatures using a memory-efficient tail approach.
6. Automatically detects threshold violations and generates multi-channel alerts (terminal, log file, database, and optional SMTP email).
7. Automatically attempts service recovery for degraded whitelisted services and verifies recovery outcomes.
8. Provides an interactive web dashboard for real-time and historical visualization.

---

## 2. Problem Statement

Small-to-medium Linux server deployments often suffer from:
- **Delayed Incident Reaction**: System crashes go unnoticed until end users report outages.
- **Resource Exhaustion**: Unchecked memory leaks or runaway processes saturate RAM and disk swap without early warning.
- **Service Outages**: Critical daemons (such as Nginx reverse proxies or SSH access) fail and remain dead without self-healing mechanisms.
- **Alert Fatigue / Overcomplication**: Heavy monitoring agents can consume excessive CPU/RAM on small instances.

**Solution**: A lightweight, self-contained Python & Bash monitoring agent that monitors health, auto-restarts failed services safely, logs incidents, and serves a live status dashboard without third-party SaaS vendor dependencies.

---

## 3. Key Features

- **System Health Observability**: Collects CPU %, Memory % (used/available/swap), Disk % (used/free), 1m/5m/15m Load Averages, system uptime, and top 5 processes by CPU and RAM.
- **Service Self-Healing**: Detects dead or failed systemd services and executes safe `systemctl restart` recovery commands with post-restart status verification.
- **Strict Security Whitelisting**: Only explicitly configured services can ever be restarted; arbitrary command injection is strictly prohibited.
- **Network Probing**: Measures round-trip ICMP latency to critical upstream DNS/gateways (`8.8.8.8`, `google.com`) and alerts on packet drops or elevated latency.
- **TCP Socket Probing**: Checks local port reachability (`22` SSH, `80` HTTP, `443` HTTPS) using Python's non-blocking `socket.connect_ex`.
- **Intelligent Log Inspection**: Uses file seek offsets (tail concept) to inspect only recent log entries for keywords (`ERROR`, `WARNING`, `CRITICAL`, `FAILED`, `TIMEOUT`) without memory overhead.
- **Alert Deduplication**: Implements a cooldown window to suppress repeat notifications and avoid alert fatigue.
- **Dual-Mode Operation**: Runs both as a one-shot scheduled cron job or a continuous background daemon.
- **Interactive Web Dashboard**: Streamlit dashboard with KPI metric cards, time-filtered Plotly charts (1h, 6h, 24h), incident filters, and service status tables.
- **Lightweight Bash Scripting**: Includes a standalone `health_check.sh` script demonstrating shell scripting fundamentals (`free`, `df`, `awk`, `/proc/loadavg`, and exit codes).

---

## 4. System Architecture

```
+-----------------------------------------------------------------------------------+
|                            LINUX SERVER ENVIRONMENT                               |
+-----------------------------------------------------------------------------------+
        |                          |                        |
        v                          v                        v
+------------------+     +-------------------+    +-------------------+
|  System Metrics  |     |  Systemd Services |    | Network & Sockets |
| (psutil, /proc)  |     |   (systemctl)     |    |  (ping, socket)   |
+------------------+     +-------------------+    +-------------------+
        |                          |                        |
        +--------------------+     |     +------------------+
                             |     |     |
                             v     v     v
                  +--------------------------------+
                  |       server_monitor.py        | <--- Reads config/config.json
                  |       (Main Orchestrator)      |
                  +--------------------------------+
                                   |
         +-------------------------+-------------------------+
         |                                                   |
         v                                                   v
+------------------+                               +--------------------+
| Incident Engine  |                               | Log File Scanner   |
| (Threshold Eval) |                               | (tail / keyword)   |
+------------------+                               +--------------------+
         |                                                   |
         v                                                   v
+--------------------------------------------------------------------+
|                         Alert Manager                              |
|   +---------------------+   +----------------+   +---------------+ |
|   | Terminal / Console  |   | logs/monitor.log|  | SMTP Email    | |
|   +---------------------+   +----------------+   +---------------+ |
+--------------------------------------------------------------------+
         |                                                   |
         v (If service down & auto_restart=true)             v
+-----------------------+                         +----------------------+
|  recovery_manager.py  |                         | SQLite Database      |
|  (systemctl restart)  |                         | (data/monitoring.db) |
+-----------------------+                         +----------------------+
         |                                                   |
         v                                                   v
+-----------------------+                         +----------------------+
| Service Verification  |                         |  Streamlit Dashboard |
| (active / failed)     |                         |  (dashboard.py)      |
+-----------------------+                         +----------------------+
```

---

## 5. Technology Stack

| Technology | Purpose | Why Chosen |
|---|---|---|
| **Python 3** | Core Application Logic | Clear syntax, rich standard library, industry standard for DevOps automation |
| **Linux Bash** | Installation & Shell Probes | Fundamental Linux administrative capability, portable across Unix environments |
| **psutil** | Cross-platform System Metrics | Efficient C-backed bindings for hardware utilization and process management |
| **systemctl / systemd** | Service Supervision | Standard init system across modern Linux distributions (Ubuntu, Debian, RHEL) |
| **socket / ping** | Network & Port Checks | Native network stack interaction without heavy external packages |
| **SQLite3** | Metric & Incident Storage | Zero-configuration, serverless, transactional database engine |
| **Streamlit** | Web UI Dashboard | Rapid data visualization and intuitive control interface |
| **Pandas & Plotly** | Analytics & Charts | Interactive time-series exploration and clean tabular manipulation |
| **Cron** | Scheduled Execution | Ubiquitous Linux daemon for time-based background job scheduling |

---

## 6. Directory Structure

```text
server-monitoring/
│
├── server_monitor.py        # Main execution orchestrator
├── system_monitor.py        # System health & process metrics (psutil)
├── network_monitor.py       # Ping latency & TCP port socket probes
├── service_monitor.py       # systemctl service health inspection
├── log_monitor.py           # Tail-based log parsing & application logger
├── alert_manager.py         # Incident alerting (terminal, log, SQLite, SMTP)
├── recovery_manager.py      # Automated service restart & verification
├── database.py              # SQLite schema, tables, and query layer
├── config_manager.py        # JSON config loader, validator, and path resolver
├── dashboard.py             # Streamlit & Plotly interactive web dashboard
│
├── config/
│   └── config.json          # Configurable thresholds, targets, and intervals
│
├── logs/
│   ├── monitor.log          # Application incident and event log
│   └── sample_app.log       # Sample application log for demo testing
│
├── data/
│   └── monitoring.db        # SQLite database storing historical metrics
│
├── scripts/
│   ├── health_check.sh      # Standalone Bash server health check script
│   ├── install.sh           # Automated installer and venv builder
│   ├── setup_cron.sh        # Idempotent crontab scheduler (every 5 min)
│   ├── cpu_load_test.py     # Safe temporary CPU load generator for demo
│   └── inject_test_log.py   # Test log anomaly injector for demo
│
├── tests/
│   ├── __init__.py
│   └── test_monitoring.py   # Automated unit test suite
│
├── requirements.txt         # Pinned Python package dependencies
├── README.md                # Comprehensive documentation & interview guide
├── .gitignore               # Git exclusion patterns
└── LICENSE                  # MIT License
```

---

## 7. Step-by-Step Installation

### Prerequisites (Ubuntu / Debian Linux)

```bash
# Update package repositories and install required tools
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git curl
```

### Option A: Automated Installation (Recommended)

Run the automated installer script:

```bash
cd server-monitoring
chmod +x scripts/install.sh
./scripts/install.sh
```

### Option B: Manual Installation

```bash
cd server-monitoring

# 1. Create a Python virtual environment
python3 -m venv venv

# 2. Activate the virtual environment
source venv/bin/activate

# 3. Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Make shell scripts executable
chmod +x scripts/*.sh

# 5. Initialize the SQLite database
python3 -c "from database import db_manager; db_manager.init_db()"
```

---

## 8. Configuration Guide

All monitoring thresholds, targets, and intervals are managed in `config/config.json`:

```json
{
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
      "auto_restart_enabled": true,
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
```

### Optional Email Alert Configuration

To enable email notifications, set standard environment variables (e.g. in `~/.bashrc` or `/etc/environment`):

```bash
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USERNAME="alerts@example.com"
export SMTP_PASSWORD="your-app-specific-password"
export ALERT_EMAIL_TO="devops-oncall@example.com"
```
*Note: If these variables are not set, email dispatch is cleanly skipped without any error or disruption.*

---

## 9. Running the System

### Manual Execution

Run a single monitoring cycle (ideal for verification, debugging, or cron triggers):

```bash
# Activate venv
source venv/bin/activate

# Execute single check
python server_monitor.py
```

Sample Terminal Output:
```text
=============================================
LINUX SERVER MONITORING REPORT
=============================================
Timestamp: 2026-09-29 17:43:22 UTC

SYSTEM HEALTH
CPU: 7.9% [OK]
Memory: 52.4% [OK]
Disk: 61.2% [OK]
Load: 0.42 [OK]

SERVICES
nginx: active [OK]
ssh: active [OK]
cron: active [OK]

NETWORK
8.8.8.8: UP - 14.2 ms [OK]
google.com: UP - 18.5 ms [OK]

PORTS
22 (SSH): OPEN [OK]
80 (HTTP): OPEN [OK]
443 (HTTPS): OPEN [OK]

LOG CHECK
No critical errors found [OK]

OVERALL STATUS
HEALTHY
=============================================
```

### Background Daemon Mode

To run continuously in the background at the interval defined in `config.json` (or custom flag):

```bash
# Run continuously every 60 seconds
python server_monitor.py --daemon --interval 60
```

### Streamlit Web Dashboard

Start the live interactive dashboard:

```bash
streamlit run dashboard.py
```

Once running, navigate to `http://localhost:8501` in your browser.

**Dashboard Sections:**
1. **Server Overview**: Metric cards showing real-time CPU %, RAM %, Disk %, 1m Load, and Status badge.
2. **Resource Trends**: Interactive Plotly charts showing CPU, RAM, and Disk metrics over 1h, 6h, 24h, or all time, with threshold indicator lines.
3. **Important Linux Services**: Live state table of monitored services (`nginx`, `ssh`, `cron`).
4. **Network Monitoring**: Reachability status and latency (ms) for external and internal endpoints.
5. **Port Probes**: Socket check state (OPEN/CLOSED) for local application ports.
6. **Top Running Processes**: Top 5 CPU-consuming and RAM-consuming processes.
7. **Incident History**: Historical incident log with severity filtering (`ALL`, `CRITICAL`, `WARNING`, `INFO`) and auto-recovery outcome tracking.
8. **Monitored Log Events**: Recent log anomalies extracted from monitored log paths.
9. **Instant Health Check Button**: Allows manual trigger of a monitoring cycle directly from the UI.

---

## 10. Cron Automation

To ensure continuous, hands-off monitoring without running a long-lived foreground process, configure a 5-minute cron schedule.

### Automated Setup

Execute the provided cron setup script:

```bash
chmod +x scripts/setup_cron.sh
./scripts/setup_cron.sh
```

### Manual Setup

Open crontab:

```bash
crontab -e
```

Add the following line (replace `/path/to/server-monitoring` with your absolute path):

```bash
*/5 * * * * cd /path/to/server-monitoring && /path/to/server-monitoring/venv/bin/python server_monitor.py >> /path/to/server-monitoring/logs/cron_execution.log 2>&1
```

Verify your active cron job:

```bash
crontab -l
```

---

## 11. Testing & Validation

The project includes an automated unit test suite covering configuration loading, database transactions, port socket probes, and log regex pattern matching.

Run the test suite:

```bash
# Run with standard Python unittest runner
python -m unittest discover tests

# Or run test file directly
python tests/test_monitoring.py
```

Expected output:
```text
........
----------------------------------------------------------------------
Ran 8 tests in 1.15s

OK
```

---

## 12. Demonstration Scenarios (Interview Walkthrough)

These 5 demonstration scenarios show the real-time capabilities of the system during a technical interview or live demo:

### Scenario 1: Normal Healthy Monitoring

1. Ensure services are running normally.
2. Run:
   ```bash
   python server_monitor.py
   ```
3. Observe terminal output: All services are `active`, ports `OPEN`, ping latency low, overall status `HEALTHY`.
4. Open the Streamlit dashboard (`streamlit run dashboard.py`) and show the green KPI cards.

---

### Scenario 2: Service Failure & Automated Self-Healing (Nginx)

1. Stop the Nginx service:
   ```bash
   sudo systemctl stop nginx
   ```
2. Verify it is inactive:
   ```bash
   systemctl is-active nginx
   # Outputs: inactive
   ```
3. Run the monitoring orchestrator:
   ```bash
   python server_monitor.py
   ```
4. **What Happens:**
   - The monitoring engine detects `nginx` is down.
   - It checks `auto_restart_enabled: true` and verifies `nginx` is on the security whitelist.
   - It triggers `recovery_manager.py`, executing `sudo systemctl restart nginx`.
   - It pauses briefly and checks `service_monitor.check_service("nginx")`.
   - The restart succeeds, the status updates to `active (recovered)`, and an incident is logged with `recovery_status: SUCCESS`.
5. Check the dashboard **Incident History** table: Show the auto-recovery audit trail!

---

### Scenario 3: High CPU Spike Detection

1. Run the safe CPU stress test script in one terminal:
   ```bash
   python scripts/cpu_load_test.py --duration 20
   ```
2. In a second terminal, trigger the monitor:
   ```bash
   python server_monitor.py
   ```
3. **What Happens:**
   - CPU usage spikes past the 80% threshold.
   - A `High CPU Utilization` incident is triggered and logged.
   - An alert prints in bold red/yellow to the console.
   - The historical Plotly chart on the dashboard displays the spike above the dotted red threshold line.

---

### Scenario 4: Port Failure / Closed Port Incident

1. Open `config/config.json` and temporarily add an unused port to `ports`:
   ```json
   {"host": "127.0.0.1", "port": 9999, "service_name": "TestService"}
   ```
2. Run:
   ```bash
   python server_monitor.py
   ```
3. **What Happens:**
   - Sockets attempt connection to `127.0.0.1:9999`, which returns `errno: 111 (Connection refused)`.
   - A `Port Unavailable` incident is created for `127.0.0.1:9999 (TestService)`.
   - System overall status transitions to `WARNING`.

---

### Scenario 5: Log Error & Keyword Detection

1. Run the test log anomaly injector:
   ```bash
   python scripts/inject_test_log.py
   ```
   *This writes a sample error: `[CRITICAL] [app.payment] Database connection TIMEOUT - Transaction FAILED` to `logs/sample_app.log`.*
2. Run:
   ```bash
   python server_monitor.py
   ```
3. **What Happens:**
   - `log_monitor.py` scans the tail of `logs/sample_app.log`.
   - Matches the keywords `CRITICAL`, `TIMEOUT`, and `FAILED`.
   - Records the anomaly in SQLite `log_events` and escalates to a `CRITICAL` incident.
   - Displays the log snippet in Section 8 of the Streamlit dashboard.

---

## 13. How to Present this in a DevOps Interview

When explaining this project in an interview, structure your narrative using the **STAR Method** (Situation, Task, Action, Result):

### Elevator Pitch (30 Seconds)
> *"I designed and built an Automated Linux Server Monitoring and Incident Alert System in Python and Bash. The project provides automated observability across CPU, memory, disk, network latency, TCP ports, and systemd services. When a monitored service fails, the system executes an automated self-healing restart, verifies recovery, logs the incident to SQLite, alerts the engineering team, and visualizes system health on a Streamlit dashboard."*

### Key Talking Points to Highlight:
1. **Operating System Fundamentals**: Explain how you used Python's `psutil` to query `/proc` virtual filesystems for load averages and memory counters, avoiding heavy third-party agent overhead.
2. **Reliability & Idempotency**: Highlight how the cron setup script checks for existing entries to prevent duplication, and how SQLite transactions use context managers to guarantee clean resource closure.
3. **Security Awareness**: Emphasize that service auto-recovery is restricted to an explicit configuration whitelist. You don't allow arbitrary service restarts or unsanitized shell inputs.
4. **Log Efficiency (The Tail Concept)**: Mention that instead of reading entire multi-gigabyte log files into memory, your log scanner reads only recent bytes using reverse seek offsets, keeping memory footprint constant ($O(1)$).
5. **Observability Stack**: Contrast this system with enterprise tooling: explain that while enterprise systems use Prometheus and Alertmanager, building this from scratch proves your mastery of low-level sockets, ICMP packets, and systemd process trees.

---

## 14. Troubleshooting Guide

| Issue | Root Cause | Solution |
|---|---|---|
| `systemctl: command not found` | Running in a minimal container (e.g. Docker without systemd) or Windows | The script handles this gracefully by marking services as `unknown`. On Linux hosts, ensure systemd is the init process (`pidof systemd`). |
| `Permission denied` on `systemctl restart` | Auto-recovery requires sudo permissions | Add a sudoers rule allowing the monitoring user to restart specific services without a password: `youruser ALL=(ALL) NOPASSWD: /bin/systemctl restart nginx` |
| `Permission denied` on `/var/log/syslog` | Log file permissions restricted to `adm` group | Add your user to the log group: `sudo usermod -aG adm $USER` or monitor application-level logs in user space. |
| Streamlit dashboard port in use | Port 8501 occupied by another process | Launch on an alternate port: `streamlit run dashboard.py --server.port 8502` |
| Ping fails or requires root | Unprivileged ping disabled by kernel | Ensure ping capabilities: `sudo setcap cap_net_raw+ep /bin/ping` or verify network routing. |

---

## 15. Security & Best Practices

1. **Principle of Least Privilege**:
   - The monitoring daemon does not require root privileges for basic metrics collection, network probes, or port checks.
   - Sudo escalation is restricted exclusively to `systemctl restart <whitelisted_service>`.
2. **Input Sanitization & Whitelisting**:
   - The recovery manager validates the requested service against the `service_list` array in `config.json` before invoking subprocess calls. Arbitrary arguments are rejected.
3. **Credential Management**:
   - No SMTP passwords or tokens are stored in source code. All email alerting secrets are read dynamically from OS environment variables.
4. **Resource Constraints**:
   - Sockets and subprocesses enforce strict execution timeouts (default: 3 seconds) to prevent frozen processes or thread starvation.
5. **Log Integrity**:
   - Log files are opened in append-only mode (`a`) with UTF-8 encoding and fallback error replacement.

---

## 16. Future Roadmap

- **Prometheus Exporter Endpoint**: Add an optional `/metrics` HTTP endpoint exposing system metrics in OpenMetrics format for Prometheus scraping.
- **Telegram / Slack Webhook Integration**: Implement webhook dispatch to send real-time alerts to a Slack or Discord channel.
- **Dynamic Thresholding**: Calculate rolling average baseline metrics (e.g. 7-day moving average) to alert on statistical anomalies rather than static thresholds.
- **Container / Docker Monitoring**: Incorporate Docker daemon socket polling to monitor container status and restart policies alongside systemd units.

---

## 17. DevOps Interview Questions & Answers

### Q1: What is the difference between CPU utilization and System Load Average?
**Answer:** CPU utilization measures the percentage of time the CPU spent executing non-idle tasks over a given sampling interval. System Load Average (reported in `/proc/loadavg` as 1, 5, and 15-minute averages) represents the average number of processes that are either actively running on a CPU core or waiting in an uninterruptible sleep state (e.g., waiting for Disk I/O or network locks). A server can have 10% CPU usage but a high load average if processes are blocked on slow disk I/O.

### Q2: Why use `systemctl is-active` instead of parsing `ps aux` to check if a service is running?
**Answer:** `ps aux` only checks for the existence of a process name, which can be fooled by unrelated scripts or zombie processes. In contrast, `systemctl is-active` queries the systemd supervisor directly, verifying unit health, PID tracking, cgroup constraints, and state transitions (active, failed, activating, or dead).

### Q3: How did you implement log monitoring without running out of memory on large files?
**Answer:** Instead of reading the entire file with `readlines()`, which loads gigabytes of data into RAM ($O(N)$), I implemented a tail-based approach using `file.seek(0, os.SEEK_END)`. If the file exceeds a buffer size, it seeks backward to inspect only the trailing 64 KB of data, ensuring $O(1)$ memory consumption regardless of log file size.

### Q4: How does your system prevent "alert storms" or alert fatigue?
**Answer:** In `alert_manager.py`, I implemented an in-memory alert deduplication dictionary with a configurable cooldown window (default: 10 minutes). When an incident triggers, its composite key `(type, resource, severity)` is cached with a timestamp. Duplicate events during subsequent monitoring cycles within that window are suppressed unless the severity level escalates.

### Q5: What security risks exist when a monitoring script can restart services, and how did you mitigate them?
**Answer:** The primary risk is command injection or arbitrary service manipulation if an attacker can manipulate input parameters or if the script runs with blanket `sudo` privileges. I mitigated this by enforcing an explicit whitelist loaded from `config.json`—only whitelisted services can be passed to `systemctl restart`—and designing the sudoers configuration to permit passwordless restarts only for specified service binaries.

### Q6: How does TCP port checking work at the network layer in your script?
**Answer:** The script creates a stream socket using `socket.socket(socket.AF_INET, socket.SOCK_STREAM)` and issues a non-blocking `connect_ex((host, port))` call. This initiates a standard TCP three-way handshake (SYN -> SYN-ACK -> ACK). If the port is open and listening, the handshake completes and `connect_ex` returns 0. If closed or firewalled, it returns an errno (such as `ECONNREFUSED` or `ETIMEDOUT`) without raising an unhandled exception.

### Q7: Why use SQLite instead of MySQL or PostgreSQL for this system?
**Answer:** SQLite is embedded directly into the Python application runtime as a self-contained, serverless database engine stored in a single file (`data/monitoring.db`). For single-node Linux monitoring, it requires zero external service configuration, eliminates network latency, has minimal resource footprint, and easily handles thousands of metric snapshots with indexed queries.

### Q8: What is the purpose of the standalone `health_check.sh` script if you already have Python?
**Answer:** In incident response or disaster recovery scenarios, Python or its virtual environment might be corrupted, misconfigured, or missing dependencies. A pure POSIX Bash script utilizing standard coreutils (`awk`, `free`, `df`, `/dev/tcp`) provides a zero-dependency fallback for rapid triage directly from a remote shell.

### Q9: How does the crontab configuration prevent overlapping script executions?
**Answer:** In production cron environments, if a monitoring check hangs, subsequent cron triggers could accumulate and exhaust system processes. We mitigated this by setting strict socket timeouts (3s), ping timeouts (2s), and subprocess timeouts (15s). Additionally, a file lock (e.g. using `flock` or a pidfile) can be added to guarantee that only one instance executes at any time.

### Q10: How would you scale this architecture from 1 server to 100 servers?
**Answer:** In a distributed multi-node fleet, instead of running local SQLite databases on each host, I would package the Python collection agent as a systemd daemon or lightweight container that pushes structured JSON metrics to a central time-series database (like Prometheus or InfluxDB) or a message queue (like RabbitMQ/Kafka). The web dashboard would then query the central data store, and alerts would be managed via Alertmanager with routing policies.
