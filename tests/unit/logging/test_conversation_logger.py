"""
Unit tests for ConversationLogger.

Tests that conversation logging properly writes to files and captures
agent interactions including progress updates, task assignments, and
status updates.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.logging.conversation_logger import ConversationLogger, ConversationType


@pytest.mark.unit
class TestConversationLogger:
    """Test suite for ConversationLogger"""

    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary log directory for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def logger(self, temp_log_dir):
        """Create ConversationLogger with temporary directory"""
        return ConversationLogger(log_dir=str(temp_log_dir))

    def test_logger_creates_log_files(self, logger, temp_log_dir):
        """Test that logger creates conversation and decision log files"""
        # Check that log files were created
        log_files = list(temp_log_dir.glob("*.jsonl"))
        assert len(log_files) >= 2, "Should create at least 2 log files"

        # Check for conversations and decisions files
        file_names = [f.name for f in log_files]
        assert any("conversations_" in name for name in file_names)
        assert any("decisions_" in name for name in file_names)

    def test_worker_message_writes_to_file(self, logger, temp_log_dir):
        """Test that worker messages are written to conversation log"""
        # Log a worker message
        logger.log_worker_message(
            worker_id="test_worker_1",
            direction="to_pm",
            message="Test task completed",
            metadata={"task_id": "TASK-123"},
        )

        # Find conversation log file
        conv_files = list(temp_log_dir.glob("conversations_*.jsonl"))
        assert len(conv_files) > 0, "Conversation log file should exist"

        # Read and verify content
        with open(conv_files[0]) as f:
            lines = f.readlines()

        assert len(lines) > 0, "Conversation log should have content"

        # Parse first log entry
        log_entry = json.loads(lines[0])
        assert log_entry["conversation_type"] == ConversationType.WORKER_TO_PM.value
        assert log_entry["worker_id"] == "test_worker_1"
        assert log_entry["message"] == "Test task completed"
        assert log_entry["metadata"]["task_id"] == "TASK-123"

    def test_pm_decision_writes_to_file(self, logger, temp_log_dir):
        """Test that PM decisions are written to decision log"""
        # Log a decision
        logger.log_pm_decision(
            decision="Assign task to worker_2",
            rationale="Best skill match for the task",
            confidence_score=0.85,
            decision_factors={"skill_match": 0.9, "availability": 0.8},
        )

        # Find decision log file
        decision_files = list(temp_log_dir.glob("decisions_*.jsonl"))
        assert len(decision_files) > 0, "Decision log file should exist"

        # Read and verify content
        with open(decision_files[0]) as f:
            lines = f.readlines()

        assert len(lines) > 0, "Decision log should have content"

        # Parse log entry
        log_entry = json.loads(lines[0])
        assert log_entry["conversation_type"] == ConversationType.DECISION.value
        assert log_entry["decision"] == "Assign task to worker_2"
        assert log_entry["rationale"] == "Best skill match for the task"
        assert log_entry["confidence_score"] == 0.85

    def test_progress_update_writes_to_file(self, logger, temp_log_dir):
        """Test that progress updates are written to conversation log"""
        # Log progress update
        logger.log_progress_update(
            worker_id="worker_1",
            task_id="TASK-456",
            progress=75,
            status="in_progress",
            message="API endpoints implemented",
            metrics={"time_spent_hours": 6, "lines_of_code": 450},
        )

        # Find conversation log file
        conv_files = list(temp_log_dir.glob("conversations_*.jsonl"))
        assert len(conv_files) > 0

        # Read and verify content
        with open(conv_files[0]) as f:
            lines = f.readlines()

        assert len(lines) > 0, "Should have progress update logged"

        # Parse log entry
        log_entry = json.loads(lines[0])
        assert log_entry["event_type"] == "progress"
        assert log_entry["worker_id"] == "worker_1"
        assert log_entry["task_id"] == "TASK-456"
        assert log_entry["progress"] == 75
        assert log_entry["status"] == "in_progress"

    def test_task_assignment_writes_to_file(self, logger, temp_log_dir):
        """Test that task assignments are written to conversation log"""
        # Log task assignment
        logger.log_task_assignment(
            task_id="TASK-789",
            worker_id="worker_backend_1",
            task_details={
                "title": "Implement authentication",
                "priority": "high",
                "estimated_hours": 16,
            },
            assignment_score=0.92,
            dependency_analysis={"blocking_tasks": [], "critical_path": True},
        )

        # Find conversation log file
        conv_files = list(temp_log_dir.glob("conversations_*.jsonl"))
        assert len(conv_files) > 0

        # Read and verify content
        with open(conv_files[0]) as f:
            lines = f.readlines()

        assert len(lines) > 0, "Should have task assignment logged"

        # Parse log entry
        log_entry = json.loads(lines[0])
        assert log_entry["event_type"] == "assignment"
        assert log_entry["task_id"] == "TASK-789"
        assert log_entry["worker_id"] == "worker_backend_1"
        assert log_entry["assignment_score"] == 0.92

    def test_kanban_interaction_writes_to_file(self, logger, temp_log_dir):
        """Test that kanban interactions are written to conversation log"""
        # Log kanban interaction
        logger.log_kanban_interaction(
            action="create_task",
            direction="to_kanban",
            data={"task_id": "TASK-101", "title": "New feature", "column": "To Do"},
            processing_steps=["validate_data", "create_card", "update_cache"],
        )

        # Find conversation log file
        conv_files = list(temp_log_dir.glob("conversations_*.jsonl"))
        assert len(conv_files) > 0

        # Read and verify content
        with open(conv_files[0]) as f:
            lines = f.readlines()

        assert len(lines) > 0, "Should have kanban interaction logged"

        # Parse log entry
        log_entry = json.loads(lines[0])
        assert log_entry["conversation_type"] == ConversationType.PM_TO_KANBAN.value
        assert log_entry["action"] == "create_task"

    def test_blocker_writes_to_file(self, logger, temp_log_dir):
        """Test that blockers are written to conversation log"""
        # Log blocker
        logger.log_blocker(
            worker_id="worker_1",
            task_id="TASK-222",
            blocker_description="API rate limit exceeded",
            severity="high",
            suggested_solutions=["Wait for rate limit reset", "Use alternative API"],
        )

        # Find conversation log file
        conv_files = list(temp_log_dir.glob("conversations_*.jsonl"))
        assert len(conv_files) > 0

        # Read and verify content
        with open(conv_files[0]) as f:
            lines = f.readlines()

        assert len(lines) > 0, "Should have blocker logged"

        # Parse log entry
        log_entry = json.loads(lines[0])
        assert log_entry["event_type"] == "blocker"
        assert log_entry["severity"] == "high"
        assert log_entry["blocker_description"] == "API rate limit exceeded"

    def test_file_handlers_use_simple_formatter(self, logger, temp_log_dir):
        """Test that file handlers are configured with simple formatter

        This prevents empty log files by ensuring structlog's JSON output
        is written directly without additional formatting.
        """
        # Log a message
        logger.log_worker_message(
            "worker_test", "to_pm", "Test message", {"key": "value"}
        )

        # Find conversation log
        conv_files = list(temp_log_dir.glob("conversations_*.jsonl"))
        assert len(conv_files) > 0

        # Read content
        with open(conv_files[0]) as f:
            content = f.read()

        # Verify it's valid JSON (not empty, not plain text)
        assert content.strip(), "Log file should not be empty"
        assert "{" in content, "Content should be JSON"

        # Verify each line is valid JSON
        with open(conv_files[0]) as f:
            for line in f:
                if line.strip():
                    json.loads(line)  # Should not raise exception

    def test_multiple_messages_append_to_file(self, logger, temp_log_dir):
        """Test that multiple log messages append to the same file"""
        # Log multiple messages
        for i in range(5):
            logger.log_worker_message(
                f"worker_{i}", "to_pm", f"Message {i}", {"index": i}
            )

        # Find conversation log
        conv_files = list(temp_log_dir.glob("conversations_*.jsonl"))
        assert len(conv_files) > 0

        # Verify all messages are in the file
        with open(conv_files[0]) as f:
            lines = f.readlines()

        assert len(lines) >= 5, "Should have at least 5 log entries"

        # Verify each message
        for i, line in enumerate(lines[:5]):
            log_entry = json.loads(line)
            assert log_entry["worker_id"] == f"worker_{i}"
            assert log_entry["metadata"]["index"] == i
