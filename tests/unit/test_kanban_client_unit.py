"""
Unit tests for MCPKanbanClient - tests that don't require external services
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from integrations.mcp_kanban_client_refactored import MCPKanbanClient, MCPConnection
from core.models import Task, TaskStatus, Priority


@pytest.mark.unit
class TestMCPKanbanClientUnit:
    """Unit tests for MCPKanbanClient"""
    
    @pytest.fixture
    def client(self):
        """Provide a basic client instance"""
        return MCPKanbanClient()
    
    def test_initialization(self, client):
        """Test client initialization"""
        assert client.board_id is None
        assert client.project_id is None
        assert client._node_path is None
        assert client._kanban_mcp_path == "/Users/lwgray/dev/kanban-mcp/dist/index.js"
        assert client._env["PLANKA_BASE_URL"] == "http://localhost:3333"
    
    def test_find_node_executable(self, client):
        """Test node executable finder"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "v18.0.0"
            
            with patch('os.path.isfile', return_value=True):
                with patch('os.access', return_value=True):
                    node_path = client._find_node_executable()
                    assert node_path is not None
    
    def test_is_available_task(self, client):
        """Test task availability checker"""
        # Available tasks
        assert client._is_available_task({"listName": "TODO"})
        assert client._is_available_task({"listName": "To Do"})
        assert client._is_available_task({"listName": "BACKLOG"})
        assert client._is_available_task({"listName": "Ready"})
        
        # Not available
        assert not client._is_available_task({"listName": "In Progress"})
        assert not client._is_available_task({"listName": "Done"})
        assert not client._is_available_task({"listName": "On Hold"})
    
    def test_map_status_from_list(self, client):
        """Test status mapping from list names"""
        assert client._map_status_from_list({"listName": "TODO"}) == TaskStatus.TODO
        assert client._map_status_from_list({"listName": "To Do"}) == TaskStatus.TODO
        assert client._map_status_from_list({"listName": "In Progress"}) == TaskStatus.IN_PROGRESS
        assert client._map_status_from_list({"listName": "On Hold"}) == TaskStatus.BLOCKED
        assert client._map_status_from_list({"listName": "Done"}) == TaskStatus.DONE
        assert client._map_status_from_list({"listName": "Unknown"}) == TaskStatus.TODO
    
    def test_extract_priority_from_labels(self, client):
        """Test priority extraction from labels"""
        # Critical/Urgent
        assert client._extract_priority_from_labels({
            "labels": [{"name": "CRITICAL"}]
        }) == Priority.URGENT
        assert client._extract_priority_from_labels({
            "labels": [{"name": "P0"}]
        }) == Priority.URGENT
        
        # High
        assert client._extract_priority_from_labels({
            "labels": [{"name": "High Priority"}]
        }) == Priority.HIGH
        assert client._extract_priority_from_labels({
            "labels": [{"name": "P1"}]
        }) == Priority.HIGH
        
        # Medium (default)
        assert client._extract_priority_from_labels({
            "labels": []
        }) == Priority.MEDIUM
        
        # Low
        assert client._extract_priority_from_labels({
            "labels": [{"name": "Low"}]
        }) == Priority.LOW
    
    def test_extract_labels(self, client):
        """Test label extraction"""
        labels = client._extract_labels({
            "labels": [
                {"name": "bug"},
                {"name": "enhancement"},
                {"name": ""}  # Empty should be filtered
            ]
        })
        
        assert labels == ["bug", "enhancement"]
        assert "" not in labels
    
    def test_card_to_task_conversion(self, client):
        """Test card to task conversion"""
        card = {
            "id": "123",
            "name": "Test Card",
            "description": "Test Description",
            "listName": "To Do",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-02T00:00:00Z",
            "dueDate": "2024-01-10T00:00:00Z",
            "labels": [{"name": "High"}]
        }
        
        task = client._card_to_task(card)
        
        assert isinstance(task, Task)
        assert task.id == "123"
        assert task.name == "Test Card"
        assert task.description == "Test Description"
        assert task.status == TaskStatus.TODO
        assert task.priority == Priority.HIGH
        assert isinstance(task.created_at, datetime)
        assert isinstance(task.updated_at, datetime)
        assert isinstance(task.due_date, datetime)
    
    def test_card_to_task_with_minimal_data(self, client):
        """Test card to task conversion with minimal data"""
        card = {
            "id": "456",
            "title": "Minimal Card"  # Using title instead of name
        }
        
        task = client._card_to_task(card)
        
        assert task.id == "456"
        assert task.name == "Minimal Card"
        assert task.description == ""
        assert task.status == TaskStatus.TODO
        assert task.priority == Priority.MEDIUM
        assert task.labels == []
    
    @pytest.mark.asyncio
    async def test_mcp_connection_context_manager(self):
        """Test MCPConnection context manager"""
        with patch('mcp.client.stdio.stdio_client') as mock_stdio:
            mock_transport = AsyncMock()
            mock_transport.__aenter__.return_value = (Mock(), Mock())
            mock_transport.__aexit__.return_value = None
            mock_stdio.return_value = mock_transport
            
            with patch('mcp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value = mock_session
                
                conn = MCPConnection("node", ["test.js"], {})
                
                async with conn as active_conn:
                    assert active_conn.session is not None
                    mock_session.initialize.assert_called_once()
                
                # After exit, session should be None
                assert conn.session is None
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test connection error handling"""
        conn = MCPConnection("node", ["test.js"], {})
        
        # Test calling tool without active connection
        with pytest.raises(RuntimeError, match="Connection not active"):
            await conn.call_tool("test_tool", {})