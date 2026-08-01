from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.access_control import access_control
from backend.agent import chat
from backend.db import run_migrations
from backend.onboarding import (
    create_hybrid_activation,
    get_activation_commands,
    verify_managed_instance,
    verify_managed_instance_by_id,
)
from backend.pingram_handler import (
    handle_inbound_email,
    get_active_session,
    end_session,
    _active_sessions,
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(title="Agent Connect Remote - JIT SSM Access")

STATIC_DIR = Path(__file__).parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
async def wipe_machines_on_startup():
    from backend.db import get_cursor
    logger = logging.getLogger(__name__)
    with get_cursor() as cur:
        cur.execute("DELETE FROM customer_machines")
        logger.info("Wiped customer_machines table on startup")


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None
    grant_id: str | None = None


class AccessRequest(BaseModel):
    customer_id: str
    duration_minutes: int = 10


class ApproveRequest(BaseModel):
    grant_id: str
    approved_by: str


class RevokeRequest(BaseModel):
    grant_id: str
    revoked_by: str
    reason: str = ""


@app.on_event("startup")
async def startup():
    run_migrations()


@app.get("/")
async def root():
    return {"status": "ok", "service": "agent-connect-remote"}


@app.get("/agent.html")
async def serve_agent_html():
    agent_path = STATIC_DIR / "agent.html"
    if not agent_path.exists():
        raise HTTPException(status_code=404, detail="agent.html not found")
    return FileResponse(agent_path)


@app.get("/audio-processors/{filename}")
async def serve_audio_processor(filename: str):
    processor_path = STATIC_DIR / "audio-processors" / filename
    if not processor_path.exists():
        raise HTTPException(status_code=404, detail=f"{filename} not found")
    return FileResponse(processor_path)


@app.post("/api/token")
async def get_gemini_token():
    import datetime
    import os
    from google import genai
    
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")
    
    client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
    
    try:
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        expire_time = now + datetime.timedelta(minutes=30)
        
        token = client.auth_tokens.create(
            config={
                "uses": 1,
                "expire_time": expire_time.isoformat(),
                "new_session_expire_time": (now + datetime.timedelta(minutes=2)).isoformat(),
                "http_options": {"api_version": "v1alpha"},
            }
        )
        
        return {
            "token": token.name,
            "model": "gemini-3.1-flash-live-preview",
            "expires_at": expire_time.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    try:
        response = await chat(req.message, req.thread_id, req.grant_id)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RegisterMachineRequest(BaseModel):
    customer_id: str
    managed_node_id: str
    machine_name: str | None = None


@app.post("/onboarding/create-activation")
async def create_activation(customer_id: str):
    activation = create_hybrid_activation(customer_id)
    commands = get_activation_commands(
        activation["activation_id"],
        activation["activation_code"],
    )
    return {
        **activation,
        "setup_commands": commands,
    }


@app.post("/onboarding/register")
async def register_machine(req: RegisterMachineRequest):
    from backend.db import get_cursor
    
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO customer_machines (customer_id, managed_node_id, machine_name, is_active)
            VALUES (%s, %s, %s, true)
            ON CONFLICT (managed_node_id) DO UPDATE
            SET customer_id = EXCLUDED.customer_id,
                machine_name = EXCLUDED.machine_name,
                is_active = true,
                last_ping_at = now()
            """,
            (req.customer_id, req.managed_node_id, req.machine_name),
        )
    
    return {"status": "registered", "customer_id": req.customer_id, "managed_node_id": req.managed_node_id}


@app.post("/onboarding/verify/{customer_id}")
async def verify_instance(customer_id: str):
    from backend.db import get_cursor
    
    # Check DB first
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT managed_node_id, machine_name, last_ping_at
            FROM customer_machines
            WHERE customer_id = %s AND is_active = true
            LIMIT 1
            """,
            (customer_id,),
        )
        db_record = cur.fetchone()
    
    if db_record:
        # Verify with SSM that it's still online
        instance = verify_managed_instance_by_id(db_record["managed_node_id"])
        if instance:
            return {
                **instance,
                "machine_name": db_record.get("machine_name"),
                "registered_in_db": True,
            }
        else:
            return {
                "managed_node_id": db_record["managed_node_id"],
                "status": "offline",
                "message": "Machine registered in DB but not found in SSM",
            }
    
    # Fallback: check SSM directly
    instance = verify_managed_instance(customer_id)
    if not instance:
        raise HTTPException(status_code=404, detail="No managed instance found")
    return instance


@app.post("/access/request")
async def request_access(req: AccessRequest):
    grant_id = access_control.request_access(
        customer_id=req.customer_id,
        requested_by="agent",
        duration_minutes=req.duration_minutes,
    )
    return {"grant_id": grant_id, "status": "pending"}


@app.post("/access/approve")
async def approve_access(req: ApproveRequest):
    grant = access_control.approve_access(req.grant_id, req.approved_by)
    return {
        "grant_id": grant.id,
        "status": grant.status,
        "expires_at": grant.expires_at.isoformat(),
    }


@app.post("/access/revoke")
async def revoke_access(req: RevokeRequest):
    access_control.revoke_access(req.grant_id, req.revoked_by, req.reason)
    return {"status": "revoked"}


@app.get("/access/status/{grant_id}")
async def get_status(grant_id: str):
    status = access_control.get_grant_status(grant_id)
    if not status:
        raise HTTPException(status_code=404, detail="Grant not found")
    return status


@app.post("/webhook/pingram")
async def pingram_webhook(payload: dict):
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Pingram webhook received: {payload}")
    
    # Try multiple possible field names for event type
    event_type = payload.get("eventType") or payload.get("type") or payload.get("event") or payload.get("event_type") or ""
    logger.info(f"Event type: {event_type}")
    
    if event_type == "EMAIL_INBOUND":
        result = await handle_inbound_email(payload)
        return result
    return {"status": "ignored", "event_type": event_type, "payload_keys": list(payload.keys())}


@app.post("/webhook/test")
async def test_webhook(payload: dict):
    """Test endpoint to manually trigger email processing"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Test webhook: {payload}")
    
    # Extract email from various possible fields
    from_email = (
        payload.get("from") or 
        payload.get("sender") or 
        payload.get("email") or
        payload.get("to") or  # might be in 'to' field
        "test@example.com"
    )
    
    # Check if it's nested
    if isinstance(payload.get("message"), dict):
        from_email = payload["message"].get("from", from_email)
    
    logger.info(f"Test webhook from_email: {from_email}")
    
    result = await handle_inbound_email({"from": from_email, "type": "EMAIL_INBOUND"})
    return result


@app.get("/sessions")
async def list_sessions():
    return {"sessions": list(_active_sessions.values())}


@app.get("/sessions/{agent_id}")
async def get_session(agent_id: str):
    session = get_active_session(agent_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.post("/sessions/{agent_id}/end")
async def end_session_endpoint(agent_id: str):
    session = end_session(agent_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "ended", "agent_id": agent_id}
