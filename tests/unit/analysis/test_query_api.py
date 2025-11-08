"""
Unit tests for ProjectHistoryQuery API.

Tests filtering, searching, and analysis methods for project history queries.
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from src.analysis.aggregator import (
    AgentHistory,
    Message,
    ProjectHistory,
    ProjectHistoryAggregator,
    TaskHistory,
    TimelineEvent,
)
from src.analysis.query_api import ProjectHistoryQuery
from src.core.project_history import ArtifactMetadata, Decision, ProjectSnapshot


@pytest.fixture
def mock_aggregator() -> Mock:
    """Create mock aggregator for testing."""
    aggregator = Mock(spec=ProjectHistoryAggregator)
    aggregator.aggregate_project = AsyncMock()
    return aggregator


@pytest.fixture
def sample_project_history() -> ProjectHistory:
    """Create sample project history for testing."""
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    two_days_ago = now - timedelta(days=2)

    # Create sample decisions
    decision1 = Decision(
        decision_id="dec1",
        task_id="task1",
        agent_id="agent1",
        timestamp=yesterday,
        what="Use FastAPI for API",
        why="Better performance",
        impact="Affects API design",
        affected_tasks=["task2", "task3"],
    )

    decision2 = Decision(
        decision_id="dec2",
        task_id="task2",
        agent_id="agent2",
        timestamp=now,
        what="Use PostgreSQL",
        why="ACID compliance",
        impact="Affects data layer",
        affected_tasks=["task3"],
    )

    # Create sample artifacts
    artifact1 = ArtifactMetadata(
        artifact_id="art1",
        task_id="task1",
        agent_id="agent1",
        timestamp=yesterday,
        filename="api_spec.md",
        artifact_type="specification",
        relative_path="docs/specifications/api_spec.md",
        absolute_path="/tmp/project/docs/specifications/api_spec.md",  # nosec
        description="API specification",
    )

    artifact2 = ArtifactMetadata(
        artifact_id="art2",
        task_id="task2",
        agent_id="agent2",
        timestamp=now,
        filename="db_schema.sql",
        artifact_type="design",
        relative_path="docs/design/db_schema.sql",
        absolute_path="/tmp/project/docs/design/db_schema.sql",  # nosec
        description="Database schema",
    )

    # Create sample tasks
    task1 = TaskHistory(
        task_id="task1",
        name="Build API",
        description="Create REST API",
        status="completed",
        estimated_hours=8.0,
        actual_hours=10.0,
        started_at=two_days_ago,
        completed_at=yesterday,
        assigned_to="agent1",
        instructions_received="Build a REST API with FastAPI",
        dependencies=[],
        decisions_made=[decision1],
        artifacts_produced=[artifact1],
    )

    task2 = TaskHistory(
        task_id="task2",
        name="Setup Database",
        description="Configure PostgreSQL",
        status="in_progress",
        estimated_hours=4.0,
        actual_hours=3.0,
        started_at=yesterday,
        assigned_to="agent2",
        instructions_received="Setup PostgreSQL database",
        dependencies=["task1"],
        decisions_made=[decision2],
        artifacts_produced=[artifact2],
    )

    task3 = TaskHistory(
        task_id="task3",
        name="Blocked Task",
        description="This task has blockers",
        status="blocked",
        estimated_hours=6.0,
        actual_hours=1.0,
        started_at=yesterday,
        assigned_to="agent1",
        dependencies=["task1", "task2"],
        blockers_reported=[
            {
                "blocker_id": "block1",
                "description": "Missing database credentials",
                "severity": "high",
            }
        ],
    )

    # Create sample agents
    agent1 = AgentHistory(
        agent_id="agent1",
        tasks_completed=1,
        tasks_blocked=1,
        total_hours=11.0,
        average_estimation_accuracy=0.8,
        decisions_made=1,
        artifacts_produced=1,
    )

    agent2 = AgentHistory(
        agent_id="agent2",
        tasks_completed=0,
        tasks_blocked=0,
        total_hours=3.0,
        average_estimation_accuracy=1.0,
        decisions_made=1,
        artifacts_produced=1,
    )

    # Create sample timeline
    timeline = [
        TimelineEvent(
            timestamp=two_days_ago,
            event_type="task_assigned",
            agent_id="agent1",
            task_id="task1",
            description="Task assigned to agent1",
        ),
        TimelineEvent(
            timestamp=yesterday,
            event_type="task_completed",
            agent_id="agent1",
            task_id="task1",
            description="Task completed",
        ),
        TimelineEvent(
            timestamp=yesterday,
            event_type="decision_logged",
            agent_id="agent1",
            task_id="task1",
            description="Decision: Use FastAPI",
            details=decision1.to_dict(),
        ),
        TimelineEvent(
            timestamp=now,
            event_type="artifact_created",
            agent_id="agent2",
            task_id="task2",
            description="Created design: db_schema.sql",
        ),
    ]

    # Create sample messages
    message1 = Message(
        timestamp=two_days_ago,
        direction="to_pm",
        agent_id="agent1",
        content="I will build the REST API using FastAPI",
        metadata={"task_id": "task1"},
    )

    message2 = Message(
        timestamp=yesterday,
        direction="to_pm",
        agent_id="agent2",
        content="Setting up PostgreSQL database",
        metadata={"task_id": "task2"},
    )

    task1.conversations = [message1]
    task2.conversations = [message2]

    # Create snapshot
    snapshot = ProjectSnapshot(
        project_id="proj1",
        project_name="Test Project",
        snapshot_timestamp=two_days_ago,
        completion_status="in_progress",
        total_tasks=3,
        completed_tasks=1,
        in_progress_tasks=1,
        blocked_tasks=1,
        completion_rate=33.3,
        project_started=two_days_ago,
        project_completed=None,
        total_duration_hours=48.0,
        estimated_hours=18.0,
        actual_hours=14.0,
        estimation_accuracy=0.78,
        total_agents=2,
    )

    return ProjectHistory(
        project_id="proj1",
        snapshot=snapshot,
        tasks=[task1, task2, task3],
        agents=[agent1, agent2],
        timeline=timeline,
        decisions=[decision1, decision2],
        artifacts=[artifact1, artifact2],
    )


@pytest.fixture
def query_api(
    mock_aggregator: Mock, sample_project_history: ProjectHistory
) -> ProjectHistoryQuery:  # noqa: E501
    """Create query API with mocked aggregator."""
    mock_aggregator.aggregate_project.return_value = sample_project_history
    return ProjectHistoryQuery(mock_aggregator)


class TestTaskQueries:
    """Test task filtering and searching."""

    @pytest.mark.asyncio
    async def test_find_tasks_by_status(self, query_api: ProjectHistoryQuery) -> None:
        """Test finding tasks by status."""
        completed = await query_api.find_tasks_by_status("proj1", "completed")
        assert len(completed) == 1
        assert completed[0].task_id == "task1"

        in_progress = await query_api.find_tasks_by_status("proj1", "in_progress")
        assert len(in_progress) == 1
        assert in_progress[0].task_id == "task2"

        blocked = await query_api.find_tasks_by_status("proj1", "blocked")
        assert len(blocked) == 1
        assert blocked[0].task_id == "task3"

    @pytest.mark.asyncio
    async def test_find_tasks_by_agent(self, query_api: ProjectHistoryQuery) -> None:
        """Test finding tasks by assigned agent."""
        agent1_tasks = await query_api.find_tasks_by_agent("proj1", "agent1")
        assert len(agent1_tasks) == 2
        assert {t.task_id for t in agent1_tasks} == {"task1", "task3"}

        agent2_tasks = await query_api.find_tasks_by_agent("proj1", "agent2")
        assert len(agent2_tasks) == 1
        assert agent2_tasks[0].task_id == "task2"

    @pytest.mark.asyncio
    async def test_find_tasks_in_timerange(
        self, query_api: ProjectHistoryQuery
    ) -> None:
        """Test finding tasks within time range."""
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        two_days_ago = now - timedelta(days=2)

        # Find tasks started in last 2 days
        recent_tasks = await query_api.find_tasks_in_timerange(
            "proj1", two_days_ago, now
        )
        assert len(recent_tasks) == 3  # All tasks

        # Find tasks started yesterday
        yesterday_tasks = await query_api.find_tasks_in_timerange(
            "proj1", yesterday, now
        )
        assert len(yesterday_tasks) == 2  # task2 and task3

    @pytest.mark.asyncio
    async def test_find_blocked_tasks(self, query_api: ProjectHistoryQuery) -> None:
        """Test finding tasks with blockers."""
        blocked = await query_api.find_blocked_tasks("proj1")
        assert len(blocked) == 1
        assert blocked[0].task_id == "task3"
        assert len(blocked[0].blockers_reported) == 1
        assert blocked[0].blockers_reported[0]["severity"] == "high"

    @pytest.mark.asyncio
    async def test_get_task_dependency_chain(
        self, query_api: ProjectHistoryQuery
    ) -> None:
        """Test getting full dependency chain for a task."""
        # task3 depends on task1 and task2, task2 depends on task1
        chain = await query_api.get_task_dependency_chain("proj1", "task3")
        assert len(chain) == 2
        task_ids = {t.task_id for t in chain}
        assert task_ids == {"task1", "task2"}

    @pytest.mark.asyncio
    async def test_get_task_dependency_chain_nonexistent(
        self, query_api: ProjectHistoryQuery
    ) -> None:
        """Test dependency chain for nonexistent task."""
        chain = await query_api.get_task_dependency_chain("proj1", "nonexistent")
        assert len(chain) == 0


class TestDecisionQueries:
    """Test decision filtering and searching."""

    @pytest.mark.asyncio
    async def test_find_decisions_by_task(self, query_api: ProjectHistoryQuery) -> None:
        """Test finding decisions by task."""
        task1_decisions = await query_api.find_decisions_by_task("proj1", "task1")
        assert len(task1_decisions) == 1
        assert task1_decisions[0].decision_id == "dec1"

        task2_decisions = await query_api.find_decisions_by_task("proj1", "task2")
        assert len(task2_decisions) == 1
        assert task2_decisions[0].decision_id == "dec2"

    @pytest.mark.asyncio
    async def test_find_decisions_by_agent(
        self, query_api: ProjectHistoryQuery
    ) -> None:
        """Test finding decisions by agent."""
        agent1_decisions = await query_api.find_decisions_by_agent("proj1", "agent1")
        assert len(agent1_decisions) == 1
        assert agent1_decisions[0].agent_id == "agent1"

        agent2_decisions = await query_api.find_decisions_by_agent("proj1", "agent2")
        assert len(agent2_decisions) == 1
        assert agent2_decisions[0].agent_id == "agent2"

    @pytest.mark.asyncio
    async def test_find_decisions_affecting_task(
        self, query_api: ProjectHistoryQuery
    ) -> None:
        """Test finding decisions that affect a task."""
        # dec1 affects task2 and task3
        task2_affected = await query_api.find_decisions_affecting_task("proj1", "task2")
        assert len(task2_affected) == 1
        assert task2_affected[0].decision_id == "dec1"

        # dec1 and dec2 affect task3
        task3_affected = await query_api.find_decisions_affecting_task("proj1", "task3")
        assert len(task3_affected) == 2
        decision_ids = {d.decision_id for d in task3_affected}
        assert decision_ids == {"dec1", "dec2"}


class TestArtifactQueries:
    """Test artifact filtering and searching."""

    @pytest.mark.asyncio
    async def test_find_artifacts_by_task(self, query_api: ProjectHistoryQuery) -> None:
        """Test finding artifacts by task."""
        task1_artifacts = await query_api.find_artifacts_by_task("proj1", "task1")
        assert len(task1_artifacts) == 1
        assert task1_artifacts[0].filename == "api_spec.md"

        task2_artifacts = await query_api.find_artifacts_by_task("proj1", "task2")
        assert len(task2_artifacts) == 1
        assert task2_artifacts[0].filename == "db_schema.sql"

    @pytest.mark.asyncio
    async def test_find_artifacts_by_type(self, query_api: ProjectHistoryQuery) -> None:
        """Test finding artifacts by type."""
        specs = await query_api.find_artifacts_by_type("proj1", "specification")
        assert len(specs) == 1
        assert specs[0].artifact_type == "specification"

        designs = await query_api.find_artifacts_by_type("proj1", "design")
        assert len(designs) == 1
        assert designs[0].artifact_type == "design"

    @pytest.mark.asyncio
    async def test_find_artifacts_by_agent(
        self, query_api: ProjectHistoryQuery
    ) -> None:
        """Test finding artifacts by agent."""
        agent1_artifacts = await query_api.find_artifacts_by_agent("proj1", "agent1")
        assert len(agent1_artifacts) == 1
        assert agent1_artifacts[0].agent_id == "agent1"


class TestAgentQueries:
    """Test agent history and performance queries."""

    @pytest.mark.asyncio
    async def test_get_agent_history(self, query_api: ProjectHistoryQuery) -> None:
        """Test getting complete agent history."""
        agent1 = await query_api.get_agent_history("proj1", "agent1")
        assert agent1 is not None
        assert agent1.agent_id == "agent1"
        assert agent1.tasks_completed == 1
        assert agent1.tasks_blocked == 1

        agent2 = await query_api.get_agent_history("proj1", "agent2")
        assert agent2 is not None
        assert agent2.agent_id == "agent2"

    @pytest.mark.asyncio
    async def test_get_agent_history_nonexistent(
        self, query_api: ProjectHistoryQuery
    ) -> None:
        """Test getting history for nonexistent agent."""
        agent = await query_api.get_agent_history("proj1", "nonexistent")
        assert agent is None

    @pytest.mark.asyncio
    async def test_get_agent_performance_metrics(
        self, query_api: ProjectHistoryQuery
    ) -> None:
        """Test calculating agent performance metrics."""
        metrics = await query_api.get_agent_performance_metrics("proj1", "agent1")

        assert metrics["agent_id"] == "agent1"
        assert metrics["tasks_assigned"] == 2
        assert metrics["tasks_completed"] == 1
        assert metrics["tasks_blocked"] == 1
        assert metrics["avg_task_hours"] == 10.0  # Only completed task counted
        assert metrics["decisions_made"] == 1
        assert metrics["artifacts_produced"] == 1

    @pytest.mark.asyncio
    async def test_get_agent_performance_metrics_nonexistent(
        self, query_api: ProjectHistoryQuery
    ) -> None:
        """Test performance metrics for nonexistent agent."""
        metrics = await query_api.get_agent_performance_metrics("proj1", "nonexistent")
        assert "error" in metrics
        assert metrics["agent_id"] == "nonexistent"


class TestTimelineQueries:
    """Test timeline event searching."""

    @pytest.mark.asyncio
    async def test_search_timeline_by_event_type(
        self, query_api: ProjectHistoryQuery
    ) -> None:
        """Test searching timeline by event type."""
        assignments = await query_api.search_timeline(
            "proj1", event_type="task_assigned"
        )  # noqa: E501
        assert len(assignments) == 1
        assert assignments[0].event_type == "task_assigned"

        completions = await query_api.search_timeline(
            "proj1", event_type="task_completed"
        )  # noqa: E501
        assert len(completions) == 1

    @pytest.mark.asyncio
    async def test_search_timeline_by_agent(
        self, query_api: ProjectHistoryQuery
    ) -> None:
        """Test searching timeline by agent."""
        agent1_events = await query_api.search_timeline("proj1", agent_id="agent1")
        assert len(agent1_events) == 3

        agent2_events = await query_api.search_timeline("proj1", agent_id="agent2")
        assert len(agent2_events) == 1

    @pytest.mark.asyncio
    async def test_search_timeline_by_task(
        self, query_api: ProjectHistoryQuery
    ) -> None:
        """Test searching timeline by task."""
        task1_events = await query_api.search_timeline("proj1", task_id="task1")
        assert len(task1_events) == 3

    @pytest.mark.asyncio
    async def test_search_timeline_by_timerange(
        self, query_api: ProjectHistoryQuery
    ) -> None:
        """Test searching timeline by time range."""
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)

        recent_events = await query_api.search_timeline(
            "proj1", start_time=yesterday, end_time=now
        )
        # Should exclude the two_days_ago event
        assert len(recent_events) >= 2

    @pytest.mark.asyncio
    async def test_search_timeline_multiple_filters(
        self, query_api: ProjectHistoryQuery
    ) -> None:
        """Test searching timeline with multiple filters."""
        events = await query_api.search_timeline(
            "proj1", event_type="decision_logged", agent_id="agent1"
        )
        assert len(events) == 1
        assert events[0].event_type == "decision_logged"
        assert events[0].agent_id == "agent1"


class TestConversationQueries:
    """Test conversation message searching."""

    @pytest.mark.asyncio
    async def test_search_conversations_by_keyword(
        self, query_api: ProjectHistoryQuery
    ) -> None:
        """Test searching conversations by keyword."""
        api_messages = await query_api.search_conversations("proj1", keyword="API")
        assert len(api_messages) == 1
        assert "API" in api_messages[0].content

        db_messages = await query_api.search_conversations("proj1", keyword="database")
        assert len(db_messages) == 1
        assert "database" in db_messages[0].content.lower()

    @pytest.mark.asyncio
    async def test_search_conversations_by_agent(
        self, query_api: ProjectHistoryQuery
    ) -> None:
        """Test searching conversations by agent."""
        agent1_messages = await query_api.search_conversations(
            "proj1", agent_id="agent1"
        )  # noqa: E501
        assert len(agent1_messages) == 1
        assert agent1_messages[0].agent_id == "agent1"

    @pytest.mark.asyncio
    async def test_search_conversations_by_task(
        self, query_api: ProjectHistoryQuery
    ) -> None:
        """Test searching conversations by task."""
        task1_messages = await query_api.search_conversations("proj1", task_id="task1")
        assert len(task1_messages) == 1
        assert task1_messages[0].metadata.get("task_id") == "task1"


class TestAnalysisHelpers:
    """Test project analysis helper methods."""

    @pytest.mark.asyncio
    async def test_get_project_summary(self, query_api: ProjectHistoryQuery) -> None:
        """Test getting project summary statistics."""
        summary = await query_api.get_project_summary("proj1")

        assert summary["project_id"] == "proj1"
        assert summary["project_name"] == "Test Project"
        assert summary["total_tasks"] == 3
        assert summary["completed_tasks"] == 1
        assert summary["blocked_tasks"] == 1
        assert summary["completion_rate"] == 33.3  # 1/3 * 100
        assert summary["total_decisions"] == 2
        assert summary["total_artifacts"] == 2
        assert summary["active_agents"] == 2
        assert summary["project_duration_hours"] > 0

    @pytest.mark.asyncio
    async def test_get_project_history(self, query_api: ProjectHistoryQuery) -> None:
        """Test getting complete project history."""
        history = await query_api.get_project_history("proj1")
        assert history.project_id == "proj1"
        assert len(history.tasks) == 3
        assert len(history.agents) == 2
        assert len(history.decisions) == 2
        assert len(history.artifacts) == 2
