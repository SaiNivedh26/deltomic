#!/usr/bin/env python3
"""Minimal server for Gemini Live API voice agent.
Generates ephemeral tokens and serves static files.
The browser connects directly to Gemini's WebSocket — no audio relay through server.
"""

import asyncio
import datetime
import mimetypes
import os

from aiohttp import web
from google import genai
from dotenv import load_dotenv

load_dotenv()

HTTP_PORT = 8001
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

MODEL = os.environ.get("LIVE_MODEL", "gemini-3.1-flash-live-preview")

if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY / GOOGLE_API_KEY not found in environment.")
    client = genai.Client(http_options={"api_version": "v1alpha"})
else:
    client = genai.Client(api_key=GEMINI_API_KEY, http_options={"api_version": "v1alpha"})


async def get_ephemeral_token(request):
    try:
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        expire_time = now + datetime.timedelta(minutes=30)

        token = client.auth_tokens.create(
            config={
                "uses": 1,
                "expire_time": expire_time.isoformat(),
                "new_session_expire_time": (now + datetime.timedelta(minutes=1)).isoformat(),
                "http_options": {"api_version": "v1alpha"},
            }
        )

        return web.json_response({
            "token": token.name,
            "model": MODEL,
            "expires_at": expire_time.isoformat(),
        })
    except Exception as e:
        print(f"Error generating ephemeral token: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def serve_static_file(request):
    path = request.match_info.get("path", "live.html")
    path = path.lstrip("/")
    if ".." in path:
        return web.Response(text="Invalid path", status=400)
    if not path or path == "/":
        path = "live.html"

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    file_path = os.path.join(static_dir, path)

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return web.Response(text="File not found", status=404)

    content_type, _ = mimetypes.guess_type(file_path)
    if content_type is None:
        content_type = "application/octet-stream"

    with open(file_path, "rb") as f:
        content = f.read()
    return web.Response(body=content, content_type=content_type)


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
    app.router.add_post("/api/token", get_ephemeral_token)
    app.router.add_get("/", serve_static_file)
    app.router.add_get("/{path:.*}", serve_static_file)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", HTTP_PORT)
    await site.start()

    print(f"""
    Gemini Live Voice Agent
    Web:  http://localhost:{HTTP_PORT}
    API:  POST /api/token
    Model: {MODEL}
    """)

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())