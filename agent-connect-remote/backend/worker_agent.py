from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, AsyncGenerator

from langchain.agents import create_agent
from langchain.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_core.utils.uuid import uuid7
from langgraph.checkpoint.memory import InMemorySaver

from backend.access_control import access_control
from backend.config import AGENT_MODEL, ALLOWED_COMMANDS, GROQ_API_KEY, GROQ_MODEL, GROQ_MAX_TOKENS
from backend.tenant_service import (
    get_or_create_tenant,
    create_session,
    end_session,
    log_tool_call,
)
from backend.tool_config import (
    build_dynamic_allowlist,
    get_allowed_commands_for_profile,
    is_destructive,
    needs_escalation,
    resolve_task_profile,
)

logger = logging.getLogger(__name__)

_task_queues: dict[str, asyncio.Queue] = {}
_pending_approvals: dict[str, asyncio.Future] = {}

_current_context: dict[str, str | None] = {
    "grant_id": None,
    "agent_id": None,
    "tenant_id": None,
    "session_id": None,
    "profile_name": None,
    "escalated": False,
    "task_id": None,
}


def _push_event(event: dict):
    task_id = _current_context.get("task_id")
    if task_id and task_id in _task_queues:
        _task_queues[task_id].put_nowait(event)


@tool
def list_available_commands() -> str:
    """List all commands currently allowed for this session."""
    profile = _current_context.get("profile_name")
    escalated = _current_context.get("escalated", False)
    commands = build_dynamic_allowlist(profile or "diagnostic", escalated)
    return "\n".join(commands)


@tool
async def run_command(command: str) -> str:
    """Execute an allowed command on the remote customer machine.

    Args:
        command: The command to execute (must be in the allowlist)
    """
    start_time = time.time()
    grant_id = _current_context.get("grant_id")
    agent_id = _current_context.get("agent_id")
    tenant_id = _current_context.get("tenant_id")
    session_id = _current_context.get("session_id")

    if not grant_id or not agent_id:
        return "Error: No active session context"

    if is_destructive(command):
        _current_context["escalated"] = True
        _push_event({"type": "approval_required", "command": command, "task_id": _current_context.get("task_id")})
        return f"ESCALATION_REQUIRED: Command '{command}' is destructive and requires explicit customer approval. Ask the customer if they approve this command before proceeding."

    _push_event({"type": "command_start", "command": command, "task_id": _current_context.get("task_id")})
    
    try:
        result = await access_control.execute_command(
            grant_id=grant_id,
            command=command,
            executed_by=agent_id,
        )

        duration_ms = int((time.time() - start_time) * 1000)

        if result["status"] == "Success":
            output = result["stdout"].strip()
            _push_event({"type": "command_complete", "command": command, "output": output, "status": "success", "duration_ms": duration_ms, "task_id": _current_context.get("task_id")})

            log_tool_call(
                tool_name="run_command",
                tool_args={"command": command},
                tool_result=output[:2000] if output else "(no output)",
                status="success",
                duration_ms=duration_ms,
                model_used=GROQ_MODEL,
                session_id=session_id,
                tenant_id=tenant_id,
                agent_id=agent_id,
                grant_id=grant_id,
            )

            return output if output else "(no output)"
        else:
            error_msg = result["stderr"] or result["status"]
            _push_event({"type": "command_complete", "command": command, "output": error_msg, "status": "failed", "duration_ms": duration_ms, "task_id": _current_context.get("task_id")})
            log_tool_call(
                tool_name="run_command",
                tool_args={"command": command},
                tool_result=error_msg,
                status="failed",
                duration_ms=duration_ms,
                model_used=GROQ_MODEL,
                session_id=session_id,
                tenant_id=tenant_id,
                agent_id=agent_id,
                grant_id=grant_id,
            )
            return f"Command failed: {error_msg}"
    except PermissionError as e:
        log_tool_call(
            tool_name="run_command",
            tool_args={"command": command},
            tool_result=str(e),
            status="permission_denied",
            duration_ms=int((time.time() - start_time) * 1000),
            model_used=GROQ_MODEL,
            session_id=session_id,
            tenant_id=tenant_id,
            agent_id=agent_id,
            grant_id=grant_id,
        )
        return f"Permission denied: {e}"
    except Exception as e:
        log_tool_call(
            tool_name="run_command",
            tool_args={"command": command},
            tool_result=str(e),
            status="error",
            duration_ms=int((time.time() - start_time) * 1000),
            model_used=GROQ_MODEL,
            session_id=session_id,
            tenant_id=tenant_id,
            agent_id=agent_id,
            grant_id=grant_id,
        )
        return f"Error: {e}"


@tool
async def approve_and_run_destructive(command: str) -> str:
    """Execute a destructive command AFTER customer has explicitly approved it.

    Args:
        command: The destructive command to execute (customer must have approved)
    """
    start_time = time.time()
    grant_id = _current_context.get("grant_id")
    agent_id = _current_context.get("agent_id")
    tenant_id = _current_context.get("tenant_id")
    session_id = _current_context.get("session_id")

    if not grant_id or not agent_id:
        return "Error: No active session context"

    _current_context["escalated"] = True

    try:
        result = await access_control.execute_command(
            grant_id=grant_id,
            command=command,
            executed_by=agent_id,
        )

        duration_ms = int((time.time() - start_time) * 1000)

        if result["status"] == "Success":
            output = result["stdout"].strip()
            log_tool_call(
                tool_name="approve_and_run_destructive",
                tool_args={"command": command},
                tool_result=output[:2000] if output else "(no output)",
                status="success",
                duration_ms=duration_ms,
                model_used=GROQ_MODEL,
                session_id=session_id,
                tenant_id=tenant_id,
                agent_id=agent_id,
                grant_id=grant_id,
            )
            return output if output else "(no output)"
        else:
            return f"Command failed: {result['stderr'] or result['status']}"
    except PermissionError as e:
        return f"Permission denied: {e}"
    except Exception as e:
        return f"Error: {e}"


@tool
def get_previous_sessions() -> str:
    """Fetch previous session history for this customer. Call this if you need context about past interactions."""
    tenant_id = _current_context.get("tenant_id")
    if not tenant_id:
        return "No tenant context available"
    
    from backend.tenant_service import get_previous_context
    context = get_previous_context(tenant_id)
    return context if context else "No previous sessions found for this customer"


@tool
def revoke_access(reason: str = "") -> str:
    """Revoke the current access session."""
    grant_id = _current_context.get("grant_id")
    agent_id = _current_context.get("agent_id")

    if not grant_id or not agent_id:
        return "Error: No active session context"

    access_control.revoke_access(
        grant_id=grant_id,
        revoked_by=agent_id,
        reason=reason or "Agent ended session",
    )
    return "Access revoked successfully"


WORKER_TOOLS = [
    list_available_commands,
    run_command,
    approve_and_run_destructive,
    get_previous_sessions,
    revoke_access,
]

WORKER_SYSTEM_PROMPT = """You are a remote support execution agent. You receive tasks from a conversation agent (Gemini Live voice) and execute them on the customer's machine.

Your role:
1. Focus on the CURRENT TASK - this is your primary objective
2. Analyze the task you've been given
3. Plan your approach step by step
4. Use run_command to execute commands on their machine
5. Analyze the output and take appropriate action
6. For destructive commands, use approve_and_run_destructive ONLY after the customer explicitly approves
7. When done, use revoke_access to end the session

Available tools:
- run_command(command): Execute a command on their machine
- approve_and_run_destructive(command): Execute a destructive command (only after customer approval)
- list_available_commands(): See all allowed commands
- get_previous_sessions(): Fetch previous session history (call this ONLY if you need context about past interactions)
- revoke_access(reason): End the session when done

Rules:
- PRIORITIZE the current task above all else
- Be thorough and methodical
- Execute commands, analyze output, and complete the task autonomously
- Default to read-only diagnostic commands first
- Only escalate to write/destructive commands when necessary
- Always explain what you're doing and why
- If you need historical context, call get_previous_sessions() - but don't let it distract from the current task
- The working directory is /home/ubuntu"""


def _get_groq_agent():
    from langchain_groq import ChatGroq

    model = ChatGroq(
        model=GROQ_MODEL,
        temperature=0,
        max_tokens=GROQ_MAX_TOKENS,
    )

    return create_agent(
        model=model,
        tools=WORKER_TOOLS,
        system_prompt=WORKER_SYSTEM_PROMPT,
        checkpointer=InMemorySaver(),
    )


_groq_agent_instance = None


def _get_groq_agent_lazy():
    global _groq_agent_instance
    if _groq_agent_instance is None:
        _groq_agent_instance = _get_groq_agent()
        logger.info(f"Groq Execution Agent: Initialized with {GROQ_MODEL}")
    return _groq_agent_instance


async def worker_chat(
    message: str,
    grant_id: str,
    agent_id: str,
    email: str = "",
    task_context: str = "",
    thread_id: str | None = None,
) -> str:
    thread_id = thread_id or str(uuid7())
    agent = _get_groq_agent_lazy()

    tenant = None
    tenant_id = None
    session_id = None

    if email:
        tenant = get_or_create_tenant(email)
        tenant_id = tenant["id"]

        session = create_session(
            tenant_id=tenant_id,
            agent_id=agent_id,
            grant_id=grant_id,
            task_description=task_context or message[:200],
        )
        session_id = session["id"]

        profile_name = resolve_task_profile(task_context or message)

        enhanced_message = message
        if task_context:
            enhanced_message = f"TASK: {task_context}\n\n{enhanced_message}"

        message = enhanced_message
    else:
        profile_name = resolve_task_profile(message)

    _current_context["grant_id"] = grant_id
    _current_context["agent_id"] = agent_id
    _current_context["tenant_id"] = tenant_id
    _current_context["session_id"] = session_id
    _current_context["profile_name"] = profile_name
    _current_context["escalated"] = False

    try:
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            {"configurable": {"thread_id": thread_id}},
        )

        response = result["messages"][-1].content

        if session_id:
            commands = []
            for msg in result["messages"]:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        if tc["name"] == "run_command":
                            commands.append(tc["args"].get("command", ""))

            end_session(
                session_id=session_id,
                summary=response[:500] if response else "",
                issue_category=profile_name,
                resolution_status="resolved",
                commands_executed=commands,
                tool_calls_count=len(commands),
            )

        return response
    finally:
        _current_context["grant_id"] = None
        _current_context["agent_id"] = None
        _current_context["tenant_id"] = None
        _current_context["session_id"] = None
        _current_context["profile_name"] = None
        _current_context["escalated"] = False


async def execute_task_with_groq(
    task_description: str,
    grant_id: str,
    agent_id: str,
    email: str = "",
) -> dict:
    """Execute a task using Groq agent for planning and command execution.
    
    Returns:
        dict with summary and list of commands executed
    """
    thread_id = str(uuid7())
    agent = _get_groq_agent_lazy()
    
    tenant = None
    tenant_id = None
    session_id = None
    
    if email:
        tenant = get_or_create_tenant(email)
        tenant_id = tenant["id"]
        
        session = create_session(
            tenant_id=tenant_id,
            agent_id=agent_id,
            grant_id=grant_id,
            task_description=task_description,
        )
        session_id = session["id"]
    
    profile_name = resolve_task_profile(task_description)
    
    _current_context["grant_id"] = grant_id
    _current_context["agent_id"] = agent_id
    _current_context["tenant_id"] = tenant_id
    _current_context["session_id"] = session_id
    _current_context["profile_name"] = profile_name
    _current_context["escalated"] = False
    
    commands_executed = []
    
    try:
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=task_description)]},
            {"configurable": {"thread_id": thread_id}},
        )
        
        response = result["messages"][-1].content
        
        for msg in result["messages"]:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc["name"] == "run_command":
                        commands_executed.append({
                            "command": tc["args"].get("command", ""),
                            "status": "success",
                            "output": "",
                        })
        
        if session_id:
            end_session(
                session_id=session_id,
                summary=response[:500] if response else "",
                issue_category=profile_name,
                resolution_status="resolved",
                commands_executed=[c["command"] for c in commands_executed],
                tool_calls_count=len(commands_executed),
            )
        
        return {
            "summary": response if response else "Task completed",
            "commands": commands_executed,
            "profile": profile_name,
        }
    finally:
        _current_context["grant_id"] = None
        _current_context["agent_id"] = None
        _current_context["tenant_id"] = None
        _current_context["session_id"] = None
        _current_context["profile_name"] = None
        _current_context["escalated"] = False


async def execute_task_streaming(
    task_description: str,
    grant_id: str,
    agent_id: str,
    email: str = "",
) -> tuple[str, AsyncGenerator[str, None]]:
    """Execute a task with streaming command updates via SSE.
    
    Returns:
        tuple of (task_id, async generator of SSE events)
    """
    task_id = str(uuid7())
    queue: asyncio.Queue = asyncio.Queue()
    _task_queues[task_id] = queue
    
    thread_id = str(uuid7())
    agent = _get_groq_agent_lazy()
    
    tenant = None
    tenant_id = None
    session_id = None
    
    if email:
        tenant = get_or_create_tenant(email)
        tenant_id = tenant["id"]
        
        session = create_session(
            tenant_id=tenant_id,
            agent_id=agent_id,
            grant_id=grant_id,
            task_description=task_description,
        )
        session_id = session["id"]
    
    profile_name = resolve_task_profile(task_description)
    
    async def run_agent():
        _current_context["grant_id"] = grant_id
        _current_context["agent_id"] = agent_id
        _current_context["tenant_id"] = tenant_id
        _current_context["session_id"] = session_id
        _current_context["profile_name"] = profile_name
        _current_context["escalated"] = False
        _current_context["task_id"] = task_id
        
        try:
            _push_event({"type": "task_start", "task_id": task_id, "description": task_description})
            
            result = await agent.ainvoke(
                {"messages": [HumanMessage(content=task_description)]},
                {"configurable": {"thread_id": thread_id}},
            )
            
            response = result["messages"][-1].content
            
            commands_executed = []
            for msg in result["messages"]:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        if tc["name"] in ("run_command", "approve_and_run_destructive"):
                            commands_executed.append(tc["args"].get("command", ""))
            
            if session_id:
                end_session(
                    session_id=session_id,
                    summary=response[:500] if response else "",
                    issue_category=profile_name,
                    resolution_status="resolved",
                    commands_executed=commands_executed,
                    tool_calls_count=len(commands_executed),
                )
            
            _push_event({"type": "task_complete", "task_id": task_id, "summary": response or "Task completed"})
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            _push_event({"type": "task_error", "task_id": task_id, "error": str(e)})
        finally:
            _current_context["grant_id"] = None
            _current_context["agent_id"] = None
            _current_context["tenant_id"] = None
            _current_context["session_id"] = None
            _current_context["profile_name"] = None
            _current_context["escalated"] = False
            _current_context["task_id"] = None
    
    asyncio.create_task(run_agent())
    
    async def event_stream():
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=300)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") in ("task_complete", "task_error"):
                    break
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        
        _task_queues.pop(task_id, None)
    
    return task_id, event_stream()


def approve_command(task_id: str, approved: bool):
    """Approve or deny a destructive command."""
    if task_id in _pending_approvals:
        _pending_approvals[task_id].set_result(approved)
    return True
