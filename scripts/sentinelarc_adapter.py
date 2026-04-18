#!/usr/bin/env python3
"""
SentinelARC → Sentinel-HealOps Adapter
=======================================
Polls SentinelARC's MCP microserver health endpoints and translates 
per-request response times into the Sentinel-HealOps CSV trace format.
The Interceptor's io_uring tail then streams these rows in real-time.

Usage:
    python3 scripts/sentinelarc_adapter.py --host 127.0.0.1 --port 8001
"""

import argparse
import csv
import time
import urllib.request
import urllib.error
import os
import json
from pathlib import Path

TRACE_LOG = Path("/tmp/healops_sentinel_arc.csv")
FIELDNAMES = ["timestamp_ns", "buy_id", "sell_id", "price", "qty", "latency_ns"]

# SentinelARC MCP endpoints to probe (adjust ports to your deployment)
ENDPOINTS = [
    "http://{host}:{port}/health",
    "http://{host}:{port}/metrics",
]


def probe_endpoint(url: str) -> float:
    """Send a HEAD request and return round-trip time in nanoseconds."""
    t0 = time.time_ns()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2):
            pass
    except (urllib.error.URLError, Exception):
        # Even a refused connection has a measurable latency
        pass
    return float(time.time_ns() - t0)


def run(host: str, port: int, interval_ms: int):
    TRACE_LOG.parent.mkdir(parents=True, exist_ok=True)
    file_exists = TRACE_LOG.exists()

    probe_id = 1

    with open(TRACE_LOG, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()

        print(f"[SentinelARC-Adapter] Polling {host}:{port} every {interval_ms}ms")
        print(f"[SentinelARC-Adapter] Writing traces to {TRACE_LOG}")

        while True:
            for endpoint_tmpl in ENDPOINTS:
                url = endpoint_tmpl.format(host=host, port=port)
                latency_ns = probe_endpoint(url)

                row = {
                    "timestamp_ns": time.time_ns(),
                    "buy_id":       probe_id,        # reuse field as probe_id
                    "sell_id":      probe_id + 1,
                    "price":        0.0,              # N/A for HTTP probes
                    "qty":          1,
                    "latency_ns":   latency_ns,
                }
                writer.writerow(row)
                f.flush()

                latency_ms = latency_ns / 1e6
                status = "OK" if latency_ms < 10 else "⚡ SPIKE"
                print(f"[SentinelARC-Adapter] {url} → {latency_ms:.2f}ms {status}")
                probe_id += 2

            time.sleep(interval_ms / 1000)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SentinelARC → HealOps Metrics Adapter")
    parser.add_argument("--host",     default="127.0.0.1", help="SentinelARC MCP host")
    parser.add_argument("--port",     type=int, default=8001, help="SentinelARC MCP port")
    parser.add_argument("--interval", type=int, default=500,  help="Poll interval in ms")
    args = parser.parse_args()
    run(args.host, args.port, args.interval)
