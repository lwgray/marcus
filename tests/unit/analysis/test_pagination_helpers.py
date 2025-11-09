"""
Unit tests for pagination helpers.

Tests automatic pagination for decisions, artifacts, and tasks to handle
Phase 1's 10,000 item limit gracefully.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from src.analysis.aggregator import TaskHistory
from src.analysis.helpers.pagination import (
    iter_all_artifacts,
    iter_all_decisions,
    iter_all_tasks,
)
from src.core.project_history import ArtifactMetadata, Decision


class TestIterAllDecisions:
    """Test suite for iter_all_decisions async generator."""

    @pytest.mark.asyncio
    async def test_single_page_of_decisions(self):
        """Test iteration when all decisions fit in one page."""
        # Arrange
        mock_persistence = AsyncMock()
        decisions = [
            Decision(
                decision_id=f"dec_{i}",
                task_id="task-1",
                agent_id="agent-1",
                timestamp=datetime.now(timezone.utc),
                what=f"Decision {i}",
                why=f"Reason {i}",
                impact="low",
                affected_tasks=[],
                confidence=0.9,
            )
            for i in range(5)
        ]
        mock_persistence.load_decisions = AsyncMock(side_effect=[decisions, []])

        # Act
        results = []
        async for decision in iter_all_decisions("proj-1", mock_persistence):
            results.append(decision)

        # Assert
        assert len(results) == 5
        assert results[0].decision_id == "dec_0"
        assert results[4].decision_id == "dec_4"
        # Verify pagination calls
        assert mock_persistence.load_decisions.call_count == 2
        mock_persistence.load_decisions.assert_any_call("proj-1", limit=100, offset=0)
        mock_persistence.load_decisions.assert_any_call("proj-1", limit=100, offset=100)

    @pytest.mark.asyncio
    async def test_multiple_pages_of_decisions(self):
        """Test iteration across multiple pages."""
        # Arrange
        mock_persistence = AsyncMock()

        # Create 3 pages: 100 + 100 + 50 = 250 decisions
        page1 = [
            Decision(
                decision_id=f"dec_{i}",
                task_id="task-1",
                agent_id="agent-1",
                timestamp=datetime.now(timezone.utc),
                what=f"Decision {i}",
                why=f"Reason {i}",
                impact="low",
                affected_tasks=[],
                confidence=0.9,
            )
            for i in range(100)
        ]
        page2 = [
            Decision(
                decision_id=f"dec_{i}",
                task_id="task-1",
                agent_id="agent-1",
                timestamp=datetime.now(timezone.utc),
                what=f"Decision {i}",
                why=f"Reason {i}",
                impact="low",
                affected_tasks=[],
                confidence=0.9,
            )
            for i in range(100, 200)
        ]
        page3 = [
            Decision(
                decision_id=f"dec_{i}",
                task_id="task-1",
                agent_id="agent-1",
                timestamp=datetime.now(timezone.utc),
                what=f"Decision {i}",
                why=f"Reason {i}",
                impact="low",
                affected_tasks=[],
                confidence=0.9,
            )
            for i in range(200, 250)
        ]

        mock_persistence.load_decisions = AsyncMock(
            side_effect=[page1, page2, page3, []]
        )

        # Act
        results = []
        async for decision in iter_all_decisions("proj-1", mock_persistence):
            results.append(decision)

        # Assert
        assert len(results) == 250
        assert results[0].decision_id == "dec_0"
        assert results[249].decision_id == "dec_249"
        # Verify pagination: 4 calls (3 full pages + 1 empty)
        assert mock_persistence.load_decisions.call_count == 4

    @pytest.mark.asyncio
    async def test_empty_project_decisions(self):
        """Test iteration when project has no decisions."""
        # Arrange
        mock_persistence = AsyncMock()
        mock_persistence.load_decisions = AsyncMock(return_value=[])

        # Act
        results = []
        async for decision in iter_all_decisions("proj-1", mock_persistence):
            results.append(decision)

        # Assert
        assert len(results) == 0
        assert mock_persistence.load_decisions.call_count == 1


class TestIterAllArtifacts:
    """Test suite for iter_all_artifacts async generator."""

    @pytest.mark.asyncio
    async def test_single_page_of_artifacts(self):
        """Test iteration when all artifacts fit in one page."""
        # Arrange
        mock_persistence = AsyncMock()
        artifacts = [
            ArtifactMetadata(
                artifact_id=f"art_{i}",
                task_id="task-1",
                agent_id="agent-1",
                timestamp=datetime.now(timezone.utc),
                artifact_type="design",
                filename=f"design_{i}.md",
                relative_path=f"design_{i}.md",
                absolute_path=f"/path/to/design_{i}.md",
                description=f"Design document {i}",
                file_size_bytes=1024,
                sha256_hash=f"hash_{i}",
            )
            for i in range(5)
        ]
        mock_persistence.load_artifacts = AsyncMock(side_effect=[artifacts, []])

        # Act
        results = []
        async for artifact in iter_all_artifacts("proj-1", mock_persistence):
            results.append(artifact)

        # Assert
        assert len(results) == 5
        assert results[0].artifact_id == "art_0"
        assert results[4].artifact_id == "art_4"

    @pytest.mark.asyncio
    async def test_custom_batch_size(self):
        """Test using custom batch size for pagination."""
        # Arrange
        mock_persistence = AsyncMock()
        batch1 = [
            ArtifactMetadata(
                artifact_id=f"art_{i}",
                task_id="task-1",
                agent_id="agent-1",
                timestamp=datetime.now(timezone.utc),
                artifact_type="design",
                filename=f"design_{i}.md",
                relative_path=f"design_{i}.md",
                absolute_path=f"/path/to/design_{i}.md",
                description=f"Design document {i}",
                file_size_bytes=1024,
                sha256_hash=f"hash_{i}",
            )
            for i in range(50)
        ]
        batch2 = [
            ArtifactMetadata(
                artifact_id=f"art_{i}",
                task_id="task-1",
                agent_id="agent-1",
                timestamp=datetime.now(timezone.utc),
                artifact_type="design",
                filename=f"design_{i}.md",
                relative_path=f"design_{i}.md",
                absolute_path=f"/path/to/design_{i}.md",
                description=f"Design document {i}",
                file_size_bytes=1024,
                sha256_hash=f"hash_{i}",
            )
            for i in range(50, 75)
        ]
        mock_persistence.load_artifacts = AsyncMock(side_effect=[batch1, batch2, []])

        # Act
        results = []
        async for artifact in iter_all_artifacts(
            "proj-1", mock_persistence, batch_size=50
        ):
            results.append(artifact)

        # Assert
        assert len(results) == 75
        # Verify batch size was used
        mock_persistence.load_artifacts.assert_any_call("proj-1", limit=50, offset=0)
        mock_persistence.load_artifacts.assert_any_call("proj-1", limit=50, offset=50)


class TestIterAllTasks:
    """Test suite for iter_all_tasks async generator."""

    @pytest.mark.asyncio
    async def test_single_page_of_tasks(self):
        """Test iteration when all tasks fit in one page."""
        # Arrange
        mock_aggregator = AsyncMock()
        tasks = [
            TaskHistory(
                task_id=f"task-{i}",
                name=f"Task {i}",
                description=f"Description {i}",
                status="completed",
                estimated_hours=4.0,
                actual_hours=5.0,
            )
            for i in range(5)
        ]

        # Mock aggregate_project to return history with tasks
        mock_history = Mock()
        mock_history.tasks = tasks
        mock_aggregator.aggregate_project = AsyncMock(return_value=mock_history)

        # Act
        results = []
        async for task in iter_all_tasks("proj-1", mock_aggregator):
            results.append(task)

        # Assert
        assert len(results) == 5
        assert results[0].task_id == "task-0"
        assert results[4].task_id == "task-4"

    @pytest.mark.asyncio
    async def test_tasks_already_in_memory(self):
        """
        Test that tasks don't need pagination (they're built from paginated decisions/artifacts).

        Tasks are constructed from already-paginated decisions and artifacts,
        so we just need to iterate over them once they're in memory.
        """
        # Arrange
        mock_aggregator = AsyncMock()
        tasks = [
            TaskHistory(
                task_id=f"task-{i}",
                name=f"Task {i}",
                description=f"Description {i}",
                status="completed",
                estimated_hours=4.0,
                actual_hours=5.0,
            )
            for i in range(100)
        ]

        mock_history = Mock()
        mock_history.tasks = tasks
        mock_aggregator.aggregate_project = AsyncMock(return_value=mock_history)

        # Act
        results = []
        async for task in iter_all_tasks("proj-1", mock_aggregator):
            results.append(task)

        # Assert
        assert len(results) == 100
        # Only one call to aggregate_project (no pagination needed)
        assert mock_aggregator.aggregate_project.call_count == 1
