"""
Unit tests for project_info.json server-side write in create_project.

Covers:
- Normal success path writes project_info.json (Bug 1 fix)
- Dedup cache path also writes project_info.json (Codex P1 fix)
"""

import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _make_state(board_id: str = "board-test") -> MagicMock:
    """Create minimal mock state with a kanban_client that has board_id."""
    state = MagicMock()
    state.kanban_client = MagicMock()
    state.kanban_client.board_id = board_id
    state.log_event = MagicMock()
    state.events = None
    return state


class TestCreateProjectInfoWrite:
    """Tests for server-side project_info.json write in create_project."""

    @pytest.mark.asyncio
    async def test_dedup_cache_writes_project_info_json(self, tmp_path: Path) -> None:
        """
        Verify the dedup cached-result path also writes project_info.json.

        Codex P1: The normal success path wrote the file, but the 10-minute
        dedup cache early-return at nlp.py:242 bypassed the write. If the
        runner deleted project_info.json at startup and then retried
        create_project within the dedup window, it would wait forever for
        a file that was never written.
        """
        from src.marcus_mcp.tools import nlp as nlp_module

        info_path = tmp_path / "project_info.json"
        cached: dict[str, Any] = {
            "success": True,
            "project_id": "proj-cached",
            "tasks_created": 5,
            "recommended_agents": 8,
        }

        # Seed the dedup cache as if a prior successful call happened 30s ago
        dedup_key = "CachedProject:Build a simple todo app"
        nlp_module._recent_create_project_calls[dedup_key] = (
            time.time() - 30,
            cached,
        )

        try:
            state = _make_state()
            options: dict[str, Any] = {
                "project_info_path": str(info_path),
                "provider": "sqlite",
                "project_root": str(tmp_path / "impl"),
            }

            result = await nlp_module.create_project(
                description="Build a simple todo app",
                project_name="CachedProject",
                options=options,
                state=state,
            )

            assert result["success"] is True
            assert result["project_id"] == "proj-cached"
            assert (
                info_path.exists()
            ), "project_info.json must be written even on dedup cache hit"
            written = json.loads(info_path.read_text())
            assert written["project_id"] == "proj-cached"
            assert written["recommended_agents"] == 8
        finally:
            nlp_module._recent_create_project_calls.pop(dedup_key, None)

    @pytest.mark.asyncio
    async def test_dedup_cache_no_write_without_project_info_path(
        self, tmp_path: Path
    ) -> None:
        """No file write on dedup cache hit when project_info_path not set.

        Confirms the write is conditional on the option being present —
        does not regress Direct MCP usage (no runner) where the option
        is never passed.
        """
        from src.marcus_mcp.tools import nlp as nlp_module

        cached: dict[str, Any] = {
            "success": True,
            "project_id": "proj-no-path",
            "tasks_created": 3,
            "recommended_agents": 4,
        }

        dedup_key = "NoCachedPath:Build a simple API"
        nlp_module._recent_create_project_calls[dedup_key] = (
            time.time() - 30,
            cached,
        )

        try:
            state = _make_state()
            # No project_info_path option
            options: dict[str, Any] = {
                "provider": "sqlite",
                "project_root": str(tmp_path / "impl"),
            }

            result = await nlp_module.create_project(
                description="Build a simple API",
                project_name="NoCachedPath",
                options=options,
                state=state,
            )

            assert result["success"] is True
            # No file should have been created
            assert not (tmp_path / "project_info.json").exists()
        finally:
            nlp_module._recent_create_project_calls.pop(dedup_key, None)
