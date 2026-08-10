from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from backend.db import get_cursor
from backend.insights_engine import store_agent_learning, create_batch_insight

logger = logging.getLogger(__name__)


def detect_error_patterns(session_id: str, tool_logs: list[dict]) -> list[dict]:
    """Analyze tool execution logs to detect error patterns."""
    errors = []
    
    for log in tool_logs:
        if log.get("status") == "failed" or log.get("error"):
            error_info = {
                "tool_name": log.get("tool_name"),
                "command": log.get("tool_args", {}).get("command"),
                "error_message": log.get("error") or log.get("tool_result", ""),
                "timestamp": log.get("created_at"),
                "error_type": classify_error(log.get("error") or log.get("tool_result", "")),
            }
            errors.append(error_info)
    
    return errors


def classify_error(error_msg: str) -> str:
    """Classify error into categories for pattern matching."""
    error_msg_lower = error_msg.lower()
    
    if "permission denied" in error_msg_lower or "access denied" in error_msg_lower:
        return "permission_error"
    elif "not found" in error_msg_lower or "no such file" in error_msg_lower:
        return "not_found_error"
    elif "command not found" in error_msg_lower:
        return "command_not_found"
    elif "timeout" in error_msg_lower or "timed out" in error_msg_lower:
        return "timeout_error"
    elif "connection" in error_msg_lower or "network" in error_msg_lower:
        return "network_error"
    elif "syntax" in error_msg_lower or "invalid" in error_msg_lower:
        return "syntax_error"
    else:
        return "unknown_error"


def generate_correction_suggestions(errors: list[dict], session_context: dict) -> list[dict]:
    """Generate correction suggestions based on error patterns and past learnings."""
    suggestions = []
    
    for error in errors:
        suggestion = {
            "error": error,
            "suggested_fix": "",
            "confidence": 0.0,
            "source": "pattern_matching",
        }
        
        # Check past learnings for similar errors
        similar_learnings = get_similar_error_learnings(error["error_type"], error.get("command"))
        
        if similar_learnings:
            best_learning = similar_learnings[0]
            suggestion["suggested_fix"] = best_learning.get("learning_text", "")
            suggestion["confidence"] = best_learning.get("confidence", 0.5)
            suggestion["source"] = "agent_memory"
        else:
            # Generate generic suggestions based on error type
            suggestion["suggested_fix"] = get_generic_fix(error["error_type"])
            suggestion["confidence"] = 0.3
        
        suggestions.append(suggestion)
    
    return suggestions


def get_similar_error_learnings(error_type: str, command: str | None = None) -> list[dict]:
    """Retrieve past learnings about similar errors."""
    with get_cursor() as cur:
        if command:
            cur.execute(
                """
                SELECT * FROM agent_learnings
                WHERE issue_category = %s
                AND learning_text ILIKE %s
                AND is_active = true
                ORDER BY confidence DESC, times_applied DESC
                LIMIT 5
                """,
                (f"error_{error_type}", f"%{command}%",),
            )
        else:
            cur.execute(
                """
                SELECT * FROM agent_learnings
                WHERE issue_category = %s
                AND is_active = true
                ORDER BY confidence DESC, times_applied DESC
                LIMIT 5
                """,
                (f"error_{error_type}",),
            )
        return [dict(r) for r in cur.fetchall()]


def get_generic_fix(error_type: str) -> str:
    """Get generic fix suggestion based on error type."""
    fixes = {
        "permission_error": "Check file permissions or run with elevated privileges if appropriate",
        "not_found_error": "Verify the path exists or check for typos in the command",
        "command_not_found": "Ensure the command is installed and in PATH",
        "timeout_error": "The operation took too long. Consider breaking it into smaller steps",
        "network_error": "Check network connectivity and retry",
        "syntax_error": "Review command syntax and correct any errors",
        "unknown_error": "Review the error message and adjust the command accordingly",
    }
    return fixes.get(error_type, "Review and retry the operation")


def store_error_learning(
    session_id: str,
    error_type: str,
    error_message: str,
    correction_applied: str,
    success: bool,
) -> str | None:
    """Store error-correction pair as a learning for future reference."""
    learning_text = (
        f"Error: {error_type} - {error_message[:100]}\n"
        f"Correction: {correction_applied}\n"
        f"Result: {'Success' if success else 'Failed'}"
    )
    
    confidence = 0.8 if success else 0.3
    
    return store_agent_learning(
        tenant_id=None,
        issue_category=f"error_{error_type}",
        learning_text=learning_text,
        confidence=confidence,
        source_session_ids=[session_id],
    )


def run_self_healing_loop(
    session_id: str,
    tool_logs: list[dict],
    session_context: dict,
) -> dict:
    """Main self-healing loop: detect errors, suggest corrections, store learnings."""
    logger.info(f"Running self-healing analysis for session {session_id}")
    
    # Step 1: Detect error patterns
    errors = detect_error_patterns(session_id, tool_logs)
    
    if not errors:
        return {
            "session_id": session_id,
            "errors_detected": 0,
            "corrections_suggested": 0,
            "learnings_stored": 0,
            "status": "no_errors",
        }
    
    # Step 2: Generate correction suggestions
    suggestions = generate_correction_suggestions(errors, session_context)
    
    # Step 3: Store error-correction pairs as learnings
    learnings_stored = 0
    for suggestion in suggestions:
        error = suggestion["error"]
        learning_id = store_error_learning(
            session_id=session_id,
            error_type=error["error_type"],
            error_message=error["error_message"],
            correction_applied=suggestion["suggested_fix"],
            success=False,  # Will be updated if correction succeeds
        )
        if learning_id:
            learnings_stored += 1
    
    # Step 4: Create batch insight about error patterns
    if errors:
        error_summary = {
            "total_errors": len(errors),
            "error_types": list(set(e["error_type"] for e in errors)),
            "most_common_error": max(set(e["error_type"] for e in errors), key=lambda x: sum(1 for err in errors if err["error_type"] == x)),
        }
        create_batch_insight(
            insight_type="error_patterns",
            title=f"Detected {len(errors)} errors in session",
            description=f"Error types: {', '.join(error_summary['error_types'])}",
            data=error_summary,
            source_session_count=1,
        )
    
    result = {
        "session_id": session_id,
        "errors_detected": len(errors),
        "corrections_suggested": len(suggestions),
        "learnings_stored": learnings_stored,
        "error_details": errors,
        "suggestions": suggestions,
        "status": "healing_complete",
    }
    
    logger.info(f"Self-healing complete: {len(errors)} errors, {learnings_stored} learnings stored")
    
    return result


def get_self_healing_history(limit: int = 50) -> list[dict]:
    """Retrieve self-healing history from batch insights."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT * FROM batch_insights
            WHERE insight_type = 'error_patterns'
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        rows = [dict(r) for r in cur.fetchall()]
        for row in rows:
            if isinstance(row.get("data"), str):
                try:
                    row["data"] = json.loads(row["data"])
                except (json.JSONDecodeError, TypeError):
                    row["data"] = {}
        return rows


def get_error_learnings(limit: int = 50) -> list[dict]:
    """Retrieve all error-related learnings."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT * FROM agent_learnings
            WHERE issue_category LIKE 'error_%%'
            AND is_active = true
            ORDER BY confidence DESC, created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]
