"""
Unit tests for HybridMarcusTools.

This module tests the orchestration of Marcus hybrid tools, including mode switching,
board analysis, project creation, and intelligent task assignment.

Notes
-----
These tests mock all external dependencies including kanban client, board analyzer,
context detector, and mode registry to ensure fast, isolated unit tests.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import pytest_asyncio

from src.core.models import Priority, Task, TaskStatus
from src.detection.board_analyzer import BoardState, WorkflowPattern
from src.detection.context_detector import MarcusMode, ModeRecommendation
from src.modes.creator.template_library import ProjectSize
from src.orchestration.hybrid_tools import HybridMarcusTools


class TestHybridMarcusTools:
    """
    Test suite for HybridMarcusTools class.

    Tests orchestration of mode switching, board analysis, project creation,
    and intelligent task coordination without external dependencies.
    """

    @pytest.fixture
    def mock_kanban_client(self):
        """Create a mock kanban client with all necessary methods."""
        client = AsyncMock()
        client.get_all_tasks = AsyncMock(return_value=[])
        client.get_available_tasks = AsyncMock(return_value=[])
        client.create_task = AsyncMock()
        client.update_task = AsyncMock()
        return client

    @pytest.fixture
    def mock_board_state(self):
        """Create a mock board state for testing."""
        state = Mock(spec=BoardState)
        state.task_count = 10
        state.structure_score = 0.75
        state.metadata_completeness = 0.8
        state.workflow_pattern = WorkflowPattern.PHASED
        state.phases_detected = ["planning", "development", "testing"]
        state.components_detected = ["frontend", "backend"]
        state.is_empty = False
        state.is_chaotic = False
        state.is_well_structured = True
        return state

    @pytest.fixture
    def mock_mode_recommendation(self):
        """Create a mock mode recommendation."""
        return ModeRecommendation(
            recommended_mode=MarcusMode.ADAPTIVE,
            confidence=0.9,
            reasoning="Board is well-structured with clear phases",
            alternative_modes=[MarcusMode.ENRICHER],
        )

    @pytest.fixture
    def sample_task(self):
        """Create a sample task for testing."""
        return Task(
            id="TASK-001",
            name="Implement feature",
            description="Add new functionality",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=None,
            updated_at=None,
            due_date=None,
            estimated_hours=4.0,
            labels=["backend", "api"],
        )

    @pytest_asyncio.fixture
    async def hybrid_tools(self, mock_kanban_client):
        """Create HybridMarcusTools instance with mocked dependencies."""
        with (
            patch("src.orchestration.hybrid_tools.BoardAnalyzer") as MockBoardAnalyzer,
            patch(
                "src.orchestration.hybrid_tools.ContextDetector"
            ) as MockContextDetector,
            patch("src.orchestration.hybrid_tools.ModeRegistry") as MockModeRegistry,
        ):

            # Set up board analyzer mock
            mock_board_analyzer = Mock()
            MockBoardAnalyzer.return_value = mock_board_analyzer

            # Set up context detector mock
            mock_context_detector = Mock()
            MockContextDetector.return_value = mock_context_detector

            # Set up mode registry mock
            mock_mode_registry = Mock()
            mock_mode_registry.current_mode = MarcusMode.ADAPTIVE
            MockModeRegistry.return_value = mock_mode_registry

            # Create instance
            tools = HybridMarcusTools(mock_kanban_client)

            # Attach mocks for testing
            tools.board_analyzer = mock_board_analyzer
            tools.context_detector = mock_context_detector
            tools.mode_registry = mock_mode_registry

            return tools

    async def test_initialization(self, mock_kanban_client):
        """Test HybridMarcusTools initialization."""
        # Arrange & Act
        tools = HybridMarcusTools(mock_kanban_client)

        # Assert
        assert tools.kanban_client == mock_kanban_client
        assert tools.board_analyzer is not None
        assert tools.context_detector is not None
        assert tools.mode_registry is not None

    async def test_switch_mode_success(self, hybrid_tools):
        """Test successful mode switching."""
        # Arrange
        hybrid_tools.mode_registry.switch_mode = AsyncMock(
            return_value={"success": True, "mode": "creator"}
        )

        # Act
        result = await hybrid_tools.switch_mode(
            mode="creator", reason="User requested creator mode", user_id="user123"
        )

        # Assert
        assert result["success"] is True
        hybrid_tools.mode_registry.switch_mode.assert_called_once_with(
            mode=MarcusMode.CREATOR,
            reason="User requested creator mode",
            user_id="user123",
        )
        hybrid_tools.context_detector.record_mode_switch.assert_called_once_with(
            "user123", MarcusMode.CREATOR
        )

    async def test_switch_mode_invalid_mode(self, hybrid_tools):
        """Test mode switching with invalid mode name."""
        # Act
        result = await hybrid_tools.switch_mode(
            mode="invalid_mode", reason="Testing invalid mode"
        )

        # Assert
        assert result["success"] is False
        assert "Invalid mode" in result["error"]
        assert result["available_modes"] == ["creator", "enricher", "adaptive"]
        hybrid_tools.mode_registry.switch_mode.assert_not_called()

    async def test_switch_mode_failure(self, hybrid_tools):
        """Test mode switching when registry fails."""
        # Arrange
        hybrid_tools.mode_registry.switch_mode = AsyncMock(
            return_value={"success": False, "error": "Mode not available"}
        )

        # Act
        result = await hybrid_tools.switch_mode(mode="creator")

        # Assert
        assert result["success"] is False
        hybrid_tools.context_detector.record_mode_switch.assert_not_called()

    async def test_get_current_mode(self, hybrid_tools):
        """Test getting current mode information."""
        # Arrange
        expected_mode_info = {
            "mode": "adaptive",
            "capabilities": ["task_assignment", "dependency_analysis"],
        }
        hybrid_tools.mode_registry.get_current_mode = AsyncMock(
            return_value=expected_mode_info
        )

        # Act
        result = await hybrid_tools.get_current_mode()

        # Assert
        assert result == expected_mode_info
        hybrid_tools.mode_registry.get_current_mode.assert_called_once()

    async def test_analyze_board_context_success(
        self, hybrid_tools, mock_board_state, mock_mode_recommendation, sample_task
    ):
        """Test successful board context analysis."""
        # Arrange
        hybrid_tools.kanban_client.get_all_tasks.return_value = [sample_task]
        hybrid_tools.board_analyzer.analyze_board = AsyncMock(
            return_value=mock_board_state
        )
        hybrid_tools.context_detector.detect_optimal_mode = AsyncMock(
            return_value=mock_mode_recommendation
        )
        hybrid_tools.context_detector.get_mode_suggestions.return_value = [
            "Consider enricher mode to improve metadata"
        ]

        # Act
        result = await hybrid_tools.analyze_board_context(
            board_id="project_board", user_id="user123"
        )

        # Assert
        assert result["success"] is True
        assert result["board_analysis"]["task_count"] == 10
        assert result["board_analysis"]["structure_score"] == 0.75
        assert result["mode_recommendation"]["recommended_mode"] == "adaptive"
        assert result["mode_recommendation"]["confidence"] == 0.9
        assert len(result["suggestions"]) == 1
        assert result["current_mode"] == "adaptive"

        hybrid_tools.kanban_client.get_all_tasks.assert_called_once()
        hybrid_tools.board_analyzer.analyze_board.assert_called_once_with(
            "project_board", [sample_task]
        )

    async def test_analyze_board_context_error(self, hybrid_tools):
        """Test board context analysis with error."""
        # Arrange
        hybrid_tools.kanban_client.get_all_tasks.side_effect = Exception(
            "Kanban connection failed"
        )

        # Act
        result = await hybrid_tools.analyze_board_context()

        # Assert
        assert result["success"] is False
        assert "Kanban connection failed" in result["error"]

    async def test_create_project_from_template_success(self, hybrid_tools):
        """Test successful project creation from template."""
        # Arrange
        mock_creator_mode = Mock()
        mock_creator_mode.create_project_from_template = AsyncMock(
            return_value={
                "success": True,
                "tasks": [
                    {
                        "name": "Setup project",
                        "description": "Initialize project structure",
                        "labels": ["setup"],
                        "estimated_hours": 2,
                        "priority": "high",
                    }
                ],
            }
        )
        hybrid_tools.mode_registry.current_mode = MarcusMode.CREATOR
        hybrid_tools.mode_registry.get_mode_handler.return_value = mock_creator_mode

        # Act
        result = await hybrid_tools.create_project_from_template(
            template_name="web",
            project_name="MyWebApp",
            size="medium",
            excluded_phases=["deployment"],
            additional_labels=["urgent"],
        )

        # Assert
        assert result["success"] is True
        assert result["tasks_created_on_board"] is True
        hybrid_tools.kanban_client.create_task.assert_called_once()

        # Verify task creation call
        call_args = hybrid_tools.kanban_client.create_task.call_args[0][0]
        assert call_args["name"] == "Setup project"
        assert "urgent" in call_args["labels"] or "setup" in call_args["labels"]

    async def test_create_project_from_template_mode_switch(self, hybrid_tools):
        """Test project creation with automatic mode switch."""
        # Arrange
        hybrid_tools.mode_registry.current_mode = MarcusMode.ADAPTIVE
        hybrid_tools.mode_registry.switch_mode = AsyncMock(
            return_value={"success": True}
        )

        mock_creator_mode = Mock()
        mock_creator_mode.create_project_from_template = AsyncMock(
            return_value={"success": True, "tasks": []}
        )
        hybrid_tools.mode_registry.get_mode_handler.return_value = mock_creator_mode

        # Act
        await hybrid_tools.create_project_from_template(
            template_name="api", project_name="MyAPI"
        )

        # Assert
        hybrid_tools.mode_registry.switch_mode.assert_called_once_with(
            MarcusMode.CREATOR,
            reason="Switching to creator mode for project generation",
        )

    async def test_create_project_from_template_invalid_size(self, hybrid_tools):
        """Test project creation with invalid size parameter."""
        # Arrange
        hybrid_tools.mode_registry.current_mode = MarcusMode.CREATOR
        mock_creator_mode = Mock()
        hybrid_tools.mode_registry.get_mode_handler.return_value = mock_creator_mode

        # Act
        result = await hybrid_tools.create_project_from_template(
            template_name="web", project_name="MyApp", size="invalid_size"
        )

        # Assert
        assert result["success"] is False
        assert "Invalid project size" in result["error"]

    async def test_create_project_from_template_no_creator_mode(self, hybrid_tools):
        """Test project creation when creator mode is not available."""
        # Arrange
        hybrid_tools.mode_registry.current_mode = MarcusMode.CREATOR
        hybrid_tools.mode_registry.get_mode_handler.return_value = None

        # Act
        result = await hybrid_tools.create_project_from_template(
            template_name="web", project_name="MyApp"
        )

        # Assert
        assert result["success"] is False
        assert "Creator mode is not available" in result["error"]

    async def test_create_project_from_description_success(self, hybrid_tools):
        """Test successful project creation from natural language description."""
        # Arrange
        mock_creator_mode = Mock()
        mock_creator_mode.create_from_description = AsyncMock(
            return_value={
                "success": True,
                "tasks": [
                    {
                        "name": "Create user model",
                        "description": "Define user data structure",
                        "labels": ["backend", "database"],
                        "estimated_hours": 3,
                    }
                ],
            }
        )
        hybrid_tools.mode_registry.current_mode = MarcusMode.CREATOR
        hybrid_tools.mode_registry.get_mode_handler.return_value = mock_creator_mode

        # Act
        result = await hybrid_tools.create_project_from_description(
            description="Build a social media platform with user profiles",
            project_name="SocialApp",
        )

        # Assert
        assert result["success"] is True
        assert result["tasks_created_on_board"] is True
        mock_creator_mode.create_from_description.assert_called_once_with(
            description="Build a social media platform with user profiles",
            project_name="SocialApp",
        )

    async def test_get_available_templates(self, hybrid_tools):
        """Test getting available templates."""
        # Arrange
        mock_creator_mode = Mock()
        mock_creator_mode.get_available_templates = AsyncMock(
            return_value={"success": True, "templates": ["web", "api", "mobile"]}
        )
        hybrid_tools.mode_registry.get_mode_handler.return_value = mock_creator_mode

        # Act
        result = await hybrid_tools.get_available_templates()

        # Assert
        assert result["success"] is True
        assert result["templates"] == ["web", "api", "mobile"]

    async def test_get_available_templates_no_creator_mode(self, hybrid_tools):
        """Test getting templates when creator mode is not available."""
        # Arrange
        hybrid_tools.mode_registry.get_mode_handler.return_value = None

        # Act
        result = await hybrid_tools.get_available_templates()

        # Assert
        assert result["success"] is False
        assert "Creator mode is not available" in result["error"]

    async def test_preview_template(self, hybrid_tools):
        """Test template preview functionality."""
        # Arrange
        mock_creator_mode = Mock()
        mock_creator_mode.preview_template = AsyncMock(
            return_value={
                "success": True,
                "preview": {
                    "task_count": 25,
                    "phases": ["planning", "development", "testing"],
                    "estimated_total_hours": 120,
                },
            }
        )
        hybrid_tools.mode_registry.get_mode_handler.return_value = mock_creator_mode

        # Act
        result = await hybrid_tools.preview_template(template_name="web", size="large")

        # Assert
        assert result["success"] is True
        assert result["preview"]["task_count"] == 25
        mock_creator_mode.preview_template.assert_called_once_with(
            template_name="web", size="large"
        )

    async def test_get_next_task_intelligent_success(self, hybrid_tools, sample_task):
        """Test intelligent task assignment success."""
        # Arrange
        mock_adaptive_mode = Mock()
        mock_adaptive_mode.find_optimal_task_for_agent = AsyncMock(
            return_value=sample_task
        )
        hybrid_tools.mode_registry.current_mode = MarcusMode.ADAPTIVE
        hybrid_tools.mode_registry.get_mode_handler.return_value = mock_adaptive_mode
        hybrid_tools.kanban_client.get_all_tasks.return_value = [sample_task]

        # Act
        result = await hybrid_tools.get_next_task_intelligent(
            agent_id="agent-001", agent_skills=["backend", "python"]
        )

        # Assert
        assert result["success"] is True
        assert result["task"]["id"] == "TASK-001"
        assert result["task"]["name"] == "Implement feature"
        assert "assignment_reasoning" in result

    async def test_get_next_task_intelligent_no_tasks(self, hybrid_tools):
        """Test intelligent task assignment when no tasks are available."""
        # Arrange
        mock_adaptive_mode = Mock()
        mock_adaptive_mode.find_optimal_task_for_agent = AsyncMock(return_value=None)
        mock_adaptive_mode.get_blocking_analysis = AsyncMock(
            return_value={
                "blocked_tasks": 5,
                "blocking_chains": ["Task A blocks B blocks C"],
            }
        )
        hybrid_tools.mode_registry.current_mode = MarcusMode.ADAPTIVE
        hybrid_tools.mode_registry.get_mode_handler.return_value = mock_adaptive_mode
        hybrid_tools.kanban_client.get_all_tasks.return_value = []

        # Act
        result = await hybrid_tools.get_next_task_intelligent(agent_id="agent-001")

        # Assert
        assert result["success"] is False
        assert result["reason"] == "no_available_tasks"
        assert "blocking_analysis" in result

    async def test_get_next_task_intelligent_mode_switch(self, hybrid_tools):
        """Test intelligent task assignment with automatic mode switch."""
        # Arrange
        hybrid_tools.mode_registry.current_mode = MarcusMode.CREATOR
        hybrid_tools.mode_registry.switch_mode = AsyncMock(
            return_value={"success": True}
        )

        mock_adaptive_mode = Mock()
        mock_adaptive_mode.find_optimal_task_for_agent = AsyncMock(return_value=None)
        mock_adaptive_mode.get_blocking_analysis = AsyncMock(return_value={})
        hybrid_tools.mode_registry.get_mode_handler.return_value = mock_adaptive_mode
        hybrid_tools.kanban_client.get_all_tasks.return_value = []

        # Act
        await hybrid_tools.get_next_task_intelligent(agent_id="agent-001")

        # Assert
        hybrid_tools.mode_registry.switch_mode.assert_called_once_with(
            MarcusMode.ADAPTIVE,
            reason="Switching to adaptive mode for intelligent task assignment",
        )

    async def test_get_next_task_intelligent_error(self, hybrid_tools):
        """Test intelligent task assignment with error handling."""
        # Arrange
        hybrid_tools.mode_registry.current_mode = MarcusMode.ADAPTIVE
        mock_adaptive_mode = Mock()
        hybrid_tools.mode_registry.get_mode_handler.return_value = mock_adaptive_mode
        hybrid_tools.kanban_client.get_all_tasks.side_effect = Exception(
            "Database error"
        )

        # Act
        result = await hybrid_tools.get_next_task_intelligent(agent_id="agent-001")

        # Assert
        assert result["success"] is False
        assert "Database error" in result["error"]

    async def test_get_blocking_analysis_success(self, hybrid_tools):
        """Test successful blocking analysis."""
        # Arrange
        mock_adaptive_mode = Mock()
        mock_adaptive_mode.get_blocking_analysis = AsyncMock(
            return_value={
                "total_tasks": 20,
                "blocked_tasks": 8,
                "blocking_chains": [
                    "Auth -> User Profile -> Settings",
                    "Database -> API -> Frontend",
                ],
            }
        )
        hybrid_tools.mode_registry.get_mode_handler.return_value = mock_adaptive_mode
        hybrid_tools.kanban_client.get_all_tasks.return_value = []

        # Act
        result = await hybrid_tools.get_blocking_analysis()

        # Assert
        assert result["success"] is True
        assert result["analysis"]["blocked_tasks"] == 8
        assert len(result["analysis"]["blocking_chains"]) == 2

    async def test_get_blocking_analysis_no_adaptive_mode(self, hybrid_tools):
        """Test blocking analysis when adaptive mode is not available."""
        # Arrange
        hybrid_tools.mode_registry.get_mode_handler.return_value = None

        # Act
        result = await hybrid_tools.get_blocking_analysis()

        # Assert
        assert result["success"] is False
        assert "Adaptive mode is not available" in result["error"]

    async def test_get_blocking_analysis_error(self, hybrid_tools):
        """Test blocking analysis with error handling."""
        # Arrange
        mock_adaptive_mode = Mock()
        hybrid_tools.mode_registry.get_mode_handler.return_value = mock_adaptive_mode
        hybrid_tools.kanban_client.get_all_tasks.side_effect = Exception(
            "Network timeout"
        )

        # Act
        result = await hybrid_tools.get_blocking_analysis()

        # Assert
        assert result["success"] is False
        assert "Network timeout" in result["error"]

    async def test_create_tasks_on_board_success(self, hybrid_tools):
        """Test successful task creation on kanban board."""
        # Arrange
        tasks = [
            {
                "name": "Task 1",
                "description": "First task",
                "labels": ["frontend"],
                "estimated_hours": 4,
                "priority": "high",
            },
            {
                "name": "Task 2",
                "description": "Second task",
                "labels": ["backend"],
                "estimated_hours": 6,
                "priority": "medium",
            },
        ]

        # Act
        await hybrid_tools._create_tasks_on_board(tasks)

        # Assert
        assert hybrid_tools.kanban_client.create_task.call_count == 2

        # Verify first task call
        first_call = hybrid_tools.kanban_client.create_task.call_args_list[0][0][0]
        assert first_call["name"] == "Task 1"
        assert first_call["priority"] == "high"

    async def test_create_tasks_on_board_partial_failure(self, hybrid_tools, caplog):
        """Test task creation with some failures."""
        # Arrange
        tasks = [
            {"name": "Task 1", "description": "First task"},
            {"name": "Task 2", "description": "Second task"},
        ]

        # Make first task succeed, second fail
        hybrid_tools.kanban_client.create_task.side_effect = [
            None,
            Exception("API error"),
        ]

        # Act
        with caplog.at_level(logging.ERROR):
            await hybrid_tools._create_tasks_on_board(tasks)

        # Assert
        assert hybrid_tools.kanban_client.create_task.call_count == 2
        assert "Error creating task 'Task 2' on board" in caplog.text

    def test_get_tool_definitions(self, hybrid_tools):
        """Test getting MCP tool definitions."""
        # Act
        tools = hybrid_tools.get_tool_definitions()

        # Assert
        assert len(tools) == 7

        # Verify tool names
        tool_names = [tool["name"] for tool in tools]
        expected_names = [
            "switch_mode",
            "analyze_board_context",
            "create_project_from_template",
            "create_project_from_description",
            "get_available_templates",
            "get_next_task_intelligent",
            "get_blocking_analysis",
        ]
        assert set(tool_names) == set(expected_names)

        # Verify switch_mode tool structure
        switch_mode_tool = next(t for t in tools if t["name"] == "switch_mode")
        assert "inputSchema" in switch_mode_tool
        assert switch_mode_tool["inputSchema"]["properties"]["mode"]["enum"] == [
            "creator",
            "enricher",
            "adaptive",
        ]
        assert switch_mode_tool["inputSchema"]["required"] == ["mode"]

    async def test_mode_switch_without_user_id(self, hybrid_tools):
        """Test mode switching without user ID doesn't record switch."""
        # Arrange
        hybrid_tools.mode_registry.switch_mode = AsyncMock(
            return_value={"success": True}
        )

        # Act
        result = await hybrid_tools.switch_mode(mode="creator")

        # Assert
        assert result["success"] is True
        hybrid_tools.context_detector.record_mode_switch.assert_not_called()

    async def test_analyze_board_with_default_values(
        self, hybrid_tools, mock_board_state, mock_mode_recommendation
    ):
        """Test board analysis with default board_id and user_id."""
        # Arrange
        hybrid_tools.kanban_client.get_all_tasks.return_value = []
        hybrid_tools.board_analyzer.analyze_board = AsyncMock(
            return_value=mock_board_state
        )
        hybrid_tools.context_detector.detect_optimal_mode = AsyncMock(
            return_value=mock_mode_recommendation
        )
        hybrid_tools.context_detector.get_mode_suggestions.return_value = []

        # Act
        result = await hybrid_tools.analyze_board_context()

        # Assert
        assert result["success"] is True
        hybrid_tools.board_analyzer.analyze_board.assert_called_once_with("default", [])
        hybrid_tools.context_detector.detect_optimal_mode.assert_called_once()

        # Verify default values were used
        call_args = hybrid_tools.context_detector.detect_optimal_mode.call_args[1]
        assert call_args["user_id"] == "anonymous"
        assert call_args["board_id"] == "default"

    async def test_create_project_from_template_mode_switch_failure(self, hybrid_tools):
        """Test project creation when mode switch fails."""
        # Arrange
        hybrid_tools.mode_registry.current_mode = MarcusMode.ADAPTIVE
        hybrid_tools.mode_registry.switch_mode = AsyncMock(
            return_value={"success": False, "error": "Mode switch failed"}
        )

        # Act
        result = await hybrid_tools.create_project_from_template(
            template_name="web", project_name="MyApp"
        )

        # Assert
        assert result["success"] is False
        assert result["error"] == "Mode switch failed"
        hybrid_tools.mode_registry.get_mode_handler.assert_not_called()

    async def test_create_project_from_description_no_creator_mode(self, hybrid_tools):
        """Test project creation from description when creator mode is not available."""
        # Arrange
        hybrid_tools.mode_registry.current_mode = MarcusMode.CREATOR
        hybrid_tools.mode_registry.get_mode_handler.return_value = None

        # Act
        result = await hybrid_tools.create_project_from_description(
            description="Build an app", project_name="MyApp"
        )

        # Assert
        assert result["success"] is False
        assert "Creator mode is not available" in result["error"]

    async def test_create_project_from_description_with_mode_switch(self, hybrid_tools):
        """Test project creation from description with automatic mode switch."""
        # Arrange
        hybrid_tools.mode_registry.current_mode = MarcusMode.ADAPTIVE
        hybrid_tools.mode_registry.switch_mode = AsyncMock(
            return_value={"success": True}
        )

        mock_creator_mode = Mock()
        mock_creator_mode.create_from_description = AsyncMock(
            return_value={"success": True, "tasks": []}
        )
        hybrid_tools.mode_registry.get_mode_handler.return_value = mock_creator_mode

        # Act
        await hybrid_tools.create_project_from_description(
            description="Build a web app", project_name="WebApp"
        )

        # Assert
        hybrid_tools.mode_registry.switch_mode.assert_called_once_with(
            MarcusMode.CREATOR,
            reason="Switching to creator mode for project generation from description",
        )

    async def test_preview_template_no_creator_mode(self, hybrid_tools):
        """Test template preview when creator mode is not available."""
        # Arrange
        hybrid_tools.mode_registry.get_mode_handler.return_value = None

        # Act
        result = await hybrid_tools.preview_template(template_name="web", size="medium")

        # Assert
        assert result["success"] is False
        assert "Creator mode is not available" in result["error"]

    async def test_get_next_task_intelligent_no_adaptive_mode(self, hybrid_tools):
        """Test intelligent task assignment when adaptive mode is not available."""
        # Arrange
        hybrid_tools.mode_registry.current_mode = MarcusMode.ADAPTIVE
        hybrid_tools.mode_registry.get_mode_handler.return_value = None

        # Act
        result = await hybrid_tools.get_next_task_intelligent(agent_id="agent-001")

        # Assert
        assert result["success"] is False
        assert "Adaptive mode is not available" in result["error"]
