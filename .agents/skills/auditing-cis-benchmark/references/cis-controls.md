# CIS CockroachDB Benchmark v1.0.0 — Level 1 Controls Reference

All 30 controls with both **Quick Scan** (one-liner automated checks) and **Full Audit** (multi-step CIS procedures). Sourced from https://github.com/cockroachlabs/CIS-benchmarks-crdb

---

## 1. Installation and Patches

### 1.1 Verify Binary Integrity (Manual)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **CIS v8** | 16.5 Use Up-to-Date and Trusted Third-Party Software Components (IG1/2/3) |
| **CIS v7** | 18.4 Only Use Up-to-date And Trusted Third-Party Components (IG1/2/3) |
| **Default** | N/A — operational process control external to CockroachDB |

**Quick Scan:**
```bash
cockroach version
# Manual review: compare installed version against https://binaries.cockroachdb.com/
```

**Full Audit:**
1. Inspect CI/CD pipelines and automation scripts — confirm they download only from `https://binaries.cockroachdb.com/` or a vetted internal mirror
2. Verify checksum for installed binary:
```bash
VERSION="v25.3.4"
FILE_NAME="cockroach-${VERSION}.linux-amd64.tgz"
SHA_URL="https://binaries.cockroachdb.com/${FILE_NAME}.sha256sum"
if [ "$(wget -qO- "$SHA_URL" | awk '{print $1}')" == "$(sha256sum "$FILE_NAME" | awk '{print $1}')" ]; then
  echo "OK: SHA-256 matches"
else
  echo "FAIL: SHA-256 mismatch"
fi
```

---

### 1.2 Ensure Systemd Service Files Are Enabled (Automated)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **CIS v8** | 4.1 Establish and Maintain a Secure Configuration Process (IG1/2/3) |
| **CIS v7** | 5.1 Establish Secure Configurations (IG1/2/3) |
| **Default** | Not configured — must be created manually |

**Quick Scan:**
```bash
systemctl is-enabled cockroach.service 2>/dev/null || echo 'not enabled'
# Expected: enabled
```

**Full Audit:**
1. Verify service is enabled: `systemctl is-enabled cockroach.service`
2. Verify service is running: `systemctl is-active cockroach.service`
3. Inspect service file for security settings:
```bash
sudo systemctl cat cockroach.service | grep -E 'User=|ExecStart=|Restart=|Type='
# Expected: User=cockroach, Type=notify, Restart=always
```

---

### 1.3 Ensure Cluster is Initialized Securely with TLS (Automated)

| Field | Value |
|-------|-------|
| **Severity** | High |
| **CIS v8** | 3.10 Encrypt Sensitive Data in Transit (IG1/2/3); 4.1 Secure Configuration (IG1/2/3) |
| **CIS v7** | 14.4 Encrypt All Sensitive Information in Transit (IG1/2/3) |
| **Default** | Secure when `--insecure` is not set and valid certs present in `--certs-dir` |

**Quick Scan:**
```bash
ps aux | grep '[c]ockroach start' | grep -o 'insecure' || echo 'secure mode'
# Expected: must NOT contain "insecure"
```

**Full Audit:**
1. Confirm no `--insecure` flag:
```bash
ps -ef | grep cockroach
# Check for --insecure or --accept-sql-without-tls
```
2. Verify certificate directory ownership:
```bash
ls -ld /var/lib/cockroach/certs
ls -l /var/lib/cockroach/certs
# Expected: owned by cockroach:cockroach, contains ca.crt, node.crt, node.key
```
3. Validate node certificate against CA:
```bash
openssl verify -CAfile /var/lib/cockroach/certs/ca.crt /var/lib/cockroach/certs/node.crt
# Expected: OK
```
4. Confirm cluster identity via secure CLI:
```bash
cockroach node status --certs-dir=/var/lib/cockroach/certs --host=<node>
# All nodes report same Cluster ID
cockroach sql --certs-dir=/var/lib/cockroach/certs --host=<node> -e "SHOW DATABASES;"
# Successful connection confirms secure SQL connectivity
```

---

### 1.4 Do Not Use --insecure Flag in Production (Automated)

| Field | Value |
|-------|-------|
| **Severity** | High |
| **CIS v8** | 3.10 Encrypt Sensitive Data in Transit (IG1/2/3); 4.1 Secure Configuration (IG1/2/3) |
| **CIS v7** | 14.4 Encrypt All Sensitive Information in Transit (IG1/2/3) |
| **Default** | Not set (secure by default when certs provided) |

**Quick Scan:**
```bash
ps aux | grep '[c]ockroach start' | grep -c 'insecure'
# Expected: 0
```

**Full Audit:**
1. Check running processes: `ps -ef | grep cockroach` — no `--insecure`
2. Check systemd service file: `sudo systemctl cat cockroach.service | grep insecure` — no matches
3. Check any wrapper scripts: `grep -ri insecure /etc/cockroach/ /usr/lib/systemd/system/`

---

### 1.5 Ensure All Nodes Are Running the Same Version (Automated)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **CIS v8** | 2.2 Ensure Authorized Software is Currently Supported (IG1/2/3); 4.1 Secure Configuration (IG1/2/3) |
| **CIS v7** | 2.2 Ensure Software is Supported by Vendor (IG1/2/3) |
| **Default** | Temporary version skew tolerated during rolling upgrades |

**Quick Scan:**
```bash
cockroach version | grep 'Build Tag'
```

**Full Audit:**
1. Check version on each node: `cockroach version`
2. Check via DB Console: Cluster Overview → Node List — all versions match
3. Check upgrade status:
```sql
SHOW CLUSTER SETTING version;
-- After major upgrade, should show new major version (e.g., 25.4)
```
4. Check node status:
```bash
cockroach node status --certs-dir=/var/lib/cockroach/certs --host=<node> --format=table
# Review build/version fields for mismatches
```

---

### 1.6 Establish Rolling Upgrade Process (Manual)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **CIS v8** | 7.3 Perform Automated Operating System Patch Management (IG1/2/3) |
| **CIS v7** | 3.4 Deploy Automated Operating System Patch Management Tools (IG1/2/3) |
| **Default** | No process exists by default — must be documented by organization |

**Quick Scan:**
```bash
echo 'Manual: Verify rolling upgrade runbook exists and has been tested'
```

**Full Audit:**
1. Request operational runbook — must cover: pre-upgrade backup, sequential node drain/stop/upgrade/start, version finalization, rollback
2. Verify last test date in non-production environment
3. Confirm security advisory monitoring at https://www.cockroachlabs.com/docs/advisories/

---

### 1.7 Encryption at Rest Keys Managed by External KMS (Manual)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **CIS v8** | 3.11 Encrypt Sensitive Data at Rest (IG1/2/3); 4.1 Secure Configuration (IG1/2/3) |
| **CIS v7** | 13.5 Manage Access Control for Remote Assets (IG1/2/3) |
| **Default** | EAR disabled — no encryption at rest unless configured with `--enterprise-encryption` |

**Quick Scan:**
```bash
ps aux | grep '[c]ockroach start' | grep 'enterprise-encryption' || echo 'EAR not configured'
```

**Full Audit:**
1. Check for enterprise encryption flag:
```bash
ps -ef | grep cockroach | grep -- '--enterprise-encryption'
# Expected: --enterprise-encryption=path=...,key=...,old-key=...,rotation-period=...
```
2. Inspect configuration for external key source:
```bash
grep -Ri "vault" /etc/cockroach /usr/lib/systemd/system
grep -Ri "encryption-key" /etc/cockroach /usr/lib/systemd/system
# Look for Vault, Transit, or other secret loader references
```
3. Verify key files are NOT on same volume as data:
```bash
find /etc/cockroach /var/lib/cockroach -type f -name "*.key" -ls
# Key files must not be in data directory; must be on separate volume with 400 permissions
```
4. Verify encryption is active:
```bash
cockroach debug encryption-active-key /var/lib/cockroach
```

---

## 2. System Hardening and Topology

### 2.1 NTP Service Configured for Clock Synchronization (Automated)

| Field | Value |
|-------|-------|
| **Severity** | High |
| **CIS v8** | 8.7 Ensure Time Synchronization Across Enterprise Assets (IG1/2/3) |
| **CIS v7** | 6.1 Maintain an Accurate Time Source (IG1/2/3) |
| **Default** | `--max-offset` defaults to 500ms; NTP must be configured at OS level |

**Quick Scan:**
```bash
systemctl is-active chronyd 2>/dev/null || systemctl is-active ntpd 2>/dev/null || echo 'no time sync'
# Expected: active
```

**Full Audit:**
1. Confirm NTP/chrony is active: `systemctl status chronyd` or `timedatectl`
2. Verify time source selection — all nodes use compatible leap-smearing sources:
   - AWS: Amazon Time Sync (`169.254.169.123`) via `chronyc sources -v`
   - GCE: Google internal NTP (`metadata.google.internal`)
   - Other: Google Public NTP (`time.google.com`)
3. Check CockroachDB clock offsets via Prometheus metric `clock_offset_meannanos` or DB Console — offsets below `--max-offset` (500ms)
4. Check logs for clock skew errors:
```bash
grep -i "clock" /var/lib/cockroach/logs/cockroach.log
# Expected: no offset error entries
```

---

### 2.2 One CockroachDB Process Per Host (Automated)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **CIS v8** | 4.1 Establish and Maintain a Secure Configuration Process (IG1/2/3) |
| **CIS v7** | 14.1 Segment the Network Based on Sensitivity (IG1/2/3) |
| **Default** | Not enforced — operator responsibility |

**Quick Scan:**
```bash
ps aux | grep '[c]ockroach start' | wc -l
# Expected: 1
```

**Full Audit:**
1. Count CockroachDB processes per host: `ps aux | grep '[c]ockroach start' | wc -l` → must be 1
2. For Kubernetes: verify pod anti-affinity rules prevent co-scheduling

---

### 2.3 Database Servers in Dedicated Subnet (Manual)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **CIS v8** | 12.1 Ensure Network Infrastructure is Up-to-Date (IG1/2/3) |
| **CIS v7** | 9.2 Ensure Only Approved Ports, Protocols and Services Are Running (IG1/2/3) |
| **Default** | Not enforced — operator responsibility |

**Quick Scan:**
```bash
echo 'Manual: Review network topology and firewall rules'
```

**Full Audit:**
1. Verify CockroachDB nodes are in a dedicated subnet/VPC
2. Verify firewall/security group rules:
   - Ingress 26257 allowed from app tier and cluster nodes only
   - Ingress 8080 allowed from admin/bastion hosts only
   - All other inbound denied
   - Outbound restricted to necessary services
3. Document network topology for evidence

---

### 2.4 Disable Linux Memory Swapping (Automated)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **CIS v8** | 4.1 Secure Configuration (IG1/2/3) |
| **CIS v7** | 5.1 Establish Secure Configurations (IG1/2/3) |
| **Default** | Swap typically enabled in default Linux installations |

**Quick Scan:**
```bash
swapon --show | wc -l
# Expected: 0
```

**Full Audit:**
1. Check swap: `swapon --show` and `free -h` — no swap space active
2. Check `/etc/fstab` for swap entries: `grep swap /etc/fstab` — all should be commented out

---

### 2.5 Configure THP to madvise (Automated)

| Field | Value |
|-------|-------|
| **Severity** | Low |
| **CIS v8** | 4.1 Secure Configuration (IG1/2/3) |
| **CIS v7** | 5.1 Establish Secure Configurations (IG1/2/3) |
| **Default** | `always` on most Linux distributions |

**Quick Scan:**
```bash
cat /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null | grep -o '\[.*\]' | tr -d '[]'
# Expected: madvise or never
```

**Full Audit:**
1. Check THP enabled mode: `cat /sys/kernel/mm/transparent_hugepage/enabled`
2. Check THP defrag mode: `cat /sys/kernel/mm/transparent_hugepage/defrag`
3. Verify persistence — check for systemd unit or rc.local entry

---

### 2.6 File Descriptor Limit >= 15,000 (Automated)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **CIS v8** | 4.1 Secure Configuration (IG1/2/3) |
| **CIS v7** | 5.1 Establish Secure Configurations (IG1/2/3) |
| **Default** | 1024 or 4096 on most Linux distributions — insufficient |

**Quick Scan:**
```bash
su - cockroach -c 'ulimit -n' 2>/dev/null || echo 'not configured'
# Expected: >= 15000 (recommended: 35000)
```

**Full Audit:**
1. Check limits for cockroach user: `su - cockroach -c 'ulimit -n'`
2. Check running process limits: `cat /proc/$(pgrep cockroach)/limits | grep 'open files'`
3. Check `/etc/security/limits.conf` and systemd `LimitNOFILE`

---

### 2.7 No Sudo Privileges for CockroachDB User (Automated)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **CIS v8** | 5.4 Restrict Administrator Privileges to Dedicated Accounts (IG1/2/3) |
| **CIS v7** | 4.3 Ensure the Use of Dedicated Administrative Accounts (IG1/2/3) |
| **Default** | Depends on how cockroach user was created |

**Quick Scan:**
```bash
sudo -l -U cockroach 2>&1 | grep -c 'not allowed'
# Expected: >= 1
```

**Full Audit:**
1. Check sudo access: `sudo -l -U cockroach` — should show "not allowed to run sudo"
2. Check `/etc/sudoers` and `/etc/sudoers.d/` for cockroach entries

---

## 3. Logging and Monitoring

### 3.1 Logging Enabled with Secure Storage (Manual)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **CIS v8** | 8.2 Collect Audit Logs (IG1/2/3); 8.5 Collect Detailed Audit Logs (IG2/3) |
| **CIS v7** | 6.2 Activate Audit Logging (IG1/2/3) |
| **Default** | Logging enabled; file sinks write to `<store>/logs`; permissions 0644; `server.eventlog.enabled` = true |

**Quick Scan:**
```bash
ls -ld /var/lib/cockroach/logs 2>/dev/null || echo 'logs directory not found'
```

**Full Audit:**
1. Check logging configuration:
```bash
cockroach debug check-log-config
sudo systemctl cat cockroach.service | grep ExecStart
# Look for --log-dir, --log-config-file, or --log={yaml}
```
2. Verify log files exist with recent timestamps:
```bash
ls -lh /var/lib/cockroach/logs/
tail -n 10 /var/lib/cockroach/logs/cockroach.log
# Expect: cockroach.log, cockroach-security.log, cockroach-sql-audit.log, cockroach-sql-auth.log
```
3. Verify directory ownership and permissions:
```bash
ls -ld /var/lib/cockroach/logs
# Expected: cockroach:cockroach, drwx------ (700)
```

---

### 3.2 Log Rotation and Retention Configured (Manual)

| Field | Value |
|-------|-------|
| **Severity** | Low |
| **CIS v8** | 8.3 Ensure Adequate Audit Log Storage (IG1/2/3) |
| **CIS v7** | 6.3 Enable Detailed Logging (IG1/2/3) |
| **Default** | max-file-size: 10 MiB, max-group-size: 100 MiB per group |

**Quick Scan:**
```bash
echo 'Manual: Review log rotation configuration'
```

**Full Audit:**
1. Check CockroachDB log config: `cockroach debug check-log-config` — review `max-file-size`, `max-group-size`
2. Check OS logrotate: `cat /etc/logrotate.d/cockroach` if present
3. Verify retention meets compliance requirements (typically 90+ days)

---

### 3.3 Connection and Authentication Logging Enabled (Automated)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **CIS v8** | 8.5 Collect Detailed Audit Logs (IG1/2/3); 8.2 Collect Audit Logs (IG1/2/3) |
| **CIS v7** | 6.3 Enable Detailed Logging (IG1/2/3) |
| **Default** | Both `sql_connections.enabled` and `sql_sessions.enabled` are `false` |

**Quick Scan:**
```sql
SHOW CLUSTER SETTING server.auth_log.sql_connections.enabled;
-- Expected: true
SHOW CLUSTER SETTING server.auth_log.sql_sessions.enabled;
-- Expected: true
```

**Full Audit:**
1. Verify both cluster settings are `true`
2. Verify SESSIONS log file is present with recent events:
```bash
ls -lh /var/lib/cockroach/logs/cockroach-sql-auth.log
tail -n 10 /var/lib/cockroach/logs/cockroach-sql-auth.log
# Expect JSON entries: client_connection_start, client_authentication_ok/failed, client_session_end
```
3. Verify events via system.eventlog:
```sql
SELECT timestamp, (info::JSONB)->>'EventType' AS eventtype
FROM system.eventlog
WHERE (info::JSONB)->>'EventType' IN ('client_connection_start','client_authentication_failed')
ORDER BY timestamp DESC LIMIT 20;
```
4. Verify integration with SIEM/log aggregator if applicable

---

### 3.4 Monitoring and Alerting in Place (Manual)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **CIS v8** | 8.2 Collect Audit Logs (IG1/2/3) |
| **CIS v7** | 6.2 Activate Audit Logging (IG1/2/3) |
| **Default** | Not configured — Prometheus endpoint available at `/_status/vars` on port 8080 |

**Quick Scan:**
```bash
echo 'Manual: Verify monitoring system is configured and alerting is active'
```

**Full Audit:**
1. Verify Prometheus/Datadog/equivalent is scraping CockroachDB metrics endpoint
2. Verify alerts for: node unavailability, under-replicated ranges, cert expiration (<30 days), disk usage >80%, clock offset >100ms, version mismatch
3. Verify DB Console is accessible and shows cluster health

---

## 4. User Access and Authorization

### 4.1 Restrict Access Using Host-Based Authentication (Manual)

| Field | Value |
|-------|-------|
| **Severity** | High |
| **CIS v8** | 3.3 Configure Data Access Control Lists (IG1/2/3); 4.4 Implement Firewall at App Layer (IG1/2/3); 6.6 Inventory and Control Auth Systems (IG2/3) |
| **CIS v7** | 14.6 Protect Information Through Access Control Lists (IG1/2/3) |
| **Default** | `host all root all cert-password` / `host all all all cert-password` / `local all all password` |

**Quick Scan:**
```sql
SHOW CLUSTER SETTING server.host_based_authentication.configuration;
-- FAIL if empty or equivalent to default (no IP restrictions)
```

**Full Audit:**
1. Review HBA for allowed network origins — rules should list specific IP/CIDR ranges
2. Final rule should be `host all all all reject` (default-deny)
3. FAIL if empty, `host all all all password`, or `trust` method present
4. Verify strong auth methods (cert, cert-password, cert-scram-sha-256, scram-sha-256)

---

### 4.2 Restrict and Secure Password Authentication (Manual)

| Field | Value |
|-------|-------|
| **Severity** | High |
| **CIS v8** | 5.2 Use Strong Authentication (IG1/2/3); 3.3 Implement Access Control (IG1/2/3); 6.6 Manage Authorization Systems (IG2/3) |
| **CIS v7** | 16.4 Encrypt or Hash Authentication Credentials (IG1/2/3) |
| **Default** | `password_encryption` defaults vary by version; HBA defaults to cert-password |

**Quick Scan:**
```sql
SHOW CLUSTER SETTING server.user_login.password_encryption;
-- Expected: scram-sha-256
```

**Full Audit:**
1. Inspect stored password hashes (⚠️ break-glass, authorized operators only):
```sql
SET allow_unsafe_internals = true;
SET bytea_output = 'escape';
SELECT username, "hashedPassword" FROM system.users WHERE "hashedPassword" IS NOT NULL;
SET allow_unsafe_internals = false;
-- SCRAM hashes show SCRAM-SHA-256$... prefix
```
2. Verify SCRAM-SHA-256 enforcement:
```sql
SHOW CLUSTER SETTING server.user_login.password_encryption;
SHOW CLUSTER SETTING server.user_login.upgrade_bcrypt_stored_passwords_to_scram.enabled;
```
3. Review HBA for password method entries — FAIL if broad rules allow password from unbounded origins

---

### 4.3 Secure the root User and Administrative Roles (Manual)

| Field | Value |
|-------|-------|
| **Severity** | High |
| **CIS v8** | 5.4 Restrict Administrator Privileges (IG1/2/3); 6.6 Manage Authorization Systems (IG2/3) |
| **CIS v7** | 4.3 Ensure Use of Dedicated Administrative Accounts (IG1/2/3) |
| **Default** | root has full cluster access with cert-password auth from any IP |

**Quick Scan:**
```sql
SHOW CLUSTER SETTING sql.log.user_audit;
-- Expected: includes 'root ALL'
```

**Full Audit:**
1. Verify root restricted in HBA to specific admin hosts with cert-only auth
2. Verify root activity audited via `sql.log.user_audit`
3. Verify limited admin roles exist for routine tasks
4. Count admin members:
```sql
SELECT member FROM [SHOW GRANTS ON ROLE admin] WHERE is_admin = true;
-- Should be minimal (1-2 accounts)
```

---

### 4.4 Centralize and Standardize User Management (Manual)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **CIS v8** | 5.1 Establish and Maintain an Inventory of Accounts (IG1/2/3); 6.6 Manage Authorization Systems (IG2/3) |
| **CIS v7** | 16.8 Disable Any Unassociated Accounts (IG1/2/3) |
| **Default** | Local database accounts only; OIDC/LDAP disabled |

**Quick Scan:**
```sql
SHOW CLUSTER SETTING server.oidc_authentication.enabled;
-- Expected: true
```

**Full Audit:**
1. Check OIDC enabled and provider URL configured
2. Check identity mapping: `SHOW CLUSTER SETTING server.identity_map.configuration;`
3. Check HBA for LDAP entries
4. Review local accounts — minimize to emergency access (root with cert)
5. Verify provisioning/deprovisioning process exists

---

## 5. Data Protection

### 5.1 Backups Are Encrypted (Manual)

| Field | Value |
|-------|-------|
| **Severity** | High |
| **CIS v8** | 3.11 Encrypt Sensitive Data at Rest (IG1/2/3); 4.1 Secure Configuration (IG1/2/3); 6.2 Establish Access Revoking Process (IG2/3) |
| **CIS v7** | 10.4 Ensure Protection of Backups (IG1/2/3); 13.10 Encrypt Sensitive Information at Rest (IG1/2/3) |
| **Default** | Backups NOT encrypted by default; EAR does NOT encrypt backups |

**Quick Scan:**
```sql
SELECT id, label, schedule_status, next_run FROM [SHOW SCHEDULES] WHERE label ILIKE '%backup%';
```

**Full Audit:**
1. Identify recent backups: `SHOW BACKUPS IN 's3://bucket/path?AUTH=...';`
2. Inspect backup options — verify `encryption_passphrase` or `kms` present
3. Validate storage-layer encryption (S3 SSE, GCS CMEK, Azure SSE)
4. Verify passphrases/keys NOT in plaintext scripts, service files, logs, or source code

---

### 5.2 Periodically Test Backup Recovery (Manual)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **CIS v8** | 11.3 Perform Automated Backup (IG1/2/3) |
| **CIS v7** | 10.4 Ensure Protection of Backups (IG1/2/3) |
| **Default** | No recovery testing by default |

**Quick Scan:**
```bash
echo 'Manual: Review backup testing logs and documentation'
```

**Full Audit:**
1. Request documentation of most recent recovery test — date, duration, results
2. Verify testing covers: full restore, PITR, RTO validation
3. Verify quarterly minimum frequency
4. Verify test environment separate from production

---

### 5.3 Multi-Region Data Localization (Manual)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **CIS v8** | 3.3 Configure Data Access Control Lists (IG1/2/3) |
| **CIS v7** | 14.4 Encrypt All Sensitive Information in Transit (IG1/2/3) |
| **Default** | No data localization by default |

**Quick Scan:**
```sql
SHOW REGIONS FROM DATABASE <database>;
-- N/A if single-region or no data residency requirements
```

**Full Audit:**
1. Check database regions, table locality (`REGIONAL BY ROW`), data placement (`SHOW RANGES`)
2. Verify zone constraints match regulatory requirements
3. Mark N/A if single-region with no data residency requirements

---

## 6. CockroachDB Settings

### 6.1 Certificate File Permissions and Validity (Automated)

| Field | Value |
|-------|-------|
| **Severity** | High |
| **CIS v8** | 3.3 Configure Data Access Control Lists (IG1/2/3) |
| **CIS v7** | 14.4 Encrypt All Sensitive Information in Transit (IG1/2/3) |
| **Default** | Depends on how certificates were deployed |

**Quick Scan:**
```bash
ls -l /var/lib/cockroach/certs/*.key | awk '{print $1}' | grep -v '^-rw-------' | wc -l
# Expected: 0
```

**Full Audit:**
1. Check key permissions: `ls -l /var/lib/cockroach/certs/*.key` — expected 0600, owned by cockroach
2. Check certificate expiry:
```bash
for cert in /var/lib/cockroach/certs/*.crt; do
  echo "Certificate: $cert"
  openssl x509 -in "$cert" -noout -dates
done
# Expected: > 90 days remaining
```
3. Verify cert chain: `openssl verify -CAfile ca.crt node.crt`

---

### 6.2 Sensitive Cluster Settings Are Redacted (Manual)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **CIS v8** | 3.11 Encrypt Sensitive Data at Rest (IG1/2/3) |
| **CIS v7** | 13.5 Manage Access Control for Remote Assets (IG1/2/3) |
| **Default** | Some settings auto-redacted; debug bundles not redacted by default |

**Quick Scan:**
```bash
echo 'Manual: Verify --redact flag used for debug bundles'
```

**Full Audit:**
1. Verify `cockroach debug zip --redact` is used for support bundles
2. Check logs for sensitive values: `grep -i 'password\|secret\|key\|token' logs/*.log`
3. Review `SHOW ALL CLUSTER SETTINGS;` for redacted values

---

### 6.3 Security Audit Logging Enabled (Manual)

| Field | Value |
|-------|-------|
| **Severity** | High |
| **CIS v8** | 8.2 Collect Audit Logs (IG1/2/3); 8.3 Ensure Adequate Audit Log Storage (IG1/2/3); 8.4 Ensure Logging Policies Are Enforced (IG2/3) |
| **CIS v7** | 6.2 Activate Audit Logging (IG1/2/3); 6.3 Ensure Audit Logs Are Reviewed Regularly (IG2/3) |
| **Default** | `sql.log.user_audit` empty; table-level audit disabled |

**Quick Scan:**
```sql
SHOW CLUSTER SETTING sql.log.user_audit;
SHOW CLUSTER SETTING sql.log.admin_audit.enabled;
-- FAIL if both empty/false
```

**Full Audit:**
1. Verify `sql.log.user_audit` non-empty (e.g., `ALL ALL` or role-specific)
2. Verify security sink includes SESSIONS, USER_ADMIN, PRIVILEGES, SENSITIVE_ACCESS with `auditable: true`
3. Verify `server.auth_log.sql_connections.enabled` = true
4. Test: execute statement as audited user, verify entry in `cockroach-security.log`

---

### 6.4 SQL Session Idle Timeouts Configured (Manual)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **CIS v8** | 4.3 Configure Automatic Session Locking (IG1/2/3) |
| **CIS v7** | 16.6 Maintain an Inventory of Accounts (IG1/2/3) |
| **Default** | `sql.defaults.idle_in_session_timeout` = `0s` (disabled) |

**Quick Scan:**
```sql
SHOW CLUSTER SETTING sql.defaults.idle_in_session_timeout;
-- Expected: non-zero (e.g., 15m0s)
```

**Full Audit:**
1. Check cluster-wide timeout (PCI DSS requires 15 minutes)
2. Check role-level timeouts:
```sql
SELECT rolname, rolconfig FROM pg_catalog.pg_roles
WHERE rolconfig IS NOT NULL AND rolconfig::text LIKE '%idle_in_session_timeout%';
```

---

### 6.5 OCSP Certificate Revocation Checking Enabled (Manual)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **CIS v8** | 3.10 Encrypt Sensitive Data in Transit (IG1/2/3); 5.2 Use Strong Authentication (IG1/2/3) |
| **CIS v7** | 16.7 Use Standard Hardening Configuration Templates (IG1/2/3); 14.4 Encrypt All Sensitive Information in Transit (IG1/2/3); 16.4 Encrypt or Hash Authentication Credentials (IG1/2/3) |
| **Default** | `security.ocsp.mode` = `off`; `security.ocsp.timeout` = `3s` |

**Quick Scan:**
```sql
SHOW CLUSTER SETTING security.ocsp.mode;
-- Expected: strict or lax (not off)
```

**Full Audit:**
1. Verify OCSP mode (strict recommended, lax acceptable):
```sql
SHOW CLUSTER SETTING security.ocsp.mode;
SHOW CLUSTER SETTING security.ocsp.timeout;
```
2. Verify certificates include OCSP responder URLs:
```bash
openssl x509 -in certs/client.crt -noout -ocsp_uri
```
3. Test OCSP query:
```bash
openssl ocsp -issuer certs/ca.crt -cert certs/client.crt \
  -url $(openssl x509 -in certs/client.crt -noout -ocsp_uri)
```
4. Check logs: `grep -i "ocsp" /var/lib/cockroach/logs/cockroach.log | tail -20`