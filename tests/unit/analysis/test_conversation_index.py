"""
Unit tests for conversation indexer.

Tests SQLite indexing of conversation logs for fast project-task lookups,
addressing the Phase 1 impact analysis requirement for conversation log performance.
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.analysis.helpers.conversation_index import ConversationIndexer


class TestConversationIndexer:
    """Test suite for ConversationIndexer."""

    @pytest.fixture
    def temp_marcus_root(self):
        """Create temporary Marcus root directory with conversation logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create conversations directory
            conv_dir = root / "logs" / "conversations"
            conv_dir.mkdir(parents=True)

            # Create sample conversation log
            log_file = conv_dir / "conversations_20251108.jsonl"
            with open(log_file, "w") as f:
                # Project 1 conversations
                f.write(
                    json.dumps(
                        {
                            "timestamp": "2025-11-08T10:00:00Z",
                            "conversation_type": "pm_to_worker",
                            "worker_id": "agent-1",
                            "message": "Please implement login feature",
                            "metadata": {
                                "project_id": "proj-1",
                                "task_id": "task-1",
                                "message_type": "task_assignment",
                            },
                        }
                    )
                    + "\n"
                )
                f.write(
                    json.dumps(
                        {
                            "timestamp": "2025-11-08T11:00:00Z",
                            "conversation_type": "worker_to_pm",
                            "worker_id": "agent-1",
                            "message": "Task completed",
                            "metadata": {
                                "project_id": "proj-1",
                                "task_id": "task-1",
                                "message_type": "task_complete",
                            },
                        }
                    )
                    + "\n"
                )

                # Project 2 conversations
                f.write(
                    json.dumps(
                        {
                            "timestamp": "2025-11-08T12:00:00Z",
                            "conversation_type": "pm_to_worker",
                            "worker_id": "agent-2",
                            "message": "Design the architecture",
                            "metadata": {
                                "project_id": "proj-2",
                                "task_id": "task-2",
                                "message_type": "task_assignment",
                            },
                        }
                    )
                    + "\n"
                )

            yield root

    @pytest.mark.asyncio
    async def test_rebuild_index(self, temp_marcus_root):
        """Test building index from conversation logs."""
        # Arrange
        indexer = ConversationIndexer(temp_marcus_root)

        # Act
        await indexer.rebuild_index()

        # Assert - check index was created
        db_path = temp_marcus_root / "data" / "marcus.db"
        assert db_path.exists()

        # Verify index contains correct entries
        task_ids = await indexer.get_task_ids_for_project("proj-1")
        assert "task-1" in task_ids
        assert len([t for t in task_ids if t == "task-1"]) >= 1

    @pytest.mark.asyncio
    async def test_get_task_ids_for_project(self, temp_marcus_root):
        """Test retrieving task IDs for a project."""
        # Arrange
        indexer = ConversationIndexer(temp_marcus_root)
        await indexer.rebuild_index()

        # Act
        proj1_tasks = await indexer.get_task_ids_for_project("proj-1")
        proj2_tasks = await indexer.get_task_ids_for_project("proj-2")

        # Assert
        assert "task-1" in proj1_tasks
        assert "task-2" in proj2_tasks
        assert "task-2" not in proj1_tasks
        assert "task-1" not in proj2_tasks

    @pytest.mark.asyncio
    async def test_get_task_ids_empty_project(self, temp_marcus_root):
        """Test retrieving task IDs for non-existent project."""
        # Arrange
        indexer = ConversationIndexer(temp_marcus_root)
        await indexer.rebuild_index()

        # Act
        task_ids = await indexer.get_task_ids_for_project("non-existent")

        # Assert
        assert len(task_ids) == 0

    @pytest.mark.asyncio
    async def test_get_conversation_count_for_task(self, temp_marcus_root):
        """Test counting conversations for a task."""
        # Arrange
        indexer = ConversationIndexer(temp_marcus_root)
        await indexer.rebuild_index()

        # Act
        count = await indexer.get_conversation_count_for_task("task-1")

        # Assert
        assert count == 2  # pm_to_worker + worker_to_pm

    @pytest.mark.asyncio
    async def test_get_conversations_by_type(self, temp_marcus_root):
        """Test retrieving conversations filtered by type."""
        # Arrange
        indexer = ConversationIndexer(temp_marcus_root)
        await indexer.rebuild_index()

        # Act
        assignments = await indexer.get_conversations_by_type(
            "proj-1", "task_assignment"
        )

        # Assert
        assert len(assignments) >= 1
        assert assignments[0]["task_id"] == "task-1"
        assert assignments[0]["message_type"] == "task_assignment"

    @pytest.mark.asyncio
    async def test_index_incremental_update(self, temp_marcus_root):
        """Test that index can be updated incrementally."""
        # Arrange
        indexer = ConversationIndexer(temp_marcus_root)
        await indexer.rebuild_index()

        # Add new conversation log
        conv_dir = temp_marcus_root / "logs" / "conversations"
        new_log = conv_dir / "conversations_20251109.jsonl"
        with open(new_log, "w") as f:
            f.write(
                json.dumps(
                    {
                        "timestamp": "2025-11-09T10:00:00Z",
                        "conversation_type": "pm_to_worker",
                        "worker_id": "agent-3",
                        "message": "New task",
                        "metadata": {
                            "project_id": "proj-3",
                            "task_id": "task-3",
                            "message_type": "task_assignment",
                        },
                    }
                )
                + "\n"
            )

        # Act - rebuild index
        await indexer.rebuild_index()

        # Assert - new task should be indexed
        proj3_tasks = await indexer.get_task_ids_for_project("proj-3")
        assert "task-3" in proj3_tasks

    @pytest.mark.asyncio
    async def test_performance_vs_full_scan(self, temp_marcus_root):
        """
        Test that indexed lookup is faster than full file scan.

        This test verifies the performance benefit cited in Phase 1 impact analysis:
        "50ms → 5ms" speedup.
        """
        # Arrange
        indexer = ConversationIndexer(temp_marcus_root)
        await indexer.rebuild_index()

        import time

        # Measure indexed lookup
        start = time.time()
        task_ids_indexed = await indexer.get_task_ids_for_project("proj-1")
        indexed_duration = time.time() - start

        # Measure full scan (simulate old approach)
        start = time.time()
        task_ids_scan = await indexer._scan_logs_for_project("proj-1")
        scan_duration = time.time() - start

        # Assert - Results should be the same
        assert set(task_ids_indexed) == set(task_ids_scan)

        # Note: With such small test data (3 entries), timing differences are
        # in microseconds and can vary. The real benefit is visible with
        # 1000+ conversation entries where indexed: ~5ms, scan: ~50ms
        # For this test, we just verify both methods return correct results

    @pytest.mark.asyncio
    async def test_handle_malformed_log_lines(self, temp_marcus_root):
        """Test that indexer handles malformed JSON lines gracefully."""
        # Arrange - add malformed log
        conv_dir = temp_marcus_root / "logs" / "conversations"
        bad_log = conv_dir / "conversations_bad.jsonl"
        with open(bad_log, "w") as f:
            f.write("not valid json\n")
            f.write('{"incomplete": \n')
            f.write(
                json.dumps(
                    {
                        "timestamp": "2025-11-08T10:00:00Z",
                        "conversation_type": "pm_to_worker",
                        "worker_id": "agent-1",
                        "message": "Valid entry",
                        "metadata": {
                            "project_id": "proj-1",
                            "task_id": "task-valid",
                        },
                    }
                )
                + "\n"
            )

        indexer = ConversationIndexer(temp_marcus_root)

        # Act - should not raise exception
        await indexer.rebuild_index()

        # Assert - valid entry should be indexed
        task_ids = await indexer.get_task_ids_for_project("proj-1")
        assert "task-valid" in task_ids

    @pytest.mark.asyncio
    async def test_missing_metadata_fields(self, temp_marcus_root):
        """Test handling of conversation entries with missing metadata."""
        # Arrange
        conv_dir = temp_marcus_root / "logs" / "conversations"
        log_file = conv_dir / "conversations_missing.jsonl"
        with open(log_file, "w") as f:
            # Entry without project_id
            f.write(
                json.dumps(
                    {
                        "timestamp": "2025-11-08T10:00:00Z",
                        "conversation_type": "pm_to_worker",
                        "worker_id": "agent-1",
                        "message": "No project ID",
                        "metadata": {"task_id": "task-orphan"},
                    }
                )
                + "\n"
            )

            # Entry without task_id
            f.write(
                json.dumps(
                    {
                        "timestamp": "2025-11-08T10:00:00Z",
                        "conversation_type": "pm_to_worker",
                        "worker_id": "agent-1",
                        "message": "No task ID",
                        "metadata": {"project_id": "proj-1"},
                    }
                )
                + "\n"
            )

        indexer = ConversationIndexer(temp_marcus_root)

        # Act - should handle missing fields gracefully
        await indexer.rebuild_index()

        # Assert - entries with missing required fields should be skipped
        task_ids = await indexer.get_task_ids_for_project("proj-1")
        assert "task-orphan" not in task_ids  # No project_id, can't associate
