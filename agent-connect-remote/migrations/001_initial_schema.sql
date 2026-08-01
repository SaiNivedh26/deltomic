-- Customer machines registered via SSM Hybrid Activation
CREATE TABLE IF NOT EXISTS customer_machines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id STRING NOT NULL,
    managed_node_id STRING NOT NULL UNIQUE,
    machine_name STRING,
    platform_type STRING,
    is_active BOOL NOT NULL DEFAULT true,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_ping_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Access grants for JIT sessions
CREATE TABLE IF NOT EXISTS support_access_grants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id STRING NOT NULL,
    managed_node_id STRING NOT NULL,
    requested_by STRING NOT NULL,
    approved_by STRING,
    status STRING NOT NULL DEFAULT 'pending',
    allowed_commands JSONB NOT NULL,
    max_session_duration_minutes INT NOT NULL DEFAULT 10,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    revoked_by STRING,
    revoked_reason STRING,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Audit log for all commands executed
CREATE TABLE IF NOT EXISTS support_command_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    grant_id UUID NOT NULL REFERENCES support_access_grants(id),
    command STRING NOT NULL,
    executed_by STRING NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    exit_code INT,
    stdout STRING,
    stderr STRING,
    session_id STRING,
    command_id STRING
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_machines_customer ON customer_machines(customer_id);
CREATE INDEX IF NOT EXISTS idx_grants_customer ON support_access_grants(customer_id);
CREATE INDEX IF NOT EXISTS idx_grants_status ON support_access_grants(status);
CREATE INDEX IF NOT EXISTS idx_grants_expires ON support_access_grants(expires_at);
CREATE INDEX IF NOT EXISTS idx_audit_grant ON support_command_audit(grant_id);
