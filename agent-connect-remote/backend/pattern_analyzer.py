from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from typing import Any

from backend.db import get_cursor

logger = logging.getLogger(__name__)


def extract_tool_sequences(session_id: str) -> list[str]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT span_name, status
            FROM agent_traces
            WHERE session_id = %s AND span_kind = 'tool'
            ORDER BY start_time ASC
            """,
            (session_id,),
        )
        rows = cur.fetchall()
    return [f"{r['span_name']}:{r['status']}" for r in rows]


def extract_all_session_sequences(limit: int = 200) -> list[dict]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT sh.id as session_id, sh.resolution_status, sh.issue_category,
                   sh.tool_calls_count, sh.tenant_id
            FROM session_history sh
            WHERE sh.started_at >= now() - INTERVAL '30 days'
            ORDER BY sh.started_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        sessions = [dict(r) for r in cur.fetchall()]

    for session in sessions:
        session["tool_sequence"] = extract_tool_sequences(session["session_id"])

    return sessions


def find_ngram_patterns(sequences: list[list[str]], n: int = 3, min_count: int = 2) -> list[dict]:
    ngram_counter: Counter[tuple[str, ...]] = Counter()
    ngram_sessions: dict[tuple[str, ...], set[str]] = defaultdict(set)

    for seq in sequences:
        session_id = seq.get("session_id", "") if isinstance(seq, dict) else ""
        tools = seq.get("tool_sequence", []) if isinstance(seq, dict) else seq
        for i in range(len(tools) - n + 1):
            ngram = tuple(tools[i : i + n])
            ngram_counter[ngram] += 1
            ngram_sessions[ngram].add(session_id)

    patterns = []
    for ngram, count in ngram_counter.most_common(50):
        if count < min_count:
            continue
        patterns.append(
            {
                "pattern": list(ngram),
                "length": n,
                "frequency": count,
                "session_count": len(ngram_sessions[ngram]),
                "tools": [n.split(":")[0].replace("tool.", "") for n in ngram],
            }
        )
    return patterns


def compare_success_failure_patterns(sessions: list[dict]) -> dict:
    successful = [s for s in sessions if s.get("resolution_status") == "resolved"]
    failed = [s for s in sessions if s.get("resolution_status") not in ("resolved", None)]

    success_sequences = [s["tool_sequence"] for s in successful if s.get("tool_sequence")]
    failure_sequences = [s["tool_sequence"] for s in failed if s.get("tool_sequence")]

    success_patterns = find_ngram_patterns(success_sequences, n=3, min_count=2)
    failure_patterns = find_ngram_patterns(failure_sequences, n=3, min_count=2)

    success_tools: Counter[str] = Counter()
    failure_tools: Counter[str] = Counter()

    for seq in success_sequences:
        for tool in seq:
            success_tools[tool.split(":")[0].replace("tool.", "")] += 1

    for seq in failure_sequences:
        for tool in seq:
            failure_tools[tool.split(":")[0].replace("tool.", "")] += 1

    return {
        "successful_sessions": len(successful),
        "failed_sessions": len(failed),
        "success_patterns": success_patterns[:10],
        "failure_patterns": failure_patterns[:10],
        "success_tool_distribution": dict(success_tools.most_common(15)),
        "failure_tool_distribution": dict(failure_tools.most_common(15)),
    }


def detect_failure_trajectories(sessions: list[dict]) -> list[dict]:
    trajectories = []

    for session in sessions:
        if session.get("resolution_status") == "resolved":
            continue
        tools = session.get("tool_sequence", [])
        if not tools:
            continue

        error_tools = [t for t in tools if t.endswith(":error")]
        if not error_tools:
            continue

        error_tool_names = [t.split(":")[0].replace("tool.", "") for t in error_tools]
        error_counter = Counter(error_tool_names)
        most_common_error = error_counter.most_common(1)[0] if error_counter else None

        loop_detected = any(error_counter[t] >= 3 for t in error_counter)

        trajectories.append(
            {
                "session_id": session["session_id"],
                "issue_category": session.get("issue_category"),
                "total_tools": len(tools),
                "error_count": len(error_tools),
                "error_tools": dict(error_counter),
                "most_common_error_tool": most_common_error[0] if most_common_error else None,
                "most_common_error_count": most_common_error[1] if most_common_error else 0,
                "loop_detected": loop_detected,
                "sequence": tools[:20],
            }
        )

    trajectories.sort(key=lambda x: x["error_count"], reverse=True)
    return trajectories


def get_pattern_analysis(limit: int = 200) -> dict:
    sessions = extract_all_session_sequences(limit=limit)
    all_sequences = [s["tool_sequence"] for s in sessions if s.get("tool_sequence")]

    overall_patterns = find_ngram_patterns(all_sequences, n=3, min_count=2)
    comparison = compare_success_failure_patterns(sessions)
    trajectories = detect_failure_trajectories(sessions)

    return {
        "total_sessions_analyzed": len(sessions),
        "sessions_with_traces": len(all_sequences),
        "recurring_patterns": overall_patterns[:20],
        "success_vs_failure": comparison,
        "failure_trajectories": trajectories[:20],
    }
