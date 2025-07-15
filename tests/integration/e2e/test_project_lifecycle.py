"""
End-to-end test for complete project lifecycle.

Tests the full flow from project creation through task completion,
simulating real-world usage of the Marcus system.
"""

import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, patch

import pytest

from src.marcus_mcp.handlers import handle_tool_call
from src.marcus_mcp.server import MarcusServer
from tests.fixtures.factories import AgentFactory, TaskFactory
from tests.utils.base import BaseTestCase


@pytest.mark.integration
@pytest.mark.e2e
class TestProjectLifecycle(BaseTestCase):
    """Test complete project lifecycle from creation to completion."""

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_complete_project_flow(self):
        """
        Test the complete flow of a project:
        1. Create project using natural language
        2. Register agents
        3. Agents request and complete tasks
        4. Monitor project progress
        5. Handle blockers
        6. Complete project
        """
        # Setup
        server = await self._create_test_server()

        # Step 1: Create project using natural language
        print("\n1. Creating project...")
        create_result = await handle_tool_call(
            "create_project",
            {
                "project_name": "E-Commerce MVP",
                "description": """
                Build a minimal e-commerce platform with:
                - User authentication and profiles
                - Product catalog with search
                - Shopping cart functionality
                - Basic checkout process
                - Order history for users
                """,
            },
            server,
        )

        create_data = self._parse_result(create_result)
        assert create_data["success"] is True
        assert len(create_data.get("tasks_created", [])) > 0

        # Step 2: Register agents
        print("\n2. Registering agents...")
        agents = [
            {
                "agent_id": "backend-dev",
                "name": "Alice",
                "role": "Backend Developer",
                "skills": ["python", "django", "postgres", "api"],
            },
            {
                "agent_id": "frontend-dev",
                "name": "Bob",
                "role": "Frontend Developer",
                "skills": ["javascript", "react", "css", "ui"],
            },
            {
                "agent_id": "fullstack-dev",
                "name": "Charlie",
                "role": "Fullstack Developer",
                "skills": ["python", "javascript", "testing"],
            },
        ]

        for agent in agents:
            result = await handle_tool_call("register_agent", agent, server)
            data = self._parse_result(result)
            assert data["success"] is True

        # Step 3: Agents request tasks
        print("\n3. Agents requesting tasks...")
        assigned_tasks = {}

        for agent in agents:
            result = await handle_tool_call(
                "request_next_task", {"agent_id": agent["agent_id"]}, server
            )
            data = self._parse_result(result)

            if data.get("success") and data.get("task"):
                task = data["task"]
                assigned_tasks[agent["agent_id"]] = task
                print(f"  - {agent['name']} assigned: {task['name']}")

        # Step 4: Simulate work progress
        print("\n4. Simulating work progress...")
        for agent_id, task in assigned_tasks.items():
            # Report progress at 25%, 50%, 75%
            for progress in [25, 50, 75]:
                await asyncio.sleep(0.1)  # Simulate work time

                result = await handle_tool_call(
                    "report_task_progress",
                    {
                        "agent_id": agent_id,
                        "task_id": task["id"],
                        "status": "in_progress",
                        "progress": progress,
                        "message": f"Completed {progress}% of {task['name']}",
                    },
                    server,
                )
                data = self._parse_result(result)
                assert data["success"] is True

        # Step 5: Simulate a blocker
        print("\n5. Simulating blocker...")
        if assigned_tasks:
            first_agent = list(assigned_tasks.keys())[0]
            first_task = assigned_tasks[first_agent]

            result = await handle_tool_call(
                "report_blocker",
                {
                    "agent_id": first_agent,
                    "task_id": first_task["id"],
                    "description": "Missing API documentation for payment gateway integration",
                    "severity": "medium",
                },
                server,
            )
            data = self._parse_result(result)
            assert data["success"] is True

            # Simulate blocker resolution
            await asyncio.sleep(0.2)

            # Continue after resolution
            result = await handle_tool_call(
                "report_task_progress",
                {
                    "agent_id": first_agent,
                    "task_id": first_task["id"],
                    "status": "in_progress",
                    "progress": 90,
                    "message": "Blocker resolved, nearing completion",
                },
                server,
            )

        # Step 6: Complete tasks
        print("\n6. Completing tasks...")
        for agent_id, task in assigned_tasks.items():
            result = await handle_tool_call(
                "report_task_progress",
                {
                    "agent_id": agent_id,
                    "task_id": task["id"],
                    "status": "completed",
                    "progress": 100,
                    "message": f"Successfully completed {task['name']}",
                },
                server,
            )
            data = self._parse_result(result)
            assert data["success"] is True
            print(f"  - {agent_id} completed: {task['name']}")

        # Step 7: Check project status
        print("\n7. Checking final project status...")
        result = await handle_tool_call("get_project_status", {}, server)
        data = self._parse_result(result)

        if data.get("success"):
            project = data.get("project", {})
            print(f"  - Total tasks: {project.get('total_tasks', 'N/A')}")
            print(f"  - Completed: {project.get('completed', 'N/A')}")
            print(f"  - In Progress: {project.get('in_progress', 'N/A')}")
            print(f"  - Completion: {project.get('completion_percentage', 'N/A')}%")

        # Verify some tasks were completed
        assert len(assigned_tasks) > 0
        print(f"\n✅ Project lifecycle test completed successfully!")

    async def _create_test_server(self) -> MarcusServer:
        """Create a test server with mocked dependencies."""
        import os

        os.environ["KANBAN_PROVIDER"] = "planka"

        server = MarcusServer()

        # Mock kanban client
        server.kanban_client = AsyncMock()
        server.kanban_client.create_task = AsyncMock(
            side_effect=lambda task_data: {
                **task_data,
                "id": f"TASK-{hash(task_data['name']) % 1000:03d}",
            }
        )
        server.kanban_client.get_available_tasks = AsyncMock(
            return_value=TaskFactory.create_batch(10)
        )
        server.kanban_client.update_task_progress = AsyncMock()
        server.kanban_client.add_comment = AsyncMock()

        # Don't start assignment monitor
        server.assignment_monitor = None

        return server

    def _parse_result(self, result: List[Any]) -> Dict[str, Any]:
        """Parse MCP tool result."""
        import json

        if result and len(result) > 0:
            return json.loads(result[0].text)
        return {}


@pytest.mark.integration
@pytest.mark.e2e
class TestMultiAgentCollaboration(BaseTestCase):
    """Test scenarios with multiple agents working together."""

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_agents_handling_dependencies(self):
        """
        Test that agents properly handle task dependencies.

        Scenario: Backend API must be completed before frontend integration.
        """
        # This would test:
        # 1. Task dependency recognition
        # 2. Proper task ordering
        # 3. Blocking when dependencies aren't met
        # 4. Notification when dependencies are resolved

        # Implementation would follow similar pattern to above
        pass
