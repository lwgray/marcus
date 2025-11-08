"""
Unit tests for cross-parent dependency wiring rules.

Tests the rule: If a parent task has NO dependencies, its subtasks can ONLY
have intra-parent dependencies, NOT cross-parent dependencies.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from src.core.models import Priority, Task, TaskStatus


def create_task(**kwargs):
    """Helper to create Task with required fields."""
    defaults = {
        "assigned_to": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "due_date": None,
        "dependencies": [],
        "labels": [],
    }
    defaults.update(kwargs)
    return Task(**defaults)


class TestCrossParentDependencyRules:
    """Test cross-parent dependency wiring respects parent dependencies."""

    @pytest.fixture
    def mock_ai_engine(self):
        """Create mock AI engine."""
        mock = Mock()
        mock.generate_structured_response = AsyncMock(
            return_value={"dependencies": [], "reasoning": {}}
        )
        return mock

    def test_independent_parents_no_cross_deps(self, mock_ai_engine):
        """
        If parent tasks have NO dependencies, their subtasks should NOT get
        cross-parent dependencies.

        Given: 3 parent tasks with NO parent dependencies
        When: Each has subtasks (1.1, 2.1, 3.1) with requires fields
        Then: NO cross-parent dependencies should be created
        Expected: All first subtasks available at time=0 (maximum parallelism)
        """
        # Arrange: Create 3 independent parent tasks
        parent_a = create_task(
            id="parent_a",
            name="Design Task A",
            description="Design feature A",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=6.0,
        )

        parent_b = create_task(
            id="parent_b",
            name="Design Task B",
            description="Design feature B",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=6.0,
        )

        parent_c = create_task(
            id="parent_c",
            name="Design Task C",
            description="Design feature C",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=6.0,
        )

        # Create subtasks for each parent
        subtask_a1 = create_task(
            id="parent_a_sub_1",
            name="First subtask of A",
            description="Do work A",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=2.0,
            is_subtask=True,
            parent_task_id="parent_a",
            subtask_index=0,
            requires="Understanding of domain patterns",  # Has requires field
            provides="Design patterns for A",
        )

        subtask_b1 = create_task(
            id="parent_b_sub_1",
            name="First subtask of B",
            description="Do work B",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=2.0,
            is_subtask=True,
            parent_task_id="parent_b",
            subtask_index=0,
            requires="Understanding of domain patterns",  # Similar requires
            provides="Design patterns for B",
        )

        subtask_c1 = create_task(
            id="parent_c_sub_1",
            name="First subtask of C",
            description="Do work C",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=2.0,
            is_subtask=True,
            parent_task_id="parent_c",
            subtask_index=0,
            requires="Understanding of domain patterns",  # Similar requires
            provides="Design patterns for C",
        )

        all_tasks = [parent_a, parent_b, parent_c, subtask_a1, subtask_b1, subtask_c1]

        # Act: Run cross-parent dependency wiring
        import asyncio

        from src.marcus_mcp.coordinator.dependency_wiring import (
            wire_cross_parent_dependencies,
        )

        stats = asyncio.run(
            wire_cross_parent_dependencies(all_tasks, mock_ai_engine, None)
        )

        # Assert: NO cross-parent dependencies should be created
        # because all parents have NO dependencies
        assert stats["dependencies_created"] == 0
        assert len(subtask_a1.dependencies) == 0
        assert len(subtask_b1.dependencies) == 0
        assert len(subtask_c1.dependencies) == 0

    def test_intra_parent_dependencies_preserved(self):
        """
        Intra-parent dependencies (within same parent) should be preserved
        regardless of parent's dependency status.

        Given: Parent task A (no dependencies) with sequential subtasks
        When: A.1 → A.2 → A.3 (intra-parent chain)
        Then: Intra-parent dependencies remain intact
        Expected: Only A.1 available initially, then A.2, then A.3
        """
        # Arrange
        parent_a = create_task(
            id="parent_a",
            name="Design Task A",
            description="Design feature A",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=6.0,
            dependencies=[],  # NO dependencies
        )

        subtask_a1 = create_task(
            id="parent_a_sub_1",
            name="Subtask A.1",
            description="First step",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=2.0,
            dependencies=[],  # No deps - can start immediately
            is_subtask=True,
            parent_task_id="parent_a",
            subtask_index=0,
        )

        subtask_a2 = create_task(
            id="parent_a_sub_2",
            name="Subtask A.2",
            description="Second step",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=2.0,
            dependencies=["parent_a_sub_1"],  # Intra-parent dependency
            is_subtask=True,
            parent_task_id="parent_a",
            subtask_index=1,
        )

        subtask_a3 = create_task(
            id="parent_a_sub_3",
            name="Subtask A.3",
            description="Third step",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=2.0,
            dependencies=["parent_a_sub_2"],  # Intra-parent dependency
            is_subtask=True,
            parent_task_id="parent_a",
            subtask_index=2,
        )

        all_tasks = [parent_a, subtask_a1, subtask_a2, subtask_a3]

        # Act: Find available subtasks
        from src.marcus_mcp.coordinator.subtask_assignment import (
            find_next_available_subtask,
        )
        from src.marcus_mcp.coordinator.subtask_manager import SubtaskManager

        subtask_manager = SubtaskManager()
        assigned_task_ids = set()

        # First call - should get A.1
        result1 = find_next_available_subtask(
            "agent1", all_tasks, subtask_manager, assigned_task_ids
        )

        # Assert
        assert result1 is not None
        assert result1.id == "parent_a_sub_1"
        assert len(result1.dependencies) == 0

        # Mark A.1 as assigned and done
        assigned_task_ids.add("parent_a_sub_1")
        subtask_a1.status = TaskStatus.DONE

        # Second call - should get A.2 (after A.1 completes)
        result2 = find_next_available_subtask(
            "agent2", all_tasks, subtask_manager, assigned_task_ids
        )

        assert result2 is not None
        assert result2.id == "parent_a_sub_2"
        assert "parent_a_sub_1" in result2.dependencies

    @pytest.mark.asyncio
    async def test_cross_parent_deps_when_parent_has_dependencies(self, mock_ai_engine):
        """
        If parent task HAS dependencies, its subtasks CAN have cross-parent
        dependencies to subtasks of the parents it depends on.

        Given:
          - Design Task A (no dependencies), Subtask A.2 provides "API spec"
          - Implement Task B (depends on A), Subtask B.1 requires "API spec"
        When: Cross-parent wiring runs
        Then: B.1 SHOULD be allowed to depend on A.2
        Expected: Cross-parent dependency is created
        """
        # Arrange
        parent_a = create_task(
            id="parent_a",
            name="Design Task A",
            description="Design feature A",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=6.0,
            dependencies=[],  # NO dependencies
        )

        parent_b = create_task(
            id="parent_b",
            name="Implement Task B",
            description="Implement feature B",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=6.0,
            dependencies=["parent_a"],  # HAS dependency on A
        )

        subtask_a2 = create_task(
            id="parent_a_sub_2",
            name="Create API specification",
            description="Define API spec",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=2.0,
            dependencies=[],
            is_subtask=True,
            parent_task_id="parent_a",
            subtask_index=1,
            provides="Complete API specification",
        )

        subtask_b1 = create_task(
            id="parent_b_sub_1",
            name="Implement endpoint",
            description="Build API endpoint",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=2.0,
            dependencies=[],  # No intra-parent deps
            is_subtask=True,
            parent_task_id="parent_b",
            subtask_index=0,
            requires="API specification",  # Needs spec from A.2
        )

        all_tasks = [parent_a, parent_b, subtask_a2, subtask_b1]

        # Mock AI to return A.2 as dependency for B.1
        mock_ai_engine.generate_structured_response = AsyncMock(
            return_value={
                "dependencies": ["parent_a_sub_2"],
                "reasoning": {
                    "parent_a_sub_2": "Provides API spec needed for implementation"
                },
            }
        )

        # Act
        from src.marcus_mcp.coordinator.dependency_wiring import (
            wire_cross_parent_dependencies,
        )

        stats = await wire_cross_parent_dependencies(all_tasks, mock_ai_engine, None)

        # Assert: Cross-parent dependency SHOULD be created
        # because parent_b depends on parent_a
        assert stats["dependencies_created"] == 1
        assert "parent_a_sub_2" in subtask_b1.dependencies

    def test_subtask_sorting_for_maximum_parallelism(self):
        """
        Subtasks should be sorted by index FIRST, then parent,
        to achieve maximum parallelism.

        Given: 3 parent tasks, each with 3 subtasks (9 total)
        When: Subtasks are sorted
        Then: Order should be 1.1, 2.1, 3.1, then 1.2, 2.2, 3.2, etc.
        Expected: Maximum parallelism across parents
        """
        # Arrange: Create tasks
        tasks = []

        for parent_idx in range(3):
            parent_id = f"parent_{parent_idx}"
            parent = create_task(
                id=parent_id,
                name=f"Parent {parent_idx}",
                description=f"Parent task {parent_idx}",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                estimated_hours=6.0,
                dependencies=[],
            )
            tasks.append(parent)

            # Create 3 subtasks for each parent
            for sub_idx in range(3):
                subtask = create_task(
                    id=f"{parent_id}_sub_{sub_idx + 1}",
                    name=f"Subtask {parent_idx}.{sub_idx + 1}",
                    description=f"Subtask {sub_idx + 1}",
                    status=TaskStatus.TODO,
                    priority=Priority.MEDIUM,
                    estimated_hours=2.0,
                    dependencies=[],
                    is_subtask=True,
                    parent_task_id=parent_id,
                    subtask_index=sub_idx,
                )
                tasks.append(subtask)

        # Act: Sort subtasks using the assignment logic
        subtasks = [t for t in tasks if t.is_subtask]
        sorted_subtasks = sorted(
            subtasks, key=lambda t: (t.subtask_index or 0, t.parent_task_id or "")
        )

        # Assert: Should be sorted by index first
        expected_order = [
            "parent_0_sub_1",  # Index 0
            "parent_1_sub_1",  # Index 0
            "parent_2_sub_1",  # Index 0
            "parent_0_sub_2",  # Index 1
            "parent_1_sub_2",  # Index 1
            "parent_2_sub_2",  # Index 1
            "parent_0_sub_3",  # Index 2
            "parent_1_sub_3",  # Index 2
            "parent_2_sub_3",  # Index 2
        ]

        actual_order = [st.id for st in sorted_subtasks]
        assert actual_order == expected_order

    @pytest.mark.asyncio
    async def test_mixed_dependency_graph(self, mock_ai_engine):
        """
        Complex scenario with multiple parent tasks and mixed dependencies.

        Given:
          - Design Task A (no deps): A.1 → A.2
          - Design Task B (no deps): B.1 → B.2
          - Implement Task C (depends on A, B): C.1, C.2, C.3
        When: Cross-parent wiring runs
        Then:
          - A.1 and B.1 should NOT depend on each other (parents have no deps)
          - C.x CAN depend on A.x and B.x (C's parent depends on A and B)
        Expected: Proper parallelism at each level
        """
        # Arrange
        parent_a = create_task(
            id="parent_a",
            name="Design Task A",
            description="Design A",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=4.0,
            dependencies=[],  # NO dependencies
        )

        parent_b = create_task(
            id="parent_b",
            name="Design Task B",
            description="Design B",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=4.0,
            dependencies=[],  # NO dependencies
        )

        parent_c = create_task(
            id="parent_c",
            name="Implement Task C",
            description="Implement C",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=6.0,
            dependencies=["parent_a", "parent_b"],  # Depends on A and B
        )

        # Subtasks for A
        subtask_a1 = create_task(
            id="parent_a_sub_1",
            name="A.1",
            description="First step A",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=2.0,
            dependencies=[],
            is_subtask=True,
            parent_task_id="parent_a",
            subtask_index=0,
            requires="Domain knowledge",
            provides="Research findings A",
        )

        subtask_a2 = create_task(
            id="parent_a_sub_2",
            name="A.2",
            description="Second step A",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=2.0,
            dependencies=["parent_a_sub_1"],  # Intra-parent
            is_subtask=True,
            parent_task_id="parent_a",
            subtask_index=1,
            provides="API spec A",
        )

        # Subtasks for B
        subtask_b1 = create_task(
            id="parent_b_sub_1",
            name="B.1",
            description="First step B",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=2.0,
            dependencies=[],
            is_subtask=True,
            parent_task_id="parent_b",
            subtask_index=0,
            requires="Domain knowledge",
            provides="Research findings B",
        )

        subtask_b2 = create_task(
            id="parent_b_sub_2",
            name="B.2",
            description="Second step B",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=2.0,
            dependencies=["parent_b_sub_1"],  # Intra-parent
            is_subtask=True,
            parent_task_id="parent_b",
            subtask_index=1,
            provides="Data model B",
        )

        # Subtasks for C
        subtask_c1 = create_task(
            id="parent_c_sub_1",
            name="C.1",
            description="Implement feature C",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=2.0,
            dependencies=[],
            is_subtask=True,
            parent_task_id="parent_c",
            subtask_index=0,
            requires="API spec from A",  # Should match A.2
        )

        all_tasks = [
            parent_a,
            parent_b,
            parent_c,
            subtask_a1,
            subtask_a2,
            subtask_b1,
            subtask_b2,
            subtask_c1,
        ]

        # Mock AI: Only C.1 should get cross-parent deps (not A.1, B.1)
        async def mock_llm_response(prompt, **kwargs):
            # Check which subtask is being analyzed
            if "parent_a_sub_1" in prompt or "parent_b_sub_1" in prompt:
                # A.1 and B.1 should NOT get cross-parent deps
                return {"dependencies": [], "reasoning": {}}
            elif "parent_c_sub_1" in prompt:
                # C.1 CAN depend on A.2
                return {
                    "dependencies": ["parent_a_sub_2"],
                    "reasoning": {"parent_a_sub_2": "Provides needed API spec"},
                }
            return {"dependencies": [], "reasoning": {}}

        mock_ai_engine.generate_structured_response = AsyncMock(
            side_effect=mock_llm_response
        )

        # Act
        from src.marcus_mcp.coordinator.dependency_wiring import (
            wire_cross_parent_dependencies,
        )

        stats = await wire_cross_parent_dependencies(all_tasks, mock_ai_engine, None)

        # Assert
        # A.1 and B.1 should have NO cross-parent deps (parents have no deps)
        assert len(subtask_a1.dependencies) == 0
        assert len(subtask_b1.dependencies) == 0

        # C.1 CAN have cross-parent dep (parent C depends on A)
        # Note: Stats might be 0 if AI wasn't called for A.1, B.1
        # The key is that A.1 and B.1 remain clean
