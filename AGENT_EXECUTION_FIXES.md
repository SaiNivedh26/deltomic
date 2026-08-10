# Agent Execution Fixes - Complete Solution

## Issues Identified

From the screenshot and user feedback:

1. **Commands firing simultaneously** - `docker ps -a`, `sudo -n true`, `groups`, `id`, `whoami`, `systemctl status docker`, `docker ps` all showing "Executing..." at once
2. **Docker commands blocked** - Agent says "Docker commands aren't allowed" despite task being about Docker containers
3. **Irrelevant commands** - Running `groups`, `id`, `whoami` instead of focused Docker debugging
4. **Allowlist expansion not persisting** - `propose_execution_plan()` suggests expansion but never updates the database

## Root Causes

### 1. Parallel Execution
LangGraph's `create_agent` executes all tool calls in a single turn **in parallel**. The system prompt alone cannot prevent this - the LLM decides to call multiple tools, and the framework executes them all simultaneously.

### 2. Missing Commands in Allowlist
`ALLOWED_COMMANDS` in `config.py` only contained diagnostic commands (`ls`, `grep`, `find`, etc.). Docker, systemctl, snap, curl were all missing.

### 3. Allowlist Expansion Broken
The `propose_execution_plan()` tool called `expand_allowlist_if_needed()` which returned suggested commands, but these were **never persisted** to the `support_access_grants` table. The grant's `allowed_commands` remained unchanged.

### 4. Irrelevant Command Selection
The agent had no guidance to use task-specific information (like "Docker installed via snap") and defaulted to generic diagnostics.

## Solutions Implemented

### Fix 1: Sequential Execution Lock

**File:** `backend/worker_agent.py`

Added `_command_in_progress` flag to enforce sequential execution:

```python
_command_in_progress: bool = False

@tool
async def run_command(command: str) -> str:
    global _command_in_progress
    
    if _command_in_progress:
        return "BUSY: Another command is currently executing. Please wait for it to complete before running the next command. Execute commands ONE AT A TIME."
    
    _command_in_progress = True
    
    try:
        # ... execute command ...
    finally:
        _command_in_progress = False
```

**How it works:**
- When first command starts executing, sets `_command_in_progress = True`
- If LLM calls another command in the same turn, it gets "BUSY" response immediately
- Both results sent back to LLM
- LLM sees one succeeded, one got "BUSY"
- LLM retries the second command in the next turn
- **Result:** Commands execute sequentially, one at a time

### Fix 2: Expanded Default Allowlist

**File:** `backend/config.py`

Added Docker and common debugging commands to `ALLOWED_COMMANDS`:

```python
ALLOWED_COMMANDS = [
    # ... existing diagnostic commands ...
    "docker",
    "snap",
    "systemctl",
    "service",
    "curl",
    "wget",
    "journalctl",
    "ps",
    "top",
    "htop",
    "netstat",
    "ss",
    "ping",
    "ip",
    "ifconfig",
    "env",
    "export",
    "which",
    "whereis",
    "dpkg",
    "apt",
    "snap run",
]
```

### Fix 3: Auto-Allowlist Expansion Based on Task Context

**File:** `backend/worker_agent.py`

Added automatic allowlist expansion when sessions are created:

```python
# Auto-expand allowlist based on task context
task_lower = task_description.lower()
auto_expand_commands = []

if any(kw in task_lower for kw in ["docker", "container", "kubernetes", "k8s", "pod"]):
    auto_expand_commands.extend(["docker", "snap", "snap run", "systemctl", "journalctl"])

if any(kw in task_lower for kw in ["network", "dns", "firewall", "port", "connect"]):
    auto_expand_commands.extend(["netstat", "ss", "ping", "ip", "ifconfig", "curl", "wget"])

if any(kw in task_lower for kw in ["install", "package", "apt", "snap", "dpkg"]):
    auto_expand_commands.extend(["apt", "dpkg", "snap", "python3", "pip3"])

if any(kw in task_lower for kw in ["service", "systemd", "restart", "start", "stop"]):
    auto_expand_commands.extend(["systemctl", "service", "journalctl"])

if auto_expand_commands and grant_id:
    # Update grant's allowed_commands in database
    with get_cursor() as cur:
        cur.execute(
            "SELECT allowed_commands FROM support_access_grants WHERE id = %s",
            (grant_id,),
        )
        row = cur.fetchone()
        if row:
            current_cmds = row["allowed_commands"]
            if isinstance(current_cmds, str):
                current_cmds = json.loads(current_cmds)
            
            added = []
            for cmd in auto_expand_commands:
                if cmd not in current_cmds:
                    current_cmds.append(cmd)
                    added.append(cmd)
            
            if added:
                cur.execute(
                    """
                    UPDATE support_access_grants 
                    SET allowed_commands = %s, updated_at = now()
                    WHERE id = %s
                    """,
                    (json.dumps(current_cmds), grant_id),
                )
```

**How it works:**
- When task description contains "docker", automatically adds Docker commands to grant
- When task mentions "network", adds network debugging commands
- Persists changes to database immediately
- Broadcasts `allowlist_expanded` event to dashboard

### Fix 4: Persist Allowlist Expansion from Critique Agent

**File:** `backend/worker_agent.py`

Updated `propose_execution_plan()` to actually update the database:

```python
if expansion:
    # Actually persist the allowlist expansion to the database
    if grant_id:
        try:
            from backend.db import get_cursor
            import json
            
            with get_cursor() as cur:
                cur.execute(
                    "SELECT allowed_commands FROM support_access_grants WHERE id = %s",
                    (grant_id,),
                )
                row = cur.fetchone()
                if row:
                    current_cmds = row["allowed_commands"]
                    if isinstance(current_cmds, str):
                        current_cmds = json.loads(current_cmds)
                    
                    # Add new commands
                    for cmd in expansion:
                        if cmd not in current_cmds:
                            current_cmds.append(cmd)
                    
                    cur.execute(
                        """
                        UPDATE support_access_grants 
                        SET allowed_commands = %s, updated_at = now()
                        WHERE id = %s
                        """,
                        (json.dumps(current_cmds), grant_id),
                    )
```

### Fix 5: Updated System Prompt

**File:** `backend/worker_agent.py`

Enhanced system prompt with task-aware debugging guidance:

```
CRITICAL EXECUTION RULES:
1. Execute ONE command at a time. NEVER call multiple tools simultaneously.
2. Wait for the result of each command before calling the next one.
3. Keep track of what you've already executed - DO NOT repeat the same command.
4. After each command, analyze the output and decide the next step.
5. If a command fails, try a different approach - don't retry the same command.
6. ONLY run commands relevant to the specific issue. Don't run generic diagnostic commands.

HOW YOU WORK:
1. You ALREADY KNOW the customer's issue from the task description. Do NOT ask them to explain it again.
2. Start by acknowledging what you know about their issue and briefly state your approach.
3. If the user tells you something specific (like "Docker installed via snap"), USE THAT INFORMATION.
4. Execute ONE command, wait for result, interpret it, then decide next command.
5. Summarize what you found and what you did.

EXAMPLE BEHAVIOR (good):
User: "My container keeps restarting"
"I see you're having issues with a container restarting. Let me check what's happening with Docker."
[runs: docker ps -a]
[waits for result]
"I can see the container is in a restart loop. Let me check the logs to understand why."
[runs: docker logs <container-name> --tail 50]

EXAMPLE BEHAVIOR (bad - DO NOT DO THIS):
User: "My container keeps restarting"
[runs: whoami, id, groups, sudo -n true, docker ps] ← WRONG! Irrelevant commands!
```

### Fix 6: Updated list_available_commands Tool

**File:** `backend/worker_agent.py`

Now returns the grant's actual allowed commands from database, not just the static profile:

```python
@tool
def list_available_commands() -> str:
    """List all commands currently allowed for this session."""
    grant_id = _current_context.get("grant_id")
    if grant_id:
        try:
            from backend.db import get_cursor
            import json
            
            with get_cursor() as cur:
                cur.execute(
                    "SELECT allowed_commands FROM support_access_grants WHERE id = %s",
                    (grant_id,),
                )
                row = cur.fetchone()
                if row:
                    cmds = row["allowed_commands"]
                    if isinstance(cmds, str):
                        cmds = json.loads(cmds)
                    return "\n".join(cmds)
        except Exception as e:
            logger.error(f"Failed to get grant commands: {e}")
    
    # Fallback to profile-based allowlist
    profile = _current_context.get("profile_name")
    escalated = _current_context.get("escalated", False)
    commands = build_dynamic_allowlist(profile or "diagnostic", escalated)
    return "\n".join(commands)
```

## Files Modified

1. **`backend/config.py`** - Added Docker, systemctl, snap, curl, and other debugging commands to `ALLOWED_COMMANDS`

2. **`backend/worker_agent.py`** - Multiple changes:
   - Added `_command_in_progress` flag for sequential execution
   - Modified `run_command()` to check/set the flag and return "BUSY" if another command is running
   - Added auto-allowlist expansion based on task context in `execute_task_streaming()`
   - Updated `propose_execution_plan()` to persist allowlist changes to database
   - Updated `list_available_commands()` to return grant's actual commands
   - Enhanced system prompt with task-aware debugging guidance

## Expected Behavior After Fix

### Before:
```
Agent: "I'll investigate..."
[Simultaneously fires:]
  $ docker ps -a → Executing...
  $ sudo -n true → Executing...
  $ groups → Executing...
  $ id → Executing...
  $ whoami → Executing...
  $ systemctl status docker → Executing...
  $ docker ps → Executing...
  
Agent: "Docker commands aren't allowed right now..."
```

### After:
```
Agent: "I see you're having issues with a container restarting. Let me check what's happening with Docker."

[Auto-expands allowlist to include: docker, snap, systemctl, journalctl]

Agent: "First, let me check what containers are running."
[runs: docker ps -a]
[waits for result - other commands would get "BUSY" if attempted]

Agent: "I can see the container is in a restart loop. Let me check the logs."
[runs: docker logs <container> --tail 50]
[waits for result]

Agent: "The logs show the application is crashing due to a missing environment variable..."
```

## Testing

1. **Restart the main server:**
   ```bash
   cd /home/sai-nivedh-26/deltomic/agent-connect-remote
   source /home/sai-nivedh-26/deltomic/del/bin/activate
   uvicorn main:app --reload --port 8000
   ```

2. **Test sequential execution:**
   - Create a session with a Docker-related task
   - Observe that commands execute one at a time
   - Verify no "Executing..." overlap in dashboard

3. **Test allowlist expansion:**
   - Check logs for "Auto-expanded allowlist for grant {grant_id}: added [...]"
   - Verify Docker commands are now allowed
   - Check dashboard for `allowlist_expanded` event

4. **Test task-aware debugging:**
   - Agent should mention Docker specifically
   - Agent should run `docker ps` first, not generic commands
   - Agent should use user-provided information (like "installed via snap")

## Verification

All files verified with `ast.parse()` - syntax OK.

## Additional Notes

- The `_command_in_progress` flag is reset at the start of each new task in `execute_task_streaming()`, `worker_chat()`, and `execute_task_with_groq()`
- Command history (`_command_history`) is also cleared at task start to prevent false duplicate detection
- The auto-expansion only adds commands that aren't already in the allowlist
- All allowlist changes are logged and broadcast to the dashboard
