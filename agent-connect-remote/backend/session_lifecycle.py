from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any

from backend.db import get_cursor
from backend.trace_service import (
    store_trace,
    store_conversation_turn,
    store_tool_execution_trace,
    store_agent_planning_trace,
    get_session_traces,
    build_trace_summary,
)
from backend.vector_store import store_session_embedding
from backend.insights_engine import (
    store_agent_learning,
    get_relevant_learnings,
    create_batch_insight,
)
from backend.tenant_service import (
    end_session as db_end_session,
    get_session_history,
)

logger = logging.getLogger(__name__)

_agent_event_queues: dict[str, list[asyncio.Queue]] = {}


def subscribe_agent_events(agent_id: str) -> asyncio.Queue:
    queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
    if agent_id not in _agent_event_queues:
        _agent_event_queues[agent_id] = []
    _agent_event_queues[agent_id].append(queue)
    return queue


def unsubscribe_agent_events(agent_id: str, queue: asyncio.Queue):
    if agent_id in _agent_event_queues:
        _agent_event_queues[agent_id] = [
            q for q in _agent_event_queues[agent_id] if q is not queue
        ]


def broadcast_agent_event(agent_id: str, event: dict):
    if agent_id in _agent_event_queues:
        for queue in _agent_event_queues[agent_id]:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO agent_events_buffer (agent_id, session_id, event_type, event_data)
            VALUES (%s, %s, %s, %s)
            """,
            (agent_id, event.get("session_id"), event.get("type"), json.dumps(event)),
        )


def broadcast_session_event(session_id: str, event: dict):
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO agent_events_buffer (agent_id, session_id, event_type, event_data)
            VALUES (%s, %s, %s, %s)
            """,
            ("session-" + session_id[:8], session_id, event.get("type"), json.dumps(event)),
        )


async def finalize_session(
    session_id: str,
    agent_id: str,
    tenant_id: str | None = None,
    summary: str = "",
    issue_category: str = "",
    resolution_status: str = "resolved",
    commands_executed: list | None = None,
    tool_calls_count: int = 0,
    conversation_history: list[dict] | None = None,
    langgraph_messages: list | None = None,
    model_used: str = "",
):
    logger.info(f"Finalizing session {session_id} for agent {agent_id}")

    db_end_session(
        session_id=session_id,
        summary=summary,
        issue_category=issue_category,
        resolution_status=resolution_status,
        commands_executed=commands_executed or [],
        tool_calls_count=tool_calls_count,
    )

    if conversation_history:
        for turn in conversation_history:
            store_conversation_turn(
                session_id=session_id,
                tenant_id=tenant_id,
                agent_id=agent_id,
                role=turn.get("role", "unknown"),
                content=turn.get("content", ""),
                metadata={"source": "session_finalize"},
            )

    if langgraph_messages:
        for msg in langgraph_messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc["name"] in ("run_command", "approve_and_run_destructive"):
                        store_tool_execution_trace(
                            session_id=session_id,
                            tenant_id=tenant_id,
                            agent_id=agent_id,
                            tool_name=tc["name"],
                            tool_args=tc.get("args", {}),
                            tool_result="",
                            status="success",
                            model_used=model_used,
                        )

    embedding_text = f"{issue_category}: {summary}"
    if commands_executed:
        embedding_text += f" | Commands: {', '.join(commands_executed[:5])}"

    store_session_embedding(
        session_id=session_id,
        tenant_id=tenant_id,
        text=embedding_text,
        content_type="session_summary",
        issue_category=issue_category,
        resolution_status=resolution_status,
    )

    broadcast_agent_event(agent_id, {
        "type": "session_finalized",
        "session_id": session_id,
        "agent_id": agent_id,
        "summary": summary[:200],
        "issue_category": issue_category,
        "resolution_status": resolution_status,
        "timestamp": datetime.utcnow().isoformat(),
    })

    logger.info(f"Session {session_id} finalized: {issue_category} -> {resolution_status}")


async def cleanup_meet_session(agent_id: str, session_data: dict):
    logger.info(f"Cleaning up meet session for agent {agent_id}")

    grant_id = session_data.get("grant_id")
    email = session_data.get("email", "")
    task_context = session_data.get("task_context", "")

    broadcast_agent_event(agent_id, {
        "type": "session_cleanup_start",
        "agent_id": agent_id,
        "timestamp": datetime.utcnow().isoformat(),
    })

    try:
        from backend.db import get_cursor
        with get_cursor() as cur:
            cur.execute(
                """
                UPDATE session_history
                SET resolution_status = 'ended', ended_at = now()
                WHERE agent_id = %s AND ended_at IS NULL
                """,
                (agent_id,),
            )
    except Exception as e:
        logger.error(f"Error updating session_history during cleanup: {e}")

    try:
        from backend.access_control import access_control
        if grant_id:
            access_control.revoke_access(
                grant_id=grant_id,
                revoked_by="session-cleanup",
                reason="Meeting ended - session cleanup",
            )
            logger.info(f"Revoked grant {grant_id} for agent {agent_id}")
    except Exception as e:
        logger.error(f"Error revoking grant during cleanup: {e}")

    broadcast_agent_event(agent_id, {
        "type": "session_cleanup_complete",
        "agent_id": agent_id,
        "timestamp": datetime.utcnow().isoformat(),
    })

    logger.info(f"Meet session cleanup complete for agent {agent_id}")


def get_live_agent_events(agent_id: str, since_seconds: int = 300) -> list[dict]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT * FROM agent_events_buffer
            WHERE agent_id = %s
            AND created_at >= now() - INTERVAL '%s seconds'
            ORDER BY created_at ASC
            """,
            (agent_id, since_seconds),
        )
        return [dict(r) for r in cur.fetchall()]


def get_all_active_events(limit: int = 100) -> list[dict]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT * FROM agent_events_buffer
            WHERE created_at >= now() - INTERVAL '5 minutes'
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]
