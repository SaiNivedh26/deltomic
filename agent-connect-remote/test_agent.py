#!/usr/bin/env python3
"""
Test script for agent-connect-remote.
Demonstrates the full JIT access flow.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.agent import chat


async def main():
    print("=" * 50)
    print("  Agent Connect Remote - Test Session")
    print("=" * 50)
    print()
    
    thread_id = "test-session-001"
    
    # Simulate conversation
    messages = [
        "Hello, I need to check the status of a customer's machine.",
        "The customer ID is 'customer-123'. Can you request access?",
        "What commands are available?",
        "Let me know when access is approved so I can run diagnostics.",
    ]
    
    for msg in messages:
        print(f"\n[User]: {msg}")
        print("-" * 40)
        
        response = await chat(msg, thread_id)
        print(f"[Agent]: {response}")
        
        if "Grant ID:" in response:
            grant_id = response.split("Grant ID:")[1].split("\n")[0].strip()
            print(f"\n  >> Extracted grant_id: {grant_id}")
            
            # Simulate customer approval
            print("  >> Simulating customer approval...")
            from backend.access_control import access_control
            try:
                access_control.approve_access(grant_id, "customer-admin@example.com")
                print("  >> Access approved!")
            except Exception as e:
                print(f"  >> Could not approve (expected in test): {e}")
    
    print("\n" + "=" * 50)
    print("  Test Complete")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
