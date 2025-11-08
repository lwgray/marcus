"""
Unit tests for the Context system
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.context import Context, Decision, DependentTask, TaskContext
from src.core.events import Events, EventTypes
from src.core.models import Priority, Task, TaskStatus


class TestTaskContext:
    """Test suite for TaskContext dataclass"""

    def test_task_context_creation(self):
        """Test creating a TaskContext"""
        context = TaskContext(
            task_id="task_123",
            previous_implementations={"task_1": {"apis": ["GET /users"]}},
            dependent_tasks=[{"task_id": "task_2", "task_name": "Frontend"}],
            related_patterns=[{"type": "api", "pattern": "REST"}],
            architectural_decisions=[{"what": "Use JWT", "why": "Stateless"}],
        )

        assert context.task_id == "task_123"
        assert "task_1" in context.previous_implementations
        assert len(context.dependent_tasks) == 1
        assert len(context.related_patterns) == 1
        assert len(context.architectural_decisions) == 1

    def test_task_context_to_dict(self):
        """Test converting TaskContext to dictionary"""
        context = TaskContext(
            task_id="task_123",
            previous_implementations={"task_1": {"apis": ["GET /users"]}},
        )

        result = context.to_dict()

        assert result["task_id"] == "task_123"
        assert "previous_implementations" in result
        assert "dependent_tasks" in result


class TestDependentTask:
    """Test suite for DependentTask dataclass"""

    def test_dependent_task_creation(self):
        """Test creating a DependentTask"""
        dep_task = DependentTask(
            task_id="task_2",
            task_name="Login UI",
            expected_interface="/auth/login endpoint",
        )

        assert dep_task.task_id == "task_2"
        assert dep_task.task_name == "Login UI"
        assert dep_task.expected_interface == "/auth/login endpoint"
        assert dep_task.dependency_type == "functional"


class TestDecision:
    """Test suite for Decision dataclass"""

    def test_decision_creation(self):
        """Test creating a Decision"""
        decision = Decision(
            decision_id="dec_1",
            task_id="task_123",
            agent_id="agent_1",
            timestamp=datetime.now(timezone.utc),
            what="Use PostgreSQL",
            why="Need ACID compliance",
            impact="All services must use SQL",
        )

        assert decision.decision_id == "dec_1"
        assert decision.task_id == "task_123"
        assert decision.agent_id == "agent_1"
        assert decision.what == "Use PostgreSQL"

    def test_decision_to_dict(self):
        """Test converting Decision to dictionary"""
        timestamp = datetime.now(timezone.utc)
        decision = Decision(
            decision_id="dec_1",
            task_id="task_123",
            agent_id="agent_1",
            timestamp=timestamp,
            what="Use JWT",
            why="Stateless auth",
            impact="All APIs need JWT validation",
        )

        result = decision.to_dict()

        assert result["decision_id"] == "dec_1"
        assert result["timestamp"] == timestamp.isoformat()
        assert result["what"] == "Use JWT"


class TestContext:
    """Test suite for Context system"""

    @pytest.fixture
    def context(self):
        """Create a Context instance for testing"""
        return Context()

    @pytest.fixture
    def context_with_events(self):
        """Create a Context instance with Events system"""
        events = Events()
        return Context(events=events)

    def test_initialization(self, context):
        """Test Context initialization"""
        assert context.implementations == {}
        assert context.dependencies == {}
        assert context.decisions == []
        assert context.patterns == {}
        assert context._decision_counter == 0

    @pytest.mark.asyncio
    async def test_add_implementation(self, context):
        """Test adding implementation details"""
        await context.add_implementation(
            "task_1",
            {
                "apis": ["GET /users", "POST /users"],
                "models": ["User"],
                "patterns": [{"type": "rest", "name": "RESTful API"}],
            },
        )

        assert "task_1" in context.implementations
        assert "apis" in context.implementations["task_1"]
        assert len(context.implementations["task_1"]["apis"]) == 2
        assert "rest" in context.patterns

    @pytest.mark.asyncio
    async def test_add_implementation_with_events(self, context_with_events):
        """Test that adding implementation triggers events"""
        handler = AsyncMock()
        context_with_events.events.subscribe(EventTypes.IMPLEMENTATION_FOUND, handler)

        await context_with_events.add_implementation("task_1", {"apis": ["GET /users"]})

        handler.assert_called_once()
        event = handler.call_args[0][0]
        assert event.event_type == EventTypes.IMPLEMENTATION_FOUND
        assert event.data["task_id"] == "task_1"

    def test_add_dependency(self, context):
        """Test adding task dependencies"""
        dep_task = DependentTask(
            task_id="task_2",
            task_name="Frontend Login",
            expected_interface="/auth/login endpoint",
        )

        context.add_dependency("task_1", dep_task)

        assert "task_1" in context.dependencies
        assert len(context.dependencies["task_1"]) == 1
        assert context.dependencies["task_1"][0].task_name == "Frontend Login"

    @pytest.mark.asyncio
    async def test_log_decision(self, context):
        """Test logging architectural decisions"""
        decision = await context.log_decision(
            agent_id="agent_1",
            task_id="task_123",
            what="Use JWT for authentication",
            why="Need stateless auth for mobile apps",
            impact="All endpoints must validate JWT tokens",
        )

        assert decision.decision_id.startswith("dec_")
        assert decision.agent_id == "agent_1"
        assert decision.task_id == "task_123"
        assert len(context.decisions) == 1

    @pytest.mark.asyncio
    async def test_log_decision_with_events(self, context_with_events):
        """Test that logging decision triggers events"""
        handler = AsyncMock()
        context_with_events.events.subscribe(EventTypes.DECISION_LOGGED, handler)

        await context_with_events.log_decision(
            "agent_1", "task_123", "Use PostgreSQL", "Need ACID", "All services use SQL"
        )

        handler.assert_called_once()
        event = handler.call_args[0][0]
        assert event.event_type == EventTypes.DECISION_LOGGED
        assert event.data["what"] == "Use PostgreSQL"

    @pytest.mark.asyncio
    async def test_get_context_empty(self, context):
        """Test getting context for a task with no dependencies"""
        task_context = await context.get_context("task_123", [])

        assert task_context.task_id == "task_123"
        assert len(task_context.previous_implementations) == 0
        assert len(task_context.dependent_tasks) == 0

    @pytest.mark.asyncio
    async def test_get_context_with_dependencies(self, context):
        """Test getting context with implementations and dependencies"""
        # Add some implementations
        await context.add_implementation(
            "task_1", {"apis": ["GET /users"], "models": ["User"]}
        )

        # Add dependent tasks
        context.add_dependency(
            "task_123", DependentTask("task_2", "Frontend", "/api/data")
        )

        # Log a decision
        await context.log_decision(
            "agent_1", "task_1", "Use REST", "Standard approach", "task_123"
        )

        # Get context
        task_context = await context.get_context("task_123", ["task_1"])

        assert "task_1" in task_context.previous_implementations
        assert len(task_context.dependent_tasks) == 1
        assert task_context.dependent_tasks[0]["task_name"] == "Frontend"
        assert len(task_context.architectural_decisions) > 0

    def test_analyze_dependencies(self, context):
        """Test analyzing task dependencies"""
        from datetime import datetime

        from src.core.models import Priority, TaskStatus

        tasks = [
            Task(
                id="task_1",
                name="Backend API",
                description="Build API",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=8.0,
                labels=["backend", "api"],
                dependencies=[],
            ),
            Task(
                id="task_2",
                name="Frontend UI",
                description="Build UI",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=6.0,
                labels=["frontend", "ui"],
                dependencies=["task_1"],
            ),
            Task(
                id="task_3",
                name="API Tests",
                description="Test API",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=4.0,
                labels=["test", "api"],
                dependencies=[],
            ),
        ]

        async def run_test():
            dep_map = await context.analyze_dependencies(tasks)

            # task_1 should have task_2 as dependent (direct dependency)
            assert "task_1" in dep_map
            assert "task_2" in dep_map["task_1"]

            # task_1 might have task_3 as dependent (inferred)
            # This depends on inference rules

        import asyncio

        asyncio.run(run_test())

    def test_infer_dependency(self, context):
        """Test dependency inference logic"""
        from datetime import datetime

        from src.core.models import Priority, TaskStatus

        backend_task = Task(
            id="task_1",
            name="User API",
            description="User API implementation",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=8.0,
            labels=["backend", "api"],
        )

        frontend_task = Task(
            id="task_2",
            name="User Dashboard",
            description="User dashboard interface",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=6.0,
            labels=["frontend", "ui"],
        )

        test_task = Task(
            id="task_3",
            name="API Tests",
            description="API testing suite",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=4.0,
            labels=["test"],
        )

        # Frontend should depend on backend
        assert context._infer_dependency(frontend_task, backend_task) is True

        # Tests should depend on implementation
        assert context._infer_dependency(test_task, backend_task) is True

        # Backend should not depend on frontend
        assert context._infer_dependency(backend_task, frontend_task) is False

    @pytest.mark.asyncio
    async def test_get_decisions_for_task(self, context):
        """Test getting decisions for a specific task"""
        await context.log_decision(
            "agent_1", "task_1", "Decision 1", "Why 1", "Impact 1"
        )
        await context.log_decision(
            "agent_2", "task_2", "Decision 2", "Why 2", "Impact 2"
        )
        await context.log_decision(
            "agent_1", "task_1", "Decision 3", "Why 3", "Impact 3"
        )

        task_1_decisions = await context.get_decisions_for_task("task_1")

        assert len(task_1_decisions) == 2
        assert all(d.task_id == "task_1" for d in task_1_decisions)

    @pytest.mark.asyncio
    async def test_get_implementation_summary(self, context):
        """Test getting implementation summary"""
        await context.add_implementation("task_1", {"apis": ["GET /users"]})
        await context.add_implementation("task_2", {"apis": ["GET /posts"]})
        await context.log_decision("agent_1", "task_1", "Use REST", "Standard", "All")

        summary = await context.get_implementation_summary()

        assert summary["total_implementations"] == 2
        assert summary["total_decisions"] == 1
        assert "recent_implementations" in summary

    @pytest.mark.asyncio
    async def test_clear_old_data(self, context):
        """Test clearing old context data"""
        # Add current data
        await context.add_implementation("task_1", {"apis": ["GET /users"]})

        # Add old decision (mock old timestamp)
        old_decision = Decision(
            decision_id="old_1",
            task_id="old_task",
            agent_id="agent_1",
            timestamp=datetime.now(timezone.utc) - timedelta(days=40),
            what="Old decision",
            why="Old reason",
            impact="Old impact",
        )
        context.decisions.append(old_decision)

        # Add recent decision
        await context.log_decision(
            "agent_2", "task_2", "Recent decision", "Recent reason", "Recent impact"
        )

        # Should have 2 decisions before clearing
        assert len(context.decisions) == 2

        # Clear data older than 30 days
        await context.clear_old_data(days=30)

        # Should only have 1 recent decision
        assert len(context.decisions) == 1
        assert context.decisions[0].what == "Recent decision"

    @pytest.mark.asyncio
    async def test_pattern_extraction(self, context):
        """Test pattern extraction from implementations"""
        await context.add_implementation(
            "task_1",
            {
                "patterns": [
                    {"type": "auth", "name": "JWT"},
                    {"type": "api", "name": "REST"},
                ]
            },
        )

        await context.add_implementation(
            "task_2",
            {
                "patterns": [
                    {"type": "auth", "name": "OAuth"},
                    {"type": "api", "name": "GraphQL"},
                ]
            },
        )

        # Check patterns were extracted
        assert "auth" in context.patterns
        assert "api" in context.patterns
        assert len(context.patterns["auth"]) == 2
        assert len(context.patterns["api"]) == 2
