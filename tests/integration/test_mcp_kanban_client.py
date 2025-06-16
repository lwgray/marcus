"""
Integration tests for the refactored MCPKanbanClient
"""

import pytest
import asyncio
from datetime import datetime

from integrations.mcp_kanban_client_refactored import MCPKanbanClient
from core.models import TaskStatus, Priority


@pytest.mark.integration
@pytest.mark.kanban
class TestMCPKanbanClientIntegration:
    """Integration tests for MCPKanbanClient"""
    
    @pytest.fixture
    async def kanban_client(self, test_project_id):
        """Provide a configured kanban client"""
        client = MCPKanbanClient()
        client.project_id = test_project_id
        # Let it find the board automatically
        return client
    
    @pytest.mark.asyncio
    async def test_connection_context_manager(self, kanban_client):
        """Test that the connection context manager works properly"""
        async with kanban_client.connect() as conn:
            assert conn is not None
            assert conn.session is not None
            
            # Test that we can make a call
            result = await conn.call_tool("mcp_kanban_project_board_manager", {
                "action": "get_project",
                "projectId": kanban_client.project_id
            })
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_auto_find_project_and_board(self):
        """Test automatic project and board discovery"""
        client = MCPKanbanClient()
        
        # Should find Task Master Test project automatically
        async with client.connect() as conn:
            assert client.project_id is not None
            assert "Task Master Test" in client.project_id or client.project_id == "1533678301472621705"
            
            # Should also find a board
            assert client.board_id is not None
    
    @pytest.mark.asyncio
    async def test_get_available_tasks(self, kanban_client, test_board):
        """Test getting available tasks"""
        kanban_client.board_id = test_board["id"]
        
        # Create a test task first
        async with kanban_client.connect() as conn:
            # Get TODO list
            lists_result = await conn.call_tool("mcp_kanban_list_manager", {
                "action": "get_all",
                "boardId": test_board["id"]
            })
            
            import json
            lists = json.loads(lists_result.content[0].text)
            todo_list = next((l for l in lists if "To Do" in l["name"]), None)
            
            if todo_list:
                # Create a task
                await conn.call_tool("mcp_kanban_card_manager", {
                    "action": "create",
                    "listId": todo_list["id"],
                    "name": "Test Available Task",
                    "description": "Should appear in available tasks"
                })
        
        # Now test getting available tasks
        tasks = await kanban_client.get_available_tasks()
        assert isinstance(tasks, list)
        assert any(task.name == "Test Available Task" for task in tasks)
    
    @pytest.mark.asyncio
    async def test_create_task(self, kanban_client, test_board):
        """Test creating a task"""
        kanban_client.board_id = test_board["id"]
        
        task_data = {
            "name": "Integration Test Task",
            "description": "Created by integration test",
            "labels": ["test", "automated"]
        }
        
        task = await kanban_client.create_task(task_data)
        
        assert task is not None
        assert task.name == "Integration Test Task"
        assert task.description == "Created by integration test"
        assert task.status == TaskStatus.TODO
    
    @pytest.mark.asyncio
    async def test_task_lifecycle(self, kanban_client, test_board):
        """Test complete task lifecycle: create, assign, update, complete"""
        kanban_client.board_id = test_board["id"]
        
        # 1. Create task
        task = await kanban_client.create_task({
            "name": "Lifecycle Test Task",
            "description": "Testing full lifecycle"
        })
        assert task is not None
        task_id = task.id
        
        # 2. Assign task
        await kanban_client.assign_task(task_id, "test_agent")
        
        # 3. Add comment
        await kanban_client.add_comment(task_id, "Starting work on this task")
        
        # 4. Update progress
        await kanban_client.update_task_progress(task_id, 25)
        await kanban_client.update_task_progress(task_id, 50)
        await kanban_client.update_task_progress(task_id, 75)
        
        # 5. Complete task
        await kanban_client.complete_task(task_id)
        
        # 6. Verify task details
        final_task = await kanban_client.get_task_details(task_id)
        assert final_task is not None
        assert final_task.status == TaskStatus.DONE
    
    @pytest.mark.asyncio
    async def test_update_task_status(self, kanban_client, test_board):
        """Test updating task status"""
        kanban_client.board_id = test_board["id"]
        
        # Create a task
        task = await kanban_client.create_task({
            "name": "Status Update Test",
            "description": "Testing status updates"
        })
        
        # Test different status updates
        statuses = ["in_progress", "blocked", "ready", "done"]
        
        for status in statuses:
            await kanban_client.update_task_status(task.id, status)
            # Small delay to ensure update processes
            await asyncio.sleep(0.5)
    
    @pytest.mark.asyncio
    async def test_board_summary(self, kanban_client, test_board):
        """Test getting board summary"""
        kanban_client.board_id = test_board["id"]
        
        # Create some tasks first
        for i in range(3):
            await kanban_client.create_task({
                "name": f"Summary Test Task {i+1}",
                "description": "For board summary test"
            })
        
        # Get summary
        summary = await kanban_client.get_board_summary()
        
        assert isinstance(summary, dict)
        assert "stats" in summary
        assert summary["stats"]["totalCards"] >= 3
    
    @pytest.mark.asyncio
    async def test_error_handling(self, kanban_client):
        """Test error handling for invalid operations"""
        # Test with no board ID set
        kanban_client.board_id = None
        
        with pytest.raises(RuntimeError, match="Board ID not set"):
            await kanban_client.get_available_tasks()
        
        with pytest.raises(RuntimeError, match="Board ID not set"):
            await kanban_client.create_task({"name": "Test"})
        
        # Test with invalid task ID
        kanban_client.board_id = "some_board_id"
        with pytest.raises(Exception):
            await kanban_client.get_task_details("invalid_task_id")