from __future__ import annotations

import json
import logging
from typing import Any

from backend.config import DESTRUCTIVE_PATTERNS
from backend.tool_config import get_task_profile

logger = logging.getLogger(__name__)


def critique_execution_plan(
    task_description: str,
    planned_commands: list[str],
    current_allowlist: list[str],
    task_profile: str = "diagnostic",
) -> dict[str, Any]:
    profile = get_task_profile(task_profile)
    restricted = profile.get("restricted_tools", []) if profile else []

    denied = []
    approved = []

    for cmd in planned_commands:
        if any(pat in cmd for pat in DESTRUCTIVE_PATTERNS):
            denied.append({"command": cmd, "reason": "Matches destructive pattern - requires explicit customer approval"})
        elif any(r in cmd for r in restricted):
            denied.append({"command": cmd, "reason": f"Restricted by {task_profile} profile"})
        else:
            approved.append(cmd)

    needs_expansion = [cmd for cmd in approved if not any(allow in cmd for allow in current_allowlist)]
    expansion_needed = list(set(cmd.split()[0] if cmd.split() else cmd for cmd in needs_expansion))

    risk = "low"
    if any(w in " ".join(planned_commands).lower() for w in ["docker run", "docker build", "systemctl", "service "]):
        risk = "medium"
    if any(w in " ".join(planned_commands).lower() for w in ["rm -rf", "format", "mkfs"]):
        risk = "high"

    result = {
        "approved": len(denied) == 0 or len(approved) > 0,
        "approved_commands": approved,
        "denied_commands": denied,
        "allowlist_expansion": {
            "needed": expansion_needed,
            "justification": f"Task requires: {task_description[:200]}",
        } if expansion_needed else None,
        "risk_level": risk,
        "critique": f"Plan reviewed: {len(approved)} commands approved, {len(denied)} denied. Risk: {risk}.",
        "suggested_modifications": [],
    }

    logger.info(f"Critique (rule-based): {len(approved)} approved, {len(denied)} denied, risk={risk}")
    return result


def expand_allowlist_if_needed(critique_result: dict) -> list[str]:
    expansion = critique_result.get("allowlist_expansion") or {}
    return expansion.get("needed", [])


def is_plan_approved(critique_result: dict) -> bool:
    return critique_result.get("approved", False)
