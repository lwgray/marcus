"""
Test suite for preventing duplicate task assignments in Marcus.

This module tests the long-term fix for the duplicate assignment issue where
multiple workers can be assigned the same task.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import json
from pathlib import Path
import tempfile
import os

# Import the components we'll be testing
from marcus_mcp_server import (
    MarcusState, 
    find_optimal_task_for_agent,
    request_next_task,
    refresh_project_state
)
from src.core.models import Task, TaskStatus, Priority, WorkerStatus
from src.integrations.kanban_interface import KanbanInterface


class TestAssignmentDeduplication:
    """Test cases for preventing duplicate task assignments."""
    
    @pytest.fixture
    async def mock_kanban_client(self):
        """Create a mock kanban client for testing."""
        client = AsyncMock(spec=KanbanInterface)
        
        # Create test tasks
        now = datetime.now()
        test_tasks = [
            Task(
                id="task-1",
                name="Write comprehensive tests",
                description="Write tests for the system",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                labels=["testing", "python"],
                estimated_hours=8,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=None,
                actual_hours=0.0,
                dependencies=[]
            ),
            Task(
                id="task-2", 
                name="Implement feature X",
                description="Build new feature",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                labels=["development", "python"],
                estimated_hours=16,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=None,
                actual_hours=0.0,
                dependencies=[]
            ),
            Task(
                id="task-3",
                name="Fix bug Y",
                description="Fix critical bug",
                status=TaskStatus.IN_PROGRESS,
                priority=Priority.URGENT,
                labels=["bug", "python"],
                estimated_hours=4,
                assigned_to="other-worker",
                created_at=now,
                updated_at=now,
                due_date=None,
                actual_hours=0.0,
                dependencies=[]
            )
        ]
        
        # Make get_available_tasks always return TODO tasks (simulating kanban not updating)
        def get_available_tasks_side_effect():
            return [t for t in test_tasks if t.status == TaskStatus.TODO]
        
        client.get_available_tasks.side_effect = get_available_tasks_side_effect
        client.update_task.return_value = test_tasks[0]  # Default return
        client.get_task_by_id.return_value = test_tasks[0]
        
        return client
    
    @pytest.fixture
    async def marcus_state(self, mock_kanban_client):
        """Create a Marcus state instance for testing."""
        with patch('marcus_mcp_server.KanbanFactory.create_default', return_value=mock_kanban_client):
            state = MarcusState()
            state.kanban_client = mock_kanban_client
            
            # Register test workers
            state.agent_status["worker-1"] = WorkerStatus(
                worker_id="worker-1",
                name="Test Worker 1",
                role="Developer",
                email="worker1@test.com",
                skills=["python", "testing"],
                current_tasks=[],
                completed_tasks_count=0,
                capacity=40,
                availability={
                    "monday": True, "tuesday": True, "wednesday": True,
                    "thursday": True, "friday": True, "saturday": False, "sunday": False
                },
                performance_score=1.0
            )
            
            state.agent_status["worker-2"] = WorkerStatus(
                worker_id="worker-2",
                name="Test Worker 2", 
                role="Developer",
                email="worker2@test.com",
                skills=["python", "development"],
                current_tasks=[],
                completed_tasks_count=0,
                capacity=40,
                availability={
                    "monday": True, "tuesday": True, "wednesday": True,
                    "thursday": True, "friday": True, "saturday": False, "sunday": False
                },
                performance_score=1.0
            )
            
            return state
    
    @pytest.mark.asyncio
    async def test_sequential_assignments_different_tasks(self, marcus_state, mock_kanban_client):
        """Test that sequential task requests assign different tasks."""
        # This test should FAIL initially, demonstrating the bug
        
        # Worker 1 requests a task
        with patch('marcus_mcp_server.state', marcus_state):
            # Need to populate project_tasks first
            await refresh_project_state()
            
            # First assignment
            task1 = await find_optimal_task_for_agent("worker-1")
            assert task1 is not None
            assert task1.id == "task-1"  # Highest priority matching task
            print(f"Worker 1 got task: {task1.id}")
            
            # Simulate the assignment being recorded
            marcus_state.agent_tasks["worker-1"] = Mock(task_id=task1.id)
            print(f"agent_tasks after assignment: {list(marcus_state.agent_tasks.keys())}")
            
            # Simulate what happens in real scenario - state refresh between requests
            # This overwrites project_tasks and loses the in-memory tracking
            await refresh_project_state()
            print(f"agent_tasks after refresh: {list(marcus_state.agent_tasks.keys())}")
            
            # Worker 2 requests a task
            task2 = await find_optimal_task_for_agent("worker-2")
            assert task2 is not None
            print(f"Worker 2 got task: {task2.id}")
            
            # This assertion should FAIL with current implementation
            assert task2.id != task1.id, "Worker 2 should not get the same task as Worker 1"
            assert task2.id == "task-2"  # Should get the next available task
    
    @pytest.mark.asyncio
    async def test_kanban_update_failure_prevents_assignment(self, marcus_state, mock_kanban_client):
        """Test that failed kanban updates prevent task assignment completion."""
        # This test should FAIL initially
        
        # Make kanban update fail
        mock_kanban_client.update_task.side_effect = Exception("Kanban update failed")
        
        with patch('marcus_mcp_server.state', marcus_state):
            with patch('marcus_mcp_server.request_next_task') as mock_request:
                # This should handle the error gracefully
                result = await request_next_task("worker-1")
                
                # Task should NOT be assigned if kanban update fails
                assert not result.get('success'), "Assignment should fail if kanban update fails"
                assert "worker-1" not in marcus_state.agent_tasks, "Task should not be tracked locally if kanban update fails"
    
    @pytest.mark.asyncio
    async def test_concurrent_assignments_use_locking(self, marcus_state, mock_kanban_client):
        """Test that concurrent requests are properly serialized."""
        # This test should FAIL initially
        
        with patch('marcus_mcp_server.state', marcus_state):
            # Simulate concurrent requests
            async def worker_request(worker_id):
                return await find_optimal_task_for_agent(worker_id)
            
            # Run both requests concurrently
            results = await asyncio.gather(
                worker_request("worker-1"),
                worker_request("worker-2"),
                return_exceptions=True
            )
            
            task1, task2 = results
            
            # Both should get tasks, but different ones
            assert task1 is not None
            assert task2 is not None
            assert task1.id != task2.id, "Concurrent requests should not get the same task"
    
    @pytest.mark.asyncio
    async def test_assignment_persistence_across_restarts(self, marcus_state, mock_kanban_client):
        """Test that assignments persist across Marcus restarts."""
        # This test should FAIL initially
        
        with patch('marcus_mcp_server.state', marcus_state):
            # Assign a task
            task1 = await find_optimal_task_for_agent("worker-1")
            marcus_state.agent_tasks["worker-1"] = Mock(task_id=task1.id)
            
            # Simulate Marcus restart by creating new state
            new_state = MarcusState()
            new_state.kanban_client = mock_kanban_client
            
            # Assignment should be restored from persistent storage
            # This will FAIL because we don't have persistence yet
            assert "worker-1" in new_state.agent_tasks, "Assignments should persist across restarts"
            assert new_state.agent_tasks["worker-1"].task_id == task1.id
    
    @pytest.mark.asyncio
    async def test_state_refresh_preserves_assignments(self, marcus_state, mock_kanban_client):
        """Test that refresh_project_state doesn't lose assignment tracking."""
        # This test should FAIL initially
        
        with patch('marcus_mcp_server.state', marcus_state):
            # Assign a task
            task1 = await find_optimal_task_for_agent("worker-1") 
            marcus_state.agent_tasks["worker-1"] = Mock(task_id=task1.id)
            
            # Refresh state (this currently overwrites everything)
            await refresh_project_state()
            
            # Assignment tracking should be preserved
            assert "worker-1" in marcus_state.agent_tasks, "Assignments should survive state refresh"
            
            # Worker 2 should not be able to get task1
            task2 = await find_optimal_task_for_agent("worker-2")
            assert task2.id != task1.id, "Previously assigned tasks should remain unavailable"
    
    @pytest.mark.asyncio
    async def test_assignment_reconciliation(self, marcus_state, mock_kanban_client):
        """Test that Marcus can reconcile assignments with kanban state."""
        # This test should FAIL initially
        
        # Simulate a task that's IN_PROGRESS in kanban but not tracked locally
        now = datetime.now()
        mock_kanban_client.get_available_tasks.return_value = [
            Task(
                id="task-1",
                name="Write comprehensive tests",
                status=TaskStatus.IN_PROGRESS,  # Already assigned in kanban
                assigned_to="worker-1",
                priority=Priority.HIGH,
                labels=["testing"],
                description="Test task",
                estimated_hours=8,
                created_at=now,
                updated_at=now,
                due_date=None,
                actual_hours=0.0,
                dependencies=[]
            )
        ]
        
        with patch('marcus_mcp_server.state', marcus_state):
            await refresh_project_state()
            
            # Marcus should detect and track this assignment
            assert "worker-1" in marcus_state.agent_tasks, "Should reconcile existing assignments from kanban"
            
            # Worker 2 should not get this task
            task = await find_optimal_task_for_agent("worker-2")
            assert task is None or task.id != "task-1", "Should not assign already assigned tasks"


class TestAssignmentPersistence:
    """Test cases for assignment persistence functionality."""
    
    @pytest.mark.asyncio
    async def test_save_assignment_to_file(self):
        """Test saving assignments to persistent storage."""
        # This will FAIL initially as we haven't implemented it
        
        from marcus_mcp_server import AssignmentPersistence  # This doesn't exist yet
        
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = AssignmentPersistence(Path(tmpdir))
            
            # Save an assignment
            await persistence.save_assignment("worker-1", "task-1", {"name": "Test task"})
            
            # Load it back
            assignments = await persistence.load_assignments()
            assert "worker-1" in assignments
            assert assignments["worker-1"]["task_id"] == "task-1"
    
    @pytest.mark.asyncio
    async def test_assignment_file_corruption_handling(self):
        """Test handling of corrupted assignment files."""
        # This will FAIL initially
        
        from marcus_mcp_server import AssignmentPersistence
        
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = AssignmentPersistence(Path(tmpdir))
            
            # Create corrupted file
            assignment_file = Path(tmpdir) / "assignments.json"
            assignment_file.write_text("corrupted data {[[")
            
            # Should handle gracefully
            assignments = await persistence.load_assignments()
            assert assignments == {}, "Should return empty dict for corrupted data"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])