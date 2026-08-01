---
name: setting-up-local-cluster
description: Downloads and starts a local CockroachDB cluster for development using the official binary. Use when a developer needs a local CockroachDB instance, when no cluster is available, or when setting up a new development environment.
---

# Setting Up a Local CockroachDB Cluster

Guides you through downloading, installing, and starting a local CockroachDB cluster for development. Uses the official binary -- no Docker or external runtime dependencies required.

## When to Use This Skill

- Developer asks to "set up CockroachDB" or "start a local database"
- No CockroachDB cluster is reachable
- Developer wants to build an app with CockroachDB from scratch
- Setting up a new development environment

## Prerequisites

- macOS (Intel or Apple Silicon), Linux (Intel or ARM), or Windows (Intel)
- `curl` or `wget` available for downloading the binary
- ~500 MB disk space per node
- Ports 26257-26259 (SQL), 26357-26359 (RPC), and 8080-8082 (DB Console) available for a 3-node cluster

## Step 1: Detect Platform and Download

Detect the OS and architecture, then download the appropriate binary.

### Download URLs

Base URL: `https://binaries.cockroachdb.com/`

| OS | Architecture | Filename Pattern |
|----|-------------|-----------------|
| Linux | Intel (amd64) | `cockroach-v{VERSION}.linux-amd64.tgz` |
| Linux | ARM (arm64) | `cockroach-v{VERSION}.linux-arm64.tgz` |
| macOS | Intel (amd64) | `cockroach-v{VERSION}.darwin-10.9-amd64.tgz` |
| macOS | Apple Silicon (arm64) | `cockroach-v{VERSION}.darwin-11.0-arm64.tgz` |
| Windows | Intel (amd64) | `cockroach-v{VERSION}.windows-6.2-amd64.zip` |

Replace `{VERSION}` with the desired release (e.g., `25.4.9`). See [CockroachDB Releases](https://www.cockroachlabs.com/docs/releases/) for the latest GA version.

### Installation

```bash
# Example: macOS Apple Silicon, v25.4.9
curl -fsSL https://binaries.cockroachdb.com/cockroach-v25.4.9.darwin-11.0-arm64.tgz | tar xz
mkdir -p ~/.cockroachdb/bin
cp cockroach-v25.4.9.darwin-11.0-arm64/cockroach ~/.cockroachdb/bin/
export PATH="$HOME/.cockroachdb/bin:$PATH"
```

If `cockroach` is already on PATH, skip the download.

## Step 2: Start the Cluster

A 3-node cluster is recommended for development because it exercises replication, range distribution, leaseholder balancing, and survival goals -- core CockroachDB capabilities that a single node cannot demonstrate.

### 3-Node Cluster (Recommended)

```bash
# Start 3 nodes with separate SQL, RPC, and HTTP ports.
# Use $HOME instead of ~ in --store / --log-dir / --pid-file: tilde does not
# expand inside --flag=~/... in bash or zsh.
cockroach start --insecure --listen-addr=localhost:26357 --sql-addr=localhost:26257 \
  --http-addr=localhost:8080 --store=$HOME/.cockroachdb/data/node1 \
  --log-dir=$HOME/.cockroachdb/logs/node1 \
  --pid-file=$HOME/.cockroachdb/data/node1/cockroach.pid \
  --join=localhost:26357,localhost:26358,localhost:26359 --background

cockroach start --insecure --listen-addr=localhost:26358 --sql-addr=localhost:26258 \
  --http-addr=localhost:8081 --store=$HOME/.cockroachdb/data/node2 \
  --log-dir=$HOME/.cockroachdb/logs/node2 \
  --pid-file=$HOME/.cockroachdb/data/node2/cockroach.pid \
  --join=localhost:26357,localhost:26358,localhost:26359 --background

cockroach start --insecure --listen-addr=localhost:26359 --sql-addr=localhost:26259 \
  --http-addr=localhost:8082 --store=$HOME/.cockroachdb/data/node3 \
  --log-dir=$HOME/.cockroachdb/logs/node3 \
  --pid-file=$HOME/.cockroachdb/data/node3/cockroach.pid \
  --join=localhost:26357,localhost:26358,localhost:26359 --background

# Initialize the cluster (only needed on first start)
cockroach init --insecure --host=localhost:26357
```

### Single-Node (Lightweight)

For minimal resource usage when full cluster capabilities are not needed:

```bash
cockroach start-single-node --insecure --listen-addr=localhost:26257 \
  --http-addr=localhost:8080 --store=$HOME/.cockroachdb/data/node1 \
  --log-dir=$HOME/.cockroachdb/logs/node1 \
  --pid-file=$HOME/.cockroachdb/data/node1/cockroach.pid --background
```

## Step 3: Verify the Cluster

```bash
# Check SQL connectivity
cockroach sql --insecure --host=localhost:26257 -e "SELECT version();"

# Verify all nodes joined (3-node cluster)
cockroach node status --insecure --host=localhost:26257

# Check replication factor (should show num_replicas = 3)
cockroach sql --insecure --host=localhost:26257 \
  -e "SHOW ZONE CONFIGURATION FOR RANGE default;"
```

## Connection Details

| Property | Value |
|----------|-------|
| SQL URL | `postgresql://root@localhost:26257/defaultdb?sslmode=disable` |
| DB Console | `http://localhost:8080` |
| User | `root` (no password in insecure mode) |
| Database | `defaultdb` |

### Environment Variables for MCP Toolbox

```bash
export COCKROACHDB_HOST=localhost
export COCKROACHDB_PORT=26257
export COCKROACHDB_USER=root
export COCKROACHDB_PASSWORD=
export COCKROACHDB_DATABASE=defaultdb
export COCKROACHDB_SSLMODE=disable
```

## Stopping the Cluster

```bash
# Graceful shutdown via PID files
kill $(cat $HOME/.cockroachdb/data/node1/cockroach.pid) 2>/dev/null
kill $(cat $HOME/.cockroachdb/data/node2/cockroach.pid) 2>/dev/null
kill $(cat $HOME/.cockroachdb/data/node3/cockroach.pid) 2>/dev/null
```

## Destroying All Data

```bash
rm -rf $HOME/.cockroachdb/data $HOME/.cockroachdb/logs
```

## Air-Gapped / Restricted Environments

For environments without internet access:

1. Pre-download the binary on an allowed machine
2. Transfer to the target machine via approved channels
3. Place at `~/.cockroachdb/bin/cockroach` or any PATH location

## What a 3-Node Cluster Enables

| Capability | Single Node | 3-Node |
|-----------|-------------|--------|
| SQL execution | Yes | Yes |
| Replication (num_replicas=3) | No | Yes |
| Range distribution | No | Yes |
| Leaseholder balancing | No | Yes |
| Node failure simulation | No | Yes |
| `SHOW RANGES` with real distribution | No | Yes |
| Survival goals (`SURVIVE ZONE FAILURE`) | No | Yes |
| Contention between nodes | No | Yes |

## Safety Considerations

- The cluster runs in **insecure mode** (no TLS, no authentication) -- suitable for local development only.
- Data persists in `$HOME/.cockroachdb/data` across restarts.
- The binary and data are user-local (`~/.cockroachdb/`) -- no `sudo` or system modifications.
- A 3-node cluster uses approximately 750 MB of RAM total.

## References

- [Install CockroachDB](https://www.cockroachlabs.com/docs/stable/install-cockroachdb.html)
- [Start a Local Cluster](https://www.cockroachlabs.com/docs/stable/start-a-local-cluster.html)
- [CockroachDB Releases](https://www.cockroachlabs.com/docs/releases/)
- [cockroach start](https://www.cockroachlabs.com/docs/stable/cockroach-start.html)
- [cockroach init](https://www.cockroachlabs.com/docs/stable/cockroach-init.html)
