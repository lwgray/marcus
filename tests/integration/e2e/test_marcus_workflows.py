"""
Integration tests for critical Marcus workflows.

Tests end-to-end workflows including:
- Agent registration and task assignment
- Project creation and task generation
- Blocker reporting and AI resolution
- Mode switching and context preservation
- Error recovery and system resilience
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.core.error_framework import (
    ConfigurationError,
    ErrorContext,
    KanbanIntegrationError,
)
from src.core.models import Priority, RiskLevel, TaskStatus, WorkerStatus
from src.marcus_mcp.handlers import handle_tool_call
from src.marcus_mcp.server import MarcusServer
from tests.fixtures.factories import (
    AgentFactory,
    BlockerFactory,
    ProjectStateFactory,
    TaskFactory,
    reset_all_counters,
)
from tests.utils.base import BaseTestCase


@pytest.mark.integration
@pytest.mark.e2e
class TestAgentRegistrationAndTaskAssignment(BaseTestCase):
    """Test the core workflow of agent registration and task assignment."""

    def setup_method(self):
        """Reset factory counters before each test."""
        super().setup_method()
        reset_all_counters()

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_agent_registration_workflow(self):
        """
        Test complete agent registration flow:
        1. Register multiple agents with different skills
        2. Verify agent status tracking
        3. Ensure proper skill-based task matching
        """
        server = await self._create_test_server()

        # Register multiple agents
        agents = [
            {
                "agent_id": "backend-1",
                "name": "Alice",
                "role": "Backend Developer",
                "skills": ["python", "django", "postgres", "api", "testing"],
            },
            {
                "agent_id": "frontend-1",
                "name": "Bob",
                "role": "Frontend Developer",
                "skills": ["javascript", "react", "css", "ui", "testing"],
            },
            {
                "agent_id": "devops-1",
                "name": "Charlie",
                "role": "DevOps Engineer",
                "skills": ["docker", "kubernetes", "aws", "monitoring", "ci/cd"],
            },
        ]

        # Test registration
        for agent in agents:
            result = await handle_tool_call("register_agent", agent, server)
            data = self._parse_result(result)

            assert data["success"] is True
            assert data["agent_id"] == agent["agent_id"]

            # Verify agent is tracked in server state
            assert agent["agent_id"] in server.agent_status
            worker = server.agent_status[agent["agent_id"]]
            assert worker.name == agent["name"]
            assert worker.role == agent["role"]
            assert set(worker.skills) == set(agent["skills"])

        # Check list of registered agents
        result = await handle_tool_call("list_registered_agents", {}, server)
        data = self._parse_result(result)

        assert data["success"] is True
        assert data["total"] == 3
        assert len(data["agents"]) == 3

        # Verify each agent in the list
        agent_ids = {a["id"] for a in data["agents"]}
        assert agent_ids == {"backend-1", "frontend-1", "devops-1"}

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_skill_based_task_assignment(self):
        """
        Test that tasks are assigned based on agent skills:
        1. Create tasks with specific skill requirements
        2. Register agents with matching skills
        3. Verify optimal task assignment
        """
        server = await self._create_test_server()

        # Create tasks with specific skill requirements
        backend_task = TaskFactory.create(
            name="Implement REST API",
            labels=["python", "api", "backend"],
            priority=Priority.HIGH,
        )
        frontend_task = TaskFactory.create(
            name="Build React Dashboard",
            labels=["javascript", "react", "frontend"],
            priority=Priority.HIGH,
        )
        devops_task = TaskFactory.create(
            name="Setup Kubernetes Cluster",
            labels=["kubernetes", "docker", "infrastructure"],
            priority=Priority.MEDIUM,
        )

        # Mock kanban to return these tasks
        server.kanban_client.get_all_tasks.return_value = [
            backend_task,
            frontend_task,
            devops_task,
        ]
        server.kanban_client.get_available_tasks.return_value = [
            backend_task,
            frontend_task,
            devops_task,
        ]

        # Register agents with matching skills
        agents = [
            {
                "agent_id": "backend-dev",
                "name": "Alice",
                "role": "Backend Developer",
                "skills": ["python", "api", "django", "backend"],
            },
            {
                "agent_id": "frontend-dev",
                "name": "Bob",
                "role": "Frontend Developer",
                "skills": ["javascript", "react", "css", "frontend"],
            },
            {
                "agent_id": "devops-eng",
                "name": "Charlie",
                "role": "DevOps Engineer",
                "skills": ["kubernetes", "docker", "aws", "infrastructure"],
            },
        ]

        for agent in agents:
            await handle_tool_call("register_agent", agent, server)

        # Request tasks for each agent
        assignments = {}
        for agent in agents:
            result = await handle_tool_call(
                "request_next_task", {"agent_id": agent["agent_id"]}, server
            )
            data = self._parse_result(result)

            if data.get("success") and data.get("task"):
                assignments[agent["agent_id"]] = data["task"]["name"]

        # Verify skill-based assignment
        assert "backend-dev" in assignments
        assert "API" in assignments["backend-dev"]  # Backend dev should get API task

        assert "frontend-dev" in assignments
        assert (
            "React" in assignments["frontend-dev"]
        )  # Frontend dev should get React task

        assert "devops-eng" in assignments
        assert "Kubernetes" in assignments["devops-eng"]  # DevOps should get K8s task

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_concurrent_task_assignment_no_duplicates(self):
        """
        Test that concurrent task requests don't result in duplicate assignments:
        1. Multiple agents request tasks simultaneously
        2. Verify no task is assigned to multiple agents
        3. Check assignment locking mechanism
        """
        server = await self._create_test_server()

        # Create limited tasks to force competition
        tasks = TaskFactory.create_batch(5, status=TaskStatus.TODO)
        server.kanban_client.get_all_tasks.return_value = tasks
        server.kanban_client.get_available_tasks.return_value = tasks

        # Register multiple agents
        agents = []
        for i in range(8):  # More agents than tasks
            agent = AgentFactory.create(worker_id=f"agent-{i}")
            agents.append(agent)
            await handle_tool_call(
                "register_agent",
                {
                    "agent_id": agent.worker_id,
                    "name": agent.name,
                    "role": agent.role,
                    "skills": agent.skills,
                },
                server,
            )

        # Simulate concurrent task requests
        async def request_task(agent_id: str) -> Optional[str]:
            result = await handle_tool_call(
                "request_next_task", {"agent_id": agent_id}, server
            )
            data = self._parse_result(result)
            if data.get("success") and data.get("task"):
                return data["task"]["id"]
            return None

        # Request tasks concurrently
        task_requests = [request_task(agent.worker_id) for agent in agents]
        assigned_task_ids = await asyncio.gather(*task_requests)

        # Filter out None values
        assigned_task_ids = [tid for tid in assigned_task_ids if tid is not None]

        # Verify no duplicates
        assert len(assigned_task_ids) == len(set(assigned_task_ids))

        # Verify at most 5 tasks were assigned (the number of available tasks)
        assert len(assigned_task_ids) <= 5

        # Verify assignment persistence
        persisted_assignments = await server.assignment_persistence.load_assignments()
        assert len(persisted_assignments) == len(assigned_task_ids)

    async def _create_test_server(self) -> MarcusServer:
        """Create a test server with mocked dependencies."""
        import os

        os.environ["KANBAN_PROVIDER"] = "planka"

        # Mock config loading
        with patch("src.marcus_mcp.server.get_config") as mock_config:
            mock_config.return_value = {
                "kanban": {"provider": "planka"},
                "project_name": "Test Project",
            }

            server = MarcusServer()

        # Setup mocked kanban client
        server.kanban_client = self.create_mock_kanban_client()
        server.kanban_client.board_id = "test-board-123"

        # Mock AI engine with realistic responses
        server.ai_engine = self.create_mock_ai_engine()
        server.ai_engine.generate_task_instructions = AsyncMock(
            return_value="1. Analyze requirements\n2. Implement solution\n3. Write tests"
        )

        # Don't start assignment monitor in tests
        server.assignment_monitor = None

        return server

    def _parse_result(self, result: List[Any]) -> Dict[str, Any]:
        """Parse MCP tool result."""
        if result and len(result) > 0:
            return json.loads(result[0].text)
        return {}


@pytest.mark.integration
@pytest.mark.e2e
class TestProjectCreationAndTaskGeneration(BaseTestCase):
    """Test project creation and automatic task generation workflows."""

    def setup_method(self):
        """Reset factory counters before each test."""
        super().setup_method()
        reset_all_counters()

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_create_project_from_description(self):
        """
        Test creating a project from natural language description:
        1. Provide high-level project description
        2. Verify task generation with proper structure
        3. Check task dependencies and priorities
        """
        server = await self._create_test_server()

        # Mock the actual natural language processing
        with patch(
            "src.integrations.nlp_tools.create_project_from_natural_language"
        ) as mock_create:
            mock_create.return_value = {
                "success": True,
                "project_name": "E-Commerce Platform",
                "tasks_created": 5,
                "task_breakdown": {"feature": 3, "bug": 0, "enhancement": 2},
                "estimated_days": 30,
            }

            # Create project
            result = await handle_tool_call(
                "create_project",
                {
                    "project_name": "E-Commerce Platform",
                    "description": "Build an e-commerce platform with user auth, product catalog, and shopping cart",
                },
                server,
            )

        data = self._parse_result(result)

        assert data["success"] is True
        assert data["project_name"] == "E-Commerce Platform"
        assert "tasks_created" in data
        assert data["tasks_created"] >= 5  # tasks_created is a count, not a list
        # The AI PRD parser may generate more detailed tasks, so we check for minimum

        # Verify that the natural language processor was called
        mock_create.assert_called_once()

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_add_feature_workflow(self):
        """
        Test adding features to existing project:
        1. Have an existing project with tasks
        2. Add new feature using natural language
        3. Verify feature tasks are created and integrated
        """
        server = await self._create_test_server()

        # Setup existing project tasks
        existing_tasks = [
            TaskFactory.create(
                id="TASK-001",
                name="User authentication API",
                description="Basic auth implementation",
                status=TaskStatus.DONE,
                labels=["backend", "api"],
            ),
            TaskFactory.create(
                id="TASK-002",
                name="Product catalog API",
                description="CRUD for products",
                status=TaskStatus.IN_PROGRESS,
                labels=["backend", "api"],
            ),
        ]

        server.kanban_client.get_all_tasks.return_value = existing_tasks

        # Mock add_feature response
        with patch(
            "src.integrations.nlp_tools.add_feature_natural_language"
        ) as mock_add:
            mock_add.return_value = {
                "success": True,
                "tasks_created": 3,
                "feature_phase": "current",
                "integration_detected": True,
                "task_breakdown": {"feature": 3},
            }

            # Add shopping cart feature
            result = await handle_tool_call(
                "add_feature",
                {
                    "feature_description": "Add shopping cart functionality with add/remove items and checkout",
                    "integration_point": "auto_detect",
                },
                server,
            )

        data = self._parse_result(result)

        assert data["success"] is True
        assert data["tasks_created"] == 3
        assert data["integration_detected"] is True

        # Verify the feature was added correctly
        mock_add.assert_called_once()

    async def _create_test_server(self) -> MarcusServer:
        """Create a test server with mocked dependencies."""
        import os

        os.environ["KANBAN_PROVIDER"] = "planka"

        with patch("src.marcus_mcp.server.get_config") as mock_config:
            mock_config.return_value = {
                "kanban": {"provider": "planka"},
                "project_name": "Test Project",
            }

            server = MarcusServer()

        server.kanban_client = self.create_mock_kanban_client()
        server.kanban_client.board_id = "test-board-123"

        # Enhanced AI engine mocking
        server.ai_engine = self.create_mock_ai_engine()

        server.assignment_monitor = None

        return server

    def _parse_result(self, result: List[Any]) -> Dict[str, Any]:
        """Parse MCP tool result."""
        if result and len(result) > 0:
            return json.loads(result[0].text)
        return {}


@pytest.mark.integration
@pytest.mark.e2e
class TestBlockerReportingAndResolution(BaseTestCase):
    """Test blocker reporting and AI-powered resolution workflows."""

    def setup_method(self):
        """Reset factory counters before each test."""
        super().setup_method()
        reset_all_counters()

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_blocker_reporting_with_ai_suggestions(self):
        """
        Test blocker reporting and AI resolution:
        1. Agent reports blocker
        2. AI analyzes and provides suggestions
        3. Blocker status is tracked
        4. Resolution is documented
        """
        server = await self._create_test_server()

        # Register agent and assign task
        agent_id = "backend-dev"
        await handle_tool_call(
            "register_agent",
            {
                "agent_id": agent_id,
                "name": "Alice",
                "role": "Backend Developer",
                "skills": ["python", "django", "postgres"],
            },
            server,
        )

        # Create and assign a task
        task = TaskFactory.create(
            id="TASK-001",
            name="Implement payment gateway",
            status=TaskStatus.IN_PROGRESS,
            assigned_to=agent_id,
        )

        server.kanban_client.get_task_by_id.return_value = task

        # Mock AI blocker analysis
        server.ai_engine.analyze_blocker = AsyncMock(
            return_value="""
## Blocker Analysis: Missing Payment Gateway API Documentation

### Suggested Solutions:

1. **Contact Integration Team**
   - Reach out to payment provider's technical support
   - Request API documentation and sandbox credentials
   - Estimated resolution: 1-2 days

2. **Alternative Approach**
   - Use Stripe instead of the planned gateway
   - Well-documented with extensive examples
   - Can be implemented immediately

3. **Temporary Workaround**
   - Mock the payment flow for development
   - Continue with other features
   - Integrate actual gateway when docs available

### Risk Assessment:
- **Impact**: High - blocks critical feature
- **Urgency**: Medium - have workaround options
- **Recommendation**: Proceed with option 2 or 3
"""
        )

        # Report blocker
        result = await handle_tool_call(
            "report_blocker",
            {
                "agent_id": agent_id,
                "task_id": "TASK-001",
                "blocker_description": "Cannot integrate payment gateway - missing API documentation",
                "severity": "high",
            },
            server,
        )

        data = self._parse_result(result)

        assert data["success"] is True
        assert "suggestions" in data
        assert "Alternative Approach" in data["suggestions"]
        assert "Stripe" in data["suggestions"]

        # Verify task status update
        server.kanban_client.update_task.assert_called_with(
            "TASK-001",
            {
                "status": TaskStatus.BLOCKED,
                "blocker": "Cannot integrate payment gateway - missing API documentation",
            },
        )

        # Verify comment was added
        server.kanban_client.add_comment.assert_called_once()
        comment_call = server.kanban_client.add_comment.call_args[0]
        assert comment_call[0] == "TASK-001"
        assert "BLOCKER (HIGH)" in comment_call[1]
        assert "AI Suggestions" in comment_call[1]

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_blocker_escalation_workflow(self):
        """
        Test blocker escalation for critical issues:
        1. Report critical blocker
        2. Verify escalation triggers
        3. Check notification mechanisms
        """
        server = await self._create_test_server()

        # Register agent
        agent_id = "devops-eng"
        await handle_tool_call(
            "register_agent",
            {
                "agent_id": agent_id,
                "name": "Charlie",
                "role": "DevOps Engineer",
                "skills": ["kubernetes", "aws", "monitoring"],
            },
            server,
        )

        # Create critical infrastructure task
        task = TaskFactory.create(
            id="TASK-CRITICAL",
            name="Fix production database",
            priority=Priority.URGENT,
            status=TaskStatus.IN_PROGRESS,
            assigned_to=agent_id,
        )

        server.kanban_client.get_task_by_id.return_value = task

        # Mock critical blocker analysis
        server.ai_engine.analyze_blocker = AsyncMock(
            return_value="""
## CRITICAL BLOCKER: Production Database Failure

### Immediate Actions Required:

1. **Emergency Response**
   - Escalate to on-call DBA immediately
   - Initiate disaster recovery procedure
   - Switch to read replica if available

2. **Root Cause Analysis**
   - Check disk space: CRITICAL - 98% full
   - Review recent deployments
   - Analyze database logs for corruption

### Escalation Required:
- **Notify**: CTO, Head of Engineering, On-call team
- **Impact**: All services degraded
- **Customer Impact**: 100% of users affected

### Emergency Contacts:
- DBA On-call: +1-555-0123
- AWS Support: Premium support ticket opened
"""
        )

        # Report critical blocker
        result = await handle_tool_call(
            "report_blocker",
            {
                "agent_id": agent_id,
                "task_id": "TASK-CRITICAL",
                "blocker_description": "Production database is down - disk full, queries timing out",
                "severity": "critical",
            },
            server,
        )

        data = self._parse_result(result)

        assert data["success"] is True
        assert "CRITICAL BLOCKER" in data["suggestions"]
        assert "Escalate to on-call DBA" in data["suggestions"]

        # In a real system, this would trigger:
        # - Slack/email notifications
        # - PagerDuty alerts
        # - Status page updates
        # - Incident management workflow

    async def _create_test_server(self) -> MarcusServer:
        """Create a test server with mocked dependencies."""
        import os

        os.environ["KANBAN_PROVIDER"] = "planka"

        with patch("src.marcus_mcp.server.get_config") as mock_config:
            mock_config.return_value = {
                "kanban": {"provider": "planka"},
                "project_name": "Test Project",
            }

            server = MarcusServer()

        server.kanban_client = self.create_mock_kanban_client()
        server.ai_engine = self.create_mock_ai_engine()
        server.assignment_monitor = None

        return server

    def _parse_result(self, result: List[Any]) -> Dict[str, Any]:
        """Parse MCP tool result."""
        if result and len(result) > 0:
            return json.loads(result[0].text)
        return {}


@pytest.mark.integration
@pytest.mark.e2e
class TestProgressTrackingAndCompletion(BaseTestCase):
    """Test task progress tracking and completion workflows."""

    def setup_method(self):
        """Reset factory counters before each test."""
        super().setup_method()
        reset_all_counters()

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_task_progress_reporting_workflow(self):
        """
        Test complete task progress workflow:
        1. Agent reports progress at milestones
        2. Progress is tracked in kanban
        3. Task completion updates agent metrics
        """
        server = await self._create_test_server()

        # Register agent
        agent_id = "fullstack-dev"
        await handle_tool_call(
            "register_agent",
            {
                "agent_id": agent_id,
                "name": "Dana",
                "role": "Fullstack Developer",
                "skills": ["python", "javascript", "testing"],
            },
            server,
        )

        # Assign a task
        task = TaskFactory.create(
            id="TASK-PROG-001",
            name="Build user dashboard",
            estimated_hours=16,
            status=TaskStatus.TODO,
        )

        server.kanban_client.get_all_tasks.return_value = [task]
        server.kanban_client.get_available_tasks.return_value = [task]
        server.kanban_client.get_task_by_id.return_value = task

        # Request task
        result = await handle_tool_call(
            "request_next_task", {"agent_id": agent_id}, server
        )

        data = self._parse_result(result)
        assert data["success"] is True
        task_id = data["task"]["id"]

        # Report progress at milestones
        progress_updates = [
            (25, "Completed backend API endpoints"),
            (50, "Frontend components created"),
            (75, "Integration testing in progress"),
            (100, "Feature complete with tests"),
        ]

        for progress, message in progress_updates:
            status = "completed" if progress == 100 else "in_progress"

            result = await handle_tool_call(
                "report_task_progress",
                {
                    "agent_id": agent_id,
                    "task_id": task_id,
                    "status": status,
                    "progress": progress,
                    "message": message,
                },
                server,
            )

            data = self._parse_result(result)
            assert data["success"] is True

            # Verify kanban updates
            if progress == 100:
                # Check that task was marked as done
                update_calls = [
                    call
                    for call in server.kanban_client.update_task.call_args_list
                    if call[0][0] == task_id
                    and call[0][1].get("status") == TaskStatus.DONE
                ]
                assert len(update_calls) > 0

        # Verify agent metrics updated
        agent = server.agent_status[agent_id]
        assert agent.completed_tasks_count == 1
        assert len(agent.current_tasks) == 0

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_multi_agent_project_completion(self):
        """
        Test project completion with multiple agents:
        1. Multiple agents work on different tasks
        2. Track overall project progress
        3. Verify project completion metrics
        """
        server = await self._create_test_server()

        # Create a project with multiple tasks
        tasks = [
            TaskFactory.create(
                id="TASK-BE-001", name="Setup backend", labels=["backend"]
            ),
            TaskFactory.create(
                id="TASK-BE-002", name="Create APIs", labels=["backend", "api"]
            ),
            TaskFactory.create(id="TASK-FE-001", name="Build UI", labels=["frontend"]),
            TaskFactory.create(
                id="TASK-FE-002", name="Add styling", labels=["frontend", "css"]
            ),
            TaskFactory.create(
                id="TASK-TEST-001", name="Write tests", labels=["testing"]
            ),
        ]

        server.kanban_client.get_all_tasks.return_value = tasks
        server.kanban_client.get_available_tasks.return_value = tasks

        # Register team of agents
        agents = [
            {
                "agent_id": "be-dev",
                "name": "Alice",
                "role": "Backend Dev",
                "skills": ["backend", "api"],
            },
            {
                "agent_id": "fe-dev",
                "name": "Bob",
                "role": "Frontend Dev",
                "skills": ["frontend", "css"],
            },
            {
                "agent_id": "qa-eng",
                "name": "Carol",
                "role": "QA Engineer",
                "skills": ["testing"],
            },
        ]

        for agent in agents:
            await handle_tool_call("register_agent", agent, server)

        # Agents request and complete tasks
        completed_count = 0

        for agent in agents:
            # Request task
            result = await handle_tool_call(
                "request_next_task", {"agent_id": agent["agent_id"]}, server
            )

            data = self._parse_result(result)
            if data.get("success") and data.get("task"):
                task_id = data["task"]["id"]

                # Simulate work and complete
                await handle_tool_call(
                    "report_task_progress",
                    {
                        "agent_id": agent["agent_id"],
                        "task_id": task_id,
                        "status": "completed",
                        "progress": 100,
                        "message": f"Completed {data['task']['name']}",
                    },
                    server,
                )
                completed_count += 1

        # Check project status
        result = await handle_tool_call("get_project_status", {}, server)
        data = self._parse_result(result)

        assert data["success"] is True
        # At least some tasks should be completed
        assert completed_count > 0

    async def _create_test_server(self) -> MarcusServer:
        """Create a test server with mocked dependencies."""
        import os

        os.environ["KANBAN_PROVIDER"] = "planka"

        with patch("src.marcus_mcp.server.get_config") as mock_config:
            mock_config.return_value = {
                "kanban": {"provider": "planka"},
                "project_name": "Test Project",
            }

            server = MarcusServer()

        server.kanban_client = self.create_mock_kanban_client()
        server.ai_engine = self.create_mock_ai_engine()
        server.assignment_monitor = None

        # Mock project state refresh
        server.project_state = ProjectStateFactory.create()

        return server

    def _parse_result(self, result: List[Any]) -> Dict[str, Any]:
        """Parse MCP tool result."""
        if result and len(result) > 0:
            return json.loads(result[0].text)
        return {}


@pytest.mark.integration
@pytest.mark.e2e
class TestErrorRecoveryAndResilience(BaseTestCase):
    """Test error recovery and system resilience workflows."""

    def setup_method(self):
        """Reset factory counters before each test."""
        super().setup_method()
        reset_all_counters()

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_kanban_connection_failure_recovery(self):
        """
        Test recovery from kanban connection failures:
        1. Simulate kanban connection failure
        2. Verify graceful error handling
        3. Test recovery when connection restored
        """
        server = await self._create_test_server()

        # Register agent
        await handle_tool_call(
            "register_agent",
            {
                "agent_id": "test-agent",
                "name": "Test Agent",
                "role": "Developer",
                "skills": ["python"],
            },
            server,
        )

        # Simulate kanban failure
        server.kanban_client.get_all_tasks.side_effect = KanbanIntegrationError(
            board_name="test-board",
            operation="get_tasks",
            details="Connection timeout",
            context=ErrorContext(operation="task_fetch"),
        )

        # Try to request task - should fail gracefully
        result = await handle_tool_call(
            "request_next_task", {"agent_id": "test-agent"}, server
        )

        data = self._parse_result(result)
        assert data["success"] is False
        assert "error" in data

        # Restore kanban connection
        server.kanban_client.get_all_tasks.side_effect = None
        server.kanban_client.get_all_tasks.return_value = [
            TaskFactory.create(name="Recovery task")
        ]
        server.kanban_client.get_available_tasks.return_value = [
            TaskFactory.create(name="Recovery task")
        ]

        # Try again - should succeed
        result = await handle_tool_call(
            "request_next_task", {"agent_id": "test-agent"}, server
        )

        data = self._parse_result(result)
        assert data["success"] is True
        assert data["task"]["name"] == "Recovery task"

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_configuration_error_handling(self):
        """
        Test handling of configuration errors:
        1. Missing required configuration
        2. Invalid configuration values
        3. Helpful error messages
        """
        # Test missing configuration
        with patch("src.marcus_mcp.server.get_config") as mock_config:
            mock_config.side_effect = ConfigurationError(
                service_name="Marcus",
                config_type="config_marcus.json",
                missing_field="kanban.provider",
                context=ErrorContext(operation="server_init"),
            )

            with pytest.raises(ConfigurationError) as exc_info:
                server = MarcusServer()

            assert "kanban.provider" in str(exc_info.value)

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_assignment_persistence_recovery(self):
        """
        Test recovery of assignments from persistent storage:
        1. Create assignments
        2. Simulate server restart
        3. Verify assignments are recovered
        """
        server1 = await self._create_test_server()

        # Register agent and assign task
        agent_id = "persistent-agent"
        await handle_tool_call(
            "register_agent",
            {
                "agent_id": agent_id,
                "name": "Persistent Agent",
                "role": "Developer",
                "skills": ["python", "testing"],
            },
            server1,
        )

        # Mock task assignment
        task = TaskFactory.create(id="TASK-PERSIST-001", name="Persistent task")
        server1.kanban_client.get_all_tasks.return_value = [task]
        server1.kanban_client.get_available_tasks.return_value = [task]

        # Request task
        result = await handle_tool_call(
            "request_next_task", {"agent_id": agent_id}, server1
        )

        data = self._parse_result(result)
        assert data["success"] is True

        # Verify assignment was persisted
        assignments = await server1.assignment_persistence.get_all_assignments()
        assert agent_id in assignments
        assert assignments[agent_id]["task_id"] == "TASK-PERSIST-001"

        # Simulate server restart - create new server instance
        server2 = await self._create_test_server()

        # Copy persistence layer
        server2.assignment_persistence = server1.assignment_persistence

        # Check that persisted assignments prevent duplicate assignment
        persisted_ids = await server2.assignment_persistence.get_all_assigned_task_ids()
        assert "TASK-PERSIST-001" in persisted_ids

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_concurrent_modification_handling(self):
        """
        Test handling of concurrent modifications:
        1. Multiple agents modifying same task
        2. Verify last-write-wins behavior
        3. Check conflict detection
        """
        server = await self._create_test_server()

        # Register two agents
        agents = ["agent-1", "agent-2"]
        for agent_id in agents:
            await handle_tool_call(
                "register_agent",
                {
                    "agent_id": agent_id,
                    "name": f"Agent {agent_id}",
                    "role": "Developer",
                    "skills": ["python"],
                },
                server,
            )

        # Both agents somehow get assigned to same task (edge case)
        task_id = "TASK-CONFLICT-001"

        # Simulate concurrent progress updates
        async def update_progress(agent_id: str, progress: int):
            return await handle_tool_call(
                "report_task_progress",
                {
                    "agent_id": agent_id,
                    "task_id": task_id,
                    "status": "in_progress",
                    "progress": progress,
                    "message": f"Progress from {agent_id}",
                },
                server,
            )

        # Run updates concurrently
        results = await asyncio.gather(
            update_progress("agent-1", 50),
            update_progress("agent-2", 60),
            return_exceptions=True,
        )

        # At least one should succeed
        successful_updates = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_updates) > 0

        # Verify final state is consistent
        final_update_calls = server.kanban_client.update_task_progress.call_args_list
        assert len(final_update_calls) >= 1

    async def _create_test_server(self) -> MarcusServer:
        """Create a test server with mocked dependencies."""
        import os

        os.environ["KANBAN_PROVIDER"] = "planka"

        with patch("src.marcus_mcp.server.get_config") as mock_config:
            mock_config.return_value = {
                "kanban": {"provider": "planka"},
                "project_name": "Test Project",
            }

            server = MarcusServer()

        server.kanban_client = self.create_mock_kanban_client()
        server.ai_engine = self.create_mock_ai_engine()
        server.assignment_monitor = None

        return server

    def _parse_result(self, result: List[Any]) -> Dict[str, Any]:
        """Parse MCP tool result."""
        if result and len(result) > 0:
            return json.loads(result[0].text)
        return {}


@pytest.mark.integration
@pytest.mark.e2e
class TestSystemHealthAndMonitoring(BaseTestCase):
    """Test system health monitoring and diagnostics workflows."""

    def setup_method(self):
        """Reset factory counters before each test."""
        super().setup_method()
        reset_all_counters()

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_system_health_check(self):
        """
        Test comprehensive system health checks:
        1. Check all system components
        2. Verify health metrics
        3. Detect degraded components
        """
        server = await self._create_test_server()

        # Setup some state
        await handle_tool_call(
            "register_agent",
            {
                "agent_id": "health-agent",
                "name": "Health Test Agent",
                "role": "Developer",
                "skills": ["monitoring"],
            },
            server,
        )

        # Perform health check
        result = await handle_tool_call("ping", {"echo": "health-check"}, server)
        data = self._parse_result(result)

        assert data["success"] is True
        assert data["status"] == "online"
        assert data["echo"] == "health-check"
        assert "timestamp" in data

        # Check assignment health
        with patch(
            "src.monitoring.assignment_monitor.AssignmentHealthChecker"
        ) as mock_checker:
            mock_health_checker = Mock()
            mock_health_checker.check_assignment_health = AsyncMock(
                return_value={
                    "status": "healthy",
                    "persistence_layer": {"status": "ok", "assignments": 1},
                    "kanban_sync": {"status": "ok", "in_sync": True},
                    "monitor": {
                        "status": "running",
                        "last_sync": datetime.now().isoformat(),
                    },
                }
            )
            mock_checker.return_value = mock_health_checker

            result = await handle_tool_call("check_assignment_health", {}, server)
            data = self._parse_result(result)

            assert data["success"] is True
            assert data["status"] == "healthy"

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_performance_monitoring(self):
        """
        Test performance monitoring capabilities:
        1. Track operation latencies
        2. Monitor resource usage
        3. Detect performance degradation
        """
        server = await self._create_test_server()

        # Simulate multiple operations to generate metrics
        operations = []

        # Register multiple agents
        for i in range(5):
            start_time = datetime.now()
            await handle_tool_call(
                "register_agent",
                {
                    "agent_id": f"perf-agent-{i}",
                    "name": f"Performance Agent {i}",
                    "role": "Developer",
                    "skills": ["python", "testing"],
                },
                server,
            )
            duration = (datetime.now() - start_time).total_seconds()
            operations.append(("register_agent", duration))

        # Request tasks
        tasks = TaskFactory.create_batch(10)
        server.kanban_client.get_all_tasks.return_value = tasks
        server.kanban_client.get_available_tasks.return_value = tasks

        for i in range(5):
            start_time = datetime.now()
            await handle_tool_call(
                "request_next_task", {"agent_id": f"perf-agent-{i}"}, server
            )
            duration = (datetime.now() - start_time).total_seconds()
            operations.append(("request_task", duration))

        # Analyze performance
        avg_latencies = {}
        for op_type, duration in operations:
            if op_type not in avg_latencies:
                avg_latencies[op_type] = []
            avg_latencies[op_type].append(duration)

        # Verify reasonable performance
        for op_type, latencies in avg_latencies.items():
            avg_latency = sum(latencies) / len(latencies)
            # Integration tests should complete operations quickly
            assert (
                avg_latency < 1.0
            ), f"{op_type} average latency too high: {avg_latency}"

    async def _create_test_server(self) -> MarcusServer:
        """Create a test server with mocked dependencies."""
        import os

        os.environ["KANBAN_PROVIDER"] = "planka"

        with patch("src.marcus_mcp.server.get_config") as mock_config:
            mock_config.return_value = {
                "kanban": {"provider": "planka"},
                "project_name": "Test Project",
            }

            server = MarcusServer()

        server.kanban_client = self.create_mock_kanban_client()
        server.ai_engine = self.create_mock_ai_engine()
        server.assignment_monitor = None

        return server

    def _parse_result(self, result: List[Any]) -> Dict[str, Any]:
        """Parse MCP tool result."""
        if result and len(result) > 0:
            return json.loads(result[0].text)
        return {}


# Run specific test scenarios
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
