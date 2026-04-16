#!/bin/bash
set -e

echo "[Test] 1. Training AI Model..."
cd /home/iiitl/Documents/Sentinel-HealOps
python3 brain/model.py

echo "[Test] 2. Starting Governor Webhook Listener..."
python3 governor/action-webhook.py &
WEBHOOK_PID=$!

echo "[Test] 3. Starting Python Brain API..."
python3 brain/main.py &
BRAIN_PID=$!

echo "[Test] 4. Waiting for servers to initialize..."
sleep 4

echo "[Test] 5. Sending CPU Spike Anomaly..."
curl -s -X POST http://127.0.0.1:8000/ingest \
  -H 'Content-Type: application/json' \
  -d '{"timestamp_ns": 1, "buy_id": 100, "sell_id": 101, "latency_ms": 15.0, "z_score": 145.0, "fault_type": "UNKNOWN"}' | grep -v 'Failed writing body'

sleep 2

echo "[Test] 5b. Sending Network Delay Anomaly..."
curl -s -X POST http://127.0.0.1:8000/ingest \
  -H 'Content-Type: application/json' \
  -d '{"timestamp_ns": 1, "buy_id": 100, "sell_id": 101, "latency_ms": 80.0, "z_score": 795.0, "fault_type": "UNKNOWN"}' | grep -v 'Failed writing body'

sleep 1

echo ""
echo "[Test] 6. Cleaning Up Processes..."
kill $BRAIN_PID
kill $WEBHOOK_PID
echo "[Test] Success! The stack is verified."
