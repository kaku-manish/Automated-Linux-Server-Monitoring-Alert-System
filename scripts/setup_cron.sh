#!/usr/bin/env bash
# ==============================================================================
# Script Name   : setup_cron.sh
# Description   : Automates the setup of a recurring crontab entry for server_monitor.py
# Schedule      : Every 5 minutes (*/5 * * * *)
# Target OS     : Ubuntu / Debian / RHEL / CentOS
# ==============================================================================

set -e

# Detect directory paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MONITOR_SCRIPT="${PROJECT_ROOT}/server_monitor.py"
CRON_LOG="${PROJECT_ROOT}/logs/cron_execution.log"

# Detect Python executable (prefer project venv if exists)
if [ -f "${PROJECT_ROOT}/venv/bin/python" ]; then
    PYTHON_BIN="${PROJECT_ROOT}/venv/bin/python"
elif [ -f "${PROJECT_ROOT}/venv/bin/python3" ]; then
    PYTHON_BIN="${PROJECT_ROOT}/venv/bin/python3"
else
    PYTHON_BIN="$(which python3 || which python)"
fi

echo "============================================="
echo "  Setting up Cron Automation for Server Monitor"
echo "============================================="
echo "Project Root   : ${PROJECT_ROOT}"
echo "Python Binary  : ${PYTHON_BIN}"
echo "Monitor Script : ${MONITOR_SCRIPT}"
echo "Cron Log       : ${CRON_LOG}"
echo "Schedule       : Every 5 minutes (*/5 * * * *)"
echo "============================================="

# Ensure log directory exists
mkdir -p "${PROJECT_ROOT}/logs"

# Construct the cron command
CRON_JOB="*/5 * * * * cd ${PROJECT_ROOT} && ${PYTHON_BIN} ${MONITOR_SCRIPT} >> ${CRON_LOG} 2>&1"

# Check if the crontab command exists
if ! command -v crontab >/dev/null 2>&1; then
    echo "Error: crontab command not found on this system. Please install cron daemon."
    exit 1
fi

# Fetch existing crontab
CURRENT_CRON=$(crontab -l 2>/dev/null || true)

# Check for duplicates
if echo "${CURRENT_CRON}" | grep -F "${MONITOR_SCRIPT}" >/dev/null 2>&1; then
    echo "Notice: A crontab entry for server_monitor.py already exists."
    echo "Current matching line:"
    echo "${CURRENT_CRON}" | grep -F "${MONITOR_SCRIPT}"
    echo "No duplicate entries were created."
else
    # Append the new job cleanly
    (echo "${CURRENT_CRON}"; echo "${CRON_JOB}") | crontab -
    echo "Success: Crontab entry successfully added!"
    echo "Installed Job: ${CRON_JOB}"
fi

echo -e "\nVerify active crontab using: crontab -l"
