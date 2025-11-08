"""
Unit tests for Context Bridge enhancements
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from src.core.context import Context, DependentTask, TaskContext
from src.core.models import Priority, Task, TaskStatus


class TestContextBridge:
    """Test suite for Context Bridge functionality"""

    @pytest.fixture
    def context(self):
        """Create context instance"""
        return Context()

    @pytest.fixture
    def sample_tasks(self):
        """Create sample task hierarchy"""
        return [
            Task(
                id="api-task",
                name="Create user API endpoints",
                description="Build REST API for user management",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=16.0,
                dependencies=[],
                labels=["backend", "api", "rest"],
            ),
            Task(
                id="frontend-task",
                name="Build user management UI",
                description="Create React components for user CRUD",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=20.0,
                dependencies=["api-task"],
                labels=["frontend", "react", "ui"],
            ),
            Task(
                id="test-task",
                name="Write integration tests",
                description="Test user management flow",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=8.0,
                dependencies=["api-task", "frontend-task"],
                labels=["testing", "integration"],
            ),
        ]

    @pytest.mark.asyncio
    async def test_analyze_dependencies(self, context, sample_tasks):
        """Test dependency analysis creates proper dependency map"""
        dep_map = await context.analyze_dependencies(sample_tasks)

        # api-task should have frontend-task and test-task as dependents
        assert "api-task" in dep_map
        assert "frontend-task" in dep_map["api-task"]
        assert "test-task" in dep_map["api-task"]

        # frontend-task should have test-task as dependent
        assert "frontend-task" in dep_map
        assert "test-task" in dep_map["frontend-task"]

        # test-task should have no dependents
        assert "test-task" not in dep_map or len(dep_map.get("test-task", [])) == 0

    def test_infer_needed_interface(self, context, sample_tasks):
        """Test interface inference between dependent tasks"""
        api_task = sample_tasks[0]
        frontend_task = sample_tasks[1]
        test_task = sample_tasks[2]

        # Frontend needs API endpoints
        interface = context.infer_needed_interface(frontend_task, api_task.id)
        assert "REST API endpoints" in interface

        # Test task needs both API and UI
        interface = context.infer_needed_interface(test_task, api_task.id)
        assert "API endpoints" in interface or "test" in interface.lower()

        interface = context.infer_needed_interface(test_task, frontend_task.id)
        assert "UI components" in interface or "interface" in interface.lower()

    @pytest.mark.asyncio
    async def test_context_with_dependent_tasks(self, context, sample_tasks):
        """Test getting context includes dependent task information"""
        # Set up dependencies
        dep_map = await context.analyze_dependencies(sample_tasks)

        # Add dependent tasks for api-task
        for dep_task_id in dep_map.get("api-task", []):
            dep_task = next(t for t in sample_tasks if t.id == dep_task_id)
            expected_interface = context.infer_needed_interface(dep_task, "api-task")

            context.add_dependency(
                "api-task",
                DependentTask(
                    task_id=dep_task.id,
                    task_name=dep_task.name,
                    expected_interface=expected_interface,
                ),
            )

        # Get context for api-task
        context_data = await context.get_context("api-task", [])

        assert context_data.task_id == "api-task"
        assert len(context_data.dependent_tasks) == 2

        # Check dependent task details
        dep_names = [dt["task_name"] for dt in context_data.dependent_tasks]
        assert "Build user management UI" in dep_names
        assert "Write integration tests" in dep_names

        # Check interfaces are included
        for dep in context_data.dependent_tasks:
            assert "expected_interface" in dep
            assert dep["expected_interface"] != ""

    @pytest.mark.asyncio
    async def test_add_implementation(self, context):
        """Test adding implementation context"""
        impl_data = {
            "endpoints": [
                {
                    "method": "POST",
                    "path": "/api/users",
                    "returns": {"id": "string", "email": "string"},
                },
                {
                    "method": "GET",
                    "path": "/api/users/:id",
                    "returns": {"id": "string", "email": "string", "name": "string"},
                },
            ],
            "models": ["User", "UserProfile"],
            "authentication": "JWT",
        }

        await context.add_implementation("api-task", impl_data)

        # Get context for a dependent task and verify implementation is included
        context_data = await context.get_context("frontend-task", ["api-task"])

        assert context_data.previous_implementations is not None
        assert "api-task" in context_data.previous_implementations
        assert "endpoints" in context_data.previous_implementations["api-task"]
        assert len(context_data.previous_implementations["api-task"]["endpoints"]) == 2

    def test_dependency_inference_patterns(self, context):
        """Test various dependency inference patterns"""
        # Test data pipeline pattern
        etl_task = Task(
            id="etl-1",
            name="Extract customer data",
            description="",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=4.0,
            dependencies=[],
            labels=["data", "extraction"],
        )

        transform_task = Task(
            id="transform-1",
            name="Transform customer records",
            description="",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=6.0,
            dependencies=["etl-1"],
            labels=["data", "transformation"],
        )

        interface = context.infer_needed_interface(transform_task, etl_task.id)
        assert (
            "data format" in interface.lower() or "extracted data" in interface.lower()
        )

        # Test ML pipeline pattern
        train_task = Task(
            id="ml-1",
            name="Train customer churn model",
            description="",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=8.0,
            dependencies=[],
            labels=["ml", "training", "model"],
        )

        deploy_task = Task(
            id="ml-2",
            name="Deploy model to production",
            description="",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=4.0,
            dependencies=["ml-1"],
            labels=["ml", "deployment", "production"],
        )

        interface = context.infer_needed_interface(deploy_task, train_task.id)
        assert "model" in interface.lower() and (
            "artifact" in interface.lower() or "file" in interface.lower()
        )
