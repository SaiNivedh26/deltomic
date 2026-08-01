from __future__ import annotations

import logging

import contextlib
import asyncio
from typing import AsyncIterator

from assemblyai_stt import AssemblyAISTT
from cartesia_tts import CartesiaTTS
from events import VoiceAgentEvent
from utils import merge_async_iters

logger = logging.getLogger(__name__)


async def stt_stream(
    audio_stream: AsyncIterator[bytes],
) -> AsyncIterator[VoiceAgentEvent]:
    """Transform stream: Audio (Bytes) -> Voice Events (VoiceAgentEvent).

    Uses a producer-consumer pattern where:
    - Producer: Reads audio chunks and sends them to AssemblyAI
    - Consumer: Receives transcription events from AssemblyAI
    """
    stt = AssemblyAISTT(sample_rate=16000)
    audio_chunk_count = 0

    async def send_audio():
        """Background task that pumps audio chunks to AssemblyAI."""
        nonlocal audio_chunk_count
        try:
            async for audio_chunk in audio_stream:
                audio_chunk_count += 1
                if audio_chunk_count % 50 == 0:
                    logger.info(f"STT: Sent {audio_chunk_count} audio chunks")
                await stt.send_audio(audio_chunk)
        except Exception as e:
            logger.error(f"STT send_audio error: {e}")
        finally:
            logger.info(f"STT: Audio stream ended after {audio_chunk_count} chunks, sending terminate")
            try:
                await stt.send_terminate()
            except Exception:
                pass

    send_task = asyncio.create_task(send_audio())

    try:
        async for event in stt.receive_events():
            yield event
    finally:
        with contextlib.suppress(asyncio.CancelledError):
            send_task.cancel()
            await send_task
        await stt.close()


async def agent_stream(
    event_stream: AsyncIterator[VoiceAgentEvent],
) -> AsyncIterator[VoiceAgentEvent]:
    """Transform stream: Voice Events -> Voice Events (with Agent Responses).

    Passes through all upstream events and adds agent_chunk events
    when processing STT transcripts.
    """
    from agent import agent_stream as _agent_stream

    async for event in _agent_stream(event_stream):
        yield event


async def tts_stream(
    event_stream: AsyncIterator[VoiceAgentEvent],
) -> AsyncIterator[VoiceAgentEvent]:
    """Transform stream: Voice Events -> Voice Events (with Audio).

    Merges two concurrent streams:
    1. process_upstream(): passes through events and sends text to Cartesia
    2. tts.receive_events(): yields audio chunks from Cartesia
    """
    tts = CartesiaTTS()

    async def process_upstream() -> AsyncIterator[VoiceAgentEvent]:
        """Process upstream events and send agent text to Cartesia."""
        async for event in event_stream:
            yield event
            if event.type == "agent_chunk":
                logger.info(f"TTS: Sending text to Cartesia: '{event.text[:60]}'")
                await tts.send_text(event.text)

    try:
        async for event in merge_async_iters(
            process_upstream(),
            tts.receive_events(),
        ):
            yield event
    finally:
        await tts.close()