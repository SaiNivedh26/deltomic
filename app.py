from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from langchain_core.runnables import RunnableGenerator

from pipeline import stt_stream, agent_stream, tts_stream

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("assemblyai_stt").setLevel(logging.DEBUG)
logging.getLogger("agent").setLevel(logging.DEBUG)
logging.getLogger("pipeline").setLevel(logging.DEBUG)

app = FastAPI(title="Voice Agent - Sandwich Shop")

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/")
async def index():
    """Serve the browser client."""
    html_path = STATIC_DIR / "index.html"
    return HTMLResponse(html_path.read_text())


pipeline = (
    RunnableGenerator(stt_stream)
    | RunnableGenerator(agent_stream)
    | RunnableGenerator(tts_stream)
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for streaming audio through the voice agent pipeline."""
    await websocket.accept()
    logging.info("WebSocket: Client connected")

    async def websocket_audio_stream():
        """Yield audio bytes from WebSocket."""
        while True:
            try:
                data = await websocket.receive_bytes()
                yield data
            except Exception:
                break

    output_stream = pipeline.atransform(websocket_audio_stream())

    try:
        async for event in output_stream:
            if event.type == "tts_chunk":
                await websocket.send_bytes(event.audio)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
    finally:
        logging.info("WebSocket: Client disconnected")