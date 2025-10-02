"""
Simplified unit tests for Phase Dependency Enforcer
"""

import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.models import Priority, Task, TaskStatus
from src.core.phase_dependency_enforcer import PhaseDependencyEnforcer


class TestPhaseDependencyEnforcerSimple:
    """Simplified test suite for PhaseDependencyEnforcer"""

    @pytest.fixture
    def enforcer(self):
        """Create a PhaseDependencyEnforcer instance"""
        return PhaseDependencyEnforcer()

    def test_single_feature_phase_ordering(self, enforcer):
        """Test that tasks within a single feature follow phase ordering"""
        # Create sample tasks
        from datetime import datetime

        tasks = [
            Task(
                id="design-001",
                name="Design authentication system",
                description="Create authentication flow diagrams",
                labels=["auth", "design"],
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                dependencies=[],
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
            ),
            Task(
                id="impl-001",
                name="Implement login API",
                description="Build REST endpoints for user login",
                labels=["auth", "backend"],
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                dependencies=[],
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=8.0,
            ),
            Task(
                id="test-001",
                name="Test authentication endpoints",
                description="Write unit tests for auth API",
                labels=["auth", "testing"],
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                dependencies=[],
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
            ),
            Task(
                id="doc-001",
                name="Document authentication API",
                description="Write API documentation for auth endpoints",
                labels=["auth", "documentation"],
                status=TaskStatus.TODO,
                priority=Priority.LOW,
                dependencies=[],
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
            ),
        ]

        # Apply phase dependencies
        result_tasks = enforcer.enforce_phase_dependencies(tasks)

        # Convert to dict for easier lookup
        task_dict = {task.id: task for task in result_tasks}

        # Check design has no dependencies (it's first)
        assert task_dict["design-001"].dependencies == []

        # Check implementation depends on design
        assert "design-001" in task_dict["impl-001"].dependencies

        # Check test depends on both design and implementation
        assert "design-001" in task_dict["test-001"].dependencies
        assert "impl-001" in task_dict["test-001"].dependencies

        # Check documentation depends on all previous phases
        assert "design-001" in task_dict["doc-001"].dependencies
        assert "impl-001" in task_dict["doc-001"].dependencies
        assert "test-001" in task_dict["doc-001"].dependencies

        print("✓ Single feature phase ordering test passed")

    def test_multiple_features_isolation(self, enforcer):
        """Test that dependencies are isolated within features"""
        from datetime import datetime

        tasks = [
            # Auth feature
            Task(
                id="auth-design",
                name="Design auth system",
                description="Design authentication system",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                labels=["auth"],
                dependencies=[],
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
            ),
            Task(
                id="auth-impl",
                name="Implement auth",
                description="Implement authentication",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                labels=["auth"],
                dependencies=[],
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=8.0,
            ),
            Task(
                id="auth-test",
                name="Test auth",
                description="Test authentication",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                labels=["auth"],
                dependencies=[],
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
            ),
            # Payment feature
            Task(
                id="pay-design",
                name="Design payment system",
                description="Design payment system",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                labels=["payment"],
                dependencies=[],
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
            ),
            Task(
                id="pay-impl",
                name="Implement payment",
                description="Implement payment system",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                labels=["payment"],
                dependencies=[],
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=8.0,
            ),
            Task(
                id="pay-test",
                name="Test payment",
                description="Test payment system",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                labels=["payment"],
                dependencies=[],
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
            ),
        ]

        result_tasks = enforcer.enforce_phase_dependencies(tasks)
        task_dict = {task.id: task for task in result_tasks}

        # Auth implementation should only depend on auth design, not payment design
        assert "auth-design" in task_dict["auth-impl"].dependencies
        assert "pay-design" not in task_dict["auth-impl"].dependencies

        # Payment test should only depend on payment tasks
        assert "pay-impl" in task_dict["pay-test"].dependencies
        assert "auth-impl" not in task_dict["pay-test"].dependencies

        print("✓ Multiple features isolation test passed")

    def test_preserve_existing_dependencies(self, enforcer):
        """Test that existing manual dependencies are preserved"""
        from datetime import datetime

        tasks = [
            Task(
                id="design-001",
                name="Design API",
                description="Design API architecture",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                dependencies=[],
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
            ),
            Task(
                id="impl-001",
                name="Implement API",
                description="Implement API endpoints",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                dependencies=["external-001"],
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=8.0,
            ),
            Task(
                id="test-001",
                name="Test API",
                description="Test API functionality",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                dependencies=["manual-001"],
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
            ),
        ]

        result_tasks = enforcer.enforce_phase_dependencies(tasks)
        task_dict = {task.id: task for task in result_tasks}

        # Check that manual dependencies are preserved
        assert "external-001" in task_dict["impl-001"].dependencies
        assert "manual-001" in task_dict["test-001"].dependencies

        # And phase dependencies are added
        assert "design-001" in task_dict["impl-001"].dependencies
        assert "impl-001" in task_dict["test-001"].dependencies

        print("✓ Preserve existing dependencies test passed")
