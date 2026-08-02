from __future__ import annotations

import json
import logging
from typing import Any

from backend.config import ALLOWED_COMMANDS, DESTRUCTIVE_PATTERNS, DEFAULT_TASK_PROFILE
from backend.db import get_cursor

logger = logging.getLogger(__name__)


def get_task_profile(name: str) -> dict | None:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM task_profiles WHERE name = %s AND is_active = true", (name,))
        row = cur.fetchone()
        return dict(row) if row else None


def list_task_profiles() -> list[dict]:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM task_profiles WHERE is_active = true ORDER BY name")
        return [dict(r) for r in cur.fetchall()]


def create_task_profile(
    name: str,
    description: str = "",
    allowed_tools: list[str] | None = None,
    restricted_tools: list[str] | None = None,
    requires_escalation: list[str] | None = None,
    default_commands: list[str] | None = None,
    escalation_commands: list[str] | None = None,
) -> dict:
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO task_profiles
            (name, description, allowed_tools, restricted_tools, requires_escalation,
             default_commands, escalation_commands)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                name,
                description,
                json.dumps(allowed_tools or ["list_available_commands", "run_command", "revoke_access"]),
                json.dumps(restricted_tools or []),
                json.dumps(requires_escalation or []),
                json.dumps(default_commands or ALLOWED_COMMANDS),
                json.dumps(escalation_commands or []),
            ),
        )
        return dict(cur.fetchone())


def is_destructive(command: str) -> bool:
    cmd_lower = command.lower().strip()
    for pattern in DESTRUCTIVE_PATTERNS:
        if pattern in cmd_lower:
            return True
    return False


def needs_escalation(command: str, profile_name: str = DEFAULT_TASK_PROFILE) -> bool:
    profile = get_task_profile(profile_name)
    if not profile:
        return is_destructive(command)

    escalation_patterns = profile.get("escalation_commands", [])
    for pattern in escalation_patterns:
        if pattern in command:
            return True

    return is_destructive(command)


def get_allowed_commands_for_profile(profile_name: str = DEFAULT_TASK_PROFILE) -> list[str]:
    profile = get_task_profile(profile_name)
    if profile:
        return profile.get("default_commands", ALLOWED_COMMANDS)
    return ALLOWED_COMMANDS


def resolve_task_profile(task_description: str) -> str:
    task_lower = task_description.lower()

    remediation_keywords = [
        "fix", "repair", "install", "configure", "update", "upgrade",
        "deploy", "restart", "reset", "create", "write", "edit",
        "modify", "change", "setup", "build", "compile",
    ]
    full_keywords = [
        "full access", "autonomous", "complete", "end-to-end",
        "multi-step", "complex", "debug", "troubleshoot",
    ]

    for kw in full_keywords:
        if kw in task_lower:
            return "full_autonomous"

    for kw in remediation_keywords:
        if kw in task_lower:
            return "remediation"

    return DEFAULT_TASK_PROFILE


def build_dynamic_allowlist(
    profile_name: str = DEFAULT_TASK_PROFILE,
    escalated: bool = False,
) -> list[str]:
    profile = get_task_profile(profile_name)
    if not profile:
        return ALLOWED_COMMANDS

    base_commands = list(profile.get("default_commands", ALLOWED_COMMANDS))

    if escalated:
        escalation_cmds = profile.get("escalation_commands", [])
        base_commands.extend(escalation_cmds)

    restricted = set(profile.get("restricted_tools", []))
    return [cmd for cmd in base_commands if cmd not in restricted]
