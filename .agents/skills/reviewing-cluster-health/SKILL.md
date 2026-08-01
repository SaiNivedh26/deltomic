---
name: reviewing-cluster-health
description: Performs a comprehensive health check of a CockroachDB cluster. Gathers deployment context first, then provides tier-appropriate diagnostics. Self-Hosted uses SQL against node-level system tables and CLI. Advanced/BYOC use Cloud Console and SQL with node visibility. Standard monitors provisioned compute and workload via Cloud Console. Basic monitors Request Unit consumption and connectivity. Use for daily checks, pre-maintenance validation, post-incident verification, or production readiness assessment.
compatibility: Self-Hosted requires SQL access with admin or VIEWCLUSTERMETADATA privilege. Advanced/BYOC require Cloud Console and SQL connectivity. Standard requires Cloud Console and SQL. Basic requires Cloud Console.
metadata:
  author: cockroachdb
  version: "2.0"
---

# Reviewing Cluster Health

Performs a comprehensive health check of a CockroachDB cluster. Before running diagnostics, this skill gathers deployment context to provide the right queries and tools for the operator's tier.

## When to Use This Skill

- Daily or shift-start operational health checks
- Before starting maintenance (Self-Hosted, Advanced, BYOC)
- After incidents to confirm recovery
- Verifying production readiness
- Monitoring capacity and performance

**For live query issues:** Use [triaging-live-sql-activity](../../cockroachdb-observability-and-diagnostics/triaging-live-sql-activity/SKILL.md).
**For background jobs:** Use [monitoring-background-jobs](../../cockroachdb-observability-and-diagnostics/monitoring-background-jobs/SKILL.md).
**For range analysis:** Use [analyzing-range-distribution](../../cockroachdb-observability-and-diagnostics/analyzing-range-distribution/SKILL.md).

---

## Step 1: Gather Context

### Required Context

| Question | Options | Why It Matters |
|----------|---------|----------------|
| **Deployment tier?** | Self-Hosted, Advanced, BYOC, Standard, Basic | Determines available diagnostics and operator responsibilities |
| **Reason for health check?** | Daily check, Pre-maintenance, Post-incident, Pre-upgrade | Prioritizes which dimensions to check first |

### Additional Context (by tier)

**If Self-Hosted:**

| Question | Options | Why It Matters |
|----------|---------|----------------|
| **Access available?** | SQL + CLI, SQL only | Determines which tools can be used |
| **Cloud provider?** | AWS, GCP, Azure, On-Premises | Affects infrastructure-level checks |
| **Kubernetes deployment?** | Yes (Operator, Helm, manual), No | Changes CLI commands and monitoring |
| **Node count and regions?** | e.g., 9 nodes, 3 regions | Sets expectations for query results |

**If Advanced or BYOC:**

| Question | Options | Why It Matters |
|----------|---------|----------------|
| **Cloud provider?** (BYOC only) | AWS, GCP, Azure | For infrastructure-level monitoring in your cloud account |

**If Standard:**

| Question | Options | Why It Matters |
|----------|---------|----------------|
| **Current provisioned vCPUs?** | Number | Context for compute utilization assessment |

**If Basic:** No additional context needed.

### Context-Driven Routing

| Tier | Go To |
|------|-------|
| Self-Hosted | [Self-Hosted Health Check](#self-hosted-health-check) |
| Advanced | [Advanced Health Check](#advanced-health-check) |
| BYOC | [BYOC Health Check](#byoc-health-check) |
| Standard | [Standard Health Check](#standard-health-check) |
| Basic | [Basic Health Check](#basic-health-check) |

---

## Self-Hosted Health Check

**Applies when:** Tier = Self-Hosted

Self-Hosted node-level health is read primarily through `cockroach node status` (CLI) and the DB Console. Cluster settings and jobs are read through public SQL (`SHOW ALL CLUSTER SETTINGS`, `SHOW JOBS`). The `crdb_internal` virtual tables for cluster topology, storage, and certificates are not for production use — see the [docs](https://www.cockroachlabs.com/docs/stable/crdb-internal) for the production-safe table list.

### Check 1: Node Liveness, Version, and Replication

```bash
cockroach node status --decommission --certs-dir=<certs-dir> --host=<any-live-node>
```

Key columns:
- `is_live` — `false` requires immediate investigation
- `is_draining`, `is_decommissioning`, `membership` — flag in-progress lifecycle operations
- `started_at` — compare across runs to spot flapping (node restarts)
- `build` — version per node; should be a single value (or two during a rolling upgrade)
- `ranges_underreplicated` — non-zero indicates ranges below the zone's `num_replicas`

For finer-grained range breakdown, use the DB Console **Replication** page.

### Check 2: Storage Capacity

No production-safe SQL view exposes per-store capacity. Use:
- DB Console **Overview** → **Storage** for per-node usage
- The Prometheus metric endpoint on each node: `curl -ks https://<node>:8080/_status/vars | grep '^capacity'` (`capacity`, `capacity_used`, `capacity_available`)

### Check 3: Certificate Expiration

No SQL view exposes node certificate expiration. Use one of:
- `cockroach cert list --certs-dir=<certs-dir>` to inspect certs locally on each node
- `openssl x509 -in <cert.crt> -noout -enddate` for a single cert file
- The Prometheus metric endpoint: `curl -ks https://<node>:8080/_status/vars | grep '^security_certificate_expiration_'` (UNIX-timestamp seconds; `node`, `ca`, `client_ca`, `ui_ca`)

Treat anything within 90 days as `EXPIRING_SOON`.

### Check 4: Critical Settings

```sql
SELECT variable, value FROM [SHOW ALL CLUSTER SETTINGS]
WHERE variable IN (
  'kv.rangefeed.enabled', 'sql.stats.automatic_collection.enabled',
  'server.time_until_store_dead', 'admission.kv.enabled',
  'cluster.preserve_downgrade_option'
) ORDER BY variable;
```

`gc.ttlseconds` is a zone-config parameter, not a cluster setting; check the effective value with `SHOW ZONE CONFIGURATION FOR ...` against the relevant table/database/range.

### Check 5: Consolidated Summary

The DB Console **Cluster Overview** page consolidates live/dead node count, version distribution, range counts, and storage. From the CLI:

```bash
cockroach node status --decommission --certs-dir=<certs-dir> --host=<any-live-node>
```

then aggregate the columns of interest in your shell. The cluster's logical version comes from SQL:

```sql
SELECT value AS cluster_version FROM [SHOW CLUSTER SETTING version];
```

**If reason = Pre-maintenance**, also check for running jobs:
```sql
WITH j AS (SHOW JOBS)
SELECT job_type, COUNT(*) FROM j WHERE status = 'running' GROUP BY job_type;
```

### Check 6: Production Readiness Assessment

Use when verifying a cluster is ready for production workloads or during periodic operational reviews.

```bash
# Node count, liveness, and locality diversity
cockroach node status --decommission --certs-dir=<certs-dir> --host=<any-live-node>
```

In the output, count rows with `is_live = true` (production wants ≥ 3) and check that `locality` shows multiple regions/zones.

```sql
-- Critical production settings check
SELECT variable, value,
  CASE
    WHEN variable = 'kv.rangefeed.enabled' AND value = 'true' THEN 'OK'
    WHEN variable = 'kv.rangefeed.enabled' AND value = 'false' THEN 'WARN: should be true for CDC'
    WHEN variable = 'sql.stats.automatic_collection.enabled' AND value = 'true' THEN 'OK'
    WHEN variable = 'sql.stats.automatic_collection.enabled' AND value = 'false' THEN 'WARN: should be true'
    WHEN variable = 'admission.kv.enabled' AND value = 'true' THEN 'OK'
    WHEN variable = 'admission.kv.enabled' AND value = 'false' THEN 'WARN: recommended for production'
    WHEN variable = 'cluster.preserve_downgrade_option' AND value != '' THEN 'INFO: finalization pending'
    ELSE 'OK'
  END AS assessment
FROM [SHOW ALL CLUSTER SETTINGS]
WHERE variable IN (
  'kv.rangefeed.enabled', 'sql.stats.automatic_collection.enabled',
  'admission.kv.enabled', 'cluster.preserve_downgrade_option',
  'server.time_until_store_dead'
) ORDER BY variable;

-- Enterprise license status (Self-Hosted only)
SELECT value AS organization FROM [SHOW CLUSTER SETTING cluster.organization];
```

See [production-readiness reference](references/production-readiness.md) for the full production readiness checklist.

---

## Advanced Health Check

**Applies when:** Tier = Advanced

Advanced clusters are dedicated single-tenant clusters managed by Cockroach Labs. You have node-level visibility via both Cloud Console and SQL.

### Cloud Console Checks

1. **Cluster Overview** — verify all nodes are live, check node count
2. **Metrics** — CPU utilization, QPS, P99 latency, storage utilization
3. **Alerts** — check for active alerts

### CLI + SQL Checks

```bash
# Node liveness, version, and replication status
cockroach node status --decommission --certs-dir=<certs-dir> --host=<any-live-node>
```

Look at `is_live`, `build`, and `ranges_underreplicated` per node.

```sql
-- Recent failed jobs
WITH j AS (SHOW JOBS)
SELECT job_type, status, COUNT(*) FROM j
WHERE status IN ('running', 'failed') AND created > now() - INTERVAL '24 hours'
GROUP BY job_type, status;
```

### Cloud API

```bash
curl -s -H "Authorization: Bearer $COCKROACH_API_KEY" \
  "https://cockroachlabs.cloud/api/v1/clusters/<cluster-id>" | jq '.state, .cockroach_version'
```

---

## BYOC Health Check

**Applies when:** Tier = BYOC

BYOC clusters are dedicated and run in your cloud account. You have the same CockroachDB visibility as Advanced, plus direct access to the underlying infrastructure.

### CockroachDB Health

Run all [Advanced Health Check](#advanced-health-check) steps.

### Cloud Provider Infrastructure Checks

**If AWS:**
```bash
aws ec2 describe-instance-status --filters "Name=tag:cockroach-cluster,Values=<cluster-name>"
```

**If GCP:**
```bash
gcloud compute instances list --filter="labels.cockroach-cluster=<cluster-name>"
```

**If Azure:**
```bash
az vm list --resource-group <rg> --query "[?tags.cockroachCluster=='<cluster-name>']"
```

### Additional BYOC Checks

- Verify VPC/network connectivity (PrivateLink, PSC, VPC Peering)
- Check IAM roles — CRL service account permissions still valid
- Review cloud provider monitoring for infrastructure-level anomalies

---

## Standard Health Check

**Applies when:** Tier = Standard

Standard is a multi-tenant managed service. There are no individual nodes to monitor — Cockroach Labs manages all infrastructure, replication, and capacity. Health checking focuses on your workload performance and provisioned compute.

### Cloud Console Checks

1. **Cluster Overview** — verify cluster state is `RUNNING`
2. **SQL Activity** — statement and transaction latency, error rates
3. **Storage** — current usage
4. **Compute** — provisioned vCPU utilization

### SQL Checks

```sql
-- Verify connectivity
SELECT 1;

-- Current version
SELECT version();

-- Recent failed jobs
WITH j AS (SHOW JOBS)
SELECT job_type, status, description FROM j
WHERE status = 'failed' AND created > now() - INTERVAL '24 hours';
```

### What to Monitor

- **P99 SQL latency** — track via Cloud Console Metrics
- **Error rates** — check for spikes in statement errors
- **Storage growth** — plan based on usage trends
- **Compute utilization** — increase provisioned vCPUs if utilization is consistently high

**Note:** Node-level visibility is not available on Standard. Use Cloud Console for all infrastructure health monitoring.

---

## Basic Health Check

**Applies when:** Tier = Basic

Basic is a serverless offering that auto-scales. There are no nodes or provisioned compute to monitor. Cockroach Labs manages all infrastructure. Health checking focuses on connectivity, consumption, and spending.

### Cloud Console Checks

1. **Cluster Overview** — verify state is `RUNNING`
2. **Request Units** — consumption rate and remaining budget
3. **Storage** — current usage (10 GiB included free)
4. **Spending Limits** — verify limits are configured to avoid unexpected charges

### SQL Checks

```sql
-- Verify connectivity
SELECT 1;

-- Current version
SELECT version();

-- Recent failed jobs
WITH j AS (SHOW JOBS)
SELECT job_type, status, description FROM j
WHERE status = 'failed' AND created > now() - INTERVAL '24 hours';
```

### What to Monitor

- **Request Unit (RU) consumption** — track via Cloud Console to stay within spending limits
- **Storage usage** — monitor growth relative to the 10 GiB free tier
- **Query efficiency** — optimize queries that consume excessive RUs
- **Cold start latency** — Basic clusters may scale to zero during inactivity; first connection after idle may have higher latency

---

## Safety Considerations

All checks in this skill are read-only. No data is modified.

- **Self-Hosted:** `cockroach node status` requires CLI access (or admin SQL privilege if you need to fall back to internal tables). Most node-level health queries have no production-safe SQL alternative.
- **Advanced/BYOC:** `cockroach node status` works the same way; certificate inspection is managed by Cockroach Labs.
- **Standard/Basic:** No node-level visibility by design — use the Cloud Console.

## Troubleshooting

| Issue | Tier | Fix |
|-------|------|-----|
| `cockroach node status` errors with permission denied | SH | Use a cert with admin or `VIEWCLUSTERMETADATA` |
| Node missing from `cockroach node status` output | SH | Check node process; verify `--join` address |
| Standard/Basic SQL doesn't expose node tables | STD/BAS | Expected — use Cloud Console |
| Cloud Console shows degraded | ADV/BYOC | Check Cloud status page; contact support |
| High RU consumption | BAS | Profile queries; set spending limits |
| Cloud API returns 401 | ADV/BYOC | Regenerate API key |
| High latency on first connection | BAS | Expected cold start after idle period |

## References

**Skill references:**
- [Production readiness checklist](references/production-readiness.md)

**Related skills:**
- [upgrading-cluster-version](../upgrading-cluster-version/SKILL.md)
- [managing-cluster-capacity](../managing-cluster-capacity/SKILL.md)
- [performing-cluster-maintenance](../performing-cluster-maintenance/SKILL.md)
- [monitoring-background-jobs](../../cockroachdb-observability-and-diagnostics/monitoring-background-jobs/SKILL.md)

**Official CockroachDB Documentation:**
- [Monitoring and Alerting](https://www.cockroachlabs.com/docs/stable/monitoring-and-alerting)
- [cockroach node status](https://www.cockroachlabs.com/docs/stable/cockroach-node)
- [Production Checklist](https://www.cockroachlabs.com/docs/stable/recommended-production-settings)
- [Cloud Console Monitoring](https://www.cockroachlabs.com/docs/cockroachcloud/cluster-overview-page)
- [Export Metrics (Advanced)](https://www.cockroachlabs.com/docs/cockroachcloud/export-metrics)
