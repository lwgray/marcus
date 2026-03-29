"""
Unit tests for project config snapshot storage.

Tests that configuration snapshots are correctly built and stored
when projects are created via the create_project MCP tool.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_state() -> MagicMock:
    """Create a mock server state with AI engine."""
    state = MagicMock()
    state.ai_engine = MagicMock()
    state.ai_engine.llm = MagicMock()
    state.ai_engine.llm.providers = {
        "anthropic": MagicMock(),
        "local": MagicMock(),
    }
    return state


@pytest.fixture
def mock_config(tmp_path: Path) -> MagicMock:
    """Create a mock MarcusConfig pointing to temp dir."""
    config = MagicMock()
    config.ai.provider = "anthropic"
    config.ai.model = "claude-haiku-4-5-20251001"
    config.ai.temperature = 0.1
    config.data_dir = str(tmp_path)
    config.features.events = True
    config.features.context = True
    config.features.memory = False
    return config


class TestConfigSnapshot:
    """Test _store_config_snapshot function."""

    @pytest.mark.asyncio
    async def test_snapshot_contains_all_fields(
        self, mock_state: MagicMock, mock_config: MagicMock
    ) -> None:
        """Test snapshot includes ai, kanban, experiment, system."""
        from src.marcus_mcp.tools.nlp import _store_config_snapshot

        with patch(
            "src.config.marcus_config.get_config",
            return_value=mock_config,
        ):
            await _store_config_snapshot(
                mock_state,
                "proj-123",
                "Test Project",
                "sqlite",
                "prototype",
                {"team_size": 2},
            )

        # Read back from the DB
        db_path = Path(mock_config.data_dir) / "marcus.db"
        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT data FROM persistence "
            "WHERE collection='project_config' AND key='proj-123'"
        ).fetchone()
        conn.close()

        assert row is not None
        data = json.loads(row[0])
        assert data["project_id"] == "proj-123"
        assert data["project_name"] == "Test Project"
        assert "created_at" in data
        assert data["ai"]["provider"] == "anthropic"
        assert data["ai"]["model"] == "claude-haiku-4-5-20251001"
        assert data["ai"]["temperature"] == 0.1
        assert "anthropic" in data["ai"]["available_providers"]
        assert data["kanban"]["provider"] == "sqlite"
        assert data["experiment"]["complexity"] == "prototype"
        assert data["experiment"]["num_agents"] == 2
        assert data["system"]["features"]["events"] is True
        assert data["system"]["features"]["memory"] is False

    @pytest.mark.asyncio
    async def test_snapshot_uses_configured_data_dir(
        self, mock_state: MagicMock, mock_config: MagicMock
    ) -> None:
        """Test snapshot writes to cfg.data_dir."""
        from src.marcus_mcp.tools.nlp import _store_config_snapshot

        with patch(
            "src.config.marcus_config.get_config",
            return_value=mock_config,
        ):
            await _store_config_snapshot(
                mock_state,
                "proj-dir",
                "Dir Test",
                "sqlite",
                "prototype",
                None,
            )

        db_path = Path(mock_config.data_dir) / "marcus.db"
        assert db_path.exists()

    @pytest.mark.asyncio
    async def test_snapshot_handles_missing_ai_engine(
        self, mock_config: MagicMock
    ) -> None:
        """Test snapshot works when AI engine is unavailable."""
        from src.marcus_mcp.tools.nlp import _store_config_snapshot

        state = MagicMock()
        state.ai_engine = None

        with patch(
            "src.config.marcus_config.get_config",
            return_value=mock_config,
        ):
            await _store_config_snapshot(
                state,
                "proj-noai",
                "No AI",
                "sqlite",
                "prototype",
                None,
            )

        db_path = Path(mock_config.data_dir) / "marcus.db"
        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT data FROM persistence "
            "WHERE collection='project_config' AND key='proj-noai'"
        ).fetchone()
        conn.close()

        data = json.loads(row[0])
        assert data["ai"]["available_providers"] == []

    @pytest.mark.asyncio
    async def test_snapshot_failure_does_not_raise(self, mock_state: MagicMock) -> None:
        """Test that storage failure is logged, not raised."""
        from src.marcus_mcp.tools.nlp import _store_config_snapshot

        bad_config = MagicMock()
        bad_config.data_dir = "/nonexistent/path/that/will/fail"
        bad_config.ai.provider = "test"
        bad_config.ai.model = "test"
        bad_config.ai.temperature = 0.0
        bad_config.features.events = False
        bad_config.features.context = False
        bad_config.features.memory = False

        with patch(
            "src.config.marcus_config.get_config",
            return_value=bad_config,
        ):
            # Should not raise
            await _store_config_snapshot(
                mock_state,
                "proj-fail",
                "Fail Test",
                "sqlite",
                "prototype",
                None,
            )

    @pytest.mark.asyncio
    async def test_snapshot_default_num_agents(
        self, mock_state: MagicMock, mock_config: MagicMock
    ) -> None:
        """Test num_agents defaults to 1 when not in options."""
        from src.marcus_mcp.tools.nlp import _store_config_snapshot

        with patch(
            "src.config.marcus_config.get_config",
            return_value=mock_config,
        ):
            await _store_config_snapshot(
                mock_state,
                "proj-default",
                "Defaults",
                "sqlite",
                "standard",
                None,
            )

        db_path = Path(mock_config.data_dir) / "marcus.db"
        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT data FROM persistence "
            "WHERE collection='project_config' AND key='proj-default'"
        ).fetchone()
        conn.close()

        data = json.loads(row[0])
        assert data["experiment"]["num_agents"] == 1
