from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.access_control import access_control
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
from backend.tenant_service import (
    get_or_create_tenant,
    get_tenant_by_email,
    get_tenant_by_id,
    get_tenant_by_customer_id,
    list_tenants,
    get_session_history,
    get_previous_context,
    get_tool_call_logs,
    get_weekly_insights,
)
from backend.tool_config import (
    get_task_profile,
    list_task_profiles,
    create_task_profile,
)
from backend.worker_agent import worker_chat

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

TEST_DIR = Path(__file__).parent.parent / "test"
if TEST_DIR.exists():
    app.mount("/test", StaticFiles(directory=TEST_DIR, html=True), name="test")


@app.get("/test")
async def serve_test_page():
    test_path = TEST_DIR / "index.html"
    if not test_path.exists():
        raise HTTPException(status_code=404, detail="test page not found")
    return FileResponse(test_path)


@app.on_event("startup")
async def wipe_machines_on_startup():
    from backend.db import get_cursor
    logger = logging.getLogger(__name__)
    with get_cursor() as cur:
        cur.execute("DELETE FROM customer_machines")
        logger.info("Wiped customer_machines table on startup")
    
    import asyncio
    asyncio.create_task(stale_session_cleanup_loop())


async def stale_session_cleanup_loop():
    """Periodically end sessions that have been inactive for too long."""
    import asyncio
    logger = logging.getLogger(__name__)
    
    while True:
        try:
            await asyncio.sleep(300)
            
            from backend.db import get_cursor
            with get_cursor() as cur:
                cur.execute(
                    """
                    UPDATE session_history
                    SET resolution_status = 'timeout', ended_at = now()
                    WHERE ended_at IS NULL
                    AND started_at < NOW() - INTERVAL '30 minutes'
                    AND id NOT IN (
                        SELECT DISTINCT session_id 
                        FROM tool_call_logs 
                        WHERE created_at > NOW() - INTERVAL '30 minutes'
                    )
                    RETURNING agent_id, id
                    """
                )
                ended = cur.fetchall()
                if ended:
                    logger.info(f"Cleaned up {len(ended)} stale sessions")
        except Exception as e:
            logger.error(f"Stale session cleanup error: {e}")


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None
    grant_id: str | None = None
    email: str = ""
    task_context: str = ""
    agent_id: str = ""


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


class RegisterMachineRequest(BaseModel):
    customer_id: str
    managed_node_id: str
    machine_name: str | None = None


class TaskProfileRequest(BaseModel):
    name: str
    description: str = ""
    allowed_tools: list[str] | None = None
    restricted_tools: list[str] | None = None
    requires_escalation: list[str] | None = None
    default_commands: list[str] | None = None
    escalation_commands: list[str] | None = None


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


@app.get("/test_agent.html")
async def serve_test_agent_html():
    test_path = STATIC_DIR / "test_agent.html"
    if not test_path.exists():
        raise HTTPException(status_code=404, detail="test_agent.html not found")
    return FileResponse(test_path)


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


class ExecuteCommandRequest(BaseModel):
    command: str
    grant_id: str
    agent_id: str


class TaskRequest(BaseModel):
    task_description: str
    grant_id: str
    agent_id: str
    email: str = ""


@app.post("/task")
async def execute_task(req: TaskRequest):
    """Execute a task using Groq agent for planning and execution."""
    import time
    from backend.worker_agent import execute_task_with_groq
    
    try:
        result = await execute_task_with_groq(
            task_description=req.task_description,
            grant_id=req.grant_id,
            agent_id=req.agent_id,
        )
        return result
    except Exception as e:
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Task execution error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Task failed: {str(e)}")


@app.post("/task/stream")
async def execute_task_stream(req: TaskRequest):
    """Start a task and return task_id for SSE streaming."""
    from backend.worker_agent import execute_task_streaming
    
    try:
        task_id, _ = await execute_task_streaming(
            task_description=req.task_description,
            grant_id=req.grant_id,
            agent_id=req.agent_id,
            email=req.email,
        )
        return {"task_id": task_id, "status": "started"}
    except Exception as e:
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Task stream error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Task failed: {str(e)}")


@app.get("/task/{task_id}/events")
async def task_events(task_id: str):
    """SSE endpoint for streaming task events."""
    from backend.worker_agent import _task_queues
    
    if task_id not in _task_queues:
        raise HTTPException(status_code=404, detail="Task not found")
    
    async def generate():
        queue = _task_queues[task_id]
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=300)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") in ("task_complete", "task_error"):
                    break
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        
        _task_queues.pop(task_id, None)
    
    return StreamingResponse(generate(), media_type="text/event-stream")


class ApprovalRequest(BaseModel):
    task_id: str
    approved: bool


@app.post("/task/approve")
async def approve_task_command(req: ApprovalRequest):
    """Approve or deny a destructive command."""
    from backend.worker_agent import approve_command
    approve_command(req.task_id, req.approved)
    return {"status": "approved" if req.approved else "denied"}


@app.post("/execute")
async def execute_command(req: ExecuteCommandRequest):
    import time
    from backend.access_control import access_control
    from backend.tool_config import is_destructive
    from backend.tenant_service import log_tool_call, get_tenant_by_email
    from backend.config import GROQ_MODEL
    
    try:
        if is_destructive(req.command):
            return {
                "response": f"ESCALATION_REQUIRED: Command '{req.command}' is destructive and requires explicit customer approval.",
                "status": "escalation_required"
            }
        
        start_time = time.time()
        result = await access_control.execute_command(
            grant_id=req.grant_id,
            command=req.command,
            executed_by=req.agent_id,
        )
        duration_ms = int((time.time() - start_time) * 1000)
        
        if result["status"] == "Success":
            output = result["stdout"].strip()
            log_tool_call(
                tool_name="run_command",
                tool_args={"command": req.command},
                tool_result=output[:2000] if output else "(no output)",
                status="success",
                duration_ms=duration_ms,
                model_used="direct",
                agent_id=req.agent_id,
                grant_id=req.grant_id,
            )
            return {"response": output if output else "(no output)", "status": "success"}
        else:
            error_msg = result["stderr"] or result["status"]
            log_tool_call(
                tool_name="run_command",
                tool_args={"command": req.command},
                tool_result=error_msg,
                status="failed",
                duration_ms=duration_ms,
                model_used="direct",
                agent_id=req.agent_id,
                grant_id=req.grant_id,
            )
            return {"response": f"Command failed: {error_msg}", "status": "failed"}
    except PermissionError as e:
        return {"response": f"Permission denied: {e}", "status": "permission_denied"}
    except Exception as e:
        return {"response": f"Error: {e}", "status": "error"}


@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    try:
        agent_id = req.agent_id or "agent-default"
        response = await worker_chat(
            message=req.message,
            grant_id=req.grant_id or "",
            agent_id=agent_id,
            email=req.email,
            task_context=req.task_context,
            thread_id=req.thread_id,
        )
        return {"response": response}
    except Exception as e:
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Chat error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


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
    logger = logging.getLogger(__name__)
    logger.info(f"Pingram webhook received: {payload}")

    event_type = payload.get("eventType") or payload.get("type") or payload.get("event") or payload.get("event_type") or ""
    logger.info(f"Event type: {event_type}")

    if event_type == "EMAIL_INBOUND":
        result = await handle_inbound_email(payload)
        return result
    return {"status": "ignored", "event_type": event_type, "payload_keys": list(payload.keys())}


@app.post("/webhook/test-pingram")
async def test_pingram_webhook(request: Request):
    import json
    from pathlib import Path
    
    logger = logging.getLogger(__name__)
    
    raw_body = await request.body()
    raw_text = raw_body.decode("utf-8")
    
    logger.info(f"=== TEST PINGRAM WEBHOOK ===")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"Raw body length: {len(raw_text)}")
    logger.info(f"Raw body: {raw_text[:2000]}")
    
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        payload = {"raw": raw_text}
    
    dump_file = Path(__file__).parent.parent / "webhook-dump.json"
    with open(dump_file, "w") as f:
        json.dump({
            "headers": dict(request.headers),
            "payload": payload,
            "raw": raw_text,
        }, f, indent=2, default=str)
    
    logger.info(f"Full payload dumped to: {dump_file}")
    
    from_email = (
        payload.get("from") or 
        payload.get("sender") or 
        payload.get("fromAddress") or
        payload.get("return_path") or
        ""
    )
    
    if isinstance(payload.get("message"), dict):
        from_email = payload["message"].get("from", from_email)
    
    email_body = (
        payload.get("body") or 
        payload.get("text") or 
        payload.get("html") or 
        payload.get("message_body") or 
        payload.get("content") or
        payload.get("message") or
        payload.get("description") or
        ""
    )
    
    if isinstance(email_body, dict):
        email_body = (
            email_body.get("text") or 
            email_body.get("html") or 
            email_body.get("body") or 
            str(email_body)
        )
    
    subject = payload.get("subject") or payload.get("title") or ""
    if isinstance(payload.get("message"), dict):
        subject = payload["message"].get("subject", subject)
    
    result = {
        "status": "received",
        "parsed": {
            "from_email": from_email,
            "subject": subject,
            "body_preview": str(email_body)[:500],
            "body_length": len(str(email_body)),
        },
        "raw_keys": list(payload.keys()) if isinstance(payload, dict) else "not-a-dict",
        "dump_file": str(dump_file),
    }
    
    logger.info(f"Parsed result: {json.dumps(result, indent=2)}")
    
    return result


@app.post("/webhook/test")
async def test_webhook(payload: dict):
    logger = logging.getLogger(__name__)
    logger.info(f"Test webhook: {payload}")

    from_email = (
        payload.get("from") or
        payload.get("sender") or
        payload.get("email") or
        payload.get("to") or
        "test@example.com"
    )

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


@app.get("/admin/tenants")
async def admin_list_tenants(limit: int = 100, offset: int = 0):
    tenants = list_tenants(limit=limit, offset=offset)
    return {"tenants": tenants, "total": len(tenants)}


@app.get("/admin/tenants/{tenant_id}")
async def admin_get_tenant(tenant_id: str):
    tenant = get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    sessions = get_session_history(tenant_id, limit=20)
    context = get_previous_context(tenant_id)

    return {
        "tenant": tenant,
        "sessions": sessions,
        "context_summary": context,
    }


@app.get("/admin/tenants/email/{email}")
async def admin_get_tenant_by_email(email: str):
    tenant = get_tenant_by_email(email)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    sessions = get_session_history(tenant["id"], limit=20)
    return {
        "tenant": tenant,
        "sessions": sessions,
    }


@app.get("/admin/sessions/{tenant_id}/history")
async def admin_session_history(tenant_id: str, limit: int = 20):
    sessions = get_session_history(tenant_id, limit=limit)
    return {"sessions": sessions}


@app.get("/admin/tool-logs")
async def admin_tool_logs(
    session_id: str | None = None,
    tenant_id: str | None = None,
    limit: int = 100,
):
    logs = get_tool_call_logs(session_id=session_id, tenant_id=tenant_id, limit=limit)
    return {"logs": logs}


@app.get("/admin/insights")
async def admin_insights():
    insights = get_weekly_insights()
    return insights


@app.get("/admin/active-agents")
async def admin_active_agents():
    agents = []
    for agent_id, session in _active_sessions.items():
        tenant = None
        if session.get("email"):
            tenant = get_tenant_by_email(session["email"])

        agents.append({
            "agent_id": agent_id,
            "customer_id": session.get("customer_id"),
            "email": session.get("email"),
            "tenant": tenant,
            "managed_node_id": session.get("managed_node_id"),
            "meet_url": session.get("meet_url"),
            "task_context": session.get("task_context"),
            "started_at": session.get("started_at"),
            "bot_id": session.get("bot_id"),
            "status": "active",
        })
    return {"active_agents": agents, "count": len(agents)}


@app.get("/admin/task-profiles")
async def admin_list_task_profiles():
    profiles = list_task_profiles()
    return {"profiles": profiles}


@app.post("/admin/task-profiles")
async def admin_create_task_profile(req: TaskProfileRequest):
    profile = create_task_profile(
        name=req.name,
        description=req.description,
        allowed_tools=req.allowed_tools,
        restricted_tools=req.restricted_tools,
        requires_escalation=req.requires_escalation,
        default_commands=req.default_commands,
        escalation_commands=req.escalation_commands,
    )
    return {"profile": profile}


@app.get("/admin/tenant-context/{email}")
async def get_tenant_context(email: str):
    tenant = get_or_create_tenant(email)
    context = get_previous_context(tenant["id"])
    return {"tenant": tenant, "context": context}


@app.get("/admin/dashboard.html")
async def serve_admin_dashboard():
    dashboard_path = STATIC_DIR / "admin.html"
    if not dashboard_path.exists():
        raise HTTPException(status_code=404, detail="admin.html not found")
    return FileResponse(dashboard_path)


@app.post("/webhook/recall")
async def recall_webhook(request: Request):
    """Handle Recall webhook for meeting end notifications."""
    try:
        payload = await request.json()
        logger.info(f"Recall webhook received: {payload}")
        
        event_type = payload.get("event", "")
        bot_id = payload.get("bot_id", "")
        
        if event_type == "meeting_ended":
            # Find agent by bot_id
            from backend.pingram_handler import _active_sessions
            agent_id = None
            session_data = None
            
            for aid, sdata in _active_sessions.items():
                if sdata.get("bot_id") == bot_id:
                    agent_id = aid
                    session_data = sdata
                    break
            
            if agent_id and session_data:
                from backend.meeting_end_handler import handle_meeting_end
                await handle_meeting_end(agent_id, session_data)
                return {"status": "processed", "agent_id": agent_id}
            else:
                logger.warning(f"No active session found for bot_id {bot_id}")
                return {"status": "no_session_found", "bot_id": bot_id}
        
        return {"status": "ignored", "event": event_type}
    
    except Exception as e:
        logger.error(f"Recall webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sessions/{agent_id}/end")
async def manual_end_session(agent_id: str):
    """End a session - triggers full cleanup flow including email confirmation."""
    from backend.pingram_handler import _active_sessions
    from backend.db import get_cursor
    
    if agent_id in _active_sessions:
        session_data = _active_sessions[agent_id]
        del _active_sessions[agent_id]
    else:
        with get_cursor() as cur:
            cur.execute(
                """
                SELECT sh.id as session_id, sh.agent_id, sh.grant_id, sh.task_description,
                       t.email, t.company_name, t.contact_name
                FROM session_history sh
                LEFT JOIN tenants t ON t.id = sh.tenant_id
                WHERE sh.agent_id = %s AND sh.ended_at IS NULL
                ORDER BY sh.started_at DESC
                LIMIT 1
                """,
                (agent_id,),
            )
            row = cur.fetchone()
            if row:
                session_data = dict(row)
            else:
                raise HTTPException(status_code=404, detail="Session not found")
    
    from backend.meeting_end_handler import handle_meeting_end
    await handle_meeting_end(agent_id, session_data)
    
    return {"status": "ended", "agent_id": agent_id}


@app.post("/admin/sessions/{agent_id}/force-end")
async def force_end_session(agent_id: str):
    """Force end a session without full cleanup (for debugging)."""
    from backend.db import get_cursor
    with get_cursor() as cur:
        cur.execute(
            """
            UPDATE session_history
            SET resolution_status = 'force_ended', ended_at = now()
            WHERE agent_id = %s AND ended_at IS NULL
            RETURNING id
            """,
            (agent_id,),
        )
        row = cur.fetchone()
        if row:
            return {"status": "force_ended", "session_id": row["id"]}
        else:
            raise HTTPException(status_code=404, detail="No active session found")


@app.get("/self-healing/history")
async def get_self_healing_history(limit: int = 50):
    """Get self-healing history."""
    from backend.self_healing import get_self_healing_history
    return {"history": get_self_healing_history(limit)}


@app.get("/self-healing/learnings")
async def get_error_learnings(limit: int = 50):
    """Get error-related learnings."""
    from backend.self_healing import get_error_learnings
    return {"learnings": get_error_learnings(limit)}


@app.post("/self-healing/analyze/{session_id}")
async def analyze_session_errors(session_id: str):
    """Manually trigger self-healing analysis for a session."""
    from backend.self_healing import run_self_healing_loop
    
    # Get tool logs for session
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT * FROM tool_call_logs
            WHERE session_id = %s
            ORDER BY created_at ASC
            """,
            (session_id,),
        )
        tool_logs = [dict(r) for r in cur.fetchall()]
    
    # Get session context
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT task_description, issue_category
            FROM session_history
            WHERE id = %s
            """,
            (session_id,),
        )
        session = cur.fetchone()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    result = run_self_healing_loop(
        session_id=session_id,
        tool_logs=tool_logs,
        session_context=dict(session),
    )
    
    return result
