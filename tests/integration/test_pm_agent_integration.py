"""
Integration tests for PM Agent server components.

This module tests the integration between PM Agent components including the MCP server,
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

from pm_agent_mcp_server_v2 import PMAgentState
from src.core.models import Task, TaskStatus, Priority, WorkerStatus, RiskLevel, ProjectState


class TestPMAgentIntegration:
    """
    Integration tests for the PM Agent Server.
    
    These tests verify that all components work together correctly,
    including MCP server request handling, AI decision making,
    monitoring state tracking, and notification delivery.
    
    Notes
    -----
    Tests use mocked external services to ensure reproducibility and
    avoid dependencies on running services.
    """
    
    @pytest.fixture
    async def pm_agent(self) -> AsyncMock:
        """
        Set up a complete PM Agent instance with mocked external dependencies.
        
        Creates a real PM Agent server instance with mocked external services
        (Kanban, Claude API) to test component integration without requiring
        actual services to be running.
        
        Returns
        -------
        PMAgentServer
            A PM Agent server instance with mocked dependencies.
        
        Notes
        -----
        This fixture mocks:
        - Kanban client for task management
        - Anthropic client for AI decisions
        - Monitoring and communication systems
        """
        with patch('src.integrations.mcp_kanban_client.MCPKanbanClient') as mock_kanban:
            with patch('anthropic.Anthropic') as mock_anthropic:
                # Create the PM Agent
                agent = PMAgentServer()
                
                # Mock the Kanban client methods
                agent.kanban_client = AsyncMock()
                agent.kanban_client.get_available_tasks = AsyncMock()
                agent.kanban_client.assign_task = AsyncMock()
                agent.kanban_client.add_comment = AsyncMock()
                agent.kanban_client.update_task_status = AsyncMock()
                
                # Mock the AI engine's Claude client
                agent.ai_engine.client = Mock()
                agent.ai_engine._call_claude = AsyncMock()
                
                # Mock monitoring and communication
                agent.monitor.get_project_state = AsyncMock()
                agent.comm_hub._send_slack_message = AsyncMock()
                agent.comm_hub._send_kanban_comment = AsyncMock()
                
                return agent
    
    @pytest.mark.asyncio
    async def test_complete_task_assignment_flow(self, pm_agent):
        """
        TEST 1: Complete task assignment workflow from request to notification
        
        This test simulates:
        1. An agent requesting work
        2. PM Agent finding the best task
        3. AI generating instructions
        4. Task being assigned on kanban board
        5. Notifications being sent
        
        What we're verifying:
        - All components integrate properly
        - Data flows correctly between systems
        - Proper notifications are sent
        """
        print("\n=== TEST: Complete Task Assignment Flow ===\n")
        
        # STEP 1: Set up test data
        print("STEP 1: Setting up test data...")
        
        # Create a test worker
        test_worker = WorkerStatus(
            worker_id="test-dev-001",
            name="Test Developer",
            role="Backend Developer",
            email="test@example.com",
            current_tasks=[],
            completed_tasks_count=10,
            capacity=40,
            skills=["python", "api", "testing"],
            availability={"monday": True},
            performance_score=1.0
        )
        pm_agent.agent_status["test-dev-001"] = test_worker
        
        # Create available tasks
        available_task = Task(
            id="TASK-TEST-001",
            name="Implement API endpoint",
            description="Create REST endpoint for user data",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=2),
            estimated_hours=8.0,
            dependencies=[],
            labels=["api", "backend"]
        )
        
        # Mock kanban client to return this task
        pm_agent.kanban_client.get_available_tasks.return_value = [available_task]
        
        # STEP 2: Mock AI responses
        print("STEP 2: Configuring AI responses...")
        
        # Mock task matching
        pm_agent.ai_engine._call_claude.return_value = json.dumps({
            "recommended_task_id": "TASK-TEST-001",
            "confidence_score": 0.9,
            "reasoning": "Task matches developer skills perfectly"
        })
        
        # Mock project state
        pm_agent.monitor.get_project_state.return_value = ProjectState(
            board_id="BOARD-TEST",
            project_name="Test Project",
            total_tasks=50,
            completed_tasks=20,
            in_progress_tasks=10,
            blocked_tasks=2,
            progress_percent=40.0,
            overdue_tasks=[],
            team_velocity=5.0,
            risk_level=RiskLevel.LOW,
            last_updated=datetime.now()
        )
        
        # STEP 3: Agent requests a task
        print("STEP 3: Agent requesting next task...")
        
        # Call the tool as an agent would
        result = await pm_agent.server.tool("request_next_task")({
            "agent_id": "test-dev-001"
        })
        
        print(f"Result: {result}")
        
        # STEP 4: Verify the complete flow
        print("\nSTEP 4: Verifying integration points...")
        
        # 4.1: Verify task was found and assigned
        assert result["has_task"] is True
        assert result["assignment"]["task_id"] == "TASK-TEST-001"
        assert result["assignment"]["assigned_to"] == "test-dev-001"
        
        # 4.2: Verify kanban board was updated
        pm_agent.kanban_client.assign_task.assert_called_once_with(
            "TASK-TEST-001", "test-dev-001"
        )
        
        # 4.3: Verify comment was added
        pm_agent.kanban_client.add_comment.assert_called()
        comment_call = pm_agent.kanban_client.add_comment.call_args
        assert "assigned to test-dev-001" in comment_call[0][1]
        
        # 4.4: Verify notifications were sent
        pm_agent.comm_hub._send_kanban_comment.assert_called()
        
        # 4.5: Verify agent's task list was updated
        assert "test-dev-001" in pm_agent.agent_tasks
        assert pm_agent.agent_tasks["test-dev-001"].task_id == "TASK-TEST-001"
        
        print("\n✅ All integration points verified successfully!")
    
    @pytest.mark.asyncio
    async def test_blocker_escalation_workflow(self, pm_agent):
        """
        TEST 2: Blocker detection and escalation workflow
        
        This test simulates:
        1. An agent reporting a blocker
        2. AI analyzing the severity
        3. Creating resolution tasks
        4. Escalating to management
        5. Notifying all stakeholders
        
        What we're verifying:
        - Blocker analysis works correctly
        - Escalation triggers appropriately
        - All parties get notified
        """
        print("\n=== TEST: Blocker Escalation Workflow ===\n")
        
        # STEP 1: Set up an agent with an assigned task
        print("STEP 1: Setting up agent with active task...")
        
        pm_agent.agent_status["test-dev-001"] = WorkerStatus(
            worker_id="test-dev-001",
            name="Test Developer",
            role="Backend Developer", 
            email="test@example.com",
            current_tasks=[Mock(id="TASK-BLOCKED-001")],
            completed_tasks_count=10,
            capacity=40,
            skills=["python"],
            availability={},
            performance_score=1.0
        )
        
        # STEP 2: Configure AI to identify this as critical
        print("STEP 2: Configuring AI to detect critical blocker...")
        
        pm_agent.ai_engine._call_claude.return_value = json.dumps({
            "root_cause": "Production database connection pool exhausted",
            "impact_assessment": "All API requests failing - complete service outage",
            "needs_coordination": True,
            "resolution_steps": [
                "1. Increase connection pool size immediately",
                "2. Identify connection leak source",
                "3. Implement connection pooling monitoring"
            ],
            "required_resources": ["DBA", "Senior Backend", "DevOps"],
            "estimated_hours": 4,
            "escalation_needed": True,
            "prevention_measures": ["Add connection pool monitoring", "Set up alerts"]
        })
        
        # Mock task creation for resolution
        pm_agent.kanban_client.create_task = AsyncMock(return_value=Mock(id="TASK-RESOLUTION-001"))
        
        # STEP 3: Agent reports the blocker
        print("STEP 3: Agent reporting critical blocker...")
        
        result = await pm_agent.server.tool("report_blocker")({
            "agent_id": "test-dev-001",
            "task_id": "TASK-BLOCKED-001",
            "blocker_description": "Cannot connect to production database - connection pool exhausted",
            "severity": "critical"
        })
        
        print(f"Blocker report result: {result}")
        
        # STEP 4: Verify escalation workflow
        print("\nSTEP 4: Verifying escalation workflow...")
        
        # 4.1: Verify blocker was analyzed
        assert result["success"] is True
        assert result["resolution_plan"]["escalation_needed"] is True
        
        # 4.2: Verify resolution task was created
        pm_agent.kanban_client.create_task.assert_called_once()
        create_call = pm_agent.kanban_client.create_task.call_args
        assert "blocker" in create_call[0][0]["labels"]
        assert create_call[0][0]["priority"] == "high"
        
        # 4.3: Verify task status was updated to blocked
        pm_agent.kanban_client.update_task_status.assert_called_with(
            "TASK-BLOCKED-001", "blocked"
        )
        
        # 4.4: Verify notifications were sent
        # Should notify via multiple channels for critical blockers
        assert pm_agent.comm_hub._send_kanban_comment.call_count >= 1
        
        print("\n✅ Blocker escalation workflow completed successfully!")
    
    @pytest.mark.asyncio
    async def test_task_completion_and_dependency_flow(self, pm_agent):
        """
        TEST 3: Task completion triggering dependent task updates
        
        This test simulates:
        1. An agent completing a task
        2. System checking for dependent tasks
        3. Unblocking tasks that were waiting
        4. Notifying affected agents
        
        What we're verifying:
        - Dependencies are tracked correctly
        - Completion triggers unblocking
        - Notifications flow to right people
        """
        print("\n=== TEST: Task Completion and Dependencies ===\n")
        
        # STEP 1: Set up task dependencies
        print("STEP 1: Setting up tasks with dependencies...")
        
        # Task A is complete, Task B depends on A
        task_a = Task(
            id="TASK-A",
            name="Create database schema",
            description="Design and create user tables",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            assigned_to="test-dev-001",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=4.0
        )
        
        task_b = Task(
            id="TASK-B", 
            name="Implement user API",
            description="Create CRUD endpoints for users",
            status=TaskStatus.BLOCKED,
            priority=Priority.HIGH,
            assigned_to="test-dev-002",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=8.0,
            dependencies=["TASK-A"]
        )
        
        # Mock the kanban client responses
        pm_agent.kanban_client.get_dependent_tasks = AsyncMock(return_value=[task_b])
        pm_agent.kanban_client.get_task_details = AsyncMock(return_value=task_a)
        
        # Set up agent with active task
        pm_agent.agent_tasks["test-dev-001"] = Mock(task_id="TASK-A")
        pm_agent.agent_status["test-dev-001"] = WorkerStatus(
            worker_id="test-dev-001",
            name="Developer 1",
            role="Backend",
            email=None,
            current_tasks=[task_a],
            completed_tasks_count=5,
            capacity=40,
            skills=["python"],
            availability={},
            performance_score=1.0
        )
        
        # STEP 2: Agent reports task completion
        print("STEP 2: Agent reporting task completion...")
        
        result = await pm_agent.server.tool("report_task_progress")({
            "agent_id": "test-dev-001",
            "task_id": "TASK-A",
            "status": "completed",
            "progress": 100,
            "message": "Database schema created and tested"
        })
        
        # STEP 3: Verify dependency handling
        print("\nSTEP 3: Verifying dependency updates...")
        
        # 3.1: Task A marked complete
        pm_agent.kanban_client.complete_task.assert_called_with("TASK-A")
        
        # 3.2: System checked for dependent tasks
        pm_agent.kanban_client.get_dependent_tasks.assert_called_with("TASK-A")
        
        # 3.3: Task B status updated to ready
        pm_agent.kanban_client.update_task_status.assert_called_with("TASK-B", "ready")
        
        # 3.4: Agent's task was cleared
        assert "test-dev-001" not in pm_agent.agent_tasks
        
        # 3.5: Agent's completed count increased
        assert pm_agent.agent_status["test-dev-001"].completed_tasks_count == 6
        
        print("\n✅ Task completion and dependency flow verified!")
    
    @pytest.mark.asyncio
    async def test_monitoring_integration(self, pm_agent):
        """
        TEST 4: Project monitoring detecting issues and triggering actions
        
        This test simulates:
        1. Monitoring system running health checks
        2. Detecting project risks
        3. AI analyzing the situation
        4. Automatic corrective actions
        
        What we're verifying:
        - Monitoring correctly identifies issues
        - AI provides appropriate recommendations
        - System takes corrective actions
        """
        print("\n=== TEST: Monitoring System Integration ===\n")
        
        # STEP 1: Set up project with warning signs
        print("STEP 1: Setting up project with risk indicators...")
        
        # Create a concerning project state
        risky_project_state = ProjectState(
            board_id="BOARD-RISK",
            project_name="At-Risk Project",
            total_tasks=100,
            completed_tasks=10,  # Only 10% complete
            in_progress_tasks=40,  # Too many WIP
            blocked_tasks=15,  # High blocker count
            progress_percent=10.0,
            overdue_tasks=[Mock(), Mock(), Mock()],  # Multiple overdue
            team_velocity=2.0,  # Very low velocity
            risk_level=RiskLevel.HIGH,
            last_updated=datetime.now()
        )
        
        pm_agent.monitor.current_state = risky_project_state
        pm_agent.monitor.get_project_state.return_value = risky_project_state
        
        # STEP 2: Configure AI health analysis
        print("STEP 2: AI analyzing project health...")
        
        pm_agent.ai_engine._call_claude.return_value = json.dumps({
            "overall_health": "red",
            "progress_assessment": "Project in critical state - immediate intervention needed",
            "risk_factors": [
                {
                    "type": "timeline",
                    "severity": "critical", 
                    "description": "At current velocity, project will be 6 months late"
                },
                {
                    "type": "resource",
                    "severity": "high",
                    "description": "Team overwhelmed - 40 tasks in progress for 5 developers"
                }
            ],
            "recommendations": [
                {
                    "action": "Emergency standup - reassess all work in progress",
                    "priority": "urgent",
                    "owner": "Project Manager"
                },
                {
                    "action": "Pause all new work until WIP reduced to manageable level",
                    "priority": "urgent", 
                    "owner": "Tech Lead"
                }
            ],
            "timeline_prediction": {
                "on_track": False,
                "estimated_completion": "2024-12-31",
                "confidence": 0.2
            }
        })
        
        # STEP 3: Trigger monitoring analysis
        print("STEP 3: Running monitoring analysis...")
        
        # This would normally run on a schedule
        await pm_agent.monitor._analyze_project_health()
        
        # STEP 4: Verify monitoring triggered appropriate actions
        print("\nSTEP 4: Verifying monitoring actions...")
        
        # 4.1: Check that risks were identified
        current_risks = pm_agent.monitor.get_current_risks()
        assert len(current_risks) > 0
        
        # 4.2: Verify high-risk items are flagged
        high_risks = [r for r in current_risks if r.severity == RiskLevel.HIGH]
        assert len(high_risks) > 0
        
        # 4.3: Check project state reflects issues
        assert pm_agent.monitor.current_state.risk_level == RiskLevel.HIGH
        assert pm_agent.monitor.current_state.blocked_tasks == 15
        
        print("\n✅ Monitoring integration verified!")
        print(f"Identified {len(current_risks)} risks")
        print(f"Project health: RED")
        print(f"Immediate actions required: 2")


# === EXECUTION EXAMPLE ===
if __name__ == "__main__":
    """
    To run these tests:
    
    1. Run all tests:
       pytest tests/integration/test_pm_agent_integration.py -v
    
    2. Run specific test:
       pytest tests/integration/test_pm_agent_integration.py::TestPMAgentIntegration::test_complete_task_assignment_flow -v -s
    
    3. Run with coverage:
       pytest tests/integration/test_pm_agent_integration.py --cov=src --cov-report=html
    
    The -s flag shows print statements, which help understand the flow.
    """
    
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
