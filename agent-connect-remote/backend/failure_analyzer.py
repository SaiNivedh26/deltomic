from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from typing import Any

from backend.db import get_cursor

logger = logging.getLogger(__name__)


def get_error_clusters(days: int = 30, limit: int = 200) -> list[dict]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT t.session_id, t.span_name, t.status, t.input_data, t.output_data,
                   t.duration_ms, t.start_time, sh.issue_category, sh.resolution_status,
                   sh.tenant_id
            FROM agent_traces t
            LEFT JOIN session_history sh ON sh.id = t.session_id
            WHERE t.span_kind = 'tool'
              AND t.status = 'error'
              AND t.start_time >= now() - INTERVAL '%s days'
            ORDER BY t.start_time DESC
            LIMIT %s
            """,
            (days, limit),
        )
        errors = [dict(r) for r in cur.fetchall()]

    clusters: dict[str, list[dict]] = defaultdict(list)
    for error in errors:
        tool_name = error["span_name"].replace("tool.", "")
        output = error.get("output_data", {})
        if isinstance(output, str):
            try:
                output = json.loads(output)
            except (json.JSONDecodeError, TypeError):
                output = {"result": output}

        error_msg = str(output.get("result", ""))[:200]
        error_type = _classify_error(error_msg)
        cluster_key = f"{tool_name}:{error_type}"
        clusters[cluster_key].append(
            {
                "session_id": error["session_id"],
                "tool": tool_name,
                "error_type": error_type,
                "error_message": error_msg,
                "issue_category": error.get("issue_category"),
                "duration_ms": error.get("duration_ms"),
                "timestamp": error["start_time"].isoformat() if error.get("start_time") else None,
            }
        )

    result = []
    for key, items in sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True):
        tool_name, error_type = key.split(":", 1)
        affected_sessions = list({i["session_id"] for i in items if i["session_id"]})
        result.append(
            {
                "cluster_key": key,
                "tool": tool_name,
                "error_type": error_type,
                "occurrence_count": len(items),
                "affected_sessions": len(affected_sessions),
                "session_ids": affected_sessions[:10],
                "sample_messages": [i["error_message"] for i in items[:3]],
                "avg_duration_ms": (
                    sum(i["duration_ms"] or 0 for i in items) / len(items)
                    if items
                    else 0
                ),
                "issue_categories": dict(
                    Counter(i.get("issue_category", "unknown") for i in items).most_common(5)
                ),
            }
        )

    return result


def detect_error_loops(limit: int = 200) -> list[dict]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT session_id, span_name, status, start_time
            FROM agent_traces
            WHERE span_kind = 'tool'
              AND start_time >= now() - INTERVAL '30 days'
            ORDER BY session_id, start_time ASC
            """,
        )
        rows = cur.fetchall()

    session_tools: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        session_tools[r["session_id"]].append(
            {"tool": r["span_name"], "status": r["status"], "time": r["start_time"]}
        )

    loops = []
    for session_id, tools in session_tools.items():
        consecutive_errors: list[dict] = []
        for t in tools:
            if t["status"] == "error":
                consecutive_errors.append(t)
            else:
                if len(consecutive_errors) >= 3:
                    tool_counts = Counter(e["tool"] for e in consecutive_errors)
                    repeated = {k: v for k, v in tool_counts.items() if v >= 2}
                    if repeated:
                        loops.append(
                            {
                                "session_id": session_id,
                                "loop_length": len(consecutive_errors),
                                "repeated_tools": repeated,
                                "primary_tool": max(repeated, key=repeated.get),
                                "start_time": consecutive_errors[0]["time"].isoformat()
                                if consecutive_errors[0].get("time")
                                else None,
                            }
                        )
                consecutive_errors = []

        if len(consecutive_errors) >= 3:
            tool_counts = Counter(e["tool"] for e in consecutive_errors)
            repeated = {k: v for k, v in tool_counts.items() if v >= 2}
            if repeated:
                loops.append(
                    {
                        "session_id": session_id,
                        "loop_length": len(consecutive_errors),
                        "repeated_tools": repeated,
                        "primary_tool": max(repeated, key=repeated.get),
                        "start_time": consecutive_errors[0]["time"].isoformat()
                        if consecutive_errors[0].get("time")
                        else None,
                    }
                )

    loops.sort(key=lambda x: x["loop_length"], reverse=True)
    return loops[:20]


def get_failure_mode_summary() -> dict:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT resolution_status, COUNT(*) as count
            FROM session_history
            WHERE started_at >= now() - INTERVAL '30 days'
            GROUP BY resolution_status
            """
        )
        status_dist = {r["resolution_status"]: r["count"] for r in cur.fetchall()}

        cur.execute(
            """
            SELECT span_name, COUNT(*) as error_count,
                   COUNT(DISTINCT session_id) as affected_sessions
            FROM agent_traces
            WHERE span_kind = 'tool' AND status = 'error'
              AND start_time >= now() - INTERVAL '30 days'
            GROUP BY span_name
            ORDER BY error_count DESC
            LIMIT 15
            """
        )
        tool_errors = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """
            SELECT issue_category, 
                   COUNT(*) as total,
                   SUM(CASE WHEN resolution_status = 'resolved' THEN 1 ELSE 0 END) as resolved
            FROM session_history
            WHERE started_at >= now() - INTERVAL '30 days'
              AND issue_category IS NOT NULL AND issue_category != ''
            GROUP BY issue_category
            HAVING COUNT(*) >= 2
            ORDER BY total DESC
            """
        )
        category_outcomes = [dict(r) for r in cur.fetchall()]

    total_sessions = sum(status_dist.values())
    resolved = status_dist.get("resolved", 0)
    overall_resolution_rate = resolved / total_sessions if total_sessions > 0 else 0

    return {
        "total_sessions": total_sessions,
        "resolution_rate": round(overall_resolution_rate, 3),
        "status_distribution": status_dist,
        "top_error_tools": tool_errors,
        "category_outcomes": [
            {
                "category": r["issue_category"],
                "total": r["total"],
                "resolved": r["resolved"],
                "resolution_rate": round(r["resolved"] / r["total"], 3) if r["total"] > 0 else 0,
            }
            for r in category_outcomes
        ],
    }


def get_failure_analysis() -> dict:
    clusters = get_error_clusters()
    loops = detect_error_loops()
    summary = get_failure_mode_summary()

    return {
        "summary": summary,
        "error_clusters": clusters[:20],
        "error_loops": loops,
        "total_clusters": len(clusters),
        "total_loops": len(loops),
    }


def _classify_error(error_msg: str) -> str:
    msg = error_msg.lower()
    if "permission denied" in msg or "access denied" in msg or "not permitted" in msg:
        return "permission"
    elif "not found" in msg or "no such file" in msg or "does not exist" in msg:
        return "not_found"
    elif "command not found" in msg or "not recognized" in msg:
        return "command_missing"
    elif "timeout" in msg or "timed out" in msg:
        return "timeout"
    elif "connection" in msg or "network" in msg or "unreachable" in msg:
        return "network"
    elif "syntax" in msg or "invalid" in msg or "parse error" in msg:
        return "syntax"
    elif "exit code" in msg or "exited with" in msg:
        return "exit_code"
    else:
        return "other"
