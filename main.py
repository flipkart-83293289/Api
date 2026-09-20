from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import uvicorn

app = FastAPI(
    title="Device Security Controller",
    docs_url=None,
    redoc_url=None
)

SECRET_API_KEY = "Dev69_SecureAuth_Token_987654321_X"

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != SECRET_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized Access - Invalid Secret Key")
    return x_api_key

pending_commands = []
latest_telemetry = {"status": "NO_DATA", "timestamp": 0}

class TelemetryPayload(BaseModel):
    deviceId: str
    timestamp: int
    batteryLevel: int
    status: str

class CommandResponse(BaseModel):
    command: Optional[str] = None
    payload: Optional[str] = None

class CommandIssue(BaseModel):
    command: str
    payload: Optional[str] = None

@app.get("/")
def health_check():
    return {"status": "online", "message": "Server is active"}

@app.post("/api/v1/telemetry", status_code=200)
async def receive_telemetry(data: TelemetryPayload, api_key: str = Depends(verify_api_key)):
    global latest_telemetry
    latest_telemetry = data.dict()
    return {"status": "success"}

@app.get("/api/v1/command/fetch", response_model=CommandResponse)
async def fetch_pending_commands(api_key: str = Depends(verify_api_key)):
    if pending_commands:
        cmd = pending_commands.pop(0)
        return cmd
    return CommandResponse(command=None, payload=None)

@app.post("/api/v1/command/issue")
async def issue_command(cmd: CommandIssue, api_key: str = Depends(verify_api_key)):
    pending_commands.append({"command": cmd.command, "payload": cmd.payload})
    return {"status": "queued", "command": cmd.command}

if name == "main":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
