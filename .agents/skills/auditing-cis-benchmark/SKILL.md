---
name: auditing-cis-benchmark
description: Audits a self-hosted CockroachDB cluster against the CIS CockroachDB Benchmark v1.0.0 Level 1 controls. Supports two audit depths — quick automated scans and full CIS audit procedures. Produces a structured PASS/FAIL/MANUAL report covering installation, system hardening, logging, user access, data protection, and CockroachDB settings. Use when preparing for CIS compliance assessments, hardening self-hosted deployments, or validating security posture against industry benchmarks.
compatibility: "CockroachDB self-hosted (all versions). Requires shell access to cluster nodes and SQL admin or VIEWACTIVITY privilege."
metadata:
  author: cockroachdb
  version: "1.0"
---

# Auditing CIS Benchmark Compliance

Assesses a self-hosted CockroachDB cluster against the CIS CockroachDB Benchmark v1.0.0 Level 1 profile. Evaluates 30 controls across six domains: installation and patches, system hardening and topology, logging and monitoring, user access and authorization, data protection, and CockroachDB settings. Produces a structured report with PASS, FAIL, and MANUAL REVIEW findings, including CIS Controls v7/v8 mappings with Implementation Group coverage.

**Scope:** Self-hosted CockroachDB deployments only. For CockroachDB Cloud clusters, use [auditing-cloud-cluster-security](../auditing-cloud-cluster-security/SKILL.md) instead — Cloud clusters have managed controls that supersede many CIS self-hosted checks.

**Authoritative source:** This skill implements the benchmark defined at https://github.com/cockroachlabs/CIS-benchmarks-crdb

**Read-only audit:** All operations are read-only. No cluster state, OS configuration, or files are modified during the assessment.

## When to Use This Skill

- Preparing for a CIS benchmark compliance assessment or external audit
- Hardening a new self-hosted CockroachDB production deployment
- Validating security posture against industry-standard benchmarks
- Performing periodic compliance checks as part of security operations
- Mapping CockroachDB security controls to CIS Controls frameworks
- Responding to auditor requests for CIS benchmark evidence

## Prerequisites

**Access requirements:**

| Requirement | Purpose |
|-------------|---------|
| SSH/shell access to cluster nodes | OS-level checks (systemd, swap, THP, file descriptors, certs) |
| SQL access (admin or VIEWACTIVITY) | Cluster settings, user/role audit, logging config |
| Access to systemd service files | Service configuration verification |
| Access to certificate directory | Certificate permission and validity checks |

**Tools:**

| Tool | Required | Purpose |
|------|----------|---------|
| `cockroach` CLI | Yes | Version check, cert inspection, SQL access |
| `systemctl` | Yes | Service status, NTP verification |
| `openssl` | Recommended | Certificate validation and expiry checks |
| Standard Unix tools | Yes | `ps`, `ls`, `cat`, `grep`, `swapon`, `ulimit` |

## Audit Depth

This skill supports two audit depths. Choose based on your needs:

| Depth | When to Use | What It Does |
|-------|-------------|--------------|
| **Quick Scan** | Periodic checks, CI/CD gates, rapid triage | Runs one-liner shell/SQL commands per control, returns pass/fail |
| **Full Audit** | Compliance evidence, external auditor requests, thorough assessments | Multi-step procedures per control from the official CIS benchmark |

At Step 0, confirm which depth the user wants. Both depths can be combined — run the quick scan first to identify failures, then run the full audit on those failures for evidence collection.

## CIS Benchmark Structure

The CIS CockroachDB Benchmark v1.0.0 Level 1 profile contains 30 controls organized into six sections:

| Section | Domain | Controls | Automated | Manual |
|---------|--------|----------|-----------|--------|
| 1 | Installation and Patches | 1.1–1.7 (7) | 3 | 4 |
| 2 | System Hardening and Topology | 2.1–2.7 (7) | 5 | 2 |
| 3 | Logging and Monitoring | 3.1–3.4 (4) | 1 | 3 |
| 4 | User Access and Authorization | 4.1–4.4 (4) | 0 | 4 |
| 5 | Data Protection | 5.1–5.3 (3) | 0 | 3 |
| 6 | CockroachDB Settings | 6.1–6.5 (5) | 1 | 4 |

See [CIS controls reference](references/cis-controls.md) for full control definitions with both quick scan commands and full audit procedures.

## Assessment Workflow

### Step 0: Confirm Audit Scope

Before starting, confirm with the user:

1. **Audit depth** — Quick scan, full audit, or both
2. **Target nodes** — Which nodes to audit (all nodes recommended)
3. **CockroachDB service account** — Username running CockroachDB (default: `cockroach`)
4. **Certificate directory** — Path to TLS certificates (default: `/var/lib/cockroach/certs`)
5. **Data directory** — Path to CockroachDB data store (default: `/var/lib/cockroach`)
6. **Log directory** — Path to logs (default: `/var/lib/cockroach/logs` or `<store>/logs`)
7. **Enterprise license** — Whether Enterprise features (EAR) are available

Record these values — they parameterize the checks below.

### Step 1: Installation and Patches (Controls 1.1–1.7)

These controls verify binary integrity, systemd service management, TLS initialization, version uniformity, upgrade processes, and encryption at rest.

**Key checks:**
- 1.1: Binary downloaded from official source, SHA-256 verified (Manual)
- 1.2: `systemctl is-enabled cockroach.service` → `enabled` (Automated)
- 1.3: No `--insecure` flag; certs directory exists with valid CA-signed certs (Automated)
- 1.4: `ps aux | grep -c insecure` → `0` (Automated)
- 1.5: All nodes run same version — quick scan via `cockroach version`, full audit via DB Console Node List and `crdb_internal.gossip_nodes` (Automated)
- 1.6: Rolling upgrade runbook exists and has been tested (Manual)
- 1.7: `--enterprise-encryption` configured with external KMS, keys not on disk (Manual)

### Step 2: System Hardening and Topology (Controls 2.1–2.7)

These controls verify OS-level configuration: time synchronization, process isolation, network segmentation, memory settings, file descriptors, and privilege restrictions.

**Key checks (run on each node):**
- 2.1: NTP/chrony active, offsets below `--max-offset` (Automated)
- 2.2: One CockroachDB process per host (Automated)
- 2.3: Dedicated subnet with restricted ingress on ports 26257/8080 (Manual)
- 2.4: `swapon --show | wc -l` → `0` (Automated)
- 2.5: THP set to `madvise` or `never` (Automated)
- 2.6: File descriptor limit ≥ 15,000 for cockroach user (Automated)
- 2.7: cockroach user has no sudo privileges (Automated)

### Step 3: Logging and Monitoring (Controls 3.1–3.4)

These controls verify logging configuration, rotation, authentication event capture, and monitoring/alerting.

**Key checks:**
- 3.1: Log directory exists, owned by cockroach, permissions 700 (Manual)
- 3.2: Log rotation configured via CockroachDB config or logrotate (Manual)
- 3.3: Both `server.auth_log.sql_connections.enabled` AND `server.auth_log.sql_sessions.enabled` = `true` (Automated)
- 3.4: Monitoring system scraping metrics, alerts configured (Manual)

### Step 4: User Access and Authorization (Controls 4.1–4.4)

These controls verify host-based authentication, password security, root user hardening, and centralized identity management.

> ⚠️ **Control 4.2 (Full Audit only):** Inspecting stored password hashes requires `SET allow_unsafe_internals = true`. This is a break-glass, audit-only operation — run only in a dedicated admin session by authorized operators, and reset immediately after with `SET allow_unsafe_internals = false`. Do not expose this to application workloads.

**Key checks (all SQL):**
- 4.1: HBA has specific IP ranges, strong auth methods, reject catch-all (Manual)
- 4.2: `password_encryption` = `scram-sha-256`, stored hashes are SCRAM format (Manual)
- 4.3: Root restricted to specific hosts via HBA with cert method, activity audited (Manual)
- 4.4: OIDC/LDAP enabled, identity mapping configured, local accounts minimized (Manual)

### Step 5: Data Protection (Controls 5.1–5.3)

These controls verify backup encryption, recovery testing, and multi-region data localization.

**Key checks:**
- 5.1: Backups use `kms` or `encryption_passphrase`, or storage-layer encryption enforced (Manual)
- 5.2: Recovery procedures tested quarterly with documented results (Manual)
- 5.3: Multi-region tables use `REGIONAL BY ROW` or zone constraints for data residency (Manual)

### Step 6: CockroachDB Settings (Controls 6.1–6.5)

These controls verify certificate security, setting redaction, audit logging, session timeouts, and OCSP.

**Key checks:**
- 6.1: Private key permissions `0600`, certs valid 90+ days (Automated)
- 6.2: Debug bundles use `--redact`, no secrets in logs (Manual)
- 6.3: `sql.log.user_audit` non-empty, `sql.log.admin_audit.enabled` = `true`, security channels configured (Manual)
- 6.4: `sql.defaults.idle_in_session_timeout` set (e.g., `15m`) (Manual)
- 6.5: `security.ocsp.mode` = `strict` or `lax` (Manual)

## Report Format

Generate a markdown report following the structure in [sample report](references/sample-report.md).

**Status markers:**
- `[PASS]` — Control is satisfied
- `[FAIL]` — Control is not satisfied, remediation required
- `[MANUAL]` — Requires human review; automated check cannot determine compliance
- `[N/A]` — Control does not apply (e.g., EAR without Enterprise license)

## Relationship to Other Security Skills

| CIS Section | Related Remediation Skills |
|-------------|---------------------------|
| 1 Installation | [managing-tls-certificates](../managing-tls-certificates/SKILL.md), [enabling-cmek-encryption](../enabling-cmek-encryption/SKILL.md) |
| 3 Logging | [configuring-audit-logging](../configuring-audit-logging/SKILL.md), [configuring-log-export](../configuring-log-export/SKILL.md) |
| 4 User Access | [hardening-user-privileges](../hardening-user-privileges/SKILL.md), [enforcing-password-policies](../enforcing-password-policies/SKILL.md), [configuring-sso-and-scim](../configuring-sso-and-scim/SKILL.md) |
| 5 Data Protection | [preparing-compliance-documentation](../preparing-compliance-documentation/SKILL.md) |
| 6 Settings | [managing-tls-certificates](../managing-tls-certificates/SKILL.md), [configuring-audit-logging](../configuring-audit-logging/SKILL.md) |

For a broader security posture assessment (covering Cloud and self-hosted), use [auditing-cloud-cluster-security](../auditing-cloud-cluster-security/SKILL.md).

## Safety Considerations

- **All operations are read-only.** No cluster settings, OS configuration, or files are modified.
- **Shell commands use read-only tools:** `ps`, `ls`, `cat`, `grep`, `systemctl is-enabled/is-active`, `swapon --show`, `ulimit`, `openssl x509`, `openssl verify`.
- **SQL queries use SHOW and SELECT only.** No DDL or DML statements.
- **One exception (4.2):** The full audit procedure for password hash inspection requires `SET allow_unsafe_internals = true` — this is a read-only break-glass operation that must be reset immediately after (`SET allow_unsafe_internals = false`). Only authorized operators should run this step.
- **No secrets are logged.** Certificate private keys and passwords are not included in report output.
- **Privilege check:** Some SQL queries require admin or VIEWACTIVITY privilege. The report notes any permission gaps.

## References

**Skill references:**
- [CIS controls reference](references/cis-controls.md) — All 30 controls with quick scan commands and full audit procedures
- [SQL queries for CIS audit](references/sql-queries.md) — All SQL queries used in the assessment
- [Sample audit report](references/sample-report.md) — Example report with findings

**Authoritative source:**
- [CIS CockroachDB Benchmark (official repo)](https://github.com/cockroachlabs/CIS-benchmarks-crdb)

**Related skills:**
- [auditing-cloud-cluster-security](../auditing-cloud-cluster-security/SKILL.md) — Broader security posture assessment
- [configuring-audit-logging](../configuring-audit-logging/SKILL.md) — SQL audit logging setup
- [hardening-user-privileges](../hardening-user-privileges/SKILL.md) — RBAC tightening
- [enforcing-password-policies](../enforcing-password-policies/SKILL.md) — Password policy enforcement
- [managing-tls-certificates](../managing-tls-certificates/SKILL.md) — TLS certificate management
- [enabling-cmek-encryption](../enabling-cmek-encryption/SKILL.md) — Encryption at rest
- [configuring-sso-and-scim](../configuring-sso-and-scim/SKILL.md) — SSO and SCIM provisioning

**Official CockroachDB documentation:**
- [Security Overview](https://www.cockroachlabs.com/docs/stable/security-reference/security-overview.html)
- [Recommended Production Settings](https://www.cockroachlabs.com/docs/stable/recommended-production-settings.html)
- [Releases](https://www.cockroachlabs.com/docs/releases/)
- [Security Advisories](https://www.cockroachlabs.com/docs/advisories/)