# DELTOMIC Enterprise Dashboard

Isolated real-time dashboard for agent operations. Runs independently from the main pipeline.

## Run

```bash
cd /home/sai-nivedh-26/deltomic/dashboard
python3 server.py
# or: uvicorn server:app --reload --host 0.0.0.0 --port 8002
```

## Access

- Dashboard UI: http://localhost:8002/dashboard
- API root: http://localhost:8002/

## Architecture

```
dashboard/
├── server.py          # Standalone FastAPI app (port 8002)
├── static/
│   └── dashboard.html # Enterprise dashboard UI
└── README.md
```

The server imports shared backend modules from `../agent-connect-remote/backend/` via sys.path.

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/dashboard/api/agents/live` | Active agents from session_history |
| GET | `/dashboard/api/analytics` | KPI stats |
| GET | `/dashboard/api/traces/recent` | Recent LangGraph traces |
| GET | `/dashboard/api/traces/session/{id}` | Trace timeline per session |
| GET | `/dashboard/api/traces/summary/{id}` | Condensed trace summary |
| GET | `/dashboard/api/insights/top-issues` | Top issues via vector search |
| GET | `/dashboard/api/insights/batch` | Batch-collected insights |
| POST | `/dashboard/api/insights/collect` | Trigger batch collection |
| GET | `/dashboard/api/learnings` | Agent learning corpus |
| POST | `/dashboard/api/learnings/generate` | Generate learnings |
| GET | `/dashboard/api/events/stream` | SSE real-time log stream |
| GET | `/dashboard/api/sessions/history` | Session history |
| GET | `/dashboard/api/vector/stats` | Vector store stats |
