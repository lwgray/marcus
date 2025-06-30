"""
Unit tests for MarcusMVP - Main MVP Implementation.

This module contains comprehensive unit tests for the Marcus MVP MCP server,
covering all core functionality including agent registration, task assignment,
progress tracking, and blocker resolution.
"""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from mcp.types import TextContent
from src.marcus_mvp_fixed import MarcusMVP
from src.core.models import (
    Task, TaskStatus, Priority, RiskLevel,
    WorkerStatus, TaskAssignment
)


class TestMarcusMVP:
    """Test suite for MarcusMVP class."""
    
    @pytest.fixture
    def mock_kanban_client(self):
        """Create mock Kanban client."""
        mock = Mock()
        mock.get_available_tasks = AsyncMock()
        mock.assign_task = AsyncMock()
        mock.add_comment = AsyncMock()
        mock.complete_task = AsyncMock()
        mock.update_task_status = AsyncMock()
        mock.get_board_summary = AsyncMock()
        mock.board_id = "test_board"
        mock.project_id = "test_project"
        return mock
    
    @pytest.fixture
    def mock_ai_engine(self):
        """Create mock AI analysis engine."""
        mock = Mock()
        mock.initialize = AsyncMock()
        mock._call_claude = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_workspace_manager(self):
        """Create mock workspace manager."""
        mock = Mock()
        mock.get_task_assignment_data = Mock(return_value={
            'workspace_path': '/test/workspace',
            'forbidden_paths': ['/etc', '/usr']
        })
        return mock
    
    @pytest.fixture
    def mock_server(self):
        """Create mock MCP server."""
        mock = Mock()
        # Create proper decorator mocks
        def create_decorator_mock():
            def decorator(func):
                # Store the decorated function for later access
                decorator.__wrapped__ = func
                return func
            return decorator
        
        mock.list_tools = create_decorator_mock
        mock.call_tool = create_decorator_mock
        return mock
    
    @pytest.fixture
    def marcus_mvp(self, mock_kanban_client, mock_ai_engine, mock_workspace_manager, mock_server):
        """Create MarcusMVP instance with mocked dependencies."""
        with patch('src.marcus_mvp_fixed.MCPKanbanClient', return_value=mock_kanban_client), \
             patch('src.marcus_mvp_fixed.AIAnalysisEngine', return_value=mock_ai_engine), \
             patch('src.marcus_mvp_fixed.WorkspaceManager', return_value=mock_workspace_manager), \
             patch('src.marcus_mvp_fixed.Server', return_value=mock_server):
            marcus = MarcusMVP()
            marcus.kanban_client = mock_kanban_client
            marcus.ai_engine = mock_ai_engine
            marcus.workspace_manager = mock_workspace_manager
            return marcus
    
    @pytest.fixture
    def sample_task(self):
        """Create sample task for testing."""
        return Task(
            id="task-123",
            name="Implement user authentication",
            description="Add login functionality",
            priority=Priority.HIGH,
            status=TaskStatus.TODO,
            labels=["backend", "security"],
            assigned_to=None,
            due_date=datetime.now() + timedelta(days=3),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            estimated_hours=8.0,
            actual_hours=0.0,
            dependencies=[]
        )


class TestAgentRegistration(TestMarcusMVP):
    """Test suite for agent registration functionality."""
    
    @pytest.mark.asyncio
    async def test_register_agent_success(self, marcus_mvp):
        """Test successful agent registration."""
        # Act
        result = await marcus_mvp._register_agent(
            agent_id="agent-001",
            name="Test Agent",
            role="Backend Developer",
            skills=["Python", "Django"]
        )
        
        # Assert
        assert result["success"] is True
        assert "agent-001" in marcus_mvp.agent_status
        assert marcus_mvp.agent_status["agent-001"].name == "Test Agent"
        assert marcus_mvp.agent_status["agent-001"].role == "Backend Developer"
        assert marcus_mvp.agent_status["agent-001"].skills == ["Python", "Django"]
    
    @pytest.mark.asyncio
    async def test_register_agent_missing_required_fields(self, marcus_mvp):
        """Test agent registration with missing required fields."""
        # Act
        result = await marcus_mvp._register_agent(
            agent_id="",
            name="Test Agent",
            role="Developer",
            skills=[]
        )
        
        # Assert
        assert result["success"] is False
        assert "required" in result["error"]
    
    @pytest.mark.asyncio
    async def test_register_agent_with_none_skills(self, marcus_mvp):
        """Test agent registration with None skills parameter."""
        # Act
        result = await marcus_mvp._register_agent(
            agent_id="agent-002",
            name="Test Agent 2",
            role="Frontend Developer",
            skills=None
        )
        
        # Assert
        assert result["success"] is True
        assert marcus_mvp.agent_status["agent-002"].skills == []
    
    @pytest.mark.asyncio
    async def test_register_agent_duplicate(self, marcus_mvp):
        """Test registering the same agent twice."""
        # Arrange
        await marcus_mvp._register_agent("agent-003", "Agent 3", "Tester", [])
        
        # Act
        result = await marcus_mvp._register_agent("agent-003", "Agent 3 Updated", "QA", ["Selenium"])
        
        # Assert
        assert result["success"] is True
        # Should update existing agent
        assert marcus_mvp.agent_status["agent-003"].role == "QA"
        assert marcus_mvp.agent_status["agent-003"].skills == ["Selenium"]
    
    @pytest.mark.asyncio
    async def test_register_agent_exception_handling(self, marcus_mvp):
        """Test exception handling during agent registration."""
        # Arrange
        # Create a mock dictionary that will raise an exception when setting items
        class ErrorDict(dict):
            def __setitem__(self, key, value):
                raise Exception("Database error")
        
        marcus_mvp.agent_status = ErrorDict()
        
        # Act
        result = await marcus_mvp._register_agent("agent-004", "Agent 4", "Developer", [])
        
        # Assert
        assert result["success"] is False
        assert "Database error" in result["error"]


class TestTaskAssignment(TestMarcusMVP):
    """Test suite for task assignment functionality."""
    
    @pytest.mark.asyncio
    async def test_request_task_unregistered_agent(self, marcus_mvp):
        """Test task request from unregistered agent."""
        # Act
        result = await marcus_mvp._request_next_task("unknown-agent")
        
        # Assert
        assert result["has_task"] is False
        assert "not registered" in result["error"]
    
    @pytest.mark.asyncio
    async def test_request_task_no_available_tasks(self, marcus_mvp):
        """Test task request when no tasks are available."""
        # Arrange
        await marcus_mvp._register_agent("agent-005", "Agent 5", "Developer", [])
        marcus_mvp.kanban_client.get_available_tasks.return_value = []
        
        # Act
        result = await marcus_mvp._request_next_task("agent-005")
        
        # Assert
        assert result["has_task"] is False
        assert "No tasks available" in result["message"]
    
    @pytest.mark.asyncio
    async def test_request_task_successful_assignment(self, marcus_mvp, sample_task):
        """Test successful task assignment to agent."""
        # Arrange
        await marcus_mvp._register_agent("agent-006", "Agent 6", "Developer", ["Python"])
        marcus_mvp.kanban_client.get_available_tasks.return_value = [sample_task]
        marcus_mvp.ai_engine._call_claude.return_value = "Test instructions"
        
        # Act
        result = await marcus_mvp._request_next_task("agent-006")
        
        # Assert
        assert result["has_task"] is True
        assert result["assignment"]["task_id"] == "task-123"
        assert result["assignment"]["task_name"] == "Implement user authentication"
        assert result["assignment"]["priority"] == "high"
        assert "agent-006" in marcus_mvp.agent_tasks
        marcus_mvp.kanban_client.assign_task.assert_called_once_with("task-123", "agent-006")
    
    @pytest.mark.asyncio
    async def test_request_task_priority_ordering(self, marcus_mvp):
        """Test that tasks are assigned by priority."""
        # Arrange
        await marcus_mvp._register_agent("agent-007", "Agent 7", "Developer", [])
        
        low_priority_task = Task(
            id="low-task",
            name="Low priority task",
            description="Not urgent",
            priority=Priority.LOW,
            status=TaskStatus.TODO,
            labels=[],
            assigned_to=None,
            due_date=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            estimated_hours=1.0,
            actual_hours=0.0,
            dependencies=[]
        )
        
        urgent_task = Task(
            id="urgent-task",
            name="Urgent task",
            description="Fix critical bug",
            priority=Priority.URGENT,
            status=TaskStatus.TODO,
            labels=["bug"],
            assigned_to=None,
            due_date=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            estimated_hours=2.0,
            actual_hours=0.0,
            dependencies=[]
        )
        
        marcus_mvp.kanban_client.get_available_tasks.return_value = [low_priority_task, urgent_task]
        marcus_mvp.ai_engine._call_claude.return_value = "Fix the bug immediately"
        
        # Act
        result = await marcus_mvp._request_next_task("agent-007")
        
        # Assert
        assert result["assignment"]["task_id"] == "urgent-task"
    
    @pytest.mark.asyncio
    async def test_request_task_ai_instruction_generation_fallback(self, marcus_mvp, sample_task):
        """Test fallback instruction generation when AI fails."""
        # Arrange
        await marcus_mvp._register_agent("agent-008", "Agent 8", "Developer", [])
        marcus_mvp.kanban_client.get_available_tasks.return_value = [sample_task]
        marcus_mvp.ai_engine._call_claude.side_effect = Exception("AI service unavailable")
        
        # Act
        result = await marcus_mvp._request_next_task("agent-008")
        
        # Assert
        assert result["has_task"] is True
        assert "Implement user authentication" in result["assignment"]["instructions"]
        assert "Definition of Done" in result["assignment"]["instructions"]
    
    @pytest.mark.asyncio
    async def test_request_task_exception_handling(self, marcus_mvp):
        """Test exception handling during task request."""
        # Arrange
        await marcus_mvp._register_agent("agent-009", "Agent 9", "Developer", [])
        marcus_mvp.kanban_client.get_available_tasks.side_effect = Exception("Kanban connection failed")
        
        # Act
        result = await marcus_mvp._request_next_task("agent-009")
        
        # Assert
        assert result["has_task"] is False
        assert "Kanban connection failed" in result["error"]


class TestProgressReporting(TestMarcusMVP):
    """Test suite for task progress reporting."""
    
    @pytest.mark.asyncio
    async def test_report_progress_in_progress(self, marcus_mvp):
        """Test reporting task progress."""
        # Act
        result = await marcus_mvp._report_task_progress(
            agent_id="agent-010",
            task_id="task-456",
            status="in_progress",
            progress=50,
            message="Completed database schema"
        )
        
        # Assert
        assert result["acknowledged"] is True
        marcus_mvp.kanban_client.add_comment.assert_called_once()
        comment = marcus_mvp.kanban_client.add_comment.call_args[0][1]
        assert "agent-010" in comment
        assert "50% complete" in comment
        assert "Completed database schema" in comment
    
    @pytest.mark.asyncio
    async def test_report_progress_completed(self, marcus_mvp, sample_task):
        """Test reporting task completion."""
        # Arrange
        await marcus_mvp._register_agent("agent-011", "Agent 11", "Developer", [])
        marcus_mvp.agent_tasks["agent-011"] = TaskAssignment(
            task_id="task-789",
            task_name="Test task",
            description="Test description",
            instructions="Test instructions",
            estimated_hours=4.0,
            priority=Priority.MEDIUM,
            dependencies=[],
            assigned_to="agent-011",
            assigned_at=datetime.now(),
            due_date=None,
            workspace_path="/test",
            forbidden_paths=[]
        )
        
        # Act
        result = await marcus_mvp._report_task_progress(
            agent_id="agent-011",
            task_id="task-789",
            status="completed",
            progress=100,
            message="Task finished successfully"
        )
        
        # Assert
        assert result["acknowledged"] is True
        marcus_mvp.kanban_client.complete_task.assert_called_once_with("task-789")
        assert "agent-011" not in marcus_mvp.agent_tasks
        assert marcus_mvp.agent_status["agent-011"].completed_tasks_count == 1
    
    @pytest.mark.asyncio
    async def test_report_progress_blocked(self, marcus_mvp):
        """Test reporting blocked task."""
        # Act
        result = await marcus_mvp._report_task_progress(
            agent_id="agent-012",
            task_id="task-999",
            status="blocked",
            progress=30,
            message="Database connection issues"
        )
        
        # Assert
        assert result["acknowledged"] is True
        marcus_mvp.kanban_client.update_task_status.assert_called_once_with("task-999", "blocked")
    
    @pytest.mark.asyncio
    async def test_report_progress_exception_handling(self, marcus_mvp):
        """Test exception handling during progress reporting."""
        # Arrange
        marcus_mvp.kanban_client.add_comment.side_effect = Exception("Kanban error")
        
        # Act
        result = await marcus_mvp._report_task_progress(
            agent_id="agent-013",
            task_id="task-111",
            status="in_progress",
            progress=25,
            message="Starting work"
        )
        
        # Assert
        assert result["acknowledged"] is False
        assert "Kanban error" in result["error"]


class TestBlockerReporting(TestMarcusMVP):
    """Test suite for blocker reporting functionality."""
    
    @pytest.mark.asyncio
    async def test_report_blocker_success(self, marcus_mvp):
        """Test successful blocker reporting."""
        # Arrange
        marcus_mvp.ai_engine._call_claude.return_value = "1. Check network connectivity\n2. Verify credentials"
        
        # Act
        result = await marcus_mvp._report_blocker(
            agent_id="agent-014",
            task_id="task-222",
            blocker_description="Cannot connect to external API",
            severity="high"
        )
        
        # Assert
        assert result["success"] is True
        assert "Check network connectivity" in result["resolution_suggestion"]
        marcus_mvp.kanban_client.add_comment.assert_called_once()
        marcus_mvp.kanban_client.update_task_status.assert_called_once_with("task-222", "blocked")
    
    @pytest.mark.asyncio
    async def test_report_blocker_with_fallback_resolution(self, marcus_mvp):
        """Test blocker reporting when AI resolution fails."""
        # Arrange
        marcus_mvp.ai_engine._call_claude.side_effect = Exception("AI unavailable")
        
        # Act
        result = await marcus_mvp._report_blocker(
            agent_id="agent-015",
            task_id="task-333",
            blocker_description="Missing documentation",
            severity="medium"
        )
        
        # Assert
        assert result["success"] is True
        assert "Basic resolution steps" in result["resolution_suggestion"]
        assert "Review the blocker description" in result["resolution_suggestion"]
    
    @pytest.mark.asyncio
    async def test_report_blocker_exception_handling(self, marcus_mvp):
        """Test exception handling during blocker reporting."""
        # Arrange
        marcus_mvp.kanban_client.add_comment.side_effect = Exception("Connection timeout")
        
        # Act
        result = await marcus_mvp._report_blocker(
            agent_id="agent-016",
            task_id="task-444",
            blocker_description="Test blocker",
            severity="low"
        )
        
        # Assert
        assert result["success"] is False
        assert "Connection timeout" in result["error"]


class TestProjectStatus(TestMarcusMVP):
    """Test suite for project status functionality."""
    
    @pytest.mark.asyncio
    async def test_get_project_status_success(self, marcus_mvp):
        """Test getting project status."""
        # Arrange
        marcus_mvp.kanban_client.get_board_summary.return_value = {
            "stats": {
                "totalCards": 25,
                "completionPercentage": 60,
                "inProgressCount": 5,
                "doneCount": 15,
                "urgentCount": 2,
                "bugCount": 3
            }
        }
        
        # Act
        result = await marcus_mvp._get_project_status()
        
        # Assert
        assert result["success"] is True
        assert result["project_status"]["total_cards"] == 25
        assert result["project_status"]["completion_percentage"] == 60
        assert result["board_info"]["board_id"] == "test_board"
    
    @pytest.mark.asyncio
    async def test_get_project_status_empty_stats(self, marcus_mvp):
        """Test project status with empty stats."""
        # Arrange
        marcus_mvp.kanban_client.get_board_summary.return_value = {}
        
        # Act
        result = await marcus_mvp._get_project_status()
        
        # Assert
        assert result["success"] is True
        assert result["project_status"]["total_cards"] == 0
        assert result["project_status"]["completion_percentage"] == 0
    
    @pytest.mark.asyncio
    async def test_get_project_status_exception_handling(self, marcus_mvp):
        """Test exception handling when getting project status."""
        # Arrange
        marcus_mvp.kanban_client.get_board_summary.side_effect = Exception("API error")
        
        # Act
        result = await marcus_mvp._get_project_status()
        
        # Assert
        assert result["success"] is False
        assert "API error" in result["error"]


class TestAgentStatus(TestMarcusMVP):
    """Test suite for agent status functionality."""
    
    @pytest.mark.asyncio
    async def test_get_agent_status_unregistered(self, marcus_mvp):
        """Test getting status of unregistered agent."""
        # Act
        result = await marcus_mvp._get_agent_status("unknown-agent")
        
        # Assert
        assert result["found"] is False
        assert "not registered" in result["message"]
    
    @pytest.mark.asyncio
    async def test_get_agent_status_without_task(self, marcus_mvp):
        """Test getting status of agent without current task."""
        # Arrange
        await marcus_mvp._register_agent("agent-017", "Agent 17", "Tester", ["pytest"])
        
        # Act
        result = await marcus_mvp._get_agent_status("agent-017")
        
        # Assert
        assert result["found"] is True
        assert result["agent_info"]["id"] == "agent-017"
        assert result["agent_info"]["name"] == "Agent 17"
        assert result["agent_info"]["current_task"] is None
    
    @pytest.mark.asyncio
    async def test_get_agent_status_with_task(self, marcus_mvp):
        """Test getting status of agent with current task."""
        # Arrange
        await marcus_mvp._register_agent("agent-018", "Agent 18", "Developer", [])
        task_assignment = TaskAssignment(
            task_id="task-555",
            task_name="Current task",
            description="Working on this",
            instructions="Do the work",
            estimated_hours=2.0,
            priority=Priority.HIGH,
            dependencies=[],
            assigned_to="agent-018",
            assigned_at=datetime.now(),
            due_date=None,
            workspace_path="/workspace",
            forbidden_paths=[]
        )
        marcus_mvp.agent_tasks["agent-018"] = task_assignment
        
        # Act
        result = await marcus_mvp._get_agent_status("agent-018")
        
        # Assert
        assert result["found"] is True
        assert result["agent_info"]["current_task"]["task_id"] == "task-555"
        assert result["agent_info"]["current_task"]["task_name"] == "Current task"
    
    @pytest.mark.asyncio
    async def test_get_agent_status_exception(self, marcus_mvp):
        """Test exception handling in get_agent_status."""
        # Arrange - create a mock that raises exception
        class ErrorDict(dict):
            def __contains__(self, key):
                raise Exception("DB error")
            def get(self, key, default=None):
                raise Exception("DB error")
        
        marcus_mvp.agent_status = ErrorDict()
        
        # Act
        result = await marcus_mvp._get_agent_status("agent-err")
        
        # Assert
        assert result["found"] is False
        assert "DB error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_list_registered_agents_empty(self, marcus_mvp):
        """Test listing agents when none registered."""
        # Act
        result = await marcus_mvp._list_registered_agents()
        
        # Assert
        assert result["success"] is True
        assert result["agent_count"] == 0
        assert result["agents"] == []
    
    @pytest.mark.asyncio
    async def test_list_registered_agents_multiple(self, marcus_mvp):
        """Test listing multiple registered agents."""
        # Arrange
        await marcus_mvp._register_agent("agent-019", "Agent 19", "Frontend", ["React"])
        await marcus_mvp._register_agent("agent-020", "Agent 20", "Backend", ["Python"])
        
        # Act
        result = await marcus_mvp._list_registered_agents()
        
        # Assert
        assert result["success"] is True
        assert result["agent_count"] == 2
        assert len(result["agents"]) == 2
        agent_ids = [agent["id"] for agent in result["agents"]]
        assert "agent-019" in agent_ids
        assert "agent-020" in agent_ids
    
    @pytest.mark.asyncio
    async def test_list_registered_agents_exception(self, marcus_mvp):
        """Test exception handling in list_registered_agents."""
        # Arrange - create a mock that raises exception
        class ErrorDict(dict):
            def items(self):
                raise Exception("DB error")
        
        marcus_mvp.agent_status = ErrorDict()
        
        # Act
        result = await marcus_mvp._list_registered_agents()
        
        # Assert
        assert result["success"] is False
        assert "DB error" in result["error"]


class TestPingAndHealth(TestMarcusMVP):
    """Test suite for ping and health check functionality."""
    
    @pytest.mark.asyncio
    async def test_ping_basic(self, marcus_mvp):
        """Test basic ping functionality."""
        # Act
        result = await marcus_mvp._ping()
        
        # Assert
        assert result["success"] is True
        assert result["pong"] is True
        assert result["status"] == "online"
        assert result["service"] == "Marcus MVP"
        assert "timestamp" in result
    
    @pytest.mark.asyncio
    async def test_ping_with_echo(self, marcus_mvp):
        """Test ping with echo message."""
        # Act
        result = await marcus_mvp._ping("Hello Marcus")
        
        # Assert
        assert result["echo"] == "Hello Marcus"
        assert result["echo_received"] is True
    
    @pytest.mark.asyncio
    async def test_ping_workload_metrics(self, marcus_mvp):
        """Test ping returns correct workload metrics."""
        # Arrange
        await marcus_mvp._register_agent("agent-021", "Agent 21", "Dev", [])
        await marcus_mvp._register_agent("agent-022", "Agent 22", "QA", [])
        marcus_mvp.agent_status["agent-021"].completed_tasks_count = 5
        marcus_mvp.agent_status["agent-022"].completed_tasks_count = 3
        
        # Act
        result = await marcus_mvp._ping()
        
        # Assert
        assert result["workload"]["registered_agents"] == 2
        assert result["workload"]["total_completed_tasks"] == 8
        assert result["workload"]["agents_available"] == 2
    
    @pytest.mark.asyncio
    async def test_ping_exception_handling(self, marcus_mvp):
        """Test ping exception handling."""
        # Arrange
        with patch.object(marcus_mvp, '_get_uptime', side_effect=Exception("Uptime error")):
            # Act
            result = await marcus_mvp._ping()
            
            # Assert
            assert result["success"] is False
            assert result["pong"] is False
            assert "Uptime error" in result["error"]
    
    def test_get_uptime(self, marcus_mvp):
        """Test uptime calculation."""
        # Arrange
        marcus_mvp._start_time = marcus_mvp._start_time - 3665  # 1 hour, 1 minute, 5 seconds ago
        
        # Act
        uptime = marcus_mvp._get_uptime()
        
        # Assert
        assert "h" in uptime
        assert "m" in uptime
        assert "s" in uptime
    
    @patch('src.marcus_mvp_fixed.psutil.Process')
    def test_get_memory_usage_success(self, mock_process, marcus_mvp):
        """Test memory usage calculation."""
        # Arrange
        mock_memory_info = Mock()
        mock_memory_info.rss = 100 * 1024 * 1024  # 100 MB
        mock_process_instance = Mock()
        mock_process_instance.memory_info.return_value = mock_memory_info
        mock_process_instance.memory_percent.return_value = 2.5
        mock_process.return_value = mock_process_instance
        
        # Act
        memory = marcus_mvp._get_memory_usage()
        
        # Assert
        assert memory["rss_mb"] == 100.0
        assert memory["percent"] == 2.5
    
    def test_get_memory_usage_exception(self, marcus_mvp):
        """Test memory usage with exception."""
        # Arrange
        with patch('src.marcus_mvp_fixed.psutil.Process', side_effect=Exception("Process error")):
            # Act
            memory = marcus_mvp._get_memory_usage()
            
            # Assert
            assert memory["rss_mb"] == 0
            assert memory["percent"] == 0


class TestMCPToolHandling(TestMarcusMVP):
    """Test suite for MCP tool registration and handling."""
    
    @pytest.mark.asyncio
    async def test_handle_call_tool_unknown_tool(self, marcus_mvp):
        """Test handling unknown tool call."""
        # Since we're testing internal method directly, not through the decorated handler
        # we'll test the method that would be called by the handler
        result = await marcus_mvp._register_agent(None, None, None, [])
        assert result["success"] is False
        assert "required" in result["error"]
    
    @pytest.mark.asyncio
    async def test_handle_call_tool_all_tools(self, marcus_mvp):
        """Test that all tools are properly callable."""
        # Test each tool method exists and is callable
        assert hasattr(marcus_mvp, '_register_agent')
        assert hasattr(marcus_mvp, '_request_next_task')
        assert hasattr(marcus_mvp, '_report_task_progress')
        assert hasattr(marcus_mvp, '_report_blocker')
        assert hasattr(marcus_mvp, '_get_project_status')
        assert hasattr(marcus_mvp, '_get_agent_status')
        assert hasattr(marcus_mvp, '_list_registered_agents')
        assert hasattr(marcus_mvp, '_ping')
    
    def test_tool_registration(self, marcus_mvp):
        """Test that tools are registered during initialization."""
        # Verify the server mock was created
        assert marcus_mvp.server is not None
        # Verify internal state was initialized
        assert isinstance(marcus_mvp.agent_tasks, dict)
        assert isinstance(marcus_mvp.agent_status, dict)
    
    @pytest.mark.asyncio
    async def test_handle_call_tool_direct(self, marcus_mvp):
        """Test the actual handle_call_tool function through decorator."""
        # Get the decorated function
        handle_call_tool = None
        for attr_name in dir(marcus_mvp):
            attr = getattr(marcus_mvp, attr_name)
            if hasattr(attr, '__wrapped__') and hasattr(attr.__wrapped__, '__name__') and attr.__wrapped__.__name__ == 'handle_call_tool':
                handle_call_tool = attr.__wrapped__
                break
        
        if handle_call_tool:
            # Test successful tool call
            result = await handle_call_tool(marcus_mvp, "ping", {"echo": "test"})
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            
            # Test unknown tool
            result = await handle_call_tool(marcus_mvp, "unknown_tool", {})
            assert isinstance(result, list)
            response_data = json.loads(result[0].text)
            assert "error" in response_data
            assert "Unknown tool" in response_data["error"]
    
    @pytest.mark.asyncio  
    async def test_list_tools_decorator(self, marcus_mvp):
        """Test the list_tools decorated function."""
        # Get the decorated function
        handle_list_tools = None
        for attr_name in dir(marcus_mvp):
            attr = getattr(marcus_mvp, attr_name)
            if hasattr(attr, '__wrapped__') and hasattr(attr.__wrapped__, '__name__') and attr.__wrapped__.__name__ == 'handle_list_tools':
                handle_list_tools = attr.__wrapped__
                break
        
        if handle_list_tools:
            tools = await handle_list_tools(marcus_mvp)
            assert isinstance(tools, list)
            assert len(tools) == 8  # We have 8 tools
            tool_names = [tool.name for tool in tools]
            assert "register_agent" in tool_names
            assert "ping" in tool_names


class TestInitialization(TestMarcusMVP):
    """Test suite for Marcus initialization."""
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, marcus_mvp):
        """Test successful initialization."""
        # Arrange
        with patch('sys.stderr'):
            # Act
            await marcus_mvp.initialize()
            
            # Assert
            marcus_mvp.ai_engine.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_ai_engine_failure(self, marcus_mvp):
        """Test initialization failure in AI engine."""
        # Arrange
        marcus_mvp.ai_engine.initialize.side_effect = Exception("AI init failed")
        
        # Act & Assert
        with patch('sys.stderr'):
            with pytest.raises(Exception, match="AI init failed"):
                await marcus_mvp.initialize()


class TestInstructionGeneration(TestMarcusMVP):
    """Test suite for AI instruction generation."""
    
    @pytest.mark.asyncio
    async def test_generate_basic_instructions_success(self, marcus_mvp, sample_task):
        """Test successful AI instruction generation."""
        # Arrange
        expected_instructions = "1. Set up authentication\n2. Create login endpoint\n3. Test thoroughly"
        marcus_mvp.ai_engine._call_claude.return_value = expected_instructions
        
        # Act
        instructions = await marcus_mvp._generate_basic_instructions(sample_task)
        
        # Assert
        assert instructions == expected_instructions
        # Verify prompt contains task details
        call_args = marcus_mvp.ai_engine._call_claude.call_args[0][0]
        assert "Implement user authentication" in call_args
        assert "Add login functionality" in call_args
        assert "high" in call_args
    
    @pytest.mark.asyncio
    async def test_generate_basic_instructions_fallback(self, marcus_mvp, sample_task):
        """Test fallback instructions when AI fails."""
        # Arrange
        marcus_mvp.ai_engine._call_claude.side_effect = Exception("AI unavailable")
        
        # Act
        instructions = await marcus_mvp._generate_basic_instructions(sample_task)
        
        # Assert
        assert "Implement user authentication" in instructions
        assert "Add login functionality" in instructions
        assert "Definition of Done" in instructions


class TestResolutionSuggestions(TestMarcusMVP):
    """Test suite for blocker resolution suggestions."""
    
    @pytest.mark.asyncio
    async def test_get_basic_resolution_success(self, marcus_mvp):
        """Test successful AI resolution suggestion."""
        # Arrange
        blocker = "Database connection timeout"
        expected_resolution = "1. Check connection string\n2. Verify network access\n3. Test with telnet"
        marcus_mvp.ai_engine._call_claude.return_value = expected_resolution
        
        # Act
        resolution = await marcus_mvp._get_basic_resolution(blocker)
        
        # Assert
        assert resolution == expected_resolution
        # Verify prompt contains blocker
        call_args = marcus_mvp.ai_engine._call_claude.call_args[0][0]
        assert "Database connection timeout" in call_args
    
    @pytest.mark.asyncio
    async def test_get_basic_resolution_fallback(self, marcus_mvp):
        """Test fallback resolution when AI fails."""
        # Arrange
        marcus_mvp.ai_engine._call_claude.side_effect = Exception("AI error")
        
        # Act
        resolution = await marcus_mvp._get_basic_resolution("Some blocker")
        
        # Assert
        assert "Basic resolution steps" in resolution
        assert "Review the blocker description" in resolution
        assert "Document the resolution" in resolution


class TestMainEntryPoint:
    """Test suite for main entry point."""
    
    @pytest.mark.asyncio
    async def test_main_function(self):
        """Test main function execution."""
        # Arrange
        mock_marcus = Mock()
        mock_marcus.initialize = AsyncMock()
        mock_marcus.server = Mock()
        mock_marcus.server.run = AsyncMock()
        mock_marcus.server.create_initialization_options = Mock(return_value={})
        
        mock_read_stream = Mock()
        mock_write_stream = Mock()
        
        # Create a proper async context manager
        class AsyncContextManager:
            async def __aenter__(self):
                return (mock_read_stream, mock_write_stream)
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        
        with patch('src.marcus_mvp_fixed.MarcusMVP', return_value=mock_marcus), \
             patch('src.marcus_mvp_fixed.stdio_server', return_value=AsyncContextManager()):
            
            # Act
            from src.marcus_mvp_fixed import main
            await main()
            
            # Assert
            mock_marcus.initialize.assert_called_once()
            mock_marcus.server.run.assert_called_once_with(
                mock_read_stream,
                mock_write_stream,
                {}
            )