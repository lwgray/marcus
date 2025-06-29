"""
Integration tests for Marcus server components.

This module tests the integration between Marcus components including the MCP server,
AI engine, monitoring system, and communication hub.

Notes
-----
These tests use mocked external dependencies to verify component interactions
without requiring actual services to be running.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.marcus_mcp.server import MarcusServer
from src.marcus_mcp.handlers import handle_tool_call
from src.core.models import Task, TaskStatus, Priority, WorkerStatus, RiskLevel, ProjectState


class TestMarcusIntegration:
    """
    Integration tests for the Marcus Server.
    
    These tests verify that all components work together correctly,
    including MCP server request handling, AI decision making,
    monitoring state tracking, and notification delivery.
    """
    
    @pytest.fixture
    def mock_kanban_client(self):
        """Create a mock kanban client for testing."""
        client = AsyncMock()
        client.get_available_tasks = AsyncMock(return_value=[])
        client.get_all_tasks = AsyncMock(return_value=[])
        client.update_task = AsyncMock()
        client.add_comment = AsyncMock()
        client.get_board_summary = AsyncMock(return_value={
            'totalCards': 0,
            'doneCount': 0,
            'inProgressCount': 0,
            'backlogCount': 0
        })
        return client
    
    @pytest.fixture
    def mock_ai_engine(self):
        """Create a mock AI engine for testing."""
        engine = AsyncMock()
        engine.analyze_task_priority = AsyncMock(return_value=0.8)
        engine.suggest_next_action = AsyncMock(return_value="Continue with implementation")
        engine.analyze_blocker = AsyncMock(return_value={
            'severity': 'medium',
            'suggestions': ['Check dependencies', 'Review documentation']
        })
        return engine
    
    @pytest.fixture
    async def marcus_server(self, mock_kanban_client, mock_ai_engine):
        """Create a fully initialized Marcus server for integration testing."""
        with patch('src.marcus_mcp.server.KanbanFactory.create') as mock_factory:
            mock_factory.return_value = mock_kanban_client
            
            server = MarcusServer()
            server.kanban_client = mock_kanban_client
            server.ai_engine = mock_ai_engine
            server.assignment_monitor = None  # Disable for tests
            
            return server
    
    @pytest.mark.asyncio
    async def test_end_to_end_task_assignment_flow(self, marcus_server, mock_kanban_client):
        """Test complete flow: register agent -> request task -> report progress -> complete."""
        # Available tasks
        available_tasks = [
            Task(
                id="task-1",
                name="Implement login API",
                description="Create REST endpoint for user login",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                labels=["backend", "api"],
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]
        mock_kanban_client.get_available_tasks.return_value = available_tasks
        
        # Step 1: Register agent
        register_result = await handle_tool_call(
            'register_agent',
            {
                'agent_id': 'backend-dev-1',
                'name': 'Backend Developer',
                'role': 'Backend Developer',
                'skills': ['python', 'api', 'backend']
            },
            marcus_server
        )
        
        register_data = json.loads(register_result[0].text)
        assert register_data['success'] is True
        
        # Step 2: Request task
        task_result = await handle_tool_call(
            'request_next_task',
            {'agent_id': 'backend-dev-1'},
            marcus_server
        )
        
        task_data = json.loads(task_result[0].text)
        assert task_data['task'] is not None
        assert task_data['task']['id'] == 'task-1'
        
        # Step 3: Report progress
        progress_result = await handle_tool_call(
            'report_task_progress',
            {
                'agent_id': 'backend-dev-1',
                'task_id': 'task-1',
                'status': 'in_progress',
                'progress': 50,
                'message': 'Endpoint structure created'
            },
            marcus_server
        )
        
        progress_data = json.loads(progress_result[0].text)
        assert progress_data['success'] is True
        
        # Step 4: Complete task
        complete_result = await handle_tool_call(
            'report_task_progress',
            {
                'agent_id': 'backend-dev-1',
                'task_id': 'task-1',
                'status': 'completed',
                'progress': 100,
                'message': 'Login API implemented and tested'
            },
            marcus_server
        )
        
        complete_data = json.loads(complete_result[0].text)
        assert complete_data['success'] is True
        
        # Verify agent status updated
        status_result = await handle_tool_call(
            'get_agent_status',
            {'agent_id': 'backend-dev-1'},
            marcus_server
        )
        
        status_data = json.loads(status_result[0].text)
        assert status_data['status'] == 'available'
        assert status_data['current_task'] is None
        assert status_data['completed_tasks'] == 1
    
    @pytest.mark.asyncio
    async def test_multiple_agents_concurrent_requests(self, marcus_server, mock_kanban_client):
        """Test multiple agents requesting tasks concurrently."""
        # Create tasks
        tasks = [
            Task(
                id=f"task-{i}",
                name=f"Task {i}",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                labels=["test"],
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            for i in range(3)
        ]
        mock_kanban_client.get_available_tasks.return_value = tasks
        
        # Register multiple agents
        agents = ['agent-1', 'agent-2', 'agent-3']
        for agent_id in agents:
            await handle_tool_call(
                'register_agent',
                {
                    'agent_id': agent_id,
                    'name': f'Agent {agent_id}',
                    'role': 'Developer',
                    'skills': ['test']
                },
                marcus_server
            )
        
        # Concurrent task requests
        async def request_task(agent_id):
            result = await handle_tool_call(
                'request_next_task',
                {'agent_id': agent_id},
                marcus_server
            )
            return json.loads(result[0].text)
        
        results = await asyncio.gather(
            *[request_task(agent_id) for agent_id in agents]
        )
        
        # Verify each agent got a different task
        assigned_task_ids = [
            r['task']['id'] for r in results if r['task'] is not None
        ]
        assert len(assigned_task_ids) == 3
        assert len(set(assigned_task_ids)) == 3  # All unique
    
    @pytest.mark.asyncio
    async def test_blocker_reporting_and_ai_suggestions(self, marcus_server, mock_ai_engine):
        """Test blocker reporting with AI-powered suggestions."""
        # Setup agent with task
        await handle_tool_call(
            'register_agent',
            {
                'agent_id': 'test-agent',
                'name': 'Test Agent',
                'role': 'Developer',
                'skills': ['python']
            },
            marcus_server
        )
        
        # Manually assign a task
        marcus_server.agent_tasks['test-agent'] = Mock(
            task_id='task-1',
            agent_id='test-agent',
            assigned_at=datetime.now(),
            status='in_progress'
        )
        
        # Report blocker
        blocker_result = await handle_tool_call(
            'report_blocker',
            {
                'agent_id': 'test-agent',
                'task_id': 'task-1',
                'blocker_description': 'Database connection failing',
                'severity': 'high'
            },
            marcus_server
        )
        
        blocker_data = json.loads(blocker_result[0].text)
        assert blocker_data['success'] is True
        assert 'suggestions' in blocker_data
        assert len(blocker_data['suggestions']) > 0
        
        # Verify AI engine was called
        mock_ai_engine.analyze_blocker.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_project_monitoring_integration(self, marcus_server, mock_kanban_client):
        """Test project status monitoring across multiple operations."""
        # Setup initial board state
        mock_kanban_client.get_all_tasks.return_value = [
            Task(id="1", name="Task 1", status=TaskStatus.DONE,
                 priority=Priority.HIGH, labels=[], assigned_to=None,
                 created_at=datetime.now(), updated_at=datetime.now()),
            Task(id="2", name="Task 2", status=TaskStatus.IN_PROGRESS,
                 priority=Priority.MEDIUM, labels=[], assigned_to="agent-1",
                 created_at=datetime.now(), updated_at=datetime.now()),
            Task(id="3", name="Task 3", status=TaskStatus.TODO,
                 priority=Priority.LOW, labels=[], assigned_to=None,
                 created_at=datetime.now(), updated_at=datetime.now())
        ]
        
        mock_kanban_client.get_board_summary.return_value = {
            'totalCards': 3,
            'doneCount': 1,
            'inProgressCount': 1,
            'backlogCount': 1
        }
        
        # Get initial project status
        status_result = await handle_tool_call(
            'get_project_status',
            {},
            marcus_server
        )
        
        status_data = json.loads(status_result[0].text)
        assert status_data['total_tasks'] == 3
        assert status_data['completed_tasks'] == 1
        assert status_data['in_progress_tasks'] == 1
        assert status_data['completion_percentage'] == pytest.approx(33.33, rel=1e-1)
        
        # Simulate task completion
        mock_kanban_client.get_all_tasks.return_value = [
            Task(id="1", name="Task 1", status=TaskStatus.DONE,
                 priority=Priority.HIGH, labels=[], assigned_to=None,
                 created_at=datetime.now(), updated_at=datetime.now()),
            Task(id="2", name="Task 2", status=TaskStatus.DONE,
                 priority=Priority.MEDIUM, labels=[], assigned_to=None,
                 created_at=datetime.now(), updated_at=datetime.now()),
            Task(id="3", name="Task 3", status=TaskStatus.IN_PROGRESS,
                 priority=Priority.LOW, labels=[], assigned_to="agent-2",
                 created_at=datetime.now(), updated_at=datetime.now())
        ]
        
        mock_kanban_client.get_board_summary.return_value = {
            'totalCards': 3,
            'doneCount': 2,
            'inProgressCount': 1,
            'backlogCount': 0
        }
        
        # Get updated status
        status_result2 = await handle_tool_call(
            'get_project_status',
            {},
            marcus_server
        )
        
        status_data2 = json.loads(status_result2[0].text)
        assert status_data2['completed_tasks'] == 2
        assert status_data2['completion_percentage'] == pytest.approx(66.67, rel=1e-1)
    
    @pytest.mark.asyncio
    async def test_health_check_integration(self, marcus_server):
        """Test system health check functionality."""
        # Perform health check
        health_result = await handle_tool_call(
            'ping',
            {'echo': 'integration-test'},
            marcus_server
        )
        
        health_data = json.loads(health_result[0].text)
        assert health_data['status'] == 'healthy'
        assert health_data['echo'] == 'integration-test'
        assert health_data['kanban_connected'] is True
        assert 'timestamp' in health_data
    
    @pytest.mark.asyncio
    async def test_assignment_tracking_persistence(self, marcus_server, mock_kanban_client):
        """Test that assignments are properly tracked and persisted."""
        # Setup
        task = Task(
            id="persist-task",
            name="Test Persistence",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["test"],
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_kanban_client.get_available_tasks.return_value = [task]
        
        # Register agent and request task
        await handle_tool_call(
            'register_agent',
            {
                'agent_id': 'persist-agent',
                'name': 'Persistence Test Agent',
                'role': 'Tester',
                'skills': ['test']
            },
            marcus_server
        )
        
        # Request task
        task_result = await handle_tool_call(
            'request_next_task',
            {'agent_id': 'persist-agent'},
            marcus_server
        )
        
        task_data = json.loads(task_result[0].text)
        assert task_data['task']['id'] == 'persist-task'
        
        # Check assignment health
        health_result = await handle_tool_call(
            'check_assignment_health',
            {},
            marcus_server
        )
        
        health_data = json.loads(health_result[0].text)
        assert health_data['healthy'] is True
        assert health_data['active_assignments'] == 1
        assert health_data['orphaned_tasks'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])