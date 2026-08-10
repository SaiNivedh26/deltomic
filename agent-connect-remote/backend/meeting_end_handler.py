from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from pingram import Pingram, SendEmailRequest

from backend.db import get_cursor
from backend.session_lifecycle import finalize_session, cleanup_meet_session, broadcast_agent_event
from backend.config import PINGRAM_API_KEY

logger = logging.getLogger(__name__)


async def handle_meeting_end(agent_id: str, session_data: dict):
    """Handle meeting end event - finalize session and send confirmation email."""
    logger.info(f"Meeting ended for agent {agent_id}")
    logger.info(f"Session data: {session_data}")
    
    session_id = session_data.get("session_id")
    email = session_data.get("email", "")
    grant_id = session_data.get("grant_id")
    task_context = session_data.get("task_context", "")
    
    if not session_id:
        with get_cursor() as cur:
            cur.execute(
                """
                SELECT id FROM session_history
                WHERE agent_id = %s AND ended_at IS NULL
                ORDER BY started_at DESC
                LIMIT 1
                """,
                (agent_id,),
            )
            row = cur.fetchone()
            if row:
                session_id = row["id"]
            else:
                logger.warning(f"No active session found for agent {agent_id}")
                return
    
    logger.info(f"Found session_id: {session_id}")
    
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT sh.*, t.email, t.company_name, t.contact_name
            FROM session_history sh
            LEFT JOIN tenants t ON t.id = sh.tenant_id
            WHERE sh.id = %s
            """,
            (session_id,),
        )
        session = cur.fetchone()
    
    if not session:
        logger.error(f"Session {session_id} not found")
        return
    
    logger.info(f"Session found: {session}")
    
    if not email:
        email = session.get("email", "")
        logger.info(f"Using email from session: {email}")
    
    if not email:
        logger.error(f"No email address found for session {session_id}")
        return
    
    # Step 2: Get tool logs for self-healing analysis
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
    
    logger.info(f"Found {len(tool_logs)} tool logs for session {session_id}")
    
    # Step 3: Run self-healing analysis
    from backend.self_healing import run_self_healing_loop
    try:
        healing_result = run_self_healing_loop(
            session_id=session_id,
            tool_logs=tool_logs,
            session_context={
                "task_description": session.get("task_description", ""),
                "issue_category": session.get("issue_category", ""),
            },
        )
        logger.info(f"Self-healing result: {healing_result}")
    except Exception as e:
        logger.error(f"Self-healing analysis failed: {e}")
        healing_result = {"status": "error", "error": str(e)}
    
    # Step 4: Finalize session
    try:
        await finalize_session(
            session_id=session_id,
            agent_id=agent_id,
            tenant_id=session.get("tenant_id"),
            summary=session.get("summary", ""),
            issue_category=session.get("issue_category", ""),
            resolution_status=session.get("resolution_status", "pending"),
            commands_executed=session.get("commands_executed", []),
            tool_calls_count=session.get("tool_calls_count", 0),
        )
        logger.info(f"Session {session_id} finalized")
    except Exception as e:
        logger.error(f"Failed to finalize session: {e}")
    
    # Step 5: Cleanup meet session (revoke access)
    try:
        await cleanup_meet_session(agent_id, session_data)
        logger.info(f"Meet session cleaned up for agent {agent_id}")
    except Exception as e:
        logger.error(f"Failed to cleanup meet session: {e}")
    
    # Step 6: Send confirmation email
    try:
        await send_session_confirmation_email(
            email=email,
            contact_name=session.get("contact_name", ""),
            company_name=session.get("company_name", ""),
            session_id=session_id,
            task_description=session.get("task_description", ""),
            resolution_status=session.get("resolution_status", "pending"),
            summary=session.get("summary", ""),
            healing_result=healing_result,
            commands_executed=session.get("commands_executed", []),
            tool_logs=tool_logs,
        )
        logger.info(f"Email sent successfully to {email}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}", exc_info=True)
    
    # Step 7: Broadcast session end event
    broadcast_agent_event(agent_id, {
        "type": "session_ended",
        "session_id": session_id,
        "agent_id": agent_id,
        "email": email,
        "resolution_status": session.get("resolution_status"),
        "healing_result": healing_result,
        "timestamp": datetime.utcnow().isoformat(),
    })
    
    logger.info(f"Session {session_id} fully processed and email sent to {email}")


async def send_session_confirmation_email(
    email: str,
    contact_name: str,
    company_name: str,
    session_id: str,
    task_description: str,
    resolution_status: str,
    summary: str,
    healing_result: dict,
    commands_executed: list = None,
    tool_logs: list = None,
):
    """Send session confirmation email to customer via Pingram."""
    logger.info(f"Sending confirmation email to {email} for session {session_id}")
    
    if not PINGRAM_API_KEY:
        logger.error("PINGRAM_API_KEY not set - cannot send email")
        return
    
    try:
        greeting = f"Hi {contact_name}," if contact_name else "Hi,"
        
        status_emoji = "✅" if resolution_status == "resolved" else "⚠️" if resolution_status == "pending" else "❌"
        
        steps_text = get_resolution_steps(commands_executed or [], tool_logs or [])
        
        html_body = f"""
<h2>Support Session Complete</h2>
<p>{greeting}</p>
<p>Your support session with Deltomic AI has concluded.</p>

<h3>Session Details</h3>
<ul>
<li><strong>Issue:</strong> {task_description}</li>
<li><strong>Status:</strong> {status_emoji} {resolution_status.title()}</li>
<li><strong>Session ID:</strong> {session_id}</li>
</ul>

{f"<p><strong>Summary:</strong> {summary}</p>" if summary else ""}

<h3>{steps_text.split(':')[0]}:</h3>
<ol>
{"".join(f"<li>{line.split('. ', 1)[1]}</li>" for line in steps_text.split('\n')[1:] if '. ' in line)}
</ol>

<h3>Self-Healing Analysis</h3>
<p>{get_healing_summary(healing_result)}</p>

<p>If your issue is not resolved or you need further assistance, please don't hesitate to reach out again.</p>

<p>Best regards,<br>Deltomic AI Support Team</p>
        """
        
        logger.info(f"Creating Pingram client with API key: {PINGRAM_API_KEY[:10]}...")
        
        async with Pingram(api_key=PINGRAM_API_KEY) as client:
            response = await client.email.email_send(SendEmailRequest(
                type="session_confirmation",
                to=email,
                subject=f"Session Complete - {resolution_status.title()}",
                html=html_body,
            ))
            logger.info(f"Confirmation email sent to {email} for session {session_id}: {response}")
            return response
        
    except Exception as e:
        logger.error(f"Failed to send confirmation email: {e}", exc_info=True)
        raise


def get_resolution_steps(commands_executed: list, tool_logs: list) -> str:
    """Generate a summary of steps taken to resolve the issue."""
    if not commands_executed and not tool_logs:
        return "No specific actions were recorded during this session."
    
    steps = ["Steps Taken to Resolve the Issue:"]
    step_num = 1
    
    if tool_logs:
        for log in tool_logs[:15]:
            tool_name = log.get("tool_name", "unknown")
            tool_args = log.get("tool_args", {})
            
            if tool_name == "run_command":
                cmd = tool_args.get("command", "")
                if cmd:
                    steps.append(f"{step_num}. Executed: {cmd[:100]}")
                    step_num += 1
            elif tool_name == "search_code":
                query = tool_args.get("query", "")
                if query:
                    steps.append(f"{step_num}. Searched for: {query[:80]}")
                    step_num += 1
            elif tool_name == "read_file":
                path = tool_args.get("path", "")
                if path:
                    steps.append(f"{step_num}. Read file: {path}")
                    step_num += 1
            elif tool_name not in ("run_command", "search_code", "read_file"):
                steps.append(f"{step_num}. Used tool: {tool_name}")
                step_num += 1
    
    if commands_executed:
        for cmd in commands_executed[:5]:
            if cmd and not any(cmd in s for s in steps):
                steps.append(f"{step_num}. Command: {cmd[:100]}")
                step_num += 1
    
    if step_num == 1:
        return "The agent analyzed the issue and provided recommendations."
    
    return "\n".join(steps)


def get_healing_summary(healing_result: dict) -> str:
    """Generate a summary of self-healing actions for the email."""
    if healing_result.get("status") == "no_errors":
        return "No errors were detected during the session."
    
    errors_detected = healing_result.get("errors_detected", 0)
    corrections_suggested = healing_result.get("corrections_suggested", 0)
    learnings_stored = healing_result.get("learnings_stored", 0)
    
    summary = f"""
Self-Healing Analysis:
- Errors detected: {errors_detected}
- Corrections suggested: {corrections_suggested}
- Learnings stored for future improvement: {learnings_stored}
    """
    
    if healing_result.get("error_details"):
        summary += "\n\nError Types Encountered:\n"
        error_types = set(e.get("error_type", "unknown") for e in healing_result["error_details"])
        for error_type in error_types:
            summary += f"  • {error_type.replace('_', ' ').title()}\n"
    
    return summary


def check_meeting_status(agent_id: str) -> dict:
    """Check if meeting is still active (placeholder for Recall API integration)."""
    # TODO: Integrate with Recall API to check meeting status
    # For now, return a placeholder
    return {
        "agent_id": agent_id,
        "meeting_active": True,
        "last_checked": datetime.utcnow().isoformat(),
    }


async def poll_meeting_status(agent_id: str, interval_seconds: int = 60):
    """Poll meeting status and trigger end when meeting ends."""
    import asyncio
    
    while True:
        status = check_meeting_status(agent_id)
        
        if not status.get("meeting_active"):
            logger.info(f"Meeting ended for agent {agent_id}, triggering cleanup")
            # Get session data and handle meeting end
            with get_cursor() as cur:
                cur.execute(
                    """
                    SELECT sh.id as session_id, sh.agent_id, sh.grant_id, sh.task_context,
                           t.email, t.company_name, t.contact_name
                    FROM session_history sh
                    LEFT JOIN tenants t ON t.id = sh.tenant_id
                    WHERE sh.agent_id = %s
                    AND sh.ended_at IS NULL
                    ORDER BY sh.started_at DESC
                    LIMIT 1
                    """,
                    (agent_id,),
                )
                session = cur.fetchone()
            
            if session:
                await handle_meeting_end(agent_id, dict(session))
            break
        
        await asyncio.sleep(interval_seconds)
