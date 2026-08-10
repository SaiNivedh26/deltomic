-- Agent traces: LangGraph/LangSmith trace data per session
CREATE TABLE IF NOT EXISTS agent_traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES session_history(id),
    tenant_id UUID REFERENCES tenants(id),
    agent_id STRING NOT NULL,
    trace_type STRING NOT NULL DEFAULT 'langgraph',
    trace_id STRING,
    parent_trace_id STRING,
    span_name STRING NOT NULL,
    span_kind STRING DEFAULT 'tool',
    input_data JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    status STRING DEFAULT 'ok',
    start_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    end_time TIMESTAMPTZ,
    duration_ms INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Session embeddings: CockroachDB distributed vector indexing for semantic memory
CREATE TABLE IF NOT EXISTS session_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES session_history(id),
    tenant_id UUID REFERENCES tenants(id),
    embedding VECTOR(1024) NOT NULL,
    content_type STRING NOT NULL DEFAULT 'summary',
    content_text STRING NOT NULL,
    issue_category STRING,
    resolution_status STRING,
    similarity_score FLOAT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Agent learnings: accumulated insights that update agent reasoning
CREATE TABLE IF NOT EXISTS agent_learnings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    issue_category STRING NOT NULL,
    learning_text STRING NOT NULL,
    confidence FLOAT DEFAULT 0.5,
    source_session_ids JSONB DEFAULT '[]',
    times_applied INT DEFAULT 0,
    is_active BOOL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Batch insights: collected from multiple sessions for dashboard analytics
CREATE TABLE IF NOT EXISTS batch_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    insight_type STRING NOT NULL,
    title STRING NOT NULL,
    description STRING,
    data JSONB DEFAULT '{}',
    tenant_id UUID REFERENCES tenants(id),
    source_session_count INT DEFAULT 0,
    is_applied BOOL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ
);

-- Real-time agent events buffer for dashboard SSE
CREATE TABLE IF NOT EXISTS agent_events_buffer (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id STRING NOT NULL,
    session_id UUID,
    event_type STRING NOT NULL,
    event_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for agent_traces
CREATE INDEX IF NOT EXISTS idx_traces_session ON agent_traces(session_id);
CREATE INDEX IF NOT EXISTS idx_traces_agent ON agent_traces(agent_id);
CREATE INDEX IF NOT EXISTS idx_traces_tenant ON agent_traces(tenant_id);
CREATE INDEX IF NOT EXISTS idx_traces_created ON agent_traces(created_at);
CREATE INDEX IF NOT EXISTS idx_traces_type ON agent_traces(trace_type);

-- Indexes for session_embeddings (vector index for distributed vector indexing)
CREATE INDEX IF NOT EXISTS idx_embeddings_session ON session_embeddings(session_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_tenant ON session_embeddings(tenant_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_category ON session_embeddings(issue_category);
CREATE INDEX IF NOT EXISTS idx_embeddings_content_type ON session_embeddings(content_type);

-- Indexes for agent_learnings
CREATE INDEX IF NOT EXISTS idx_learnings_tenant ON agent_learnings(tenant_id);
CREATE INDEX IF NOT EXISTS idx_learnings_category ON agent_learnings(issue_category);
CREATE INDEX IF NOT EXISTS idx_learnings_active ON agent_learnings(is_active);

-- Indexes for batch_insights
CREATE INDEX IF NOT EXISTS idx_batch_insights_type ON batch_insights(insight_type);
CREATE INDEX IF NOT EXISTS idx_batch_insights_tenant ON batch_insights(tenant_id);
CREATE INDEX IF NOT EXISTS idx_batch_insights_created ON batch_insights(created_at);

-- Indexes for agent_events_buffer
CREATE INDEX IF NOT EXISTS idx_events_buffer_agent ON agent_events_buffer(agent_id);
CREATE INDEX IF NOT EXISTS idx_events_buffer_created ON agent_events_buffer(created_at);
