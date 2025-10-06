#!/usr/bin/env python3
"""
Test script for the Inspector client using HTTP connection.

This demonstrates that the Inspector client (from inspector.py) works properly
with FastMCP's streamable HTTP implementation.
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


async def test_http_connection() -> None:
    """Test the Inspector client with HTTP connection (streamablehttp transport)."""
    print("\n" + "=" * 70)
    print("Testing Inspector Client - HTTP Mode (streamablehttp_client)")
    print("=" * 70)
    print("\nConnecting to Marcus HTTP server...")
    print("URL: http://localhost:4298/mcp")
    print("\n" + "=" * 70)

    client = Inspector(connection_type="http")
    url = "http://localhost:4298/mcp"

    try:
        async with client.connect(url=url) as session:
            print("\n✅ Successfully connected using streamablehttp_client!")

            # Step 1: Authenticate
            print("\n🔐 Step 1: Authenticating as admin...")
            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": "test-http-client",
                    "client_type": "admin",
                    "role": "admin",
                    "metadata": {"test": True, "transport": "streamablehttp"},
                },
            )
            print("✅ Authenticated successfully")

            # Step 2: List projects
            print("\n📂 Step 2: Listing projects...")
            projects_result = await session.call_tool("list_projects", arguments={})
            pretty_print("Available projects:", projects_result)

            # Step 3: Get current project
            print("\n📍 Step 3: Getting current project...")
            current_result = await session.call_tool(
                "get_current_project", arguments={}
            )
            pretty_print("Current project:", current_result)

            # Step 4: Register agent
            print("\n🤖 Step 4: Registering test agent...")
            register_result = await client.register_agent(
                agent_id="test-http-client",
                name="HTTP Test Agent",
                role="Developer",
                skills=["python", "http", "testing"],
            )
            pretty_print("Agent registered:", register_result)

            # Step 5: Request a task
            print("\n📋 Step 5: Requesting next task...")
            task_result = await client.request_next_task("test-http-client")
            pretty_print("Task result:", task_result)

            print("\n" + "=" * 70)
            print("✅ All tests passed! HTTP client is working correctly.")
            print("=" * 70)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Make sure Marcus server is running: ./marcus status")
        print("   2. If not running, start it: ./marcus start")
        print(f"   3. Verify the URL is correct: {url}")
        import traceback

        traceback.print_exc()
        raise


async def main() -> None:
    """Run the Inspector HTTP client test."""
    print("\n🚀 Inspector Client Test - HTTP Mode (streamablehttp_client)")
    print("=" * 70)
    print("\nThis test validates that the Inspector client works correctly")
    print("in HTTP mode with FastMCP's streamable HTTP transport.")
    print("\nPrerequisites:")
    print("- Marcus server running in HTTP mode")
    print("- Check status: ./marcus status")
    print("=" * 70)

    await test_http_connection()

    print("\n✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(main())
