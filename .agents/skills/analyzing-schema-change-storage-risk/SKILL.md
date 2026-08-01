---
name: analyzing-schema-change-storage-risk
description: Estimates storage requirements for CockroachDB online schema change backfills using SHOW RANGES WITH DETAILS, KEYS, INDEXES. Use before CREATE INDEX, ADD COLUMN with INDEX/UNIQUE, ALTER PRIMARY KEY, CREATE MATERIALIZED VIEW, CREATE TABLE AS, REFRESH, or SET LOCALITY on tables with large per-index footprints, to avoid mid-backfill disk exhaustion.
compatibility: Requires SQL access. SHOW RANGES WITH DETAILS computes span_stats on demand and is expensive on tables with many ranges; target specific tables. Mirrors official guidance at https://www.cockroachlabs.com/docs/stable/online-schema-changes#estimate-your-storage-capacity-before-performing-online-schema-changes.
metadata:
  author: cockroachdb
  version: "2.0"
---

# Analyzing Schema Change Storage Risk

Estimates the storage headroom needed to safely run online schema changes.
Mirrors the [official guidance](https://www.cockroachlabs.com/docs/stable/online-schema-changes#estimate-your-storage-capacity-before-performing-online-schema-changes):
some operations may temporarily require up to **3× the size of the affected
table or index** while the schema change is in flight.

For ongoing range-distribution monitoring, see
[analyzing-range-distribution](../analyzing-range-distribution/SKILL.md).

## When to Use This Skill

Run a quick estimate before issuing any of these operations on a table whose
indexes are large (multiple GB per index, or many ranges per index):

- `CREATE INDEX`
- `ADD COLUMN` with `INDEX` or `UNIQUE`
- `ALTER PRIMARY KEY`
- `CREATE MATERIALIZED VIEW`
- `CREATE TABLE AS`
- `REFRESH MATERIALIZED VIEW`
- `ALTER TABLE ... SET LOCALITY` (when the locality change rewrites data)

Tables whose indexes are small (kilobytes to a few megabytes) carry trivial
storage risk; estimation is unnecessary.

## Background

### How much temporary space does a backfill actually need?

The honest answer depends on the operation:

- **`CREATE INDEX` / `ADD COLUMN ... UNIQUE`**: needs roughly **1× the size of
  the new index** — the indexed columns plus the primary key columns, written
  into a fresh index span. This is typically a small fraction of the table.
  Worst-case headroom is bounded by the size of that one index.
- **`ALTER PRIMARY KEY`**: rewrites the primary index and any secondary indexes
  whose definitions depend on the old PK. Old data sticks around until GC, so
  peak on-disk usage during the change can approach the size of the table again.
- **All bulk-ingest backfills**: extra MVCC versions and pre-compaction SSTs
  add overhead until Pebble compacts and GC runs.

The official docs round these up into a single conservative recommendation:
plan for up to **3× the size of the affected table or index** as free space.
That figure is a safety bound, not a precise prediction. For most
`CREATE INDEX` operations the real cost is much smaller; for
`ALTER PRIMARY KEY` on a large table it is the right ballpark.

### What happens if the cluster runs out of disk mid-backfill?

Backfills bulk-ingest data via `AddSSTable`, which checks the per-store
remaining capacity before each ingestion. If the remaining fraction falls
below `kv.bulk_io_write.min_capacity_remaining_fraction` (default `0.05`,
i.e. 5%), the ingest is rejected with `InsufficientSpaceError`. Both the
legacy and declarative schema changers translate that error into a job pause
request, so the schema change halts rather than wedging the cluster. To
resume, free space (e.g. drop unused indexes, expand storage) and resume the
paused job.

This is a *reactive* safety net, not a planning tool — by the time it fires,
foreground writes on the affected store may already be unhealthy.

## Estimating Capacity

### Step 1 — Check free space per store

The minimum free space across stores is what bounds the schema change, not the
total cluster free space (replicas are spread across nodes).

No production-safe SQL view exposes per-store capacity. Use the DB Console
**Overview** → **Storage** page (sorts per-store usage), or scrape the
per-node Prometheus endpoint and look at the smallest `capacity_available`:

```bash
curl -ks https://<node>:8080/_status/vars | grep -E '^capacity( |_used|_available)'
```

### Step 2 — Estimate the affected table/index size

Use the docs-recommended form of `SHOW RANGES`:

```sql
SHOW RANGES FROM TABLE <table> WITH DETAILS, KEYS, INDEXES;
```

The output includes one row per range, with `range_size_mb` and `index_name`.
Aggregate by index for the per-index totals that matter for capacity planning:

```sql
WITH r AS (SHOW RANGES FROM TABLE <table> WITH DETAILS, KEYS, INDEXES)
SELECT
  index_name,
  COUNT(*)                              AS range_count,
  ROUND(SUM(range_size_mb), 2)          AS index_size_mb,
  ROUND(SUM(range_size_mb) / 1024, 2)   AS index_size_gb
FROM r
GROUP BY index_name
ORDER BY index_size_mb DESC;
```

### Step 3 — Compare against the operation

| Operation                                   | Conservative free-space target (per store)                                  |
|---------------------------------------------|-----------------------------------------------------------------------------|
| `CREATE INDEX` / `ADD COLUMN ... UNIQUE`    | Up to 3× the size of the *new* index (its indexed + PK columns).            |
| `ALTER PRIMARY KEY`                          | Up to 3× the size of the *table* (sum of the relevant indexes from step 2). |
| `CREATE MATERIALIZED VIEW` / `CREATE TABLE AS` | Up to 3× the expected size of the materialized result.                   |

The new index does not exist yet, so estimate it from a comparable existing
index (e.g. one on similarly typed columns) or from the source columns'
contribution to the primary index.

If the smallest free-space figure from step 1 is well above the target, the
operation is safe to run. If it is close, free space first (drop unused
indexes, expand storage) before issuing the DDL.

## Operational Notes

- **`SHOW RANGES ... WITH DETAILS` is expensive.** It computes span statistics
  on demand. Always target a specific table, never run it cluster-wide, and
  prefer maintenance windows on tables with thousands of ranges.
- **Watch the job, not just disk.** If a backfill pauses with
  `InsufficientSpaceError`, free disk on the affected store and resume the
  paused schema change job. Check with:
  ```sql
  WITH j AS (SHOW JOBS)
  SELECT job_id, status, error
  FROM j
  WHERE job_type = 'SCHEMA CHANGE' AND status = 'paused';
  ```
- **Drop unused indexes first.** Often the cheapest way to free headroom
  before a large backfill is to drop indexes that
  `crdb_internal.index_usage_statistics` shows are unused (this is one of the
  12 production-safe `crdb_internal` views, per the
  [docs](https://www.cockroachlabs.com/docs/stable/crdb-internal)).
- **Statistics lag.** `range_size_mb` is approximate and can lag actual disk
  usage; treat estimates as conservative ballparks, not exact figures.

## References

- [Online Schema Changes — Estimate your storage capacity](https://www.cockroachlabs.com/docs/stable/online-schema-changes#estimate-your-storage-capacity-before-performing-online-schema-changes)
- [SHOW RANGES](https://www.cockroachlabs.com/docs/stable/show-ranges.html)

## Related Skills

- [analyzing-range-distribution](../analyzing-range-distribution/SKILL.md) — range count, leaseholder placement, fragmentation
