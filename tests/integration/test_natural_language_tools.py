#!/usr/bin/env python3
"""
Test suite for Natural Language Tools

Tests the MCP tools that expose Marcus's AI capabilities for:
1. Creating projects from natural language descriptions
2. Adding features to existing projects
"""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.ai.advanced.prd.advanced_parser import TaskGenerationResult
from src.core.models import Priority, Task, TaskStatus

# Test imports
from src.integrations.nlp_tools import (
    NaturalLanguageFeatureAdder,
    NaturalLanguageProjectCreator,
    add_feature_natural_language,
)
from src.marcus_mcp.tools.nlp import create_project


@pytest.fixture(autouse=True)
def _mock_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure ANTHROPIC_API_KEY is set so config validation passes."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-for-unit-tests")


@pytest.fixture(autouse=True)
def _clear_dedup_cache():
    """Clear create_project's dedup cache between tests."""
    from src.marcus_mcp.tools import nlp as nlp_module

    nlp_module._recent_create_project_calls.clear()
    yield
    nlp_module._recent_create_project_calls.clear()


class TestCreateProjectFromNaturalLanguage:
    """Test create_project MCP tool in src.marcus_mcp.tools.nlp."""

    @pytest.fixture
    def mock_state(self):
        """Setup mock state for create_project.

        Returns
        -------
        Mock
            Mock server state pre-wired with a kanban client, ai engine,
            project registry, and project manager.
        """
        mock_state = Mock()
        mock_state.log_event = Mock()

        mock_state.kanban_client = Mock()
        mock_state.kanban_client.provider = "planka"
        mock_state.kanban_client.project_id = "planka-test-project"
        mock_state.kanban_client.board_id = "planka-test-board"
        mock_state.kanban_client.connect = AsyncMock()
        mock_state.kanban_client.create_task = AsyncMock(
            side_effect=self._mock_create_task
        )

        mock_state.ai_engine = AsyncMock()
        mock_state.subtask_manager = Mock()
        mock_state._subtasks_migrated = False

        mock_state.project_registry = Mock()
        mock_state.project_registry.add_project = AsyncMock(
            return_value="marcus-proj-test"
        )
        mock_state.project_registry.get_active_project = AsyncMock(return_value=None)
        mock_state.project_manager = Mock()
        mock_state.project_manager.switch_project = AsyncMock(return_value=True)
        mock_state.project_manager.get_kanban_client = AsyncMock(
            return_value=mock_state.kanban_client
        )

        mock_state.project_tasks = []
        mock_state.project_state = {}
        mock_state.refresh_project_state = AsyncMock()

        return mock_state

    def _mock_create_task(self, task_data):
        """Mock task creation"""
        return Task(
            id=f"task-{len(self.created_tasks) + 1}",
            name=task_data.get("name", "Mock Task"),
            description=task_data.get("description", "Mock task description"),
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=task_data.get("estimated_hours", 1.0),
        )

    @pytest.mark.asyncio
    async def test_create_simple_project(self, mock_state):
        """Test creating a simple project from natural language."""
        self.created_tasks = []

        description = "I need a todo app with user accounts and task sharing"
        project_name = "Todo App MVP"

        creator_result = {
            "success": True,
            "project_name": project_name,
            "tasks_created": 3,
            "board": {
                "project_name": project_name,
                "board_name": "Main Board",
            },
        }

        with (
            patch(
                "src.integrations.nlp_tools.NaturalLanguageProjectCreator"
            ) as MockCreator,
            patch(
                "src.integrations.kanban_factory.KanbanFactory.create"
            ) as mock_factory,
        ):
            mock_factory.return_value = mock_state.kanban_client
            mock_creator = MockCreator.return_value
            mock_creator.create_project_from_description = AsyncMock(
                return_value=creator_result
            )

            result = await create_project(
                description=description,
                project_name=project_name,
                options={"provider": "planka"},
                state=mock_state,
            )

        assert result["success"] is True
        assert result["project_name"] == project_name
        assert result["tasks_created"] >= 0

    @pytest.mark.asyncio
    async def test_create_project_with_options(self, mock_state):
        """Test creating project with deadline and team size options."""
        description = "E-commerce platform with payment integration"
        project_name = "E-commerce MVP"
        options = {
            "provider": "planka",
            "deadline": "2024-12-31",
            "team_size": 5,
            "tech_stack": ["python", "react", "postgresql"],
        }

        creator_result = {
            "success": True,
            "project_name": project_name,
            "tasks_created": 0,
            "board": {
                "project_name": project_name,
                "board_name": "Main Board",
            },
        }

        with (
            patch(
                "src.integrations.nlp_tools.NaturalLanguageProjectCreator"
            ) as MockCreator,
            patch(
                "src.integrations.kanban_factory.KanbanFactory.create"
            ) as mock_factory,
        ):
            mock_factory.return_value = mock_state.kanban_client
            mock_creator = MockCreator.return_value
            mock_creator.create_project_from_description = AsyncMock(
                return_value=creator_result
            )

            result = await create_project(
                description=description,
                project_name=project_name,
                options=options,
                state=mock_state,
            )

        assert result["success"] is True
        assert result["project_name"] == project_name

    @pytest.mark.asyncio
    async def test_create_project_validation(self, mock_state):
        """Test input validation rejects empty description and name."""
        # Empty description
        result = await create_project(
            description="",
            project_name="Test",
            options=None,
            state=mock_state,
        )
        assert result["success"] is False
        assert "description" in result["error"].lower()

        # Empty project name
        result = await create_project(
            description="Valid description",
            project_name="",
            options=None,
            state=mock_state,
        )
        assert result["success"] is False
        assert "project_name" in result["error"]

    @pytest.mark.asyncio
    async def test_create_project_kanban_error(self, mock_state):
        """Test handling kanban provider initialization errors."""
        # Force a provider mismatch so create_project tries to rebuild
        # the kanban client via KanbanFactory — then make the factory fail.
        mock_state.kanban_client.provider = "different-provider"

        with patch(
            "src.integrations.kanban_factory.KanbanFactory.create",
            side_effect=Exception("Connection failed"),
        ):
            result = await create_project(
                description="Test project description",
                project_name="Test",
                options={"provider": "planka"},
                state=mock_state,
            )

        assert result["success"] is False
        assert "Failed to initialize kanban provider" in result["error"]


class TestAddFeatureNaturalLanguage:
    """Test add_feature_natural_language tool"""

    @pytest.fixture
    def mock_state_with_tasks(self):
        """Setup mock state with existing tasks"""
        mock_state = Mock()
        mock_state.kanban_client = AsyncMock()
        mock_state.kanban_client.create_task = AsyncMock()
        mock_state.ai_engine = AsyncMock()
        mock_state.initialize_kanban = AsyncMock()
        mock_state.refresh_project_state = AsyncMock()

        # Add existing project tasks
        mock_state.project_tasks = [
            Task(
                id="1",
                name="User authentication",
                status=TaskStatus.DONE,
                priority=Priority.HIGH,
                labels=["backend", "auth"],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            Task(
                id="2",
                name="Basic UI",
                status=TaskStatus.IN_PROGRESS,
                priority=Priority.MEDIUM,
                labels=["frontend"],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
        ]

        return mock_state

    @pytest.mark.asyncio
    async def test_add_feature_to_project(self, mock_state_with_tasks):
        """Test adding a feature to existing project"""
        feature_description = "Add real-time notifications for task updates"

        # Mock AI analysis
        mock_state_with_tasks.ai_engine.analyze_feature_request = AsyncMock(
            return_value={
                "required_tasks": [
                    {
                        "name": "Design notification system",
                        "description": "Design real-time notification architecture",
                        "estimated_hours": 8,
                        "labels": ["design", "feature"],
                        "critical": False,
                    },
                    {
                        "name": "Implement WebSocket server",
                        "description": "Set up WebSocket for real-time updates",
                        "estimated_hours": 16,
                        "labels": ["backend", "feature"],
                        "critical": True,
                    },
                ]
            }
        )

        # Mock task creation
        created_tasks = []

        async def mock_create_task(task_data):
            task = Task(
                id=f"task-{len(created_tasks) + 3}",
                name=task_data["name"],
                description=task_data.get("description", ""),
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                labels=task_data.get("labels", []),
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            created_tasks.append(task)
            return task

        mock_state_with_tasks.kanban_client.create_task = mock_create_task

        result = await add_feature_natural_language(
            feature_description=feature_description, state=mock_state_with_tasks
        )

        assert result["success"] == True
        assert result["tasks_created"] > 0
        assert "integration_points" in result

    @pytest.mark.asyncio
    async def test_add_feature_validation(self, mock_state_with_tasks):
        """Test input validation for add_feature"""
        # Test empty description
        result = await add_feature_natural_language(
            feature_description="", state=mock_state_with_tasks
        )
        assert result["success"] == False
        assert "required" in result["error"]

    @pytest.mark.asyncio
    async def test_add_feature_no_existing_project(self):
        """Test adding feature when no project exists"""
        mock_state = Mock()
        mock_state.kanban_client = AsyncMock()
        mock_state.project_tasks = []  # No existing tasks
        mock_state.initialize_kanban = AsyncMock()

        result = await add_feature_natural_language(
            feature_description="Add new feature", state=mock_state
        )

        assert result["success"] == False
        assert "No existing project found" in result["error"]

    @pytest.mark.asyncio
    async def test_add_feature_integration_points(self, mock_state_with_tasks):
        """Test different integration point options"""
        feature_description = "Add export functionality"

        # Mock AI analysis
        mock_state_with_tasks.ai_engine.analyze_feature_request = AsyncMock(
            return_value={"required_tasks": []}
        )
        mock_state_with_tasks.ai_engine.analyze_integration_points = AsyncMock(
            return_value={
                "dependent_task_ids": ["1"],
                "suggested_phase": "post-deployment",
                "confidence": 0.9,
            }
        )

        for integration_point in [
            "auto_detect",
            "after_current",
            "parallel",
            "new_phase",
        ]:
            result = await add_feature_natural_language(
                feature_description=feature_description,
                integration_point=integration_point,
                state=mock_state_with_tasks,
            )

            # Should handle all integration points without error
            assert "error" not in result or result["success"] == True


class TestNaturalLanguageCreators:
    """Test the underlying creator classes"""

    @pytest.mark.asyncio
    async def test_project_creator_phases(self):
        """Test project phase extraction"""
        mock_client = AsyncMock()
        mock_ai = AsyncMock()

        creator = NaturalLanguageProjectCreator(mock_client, mock_ai)

        tasks = [
            Task(
                id="1",
                name="Setup infra",
                labels=["infrastructure"],
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            Task(
                id="2",
                name="API development",
                labels=["backend"],
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            Task(
                id="3",
                name="UI components",
                labels=["frontend"],
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
        ]

        phases = creator._extract_phases(tasks)
        assert "infrastructure" in phases
        assert "backend" in phases
        assert "frontend" in phases

    @pytest.mark.asyncio
    async def test_feature_adder_complexity(self):
        """Test feature complexity calculation"""
        mock_client = AsyncMock()
        mock_ai = AsyncMock()

        adder = NaturalLanguageFeatureAdder(mock_client, mock_ai, [])

        # Low complexity
        tasks_low = [
            Task(
                id="1",
                name="Add button",
                estimated_hours=4,
                status=TaskStatus.TODO,
                priority=Priority.LOW,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        ]
        assert adder._calculate_complexity(tasks_low) == "low"

        # Medium complexity
        tasks_medium = [
            Task(
                id="1",
                name="Feature 1",
                estimated_hours=15,
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            Task(
                id="2",
                name="Feature 2",
                estimated_hours=10,
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
        ]
        assert adder._calculate_complexity(tasks_medium) == "medium"

        # High complexity
        tasks_high = [
            Task(
                id="1",
                name="Major feature",
                estimated_hours=50,
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        ]
        assert adder._calculate_complexity(tasks_high) == "high"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
