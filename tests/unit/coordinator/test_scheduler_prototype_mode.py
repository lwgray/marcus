"""
Unit tests for scheduler support of prototype mode and parent-only projects.

Tests verify that calculate_optimal_agents() correctly schedules:
1. Parent tasks when no subtasks exist (prototype mode)
2. Subtasks when they exist (standard mode)
3. Mixed scenarios with both parents and subtasks
"""

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.coordinator.scheduler import calculate_optimal_agents


class TestSchedulerPrototypeMode:
    """Test scheduler handles prototype mode (no subtasks) correctly."""

    @pytest.fixture
    def prototype_tasks(self):
        """Create parent tasks without subtasks (prototype mode)."""
        return [
            Task(
                id="task_1",
                name="Design Calculator",
                description="Design the calculator",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                estimated_hours=0.1,
                dependencies=[],
                labels=["type:design"],
                is_subtask=False,
            ),
            Task(
                id="task_2",
                name="Implement Addition",
                description="Implement addition feature",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                estimated_hours=0.1,
                dependencies=["task_1"],
                labels=["type:implementation"],
                is_subtask=False,
            ),
            Task(
                id="task_3",
                name="Implement Division",
                description="Implement division with error handling",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                estimated_hours=0.1,
                dependencies=["task_1"],
                labels=["type:implementation"],
                is_subtask=False,
            ),
        ]

    def test_prototype_mode_schedules_parent_tasks(self, prototype_tasks):
        """Test that parent tasks are scheduled when no subtasks exist."""
        # Act
        schedule = calculate_optimal_agents(prototype_tasks)

        # Assert - should schedule parent tasks, not return 0
        assert (
            schedule.optimal_agents > 0
        ), "Prototype mode should schedule parent tasks, not return 0 agents"
        assert (
            schedule.max_parallelism > 0
        ), "Should detect parallel opportunities in independent parent tasks"

    def test_prototype_mode_detects_parallelism(self, prototype_tasks):
        """Test that independent parent tasks can run in parallel."""
        # Act
        schedule = calculate_optimal_agents(prototype_tasks)

        # Assert - task_2 and task_3 both depend on task_1, so can run in parallel
        assert schedule.max_parallelism == 2, (
            f"Expected 2 parallel tasks (implement tasks after design), "
            f"got {schedule.max_parallelism}"
        )

    def test_prototype_mode_calculates_critical_path(self, prototype_tasks):
        """Test that critical path is calculated for parent tasks."""
        # Act
        schedule = calculate_optimal_agents(prototype_tasks)

        # Assert - critical path should be design (0.1h) + implement (0.1h) = 0.2h
        assert schedule.critical_path_hours == pytest.approx(
            0.2, abs=0.01
        ), f"Expected critical path of 0.2 hours, got {schedule.critical_path_hours}"

    def test_empty_task_list_returns_zero(self):
        """Test that empty task list returns zero agents."""
        # Act
        schedule = calculate_optimal_agents([])

        # Assert
        assert schedule.optimal_agents == 0
        assert schedule.max_parallelism == 0
        assert schedule.critical_path_hours == 0.0


class TestSchedulerStandardMode:
    """Test scheduler handles standard mode (with subtasks) correctly."""

    @pytest.fixture
    def standard_tasks(self):
        """Create parent tasks with subtasks (standard mode)."""
        return [
            # Parent task
            Task(
                id="task_1",
                name="Design Calculator",
                description="Design the calculator",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                estimated_hours=2.0,
                dependencies=[],
                labels=["type:design"],
                is_subtask=False,
            ),
            # Subtasks of task_1
            Task(
                id="task_1_sub_1",
                name="Create UI mockups",
                description="Design UI",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                estimated_hours=1.0,
                dependencies=[],
                labels=["type:design"],
                is_subtask=True,
                parent_task_id="task_1",
            ),
            Task(
                id="task_1_sub_2",
                name="Define API contract",
                description="Define API",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                estimated_hours=1.0,
                dependencies=[],
                labels=["type:design"],
                is_subtask=True,
                parent_task_id="task_1",
            ),
        ]

    def test_standard_mode_schedules_only_subtasks(self, standard_tasks):
        """Test that only subtasks are scheduled when they exist."""
        # Act
        schedule = calculate_optimal_agents(standard_tasks)

        # Assert - should schedule 2 subtasks, not the parent
        assert (
            schedule.optimal_agents == 2
        ), f"Expected 2 agents for 2 parallel subtasks, got {schedule.optimal_agents}"
        assert (
            schedule.max_parallelism == 2
        ), f"Expected 2 parallel subtasks, got {schedule.max_parallelism}"

    def test_standard_mode_ignores_parent_tasks(self, standard_tasks):
        """Test that parent tasks don't inflate parallelism in standard mode."""
        # Act
        schedule = calculate_optimal_agents(standard_tasks)

        # Assert - critical path should be 1.0h (one subtask), not 2.0h (parent)
        assert schedule.critical_path_hours == pytest.approx(
            1.0, abs=0.01
        ), f"Parent task should be ignored, got {schedule.critical_path_hours}h"


class TestSchedulerMixedMode:
    """Test scheduler handles edge cases with mixed task types."""

    def test_completed_tasks_excluded(self):
        """Test that completed tasks are not scheduled."""
        # Arrange
        tasks = [
            Task(
                id="task_1",
                name="Done Task",
                description="Already done",
                status=TaskStatus.DONE,
                priority=Priority.MEDIUM,
                estimated_hours=1.0,
                dependencies=[],
                labels=[],
                is_subtask=False,
            ),
            Task(
                id="task_2",
                name="Todo Task",
                description="Still to do",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                estimated_hours=1.0,
                dependencies=[],
                labels=[],
                is_subtask=False,
            ),
        ]

        # Act
        schedule = calculate_optimal_agents(tasks)

        # Assert - should only schedule the TODO task
        assert (
            schedule.optimal_agents == 1
        ), f"Should schedule 1 task, got {schedule.optimal_agents}"

    def test_all_completed_returns_zero(self):
        """Test that all completed tasks returns zero agents."""
        # Arrange
        tasks = [
            Task(
                id="task_1",
                name="Done Task 1",
                description="Done",
                status=TaskStatus.DONE,
                priority=Priority.MEDIUM,
                estimated_hours=1.0,
                dependencies=[],
                labels=[],
                is_subtask=False,
            ),
            Task(
                id="task_2",
                name="Done Task 2",
                description="Done",
                status=TaskStatus.DONE,
                priority=Priority.MEDIUM,
                estimated_hours=1.0,
                dependencies=[],
                labels=[],
                is_subtask=False,
            ),
        ]

        # Act
        schedule = calculate_optimal_agents(tasks)

        # Assert
        assert schedule.optimal_agents == 0
        assert schedule.max_parallelism == 0

    def test_tasks_without_is_subtask_attribute(self):
        """Test backward compatibility with tasks missing is_subtask attribute."""
        # Arrange - simulate old Task objects without is_subtask field
        task = Task(
            id="task_1",
            name="Old Task",
            description="Task without is_subtask",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=1.0,
            dependencies=[],
            labels=[],
        )
        # Remove is_subtask attribute if it exists
        if hasattr(task, "is_subtask"):
            delattr(task, "is_subtask")

        # Act - should not crash
        schedule = calculate_optimal_agents([task])

        # Assert - should schedule the task
        assert schedule.optimal_agents > 0, "Should handle tasks without is_subtask"

    def test_mixed_project_with_atomic_and_decomposed_tasks(self):
        """Test hybrid project with both atomic parents and decomposed parents."""
        # Arrange - Create mixed project:
        # - Parent A: Decomposed into 2 subtasks
        # - Parent B: Atomic (no subtasks)
        # - Parent C: Decomposed into 2 subtasks
        tasks = [
            # Parent A (container - should be excluded)
            Task(
                id="parent_a",
                name="Parent A",
                description="Parent with subtasks",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                estimated_hours=2.0,
                dependencies=[],
                labels=[],
                is_subtask=False,
            ),
            # Parent A subtasks (should be included)
            Task(
                id="parent_a_sub_1",
                name="Subtask A1",
                description="First subtask",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                estimated_hours=1.0,
                dependencies=[],
                labels=[],
                is_subtask=True,
                parent_task_id="parent_a",
            ),
            Task(
                id="parent_a_sub_2",
                name="Subtask A2",
                description="Second subtask",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                estimated_hours=1.0,
                dependencies=[],
                labels=[],
                is_subtask=True,
                parent_task_id="parent_a",
            ),
            # Parent B (atomic - should be included)
            Task(
                id="parent_b",
                name="Parent B",
                description="Parent without subtasks (atomic)",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                estimated_hours=1.0,
                dependencies=[],
                labels=[],
                is_subtask=False,
            ),
            # Parent C (container - should be excluded)
            Task(
                id="parent_c",
                name="Parent C",
                description="Parent with subtasks",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                estimated_hours=2.0,
                dependencies=[],
                labels=[],
                is_subtask=False,
            ),
            # Parent C subtasks (should be included)
            Task(
                id="parent_c_sub_1",
                name="Subtask C1",
                description="First subtask",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                estimated_hours=1.0,
                dependencies=[],
                labels=[],
                is_subtask=True,
                parent_task_id="parent_c",
            ),
            Task(
                id="parent_c_sub_2",
                name="Subtask C2",
                description="Second subtask",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                estimated_hours=1.0,
                dependencies=[],
                labels=[],
                is_subtask=True,
                parent_task_id="parent_c",
            ),
        ]

        # Act
        schedule = calculate_optimal_agents(tasks)

        # Assert - Should schedule 5 tasks:
        # - 2 subtasks from parent_a
        # - 1 atomic parent_b
        # - 2 subtasks from parent_c
        # Parents A and C should be excluded (they're containers)
        assert (
            schedule.optimal_agents == 5
        ), f"Expected 5 agents (all tasks independent), got {schedule.optimal_agents}"
        assert (
            schedule.max_parallelism == 5
        ), f"Expected 5 parallel tasks, got {schedule.max_parallelism}"

        # Critical path should be 1.0h (all tasks are independent and take 1.0h)
        assert schedule.critical_path_hours == pytest.approx(
            1.0, abs=0.01
        ), f"Expected critical path of 1.0h, got {schedule.critical_path_hours}h"
