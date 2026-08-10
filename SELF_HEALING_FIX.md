# Self-Healing Dashboard Fix - Session ID Issue

## Problem

The self-healing dashboard was showing "Analyzed 2 sessions" but no stats were displayed. The root cause was that tool calls were being logged to `tool_call_logs` table with `session_id = NULL`, so the self-healing analysis couldn't find any tool calls for the sessions.

## Root Cause Analysis

1. **Sessions were being created** in `session_history` table with proper IDs
2. **Tool calls were being counted** in `session_history.tool_calls_count`
3. **But individual tool calls** in `tool_call_logs` had `session_id = NULL`
4. **Self-healing queries** look for tool calls by session_id, so they found nothing

### Why session_id was NULL

The `/task/stream` endpoint calls `execute_task_streaming()` which has an `email` parameter. When email is provided:
- A tenant is created/retrieved
- A session is created with a session_id
- The session_id is set in `_current_context`
- Tool calls are logged with that session_id

**But** the `/task/stream` endpoint was NOT passing the email parameter, so:
- No session was created
- session_id remained NULL
- Tool calls were logged with session_id = NULL

## Solution

### 1. Added email field to TaskRequest model

**File:** `agent-connect-remote/main.py`

```python
class TaskRequest(BaseModel):
    task_description: str
    grant_id: str
    agent_id: str
    email: str = ""  # Added this line
```

### 2. Pass email to execute_task_streaming

**File:** `agent-connect-remote/main.py`

```python
task_id, _ = await execute_task_streaming(
    task_description=req.task_description,
    grant_id=req.grant_id,
    agent_id=req.agent_id,
    email=req.email,  # Added this line
)
```

### 3. Send email from agent.html

**File:** `static/agent.html`

Made `sessionData` a global variable (was local to `loadContext()`):

```javascript
let taskContext = "";
let sessionData = null;  // Added this line

async function loadContext() {
  // ...
  sessionData = await sessionResp.json();  // Changed from const to global
  // ...
}
```

Updated the task/stream call to include email:

```javascript
const startResp = await fetch(`${BACKEND_URL}/task/stream`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    task_description: args.task_description,
    grant_id: GRANT_ID,
    agent_id: AGENT_ID,
    email: sessionData?.email || "",  // Added this line
  }),
});
```

### 4. Send email from test_agent.html

**File:** `static/test_agent.html`

For testing purposes, send a test email:

```javascript
body: JSON.stringify({
  task_description: args.task_description,
  grant_id: "test-grant-id",
  agent_id: "test-agent-id",
  email: "test@example.com",  // Added this line
}),
```

## Verification

After these changes:

1. **New sessions** will have proper session_ids
2. **Tool calls** will be logged with the correct session_id
3. **Self-healing analysis** will find the tool calls and detect errors
4. **Dashboard stats** will display correctly

### Test the fix

1. Restart the main server:
   ```bash
   cd /home/sai-nivedh-26/deltomic/agent-connect-remote
   source /home/sai-nivedh-26/deltomic/del/bin/activate
   uvicorn main:app --reload --port 8000
   ```

2. Create a new session through the agent

3. Check tool_call_logs:
   ```bash
   cd /home/sai-nivedh-26/deltomic/agent-connect-remote
   source /home/sai-nivedh-26/deltomic/del/bin/activate
   python3 -c "
   from backend.db import get_cursor
   with get_cursor() as cur:
       cur.execute('SELECT COUNT(*) as count FROM tool_call_logs WHERE session_id IS NOT NULL')
       result = cur.fetchone()
       print(f'Tool calls WITH session_id: {result[\"count\"]}')
   "
   ```

4. Run self-healing analysis on the new session

5. Check dashboard - stats should now display

## Files Modified

1. `/home/sai-nivedh-26/deltomic/agent-connect-remote/main.py`
   - Added `email` field to `TaskRequest` model
   - Pass `email` to `execute_task_streaming()`

2. `/home/sai-nivedh-26/deltomic/static/agent.html`
   - Made `sessionData` a global variable
   - Send `email` in task/stream request

3. `/home/sai-nivedh-26/deltomic/static/test_agent.html`
   - Send test email in task/stream request

## Impact

- **Existing sessions** with NULL session_id in tool_call_logs will not be affected
- **New sessions** will have proper session tracking
- **Self-healing dashboard** will work correctly for new sessions
- **No breaking changes** - email is optional (defaults to "")
