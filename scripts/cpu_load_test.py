#!/usr/bin/env python3
"""
CPU Load Generator for Monitoring Demo
Generates safe temporary CPU load for a specified duration (default: 15 seconds)
to trigger high CPU alerts during demonstrations.
"""

import argparse
import multiprocessing
import time


def cpu_stress_worker(stop_time: float):
    """Performs continuous arithmetic calculations until stop_time is reached."""
    while time.time() < stop_time:
        _ = 999999 * 999999


def main():
    parser = argparse.ArgumentParser(description="Temporary safe CPU load generator for demo")
    parser.add_argument("--duration", type=int, default=15, help="Duration in seconds (default: 15s)")
    args = parser.parse_args()

    stop_time = time.time() + args.duration
    cores = multiprocessing.cpu_count()
    print(f"[*] Starting temporary CPU stress test on {cores} cores for {args.duration} seconds...")
    print("[*] Monitoring alerts should trigger when server_monitor.py runs.")

    processes = []
    for _ in range(cores):
        p = multiprocessing.Process(target=cpu_stress_worker, args=(stop_time,))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    print("[*] CPU stress test completed. System returning to idle.")


if __name__ == "__main__":
    main()
