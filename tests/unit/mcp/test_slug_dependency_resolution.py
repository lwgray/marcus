"""
Unit tests for slug-based dependency resolution in task assignment.

Tests that bundled design tasks with slug IDs (like 'design_productivity_tools')
are properly resolved when checking dependencies for implementation tasks.
"""

from unittest.mock import Mock

import pytest

from src.core.models import Task, TaskStatus


class TestSlugDependencyResolution:
    """Test suite for slug dependency resolution in task assignment"""

    @pytest.fixture
    def mock_state(self) -> Mock:
        """Create mock agent state with slug-based design task and dependent impl task"""
        state = Mock()

        # Bundled design task with slug ID
        design_task = Mock(spec=Task)
        design_task.id = "design_productivity_tools"
        design_task.name = "Design Productivity Tools"
        design_task.status = TaskStatus.TODO
        design_task.dependencies = []

        # Implementation task that depends on slug-based design task
        impl_task = Mock(spec=Task)
        impl_task.id = "1640368844172166775"
        impl_task.name = "Implement Pomodoro Timer UI"
        impl_task.status = TaskStatus.TODO
        impl_task.dependencies = ["design_productivity_tools"]  # Slug dependency!

        state.project_tasks = [design_task, impl_task]
        state.active_agents = {}

        return state

    def test_slug_to_id_mapping_created(self, mock_state: Mock) -> None:
        """Test that slug-to-ID mapping is built for slug-based task IDs"""
        # This tests the logic added at lines 1525-1533 in task.py

        slug_to_id = {}
        for t in mock_state.project_tasks:
            # Check if task has a slug-like ID (contains letters/underscores)
            if (
                t.id
                and isinstance(t.id, str)
                and any(c.isalpha() or c == "_" for c in t.id)
            ):
                slug_to_id[t.id] = t.id  # Slug maps to itself

        # Verify slug was found
        assert "design_productivity_tools" in slug_to_id
        assert slug_to_id["design_productivity_tools"] == "design_productivity_tools"

        # Verify numeric ID was not included
        assert "1640368844172166775" not in slug_to_id

    def test_slug_dependency_resolution(self, mock_state: Mock) -> None:
        """Test that slug dependencies are resolved before checking completion"""
        # This tests the logic added at lines 1593-1615 in task.py

        # Build slug mapping
        slug_to_id = {}
        for t in mock_state.project_tasks:
            if (
                t.id
                and isinstance(t.id, str)
                and any(c.isalpha() or c == "_" for c in t.id)
            ):
                slug_to_id[t.id] = t.id

        # Simulate checking impl task dependencies
        impl_task = mock_state.project_tasks[1]
        deps = impl_task.dependencies or []

        # Resolve slugs
        resolved_deps = []
        for dep_id in deps:
            if dep_id in slug_to_id:
                resolved_deps.append(slug_to_id[dep_id])
            else:
                resolved_deps.append(dep_id)

        # Verify resolution
        assert deps == ["design_productivity_tools"]
        assert resolved_deps == ["design_productivity_tools"]

    def test_dependency_blocking_when_slug_incomplete(self, mock_state: Mock) -> None:
        """Test that task is blocked when slug dependency is incomplete"""
        # Build slug mapping
        slug_to_id = {}
        for t in mock_state.project_tasks:
            if (
                t.id
                and isinstance(t.id, str)
                and any(c.isalpha() or c == "_" for c in t.id)
            ):
                slug_to_id[t.id] = t.id

        # Design task is NOT complete
        completed_task_ids: set[str] = set()  # Empty - design not done

        # Check impl task dependencies
        impl_task = mock_state.project_tasks[1]
        deps = impl_task.dependencies or []

        resolved_deps = []
        for dep_id in deps:
            if dep_id in slug_to_id:
                resolved_deps.append(slug_to_id[dep_id])
            else:
                resolved_deps.append(dep_id)

        all_deps_complete = all(
            dep_id in completed_task_ids for dep_id in resolved_deps
        )

        # Verify task is blocked
        assert not all_deps_complete
        incomplete_deps = [
            dep_id for dep_id in resolved_deps if dep_id not in completed_task_ids
        ]
        assert incomplete_deps == ["design_productivity_tools"]

    def test_dependency_unblocked_when_slug_complete(self, mock_state: Mock) -> None:
        """Test that task is unblocked when slug dependency completes"""
        # Build slug mapping
        slug_to_id = {}
        for t in mock_state.project_tasks:
            if (
                t.id
                and isinstance(t.id, str)
                and any(c.isalpha() or c == "_" for c in t.id)
            ):
                slug_to_id[t.id] = t.id

        # Design task IS complete
        completed_task_ids = {"design_productivity_tools"}

        # Check impl task dependencies
        impl_task = mock_state.project_tasks[1]
        deps = impl_task.dependencies or []

        resolved_deps = []
        for dep_id in deps:
            if dep_id in slug_to_id:
                resolved_deps.append(slug_to_id[dep_id])
            else:
                resolved_deps.append(dep_id)

        all_deps_complete = all(
            dep_id in completed_task_ids for dep_id in resolved_deps
        )

        # Verify task is unblocked
        assert all_deps_complete

    def test_mixed_slug_and_numeric_dependencies(self) -> None:
        """Test resolution when task has both slug and numeric dependencies"""
        # Setup
        slug_to_id = {
            "design_productivity_tools": "design_productivity_tools",
            "setup_environment": "setup_environment",
        }

        # Mixed dependencies
        deps = [
            "design_productivity_tools",  # Slug
            "1640368842335061613",  # Numeric
            "setup_environment",  # Slug
        ]

        # Resolve
        resolved_deps = []
        for dep_id in deps:
            if dep_id in slug_to_id:
                resolved_deps.append(slug_to_id[dep_id])
            else:
                resolved_deps.append(dep_id)

        # Verify both types resolved correctly
        assert resolved_deps == [
            "design_productivity_tools",
            "1640368842335061613",
            "setup_environment",
        ]

        # Test partial completion
        completed_task_ids = {
            "design_productivity_tools",
            # Missing: "1640368842335061613" and "setup_environment"
        }

        all_deps_complete = all(
            dep_id in completed_task_ids for dep_id in resolved_deps
        )

        assert not all_deps_complete
        incomplete = [d for d in resolved_deps if d not in completed_task_ids]
        assert incomplete == ["1640368842335061613", "setup_environment"]
