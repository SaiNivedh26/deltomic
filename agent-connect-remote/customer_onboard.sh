#!/bin/bash
# Customer Onboarding Script
# This script registers the customer's machine with SSM for JIT access

set -e

echo "=========================================="
echo "  Remote Support - Machine Registration"
echo "=========================================="
echo ""

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "Usage: $0 <CUSTOMER_ID> <ACTIVATION_ID> <ACTIVATION_CODE> [REGION] [API_URL]"
    echo ""
    echo "Example: $0 customer-123 abc123-def456 XYZ789 us-east-1 http://localhost:8000"
    exit 1
fi

CUSTOMER_ID="$1"
ACTIVATION_ID="$2"
ACTIVATION_CODE="$3"
REGION="${4:-us-east-1}"
API_URL="${5:-http://localhost:8000}"

echo "Customer ID: $CUSTOMER_ID"
echo "Activation ID: $ACTIVATION_ID"
echo "Region: $REGION"
echo "API URL: $API_URL"
echo ""

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "Cannot detect OS. Please install SSM Agent manually."
    exit 1
fi

echo "Detected OS: $OS"
echo ""

# Install SSM Agent based on OS
echo "Installing SSM Agent..."
case "$OS" in
    ubuntu|debian)
        sudo snap install amazon-ssm-agent --classic
        ;;
    amzn|rhel|centos|fedora)
        sudo yum install -y amazon-ssm-agent
        ;;
    *)
        echo "Unsupported OS: $OS"
        echo "Please install SSM Agent manually from AWS documentation."
        exit 1
        ;;
esac

echo ""
echo "Registering machine with SSM..."

# Find SSM Agent binary (snap vs system)
SSM_AGENT_BIN=""
if command -v amazon-ssm-agent &> /dev/null; then
    SSM_AGENT_BIN="amazon-ssm-agent"
elif [ -f /snap/bin/amazon-ssm-agent ]; then
    SSM_AGENT_BIN="/snap/bin/amazon-ssm-agent"
elif [ -f /snap/amazon-ssm-agent/current/amazon-ssm-agent ]; then
    SSM_AGENT_BIN="/snap/amazon-ssm-agent/current/amazon-ssm-agent"
elif snap list amazon-ssm-agent &> /dev/null; then
    # Snap is installed, use snap run
    SSM_AGENT_BIN="snap run amazon-ssm-agent"
else
    echo "ERROR: SSM Agent not found. Please install it first."
    exit 1
fi

echo "Using SSM Agent: $SSM_AGENT_BIN"

# Register with hybrid activation (auto-confirm if already registered)
REGISTER_OUTPUT=$(echo "Yes" | sudo $SSM_AGENT_BIN -register \
    -code "$ACTIVATION_CODE" \
    -id "$ACTIVATION_ID" \
    -region "$REGION" 2>&1)

echo "$REGISTER_OUTPUT"

# Extract managed instance ID
MANAGED_NODE_ID=$(echo "$REGISTER_OUTPUT" | grep -oP 'mi-[a-f0-9]+' | head -1)

if [ -z "$MANAGED_NODE_ID" ]; then
    echo ""
    echo "WARNING: Could not extract managed instance ID from registration output."
    echo "Please register manually:"
    echo "  curl -X POST '$API_URL/onboarding/register' -H 'Content-Type: application/json' -d '{\"customer_id\": \"$CUSTOMER_ID\", \"managed_node_id\": \"mi-YOUR_ID\"}'"
else
    echo ""
    echo "Managed Instance ID: $MANAGED_NODE_ID"
    
    # Register in our database
    echo "Registering machine in database..."
    REGISTER_RESPONSE=$(curl -s -X POST "$API_URL/onboarding/register" \
        -H "Content-Type: application/json" \
        -d "{\"customer_id\": \"$CUSTOMER_ID\", \"managed_node_id\": \"$MANAGED_NODE_ID\", \"machine_name\": \"$(hostname)\"}")
    
    echo "Database response: $REGISTER_RESPONSE"
fi

# Enable and start the agent
if systemctl list-unit-files | grep -q "amazon-ssm-agent.service"; then
    sudo systemctl enable amazon-ssm-agent
    sudo systemctl restart amazon-ssm-agent
else
    echo "Starting SSM Agent via snap..."
    sudo snap restart amazon-ssm-agent 2>/dev/null || true
fi

echo ""
echo "Verifying registration..."
sleep 3
sudo $SSM_AGENT_BIN -check

echo ""
echo "=========================================="
echo "  Registration Complete!"
echo "=========================================="
echo ""
echo "Your machine is now registered for remote support."
echo "Support agents can request temporary access when needed."
echo ""
