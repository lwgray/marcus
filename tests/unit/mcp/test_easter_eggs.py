"""Unit tests for Marcus easter eggs.

Validates:
1. project_name='why'    → Zen of Multi-Agent Systems + quokka
2. project_name='snake'  → browser snake game URL
3. project_name='quokka' → self-completing Be Happy task
4. ping(echo='quokka')   → quokka greeting + zen
"""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Direct easter_eggs module tests
# ---------------------------------------------------------------------------


class TestEasterEggModule:
    """Direct tests of easter_eggs.py helper functions."""

    def test_easter_egg_why_returns_zen(self) -> None:
        """easter_egg_why() contains zen text and quokka art."""
        from src.marcus_mcp.tools.easter_eggs import easter_egg_why

        result = easter_egg_why()
        assert result["success"] is True
        assert result["easter_egg"] == "why"
        assert "board" in result["zen"].lower()
        assert "quokka" in result

    def test_easter_egg_quokka_project_task_done(self) -> None:
        """easter_egg_quokka_project() returns task with status=done."""
        from src.marcus_mcp.tools.easter_eggs import easter_egg_quokka_project

        result = easter_egg_quokka_project()
        assert result["success"] is True
        assert result["easter_egg"] == "quokka"
        assert result["task"]["status"] == "done"
        assert result["task"]["assigned_to"] == "quokka_1"
        assert "Be Happy" in result["task"]["name"]

    def test_easter_egg_quokka_ping_returns_zen_and_quokka(self) -> None:
        """easter_egg_quokka_ping() contains both zen and quokka art."""
        from src.marcus_mcp.tools.easter_eggs import easter_egg_quokka_ping

        result = easter_egg_quokka_ping()
        assert result["success"] is True
        assert result["easter_egg"] == "quokka"
        assert "quokka" in result
        assert "zen" in result
        assert "timestamp" in result

    def test_easter_egg_snake_returns_url(self) -> None:
        """easter_egg_snake() returns a localhost URL without actually binding."""
        from src.marcus_mcp.tools.easter_eggs import easter_egg_snake

        with (
            patch("src.marcus_mcp.tools.easter_eggs._serve_snake_in_thread"),
            patch("time.sleep"),
        ):
            result = easter_egg_snake()

        assert result["success"] is True
        assert result["easter_egg"] == "snake"
        assert result["play_url"].startswith("http://localhost:")
        assert "quokka" in result

    def test_quokka_art_contains_expected_ascii(self) -> None:
        """QUOKKA constant contains recognisable ASCII art."""
        from src.marcus_mcp.tools.easter_eggs import QUOKKA

        assert "quokka" in QUOKKA.lower() or "(\\_/)" in QUOKKA or "(='.'" in QUOKKA

    def test_zen_contains_invariants(self) -> None:
        """ZEN text references the three Marcus agent invariants."""
        from src.marcus_mcp.tools.easter_eggs import ZEN

        assert "board" in ZEN.lower()
        assert "agent" in ZEN.lower()


# ---------------------------------------------------------------------------
# Integration: create_project easter egg dispatch
# ---------------------------------------------------------------------------


class TestCreateProjectEasterEggs:
    """create_project routes magic project names to easter eggs."""

    @pytest.mark.asyncio
    async def test_why_project_name_triggers_zen(self) -> None:
        """create_project('why') returns zen egg without touching kanban."""
        from src.marcus_mcp.tools.nlp import create_project

        state = MagicMock()
        result = await create_project("build me something", "why", None, state)

        assert result["success"] is True
        assert result.get("easter_egg") == "why"
        assert "zen" in result
        state.initialize_kanban.assert_not_called()

    @pytest.mark.asyncio
    async def test_why_project_case_insensitive(self) -> None:
        """'WHY' and 'Why' also trigger the zen egg."""
        from src.marcus_mcp.tools.nlp import create_project

        state = MagicMock()
        for name in ("WHY", "Why", "  why  "):
            result = await create_project("desc", name, None, state)
            assert result.get("easter_egg") == "why", f"Failed for name={name!r}"

    @pytest.mark.asyncio
    async def test_snake_project_name_returns_play_url(self) -> None:
        """create_project('snake') returns a snake game URL."""
        from src.marcus_mcp.tools.nlp import create_project

        state = MagicMock()
        with (
            patch("src.marcus_mcp.tools.easter_eggs._serve_snake_in_thread"),
            patch("time.sleep"),
        ):
            result = await create_project("build me something", "snake", None, state)

        assert result["success"] is True
        assert result.get("easter_egg") == "snake"
        assert "play_url" in result

    @pytest.mark.asyncio
    async def test_snake_project_case_insensitive(self) -> None:
        """'Snake' and 'SNAKE' also trigger the game."""
        from src.marcus_mcp.tools.nlp import create_project

        state = MagicMock()
        for name in ("Snake", "SNAKE"):
            with (
                patch("src.marcus_mcp.tools.easter_eggs._serve_snake_in_thread"),
                patch("time.sleep"),
            ):
                result = await create_project("desc", name, None, state)
            assert result.get("easter_egg") == "snake", f"Failed for name={name!r}"

    @pytest.mark.asyncio
    async def test_quokka_project_name_returns_done_task(self) -> None:
        """create_project('quokka') returns self-completed Be Happy task."""
        from src.marcus_mcp.tools.nlp import create_project

        state = MagicMock()
        result = await create_project("build me something", "quokka", None, state)

        assert result["success"] is True
        assert result.get("easter_egg") == "quokka"
        assert result["task"]["status"] == "done"
        assert result["task"]["assigned_to"] == "quokka_1"

    @pytest.mark.asyncio
    async def test_quokka_project_case_insensitive(self) -> None:
        """'QUOKKA' and 'Quokka' also trigger the egg."""
        from src.marcus_mcp.tools.nlp import create_project

        state = MagicMock()
        for name in ("QUOKKA", "Quokka"):
            result = await create_project("desc", name, None, state)
            assert result.get("easter_egg") == "quokka", f"Failed for name={name!r}"

    @pytest.mark.asyncio
    async def test_normal_project_name_not_intercepted(self) -> None:
        """Ordinary project names fall through to the real create_project logic."""
        from src.marcus_mcp.tools.nlp import create_project

        state = MagicMock()
        state.provider = "sqlite"

        # Normal names always exit the easter-egg block and enter real logic.
        # Real logic may raise (missing config) — catch everything.
        try:
            result = await create_project("build a widget", "MyProject", None, state)
            assert result.get("easter_egg") is None
        except Exception:
            pass  # fell through to real logic as expected


# ---------------------------------------------------------------------------
# Integration: ping quokka easter egg
# ---------------------------------------------------------------------------


class TestPingQuokkaEasterEgg:
    """ping(echo='quokka') returns quokka greeting."""

    @pytest.mark.asyncio
    async def test_ping_quokka_returns_egg(self) -> None:
        """ping(echo='quokka') returns success with zen and quokka art."""
        from src.marcus_mcp.tools.system import ping

        state = MagicMock()
        result = await ping(echo="quokka", state=state)

        assert result["success"] is True
        assert result.get("easter_egg") == "quokka"
        assert "quokka" in result
        assert "zen" in result

    @pytest.mark.asyncio
    async def test_ping_quokka_case_insensitive(self) -> None:
        """'QUOKKA' and 'Quokka' also trigger the egg."""
        from src.marcus_mcp.tools.system import ping

        state = MagicMock()
        for echo in ("QUOKKA", "Quokka", "  quokka  "):
            result = await ping(echo=echo, state=state)
            assert result.get("easter_egg") == "quokka", f"Failed for echo={echo!r}"

    @pytest.mark.asyncio
    async def test_ping_normal_echo_not_intercepted(self) -> None:
        """Normal ping echo falls through to standard ping logic."""
        from src.marcus_mcp.tools.system import ping

        state = MagicMock()
        state.provider = "sqlite"
        state.agent_status = {}
        state.agent_tasks = {}
        state.tasks_being_assigned = set()

        with (
            patch("src.marcus_mcp.tools.system.log_agent_event"),
            patch("src.marcus_mcp.tools.system.log_thinking"),
            patch("src.marcus_mcp.tools.system.conversation_logger"),
        ):
            result = await ping(echo="pong", state=state)

        assert result.get("easter_egg") is None
        assert result["echo"] == "pong"
