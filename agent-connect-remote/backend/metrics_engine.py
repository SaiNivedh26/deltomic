from __future__ import annotations

import json
import logging
import statistics
from typing import Any

from backend.db import get_cursor

logger = logging.getLogger(__name__)


def get_task_completion_metrics(tenant_id: str | None = None, days: int = 30) -> dict:
    with get_cursor() as cur:
        params: list = [days]
        tenant_filter = ""
        if tenant_id:
            tenant_filter = "AND sh.tenant_id = %s"
            params.append(tenant_id)

        cur.execute(
            f"""
            SELECT
                COUNT(*) AS total_sessions,
                COUNT(*) FILTER (WHERE sh.resolution_status = 'resolved') AS resolved,
                COUNT(*) FILTER (WHERE sh.resolution_status = 'failed') AS failed,
                COUNT(*) FILTER (WHERE sh.resolution_status = 'pending') AS pending,
                COUNT(*) FILTER (WHERE sh.resolution_status = 'escalated') AS escalated
            FROM session_history sh
            WHERE sh.started_at >= now() - (%s * INTERVAL '1 day')
            {tenant_filter}
            """,
            tuple(params),
        )
        row = dict(cur.fetchone() or {})

    total = row.get("total_sessions", 0) or 0
    resolved = row.get("resolved", 0) or 0
    failed = row.get("failed", 0) or 0
    pending = row.get("pending", 0) or 0
    escalated = row.get("escalated", 0) or 0

    completion_rate = resolved / total if total > 0 else 0.0
    failure_rate = failed / total if total > 0 else 0.0

    return {
        "total_sessions": total,
        "resolved": resolved,
        "failed": failed,
        "pending": pending,
        "escalated": escalated,
        "completion_rate": round(completion_rate, 4),
        "failure_rate": round(failure_rate, 4),
        "period_days": days,
    }


def get_error_rate_metrics(tenant_id: str | None = None, days: int = 30) -> dict:
    with get_cursor() as cur:
        params: list = [days]
        tenant_filter = ""
        if tenant_id:
            tenant_filter = "AND tenant_id = %s"
            params.append(tenant_id)

        cur.execute(
            f"""
            SELECT
                COUNT(*) AS total_calls,
                COUNT(*) FILTER (WHERE status = 'success') AS success_calls,
                COUNT(*) FILTER (WHERE status = 'error') AS error_calls,
                COUNT(*) FILTER (WHERE status = 'timeout') AS timeout_calls
            FROM tool_call_logs
            WHERE created_at >= now() - (%s * INTERVAL '1 day')
            {tenant_filter}
            """,
            tuple(params),
        )
        row = dict(cur.fetchone() or {})

    total = row.get("total_calls", 0) or 0
    errors = (row.get("error_calls", 0) or 0) + (row.get("timeout_calls", 0) or 0)
    error_rate = errors / total if total > 0 else 0.0

    with get_cursor() as cur:
        params2: list = [days]
        tenant_filter2 = ""
        if tenant_id:
            tenant_filter2 = "AND tenant_id = %s"
            params2.append(tenant_id)

        cur.execute(
            f"""
            SELECT tool_name,
                   COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE status = 'error') AS errors
            FROM tool_call_logs
            WHERE created_at >= now() - (%s * INTERVAL '1 day')
            {tenant_filter2}
            GROUP BY tool_name
            ORDER BY errors DESC
            LIMIT 10
            """,
            tuple(params2),
        )
        per_tool = [dict(r) for r in cur.fetchall()]

    per_tool_rates = []
    for t in per_tool:
        t_total = t.get("total", 0) or 0
        t_errors = t.get("errors", 0) or 0
        per_tool_rates.append({
            "tool": t["tool_name"],
            "total_calls": t_total,
            "errors": t_errors,
            "error_rate": round(t_errors / t_total, 4) if t_total > 0 else 0.0,
        })

    return {
        "total_tool_calls": total,
        "success_calls": row.get("success_calls", 0) or 0,
        "error_calls": row.get("error_calls", 0) or 0,
        "timeout_calls": row.get("timeout_calls", 0) or 0,
        "overall_error_rate": round(error_rate, 4),
        "per_tool_error_rates": per_tool_rates,
        "period_days": days,
    }


def get_p50_latency_metrics(tenant_id: str | None = None, days: int = 30) -> dict:
    with get_cursor() as cur:
        params: list = [days]
        tenant_filter = ""
        if tenant_id:
            tenant_filter = "AND tenant_id = %s"
            params.append(tenant_id)

        cur.execute(
            f"""
            SELECT duration_ms
            FROM tool_call_logs
            WHERE created_at >= now() - (%s * INTERVAL '1 day')
            AND duration_ms IS NOT NULL
            AND duration_ms > 0
            {tenant_filter}
            ORDER BY duration_ms ASC
            """,
            tuple(params),
        )
        durations = [r["duration_ms"] for r in cur.fetchall()]

    if not durations:
        return {
            "p50_ms": 0, "p90_ms": 0, "p95_ms": 0, "p99_ms": 0,
            "mean_ms": 0, "min_ms": 0, "max_ms": 0,
            "sample_count": 0, "period_days": days,
        }

    def percentile(data: list, p: float) -> float:
        k = (len(data) - 1) * (p / 100.0)
        f = int(k)
        c = f + 1
        if c >= len(data):
            return float(data[f])
        return data[f] + (k - f) * (data[c] - data[f])

    return {
        "p50_ms": round(percentile(durations, 50), 1),
        "p90_ms": round(percentile(durations, 90), 1),
        "p95_ms": round(percentile(durations, 95), 1),
        "p99_ms": round(percentile(durations, 99), 1),
        "mean_ms": round(statistics.mean(durations), 1),
        "min_ms": min(durations),
        "max_ms": max(durations),
        "sample_count": len(durations),
        "period_days": days,
    }


def get_satisfaction_metrics(tenant_id: str | None = None, days: int = 30) -> dict:
    with get_cursor() as cur:
        params: list = [days]
        tenant_filter = ""
        if tenant_id:
            tenant_filter = "AND tenant_id = %s"
            params.append(tenant_id)

        cur.execute(
            f"""
            SELECT
                COUNT(*) AS total_feedback,
                AVG(satisfaction_score) AS avg_satisfaction,
                MIN(satisfaction_score) AS min_satisfaction,
                MAX(satisfaction_score) AS max_satisfaction,
                COUNT(*) FILTER (WHERE satisfaction_score >= 0.7) AS satisfied,
                COUNT(*) FILTER (WHERE satisfaction_score < 0.4) AS dissatisfied
            FROM user_feedback
            WHERE created_at >= now() - (%s * INTERVAL '1 day')
            AND satisfaction_score IS NOT NULL
            {tenant_filter}
            """,
            tuple(params),
        )
        row = dict(cur.fetchone() or {})

    total = row.get("total_feedback", 0) or 0
    avg = row.get("avg_satisfaction")
    if avg is None:
        avg = _estimate_satisfaction_from_sessions(tenant_id, days)

    return {
        "avg_satisfaction": round(float(avg), 4) if avg is not None else None,
        "total_feedback_responses": total,
        "satisfied_count": row.get("satisfied", 0) or 0,
        "dissatisfied_count": row.get("dissatisfied", 0) or 0,
        "satisfaction_rate": round(
            (row.get("satisfied", 0) or 0) / total if total > 0 else 0.0, 4
        ),
        "source": "explicit" if total > 0 else "estimated",
        "period_days": days,
    }


def _estimate_satisfaction_from_sessions(
    tenant_id: str | None, days: int
) -> float | None:
    with get_cursor() as cur:
        params: list = [days]
        tenant_filter = ""
        if tenant_id:
            tenant_filter = "AND sh.tenant_id = %s"
            params.append(tenant_id)

        cur.execute(
            f"""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE resolution_status = 'resolved') AS resolved,
                AVG(tool_calls_count) AS avg_tool_calls
            FROM session_history sh
            WHERE sh.started_at >= now() - (%s * INTERVAL '1 day')
            {tenant_filter}
            """,
            tuple(params),
        )
        row = dict(cur.fetchone() or {})

    total = row.get("total", 0) or 0
    if total == 0:
        return None

    resolved = row.get("resolved", 0) or 0
    resolution_rate = resolved / total
    avg_calls = float(row.get("avg_tool_calls") or 0)

    score = 0.4 + (resolution_rate * 0.4) + min(avg_calls / 50.0, 1.0) * 0.2
    return min(max(score, 0.0), 1.0)


def get_sentiment_metrics(tenant_id: str | None = None, days: int = 30) -> dict:
    with get_cursor() as cur:
        params: list = [days]
        tenant_filter = ""
        if tenant_id:
            tenant_filter = "AND tenant_id = %s"
            params.append(tenant_id)

        cur.execute(
            f"""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE sentiment = 'positive') AS positive,
                COUNT(*) FILTER (WHERE sentiment = 'neutral') AS neutral,
                COUNT(*) FILTER (WHERE sentiment = 'negative') AS negative,
                AVG(sentiment_score) AS avg_sentiment
            FROM user_feedback
            WHERE created_at >= now() - (%s * INTERVAL '1 day')
            AND sentiment IS NOT NULL
            {tenant_filter}
            """,
            tuple(params),
        )
        row = dict(cur.fetchone() or {})

    total = row.get("total", 0) or 0
    if total == 0:
        return {
            "avg_sentiment_score": None,
            "positive": 0, "neutral": 0, "negative": 0,
            "total_feedback": 0,
            "source": "none",
            "period_days": days,
        }

    return {
        "avg_sentiment_score": round(float(row.get("avg_sentiment") or 0), 4),
        "positive": row.get("positive", 0) or 0,
        "neutral": row.get("neutral", 0) or 0,
        "negative": row.get("negative", 0) or 0,
        "total_feedback": total,
        "source": "explicit",
        "period_days": days,
    }


def get_user_feedback_list(
    tenant_id: str | None = None, limit: int = 50
) -> list[dict]:
    with get_cursor() as cur:
        params: list = [limit]
        tenant_filter = ""
        if tenant_id:
            tenant_filter = "AND uf.tenant_id = %s"
            params.append(tenant_id)

        cur.execute(
            f"""
            SELECT uf.*, sh.task_description, sh.resolution_status,
                   t.email AS tenant_email, t.company_name
            FROM user_feedback uf
            LEFT JOIN session_history sh ON sh.id = uf.session_id
            LEFT JOIN tenants t ON t.id = uf.tenant_id
            WHERE 1=1
            {tenant_filter}
            ORDER BY uf.created_at DESC
            LIMIT %s
            """,
            tuple(params),
        )
        return [dict(r) for r in cur.fetchall()]


def submit_feedback(
    session_id: str,
    satisfaction_score: float | None = None,
    sentiment: str | None = None,
    sentiment_score: float | None = None,
    task_completed: bool | None = None,
    feedback_text: str | None = None,
    feedback_tags: list | None = None,
    source: str = "explicit",
) -> dict:
    with get_cursor() as cur:
        cur.execute(
            "SELECT tenant_id FROM session_history WHERE id = %s", (session_id,)
        )
        row = cur.fetchone()
        if not row:
            return {"error": "Session not found"}
        tenant_id = row["tenant_id"]

        cur.execute(
            """
            INSERT INTO user_feedback
                (session_id, tenant_id, satisfaction_score, sentiment,
                 sentiment_score, task_completed, feedback_text,
                 feedback_tags, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
            """,
            (
                session_id, tenant_id, satisfaction_score, sentiment,
                sentiment_score, task_completed, feedback_text,
                json.dumps(feedback_tags or []), source,
            ),
        )
        result = dict(cur.fetchone())
    return {"id": str(result["id"]), "created_at": str(result["created_at"])}


def get_all_metrics(tenant_id: str | None = None, days: int = 30) -> dict:
    return {
        "task_completion": get_task_completion_metrics(tenant_id, days),
        "error_rate": get_error_rate_metrics(tenant_id, days),
        "latency": get_p50_latency_metrics(tenant_id, days),
        "satisfaction": get_satisfaction_metrics(tenant_id, days),
        "sentiment": get_sentiment_metrics(tenant_id, days),
    }
