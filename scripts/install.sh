#!/usr/bin/env bash
# ==============================================================================
# Script Name   : install.sh
# Description   : Automated installer for Linux Server Monitoring & Alert System
# Target OS     : Ubuntu / Debian / Linux
# ==============================================================================

set -e

# ANSI Color definitions
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}   Automated Linux Server Monitoring System - Installer        ${NC}"
echo -e "${BLUE}================================================================${NC}"

# 1. Project Directory Resolution
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

echo -e "\n[*] Project Directory: ${PROJECT_ROOT}"

# 2. Check for Python 3
echo -e "\n[*] Checking Python 3..."
if command -v python3 >/dev/null 2>&1; then
    PY_VER=$(python3 --version)
    echo -e "    ${GREEN}[OK] Found ${PY_VER}${NC}"
else
    echo -e "    ${RED}[FAIL] Python 3 is not installed.${NC}"
    echo "    Please install it using: sudo apt update && sudo apt install -y python3 python3-pip python3-venv"
    exit 1
fi

# 3. Create Required Folder Structure
echo -e "\n[*] Creating required directory hierarchy..."
mkdir -p "${PROJECT_ROOT}/config"
mkdir -p "${PROJECT_ROOT}/logs"
mkdir -p "${PROJECT_ROOT}/data"
mkdir -p "${PROJECT_ROOT}/scripts"
mkdir -p "${PROJECT_ROOT}/tests"
echo -e "    ${GREEN}[OK] Directories verified (config, logs, data, scripts, tests)${NC}"

# 4. Create Virtual Environment
echo -e "\n[*] Setting up Python virtual environment..."
if [ ! -d "${PROJECT_ROOT}/venv" ]; then
    python3 -m venv "${PROJECT_ROOT}/venv"
    echo -e "    ${GREEN}[OK] Virtual environment created at ${PROJECT_ROOT}/venv${NC}"
else
    echo -e "    ${YELLOW}[INFO] Virtual environment already exists at ${PROJECT_ROOT}/venv${NC}"
fi

# 5. Activate Venv & Install Requirements
echo -e "\n[*] Installing Python dependencies..."
# shellcheck source=/dev/null
source "${PROJECT_ROOT}/venv/bin/activate"

pip install --upgrade pip >/dev/null 2>&1 || true
if [ -f "${PROJECT_ROOT}/requirements.txt" ]; then
    pip install -r "${PROJECT_ROOT}/requirements.txt"
    echo -e "    ${GREEN}[OK] Dependencies successfully installed from requirements.txt${NC}"
else
    echo -e "    ${RED}[FAIL] requirements.txt not found!${NC}"
    exit 1
fi

# 6. Initialize SQLite Database
echo -e "\n[*] Initializing SQLite Database schema..."
python3 -c "import sys; sys.path.insert(0, '${PROJECT_ROOT}'); from database import db_manager; db_manager.init_db(); print('SQLite schema initialized at ' + str(db_manager.db_path))"
echo -e "    ${GREEN}[OK] Database initialized successfully.${NC}"

# 7. Check System Services (Informational)
echo -e "\n[*] Checking availability of systemctl and nginx..."
if command -v systemctl >/dev/null 2>&1; then
    echo -e "    ${GREEN}[OK] systemctl is available.${NC}"
    if systemctl list-unit-files | grep -q "^nginx.service"; then
        echo -e "    ${GREEN}[OK] nginx service is registered on this host.${NC}"
    else
        echo -e "    ${YELLOW}[INFO] nginx is not currently installed. To test nginx recovery later: sudo apt install nginx${NC}"
    fi
else
    echo -e "    ${YELLOW}[WARNING] systemctl not found in PATH. Service auto-recovery will report unavailable.${NC}"
fi

# 8. Set Execution Permissions on Bash scripts
chmod +x "${PROJECT_ROOT}/scripts/health_check.sh" || true
chmod +x "${PROJECT_ROOT}/scripts/setup_cron.sh" || true
chmod +x "${PROJECT_ROOT}/scripts/install.sh" || true

echo -e "\n${GREEN}================================================================${NC}"
echo -e "${GREEN}   INSTALLATION COMPLETE! YOU'RE READY TO MONITOR.              ${NC}"
echo -e "${GREEN}================================================================${NC}"
echo -e "\nNext steps:"
echo -e "  1. Run single monitoring cycle:"
echo -e "     ${BLUE}${PROJECT_ROOT}/venv/bin/python ${PROJECT_ROOT}/server_monitor.py${NC}"
echo -e "  2. Launch Streamlit Web Dashboard:"
echo -e "     ${BLUE}${PROJECT_ROOT}/venv/bin/streamlit run ${PROJECT_ROOT}/dashboard.py${NC}"
echo -e "  3. Set up automated 5-minute cron job:"
echo -e "     ${BLUE}${PROJECT_ROOT}/scripts/setup_cron.sh${NC}"
echo -e "  4. Run standalone bash health check:"
echo -e "     ${BLUE}${PROJECT_ROOT}/scripts/health_check.sh${NC}"
echo ""
