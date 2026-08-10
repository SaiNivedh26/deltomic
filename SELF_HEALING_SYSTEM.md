# DELTOMIC Self-Healing & Session Management System

## Overview

This document explains how the embedding, agent learning, and self-healing systems work in DELTOMIC, along with the new automatic session end detection and email confirmation features.

---

## 1. Current Embedding & Agent Learning System

### How Embeddings Work

**Location:** `backend/vector_store.py`

**Process:**
1. When a session ends, the system creates a summary text containing:
   - Issue category
   - Session summary
   - Commands executed (first 5)

2. This text is sent to Amazon Titan Embeddings v2 (1024 dimensions) via AWS Bedrock

3. The resulting embedding vector is stored in the `session_embeddings` table with:
   - Session ID
   - Tenant ID
   - Embedding vector (1024 dimensions)
   - Content text (original summary)
   - Issue category
   - Resolution status

**Purpose:**
- Find similar past sessions/issues using cosine similarity
- Identify top issues this week
- Recommend solutions based on past successful resolutions

**Example Query:**
```python
# Find sessions similar to "high CPU usage"
similar = find_similar_sessions("high CPU usage", limit=5)
# Returns: list of sessions with similarity scores
```

### How Agent Learning Works

**Location:** `backend/insights_engine.py`

**Process:**
1. **Batch Insight Collection** (`collect_weekly_issue_insights()`):
   - Analyzes last 7 days of sessions
   - Groups by issue category
   - Counts occurrences
   - Creates batch insights in `batch_insights` table

2. **Learning Generation** (`generate_learnings_from_sessions()`):
   - Analyzes resolution rates per issue category
   - If resolution rate >= 80%: Creates high-confidence learning
     - Example: "For 'disk_full' issues, standard diagnostics resolve 85% of cases"
   - If resolution rate < 50%: Creates low-confidence learning
     - Example: "'network_timeout' issues have low resolution rate (40%). Consider escalating faster"
   - Stores in `agent_learnings` table with confidence score

3. **Learning Application** (`get_relevant_learnings()`):
   - When a new session starts with an issue category
   - Retrieves relevant learnings sorted by confidence
   - Can inject into agent's system prompt for better reasoning

**Example Learning:**
```
Category: disk_full
Text: "For 'disk_full' issues, the standard diagnostic approach (avg 4.2 tool calls) 
       resolves 85% of cases. Prioritize read-only diagnostics first, then targeted remediation."
Confidence: 0.85
Times Applied: 12
```

---

## 2. Self-Healing System (NEW)

### Overview

The self-healing system automatically detects errors during session execution, analyzes patterns, suggests corrections, and stores learnings for future sessions.

### Location

**Main Module:** `backend/self_healing.py`

### How It Works

#### Step 1: Error Detection

When a session ends (or manually triggered), the system:
1. Retrieves all tool execution logs for the session
2. Identifies failed commands or errors
3. Classifies errors into categories:
   - `permission_error`: Access denied, permission issues
   - `not_found_error`: File/path not found
   - `command_not_found`: Command not installed
   - `timeout_error`: Operation timed out
   - `network_error`: Connection issues
   - `syntax_error`: Invalid command syntax
   - `unknown_error`: Other errors

**Code:**
```python
errors = detect_error_patterns(session_id, tool_logs)
# Returns: list of error dicts with type, message, command, timestamp
```

#### Step 2: Pattern Classification

Each error is classified and stored with:
- Error type (from classification above)
- Original error message
- Command that failed
- Timestamp

#### Step 3: Memory Lookup

The system searches `agent_learnings` for similar past errors:
```python
similar_learnings = get_similar_error_learnings(error_type, command)
```

This retrieves past error-correction pairs from the `agent_learnings` table where:
- `issue_category` = `error_{error_type}`
- Learning text contains similar commands

#### Step 4: Correction Suggestion

Based on memory lookup:
- **If similar learning found**: Use past correction with confidence score
- **If no learning found**: Generate generic fix based on error type

**Generic Fixes:**
```python
fixes = {
    "permission_error": "Check file permissions or run with elevated privileges",
    "not_found_error": "Verify the path exists or check for typos",
    "command_not_found": "Ensure the command is installed and in PATH",
    "timeout_error": "Break operation into smaller steps",
    "network_error": "Check network connectivity and retry",
    "syntax_error": "Review command syntax and correct errors",
}
```

#### Step 5: Learning Storage

Each error-correction pair is stored as a new learning:
```python
store_error_learning(
    session_id=session_id,
    error_type="permission_error",
    error_message="Permission denied: /var/log/app.log",
    correction_applied="Run with sudo or check file ownership",
    success=True/False
)
```

This creates a learning in `agent_learnings` with:
- `issue_category`: `error_permission_error`
- `learning_text`: Contains error + correction + result
- `confidence`: 0.8 if successful, 0.3 if failed
- `source_session_ids`: [session_id]

#### Step 6: Batch Insight Creation

Creates a batch insight in `batch_insights` table:
```python
create_batch_insight(
    insight_type="error_patterns",
    title=f"Detected {len(errors)} errors in session",
    description="Error types: permission_error, timeout_error",
    data={
        "total_errors": 5,
        "error_types": ["permission_error", "timeout_error"],
        "most_common_error": "permission_error"
    }
)
```

### Self-Healing Loop Visualization

The dashboard shows the 5-step process:

```
┌─────────────────────────────────────────────────────────┐
│ 1. Error Detection                                       │
│    Scanning tool execution logs for failures            │
├─────────────────────────────────────────────────────────┤
│ 2. Pattern Classification                                │
│    Categorizing errors (permission, timeout, etc.)      │
├─────────────────────────────────────────────────────────┤
│ 3. Memory Lookup                                         │
│    Searching agent learnings for similar corrections    │
├─────────────────────────────────────────────────────────┤
│ 4. Correction Suggestion                                 │
│    Generating fix recommendations                       │
├─────────────────────────────────────────────────────────┤
│ 5. Learning Storage                                      │
│    Storing error-correction pairs for future use        │
└─────────────────────────────────────────────────────────┘
```

### Dashboard Integration

**Location:** `dashboard/static/dashboard.html` (Self-Healing page)

**Features:**
- Stats cards: Errors detected, corrections applied, learnings generated, success rate
- Self-healing loop visualization (5 steps)
- Error patterns chart (aggregated error types)
- Self-healing history (recent analyses)
- "Analyze All Sessions" button to trigger batch analysis

**API Endpoints:**
```
GET  /dashboard/api/self-healing/history     # Get healing history
GET  /dashboard/api/self-healing/learnings   # Get error learnings
POST /dashboard/api/self-healing/analyze/{session_id}  # Analyze specific session
```

---

## 3. Automatic Session End Detection (NEW)

### Overview

When a user leaves a Google Meet meeting, the system automatically:
1. Detects meeting end via Recall webhook
2. Finalizes the session (stores traces, embeddings)
3. Runs self-healing analysis
4. Sends confirmation email to customer
5. Revokes access grants

### Location

**Main Module:** `backend/meeting_end_handler.py`

### How It Works

#### Step 1: Recall Webhook

Recall.ai sends a webhook when meeting ends:
```
POST /webhook/recall
{
  "event": "meeting_ended",
  "bot_id": "recall-bot-123",
  "meeting_id": "meet-abc-456"
}
```

#### Step 2: Find Active Session

System finds the active session by bot_id:
```python
for agent_id, session_data in _active_sessions.items():
    if session_data.get("bot_id") == bot_id:
        # Found the session
        break
```

#### Step 3: Handle Meeting End

Calls `handle_meeting_end(agent_id, session_data)` which:

1. **Retrieves session details** from `session_history` table
2. **Gets tool logs** for self-healing analysis
3. **Runs self-healing loop** (detects errors, stores learnings)
4. **Finalizes session**:
   - Updates `session_history` with summary, resolution status
   - Stores conversation traces
   - Stores tool execution traces
   - Creates session embedding
   - Broadcasts "session_finalized" event
5. **Cleans up meet session**:
   - Revokes access grant
   - Broadcasts "session_cleanup_complete" event
6. **Sends confirmation email** (see below)
7. **Broadcasts "session_ended" event** to dashboard

#### Step 4: Email Confirmation

**Function:** `send_session_confirmation_email()`

**Email Content:**
```
Subject: Session Complete - Resolved

Hi John,

Your support session with Deltomic AI has concluded.

Session Details:
- Issue: High CPU usage on production server
- Status: ✅ Resolved
- Session ID: abc-123-def

Summary: Identified and killed runaway process. CPU usage normalized.

Self-Healing Analysis:
- Errors detected: 2
- Corrections suggested: 2
- Learnings stored for future improvement: 2

Error Types Encountered:
  • Permission Error
  • Timeout Error

If your issue is not resolved or you need further assistance, please don't hesitate to reach out again.

Best regards,
Deltomic AI Support Team
```

**Configuration:**
```python
# TODO: Move to environment variables
smtp_server = "smtp.gmail.com"
smtp_port = 587
smtp_user = "your-email@gmail.com"
smtp_password = "your-app-password"
from_email = "deltomic-support@example.com"
```

### Manual Session End

You can also manually end a session via API:
```
POST /sessions/{agent_id}/end
```

This triggers the same cleanup flow as the Recall webhook.

---

## 4. Integration Points

### Session Lifecycle Flow

```
1. User joins Meet → Agent spawned
2. Agent executes commands → Tool logs stored
3. User leaves Meet → Recall webhook fires
4. handle_meeting_end() triggered:
   a. Retrieve session + tool logs
   b. Run self-healing analysis
   c. Finalize session (traces, embeddings)
   d. Cleanup (revoke access)
   e. Send confirmation email
   f. Broadcast events to dashboard
5. Dashboard updates in real-time
```

### Data Flow

```
Session History
    ↓
Tool Call Logs
    ↓
Self-Healing Analysis
    ↓
    ├─→ Error Detection
    ├─→ Pattern Classification
    ├─→ Memory Lookup (agent_learnings)
    ├─→ Correction Suggestion
    └─→ Learning Storage (agent_learnings)
    ↓
Batch Insights (batch_insights)
    ↓
Dashboard Visualization
```

---

## 5. API Endpoints Summary

### Main Server (port 8000)

```
POST /webhook/recall                          # Recall meeting end webhook
POST /sessions/{agent_id}/end                 # Manual session end
GET  /self-healing/history                    # Get healing history
GET  /self-healing/learnings                  # Get error learnings
POST /self-healing/analyze/{session_id}       # Analyze specific session
```

### Dashboard Server (port 8002)

```
GET  /dashboard/api/self-healing/history      # Get healing history
GET  /dashboard/api/self-healing/learnings    # Get error learnings
POST /dashboard/api/self-healing/analyze/{id} # Analyze session
```

---

## 6. Database Tables

### New Tables (Migration 003)

```sql
-- Self-healing insights
CREATE TABLE batch_insights (
    id UUID PRIMARY KEY,
    insight_type STRING,
    title STRING,
    description STRING,
    data JSONB,
    tenant_id UUID,
    source_session_count INT,
    created_at TIMESTAMPTZ
);

-- Error-correction learnings
CREATE TABLE agent_learnings (
    id UUID PRIMARY KEY,
    tenant_id UUID,
    issue_category STRING,
    learning_text STRING,
    confidence FLOAT,
    times_applied INT,
    source_session_ids JSONB,
    is_active BOOL,
    created_at TIMESTAMPTZ
);

-- Session embeddings
CREATE TABLE session_embeddings (
    id UUID PRIMARY KEY,
    session_id UUID,
    tenant_id UUID,
    embedding VECTOR(1024),
    content_type STRING,
    content_text STRING,
    issue_category STRING,
    resolution_status STRING,
    created_at TIMESTAMPTZ
);
```

---

## 7. Testing the System

### Test Self-Healing

1. Create a session with some failed commands
2. End the session (manually or via Recall webhook)
3. Check dashboard → Self-Healing page
4. Verify:
   - Errors detected count
   - Error patterns displayed
   - Learnings generated
   - Healing history updated

### Test Email Confirmation

1. End a session with a known email
2. Check email inbox for confirmation
3. Verify:
   - Subject line includes resolution status
   - Session details are correct
   - Self-healing summary is included

### Test Automatic Session End

1. Start a session with Recall bot
2. Leave the Meet call
3. Check logs for:
   - "Recall webhook received"
   - "Meeting ended for agent {agent_id}"
   - "Self-healing complete"
   - "Confirmation email sent"

---

## 8. Future Enhancements

### Planned Features

1. **Real-time Error Detection**: Detect errors during session, not just at end
2. **Auto-Correction**: Automatically apply corrections without waiting for next session
3. **Learning Confidence Decay**: Reduce confidence of old learnings over time
4. **Multi-Tenant Learning**: Share learnings across tenants (with permission)
5. **Error Prediction**: Predict likely errors based on issue category
6. **Integration with External Systems**: Jira, Slack notifications for critical errors

---

## 9. Troubleshooting

### Common Issues

**Issue:** Self-healing not running
- **Check:** Is `handle_meeting_end()` being called?
- **Check:** Are tool logs being stored in `tool_call_logs` table?

**Issue:** Email not sending
- **Check:** SMTP credentials configured in `meeting_end_handler.py`
- **Check:** Email address is valid in `tenants` table
- **Check:** SMTP server logs for delivery errors

**Issue:** Learnings not appearing in dashboard
- **Check:** Are learnings being stored in `agent_learnings` table?
- **Check:** Is `is_active` flag set to true?
- **Check:** Dashboard API endpoint `/dashboard/api/self-healing/learnings` returning data?

---

## 10. Configuration

### Environment Variables

Add to `.env`:
```bash
# Email configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=deltomic-support@example.com

# Recall webhook (if using Recall.ai)
RECALL_WEBHOOK_SECRET=your-webhook-secret
```

### Update meeting_end_handler.py

Replace placeholder values:
```python
smtp_user = os.getenv("SMTP_USER", "your-email@gmail.com")
smtp_password = os.getenv("SMTP_PASSWORD", "your-app-password")
from_email = os.getenv("FROM_EMAIL", "deltomic-support@example.com")
```

---

## Summary

The DELTOMIC system now includes:

✅ **Embedding System**: Store session summaries as vectors for similarity search
✅ **Agent Learning**: Generate learnings from past sessions to improve future reasoning
✅ **Self-Healing**: Automatically detect errors, suggest corrections, store learnings
✅ **Dashboard Visualization**: Visual representation of self-healing process
✅ **Automatic Session End**: Detect meeting end via Recall webhook
✅ **Email Confirmation**: Send session summary and resolution status to customer

All components are integrated and ready for testing.
