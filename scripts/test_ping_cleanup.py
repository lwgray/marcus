#!/usr/bin/env python3
"""
Test script to interact with Marcus ping tool for cleanup and health check.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.marcus_mcp.client import SimpleMarcusClient


async def test_ping_cleanup():
    """Test ping cleanup and health functionality."""
    client = SimpleMarcusClient()

    try:
        await client.initialize()
        print("Connected to Marcus server\n")

        # First check health before cleanup
        print("=== Health Check BEFORE Cleanup ===")
        health_result = await client.call_tool("ping", arguments={"echo": "health"})
        print(json.dumps(health_result, indent=2))

        # Show specific info about stuck assignments
        if health_result and "health" in health_result:
            health_info = health_result["health"]
            if "tasks_being_assigned" in health_info:
                stuck_tasks = health_info["tasks_being_assigned"]
                if stuck_tasks:
                    print(
                        f"\n⚠️  Found {len(stuck_tasks)} stuck task assignments: {stuck_tasks}"
                    )
                else:
                    print("\n✅ No stuck task assignments found")

            # Show lease statistics
            if "lease_statistics" in health_info:
                print("\n=== Lease Statistics ===")
                print(json.dumps(health_info["lease_statistics"], indent=2))

        # Perform cleanup if needed
        if health_result and health_result.get("health", {}).get(
            "tasks_being_assigned", []
        ):
            print("\n=== Performing Cleanup ===")
            cleanup_result = await client.call_tool(
                "ping", arguments={"echo": "cleanup"}
            )
            print(json.dumps(cleanup_result, indent=2))

            # Check health after cleanup
            print("\n=== Health Check AFTER Cleanup ===")
            health_after = await client.call_tool("ping", arguments={"echo": "health"})
            print(json.dumps(health_after, indent=2))
        else:
            print("\n✅ No cleanup needed - no stuck assignments")

        # Close the client properly
        await client.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        # Make sure to close even on error
        if client:
            await client.close()


if __name__ == "__main__":
    asyncio.run(test_ping_cleanup())
