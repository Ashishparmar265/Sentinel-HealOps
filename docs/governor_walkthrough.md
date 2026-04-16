# Exhaustive Walkthrough: `governor/action-webhook.py`

This document explains the final layer of the Sentinel-HealOps loop: The Governor.
The Governor runs alongside our infrastructure natively or as a GitHub Action runner to intercept logic commands from the Python Brain and manipulate Kubernetes states.

---

## 1. Webhook Payload Binding

```python
class ActionRequest(BaseModel):
    action: str
    target: str = "healops-engine"
```
- **`pydantic.BaseModel`**: Validates the payload schemas from the Brain automatically. It restricts incoming traffic to requiring at least an `action` string (e.g. `RESTART`).
- **`target`**: A default deployment target in Kubernetes.

---

## 2. Command Evaluation (`/webhook`)

```python
@app.post("/webhook")
async def trigger_action(req: ActionRequest):
    if req.action == "RESTART":
        cmd = ["kubectl", "rollout", "restart", f"deployment/{req.target}"] # [1]
    elif req.action == "ROLLBACK":
        cmd = ["kubectl", "rollout", "undo", f"deployment/{req.target}"] # [2]
```
- **[1] Restart**: This triggers a rolling restart in Kubernetes. If we observed an anomalous `CPU_SPIKE`, we restart the containers sequentially, ensuring no downtime, but fully wiping the memory slate.
- **[2] Rollback (Undo)**: If the anomaly was defined as `NETWORK_DELAY` immediately after a deployment upgrade, it's safer to undo the deployment back to the last stable replica-set explicitly.

---

## 3. Subprocess Execution

```python
        result = subprocess.run(cmd, capture_output=True, text=True, check=True) # [3]
```
- **[3] `subprocess.run`**: We execute the shell array natively. 
   - `capture_output=True` captures stdout/stderr into the `result` context so we can return it as an HTTP result.
   - `check=True` ensures Python raises an exception (`CalledProcessError`) if `kubectl` returns a non-zero exit code (failure).

```python
    except FileNotFoundError: # [4]
        return {"status": "mock_success", "remediated": True, "output": f"Mock executed..."}
```
- **[4] Mock Fallback**: As Sentinel-HealOps was initially designed as an MVP demo outside of dedicated Kubernetes clusters, we safely trap `FileNotFoundError` (missing `kubectl`). This allows us to simulate and guarantee the webhook routing behavior even inside pure Python VMs.

---

*This concludes the MVP backend pipeline tracing.*
