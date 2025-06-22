"""
Unit tests for PM Agent MCP Server v2
"""

import pytest
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock, mock_open
from typing import List, Dict, Any

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pm_agent_mcp_server_v2 as pm_server
from pm_agent_mcp_server_v2 import (
    PMAgentState, 
    register_agent, 
    request_next_task,
    report_task_progress,
    report_blocker,
    get_project_status,
    get_agent_status,
    list_registered_agents,
    ping,
    refresh_project_state,
    find_optimal_task_for_agent,
    handle_list_tools,
    handle_call_tool
)

from src.core.models import (
    Task, TaskStatus, Priority, RiskLevel,
    ProjectState, WorkerStatus, TaskAssignment
)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up test environment variables"""
    monkeypatch.setenv('KANBAN_PROVIDER', 'planka')
    monkeypatch.setenv('GITHUB_OWNER', 'test-owner')
    monkeypatch.setenv('GITHUB_REPO', 'test-repo')


@pytest.fixture
def mock_kanban_client():
    """Mock kanban client"""
    client = AsyncMock()
    client.connect = AsyncMock()
    client.get_available_tasks = AsyncMock(return_value=[])
    client.update_task = AsyncMock()
    client.update_task_progress = AsyncMock()
    client.get_task_by_id = AsyncMock()
    client.add_comment = AsyncMock()
    return client


@pytest.fixture
def mock_ai_engine():
    """Mock AI analysis engine"""
    engine = AsyncMock()
    engine.generate_task_instructions = AsyncMock(return_value="Test instructions")
    engine.analyze_blocker = AsyncMock(return_value="Test suggestions")
    return engine


@pytest.fixture
def mock_code_analyzer():
    """Mock code analyzer"""
    analyzer = AsyncMock()
    analyzer.get_implementation_details = AsyncMock(return_value=None)
    analyzer.analyze_task_completion = AsyncMock(return_value=None)
    return analyzer


@pytest.fixture
def sample_task():
    """Create a sample task"""
    return Task(
        id="task-123",
        name="Test Task",
        description="Test Description",
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        labels=["backend", "api"],
        estimated_hours=4.0,
        dependencies=[],
        due_date=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        assigned_to=None,
        actual_hours=0.0
    )


@pytest.fixture
def sample_worker():
    """Create a sample worker status"""
    return WorkerStatus(
        worker_id="agent-1",
        name="Test Agent",
        role="Backend Developer",
        email=None,
        current_tasks=[],
        completed_tasks_count=0,
        capacity=40,
        skills=["python", "backend", "api"],
        availability={
            "monday": True,
            "tuesday": True,
            "wednesday": True,
            "thursday": True,
            "friday": True,
            "saturday": False,
            "sunday": False
        },
        performance_score=1.0
    )


class TestPMAgentState:
    """Test PMAgentState class"""
    
    @patch('pm_agent_mcp_server_v2.load_dotenv')
    @patch('pm_agent_mcp_server_v2.Settings')
    @patch('pm_agent_mcp_server_v2.AIAnalysisEngine')
    @patch('pm_agent_mcp_server_v2.ProjectMonitor')
    @patch('pm_agent_mcp_server_v2.CommunicationHub')
    @patch('builtins.open', new_callable=mock_open)
    def test_init(self, mock_file, mock_comm, mock_monitor, mock_ai, mock_settings, mock_dotenv, mock_env_vars):
        """Test PMAgentState initialization"""
        # Create instance
        state = PMAgentState()
        
        # Verify initialization
        assert state.provider == 'planka'
        assert state.kanban_client is None
        assert state.agent_tasks == {}
        assert state.agent_status == {}
        assert state.project_state is None
        assert state.project_tasks == []
        
        # Verify components were created
        mock_ai.assert_called_once()
        mock_monitor.assert_called_once()
        mock_comm.assert_called_once()
        
        # Verify log file was opened
        mock_file.assert_called()
        
    @patch('pm_agent_mcp_server_v2.KanbanFactory')
    async def test_initialize_kanban(self, mock_factory, mock_env_vars):
        """Test kanban initialization"""
        # Mock factory
        mock_client = AsyncMock()
        mock_factory.create_default.return_value = mock_client
        
        # Create state
        with patch('builtins.open', mock_open()):
            state = PMAgentState()
        
        # Initialize kanban
        await state.initialize_kanban()
        
        # Verify
        assert state.kanban_client == mock_client
        mock_client.connect.assert_called_once()
        
    def test_log_event(self, mock_env_vars):
        """Test event logging"""
        # Create state with mocked file
        mock_file = MagicMock()
        with patch('builtins.open', return_value=mock_file):
            state = PMAgentState()
        
        # Log event
        state.log_event("test_event", {"data": "test"})
        
        # Verify write was called
        mock_file.write.assert_called()
        written_data = mock_file.write.call_args[0][0]
        assert "test_event" in written_data
        assert "data" in written_data


class TestToolRegistration:
    """Test tool registration"""
    
    async def test_handle_list_tools(self):
        """Test tool list handler"""
        tools = await handle_list_tools()
        
        # Verify all tools are registered
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "register_agent",
            "request_next_task",
            "report_task_progress",
            "report_blocker",
            "get_project_status",
            "get_agent_status",
            "list_registered_agents",
            "ping"
        ]
        
        for expected in expected_tools:
            assert expected in tool_names
            
        # Verify tool structure
        for tool in tools:
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'inputSchema')
            assert tool.inputSchema['type'] == 'object'
            assert 'properties' in tool.inputSchema
            assert 'required' in tool.inputSchema


class TestToolCallHandler:
    """Test tool call handler"""
    
    @patch('pm_agent_mcp_server_v2.register_agent')
    async def test_handle_call_tool_register_agent(self, mock_register):
        """Test calling register_agent tool"""
        mock_register.return_value = {"success": True}
        
        result = await handle_call_tool("register_agent", {
            "agent_id": "test-agent",
            "name": "Test Agent",
            "role": "Developer",
            "skills": ["python"]
        })
        
        # Verify
        assert len(result) == 1
        assert result[0].type == "text"
        assert "success" in result[0].text
        mock_register.assert_called_once_with("test-agent", "Test Agent", "Developer", ["python"])
        
    async def test_handle_call_tool_unknown(self):
        """Test calling unknown tool"""
        result = await handle_call_tool("unknown_tool", {})
        
        assert len(result) == 1
        assert "error" in result[0].text
        assert "Unknown tool" in result[0].text
        
    async def test_handle_call_tool_exception(self):
        """Test exception handling in tool calls"""
        with patch('pm_agent_mcp_server_v2.ping', side_effect=Exception("Test error")):
            result = await handle_call_tool("ping", {})
            
            assert len(result) == 1
            assert "error" in result[0].text
            assert "Test error" in result[0].text


class TestRegisterAgent:
    """Test agent registration"""
    
    @patch('pm_agent_mcp_server_v2.state')
    @patch('pm_agent_mcp_server_v2.conversation_logger')
    async def test_register_agent_success(self, mock_logger, mock_state):
        """Test successful agent registration"""
        mock_state.agent_status = {}
        mock_state.log_event = Mock()
        
        result = await register_agent("agent-1", "Test Agent", "Developer", ["python"])
        
        # Verify result
        assert result['success'] is True
        assert "registered successfully" in result['message']
        assert result['agent_id'] == "agent-1"
        
        # Verify agent was added
        assert "agent-1" in mock_state.agent_status
        agent = mock_state.agent_status["agent-1"]
        assert agent.name == "Test Agent"
        assert agent.role == "Developer"
        assert agent.skills == ["python"]
        
        # Verify logging
        mock_state.log_event.assert_called()
        mock_logger.log_worker_message.assert_called()
        mock_logger.log_pm_decision.assert_called()
        
    @patch('pm_agent_mcp_server_v2.state')
    @patch('pm_agent_mcp_server_v2.conversation_logger')
    async def test_register_agent_exception(self, mock_logger, mock_state):
        """Test agent registration with exception"""
        mock_state.agent_status = None  # Force AttributeError
        
        result = await register_agent("agent-1", "Test Agent", "Developer", [])
        
        assert result['success'] is False
        assert 'error' in result


class TestRequestNextTask:
    """Test task request functionality"""
    
    @patch('pm_agent_mcp_server_v2.state')
    @patch('pm_agent_mcp_server_v2.refresh_project_state')
    @patch('pm_agent_mcp_server_v2.find_optimal_task_for_agent')
    @patch('pm_agent_mcp_server_v2.conversation_logger')
    async def test_request_next_task_success(self, mock_logger, mock_find_task, 
                                           mock_refresh, mock_state, sample_task, sample_worker):
        """Test successful task request"""
        # Setup mocks
        mock_state.agent_status = {"agent-1": sample_worker}
        mock_state.agent_tasks = {}
        mock_state.ai_engine = AsyncMock()
        mock_state.ai_engine.generate_task_instructions.return_value = "Do the task"
        mock_state.kanban_client = AsyncMock()
        mock_state.initialize_kanban = AsyncMock()  # Fix the await issue
        mock_state.provider = 'planka'
        mock_state.log_event = Mock()
        mock_find_task.return_value = sample_task
        
        result = await request_next_task("agent-1")
        
        # Verify result
        assert result['success'] is True
        assert result['task']['id'] == sample_task.id
        assert result['task']['name'] == sample_task.name
        assert result['task']['instructions'] == "Do the task"
        
        # Verify assignment was tracked
        assert "agent-1" in mock_state.agent_tasks
        assignment = mock_state.agent_tasks["agent-1"]
        assert assignment.task_id == sample_task.id
        
        # Verify kanban update
        mock_state.kanban_client.update_task.assert_called_once()
        
    @patch('pm_agent_mcp_server_v2.state')
    @patch('pm_agent_mcp_server_v2.refresh_project_state')
    @patch('pm_agent_mcp_server_v2.find_optimal_task_for_agent')
    @patch('pm_agent_mcp_server_v2.conversation_logger')
    async def test_request_next_task_no_tasks(self, mock_logger, mock_find_task, mock_refresh, mock_state, sample_worker):
        """Test task request when no tasks available"""
        mock_state.agent_status = {"agent-1": sample_worker}
        mock_state.log_event = Mock()
        mock_state.initialize_kanban = AsyncMock()
        mock_find_task.return_value = None
        
        result = await request_next_task("agent-1")
        
        assert result['success'] is False
        assert "No suitable tasks" in result.get('message', '')


class TestReportTaskProgress:
    """Test task progress reporting"""
    
    @patch('pm_agent_mcp_server_v2.state')
    @patch('pm_agent_mcp_server_v2.refresh_project_state')
    @patch('pm_agent_mcp_server_v2.conversation_logger')
    async def test_report_progress_completed(self, mock_logger, mock_refresh, mock_state, sample_worker):
        """Test reporting task completion"""
        # Setup mocks
        mock_state.kanban_client = AsyncMock()
        mock_state.agent_status = {"agent-1": sample_worker}
        mock_state.agent_tasks = {"agent-1": Mock()}
        mock_state.provider = 'planka'
        mock_state.initialize_kanban = AsyncMock()
        
        result = await report_task_progress("agent-1", "task-123", "completed", 100, "Task done")
        
        # Verify result
        assert result['success'] is True
        
        # Verify kanban updates
        calls = mock_state.kanban_client.update_task.call_args_list
        assert len(calls) == 1
        assert calls[0][0][1]['status'] == TaskStatus.DONE
        assert 'completed_at' in calls[0][0][1]
        
        # Verify agent state updated
        assert sample_worker.current_tasks == []
        assert sample_worker.completed_tasks_count == 1
        assert "agent-1" not in mock_state.agent_tasks
        
    @patch('pm_agent_mcp_server_v2.state')
    @patch('pm_agent_mcp_server_v2.refresh_project_state')
    @patch('pm_agent_mcp_server_v2.conversation_logger')
    async def test_report_progress_blocked(self, mock_logger, mock_refresh, mock_state):
        """Test reporting blocked status"""
        mock_state.kanban_client = AsyncMock()
        mock_state.initialize_kanban = AsyncMock()
        
        result = await report_task_progress("agent-1", "task-123", "blocked", 50, "Blocked")
        
        assert result['success'] is True
        mock_state.kanban_client.update_task.assert_called()
        update_data = mock_state.kanban_client.update_task.call_args[0][1]
        assert update_data['status'] == TaskStatus.BLOCKED


class TestReportBlocker:
    """Test blocker reporting"""
    
    @patch('pm_agent_mcp_server_v2.state')
    @patch('pm_agent_mcp_server_v2.conversation_logger')
    async def test_report_blocker_success(self, mock_logger, mock_state, sample_task, sample_worker):
        """Test successful blocker report"""
        # Setup mocks
        mock_state.kanban_client = AsyncMock()
        mock_state.kanban_client.get_task_by_id.return_value = sample_task
        mock_state.agent_status = {"agent-1": sample_worker}
        mock_state.ai_engine = AsyncMock()
        mock_state.ai_engine.analyze_blocker.return_value = "Try this solution"
        mock_state.initialize_kanban = AsyncMock()
        
        result = await report_blocker("agent-1", "task-123", "Cannot connect to DB", "high")
        
        # Verify result
        assert result['success'] is True
        assert result['suggestions'] == "Try this solution"
        
        # Verify task updated
        mock_state.kanban_client.update_task.assert_called_once()
        update_data = mock_state.kanban_client.update_task.call_args[0][1]
        assert update_data['status'] == TaskStatus.BLOCKED
        assert update_data['blocker'] == "Cannot connect to DB"
        
        # Verify comment added
        mock_state.kanban_client.add_comment.assert_called_once()


class TestProjectStatus:
    """Test project status functionality"""
    
    @patch('pm_agent_mcp_server_v2.state')
    @patch('pm_agent_mcp_server_v2.refresh_project_state')
    async def test_get_project_status_success(self, mock_refresh, mock_state, sample_task):
        """Test getting project status"""
        # Setup state
        completed_task = Task(**sample_task.__dict__)
        completed_task.status = TaskStatus.DONE
        blocked_task = Task(**sample_task.__dict__)
        blocked_task.status = TaskStatus.BLOCKED
        
        mock_state.project_state = Mock()
        mock_state.project_tasks = [sample_task, completed_task, blocked_task]
        mock_state.agent_status = {
            "agent-1": Mock(current_tasks=[sample_task]),
            "agent-2": Mock(current_tasks=[])
        }
        mock_state.provider = 'planka'
        mock_state.initialize_kanban = AsyncMock()
        
        result = await get_project_status()
        
        # Verify result
        assert result['success'] is True
        assert result['project']['total_tasks'] == 3
        assert result['project']['completed'] == 1
        assert result['project']['in_progress'] == 0
        assert result['project']['blocked'] == 1
        assert result['workers']['total'] == 2
        assert result['workers']['active'] == 1
        assert result['workers']['available'] == 1


class TestAgentStatus:
    """Test agent status functionality"""
    
    @patch('pm_agent_mcp_server_v2.state')
    async def test_get_agent_status_exists(self, mock_state, sample_worker, sample_task):
        """Test getting status for existing agent"""
        sample_worker.current_tasks = [sample_task]
        mock_state.agent_status = {"agent-1": sample_worker}
        mock_state.agent_tasks = {
            "agent-1": TaskAssignment(
                task_id=sample_task.id,
                task_name=sample_task.name,
                description=sample_task.description,
                instructions="Do it",
                estimated_hours=4,
                priority=Priority.HIGH,
                dependencies=[],
                assigned_to="agent-1",
                assigned_at=datetime.now(),
                due_date=None
            )
        }
        
        result = await get_agent_status("agent-1")
        
        assert result['success'] is True
        assert result['agent']['id'] == "agent-1"
        assert result['agent']['status'] == "working"
        assert len(result['agent']['current_tasks']) == 1
        assert 'current_assignment' in result
        
    @patch('pm_agent_mcp_server_v2.state')
    async def test_get_agent_status_not_found(self, mock_state):
        """Test getting status for non-existent agent"""
        mock_state.agent_status = {}
        
        result = await get_agent_status("agent-999")
        
        assert result['success'] is False
        assert "not found" in result['message']


class TestListAgents:
    """Test listing agents"""
    
    @patch('pm_agent_mcp_server_v2.state')
    async def test_list_registered_agents(self, mock_state, sample_worker):
        """Test listing all registered agents"""
        mock_state.agent_status = {
            "agent-1": sample_worker,
            "agent-2": WorkerStatus(
                worker_id="agent-2",
                name="Agent 2",
                role="Frontend Developer",
                email=None,
                current_tasks=[],
                completed_tasks_count=5,
                capacity=40,
                skills=["javascript"],
                availability={},
                performance_score=0.9
            )
        }
        
        result = await list_registered_agents()
        
        assert result['success'] is True
        assert result['total'] == 2
        assert len(result['agents']) == 2
        
        # Check agent data
        agent1 = next(a for a in result['agents'] if a['id'] == 'agent-1')
        assert agent1['name'] == "Test Agent"
        assert agent1['status'] == "available"


class TestPing:
    """Test ping functionality"""
    
    @patch('pm_agent_mcp_server_v2.state')
    @patch('pm_agent_mcp_server_v2.conversation_logger')
    async def test_ping_with_echo(self, mock_logger, mock_state):
        """Test ping with echo message"""
        mock_state.log_event = Mock()
        mock_state.provider = 'planka'
        
        result = await ping("hello")
        
        assert result['success'] is True
        assert result['status'] == "online"
        assert result['echo'] == "hello"
        assert result['provider'] == 'planka'
        assert 'timestamp' in result
        
        # Verify logging
        assert mock_state.log_event.call_count == 2  # request and response
        
    @patch('pm_agent_mcp_server_v2.state')
    async def test_ping_without_echo(self, mock_state):
        """Test ping without echo message"""
        mock_state.log_event = Mock()
        mock_state.provider = 'github'
        
        result = await ping("")
        
        assert result['echo'] == "pong"


class TestHelperFunctions:
    """Test helper functions"""
    
    @patch('pm_agent_mcp_server_v2.state')
    @patch('pm_agent_mcp_server_v2.conversation_logger')
    async def test_refresh_project_state(self, mock_logger, mock_state, sample_task):
        """Test refreshing project state"""
        # Setup mocks
        mock_state.kanban_client = AsyncMock()
        mock_state.kanban_client.get_available_tasks.return_value = [sample_task]
        mock_state.log_event = Mock()
        
        await refresh_project_state()
        
        # Verify state updated
        assert mock_state.project_tasks == [sample_task]
        assert mock_state.project_state is not None
        assert mock_state.project_state.total_tasks == 1
        assert mock_state.project_state.completed_tasks == 0
        
        # Verify logging
        mock_state.log_event.assert_called()
        mock_logger.log_system_state.assert_called_once()
        
    @patch('pm_agent_mcp_server_v2.state')
    async def test_find_optimal_task_no_agent(self, mock_state):
        """Test finding task when agent doesn't exist"""
        mock_state.agent_status = {}
        
        result = await find_optimal_task_for_agent("agent-999")
        
        assert result is None
        
    @patch('pm_agent_mcp_server_v2.state')
    async def test_find_optimal_task_with_skills(self, mock_state, sample_worker, sample_task):
        """Test finding optimal task based on skills"""
        # Setup
        mock_state.agent_status = {"agent-1": sample_worker}
        mock_state.project_state = Mock()
        mock_state.project_tasks = [sample_task]
        mock_state.agent_tasks = {}
        mock_state.log_event = Mock()
        
        result = await find_optimal_task_for_agent("agent-1")
        
        assert result == sample_task
        
    @patch('pm_agent_mcp_server_v2.state')
    async def test_find_optimal_task_already_assigned(self, mock_state, sample_worker, sample_task):
        """Test finding task when all tasks are assigned"""
        mock_state.agent_status = {"agent-1": sample_worker}
        mock_state.project_state = Mock()
        mock_state.project_tasks = [sample_task]
        mock_state.agent_tasks = {"agent-2": Mock(task_id=sample_task.id)}
        mock_state.log_event = Mock()
        
        result = await find_optimal_task_for_agent("agent-1")
        
        assert result is None


class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.asyncio
    async def test_full_agent_workflow(self, mock_env_vars):
        """Test complete agent workflow from registration to task completion"""
        with patch('builtins.open', mock_open()):
            # Create fresh state
            test_state = PMAgentState()
            
            # Mock dependencies
            test_state.kanban_client = AsyncMock()
            test_state.ai_engine = AsyncMock()
            test_state.ai_engine.generate_task_instructions.return_value = "Test instructions"
            
            # Create test task
            test_task = Task(
                id="task-1",
                name="Test Task",
                description="Test",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                labels=["python"],
                estimated_hours=4,
                dependencies=[],
                due_date=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                assigned_to=None,
                actual_hours=0.0
            )
            
            test_state.kanban_client.get_available_tasks.return_value = [test_task]
            
            with patch('pm_agent_mcp_server_v2.state', test_state):
                # 1. Register agent
                reg_result = await register_agent("test-agent", "Test Agent", "Developer", ["python"])
                assert reg_result['success'] is True
                
                # 2. Request task
                task_result = await request_next_task("test-agent")
                assert task_result['success'] is True
                assert task_result['task']['id'] == "task-1"
                
                # 3. Report progress
                progress_result = await report_task_progress("test-agent", "task-1", "in_progress", 50, "Half done")
                assert progress_result['success'] is True
                
                # 4. Complete task
                complete_result = await report_task_progress("test-agent", "task-1", "completed", 100, "All done")
                assert complete_result['success'] is True
                
                # 5. Verify agent is available again
                status_result = await get_agent_status("test-agent")
                assert status_result['success'] is True
                assert status_result['agent']['status'] == "available"


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])