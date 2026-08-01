---
name: benchmarking-transaction-patterns
description: Guides benchmarking and comparing explicit multi-statement transactions versus single-statement CTE transactions in CockroachDB, with fair test methodology, contention analysis, and performance interpretation. Use when comparing transaction formulations, benchmarking CockroachDB workloads under contention, investigating retry pressure, or deciding whether to rewrite multi-step application flows into single SQL statements.
compatibility: "CockroachDB >= 22.1. Requires SQL access and a test cluster for benchmark execution. Do not run benchmarks against production workloads."
metadata:
  author: cockroachdb
  version: "1.0"
---

# Benchmarking Transaction Patterns

Guides users through benchmarking, explaining, and comparing two formulations of the same transactional business workflow in CockroachDB: explicit multi-statement transactions versus single-statement CTE transactions. Focuses on performance under contention, fair test methodology, and result interpretation.

**Complement to design skills:** For general transaction design principles, see [designing-application-transactions](../designing-application-transactions/SKILL.md). For SQL syntax and query patterns, see [cockroachdb-sql](../../cockroachdb-query-and-schema-design/cockroachdb-sql/SKILL.md).

## Core Concept

Under contention, the transaction formulation itself is a primary performance lever. The **explicit model** (multi-statement `BEGIN`/`COMMIT`) keeps the transaction open across round trips, widening the contention window. The **CTE model** (single-statement) collapses the same logic into one atomic statement, reducing transaction duration and retries.

### Explicit Transaction Model

```sql
BEGIN;
SELECT balance FROM accounts WHERE id = $1;
-- Application decides whether transfer is allowed
UPDATE accounts SET balance = balance - $2 WHERE id = $1;
UPDATE accounts SET balance = balance + $2 WHERE id = $3;
INSERT INTO transfers (from_acct, to_acct, amount, created_at)
VALUES ($1, $3, $2, now());
COMMIT;
```

### CTE Transaction Model

CockroachDB rejects multiple mutations of the same table in a single statement by default (`sql.multiple_modifications_of_table.enabled`), so the debit and credit are folded into one `UPDATE` using `CASE`.

```sql
WITH funded AS (
  SELECT 1 FROM accounts WHERE id = $1 AND balance >= $2
), upd AS (
  UPDATE accounts
  SET balance = CASE WHEN id = $1 THEN balance - $2 ELSE balance + $2 END
  WHERE id IN ($1, $3) AND EXISTS (SELECT 1 FROM funded)
  RETURNING id
), ins AS (
  INSERT INTO transfers (from_acct, to_acct, amount, created_at)
  SELECT $1, $3, $2, now() WHERE (SELECT count(*) FROM upd) = 2
  RETURNING id
)
SELECT id FROM ins;
```

## Steps

### 1. Prepare the Benchmark Environment

Set up a dedicated test database and schema. Do not mix benchmark workloads with other traffic.

```sql
CREATE DATABASE IF NOT EXISTS bankbench;
USE bankbench;

CREATE TABLE accounts (
  id INT PRIMARY KEY,
  balance DECIMAL(18,2) NOT NULL DEFAULT 0
);

CREATE TABLE transfers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  from_acct INT NOT NULL,
  to_acct INT NOT NULL,
  amount DECIMAL(18,2) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 2. Seed the Test Data

Use multi-row UPSERT for efficient seeding. Single-row inserts distort setup cost.

```sql
INSERT INTO accounts (id, balance)
SELECT generate_series(1, 10000), 1000.00
ON CONFLICT (id) DO UPDATE SET balance = 1000.00;
```

### 3. Run the Explicit Transaction Benchmark

Execute with realistic concurrency. Example using `pgbench` (PostgreSQL-compatible):

```bash
# Create a pgbench script file: explicit_transfer.sql
# \set from_id random(1, 10000)
# \set to_id random(1, 10000)
# \set amount 10.00
# BEGIN;
# SELECT balance FROM accounts WHERE id = :from_id;
# UPDATE accounts SET balance = balance - :amount WHERE id = :from_id;
# UPDATE accounts SET balance = balance + :amount WHERE id = :to_id;
# INSERT INTO transfers (from_acct, to_acct, amount, created_at) VALUES (:from_id, :to_id, :amount, now());
# COMMIT;

pgbench -n -c 64 -j 8 -T 120 -f explicit_transfer.sql \
  "postgresql://root@localhost:26257/bankbench?sslmode=disable"
```

Record throughput (tps), retries, p50/p95/p99 latency, max latency, and failures.

### 4. Reset Between Runs for Fair Comparison

For a fair benchmark, reset account balances between explicit and CTE runs so table size, index size, and account state remain comparable.

```sql
UPDATE accounts SET balance = 1000.00;
```

### 5. Run the CTE Transaction Benchmark

Execute with the same concurrency, duration, and parameters as the explicit run:

```bash
# Create a pgbench script file: cte_transfer.sql containing the CTE query above
pgbench -n -c 64 -j 8 -T 120 -f cte_transfer.sql \
  "postgresql://root@localhost:26257/bankbench?sslmode=disable"
```

### 6. Compare Results

Always compare these metrics side by side:

| Metric             | What to Look For                                                 |
|--------------------|------------------------------------------------------------------|
| Throughput (txn/s) | Higher is better; CTE typically sustains better under contention |
| Total retries      | CTE often reduces to near-zero                                   |
| p50 latency        | Median transaction time                                          |
| p95 latency        | Tail latency under moderate contention                           |
| p99 latency        | Worst-case tail; explicit model often shows spikes               |
| Max latency        | Outlier behavior                                                 |
| Failures           | Non-retryable errors                                             |

### 7. Validate Benchmark Integrity

Before interpreting results, verify the benchmark ran cleanly:

```sql
-- Confirm expected transfer volume
SELECT COUNT(*) AS total_transfers FROM transfers;
```

```bash
# Check node liveness and start times (no node restarts mid-benchmark)
cockroach node status --certs-dir=<certs-dir>     # or --insecure for an insecure cluster
```

## Benchmark Reference Results

In a reported high-contention run comparing the two models:

| Metric          | Explicit    | CTE           | Change |
|-----------------|-------------|---------------|--------|
| Throughput      | 591.1 txn/s | 1,035.1 txn/s | +75.1% |
| Wall time       | 216.5s      | 123.7s        | -42.9% |
| Average latency | 202.2 ms    | 111.3 ms      | -45.0% |
| Total retries   | 2,270,977   | 0             | -100%  |

Extended runs preserved the same directional result at higher total volume, with the explicit model continuing to accumulate retries and occasional failures while the CTE model stayed at zero retries and zero failures.

### Impact Summary

| Dimension                    | Explicit Multi-Statement            | Single-Statement CTE    |
|------------------------------|-------------------------------------|-------------------------|
| Round trips                  | Multiple client/server interactions | Single request          |
| Transaction lifetime         | Longer                              | Shorter                 |
| Client retry complexity      | Higher                              | Lower                   |
| Atomic invariant enforcement | Spread across statements/app logic  | Contained in SQL        |
| Expected throughput          | Lower under contention              | Higher under contention |
| Client-visible retries       | More likely                         | Often reduced           |

## Decision Guidance

### Prefer the Explicit Pattern When

- The business workflow truly cannot be expressed cleanly in one SQL statement
- Readability or staged business logic matters more than peak throughput
- The contention level is low enough that retry amplification is not the dominant cost

### Prefer the CTE Pattern When

- The workflow is contention-heavy
- The operation is naturally atomic
- The application currently performs read-decide-write across multiple statements
- The main goal is higher throughput, lower retries, and more stable p95/p99 latency

## Fair Benchmark Rules

1. **Reset between runs** for fair comparison so balances, table size, and index size stay consistent
2. **Treat no-reset runs as a demo**, not an apples-to-apples benchmark
3. **Use `--batch-size=1`** when you want one business unit of work at a time for clean comparison
4. **Compare the right metrics** — always include throughput, retries, p50, p95, p99, max latency, and failures
5. **Use multi-row UPSERT for seeding** — single-row seeding distorts setup cost

## Common Misconceptions

- **"CTE always wins"** — Only when the workflow is contention-sensitive and expressible as a single atomic statement.
- **"SQL Activity showing waiting means CTE failed"** — CTE reduces but does not eliminate contention. Compare throughput, tail latency, and retry profile.
- **"Single-statement means no contention"** — CTE narrows the contention window but does not eliminate it.

## Safety Considerations

- Run benchmarks on dedicated test clusters, not production
- Reset data between runs for fair comparison
- Monitor cluster health during benchmark execution
- Use realistic but not destructive concurrency levels
- Validate that benchmark results transfer to your specific workload before making production changes

## References

- [CockroachDB Transactions Documentation](https://www.cockroachlabs.com/docs/stable/transactions)
- [Advanced Client-Side Transaction Retries](https://www.cockroachlabs.com/docs/stable/advanced-client-side-transaction-retries)
- [Performance Best Practices](https://www.cockroachlabs.com/docs/stable/performance-best-practices-overview)
- [Comparing Multi-Statement vs Single-Statement Transactions](https://andrewdeally.medium.com/comparing-multi-statement-vs-single-statement-transactions-for-account-transfers-in-sql-09190b116e64)
- [Set-Based Operations with CockroachDB](https://andrewdeally.medium.com/set-based-operations-with-cockroachdb-c9f371992dc7)
- [Deep Dive into Transaction Retry Failures](https://www.mindfulchase.com/explore/troubleshooting-tips/databases/deep-dive-into-transaction-retry-failures-in-cockroachdb-root-causes-and-fixes.html)
- [Troubleshooting CockroachDB Performance](https://www.mindfulchase.com/explore/troubleshooting-tips/databases/troubleshooting-cockroachdb-performance-in-enterprise-deployments.html)
- [CockroachDB Transaction Demo](https://github.com/cockroachdb/cockroach-transaction-demo)
- [CockroachDB Best Practices & Anti-Patterns Demo](https://github.com/viragtripathi/cockroachdb-best-practices-demo) -- Demos 1-2 show retry patterns and contention scaling under concurrency
