#!/usr/bin/env python3
"""
Live test for MCP tool logger.

This script connects to a running Marcus HTTP server and triggers various
MCP tool failures to verify the logger captures them correctly.

Prerequisites:
- Marcus server running in HTTP mode
- Start server with: python -m src.marcus_mcp.server --http

After running this script, check:
- logs/conversations/marcus_*.log - Should have WARNING entries for failures
- logs/marcus_*.log - Should have "Diagnostic Report" for request_next_task
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add project root to path
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


async def test_scenario_1_no_tasks_available(session: Any, client: Inspector) -> None:
    """
    Test Scenario 1: No tasks available.

    Expected: request_next_task returns false, logger creates WARNING entry
    with diagnostic pointer.
    """
    print("\n" + "=" * 70)
    print("TEST 1: No Tasks Available")
    print("=" * 70)
    print("\nSetup: Request task when no project has tasks")
    print("Expected: Logger creates WARNING + diagnostic pointer")

    timestamp = datetime.now(timezone.utc).isoformat()

    # Register agent
    agent_id = "test-no-tasks-agent"
    result = await client.register_agent(
        agent_id=agent_id,
        name="No Tasks Test Agent",
        role="Developer",
        skills=["python"],
    )
    pretty_print_result("Agent registered:", result)

    # Request task (should fail if no project or no tasks)
    print(f"\n⏰ Timestamp: {timestamp}")
    print(f"🔍 Requesting task for agent: {agent_id}")
    task_result = await client.request_next_task(agent_id)
    pretty_print_result("Task result:", task_result)

    # Parse result to check success
    if hasattr(task_result, "content") and task_result.content:
        text = task_result.content[0].text
        data = json.loads(text)

        if not data.get("success", True):
            print("\n✅ FAILURE LOGGED - Check logs:")
            print(f"   grep '{agent_id}' logs/conversations/marcus_*.log")
            print(
                "   grep -A 10 'Diagnostic Report' logs/marcus_*.log | "
                f"grep -A 10 '{timestamp[:10]}'"
            )
        else:
            print("\n⚠️  Task succeeded - no failure to log")


async def test_scenario_2_agent_already_busy(session: Any, client: Inspector) -> None:
    """
    Test Scenario 2: Agent already has a task.

    Expected: request_next_task returns false with "already have a task" error.
    """
    print("\n" + "=" * 70)
    print("TEST 2: Agent Already Busy")
    print("=" * 70)
    print("\nSetup: Request task twice for same agent")
    print("Expected: Second request fails with 'already have a task' error")

    timestamp = datetime.now(timezone.utc).isoformat()
    agent_id = "test-busy-agent"

    # Register agent
    result = await client.register_agent(
        agent_id=agent_id,
        name="Busy Test Agent",
        role="Developer",
        skills=["python", "testing"],
    )
    pretty_print_result("Agent registered:", result)

    # First request - might succeed if tasks available
    print("\n📋 First task request (might succeed)...")
    task1_result = await client.request_next_task(agent_id)
    pretty_print_result("First request:", task1_result)

    # Second request - should fail if first succeeded
    print(f"\n⏰ Timestamp: {timestamp}")
    print("📋 Second task request (should fail)...")
    task2_result = await client.request_next_task(agent_id)
    pretty_print_result("Second request:", task2_result)

    if hasattr(task2_result, "content") and task2_result.content:
        text = task2_result.content[0].text
        data = json.loads(text)

        if not data.get("success", True):
            print("\n✅ FAILURE LOGGED - Check logs:")
            print(f"   grep '{agent_id}' logs/conversations/marcus_*.log")
            print("   Should see: 'already have a task assigned'")


async def test_scenario_3_all_tasks_assigned(session: Any, client: Inspector) -> None:
    """
    Test Scenario 3: All tasks assigned to other agents.

    Expected: request_next_task returns false, diagnostic report shows
    why (all tasks assigned, dependency blocked, etc).
    """
    print("\n" + "=" * 70)
    print("TEST 3: All Tasks Assigned")
    print("=" * 70)
    print("\nSetup: Multiple agents requesting tasks")
    print("Expected: Eventually one fails when all tasks assigned")

    timestamp = datetime.now(timezone.utc).isoformat()

    # Register multiple agents
    agents = []
    for i in range(3):
        agent_id = f"test-assigned-agent-{i}"
        await client.register_agent(
            agent_id=agent_id,
            name=f"Assigned Test Agent {i}",
            role="Developer",
            skills=["python", "testing"],
        )
        agents.append(agent_id)
        print(f"✅ Registered: {agent_id}")

    # Each agent requests a task
    print(f"\n⏰ Timestamp: {timestamp}")
    for agent_id in agents:
        print(f"\n📋 Requesting task for: {agent_id}")
        task_result = await client.request_next_task(agent_id)

        if hasattr(task_result, "content") and task_result.content:
            text = task_result.content[0].text
            data = json.loads(text)

            if data.get("success", True):
                print("   ✅ Task assigned")
            else:
                print("   ❌ Task request failed")
                print("\n✅ FAILURE LOGGED - Check logs:")
                print(f"   grep '{agent_id}' logs/conversations/marcus_*.log")
                print("   grep -A 20 'Diagnostic Report' logs/marcus_*.log")
                break


async def test_scenario_4_other_tool_failure(session: Any, client: Inspector) -> None:
    """
    Test Scenario 4: Non-request_next_task failure.

    Expected: Logger creates WARNING entry WITHOUT diagnostic pointer.
    """
    print("\n" + "=" * 70)
    print("TEST 4: Other Tool Failure")
    print("=" * 70)
    print("\nSetup: Call tool with invalid arguments")
    print("Expected: Logger creates WARNING WITHOUT diagnostic pointer")

    timestamp = datetime.now(timezone.utc).isoformat()

    # Try to get non-existent project
    print(f"\n⏰ Timestamp: {timestamp}")
    print("🔍 Getting non-existent project...")

    try:
        result = await session.call_tool(
            "get_project_status",
            arguments={"name": "non-existent-project-12345"},
        )
        pretty_print_result("Result:", result)

        if hasattr(result, "content") and result.content:
            text = result.content[0].text
            data = json.loads(text)

            if not data.get("success", True):
                print("\n✅ FAILURE LOGGED - Check logs:")
                print("   grep 'get_project_status' logs/conversations/marcus_*.log")
                print("   Should NOT contain 'Diagnostic Report' reference")
    except Exception as e:
        print(f"❌ Error: {e}")


async def verify_log_structure(session: Any) -> None:
    """Verify the log structure is correct."""
    print("\n" + "=" * 70)
    print("LOG VERIFICATION")
    print("=" * 70)

    print("\n📂 Expected log locations:")
    print("   • logs/conversations/marcus_*.log - Activity tracking (WHAT/WHEN)")
    print("   • logs/marcus_*.log - Diagnostic reports (WHY)")

    print("\n📋 What to look for in conversation logs:")
    print("   • Level: 'warning'")
    print("   • Message: 'MCP tool \"<name>\" returned failure'")
    print("   • Fields: tool_name, arguments, error, retry_reason, response")
    print("   • For request_next_task: Diagnostic pointer message")

    print("\n📋 What to look for in Python logs:")
    print("   • 'Diagnostic Report (for operators):'")
    print("   • Dependency analysis")
    print("   • Task filtering statistics")

    print("\n🔍 Quick verification commands:")
    print("   # See all MCP tool failures")
    print("   grep 'returned failure' logs/conversations/marcus_*.log")
    print()
    print("   # See diagnostic pointers")
    print("   grep 'Diagnostic Report' logs/conversations/marcus_*.log")
    print()
    print("   # See actual diagnostic reports")
    print("   grep -A 30 'Diagnostic Report (for operators)' logs/marcus_*.log")


async def main() -> None:
    """
    Run live tests for MCP tool logger.

    This connects to a running Marcus server and triggers various failure
    scenarios to verify logging works correctly.
    """
    print("\n" + "=" * 70)
    print("🧪 MCP Tool Logger - Live System Test")
    print("=" * 70)
    print("\nThis test connects to running Marcus HTTP server")
    print("and triggers various MCP tool failures to verify logging.")
    print("\nMake sure Marcus server is running:")
    print("  python -m src.marcus_mcp.server --http")
    print("=" * 70)

    client = Inspector(connection_type="http")
    url = "http://localhost:4298/mcp"  # Main endpoint

    try:
        async with client.connect(url=url) as session:
            # Authenticate as admin
            print("\n🔐 Authenticating as admin...")
            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": "mcp-logger-test",
                    "client_type": "admin",
                    "role": "admin",
                    "metadata": {"test_type": "mcp_logger_live_test"},
                },
            )
            print("✅ Authenticated")

            # Run test scenarios
            await test_scenario_1_no_tasks_available(session, client)
            await asyncio.sleep(1)  # Brief pause between tests

            await test_scenario_2_agent_already_busy(session, client)
            await asyncio.sleep(1)

            await test_scenario_3_all_tasks_assigned(session, client)
            await asyncio.sleep(1)

            await test_scenario_4_other_tool_failure(session, client)

            # Show verification instructions
            await verify_log_structure(session)

            print("\n" + "=" * 70)
            print("✅ Live test complete!")
            print("=" * 70)
            print("\n📊 NEXT STEPS:")
            print("1. Check logs/conversations/marcus_*.log for WARNING entries")
            print("2. Check logs/marcus_*.log for 'Diagnostic Report'")
            print("3. Verify diagnostic pointers only appear for request_next_task")
            print("4. Verify NO 'failure_category' or 'dependency_issue' labels")
            print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Is Marcus server running? python -m src.marcus_mcp.server --http")
        print(f"   2. Is server accessible at: {url}")
        print("   3. Check server logs for connection errors")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
