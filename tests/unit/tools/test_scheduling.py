"""
Unit tests for scheduling tools (optimal agent calculation).
"""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.tools.scheduling import get_optimal_agent_count


class TestGetOptimalAgentCount:
    """Test suite for optimal agent count calculation."""

    @pytest.fixture
    def mock_state(self):
        """Create mock state with tasks."""
        state = Mock()
        state.project_tasks = []
        return state

    @pytest.mark.asyncio
    async def test_no_tasks_returns_zero_agents(self, mock_state):
        """Test that empty project returns 0 agents."""
        result = await get_optimal_agent_count(state=mock_state)

        assert result["success"] is True
        assert result["optimal_agents"] == 0
        assert result["critical_path_hours"] == 0.0
        assert "No tasks available" in result["message"]

    @pytest.mark.asyncio
    async def test_single_task_returns_one_agent(self, mock_state):
        """Test that single task returns 1 agent."""
        mock_state.project_tasks = [
            Task(
                id="task1",
                name="Task 1",
                description="Single task",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=5.0,
                dependencies=[],
            )
        ]

        result = await get_optimal_agent_count(state=mock_state)

        assert result["success"] is True
        assert result["optimal_agents"] == 1
        assert result["critical_path_hours"] == 5.0
        assert result["single_agent_hours"] == 5.0
        assert result["max_parallelism"] == 1

    @pytest.mark.asyncio
    async def test_parallel_tasks_returns_multiple_agents(self, mock_state):
        """Test that parallel tasks return multiple agents."""
        # 3 independent tasks that can run in parallel
        mock_state.project_tasks = [
            Task(
                id="task1",
                name="Task 1",
                description="First task",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=4.0,
                dependencies=[],
            ),
            Task(
                id="task2",
                name="Task 2",
                description="Second task",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=4.0,
                dependencies=[],
            ),
            Task(
                id="task3",
                name="Task 3",
                description="Third task",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=4.0,
                dependencies=[],
            ),
        ]

        result = await get_optimal_agent_count(state=mock_state)

        assert result["success"] is True
        assert result["optimal_agents"] == 3  # All 3 can run in parallel
        assert result["critical_path_hours"] == 4.0  # Longest task
        assert result["single_agent_hours"] == 12.0  # Total work
        assert result["max_parallelism"] == 3
        assert result["efficiency_gain_percent"] > 0

    @pytest.mark.asyncio
    async def test_sequential_tasks_returns_one_agent(self, mock_state):
        """Test that sequential tasks return 1 agent."""
        # 3 tasks in a chain: task1 → task2 → task3
        mock_state.project_tasks = [
            Task(
                id="task1",
                name="Task 1",
                description="First task",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=3.0,
                dependencies=[],
            ),
            Task(
                id="task2",
                name="Task 2",
                description="Second task",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=3.0,
                dependencies=["task1"],
            ),
            Task(
                id="task3",
                name="Task 3",
                description="Third task",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=3.0,
                dependencies=["task2"],
            ),
        ]

        result = await get_optimal_agent_count(state=mock_state)

        assert result["success"] is True
        assert result["optimal_agents"] == 1  # Sequential chain
        assert result["critical_path_hours"] == 9.0  # Sum of all tasks
        assert result["single_agent_hours"] == 9.0
        assert result["max_parallelism"] == 1
        assert result["efficiency_gain_percent"] == 0.0  # No parallelism benefit

    @pytest.mark.asyncio
    async def test_mixed_dependencies_calculates_correctly(self, mock_state):
        """Test mixed parallel and sequential dependencies."""
        # Diamond pattern: task1 → (task2, task3) → task4
        mock_state.project_tasks = [
            Task(
                id="task1",
                name="Task 1",
                description="Start",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=2.0,
                dependencies=[],
            ),
            Task(
                id="task2",
                name="Task 2",
                description="Parallel 1",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=3.0,
                dependencies=["task1"],
            ),
            Task(
                id="task3",
                name="Task 3",
                description="Parallel 2",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=3.0,
                dependencies=["task1"],
            ),
            Task(
                id="task4",
                name="Task 4",
                description="End",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=2.0,
                dependencies=["task2", "task3"],
            ),
        ]

        result = await get_optimal_agent_count(state=mock_state)

        assert result["success"] is True
        assert result["optimal_agents"] == 2  # task2 and task3 can run in parallel
        assert result["critical_path_hours"] == 7.0  # task1 + task2 + task4 (or task3)
        assert result["single_agent_hours"] == 10.0  # Total work
        assert result["max_parallelism"] == 2
        assert result["efficiency_gain_percent"] > 0

    @pytest.mark.asyncio
    async def test_include_details_returns_parallel_opportunities(self, mock_state):
        """Test that include_details flag returns parallel opportunities."""
        mock_state.project_tasks = [
            Task(
                id="task1",
                name="Task 1",
                description="Task",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=2.0,
                dependencies=[],
            ),
            Task(
                id="task2",
                name="Task 2",
                description="Task",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=2.0,
                dependencies=[],
            ),
        ]

        result = await get_optimal_agent_count(include_details=True, state=mock_state)

        assert result["success"] is True
        assert "parallel_opportunities" in result
        assert len(result["parallel_opportunities"]) > 0
        assert result["parallel_opportunities"][0]["task_count"] == 2

    @pytest.mark.asyncio
    async def test_circular_dependency_returns_error(self, mock_state):
        """Test that circular dependencies are detected."""
        # Create circular dependency: task1 → task2 → task1
        mock_state.project_tasks = [
            Task(
                id="task1",
                name="Task 1",
                description="Task",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=2.0,
                dependencies=["task2"],
            ),
            Task(
                id="task2",
                name="Task 2",
                description="Task",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=2.0,
                dependencies=["task1"],
            ),
        ]

        result = await get_optimal_agent_count(state=mock_state)

        assert result["success"] is False
        assert "cycle" in result["error"].lower()
        assert "suggestion" in result

    @pytest.mark.asyncio
    async def test_no_state_returns_error(self):
        """Test that missing state returns error."""
        result = await get_optimal_agent_count(state=None)

        assert result["success"] is False
        assert "not available" in result["error"]

    @pytest.mark.asyncio
    async def test_includes_subtasks_in_calculation(self, mock_state):
        """Test that subtasks are included in optimal agent calculation."""
        # Parent task + 2 subtasks
        mock_state.project_tasks = [
            Task(
                id="parent1",
                name="Parent Task",
                description="Parent",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=10.0,
                dependencies=[],
            ),
            Task(
                id="parent1_sub_1",
                name="Subtask 1",
                description="Subtask",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=3.0,
                dependencies=[],
                is_subtask=True,
                parent_task_id="parent1",
                subtask_index=0,
            ),
            Task(
                id="parent1_sub_2",
                name="Subtask 2",
                description="Subtask",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=3.0,
                dependencies=[],
                is_subtask=True,
                parent_task_id="parent1",
                subtask_index=1,
            ),
        ]

        result = await get_optimal_agent_count(state=mock_state)

        assert result["success"] is True
        # All 3 tasks included in calculation
        assert result["total_tasks"] == 3
        # Parent + subtasks can run in parallel (max 3 agents)
        assert result["optimal_agents"] <= 3
