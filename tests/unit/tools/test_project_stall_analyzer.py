"""
Unit tests for project stall analyzer.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.tools.project_stall_analyzer import (
    ConversationEvent,
    ConversationReplayAnalyzer,
    DependencyLockVisualizer,
    TaskCompletionAnalyzer,
    TaskCompletionEvent,
)


@pytest.fixture
def sample_tasks():
    """Create sample tasks for testing."""
    now = datetime.now(timezone.utc)

    tasks = [
        Task(
            id="task1",
            name="Setup Project",
            description="Initial setup",
            status=TaskStatus.DONE,
            priority=Priority.HIGH,
            dependencies=[],
            assigned_to=None,
            created_at=now - timedelta(days=5),
            updated_at=now - timedelta(days=1),
            due_date=None,
            estimated_hours=8,
        ),
        Task(
            id="task2",
            name="Build API",
            description="Create API",
            status=TaskStatus.DONE,
            priority=Priority.HIGH,
            dependencies=["task1"],
            assigned_to=None,
            created_at=now - timedelta(days=4),
            updated_at=now - timedelta(days=1),
            due_date=None,
            estimated_hours=16,
        ),
        Task(
            id="task3",
            name="Project Success",  # This is a "final" task
            description="Mark project as successful",
            status=TaskStatus.DONE,
            priority=Priority.LOW,
            dependencies=[],  # No dependencies - completed too early!
            assigned_to=None,
            created_at=now - timedelta(days=3),
            updated_at=now - timedelta(days=1),
            due_date=None,
            estimated_hours=1,
        ),
        Task(
            id="task4",
            name="Add Tests",
            description="Add test suite",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            dependencies=["task2"],
            assigned_to=None,
            created_at=now - timedelta(days=2),
            updated_at=now,
            due_date=None,
            estimated_hours=8,
        ),
        Task(
            id="task5",
            name="Documentation",
            description="Write docs",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            dependencies=["task4"],  # Blocked by task4
            assigned_to=None,
            created_at=now - timedelta(days=1),
            updated_at=now,
            due_date=None,
            estimated_hours=4,
        ),
    ]

    # Set completion timestamps
    for i, task in enumerate(tasks):
        if task.status == TaskStatus.DONE:
            task.completed_at = now - timedelta(days=4 - i)

    return tasks


class TestTaskCompletionAnalyzer:
    """Test task completion pattern analysis."""

    def test_build_completion_timeline(self, sample_tasks):
        """Test building completion timeline."""
        analyzer = TaskCompletionAnalyzer(sample_tasks)
        timeline = analyzer.build_completion_timeline()

        # Should have 3 completed tasks
        assert len(timeline) == 3

        # Should be ordered by completion time
        assert timeline[0].task_name == "Setup Project"
        assert timeline[1].task_name == "Build API"
        assert timeline[2].task_name == "Project Success"

        # Should have sequence numbers
        assert timeline[0].sequence_number == 1
        assert timeline[1].sequence_number == 2
        assert timeline[2].sequence_number == 3

    def test_detect_early_completions(self, sample_tasks):
        """Test detection of tasks completed too early."""
        analyzer = TaskCompletionAnalyzer(sample_tasks)
        timeline = analyzer.build_completion_timeline()
        early_completions = analyzer.detect_early_completions(timeline)

        # Should detect "Project Success" completed early
        assert len(early_completions) > 0

        # Find the "Project Success" early completion
        success_completion = next(
            (ec for ec in early_completions if "Success" in ec["task_name"]), None
        )
        assert success_completion is not None

        # It was 3rd of 5 tasks = 60% progress
        assert success_completion["completion_percentage"] == 60.0
        assert success_completion["completion_percentage"] < 80  # Threshold
        assert success_completion["severity"] == "high"


class TestConversationReplayAnalyzer:
    """Test conversation replay and pattern detection."""

    @pytest.fixture
    def temp_log_dir(self, tmp_path):
        """Create temporary log directory with sample logs."""
        log_dir = tmp_path / "conversations"
        log_dir.mkdir()

        # Create sample log file
        log_file = log_dir / "realtime_20251006_120000.jsonl"

        now = datetime.now(timezone.utc)
        events = [
            {
                "timestamp": (now - timedelta(hours=2)).isoformat(),
                "type": "agent_request_task",
                "agent_id": "agent1",
            },
            {
                "timestamp": (now - timedelta(hours=2, minutes=1)).isoformat(),
                "type": "no_task_available",
                "agent_id": "agent1",
            },
            {
                "timestamp": (now - timedelta(hours=1)).isoformat(),
                "type": "agent_request_task",
                "agent_id": "agent1",
            },
            {
                "timestamp": (now - timedelta(hours=1, minutes=1)).isoformat(),
                "type": "no_task_available",
                "agent_id": "agent1",
            },
            {
                "timestamp": (now - timedelta(minutes=30)).isoformat(),
                "type": "agent_request_task",
                "agent_id": "agent1",
            },
            {
                "timestamp": (now - timedelta(minutes=29)).isoformat(),
                "type": "no_task_available",
                "agent_id": "agent1",
            },
            {
                "timestamp": (now - timedelta(minutes=10)).isoformat(),
                "type": "task_failed",
                "task_id": "task_x",
                "error": "Test error",
            },
            {
                "timestamp": (now - timedelta(minutes=5)).isoformat(),
                "type": "task_failed",
                "task_id": "task_x",
                "error": "Test error again",
            },
        ]

        with open(log_file, "w") as f:
            for event in events:
                import json

                f.write(json.dumps(event) + "\n")

        return log_dir

    def test_load_recent_events(self, temp_log_dir):
        """Test loading recent conversation events."""
        analyzer = ConversationReplayAnalyzer(temp_log_dir)
        events = analyzer.load_recent_events(lookback_hours=24)

        # Should load all events from the log file
        assert len(events) == 8

        # Events should be ConversationEvent objects
        assert all(isinstance(e, ConversationEvent) for e in events)

        # Should be sorted by timestamp
        timestamps = [e.timestamp for e in events]
        assert timestamps == sorted(timestamps)

    def test_identify_repeated_no_tasks_pattern(self, temp_log_dir):
        """Test detection of repeated 'no tasks available' pattern."""
        analyzer = ConversationReplayAnalyzer(temp_log_dir)
        events = analyzer.load_recent_events(lookback_hours=24)
        patterns = analyzer.identify_stall_patterns(events)

        # Should detect repeated "no tasks" pattern
        no_task_pattern = next(
            (p for p in patterns if p["pattern"] == "repeated_no_tasks"), None
        )
        assert no_task_pattern is not None
        assert no_task_pattern["count"] == 3  # 3 "no_task_available" events
        assert no_task_pattern["severity"] == "high"

    def test_identify_repeated_failure_pattern(self, temp_log_dir):
        """Test detection of repeated task failure pattern."""
        analyzer = ConversationReplayAnalyzer(temp_log_dir)
        events = analyzer.load_recent_events(lookback_hours=24)
        patterns = analyzer.identify_stall_patterns(events)

        # Should detect repeated task failure
        failure_pattern = next(
            (p for p in patterns if p["pattern"] == "repeated_task_failure"), None
        )
        assert failure_pattern is not None
        assert failure_pattern["task_id"] == "task_x"
        assert failure_pattern["count"] == 2  # Failed twice
        assert failure_pattern["severity"] == "high"


class TestDependencyLockVisualizer:
    """Test dependency lock visualization."""

    def test_generate_lock_visualization(self, sample_tasks):
        """Test generation of dependency lock visualization."""
        from src.core.task_diagnostics import DependencyChainAnalyzer

        analyzer = DependencyChainAnalyzer(sample_tasks)
        visualizer = DependencyLockVisualizer(analyzer)

        viz = visualizer.generate_lock_visualization()

        # Should have 1 lock (task5 blocked by task4)
        assert viz["total_locks"] == 1

        # Check lock details
        lock = viz["locks"][0]
        assert lock["blocked_task"]["name"] == "Documentation"
        assert len(lock["blocking_tasks"]) == 1
        assert lock["blocking_tasks"][0]["name"] == "Add Tests"

        # Should have ASCII visualization
        assert "Dependency Lock Visualization" in viz["ascii_visualization"]
        assert "Documentation" in viz["ascii_visualization"]
        assert "Add Tests" in viz["ascii_visualization"]

    def test_lock_metrics(self, sample_tasks):
        """Test lock metrics calculation."""
        from src.core.task_diagnostics import DependencyChainAnalyzer

        analyzer = DependencyChainAnalyzer(sample_tasks)
        visualizer = DependencyLockVisualizer(analyzer)

        viz = visualizer.generate_lock_visualization()

        # Check metrics
        assert "metrics" in viz
        assert viz["metrics"]["average_lock_depth"] == 1.0
        assert viz["metrics"]["max_lock_depth"] == 1


@pytest.mark.asyncio
class TestCaptureStallSnapshot:
    """Test capturing complete stall snapshot."""

    @pytest.fixture
    def mock_state(self):
        """Create mock Marcus server state."""
        state = Mock()
        state.kanban_client = Mock()
        state.agent_tasks = {}
        state.project_registry = Mock()

        # Mock project
        project = Mock()
        project.id = "proj-123"
        project.name = "Test Project"
        state.project_registry.get_active_project = AsyncMock(return_value=project)

        return state

    async def test_capture_snapshot_success(self, mock_state, sample_tasks, tmp_path):
        """Test successful snapshot capture."""
        from src.marcus_mcp.tools.project_stall_analyzer import (
            capture_project_stall_snapshot,
        )

        # Mock task retrieval
        mock_state.kanban_client.get_all_tasks = AsyncMock(return_value=sample_tasks)

        # Mock log directory to use temp path
        with patch("src.marcus_mcp.tools.project_stall_analyzer.Path") as mock_path:
            # Make snapshot dir point to temp path
            snapshot_dir = tmp_path / "stall_snapshots"
            snapshot_dir.mkdir()
            mock_path.return_value = snapshot_dir

            # Also mock the log_dir for conversation analyzer
            log_dir = tmp_path / "conversations"
            log_dir.mkdir()

            # Create empty log file
            log_file = log_dir / "realtime_test.jsonl"
            log_file.write_text("")

            with patch(
                "src.marcus_mcp.tools.project_stall_analyzer.ConversationReplayAnalyzer"
            ) as MockAnalyzer:
                mock_analyzer = MockAnalyzer.return_value
                mock_analyzer.load_recent_events = Mock(return_value=[])
                mock_analyzer.identify_stall_patterns = Mock(return_value=[])

                result = await capture_project_stall_snapshot(
                    mock_state, include_conversation_hours=24
                )

        # Should succeed
        assert result["success"] is True
        assert "snapshot" in result
        assert "summary" in result

        # Check summary
        summary = result["summary"]
        assert "stall_reason" in summary
        assert "total_issues" in summary
        assert "dependency_locks" in summary
        assert "early_completions" in summary

        # Check new diagnostic fields in summary
        assert "zombie_tasks" in summary
        assert "redundant_dependencies" in summary
        assert "state_inconsistencies" in summary
        assert "circular_dependencies" in summary
        assert "bottlenecks" in summary

        # Should detect early completion of "Project Success"
        assert summary["early_completions"] >= 1

        # Check snapshot has diagnostic data
        snapshot = result["snapshot"]
        assert "zombie_tasks" in snapshot
        assert "redundant_dependencies" in snapshot
        assert "state_inconsistencies" in snapshot
        assert "circular_dependencies" in snapshot
        assert "bottlenecks" in snapshot
