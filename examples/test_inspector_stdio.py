#!/usr/bin/env python3
"""
Test script for the Inspector client using stdio connection.

This demonstrates that the Inspector client works with stdio transport,
spawning an isolated Marcus instance for testing.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from typing import Any  # noqa: E402

from src.worker.inspector import Inspector  # noqa: E402


def pretty_print(label: str, result: Any) -> None:
    """Pretty print MCP tool results."""
    print(f"\n{label}")
    if hasattr(result, "content") and result.content:
        text = result.content[0].text if result.content else str(result)
        try:
            data = json.loads(text)
            print(json.dumps(data, indent=2))
        except (json.JSONDecodeError, AttributeError):
            print(text)
    else:
        print(result)


async def test_stdio_connection() -> None:
    """Test the Inspector client with stdio connection."""
    print("\n" + "=" * 70)
    print("Testing Inspector Client - Stdio Mode")
    print("=" * 70)
    print("\nSpawning isolated Marcus instance via stdio...")
    print("=" * 70)

    client = Inspector(connection_type="stdio")

    try:
        async with client.connect() as session:
            print("\n✅ Successfully connected using stdio_client!")

            # Step 1: Authenticate
            print("\n🔐 Step 1: Authenticating as test client...")
            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": "test-stdio-client",
                    "client_type": "admin",
                    "role": "admin",
                    "metadata": {"test": True, "transport": "stdio"},
                },
            )
            print("✅ Authenticated successfully")

            # Step 2: Register agent
            print("\n🤖 Step 2: Registering test agent...")
            register_result = await client.register_agent(
                agent_id="test-stdio-agent",
                name="Stdio Test Agent",
                role="Developer",
                skills=["python", "stdio", "testing"],
            )
            pretty_print("Agent registered:", register_result)

            # Step 3: Ping
            print("\n🏓 Step 3: Testing ping...")
            ping_result = await session.call_tool(
                "ping", arguments={"echo": "Hello from stdio!"}
            )
            pretty_print("Ping result:", ping_result)

            print("\n" + "=" * 70)
            print("✅ All tests passed! Stdio client is working correctly.")
            print("=" * 70)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        raise


async def main() -> None:
    """Run the Inspector stdio client test."""
    print("\n🚀 Inspector Client Test - Stdio Mode")
    print("=" * 70)
    print("\nThis test validates that the Inspector client works correctly")
    print("in stdio mode by spawning an isolated Marcus instance.")
    print("\nNo prerequisites needed - stdio spawns its own instance.")
    print("=" * 70)

    await test_stdio_connection()

    print("\n✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(main())
