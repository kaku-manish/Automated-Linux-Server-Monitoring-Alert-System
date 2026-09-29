#!/usr/bin/env python3
"""
Test Log Anomaly Injector
Appends a sample ERROR/CRITICAL line to logs/sample_app.log to demonstrate
log event parsing and incident escalation.
"""

from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_LOG = BASE_DIR / "logs" / "sample_app.log"


def main():
    SAMPLE_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    sample_error = f"{ts} [CRITICAL] [app.payment_service] Database connection TIMEOUT - Transaction FAILED for user_id=4821\n"

    with open(SAMPLE_LOG, "a", encoding="utf-8") as f:
        f.write(sample_error)

    print(f"[+] Injected anomaly into {SAMPLE_LOG}:")
    print(f"    {sample_error.strip()}")
    print("\nRun 'python server_monitor.py' or check the Streamlit dashboard to see the detected incident.")


if __name__ == "__main__":
    main()
