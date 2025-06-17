"""
Unit tests for SimpleMCPKanbanClient
Tests internal methods and edge cases without requiring MCP connection
"""

import pytest
import json
import os
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.integrations.mcp_kanban_client_simple import SimpleMCPKanbanClient
from src.core.models import Task, TaskStatus, Priority


class TestSimpleClientUnit:
    """Unit tests for SimpleMCPKanbanClient internal methods"""
    
    def test_config_loading_with_file(self, tmp_path):
        """Test configuration loading from file"""
        # Create a temporary config file
        config_data = {
            "project_id": "test-project-123",
            "board_id": "test-board-456"
        }
        
        config_file = tmp_path / "config_pm_agent.json"
        config_file.write_text(json.dumps(config_data))
        
        # Change to tmp directory and create client
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            client = SimpleMCPKanbanClient()
            
            assert client.project_id == "test-project-123"
            assert client.board_id == "test-board-456"
        finally:
            os.chdir(original_cwd)
    
    def test_config_loading_without_file(self, tmp_path):
        """Test configuration loading when file doesn't exist"""
        # Change to empty directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            client = SimpleMCPKanbanClient()
            
            # Should have None values when no config file
            assert client.project_id is None
            assert client.board_id is None
        finally:
            os.chdir(original_cwd)
    
    def test_card_to_task_complete_data(self):
        """Test _card_to_task with complete card data"""
        client = SimpleMCPKanbanClient()
        
        card = {
            "id": "card-123",
            "name": "Test Task",
            "description": "Test description with details",
            "listName": "TODO",
            "labels": ["bug", "urgent"],
            "dueDate": "2024-12-31T23:59:59Z",
            "members": [{"id": "user-1", "name": "John Doe"}]
        }
        
        task = client._card_to_task(card)
        
        assert task.id == "card-123"
        assert task.name == "Test Task"
        assert task.description == "Test description with details"
        assert task.status == TaskStatus.TODO
        assert task.priority == Priority.MEDIUM
        assert task.assigned_to is None
        assert isinstance(task.created_at, datetime)
        assert isinstance(task.updated_at, datetime)
        assert task.due_date is None  # SimpleMCPKanbanClient doesn't parse due dates
        assert task.estimated_hours == 0.0
        assert task.actual_hours == 0.0
        assert task.dependencies == []
        assert task.labels == []
    
    def test_card_to_task_minimal_data(self):
        """Test _card_to_task with minimal card data"""
        client = SimpleMCPKanbanClient()
        
        card = {
            "id": "card-456",
            "listName": "In Progress"
        }
        
        task = client._card_to_task(card)
        
        assert task.id == "card-456"
        assert task.name == ""  # Should handle missing name
        assert task.description == ""
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.priority == Priority.MEDIUM
    
    def test_card_to_task_title_fallback(self):
        """Test _card_to_task uses title when name is missing"""
        client = SimpleMCPKanbanClient()
        
        card = {
            "id": "card-789",
            "title": "Task Title",  # Some APIs use 'title' instead of 'name'
            "listName": "Done"
        }
        
        task = client._card_to_task(card)
        
        assert task.name == "Task Title"
        assert task.status == TaskStatus.DONE
    
    def test_is_available_task_various_states(self):
        """Test _is_available_task with various list names"""
        client = SimpleMCPKanbanClient()
        
        # Test available states
        available_states = [
            "TODO",
            "To Do",
            "TO DO",
            "todo",
            "Backlog",
            "BACKLOG",
            "Ready",
            "Ready for Development",
            "TODO - High Priority"
        ]
        
        for state in available_states:
            card = {"listName": state}
            assert client._is_available_task(card), f"'{state}' should be available"
        
        # Test unavailable states
        unavailable_states = [
            "In Progress",
            "IN PROGRESS",
            "Done",
            "DONE",
            "Completed",
            "Blocked",
            "On Hold",
            "Review",
            "Testing"
        ]
        
        for state in unavailable_states:
            card = {"listName": state}
            assert not client._is_available_task(card), f"'{state}' should not be available"
    
    def test_status_mapping_edge_cases(self):
        """Test status mapping with edge case list names"""
        client = SimpleMCPKanbanClient()
        
        edge_cases = [
            ("Work In Progress", TaskStatus.IN_PROGRESS),
            ("DONE - Archived", TaskStatus.DONE),
            ("Blocked by External", TaskStatus.BLOCKED),
            ("Development TODO", TaskStatus.TODO),
            ("Random List Name", TaskStatus.TODO),  # Default to TODO
            ("", TaskStatus.TODO),  # Empty list name
            ("In-Progress", TaskStatus.IN_PROGRESS),  # Hyphenated
            ("inprogress", TaskStatus.IN_PROGRESS),  # No space
            ("done!", TaskStatus.DONE),  # With punctuation
        ]
        
        for list_name, expected_status in edge_cases:
            card = {"id": "test", "listName": list_name}
            task = client._card_to_task(card)
            assert task.status == expected_status, f"List '{list_name}' should map to {expected_status}"
    
    @pytest.mark.asyncio
    async def test_get_available_tasks_error_handling(self):
        """Test get_available_tasks error scenarios"""
        client = SimpleMCPKanbanClient()
        
        # Test with no board_id
        client.board_id = None
        with pytest.raises(RuntimeError, match="Board ID not set"):
            await client.get_available_tasks()
        
        # Test with empty board_id
        client.board_id = ""
        with pytest.raises(RuntimeError, match="Board ID not set"):
            await client.get_available_tasks()
    
    @pytest.mark.asyncio
    async def test_get_board_summary_error_handling(self):
        """Test get_board_summary error scenarios"""
        client = SimpleMCPKanbanClient()
        
        # Test with no board_id
        client.board_id = None
        with pytest.raises(RuntimeError, match="Board ID not set"):
            await client.get_board_summary()
    
    def test_environment_variables_set(self):
        """Test that environment variables are properly set"""
        client = SimpleMCPKanbanClient()
        
        assert os.environ.get('PLANKA_BASE_URL') == 'http://localhost:3333'
        assert os.environ.get('PLANKA_AGENT_EMAIL') == 'demo@demo.demo'
        assert os.environ.get('PLANKA_AGENT_PASSWORD') == 'demo'
    
    @patch('src.integrations.mcp_kanban_client_simple.stdio_client')
    @pytest.mark.asyncio
    async def test_assign_task_moves_to_progress(self, mock_stdio_client):
        """Test that assign_task moves card to In Progress list"""
        client = SimpleMCPKanbanClient()
        client.board_id = "test-board"
        
        # Mock the MCP session
        mock_session = AsyncMock()
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        
        # Mock stdio_client context manager
        mock_stdio_client.return_value.__aenter__.return_value = (mock_read, mock_write)
        
        # Mock ClientSession
        with patch('src.integrations.mcp_kanban_client_simple.ClientSession') as mock_client_session:
            mock_client_session.return_value.__aenter__.return_value = mock_session
            
            # Mock list manager response
            lists_response = MagicMock()
            lists_response.content = [MagicMock(text=json.dumps([
                {"id": "list-1", "name": "TODO"},
                {"id": "list-2", "name": "In Progress"},
                {"id": "list-3", "name": "Done"}
            ]))]
            
            # Setup mock responses
            mock_session.call_tool.side_effect = [
                MagicMock(),  # Comment creation
                lists_response,  # Get lists
                MagicMock()  # Move card
            ]
            
            # Call assign_task
            await client.assign_task("task-123", "agent-001")
            
            # Verify calls were made
            assert mock_session.call_tool.call_count == 3
            
            # Verify comment was added
            comment_call = mock_session.call_tool.call_args_list[0]
            assert comment_call[0][0] == "mcp_kanban_comment_manager"
            assert "agent-001" in comment_call[0][1]["text"]
            
            # Verify card was moved to In Progress
            move_call = mock_session.call_tool.call_args_list[2]
            assert move_call[0][0] == "mcp_kanban_card_manager"
            assert move_call[0][1]["action"] == "move"
            assert move_call[0][1]["listId"] == "list-2"  # In Progress list
    
    def test_task_object_completeness(self):
        """Test that Task objects have all required fields"""
        client = SimpleMCPKanbanClient()
        
        card = {
            "id": "test-123",
            "name": "Complete Task",
            "description": "Full description",
            "listName": "TODO"
        }
        
        task = client._card_to_task(card)
        
        # Check all Task model fields are present
        required_fields = [
            'id', 'name', 'description', 'status', 'priority',
            'assigned_to', 'created_at', 'updated_at', 'due_date',
            'estimated_hours', 'actual_hours', 'dependencies', 'labels'
        ]
        
        for field in required_fields:
            assert hasattr(task, field), f"Task should have field '{field}'"
    
    def test_card_with_special_characters(self):
        """Test handling cards with special characters"""
        client = SimpleMCPKanbanClient()
        
        card = {
            "id": "test-special",
            "name": "Task with émojis 🚀 and special chars!@#$%",
            "description": "Description with\nnewlines\tand\ttabs",
            "listName": "TODO"
        }
        
        task = client._card_to_task(card)
        
        assert task.name == "Task with émojis 🚀 and special chars!@#$%"
        assert task.description == "Description with\nnewlines\tand\ttabs"
        assert task.status == TaskStatus.TODO


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])