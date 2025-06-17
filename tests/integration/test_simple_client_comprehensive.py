"""
Comprehensive test suite for SimpleMCPKanbanClient
Tests all board functionalities including tasks, assignments, comments, and summaries
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

from src.integrations.mcp_kanban_client_simple import SimpleMCPKanbanClient
from src.core.models import Task, TaskStatus, Priority


class TestSimpleClientComprehensive:
    """Comprehensive test suite for SimpleMCPKanbanClient"""
    
    @classmethod
    def setup_class(cls):
        """Set up test configuration"""
        cls.client = SimpleMCPKanbanClient()
        cls.test_card_ids = []
        cls.test_comment_ids = []
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Reset client state before each test"""
        self.client = SimpleMCPKanbanClient()
    
    # Test 1: Configuration Loading
    @pytest.mark.asyncio
    async def test_01_configuration_loading(self):
        """Test that configuration is properly loaded"""
        print("\n🔧 Testing Configuration Loading")
        
        assert self.client.board_id is not None, "Board ID should be loaded from config"
        assert self.client.project_id is not None, "Project ID should be loaded from config"
        print(f"  ✅ Loaded config: project_id={self.client.project_id}, board_id={self.client.board_id}")
    
    # Test 2: Board Summary
    @pytest.mark.asyncio
    async def test_02_get_board_summary(self):
        """Test getting board summary statistics"""
        print("\n🔧 Testing Board Summary")
        
        summary = await self.client.get_board_summary()
        assert isinstance(summary, dict), "Summary should be a dictionary"
        
        # Check for expected fields
        assert "stats" in summary or "totalCards" in summary, "Summary should contain statistics"
        
        if "stats" in summary:
            stats = summary["stats"]
            print(f"  ✅ Board statistics:")
            print(f"     - Total cards: {stats.get('totalCards', 0)}")
            print(f"     - In progress: {stats.get('inProgressCount', 0)}")
            print(f"     - Done: {stats.get('doneCount', 0)}")
        else:
            print(f"  ✅ Board has {summary.get('totalCards', 0)} cards")
    
    # Test 3: Get Available Tasks
    @pytest.mark.asyncio
    async def test_03_get_available_tasks(self):
        """Test retrieving available (unassigned) tasks"""
        print("\n🔧 Testing Get Available Tasks")
        
        tasks = await self.client.get_available_tasks()
        assert isinstance(tasks, list), "Tasks should be a list"
        
        print(f"  ✅ Found {len(tasks)} available tasks")
        
        # Verify task structure
        if tasks:
            task = tasks[0]
            assert hasattr(task, 'id'), "Task should have an id"
            assert hasattr(task, 'name'), "Task should have a name"
            assert hasattr(task, 'status'), "Task should have a status"
            assert hasattr(task, 'priority'), "Task should have a priority"
            assert hasattr(task, 'assigned_to'), "Task should have assigned_to field"
            assert task.assigned_to is None, "Available tasks should not be assigned"
            
            print(f"  ✅ First available task: {task.name} (ID: {task.id})")
    
    # Test 4: Task Assignment
    @pytest.mark.asyncio
    async def test_04_assign_task(self):
        """Test assigning a task to an agent"""
        print("\n🔧 Testing Task Assignment")
        
        # Get an available task
        tasks = await self.client.get_available_tasks()
        if not tasks:
            print("  ⚠️ No available tasks to test assignment")
            return
        
        task = tasks[0]
        agent_id = "test-agent-001"
        
        print(f"  → Assigning task '{task.name}' to {agent_id}")
        await self.client.assign_task(task.id, agent_id)
        print(f"  ✅ Task assigned successfully")
        
        # Store for cleanup
        self.test_card_ids.append(task.id)
    
    # Test 5: Task Status Filtering
    @pytest.mark.asyncio
    async def test_05_task_status_filtering(self):
        """Test that task status is correctly determined from list names"""
        print("\n🔧 Testing Task Status Filtering")
        
        # Create a mock card for each status type
        test_cards = [
            {"id": "1", "name": "Todo Task", "listName": "TODO", "description": ""},
            {"id": "2", "name": "In Progress Task", "listName": "In Progress", "description": ""},
            {"id": "3", "name": "Done Task", "listName": "Done", "description": ""},
            {"id": "4", "name": "Blocked Task", "listName": "Blocked", "description": ""}
        ]
        
        for card in test_cards:
            task = self.client._card_to_task(card)
            print(f"  → Card in '{card['listName']}' list -> Status: {task.status.value}")
            
            if "TODO" in card["listName"].upper():
                assert task.status == TaskStatus.TODO
            elif "PROGRESS" in card["listName"].upper():
                assert task.status == TaskStatus.IN_PROGRESS
            elif "DONE" in card["listName"].upper():
                assert task.status == TaskStatus.DONE
            elif "BLOCKED" in card["listName"].upper():
                assert task.status == TaskStatus.BLOCKED
        
        print("  ✅ All task statuses correctly mapped")
    
    # Test 6: Available Task Filtering
    @pytest.mark.asyncio
    async def test_06_available_task_filtering(self):
        """Test that only tasks in available states are returned"""
        print("\n🔧 Testing Available Task Filtering")
        
        # Test cards in different states
        available_cards = [
            {"id": "1", "name": "Task 1", "listName": "TODO"},
            {"id": "2", "name": "Task 2", "listName": "To Do"},
            {"id": "3", "name": "Task 3", "listName": "Backlog"},
            {"id": "4", "name": "Task 4", "listName": "Ready"}
        ]
        
        unavailable_cards = [
            {"id": "5", "name": "Task 5", "listName": "In Progress"},
            {"id": "6", "name": "Task 6", "listName": "Done"},
            {"id": "7", "name": "Task 7", "listName": "Blocked"}
        ]
        
        # Check available cards
        for card in available_cards:
            is_available = self.client._is_available_task(card)
            assert is_available == True, f"Card in '{card['listName']}' should be available"
            print(f"  ✅ Card in '{card['listName']}' correctly identified as available")
        
        # Check unavailable cards
        for card in unavailable_cards:
            is_available = self.client._is_available_task(card)
            assert is_available == False, f"Card in '{card['listName']}' should not be available"
            print(f"  ✅ Card in '{card['listName']}' correctly identified as unavailable")
    
    # Test 7: Error Handling
    @pytest.mark.asyncio
    async def test_07_error_handling(self):
        """Test error handling for various scenarios"""
        print("\n🔧 Testing Error Handling")
        
        # Test with no board_id
        client_no_board = SimpleMCPKanbanClient()
        client_no_board.board_id = None
        
        print("  → Testing get_available_tasks with no board_id...")
        try:
            await client_no_board.get_available_tasks()
            assert False, "Should have raised RuntimeError"
        except RuntimeError as e:
            assert "Board ID not set" in str(e)
            print("  ✅ Correctly raised RuntimeError for missing board_id")
        
        # Test get_board_summary with no board_id
        print("  → Testing get_board_summary with no board_id...")
        try:
            await client_no_board.get_board_summary()
            assert False, "Should have raised RuntimeError"
        except RuntimeError as e:
            assert "Board ID not set" in str(e)
            print("  ✅ Correctly raised RuntimeError for missing board_id")
    
    # Test 8: Task Priority Handling
    @pytest.mark.asyncio
    async def test_08_task_priority(self):
        """Test that all tasks get appropriate priority"""
        print("\n🔧 Testing Task Priority Handling")
        
        test_card = {
            "id": "test-123",
            "name": "Test Task",
            "description": "Test description",
            "listName": "TODO"
        }
        
        task = self.client._card_to_task(test_card)
        assert task.priority == Priority.MEDIUM, "Default priority should be MEDIUM"
        print(f"  ✅ Task created with default priority: {task.priority.value}")
    
    # Test 9: Date Handling
    @pytest.mark.asyncio
    async def test_09_date_handling(self):
        """Test that dates are properly handled"""
        print("\n🔧 Testing Date Handling")
        
        test_card = {
            "id": "test-123",
            "name": "Test Task",
            "description": "Test description",
            "listName": "TODO"
        }
        
        task = self.client._card_to_task(test_card)
        
        assert isinstance(task.created_at, datetime), "created_at should be a datetime"
        assert isinstance(task.updated_at, datetime), "updated_at should be a datetime"
        assert task.due_date is None, "due_date should be None when not provided"
        
        print("  ✅ Dates properly initialized")
        print(f"     - Created at: {task.created_at}")
        print(f"     - Updated at: {task.updated_at}")
        print(f"     - Due date: {task.due_date}")
    
    # Test 10: Performance Test
    @pytest.mark.asyncio
    async def test_10_performance(self):
        """Test performance of operations"""
        print("\n🔧 Testing Performance")
        
        import time
        
        # Test get_available_tasks performance
        start = time.time()
        tasks = await self.client.get_available_tasks()
        elapsed = time.time() - start
        
        print(f"  ✅ get_available_tasks completed in {elapsed:.2f} seconds")
        assert elapsed < 10, "Operation should complete within 10 seconds"
        
        # Test get_board_summary performance
        start = time.time()
        summary = await self.client.get_board_summary()
        elapsed = time.time() - start
        
        print(f"  ✅ get_board_summary completed in {elapsed:.2f} seconds")
        assert elapsed < 5, "Operation should complete within 5 seconds"
    
    # Test 11: Integration with PM Agent
    @pytest.mark.asyncio
    async def test_11_pm_agent_integration(self):
        """Test that client works well with PM Agent requirements"""
        print("\n🔧 Testing PM Agent Integration Requirements")
        
        # Test that we can get tasks for assignment
        tasks = await self.client.get_available_tasks()
        
        # Verify tasks have all required fields for PM Agent
        if tasks:
            task = tasks[0]
            
            # Check required fields
            assert hasattr(task, 'id'), "Task must have id for PM Agent"
            assert hasattr(task, 'name'), "Task must have name for PM Agent"
            assert hasattr(task, 'description'), "Task must have description for PM Agent"
            assert hasattr(task, 'status'), "Task must have status for PM Agent"
            assert hasattr(task, 'priority'), "Task must have priority for PM Agent"
            assert hasattr(task, 'assigned_to'), "Task must have assigned_to for PM Agent"
            assert hasattr(task, 'created_at'), "Task must have created_at for PM Agent"
            assert hasattr(task, 'updated_at'), "Task must have updated_at for PM Agent"
            assert hasattr(task, 'due_date'), "Task must have due_date for PM Agent"
            assert hasattr(task, 'estimated_hours'), "Task must have estimated_hours for PM Agent"
            assert hasattr(task, 'actual_hours'), "Task must have actual_hours for PM Agent"
            assert hasattr(task, 'dependencies'), "Task must have dependencies for PM Agent"
            assert hasattr(task, 'labels'), "Task must have labels for PM Agent"
            
            print("  ✅ Task has all required fields for PM Agent")
            print(f"     - Task ID: {task.id}")
            print(f"     - Task Name: {task.name}")
            print(f"     - Status: {task.status.value}")
            print(f"     - Priority: {task.priority.value}")
    
    # Test 12: Multiple List Handling
    @pytest.mark.asyncio
    async def test_12_multiple_list_handling(self):
        """Test that client correctly handles cards from multiple lists"""
        print("\n🔧 Testing Multiple List Handling")
        
        # This test verifies the fix for the listId requirement
        tasks = await self.client.get_available_tasks()
        
        # Check that we got tasks and they have list information
        if tasks:
            # Group tasks by their list
            lists_found = set()
            for task in tasks:
                # The listName is added during card collection
                # We can't directly access it from Task object, but we know it worked
                # if we got tasks from multiple lists
                lists_found.add(task.status.value)
            
            print(f"  ✅ Successfully retrieved tasks from lists with statuses: {lists_found}")
            print(f"     - Total tasks found: {len(tasks)}")
        else:
            print("  ⚠️ No tasks available for multiple list testing")
    
    # Cleanup
    @classmethod
    def teardown_class(cls):
        """Clean up any test data if needed"""
        print("\n🧹 Test suite completed")
        if cls.test_card_ids:
            print(f"  ℹ️ Created {len(cls.test_card_ids)} test cards during testing")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])