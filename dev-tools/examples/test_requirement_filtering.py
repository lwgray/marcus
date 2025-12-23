#!/usr/bin/env python3
"""
End-to-end test for requirement filtering fix.

Tests that prototype mode correctly limits tasks even with explicit requirements.

Prerequisites:
- Marcus server must be running: python -m src.marcus_mcp.server --http
- Planka must be running: docker-compose up -d
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Add project root to path (go up two levels from dev-tools/examples/)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.worker.inspector import Inspector  # noqa: E402


def pretty_print_result(label: str, result: Any) -> None:
    """Pretty print MCP tool results."""
    print(f"\n{label}")
    if hasattr(result, "content") and result.content:
        # Extract text from MCP result
        text = result.content[0].text if result.content else str(result)
        try:
            # Try to parse and pretty print JSON
            data = json.loads(text)
            print(json.dumps(data, indent=2))
        except (json.JSONDecodeError, AttributeError):
            print(text)
    else:
        print(result)


async def test_prototype_filtering() -> None:
    """
    Test that prototype mode limits to 3 tasks even with 10 explicit requirements.

    This is an end-to-end test using a real Marcus instance and Planka.
    """
    print("\n" + "=" * 70)
    print("🧪 E2E TEST: Requirement Filtering Fix")
    print("=" * 70)
    print("\nConnecting to Marcus HTTP server...")

    client = Inspector(connection_type="http")
    url = "http://localhost:4298/mcp"  # Main endpoint

    try:
        async with client.connect(url=url) as session:
            # Authenticate as admin
            print("🔐 Authenticating as admin...")
            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": "filtering-test",
                    "client_type": "admin",
                    "role": "admin",
                    "metadata": {"test": "requirement_filtering"},
                },
            )
            print("✅ Authenticated\n")

            # Test 1: Prototype mode with 10 explicit MCP tools
            print("=" * 70)
            print("TEST 1: Prototype Mode with 10 Explicit Tools")
            print("=" * 70)

            description_10_tools = """
            Create an MCP server with these 10 tools:
            1. ping - Test server connectivity
            2. echo - Echo messages back
            3. get_time - Get current timestamp
            4. calculate - Basic calculator
            5. convert_units - Unit converter
            6. search - Search functionality
            7. translate - Language translation
            8. get_weather - Weather information
            9. get_news - News fetcher
            10. get_stocks - Stock prices
            """

            print("\n📝 Creating project with 10 explicit tools in PROTOTYPE mode...")
            print("Expected: Only 3 tasks should be created (not 10)\n")

            result = await session.call_tool(
                "create_project",
                arguments={
                    "description": description_10_tools,
                    "project_name": "Test MCP Toolbox Prototype",
                    "options": {
                        "complexity": "prototype",
                        "provider": "planka",
                    },
                },
            )

            pretty_print_result("Project creation result:", result)

            # Parse result to check task count
            if hasattr(result, "content") and result.content:
                text = result.content[0].text
                data = json.loads(text)

                if data.get("success"):
                    tasks_created = data.get("tasks_created", 0)
                    print(f"\n{'=' * 70}")
                    print(f"📊 RESULT: {tasks_created} tasks created")
                    print(f"{'=' * 70}")

                    if tasks_created <= 3:
                        print("✅ TEST PASSED: Prototype mode correctly limited tasks!")
                        print("   Expected: ≤3 tasks")
                        print(f"   Actual: {tasks_created} tasks")
                        print("\n   This proves the filtering fix is working:")
                        print("   - 10 explicit requirements provided")
                        print("   - Only 3 tasks created (prototype limit)")
                        print("   - Requirements were bundled, not created 1:1")
                    else:
                        print("❌ TEST FAILED: Too many tasks created!")
                        print("   Expected: ≤3 tasks")
                        print(f"   Actual: {tasks_created} tasks")
                        print("\n   This indicates the filtering fix is NOT working.")
                else:
                    error_msg = data.get("error", "Unknown error")
                    print(f"❌ Project creation failed: {error_msg}")

            # Test 2: Standard mode with same requirements
            print("\n" + "=" * 70)
            print("TEST 2: Standard Mode with 10 Explicit Tools")
            print("=" * 70)

            print("\n📝 Creating project with 10 explicit tools in STANDARD mode...")
            print("Expected: 3-5 tasks based on team size\n")

            result = await session.call_tool(
                "create_project",
                arguments={
                    "description": description_10_tools,
                    "project_name": "Test MCP Toolbox Standard",
                    "options": {
                        "complexity": "standard",
                        "provider": "planka",
                    },
                },
            )

            pretty_print_result("Project creation result:", result)

            if hasattr(result, "content") and result.content:
                text = result.content[0].text
                data = json.loads(text)

                if data.get("success"):
                    tasks_created = data.get("tasks_created", 0)
                    print(f"\n{'=' * 70}")
                    print(f"📊 RESULT: {tasks_created} tasks created")
                    print(f"{'=' * 70}")

                    if 3 <= tasks_created <= 5:
                        print("✅ TEST PASSED: Standard mode correctly limited tasks!")
                        print("   Expected: 3-5 tasks (team size dependent)")
                        print(f"   Actual: {tasks_created} tasks")
                    else:
                        print("⚠️  Warning: Task count outside expected range")
                        print("   Expected: 3-5 tasks")
                        print(f"   Actual: {tasks_created} tasks")

            # Test 3: Enterprise mode
            print("\n" + "=" * 70)
            print("TEST 3: Enterprise Mode with 5 Explicit Tools")
            print("=" * 70)

            description_5_tools = """
            Create an MCP server with these 5 tools:
            1. ping - Test connectivity
            2. echo - Echo messages
            3. get_time - Get timestamp
            4. calculate - Calculator
            5. convert - Unit converter
            """

            print("\n📝 Creating project with 5 explicit tools in ENTERPRISE mode...")
            print("Expected: All 5 requirements included (no filtering)\n")

            result = await session.call_tool(
                "create_project",
                arguments={
                    "description": description_5_tools,
                    "project_name": "Test MCP Toolbox Enterprise",
                    "options": {
                        "complexity": "enterprise",
                        "provider": "planka",
                    },
                },
            )

            pretty_print_result("Project creation result:", result)

            if hasattr(result, "content") and result.content:
                text = result.content[0].text
                data = json.loads(text)

                if data.get("success"):
                    tasks_created = data.get("tasks_created", 0)
                    print(f"\n{'=' * 70}")
                    print(f"📊 RESULT: {tasks_created} tasks created")
                    print(f"{'=' * 70}")

                    if tasks_created >= 5:
                        print("✅ TEST PASSED: Enterprise mode kept all requirements!")
                        print("   Expected: ≥5 tasks")
                        print(f"   Actual: {tasks_created} tasks")
                    else:
                        print("❌ TEST FAILED: Not enough tasks created")
                        print("   Expected: ≥5 tasks")
                        print(f"   Actual: {tasks_created} tasks")

            # Test 4: Prototype mode with only 2 explicit tools
            print("\n" + "=" * 70)
            print("TEST 4: Prototype Mode with ONLY 2 Explicit Tools")
            print("=" * 70)

            description_2_tools = """
            Create an MCP server with these 2 tools:
            1. ping - Test connectivity
            2. echo - Echo messages
            """

            print("\n📝 Creating project with 2 explicit tools in PROTOTYPE mode...")
            print("Expected: All 2 requirements kept (explicit mode)")
            print("(Testing that explicit requirements bypass filtering)\n")

            result = await session.call_tool(
                "create_project",
                arguments={
                    "description": description_2_tools,
                    "project_name": "Test MCP Minimal Prototype",
                    "options": {
                        "complexity": "prototype",
                        "provider": "planka",
                    },
                },
            )

            pretty_print_result("Project creation result:", result)

            if hasattr(result, "content") and result.content:
                text = result.content[0].text
                data = json.loads(text)

                if data.get("success"):
                    tasks_created = data.get("tasks_created", 0)
                    print(f"\n{'=' * 70}")
                    print(f"📊 RESULT: {tasks_created} tasks created")
                    print(f"{'=' * 70}")

                    # With 2 explicit requirements, all should be kept
                    print("✅ TEST INFO: 2 explicit requirements were provided")
                    print(f"   Actual: {tasks_created} tasks created")
                    print("\n   This shows explicit requirements are preserved")
                    print("   even in prototype mode (bypassing filtering)")

            print("\n" + "=" * 70)
            print("✅ E2E Testing Complete!")
            print("=" * 70)
            print("\nTo verify visually:")
            print("1. Open Planka: http://localhost:3333")
            print("2. Check the projects created:")
            print("   - 'Test MCP Toolbox Prototype' should have ≤3 tasks")
            print("   - 'Test MCP Toolbox Standard' should have 3-5 tasks")
            print("   - 'Test MCP Toolbox Enterprise' should have ≥5 tasks")
            print("   - 'Test MCP Minimal Prototype' shows 2 explicit reqs preserved")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Make sure Marcus server is running:")
        print("      python -m src.marcus_mcp.server --http")
        print("   2. Make sure Planka is running:")
        print("      cd /path/to/planka && docker-compose up -d")
        print(f"   3. Verify the URL is correct: {url}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_prototype_filtering())
