"""
Unit tests for output_paths field on Task and Subtask.

Verifies:
- Task.output_paths field exists with correct default
- Subtask.output_paths field exists with correct default
- SubtaskManager.add_subtasks propagates output_paths from dict to both objects
"""

from dataclasses import fields
from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.unit


def _make_task(**kwargs):
    """Create a minimal valid Task for testing."""
    from src.core.models import Priority, Task, TaskStatus

    defaults = dict(
        id="t1",
        name="Test Task",
        description="desc",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        due_date=None,
        estimated_hours=1.0,
    )
    defaults.update(kwargs)
    return Task(**defaults)


class TestTaskOutputPathsField:
    """Task dataclass has output_paths with correct shape."""

    def test_task_has_output_paths_field(self) -> None:
        """output_paths field exists on Task dataclass."""
        from src.core.models import Task

        field_names = {f.name for f in fields(Task)}
        assert "output_paths" in field_names

    def test_output_paths_defaults_to_empty_list(self) -> None:
        """output_paths defaults to [] so legacy tasks need no migration."""
        task = _make_task(id="t1")
        assert task.output_paths == []

    def test_output_paths_accepts_path_list(self) -> None:
        """output_paths can hold any list of path strings."""
        paths = ["src/components/WeatherCard.tsx", "src/styles/theme.css"]
        task = _make_task(id="t1", output_paths=paths)
        assert task.output_paths == paths

    def test_output_paths_instances_are_independent(self) -> None:
        """Two Tasks do not share the same output_paths list (mutable default)."""
        t1 = _make_task(id="t1", name="A", description="a")
        t2 = _make_task(id="t2", name="B", description="b")
        t1.output_paths.append("src/foo.py")
        assert t2.output_paths == []


class TestSubtaskOutputPathsField:
    """Subtask dataclass has output_paths with correct shape."""

    def test_subtask_has_output_paths_field(self) -> None:
        """output_paths field exists on Subtask dataclass."""
        from src.marcus_mcp.coordinator.subtask_manager import Subtask

        field_names = {f.name for f in fields(Subtask)}
        assert "output_paths" in field_names

    def test_subtask_output_paths_defaults_to_empty_list(self) -> None:
        """output_paths defaults to [] on Subtask."""
        from src.core.models import Priority, TaskStatus
        from src.marcus_mcp.coordinator.subtask_manager import Subtask

        subtask = Subtask(
            id="s1",
            parent_task_id="p1",
            name="Test",
            description="desc",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            estimated_hours=1.0,
        )
        assert subtask.output_paths == []


class TestSubtaskManagerPropagatesOutputPaths:
    """SubtaskManager.add_subtasks copies output_paths to both Subtask and Task."""

    def test_add_subtasks_propagates_output_paths_to_subtask(self) -> None:
        """output_paths from subtask dict flows through to the Subtask object."""
        from src.marcus_mcp.coordinator.subtask_manager import SubtaskManager

        manager = SubtaskManager()
        subtask_data = [
            {
                "name": "Implement WeatherCard",
                "description": "Build WeatherCard component",
                "estimated_hours": 2.0,
                "dependencies": [],
                "dependency_types": [],
                "output_paths": ["src/components/WeatherCard.tsx"],
                "provides": "weather card component",
                "requires": None,
                "labels": [],
                "acceptance_criteria": [],
            }
        ]
        parent_id = "test-output-paths-parent-001"
        manager.add_subtasks(parent_id, subtask_data)
        subtask = manager.subtasks[f"{parent_id}_sub_1"]
        assert subtask.output_paths == ["src/components/WeatherCard.tsx"]

    def test_add_subtasks_propagates_output_paths_to_task(self) -> None:
        """output_paths from subtask dict flows through to the returned Task."""
        from src.marcus_mcp.coordinator.subtask_manager import SubtaskManager

        manager = SubtaskManager()
        subtask_data = [
            {
                "name": "Implement WeatherCard",
                "description": "Build WeatherCard component",
                "estimated_hours": 2.0,
                "dependencies": [],
                "dependency_types": [],
                "output_paths": ["src/components/WeatherCard.tsx"],
                "provides": "weather card component",
                "requires": None,
                "labels": [],
                "acceptance_criteria": [],
            }
        ]
        tasks = manager.add_subtasks("parent-001", subtask_data)
        assert tasks[0].output_paths == ["src/components/WeatherCard.tsx"]

    def test_add_subtasks_output_paths_defaults_when_absent(self) -> None:
        """output_paths defaults to [] when not in subtask dict."""
        from src.marcus_mcp.coordinator.subtask_manager import SubtaskManager

        manager = SubtaskManager()
        subtask_data = [
            {
                "name": "Setup tooling",
                "description": "Configure build tools",
                "estimated_hours": 1.0,
                "dependencies": [],
                "dependency_types": [],
                "provides": None,
                "requires": None,
                "labels": [],
                "acceptance_criteria": [],
                # output_paths intentionally absent
            }
        ]
        parent_id = "test-output-paths-parent-002"
        tasks = manager.add_subtasks(parent_id, subtask_data)
        assert manager.subtasks[f"{parent_id}_sub_1"].output_paths == []
        assert tasks[0].output_paths == []
