from __future__ import annotations

import json
import logging
import os
from typing import AsyncIterator

import websockets
from websockets import WebSocketClientProtocol

from events import STTChunkEvent, STTOutputEvent, VoiceAgentEvent

logger = logging.getLogger(__name__)


class AssemblyAISTT:
    """Client for AssemblyAI real-time speech-to-text via WebSocket.

    Sends 16kHz PCM audio and receives transcription events.
    """

    def __init__(self, api_key: str | None = None, sample_rate: int = 16000):
        self.api_key = api_key or os.getenv("ASSEMBLYAI_API_KEY")
        if not self.api_key:
            raise ValueError("ASSEMBLYAI_API_KEY is required")
        self.sample_rate = sample_rate
        self._ws: WebSocketClientProtocol | None = None

    async def send_audio(self, audio_chunk: bytes) -> None:
        """Send PCM audio bytes to AssemblyAI."""
        ws = await self._ensure_connection()
        await ws.send(audio_chunk)

    async def send_terminate(self) -> None:
        """Send terminate message to flush final transcripts."""
        ws = await self._ensure_connection()
        await ws.send(json.dumps({"type": "terminate"}))
        logger.info("STT: Sent terminate signal")

    async def receive_events(self) -> AsyncIterator[VoiceAgentEvent]:
        """Yield STT events as they arrive from AssemblyAI."""
        ws = await self._ensure_connection()
        async for raw_message in ws:
            message = json.loads(raw_message)
            msg_type = message.get("type")
            logger.debug(f"STT raw event: type={msg_type} keys={list(message.keys())}")

            if msg_type == "Turn":
                turn_order = message.get("turn_order", "")
                is_final = message.get("turn_is_formatted", False)
                transcript = message.get("transcript", "")
                logger.info(f"STT Turn: final={is_final} text='{transcript[:80]}'")
                if is_final and transcript.strip():
                    yield STTOutputEvent.create(transcript)
                else:
                    yield STTChunkEvent.create(transcript)
            elif msg_type == "Begin":
                logger.info(f"STT: Session began (id={message.get('id', '?')})")
            elif msg_type == "Termination":
                logger.info("STT: Session terminated")
                break

    async def _ensure_connection(self) -> WebSocketClientProtocol:
        """Establish WebSocket connection if not already connected."""
        if self._ws is None:
            url = (
                f"wss://streaming.assemblyai.com/v3/ws"
                f"?sample_rate={self.sample_rate}&format_turns=true"
            )
            self._ws = await websockets.connect(
                url,
                additional_headers={"Authorization": self.api_key},
            )
            logger.info("STT: WebSocket connected to AssemblyAI")
        return self._ws

    async def close(self) -> None:
        """Close the WebSocket connection."""
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
            logger.info("STT: WebSocket closed")