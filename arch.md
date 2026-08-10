# Agent Connect Remote — Architecture

## Overview

A dual-agent remote support system that lets AI agents join Google Meet calls via Recall bots, converse with customers using Gemini Live (voice), and execute commands on customer machines via AWS SSM. Built with FastAPI, CockroachDB, LangChain (Groq), and LangSmith observability.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL SERVICES                             │
├─────────────────────────────────────────────────────────────────────┤
│  Pingram (email)  │  Recall.ai (Meet bots)  │  Composio (Calendar)  │
│  AWS SSM          │  Google Gemini Live     │  Groq (LLM)           │
│  LangSmith        │  CockroachDB (Postgres) │                       │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (main.py)                         │
│  Port 8000  │  /chat  /task  /execute  /webhook  /admin  /onboarding │
└─────────────────────────────────────────────────────────────────────┘
          │                              │
          ▼                              ▼
┌─────────────────────┐      ┌──────────────────────────┐
│  Conversation Agent │      │   Execution Agent (Groq) │
│  Gemini Live Voice  │      │   qwen/qwen3.6-27b       │
│  (in Meet call)     │      │   LangChain + tools      │
└─────────────────────┘      └──────────────────────────┘
          │                              │
          └──────────┬───────────────────┘
                     ▼
         ┌───────────────────────
         │  Access Control (SSM) │
         │  JIT grants + audit   │
         └───────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  Customer Machine     │
         │  (AWS SSM managed)    │
         └───────────────────────┘
```

---

## Agent Architecture (Dual-Agent Model)

### Agent 1: Conversation Agent (Gemini Live)
- **Location**: Runs in the browser inside a Google Meet call (via Recall bot)
- **Model**: `gemini-3.1-flash-live-preview` (real-time multimodal)
- **Role**: Voice conversation with the customer
- **Tools exposed to Gemini**:
  - `delegate_task` — sends a task description to the Groq execution agent via `/task/stream`
  - `revoke_access` — ends the support session
- **Streaming**: Receives audio + transcription from Gemini Live WebSocket, sends tool calls to backend

### Agent 2: Execution Agent (Groq / Qwen)
- **Location**: Server-side, invoked via FastAPI endpoints
- **Model**: `qwen/qwen3.6-27b` via ChatGroq (LangChain)
- **Role**: Plans and executes commands on customer machines
- **Tools**:
  - `run_command(command)` — execute allowed command via SSM, streams events
  - `approve_and_run_destructive(command)` — execute destructive command after approval
  - `list_available_commands()` — list commands in current allowlist
  - `get_previous_sessions()` — fetch tenant's past session context
  - `revoke_access(reason)` — end the session
- **Checkpointer**: LangGraph `InMemorySaver` for thread state

### Task Resolution Flow

```
Customer speaks in Meet
  → Gemini Live transcribes
    → Gemini decides to delegate_task
      → POST /task/stream (creates task_id, starts Groq agent in background)
        → Groq agent plans + executes commands
          → SSE events stream to /task/{task_id}/events
            → Frontend renders command blocks in real-time
        → Groq agent finishes, emits task_complete
          → Session summary saved to DB
        → Gemini receives result, speaks to customer
```

---

## Data Flow

### 1. Onboarding (Email → Machine Registration)

```
Customer emails support
  → Pingram webhook → POST /webhook/pingram
    → parse email, extract from_address, bodyText
    → create SSM hybrid activation (AWS)
    → send onboarding email with setup script
    → start background poll (5s intervals, 10min timeout)
      → poll customer_machines table for registered node
      → when found: verify SSM ping status = Online
        → request + approve access grant (120min)
        → create Google Calendar event with Meet link (Composio)
        → create Recall bot (joins Meet, loads agent.html)
        → send meet link email to customer + organizer
        → store session in _active_sessions dict
```

### 2. Support Session

```
Recall bot joins Meet → loads agent.html in browser
  → agent.html connects to Gemini Live WebSocket
    → on setupComplete: sends greeting, starts audio loop
    → customer speaks → Gemini transcribes → addConversation("user")
    → Gemini responds → audio playback + addConversation("assistant")
    → Gemini calls delegate_task → handleToolCall()
      → POST /task/stream → get task_id
      → EventSource /task/{task_id}/events
        → command_start → addCommandBlock("running")
        → command_complete → updateCommandBlock(output, status)
        → approval_required → showApprovalCard()
        → task_complete → close stream, show summary
    → Gemini calls revoke_access → POST /sessions/{agent_id}/end
```

### 3. Command Execution Pipeline

```
Groq agent calls run_command("ls -la")
  → _push_event(command_start)
  → access_control.execute_command()
    → check grant: status = approved/active, not expired
    → check command in allowlist (exact or prefix match)
    → update grant status to 'active'
    → SSM send_command (AWS-RunShellScript, 30s timeout)
    → poll every 5s (12 attempts = 60s max)
    → insert audit record in support_command_audit
    → return {status, stdout, stderr}
  → _push_event(command_complete)
  → log_tool_call() → tool_call_logs table
  → return output to Groq agent
```

---

## Database Schema (CockroachDB)

### Migration 001: Core Access Control

| Table | Purpose |
|---|---|
| `customer_machines` | Registered SSM managed instances (customer_id, managed_node_id, is_active) |
| `support_access_grants` | JIT access grants (status: pending→approved→active→revoked, allowed_commands JSONB, expires_at) |
| `support_command_audit` | Full audit of every command executed (grant_id, command, stdout, stderr, exit_code, command_id) |

### Migration 002: Tenant Observability

| Table | Purpose |
|---|---|
| `tenants` | Customer identity (email UNIQUE, company_name, customer_id derived from email hash) |
| `session_history` | Per-session summary (tenant_id FK, task_description, summary, issue_category, resolution_status, commands_executed JSONB) |
| `tool_call_logs` | Granular tool call tracking (session_id, tool_name, tool_args JSONB, tool_result, duration_ms, model_used, trace_id) |
| `task_profiles` | Dynamic tool configs (name, allowed_tools, restricted_tools, requires_escalation, default_commands, escalation_commands) |

### Seeded Task Profiles

| Profile | Default Commands | Escalation Commands |
|---|---|---|
| `diagnostic` | Read-only (ls, df, whoami, grep, find, head, tail, wc) | rm, chmod, mv, cp, bash, sh |
| `remediation` | Diagnostic + write (cat, sed, awk, touch, mkdir, cp, mv, chmod, python3, bash) | rm -rf, mkfs, dd if= |
| `full_autonomous` | All commands | mkfs, dd if=, rm -rf / |

---

## Backend Modules

```
agent-connect-remote/
├── main.py              # FastAPI app, all endpoints
├── backend/
│   ├── config.py        # Env vars, allowed commands, destructive patterns
│   ├── db.py            # CockroachDB connection, migration runner
│   ├── access_control.py # SSM command execution, grant lifecycle, audit logging
│   ├── onboarding.py    # SSM hybrid activation, instance verification
│   ├── pingram_handler.py # Email webhook, polling, Meet link creation, Recall bot
│   ├── tenant_service.py # Tenant CRUD, session history, tool call logs, weekly insights
│   ├── tool_config.py   # Task profile resolution, dynamic allowlists, destructive detection
│   └── worker_agent.py  # Groq execution agent, tools, streaming, approval flow
├── migrations/
│   ├── 001_initial_schema.sql
│   └── 002_tenant_observability.sql
└── requirements.txt
```

---

## API Endpoints

### Core
| Method | Path | Purpose |
|---|---|---|
| POST | `/chat` | Gemini → Groq agent chat (non-streaming) |
| POST | `/task` | Execute task via Groq agent (non-streaming) |
| POST | `/task/stream` | Start streaming task, returns task_id |
| GET | `/task/{task_id}/events` | SSE stream of command events |
| POST | `/task/approve` | Approve/deny destructive command |
| POST | `/execute` | Direct command execution (no LLM) |

### Onboarding
| Method | Path | Purpose |
|---|---|---|
| POST | `/onboarding/create-activation` | Create SSM hybrid activation |
| POST | `/onboarding/register` | Register machine in DB |
| POST | `/onboarding/verify/{customer_id}` | Verify SSM instance status |

### Access Control
| Method | Path | Purpose |
|---|---|---|
| POST | `/access/request` | Request JIT access grant |
| POST | `/access/approve` | Approve pending grant |
| POST | `/access/revoke` | Revoke active grant |
| GET | `/access/status/{grant_id}` | Get grant status |

### Sessions
| Method | Path | Purpose |
|---|---|---|
| GET | `/sessions` | List active sessions |
| GET | `/sessions/{agent_id}` | Get session details |
| POST | `/sessions/{agent_id}/end` | End session, revoke grant |

### Webhooks
| Method | Path | Purpose |
|---|---|---|
| POST | `/webhook/pingram` | Handle inbound email from Pingram |
| POST | `/webhook/test` | Test webhook handler |
| POST | `/webhook/test-pingram` | Debug webhook payload |

### Admin Dashboard
| Method | Path | Purpose |
|---|---|---|
| GET | `/admin/dashboard.html` | Serve admin dashboard UI |
| GET | `/admin/tenants` | List all tenants |
| GET | `/admin/tenants/{id}` | Tenant detail + sessions |
| GET | `/admin/tenants/email/{email}` | Lookup tenant by email |
| GET | `/admin/sessions/{tenant_id}/history` | Session history for tenant |
| GET | `/admin/tool-logs` | Tool call logs (filter by session/tenant) |
| GET | `/admin/insights` | Weekly analytics (categories, top tools, top tenants) |
| GET | `/admin/active-agents` | Currently active agent sessions |
| GET | `/admin/task-profiles` | List task profiles |
| POST | `/admin/task-profiles` | Create new task profile |
| GET | `/admin/tenant-context/{email}` | Get previous session context for prompt injection |

### Gemini
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/token` | Generate Gemini Live auth token (30min expiry) |
| GET | `/agent.html` | Serve agent page to Recall bot |

---

## Frontend

### `static/agent.html` — Split UI (loaded by Recall bot in Meet)

```
┌─────────────────────────────────────────────────────────────
│  DELTOMIC                                                   │
──────────────────────────┬──────────────────────────────────┤
│  CONVERSATION (50%)      │  COMMAND EXECUTION (50%)         │
│                          │                                  │
│  [Status: Connected]     │  [Live command feed]             │
│  [Chips: Gemini | Groq]  │                                  │
│  [Context banner]        │  ┌─ cmd: ls -la ─────────────┐ │
│                          │  │ ● running                   │ │
│  User: "my server is     │  │ output: total 48...         │ │
│  slow today"             │  └─────────────────────────────┘ │
│                          │                                  │
│  Agent: "Let me check    │  ┌─ cmd: df -h ──────────────┐ │
│  what's going on..."     │  │ ● success                   │ │
│                          │  │ output: /dev/sda1 50G 20G   │ │
│  [Working on: check      │  └─────────────────────────────┘ │
│   disk usage]            │                                  │
│                          │  [Approval card (if needed)]     │
──────────────────────────┴──────────────────────────────────┘
```

- **Left pane**: Conversation transcript (user/assistant/system messages)
- **Right pane**: Real-time command execution blocks (running → success/failed)
- **Streaming**: SSE events update command blocks in real-time
- **Approval cards**: Shown when Groq agent detects destructive command

### `static/admin.html` — Admin Dashboard

Tabs: Overview, Active Agents, Tenants, Tool Logs, Insights, Task Profiles
- Auto-refreshes every 15 seconds
- Issue category bar chart
- Clickable tenant rows with session history
- Filterable tool call logs

---

## Key Design Decisions

### 1. Dual-Agent Separation
- **Gemini Live** handles only conversation (voice I/O, transcription, tool calling)
- **Groq/Qwen** handles only execution (planning, command selection, output analysis)
- Prevents Gemini from directly executing commands; all execution goes through the controlled Groq agent

### 2. JIT Access Control
- Every command execution requires a valid, non-expired access grant
- Commands checked against per-grant allowlist (exact + prefix matching)
- Destructive commands require explicit customer approval via `approve_and_run_destructive`
- All commands audited in `support_command_audit` with stdout/stderr capture

### 3. Dynamic Task Profiles
- Task type auto-resolved from keywords (diagnostic/remediation/full_autonomous)
- Each profile defines different command allowlists and escalation rules
- Profiles stored in DB, configurable via admin dashboard

### 4. Tenant Memory
- Each customer identified by email → tenant record
- Previous 5 sessions injected into Groq agent context via `get_previous_sessions()` tool
- Enables continuity: "last time we did this, do you want me to try this"

### 5. Streaming Architecture
- Groq agent runs in background `asyncio.create_task()`
- Command events pushed to per-task `asyncio.Queue`
- Frontend consumes via SSE (`EventSource`)
- Heartbeat every 300s to keep connection alive

### 6. Observability
- Every tool call logged to `tool_call_logs` with duration, status, model_used
- LangSmith tracing enabled via env vars (LANGSMITH_TRACING, LANGSMITH_API_KEY)
- Weekly insights: issue categories, top tools, top tenants, session counts

---

## Environment Variables

```
COCKROACH_CONNECTION_STRING=postgresql://...
AWS_ACCESS_KEY=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
GEMINI_API_KEY=...
GROQ_API_KEY=...
GROQ_MODEL=qwen/qwen3.6-27b
GROQ_MAX_TOKENS=4096
GROQ_MAX_RETRIES=3
PINGRAM_API_KEY=...
COMPOSIO_API_KEY=...
RECALL_API_KEY=...
BACKEND_URL=https://...
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=agent-connect-remote
```

---

## External Service Integrations

| Service | Purpose | SDK/Library |
|---|---|---|
| AWS SSM | Remote command execution on customer machines | boto3 |
| Google Gemini Live | Real-time voice conversation in Meet | google-genai |
| Recall.ai | Bot that joins Meet calls, renders agent.html | HTTP API |
| Pingram | Email inbound/outbound webhooks | pingram-python |
| Composio | Google Calendar event creation (Meet links) | composio |
| CockroachDB | Persistent storage (Postgres-compatible) | psycopg2 |
| Groq | LLM for execution agent planning | langchain-groq |
| LangSmith | LLM observability/tracing | langsmith |
| CockroachDB MCP | Managed agent DB operations | MCP Protocol |
| CockroachDB Vector | Distributed vector indexing for semantic memory | pgvector |

---

## Enterprise Dashboard Architecture

### Overview

A separate real-time enterprise dashboard (`/dashboard`) providing graphical visualization of agent operations, trace exploration, session insights, and agent learning accumulation. Built with a clean, minimal dark UI using vanilla HTML/CSS/JS.

### Dashboard Pages

| Page | Purpose |
|---|---|
| Overview | KPI cards, top issues chart, active agent map, recent activity |
| Live Agents | Real-time visualization of deployed agents with customer context |
| Trace Explorer | LangGraph/LangSmith trace timeline per session, recent traces |
| Sessions | Full session history with click-to-expand trace summary |
| Insights | Issue frequency, resolution rates, batch-collected insights |
| Agent Learnings | Accumulated knowledge corpus that informs agent reasoning |
| Log Stream | Real-time SSE log ingestion from all spawned sub-agents |

### Real-time Architecture

```
Sub-agents (worker_agent.py)
  → broadcast_agent_event() → agent_events_buffer table
  → SSE endpoint /dashboard/api/events/stream
  → Dashboard EventSource → live log stream + agent status updates
```

- Events are persisted to `agent_events_buffer` for durability
- SSE endpoint polls every 3s for new events
- Dashboard auto-refreshes all data every 10s
- Log stream uses `EventSource` for push-based updates

---

## Database Schema Extensions (Migration 003)

| Table | Purpose |
|---|---|
| `agent_traces` | LangGraph/LangSmith trace spans per session (span_name, span_kind, input/output JSONB, duration) |
| `session_embeddings` | CockroachDB distributed vector index — session summaries as VECTOR(1536) for semantic search |
| `agent_learnings` | Accumulated insights from past sessions (issue_category, learning_text, confidence, times_applied) |
| `batch_insights` | Collected analytics from multiple sessions (issue_frequency, tool_usage, resolution_rates) |
| `agent_events_buffer` | Real-time event buffer for dashboard SSE streaming |

### CockroachDB Managed MCP Server Integration

The MCP server configuration provides agents a clean integration path for DB operations:

```json
{
  "mcpServers": {
    "cockroachdb-cloud": {
      "type": "http",
      "url": "https://cockroachlabs.cloud/mcp",
      "headers": {
        "mcp-cluster-id": "6db24597-793b-4338-96df-5ea6acfaa469"
      }
    }
  }
}
```

Used for: `create_session`, `store_message`, `store_tool_call`, `store_command_output`, `fetch_tenant_context`, `fetch_previous_sessions`.

### CockroachDB Distributed Vector Indexing

Session summaries are embedded (Google `embedding-001`, 1536 dims) and stored in `session_embeddings` using CockroachDB's native `VECTOR` type. This enables:

- **Per-tenant semantic search**: "find similar past issues for this customer"
- **Cross-tenant pattern detection**: "common issues this week"
- **Recurring issue identification**: "last time we did X for this tenant"
- **Similarity-based retrieval**: cosine distance via `<=>` operator

---

## Session Lifecycle & Cleanup

### Full Session Teardown Flow

```
Meet session ends (Recall bot leaves / Gemini calls revoke_access)
  → pingram_handler.end_session()
    → session_lifecycle.cleanup_meet_session()
      → revoke access grant
      → broadcast cleanup events to dashboard
  → worker_agent finalize_session()
    → db_end_session() — update session_history with summary, category, resolution
    → store_conversation_turn() — persist all conversation traces
    → store_tool_execution_trace() — persist all tool call traces
    → store_session_embedding() — embed summary for vector search
    → broadcast_agent_event(session_finalized) — notify dashboard
```

This ensures:
1. All logs written to CockroachDB before session closes
2. LangSmith traces captured in `agent_traces` table
3. Session embedding stored for semantic memory
4. Dashboard notified in real-time
5. Access grants properly revoked
6. Zero data loss with CockroachDB's distributed consistency

---

## Insights & Agent Learning Pipeline

### Batch Insight Collection

Triggered manually via dashboard or scheduled:

```
collect_weekly_issue_insights()
  → Query session_history for last 7 days
  → Group by issue_category → create batch_insights (issue_frequency)
  → Aggregate tool_call_logs → create batch_insights (tool_usage)
  → Aggregate resolution_status → create batch_insights (resolution_rates)
```

### Agent Learning Generation

```
generate_learnings_from_sessions()
  → Analyze resolution rates per issue_category
  → High resolution (>=80%) → "standard approach works" learning (high confidence)
  → Low resolution (<50%) → "escalate faster" learning (lower confidence)
  → Store in agent_learnings with confidence score
```

### Learning Application

When a new session starts with a known issue category:
```
get_relevant_learnings(issue_category, tenant_id)
  → Returns sorted by confidence DESC, times_applied DESC
  → Agent can inject learnings into system prompt for better reasoning
```

### Dashboard Visualization

The "Agent Learnings" page shows:
- All active learnings with category, text, confidence %, times applied
- "Generate from Sessions" button to trigger batch learning extraction
- Direct correlation with CockroachDB data (source sessions, categories)

---

## Backend Module Extensions

```
agent-connect-remote/
├── main.py                    # + Dashboard API endpoints (15+ new routes)
├── backend/
│   ├── vector_store.py        # CockroachDB distributed vector indexing
│   ├── trace_service.py       # LangGraph/LangSmith trace ingestion & retrieval
│   ├── insights_engine.py     # Batch insight collection & agent learning generation
│   ├── session_lifecycle.py   # Session cleanup, event broadcasting, finalize pipeline
│   ├── config.py              # (unchanged)
│   ├── db.py                  # (unchanged)
│   ├── access_control.py      # (unchanged)
│   ├── worker_agent.py        # + trace capture, finalize_session integration
│   ├── pingram_handler.py     # + session_lifecycle cleanup on meet end
│   ├── tenant_service.py      # (unchanged)
│   ├── tool_config.py         # (unchanged)
│   └── onboarding.py          # (unchanged)
├── migrations/
│   ├── 001_initial_schema.sql
│   ├── 002_tenant_observability.sql
│   └── 003_dashboard_observability.sql   # NEW: traces, vectors, learnings, events
└── static/
    ├── dashboard.html         # NEW: Enterprise real-time dashboard
    ├── admin.html             # (existing admin dashboard)
    └── agent.html             # (existing agent UI)
```

---

## Dashboard API Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/dashboard` | Serve enterprise dashboard UI |
| GET | `/dashboard/api/agents/live` | Live agent status with tenant context |
| GET | `/dashboard/api/analytics` | KPI stats (sessions, tools, tenants, embeddings) |
| GET | `/dashboard/api/traces/session/{id}` | Full trace timeline for a session |
| GET | `/dashboard/api/traces/agent/{id}` | All traces for an agent |
| GET | `/dashboard/api/traces/recent` | Recent traces across all agents |
| GET | `/dashboard/api/traces/summary/{id}` | Condensed trace summary (conversation + tools + LLM) |
| GET | `/dashboard/api/insights/top-issues` | Top issues via vector similarity |
| GET | `/dashboard/api/insights/batch` | Batch-collected insights |
| POST | `/dashboard/api/insights/collect` | Trigger batch insight collection |
| GET | `/dashboard/api/learnings` | Agent learning corpus |
| POST | `/dashboard/api/learnings/generate` | Generate learnings from session data |
| GET | `/dashboard/api/events/stream` | SSE stream for real-time log ingestion |
| GET | `/dashboard/api/sessions/history` | Full session history with tenant info |
| GET | `/dashboard/api/sessions/{id}/embedding-search` | Find similar sessions via vector search |
| GET | `/dashboard/api/vector/stats` | Vector store statistics |
