#!/usr/bin/env python3
"""
Test the MCPKanbanClientSimplified functionality
Quick diagnostic to verify the client is working properly
"""

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mcp.client.stdio import stdio_client

from mcp import ClientSession, StdioServerParameters
from src.integrations.mcp_kanban_client_simple import SimpleMCPKanbanClient


async def create_mcp_function_caller():
    """Create a real MCP function caller for testing"""
    @asynccontextmanager
    async def get_client():
        server_params = StdioServerParameters(
            command="node",
            args=["/Users/lwgray/.nvm/versions/node/v22.14.0/lib/node_modules/@lwgray1975/kanban-mcp/dist/index.js"],
            env=None
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session

    async def mcp_call(tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call an MCP tool"""
        async with get_client() as session:
            result = await session.call_tool(tool_name, arguments)
            return result.content[0].text if result.content else None

    return mcp_call


async def test_simple():
    """Test basic MCPKanbanClientSimplified operations"""
    # Create MCP function caller
    mcp_caller = await create_mcp_function_caller()

    # Create client with MCP caller
    client = SimpleMCPKanbanClient(mcp_caller)

    print("🔍 Testing MCPKanbanClientSimplified")
    print("=" * 60)

    try:
        # Initialize the client
        print("\n1. Initializing client...")
        await client.initialize("Task Master Test")
        print(f"✅ Initialized successfully")
        print(f"  - Project ID: {client.project_id}")
        print(f"  - Board ID: {client.board_id}")

        # Test get board summary
        print("\n2. Testing get_board_summary...")
        summary = await client.get_board_summary()
        stats = summary.get('stats', {})
        print(f"✅ Board statistics:")
        print(f"   - Total cards: {stats.get('totalCards', 0)}")
        print(f"   - In progress: {stats.get('inProgressCount', 0)}")
        print(f"   - Done: {stats.get('doneCount', 0)}")
        print(f"   - Completion: {stats.get('completionPercentage', 0)}%")

        # Test get available tasks
        print("\n3. Testing get_available_tasks...")
        tasks = await client.get_available_tasks()
        print(f"✅ Found {len(tasks)} tasks")

        if tasks:
            print("\nTasks:")
            for i, task in enumerate(tasks[:5]):  # Show first 5
                print(f"   {i+1}. {task.name}")
                print(f"      - ID: {task.id}")
                print(f"      - Status: {task.status.value}")
                print(f"      - Priority: {task.priority.value}")
        else:
            print("   (No tasks found)")

        # Test task assignment (if tasks available)
        if tasks and len(tasks) > 0:
            # Find an unassigned task
            unassigned_task = None
            for task in tasks:
                if task.status == TaskStatus.TODO:
                    unassigned_task = task
                    break

            if unassigned_task:
                print("\n4. Testing task assignment...")
                test_agent = "diagnostic-test-agent"

                print(f"   Assigning '{unassigned_task.name}' to {test_agent}")
                await client.assign_task(unassigned_task.id, test_agent)
                print(f"✅ Task assigned successfully")
                print("   (Check kanban board for comment and list change)")
            else:
                print("\n4. No unassigned tasks available for assignment test")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_simple())
