from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


def get_env(key: str, default: str | None = None) -> str:
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"Missing required environment variable: {key}")
    return value


COCKROACH_CONNECTION_STRING = get_env("COCKROACH_CONNECTION_STRING")
AWS_ACCESS_KEY = get_env("AWS_ACCESS_KEY")
AWS_SECRET_ACCESS_KEY = get_env("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION = get_env("AWS_DEFAULT_REGION", "us-east-1")
AGENT_MODEL = get_env("AGENT_MODEL", "google_genai:gemini-3.6-flash")
PINGRAM_API_KEY = get_env("PINGRAM_API_KEY")
COMPOSIO_API_KEY = get_env("COMPOSIO_API_KEY")
BACKEND_URL = get_env("BACKEND_URL", "https://egregious-gale-unmusically.ngrok-free.dev")
LIVE_SERVER_URL = get_env("LIVE_SERVER_URL", "http://localhost:8001")

ALLOWED_COMMANDS = [
    "ls",
    "ls -la",
    "ls -l",
    "df -h",
    "whoami",
    "pwd",
    "uname -a",
    "uptime",
    "free -m",
    "cat /etc/os-release",
]
