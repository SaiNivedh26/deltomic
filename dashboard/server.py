from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "agent-connect-remote"))

import asyncio
import json
import logging
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="DELTOMIC Enterprise Dashboard", version="1.0.0")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@contextmanager
def get_cursor():
    from backend.config import COCKROACH_CONNECTION_STRING
    conn = psycopg2.connect(COCKROACH_CONNECTION_STRING)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@app.get("/")
async def root():
    return {"status": "running", "service": "enterprise-dashboard", "version": "1.0.0"}


@app.get("/dashboard")
async def serve_dashboard():
    path = STATIC_DIR / "dashboard.html"
    if not path.exists():
        raise HTTPException(status_code=404, detail="dashboard.html not found")
    return FileResponse(path)


@app.get("/dashboard/api/agents/live")
async def live_agents():
    with get_cursor() as cur:
        # Get active sessions from session_history
        cur.execute("""
            SELECT sh.id, sh.tenant_id, sh.agent_id, sh.task_description, sh.started_at, sh.resolution_status,
                   sh.ended_at, sh.summary, sh.issue_category,
                   t.email, t.company_name, t.customer_id
            FROM session_history sh
            LEFT JOIN tenants t ON t.id = sh.tenant_id
            WHERE sh.ended_at IS NULL
            ORDER BY sh.started_at DESC
            LIMIT 50
        """)
        db_agents = [dict(r) for r in cur.fetchall()]
        
        # Get recent dispatch events from agent_events_buffer (last 30 minutes)
        cur.execute("""
            SELECT event_data, created_at
            FROM agent_events_buffer
            WHERE event_data->>'type' = 'agent_dispatched'
              AND created_at > NOW() - INTERVAL '30 minutes'
            ORDER BY created_at DESC
        """)
        events = cur.fetchall()
        
        # Combine: show event-based agents if not already in session_history
        event_agents = []
        db_agent_ids = {a['agent_id'] for a in db_agents}
        
        for event in events:
            event_data = event['event_data']
            if isinstance(event_data, str):
                event_data = json.loads(event_data)
            
            agent_id = event_data.get('agent_id')
            if agent_id and agent_id not in db_agent_ids:
                event_agents.append({
                    'id': None,
                    'agent_id': agent_id,
                    'customer_id': event_data.get('customer_id'),
                    'email': event_data.get('email'),
                    'company_name': None,
                    'task_description': event_data.get('task_context', ''),
                    'started_at': event['created_at'],
                    'ended_at': None,
                    'resolution_status': 'active',
                    'meet_url': event_data.get('meet_url'),
                    'source': 'event'
                })
        
        # Combine both sources
        all_agents = event_agents + db_agents
        
    return {"agents": all_agents, "count": len(all_agents)}


@app.get("/dashboard/api/analytics")
async def analytics():
    from backend.insights_engine import get_dashboard_analytics
    return get_dashboard_analytics()


@app.get("/dashboard/api/traces/session/{session_id}")
async def session_traces(session_id: str):
    from backend.trace_service import get_trace_timeline
    return get_trace_timeline(session_id)


@app.get("/dashboard/api/traces/agent/{agent_id}")
async def agent_traces(agent_id: str, limit: int = 100):
    from backend.trace_service import get_agent_traces
    return {"traces": get_agent_traces(agent_id, limit)}


@app.get("/dashboard/api/traces/recent")
async def recent_traces(limit: int = 50):
    from backend.trace_service import get_recent_traces
    return {"traces": get_recent_traces(limit)}


@app.get("/dashboard/api/traces/summary/{session_id}")
async def trace_summary(session_id: str):
    from backend.trace_service import build_trace_summary
    return build_trace_summary(session_id)


@app.get("/dashboard/api/insights/top-issues")
async def top_issues():
    from backend.vector_store import get_top_issues_this_week
    return {"issues": get_top_issues_this_week()}


@app.get("/dashboard/api/insights/batch")
async def batch_insights(insight_type: str | None = None, limit: int = 50):
    from backend.insights_engine import get_batch_insights
    return {"insights": get_batch_insights(insight_type, limit)}


@app.post("/dashboard/api/insights/collect")
async def collect_insights():
    from backend.insights_engine import collect_weekly_issue_insights
    insights = collect_weekly_issue_insights()
    return {"status": "collected", "insights": insights}


@app.get("/dashboard/api/learnings")
async def learnings(issue_category: str | None = None, limit: int = 50):
    from backend.insights_engine import get_agent_learnings
    return {"learnings": get_agent_learnings(issue_category, limit)}


@app.post("/dashboard/api/learnings/generate")
async def generate_learnings():
    from backend.insights_engine import generate_learnings_from_sessions
    learnings = generate_learnings_from_sessions()
    return {"status": "generated", "learnings": learnings}


@app.get("/dashboard/api/sessions/{session_id}/embedding-search")
async def embedding_search(session_id: str, limit: int = 5):
    with get_cursor() as cur:
        cur.execute(
            "SELECT content_text, issue_category FROM session_embeddings WHERE session_id = %s LIMIT 1",
            (session_id,),
        )
        row = cur.fetchone()
        if not row:
            return {"similar": [], "query": ""}
        query_text = row["content_text"]
        from backend.vector_store import find_similar_sessions
        similar = find_similar_sessions(query_text, limit=limit)
        return {"similar": similar, "query": query_text}


@app.get("/dashboard/api/events/stream")
async def events_stream():
    async def generate():
        while True:
            try:
                with get_cursor() as cur:
                    cur.execute("""
                        SELECT event_data, created_at
                        FROM agent_events_buffer
                        ORDER BY created_at DESC
                        LIMIT 20
                    """)
                    events = cur.fetchall()
                for event in events:
                    event_data = event.get("event_data", {})
                    if isinstance(event_data, str):
                        event_data = json.loads(event_data)
                    yield f"data: {json.dumps(event_data)}\n\n"
            except Exception as e:
                logger.error(f"SSE error: {e}")
            await asyncio.sleep(3)

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/dashboard/api/sessions/history")
async def session_history(limit: int = 50):
    with get_cursor() as cur:
        cur.execute("""
            SELECT sh.*, t.email, t.company_name
            FROM session_history sh
            LEFT JOIN tenants t ON t.id = sh.tenant_id
            ORDER BY sh.started_at DESC
            LIMIT %s
        """, (limit,))
        return {"sessions": [dict(r) for r in cur.fetchall()]}


@app.get("/dashboard/api/vector/stats")
async def vector_stats():
    from backend.vector_store import get_embedding_stats
    return get_embedding_stats()


@app.get("/dashboard/api/self-healing/history")
async def self_healing_history(limit: int = 50):
    from backend.self_healing import get_self_healing_history
    return {"history": get_self_healing_history(limit)}


@app.get("/dashboard/api/self-healing/learnings")
async def self_healing_learnings(limit: int = 50):
    from backend.self_healing import get_error_learnings
    return {"learnings": get_error_learnings(limit)}


@app.post("/dashboard/api/self-healing/analyze/{session_id}")
async def analyze_session(session_id: str):
    from backend.self_healing import run_self_healing_loop
    
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT * FROM tool_call_logs
            WHERE session_id = %s
            ORDER BY created_at ASC
            """,
            (session_id,),
        )
        tool_logs = [dict(r) for r in cur.fetchall()]
    
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT task_description, issue_category
            FROM session_history
            WHERE id = %s
            """,
            (session_id,),
        )
        session = cur.fetchone()
    
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found")
    
    result = run_self_healing_loop(
        session_id=session_id,
        tool_logs=tool_logs,
        session_context=dict(session),
    )
    
    return result


@app.get("/dashboard/api/pro-insights/patterns")
async def pattern_analysis():
    from backend.pattern_analyzer import get_pattern_analysis
    return get_pattern_analysis()


@app.get("/dashboard/api/pro-insights/failures")
async def failure_analysis():
    from backend.failure_analyzer import get_failure_analysis
    return get_failure_analysis()


@app.get("/dashboard/api/pro-insights/usage")
async def usage_analysis():
    from backend.usage_analyzer import get_usage_analysis
    return get_usage_analysis()


@app.post("/dashboard/api/pro-insights/recommendations")
async def generate_recommendations():
    from backend.recommendation_engine import generate_recommendations
    return generate_recommendations()


@app.get("/dashboard/api/pro-insights/recommendations/{session_id}")
async def session_recommendation(session_id: str):
    from backend.recommendation_engine import generate_session_recommendation
    return generate_session_recommendation(session_id)


@app.get("/dashboard/api/pro-insights/metrics")
async def core_metrics(tenant_id: str | None = None, days: int = 30):
    from backend.metrics_engine import get_all_metrics
    return get_all_metrics(tenant_id, days)


@app.get("/dashboard/api/pro-insights/metrics/task-completion")
async def task_completion_metrics(tenant_id: str | None = None, days: int = 30):
    from backend.metrics_engine import get_task_completion_metrics
    return get_task_completion_metrics(tenant_id, days)


@app.get("/dashboard/api/pro-insights/metrics/error-rate")
async def error_rate_metrics(tenant_id: str | None = None, days: int = 30):
    from backend.metrics_engine import get_error_rate_metrics
    return get_error_rate_metrics(tenant_id, days)


@app.get("/dashboard/api/pro-insights/metrics/latency")
async def latency_metrics(tenant_id: str | None = None, days: int = 30):
    from backend.metrics_engine import get_p50_latency_metrics
    return get_p50_latency_metrics(tenant_id, days)


@app.get("/dashboard/api/pro-insights/metrics/satisfaction")
async def satisfaction_metrics(tenant_id: str | None = None, days: int = 30):
    from backend.metrics_engine import get_satisfaction_metrics
    return get_satisfaction_metrics(tenant_id, days)


@app.get("/dashboard/api/pro-insights/metrics/sentiment")
async def sentiment_metrics(tenant_id: str | None = None, days: int = 30):
    from backend.metrics_engine import get_sentiment_metrics
    return get_sentiment_metrics(tenant_id, days)


@app.get("/dashboard/api/pro-insights/feedback")
async def list_feedback(tenant_id: str | None = None, limit: int = 50):
    from backend.metrics_engine import get_user_feedback_list
    return {"feedback": get_user_feedback_list(tenant_id, limit)}


@app.post("/dashboard/api/pro-insights/feedback")
async def submit_feedback_endpoint(payload: dict):
    from backend.metrics_engine import submit_feedback
    session_id = payload.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    result = submit_feedback(
        session_id=session_id,
        satisfaction_score=payload.get("satisfaction_score"),
        sentiment=payload.get("sentiment"),
        sentiment_score=payload.get("sentiment_score"),
        task_completed=payload.get("task_completed"),
        feedback_text=payload.get("feedback_text"),
        feedback_tags=payload.get("feedback_tags"),
        source=payload.get("source", "explicit"),
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
