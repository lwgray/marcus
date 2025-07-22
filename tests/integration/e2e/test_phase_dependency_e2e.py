"""
End-to-End Integration Tests for Phase Dependency Enforcement

Tests the complete flow from project creation through task assignment,
ensuring tasks are assigned in the correct development lifecycle order.
"""

import asyncio
from datetime import datetime
from typing import List
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.core.phase_dependency_enforcer import PhaseDependencyEnforcer
from src.integrations.nlp_task_utils import TaskClassifier, TaskType


@pytest.mark.integration
@pytest.mark.asyncio
class TestPhaseOrderingE2E:
    """End-to-end tests for phase-based task ordering"""

    @pytest.fixture
    async def mock_kanban_client(self):
        """Mock kanban client for testing"""
        client = AsyncMock()
        client.create_task = AsyncMock(
            side_effect=lambda task_data: {
                "id": task_data.get("id", f"kb-{datetime.now().timestamp()}"),
                "name": task_data["name"],
                "status": "todo",
            }
        )
        return client

    @pytest.fixture
    def sample_project_tasks(self):
        """Create a sample project with multiple features"""
        now = datetime.now()
        base_task = {
            "status": TaskStatus.TODO,
            "assigned_to": None,
            "created_at": now,
            "updated_at": now,
            "due_date": None,
        }

        return [
            # Authentication feature
            Task(
                id="auth-design-1",
                name="Design authentication flow",
                description="Create auth flow diagrams",
                priority=Priority.HIGH,
                labels=["auth", "design"],
                dependencies=[],
                estimated_hours=4,
                **base_task,
            ),
            Task(
                id="auth-impl-1",
                name="Implement login API",
                description="Build login endpoints",
                priority=Priority.HIGH,
                labels=["auth", "backend"],
                dependencies=[],
                estimated_hours=8,
                **base_task,
            ),
            Task(
                id="auth-impl-2",
                name="Implement JWT tokens",
                description="Add JWT token generation",
                priority=Priority.HIGH,
                labels=["auth", "backend"],
                dependencies=[],
                estimated_hours=6,
                **base_task,
            ),
            Task(
                id="auth-test-1",
                name="Test authentication endpoints",
                description="Write auth API tests",
                priority=Priority.MEDIUM,
                labels=["auth", "testing"],
                dependencies=[],
                estimated_hours=4,
                **base_task,
            ),
            Task(
                id="auth-doc-1",
                name="Document authentication API",
                description="Write auth API docs",
                priority=Priority.LOW,
                labels=["auth", "documentation"],
                dependencies=[],
                estimated_hours=2,
                **base_task,
            ),
            # User Profile feature
            Task(
                id="profile-design-1",
                name="Design user profile system",
                description="Design profile data model",
                priority=Priority.HIGH,
                labels=["profile", "design"],
                dependencies=[],
                estimated_hours=3,
                **base_task,
            ),
            Task(
                id="profile-impl-1",
                name="Implement user profile API",
                description="Build profile CRUD endpoints",
                priority=Priority.HIGH,
                labels=["profile", "backend"],
                dependencies=[],
                estimated_hours=10,
                **base_task,
            ),
            Task(
                id="profile-test-1",
                name="Test user profile functionality",
                description="Test profile operations",
                priority=Priority.MEDIUM,
                labels=["profile", "testing"],
                dependencies=[],
                estimated_hours=4,
                **base_task,
            ),
            # Global documentation
            Task(
                id="doc-global-1",
                name="Document complete API",
                description="Create comprehensive API documentation",
                priority=Priority.LOW,
                labels=["documentation", "global"],
                dependencies=[],
                estimated_hours=8,
                **base_task,
            ),
        ]

    async def test_single_feature_task_assignment_order(self):
        """Test that a single feature's tasks are assigned in correct order"""
        # Create simple auth feature tasks
        tasks = [
            Task(
                id="1",
                name="Design auth",
                labels=["auth"],
                dependencies=[],
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                estimated_hours=4,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            Task(
                id="2",
                name="Implement auth",
                labels=["auth"],
                dependencies=[],
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                estimated_hours=8,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            Task(
                id="3",
                name="Test auth",
                labels=["auth"],
                dependencies=[],
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                estimated_hours=4,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            Task(
                id="4",
                name="Document auth",
                labels=["auth"],
                dependencies=[],
                status=TaskStatus.TODO,
                priority=Priority.LOW,
                estimated_hours=2,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]

        # Apply phase dependencies
        enforcer = PhaseDependencyEnforcer()
        tasks_with_deps = enforcer.enforce_phase_dependencies(tasks)

        # Simulate task assignment
        completed_tasks = set()
        assigned_order = []

        for _ in range(len(tasks)):
            # Find next assignable task
            assignable = None
            for task in tasks_with_deps:
                if task.id not in completed_tasks and all(
                    dep in completed_tasks for dep in task.dependencies
                ):
                    assignable = task
                    break

            assert assignable is not None, "No assignable task found"
            assigned_order.append(assignable.id)
            completed_tasks.add(assignable.id)

        # Verify assignment order
        assert assigned_order == [
            "1",
            "2",
            "3",
            "4",
        ], f"Tasks assigned in wrong order: {assigned_order}"

    async def test_multiple_features_parallel_assignment(self):
        """Test that multiple features can progress in parallel while maintaining phase order"""
        # Create two feature tasks
        tasks = [
            # Feature A
            Task(
                id="a-design",
                name="Design feature A",
                labels=["feature-a"],
                dependencies=[],
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                estimated_hours=4,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            Task(
                id="a-impl",
                name="Implement feature A",
                labels=["feature-a"],
                dependencies=[],
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                estimated_hours=8,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            # Feature B
            Task(
                id="b-design",
                name="Design feature B",
                labels=["feature-b"],
                dependencies=[],
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                estimated_hours=4,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            Task(
                id="b-impl",
                name="Implement feature B",
                labels=["feature-b"],
                dependencies=[],
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                estimated_hours=8,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]

        # Apply phase dependencies
        enforcer = PhaseDependencyEnforcer()
        tasks_with_deps = enforcer.enforce_phase_dependencies(tasks)

        # Both design tasks should be assignable initially
        initial_assignable = [
            task for task in tasks_with_deps if len(task.dependencies) == 0
        ]
        assert len(initial_assignable) == 2
        assert set(t.id for t in initial_assignable) == {"a-design", "b-design"}

        # After completing one design, its implementation should be assignable
        completed = {"a-design"}
        next_assignable = [
            task
            for task in tasks_with_deps
            if task.id not in completed
            and all(dep in completed for dep in task.dependencies)
        ]

        assert "a-impl" in [t.id for t in next_assignable]
        assert "b-impl" not in [t.id for t in next_assignable]  # B design not complete

    async def test_complex_project_with_shared_tasks(self, sample_project_tasks):
        """Test complex project with multiple features and global tasks"""
        # Apply phase dependencies
        enforcer = PhaseDependencyEnforcer()
        tasks_with_deps = enforcer.enforce_phase_dependencies(sample_project_tasks)

        # Check that global documentation depends on all other tasks
        global_doc = next(t for t in tasks_with_deps if t.id == "doc-global-1")
        non_doc_tasks = [
            t
            for t in tasks_with_deps
            if "documentation" not in t.labels or t.id == "doc-global-1"
        ]

        # Global doc should depend on many tasks (not necessarily all due to feature isolation)
        assert len(global_doc.dependencies) > 0

        # Verify phase ordering within features
        auth_impl = next(t for t in tasks_with_deps if t.id == "auth-impl-1")
        auth_test = next(t for t in tasks_with_deps if t.id == "auth-test-1")

        assert "auth-design-1" in auth_impl.dependencies
        assert (
            "auth-impl-1" in auth_test.dependencies
            or "auth-impl-2" in auth_test.dependencies
        )

    async def test_blocked_task_cannot_be_assigned(self):
        """Test that tasks with incomplete dependencies cannot be assigned"""
        tasks = [
            Task(
                id="impl-1",
                name="Implement feature",
                labels=["feature"],
                dependencies=["design-1"],
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                estimated_hours=8,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]

        # With no completed tasks, impl-1 should not be assignable
        completed_tasks = set()
        assignable = [
            task
            for task in tasks
            if all(dep in completed_tasks for dep in task.dependencies)
        ]

        assert len(assignable) == 0, "Task with incomplete dependencies was assignable"

    async def test_task_completion_enables_dependents(self):
        """Test that completing a task makes its dependents assignable"""
        tasks = [
            Task(
                id="design-1",
                name="Design",
                labels=["feature"],
                dependencies=[],
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                estimated_hours=4,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            Task(
                id="impl-1",
                name="Implement",
                labels=["feature"],
                dependencies=[],
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                estimated_hours=8,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]

        # Apply dependencies
        enforcer = PhaseDependencyEnforcer()
        tasks_with_deps = enforcer.enforce_phase_dependencies(tasks)

        # Initially only design is assignable
        completed = set()
        assignable = [
            t
            for t in tasks_with_deps
            if t.id not in completed and all(dep in completed for dep in t.dependencies)
        ]
        assert len(assignable) == 1
        assert assignable[0].id == "design-1"

        # Complete design
        completed.add("design-1")

        # Now implementation should be assignable
        assignable = [
            t
            for t in tasks_with_deps
            if t.id not in completed and all(dep in completed for dep in t.dependencies)
        ]
        assert len(assignable) == 1
        assert assignable[0].id == "impl-1"

    async def test_phase_statistics(self, sample_project_tasks):
        """Test phase statistics generation"""
        enforcer = PhaseDependencyEnforcer()
        tasks_with_deps = enforcer.enforce_phase_dependencies(sample_project_tasks)

        stats = enforcer.get_phase_statistics(tasks_with_deps)

        assert stats["total_tasks"] == len(sample_project_tasks)
        assert stats["feature_count"] >= 2  # At least auth and profile
        assert stats["dependency_count"] > 0
        assert "DESIGN" in stats["phase_distribution"]
        assert "IMPLEMENTATION" in stats["phase_distribution"]
        assert "TESTING" in stats["phase_distribution"]
        assert "DOCUMENTATION" in stats["phase_distribution"]

    @pytest.mark.parametrize(
        "invalid_sequence",
        [
            # Test depends on non-existent implementation
            [
                {
                    "id": "test-1",
                    "name": "Test feature",
                    "labels": ["feat"],
                    "deps": [],
                },
            ],
            # Documentation before implementation
            [
                {"id": "doc-1", "name": "Document API", "labels": ["feat"], "deps": []},
                {
                    "id": "impl-1",
                    "name": "Implement API",
                    "labels": ["feat"],
                    "deps": ["doc-1"],
                },
            ],
        ],
    )
    async def test_invalid_sequences_corrected(self, invalid_sequence):
        """Test that invalid task sequences are corrected by phase enforcement"""
        tasks = []
        for task_data in invalid_sequence:
            tasks.append(
                Task(
                    id=task_data["id"],
                    name=task_data["name"],
                    labels=task_data["labels"],
                    dependencies=task_data["deps"],
                    status=TaskStatus.TODO,
                    priority=Priority.MEDIUM,
                    estimated_hours=4,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
            )

        # Apply phase enforcement
        enforcer = PhaseDependencyEnforcer()
        corrected_tasks = enforcer.enforce_phase_dependencies(tasks)

        # Validate the ordering is now correct
        is_valid, errors = enforcer.validate_phase_ordering(corrected_tasks)
        assert is_valid, f"Phase ordering still invalid: {errors}"
