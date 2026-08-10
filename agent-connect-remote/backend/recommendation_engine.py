from __future__ import annotations

import json
import logging
import os
from typing import Any

from backend.config import BEDROCK_MODEL, BEDROCK_REGION, BEDROCK_API_KEY
from backend.db import get_cursor

logger = logging.getLogger(__name__)

_qwen_client = None


def _get_qwen_client():
    global _qwen_client
    if _qwen_client is not None:
        return _qwen_client

    from langchain_aws import ChatBedrockConverse

    os.environ["AWS_BEARER_TOKEN_BEDROCK"] = BEDROCK_API_KEY

    _qwen_client = ChatBedrockConverse(
        model=BEDROCK_MODEL,
        region_name=BEDROCK_REGION,
        temperature=0.2,
        max_tokens=8192,
    )
    logger.info(f"Recommendation Engine: Initialized Qwen via Bedrock ({BEDROCK_MODEL})")
    return _qwen_client


def _invoke_qwen(prompt: str) -> str:
    client = _get_qwen_client()
    from langchain.messages import HumanMessage

    response = client.invoke([HumanMessage(content=prompt)])
    return response.content


def gather_analysis_context() -> dict:
    from backend.pattern_analyzer import get_pattern_analysis
    from backend.failure_analyzer import get_failure_analysis
    from backend.usage_analyzer import get_usage_analysis
    from backend.metrics_engine import get_all_metrics

    patterns = get_pattern_analysis(limit=100)
    failures = get_failure_analysis()
    usage = get_usage_analysis()
    metrics = get_all_metrics()

    return {
        "patterns": patterns,
        "failures": failures,
        "usage": usage,
        "metrics": metrics,
    }


def generate_recommendations() -> dict:
    context = gather_analysis_context()

    summary = _build_context_summary(context)

    prompt = f"""You are an AI agent performance analyst. Analyze this data and provide recommendations.

## Agent Interaction Summary

{summary}

## Task

Provide a structured analysis in JSON format. Be concise and specific.

Respond with ONLY valid JSON (no markdown, no explanations outside JSON):
{{
  "critical_issues": [
    {{"title": "...", "description": "...", "priority": "critical", "evidence": "..."}}
  ],
  "recommendations": [
    {{"title": "...", "priority": "high", "category": "tool_usage|error_handling|workflow|prompt|configuration|latency|satisfaction", "description": "...", "expected_impact": "...", "confidence": 0.8}}
  ],
  "tool_analysis": [
    {{"tool": "...", "assessment": "overused|underused|misused|optimal", "suggestion": "..."}}
  ],
  "overall_health_score": 0.75,
  "summary": "one paragraph executive summary"
}}

Limit: max 5 critical issues, max 8 recommendations, max 10 tool analyses."""

    try:
        raw_response = _invoke_qwen(prompt)
        parsed = _parse_json_response(raw_response)
        parsed["context_summary"] = {
            "sessions_analyzed": context["patterns"].get("total_sessions_analyzed", 0),
            "error_clusters": context["failures"].get("total_clusters", 0),
            "error_loops": context["failures"].get("total_loops", 0),
            "workflow_patterns": len(context["usage"].get("workflow_patterns", [])),
        }
        parsed["raw_context"] = context
        return parsed
    except Exception as e:
        logger.error(f"Qwen recommendation generation failed: {e}")
        return {
            "critical_issues": [],
            "recommendations": [],
            "tool_analysis": [],
            "overall_health_score": 0,
            "summary": f"Analysis failed: {str(e)}",
            "context_summary": {},
            "raw_context": context,
        }


def generate_session_recommendation(session_id: str) -> dict:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT sh.*, t.email, t.company_name
            FROM session_history sh
            LEFT JOIN tenants t ON t.id = sh.tenant_id
            WHERE sh.id = %s
            """,
            (session_id,),
        )
        session = cur.fetchone()
        if not session:
            return {"error": "Session not found"}

        cur.execute(
            """
            SELECT span_name, span_kind, status, input_data, output_data, duration_ms
            FROM agent_traces
            WHERE session_id = %s
            ORDER BY start_time ASC
            LIMIT 100
            """,
            (session_id,),
        )
        traces = [dict(r) for r in cur.fetchall()]

    tool_chain = []
    errors = []
    for t in traces:
        if t["span_kind"] == "tool":
            tool_chain.append(t["span_name"].replace("tool.", ""))
            if t["status"] == "error":
                output = t.get("output_data", {})
                if isinstance(output, str):
                    try:
                        output = json.loads(output)
                    except (json.JSONDecodeError, TypeError):
                        output = {"result": output}
                errors.append(
                    {
                        "tool": t["span_name"].replace("tool.", ""),
                        "error": str(output.get("result", ""))[:200],
                    }
                )

    prompt = f"""Analyze this agent support session and provide specific recommendations for improvement.

## Session Details
- Task: {session.get('task_description', 'N/A')}
- Issue Category: {session.get('issue_category', 'N/A')}
- Resolution: {session.get('resolution_status', 'N/A')}
- Tool Calls: {session.get('tool_calls_count', 0)}
- Customer: {session.get('email', 'N/A')}

## Tool Execution Chain
{' -> '.join(tool_chain[:30]) if tool_chain else 'No tool traces'}

## Errors Encountered
{json.dumps(errors[:10], indent=2) if errors else 'No errors'}

Provide recommendations in JSON:
{{
  "what_went_well": ["..."],
  "what_went_wrong": ["..."],
  "recommendations": [
    {{"area": "...", "suggestion": "...", "priority": "critical|high|medium|low"}}
  ],
  "estimated_improvement": "..."
}}"""

    try:
        raw_response = _invoke_qwen(prompt)
        parsed = _parse_json_response(raw_response)
        parsed["session_id"] = session_id
        return parsed
    except Exception as e:
        logger.error(f"Session recommendation failed: {e}")
        return {"session_id": session_id, "error": str(e)}


def _build_context_summary(context: dict) -> str:
    parts = []

    patterns = context.get("patterns", {})
    parts.append(
        f"Sessions analyzed: {patterns.get('total_sessions_analyzed', 0)}"
    )

    comparison = patterns.get("success_vs_failure", {})
    parts.append(
        f"Successful sessions: {comparison.get('successful_sessions', 0)}, "
        f"Failed sessions: {comparison.get('failed_sessions', 0)}"
    )

    recurring = patterns.get("recurring_patterns", [])
    if recurring:
        top_patterns = recurring[:5]
        parts.append("Top recurring tool sequences:")
        for p in top_patterns:
            parts.append(f"  - {' -> '.join(p['tools'])} (seen {p['frequency']}x)")

    failures = context.get("failures", {})
    summary = failures.get("summary", {})
    parts.append(
        f"\nOverall resolution rate: {summary.get('resolution_rate', 0):.1%}"
    )

    clusters = failures.get("error_clusters", [])
    if clusters:
        parts.append("Top error clusters:")
        for c in clusters[:5]:
            parts.append(
                f"  - {c['tool']}:{c['error_type']} ({c['occurrence_count']} occurrences, "
                f"{c['affected_sessions']} sessions)"
            )

    loops = failures.get("error_loops", [])
    if loops:
        parts.append(f"Error loops detected: {len(loops)}")
        for loop in loops[:3]:
            parts.append(
                f"  - Session {loop['session_id'][:8]}: {loop['loop_length']} consecutive errors on {loop['primary_tool']}"
            )

    usage = context.get("usage", {})
    metrics = usage.get("metrics", {})
    session_m = metrics.get("session_metrics", {})
    parts.append(
        f"\nAvg tool calls/session: {session_m.get('avg_tool_calls', 0)}, "
        f"Avg duration: {session_m.get('avg_duration_secs', 0)}s"
    )

    workflows = usage.get("workflow_patterns", [])
    if workflows:
        parts.append("Common workflow patterns:")
        for w in workflows[:5]:
            parts.append(
                f"  - {' -> '.join(w['workflow_signature'][:5])} "
                f"(freq: {w['frequency']}, success: {w['success_rate']:.0%})"
            )

    core_metrics = context.get("metrics", {})

    task_comp = core_metrics.get("task_completion", {})
    parts.append(
        f"\nTask completion rate: {task_comp.get('completion_rate', 0):.1%} "
        f"({task_comp.get('resolved', 0)}/{task_comp.get('total_sessions', 0)} sessions)"
    )

    error_rate = core_metrics.get("error_rate", {})
    parts.append(
        f"Overall tool error rate: {error_rate.get('overall_error_rate', 0):.1%} "
        f"({error_rate.get('error_calls', 0)} errors / {error_rate.get('total_tool_calls', 0)} calls)"
    )

    latency = core_metrics.get("latency", {})
    parts.append(
        f"P50 latency: {latency.get('p50_ms', 0)}ms, "
        f"P95: {latency.get('p95_ms', 0)}ms, "
        f"P99: {latency.get('p99_ms', 0)}ms"
    )

    satisfaction = core_metrics.get("satisfaction", {})
    sat_score = satisfaction.get("avg_satisfaction")
    if sat_score is not None:
        parts.append(
            f"Satisfaction score: {sat_score:.2f}/1.0 "
            f"(source: {satisfaction.get('source', 'unknown')}, "
            f"responses: {satisfaction.get('total_feedback_responses', 0)})"
        )

    sentiment = core_metrics.get("sentiment", {})
    sent_score = sentiment.get("avg_sentiment_score")
    if sent_score is not None:
        parts.append(
            f"User sentiment: {sent_score:.2f} "
            f"(positive: {sentiment.get('positive', 0)}, "
            f"neutral: {sentiment.get('neutral', 0)}, "
            f"negative: {sentiment.get('negative', 0)})"
        )

    return "\n".join(parts)


def _parse_json_response(response: str) -> dict:
    cleaned = response.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        start = 1
        end = len(lines)
        for i, line in enumerate(lines):
            if i > 0 and line.strip().startswith("```"):
                end = i
                break
        cleaned = "\n".join(lines[start:end])

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        brace_start = cleaned.find("{")
        brace_end = cleaned.rfind("}")
        if brace_start != -1 and brace_end != -1:
            try:
                return json.loads(cleaned[brace_start : brace_end + 1])
            except json.JSONDecodeError:
                pass
        
        if brace_start != -1:
            truncated = cleaned[brace_start:]
            for end_char in ["}", "]", ","]:
                last_idx = truncated.rfind(end_char)
                if last_idx > 0:
                    try:
                        candidate = truncated[:last_idx + 1]
                        if not candidate.endswith("}"):
                            candidate = candidate.rstrip(",]") + "}"
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        continue

        return {
            "critical_issues": [],
            "recommendations": [],
            "tool_analysis": [],
            "overall_health_score": 0,
            "summary": cleaned[:500],
        }
