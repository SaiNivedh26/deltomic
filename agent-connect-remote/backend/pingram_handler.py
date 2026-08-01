from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from pingram import Pingram, SendEmailRequest
from composio import Composio

from backend.access_control import access_control
from backend.config import BACKEND_URL, COMPOSIO_API_KEY, PINGRAM_API_KEY
from backend.db import get_cursor
from backend.onboarding import (
    create_hybrid_activation,
    verify_managed_instance_by_id,
)

logger = logging.getLogger(__name__)

_active_sessions: dict[str, dict[str, Any]] = {}
_composio_client = None

RECALL_API_KEY = os.environ.get("RECALL_API_KEY", "")
RECALL_BASE = "https://ap-northeast-1.recall.ai"
CAL_ACCOUNT_ID = os.environ.get("CAL_ACCOUNT_ID", "ca_KJVLl830D-Nl")
CAL_USER_ID = os.environ.get("CAL_USER_ID", "default-user")


def _get_composio():
    global _composio_client
    if _composio_client is None:
        _composio_client = Composio(api_key=COMPOSIO_API_KEY)
    return _composio_client


def _customer_id_from_email(email: str) -> str:
    h = hashlib.md5(email.lower().strip().encode()).hexdigest()[:12]
    return f"customer-{h}"


async def send_onboarding_email(to_email: str, activation: dict, customer_id: str, region: str = "us-east-1"):
    activation_id = activation["activation_id"]
    activation_code = activation["activation_code"]
    api_url = BACKEND_URL

    script = f"""#!/bin/bash
# Remote Support Setup Script
# Usage: ./customer.sh {customer_id} {activation_id} {activation_code}

set -e

CUSTOMER_ID="$1"
ACTIVATION_ID="$2"
ACTIVATION_CODE="$3"
API_URL="{api_url}"
REGION="{region}"

if [ -z "$CUSTOMER_ID" ] || [ -z "$ACTIVATION_ID" ] || [ -z "$ACTIVATION_CODE" ]; then
    echo "Usage: $0 <customer_id> <activation_id> <activation_code>"
    echo "Example: $0 {customer_id} {activation_id} {activation_code}"
    exit 1
fi

echo "=========================================="
echo "  Remote Support - Machine Registration"
echo "=========================================="
echo "Customer ID: $CUSTOMER_ID"
echo ""

# Install SSM Agent
echo "Installing SSM Agent..."
if command -v snap &> /dev/null; then
    sudo snap install amazon-ssm-agent --classic
else
    echo "ERROR: snap not found. Please install SSM Agent manually."
    exit 1
fi

# Find agent binary
SSM_AGENT_BIN=""
if [ -f /snap/amazon-ssm-agent/current/amazon-ssm-agent ]; then
    SSM_AGENT_BIN="/snap/amazon-ssm-agent/current/amazon-ssm-agent"
elif command -v amazon-ssm-agent &> /dev/null; then
    SSM_AGENT_BIN="amazon-ssm-agent"
else
    echo "ERROR: SSM Agent not found after install"
    exit 1
fi

echo "Registering machine with SSM..."
REGISTER_OUTPUT=$(echo "Yes" | sudo $SSM_AGENT_BIN -register \\
    -code "$ACTIVATION_CODE" \\
    -id "$ACTIVATION_ID" \\
    -region "$REGION" 2>&1)

echo "$REGISTER_OUTPUT"

MANAGED_NODE_ID=$(echo "$REGISTER_OUTPUT" | grep -oP 'mi-[a-f0-9]+' | head -1)

if [ -z "$MANAGED_NODE_ID" ]; then
    echo "ERROR: Could not extract managed instance ID"
    exit 1
fi

echo "Managed Instance ID: $MANAGED_NODE_ID"

# Register in database
echo "Registering in database..."
curl -s -X POST "$API_URL/onboarding/register" \\
    -H "Content-Type: application/json" \\
    -d '{{"customer_id": "'$CUSTOMER_ID'", "managed_node_id": "'$MANAGED_NODE_ID'", "machine_name": "'$(hostname)'"}}'

echo ""

# Request access
echo "Requesting access..."
GRANT_RESPONSE=$(curl -s -X POST "$API_URL/access/request" \\
    -H "Content-Type: application/json" \\
    -d '{{"customer_id": "'$CUSTOMER_ID'", "duration_minutes": 120}}')

echo "Grant response: $GRANT_RESPONSE"

GRANT_ID=$(echo "$GRANT_RESPONSE" | grep -oP '"grant_id":"[^"]+' | cut -d'"' -f4)

if [ -z "$GRANT_ID" ]; then
    echo "ERROR: Could not extract grant_id"
    exit 1
fi

echo "Grant ID: $GRANT_ID"

# Approve access
echo "Approving access..."
curl -s -X POST "$API_URL/access/approve" \\
    -H "Content-Type: application/json" \\
    -d '{{"grant_id": "'$GRANT_ID'", "approved_by": "customer-auto"}}'

echo ""

# Start agent
echo "Starting SSM Agent..."
if command -v snap &> /dev/null && snap list amazon-ssm-agent &> /dev/null; then
    echo "Using snap to restart SSM Agent..."
    sudo snap restart amazon-ssm-agent
    sleep 2
    sudo snap services amazon-ssm-agent
elif systemctl list-unit-files 2>/dev/null | grep -q "amazon-ssm-agent.service"; then
    sudo systemctl enable amazon-ssm-agent
    sudo systemctl restart amazon-ssm-agent
else
    echo "WARNING: Could not determine how to restart SSM Agent"
fi

echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Your machine is registered and access is approved."
echo "Waiting for support agent to connect..."
"""

    instructions = f"""
    <h2>Remote Support - Setup Instructions</h2>
    <p><strong>Step 1:</strong> Save the script below as <code>customer.sh</code></p>
    <p><strong>Step 2:</strong> Make it executable: <code>chmod +x customer.sh</code></p>
    <p><strong>Step 3:</strong> Run it on your server:</p>
    <pre><code>./customer.sh {customer_id} {activation_id} {activation_code}</code></pre>
    
    <h3>Script Content:</h3>
    <pre><code>{script}</code></pre>
    
    <p>After running the script, a support agent will be automatically assigned and will begin working on your machine.</p>
    """

    async with Pingram(api_key=PINGRAM_API_KEY) as client:
        response = await client.email.email_send(SendEmailRequest(
            type="onboarding_script",
            to=to_email,
            subject="Remote Support - Run This Script to Setup Access",
            html=instructions,
        ))
        logger.info(f"Onboarding email sent to {to_email}: {response}")
        return response


async def poll_for_instance(customer_id: str, timeout_minutes: int = 10):
    logger = logging.getLogger(__name__)
    deadline = datetime.utcnow() + timedelta(minutes=timeout_minutes)
    poll_count = 0

    while datetime.utcnow() < deadline:
        poll_count += 1
        with get_cursor() as cur:
            cur.execute(
                """
                SELECT managed_node_id, machine_name FROM customer_machines
                WHERE customer_id = %s AND is_active = true
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (customer_id,),
            )
            machine = cur.fetchone()

        if machine:
            logger.info(f"Poll #{poll_count}: Found machine in DB: {machine['managed_node_id']}, checking SSM status...")
            instance = verify_managed_instance_by_id(machine["managed_node_id"])
            if instance:
                logger.info(f"Poll #{poll_count}: SSM status = {instance.get('ping_status')}")
                if instance.get("ping_status") == "Online":
                    logger.info(f"Instance online: {machine['managed_node_id']} for {customer_id}")
                    return machine
            else:
                logger.warning(f"Poll #{poll_count}: Instance not found in SSM yet: {machine['managed_node_id']}")
        else:
            logger.info(f"Poll #{poll_count}: No machine in DB yet for {customer_id}")

        await asyncio.sleep(5)

    logger.warning(f"Timeout waiting for instance: {customer_id} after {poll_count} polls")
    return None


async def create_meet_link(customer_email: str, agent_id: str) -> str:
    """Create a Google Calendar event with Meet link using Composio."""
    try:
        composio = _get_composio()
        
        from zoneinfo import ZoneInfo
        start_time = datetime.now(ZoneInfo("Asia/Kolkata"))
        end_time = start_time + timedelta(hours=2)
        
        result = composio.tools.execute(
            slug="googlecalendar_create_event",
            arguments={
                "start_datetime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "timezone": "Asia/Kolkata",
                "event_duration_minutes": 59,
                "summary": f"Remote Support Session - {agent_id}",
                "description": f"Support session for {customer_email}. Agent ID: {agent_id}",
                "conference_data": {
                    "conference_solution": "hangoutsMeet"
                },
            },
            connected_account_id=CAL_ACCOUNT_ID,
            user_id=CAL_USER_ID,
            dangerously_skip_version_check=True,
        )
        
        d = result.model_dump() if hasattr(result, "model_dump") else result
        logger.info(f"Calendar event creation result: {d}")
        data = d.get("data", d) if isinstance(d, dict) else d
        rd = data.get("response_data", data) if isinstance(data, dict) else data
        
        meet_link = rd.get("hangoutLink", "")
        if not meet_link:
            meet_link = rd.get("htmlLink", "")
        
        logger.info(f"Created meet link: {meet_link}")
        return meet_link or f"https://calendar.google.com/calendar/event?eid={rd.get('id', '')}"
    except Exception as e:
        logger.error(f"Error creating meet link: {e}")
        return f"https://meet.google.com/agent-{agent_id}"


async def create_recall_bot(meeting_url: str, agent_url: str, bot_name: str = "AI Support Agent") -> dict:
    """Create a Recall bot to join the meeting and load the agent page."""
    payload = {
        "meeting_url": meeting_url,
        "bot_name": bot_name,
        "output_media": {
            "camera": {
                "kind": "webpage",
                "config": {"url": agent_url},
            },
        },
        "recording_config": {
            "include_bot_in_recording": {"audio": True},
        },
        "automatic_leave": {
            "waiting_room_timeout": 300,
            "empty_call_timeout": 60,
        },
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{RECALL_BASE}/api/v1/bot/",
                headers={"Authorization": RECALL_API_KEY, "Content-Type": "application/json"},
                json=payload,
            ) as resp:
                resp_data = await resp.json()
                if resp.status not in (200, 201):
                    logger.error(f"Recall error {resp.status}: {json.dumps(resp_data)[:500]}")
                    return {"error": resp_data, "status": resp.status}

                bot_id = resp_data.get("id")
                logger.info(f"Recall bot created: {bot_id}")
                return {
                    "bot_id": bot_id,
                    "status_changes": resp_data.get("status_changes", []),
                    "meeting_url": meeting_url,
                }
    except Exception as e:
        logger.error(f"Recall error: {e}")
        return {"error": str(e)}


async def on_instance_connected(customer_id: str, managed_node_id: str, to_email: str):
    grant_id = access_control.request_access(
        customer_id=customer_id,
        requested_by="pingram-auto",
        duration_minutes=120,
    )
    grant = access_control.approve_access(grant_id, "pingram-auto")

    agent_uuid = str(uuid.uuid4())[:8]
    agent_id = f"agent-{agent_uuid}"
    
    meet_url = await create_meet_link(to_email, agent_id)
    
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    agent_page_url = f"{backend_url}/agent.html?agent={agent_id}&grant={grant_id}"

    html_body = f"""
    <h2>Support Agent Assigned</h2>
    <p><strong>Agent:</strong> {agent_id}</p>
    <p><a href="{meet_url}">Join the support meeting</a></p>
    <p>The AI support agent will join the meeting and help diagnose and resolve your issue. The session is active as long as the meeting is open.</p>
    """

    async with Pingram(api_key=PINGRAM_API_KEY) as client:
        await client.email.email_send(SendEmailRequest(
            type="meet_link",
            to=to_email,
            subject=f"Support Agent {agent_id} Assigned - Join Meeting",
            html=html_body,
        ))

    recall_result = await create_recall_bot(meet_url, agent_page_url, f"Support Agent {agent_id}")
    
    _active_sessions[agent_id] = {
        "grant_id": grant_id,
        "customer_id": customer_id,
        "managed_node_id": managed_node_id,
        "agent_id": agent_id,
        "email": to_email,
        "meet_url": meet_url,
        "bot_id": recall_result.get("bot_id"),
        "started_at": datetime.utcnow().isoformat(),
    }

    logger.info(f"Session created: {agent_id} -> grant {grant_id}, node {managed_node_id}, bot {recall_result.get('bot_id')}")
    return {"agent_id": agent_id, "grant_id": grant_id, "meet_url": meet_url, "bot_id": recall_result.get("bot_id")}


async def handle_inbound_email(payload: dict):
    logger = logging.getLogger(__name__)
    logger.info(f"handle_inbound_email called with payload keys: {list(payload.keys())}")
    
    try:
        from_email = payload.get("from") or payload.get("sender") or payload.get("fromAddress") or ""
        logger.info(f"Extracted from_email: {from_email}")
        
        if not from_email:
            logger.error("No sender email in webhook payload")
            return {"error": "no sender email"}

        customer_id = _customer_id_from_email(from_email)
        logger.info(f"Inbound email from {from_email} -> customer_id={customer_id}")

        activation = create_hybrid_activation(customer_id)
        logger.info(f"Created activation: {activation['activation_id']}")
        
        try:
            await send_onboarding_email(from_email, activation, customer_id)
            logger.info(f"Sent onboarding email to {from_email}")
        except Exception as e:
            logger.error(f"Failed to send onboarding email: {e}", exc_info=True)
            return {"error": f"Failed to send email: {str(e)}"}

        asyncio.create_task(_poll_and_connect(customer_id, from_email))
        logger.info(f"Started polling task for {customer_id}")

        return {
            "status": "processing",
            "customer_id": customer_id,
            "activation_id": activation["activation_id"],
        }
    except Exception as e:
        logger.error(f"Error in handle_inbound_email: {e}", exc_info=True)
        return {"error": str(e)}


async def _poll_and_connect(customer_id: str, email: str):
    logger = logging.getLogger(__name__)
    logger.info(f"_poll_and_connect STARTED for {customer_id}, email={email}")
    try:
        machine = await poll_for_instance(customer_id)
        if machine:
            logger.info(f"Poll succeeded, calling on_instance_connected for {customer_id}")
            await on_instance_connected(customer_id, machine["managed_node_id"], email)
        else:
            logger.error(f"Instance never came online for {customer_id}")
    except Exception as e:
        logger.error(f"Error in poll_and_connect for {customer_id}: {e}", exc_info=True)


def get_active_session(agent_id: str) -> dict | None:
    return _active_sessions.get(agent_id)


def end_session(agent_id: str):
    session = _active_sessions.pop(agent_id, None)
    if session:
        try:
            access_control.revoke_access(
                grant_id=session["grant_id"],
                revoked_by="session-ended",
                reason="Meeting ended",
            )
            logger.info(f"Session ended: {agent_id}, grant revoked")
        except Exception as e:
            logger.error(f"Error revoking grant on session end: {e}")
    return session
