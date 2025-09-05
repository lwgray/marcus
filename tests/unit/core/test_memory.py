"""
Unit tests for the Memory system
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.events import Events, EventTypes
from src.core.memory import AgentProfile, Memory, TaskOutcome, TaskPattern
from src.core.models import Priority, Task, TaskStatus


class TestTaskOutcome:
    """Test suite for TaskOutcome dataclass"""

    def test_task_outcome_creation(self):
        """Test creating a TaskOutcome"""
        outcome = TaskOutcome(
            task_id="task_1",
            agent_id="agent_1",
            task_name="Build API",
            estimated_hours=8.0,
            actual_hours=10.0,
            success=True,
            blockers=["database_connection"],
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )

        assert outcome.task_id == "task_1"
        assert outcome.actual_hours == 10.0
        assert outcome.success is True
        assert len(outcome.blockers) == 1

    def test_estimation_accuracy(self):
        """Test estimation accuracy calculation"""
        # Perfect estimate
        outcome1 = TaskOutcome(
            task_id="task_1",
            agent_id="agent_1",
            task_name="Task",
            estimated_hours=8.0,
            actual_hours=8.0,
            success=True,
        )
        assert outcome1.estimation_accuracy == 1.0

        # Underestimate
        outcome2 = TaskOutcome(
            task_id="task_2",
            agent_id="agent_1",
            task_name="Task",
            estimated_hours=8.0,
            actual_hours=10.0,
            success=True,
        )
        assert outcome2.estimation_accuracy == 0.8

        # Overestimate
        outcome3 = TaskOutcome(
            task_id="task_3",
            agent_id="agent_1",
            task_name="Task",
            estimated_hours=10.0,
            actual_hours=8.0,
            success=True,
        )
        assert outcome3.estimation_accuracy == 0.8

    def test_task_outcome_to_dict(self):
        """Test converting TaskOutcome to dictionary"""
        now = datetime.now()
        outcome = TaskOutcome(
            task_id="task_1",
            agent_id="agent_1",
            task_name="Build API",
            estimated_hours=8.0,
            actual_hours=10.0,
            success=True,
            started_at=now,
            completed_at=now + timedelta(hours=10),
        )

        result = outcome.to_dict()

        assert result["task_id"] == "task_1"
        assert result["actual_hours"] == 10.0
        assert result["estimation_accuracy"] == 0.8
        assert "started_at" in result
        assert "completed_at" in result


class TestAgentProfile:
    """Test suite for AgentProfile dataclass"""

    def test_agent_profile_creation(self):
        """Test creating an AgentProfile"""
        profile = AgentProfile(
            agent_id="agent_1",
            total_tasks=10,
            successful_tasks=8,
            failed_tasks=2,
            blocked_tasks=3,
        )

        assert profile.agent_id == "agent_1"
        assert profile.total_tasks == 10
        assert profile.successful_tasks == 8

    def test_success_rate(self):
        """Test success rate calculation"""
        profile = AgentProfile(agent_id="agent_1", total_tasks=10, successful_tasks=8)

        assert profile.success_rate == 0.8

        # Empty profile
        empty_profile = AgentProfile(agent_id="agent_2")
        assert empty_profile.success_rate == 0.0

    def test_blockage_rate(self):
        """Test blockage rate calculation"""
        profile = AgentProfile(agent_id="agent_1", total_tasks=10, blocked_tasks=3)

        assert profile.blockage_rate == 0.3


class TestMemory:
    """Test suite for Memory system"""

    @pytest.fixture
    def memory(self):
        """Create a Memory instance for testing"""
        return Memory()

    @pytest.fixture
    def memory_with_events(self):
        """Create a Memory instance with Events"""
        events = Events()
        return Memory(events=events)

    @pytest.fixture
    def sample_task(self):
        """Create a sample task for testing"""
        return Task(
            id="task_1",
            name="Build User API",
            description="Create REST API",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=8.0,
            labels=["backend", "api"],
        )

    def test_initialization(self, memory):
        """Test Memory initialization"""
        assert memory.working["active_tasks"] == {}
        assert memory.episodic["outcomes"] == []
        assert memory.semantic["agent_profiles"] == {}
        assert memory.learning_rate == 0.1

    @pytest.mark.asyncio
    async def test_record_task_start(self, memory, sample_task):
        """Test recording task start"""
        await memory.record_task_start("agent_1", sample_task)

        assert "agent_1" in memory.working["active_tasks"]
        active = memory.working["active_tasks"]["agent_1"]
        assert active["task"].id == "task_1"
        assert "started_at" in active

    @pytest.mark.asyncio
    async def test_record_task_start_with_events(self, memory_with_events, sample_task):
        """Test that task start triggers events"""
        handler = AsyncMock()
        memory_with_events.events.subscribe(EventTypes.TASK_STARTED, handler)

        await memory_with_events.record_task_start("agent_1", sample_task)

        handler.assert_called_once()
        event = handler.call_args[0][0]
        assert event.data["task_id"] == "task_1"

    @pytest.mark.asyncio
    async def test_record_task_completion(self, memory, sample_task):
        """Test recording task completion"""
        # Start task first
        await memory.record_task_start("agent_1", sample_task)

        # Complete task
        outcome = await memory.record_task_completion(
            "agent_1",
            "task_1",
            success=True,
            actual_hours=10.0,
            blockers=["config_issue"],
        )

        assert outcome is not None
        assert outcome.success is True
        assert outcome.actual_hours == 10.0
        assert outcome.blockers == ["config_issue"]

        # Check episodic memory
        assert len(memory.episodic["outcomes"]) == 1
        assert memory.episodic["outcomes"][0] == outcome

        # Check agent profile was created
        assert "agent_1" in memory.semantic["agent_profiles"]
        profile = memory.semantic["agent_profiles"]["agent_1"]
        assert profile.total_tasks == 1
        assert profile.successful_tasks == 1
        assert profile.blocked_tasks == 1

        # Check working memory was cleared
        assert "agent_1" not in memory.working["active_tasks"]

    @pytest.mark.asyncio
    async def test_agent_profile_learning(self, memory, sample_task):
        """Test that agent profiles learn from outcomes"""
        # Complete multiple tasks
        for i in range(5):
            await memory.record_task_start("agent_1", sample_task)
            await memory.record_task_completion(
                "agent_1",
                "task_1",
                success=i < 4,  # 4 successes, 1 failure
                actual_hours=8.0,
            )

        profile = memory.semantic["agent_profiles"]["agent_1"]

        assert profile.total_tasks == 5
        assert profile.successful_tasks == 4
        assert profile.failed_tasks == 1
        assert profile.success_rate == 0.8

        # Check skill success rates
        assert "backend" in profile.skill_success_rates
        assert "api" in profile.skill_success_rates
        # With learning rate 0.1 and exponential moving average, after 4 successes then 1 failure:
        # Expected: ~0.31 (calculated as shown in exponential moving average)
        assert 0.25 < profile.skill_success_rates["backend"] < 0.35

    @pytest.mark.asyncio
    async def test_task_pattern_learning(self, memory, sample_task):
        """Test that task patterns are learned"""
        # Complete same type of task multiple times
        for i in range(3):
            await memory.record_task_start(f"agent_{i}", sample_task)
            await memory.record_task_completion(
                f"agent_{i}",
                "task_1",
                success=True,
                actual_hours=8.0 + i,  # Varying durations
            )

        # Check pattern was created
        pattern_key = "api_backend"  # Sorted labels
        assert pattern_key in memory.semantic["task_patterns"]

        pattern = memory.semantic["task_patterns"][pattern_key]
        assert pattern.task_labels == ["backend", "api"]
        assert 8.0 <= pattern.average_duration <= 10.0  # Should average the durations
        assert pattern.success_rate > 0.9  # All successful

    @pytest.mark.asyncio
    async def test_predict_task_outcome(self, memory, sample_task):
        """Test task outcome prediction"""
        # Build some history
        await memory.record_task_start("agent_1", sample_task)
        await memory.record_task_completion(
            "agent_1", "task_1", success=True, actual_hours=10.0
        )

        # Make prediction
        prediction = await memory.predict_task_outcome("agent_1", sample_task)

        assert "success_probability" in prediction
        assert "estimated_duration" in prediction
        assert "blockage_risk" in prediction
        assert "risk_factors" in prediction

        # With history, should have non-default values
        # With one success and exponential moving average with learning rate 0.1:
        # Initial: 0.0 * 0.9 + 1.0 * 0.1 = 0.1 
        assert prediction["success_probability"] == 0.1  # One success with learning rate 0.1
        assert prediction["estimated_duration"] != sample_task.estimated_hours

    @pytest.mark.asyncio
    async def test_find_similar_outcomes(self, memory):
        """Test finding similar task outcomes"""
        # Create some varied outcomes
        tasks = [
            ("Build User API", ["backend", "api"]),
            ("Create User Service", ["backend", "service"]),
            ("Build Product API", ["backend", "api"]),
            ("Design UI", ["frontend", "ui"]),
        ]

        for i, (name, labels) in enumerate(tasks):
            task = Task(
                id=f"task_{i}",
                name=name,
                description="Test",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=8.0,
                labels=labels,
            )
            await memory.record_task_start("agent_1", task)
            await memory.record_task_completion(
                "agent_1", f"task_{i}", success=True, actual_hours=8.0
            )

        # Find similar to "Build User API"
        search_task = Task(
            id="search",
            name="Build Authentication API",
            description="Test",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=8.0,
            labels=["backend", "api"],
        )

        similar = await memory.find_similar_outcomes(search_task, limit=2)

        assert len(similar) == 2
        # Should find other API tasks first
        assert "API" in similar[0].task_name

    def test_get_working_memory_summary(self, memory, sample_task):
        """Test working memory summary"""

        async def setup():
            await memory.record_task_start("agent_1", sample_task)
            await memory.record_task_start("agent_2", sample_task)

        asyncio.run(setup())

        summary = memory.get_working_memory_summary()

        assert summary["active_agents"] == 2
        assert len(summary["active_tasks"]) == 2
        assert summary["active_tasks"][0]["agent_id"] in ["agent_1", "agent_2"]

    def test_get_memory_stats(self, memory):
        """Test memory statistics"""

        async def setup():
            # Add some data
            task = Task(
                id="task_1",
                name="Test",
                description="Test",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=1.0,
            )
            await memory.record_task_start("agent_1", task)
            await memory.record_task_completion("agent_1", "task_1", True, 1.0)

        asyncio.run(setup())

        stats = memory.get_memory_stats()

        assert "working_memory" in stats
        assert "episodic_memory" in stats
        assert "semantic_memory" in stats
        assert "procedural_memory" in stats

        assert stats["episodic_memory"]["total_outcomes"] == 1
        assert stats["semantic_memory"]["agent_profiles"] == 1
