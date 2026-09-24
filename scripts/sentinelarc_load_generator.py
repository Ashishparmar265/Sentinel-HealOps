#!/usr/bin/env python3
"""
Load generator for the SentinelARC system.
Writes synthetic task events with latency to a log file that Sentinel-HealOps intercepts.
"""

import argparse
import csv
import random
import time
from pathlib import Path

TRADE_LOG = Path("/tmp/sentinelarc_events.csv")

def generate_event(event_id: int, inject_fault: bool = False) -> dict:
    # Simulated SentinelARC operations: CRIU resume, FastAPI endpoint, RMQ task
    base_latency_ns = random.gauss(2_000_000, 500_000)  # ~2ms normal latency

    if inject_fault:
        base_latency_ns *= random.uniform(10, 50)  # 20ms - 100ms stall

    latency_ns = max(1_000_000, int(base_latency_ns))
    ts = time.time_ns()

    return {
        "timestamp_ns": ts,
        "event_id": event_id,
        "agent_id": event_id % 10,
        "operation": "criu_restore",
        "status": "success",
        "latency_ns": latency_ns,
    }

def run(rate: int, duration: int, fault_probability: float):
    TRADE_LOG.parent.mkdir(parents=True, exist_ok=True)
    file_exists = TRADE_LOG.exists()
    
    with open(TRADE_LOG, "a", newline="") as f:
        # We reuse the same format interceptor expects to avoid changing the C++ CSV parser
        # Expects: timestamp_ns, buy_id, sell_id, price, qty, latency_ns
        writer = csv.DictWriter(
            f, fieldnames=["timestamp_ns", "buy_id", "sell_id", "price", "qty", "latency_ns"]
        )
        if not file_exists:
            writer.writeheader()

        interval = 1.0 / rate
        event_id = 1
        start = time.time()
        total = 0
        faults = 0

        print(f"[SentinelARC Gen] Generating {rate} events/sec for {duration}s ...")
        
        while time.time() - start < duration:
            inject = random.random() < fault_probability
            evt = generate_event(event_id, inject_fault=inject)
            
            # Map event to the CSV format expected by interceptor.cpp
            row = {
                "timestamp_ns": evt["timestamp_ns"],
                "buy_id": evt["event_id"],
                "sell_id": evt["agent_id"],
                "price": 0.0,
                "qty": 0,
                "latency_ns": evt["latency_ns"]
            }
            writer.writerow(row)
            f.flush()
            event_id += 1
            total += 1
            if inject:
                faults += 1
                print(f"[SentinelARC Gen] ⚡ Stall injected! latency={row['latency_ns']/1e6:.1f}ms")

            time.sleep(interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SentinelARC Load Generator")
    parser.add_argument("--rate", type=int, default=100, help="Events per second")
    parser.add_argument("--duration", type=int, default=30, help="Run duration in seconds")
    parser.add_argument("--fault-prob", type=float, default=0.05, help="Fault probability")
    args = parser.parse_args()
    run(args.rate, args.duration, args.fault_prob)
