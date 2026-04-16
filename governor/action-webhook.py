import os
import subprocess
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(
    title="HealOps Governor Webhook",
    description="Simulates a GitHub Actions runner receiving remediation webhooks from the Brain."
)

class ActionRequest(BaseModel):
    action: str
    target: str = "healops-engine"

@app.post("/webhook")
async def trigger_action(req: ActionRequest):
    """
    Receives an action (e.g., RESTART, ROLLBACK) and translates it into
    a local Kubernetes command to heal the system.
    """
    print(f"[Governor] Received webhook action: '{req.action}' targeting '{req.target}'")
    
    # Map AI model actions to shell commands
    if req.action == "RESTART":
        cmd = ["kubectl", "rollout", "restart", f"deployment/{req.target}"]
    elif req.action == "ROLLBACK":
        cmd = ["kubectl", "rollout", "undo", f"deployment/{req.target}"]
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")
        
    try:
        print(f"[Governor] Executing shell command: {' '.join(cmd)}")
        # Execute the kubectl command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"[Governor] Command Success:\n{result.stdout}")
        return {"status": "success", "remediated": True, "output": result.stdout}
    
    except subprocess.CalledProcessError as e:
        print(f"[Governor] Command Failed:\n{e.stderr}")
        raise HTTPException(status_code=500, detail=f"Failed to execute {cmd[0]}: {e.stderr}")
    except FileNotFoundError:
         print(f"[Governor] Error: `kubectl` binary not found. Are you running this in the correct environment?")
         # Fallback mock for pure local testing without Kubernetes cluster installed
         print(f"[Governor] Mocking success of {' '.join(cmd)} for demonstration purposes.")
         return {"status": "mock_success", "remediated": True, "output": f"Mock executed {' '.join(cmd)}"}

if __name__ == "__main__":
    port = int(os.environ.get("GOVERNOR_PORT", 8080))
    print(f"Starting Governor webhook listener on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
