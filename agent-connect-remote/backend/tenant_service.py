from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from typing import Any

from backend.db import get_cursor

logger = logging.getLogger(__name__)


def _customer_id_from_email(email: str) -> str:
    h = hashlib.md5(email.lower().strip().encode()).hexdigest()[:12]
    return f"customer-{h}"


def get_or_create_tenant(email: str, metadata: dict | None = None) -> dict:
    email = email.lower().strip()
    customer_id = _customer_id_from_email(email)

    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM tenants WHERE email = %s",
            (email,),
        )
        tenant = cur.fetchone()

        if tenant:
            if metadata:
                cur.execute(
                    """
                    UPDATE tenants SET metadata = metadata || %s, updated_at = now()
                    WHERE email = %s RETURNING *
                    """,
                    (json.dumps(metadata), email),
                )
                tenant = cur.fetchone()
            return dict(tenant)

        cur.execute(
            """
            INSERT INTO tenants (email, customer_id, metadata)
            VALUES (%s, %s, %s)
            RETURNING *
            """,
            (email, customer_id, json.dumps(metadata or {})),
        )
        tenant = cur.fetchone()
        logger.info(f"Created tenant: {email} -> {customer_id}")
        return dict(tenant)


def get_tenant_by_email(email: str) -> dict | None:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM tenants WHERE email = %s", (email.lower().strip(),))
        row = cur.fetchone()
        return dict(row) if row else None


def get_tenant_by_id(tenant_id: str) -> dict | None:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM tenants WHERE id = %s", (tenant_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_tenant_by_customer_id(customer_id: str) -> dict | None:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM tenants WHERE customer_id = %s", (customer_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def list_tenants(limit: int = 100, offset: int = 0) -> list[dict]:
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM tenants ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset),
        )
        return [dict(r) for r in cur.fetchall()]


def create_session(
    tenant_id: str,
    agent_id: str,
    grant_id: str | None = None,
    task_description: str = "",
) -> dict:
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO session_history (tenant_id, agent_id, grant_id, task_description)
            VALUES (%s, %s, %s, %s)
            RETURNING *
            """,
            (tenant_id, agent_id, grant_id, task_description),
        )
        session = cur.fetchone()
        return dict(session)


def end_session(
    session_id: str,
    summary: str = "",
    issue_category: str = "",
    resolution_status: str = "resolved",
    commands_executed: list | None = None,
    tool_calls_count: int = 0,
):
    with get_cursor() as cur:
        cur.execute(
            """
            UPDATE session_history
            SET summary = %s, issue_category = %s, resolution_status = %s,
                commands_executed = %s, tool_calls_count = %s, ended_at = now()
            WHERE id = %s
            """,
            (summary, issue_category, resolution_status,
             json.dumps(commands_executed or []), tool_calls_count, session_id),
        )


def get_session_history(tenant_id: str, limit: int = 10) -> list[dict]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT * FROM session_history
            WHERE tenant_id = %s
            ORDER BY started_at DESC
            LIMIT %s
            """,
            (tenant_id, limit),
        )
        return [dict(r) for r in cur.fetchall()]


def get_previous_context(tenant_id: str) -> str:
    sessions = get_session_history(tenant_id, limit=5)
    if not sessions:
        return ""

    context_parts = []
    for s in sessions:
        task = s.get("task_description", "")
        summary = s.get("summary", "")
        category = s.get("issue_category", "")
        status = s.get("resolution_status", "")
        started = s.get("started_at", "")

        part = f"- [{started}] Task: {task}"
        if summary:
            part += f" | Summary: {summary}"
        if category:
            part += f" | Category: {category}"
        if status:
            part += f" | Status: {status}"
        context_parts.append(part)

    return "PREVIOUS SESSIONS WITH THIS CUSTOMER:\n" + "\n".join(context_parts)


def log_tool_call(
    tool_name: str,
    tool_args: dict,
    tool_result: str = "",
    status: str = "success",
    duration_ms: int = 0,
    model_used: str = "",
    session_id: str | None = None,
    tenant_id: str | None = None,
    agent_id: str = "",
    grant_id: str | None = None,
    trace_id: str = "",
):
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO tool_call_logs
            (tool_name, tool_args, tool_result, status, duration_ms, model_used,
             session_id, tenant_id, agent_id, grant_id, trace_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (tool_name, json.dumps(tool_args), tool_result, status,
             duration_ms, model_used, session_id, tenant_id, agent_id,
             grant_id, trace_id),
        )


def get_tool_call_logs(
    session_id: str | None = None,
    tenant_id: str | None = None,
    limit: int = 100,
) -> list[dict]:
    with get_cursor() as cur:
        if session_id:
            cur.execute(
                """
                SELECT * FROM tool_call_logs WHERE session_id = %s
                ORDER BY created_at DESC LIMIT %s
                """,
                (session_id, limit),
            )
        elif tenant_id:
            cur.execute(
                """
                SELECT * FROM tool_call_logs WHERE tenant_id = %s
                ORDER BY created_at DESC LIMIT %s
                """,
                (tenant_id, limit),
            )
        else:
            cur.execute(
                "SELECT * FROM tool_call_logs ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
        return [dict(r) for r in cur.fetchall()]


def get_weekly_insights() -> dict:
    with get_cursor() as cur:
        cur.execute("""
            SELECT issue_category, COUNT(*) as count
            FROM session_history
            WHERE started_at >= now() - INTERVAL '7 days'
            AND issue_category IS NOT NULL AND issue_category != ''
            GROUP BY issue_category
            ORDER BY count DESC
        """)
        categories = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT COUNT(*) as total_sessions,
                   COUNT(DISTINCT tenant_id) as unique_tenants,
                   SUM(tool_calls_count) as total_tool_calls
            FROM session_history
            WHERE started_at >= now() - INTERVAL '7 days'
        """)
        totals = cur.fetchone()

        cur.execute("""
            SELECT tool_name, COUNT(*) as count
            FROM tool_call_logs
            WHERE created_at >= now() - INTERVAL '7 days'
            GROUP BY tool_name
            ORDER BY count DESC
            LIMIT 10
        """)
        top_tools = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT t.email, t.company_name, COUNT(sh.id) as session_count
            FROM tenants t
            JOIN session_history sh ON sh.tenant_id = t.id
            WHERE sh.started_at >= now() - INTERVAL '7 days'
            GROUP BY t.id, t.email, t.company_name
            ORDER BY session_count DESC
            LIMIT 10
        """)
        top_tenants = [dict(r) for r in cur.fetchall()]

        return {
            "issue_categories": categories,
            "totals": dict(totals) if totals else {},
            "top_tools": top_tools,
            "top_tenants": top_tenants,
        }
