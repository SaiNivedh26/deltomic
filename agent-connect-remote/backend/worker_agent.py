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
from backend.config import (
    AGENT_MODEL, ALLOWED_COMMANDS,
    BEDROCK_MODEL, BEDROCK_REGION, BEDROCK_API_KEY,
    AWS_ACCESS_KEY, AWS_SECRET_ACCESS_KEY,
)
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
from backend.trace_service import (
    store_tool_execution_trace,
    store_agent_planning_trace,
    store_conversation_turn,
)
from backend.session_lifecycle import finalize_session, broadcast_agent_event
from backend.critique_agent import critique_execution_plan, is_plan_approved, expand_allowlist_if_needed

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
    "task_description": None,
}

_command_history: list[dict] = []
_command_in_progress: bool = False


def _push_event(event: dict):
    task_id = _current_context.get("task_id")
    if task_id and task_id in _task_queues:
        _task_queues[task_id].put_nowait(event)


def _get_model_name():
    return BEDROCK_MODEL


@tool
def list_available_commands() -> str:
    """List all commands currently allowed for this session."""
    grant_id = _current_context.get("grant_id")
    if grant_id:
        try:
            from backend.db import get_cursor
            import json
            
            with get_cursor() as cur:
                cur.execute(
                    "SELECT allowed_commands FROM support_access_grants WHERE id = %s",
                    (grant_id,),
                )
                row = cur.fetchone()
                if row:
                    cmds = row["allowed_commands"]
                    if isinstance(cmds, str):
                        cmds = json.loads(cmds)
                    return "\n".join(cmds)
        except Exception as e:
            logger.error(f"Failed to get grant commands: {e}")
    
    # Fallback to profile-based allowlist
    profile = _current_context.get("profile_name")
    escalated = _current_context.get("escalated", False)
    commands = build_dynamic_allowlist(profile or "diagnostic", escalated)
    return "\n".join(commands)


@tool
async def run_command(command: str) -> str:
    """Execute an allowed command on the remote customer machine.

    Args:
        command: The command to execute
    """
    global _command_in_progress
    
    if _command_in_progress:
        return "BUSY: Another command is currently executing. Please wait for it to complete before running the next command. Execute commands ONE AT A TIME."
    
    _command_in_progress = True
    
    try:
        start_time = time.time()
        grant_id = _current_context.get("grant_id")
        agent_id = _current_context.get("agent_id")
        tenant_id = _current_context.get("tenant_id")
        session_id = _current_context.get("session_id")
        model_used = _get_model_name()

        if not grant_id or not agent_id:
            return "Error: No active session context"

        normalized_cmd = command.strip()
        for prev in _command_history:
            if prev["command"].strip() == normalized_cmd:
                return f"DUPLICATE_COMMAND: You already ran this command. Previous output: {prev['output'][:200]}. Use a different command or analyze the previous result."

        if is_destructive(command):
            _current_context["escalated"] = True
            _push_event({"type": "approval_required", "command": command, "task_id": _current_context.get("task_id")})
            return f"ESCALATION_REQUIRED: Command '{command}' is destructive and requires explicit customer approval."

        _push_event({"type": "command_start", "command": command, "task_id": _current_context.get("task_id")})

        broadcast_agent_event(agent_id, {
            "type": "command_start",
            "command": command,
            "session_id": session_id,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        })

        try:
            result = await access_control.execute_command(
                grant_id=grant_id,
                command=command,
                executed_by=agent_id,
            )

            duration_ms = int((time.time() - start_time) * 1000)

            if result["status"] == "Success":
                output = result["stdout"].strip()
                
                _command_history.append({
                    "command": normalized_cmd,
                    "output": output[:500] if output else "(no output)",
                    "status": "success",
                    "timestamp": time.time(),
                })
                
                _push_event({"type": "command_complete", "command": command, "output": output, "status": "success", "duration_ms": duration_ms, "task_id": _current_context.get("task_id")})

                log_tool_call(
                    tool_name="run_command",
                    tool_args={"command": command},
                    tool_result=output[:2000] if output else "(no output)",
                    status="success",
                    duration_ms=duration_ms,
                    model_used=model_used,
                    session_id=session_id,
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                    grant_id=grant_id,
                )

                store_tool_execution_trace(
                    session_id=session_id,
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                    tool_name="run_command",
                    tool_args={"command": command},
                    tool_result=output[:2000] if output else "(no output)",
                    status="success",
                    duration_ms=duration_ms,
                    model_used=model_used,
                )

                broadcast_agent_event(agent_id, {
                    "type": "command_complete",
                    "command": command,
                    "status": "success",
                    "output_preview": output[:200] if output else "",
                    "duration_ms": duration_ms,
                    "session_id": session_id,
                    "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
                })

                return output if output else "(no output)"
            else:
                error_msg = result["stderr"] or result["status"]
                
                _command_history.append({
                    "command": normalized_cmd,
                    "output": error_msg[:500],
                    "status": "failed",
                    "timestamp": time.time(),
                })
                
                _push_event({"type": "command_complete", "command": command, "output": error_msg, "status": "failed", "duration_ms": duration_ms, "task_id": _current_context.get("task_id")})
                log_tool_call(
                    tool_name="run_command",
                    tool_args={"command": command},
                    tool_result=error_msg,
                    status="failed",
                    duration_ms=duration_ms,
                    model_used=model_used,
                    session_id=session_id,
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                    grant_id=grant_id,
                )
                return f"Command failed: {error_msg}"
        except PermissionError as e:
            return f"Permission denied: {e}"
        except Exception as e:
            return f"Error: {e}"
    finally:
        _command_in_progress = False


@tool
async def approve_and_run_destructive(command: str) -> str:
    """Execute a destructive command AFTER customer has explicitly approved it.

    Args:
        command: The destructive command to execute (customer must have approved)
    """
    start_time = time.time()
    grant_id = _current_context.get("grant_id")
    agent_id = _current_context.get("agent_id")
    session_id = _current_context.get("session_id")
    model_used = _get_model_name()

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
                model_used=model_used,
                session_id=session_id,
                tenant_id=_current_context.get("tenant_id"),
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
def propose_execution_plan(commands: list[str], reasoning: str) -> str:
    """Propose an execution plan for security review BEFORE running commands.

    Args:
        commands: List of commands you plan to execute
        reasoning: Brief explanation of why these commands are needed
    """
    profile = _current_context.get("profile_name", "diagnostic")
    current_allowlist = build_dynamic_allowlist(profile, _current_context.get("escalated", False))
    task_description = _current_context.get("task_description", "")
    grant_id = _current_context.get("grant_id")

    broadcast_agent_event(
        _current_context.get("agent_id", ""),
        {
            "type": "plan_proposed",
            "commands": commands,
            "reasoning": reasoning,
            "profile": profile,
            "session_id": _current_context.get("session_id"),
        },
    )

    critique_result = critique_execution_plan(
        task_description=task_description,
        planned_commands=commands,
        current_allowlist=current_allowlist,
        task_profile=profile,
    )

    if is_plan_approved(critique_result):
        approved = critique_result.get("approved_commands", commands)
        expansion = expand_allowlist_if_needed(critique_result)

        if expansion:
            # Actually persist the allowlist expansion to the database
            if grant_id:
                try:
                    from backend.db import get_cursor
                    import json
                    
                    with get_cursor() as cur:
                        cur.execute(
                            """
                            SELECT allowed_commands FROM support_access_grants WHERE id = %s
                            """,
                            (grant_id,),
                        )
                        row = cur.fetchone()
                        if row:
                            current_cmds = row["allowed_commands"]
                            if isinstance(current_cmds, str):
                                current_cmds = json.loads(current_cmds)
                            
                            # Add new commands
                            for cmd in expansion:
                                if cmd not in current_cmds:
                                    current_cmds.append(cmd)
                            
                            cur.execute(
                                """
                                UPDATE support_access_grants 
                                SET allowed_commands = %s, updated_at = now()
                                WHERE id = %s
                                """,
                                (json.dumps(current_cmds), grant_id),
                            )
                            
                            logger.info(f"Allowlist expanded for grant {grant_id}: added {expansion}")
                except Exception as e:
                    logger.error(f"Failed to expand allowlist: {e}")
            
            broadcast_agent_event(
                _current_context.get("agent_id", ""),
                {
                    "type": "allowlist_expanded",
                    "added_commands": expansion,
                    "justification": (critique_result.get("allowlist_expansion") or {}).get("justification", ""),
                },
            )

        return json.dumps({
            "status": "approved",
            "approved_commands": approved,
            "critique": critique_result.get("critique", ""),
            "risk_level": critique_result.get("risk_level", "unknown"),
        })
    else:
        return json.dumps({
            "status": "denied",
            "denied_commands": critique_result.get("denied_commands", []),
            "critique": critique_result.get("critique", ""),
        })


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
    propose_execution_plan,
    revoke_access,
]

WORKER_SYSTEM_PROMPT = """You are Deltomic, a senior remote support engineer. You are connected to a customer's machine and need to help them.

CRITICAL EXECUTION RULES:
1. Execute ONE command at a time. NEVER call multiple tools simultaneously.
2. Wait for the result of each command before calling the next one.
3. Keep track of what you've already executed - DO NOT repeat the same command.
4. After each command, analyze the output and decide the next step.
5. If a command fails, try a different approach - don't retry the same command.
6. ONLY run commands relevant to the specific issue. Don't run generic diagnostic commands.

HOW YOU WORK:
1. You ALREADY KNOW the customer's issue from the task description. Do NOT ask them to explain it again.
2. Start by acknowledging what you know about their issue and briefly state your approach.
3. If the user tells you something specific (like "Docker installed via snap"), USE THAT INFORMATION.
4. Execute ONE command, wait for result, interpret it, then decide next command.
5. Summarize what you found and what you did.

EXAMPLE BEHAVIOR (good):
User: "My container keeps restarting"
"I see you're having issues with a container restarting. Let me check what's happening with Docker."
[runs: docker ps -a]
[waits for result]
"I can see the container is in a restart loop. Let me check the logs to understand why."
[runs: docker logs <container-name> --tail 50]
[waits for result]
"The logs show the application is crashing due to a missing environment variable. Let me check the docker-compose file."

EXAMPLE BEHAVIOR (bad - DO NOT DO THIS):
User: "My container keeps restarting"
[runs: whoami, id, groups, sudo -n true, docker ps] ← WRONG! Irrelevant commands!

RULES:
- NEVER ask the customer to re-explain their issue - you already have the task context
- ALWAYS execute commands ONE AT A TIME - wait for each result before proceeding
- NEVER repeat a command you've already run - track your execution history
- ONLY run commands relevant to the issue - don't run generic diagnostics
- If the user provides specific information (like how something was installed), use it
- Always explain what you're doing and why BEFORE running each command
- Be proactive - don't wait for instructions, take initiative
- For destructive commands, explain consequences and ask for approval
- Keep explanations concise but informative
- The working directory is /home/ubuntu

Available tools:
- run_command(command): Execute a command on their machine (ONE AT A TIME!)
- propose_execution_plan(commands, reasoning): Submit a plan for review (optional, use for complex multi-step tasks)
- list_available_commands(): See allowed commands
- get_previous_sessions(): Check past session history
- revoke_access(reason): End the session when done"""


def _get_bedrock_agent():
    from langchain_aws import ChatBedrockConverse

    os.environ["AWS_BEARER_TOKEN_BEDROCK"] = BEDROCK_API_KEY

    model = ChatBedrockConverse(
        model=BEDROCK_MODEL,
        region_name=BEDROCK_REGION,
        temperature=0,
        max_tokens=4096,
    )

    return create_agent(
        model=model,
        tools=WORKER_TOOLS,
        system_prompt=WORKER_SYSTEM_PROMPT,
        checkpointer=InMemorySaver(),
    )


_bedrock_agent_instance = None


def _get_bedrock_agent_lazy():
    global _bedrock_agent_instance
    if _bedrock_agent_instance is None:
        _bedrock_agent_instance = _get_bedrock_agent()
        logger.info(f"Bedrock Execution Agent: Initialized with {BEDROCK_MODEL}")
    return _bedrock_agent_instance


async def worker_chat(
    message: str,
    grant_id: str,
    agent_id: str,
    email: str = "",
    task_context: str = "",
    thread_id: str | None = None,
) -> str:
    _command_history.clear()
    thread_id = thread_id or str(uuid7())
    agent = _get_bedrock_agent_lazy()

    tenant = None
    tenant_id = None
    session_id = None

    if email:
        tenant = get_or_create_tenant(email)
        tenant_id = tenant["id"]

        session = create_session(
            tenant_id=tenant_id,
            agent_id=agent_id,
            grant_id=grant_id if grant_id else None,
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
    _current_context["task_description"] = task_context or message[:200]

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

            await finalize_session(
                session_id=session_id,
                agent_id=agent_id,
                tenant_id=tenant_id,
                summary=response[:500] if response else "",
                issue_category=profile_name,
                resolution_status="resolved",
                commands_executed=commands,
                tool_calls_count=len(commands),
                langgraph_messages=result["messages"],
                model_used=_get_model_name(),
            )

        return response
    finally:
        _current_context["grant_id"] = None
        _current_context["agent_id"] = None
        _current_context["tenant_id"] = None
        _current_context["session_id"] = None
        _current_context["profile_name"] = None
        _current_context["escalated"] = False
        _current_context["task_description"] = None


async def execute_task_with_groq(
    task_description: str,
    grant_id: str,
    agent_id: str,
    email: str = "",
) -> dict:
    _command_history.clear()
    thread_id = str(uuid7())
    agent = _get_bedrock_agent_lazy()

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
    _current_context["task_description"] = task_description

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
        _current_context["task_description"] = None


async def execute_task_streaming(
    task_description: str,
    grant_id: str,
    agent_id: str,
    email: str = "",
) -> tuple[str, AsyncGenerator[str, None]]:
    task_id = str(uuid7())
    queue: asyncio.Queue = asyncio.Queue()
    _task_queues[task_id] = queue

    thread_id = str(uuid7())
    agent = _get_bedrock_agent_lazy()

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

    # Auto-expand allowlist based on task context
    task_lower = task_description.lower()
    auto_expand_commands = []
    
    if any(kw in task_lower for kw in ["docker", "container", "kubernetes", "k8s", "pod"]):
        auto_expand_commands.extend(["docker", "snap", "snap run", "systemctl", "journalctl"])
    
    if any(kw in task_lower for kw in ["network", "dns", "firewall", "port", "connect"]):
        auto_expand_commands.extend(["netstat", "ss", "ping", "ip", "ifconfig", "curl", "wget"])
    
    if any(kw in task_lower for kw in ["install", "package", "apt", "snap", "dpkg"]):
        auto_expand_commands.extend(["apt", "dpkg", "snap", "python3", "pip3"])
    
    if any(kw in task_lower for kw in ["service", "systemd", "restart", "start", "stop"]):
        auto_expand_commands.extend(["systemctl", "service", "journalctl"])
    
    if auto_expand_commands and grant_id:
        try:
            from backend.db import get_cursor
            
            with get_cursor() as cur:
                cur.execute(
                    "SELECT allowed_commands FROM support_access_grants WHERE id = %s",
                    (grant_id,),
                )
                row = cur.fetchone()
                if row:
                    current_cmds = row["allowed_commands"]
                    if isinstance(current_cmds, str):
                        current_cmds = json.loads(current_cmds)
                    
                    added = []
                    for cmd in auto_expand_commands:
                        if cmd not in current_cmds:
                            current_cmds.append(cmd)
                            added.append(cmd)
                    
                    if added:
                        cur.execute(
                            """
                            UPDATE support_access_grants 
                            SET allowed_commands = %s, updated_at = now()
                            WHERE id = %s
                            """,
                            (json.dumps(current_cmds), grant_id),
                        )
                        logger.info(f"Auto-expanded allowlist for grant {grant_id}: added {added}")
                        
                        broadcast_agent_event(agent_id, {
                            "type": "allowlist_expanded",
                            "added_commands": added,
                            "justification": f"Task context requires: {task_description[:100]}",
                        })
        except Exception as e:
            logger.error(f"Failed to auto-expand allowlist: {e}")

    async def run_agent():
        _command_history.clear()
        
        _current_context["grant_id"] = grant_id
        _current_context["agent_id"] = agent_id
        _current_context["tenant_id"] = tenant_id
        _current_context["session_id"] = session_id
        _current_context["profile_name"] = profile_name
        _current_context["escalated"] = False
        _current_context["task_id"] = task_id
        _current_context["task_description"] = task_description

        try:
            _push_event({"type": "task_start", "task_id": task_id, "description": task_description})

            broadcast_agent_event(agent_id, {
                "type": "task_start",
                "task_id": task_id,
                "description": task_description,
                "session_id": session_id,
                "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            })

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
                await finalize_session(
                    session_id=session_id,
                    agent_id=agent_id,
                    tenant_id=tenant_id,
                    summary=response[:500] if response else "",
                    issue_category=profile_name,
                    resolution_status="resolved",
                    commands_executed=commands_executed,
                    tool_calls_count=len(commands_executed),
                    langgraph_messages=result["messages"],
                    model_used=_get_model_name(),
                )

            broadcast_agent_event(agent_id, {
                "type": "task_complete",
                "task_id": task_id,
                "summary": response or "Task completed",
                "session_id": session_id,
                "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            })

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
            _current_context["task_description"] = None

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
    if task_id in _pending_approvals:
        _pending_approvals[task_id].set_result(approved)
    return True
