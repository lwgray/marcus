"""
Unit tests for Memory system predictive intelligence features
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from src.core.events import Events
from src.core.memory import AgentProfile, Memory, TaskOutcome
from src.core.models import Priority, Task, TaskStatus


class TestMemoryPredictions:
    """Test suite for predictive intelligence in Memory system"""

    @pytest.fixture
    def memory(self):
        """Create memory instance without persistence"""
        return Memory()

    @pytest.fixture
    def sample_task(self):
        """Create a sample task"""
        return Task(
            id="task-001",
            name="Implement user authentication",
            description="Add JWT-based auth",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=8.0,
            dependencies=[],
            labels=["backend", "authentication", "security"],
        )

    @pytest.fixture
    def agent_with_history(self, memory):
        """Create an agent with task history"""
        agent_id = "agent-001"

        # Add some task outcomes to build history
        outcomes = [
            TaskOutcome(
                task_id=f"task-{i}",
                agent_id=agent_id,
                task_name=f"Task {i}",
                estimated_hours=8.0,
                actual_hours=10.0 if i % 2 == 0 else 7.0,
                success=i % 3 != 0,  # Fail every 3rd task
                blockers=["API unavailable"] if i % 4 == 0 else [],
                started_at=datetime.now() - timedelta(days=i),
                completed_at=datetime.now() - timedelta(days=i - 1),
            )
            for i in range(1, 6)
        ]

        for outcome in outcomes:
            memory.episodic["outcomes"].append(outcome)

        # Build profile
        profile = AgentProfile(
            agent_id=agent_id,
            total_tasks=5,
            successful_tasks=3,
            failed_tasks=2,
            blocked_tasks=1,
            skill_success_rates={"backend": 0.7, "authentication": 0.8},
            average_estimation_accuracy=0.85,
            common_blockers={"API unavailable": 1},
        )
        memory.semantic["agent_profiles"][agent_id] = profile

        return agent_id

    @pytest.mark.asyncio
    async def test_predict_completion_time(
        self, memory, sample_task, agent_with_history
    ):
        """Test completion time prediction with confidence intervals"""
        result = await memory.predict_completion_time(agent_with_history, sample_task)

        assert "expected_hours" in result
        assert "confidence_interval" in result
        assert "factors" in result
        assert "confidence" in result

        # Check confidence interval logic
        assert result["confidence_interval"]["lower"] < result["expected_hours"]
        assert result["confidence_interval"]["upper"] > result["expected_hours"]
        assert result["confidence_interval"]["lower"] >= 0.5  # Minimum bound

        # With history, confidence should be higher
        assert result["confidence"] >= 0.6

    @pytest.mark.asyncio
    async def test_predict_blockage_probability(
        self, memory, sample_task, agent_with_history
    ):
        """Test blockage probability prediction"""
        result = await memory.predict_blockage_probability(
            agent_with_history, sample_task
        )

        assert "overall_risk" in result
        assert "risk_breakdown" in result
        assert "preventive_measures" in result
        assert "historical_blockers" in result

        # Check risk is within bounds
        assert 0 <= result["overall_risk"] <= 0.95

        # Authentication tasks should have higher risk
        assert "authentication_complexity" in result["risk_breakdown"]

        # Should suggest preventive measures for auth tasks
        assert any(
            "auth" in measure.lower() or "credential" in measure.lower()
            for measure in result["preventive_measures"]
        )

    @pytest.mark.asyncio
    async def test_predict_cascade_effects(self, memory):
        """Test cascade effect analysis"""
        # Create a task network
        tasks = [
            Task(
                id="task-1",
                name="Create API",
                description="",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=8.0,
                dependencies=[],
            ),
            Task(
                id="task-2",
                name="Create Frontend",
                description="",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=12.0,
                dependencies=["task-1"],
            ),
            Task(
                id="task-3",
                name="Integration Tests",
                description="",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=6.0,
                dependencies=["task-2"],
            ),
        ]

        # Update memory with tasks
        memory.update_project_tasks(tasks)

        # Predict cascade effects of 4-hour delay on task-1
        result = await memory.predict_cascade_effects("task-1", 4.0)

        assert "affected_tasks" in result
        assert "total_delay" in result
        assert "critical_path_impact" in result
        assert "mitigation_options" in result

        # Should affect task-2 and task-3
        assert len(result["affected_tasks"]) == 2

        # Total delay should be more than initial delay due to cascading
        assert result["total_delay"] > 4.0

        # Check affected task details
        affected_ids = [t["task_id"] for t in result["affected_tasks"]]
        assert "task-2" in affected_ids
        assert "task-3" in affected_ids

    @pytest.mark.asyncio
    async def test_agent_performance_trajectory(self, memory, agent_with_history):
        """Test agent skill development trajectory calculation"""
        # Add more recent outcomes to show improvement
        recent_outcomes = [
            TaskOutcome(
                task_id=f"recent-{i}",
                agent_id=agent_with_history,
                task_name=f"Recent Task {i}",
                estimated_hours=8.0,
                actual_hours=8.5,  # Getting more accurate
                success=True,  # All successful
                blockers=[],
                started_at=datetime.now() - timedelta(days=30 - i),
                completed_at=datetime.now() - timedelta(days=29 - i),
            )
            for i in range(5)
        ]

        for outcome in recent_outcomes:
            memory.episodic["outcomes"].append(outcome)

        result = await memory.calculate_agent_performance_trajectory(agent_with_history)

        assert "current_skills" in result
        assert "improving_skills" in result
        assert "struggling_skills" in result
        assert "projected_skills" in result
        assert "recommendations" in result

        # Should have recommendations based on performance
        assert len(result["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_find_similar_outcomes(self, memory):
        """Test finding similar past task executions"""
        # Add some outcomes
        outcomes = [
            TaskOutcome(
                task_id="past-1",
                agent_id="agent-001",
                task_name="Build user authentication API",
                estimated_hours=8.0,
                actual_hours=10.0,
                success=True,
                blockers=[],
                started_at=datetime.now() - timedelta(days=10),
                completed_at=datetime.now() - timedelta(days=9),
            ),
            TaskOutcome(
                task_id="past-2",
                agent_id="agent-002",
                task_name="Create product catalog",
                estimated_hours=6.0,
                actual_hours=5.0,
                success=True,
                blockers=[],
                started_at=datetime.now() - timedelta(days=8),
                completed_at=datetime.now() - timedelta(days=7),
            ),
            TaskOutcome(
                task_id="past-3",
                agent_id="agent-001",
                task_name="Implement user login",
                estimated_hours=4.0,
                actual_hours=5.0,
                success=False,
                blockers=["Missing OAuth config"],
                started_at=datetime.now() - timedelta(days=5),
                completed_at=datetime.now() - timedelta(days=4),
            ),
        ]

        for outcome in outcomes:
            memory.episodic["outcomes"].append(outcome)

        # Search for similar tasks
        task = Task(
            id="new-task",
            name="Add user registration API",
            description="",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=6.0,
            dependencies=[],
            labels=["backend", "api", "authentication"],
        )

        similar = await memory.find_similar_outcomes(task, limit=2)

        assert len(similar) <= 2
        # Should find auth-related tasks as most similar
        if similar:
            assert any(
                "auth" in outcome.task_name.lower()
                or "user" in outcome.task_name.lower()
                for outcome in similar
            )

    def test_update_project_tasks(self, memory):
        """Test updating working memory with project tasks"""
        tasks = [
            Task(
                id=f"task-{i}",
                name=f"Task {i}",
                description="",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
                dependencies=[],
            )
            for i in range(5)
        ]

        memory.update_project_tasks(tasks)

        assert len(memory.working["all_tasks"]) == 5
        stats = memory.get_memory_stats()
        assert stats["working_memory"]["project_tasks"] == 5
