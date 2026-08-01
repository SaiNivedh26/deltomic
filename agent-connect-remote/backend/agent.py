from __future__ import annotations

import logging
import os

from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_core.tools import tool
from langchain_core.utils.uuid import uuid7
from langgraph.checkpoint.memory import InMemorySaver

from backend.access_control import access_control
from backend.config import AGENT_MODEL, ALLOWED_COMMANDS

logger = logging.getLogger(__name__)

_current_grant_id: str | None = None
_current_agent_id: str = "agent-001"


@tool
def list_available_commands() -> str:
    """List all commands that are allowed to run on the remote machine."""
    return "\n".join(ALLOWED_COMMANDS)


@tool
async def run_command(command: str) -> str:
    """Execute an allowed command on the remote customer machine.
    
    Args:
        command: The command to execute (must be in the allowlist)
    """
    if not _current_grant_id:
        return "ERROR: No active session. Request access first."
    
    try:
        result = await access_control.execute_command(
            grant_id=_current_grant_id,
            command=command,
            executed_by=_current_agent_id,
        )
        
        if result["status"] == "Success":
            output = result["stdout"].strip()
            return output if output else "(no output)"
        else:
            return f"Command failed: {result['stderr'] or result['status']}"
    except PermissionError as e:
        return f"Permission denied: {e}"
    except Exception as e:
        return f"Error: {e}"


@tool
def request_access(customer_id: str, duration_minutes: int = 10) -> str:
    """Request temporary access to a customer's machine.
    
    Args:
        customer_id: The customer identifier
        duration_minutes: How long access should last (default 10 min)
    """
    global _current_grant_id
    
    try:
        grant_id = access_control.request_access(
            customer_id=customer_id,
            requested_by=_current_agent_id,
            duration_minutes=duration_minutes,
        )
        _current_grant_id = grant_id
        return f"Access requested. Grant ID: {grant_id}\nWaiting for customer approval..."
    except ValueError as e:
        return f"Error: {e}"


@tool
def check_access_status(grant_id: str) -> str:
    """Check the status of an access request.
    
    Args:
        grant_id: The grant ID to check
    """
    status = access_control.get_grant_status(grant_id)
    if not status:
        return "Grant not found"
    
    return f"Status: {status['status']}, Expires: {status['expires_at']}"


@tool
def revoke_access(reason: str = "") -> str:
    """Revoke the current access session."""
    global _current_grant_id
    
    if not _current_grant_id:
        return "No active session to revoke"
    
    access_control.revoke_access(
        grant_id=_current_grant_id,
        revoked_by=_current_agent_id,
        reason=reason or "Agent ended session",
    )
    _current_grant_id = None
    return "Access revoked successfully"


TOOLS = [
    list_available_commands,
    request_access,
    check_access_status,
    run_command,
    revoke_access,
]

SYSTEM_PROMPT = """You are a remote support agent that executes diagnostic commands on customer machines.

CRITICAL: When you see [SYSTEM: You have ACTIVE access...] in the message, you ALREADY have permission. 
Do NOT call request_access. Go directly to run_command.

Available tools:
- run_command(command): Execute a diagnostic command (ls, df -h, whoami, pwd, uname -a, uptime, free -m)
- list_available_commands(): See all allowed commands
- revoke_access(): End the session when done

ONLY use request_access if explicitly told you don't have access yet.

Be concise. Show command output and explain briefly."""


def get_agent():
    model = os.getenv("AGENT_MODEL", AGENT_MODEL)
    return create_agent(
        model=model,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=InMemorySaver(),
    )


_agent_instance = None


def get_agent_lazy():
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = get_agent()
        logger.info("Agent: Initialized remote support agent")
    return _agent_instance


async def chat(message: str, thread_id: str | None = None, grant_id: str | None = None) -> str:
    global _current_grant_id
    if grant_id:
        _current_grant_id = grant_id
    
    thread_id = thread_id or str(uuid7())
    agent = get_agent_lazy()
    
    if grant_id:
        status = access_control.get_grant_status(grant_id)
        if status and status['status'] == 'approved':
            message = f"""[SYSTEM: You have ACTIVE access to the customer's machine. Grant ID: {grant_id}
Status: APPROVED. Do NOT call request_access - you already have permission.
Go directly to running commands using run_command tool.]

User request: {message}"""
    
    result = await agent.ainvoke(
        {"messages": [HumanMessage(content=message)]},
        {"configurable": {"thread_id": thread_id}},
    )
    
    return result["messages"][-1].content
