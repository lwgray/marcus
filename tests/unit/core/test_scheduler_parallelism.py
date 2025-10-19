"""
Unit tests for parallelism calculation in scheduler.

Tests the sweep-line algorithm that correctly handles overlapping task intervals.
"""

import pytest

from src.marcus_mcp.coordinator.scheduler import _calculate_max_parallelism


class TestCalculateMaxParallelism:
    """Test suite for _calculate_max_parallelism function."""

    def test_empty_task_times(self):
        """Test parallelism calculation with no tasks."""
        # Arrange
        task_times = {}

        # Act
        result = _calculate_max_parallelism(task_times)

        # Assert
        assert result == 0

    def test_single_task(self):
        """Test parallelism with a single task."""
        # Arrange
        task_times = {"task1": {"start": 0.0, "finish": 10.0, "task": None}}

        # Act
        result = _calculate_max_parallelism(task_times)

        # Assert
        assert result == 1

    def test_sequential_tasks_no_overlap(self):
        """Test tasks that run sequentially with no overlap."""
        # Arrange
        # Task A: [0────10]
        # Task B:          [10────20]
        task_times = {
            "task1": {"start": 0.0, "finish": 10.0, "task": None},
            "task2": {"start": 10.0, "finish": 20.0, "task": None},
        }

        # Act
        result = _calculate_max_parallelism(task_times)

        # Assert
        assert result == 1

    def test_two_overlapping_tasks(self):
        """Test two tasks that overlap in time."""
        # Arrange
        # Task A: [0────────10]
        # Task B:      [5────────15]
        task_times = {
            "task1": {"start": 0.0, "finish": 10.0, "task": None},
            "task2": {"start": 5.0, "finish": 15.0, "task": None},
        }

        # Act
        result = _calculate_max_parallelism(task_times)

        # Assert
        assert result == 2

    def test_three_overlapping_tasks(self):
        """Test three tasks with varying overlaps."""
        # Arrange
        # Task A: [0────────10]
        # Task B:      [5────────15]
        # Task C:           [8──13]
        task_times = {
            "task1": {"start": 0.0, "finish": 10.0, "task": None},
            "task2": {"start": 5.0, "finish": 15.0, "task": None},
            "task3": {"start": 8.0, "finish": 13.0, "task": None},
        }

        # Act
        result = _calculate_max_parallelism(task_times)

        # Assert
        assert result == 3

    def test_tasks_starting_at_same_time(self):
        """Test multiple tasks that start at the exact same time."""
        # Arrange
        # Task A: [0────10]
        # Task B: [0────────15]
        # Task C: [0──5]
        task_times = {
            "task1": {"start": 0.0, "finish": 10.0, "task": None},
            "task2": {"start": 0.0, "finish": 15.0, "task": None},
            "task3": {"start": 0.0, "finish": 5.0, "task": None},
        }

        # Act
        result = _calculate_max_parallelism(task_times)

        # Assert
        assert result == 3

    def test_tasks_ending_at_same_time(self):
        """Test multiple tasks that end at the exact same time."""
        # Arrange
        # Task A: [0────────10]
        # Task B:      [5───10]
        # Task C:           [8───10]
        task_times = {
            "task1": {"start": 0.0, "finish": 10.0, "task": None},
            "task2": {"start": 5.0, "finish": 10.0, "task": None},
            "task3": {"start": 8.0, "finish": 10.0, "task": None},
        }

        # Act
        result = _calculate_max_parallelism(task_times)

        # Assert
        assert result == 3

    def test_nested_intervals(self):
        """Test tasks where one is completely contained within another."""
        # Arrange
        # Task A: [0──────────────20]
        # Task B:      [5────15]
        # Task C:           [10──12]
        task_times = {
            "task1": {"start": 0.0, "finish": 20.0, "task": None},
            "task2": {"start": 5.0, "finish": 15.0, "task": None},
            "task3": {"start": 10.0, "finish": 12.0, "task": None},
        }

        # Act
        result = _calculate_max_parallelism(task_times)

        # Assert
        assert result == 3

    def test_gap_between_overlaps(self):
        """Test tasks with gaps where parallelism drops to zero."""
        # Arrange
        # Task A: [0──5]          [20──25]
        # Task B:      [5──10]
        # Task C:           [10──15]
        task_times = {
            "task1": {"start": 0.0, "finish": 5.0, "task": None},
            "task2": {"start": 5.0, "finish": 10.0, "task": None},
            "task3": {"start": 10.0, "finish": 15.0, "task": None},
            "task4": {"start": 20.0, "finish": 25.0, "task": None},
        }

        # Act
        result = _calculate_max_parallelism(task_times)

        # Assert
        assert result == 1

    def test_complex_overlap_scenario(self):
        """Test complex scenario with multiple peaks."""
        # Arrange
        # Task A: [0────────10]
        # Task B:    [2────────12]
        # Task C:       [5───────13]
        # Task D:          [8─────────16]
        # Task E:             [11────────18]
        # Peak is 4 tasks (at t=8, before task1 ends at t=10)
        task_times = {
            "task1": {"start": 0.0, "finish": 10.0, "task": None},
            "task2": {"start": 2.0, "finish": 12.0, "task": None},
            "task3": {"start": 5.0, "finish": 13.0, "task": None},
            "task4": {"start": 8.0, "finish": 16.0, "task": None},
            "task5": {"start": 11.0, "finish": 18.0, "task": None},
        }

        # Act
        result = _calculate_max_parallelism(task_times)

        # Assert
        assert result == 4

    def test_zero_duration_tasks(self):
        """Test tasks with zero duration (instant completion)."""
        # Arrange
        # Task A: [5]  (instant at t=5)
        # Task B: [5]  (instant at t=5)
        task_times = {
            "task1": {"start": 5.0, "finish": 5.0, "task": None},
            "task2": {"start": 5.0, "finish": 5.0, "task": None},
        }

        # Act
        result = _calculate_max_parallelism(task_times)

        # Assert
        # Zero duration tasks should not count as overlapping
        assert result == 0

    def test_fractional_hours(self):
        """Test tasks with fractional hour durations."""
        # Arrange
        # Task A: [0.0────2.5]
        # Task B:      [1.5────4.0]
        # Task C:           [2.0─────5.5]
        task_times = {
            "task1": {"start": 0.0, "finish": 2.5, "task": None},
            "task2": {"start": 1.5, "finish": 4.0, "task": None},
            "task3": {"start": 2.0, "finish": 5.5, "task": None},
        }

        # Act
        result = _calculate_max_parallelism(task_times)

        # Assert
        assert result == 3

    def test_realistic_project_scenario(self):
        """Test a realistic project with various task patterns."""
        # Arrange
        # Setup: 2 tasks, Design: 3 tasks (after setup), Implementation: 4 tasks (after design)
        # Testing: 2 tasks (after implementation)
        task_times = {
            # Setup phase (parallel)
            "setup1": {"start": 0.0, "finish": 2.0, "task": None},
            "setup2": {"start": 0.0, "finish": 2.0, "task": None},
            # Design phase (parallel, starts after setup)
            "design1": {"start": 2.0, "finish": 5.0, "task": None},
            "design2": {"start": 2.0, "finish": 5.0, "task": None},
            "design3": {"start": 2.0, "finish": 6.0, "task": None},
            # Implementation (parallel, starts after design)
            "impl1": {"start": 6.0, "finish": 10.0, "task": None},
            "impl2": {"start": 6.0, "finish": 12.0, "task": None},
            "impl3": {"start": 6.0, "finish": 11.0, "task": None},
            "impl4": {"start": 6.0, "finish": 13.0, "task": None},
            # Testing (parallel, starts after implementation)
            "test1": {"start": 13.0, "finish": 15.0, "task": None},
            "test2": {"start": 13.0, "finish": 16.0, "task": None},
        }

        # Act
        result = _calculate_max_parallelism(task_times)

        # Assert
        # Peak is 4 during implementation phase
        assert result == 4
