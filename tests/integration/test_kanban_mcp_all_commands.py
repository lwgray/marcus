"""
Comprehensive test suite for all Kanban MCP commands
Tests all 8 tool endpoints and their various actions
"""

import asyncio
import pytest
import json
from datetime import datetime
from typing import Dict, Any, Optional
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.integrations.mcp_kanban_client_refactored import MCPKanbanClient
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class TestKanbanMCPCommands:
    """Test all Kanban MCP commands comprehensively"""
    
    @classmethod
    def setup_class(cls):
        """Set up test data"""
        cls.test_project_id = "1533678301472621705"  # Task Master Test
        cls.test_board_id = None
        cls.test_card_id = None
        cls.test_list_id = None
        cls.test_label_id = None
        cls.test_task_id = None
        cls.test_comment_id = None
        cls.created_resources = {
            "boards": [],
            "cards": [],
            "tasks": [],
            "comments": [],
            "labels": []
        }
    
    @pytest.fixture
    async def mcp_connection(self):
        """Create MCP connection for testing"""
        server_params = StdioServerParameters(
            command="/opt/homebrew/bin/node",
            args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
            env={
                "PLANKA_BASE_URL": "http://localhost:3333",
                "PLANKA_AGENT_EMAIL": "demo@demo.demo",
                "PLANKA_AGENT_PASSWORD": "demo"
            }
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    
    async def _call_tool(self, session, tool_name: str, args: Dict[str, Any]) -> Any:
        """Helper to call tool and parse response"""
        result = await session.call_tool(tool_name, args)
        if hasattr(result, 'content') and result.content:
            text = result.content[0].text
            if text and not text.startswith("Error"):
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return text
        return None
    
    # Test 1: Project and Board Manager
    @pytest.mark.asyncio
    async def test_01_project_board_manager(self, mcp_connection):
        """Test mcp_kanban_project_board_manager tool"""
        print("\n🔧 Testing Project & Board Manager")
        
        # Test get_projects
        print("  → Testing get_projects...")
        projects = await self._call_tool(mcp_connection, "mcp_kanban_project_board_manager", {
            "action": "get_projects",
            "page": 1,
            "perPage": 10
        })
        assert projects is not None
        assert "items" in projects
        print(f"  ✅ Found {len(projects['items'])} projects")
        
        # Test get_project
        print("  → Testing get_project...")
        project = await self._call_tool(mcp_connection, "mcp_kanban_project_board_manager", {
            "action": "get_project",
            "projectId": self.test_project_id
        })
        assert project is not None
        assert project.get("id") == self.test_project_id
        print(f"  ✅ Got project: {project.get('name')}")
        
        # Test create_board
        print("  → Testing create_board...")
        board_name = f"Test Board - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        board = await self._call_tool(mcp_connection, "mcp_kanban_project_board_manager", {
            "action": "create_board",
            "projectId": self.test_project_id,
            "name": board_name,
            "position": 1
        })
        assert board is not None
        assert board.get("name") == board_name
        self.__class__.test_board_id = board["id"]
        self.created_resources["boards"].append(board["id"])
        print(f"  ✅ Created board: {board_name} (ID: {board['id']})")
        
        # Test get_boards
        print("  → Testing get_boards...")
        boards = await self._call_tool(mcp_connection, "mcp_kanban_project_board_manager", {
            "action": "get_boards",
            "projectId": self.test_project_id,
            "page": 1,
            "perPage": 10
        })
        assert boards is not None
        assert isinstance(boards, list)
        assert any(b["id"] == self.test_board_id for b in boards)
        print(f"  ✅ Found {len(boards)} boards")
        
        # Test get_board
        print("  → Testing get_board...")
        board_detail = await self._call_tool(mcp_connection, "mcp_kanban_project_board_manager", {
            "action": "get_board",
            "boardId": self.test_board_id
        })
        assert board_detail is not None
        assert board_detail.get("id") == self.test_board_id
        print(f"  ✅ Got board details")
        
        # Test update_board
        print("  → Testing update_board...")
        updated_name = f"{board_name} - Updated"
        updated_board = await self._call_tool(mcp_connection, "mcp_kanban_project_board_manager", {
            "action": "update_board",
            "boardId": self.test_board_id,
            "name": updated_name
        })
        assert updated_board is not None
        assert updated_board.get("name") == updated_name
        print(f"  ✅ Updated board name")
        
        # Test get_board_summary
        print("  → Testing get_board_summary...")
        summary = await self._call_tool(mcp_connection, "mcp_kanban_project_board_manager", {
            "action": "get_board_summary",
            "boardId": self.test_board_id
        })
        assert summary is not None
        assert "stats" in summary
        print(f"  ✅ Got board summary")
    
    # Test 2: List Manager
    @pytest.mark.asyncio
    async def test_02_list_manager(self, mcp_connection):
        """Test mcp_kanban_list_manager tool"""
        print("\n🔧 Testing List Manager")
        
        # Test get_all lists
        print("  → Testing get_all lists...")
        lists = await self._call_tool(mcp_connection, "mcp_kanban_list_manager", {
            "action": "get_all",
            "boardId": self.test_board_id
        })
        assert lists is not None
        assert isinstance(lists, list)
        assert len(lists) > 0
        self.__class__.test_list_id = lists[0]["id"]
        print(f"  ✅ Found {len(lists)} lists")
        
        # Test create list
        print("  → Testing create list...")
        new_list = await self._call_tool(mcp_connection, "mcp_kanban_list_manager", {
            "action": "create",
            "boardId": self.test_board_id,
            "name": "Test List",
            "position": 1000
        })
        assert new_list is not None
        assert new_list.get("name") == "Test List"
        print(f"  ✅ Created list: {new_list['name']}")
        
        # Test get_one list
        print("  → Testing get_one list...")
        list_detail = await self._call_tool(mcp_connection, "mcp_kanban_list_manager", {
            "action": "get_one",
            "id": new_list["id"]
        })
        assert list_detail is not None
        assert list_detail.get("id") == new_list["id"]
        print(f"  ✅ Got list details")
        
        # Test update list
        print("  → Testing update list...")
        updated_list = await self._call_tool(mcp_connection, "mcp_kanban_list_manager", {
            "action": "update",
            "id": new_list["id"],
            "name": "Test List - Updated"
        })
        assert updated_list is not None
        assert updated_list.get("name") == "Test List - Updated"
        print(f"  ✅ Updated list name")
        
        # Test delete list
        print("  → Testing delete list...")
        delete_result = await self._call_tool(mcp_connection, "mcp_kanban_list_manager", {
            "action": "delete",
            "id": new_list["id"]
        })
        assert delete_result is not None
        print(f"  ✅ Deleted list")
    
    # Test 3: Card Manager
    @pytest.mark.asyncio
    async def test_03_card_manager(self, mcp_connection):
        """Test mcp_kanban_card_manager tool"""
        print("\n🔧 Testing Card Manager")
        
        # Test create card
        print("  → Testing create card...")
        card = await self._call_tool(mcp_connection, "mcp_kanban_card_manager", {
            "action": "create",
            "listId": self.test_list_id,
            "name": "Test Card",
            "description": "This is a test card created by the test suite"
        })
        assert card is not None
        assert card.get("name") == "Test Card"
        self.__class__.test_card_id = card["id"]
        self.created_resources["cards"].append(card["id"])
        print(f"  ✅ Created card: {card['name']} (ID: {card['id']})")
        
        # Test get_all cards
        print("  → Testing get_all cards...")
        cards = await self._call_tool(mcp_connection, "mcp_kanban_card_manager", {
            "action": "get_all",
            "boardId": self.test_board_id
        })
        assert cards is not None
        assert isinstance(cards, list)
        assert any(c["id"] == self.test_card_id for c in cards)
        print(f"  ✅ Found {len(cards)} cards")
        
        # Test get_one card
        print("  → Testing get_one card...")
        card_detail = await self._call_tool(mcp_connection, "mcp_kanban_card_manager", {
            "action": "get_one",
            "id": self.test_card_id
        })
        assert card_detail is not None
        assert card_detail.get("id") == self.test_card_id
        print(f"  ✅ Got card details")
        
        # Test update card
        print("  → Testing update card...")
        updated_card = await self._call_tool(mcp_connection, "mcp_kanban_card_manager", {
            "action": "update",
            "id": self.test_card_id,
            "name": "Test Card - Updated",
            "description": "Updated description"
        })
        assert updated_card is not None
        assert updated_card.get("name") == "Test Card - Updated"
        print(f"  ✅ Updated card")
        
        # Test duplicate card
        print("  → Testing duplicate card...")
        duplicated = await self._call_tool(mcp_connection, "mcp_kanban_card_manager", {
            "action": "duplicate",
            "id": self.test_card_id
        })
        assert duplicated is not None
        self.created_resources["cards"].append(duplicated["id"])
        print(f"  ✅ Duplicated card")
        
        # Test get_details
        print("  → Testing get_details...")
        details = await self._call_tool(mcp_connection, "mcp_kanban_card_manager", {
            "action": "get_details",
            "cardId": self.test_card_id
        })
        assert details is not None
        print(f"  ✅ Got detailed card info")
    
    # Test 4: Label Manager
    @pytest.mark.asyncio
    async def test_04_label_manager(self, mcp_connection):
        """Test mcp_kanban_label_manager tool"""
        print("\n🔧 Testing Label Manager")
        
        # Test get_all labels
        print("  → Testing get_all labels...")
        labels = await self._call_tool(mcp_connection, "mcp_kanban_label_manager", {
            "action": "get_all",
            "boardId": self.test_board_id
        })
        assert labels is not None
        assert isinstance(labels, list)
        if labels:
            self.__class__.test_label_id = labels[0]["id"]
        print(f"  ✅ Found {len(labels)} labels")
        
        # Test create label
        print("  → Testing create label...")
        new_label = await self._call_tool(mcp_connection, "mcp_kanban_label_manager", {
            "action": "create",
            "boardId": self.test_board_id,
            "name": "Test Label",
            "color": "red"
        })
        assert new_label is not None
        assert new_label.get("name") == "Test Label"
        self.created_resources["labels"].append(new_label["id"])
        print(f"  ✅ Created label: {new_label['name']}")
        
        # Test add_to_card
        print("  → Testing add_to_card...")
        add_result = await self._call_tool(mcp_connection, "mcp_kanban_label_manager", {
            "action": "add_to_card",
            "cardId": self.test_card_id,
            "labelId": new_label["id"]
        })
        assert add_result is not None
        print(f"  ✅ Added label to card")
        
        # Test remove_from_card
        print("  → Testing remove_from_card...")
        remove_result = await self._call_tool(mcp_connection, "mcp_kanban_label_manager", {
            "action": "remove_from_card",
            "cardId": self.test_card_id,
            "labelId": new_label["id"]
        })
        assert remove_result is not None
        print(f"  ✅ Removed label from card")
        
        # Test update label
        print("  → Testing update label...")
        updated_label = await self._call_tool(mcp_connection, "mcp_kanban_label_manager", {
            "action": "update",
            "id": new_label["id"],
            "name": "Test Label - Updated",
            "color": "blue"
        })
        assert updated_label is not None
        assert updated_label.get("name") == "Test Label - Updated"
        print(f"  ✅ Updated label")
    
    # Test 5: Task Manager
    @pytest.mark.asyncio
    async def test_05_task_manager(self, mcp_connection):
        """Test mcp_kanban_task_manager tool"""
        print("\n🔧 Testing Task Manager")
        
        # Test create task
        print("  → Testing create task...")
        task = await self._call_tool(mcp_connection, "mcp_kanban_task_manager", {
            "action": "create",
            "cardId": self.test_card_id,
            "name": "Test Task",
            "position": 1
        })
        assert task is not None
        assert task.get("name") == "Test Task"
        self.__class__.test_task_id = task["id"]
        self.created_resources["tasks"].append(task["id"])
        print(f"  ✅ Created task: {task['name']}")
        
        # Test get_all tasks
        print("  → Testing get_all tasks...")
        tasks = await self._call_tool(mcp_connection, "mcp_kanban_task_manager", {
            "action": "get_all",
            "cardId": self.test_card_id
        })
        assert tasks is not None
        assert isinstance(tasks, list)
        assert any(t["id"] == self.test_task_id for t in tasks)
        print(f"  ✅ Found {len(tasks)} tasks")
        
        # Test batch_create tasks
        print("  → Testing batch_create tasks...")
        batch_tasks = await self._call_tool(mcp_connection, "mcp_kanban_task_manager", {
            "action": "batch_create",
            "cardId": self.test_card_id,
            "tasks": [
                {"name": "Batch Task 1", "position": 2},
                {"name": "Batch Task 2", "position": 3}
            ]
        })
        assert batch_tasks is not None
        assert len(batch_tasks) == 2
        for task in batch_tasks:
            self.created_resources["tasks"].append(task["id"])
        print(f"  ✅ Created {len(batch_tasks)} tasks in batch")
        
        # Test update task
        print("  → Testing update task...")
        updated_task = await self._call_tool(mcp_connection, "mcp_kanban_task_manager", {
            "action": "update",
            "id": self.test_task_id,
            "name": "Test Task - Updated",
            "isCompleted": True
        })
        assert updated_task is not None
        assert updated_task.get("name") == "Test Task - Updated"
        assert updated_task.get("isCompleted") == True
        print(f"  ✅ Updated task")
        
        # Test complete_task
        print("  → Testing complete_task...")
        completed = await self._call_tool(mcp_connection, "mcp_kanban_task_manager", {
            "action": "complete_task",
            "taskId": batch_tasks[0]["id"]
        })
        assert completed is not None
        assert completed.get("isCompleted") == True
        print(f"  ✅ Completed task")
    
    # Test 6: Comment Manager
    @pytest.mark.asyncio
    async def test_06_comment_manager(self, mcp_connection):
        """Test mcp_kanban_comment_manager tool"""
        print("\n🔧 Testing Comment Manager")
        
        # Test create comment
        print("  → Testing create comment...")
        comment = await self._call_tool(mcp_connection, "mcp_kanban_comment_manager", {
            "action": "create",
            "cardId": self.test_card_id,
            "text": "This is a test comment from the test suite"
        })
        assert comment is not None
        assert "test comment" in comment.get("text", "").lower()
        self.__class__.test_comment_id = comment["id"]
        self.created_resources["comments"].append(comment["id"])
        print(f"  ✅ Created comment")
        
        # Test get_all comments
        print("  → Testing get_all comments...")
        comments = await self._call_tool(mcp_connection, "mcp_kanban_comment_manager", {
            "action": "get_all",
            "cardId": self.test_card_id
        })
        assert comments is not None
        assert isinstance(comments, list)
        assert any(c["id"] == self.test_comment_id for c in comments)
        print(f"  ✅ Found {len(comments)} comments")
        
        # Test update comment
        print("  → Testing update comment...")
        updated_comment = await self._call_tool(mcp_connection, "mcp_kanban_comment_manager", {
            "action": "update",
            "id": self.test_comment_id,
            "text": "This is an updated test comment"
        })
        assert updated_comment is not None
        assert "updated test comment" in updated_comment.get("text", "").lower()
        print(f"  ✅ Updated comment")
        
        # Test delete comment
        print("  → Testing delete comment...")
        delete_result = await self._call_tool(mcp_connection, "mcp_kanban_comment_manager", {
            "action": "delete",
            "id": self.test_comment_id
        })
        assert delete_result is not None
        print(f"  ✅ Deleted comment")
    
    # Test 7: Stopwatch
    @pytest.mark.asyncio
    async def test_07_stopwatch(self, mcp_connection):
        """Test mcp_kanban_stopwatch tool"""
        print("\n🔧 Testing Stopwatch")
        
        # Test start stopwatch
        print("  → Testing start stopwatch...")
        start_result = await self._call_tool(mcp_connection, "mcp_kanban_stopwatch", {
            "action": "start",
            "cardId": self.test_card_id
        })
        assert start_result is not None
        print(f"  ✅ Started stopwatch")
        
        # Wait a bit
        await asyncio.sleep(2)
        
        # Test get stopwatch
        print("  → Testing get stopwatch...")
        get_result = await self._call_tool(mcp_connection, "mcp_kanban_stopwatch", {
            "action": "get",
            "cardId": self.test_card_id
        })
        assert get_result is not None
        print(f"  ✅ Got stopwatch data")
        
        # Test stop stopwatch
        print("  → Testing stop stopwatch...")
        stop_result = await self._call_tool(mcp_connection, "mcp_kanban_stopwatch", {
            "action": "stop",
            "cardId": self.test_card_id
        })
        assert stop_result is not None
        print(f"  ✅ Stopped stopwatch")
        
        # Test reset stopwatch
        print("  → Testing reset stopwatch...")
        reset_result = await self._call_tool(mcp_connection, "mcp_kanban_stopwatch", {
            "action": "reset",
            "cardId": self.test_card_id
        })
        assert reset_result is not None
        print(f"  ✅ Reset stopwatch")
    
    # Test 8: Membership Manager
    @pytest.mark.asyncio
    async def test_08_membership_manager(self, mcp_connection):
        """Test mcp_kanban_membership_manager tool"""
        print("\n🔧 Testing Membership Manager")
        
        # Test get_all memberships
        print("  → Testing get_all memberships...")
        memberships = await self._call_tool(mcp_connection, "mcp_kanban_membership_manager", {
            "action": "get_all",
            "boardId": self.test_board_id
        })
        assert memberships is not None
        assert isinstance(memberships, list)
        print(f"  ✅ Found {len(memberships)} memberships")
        
        # Note: We won't test create/delete membership as it requires additional user IDs
        # and could affect the demo user's access
    
    # Cleanup
    @pytest.mark.asyncio
    async def test_99_cleanup(self, mcp_connection):
        """Clean up created resources"""
        print("\n🧹 Cleaning up test resources...")
        
        # Delete test board (will cascade delete cards, lists, etc.)
        if self.test_board_id in self.created_resources["boards"]:
            try:
                await self._call_tool(mcp_connection, "mcp_kanban_project_board_manager", {
                    "action": "delete_board",
                    "boardId": self.test_board_id
                })
                print(f"  ✅ Deleted test board")
            except Exception as e:
                print(f"  ⚠️ Could not delete board: {e}")
        
        print("  ✅ Cleanup complete")


# Test the refactored client
class TestRefactoredClient:
    """Test the refactored MCPKanbanClient"""
    
    @pytest.mark.asyncio
    async def test_client_connection(self):
        """Test basic client connection"""
        print("\n🔧 Testing Refactored Client")
        
        client = MCPKanbanClient()
        client.project_id = "1533678301472621705"
        
        # Test connection context manager
        print("  → Testing connection context...")
        async with client.connect() as conn:
            assert conn is not None
            assert conn.session is not None
            print("  ✅ Connection established")
        
        # Test get available tasks
        print("  → Testing get_available_tasks...")
        tasks = await client.get_available_tasks()
        assert isinstance(tasks, list)
        print(f"  ✅ Found {len(tasks)} available tasks")
        
        # Test board summary
        print("  → Testing get_board_summary...")
        if client.board_id:
            summary = await client.get_board_summary()
            assert isinstance(summary, dict)
            print("  ✅ Got board summary")
    
    @pytest.mark.asyncio
    async def test_task_operations(self):
        """Test task-related operations"""
        print("\n🔧 Testing Task Operations")
        
        client = MCPKanbanClient()
        client.project_id = "1533678301472621705"
        
        # Create a test task
        print("  → Testing create_task...")
        task = await client.create_task({
            "name": "Test Task from Refactored Client",
            "description": "Created by test suite",
            "labels": ["test"]
        })
        assert task is not None
        assert task.name == "Test Task from Refactored Client"
        print(f"  ✅ Created task: {task.id}")
        
        # Add comment
        print("  → Testing add_comment...")
        await client.add_comment(task.id, "Test comment from refactored client")
        print("  ✅ Added comment")
        
        # Update progress
        print("  → Testing update_task_progress...")
        await client.update_task_progress(task.id, 50)
        print("  ✅ Updated progress")
        
        # Complete task
        print("  → Testing complete_task...")
        await client.complete_task(task.id)
        print("  ✅ Completed task")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])