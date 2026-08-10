from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from typing import Any

from backend.db import get_cursor

logger = logging.getLogger(__name__)


def get_session_metrics(days: int = 30) -> dict:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT 
                COUNT(*) as total_sessions,
                AVG(tool_calls_count) as avg_tool_calls
            FROM session_history
            WHERE started_at >= now() - INTERVAL '%s days'
            """,
            (days,),
        )
        base_metrics = dict(cur.fetchone() or {})

        cur.execute(
            """
            SELECT started_at, ended_at, tool_calls_count
            FROM session_history
            WHERE started_at >= now() - INTERVAL '%s days'
              AND ended_at IS NOT NULL
            ORDER BY started_at DESC
            LIMIT 500
            """,
            (days,),
        )
        duration_rows = cur.fetchall()

    durations_secs = []
    for r in duration_rows:
        if r["started_at"] and r["ended_at"]:
            delta = (r["ended_at"] - r["started_at"]).total_seconds()
            if delta > 0:
                durations_secs.append(delta)

    avg_duration = sum(durations_secs) / len(durations_secs) if durations_secs else 0
    min_duration = min(durations_secs) if durations_secs else 0
    max_duration = max(durations_secs) if durations_secs else 0

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT span_kind,
                   COUNT(*) as count,
                   AVG(duration_ms) as avg_duration_ms,
                   SUM(duration_ms) as total_duration_ms
            FROM agent_traces
            WHERE start_time >= now() - INTERVAL '%s days'
            GROUP BY span_kind
            """,
            (days,),
        )
        span_metrics = {r["span_kind"]: dict(r) for r in cur.fetchall()}

        cur.execute(
            """
            SELECT tool_name, COUNT(*) as count
            FROM tool_call_logs
            WHERE created_at >= now() - INTERVAL '%s days'
            GROUP BY tool_name
            ORDER BY count DESC
            LIMIT 15
            """,
            (days,),
        )
        tool_metrics = [dict(r) for r in cur.fetchall()]

    return {
        "period_days": days,
        "session_metrics": {
            "total": base_metrics.get("total_sessions", 0),
            "avg_tool_calls": round(float(base_metrics.get("avg_tool_calls") or 0), 1),
            "avg_duration_secs": round(avg_duration, 1),
            "min_duration_secs": round(min_duration, 1),
            "max_duration_secs": round(max_duration, 1),
        },
        "span_metrics": span_metrics,
        "top_tools": tool_metrics,
    }


def detect_workflow_patterns(days: int = 30, limit: int = 200) -> list[dict]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT t.session_id, t.span_name, t.status, t.start_time,
                   sh.issue_category, sh.resolution_status
            FROM agent_traces t
            LEFT JOIN session_history sh ON sh.id = t.session_id
            WHERE t.span_kind = 'tool'
              AND t.start_time >= now() - INTERVAL '%s days'
            ORDER BY t.session_id, t.start_time ASC
            LIMIT %s
            """,
            (days, limit * 50),
        )
        rows = cur.fetchall()

    session_workflows: dict[str, list[str]] = defaultdict(list)
    session_meta: dict[str, dict] = {}
    for r in rows:
        tool = r["span_name"].replace("tool.", "")
        session_workflows[r["session_id"]].append(tool)
        if r["session_id"] not in session_meta:
            session_meta[r["session_id"]] = {
                "issue_category": r.get("issue_category"),
                "resolution_status": r.get("resolution_status"),
            }

    workflow_counter: Counter[tuple[str, ...]] = Counter()
    workflow_outcomes: dict[tuple[str, ...], dict] = defaultdict(
        lambda: {"resolved": 0, "failed": 0, "total": 0}
    )

    for session_id, tools in session_workflows.items():
        if len(tools) < 3:
            continue
        signature = _compute_workflow_signature(tools)
        workflow_counter[signature] += 1
        workflow_outcomes[signature]["total"] += 1
        status = session_meta.get(session_id, {}).get("resolution_status")
        if status == "resolved":
            workflow_outcomes[signature]["resolved"] += 1
        elif status and status != "resolved":
            workflow_outcomes[signature]["failed"] += 1

    patterns = []
    for sig, count in workflow_counter.most_common(20):
        outcomes = workflow_outcomes[sig]
        patterns.append(
            {
                "workflow_signature": list(sig),
                "frequency": count,
                "resolved": outcomes["resolved"],
                "failed": outcomes["failed"],
                "success_rate": round(
                    outcomes["resolved"] / outcomes["total"], 3
                )
                if outcomes["total"] > 0
                else 0,
            }
        )

    return patterns


def get_tenant_profiles(days: int = 30) -> list[dict]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT t.id as tenant_id, t.email, t.company_name,
                   COUNT(sh.id) as session_count,
                   SUM(sh.tool_calls_count) as total_tool_calls,
                   AVG(sh.tool_calls_count) as avg_tool_calls,
                   SUM(CASE WHEN sh.resolution_status = 'resolved' THEN 1 ELSE 0 END) as resolved_count
            FROM tenants t
            LEFT JOIN session_history sh ON sh.tenant_id = t.id
                AND sh.started_at >= now() - INTERVAL '%s days'
            WHERE sh.id IS NOT NULL
            GROUP BY t.id, t.email, t.company_name
            ORDER BY session_count DESC
            LIMIT 20
            """,
            (days,),
        )
        tenants = [dict(r) for r in cur.fetchall()]

    profiles = []
    for t in tenants:
        session_count = t["session_count"] or 0
        resolved = t["resolved_count"] or 0
        profiles.append(
            {
                "tenant_id": t["tenant_id"],
                "email": t["email"],
                "company_name": t["company_name"],
                "session_count": session_count,
                "total_tool_calls": t["total_tool_calls"] or 0,
                "avg_tool_calls": round(float(t["avg_tool_calls"] or 0), 1),
                "resolution_rate": round(resolved / session_count, 3)
                if session_count > 0
                else 0,
                "profile_tier": _classify_tenant(session_count, resolved / session_count if session_count > 0 else 0),
            }
        )

    return profiles


def get_time_distribution(days: int = 30) -> list[dict]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT EXTRACT(HOUR FROM started_at) as hour,
                   COUNT(*) as session_count,
                   AVG(tool_calls_count) as avg_tools
            FROM session_history
            WHERE started_at >= now() - INTERVAL '%s days'
            GROUP BY EXTRACT(HOUR FROM started_at)
            ORDER BY hour
            """,
            (days,),
        )
        hourly = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """
            SELECT EXTRACT(DOW FROM started_at) as day_of_week,
                   COUNT(*) as session_count
            FROM session_history
            WHERE started_at >= now() - INTERVAL '%s days'
            GROUP BY EXTRACT(DOW FROM started_at)
            ORDER BY day_of_week
            """,
            (days,),
        )
        daily = [dict(r) for r in cur.fetchall()]

    return {
        "hourly": [
            {"hour": int(r["hour"]), "sessions": r["session_count"], "avg_tools": round(float(r["avg_tools"] or 0), 1)}
            for r in hourly
        ],
        "daily": [
            {"day": int(r["day_of_week"]), "sessions": r["session_count"]}
            for r in daily
        ],
    }


def get_usage_analysis() -> dict:
    metrics = get_session_metrics()
    workflows = detect_workflow_patterns()
    tenants = get_tenant_profiles()
    time_dist = get_time_distribution()

    return {
        "metrics": metrics,
        "workflow_patterns": workflows,
        "tenant_profiles": tenants,
        "time_distribution": time_dist,
    }


def _compute_workflow_signature(tools: list[str]) -> tuple[str, ...]:
    if len(tools) <= 5:
        return tuple(tools)
    compressed = []
    prev = tools[0]
    count = 1
    for t in tools[1:]:
        if t == prev:
            count += 1
        else:
            compressed.append(f"{prev}x{count}" if count > 1 else prev)
            prev = t
            count = 1
    compressed.append(f"{prev}x{count}" if count > 1 else prev)
    if len(compressed) > 8:
        return tuple(compressed[:8])
    return tuple(compressed)


def _classify_tenant(session_count: int, resolution_rate: float) -> str:
    if session_count >= 20 and resolution_rate >= 0.7:
        return "power_user"
    elif session_count >= 10:
        return "regular"
    elif session_count >= 3:
        return "occasional"
    else:
        return "new"
