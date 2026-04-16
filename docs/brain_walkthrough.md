# Exhaustive Walkthrough: `brain/main.py` & `model.py`

This document explains the Python-based AI Control Plane (Phase 2) line-by-line.

---

## 1. `brain/model.py` (The Model Training)

This script creates the "AI Brain" from scratch using synthetic data.

```python
def generate_training_data(n_samples=5000):
    # ...
    lat = np.random.normal(15.0, 2.0) # [1]
    z = (lat - 0.5) / 0.1 # [2]
```
- **[1] `np.random.normal`**: We use a Normal Distribution (Gaussian) to simulate realistic latencies. For a CPU spike, we assume an average of 15ms.
- **[2] `z = (lat - 0.5) / 0.1`**: We calculate the Z-score exactly as the C++ sidecar does. This ensures the training data matches the real-world input.

```python
clf = RandomForestClassifier(n_estimators=100) # [3]
clf.fit(X, y)
```
- **[3] Random Forest**: A robust ensemble model. 100 "trees" vote on the outcome. It's extremely fast and handles the high-variance latency data very well.

---

## 2. `brain/main.py` (The Live API)

This file is the decision engine that receives data from C++.

```python
FAULT_REGISTRY = {
    1: {"type": "CPU_SPIKE", "action": "RESTART"}, # [4]
```
- **[4] Registry**: We map model labels (0, 1, 2) to human-readable types and specific "Remediation Actions". This decouples the AI prediction from the actual infrastructure logic.

```python
@app.post("/ingest")
async def ingest_anomaly(anomaly: Anomaly): # [5]
```
- **[5] `Anomaly` Model**: A Pydantic model that validates the incoming JSON from the C++ side. If the C++ side sends a string where it should be a number, FastAPI automatically returns an error (422).

```python
X = np.array([[anomaly.latency_ms, anomaly.z_score]]) # [6]
label = int(clf.predict(X)[0]) # [7]
```
- **[6] Feature Vector**: We convert the JSON data into a NumPy array, which is the input format required by scikit-learn.
- **[7] `clf.predict`**: The model makes a prediction in **microseconds**. This is critical because the remediation shouldn't take longer than the anomaly discovery.

---

## 3. The "Ifs" and "Buts" of Phase 2

- **"If" the model isn't trained yet?**
    - The code includes a check: `if os.path.exists(MODEL_PATH)`. If the file is missing, it falls back to a simple `if latency > 50` heuristic.
- **"But" what about data drift?**
    - If the trading engine's baseline latency changes (e.g., after an upgrade), the old model might start flagging everything as an anomaly.
    - **Future Scope**: Implementation of a "Re-training Pipeline" that periodically updates the model with the latest stable traffic.
- **"Why" use FastAPI?**
    - FastAPI uses `uvicorn` and `asyncio`, making it much faster than older frameworks like Flask. It can handle hundreds of anomaly events per second without breaking a sweat.

---

*[DEEP DIVE: Line-by-Line Governor Walkthrough](file:///home/iiitl/Documents/Sentinel-HealOps/docs/governor_walkthrough.md)*
