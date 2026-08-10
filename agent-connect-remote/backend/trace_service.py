from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any

from backend.db import get_cursor

logger = logging.getLogger(__name__)


def store_trace(
    session_id: str | None,
    tenant_id: str | None,
    agent_id: str,
    span_name: str,
    trace_type: str = "langgraph",
    trace_id: str | None = None,
    parent_trace_id: str | None = None,
    span_kind: str = "tool",
    input_data: dict | None = None,
    output_data: dict | None = None,
    metadata: dict | None = None,
    status: str = "ok",
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    duration_ms: int | None = None,
) -> str | None:
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO agent_traces
            (session_id, tenant_id, agent_id, trace_type, trace_id, parent_trace_id,
             span_name, span_kind, input_data, output_data, metadata, status,
             start_time, end_time, duration_ms)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                session_id, tenant_id, agent_id, trace_type, trace_id, parent_trace_id,
                span_name, span_kind, json.dumps(input_data or {}),
                json.dumps(output_data or {}), json.dumps(metadata or {}),
                status, start_time or datetime.utcnow(), end_time, duration_ms,
            ),
        )
        row = cur.fetchone()
        return str(row["id"]) if row else None


def store_conversation_turn(
    session_id: str | None,
    tenant_id: str | None,
    agent_id: str,
    role: str,
    content: str,
    trace_id: str | None = None,
    metadata: dict | None = None,
) -> str | None:
    return store_trace(
        session_id=session_id,
        tenant_id=tenant_id,
        agent_id=agent_id,
        span_name=f"conversation.{role}",
        trace_type="conversation",
        trace_id=trace_id,
        span_kind="message",
        input_data={"role": role, "content": content[:5000]},
        metadata=metadata or {},
        status="ok",
    )


def store_tool_execution_trace(
    session_id: str | None,
    tenant_id: str | None,
    agent_id: str,
    tool_name: str,
    tool_args: dict,
    tool_result: str,
    status: str = "success",
    duration_ms: int = 0,
    trace_id: str | None = None,
    model_used: str = "",
) -> str | None:
    return store_trace(
        session_id=session_id,
        tenant_id=tenant_id,
        agent_id=agent_id,
        span_name=f"tool.{tool_name}",
        trace_type="langgraph",
        trace_id=trace_id,
        span_kind="tool",
        input_data=tool_args,
        output_data={"result": tool_result[:5000], "status": status},
        metadata={"model_used": model_used, "tool_name": tool_name},
        status="ok" if status == "success" else "error",
        duration_ms=duration_ms,
    )


def store_agent_planning_trace(
    session_id: str | None,
    tenant_id: str | None,
    agent_id: str,
    model_used: str,
    input_messages: list[dict],
    output_message: str,
    tool_calls: list[dict] | None = None,
    duration_ms: int = 0,
    trace_id: str | None = None,
) -> str | None:
    return store_trace(
        session_id=session_id,
        tenant_id=tenant_id,
        agent_id=agent_id,
        span_name=f"llm.{model_used}",
        trace_type="langgraph",
        trace_id=trace_id,
        span_kind="llm",
        input_data={"messages_count": len(input_messages), "last_message": input_messages[-1]["content"][:1000] if input_messages else ""},
        output_data={"response": output_message[:2000], "tool_calls": tool_calls or []},
        metadata={"model_used": model_used},
        status="ok",
        duration_ms=duration_ms,
    )


def get_session_traces(session_id: str, limit: int = 200) -> list[dict]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT * FROM agent_traces
            WHERE session_id = %s
            ORDER BY start_time ASC
            LIMIT %s
            """,
            (session_id, limit),
        )
        return [dict(r) for r in cur.fetchall()]


def get_agent_traces(agent_id: str, limit: int = 100) -> list[dict]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT * FROM agent_traces
            WHERE agent_id = %s
            ORDER BY start_time DESC
            LIMIT %s
            """,
            (agent_id, limit),
        )
        return [dict(r) for r in cur.fetchall()]


def get_trace_timeline(session_id: str) -> dict:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT span_kind, COUNT(*) as count,
                   SUM(duration_ms) as total_duration_ms,
                   AVG(duration_ms) as avg_duration_ms
            FROM agent_traces
            WHERE session_id = %s
            GROUP BY span_kind
            """,
            (session_id,),
        )
        by_kind = {r["span_kind"]: dict(r) for r in cur.fetchall()}

        cur.execute(
            """
            SELECT * FROM agent_traces
            WHERE session_id = %s
            ORDER BY start_time ASC
            """,
            (session_id,),
        )
        timeline = [dict(r) for r in cur.fetchall()]

        conversation = [t for t in timeline if t["trace_type"] == "conversation"]
        tool_calls = [t for t in timeline if t["span_kind"] == "tool"]
        llm_calls = [t for t in timeline if t["span_kind"] == "llm"]

        return {
            "session_id": session_id,
            "total_spans": len(timeline),
            "conversation_turns": len(conversation),
            "tool_executions": len(tool_calls),
            "llm_calls": len(llm_calls),
            "by_kind": by_kind,
            "timeline": timeline,
        }


def get_recent_traces(limit: int = 50) -> list[dict]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT at.*, sh.task_description, t.email as tenant_email
            FROM agent_traces at
            LEFT JOIN session_history sh ON sh.id = at.session_id
            LEFT JOIN tenants t ON t.id = at.tenant_id
            ORDER BY at.start_time DESC
            LIMIT %s
            """,
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]


def build_trace_summary(session_id: str) -> dict:
    traces = get_session_traces(session_id)
    if not traces:
        return {"session_id": session_id, "spans": []}

    conversation = []
    tool_chain = []
    llm_decisions = []

    for t in traces:
        if t["trace_type"] == "conversation":
            conversation.append({
                "role": t["input_data"].get("role", "unknown") if isinstance(t["input_data"], dict) else "unknown",
                "content": t["input_data"].get("content", "")[:500] if isinstance(t["input_data"], dict) else "",
                "timestamp": t["start_time"].isoformat() if t["start_time"] else None,
            })
        elif t["span_kind"] == "tool":
            tool_chain.append({
                "tool": t["span_name"].replace("tool.", ""),
                "status": t["status"],
                "duration_ms": t["duration_ms"],
                "timestamp": t["start_time"].isoformat() if t["start_time"] else None,
            })
        elif t["span_kind"] == "llm":
            llm_decisions.append({
                "model": t["metadata"].get("model_used", "") if isinstance(t["metadata"], dict) else "",
                "timestamp": t["start_time"].isoformat() if t["start_time"] else None,
            })

    return {
        "session_id": session_id,
        "conversation": conversation,
        "tool_chain": tool_chain,
        "llm_decisions": llm_decisions,
        "total_duration_ms": sum(t.get("duration_ms", 0) or 0 for t in traces),
    }
