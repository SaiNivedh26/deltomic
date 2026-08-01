from __future__ import annotations

import logging
from datetime import datetime, timedelta

import boto3

from backend.config import AWS_ACCESS_KEY, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION

logger = logging.getLogger(__name__)

ssm_client = boto3.client(
    "ssm",
    region_name=AWS_DEFAULT_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)


def create_hybrid_activation(customer_id: str, expires_hours: int = 24) -> dict:
    expiration_date = datetime.utcnow() + timedelta(hours=expires_hours)
    
    response = ssm_client.create_activation(
        Description=f"Customer {customer_id} JIT access",
        DefaultInstanceName=f"customer-{customer_id}-node",
        IamRole="AmazonEC2RunCommandRoleForManagedInstances",
        RegistrationLimit=1,
        ExpirationDate=expiration_date,
        Tags=[
            {"Key": "CustomerId", "Value": customer_id},
            {"Key": "ManagedBy", "Value": "AgentConnectRemote"},
        ],
    )

    return {
        "activation_id": response["ActivationId"],
        "activation_code": response["ActivationCode"],
        "expires_at": expiration_date.isoformat(),
    }


def get_activation_commands(activation_id: str, activation_code: str, region: str = None) -> str:
    region = region or AWS_DEFAULT_REGION
    return f"""#!/bin/bash
# Customer Onboarding Script - Run ONCE
# This registers your machine with our SSM for temporary support access

# Install SSM Agent (Ubuntu/Debian)
sudo snap install amazon-ssm-agent

# For Amazon Linux/RHEL/CentOS:
# sudo yum install -y amazon-ssm-agent

# Register with hybrid activation
sudo amazon-ssm-agent -register \\
  -code "{activation_code}" \\
  -id "{activation_id}" \\
  -region "{region}"

# Start the agent
sudo systemctl enable amazon-ssm-agent
sudo systemctl restart amazon-ssm-agent

# Verify
sudo amazon-ssm-agent -check
echo "Registration complete. Your machine is now managed."
"""


def verify_managed_instance(customer_id: str) -> dict | None:
    response = ssm_client.describe_instance_information()

    instances = response.get("InstanceInformationList", [])
    
    # Filter client-side by CustomerId tag
    for instance in instances:
        tags = instance.get("Tags", [])
        customer_tag = next((t["Value"] for t in tags if t["Key"] == "CustomerId"), None)
        if customer_tag == customer_id:
            return {
                "managed_node_id": instance["InstanceId"],
                "ping_status": instance["PingStatus"],
                "platform": instance.get("PlatformType"),
                "agent_version": instance.get("AgentVersion"),
                "last_ping": instance.get("LastPingDateTime"),
            }
    
    return None


def verify_managed_instance_by_id(managed_node_id: str) -> dict | None:
    response = ssm_client.describe_instance_information(
        Filters=[
            {"Key": "InstanceIds", "Values": [managed_node_id]},
        ]
    )

    instances = response.get("InstanceInformationList", [])
    if not instances:
        return None

    instance = instances[0]
    return {
        "managed_node_id": instance["InstanceId"],
        "ping_status": instance["PingStatus"],
        "platform": instance.get("PlatformType"),
        "agent_version": instance.get("AgentVersion"),
        "last_ping": instance.get("LastPingDateTime"),
    }


def list_managed_instances() -> list[dict]:
    response = ssm_client.describe_instance_information()

    instances = response.get("InstanceInformationList", [])
    
    # Filter client-side by ManagedBy tag
    result = []
    for inst in instances:
        tags = inst.get("Tags", [])
        managed_by = next((t["Value"] for t in tags if t["Key"] == "ManagedBy"), None)
        if managed_by == "AgentConnectRemote":
            customer_id = next((t["Value"] for t in tags if t["Key"] == "CustomerId"), None)
            result.append({
                "managed_node_id": inst["InstanceId"],
                "customer_id": customer_id,
                "ping_status": inst["PingStatus"],
                "platform": inst.get("PlatformType"),
            })
    
    return result
