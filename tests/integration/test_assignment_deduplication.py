"""
Test suite for preventing duplicate task assignments in Marcus.

This module tests the long-term fix for the duplicate assignment issue where
multiple workers can be assigned the same task.
"""

import asyncio
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.core.assignment_persistence import AssignmentPersistence
from src.core.models import Priority, Task, TaskStatus, WorkerStatus
from src.integrations.kanban_interface import KanbanInterface

# Import the components we'll be testing
from src.marcus_mcp.server import MarcusServer
from src.marcus_mcp.tools.task import find_optimal_task_for_agent, request_next_task


class TestAssignmentDeduplication:
    """Test cases for preventing duplicate task assignments."""

    @pytest.fixture
    def mock_kanban_client(self):
        """Create a mock kanban client."""
        client = AsyncMock(spec=KanbanInterface)
        client.get_available_tasks = AsyncMock(return_value=[])
        client.update_task = AsyncMock()
        client.add_comment = AsyncMock()
        return client

    @pytest.fixture
    def marcus_server(self, mock_kanban_client):
        """Create a Marcus server instance for testing."""
        server = MarcusServer()
        server.kanban_client = mock_kanban_client
        server.assignment_persistence = AssignmentPersistence()
        server.assignment_monitor = None  # Disable monitor for tests
        return server

    @pytest.fixture
    def sample_tasks(self):
        """Create sample tasks for testing."""
        return [
            Task(
                id="task-1",
                name="Implement user authentication",
                description="Add JWT-based auth",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                labels=["backend", "security"],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            Task(
                id="task-2",
                name="Create login UI",
                description="Design and implement login form",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                labels=["frontend", "ui"],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            Task(
                id="task-3",
                name="Write API tests",
                description="Test authentication endpoints",
                status=TaskStatus.TODO,
                priority=Priority.LOW,
                labels=["testing", "backend"],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
        ]

    @pytest.fixture
    def sample_agents(self):
        """Create sample agents for testing."""
        return {
            "agent-1": WorkerStatus(
                worker_id="agent-1",
                name="Backend Developer",
                role="Backend Developer",
                current_tasks=[],
                completed_tasks_count=5,
                capacity=40,
                skills=["python", "backend", "security"],
                availability={},
                performance_score=1.2,
            ),
            "agent-2": WorkerStatus(
                worker_id="agent-2",
                name="Frontend Developer",
                role="Frontend Developer",
                current_tasks=[],
                completed_tasks_count=3,
                capacity=40,
                skills=["javascript", "frontend", "ui"],
                availability={},
                performance_score=1.0,
            ),
            "agent-3": WorkerStatus(
                worker_id="agent-3",
                name="QA Engineer",
                role="QA Engineer",
                current_tasks=[],
                completed_tasks_count=8,
                capacity=40,
                skills=["testing", "automation"],
                availability={},
                performance_score=1.1,
            ),
        }

    @pytest.mark.asyncio
    async def test_sequential_assignment_prevents_duplicates(
        self, marcus_server, mock_kanban_client, sample_tasks, sample_agents
    ):
        """Test that sequential task requests don't assign the same task twice."""
        # Setup
        marcus_server.agent_status = sample_agents
        mock_kanban_client.get_available_tasks.return_value = sample_tasks

        # First agent requests a task
        result1 = await request_next_task("agent-1", marcus_server)
        assert result1["task"] is not None
        task1_id = result1["task"]["id"]

        # Verify task is tracked as assigned
        assert task1_id in marcus_server.tasks_being_assigned

        # Second agent requests a task - should get different task
        result2 = await request_next_task("agent-2", marcus_server)
        assert result2["task"] is not None
        task2_id = result2["task"]["id"]

        # Verify different tasks were assigned
        assert task1_id != task2_id
        assert task2_id in marcus_server.tasks_being_assigned

        # Third agent requests a task
        result3 = await request_next_task("agent-3", marcus_server)
        assert result3["task"] is not None
        task3_id = result3["task"]["id"]

        # All three tasks should be different
        assert len({task1_id, task2_id, task3_id}) == 3

    @pytest.mark.asyncio
    async def test_concurrent_assignment_with_lock(
        self, marcus_server, mock_kanban_client, sample_tasks, sample_agents
    ):
        """Test that concurrent requests with proper locking prevent duplicates."""
        # Setup
        marcus_server.agent_status = sample_agents
        mock_kanban_client.get_available_tasks.return_value = sample_tasks

        # Create concurrent requests
        async def request_task(agent_id):
            return await request_next_task(agent_id, marcus_server)

        # Run three agents concurrently
        results = await asyncio.gather(
            request_task("agent-1"), request_task("agent-2"), request_task("agent-3")
        )

        # Extract assigned task IDs
        assigned_task_ids = [r["task"]["id"] for r in results if r["task"] is not None]

        # Verify no duplicates
        assert len(assigned_task_ids) == len(set(assigned_task_ids))
        assert len(assigned_task_ids) == 3  # All agents got tasks

    @pytest.mark.asyncio
    async def test_task_filtering_excludes_assigned(
        self, marcus_server, mock_kanban_client, sample_tasks, sample_agents
    ):
        """Test that find_optimal_task_for_agent filters out already assigned tasks."""
        # Setup
        marcus_server.agent_status = sample_agents
        agent = sample_agents["agent-1"]

        # Mark task-1 as already assigned
        marcus_server.tasks_being_assigned.add("task-1")

        # Find optimal task - should not include task-1
        optimal_task = await find_optimal_task_for_agent(
            agent, sample_tasks, marcus_server
        )

        assert optimal_task is not None
        assert optimal_task.id != "task-1"

    @pytest.mark.asyncio
    async def test_assignment_persistence(
        self, marcus_server, mock_kanban_client, sample_tasks, sample_agents
    ):
        """Test that assignments are persisted correctly."""
        # Setup
        marcus_server.agent_status = sample_agents
        mock_kanban_client.get_available_tasks.return_value = sample_tasks

        # Create assignment
        result = await request_next_task("agent-1", marcus_server)
        assert result["task"] is not None

        # Verify assignment is persisted
        task_id = result["task"]["id"]
        agent_id = "agent-1"

        assert agent_id in marcus_server.agent_tasks
        assignment = marcus_server.agent_tasks[agent_id]
        assert assignment.task_id == task_id
        assert assignment.agent_id == agent_id

        # Verify persistence file exists
        assignments = marcus_server.assignment_persistence.load_assignments()
        assert agent_id in assignments
        assert assignments[agent_id]["task_id"] == task_id

    @pytest.mark.asyncio
    async def test_no_suitable_tasks_when_all_assigned(
        self, marcus_server, mock_kanban_client, sample_tasks, sample_agents
    ):
        """Test behavior when all tasks are already assigned."""
        # Setup
        marcus_server.agent_status = sample_agents
        mock_kanban_client.get_available_tasks.return_value = sample_tasks

        # Mark all tasks as assigned
        for task in sample_tasks:
            marcus_server.tasks_being_assigned.add(task.id)

        # Request should return no task
        result = await request_next_task("agent-1", marcus_server)
        assert result["task"] is None
        assert result["message"] == "No suitable tasks available"

    @pytest.mark.asyncio
    async def test_task_reassignment_after_completion(
        self, marcus_server, mock_kanban_client, sample_tasks, sample_agents
    ):
        """Test that completed tasks can be reassigned."""
        # Setup
        marcus_server.agent_status = sample_agents
        mock_kanban_client.get_available_tasks.return_value = sample_tasks

        # Assign task to agent-1
        result1 = await request_next_task("agent-1", marcus_server)
        task_id = result1["task"]["id"]

        # Mark task as completed (would normally happen via report_task_progress)
        marcus_server.tasks_being_assigned.discard(task_id)
        if "agent-1" in marcus_server.agent_tasks:
            del marcus_server.agent_tasks["agent-1"]

        # Same task should now be available for assignment
        result2 = await request_next_task("agent-2", marcus_server)

        # Could get the same task since it's no longer marked as assigned
        assert result2["task"] is not None

    @pytest.mark.asyncio
    async def test_concurrent_assignment_stress_test(
        self, marcus_server, mock_kanban_client, sample_agents
    ):
        """Stress test with many concurrent agents and limited tasks."""
        # Create 10 tasks
        tasks = [
            Task(
                id=f"task-{i}",
                name=f"Task {i}",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                labels=["test"],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            for i in range(10)
        ]

        # Create 20 agents
        agents = {}
        for i in range(20):
            agent_id = f"agent-{i}"
            agents[agent_id] = WorkerStatus(
                worker_id=agent_id,
                name=f"Agent {i}",
                role="Developer",
                current_tasks=[],
                completed_tasks_count=0,
                capacity=40,
                skills=["test"],
                availability={},
                performance_score=1.0,
            )

        # Setup
        marcus_server.agent_status = agents
        mock_kanban_client.get_available_tasks.return_value = tasks

        # Create concurrent requests from all 20 agents
        async def request_task(agent_id):
            return await request_next_task(agent_id, marcus_server)

        # Run all agents concurrently
        results = await asyncio.gather(*[request_task(f"agent-{i}") for i in range(20)])

        # Count successful assignments
        assigned_tasks = [r["task"]["id"] for r in results if r["task"] is not None]

        # Should have exactly 10 assignments (one per task)
        assert len(assigned_tasks) == 10

        # No duplicates
        assert len(set(assigned_tasks)) == 10

        # Remaining 10 agents should have no task
        no_task_count = sum(1 for r in results if r["task"] is None)
        assert no_task_count == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
