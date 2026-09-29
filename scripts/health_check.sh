#!/usr/bin/env bash
# ==============================================================================
# Script Name   : health_check.sh
# Description   : Lightweight standalone Bash health check for Linux servers.
# Target OS     : Ubuntu / Debian / RHEL / CentOS
# Author        : DevOps Engineering
# ==============================================================================

set -o pipefail

# ANSI Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BLUE}${BOLD}====================================================${NC}"
echo -e "${BLUE}${BOLD}        LINUX SERVER QUICK HEALTH CHECK             ${NC}"
echo -e "${BLUE}${BOLD}====================================================${NC}"
echo -e "Timestamp: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo -e "Hostname : $(hostname)"
echo -e "Uptime   : $(uptime -p 2>/dev/null || uptime)\n"

# ----------------- 1. CPU & LOAD AVERAGE -----------------
echo -e "${BOLD}[1] CPU & System Load${NC}"
LOAD_1M=$(awk '{print $1}' /proc/loadavg 2>/dev/null || uptime | awk -F'load average:' '{ print $2 }' | cut -d, -f1 | tr -d ' ')
CPU_CORES=$(nproc 2>/dev/null || echo 1)
echo -e "  * CPU Cores    : ${CPU_CORES}"
echo -e "  * Load Average : ${LOAD_1M}"

# ----------------- 2. MEMORY USAGE -----------------
echo -e "\n${BOLD}[2] Memory Utilization${NC}"
if command -v free >/dev/null 2>&1; then
    MEM_TOTAL=$(free -m | awk '/Mem:/ {print $2}')
    MEM_USED=$(free -m | awk '/Mem:/ {print $3}')
    MEM_PERCENT=$(( 100 * MEM_USED / MEM_TOTAL ))
    
    if [ "$MEM_PERCENT" -ge 90 ]; then
        echo -e "  * RAM: ${MEM_USED}MB / ${MEM_TOTAL}MB (${MEM_PERCENT}%) ${RED}[CRITICAL]${NC}"
    elif [ "$MEM_PERCENT" -ge 80 ]; then
        echo -e "  * RAM: ${MEM_USED}MB / ${MEM_TOTAL}MB (${MEM_PERCENT}%) ${YELLOW}[WARNING]${NC}"
    else
        echo -e "  * RAM: ${MEM_USED}MB / ${MEM_TOTAL}MB (${MEM_PERCENT}%) ${GREEN}[OK]${NC}"
    fi
else
    echo -e "  * free command not found."
fi

# ----------------- 3. DISK USAGE -----------------
echo -e "\n${BOLD}[3] Root Disk Utilization${NC}"
if command -v df >/dev/null 2>&1; then
    DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
    DISK_AVAIL=$(df -h / | awk 'NR==2 {print $4}')
    
    if [ "$DISK_USAGE" -ge 90 ]; then
        echo -e "  * Root (/): ${DISK_USAGE}% used (${DISK_AVAIL} free) ${RED}[CRITICAL]${NC}"
    elif [ "$DISK_USAGE" -ge 80 ]; then
        echo -e "  * Root (/): ${DISK_USAGE}% used (${DISK_AVAIL} free) ${YELLOW}[WARNING]${NC}"
    else
        echo -e "  * Root (/): ${DISK_USAGE}% used (${DISK_AVAIL} free) ${GREEN}[OK]${NC}"
    fi
fi

# ----------------- 4. SERVICES STATUS -----------------
echo -e "\n${BOLD}[4] Core Services Status${NC}"
check_service() {
    local svc="$1"
    if command -v systemctl >/dev/null 2>&1; then
        if systemctl is-active --quiet "$svc"; then
            echo -e "  * ${svc} : ${GREEN}ACTIVE [OK]${NC}"
        else
            echo -e "  * ${svc} : ${RED}INACTIVE / FAILED [CRITICAL]${NC}"
        fi
    else
        echo -e "  * ${svc} : ${YELLOW}systemctl not available${NC}"
    fi
}

check_service "nginx"
check_service "ssh"
check_service "cron"

# ----------------- 5. NETWORK CONNECTIVITY -----------------
echo -e "\n${BOLD}[5] Network Reachability${NC}"
check_ping() {
    local host="$1"
    if ping -c 1 -W 2 "$host" >/dev/null 2>&1; then
        echo -e "  * Ping to ${host} : ${GREEN}REACHABLE [OK]${NC}"
    else
        echo -e "  * Ping to ${host} : ${RED}UNREACHABLE [CRITICAL]${NC}"
    fi
}

check_ping "8.8.8.8"
check_ping "google.com"

# ----------------- 6. LOCAL PORT PROBES -----------------
echo -e "\n${BOLD}[6] Local Port Probes${NC}"
check_port() {
    local port="$1"
    local name="$2"
    # Test via /dev/tcp or nc if bash supports it
    if (echo > /dev/tcp/127.0.0.1/"$port") >/dev/null 2>&1; then
        echo -e "  * Port ${port} (${name}) : ${GREEN}OPEN [OK]${NC}"
    elif command -v nc >/dev/null 2>&1 && nc -z -w 1 127.0.0.1 "$port" >/dev/null 2>&1; then
        echo -e "  * Port ${port} (${name}) : ${GREEN}OPEN [OK]${NC}"
    else
        echo -e "  * Port ${port} (${name}) : ${YELLOW}CLOSED / REFUSED${NC}"
    fi
}

check_port 22 "SSH"
check_port 80 "HTTP"
check_port 443 "HTTPS"

echo -e "\n${BLUE}${BOLD}====================================================${NC}"
echo -e "${BLUE}${BOLD}             HEALTH CHECK COMPLETED                 ${NC}"
echo -e "${BLUE}${BOLD}====================================================${NC}"
exit 0
