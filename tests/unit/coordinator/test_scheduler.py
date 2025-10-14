"""
Unit tests for task scheduling and CPM algorithm.

Tests the critical path method (CPM) implementation for calculating
optimal agent counts and project schedules.
"""

from datetime import datetime

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.coordinator.scheduler import (
    ProjectSchedule,
    calculate_optimal_agents,
    calculate_task_times,
    detect_cycles,
    topological_sort,
)


class TestTopologicalSort:
    """Test suite for topological sort algorithm."""

    def test_topological_sort_no_dependencies(self):
        """Test sorting tasks with no dependencies."""
        # Arrange
        tasks = [
            Task(
                id="A",
                name="Task A",
                description="First",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=[],
            ),
            Task(
                id="B",
                name="Task B",
                description="Second",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=3.0,
                dependencies=[],
            ),
        ]

        # Act
        sorted_tasks = topological_sort(tasks)

        # Assert
        assert len(sorted_tasks) == 2
        # Order doesn't matter when no dependencies
        assert {t.id for t in sorted_tasks} == {"A", "B"}

    def test_topological_sort_sequential_chain(self):
        """Test sorting tasks in a sequential chain."""
        # Arrange
        tasks = [
            Task(
                id="C",
                name="Task C",
                description="Third",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=["B"],
            ),
            Task(
                id="A",
                name="Task A",
                description="First",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=[],
            ),
            Task(
                id="B",
                name="Task B",
                description="Second",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=3.0,
                dependencies=["A"],
            ),
        ]

        # Act
        sorted_tasks = topological_sort(tasks)

        # Assert
        assert len(sorted_tasks) == 3
        task_ids = [t.id for t in sorted_tasks]
        # A must come before B, B must come before C
        assert task_ids.index("A") < task_ids.index("B")
        assert task_ids.index("B") < task_ids.index("C")

    def test_topological_sort_diamond_dependencies(self):
        """Test sorting tasks with diamond-shaped dependencies."""
        # Arrange
        #     A
        #    / \
        #   B   C
        #    \ /
        #     D
        tasks = [
            Task(
                id="D",
                name="Task D",
                description="Fourth",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=["B", "C"],
            ),
            Task(
                id="B",
                name="Task B",
                description="Second",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=3.0,
                dependencies=["A"],
            ),
            Task(
                id="C",
                name="Task C",
                description="Third",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=["A"],
            ),
            Task(
                id="A",
                name="Task A",
                description="First",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=[],
            ),
        ]

        # Act
        sorted_tasks = topological_sort(tasks)

        # Assert
        assert len(sorted_tasks) == 4
        task_ids = [t.id for t in sorted_tasks]
        # A must come before B and C
        assert task_ids.index("A") < task_ids.index("B")
        assert task_ids.index("A") < task_ids.index("C")
        # B and C must come before D
        assert task_ids.index("B") < task_ids.index("D")
        assert task_ids.index("C") < task_ids.index("D")


class TestCycleDetection:
    """Test suite for cycle detection in dependency graphs."""

    def test_detect_cycles_no_cycle(self):
        """Test that no cycle is detected in valid graph."""
        # Arrange
        tasks = [
            Task(
                id="A",
                name="Task A",
                description="First",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=[],
            ),
            Task(
                id="B",
                name="Task B",
                description="Second",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=3.0,
                dependencies=["A"],
            ),
        ]

        # Act
        has_cycle = detect_cycles(tasks)

        # Assert
        assert has_cycle is False

    def test_detect_cycles_simple_cycle(self):
        """Test detection of simple two-task cycle."""
        # Arrange - A depends on B, B depends on A
        tasks = [
            Task(
                id="A",
                name="Task A",
                description="First",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=["B"],
            ),
            Task(
                id="B",
                name="Task B",
                description="Second",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=3.0,
                dependencies=["A"],
            ),
        ]

        # Act
        has_cycle = detect_cycles(tasks)

        # Assert
        assert has_cycle is True

    def test_detect_cycles_complex_cycle(self):
        """Test detection of cycle in complex graph."""
        # Arrange - A → B → C → D → B (cycle at B-C-D)
        tasks = [
            Task(
                id="A",
                name="Task A",
                description="First",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=[],
            ),
            Task(
                id="B",
                name="Task B",
                description="Second",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=3.0,
                dependencies=["A", "D"],
            ),
            Task(
                id="C",
                name="Task C",
                description="Third",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=["B"],
            ),
            Task(
                id="D",
                name="Task D",
                description="Fourth",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=["C"],
            ),
        ]

        # Act
        has_cycle = detect_cycles(tasks)

        # Assert
        assert has_cycle is True


class TestCalculateTaskTimes:
    """Test suite for calculating earliest start/finish times."""

    def test_calculate_task_times_sequential(self):
        """Test time calculation for sequential tasks."""
        # Arrange - A(2h) → B(3h) → C(2h)
        tasks = [
            Task(
                id="A",
                name="Task A",
                description="First",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=[],
            ),
            Task(
                id="B",
                name="Task B",
                description="Second",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=3.0,
                dependencies=["A"],
            ),
            Task(
                id="C",
                name="Task C",
                description="Third",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=["B"],
            ),
        ]

        # Act
        task_times = calculate_task_times(tasks)

        # Assert
        assert task_times["A"]["start"] == 0
        assert task_times["A"]["finish"] == 2.0
        assert task_times["B"]["start"] == 2.0
        assert task_times["B"]["finish"] == 5.0
        assert task_times["C"]["start"] == 5.0
        assert task_times["C"]["finish"] == 7.0

    def test_calculate_task_times_parallel(self):
        """Test time calculation for parallel tasks."""
        # Arrange - A(2h), B(3h) both start at 0
        tasks = [
            Task(
                id="A",
                name="Task A",
                description="First",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=[],
            ),
            Task(
                id="B",
                name="Task B",
                description="Second",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=3.0,
                dependencies=[],
            ),
        ]

        # Act
        task_times = calculate_task_times(tasks)

        # Assert
        # Both can start immediately
        assert task_times["A"]["start"] == 0
        assert task_times["B"]["start"] == 0
        assert task_times["A"]["finish"] == 2.0
        assert task_times["B"]["finish"] == 3.0

    def test_calculate_task_times_diamond(self):
        """Test time calculation for diamond dependencies."""
        # Arrange
        #     A(2h)
        #    / \
        # B(3h) C(2h)
        #    \ /
        #    D(1h)
        tasks = [
            Task(
                id="A",
                name="Task A",
                description="First",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=[],
            ),
            Task(
                id="B",
                name="Task B",
                description="Second",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=3.0,
                dependencies=["A"],
            ),
            Task(
                id="C",
                name="Task C",
                description="Third",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=["A"],
            ),
            Task(
                id="D",
                name="Task D",
                description="Fourth",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=1.0,
                dependencies=["B", "C"],
            ),
        ]

        # Act
        task_times = calculate_task_times(tasks)

        # Assert
        assert task_times["A"]["start"] == 0
        assert task_times["A"]["finish"] == 2.0
        # B and C can both start at 2.0
        assert task_times["B"]["start"] == 2.0
        assert task_times["C"]["start"] == 2.0
        assert task_times["B"]["finish"] == 5.0
        assert task_times["C"]["finish"] == 4.0
        # D must wait for B (finishes at 5.0, later than C at 4.0)
        assert task_times["D"]["start"] == 5.0
        assert task_times["D"]["finish"] == 6.0


class TestCalculateOptimalAgents:
    """Test suite for optimal agent calculation."""

    def test_calculate_optimal_agents_sequential(self):
        """Test optimal agents for sequential tasks."""
        # Arrange - A(2h) → B(3h) → C(2h) = 7h total, 7h critical path
        tasks = [
            Task(
                id="A",
                name="Task A",
                description="First",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=[],
            ),
            Task(
                id="B",
                name="Task B",
                description="Second",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=3.0,
                dependencies=["A"],
            ),
            Task(
                id="C",
                name="Task C",
                description="Third",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=["B"],
            ),
        ]

        # Act
        schedule = calculate_optimal_agents(tasks)

        # Assert
        assert schedule.optimal_agents == 1
        assert schedule.critical_path_hours == 7.0
        assert schedule.max_parallelism == 1
        assert schedule.single_agent_hours == 7.0
        assert schedule.efficiency_gain == 0.0

    def test_calculate_optimal_agents_fully_parallel(self):
        """Test optimal agents for fully parallel tasks."""
        # Arrange - A(2h), B(3h), C(2h) all independent = 7h total, 3h critical path
        tasks = [
            Task(
                id="A",
                name="Task A",
                description="First",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=[],
            ),
            Task(
                id="B",
                name="Task B",
                description="Second",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=3.0,
                dependencies=[],
            ),
            Task(
                id="C",
                name="Task C",
                description="Third",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=[],
            ),
        ]

        # Act
        schedule = calculate_optimal_agents(tasks)

        # Assert
        assert schedule.optimal_agents == 3
        assert schedule.critical_path_hours == 3.0  # Longest single task
        assert schedule.max_parallelism == 3
        assert schedule.single_agent_hours == 7.0
        # Efficiency: (7 - 3) / 7 = 57.14%
        assert schedule.efficiency_gain > 0.57

    def test_calculate_optimal_agents_mixed(self):
        """Test optimal agents for mixed sequential/parallel tasks."""
        # Arrange - Example from design doc
        #     A(2h)
        #    / \
        # B(3h) C(2h) D(2h) (C and D parallel)
        #    \ /
        #    E(1h)
        tasks = [
            Task(
                id="A",
                name="Task A",
                description="First",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=[],
            ),
            Task(
                id="B",
                name="Task B",
                description="Second",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=3.0,
                dependencies=["A"],
            ),
            Task(
                id="C",
                name="Task C",
                description="Third",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=["A"],
            ),
            Task(
                id="D",
                name="Task D",
                description="Fourth",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=["A"],
            ),
            Task(
                id="E",
                name="Task E",
                description="Fifth",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=1.0,
                dependencies=["B", "C"],
            ),
        ]

        # Act
        schedule = calculate_optimal_agents(tasks)

        # Assert
        # Critical path: A(2) → B(3) → E(1) = 6h
        assert schedule.critical_path_hours == 6.0
        # Max parallelism: 3 tasks (B, C, D) can run at same time after A
        assert schedule.max_parallelism == 3
        # Optimal: Use max_parallelism (peak demand) since agents can't auto-scale
        assert schedule.optimal_agents == 3
        assert schedule.single_agent_hours == 10.0

    def test_calculate_optimal_agents_with_subtasks(self):
        """Test optimal agents calculation includes subtasks."""
        # Arrange - Parent A with subtasks A1, A2
        tasks = [
            Task(
                id="A",
                name="Task A",
                description="Parent",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=5.0,
                dependencies=[],
                is_subtask=False,
            ),
            Task(
                id="A_sub_1",
                name="Subtask A1",
                description="First subtask",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                dependencies=[],
                is_subtask=True,
                parent_task_id="A",
                subtask_index=0,
            ),
            Task(
                id="A_sub_2",
                name="Subtask A2",
                description="Second subtask",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=3.0,
                dependencies=["A_sub_1"],
                is_subtask=True,
                parent_task_id="A",
                subtask_index=1,
            ),
        ]

        # Act
        schedule = calculate_optimal_agents(tasks)

        # Assert
        # All 3 tasks are in the graph, but parent is likely a container
        # Critical path through subtasks: A_sub_1(2) → A_sub_2(3) = 5h
        assert schedule.critical_path_hours >= 5.0
        assert schedule.optimal_agents >= 1


class TestProjectSchedule:
    """Test suite for ProjectSchedule dataclass."""

    def test_project_schedule_creation(self):
        """Test creating ProjectSchedule with all fields."""
        # Arrange & Act
        schedule = ProjectSchedule(
            optimal_agents=3,
            critical_path_hours=10.0,
            max_parallelism=3,
            estimated_completion_hours=10.0,
            single_agent_hours=15.0,
            efficiency_gain=0.33,
            parallel_opportunities=[
                {"time": 0, "task_count": 3, "tasks": ["A", "B", "C"]}
            ],
        )

        # Assert
        assert schedule.optimal_agents == 3
        assert schedule.critical_path_hours == 10.0
        assert schedule.max_parallelism == 3
        assert schedule.estimated_completion_hours == 10.0
        assert schedule.single_agent_hours == 15.0
        assert schedule.efficiency_gain == 0.33
        assert len(schedule.parallel_opportunities) == 1
