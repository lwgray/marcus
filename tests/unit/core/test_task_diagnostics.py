"""
Unit tests for the automatic task diagnostics system.

Tests the diagnostic collectors, analyzers, and report generators.
"""

from datetime import datetime, timedelta
from typing import List
from unittest.mock import Mock

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.core.task_diagnostics import (
    DependencyChainAnalyzer,
    DiagnosticReportGenerator,
    TaskDiagnosticCollector,
    run_automatic_diagnostics,
)


def create_task(
    task_id: str,
    name: str,
    status: TaskStatus = TaskStatus.TODO,
    priority: Priority = Priority.MEDIUM,
    dependencies: List[str] = None,
    description: str = "",
) -> Task:
    """Helper function to create a task with all required fields."""
    now = datetime.now()
    return Task(
        id=task_id,
        name=name,
        description=description or f"Description for {name}",
        status=status,
        priority=priority,
        assigned_to=None,
        created_at=now,
        updated_at=now,
        due_date=now + timedelta(days=7),
        estimated_hours=8.0,
        dependencies=dependencies or [],
        labels=[],
    )


class TestTaskDiagnosticCollector:
    """Test suite for TaskDiagnosticCollector."""

    @pytest.fixture
    def sample_tasks(self):
        """Create sample tasks for testing."""
        return [
            create_task("task-1", "Design API", priority=Priority.HIGH),
            create_task("task-2", "Implement API", dependencies=["task-1"]),
            create_task("task-3", "Test API", dependencies=["task-2"]),
            create_task(
                "task-4",
                "Deploy API",
                status=TaskStatus.DONE,
                priority=Priority.LOW,
                dependencies=["task-3"],
            ),
        ]

    def test_collect_filtering_stats_basic(self, sample_tasks):
        """Test basic filtering statistics collection."""
        collector = TaskDiagnosticCollector(sample_tasks)
        completed_ids = {"task-4"}
        assigned_ids = set()

        stats = collector.collect_filtering_stats(completed_ids, assigned_ids)

        assert stats["total_tasks"] == 4
        assert stats["completed"] == 1
        assert stats["assigned"] == 0
        assert stats["todo"] == 3
        assert len(stats["available"]) == 1  # Only task-1 has no dependencies
        assert stats["available"][0]["id"] == "task-1"

    def test_collect_filtering_stats_blocked_by_dependencies(self, sample_tasks):
        """Test detection of tasks blocked by dependencies."""
        collector = TaskDiagnosticCollector(sample_tasks)
        completed_ids = set()  # Nothing completed
        assigned_ids = set()

        stats = collector.collect_filtering_stats(completed_ids, assigned_ids)

        # task-2 and task-3 are blocked
        assert len(stats["blocked_by_dependencies"]) == 2
        blocked_ids = [t["id"] for t in stats["blocked_by_dependencies"]]
        assert "task-2" in blocked_ids
        assert "task-3" in blocked_ids

    def test_collect_filtering_stats_already_assigned(self, sample_tasks):
        """Test detection of already assigned tasks."""
        collector = TaskDiagnosticCollector(sample_tasks)
        completed_ids = {"task-4"}
        assigned_ids = {"task-1"}

        stats = collector.collect_filtering_stats(completed_ids, assigned_ids)

        assert len(stats["blocked_by_assignment"]) == 1
        assert stats["blocked_by_assignment"][0]["id"] == "task-1"
        assert len(stats["available"]) == 0  # task-1 is assigned


class TestDependencyChainAnalyzer:
    """Test suite for DependencyChainAnalyzer."""

    @pytest.fixture
    def circular_dependency_tasks(self):
        """Create tasks with circular dependencies."""
        return [
            create_task("task-a", "Task A", dependencies=["task-c"]),
            create_task("task-b", "Task B", dependencies=["task-a"]),
            create_task("task-c", "Task C", dependencies=["task-b"]),
        ]

    @pytest.fixture
    def bottleneck_tasks(self):
        """Create tasks where one task blocks many others."""
        return [
            create_task("bottleneck", "Critical Task", priority=Priority.HIGH),
            create_task("task-1", "Task 1", dependencies=["bottleneck"]),
            create_task("task-2", "Task 2", dependencies=["bottleneck"]),
            create_task("task-3", "Task 3", dependencies=["bottleneck"]),
            create_task("task-4", "Task 4", dependencies=["bottleneck"]),
        ]

    def test_find_circular_dependencies(self, circular_dependency_tasks):
        """Test detection of circular dependencies."""
        analyzer = DependencyChainAnalyzer(circular_dependency_tasks)
        cycles = analyzer.find_circular_dependencies()

        assert len(cycles) > 0
        # The cycle should contain all three tasks
        cycle_tasks = set()
        for cycle in cycles:
            cycle_tasks.update(cycle)
        assert "task-a" in cycle_tasks
        assert "task-b" in cycle_tasks
        assert "task-c" in cycle_tasks

    def test_find_bottlenecks(self, bottleneck_tasks):
        """Test detection of bottleneck tasks."""
        analyzer = DependencyChainAnalyzer(bottleneck_tasks)
        bottlenecks = analyzer.find_bottlenecks(threshold=3)

        assert len(bottlenecks) == 1
        assert bottlenecks[0]["task_id"] == "bottleneck"
        assert bottlenecks[0]["blocks_count"] == 4

    def test_find_missing_dependencies(self):
        """Test detection of missing dependencies."""
        tasks = [
            create_task("task-1", "Task 1", dependencies=["nonexistent-task"]),
        ]

        analyzer = DependencyChainAnalyzer(tasks)
        missing = analyzer.find_missing_dependencies()

        assert len(missing) == 1
        assert missing[0]["task_id"] == "task-1"
        assert "nonexistent-task" in missing[0]["missing_dependency_ids"]

    def test_find_long_chains(self):
        """Test detection of long dependency chains."""
        tasks = [
            create_task("task-1", "Task 1"),
            create_task("task-2", "Task 2", dependencies=["task-1"]),
            create_task("task-3", "Task 3", dependencies=["task-2"]),
            create_task("task-4", "Task 4", dependencies=["task-3"]),
            create_task("task-5", "Task 5", dependencies=["task-4"]),
        ]

        analyzer = DependencyChainAnalyzer(tasks)
        chains = analyzer.find_long_chains(min_length=4)

        assert len(chains) >= 1
        # Should find a chain of at least 4 tasks
        assert any(len(chain) >= 4 for chain in chains)


class TestDiagnosticReportGenerator:
    """Test suite for DiagnosticReportGenerator."""

    @pytest.fixture
    def sample_filtering_stats(self):
        """Create sample filtering statistics."""
        return {
            "total_tasks": 10,
            "completed": 3,
            "assigned": 2,
            "todo": 5,
            "in_progress": 2,
            "blocked_by_dependencies": [
                {
                    "id": "task-2",
                    "name": "Task 2",
                    "blocked_by": ["task-1"],
                    "blocked_by_names": ["Task 1"],
                },
                {
                    "id": "task-3",
                    "name": "Task 3",
                    "blocked_by": ["task-2"],
                    "blocked_by_names": ["Task 2"],
                },
            ],
            "blocked_by_assignment": [],
            "available": [],
        }

    @pytest.fixture
    def circular_tasks(self):
        """Create tasks with circular dependency."""
        return [
            create_task("task-a", "Task A", dependencies=["task-b"]),
            create_task("task-b", "Task B", dependencies=["task-a"]),
        ]

    def test_generate_report_identifies_circular_dependency(
        self, circular_tasks, sample_filtering_stats
    ):
        """Test that report identifies circular dependencies."""
        analyzer = DependencyChainAnalyzer(circular_tasks)
        generator = DiagnosticReportGenerator(
            circular_tasks, sample_filtering_stats, analyzer
        )

        report = generator.generate_report()

        # Should identify circular dependency
        circular_issues = [
            i for i in report.issues if i.issue_type == "circular_dependency"
        ]
        assert len(circular_issues) > 0
        assert circular_issues[0].severity == "critical"

    def test_generate_report_includes_recommendations(
        self, circular_tasks, sample_filtering_stats
    ):
        """Test that report includes actionable recommendations."""
        analyzer = DependencyChainAnalyzer(circular_tasks)
        generator = DiagnosticReportGenerator(
            circular_tasks, sample_filtering_stats, analyzer
        )

        report = generator.generate_report()

        assert len(report.recommendations) > 0
        # Recommendations should mention the critical issue
        assert any("CRITICAL" in rec for rec in report.recommendations)


@pytest.mark.asyncio
async def test_run_automatic_diagnostics_integration():
    """
    Integration test for the complete diagnostic system.

    Tests the full workflow from data collection to report generation.
    """
    # Create test scenario: tasks blocked by circular dependency
    tasks = [
        create_task(
            "task-a", "Design System", priority=Priority.HIGH, dependencies=["task-b"]
        ),
        create_task(
            "task-b",
            "Implement System",
            priority=Priority.HIGH,
            dependencies=["task-a"],
        ),
        create_task("task-c", "Completed Task", status=TaskStatus.DONE),
    ]

    completed_ids = {"task-c"}
    assigned_ids = set()

    # Run diagnostics
    report = await run_automatic_diagnostics(tasks, completed_ids, assigned_ids)

    # Verify report structure
    assert report.total_tasks == 3
    assert report.blocked_tasks >= 2  # Both A and B are blocked
    assert len(report.issues) > 0

    # Should detect circular dependency
    circular_issues = [
        i for i in report.issues if i.issue_type == "circular_dependency"
    ]
    assert len(circular_issues) > 0

    # Should have recommendations
    assert len(report.recommendations) > 0


@pytest.mark.asyncio
async def test_run_automatic_diagnostics_no_issues():
    """Test diagnostics when there are no issues (happy path)."""
    tasks = [
        create_task("task-1", "Design", status=TaskStatus.DONE, priority=Priority.HIGH),
        create_task("task-2", "Implement", dependencies=["task-1"]),
    ]

    completed_ids = {"task-1"}
    assigned_ids = set()

    report = await run_automatic_diagnostics(tasks, completed_ids, assigned_ids)

    # Should have available tasks
    assert report.available_tasks == 1

    # Should have no critical issues
    critical_issues = [i for i in report.issues if i.severity == "critical"]
    assert len(critical_issues) == 0
