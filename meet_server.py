#!/usr/bin/env python3
"""Server for creating Google Meet links, spinning up Recall bots,
and generating Gemini Live ephemeral tokens.

Flow:
1. User opens / → meet.html
2. User clicks "Create Meeting" → /api/create-meeting (Composio Google Calendar)
3. User clicks "Send Agent" → /api/join-meeting (Recall bot with output_media webpage)
4. Recall bot loads /agent → agent.html (Gemini Live + getUserMedia)
5. Bot streams agent audio into the Meet, receives meeting audio
"""

import asyncio
import datetime
import json
import mimetypes
import os

import aiohttp
from aiohttp import web
from google import genai
from dotenv import load_dotenv
from composio import Composio

load_dotenv()

HTTP_PORT = int(os.environ.get("MEET_SERVER_PORT", "8002"))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
LIVE_MODEL = os.environ.get("LIVE_MODEL", "gemini-3.1-flash-live-preview")

RECALL_API_KEY = os.environ.get("RECALL_API_KEY", "")
RECALL_BASE = "https://ap-northeast-1.recall.ai"

COMPOSIO_API_KEY = os.environ.get("COMPOSIO_API_KEY", "")
CAL_ACCOUNT_ID = os.environ.get("CAL_ACCOUNT_ID", "ca_KJVLl830D-Nl")
CAL_USER_ID = os.environ.get("CAL_USER_ID", "default-user")

genai_client = None
composio_client = None

if GEMINI_API_KEY:
    genai_client = genai.Client(api_key=GEMINI_API_KEY, http_options={"api_version": "v1alpha"})
else:
    print("Warning: GOOGLE_API_KEY not set — Gemini token endpoint will fail.")

if COMPOSIO_API_KEY:
    composio_client = Composio(api_key=COMPOSIO_API_KEY)
else:
    print("Warning: COMPOSIO_API_KEY not set — meeting creation will fail.")


# ─── Gemini ephemeral token ──────────────────────────────────
async def get_gemini_token(request):
    try:
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        expire_time = now + datetime.timedelta(minutes=30)
        token = genai_client.auth_tokens.create(
            config={
                "uses": 1,
                "expire_time": expire_time.isoformat(),
                "new_session_expire_time": (now + datetime.timedelta(minutes=2)).isoformat(),
                "http_options": {"api_version": "v1alpha"},
            }
        )
        return web.json_response({
            "token": token.name,
            "model": LIVE_MODEL,
            "expires_at": expire_time.isoformat(),
        })
    except Exception as e:
        print(f"[token] Error: {e}")
        return web.json_response({"error": str(e)}, status=500)


# ─── Create Google Meet via Composio ─────────────────────────
async def create_meeting(request):
    try:
        body = await request.json()
    except Exception:
        body = {}

    summary = body.get("summary", "AI Voice Agent Meeting")
    duration = body.get("duration_minutes", 30)

    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
    minutes_from_now = body.get("minutes_from_now", 2)
    start = (now + datetime.timedelta(minutes=minutes_from_now)).strftime("%Y-%m-%dT%H:%M:%S")

    try:
        result = composio_client.tools.execute(
            slug="googlecalendar_create_event",
            arguments={
                "start_datetime": start,
                "timezone": "Asia/Kolkata",
                "event_duration_minutes": duration,
                "summary": summary,
                "create_meeting_room": True,
            },
            connected_account_id=CAL_ACCOUNT_ID,
            user_id=CAL_USER_ID,
            dangerously_skip_version_check=True,
        )
        d = result.model_dump() if hasattr(result, "model_dump") else result
        data = d.get("data", d) if isinstance(d, dict) else d
        rd = data.get("response_data", data) if isinstance(data, dict) else data

        meet_url = rd.get("hangoutLink", "")
        event_id = rd.get("id", "")

        if not meet_url:
            return web.json_response({"error": "No hangoutLink in response", "raw": str(rd)[:500]}, status=500)

        print(f"[meeting] Created: {meet_url}")
        return web.json_response({
            "meet_url": meet_url,
            "event_id": event_id,
            "summary": summary,
        })
    except Exception as e:
        print(f"[meeting] Error: {e}")
        return web.json_response({"error": str(e)}, status=500)


# ─── Create Recall bot to join meeting ──────────────────────
async def join_meeting(request):
    try:
        body = await request.json()
    except Exception:
        body = {}

    meeting_url = body.get("meeting_url")
    agent_url = body.get("agent_url")
    bot_name = body.get("bot_name", "AI Voice Agent")

    if not meeting_url:
        return web.json_response({"error": "meeting_url required"}, status=400)
    if not agent_url:
        return web.json_response({"error": "agent_url required"}, status=400)

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
                    print(f"[recall] Error {resp.status}: {json.dumps(resp_data)[:500]}")
                    return web.json_response({"error": resp_data}, status=resp.status)

                bot_id = resp_data.get("id")
                print(f"[recall] Bot created: {bot_id}")
                return web.json_response({
                    "bot_id": bot_id,
                    "status_changes": resp_data.get("status_changes", []),
                    "meeting_url": meeting_url,
                })
    except Exception as e:
        print(f"[recall] Error: {e}")
        return web.json_response({"error": str(e)}, status=500)


# ─── Get Recall bot status ───────────────────────────────────
async def get_bot_status(request):
    bot_id = request.match_info.get("bot_id")
    if not bot_id:
        return web.json_response({"error": "bot_id required"}, status=400)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{RECALL_BASE}/api/v1/bot/{bot_id}/",
                headers={"Authorization": RECALL_API_KEY},
            ) as resp:
                resp_data = await resp.json()
                if resp.status != 200:
                    return web.json_response({"error": resp_data}, status=resp.status)

                status_changes = resp_data.get("status_changes", [])
                latest = status_changes[-1] if status_changes else {}
                return web.json_response({
                    "bot_id": bot_id,
                    "status": latest.get("code", "unknown"),
                    "status_changes": status_changes,
                    "meeting_url": resp_data.get("meeting_url"),
                    "recordings": resp_data.get("recordings", []),
                })
    except Exception as e:
        print(f"[bot-status] Error: {e}")
        return web.json_response({"error": str(e)}, status=500)


# ─── Leave the meeting (remove bot) ──────────────────────────
async def leave_meeting(request):
    bot_id = request.match_info.get("bot_id")
    if not bot_id:
        return web.json_response({"error": "bot_id required"}, status=400)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{RECALL_BASE}/api/v1/bot/{bot_id}/leave_call/",
                headers={"Authorization": RECALL_API_KEY},
            ) as resp:
                resp_data = await resp.json()
                return web.json_response({"bot_id": bot_id, "result": resp_data})
    except Exception as e:
        print(f"[leave] Error: {e}")
        return web.json_response({"error": str(e)}, status=500)


# ─── Static file server ──────────────────────────────────────
async def serve_static(request):
    path = request.match_info.get("path", "meet.html")
    path = path.lstrip("/")
    if ".." in path:
        return web.Response(text="Invalid path", status=400)
    if not path or path == "/":
        path = "meet.html"

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    file_path = os.path.join(static_dir, path)

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return web.Response(text="File not found", status=404)

    content_type, _ = mimetypes.guess_type(file_path)
    if content_type is None:
        content_type = "application/octet-stream"
    if path.endswith(".js"):
        content_type = "application/javascript"

    with open(file_path, "rb") as f:
        content = f.read()
    return web.Response(body=content, content_type=content_type)


# ─── Main ────────────────────────────────────────────────────
async def main():
    @web.middleware
    async def cors_middleware(request, handler):
        if request.method == "OPTIONS":
            return web.Response(status=200, headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            })
        response = await handler(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    app = web.Application(middlewares=[cors_middleware])
    app.router.add_post("/api/token", get_gemini_token)
    app.router.add_post("/api/create-meeting", create_meeting)
    app.router.add_post("/api/join-meeting", join_meeting)
    app.router.add_get("/api/bot/{bot_id}", get_bot_status)
    app.router.add_post("/api/leave-meeting/{bot_id}", leave_meeting)
    app.router.add_get("/", serve_static)
    app.router.add_get("/{path:.*}", serve_static)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", HTTP_PORT)
    await site.start()

    print(f"""
    Meet + Recall Bot + Gemini Live Agent
    Web:            http://localhost:{HTTP_PORT}
    Agent page:     http://localhost:{HTTP_PORT}/agent.html
    Recall region:  {RECALL_BASE}

    Endpoints:
      POST /api/token            — Gemini ephemeral token
      POST /api/create-meeting   — Create Google Meet via Composio
      POST /api/join-meeting     — Create Recall bot to join
      GET  /api/bot/{{id}}        — Bot status
      POST /api/leave-meeting/{{id}} — Remove bot from call
    """)

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())