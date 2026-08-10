from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from backend.db import get_cursor

logger = logging.getLogger(__name__)


def create_batch_insight(
    insight_type: str,
    title: str,
    description: str = "",
    data: dict | None = None,
    tenant_id: str | None = None,
    source_session_count: int = 0,
    expires_at: datetime | None = None,
) -> str | None:
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO batch_insights
            (insight_type, title, description, data, tenant_id, source_session_count, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (insight_type, title, description, json.dumps(data or {}), tenant_id, source_session_count, expires_at),
        )
        row = cur.fetchone()
        return str(row["id"]) if row else None


def collect_weekly_issue_insights() -> list[dict]:
    insights = []
    with get_cursor() as cur:
        cur.execute("""
            SELECT issue_category, COUNT(*) as count,
                   ARRAY_AGG(DISTINCT task_description) as task_samples
            FROM session_history
            WHERE started_at >= now() - INTERVAL '7 days'
            AND issue_category IS NOT NULL AND issue_category != ''
            GROUP BY issue_category
            ORDER BY count DESC
        """)
        category_rows = cur.fetchall()

        for row in category_rows:
            d = dict(row)
            insight_id = create_batch_insight(
                insight_type="issue_frequency",
                title=f"{d['issue_category']}: {d['count']} sessions this week",
                description=f"Issue category '{d['issue_category']}' appeared {d['count']} times in the last 7 days.",
                data={
                    "category": d["issue_category"],
                    "count": d["count"],
                    "sample_tasks": (d["task_samples"] or [])[:5],
                },
                source_session_count=d["count"],
            )
            insights.append({"id": insight_id, "category": d["issue_category"], "count": d["count"]})

        cur.execute("""
            SELECT tool_name, COUNT(*) as count
            FROM tool_call_logs
            WHERE created_at >= now() - INTERVAL '7 days'
            GROUP BY tool_name
            ORDER BY count DESC
            LIMIT 10
        """)
        tool_rows = [dict(r) for r in cur.fetchall()]

        if tool_rows:
            create_batch_insight(
                insight_type="tool_usage",
                title="Top tools used this week",
                description="Most frequently used tools across all agents.",
                data={"tools": tool_rows},
                source_session_count=sum(t["count"] for t in tool_rows),
            )

        cur.execute("""
            SELECT resolution_status, COUNT(*) as count
            FROM session_history
            WHERE started_at >= now() - INTERVAL '7 days'
            GROUP BY resolution_status
            ORDER BY count DESC
        """)
        resolution_rows = [dict(r) for r in cur.fetchall()]

        if resolution_rows:
            create_batch_insight(
                insight_type="resolution_rates",
                title="Resolution rates this week",
                description="Distribution of session outcomes.",
                data={"resolutions": resolution_rows},
                source_session_count=sum(r["count"] for r in resolution_rows),
            )

    return insights


def store_agent_learning(
    tenant_id: str | None,
    issue_category: str,
    learning_text: str,
    confidence: float = 0.5,
    source_session_ids: list[str] | None = None,
) -> str | None:
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO agent_learnings
            (tenant_id, issue_category, learning_text, confidence, source_session_ids)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (tenant_id, issue_category, learning_text, confidence, json.dumps(source_session_ids or [])),
        )
        row = cur.fetchone()
        learning_id = str(row["id"]) if row else None
        logger.info(f"Stored learning {learning_id} for category '{issue_category}'")
        return learning_id


def get_relevant_learnings(
    issue_category: str,
    tenant_id: str | None = None,
    limit: int = 5,
) -> list[dict]:
    with get_cursor() as cur:
        if tenant_id:
            cur.execute(
                """
                SELECT * FROM agent_learnings
                WHERE is_active = true
                AND (issue_category = %s OR issue_category = 'general')
                AND (tenant_id = %s OR tenant_id IS NULL)
                ORDER BY confidence DESC, times_applied DESC
                LIMIT %s
                """,
                (issue_category, tenant_id, limit),
            )
        else:
            cur.execute(
                """
                SELECT * FROM agent_learnings
                WHERE is_active = true
                AND (issue_category = %s OR issue_category = 'general')
                ORDER BY confidence DESC, times_applied DESC
                LIMIT %s
                """,
                (issue_category, limit),
            )
        return [dict(r) for r in cur.fetchall()]


def increment_learning_applied(learning_id: str):
    with get_cursor() as cur:
        cur.execute(
            """
            UPDATE agent_learnings
            SET times_applied = times_applied + 1, updated_at = now()
            WHERE id = %s
            """,
            (learning_id,),
        )


def generate_learnings_from_sessions() -> list[dict]:
    learnings = []
    with get_cursor() as cur:
        cur.execute("""
            SELECT issue_category,
                   COUNT(*) as total,
                   SUM(CASE WHEN resolution_status = 'resolved' THEN 1 ELSE 0 END) as resolved,
                   AVG(tool_calls_count) as avg_tools
            FROM session_history
            WHERE started_at >= now() - INTERVAL '7 days'
            AND issue_category IS NOT NULL AND issue_category != ''
            GROUP BY issue_category
            HAVING COUNT(*) >= 2
        """)
        rows = cur.fetchall()

        for row in rows:
            d = dict(row)
            category = d["issue_category"]
            total = d["total"]
            resolved = d["resolved"]
            avg_tools = float(d["avg_tools"]) if d["avg_tools"] else 0
            resolution_rate = resolved / total if total > 0 else 0

            if resolution_rate >= 0.8:
                learning_text = (
                    f"For '{category}' issues, the standard diagnostic approach "
                    f"(avg {avg_tools:.1f} tool calls) resolves {resolution_rate:.0%} of cases. "
                    f"Prioritize read-only diagnostics first, then targeted remediation."
                )
                confidence = min(0.9, 0.5 + (resolution_rate * 0.3) + (total * 0.02))
            elif resolution_rate < 0.5:
                learning_text = (
                    f"'{category}' issues have low resolution rate ({resolution_rate:.0%}). "
                    f"Consider escalating faster or requesting additional context from customer. "
                    f"Avg {avg_tools:.1f} tool calls per session suggests complex multi-step resolution."
                )
                confidence = 0.4
            else:
                learning_text = (
                    f"'{category}' issues resolve at {resolution_rate:.0%} rate. "
                    f"Average {avg_tools:.1f} tool calls. Review unsuccessful cases for patterns."
                )
                confidence = 0.5

            learning_id = store_agent_learning(
                tenant_id=None,
                issue_category=category,
                learning_text=learning_text,
                confidence=confidence,
            )
            learnings.append({"id": learning_id, "category": category, "confidence": confidence})

    return learnings


def get_batch_insights(
    insight_type: str | None = None,
    limit: int = 50,
) -> list[dict]:
    with get_cursor() as cur:
        if insight_type:
            cur.execute(
                """
                SELECT * FROM batch_insights
                WHERE insight_type = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (insight_type, limit),
            )
        else:
            cur.execute(
                """
                SELECT * FROM batch_insights
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
        return [dict(r) for r in cur.fetchall()]


def get_agent_learnings(
    issue_category: str | None = None,
    limit: int = 50,
) -> list[dict]:
    with get_cursor() as cur:
        if issue_category:
            cur.execute(
                """
                SELECT * FROM agent_learnings
                WHERE issue_category = %s AND is_active = true
                ORDER BY confidence DESC, created_at DESC
                LIMIT %s
                """,
                (issue_category, limit),
            )
        else:
            cur.execute(
                """
                SELECT * FROM agent_learnings
                WHERE is_active = true
                ORDER BY confidence DESC, created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
        return [dict(r) for r in cur.fetchall()]


def get_dashboard_analytics() -> dict:
    with get_cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) as total_sessions,
                   COUNT(DISTINCT tenant_id) as unique_tenants,
                   SUM(tool_calls_count) as total_tool_calls,
                   SUM(CASE WHEN resolution_status = 'resolved' THEN 1 ELSE 0 END) as resolved_count
            FROM session_history
            WHERE started_at >= now() - INTERVAL '7 days'
        """)
        session_stats = dict(cur.fetchone() or {})

        cur.execute("""
            SELECT issue_category, COUNT(*) as count
            FROM session_history
            WHERE started_at >= now() - INTERVAL '7 days'
            AND issue_category IS NOT NULL AND issue_category != ''
            GROUP BY issue_category
            ORDER BY count DESC
            LIMIT 10
        """)
        top_issues = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT COUNT(*) as total FROM agent_learnings WHERE is_active = true")
        learnings_count = cur.fetchone()

        cur.execute("SELECT COUNT(*) as total FROM batch_insights WHERE created_at >= now() - INTERVAL '7 days'")
        insights_count = cur.fetchone()

        cur.execute("SELECT COUNT(*) as total FROM session_embeddings WHERE created_at >= now() - INTERVAL '7 days'")
        embeddings_count = cur.fetchone()

        return {
            "session_stats": session_stats,
            "top_issues": top_issues,
            "total_learnings": learnings_count["total"] if learnings_count else 0,
            "weekly_insights": insights_count["total"] if insights_count else 0,
            "weekly_embeddings": embeddings_count["total"] if embeddings_count else 0,
        }
