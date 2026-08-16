# Get Started

## Required Config Keys

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

| Key | Description | Required |
|-----|-------------|----------|
| `ASSEMBLYAI_API_KEY` | AssemblyAI Speech-to-Text API key ([get key](https://www.assemblyai.com/)) | Yes (voice pipeline) |
| `CARTESIA_API_KEY` | Cartesia Text-to-Speech API key ([get key](https://cartesia.ai/)) | Yes (voice pipeline) |
| `GOOGLE_API_KEY` | Google Gemini API key ([get key](https://aistudio.google.com/)) | Yes |
| `AGENT_MODEL` | LLM model for agent (e.g. `google_genai:gemini-3.6-flash`) | No (defaults to `google_genai:gemini-3.6-flash`) |
| `COMPOSIO_API_KEY` | Composio API key for Google Calendar integration | Yes (Meet server) |
| `RECALL_API_KEY` | Recall.ai API key for meeting bots | Yes (Meet server) |
| `COCKROACH_CONNECTION_STRING` | CockroachDB/Postgres connection string | Yes (agent-connect-remote) |
| `AWS_ACCESS_KEY` | AWS access key for SSM managed instances | Yes (agent-connect-remote) |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key | Yes (agent-connect-remote) |
| `BACKEND_URL` | Public ngrok URL (e.g. `https://your-url.ngrok-free.dev`) | Yes (webhooks) |
| `PINGRAM_API_KEY` | Pingram API key for email notifications ([get key](https://app.pingram.io/environments)) | Yes (agent-connect-remote) |
| `LANGSMITH_TRACING` | Enable LangSmith tracing (`true`/`false`) | No |
| `LANGSMITH_API_KEY` | LangSmith API key for observability | Optional |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key for tracing | Optional |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key | Optional |
| `LANGFUSE_BASE_URL` | Langfuse base URL | Optional |

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Run Commands


### Agent Connect Remote (main backend with Pingram webhook)

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Run from the `agent-connect-remote/` directory.

### Dashboard

```bash
python3 dashboard/server.py
```

Serves enterprise dashboard on port `8002`.

### Expose webhook via ngrok

```bash
ngrok http 8000
```

Update `BACKEND_URL` in `.env` with the ngrok URL. Set the Pingram webhook URL to:
```
https://<your-ngrok-url>.ngrok-free.dev/webhook/pingram
```

---

## Debugging scripts

### Gemini Live Token Server

```bash
python3 live_server.py
```

Serves ephemeral Gemini tokens on port `8001`.

### Meet Server (Google Meet + Recall bots)

```bash
python3 meet_server.py
```

Serves on port `8002` (configurable via `MEET_SERVER_PORT`).

### Voice Agent (FastAPI + WebSocket pipeline)

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

---

## Endpoint Reference

### Agent Connect Remote (`agent-connect-remote/main.py`)

#### Webhooks
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/webhook/pingram` | Receives Pingram inbound email events (`EMAIL_INBOUND`) and triggers agent session |
| `POST` | `/webhook/test-pingram` | Test endpoint that dumps raw Pingram webhook payload for debugging |
| `POST` | `/webhook/test` | Simplified test webhook that simulates an inbound email |
| `POST` | `/webhook/recall` | Receives Recall.ai meeting-ended notifications |

#### Gemini Token
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/token` | Generates ephemeral Gemini Live API token (30 min expiry) |

#### Task Execution
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/task` | Execute a task using Groq agent (blocking) |
| `POST` | `/task/stream` | Start a task and return `task_id` for SSE streaming |
| `GET` | `/task/{task_id}/events` | SSE stream of task execution events |
| `POST` | `/task/approve` | Approve or deny a destructive command |
| `POST` | `/execute` | Execute a single command via SSM |
| `POST` | `/chat` | Chat with the worker agent |

#### Onboarding
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/onboarding/create-activation` | Create SSM hybrid activation for a customer |
| `POST` | `/onboarding/register` | Register a customer machine (managed node) |
| `POST` | `/onboarding/verify/{customer_id}` | Verify managed instance is online |

#### Access Control
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/access/request` | Request JIT access grant for a customer |
| `POST` | `/access/approve` | Approve an access grant |
| `POST` | `/access/revoke` | Revoke an access grant |
| `GET` | `/access/status/{grant_id}` | Get grant status |

#### Sessions
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/sessions` | List active agent sessions |
| `GET` | `/sessions/{agent_id}` | Get specific session details |
| `POST` | `/sessions/{agent_id}/end` | End session (triggers cleanup + email confirmation) |

#### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/admin/tenants` | List all tenants |
| `GET` | `/admin/tenants/{tenant_id}` | Get tenant details + sessions |
| `GET` | `/admin/tenants/email/{email}` | Get tenant by email |
| `GET` | `/admin/sessions/{tenant_id}/history` | Session history for a tenant |
| `GET` | `/admin/tool-logs` | Tool call logs (filter by session/tenant) |
| `GET` | `/admin/insights` | Weekly insights |
| `GET` | `/admin/active-agents` | List active agents with details |
| `GET` | `/admin/task-profiles` | List task profiles |
| `POST` | `/admin/task-profiles` | Create a task profile |
| `GET` | `/admin/tenant-context/{email}` | Get tenant context summary |
| `POST` | `/admin/sessions/{agent_id}/force-end` | Force end session without cleanup |

#### Self-Healing
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/self-healing/history` | Self-healing analysis history |
| `GET` | `/self-healing/learnings` | Error-related learnings |
| `POST` | `/self-healing/analyze/{session_id}` | Trigger self-healing analysis for a session |

---

### Voice Agent (`app.py`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serves browser client (`static/index.html`) |
| `WS` | `/ws` | WebSocket endpoint: streams audio through STT -> Agent -> TTS pipeline |

---

### Gemini Live Server (`live_server.py`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/token` | Generate ephemeral Gemini Live token |
| `GET` | `/` | Serves `static/live.html` |
| `GET` | `/{path:.*}` | Serves static files |

---

### Meet Server (`meet_server.py`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/token` | Generate Gemini ephemeral token |
| `POST` | `/api/create-meeting` | Create Google Meet event via Composio |
| `POST` | `/api/join-meeting` | Create Recall bot to join meeting |
| `GET` | `/api/bot/{bot_id}` | Get Recall bot status |
| `POST` | `/api/leave-meeting/{bot_id}` | Remove bot from call |
| `GET` | `/` | Serves `static/meet.html` |

---

### Dashboard (`dashboard/server.py`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/dashboard` | Serve dashboard UI |
| `GET` | `/dashboard/api/agents/live` | Live active agents |
| `GET` | `/dashboard/api/analytics` | Dashboard analytics |
| `GET` | `/dashboard/api/traces/session/{session_id}` | Trace timeline for session |
| `GET` | `/dashboard/api/traces/agent/{agent_id}` | Traces for agent |
| `GET` | `/dashboard/api/traces/recent` | Recent traces |
| `GET` | `/dashboard/api/events/stream` | SSE event stream |
| `GET` | `/dashboard/api/sessions/history` | Session history |
| `GET` | `/dashboard/api/insights/top-issues` | Top issues this week |
| `GET` | `/dashboard/api/insights/batch` | Batch insights |
| `GET` | `/dashboard/api/learnings` | Agent learnings |
| `GET` | `/dashboard/api/pro-insights/metrics` | Core metrics |
| `POST` | `/dashboard/api/pro-insights/feedback` | Submit feedback |
| `POST` | `/dashboard/api/self-healing/analyze/{session_id}` | Self-healing analysis |

---

## Pingram Webhook Flow

1. Inbound email arrives at Pingram
2. Pingram sends `EMAIL_INBOUND` event to `POST /webhook/pingram`
3. Server extracts sender email, creates/finds tenant
4. SSM activation + managed instance verification
5. Agent session starts, executes tasks on customer machine
6. On meeting/session end, Recall webhook triggers summary email via Pingram
