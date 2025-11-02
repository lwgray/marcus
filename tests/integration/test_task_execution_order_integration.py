"""
Integration tests for Task Execution Order System.

Tests the complete workflow of task classification, phase dependency enforcement,
and integration with the natural language processing tools.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, List
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.core.phase_dependency_enforcer import PhaseDependencyEnforcer
from src.integrations.enhanced_task_classifier import EnhancedTaskClassifier
from src.integrations.nlp_base import NaturalLanguageTaskCreator
from src.integrations.nlp_task_utils import SafetyChecker, TaskBuilder


class MockKanbanClient:
    """Mock kanban client for testing."""

    def __init__(self) -> None:
        self.created_tasks: List[Any] = []

    async def create_task(self, task_data: Any) -> Any:
        """Mock task creation."""
        self.created_tasks.append(task_data)
        return {"id": f"kb-{len(self.created_tasks)}", "status": "success"}


class MockNLPTaskCreator(NaturalLanguageTaskCreator):
    """Test implementation of NaturalLanguageTaskCreator."""

    async def process_natural_language(
        self, description: str, **kwargs: Any
    ) -> List[Task]:
        """Simple test implementation."""
        # Return predefined tasks based on description
        if "authentication" in description.lower():
            return [
                self._create_task("1", "Design authentication system", ["auth"]),
                self._create_task("2", "Setup auth database", ["auth"]),
                self._create_task("3", "Implement login API", ["auth"]),
                self._create_task("4", "Write auth tests", ["auth"]),
                self._create_task("5", "Document auth API", ["auth"]),
            ]
        return []

    def _create_task(self, id: str, name: str, labels: List[str]) -> Task:
        """Helper to create tasks."""
        return Task(
            id=id,
            name=name,
            description=f"Description for {name}",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
            estimated_hours=4.0,
            actual_hours=0.0,
            dependencies=[],
            labels=labels,
        )


class TestTaskExecutionOrderIntegration:
    """Integration tests for task execution order system."""

    @pytest.fixture
    def kanban_client(self) -> MockKanbanClient:
        """Create mock kanban client."""
        return MockKanbanClient()

    @pytest.fixture
    def task_creator(self, kanban_client: MockKanbanClient) -> MockNLPTaskCreator:
        """Create test task creator."""
        return MockNLPTaskCreator(kanban_client)

    @pytest.mark.asyncio
    async def test_complete_workflow_with_phase_dependencies(
        self, task_creator, kanban_client
    ):
        """Test complete workflow from NLP to kanban with phase dependencies."""
        # Process natural language to create tasks
        tasks = await task_creator.process_natural_language(
            "Build authentication system"
        )

        assert len(tasks) == 5

        # Apply safety checks (which includes phase dependencies)
        tasks = await task_creator.apply_safety_checks(tasks)

        # Verify phase dependencies were applied
        task_map = {t.id: t for t in tasks}

        # Design has no dependencies
        assert task_map["1"].dependencies == []

        # Infrastructure depends on design
        assert "1" in task_map["2"].dependencies

        # Implementation depends on design and infrastructure
        assert "1" in task_map["3"].dependencies
        assert "2" in task_map["3"].dependencies

        # Testing depends on all previous phases
        assert set(["1", "2", "3"]).issubset(set(task_map["4"].dependencies))

        # Documentation depends on design, infrastructure, and implementation
        # but not testing (they're parallel phases)
        assert set(["1", "2", "3"]).issubset(set(task_map["5"].dependencies))

        # Create tasks on kanban board
        await task_creator.create_tasks_on_board(tasks)

        # Verify all tasks were created
        assert len(kanban_client.created_tasks) == 5

        # Verify dependencies were preserved in kanban data
        for i, task_data in enumerate(kanban_client.created_tasks):
            assert task_data["dependencies"] == tasks[i].dependencies

    @pytest.mark.asyncio
    async def test_classification_integration(self, task_creator):
        """Test task classification integration."""
        tasks = await task_creator.process_natural_language(
            "Build authentication system"
        )

        # Classify tasks
        classified = task_creator.classify_tasks_with_details(tasks)

        expected_types = [
            "design",
            "infrastructure",
            "implementation",
            "testing",
            "documentation",
        ]

        for task_id, expected_type in zip(["1", "2", "3", "4", "5"], expected_types):
            assert classified[task_id]["type"] == expected_type
            assert classified[task_id]["confidence"] > 0.5

    @pytest.mark.asyncio
    async def test_multi_feature_project(self, kanban_client: MockKanbanClient) -> None:
        """Test handling of multiple features with isolated dependencies."""
        # Create a more complex task creator
        creator = MockNLPTaskCreator(kanban_client)

        # Override process_natural_language for multi-feature
        async def multi_feature_process(description: str) -> List[Task]:
            return [
                # Auth feature
                creator._create_task("auth-1", "Design authentication", ["auth"]),
                creator._create_task("auth-2", "Implement auth API", ["auth"]),
                creator._create_task("auth-3", "Test authentication", ["auth"]),
                # Payment feature
                creator._create_task("pay-1", "Design payment system", ["payment"]),
                creator._create_task(
                    "pay-2", "Implement payment processing", ["payment"]
                ),
                creator._create_task("pay-3", "Test payment flow", ["payment"]),
            ]

        # Replace the method using monkey patching
        setattr(creator, "process_natural_language", multi_feature_process)

        tasks = await creator.process_natural_language("Build complete system")
        tasks = await creator.apply_safety_checks(tasks)

        # Verify feature isolation
        task_map = {t.id: t for t in tasks}

        # Auth dependencies stay within auth
        assert "pay-1" not in task_map["auth-2"].dependencies
        assert "pay-2" not in task_map["auth-3"].dependencies

        # Payment dependencies stay within payment
        assert "auth-1" not in task_map["pay-2"].dependencies
        assert "auth-2" not in task_map["pay-3"].dependencies

    def test_phase_enforcer_with_classifier(self):
        """Test phase enforcer integration with enhanced classifier."""
        enforcer = PhaseDependencyEnforcer()
        classifier = EnhancedTaskClassifier()

        # The enforcer should use the enhanced classifier
        assert isinstance(enforcer.task_classifier, EnhancedTaskClassifier)

        # Test classification through enforcer
        task = Task(
            id="1",
            name="Write unit tests for user service",
            description="Create comprehensive test suite",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
            estimated_hours=4.0,
            actual_hours=0.0,
            dependencies=[],
            labels=[],
        )

        task_type = enforcer.task_classifier.classify(task)
        assert task_type.value == "testing"

    def test_safety_checker_integration(self):
        """Test safety checker with enhanced classification."""
        safety_checker = SafetyChecker()

        tasks = [
            Task(
                id="1",
                name="Fix bug in login",
                description="",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=datetime.now(timezone.utc) + timedelta(days=1),
                estimated_hours=2.0,
                actual_hours=0.0,
                dependencies=[],
                labels=["login", "bugfix"],  # Add login label for relation
            ),
            Task(
                id="2",
                name="Test login bug fix",
                description="",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=datetime.now(timezone.utc) + timedelta(days=1),
                estimated_hours=1.0,
                actual_hours=0.0,
                dependencies=[],
                labels=["login", "bugfix"],  # Add login label for relation
            ),
        ]

        # Apply testing dependencies
        tasks = safety_checker.apply_testing_dependencies(tasks)

        # Test task should depend on implementation
        assert "1" in tasks[1].dependencies

    @pytest.mark.asyncio
    async def test_error_handling_in_workflow(self, task_creator):
        """Test error handling throughout the workflow."""
        # Test with empty task list
        result = await task_creator.apply_safety_checks([])
        assert result == []

        # Test with invalid dependencies
        tasks = [
            task_creator._create_task("1", "Test something", ["test"]),
        ]
        tasks[0].dependencies = ["non-existent-task"]

        errors = SafetyChecker.validate_dependencies(tasks)
        assert len(errors) > 0
        assert "invalid dependency" in errors[0]

    def test_performance_with_realistic_project(self):
        """Test performance with a realistic project size."""
        import time

        enforcer = PhaseDependencyEnforcer()

        # Create 50 tasks across 5 features
        tasks = []
        features = ["auth", "payment", "notification", "dashboard", "reporting"]
        phases = ["Design", "Setup", "Implement", "Test", "Document"]

        task_id = 1
        for feature in features:
            for i, phase in enumerate(phases):
                for j in range(2):  # 2 tasks per phase
                    tasks.append(
                        Task(
                            id=str(task_id),
                            name=f"{phase} {feature} component {j+1}",
                            description=f"Work on {feature} {phase.lower()}",
                            status=TaskStatus.TODO,
                            priority=Priority.MEDIUM,
                            assigned_to=None,
                            created_at=datetime.now(timezone.utc),
                            updated_at=datetime.now(timezone.utc),
                            due_date=datetime.now(timezone.utc) + timedelta(days=30),
                            estimated_hours=4.0,
                            actual_hours=0.0,
                            dependencies=[],
                            labels=[feature],
                        )
                    )
                    task_id += 1

        start_time = time.time()
        result = enforcer.enforce_phase_dependencies(tasks)
        end_time = time.time()

        # Should complete quickly even with 50 tasks
        assert (end_time - start_time) < 0.5

        # Verify dependencies were created
        total_deps = sum(len(t.dependencies) for t in result)
        assert total_deps > 100  # Should have many dependencies

        # Verify no cross-feature dependencies
        for task in result:
            if task.dependencies:  # Only check tasks with dependencies
                task_feature = task.labels[0]
                for dep_id in task.dependencies:
                    dep_task = next(t for t in result if t.id == dep_id)
                    assert (
                        dep_task.labels[0] == task_feature
                    ), f"Cross-feature dependency: {task.name} ({task_feature}) depends on {dep_task.name} ({dep_task.labels[0]})"
