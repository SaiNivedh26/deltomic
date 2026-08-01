# Agent Connect Remote

Just-in-time (JIT) remote access to customer machines via AWS SSM, with an AI agent that can run safe diagnostic commands.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│   FastAPI App   │────▶│  AWS SSM/Session │────▶│  Customer Machine   │
│  (Control Plane)│     │   Manager        │     │  (SSM Agent)        │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
        │                        │                        │
        ▼                        ▼                        ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  CockroachDB    │     │  CloudWatch      │     │  Hybrid Activation  │
│  (Access Grants)│     │  (Audit Logs)    │     │  (mi-xxxxxxx)       │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
```

## Flow

### 1. Customer Onboarding (One-time)
```bash
# Your app creates activation
POST /onboarding/create-activation?customer_id=customer-123

# Customer runs on their machine
./customer_onboard.sh <ACTIVATION_ID> <ACTIVATION_CODE>
```

### 2. Agent Requests Access
```bash
# Via API
POST /access/request
{
  "customer_id": "customer-123",
  "duration_minutes": 10
}

# Returns grant_id (pending approval)
```

### 3. Customer Approves
```bash
POST /access/approve
{
  "grant_id": "<grant_id>",
  "approved_by": "customer-admin@example.com"
}
```

### 4. Agent Runs Commands
```bash
# Via chat endpoint
POST /chat
{
  "message": "Check disk usage on customer-123's machine",
  "thread_id": "session-001"
}

# Agent uses tools:
# - request_access(customer_id)
# - run_command("df -h")
# - revoke_access()
```

## Allowed Commands

Only safe diagnostic commands are allowed:
- `ls`, `ls -la`, `ls -l`
- `df -h`
- `whoami`
- `pwd`
- `uname -a`
- `uptime`
- `free -m`
- `cat /etc/os-release`

## Setup

### 1. Install dependencies
```bash
cd agent-connect-remote
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

Required env vars:
- `COCKROACH_CONNECTION_STRING` - CockroachDB connection
- `AWS_ACCESS_KEY` - AWS access key with SSM permissions
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `AWS_DEFAULT_REGION` - AWS region (default: us-east-1)

### 3. Run the server
```bash
uvicorn main:app --reload
```

### 4. Test
```bash
python test_agent.py
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Chat with the agent |
| `/onboarding/create-activation` | POST | Create hybrid activation for customer |
| `/onboarding/verify/{customer_id}` | POST | Verify customer's machine is registered |
| `/access/request` | POST | Request temporary access |
| `/access/approve` | POST | Customer approves access |
| `/access/revoke` | POST | Revoke access |
| `/access/status/{grant_id}` | GET | Check grant status |

## Security

- **No inbound ports** - SSM uses outbound HTTPS only
- **IAM-based control** - AWS credentials control who can call SSM
- **Time-limited access** - Grants expire automatically
- **Command allowlist** - Only pre-approved commands can run
- **Full audit trail** - Every command logged to DB + CloudWatch
- **Customer approval required** - No access without explicit approval
- **Immediate revocation** - Customer or agent can revoke anytime

## Database Schema

- `customer_machines` - Registered machines (mi-xxxxx IDs)
- `support_access_grants` - Access grant lifecycle
- `support_command_audit` - Command execution audit log
