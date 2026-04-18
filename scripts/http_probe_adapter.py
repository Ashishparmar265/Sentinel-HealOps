#!/usr/bin/env python3
"""
HealOps HTTP Probe Adapter
==========================
A generic adapter that probes any HTTP microservice and emits latency
traces in the Sentinel-HealOps Interceptor-compatible CSV format.

Works with any FastAPI, Flask, Express, or HTTP-compliant service.
To monitor a new service, just point this at it — no code changes needed.

Usage:
    python3 scripts/http_probe_adapter.py \\
        --service-name my-service \\
        --host 127.0.0.1 \\
        --port 8001 \\
        --endpoints /health /metrics \\
        --interval 500

Output:
    /tmp/healops_<service-name>.csv  (auto-tailed by the Interceptor)
"""

import argparse
import csv
import time
import urllib.request
import urllib.error
import os
from pathlib import Path

FIELDNAMES = ["timestamp_ns", "buy_id", "sell_id", "price", "qty", "latency_ns"]


def probe_endpoint(url: str) -> float:
    """Probe a URL and return round-trip latency in nanoseconds."""
    t0 = time.time_ns()
    try:
        with urllib.request.urlopen(url, timeout=2):
            pass
    except Exception:
        pass  # Even a refused connection has measurable latency
    return float(time.time_ns() - t0)


def run(service_name: str, host: str, port: int, endpoints: list, interval_ms: int):
    trace_log = Path(f"/tmp/healops_{service_name}.csv")
    trace_log.parent.mkdir(parents=True, exist_ok=True)
    file_exists = trace_log.exists()

    probe_id = 1

    with open(trace_log, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()

        base_url = f"http://{host}:{port}"
        print(f"[HealOps-Probe] Monitoring: {base_url}")
        print(f"[HealOps-Probe] Service name: {service_name}")
        print(f"[HealOps-Probe] Endpoints: {endpoints}")
        print(f"[HealOps-Probe] Interval: {interval_ms}ms → {trace_log}\n")

        while True:
            for path in endpoints:
                url = f"{base_url}{path}"
                latency_ns = probe_endpoint(url)
                latency_ms = latency_ns / 1e6

                writer.writerow({
                    "timestamp_ns": time.time_ns(),
                    "buy_id":       probe_id,
                    "sell_id":      probe_id + 1,
                    "price":        0.0,
                    "qty":          1,
                    "latency_ns":   latency_ns,
                })
                f.flush()

                badge = "✅" if latency_ms < 10 else "⚡ SPIKE"
                print(f"[HealOps-Probe] {url} → {latency_ms:.2f}ms {badge}")
                probe_id += 2

            time.sleep(interval_ms / 1000)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HealOps Generic HTTP Probe Adapter")
    parser.add_argument("--service-name", required=True, help="Service identifier (e.g. my-api)")
    parser.add_argument("--host",         default="127.0.0.1", help="Target host")
    parser.add_argument("--port",         type=int, required=True, help="Target port")
    parser.add_argument("--endpoints",    nargs="+", default=["/health"], help="Paths to probe")
    parser.add_argument("--interval",     type=int, default=500, help="Poll interval in ms")
    args = parser.parse_args()

    run(args.service_name, args.host, args.port, args.endpoints, args.interval)
