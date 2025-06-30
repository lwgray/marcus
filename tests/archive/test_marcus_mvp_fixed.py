"""
Unit tests for MarcusMVP - the MCP server implementation
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock, PropertyMock
from datetime import datetime, timedelta
from typing import Dict, Any, List

from src.marcus_mvp_fixed import MarcusMVP
from src.core.models import (
    Task, TaskStatus, Priority, RiskLevel,
    ProjectState, WorkerStatus, TaskAssignment
)
from mcp.types import TextContent


class TestMarcusMVP:
    """Test suite for MarcusMVP class"""
    
    @pytest.fixture
    def mock_kanban_client(self):
        """Mock MCPKanbanClient"""
        client = AsyncMock()
        client.board_id = "test-board-id"
        client.project_id = "test-project-id"
        return client
    
    @pytest.fixture
    def mock_ai_engine(self):
        """Mock AIAnalysisEngine"""
        engine = AsyncMock()
        engine._call_claude = AsyncMock(return_value="AI generated instructions")
        return engine
    
    @pytest.fixture
    def mock_workspace_manager(self):
        """Mock WorkspaceManager"""
        manager = Mock()
        manager.get_task_assignment_data = Mock(return_value={
            'workspace_path': '/workspace/agent-001',
            'forbidden_paths': ['/workspace/agent-002', '/workspace/agent-003']
        })
        return manager
    
    @pytest.fixture
    async def pm_agent(self, mock_kanban_client, mock_ai_engine, mock_workspace_manager):
        """Create MarcusMVP instance with mocked dependencies"""
        agent = MarcusMVP()
        agent.kanban_client = mock_kanban_client
        agent.ai_engine = mock_ai_engine
        agent.workspace_manager = mock_workspace_manager
        return agent
    
    @pytest.fixture
    def sample_task(self):
        """Create a sample task for testing"""
        return Task(
            id="TASK-001",
            name="Implement user authentication",
            description="Add login functionality with JWT tokens",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=3),
            estimated_hours=8.0,
            labels=["backend", "security"],
            dependencies=[]
        )
    
    @pytest.fixture
    def sample_tasks(self):
        """Create multiple sample tasks for testing"""
        now = datetime.now()
        return [
            Task(
                id="TASK-001",
                name="Urgent security fix",
                description="Fix authentication vulnerability",
                status=TaskStatus.TODO,
                priority=Priority.URGENT,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=now + timedelta(hours=24),
                estimated_hours=4.0
            ),
            Task(
                id="TASK-002",
                name="Add user profile",
                description="Implement user profile management",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=now + timedelta(days=7),
                estimated_hours=12.0
            ),
            Task(
                id="TASK-003",
                name="Database optimization",
                description="Optimize database queries",
                status=TaskStatus.TODO,
                priority=Priority.LOW,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=now + timedelta(days=14),
                estimated_hours=16.0
            )
        ]


class TestAgentRegistration(TestMarcusMVP):
    """Test agent registration functionality"""
    
    async def test_register_agent_success(self, pm_agent):
        """Test successful agent registration"""
        result = await pm_agent._register_agent(
            agent_id="agent-001",
            name="Test Agent",
            role="Backend Developer",
            skills=["Python", "Django"]
        )
        
        assert result["success"] is True
        assert "agent-001" in pm_agent.agent_status
        assert pm_agent.agent_status["agent-001"].name == "Test Agent"
        assert pm_agent.agent_status["agent-001"].role == "Backend Developer"
        assert pm_agent.agent_status["agent-001"].skills == ["Python", "Django"]
        assert pm_agent.agent_status["agent-001"].capacity == 40
    
    async def test_register_agent_missing_required_fields(self, pm_agent):
        """Test agent registration with missing required fields"""
        result = await pm_agent._register_agent(
            agent_id="",
            name="Test Agent",
            role="Developer",
            skills=[]
        )
        
        assert result["success"] is False
        assert "required" in result["error"]
        assert "agent-001" not in pm_agent.agent_status
    
    async def test_register_agent_with_none_skills(self, pm_agent):
        """Test agent registration with None skills defaults to empty list"""
        result = await pm_agent._register_agent(
            agent_id="agent-001",
            name="Test Agent",
            role="Developer",
            skills=None
        )
        
        assert result["success"] is True
        assert pm_agent.agent_status["agent-001"].skills == []
    
    async def test_register_agent_duplicate(self, pm_agent):
        """Test registering the same agent twice overwrites the first"""
        # First registration
        await pm_agent._register_agent(
            agent_id="agent-001",
            name="Original Agent",
            role="Developer",
            skills=["Python"]
        )
        
        # Second registration with same ID
        result = await pm_agent._register_agent(
            agent_id="agent-001",
            name="Updated Agent",
            role="Senior Developer",
            skills=["Python", "Go"]
        )
        
        assert result["success"] is True
        assert pm_agent.agent_status["agent-001"].name == "Updated Agent"
        assert pm_agent.agent_status["agent-001"].role == "Senior Developer"
        assert len(pm_agent.agent_status) == 1
    
    async def test_register_agent_default_values(self, pm_agent):
        """Test agent registration sets proper default values"""
        result = await pm_agent._register_agent(
            agent_id="agent-001",
            name="Test Agent",
            role="Developer",
            skills=[]
        )
        
        agent = pm_agent.agent_status["agent-001"]
        assert agent.email == "agent-001@company.com"
        assert agent.current_tasks == []
        assert agent.completed_tasks_count == 0
        assert agent.capacity == 40
        assert agent.performance_score == 1.0
        assert agent.availability == {
            "monday": True, "tuesday": True, "wednesday": True,
            "thursday": True, "friday": True
        }


class TestTaskAssignment(TestMarcusMVP):
    """Test task assignment functionality"""
    
    async def test_request_task_unregistered_agent(self, pm_agent):
        """Test requesting task with unregistered agent"""
        result = await pm_agent._request_next_task("unknown-agent")
        
        assert result["has_task"] is False
        assert "not registered" in result["error"]
    
    async def test_request_task_no_available_tasks(self, pm_agent, mock_kanban_client):
        """Test requesting task when no tasks are available"""
        # Register agent first
        await pm_agent._register_agent("agent-001", "Test Agent", "Developer", [])
        
        # Mock empty task list
        mock_kanban_client.get_available_tasks.return_value = []
        
        result = await pm_agent._request_next_task("agent-001")
        
        assert result["has_task"] is False
        assert "No tasks available" in result["message"]
        mock_kanban_client.get_available_tasks.assert_called_once()
    
    async def test_request_task_assigns_highest_priority(self, pm_agent, mock_kanban_client, sample_tasks):
        """Test that highest priority task is assigned"""
        # Register agent
        await pm_agent._register_agent("agent-001", "Test Agent", "Developer", [])
        
        # Mock available tasks
        mock_kanban_client.get_available_tasks.return_value = sample_tasks
        
        result = await pm_agent._request_next_task("agent-001")
        
        assert result["has_task"] is True
        assert result["assignment"]["task_id"] == "TASK-001"  # Urgent priority task
        assert result["assignment"]["priority"] == "urgent"
        assert "agent-001" in pm_agent.agent_tasks
        mock_kanban_client.assign_task.assert_called_once_with("TASK-001", "agent-001")
    
    async def test_request_task_creates_proper_assignment(self, pm_agent, mock_kanban_client, sample_task):
        """Test that task assignment is properly created"""
        # Register agent
        await pm_agent._register_agent("agent-001", "Test Agent", "Developer", [])
        
        # Mock available tasks
        mock_kanban_client.get_available_tasks.return_value = [sample_task]
        
        result = await pm_agent._request_next_task("agent-001")
        
        assignment = pm_agent.agent_tasks["agent-001"]
        assert assignment.task_id == sample_task.id
        assert assignment.task_name == sample_task.name
        assert assignment.description == sample_task.description
        assert assignment.priority == sample_task.priority
        assert assignment.estimated_hours == sample_task.estimated_hours
        assert assignment.assigned_to == "agent-001"
        assert assignment.workspace_path == "/workspace/agent-001"
        assert assignment.forbidden_paths == ["/workspace/agent-002", "/workspace/agent-003"]
    
    async def test_request_task_generates_ai_instructions(self, pm_agent, mock_kanban_client, mock_ai_engine, sample_task):
        """Test that AI instructions are generated for tasks"""
        # Register agent
        await pm_agent._register_agent("agent-001", "Test Agent", "Developer", [])
        
        # Mock available tasks
        mock_kanban_client.get_available_tasks.return_value = [sample_task]
        
        result = await pm_agent._request_next_task("agent-001")
        
        assert result["assignment"]["instructions"] == "AI generated instructions"
        mock_ai_engine._call_claude.assert_called_once()
        
        # Check the prompt contains task details
        call_args = mock_ai_engine._call_claude.call_args[0][0]
        assert sample_task.name in call_args
        assert sample_task.description in call_args
        assert sample_task.priority.value in call_args
    
    async def test_request_task_handles_error(self, pm_agent, mock_kanban_client):
        """Test error handling in task request"""
        # Register agent
        await pm_agent._register_agent("agent-001", "Test Agent", "Developer", [])
        
        # Mock error
        mock_kanban_client.get_available_tasks.side_effect = Exception("Connection error")
        
        result = await pm_agent._request_next_task("agent-001")
        
        assert result["has_task"] is False
        assert "Connection error" in result["error"]


class TestProgressReporting(TestMarcusMVP):
    """Test progress reporting functionality"""
    
    async def test_report_progress_in_progress(self, pm_agent, mock_kanban_client):
        """Test reporting in-progress status"""
        result = await pm_agent._report_task_progress(
            agent_id="agent-001",
            task_id="TASK-001",
            status="in_progress",
            progress=50,
            message="Halfway done"
        )
        
        assert result["acknowledged"] is True
        assert result["status"] == "progress_recorded"
        
        # Verify comment was added
        mock_kanban_client.add_comment.assert_called_once()
        comment = mock_kanban_client.add_comment.call_args[0][1]
        assert "agent-001" in comment
        assert "Halfway done" in comment
        assert "50% complete" in comment
    
    async def test_report_progress_completed(self, pm_agent, mock_kanban_client):
        """Test reporting completed status"""
        # Setup agent with task
        pm_agent.agent_status["agent-001"] = WorkerStatus(
            worker_id="agent-001",
            name="Test Agent",
            role="Developer",
            email="test@example.com",
            current_tasks=[],
            completed_tasks_count=0,
            capacity=40,
            skills=[],
            availability={},
            performance_score=1.0
        )
        pm_agent.agent_tasks["agent-001"] = Mock()
        
        result = await pm_agent._report_task_progress(
            agent_id="agent-001",
            task_id="TASK-001",
            status="completed",
            progress=100,
            message="Task completed successfully"
        )
        
        assert result["acknowledged"] is True
        
        # Verify task was completed and agent freed
        mock_kanban_client.complete_task.assert_called_once_with("TASK-001")
        assert "agent-001" not in pm_agent.agent_tasks
        assert pm_agent.agent_status["agent-001"].completed_tasks_count == 1
    
    async def test_report_progress_blocked(self, pm_agent, mock_kanban_client):
        """Test reporting blocked status"""
        result = await pm_agent._report_task_progress(
            agent_id="agent-001",
            task_id="TASK-001",
            status="blocked",
            progress=30,
            message="Waiting for API access"
        )
        
        assert result["acknowledged"] is True
        mock_kanban_client.update_task_status.assert_called_once_with("TASK-001", "blocked")
    
    async def test_report_progress_handles_error(self, pm_agent, mock_kanban_client):
        """Test error handling in progress reporting"""
        mock_kanban_client.add_comment.side_effect = Exception("Network error")
        
        result = await pm_agent._report_task_progress(
            agent_id="agent-001",
            task_id="TASK-001",
            status="in_progress",
            progress=25,
            message="Starting work"
        )
        
        assert result["acknowledged"] is False
        assert "Network error" in result["error"]


class TestBlockerReporting(TestMarcusMVP):
    """Test blocker reporting functionality"""
    
    async def test_report_blocker_success(self, pm_agent, mock_kanban_client):
        """Test successful blocker reporting"""
        result = await pm_agent._report_blocker(
            agent_id="agent-001",
            task_id="TASK-001",
            blocker_description="Database connection refused",
            severity="high"
        )
        
        assert result["success"] is True
        assert "resolution_suggestion" in result
        
        # Verify comment and status update
        mock_kanban_client.add_comment.assert_called_once()
        comment = mock_kanban_client.add_comment.call_args[0][1]
        assert "BLOCKER" in comment
        assert "Database connection refused" in comment
        assert "high" in comment
        
        mock_kanban_client.update_task_status.assert_called_once_with("TASK-001", "blocked")
    
    async def test_report_blocker_with_ai_resolution(self, pm_agent, mock_kanban_client, mock_ai_engine):
        """Test blocker reporting includes AI-generated resolution"""
        mock_ai_engine._call_claude.return_value = "1. Check database service\n2. Verify credentials"
        
        result = await pm_agent._report_blocker(
            agent_id="agent-001",
            task_id="TASK-001",
            blocker_description="Cannot connect to database",
            severity="medium"
        )
        
        assert result["success"] is True
        assert "Check database service" in result["resolution_suggestion"]
    
    async def test_report_blocker_ai_fallback(self, pm_agent, mock_kanban_client, mock_ai_engine):
        """Test blocker reporting falls back when AI fails"""
        mock_ai_engine._call_claude.side_effect = Exception("AI service unavailable")
        
        result = await pm_agent._report_blocker(
            agent_id="agent-001",
            task_id="TASK-001",
            blocker_description="Unknown error",
            severity="low"
        )
        
        assert result["success"] is True
        assert "Basic resolution steps" in result["resolution_suggestion"]
    
    async def test_report_blocker_error_handling(self, pm_agent, mock_kanban_client):
        """Test error handling in blocker reporting"""
        mock_kanban_client.add_comment.side_effect = Exception("API error")
        
        result = await pm_agent._report_blocker(
            agent_id="agent-001",
            task_id="TASK-001",
            blocker_description="Test blocker",
            severity="medium"
        )
        
        assert result["success"] is False
        assert "API error" in result["error"]


class TestProjectStatus(TestMarcusMVP):
    """Test project status functionality"""
    
    async def test_get_project_status_success(self, pm_agent, mock_kanban_client):
        """Test getting project status"""
        mock_kanban_client.get_board_summary.return_value = {
            "stats": {
                "totalCards": 50,
                "completionPercentage": 60,
                "inProgressCount": 10,
                "doneCount": 30,
                "urgentCount": 2,
                "bugCount": 5
            }
        }
        
        result = await pm_agent._get_project_status()
        
        assert result["success"] is True
        assert result["project_status"]["total_cards"] == 50
        assert result["project_status"]["completion_percentage"] == 60
        assert result["project_status"]["in_progress_count"] == 10
        assert result["project_status"]["done_count"] == 30
        assert result["project_status"]["urgent_count"] == 2
        assert result["project_status"]["bug_count"] == 5
        assert result["board_info"]["board_id"] == "test-board-id"
        assert result["board_info"]["project_id"] == "test-project-id"
    
    async def test_get_project_status_empty_stats(self, pm_agent, mock_kanban_client):
        """Test getting project status with empty stats"""
        mock_kanban_client.get_board_summary.return_value = {"stats": {}}
        
        result = await pm_agent._get_project_status()
        
        assert result["success"] is True
        assert result["project_status"]["total_cards"] == 0
        assert result["project_status"]["completion_percentage"] == 0
    
    async def test_get_project_status_error(self, pm_agent, mock_kanban_client):
        """Test error handling in project status"""
        mock_kanban_client.get_board_summary.side_effect = Exception("Connection timeout")
        
        result = await pm_agent._get_project_status()
        
        assert result["success"] is False
        assert "Connection timeout" in result["error"]


class TestAgentStatus(TestMarcusMVP):
    """Test agent status functionality"""
    
    async def test_get_agent_status_not_found(self, pm_agent):
        """Test getting status for non-existent agent"""
        result = await pm_agent._get_agent_status("unknown-agent")
        
        assert result["found"] is False
        assert "not registered" in result["message"]
    
    async def test_get_agent_status_without_task(self, pm_agent):
        """Test getting status for agent without current task"""
        # Register agent
        await pm_agent._register_agent("agent-001", "Test Agent", "Developer", ["Python"])
        
        result = await pm_agent._get_agent_status("agent-001")
        
        assert result["found"] is True
        assert result["agent_info"]["id"] == "agent-001"
        assert result["agent_info"]["name"] == "Test Agent"
        assert result["agent_info"]["role"] == "Developer"
        assert result["agent_info"]["skills"] == ["Python"]
        assert result["agent_info"]["completed_tasks"] == 0
        assert result["agent_info"]["current_task"] is None
    
    async def test_get_agent_status_with_task(self, pm_agent):
        """Test getting status for agent with current task"""
        # Register agent
        await pm_agent._register_agent("agent-001", "Test Agent", "Developer", [])
        
        # Assign a task
        assignment = TaskAssignment(
            task_id="TASK-001",
            task_name="Test Task",
            description="Test description",
            instructions="Do the task",
            estimated_hours=8.0,
            priority=Priority.MEDIUM,
            dependencies=[],
            assigned_to="agent-001",
            assigned_at=datetime.now(),
            due_date=None,
            workspace_path="/workspace/agent-001",
            forbidden_paths=[]
        )
        pm_agent.agent_tasks["agent-001"] = assignment
        
        result = await pm_agent._get_agent_status("agent-001")
        
        assert result["found"] is True
        assert result["agent_info"]["current_task"]["task_id"] == "TASK-001"
        assert result["agent_info"]["current_task"]["task_name"] == "Test Task"
        assert "assigned_at" in result["agent_info"]["current_task"]
    
    async def test_get_agent_status_error(self, pm_agent):
        """Test error handling in agent status"""
        # Register agent but cause an error when accessing properties
        mock_agent = Mock()
        # Configure the mock to raise an exception when worker_id is accessed
        type(mock_agent).worker_id = PropertyMock(side_effect=Exception("Attribute error"))
        pm_agent.agent_status["agent-001"] = mock_agent
        
        result = await pm_agent._get_agent_status("agent-001")
        
        assert result["found"] is False
        assert "Attribute error" in result["error"]


class TestListAgents(TestMarcusMVP):
    """Test listing registered agents"""
    
    async def test_list_agents_empty(self, pm_agent):
        """Test listing agents when none are registered"""
        result = await pm_agent._list_registered_agents()
        
        assert result["success"] is True
        assert result["agent_count"] == 0
        assert result["agents"] == []
    
    async def test_list_agents_multiple(self, pm_agent):
        """Test listing multiple registered agents"""
        # Register multiple agents
        await pm_agent._register_agent("agent-001", "Alice", "Frontend Dev", ["React"])
        await pm_agent._register_agent("agent-002", "Bob", "Backend Dev", ["Python", "Go"])
        
        # Assign task to one agent
        pm_agent.agent_tasks["agent-001"] = Mock(task_id="TASK-001")
        
        result = await pm_agent._list_registered_agents()
        
        assert result["success"] is True
        assert result["agent_count"] == 2
        
        agents = result["agents"]
        assert len(agents) == 2
        
        # Check first agent
        alice = next(a for a in agents if a["id"] == "agent-001")
        assert alice["name"] == "Alice"
        assert alice["has_current_task"] is True
        assert alice["current_task_id"] == "TASK-001"
        
        # Check second agent
        bob = next(a for a in agents if a["id"] == "agent-002")
        assert bob["name"] == "Bob"
        assert bob["has_current_task"] is False
        assert bob["current_task_id"] is None
    
    async def test_list_agents_error(self, pm_agent):
        """Test error handling in list agents"""
        # Cause an error by making agent_status not iterable
        pm_agent.agent_status = None
        
        result = await pm_agent._list_registered_agents()
        
        assert result["success"] is False
        assert "error" in result


class TestPingEndpoint(TestMarcusMVP):
    """Test ping/health check functionality"""
    
    async def test_ping_basic(self, pm_agent):
        """Test basic ping response"""
        result = await pm_agent._ping()
        
        assert result["success"] is True
        assert result["pong"] is True
        assert result["status"] == "online"
        assert result["service"] == "Marcus MVP"
        assert "timestamp" in result
        assert result["version"] == "1.0.0"
    
    async def test_ping_with_echo(self, pm_agent):
        """Test ping with echo message"""
        result = await pm_agent._ping("Hello Marcus")
        
        assert result["success"] is True
        assert result["echo"] == "Hello Marcus"
        assert result["echo_received"] is True
    
    async def test_ping_health_status(self, pm_agent, mock_ai_engine):
        """Test ping includes health status"""
        result = await pm_agent._ping()
        
        health = result["health"]
        assert health["status"] == "healthy"
        assert health["ai_engine"] == "available"
        assert "memory_usage" in health
    
    async def test_ping_capabilities(self, pm_agent, mock_ai_engine):
        """Test ping includes capabilities"""
        result = await pm_agent._ping()
        
        capabilities = result["capabilities"]
        assert capabilities["agent_registration"] is True
        assert capabilities["task_assignment"] is True
        assert capabilities["progress_tracking"] is True
        assert capabilities["blocker_resolution"] is True
        assert capabilities["ai_assistance"] is True
    
    async def test_ping_workload_metrics(self, pm_agent):
        """Test ping includes workload metrics"""
        # Register some agents and assign tasks
        await pm_agent._register_agent("agent-001", "Alice", "Dev", [])
        await pm_agent._register_agent("agent-002", "Bob", "Dev", [])
        pm_agent.agent_tasks["agent-001"] = Mock()
        pm_agent.agent_status["agent-001"].completed_tasks_count = 5
        pm_agent.agent_status["agent-002"].completed_tasks_count = 3
        
        result = await pm_agent._ping()
        
        workload = result["workload"]
        assert workload["registered_agents"] == 2
        assert workload["active_assignments"] == 1
        assert workload["total_completed_tasks"] == 8
        assert workload["agents_available"] == 1
    
    @patch('psutil.Process')
    async def test_ping_memory_usage(self, mock_process, pm_agent):
        """Test ping includes memory usage stats"""
        # Mock memory info
        mock_memory = Mock()
        mock_memory.rss = 100 * 1024 * 1024  # 100 MB
        mock_process.return_value.memory_info.return_value = mock_memory
        mock_process.return_value.memory_percent.return_value = 2.5
        
        result = await pm_agent._ping()
        
        memory = result["health"]["memory_usage"]
        assert memory["rss_mb"] == 100.0
        assert memory["percent"] == 2.5
    
    async def test_ping_error_handling(self, pm_agent):
        """Test ping error handling"""
        # Force an error by breaking the agent_status
        pm_agent.agent_status = None
        
        result = await pm_agent._ping()
        
        assert result["success"] is False
        assert result["pong"] is False
        assert result["status"] == "error"
        assert "error" in result


class TestHelperMethods(TestMarcusMVP):
    """Test helper methods"""
    
    async def test_generate_basic_instructions_with_ai(self, pm_agent, mock_ai_engine, sample_task):
        """Test AI instruction generation"""
        mock_ai_engine._call_claude.return_value = "1. Setup environment\n2. Implement feature\n3. Test"
        
        instructions = await pm_agent._generate_basic_instructions(sample_task)
        
        assert instructions == "1. Setup environment\n2. Implement feature\n3. Test"
        
        # Verify prompt contains task details
        call_args = mock_ai_engine._call_claude.call_args[0][0]
        assert sample_task.name in call_args
        assert sample_task.description in call_args
        assert "security" in call_args  # Label
    
    async def test_generate_basic_instructions_fallback(self, pm_agent, mock_ai_engine, sample_task):
        """Test instruction generation fallback when AI fails"""
        mock_ai_engine._call_claude.side_effect = Exception("AI unavailable")
        
        instructions = await pm_agent._generate_basic_instructions(sample_task)
        
        assert sample_task.name in instructions
        assert sample_task.description in instructions
        assert "Definition of Done" in instructions
    
    async def test_get_basic_resolution_with_ai(self, pm_agent, mock_ai_engine):
        """Test AI resolution generation"""
        mock_ai_engine._call_claude.return_value = "1. Check logs\n2. Restart service\n3. Contact admin"
        
        resolution = await pm_agent._get_basic_resolution("Service not responding")
        
        assert "Check logs" in resolution
        assert "Restart service" in resolution
    
    async def test_get_basic_resolution_fallback(self, pm_agent, mock_ai_engine):
        """Test resolution generation fallback"""
        mock_ai_engine._call_claude.side_effect = Exception("AI error")
        
        resolution = await pm_agent._get_basic_resolution("Unknown error")
        
        assert "Basic resolution steps" in resolution
        assert "Review the blocker description" in resolution
    
    def test_get_uptime_calculation(self, pm_agent):
        """Test uptime calculation"""
        import time
        pm_agent._start_time = time.time() - 3665  # 1 hour, 1 minute, 5 seconds ago
        
        uptime = pm_agent._get_uptime()
        
        assert "1h" in uptime
        assert "1m" in uptime
        assert "s" in uptime
    
    def test_get_uptime_no_start_time(self):
        """Test uptime when start time not set"""
        agent = MarcusMVP()
        delattr(agent, '_start_time')
        
        uptime = agent._get_uptime()
        
        assert uptime == "unknown"
    
    @patch('psutil.Process')
    def test_get_memory_usage(self, mock_process, pm_agent):
        """Test memory usage calculation"""
        mock_memory = Mock()
        mock_memory.rss = 256 * 1024 * 1024  # 256 MB
        mock_process.return_value.memory_info.return_value = mock_memory
        mock_process.return_value.memory_percent.return_value = 5.2
        
        memory = pm_agent._get_memory_usage()
        
        assert memory["rss_mb"] == 256.0
        assert memory["percent"] == 5.2
    
    @patch('psutil.Process')
    def test_get_memory_usage_error(self, mock_process, pm_agent):
        """Test memory usage with error"""
        mock_process.side_effect = Exception("Process error")
        
        memory = pm_agent._get_memory_usage()
        
        assert memory["rss_mb"] == 0
        assert memory["percent"] == 0




class TestInitialization(TestMarcusMVP):
    """Test MarcusMVP initialization"""
    
    async def test_initialize_success(self, pm_agent, mock_ai_engine, capsys):
        """Test successful initialization"""
        await pm_agent.initialize()
        
        # Check AI engine was initialized
        mock_ai_engine.initialize.assert_called_once()
        
        # Check output messages
        captured = capsys.readouterr()
        assert "Starting PM Agent MVP" in captured.err
        assert "AI engine ready" in captured.err
        assert "PM Agent MVP is ready" in captured.err
    
    async def test_initialize_ai_failure(self, pm_agent, mock_ai_engine, capsys):
        """Test initialization with AI engine failure"""
        mock_ai_engine.initialize.side_effect = Exception("AI init failed")
        
        with pytest.raises(Exception, match="AI init failed"):
            await pm_agent.initialize()
        
        captured = capsys.readouterr()
        assert "Failed to initialize PM Agent MVP" in captured.err
    
    def test_constructor_initialization(self):
        """Test MarcusMVP constructor properly initializes"""
        agent = MarcusMVP()
        
        assert agent.server.name == "pm-agent-mvp"
        assert hasattr(agent, 'settings')
        assert hasattr(agent, 'kanban_client')
        assert hasattr(agent, 'ai_engine')
        assert hasattr(agent, 'workspace_manager')
        assert agent.agent_tasks == {}
        assert agent.agent_status == {}
        assert hasattr(agent, '_start_time')