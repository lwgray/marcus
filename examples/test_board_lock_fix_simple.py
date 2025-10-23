#!/usr/bin/env python3
"""
Simple board lock test using direct HTTP requests to Marcus.

This bypasses MCP client library Python version issues by using
direct JSON-RPC HTTP calls.
"""

import argparse
import asyncio
import json
from typing import Any, Dict

import httpx


class MarcusHTTPClient:
    """Simple HTTP client for Marcus MCP server."""

    def __init__(self, base_url: str = "http://localhost:4298/mcp/"):
        self.base_url = base_url
        self.request_id = 0

    def _next_id(self) -> int:
        """Get next request ID."""
        self.request_id += 1
        return self.request_id

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call a Marcus MCP tool via HTTP."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
            "id": self._next_id(),
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.base_url,
                json=request,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                raise Exception(f"MCP Error: {result['error']}")

            # Extract tool result
            if "result" in result and "content" in result["result"]:
                content = result["result"]["content"]
                if content and len(content) > 0:
                    text: str = str(content[0].get("text", "{}"))
                    parsed: Dict[str, Any] = json.loads(text)
                    return parsed

            result_data: Dict[str, Any] = result.get("result", {})
            return result_data


async def test_board_lock(num_endpoints: int = 1) -> None:
    """Test board lock with simple HTTP client."""
    print(f"\n🚀 Board Lock Fix Test ({num_endpoints} endpoint)")
    print("=" * 70)

    client = MarcusHTTPClient()
    agent_id = f"test-agent-{num_endpoints}ep"

    try:
        # Authenticate
        print("\n🔐 Authenticating...")
        await client.call_tool(
            "authenticate",
            {
                "client_id": agent_id,
                "client_type": "admin",
                "role": "admin",
                "metadata": {"test_mode": True},
            },
        )
        print("✅ Authenticated")

        # Create project
        print(f"\n📦 Creating project with {num_endpoints} endpoint(s)...")
        if num_endpoints == 1:
            description = "Create a simple REST API with 1 endpoint: GET /api/health"
            project_name = "Test API - Single Endpoint"
        else:
            description = (
                "Create a simple REST API with 2 endpoints: "
                "GET /api/health and GET /api/version"
            )
            project_name = "Test API - Two Endpoints"

        project_result = await client.call_tool(
            "create_project",
            {
                "description": description,
                "project_name": project_name,
                "options": {"mode": "new_project", "complexity": "prototype"},
            },
        )
        print(f"✅ Project created: {project_result.get('project_id')}")
        print(f"   Tasks: {project_result.get('tasks_created', 0)}")
        expected_tasks = project_result.get("tasks_created", 0)

        # Register agent
        print(f"\n🤖 Registering agent: {agent_id}")
        await client.call_tool(
            "register_agent",
            {
                "agent_id": agent_id,
                "name": f"Test Agent ({num_endpoints}EP)",
                "role": "Developer",
                "skills": ["python", "fastapi"],
            },
        )
        print("✅ Agent registered")

        # Task completion loop
        print(f"\n{'='*70}")
        print("🔄 TASK COMPLETION LOOP")
        print("=" * 70)

        completed_count = 0
        no_task_count = 0
        iteration = 0
        completed_tasks = []

        while iteration < 50:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")

            # Request task
            print("📋 Requesting task...")
            task_result = await client.call_tool(
                "request_next_task", {"agent_id": agent_id}
            )

            if not task_result.get("success"):
                no_task_count += 1
                print(f"⏸️  No task ({task_result.get('retry_reason')})")

                if no_task_count >= 3:
                    print("\n🏁 No tasks for 3 iterations - done!")
                    break
                await asyncio.sleep(1)
                continue

            # Got task
            task_id = task_result.get("task_id")
            task_name = task_result.get("task", {}).get("name", "Unknown")
            print(f"✅ Task: {task_id}")
            print(f"   Name: {task_name}")

            no_task_count = 0

            # Complete task immediately
            print("📊 Completing task...")
            progress_result = await client.call_tool(
                "report_task_progress",
                {
                    "agent_id": agent_id,
                    "task_id": task_id,
                    "status": "completed",
                    "progress": 100,
                    "message": "Test completion",
                },
            )

            if progress_result.get("success"):
                completed_count += 1
                completed_tasks.append(task_name)
                print(f"✅ Completed! (Total: {completed_count})")
            else:
                print(f"❌ Failed: {progress_result.get('error')}")

            await asyncio.sleep(0.5)

        # Results
        print(f"\n{'='*70}")
        print("📊 TEST RESULTS")
        print("=" * 70)
        print(f"Expected tasks: {expected_tasks}")
        print(f"Completed tasks: {completed_count}")
        print(f"Iterations: {iteration}")
        print("\nCompleted tasks:")
        for i, task_name in enumerate(completed_tasks, 1):
            print(f"  {i}. {task_name}")

        if completed_count == expected_tasks:
            print(f"\n✅ SUCCESS: All {expected_tasks} tasks completed!")
            print("   No board lock detected!")
        else:
            print(f"\n⚠️  WARNING: {completed_count}/{expected_tasks} tasks completed")
            print("   Possible board lock!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--endpoints", type=int, default=1, choices=[1, 2], help="Number of endpoints"
    )
    args = parser.parse_args()

    asyncio.run(test_board_lock(args.endpoints))
