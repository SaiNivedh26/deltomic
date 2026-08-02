-- Tenants: uniquely identified by email, stores customer metadata
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email STRING NOT NULL UNIQUE,
    company_name STRING,
    contact_name STRING,
    customer_id STRING NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Session history: stores context/summary of each session per tenant
CREATE TABLE IF NOT EXISTS session_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    agent_id STRING NOT NULL,
    grant_id UUID,
    task_description STRING,
    summary STRING,
    issue_category STRING,
    resolution_status STRING DEFAULT 'pending',
    tool_calls_count INT DEFAULT 0,
    commands_executed JSONB DEFAULT '[]',
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Tool call logs: detailed tracking for observability (LangSmith-style)
CREATE TABLE IF NOT EXISTS tool_call_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES session_history(id),
    tenant_id UUID REFERENCES tenants(id),
    agent_id STRING NOT NULL,
    grant_id UUID,
    tool_name STRING NOT NULL,
    tool_args JSONB DEFAULT '{}',
    tool_result STRING,
    status STRING DEFAULT 'success',
    duration_ms INT,
    model_used STRING,
    trace_id STRING,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Task profiles: dynamic tool configurations per task type
CREATE TABLE IF NOT EXISTS task_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name STRING NOT NULL UNIQUE,
    description STRING,
    allowed_tools JSONB NOT NULL DEFAULT '[]',
    restricted_tools JSONB NOT NULL DEFAULT '[]',
    requires_escalation JSONB NOT NULL DEFAULT '[]',
    default_commands JSONB NOT NULL DEFAULT '[]',
    escalation_commands JSONB NOT NULL DEFAULT '[]',
    is_active BOOL NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_tenants_email ON tenants(email);
CREATE INDEX IF NOT EXISTS idx_tenants_customer_id ON tenants(customer_id);
CREATE INDEX IF NOT EXISTS idx_session_history_tenant ON session_history(tenant_id);
CREATE INDEX IF NOT EXISTS idx_session_history_started ON session_history(started_at);
CREATE INDEX IF NOT EXISTS idx_session_history_category ON session_history(issue_category);
CREATE INDEX IF NOT EXISTS idx_tool_call_logs_session ON tool_call_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_call_logs_tenant ON tool_call_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tool_call_logs_created ON tool_call_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_tool_call_logs_tool ON tool_call_logs(tool_name);
CREATE INDEX IF NOT EXISTS idx_task_profiles_name ON task_profiles(name);

-- Seed default task profiles
INSERT INTO task_profiles (name, description, allowed_tools, restricted_tools, requires_escalation, default_commands, escalation_commands)
VALUES
    (
        'diagnostic',
        'Read-only diagnostic tasks',
        '["list_available_commands", "run_command", "revoke_access"]',
        '["rm", "chmod", "mv", "cp"]',
        '["rm -rf", "chmod 777", "mkfs", "dd if="]',
        '["ls", "ls -la", "df -h", "whoami", "pwd", "uname -a", "uptime", "free -m", "cat /etc/os-release", "grep", "find", "head", "tail", "wc"]',
        '["rm", "chmod", "mv", "cp", "bash", "sh"]'
    ),
    (
        'remediation',
        'Fix-oriented tasks with write access',
        '["list_available_commands", "run_command", "revoke_access"]',
        '["rm -rf", "mkfs", "dd if="]',
        '["rm -rf", "chmod 777", "mkfs", "dd if="]',
        '["ls", "ls -la", "df -h", "whoami", "pwd", "uname -a", "uptime", "free -m", "cat", "grep", "find", "head", "tail", "wc", "sed", "awk", "touch", "mkdir", "cp", "mv", "echo", "tee", "chmod", "python3", "bash", "sh"]',
        '["rm -rf", "mkfs", "dd if="]'
    ),
    (
        'full_autonomous',
        'Full autonomous access for complex multi-step tasks',
        '["list_available_commands", "run_command", "revoke_access"]',
        '["mkfs", "dd if="]',
        '["mkfs", "dd if=", "rm -rf /"]',
        '["ls", "ls -la", "df -h", "whoami", "pwd", "uname -a", "uptime", "free -m", "cat", "grep", "find", "head", "tail", "wc", "sort", "uniq", "sed", "awk", "touch", "mkdir", "rm", "mv", "cp", "echo", "tee", "chmod", "python3", "python", "bash", "sh", "./"]',
        '["mkfs", "dd if=", "rm -rf /"]'
    )
ON CONFLICT (name) DO NOTHING;
