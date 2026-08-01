# SQL Queries for CIS Benchmark Audit

All SQL queries used during CIS CockroachDB Benchmark assessments. All queries are read-only (SELECT and SHOW statements only), except the break-glass `allow_unsafe_internals` step in 4.2 which is audit-only and must be reset immediately.

## Installation and Patches

### 1.5 — Verify All Nodes Same Version
```sql
SELECT version();

-- Compare versions across all cluster nodes
SELECT node_id, build_tag FROM crdb_internal.gossip_nodes ORDER BY node_id;

-- Check cluster logical version (upgrade finalization status)
SHOW CLUSTER SETTING version;
```

## Logging and Monitoring

### 3.3 — Connection and Authentication Logging
```sql
-- Both must be true for comprehensive SESSIONS logging
SHOW CLUSTER SETTING server.auth_log.sql_connections.enabled;
SHOW CLUSTER SETTING server.auth_log.sql_sessions.enabled;

-- Verify events in system.eventlog
SELECT timestamp, (info::JSONB)->>'EventType' AS eventtype
FROM system.eventlog
WHERE (info::JSONB)->>'EventType' IN ('client_connection_start','client_authentication_failed')
ORDER BY timestamp DESC LIMIT 20;
```

## User Access and Authorization

### 4.1 — Host-Based Authentication
```sql
SHOW CLUSTER SETTING server.host_based_authentication.configuration;
-- FAIL if empty (default allows all with cert-password)
-- FAIL if contains trust method
-- FAIL if no reject catch-all
```

### 4.2 — Password Authentication Security
```sql
-- Check password hashing algorithm
SHOW CLUSTER SETTING server.user_login.password_encryption;
-- Expected: scram-sha-256

-- Check bcrypt-to-SCRAM migration
SHOW CLUSTER SETTING server.user_login.upgrade_bcrypt_stored_passwords_to_scram.enabled;

-- ⚠️ Break-glass: inspect stored password hashes (authorized operators only)
SET allow_unsafe_internals = true;
SET bytea_output = 'escape';
SELECT username, "hashedPassword" FROM system.users WHERE "hashedPassword" IS NOT NULL;
SET allow_unsafe_internals = false;
-- SCRAM hashes show SCRAM-SHA-256$... prefix when decoded
```

### 4.3 — Root User and Admin Audit
```sql
-- Check user audit logging (should include root)
SHOW CLUSTER SETTING sql.log.user_audit;

-- List admin role members
SELECT member AS admin_user FROM [SHOW GRANTS ON ROLE admin] WHERE is_admin = true ORDER BY member;

-- List all users with roles
SELECT username, options, member_of FROM [SHOW USERS] ORDER BY username;

-- Find users without role membership (potential orphaned accounts)
SELECT username FROM [SHOW USERS]
WHERE 'NOLOGIN' != ALL(options) AND array_length(member_of, 1) IS NULL
ORDER BY username;
```

### 4.4 — Centralized Identity Management
```sql
SHOW CLUSTER SETTING server.oidc_authentication.enabled;
SHOW CLUSTER SETTING server.oidc_authentication.provider_url;
SHOW CLUSTER SETTING server.oidc_authentication.client_id;
SHOW CLUSTER SETTING server.identity_map.configuration;

-- Check HBA for LDAP entries
SHOW CLUSTER SETTING server.host_based_authentication.configuration;
-- Look for lines with ldap method
```

## Data Protection

### 5.1 — Backup Encryption Verification
```sql
-- List backup schedules
SELECT id, label, schedule_status, next_run, created
FROM [SHOW SCHEDULES]
WHERE label ILIKE '%backup%';

-- Check recent backup jobs
SELECT job_id, job_type, status, created, finished
FROM [SHOW JOBS]
WHERE job_type = 'BACKUP'
ORDER BY created DESC LIMIT 10;

-- View backups in a location
SHOW BACKUPS IN 's3://bucket/path?AUTH=...';
```

### 5.3 — Multi-Region Data Placement
```sql
SHOW REGIONS FROM DATABASE <database_name>;
SHOW CREATE TABLE <table_name>;
SHOW RANGES FROM TABLE <table_name>;
```

## CockroachDB Settings

### 6.3 — Security Audit Logging
```sql
SHOW CLUSTER SETTING sql.log.user_audit;
SHOW CLUSTER SETTING sql.log.admin_audit.enabled;
SHOW CLUSTER SETTING server.auth_log.sql_connections.enabled;
```

### 6.4 — Session Idle Timeout
```sql
SHOW CLUSTER SETTING sql.defaults.idle_in_session_timeout;

-- Check role-level timeouts
SELECT rolname, rolconfig FROM pg_catalog.pg_roles
WHERE rolconfig IS NOT NULL AND rolconfig::text LIKE '%idle_in_session_timeout%';
```

### 6.5 — OCSP Configuration
```sql
SHOW CLUSTER SETTING security.ocsp.mode;
SHOW CLUSTER SETTING security.ocsp.timeout;
```

## Comprehensive Security Settings Dump

Capture all security-relevant cluster settings in a single pass for evidence collection:

```sql
SELECT variable, value
FROM [SHOW ALL CLUSTER SETTINGS]
WHERE variable IN (
  'server.auth_log.sql_connections.enabled',
  'server.auth_log.sql_sessions.enabled',
  'server.host_based_authentication.configuration',
  'server.user_login.password_encryption',
  'server.user_login.upgrade_bcrypt_stored_passwords_to_scram.enabled',
  'server.user_login.min_password_length',
  'server.oidc_authentication.enabled',
  'server.oidc_authentication.provider_url',
  'server.identity_map.configuration',
  'sql.log.user_audit',
  'sql.log.admin_audit.enabled',
  'sql.defaults.idle_in_session_timeout',
  'security.ocsp.mode',
  'security.ocsp.timeout'
)
ORDER BY variable;
```