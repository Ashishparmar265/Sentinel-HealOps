from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import logging
import json
import urllib.request
import pickle
import os
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | [Brain] | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="HealOps Brain", description="Autonomous Anomaly Classification Engine")

# Mapping of model labels to fault types and remediation actions
# 0: HEALTHY, 1: CPU_SPIKE, 2: NETWORK_DELAY, 3: MEMORY_LEAK
FAULT_REGISTRY = {
    0: {"type": "HEALTHY",      "action": "NOOP"},
    1: {"type": "CPU_SPIKE",    "action": "RESTART"},
    2: {"type": "NETWORK_DELAY","action": "ROLLBACK"},
    3: {"type": "MEMORY_LEAK",  "action": "RESTART"}
}

# Deployment targets loaded from governor/targets.json
# To monitor a new service, add it to that file — no code changes needed.
_TARGETS_FILE = "governor/targets.json"
if os.path.exists(_TARGETS_FILE):
    with open(_TARGETS_FILE) as _f:
        TARGET_REGISTRY = {k: v for k, v in json.load(_f).items() if not k.startswith("_")}
else:
    TARGET_REGISTRY = {"default": "healops-engine"}

# Load the trained model
MODEL_PATH = "brain/models/classifier.pkl"
clf = None

if os.path.exists(MODEL_PATH):
    with open(MODEL_PATH, 'rb') as f:
        clf = pickle.load(f)
    logger.info(f"Loaded classifier from {MODEL_PATH}")
else:
    logger.warning(f"No model found at {MODEL_PATH}. Using fallback logic.")

class Anomaly(BaseModel):
    timestamp_ns: int
    buy_id: int
    sell_id: int
    latency_ms: float
    z_score: float
    fault_type: str
    source: str = "default"   # "engine" | "sentinelarc" | "default"

@app.post("/ingest")
async def ingest_anomaly(anomaly: Anomaly):
    logger.warning(f"Ingesting Anomaly Trace: Z={anomaly.z_score:.2f} | Latency={anomaly.latency_ms:.1f}ms | Source={anomaly.source}")
    
    if clf:
        X = np.array([[anomaly.latency_ms, anomaly.z_score]])
        label = int(clf.predict(X)[0])
        info = FAULT_REGISTRY.get(label, {"type": "UNKNOWN", "action": "NOOP"})
    else:
        # Fallback heuristic
        if anomaly.latency_ms > 50.0:
            info = FAULT_REGISTRY[2] # NETWORK_DELAY -> ROLLBACK
        else:
            info = FAULT_REGISTRY[1] # CPU_SPIKE -> RESTART
            
    # Resolve which K8s deployment to remediate based on anomaly source
    target = TARGET_REGISTRY.get(anomaly.source, TARGET_REGISTRY["default"])
    logger.info(f"Classification Result: {info['type']} -> Action: {info['action']} -> Target: {target}")
    
    if info["action"] != "NOOP":
        try:
            req_data = json.dumps({"action": info["action"], "target": target}).encode("utf-8")
            req = urllib.request.Request("http://127.0.0.1:8080/webhook", data=req_data, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req) as response:
                logger.info(f"Triggered Governor Response: {response.read().decode('utf-8')}")
        except Exception as e:
            logger.error(f"Failed to trigger Governor Webhook: {e}")
            
    return {
        "status": "processed",
        "source": anomaly.source,
        "target": target,
        "trade_ids": [anomaly.buy_id, anomaly.sell_id],
        "classification": info["type"],
        "remediation_action": info["action"]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
