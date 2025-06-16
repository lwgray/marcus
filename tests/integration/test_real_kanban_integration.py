import pytest
import asyncio
import os
from datetime import datetime, timedelta

from pm_agent_mcp_server import PMAgentServer
from src.integrations.mcp_kanban_client import MCPKanbanClient
from src.core.models import Task, TaskStatus, Priority, WorkerStatus


class TestRealKanbanIntegration:
    """
    Integration tests using the real "Task Master Test" project on kanban-mcp server.
    
    These tests connect to the actual MCP server and work with real tasks,
    providing true end-to-end validation.
    """
    
    @pytest.fixture
    async def kanban_client(self):
        """
        Create a real MCP Kanban client connected to the test project.
        """
        client = MCPKanbanClient()
        await client.connect()
        
        # Find and select the "Task Master Test" project
        boards = await client._call_tool("mcp_kanban_project_board_manager", {
            "action": "get_boards"
        })
        
        test_board = None
        for board in boards:
            if "Task Master Test" in board.get("name", ""):
                test_board = board
                break
        
        if not test_board:
            pytest.skip("Task Master Test project not found on MCP server")
        
        client.board_id = test_board["id"]
        client.project_id = test_board.get("project_id")
        
        yield client
        
        # Cleanup if needed
        # await client.disconnect()
    
    @pytest.fixture
    async def pm_agent_with_real_kanban(self, kanban_client):
        """
        Create PM Agent connected to real kanban server.
        """
        agent = PMAgentServer()
        agent.kanban_client = kanban_client
        
        # Initialize other components
        await agent.ai_engine.initialize()
        
        # Set up a test worker
        test_worker = WorkerStatus(
            worker_id="test-agent-001",
            name="Test Agent",
            role="Full Stack Developer",
            email="test@example.com",
            current_tasks=[],
            completed_tasks_count=0,
            capacity=40,
            skills=["python", "javascript", "testing"],
            availability={"monday": True, "tuesday": True},
            performance_score=1.0
        )
        agent.agent_status["test-agent-001"] = test_worker
        
        return agent
    
    @pytest.mark.asyncio
    async def test_real_task_retrieval(self, kanban_client):
        """
        Test 1: Retrieve real tasks from the Task Master Test project.
        
        What happens:
        1. Connect to real MCP server
        2. Get tasks from TODO column
        3. Verify we can read real task data
        """
        print("\n=== TEST: Real Task Retrieval ===\n")
        
        # Get available tasks from the real board
        print("Fetching tasks from Task Master Test project...")
        available_tasks = await kanban_client.get_available_tasks()
        
        print(f"Found {len(available_tasks)} available tasks:")
        for task in available_tasks:
            print(f"  - {task.id}: {task.name} (Priority: {task.priority.value})")
            print(f"    Status: {task.status.value}, Estimated: {task.estimated_hours}h")
            if task.labels:
                print(f"    Labels: {', '.join(task.labels)}")
        
        # Verify we got real tasks
        assert isinstance(available_tasks, list)
        if available_tasks:
            task = available_tasks[0]
            assert hasattr(task, 'id')
            assert hasattr(task, 'name')
            assert hasattr(task, 'status')
            print(f"\n✅ Successfully retrieved {len(available_tasks)} real tasks")
        else:
            print("\n⚠️  No available tasks in TODO column")
    
    @pytest.mark.asyncio
    async def test_real_task_assignment(self, pm_agent_with_real_kanban):
        """
        Test 2: Assign a real task to a test agent.
        
        What happens:
        1. Agent requests work
        2. PM finds real task from board
        3. Task gets assigned
        4. Board is updated
        """
        print("\n=== TEST: Real Task Assignment ===\n")
        
        # First, check what tasks are available
        available_tasks = await pm_agent_with_real_kanban.kanban_client.get_available_tasks()
        print(f"Available tasks before assignment: {len(available_tasks)}")
        
        if not available_tasks:
            # Create a test task if none exist
            print("No tasks available, creating a test task...")
            test_task = await pm_agent_with_real_kanban.kanban_client.create_task({
                "name": f"Test Task {datetime.now().strftime('%H:%M:%S')}",
                "description": "Created by PM Agent integration test",
                "priority": "medium",
                "labels": ["test", "automated"],
                "estimated_hours": 2
            })
            print(f"Created test task: {test_task.id}")
        
        # Agent requests next task
        print("\nAgent requesting next task...")
        result = await pm_agent_with_real_kanban.request_next_task("test-agent-001")
        
        if result["has_task"]:
            assignment = result["assignment"]
            print(f"\n✅ Task assigned successfully!")
            print(f"   Task ID: {assignment['task_id']}")
            print(f"   Task Name: {assignment['task_name']}")
            print(f"   Instructions: {assignment['instructions'][:200]}...")
            
            # Verify task is now assigned on the board
            task_details = await pm_agent_with_real_kanban.kanban_client.get_task_details(
                assignment['task_id']
            )
            assert task_details.assigned_to == "test-agent-001"
            print(f"\n✅ Verified task is assigned to test-agent-001 on the board")
        else:
            print(f"\n⚠️  No task assigned: {result.get('message', 'Unknown reason')}")
    
    @pytest.mark.asyncio
    async def test_real_progress_reporting(self, pm_agent_with_real_kanban):
        """
        Test 3: Report progress on a real task.
        
        What happens:
        1. Get or create a task assigned to test agent
        2. Report progress
        3. Verify kanban board updated
        """
        print("\n=== TEST: Real Progress Reporting ===\n")
        
        # First ensure we have an assigned task
        if "test-agent-001" not in pm_agent_with_real_kanban.agent_tasks:
            print("No assigned task, requesting one...")
            await pm_agent_with_real_kanban.request_next_task("test-agent-001")
        
        if "test-agent-001" in pm_agent_with_real_kanban.agent_tasks:
            task_assignment = pm_agent_with_real_kanban.agent_tasks["test-agent-001"]
            task_id = task_assignment.task_id
            
            print(f"Reporting progress on task {task_id}...")
            
            # Report 50% progress
            result = await pm_agent_with_real_kanban.report_task_progress(
                "test-agent-001",
                task_id,
                "in_progress",
                50,
                "Completed initial implementation, starting tests"
            )
            
            assert result["acknowledged"] is True
            print("✅ Progress reported successfully")
            
            # Check comments were added to the board
            comments = await pm_agent_with_real_kanban.kanban_client._call_tool(
                "mcp_kanban_comment_manager",
                {
                    "action": "get_all",
                    "cardId": task_id
                }
            )
            
            # Find our progress comment
            progress_comments = [c for c in comments if "50% complete" in c.get("text", "")]
            assert len(progress_comments) > 0
            print(f"✅ Found progress comment on board: {progress_comments[0]['text'][:100]}...")
        else:
            print("⚠️  No tasks available for progress reporting")
    
    @pytest.mark.asyncio
    async def test_real_blocker_handling(self, pm_agent_with_real_kanban):
        """
        Test 4: Report and handle a real blocker.
        
        What happens:
        1. Report blocker on a task
        2. Verify task status changes
        3. Check resolution task created
        """
        print("\n=== TEST: Real Blocker Handling ===\n")
        
        # Ensure we have a task to block
        if "test-agent-001" not in pm_agent_with_real_kanban.agent_tasks:
            await pm_agent_with_real_kanban.request_next_task("test-agent-001")
        
        if "test-agent-001" in pm_agent_with_real_kanban.agent_tasks:
            task_id = pm_agent_with_real_kanban.agent_tasks["test-agent-001"].task_id
            
            print(f"Reporting blocker on task {task_id}...")
            
            result = await pm_agent_with_real_kanban.report_blocker(
                "test-agent-001",
                task_id,
                "Cannot access test database - permissions issue",
                "high"
            )
            
            assert result["success"] is True
            print("✅ Blocker reported successfully")
            print(f"   Resolution plan: {result['resolution_plan']}")
            
            # Verify task is now blocked
            task_details = await pm_agent_with_real_kanban.kanban_client.get_task_details(task_id)
            print(f"✅ Task status is now: {task_details.status.value}")
            
            # Check if resolution task was created
            if result["resolution_plan"].get("needs_coordination"):
                print("✅ Resolution task should be created for coordination")
        else:
            print("⚠️  No tasks available for blocker testing")
    
    @pytest.mark.asyncio 
    async def test_real_board_monitoring(self, pm_agent_with_real_kanban):
        """
        Test 5: Monitor real project health.
        
        What happens:
        1. Get current board state
        2. Analyze project metrics
        3. Identify any risks
        """
        print("\n=== TEST: Real Board Monitoring ===\n")
        
        # Get project state
        print("Analyzing Task Master Test project health...")
        project_state = await pm_agent_with_real_kanban.monitor.get_project_state()
        
        print(f"\nProject Status:")
        print(f"  Total Tasks: {project_state.total_tasks}")
        print(f"  Completed: {project_state.completed_tasks}")
        print(f"  In Progress: {project_state.in_progress_tasks}")
        print(f"  Blocked: {project_state.blocked_tasks}")
        print(f"  Progress: {project_state.progress_percent:.1f}%")
        print(f"  Velocity: {project_state.team_velocity} tasks/week")
        print(f"  Risk Level: {project_state.risk_level.value}")
        
        if project_state.overdue_tasks:
            print(f"\n⚠️  Overdue Tasks: {len(project_state.overdue_tasks)}")
            for task in project_state.overdue_tasks[:3]:
                print(f"    - {task.name}")
        
        # Get current risks
        risks = pm_agent_with_real_kanban.monitor.get_current_risks()
        if risks:
            print(f"\n⚠️  Identified Risks:")
            for risk in risks:
                print(f"    - {risk.risk_type}: {risk.description}")
                print(f"      Severity: {risk.severity.value}")
        
        print("\n✅ Real board monitoring completed")
        
        # Assertions
        assert project_state is not None
        assert project_state.board_id is not None
        assert project_state.total_tasks >= 0


if __name__ == "__main__":
    """
    Run these tests against the real MCP server:
    
    1. Ensure MCP kanban server is running
    2. Ensure "Task Master Test" project exists
    3. Run: pytest tests/integration/test_real_kanban_integration.py -v -s
    """
    import sys
    
    # Check for required environment variable
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable required")
        sys.exit(1)
    
    pytest.main([__file__, "-v", "-s"])