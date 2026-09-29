@echo off
title Linux Server Monitoring System
color 0A

echo =========================================================
echo   Automated Server Monitoring & Incident Alert System
echo =========================================================
echo.

cd /d "%~dp0"

echo [*] Step 1: Running initial monitoring and health check cycle...
echo ---------------------------------------------------------
python server_monitor.py

echo.
echo =========================================================
echo [*] Step 2: Launching Streamlit Web Dashboard...
echo [*] Opening dashboard at http://localhost:8501
echo [*] (Press Ctrl+C to stop the dashboard server)
echo =========================================================
echo.

python -m streamlit run dashboard.py

pause
