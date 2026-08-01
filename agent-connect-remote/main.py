from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
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

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(title="Agent Connect Remote - JIT SSM Access")


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
