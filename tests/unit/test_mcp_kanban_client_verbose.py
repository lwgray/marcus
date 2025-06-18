"""
Unit tests for Verbose MCP Kanban Client
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from io import StringIO

from src.integrations.mcp_kanban_client_verbose import VerboseMCPKanbanClient


class TestVerboseMCPKanbanClient:
    """Test cases for VerboseMCPKanbanClient"""
    
    @pytest.fixture
    def client(self):
        """Create a VerboseMCPKanbanClient instance"""
        return VerboseMCPKanbanClient()
        
    @pytest.fixture
    @patch('src.integrations.mcp_kanban_client_verbose.console')
    def mock_console(self, mock):
        """Mock the console for output capture"""
        return mock
        
    def test_initialization(self, client):
        """Test client initialization"""
        assert client.conversation_log == []
        assert hasattr(client, '_log_kanban_request')
        assert hasattr(client, '_log_kanban_response')
        assert hasattr(client, '_log_kanban_thinking')
        
    @pytest.mark.asyncio
    @patch('src.integrations.mcp_kanban_client_verbose.super')
    async def test_initialize_with_logging(self, mock_super, client, mock_console):
        """Test initialize method with verbose logging"""
        # Setup mock
        mock_super_instance = AsyncMock()
        mock_super_instance.initialize.return_value = True
        mock_super.return_value = mock_super_instance
        
        # Call initialize
        result = await client.initialize()
        
        # Verify logging
        assert result is True
        # Check that console.print was called for logging
        assert mock_console.print.called
        
    @pytest.mark.asyncio
    @patch('src.integrations.mcp_kanban_client_verbose.super')
    async def test_get_available_tasks_with_logging(self, mock_super, client, mock_console):
        """Test get_available_tasks with verbose logging"""
        # Setup mock tasks
        mock_tasks = [
            {
                "id": "task-1",
                "name": "Test Task 1",
                "status": "Backlog",
                "priority": "High",
                "assigned_to": None,
                "estimated_hours": 4,
                "labels": ["backend"]
            },
            {
                "id": "task-2",
                "name": "Test Task 2",
                "status": "Ready",
                "priority": "Medium",
                "assigned_to": None,
                "estimated_hours": 2,
                "labels": ["frontend"]
            }
        ]
        
        # Mock the parent method
        mock_super_instance = AsyncMock()
        mock_super_instance.get_available_tasks.return_value = mock_tasks
        mock_super.return_value = mock_super_instance
        
        # Call method
        result = await client.get_available_tasks()
        
        # Verify
        assert result == mock_tasks
        assert mock_console.print.called
        
    @pytest.mark.asyncio
    @patch('src.integrations.mcp_kanban_client_verbose.super')
    async def test_assign_task_with_logging(self, mock_super, client, mock_console):
        """Test assign_task with verbose logging"""
        # Setup mock
        mock_super_instance = AsyncMock()
        mock_super_instance.assign_task.return_value = True
        mock_super.return_value = mock_super_instance
        
        # Call method
        result = await client.assign_task("task-1", "agent-1")
        
        # Verify
        assert result is True
        assert mock_console.print.called
        # Verify success message was logged
        call_args = [str(call) for call in mock_console.print.call_args_list]
        assert any("successfully" in str(arg).lower() for arg in call_args)
        
    @pytest.mark.asyncio
    @patch('src.integrations.mcp_kanban_client_verbose.super')
    async def test_update_task_progress_with_logging(self, mock_super, client, mock_console):
        """Test update_task_progress with verbose logging"""
        # Setup mock
        mock_super_instance = AsyncMock()
        mock_super_instance.update_task_progress.return_value = True
        mock_super.return_value = mock_super_instance
        
        # Progress data
        progress_data = {
            "progress": 50,
            "status": "in_progress",
            "message": "Halfway done"
        }
        
        # Call method
        result = await client.update_task_progress("task-1", progress_data)
        
        # Verify
        assert result is True
        assert mock_console.print.called
        
    @pytest.mark.asyncio
    @patch('src.integrations.mcp_kanban_client_verbose.super')
    async def test_report_blocker_with_logging(self, mock_super, client, mock_console):
        """Test report_blocker with verbose logging"""
        # Setup mock
        mock_super_instance = AsyncMock()
        mock_super_instance.report_blocker.return_value = True
        mock_super.return_value = mock_super_instance
        
        # Call method
        result = await client.report_blocker(
            "task-1",
            "Missing dependencies",
            "high"
        )
        
        # Verify
        assert result is True
        assert mock_console.print.called
        
    @pytest.mark.asyncio
    async def test_get_project_metrics(self, client, mock_console):
        """Test get_project_metrics with logging"""
        # Call method
        result = await client.get_project_metrics()
        
        # Verify metrics structure
        assert isinstance(result, dict)
        assert "total_tasks" in result
        assert "completed" in result
        assert "velocity" in result
        
        # Verify table was displayed
        assert mock_console.print.called
        
    def test_log_kanban_request(self, client, mock_console):
        """Test _log_kanban_request method"""
        # Call with params
        client._log_kanban_request("Test Action", {"param1": "value1", "param2": "value2"})
        
        # Verify console output
        assert mock_console.print.called
        call_args = [str(call) for call in mock_console.print.call_args_list]
        assert any("Test Action" in str(arg) for arg in call_args)
        assert any("param1" in str(arg) for arg in call_args)
        
    def test_log_kanban_response_list(self, client, mock_console):
        """Test _log_kanban_response with list response"""
        # Response list
        response = [
            {"name": "Task 1"},
            {"name": "Task 2"},
            {"name": "Task 3"},
            {"name": "Task 4"}
        ]
        
        # Call method
        client._log_kanban_response("Get Tasks", response)
        
        # Verify
        assert mock_console.print.called
        call_args = [str(call) for call in mock_console.print.call_args_list]
        assert any("4" in str(arg) for arg in call_args)  # Items count
        assert any("Task 1" in str(arg) for arg in call_args)
        
    def test_log_kanban_response_dict(self, client, mock_console):
        """Test _log_kanban_response with dict response"""
        # Response dict
        response = {
            "success": True,
            "task_id": "task-123",
            "status": "completed"
        }
        
        # Call method
        client._log_kanban_response("Update Task", response)
        
        # Verify
        assert mock_console.print.called
        call_args = [str(call) for call in mock_console.print.call_args_list]
        assert any("success" in str(arg) for arg in call_args)
        assert any("task_id" in str(arg) for arg in call_args)
        
    def test_log_kanban_thinking(self, client, mock_console):
        """Test _log_kanban_thinking method"""
        # Call method
        client._log_kanban_thinking("Processing task assignment logic")
        
        # Verify
        assert mock_console.print.called
        call_args = [str(call) for call in mock_console.print.call_args_list]
        assert any("Processing task assignment logic" in str(arg) for arg in call_args)
        
    def test_show_board_state(self, client, mock_console):
        """Test _show_board_state method"""
        # Test tasks
        tasks = [
            {"name": "Task 1", "status": "Backlog", "priority": "High", "assigned_to": None},
            {"name": "Task 2", "status": "In Progress", "priority": "Medium", "assigned_to": "agent-1"},
            {"name": "Task 3", "status": "Done", "priority": "Low", "assigned_to": "agent-2"}
        ]
        
        # Call method
        client._show_board_state(tasks)
        
        # Verify table was created
        assert mock_console.print.called
        
    @pytest.mark.asyncio
    async def test_create_task_from_command(self, client, mock_console):
        """Test create_task_from_command method"""
        # Test tasks
        tasks = [
            {
                "title": "New Task 1",
                "description": "Description 1",
                "priority": "High",
                "agent_type": "backend",
                "estimated_hours": 4
            }
        ]
        
        # Call method
        result = await client.create_task_from_command("issue-123", tasks)
        
        # Verify
        assert result is True
        assert mock_console.print.called