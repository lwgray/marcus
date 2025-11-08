"""
Unit tests for ProjectHistoryPersistence SQLite refactor.

Tests the new SQLite-based storage for decisions and artifacts.
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from src.core.persistence import SQLitePersistence
from src.core.project_history import (
    ArtifactMetadata,
    Decision,
    ProjectHistoryPersistence,
)


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """Create temporary database for testing."""
    return tmp_path / "test_marcus.db"


@pytest.fixture
def persistence(temp_db: Path, tmp_path: Path) -> ProjectHistoryPersistence:
    """Create ProjectHistoryPersistence with temporary database."""
    # Create a mock marcus root structure
    marcus_root = tmp_path / "marcus"
    marcus_root.mkdir()
    (marcus_root / "data").mkdir()

    # Move test db to the data directory
    test_db = marcus_root / "data" / "marcus.db"

    persistence = ProjectHistoryPersistence(marcus_root=marcus_root)
    return persistence


@pytest.fixture
async def sample_decisions(temp_db: Path) -> list[dict[str, Any]]:
    """Create sample decisions in SQLite."""
    backend = SQLitePersistence(db_path=temp_db)

    decisions = [
        {
            "decision_id": "dec_1_123.456",
            "task_id": "task_001",
            "agent_id": "agent_001",
            "timestamp": "2025-11-08T12:00:00+00:00",
            "what": "Chose PostgreSQL",
            "why": "Need ACID compliance",
            "impact": "Affects all data models",
            "affected_tasks": ["task_002"],
            "confidence": 0.9,
            "kanban_comment_url": None,
            "project_id": "test_project_001",
        },
        {
            "decision_id": "dec_2_123.789",
            "task_id": "task_002",
            "agent_id": "agent_001",
            "timestamp": "2025-11-08T13:00:00+00:00",
            "what": "Chose React",
            "why": "Team familiarity",
            "impact": "Affects frontend architecture",
            "affected_tasks": [],
            "confidence": 0.8,
            "kanban_comment_url": None,
            "project_id": "test_project_001",
        },
    ]

    for dec in decisions:
        await backend.store("decisions", dec["decision_id"], dec)

    return decisions


class TestProjectHistoryPersistence:
    """Test suite for ProjectHistoryPersistence SQLite refactor."""

    def test_initialization(self, persistence: ProjectHistoryPersistence) -> None:
        """Test ProjectHistoryPersistence initializes with SQLite backend."""
        # Arrange & Act: done in fixture
        # Assert
        assert persistence.db_path.name == "marcus.db"
        assert persistence.marcus_root.exists()
        assert persistence.history_dir.exists()

    @pytest.mark.asyncio
    async def test_load_decisions_empty(
        self, persistence: ProjectHistoryPersistence
    ) -> None:
        """Test load_decisions returns empty list when no decisions exist."""
        # Arrange
        project_id = "test_project_001"

        # Act
        decisions = await persistence.load_decisions(project_id)

        # Assert
        assert decisions == []

    @pytest.mark.asyncio
    async def test_load_decisions_from_sqlite(
        self,
        persistence: ProjectHistoryPersistence,
        temp_db: Path,
        sample_decisions: list[dict[str, Any]],
        tmp_path: Path,
    ) -> None:
        """Test load_decisions loads from SQLite backend."""
        # Arrange
        project_id = "test_project_001"

        # Update persistence to use the temp_db with sample data
        persistence.db_path = temp_db

        # Create conversation logs with project_id and task_ids
        conversations_dir = persistence.marcus_root / "logs" / "conversations"
        conversations_dir.mkdir(parents=True, exist_ok=True)
        conv_file = conversations_dir / "conversations_test.jsonl"

        import json

        with open(conv_file, "w") as f:
            # Add conversation entries for each task
            for task_id in ["task_001", "task_002"]:
                entry = {
                    "metadata": {
                        "project_id": project_id,
                        "task_id": task_id,
                    },
                    "message": f"Test message for {task_id}",
                }
                f.write(json.dumps(entry) + "\n")

        # Act
        decisions = await persistence.load_decisions(project_id)

        # Assert
        assert len(decisions) == 2
        assert isinstance(decisions[0], Decision)
        assert decisions[0].what == "Chose PostgreSQL"
        assert decisions[0].task_id == "task_001"
        assert decisions[0].project_id == "test_project_001"
        assert decisions[1].what == "Chose React"
        assert decisions[1].project_id == "test_project_001"

    @pytest.mark.asyncio
    async def test_load_decisions_timezone_aware(
        self,
        persistence: ProjectHistoryPersistence,
        temp_db: Path,
        sample_decisions: list[dict[str, Any]],
    ) -> None:
        """Test loaded decisions have timezone-aware timestamps."""
        # Arrange
        project_id = "test_project_001"
        persistence.db_path = temp_db

        # Create conversation logs
        conversations_dir = persistence.marcus_root / "logs" / "conversations"
        conversations_dir.mkdir(parents=True, exist_ok=True)
        conv_file = conversations_dir / "conversations_test.jsonl"

        import json

        with open(conv_file, "w") as f:
            for task_id in ["task_001", "task_002"]:
                entry = {
                    "metadata": {"project_id": project_id, "task_id": task_id},
                    "message": f"Test message for {task_id}",
                }
                f.write(json.dumps(entry) + "\n")

        # Act
        decisions = await persistence.load_decisions(project_id)

        # Assert
        assert len(decisions) > 0
        for decision in decisions:
            assert decision.timestamp.tzinfo is not None
            assert decision.timestamp.tzinfo == timezone.utc

    @pytest.mark.asyncio
    async def test_load_decisions_naive_timestamp_converted(
        self, persistence: ProjectHistoryPersistence, temp_db: Path
    ) -> None:
        """Test naive timestamps are converted to timezone-aware."""
        # Arrange
        backend = SQLitePersistence(db_path=temp_db)
        persistence.db_path = temp_db

        # Store decision with naive timestamp (no timezone)
        naive_decision = {
            "decision_id": "dec_3_456.789",
            "task_id": "task_003",
            "agent_id": "agent_002",
            "timestamp": "2025-11-08T14:00:00",  # No timezone info
            "what": "Chose MongoDB",
            "why": "Need flexible schema",
            "impact": "Affects data layer",
            "affected_tasks": [],
            "confidence": 0.7,
            "kanban_comment_url": None,
            "project_id": "test_project",
        }
        await backend.store("decisions", naive_decision["decision_id"], naive_decision)

        # Create conversation logs
        conversations_dir = persistence.marcus_root / "logs" / "conversations"
        conversations_dir.mkdir(parents=True, exist_ok=True)
        conv_file = conversations_dir / "conversations_test.jsonl"

        import json

        with open(conv_file, "w") as f:
            entry = {
                "metadata": {"project_id": "test_project", "task_id": "task_003"},
                "message": "Test message for task_003",
            }
            f.write(json.dumps(entry) + "\n")

        # Act
        decisions = await persistence.load_decisions("test_project")

        # Assert
        naive_loaded = [d for d in decisions if d.decision_id == "dec_3_456.789"][0]
        assert naive_loaded.timestamp.tzinfo is not None
        assert naive_loaded.timestamp.tzinfo == timezone.utc

    @pytest.mark.asyncio
    async def test_load_artifacts_empty(
        self, persistence: ProjectHistoryPersistence
    ) -> None:
        """Test load_artifacts returns empty list when no artifacts exist."""
        # Arrange
        project_id = "test_project_001"

        # Act
        artifacts = await persistence.load_artifacts(project_id)

        # Assert
        assert artifacts == []

    @pytest.mark.asyncio
    async def test_load_decisions_malformed_data(
        self, persistence: ProjectHistoryPersistence, temp_db: Path
    ) -> None:
        """Test load_decisions skips malformed decision records."""
        # Arrange
        backend = SQLitePersistence(db_path=temp_db)
        persistence.db_path = temp_db

        # Store valid decision
        valid_dec = {
            "decision_id": "dec_4_111.222",
            "task_id": "task_004",
            "agent_id": "agent_003",
            "timestamp": "2025-11-08T15:00:00+00:00",
            "what": "Valid decision",
            "why": "Good reason",
            "impact": "Some impact",
            "project_id": "test_project",
        }
        await backend.store("decisions", valid_dec["decision_id"], valid_dec)

        # Store malformed decision (missing required fields)
        malformed_dec = {
            "decision_id": "dec_5_333.444",
            # Missing task_id, agent_id, etc.
            "what": "Incomplete decision",
        }
        await backend.store("decisions", malformed_dec["decision_id"], malformed_dec)

        # Create conversation logs
        conversations_dir = persistence.marcus_root / "logs" / "conversations"
        conversations_dir.mkdir(parents=True, exist_ok=True)
        conv_file = conversations_dir / "conversations_test.jsonl"

        import json

        with open(conv_file, "w") as f:
            entry = {
                "metadata": {"project_id": "test_project", "task_id": "task_004"},
                "message": "Test message for task_004",
            }
            f.write(json.dumps(entry) + "\n")

        # Act
        decisions = await persistence.load_decisions("test_project")

        # Assert - should only load valid decision, skip malformed
        assert len(decisions) == 1
        assert decisions[0].decision_id == "dec_4_111.222"


class TestDecisionFromDict:
    """Test suite for Decision.from_dict() method."""

    def test_from_dict_with_timezone_aware_timestamp(self) -> None:
        """Test from_dict handles timezone-aware timestamp correctly."""
        # Arrange
        data = {
            "decision_id": "dec_1",
            "task_id": "task_1",
            "agent_id": "agent_1",
            "timestamp": "2025-11-08T12:00:00+00:00",
            "what": "Decision",
            "why": "Reason",
            "impact": "Impact",
        }

        # Act
        decision = Decision.from_dict(data)

        # Assert
        assert decision.timestamp.tzinfo is not None
        assert decision.timestamp.hour == 12

    def test_from_dict_with_naive_timestamp(self) -> None:
        """Test from_dict converts naive timestamp to UTC."""
        # Arrange
        data = {
            "decision_id": "dec_2",
            "task_id": "task_2",
            "agent_id": "agent_2",
            "timestamp": "2025-11-08T12:00:00",  # Naive
            "what": "Decision",
            "why": "Reason",
            "impact": "Impact",
        }

        # Act
        decision = Decision.from_dict(data)

        # Assert
        assert decision.timestamp.tzinfo is not None
        assert decision.timestamp.tzinfo == timezone.utc
        assert decision.timestamp.hour == 12

    def test_from_dict_with_project_id(self) -> None:
        """Test from_dict handles project_id correctly."""
        # Arrange
        data = {
            "decision_id": "dec_3",
            "task_id": "task_3",
            "agent_id": "agent_3",
            "timestamp": "2025-11-08T12:00:00+00:00",
            "what": "Decision with project",
            "why": "Reason",
            "impact": "Impact",
            "project_id": "test_project_123",
        }

        # Act
        decision = Decision.from_dict(data)

        # Assert
        assert decision.project_id == "test_project_123"
        assert decision.to_dict()["project_id"] == "test_project_123"

    def test_from_dict_without_project_id(self) -> None:
        """Test from_dict handles missing project_id gracefully."""
        # Arrange
        data = {
            "decision_id": "dec_4",
            "task_id": "task_4",
            "agent_id": "agent_4",
            "timestamp": "2025-11-08T12:00:00+00:00",
            "what": "Decision without project",
            "why": "Reason",
            "impact": "Impact",
            # No project_id field
        }

        # Act
        decision = Decision.from_dict(data)

        # Assert
        assert decision.project_id is None
        assert decision.to_dict()["project_id"] is None


class TestArtifactMetadataFromDict:
    """Test suite for ArtifactMetadata.from_dict() method."""

    def test_from_dict_with_timezone_aware_timestamp(self) -> None:
        """Test from_dict handles timezone-aware timestamp correctly."""
        # Arrange
        data = {
            "artifact_id": "art_1",
            "task_id": "task_1",
            "agent_id": "agent_1",
            "timestamp": "2025-11-08T12:00:00+00:00",
            "filename": "spec.md",
            "artifact_type": "specification",
            "relative_path": "docs/spec.md",
            "absolute_path": "/path/to/docs/spec.md",
        }

        # Act
        artifact = ArtifactMetadata.from_dict(data)

        # Assert
        assert artifact.timestamp.tzinfo is not None
        assert artifact.timestamp.hour == 12

    def test_from_dict_with_naive_timestamp(self) -> None:
        """Test from_dict converts naive timestamp to UTC."""
        # Arrange
        data = {
            "artifact_id": "art_2",
            "task_id": "task_2",
            "agent_id": "agent_2",
            "timestamp": "2025-11-08T12:00:00",  # Naive
            "filename": "design.md",
            "artifact_type": "design",
            "relative_path": "docs/design.md",
            "absolute_path": "/path/to/docs/design.md",
        }

        # Act
        artifact = ArtifactMetadata.from_dict(data)

        # Assert
        assert artifact.timestamp.tzinfo is not None
        assert artifact.timestamp.tzinfo == timezone.utc
        assert artifact.timestamp.hour == 12

    def test_from_dict_with_project_id(self) -> None:
        """Test from_dict handles project_id correctly."""
        # Arrange
        data = {
            "artifact_id": "art_3",
            "task_id": "task_3",
            "agent_id": "agent_3",
            "timestamp": "2025-11-08T12:00:00+00:00",
            "filename": "spec.md",
            "artifact_type": "specification",
            "relative_path": "docs/spec.md",
            "absolute_path": "/path/to/docs/spec.md",
            "project_id": "test_project_456",
        }

        # Act
        artifact = ArtifactMetadata.from_dict(data)

        # Assert
        assert artifact.project_id == "test_project_456"
        assert artifact.to_dict()["project_id"] == "test_project_456"

    def test_from_dict_without_project_id(self) -> None:
        """Test from_dict handles missing project_id gracefully."""
        # Arrange
        data = {
            "artifact_id": "art_4",
            "task_id": "task_4",
            "agent_id": "agent_4",
            "timestamp": "2025-11-08T12:00:00+00:00",
            "filename": "api.md",
            "artifact_type": "api",
            "relative_path": "docs/api.md",
            "absolute_path": "/path/to/docs/api.md",
            # No project_id field
        }

        # Act
        artifact = ArtifactMetadata.from_dict(data)

        # Assert
        assert artifact.project_id is None
        assert artifact.to_dict()["project_id"] is None
