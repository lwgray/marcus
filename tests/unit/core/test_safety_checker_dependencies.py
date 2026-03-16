"""
Unit tests for SafetyChecker dependency setup
"""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.integrations.nlp_task_utils import SafetyChecker, TaskClassifier, TaskType


class TestSafetyCheckerDependencies:
    """Test suite for SafetyChecker dependency management"""

    @pytest.fixture
    def safety_checker(self):
        """Create a SafetyChecker instance for testing"""
        return SafetyChecker()

    @pytest.fixture
    def sample_tasks(self):
        """Create sample tasks for testing"""
        return [
            Task(
                id="impl-1",
                name="Implement user authentication",
                description="Create authentication system with login and registration",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=8.0,
                labels=["backend", "auth"],
            ),
            Task(
                id="impl-2",
                name="Build product catalog",
                description="Develop product management system",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=6.0,
                labels=["backend", "products"],
            ),
            Task(
                id="test-1",
                name="Test authentication system",  # Avoiding "Write tests" to prevent misclassification
                description="Create unit and integration tests for auth endpoints",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=4.0,
                labels=["testing", "auth"],
            ),
            Task(
                id="test-2",
                name="QA product functionality",  # Using QA keyword which should classify correctly
                description="Test product CRUD operations comprehensively",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=3.0,
                labels=["testing", "products"],
            ),
            Task(
                id="deploy-1",
                name="Deploy to production",
                description="Release application to production environment",
                status=TaskStatus.TODO,
                priority=Priority.LOW,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=2.0,
                labels=["deployment"],
            ),
        ]

    def test_task_classification(self, sample_tasks):
        """Test that tasks are classified correctly"""
        # Test implementation tasks
        impl_tasks = TaskClassifier.filter_by_type(
            sample_tasks, TaskType.IMPLEMENTATION
        )
        assert len(impl_tasks) == 2
        assert all(task.id.startswith("impl-") for task in impl_tasks)

        # Test testing tasks - this is where the issue might be
        test_tasks = TaskClassifier.filter_by_type(sample_tasks, TaskType.TESTING)
        assert len(test_tasks) == 2, f"Expected 2 testing tasks, got {len(test_tasks)}"
        assert all(task.id.startswith("test-") for task in test_tasks)

        # Test deployment tasks
        deploy_tasks = TaskClassifier.filter_by_type(sample_tasks, TaskType.DEPLOYMENT)
        assert len(deploy_tasks) == 1
        assert deploy_tasks[0].id == "deploy-1"

    def test_apply_testing_dependencies(self, sample_tasks, safety_checker):
        """Test that testing dependencies are correctly applied"""
        # Apply testing dependencies
        updated_tasks = safety_checker.apply_testing_dependencies(sample_tasks)

        # Get test tasks
        test_tasks = [task for task in updated_tasks if task.id.startswith("test-")]

        # Verify test-1 depends on impl-1 (matching auth labels)
        test_1 = next(task for task in test_tasks if task.id == "test-1")
        assert (
            "impl-1" in test_1.dependencies
        ), "Test task should depend on related implementation"
        assert (
            "impl-2" not in test_1.dependencies
        ), "Test task should not depend on unrelated implementation"

        # Verify test-2 depends on impl-2 (matching products labels)
        test_2 = next(task for task in test_tasks if task.id == "test-2")
        assert (
            "impl-2" in test_2.dependencies
        ), "Test task should depend on related implementation"
        assert (
            "impl-1" not in test_2.dependencies
        ), "Test task should not depend on unrelated implementation"

    def test_apply_deployment_dependencies(self, sample_tasks, safety_checker):
        """Test that deployment dependencies include all implementation and test tasks"""
        # First apply testing dependencies
        tasks_with_test_deps = safety_checker.apply_testing_dependencies(sample_tasks)

        # Then apply deployment dependencies
        final_tasks = safety_checker.apply_deployment_dependencies(tasks_with_test_deps)

        # Get deployment task
        deploy_task = next(task for task in final_tasks if task.id == "deploy-1")

        # Verify it depends on all implementation and test tasks
        expected_dependencies = {"impl-1", "impl-2", "test-1", "test-2"}
        actual_dependencies = set(deploy_task.dependencies)

        assert (
            expected_dependencies == actual_dependencies
        ), f"Deployment should depend on all implementation and test tasks. Expected: {expected_dependencies}, Got: {actual_dependencies}"

    def test_related_task_finding_by_labels(self, sample_tasks, safety_checker):
        """Test the _find_related_tasks method matches by labels"""
        test_task = next(task for task in sample_tasks if task.id == "test-1")
        impl_tasks = [task for task in sample_tasks if task.id.startswith("impl-")]

        related = SafetyChecker._find_related_tasks(test_task, impl_tasks)

        # Should find impl-1 due to matching "auth" label
        assert len(related) == 1
        assert related[0].id == "impl-1"

    def test_related_task_finding_by_keywords(self):
        """Test the _find_related_tasks method matches by keywords"""
        test_task = Task(
            id="test-1",
            name="Test user management system",
            description="Test user CRUD operations",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=4.0,
            labels=[],  # No labels to force keyword matching
        )

        impl_tasks = [
            Task(
                id="impl-1",
                name="Implement user management service",
                description="Create user management API",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=8.0,
                labels=[],
            ),
            Task(
                id="impl-2",
                name="Build product catalog",
                description="Product management system",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=6.0,
                labels=[],
            ),
        ]

        related = SafetyChecker._find_related_tasks(test_task, impl_tasks)

        # Should find impl-1 due to matching "user" and "management" keywords
        assert len(related) == 1
        assert related[0].id == "impl-1"

    def test_dependency_validation(self, sample_tasks, safety_checker):
        """Test dependency validation catches invalid references"""
        # Add an invalid dependency
        sample_tasks[0].dependencies.append("non-existent-task")

        errors = SafetyChecker.validate_dependencies(sample_tasks)

        assert len(errors) == 1
        assert "non-existent-task" in errors[0]
        assert sample_tasks[0].name in errors[0]

    def test_classification_priority_issue(self):
        """Test the specific issue where 'Write tests' gets misclassified"""
        # This test demonstrates the current issue
        task = Task(
            id="test-1",
            name="Write tests for authentication",
            description="Create comprehensive test suite",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=4.0,
            labels=["testing"],
        )

        task_type = TaskClassifier.classify(task)

        # With the enhanced classifier integrated, this now correctly identifies "Write tests" as TESTING
        assert task_type == TaskType.TESTING, f"Expected TESTING but got {task_type}"
