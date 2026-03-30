#!/usr/bin/env python3
"""
Load generator for the C++ Order Matching Engine.
Writes synthetic FIX-encoded order messages to a named pipe / TCP socket
that the engine can consume. For MVP, it appends trade log lines directly.

Usage:
    python3 scripts/load_generator.py --rate 10000 --duration 30
"""

import argparse
import csv
import math
import random
import time
import os
from pathlib import Path

TRADE_LOG = Path("/tmp/healops_trades.csv")


def generate_trade(order_id: int, inject_fault: bool = False) -> dict:
    """Simulate a matched trade with optional latency spike."""
    base_latency_ns = random.gauss(500_000, 50_000)  # ~0.5ms ± 0.05ms

    if inject_fault:
        # Inject a 10–50x latency spike to test anomaly detection
        base_latency_ns *= random.uniform(10, 50)

    latency_ns = max(100_000, int(base_latency_ns))
    price = round(random.uniform(99.0, 101.0), 2)
    qty = random.randint(1, 100)
    ts = time.time_ns()

    return {
        "timestamp_ns": ts,
        "buy_id": order_id,
        "sell_id": order_id + 1,
        "price": price,
        "qty": qty,
        "latency_ns": latency_ns,
    }


def run(rate: int, duration: int, fault_probability: float):
    TRADE_LOG.parent.mkdir(parents=True, exist_ok=True)

    file_exists = TRADE_LOG.exists()
    with open(TRADE_LOG, "a", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["timestamp_ns", "buy_id", "sell_id", "price", "qty", "latency_ns"]
        )
        if not file_exists:
            writer.writeheader()

        interval = 1.0 / rate
        order_id = 1
        start = time.time()
        total = 0
        faults = 0

        print(f"[LoadGen] Generating {rate} trades/sec for {duration}s ...")
        print(f"[LoadGen] Fault probability: {fault_probability*100:.1f}%")
        print(f"[LoadGen] Writing to: {TRADE_LOG}\n")

        while time.time() - start < duration:
            inject = random.random() < fault_probability
            row = generate_trade(order_id, inject_fault=inject)
            writer.writerow(row)
            f.flush()
            order_id += 2
            total += 1
            if inject:
                faults += 1
                print(f"[LoadGen] ⚡ Fault injected! latency={row['latency_ns']/1e6:.1f}ms")

            time.sleep(interval)

    print(f"\n[LoadGen] Done. Total trades: {total}, Fault events: {faults}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HealOps Load Generator")
    parser.add_argument("--rate", type=int, default=1000, help="Orders per second")
    parser.add_argument("--duration", type=int, default=60, help="Run duration in seconds")
    parser.add_argument("--fault-prob", type=float, default=0.02, help="Fault injection probability (0.0–1.0)")
    args = parser.parse_args()

    run(args.rate, args.duration, args.fault_prob)
