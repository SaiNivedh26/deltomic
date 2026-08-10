-- User feedback: explicit satisfaction ratings and sentiment per session
CREATE TABLE IF NOT EXISTS user_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES session_history(id),
    tenant_id UUID REFERENCES tenants(id),
    satisfaction_score FLOAT CHECK (satisfaction_score >= 0 AND satisfaction_score <= 1),
    sentiment STRING CHECK (sentiment IN ('positive', 'neutral', 'negative')),
    sentiment_score FLOAT CHECK (sentiment_score >= -1 AND sentiment_score <= 1),
    task_completed BOOL DEFAULT NULL,
    feedback_text STRING,
    feedback_tags JSONB DEFAULT '[]',
    source STRING DEFAULT 'explicit',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_feedback_session ON user_feedback(session_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_tenant ON user_feedback(tenant_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_sentiment ON user_feedback(sentiment);
CREATE INDEX IF NOT EXISTS idx_user_feedback_created ON user_feedback(created_at);
CREATE INDEX IF NOT EXISTS idx_user_feedback_satisfaction ON user_feedback(satisfaction_score);
