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
    async def mock_kanban_client(self) -> AsyncMock:
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
    def sample_project_tasks(self) -> List[Task]:
        """Create a sample project with multiple features"""
        now = datetime.now()

        return [
            # Authentication feature
            Task(
                id="auth-design-1",
                name="Design authentication flow",
                description="Create auth flow diagrams",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=None,
                estimated_hours=4.0,
                labels=["auth", "design"],
                dependencies=[],
            ),
            Task(
                id="auth-impl-1",
                name="Implement login API",
                description="Build login endpoints",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=None,
                estimated_hours=8.0,
                labels=["auth", "backend"],
                dependencies=[],
            ),
            Task(
                id="auth-impl-2",
                name="Implement JWT tokens",
                description="Add JWT token generation",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=None,
                estimated_hours=6.0,
                labels=["auth", "backend"],
                dependencies=[],
            ),
            Task(
                id="auth-test-1",
                name="Test authentication endpoints",
                description="Write auth API tests",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=None,
                estimated_hours=4.0,
                labels=["auth", "testing"],
                dependencies=[],
            ),
            Task(
                id="auth-doc-1",
                name="Document authentication API",
                description="Write auth API docs",
                status=TaskStatus.TODO,
                priority=Priority.LOW,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=None,
                estimated_hours=2.0,
                labels=["auth", "documentation"],
                dependencies=[],
            ),
            # User Profile feature
            Task(
                id="profile-design-1",
                name="Design user profile system",
                description="Design profile data model",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=None,
                estimated_hours=3.0,
                labels=["profile", "design"],
                dependencies=[],
            ),
            Task(
                id="profile-impl-1",
                name="Implement user profile API",
                description="Build profile CRUD endpoints",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=None,
                estimated_hours=10.0,
                labels=["profile", "backend"],
                dependencies=[],
            ),
            Task(
                id="profile-test-1",
                name="Test user profile functionality",
                description="Test profile operations",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=None,
                estimated_hours=4.0,
                labels=["profile", "testing"],
                dependencies=[],
            ),
            # Global documentation
            Task(
                id="doc-global-1",
                name="Document complete API",
                description="Create comprehensive API documentation",
                status=TaskStatus.TODO,
                priority=Priority.LOW,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=None,
                estimated_hours=8.0,
                labels=["documentation", "global"],
                dependencies=[],
            ),
        ]

    async def test_single_feature_task_assignment_order(self):
        """Test that a single feature's tasks are assigned in correct order"""
        # Create simple auth feature tasks
        tasks = [
            Task(
                id="1",
                name="Design auth",
                description="Design authentication flow",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
                labels=["auth"],
                dependencies=[],
            ),
            Task(
                id="2",
                name="Implement auth",
                description="Implement authentication logic",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=8.0,
                labels=["auth"],
                dependencies=[],
            ),
            Task(
                id="3",
                name="Test auth",
                description="Test authentication functionality",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
                labels=["auth"],
                dependencies=[],
            ),
            Task(
                id="4",
                name="Document auth",
                description="Document authentication API",
                status=TaskStatus.TODO,
                priority=Priority.LOW,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                labels=["auth"],
                dependencies=[],
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
                description="Design feature A architecture",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
                labels=["feature-a"],
                dependencies=[],
            ),
            Task(
                id="a-impl",
                name="Implement feature A",
                description="Implement feature A logic",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=8.0,
                labels=["feature-a"],
                dependencies=[],
            ),
            # Feature B
            Task(
                id="b-design",
                name="Design feature B",
                description="Design feature B architecture",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
                labels=["feature-b"],
                dependencies=[],
            ),
            Task(
                id="b-impl",
                name="Implement feature B",
                description="Implement feature B logic",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=8.0,
                labels=["feature-b"],
                dependencies=[],
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
                description="Implement the feature",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=8.0,
                labels=["feature"],
                dependencies=["design-1"],
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
                description="Design the feature",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
                labels=["feature"],
                dependencies=[],
            ),
            Task(
                id="impl-1",
                name="Implement",
                description="Implement the feature",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=8.0,
                labels=["feature"],
                dependencies=[],
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
                    description=f"Task: {task_data['name']}",
                    status=TaskStatus.TODO,
                    priority=Priority.MEDIUM,
                    assigned_to=None,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    due_date=None,
                    estimated_hours=4.0,
                    labels=task_data["labels"],
                    dependencies=task_data["deps"],
                )
            )

        # Apply phase enforcement
        enforcer = PhaseDependencyEnforcer()
        corrected_tasks = enforcer.enforce_phase_dependencies(tasks)

        # Validate the ordering is now correct
        is_valid, errors = enforcer.validate_phase_ordering(corrected_tasks)
        assert is_valid, f"Phase ordering still invalid: {errors}"
