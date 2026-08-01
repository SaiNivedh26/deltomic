# CIS CockroachDB Benchmark Audit Report

This is a sample report from an audit of a self-hosted CockroachDB production cluster. It demonstrates the expected output format with both quick scan and full audit findings. Use this as a template when producing audit reports — replace all values with actual findings from the target cluster.

---

**Date:** 2026-06-09
**Benchmark:** CIS CockroachDB 2.x v1.0.0 — Level 1
**Audit Depth:** Quick Scan + Full Audit on failures
**Cluster:** prod-east-cluster
**CockroachDB Version:** v25.2.3
**Nodes Assessed:** 3 (node1, node2, node3)
**Auditor:** <auditor-name>
**Compliance Context:** SOC 2, PCI DSS
**Enterprise License:** Yes

## Summary

| Status | Count |
|--------|-------|
| PASS   | 19    |
| FAIL   | 5     |
| MANUAL | 5     |
| N/A    | 1     |

## Findings

### 1. Installation and Patches

| Control | Description | Status | Details |
|---------|-------------|--------|---------|
| 1.1 | Binary integrity | MANUAL | v25.2.3 confirmed. SHA-256 verification requires comparison against binaries.cockroachdb.com |
| 1.2 | Systemd service enabled | PASS | `systemctl is-enabled` → `enabled` on all 3 nodes. Service runs as User=cockroach with Type=notify, Restart=always |
| 1.3 | TLS enabled | PASS | No `--insecure` flag. Cert directory owned by cockroach:cockroach. `openssl verify` confirms node.crt signed by ca.crt. All nodes report same Cluster ID |
| 1.4 | No --insecure flag | PASS | `grep -c insecure` → `0` on all nodes. No insecure flags in service files or wrapper scripts |
| 1.5 | All nodes same version | PASS | All 3 nodes report `build_tag: v25.2.3`. `SHOW CLUSTER SETTING version` = `25.2` |
| 1.6 | Rolling upgrade process | MANUAL | Runbook exists. Last tested 2026-04-01. Security advisories monitored |
| 1.7 | EAR with external KMS | PASS | `--enterprise-encryption` present with Vault KMS URI. Key files on separate `/secure-keys` volume with 400 permissions |

### 2. System Hardening and Topology

| Control | Description | Status | Details |
|---------|-------------|--------|---------|
| 2.1 | NTP active | PASS | chronyd active on all 3 nodes, synced to Amazon Time Sync (169.254.169.123). Clock offsets < 5ms per DB Console |
| 2.2 | One process per host | PASS | 1 CockroachDB process per node |
| 2.3 | Dedicated subnet | MANUAL | VPC security groups reviewed — port 26257 restricted to app subnet, 8080 to bastion only |
| 2.4 | Swap disabled | PASS | `swapon --show` returns 0 lines, swap commented in /etc/fstab |
| 2.5 | THP madvise | PASS | `[madvise]` on all 3 nodes, persistent via systemd unit |
| 2.6 | File descriptors >= 15k | PASS | `ulimit -n` → 35000, confirmed via `/proc/$(pgrep cockroach)/limits` |
| 2.7 | No sudo for cockroach | PASS | "not allowed to run sudo" on all nodes. No entries in sudoers |

### 3. Logging and Monitoring

| Control | Description | Status | Details |
|---------|-------------|--------|---------|
| 3.1 | Logging enabled | PASS | `--log-dir=/var/lib/cockroach/logs` in service file. Log files present with recent timestamps. Directory owned by cockroach, permissions drwx------ |
| 3.2 | Log rotation | MANUAL | CockroachDB defaults: max-file-size 10MiB, max-group-size 100MiB. Logrotate also configured with 30-day retention |
| 3.3 | Auth logging | FAIL | `sql_connections.enabled` = `false`, `sql_sessions.enabled` = `false`. No SESSIONS events in cockroach-sql-auth.log |
| 3.4 | Monitoring/alerting | PASS | Prometheus scraping confirmed, Grafana dashboards active, PagerDuty alerts for node health, replication, disk, clock offset |

### 4. User Access and Authorization

| Control | Description | Status | Details |
|---------|-------------|--------|---------|
| 4.1 | HBA configured | FAIL | HBA configuration is empty (using defaults: `host all all all cert-password`). No IP restrictions, no reject catch-all |
| 4.2 | SCRAM-SHA-256 | PASS | `password_encryption` = `scram-sha-256`. Bcrypt migration enabled. All stored hashes show SCRAM-SHA-256 prefix |
| 4.3 | Root user secured | FAIL | `sql.log.user_audit` is empty — root activity not audited. HBA does not restrict root to specific hosts. 3 users have admin role |
| 4.4 | Centralized users | FAIL | `oidc_authentication.enabled` = `false`. All users are local database accounts. No identity mapping configured |

### 5. Data Protection

| Control | Description | Status | Details |
|---------|-------------|--------|---------|
| 5.1 | Backup encryption | PASS | Backup schedules use `WITH kms = 'aws:///...'`. S3 bucket also has SSE-KMS enforced. No plaintext passphrases in scripts |
| 5.2 | Recovery testing | PASS | Last test 2026-04-15. Full restore in 47 minutes. PITR also tested. Documented in Confluence |
| 5.3 | Data localization | N/A | Single-region deployment. No data residency requirements |

### 6. CockroachDB Settings

| Control | Description | Status | Details |
|---------|-------------|--------|---------|
| 6.1 | Cert permissions | PASS | All `.key` files have 0600. node.crt expires 2027-03-15 (279 days). ca.crt expires 2028-01-01 (571 days). `openssl verify` OK |
| 6.2 | Settings redacted | PASS | Support bundle procedures use `--redact` per runbook. No secrets found in log grep |
| 6.3 | Audit logging | FAIL | `sql.log.user_audit` is empty. `sql.log.admin_audit.enabled` = `false`. No security sink with auditable: true |
| 6.4 | Session timeouts | PASS | `idle_in_session_timeout` = `15m0s`. PCI DSS compliant |
| 6.5 | OCSP checking | MANUAL | `security.ocsp.mode` = `off`. Requires review — certs do not currently include OCSP responder URLs |

## CIS Controls Mapping (Failures Only)

| CIS Control | NIST Safeguards Affected | Status |
|-------------|-------------------------|--------|
| 3.3 | CIS v8 8.5, 8.2; CIS v7 6.3 | FAIL |
| 4.1 | CIS v8 3.3, 4.4, 6.6; CIS v7 14.6 | FAIL |
| 4.3 | CIS v8 5.4, 6.6; CIS v7 4.3 | FAIL |
| 4.4 | CIS v8 5.1, 6.6; CIS v7 16.8 | FAIL |
| 6.3 | CIS v8 8.2, 8.3, 8.4; CIS v7 6.2, 6.3 | FAIL |

## Remediation Summary

Ordered by severity:

| # | Control | Finding | Severity | Remediation |
|---|---------|---------|----------|-------------|
| 1 | 4.1 | HBA not configured — all IPs allowed with cert-password | High | Configure HBA with specific IP ranges, strong auth, reject catch-all |
| 2 | 4.3 | Root user not secured — no audit, no IP restriction | High | Restrict root via HBA; set `sql.log.user_audit = 'root ALL'` |
| 3 | 6.3 | Audit logging disabled — no user or admin audit | High | `SET CLUSTER SETTING sql.log.user_audit = 'ALL ALL'; SET CLUSTER SETTING sql.log.admin_audit.enabled = true;` |
| 4 | 3.3 | Connection/auth logging disabled | Medium | `SET CLUSTER SETTING server.auth_log.sql_connections.enabled = true; SET CLUSTER SETTING server.auth_log.sql_sessions.enabled = true;` |
| 5 | 4.4 | No centralized identity — all local accounts | Medium | Enable OIDC authentication, configure identity mapping |

## How to Use This Report

For each FAIL finding:

1. **"Explain how to fix this"** — Open the linked remediation skill for step-by-step guidance
2. **"Help me fix this now"** — Walk through remediation interactively

After remediating, re-run the audit (quick scan first) to verify PASS.

## Evidence Artifacts

For compliance evidence, the following were collected during this audit:
- Quick scan output (all 30 control one-liners)
- Full security settings dump (comprehensive SQL query)
- Certificate expiry report
- HBA configuration export
- Screenshot of DB Console Node List (version uniformity)
- Prometheus/Grafana alerting configuration