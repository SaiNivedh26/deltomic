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

_current_context = {"grant_id": None, "agent_id": None}


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
    try:
        grant_id = _current_context.get("grant_id")
        agent_id = _current_context.get("agent_id")
        
        if not grant_id or not agent_id:
            return "Error: No active session context"
        
        result = await access_control.execute_command(
            grant_id=grant_id,
            command=command,
            executed_by=agent_id,
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
def revoke_access(reason: str = "") -> str:
    """Revoke the current access session.
    
    Args:
        reason: Reason for revoking
    """
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
    revoke_access,
]

WORKER_SYSTEM_PROMPT = """You are a remote support worker agent with autonomous access to a customer's machine via SSM.

Your role:
1. Analyze the task you've been given
2. Use run_command to execute commands on their machine
3. Analyze the output and take appropriate action
4. Execute any necessary fixes or create required scripts
5. When done, use revoke_access to end the session

Available tools:
- run_command(command): Execute a command on their machine
- list_available_commands(): See all allowed commands
- revoke_access(reason): End the session when done

Be thorough and methodical. Execute commands, analyze output, and complete the task autonomously."""


def get_worker_agent():
    model = os.getenv("AGENT_MODEL", AGENT_MODEL)
    return create_agent(
        model=model,
        tools=WORKER_TOOLS,
        system_prompt=WORKER_SYSTEM_PROMPT,
        checkpointer=InMemorySaver(),
    )


_worker_agent_instance = None


def get_worker_agent_lazy():
    global _worker_agent_instance
    if _worker_agent_instance is None:
        _worker_agent_instance = get_worker_agent()
        logger.info("Worker Agent: Initialized")
    return _worker_agent_instance


async def worker_chat(message: str, grant_id: str, agent_id: str, thread_id: str | None = None) -> str:
    thread_id = thread_id or str(uuid7())
    agent = get_worker_agent_lazy()
    
    _current_context["grant_id"] = grant_id
    _current_context["agent_id"] = agent_id
    
    try:
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            {"configurable": {"thread_id": thread_id}},
        )
        
        return result["messages"][-1].content
    finally:
        _current_context["grant_id"] = None
        _current_context["agent_id"] = None
