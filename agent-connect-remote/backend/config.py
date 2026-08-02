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

GROQ_API_KEY = get_env("GROQ_API_KEY", "")
GROQ_MODEL = get_env("GROQ_MODEL", "qwen/qwen3.6-27b")
GROQ_MAX_TOKENS = int(get_env("GROQ_MAX_TOKENS", "4096"))
GROQ_MAX_RETRIES = int(get_env("GROQ_MAX_RETRIES", "3"))

LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "true").lower() == "true"
LANGSMITH_API_KEY = get_env("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT = get_env("LANGSMITH_PROJECT", "agent-connect-remote")

if LANGSMITH_TRACING and LANGSMITH_API_KEY:
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = LANGSMITH_API_KEY
    os.environ["LANGSMITH_PROJECT"] = LANGSMITH_PROJECT

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
    "chmod",
    "echo",
    "cat",
    "tee",
    "mkdir",
    "rm",
    "mv",
    "cp",
    "./",
    "bash",
    "sh",
    "python3",
    "python",
    "grep",
    "find",
    "head",
    "tail",
    "wc",
    "sort",
    "uniq",
    "sed",
    "awk",
    "touch",
]

DESTRUCTIVE_PATTERNS = [
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    "dd if=/dev/zero",
    ":(){:|:&};:",
    "chmod -R 777 /",
    "> /dev/sda",
]

DEFAULT_TASK_PROFILE = "diagnostic"
