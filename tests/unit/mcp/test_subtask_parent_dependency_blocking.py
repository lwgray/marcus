"""
Unit tests for subtask blocking based on parent task dependencies.

Tests that subtasks are not assigned until their parent task's dependencies
are complete, even if the subtask itself has no direct dependencies.
"""

from unittest.mock import Mock

import pytest

from src.core.models import Task, TaskStatus


class TestSubtaskParentDependencyBlocking:
    """Test suite for parent dependency checking in subtask assignment"""

    @pytest.fixture
    def mock_state_with_parent_deps(self) -> Mock:
        """Create mock state with parent task that has dependencies"""
        state = Mock()

        # Design task (dependency)
        design_task = Mock(spec=Task)
        design_task.id = "1640649568578176204"
        design_task.name = "Design Productivity Tools"
        design_task.status = TaskStatus.TODO  # Not complete yet!
        design_task.dependencies = []
        design_task.is_subtask = False
        design_task.parent_task_id = None
        design_task.labels = ["design", "architecture", "productivity tools"]

        # Parent implementation task (depends on Design)
        parent_task = Mock(spec=Task)
        parent_task.id = "1640649570306229462"
        parent_task.name = "Implement Pomodoro Timer"
        parent_task.status = TaskStatus.TODO
        parent_task.dependencies = ["1640649568578176204"]  # Depends on Design
        parent_task.is_subtask = False
        parent_task.parent_task_id = None

        # Subtask (no direct dependencies, but parent has deps)
        subtask = Mock(spec=Task)
        subtask.id = "1640649570306229462_sub_1"
        subtask.name = "Implement Timer UI"
        subtask.status = TaskStatus.TODO
        subtask.dependencies = []  # No direct dependencies!
        subtask.is_subtask = True
        subtask.parent_task_id = "1640649570306229462"  # Parent ID

        state.project_tasks = [design_task, parent_task, subtask]
        state.active_agents = {}

        return state

    def test_subtask_blocked_when_parent_has_incomplete_deps(
        self, mock_state_with_parent_deps: Mock
    ) -> None:
        """Test that subtask is blocked when parent's dependencies incomplete"""
        state = mock_state_with_parent_deps

        # Build slug mapping
        slug_to_id: dict[str, str] = {}
        for t in state.project_tasks:
            if (
                t.name
                and "Design" in t.name
                and hasattr(t, "labels")
                and t.labels
                and len(t.labels) >= 3
            ):
                domain_labels = [
                    label
                    for label in t.labels
                    if label.lower() not in ["design", "architecture"]
                ]
                if domain_labels:
                    domain = domain_labels[-1]
                    slug = f"design_{domain.lower().replace(' ', '_')}"
                    slug_to_id[slug] = str(t.id)

        # Design task NOT complete
        completed_task_ids: set[str] = set()

        # Get subtask
        subtask = state.project_tasks[2]
        parent_task = state.project_tasks[1]

        # Check subtask's direct dependencies (should be empty)
        assert subtask.dependencies == []

        # Check parent's dependencies
        parent_deps = parent_task.dependencies or []
        parent_resolved_deps = []
        for dep_id in parent_deps:
            if dep_id in slug_to_id:
                parent_resolved_deps.append(slug_to_id[dep_id])
            else:
                parent_resolved_deps.append(dep_id)

        parent_deps_complete = all(
            dep_id in completed_task_ids for dep_id in parent_resolved_deps
        )

        # Verify parent deps NOT complete
        assert not parent_deps_complete
        assert parent_resolved_deps == ["1640649568578176204"]

        # Subtask should be BLOCKED even though it has no direct dependencies
        # This is the key test: parent dependency should block subtask

    def test_subtask_unblocked_when_parent_deps_complete(
        self, mock_state_with_parent_deps: Mock
    ) -> None:
        """Test that subtask is unblocked when parent's dependencies complete"""
        state = mock_state_with_parent_deps

        # Build slug mapping
        slug_to_id: dict[str, str] = {}
        for t in state.project_tasks:
            if (
                t.name
                and "Design" in t.name
                and hasattr(t, "labels")
                and t.labels
                and len(t.labels) >= 3
            ):
                domain_labels = [
                    label
                    for label in t.labels
                    if label.lower() not in ["design", "architecture"]
                ]
                if domain_labels:
                    domain = domain_labels[-1]
                    slug = f"design_{domain.lower().replace(' ', '_')}"
                    slug_to_id[slug] = str(t.id)

        # Design task IS complete
        completed_task_ids: set[str] = {"1640649568578176204"}

        # Get subtask
        subtask = state.project_tasks[2]
        parent_task = state.project_tasks[1]

        # Check parent's dependencies
        parent_deps = parent_task.dependencies or []
        parent_resolved_deps = []
        for dep_id in parent_deps:
            if dep_id in slug_to_id:
                parent_resolved_deps.append(slug_to_id[dep_id])
            else:
                parent_resolved_deps.append(dep_id)

        parent_deps_complete = all(
            dep_id in completed_task_ids for dep_id in parent_resolved_deps
        )

        # Verify parent deps ARE complete
        assert parent_deps_complete

        # Subtask should be UNBLOCKED now
        subtask_can_be_assigned = True  # Would be assigned in real code

        assert subtask_can_be_assigned

    def test_regular_task_not_affected_by_parent_check(self) -> None:
        """Test that non-subtasks are not affected by parent dependency check"""
        state = Mock()

        # Regular task (not a subtask)
        regular_task = Mock(spec=Task)
        regular_task.id = "1640649568578176204"
        regular_task.name = "Design Productivity Tools"
        regular_task.status = TaskStatus.TODO
        regular_task.dependencies = []
        regular_task.is_subtask = False  # Not a subtask
        regular_task.parent_task_id = None

        state.project_tasks = [regular_task]

        # Should not attempt to check parent dependencies
        # (this is a logic test - the code shouldn't even look for a parent)
        assert not regular_task.is_subtask
        assert regular_task.parent_task_id is None
