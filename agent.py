from __future__ import annotations

import logging

import os

from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_core.utils.uuid import uuid7
from langgraph.checkpoint.memory import InMemorySaver
from typing import AsyncIterator

from events import AgentChunkEvent, VoiceAgentEvent

logger = logging.getLogger(__name__)


def add_to_order(item: str, quantity: int) -> str:
    """Add an item to the customer's sandwich order."""
    return f"Added {quantity} x {item} to the order."


def confirm_order(order_summary: str) -> str:
    """Confirm the final order with the customer."""
    return f"Order confirmed: {order_summary}. Sending to kitchen."


SYSTEM_PROMPT = """You are a helpful sandwich shop assistant.
Your goal is to take the user's order. Be concise and friendly.
Do NOT use emojis, special characters, or markdown.
Your responses will be read by a text-to-speech engine."""


def get_agent():
    """Create and return the LangChain agent with tools and memory."""
    model = os.getenv("AGENT_MODEL", "google_genai:gemini-3.6-flash")
    return create_agent(
        model=model,
        tools=[add_to_order, confirm_order],
        system_prompt=SYSTEM_PROMPT,
        checkpointer=InMemorySaver(),
    )


_agent_instance = None


def get_agent_lazy():
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = get_agent()
        logger.info("Agent: Initialized LLM agent")
    return _agent_instance


async def agent_stream(
    event_stream: AsyncIterator[VoiceAgentEvent],
) -> AsyncIterator[VoiceAgentEvent]:
    """Transform stream: Voice Events -> Voice Events (with Agent Responses).

    Passes through all upstream events and adds agent_chunk events
    when processing STT transcripts.
    """
    agent = get_agent_lazy()
    thread_id = str(uuid7())
    logger.info(f"Agent: New conversation thread={thread_id}")

    async for event in event_stream:
        yield event

        if event.type == "stt_output":
            transcript = event.transcript.strip()
            logger.info(f"Agent: Processing transcript: '{transcript[:100]}'")
            if not transcript:
                continue

            stream = await agent.astream_events(
                {"messages": [HumanMessage(content=transcript)]},
                {"configurable": {"thread_id": thread_id}},
                version="v3",
            )

            token_count = 0
            async for message in stream.messages:
                async for token in message.text:
                    token_count += 1
                    yield AgentChunkEvent.create(token)
            logger.info(f"Agent: Response complete ({token_count} tokens)")