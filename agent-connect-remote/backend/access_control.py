from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

import boto3

from backend.config import (
    ALLOWED_COMMANDS,
    AWS_ACCESS_KEY,
    AWS_DEFAULT_REGION,
    AWS_SECRET_ACCESS_KEY,
)
from backend.db import get_cursor

logger = logging.getLogger(__name__)

ssm_client = boto3.client(
    "ssm",
    region_name=AWS_DEFAULT_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)


@dataclass
class AccessGrant:
    id: str
    customer_id: str
    managed_node_id: str
    status: str
    allowed_commands: list[str]
    expires_at: datetime
    max_session_duration_minutes: int


class AccessControlService:
    def request_access(
        self,
        customer_id: str,
        requested_by: str,
        duration_minutes: int = 10,
    ) -> str:
        with get_cursor() as cur:
            cur.execute(
                """
                SELECT managed_node_id FROM customer_machines
                WHERE customer_id = %s AND is_active = true
                LIMIT 1
                """,
                (customer_id,),
            )
            machine = cur.fetchone()

            if not machine:
                raise ValueError(f"No registered machine for customer: {customer_id}")

            grant_id = str(uuid.uuid4())
            expires_at = datetime.utcnow() + timedelta(minutes=duration_minutes)

            cur.execute(
                """
                INSERT INTO support_access_grants
                (id, customer_id, managed_node_id, requested_by, allowed_commands,
                 max_session_duration_minutes, expires_at, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
                """,
                (
                    grant_id,
                    customer_id,
                    machine["managed_node_id"],
                    requested_by,
                    json.dumps(ALLOWED_COMMANDS),
                    duration_minutes,
                    expires_at,
                ),
            )

            logger.info(f"Access requested: grant_id={grant_id}, customer={customer_id}")
            return grant_id

    def approve_access(self, grant_id: str, approved_by: str) -> AccessGrant:
        with get_cursor() as cur:
            cur.execute(
                """
                UPDATE support_access_grants
                SET status = 'approved', approved_by = %s, approved_at = now(),
                    updated_at = now()
                WHERE id = %s AND status = 'pending'
                RETURNING *
                """,
                (approved_by, grant_id),
            )

            grant = cur.fetchone()
            if not grant:
                raise ValueError("Grant not found or not pending")

            logger.info(f"Access approved: grant_id={grant_id}")
            return AccessGrant(
                id=grant["id"],
                customer_id=grant["customer_id"],
                managed_node_id=grant["managed_node_id"],
                status=grant["status"],
                allowed_commands=grant["allowed_commands"],
                expires_at=grant["expires_at"],
                max_session_duration_minutes=grant["max_session_duration_minutes"],
            )

    async def execute_command(self, grant_id: str, command: str, executed_by: str) -> dict:
        # Check grant in thread to avoid blocking event loop
        def check_grant():
            with get_cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM support_access_grants
                    WHERE id = %s AND status IN ('approved', 'active')
                    AND expires_at > now()
                    """,
                    (grant_id,),
                )
                grant = cur.fetchone()
                if not grant:
                    raise PermissionError("Access grant expired, revoked, or not approved")

                allowed = grant["allowed_commands"]
                # Check if command is allowed (exact match or prefix match for commands with args)
                is_allowed = False
                for allowed_cmd in allowed:
                    if command == allowed_cmd:
                        is_allowed = True
                        break
                    # Allow commands with additional arguments (e.g., "ls /home" matches "ls")
                    if command.startswith(allowed_cmd + " "):
                        is_allowed = True
                        break
                
                if not is_allowed:
                    raise PermissionError(f"Command not in allowlist: {command}")

                cur.execute(
                    """
                    UPDATE support_access_grants SET status = 'active', updated_at = now()
                    WHERE id = %s AND status = 'approved'
                    """,
                    (grant_id,),
                )
            return grant

        grant = await asyncio.to_thread(check_grant)

        result = await asyncio.to_thread(
            self._execute_ssm_command,
            grant["managed_node_id"],
            command,
            grant_id,
            executed_by,
        )

        return result

    def _execute_ssm_command(
        self, node_id: str, command: str, grant_id: str, executed_by: str
    ) -> dict:
        audit_id = str(uuid.uuid4())
        logger.info(f"SSM command start: audit_id={audit_id}, node={node_id}, cmd={command}")

        with get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO support_command_audit
                (id, grant_id, command, executed_by, started_at)
                VALUES (%s, %s, %s, %s, now())
                """,
                (audit_id, grant_id, command, executed_by),
            )
        logger.info("Audit record inserted, sending SSM command...")

        try:
            response = ssm_client.send_command(
                InstanceIds=[node_id],
                DocumentName="AWS-RunShellScript",
                Parameters={
                    "commands": [command],
                    "workingDirectory": ["/home/ubuntu"],
                },
                TimeoutSeconds=30,
            )

            command_id = response["Command"]["CommandId"]
            logger.info(f"SSM command sent: {command_id}, starting poll loop...")

            for i in range(12):
                logger.info(f"Poll attempt {i+1}/12...")
                time.sleep(5)
                invocation = ssm_client.get_command_invocation(
                    CommandId=command_id,
                    InstanceId=node_id,
                )

                status = invocation["Status"]
                logger.info(f"Poll {i+1} status: {status}")

                if status in ["Success", "Failed", "Cancelled", "TimedOut"]:
                    exit_code = invocation.get("ResponseCode", -1)
                    stdout = invocation.get("StandardOutputContent", "")
                    stderr = invocation.get("StandardErrorContent", "")
                    
                    stdout = stdout.replace("\x00", "") if stdout else ""
                    stderr = stderr.replace("\x00", "") if stderr else ""

                    with get_cursor() as cur:
                        cur.execute(
                            """
                            UPDATE support_command_audit
                            SET completed_at = now(), exit_code = %s,
                                stdout = %s, stderr = %s, command_id = %s
                            WHERE id = %s
                            """,
                            (exit_code, stdout, stderr, command_id, audit_id),
                        )

                    logger.info(f"Command completed: {command} -> {status}")

                    return {
                        "status": status,
                        "exit_code": exit_code,
                        "stdout": stdout,
                        "stderr": stderr,
                    }

            logger.error("Command timed out after 12 poll attempts")
            raise TimeoutError("Command execution timed out")

        except Exception as e:
            logger.error(f"SSM command error: {e}", exc_info=True)
            with get_cursor() as cur:
                cur.execute(
                    """
                    UPDATE support_command_audit
                    SET completed_at = now(), exit_code = -1, stderr = %s
                    WHERE id = %s
                    """,
                    (str(e), audit_id),
                )
            raise

    def revoke_access(self, grant_id: str, revoked_by: str, reason: str = ""):
        with get_cursor() as cur:
            cur.execute(
                """
                UPDATE support_access_grants
                SET status = 'revoked', revoked_at = now(),
                    revoked_by = %s, revoked_reason = %s, updated_at = now()
                WHERE id = %s
                """,
                (revoked_by, reason, grant_id),
            )

            cur.execute(
                "SELECT managed_node_id FROM support_access_grants WHERE id = %s",
                (grant_id,),
            )
            grant = cur.fetchone()

        if grant:
            self._terminate_sessions(grant["managed_node_id"])

        logger.info(f"Access revoked: grant_id={grant_id}")

    def _terminate_sessions(self, node_id: str):
        try:
            sessions = ssm_client.describe_sessions(
                State="Active",
                Filters=[{"key": "Target", "value": node_id}],
            )
            for session in sessions["Sessions"]:
                ssm_client.terminate_session(SessionId=session["SessionId"])
        except Exception as e:
            logger.error(f"Error terminating sessions: {e}")

    def get_grant_status(self, grant_id: str) -> dict | None:
        with get_cursor() as cur:
            cur.execute(
                """
                SELECT id, customer_id, managed_node_id, status, expires_at
                FROM support_access_grants WHERE id = %s
                """,
                (grant_id,),
            )
            return cur.fetchone()


access_control = AccessControlService()
