from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class VoiceAgentEvent:
    """Base event type for the voice agent pipeline."""

    type: str

    @classmethod
    def create(cls, **kwargs: Any) -> "VoiceAgentEvent":
        return cls(**kwargs)


@dataclass
class STTChunkEvent(VoiceAgentEvent):
    """Partial transcript from the STT provider."""

    transcript: str = ""

    def __init__(self, transcript: str = ""):
        super().__init__(type="stt_chunk")
        self.transcript = transcript

    @classmethod
    def create(cls, transcript: str = "") -> "STTChunkEvent":
        return cls(transcript=transcript)


@dataclass
class STTOutputEvent(VoiceAgentEvent):
    """Final formatted transcript from the STT provider."""

    transcript: str = ""

    def __init__(self, transcript: str = ""):
        super().__init__(type="stt_output")
        self.transcript = transcript

    @classmethod
    def create(cls, transcript: str = "") -> "STTOutputEvent":
        return cls(transcript=transcript)


@dataclass
class AgentChunkEvent(VoiceAgentEvent):
    """A chunk of agent-generated text."""

    text: str = ""

    def __init__(self, text: str = ""):
        super().__init__(type="agent_chunk")
        self.text = text

    @classmethod
    def create(cls, text: str = "") -> "AgentChunkEvent":
        return cls(text=text)


@dataclass
class TTSChunkEvent(VoiceAgentEvent):
    """A chunk of synthesized audio from the TTS provider."""

    audio: bytes = b""

    def __init__(self, audio: bytes = b""):
        super().__init__(type="tts_chunk")
        self.audio = audio

    @classmethod
    def create(cls, audio: bytes = b"") -> "TTSChunkEvent":
        return cls(audio=audio)