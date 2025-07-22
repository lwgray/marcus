"""
Unit tests for Phase Dependency Enforcer

Tests the phase-based dependency enforcement system that ensures tasks
follow the correct development lifecycle order.
"""

from typing import List
from unittest.mock import Mock, patch

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.core.phase_dependency_enforcer import (
    DependencyType,
    TaskPhase,
)
from src.core.phase_dependency_enforcer import (
    FeatureGroup,
    PhaseDependencyEnforcer,
)
from src.integrations.nlp_task_utils import TaskType


class TestPhaseDependencyEnforcer:
    """Test suite for PhaseDependencyEnforcer"""

    @pytest.fixture
    def enforcer(self):
        """Create a PhaseDependencyEnforcer instance"""
        return PhaseDependencyEnforcer()

    @pytest.fixture
    def sample_tasks(self):
        """Create sample tasks for testing"""
        return [
            Task(
                id="design-001",
                name="Design authentication system",
                description="Create authentication flow diagrams",
                labels=["auth", "design"],
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                dependencies=[],
            ),
            Task(
                id="impl-001",
                name="Implement login API",
                description="Build REST endpoints for user login",
                labels=["auth", "backend"],
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                dependencies=[],
            ),
            Task(
                id="test-001",
                name="Test authentication endpoints",
                description="Write unit tests for auth API",
                labels=["auth", "testing"],
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                dependencies=[],
            ),
            Task(
                id="doc-001",
                name="Document authentication API",
                description="Write API documentation for auth endpoints",
                labels=["auth", "documentation"],
                status=TaskStatus.TODO,
                priority=Priority.LOW,
                dependencies=[],
            ),
        ]

    def test_single_feature_phase_ordering(self, enforcer, sample_tasks):
        """Test that tasks within a single feature follow phase ordering"""
        # Apply phase dependencies
        result_tasks = enforcer.enforce_phase_dependencies(sample_tasks)

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

    def test_multiple_features_isolation(self, enforcer):
        """Test that dependencies are isolated within features"""
        tasks = [
            # Auth feature
            Task(id="auth-design", name="Design auth system", labels=["auth"]),
            Task(id="auth-impl", name="Implement auth", labels=["auth"]),
            Task(id="auth-test", name="Test auth", labels=["auth"]),
            # Payment feature
            Task(id="pay-design", name="Design payment system", labels=["payment"]),
            Task(id="pay-impl", name="Implement payment", labels=["payment"]),
            Task(id="pay-test", name="Test payment", labels=["payment"]),
        ]

        result_tasks = enforcer.enforce_phase_dependencies(tasks)
        task_dict = {task.id: task for task in result_tasks}

        # Auth implementation should only depend on auth design, not payment design
        assert "auth-design" in task_dict["auth-impl"].dependencies
        assert "pay-design" not in task_dict["auth-impl"].dependencies

        # Payment test should only depend on payment tasks
        assert "pay-impl" in task_dict["pay-test"].dependencies
        assert "auth-impl" not in task_dict["pay-test"].dependencies

    def test_feature_identification_from_name(self, enforcer):
        """Test feature identification from task names"""
        task1 = Task(id="1", name="Design authentication flow", labels=[])
        task2 = Task(id="2", name="Build payment processing", labels=[])
        task3 = Task(id="3", name="Create user dashboard", labels=[])

        assert enforcer._identify_task_feature(task1) == "auth"
        assert enforcer._identify_task_feature(task2) == "payment"
        assert enforcer._identify_task_feature(task3) == "dashboard"

    def test_feature_identification_from_labels(self, enforcer):
        """Test feature identification prioritizes explicit labels"""
        task1 = Task(id="1", name="Generic task", labels=["feature:checkout"])
        task2 = Task(id="2", name="Another task", labels=["authentication"])

        assert enforcer._identify_task_feature(task1) == "checkout"
        assert enforcer._identify_task_feature(task2) == "authentication"

    def test_phase_classification(self, enforcer):
        """Test task phase classification"""
        tasks = [
            Task(id="1", name="Design API architecture", labels=[]),
            Task(id="2", name="Implement user service", labels=[]),
            Task(id="3", name="Write unit tests for API", labels=[]),
            Task(id="4", name="Document API endpoints", labels=[]),
        ]

        phase_tasks = enforcer._classify_tasks_by_phase(tasks)

        assert len(phase_tasks[TaskPhase.DESIGN]) == 1
        assert len(phase_tasks[TaskPhase.IMPLEMENTATION]) == 1
        assert len(phase_tasks[TaskPhase.TESTING]) == 1
        assert len(phase_tasks[TaskPhase.DOCUMENTATION]) == 1

    def test_enhanced_task_support(self, enforcer):
        """Test that EnhancedTask models get proper metadata"""
        tasks = [
            EnhancedTask(
                id="design-001",
                name="Design system",
                labels=["feature:auth"],
                dependencies=[],
            ),
            EnhancedTask(
                id="impl-001",
                name="Implement system",
                labels=["feature:auth"],
                dependencies=[],
            ),
        ]

        result_tasks = enforcer.enforce_phase_dependencies(tasks)

        # Check that phase metadata was set
        assert result_tasks[0].phase == TaskPhase.DESIGN
        assert result_tasks[1].phase == TaskPhase.IMPLEMENTATION

        # Check dependency metadata
        impl_task = next(t for t in result_tasks if t.id == "impl-001")
        assert impl_task.dependency_metadata.get("design-001") == DependencyType.PHASE

    def test_preserve_existing_dependencies(self, enforcer):
        """Test that existing manual dependencies are preserved"""
        tasks = [
            Task(id="design-001", name="Design API", dependencies=[]),
            Task(id="impl-001", name="Implement API", dependencies=["external-001"]),
            Task(id="test-001", name="Test API", dependencies=["manual-001"]),
        ]

        result_tasks = enforcer.enforce_phase_dependencies(tasks)
        task_dict = {task.id: task for task in result_tasks}

        # Check that manual dependencies are preserved
        assert "external-001" in task_dict["impl-001"].dependencies
        assert "manual-001" in task_dict["test-001"].dependencies

        # And phase dependencies are added
        assert "design-001" in task_dict["impl-001"].dependencies
        assert "impl-001" in task_dict["test-001"].dependencies

    def test_validate_phase_ordering(self, enforcer):
        """Test phase ordering validation"""
        # Valid ordering
        valid_tasks = [
            Task(id="1", name="Design", dependencies=[]),
            Task(id="2", name="Implement", dependencies=["1"]),
            Task(id="3", name="Test", dependencies=["2"]),
        ]

        is_valid, errors = enforcer.validate_phase_ordering(valid_tasks)
        assert is_valid
        assert len(errors) == 0

        # Invalid ordering - test depends on documentation
        invalid_tasks = [
            Task(id="1", name="Test something", dependencies=["2"]),
            Task(id="2", name="Document something", dependencies=[]),
        ]

        is_valid, errors = enforcer.validate_phase_ordering(invalid_tasks)
        assert not is_valid
        assert len(errors) > 0
        assert "Phase order violation" in errors[0]

    def test_empty_project(self, enforcer):
        """Test handling of empty project"""
        result = enforcer.enforce_phase_dependencies([])
        assert result == []

    def test_single_task_project(self, enforcer):
        """Test project with single task"""
        tasks = [Task(id="1", name="Implement feature", dependencies=[])]
        result = enforcer.enforce_phase_dependencies(tasks)

        assert len(result) == 1
        assert result[0].dependencies == []

    def test_all_same_phase_tasks(self, enforcer):
        """Test project where all tasks are in same phase"""
        tasks = [
            Task(id="1", name="Implement feature A", labels=["feature-a"]),
            Task(id="2", name="Implement feature B", labels=["feature-b"]),
            Task(id="3", name="Implement feature C", labels=["feature-c"]),
        ]

        result = enforcer.enforce_phase_dependencies(tasks)

        # No dependencies should be added between tasks in same phase
        for task in result:
            assert task.dependencies == []

    def test_infrastructure_phase_ordering(self, enforcer):
        """Test that infrastructure phase is ordered correctly"""
        tasks = [
            Task(id="design-001", name="Design system architecture", labels=["infra"]),
            Task(id="infra-001", name="Setup database", labels=["infra"]),
            Task(id="impl-001", name="Implement API", labels=["infra"]),
        ]

        result_tasks = enforcer.enforce_phase_dependencies(tasks)
        task_dict = {task.id: task for task in result_tasks}

        # Infrastructure should depend on design
        assert "design-001" in task_dict["infra-001"].dependencies

        # Implementation should depend on both design and infrastructure
        assert "design-001" in task_dict["impl-001"].dependencies
        assert "infra-001" in task_dict["impl-001"].dependencies

    def test_get_phase_statistics(self, enforcer, sample_tasks):
        """Test phase statistics generation"""
        # Apply dependencies first
        result_tasks = enforcer.enforce_phase_dependencies(sample_tasks)

        stats = enforcer.get_phase_statistics(result_tasks)

        assert stats["total_tasks"] == 4
        assert stats["feature_count"] == 1
        assert "auth" in stats["features_identified"]
        assert stats["dependency_count"] > 0
        assert stats["phase_distribution"]["DESIGN"] == 1
        assert stats["phase_distribution"]["IMPLEMENTATION"] == 1
        assert stats["phase_distribution"]["TESTING"] == 1
        assert stats["phase_distribution"]["DOCUMENTATION"] == 1

    def test_complex_feature_extraction(self, enforcer):
        """Test complex feature name extraction patterns"""
        test_cases = [
            ("Design user authentication system", "auth"),
            ("Build payment processing service", "payment"),
            ("Create dashboard analytics module", "dashboard"),
            ("Implement notification service", "notification"),
            ("Test user registration flow", "user"),
            ("Document API gateway", "api"),
        ]

        for task_name, expected_feature in test_cases:
            task = Task(id="1", name=task_name, labels=[])
            assert enforcer._identify_task_feature(task) == expected_feature

    @pytest.mark.parametrize(
        "task_name,expected_phase",
        [
            ("Design user interface", TaskPhase.DESIGN),
            ("Plan system architecture", TaskPhase.DESIGN),
            ("Create wireframes", TaskPhase.DESIGN),
            ("Setup database", TaskPhase.INFRASTRUCTURE),
            ("Configure servers", TaskPhase.INFRASTRUCTURE),
            ("Implement login feature", TaskPhase.IMPLEMENTATION),
            ("Build API endpoints", TaskPhase.IMPLEMENTATION),
            ("Write unit tests", TaskPhase.TESTING),
            ("Create test scenarios", TaskPhase.TESTING),
            ("Document API", TaskPhase.DOCUMENTATION),
            ("Write user guide", TaskPhase.DOCUMENTATION),
            ("Deploy to production", TaskPhase.DEPLOYMENT),
            ("Release version 1.0", TaskPhase.DEPLOYMENT),
        ],
    )
    def test_phase_classification_variations(self, enforcer, task_name, expected_phase):
        """Test phase classification with various task names"""
        task = Task(id="1", name=task_name, labels=[])
        phase_tasks = enforcer._classify_tasks_by_phase([task])

        assert task in phase_tasks[expected_phase]
