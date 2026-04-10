"""
Unit tests for project registry integration in the natural-language
project creation MCP tool.

Tests verify that :func:`src.marcus_mcp.tools.nlp.create_project`
registers newly created projects in Marcus's ``ProjectRegistry`` and
forces a fresh project even when a same-named project already exists.
"""

from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.project_registry import ProjectConfig


@pytest.fixture(autouse=True)
def _mock_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure ANTHROPIC_API_KEY is set so config validation passes."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-for-unit-tests")


class TestCreateProjectWithDiscovery:
    """Test suite for create_project with project registry integration."""

    @pytest.fixture
    def mock_state(self) -> Mock:
        """Create a mock Marcus server state with a ready kanban client.

        Returns
        -------
        Mock
            A mock ``state`` whose ``kanban_client`` already has
            ``project_id`` and ``board_id`` set so ``create_project`` can
            register the project without hitting a real provider.
        """
        state = Mock()
        state.log_event = Mock()

        # Kanban client set up as if KanbanFactory created a fresh client.
        # create_project uses KanbanFactory to (re)create the client, so we
        # patch that call below rather than relying on this mock for creation.
        state.kanban_client = Mock()
        state.kanban_client.provider = "planka"
        state.kanban_client.project_id = "planka-new-123"
        state.kanban_client.board_id = "planka-board-456"
        state.kanban_client.connect = AsyncMock()
        state.kanban_client.create_task = AsyncMock(return_value={"id": "task-123"})

        state.ai_engine = Mock()
        state.subtask_manager = Mock()
        state._subtasks_migrated = False

        state.project_registry = Mock()
        state.project_registry.list_projects = AsyncMock(return_value=[])
        state.project_registry.add_project = AsyncMock(
            return_value="marcus-proj-id-123"
        )
        state.project_registry.get_active_project = AsyncMock(return_value=None)

        state.project_manager = Mock()
        state.project_manager.switch_project = AsyncMock(return_value=True)
        state.project_manager.get_kanban_client = AsyncMock(
            return_value=state.kanban_client
        )
        state.refresh_project_state = AsyncMock()
        return state

    @pytest.fixture
    def sample_existing_project(self) -> ProjectConfig:
        """Build a ``ProjectConfig`` to stand in for a pre-existing project."""
        return ProjectConfig(
            id="existing-123",
            name="MyAPI",
            provider="planka",
            provider_config={
                "project_id": "planka-789",
                "board_id": "board-101",
            },
            created_at=datetime.now(timezone.utc),
            last_used=datetime.now(timezone.utc),
            tags=["backend"],
        )

    @pytest.fixture(autouse=True)
    def _clear_dedup_cache(self) -> None:
        """Clear the per-process dedup cache between tests.

        ``create_project`` guards against duplicate invocations within a
        10-minute window via a module-level cache. Without clearing, the
        second test in the suite would see a duplicate and short-circuit.
        """
        from src.marcus_mcp.tools import nlp as nlp_module

        nlp_module._recent_create_project_calls.clear()
        yield
        nlp_module._recent_create_project_calls.clear()

    @pytest.mark.asyncio
    async def test_create_project_with_no_existing_projects(
        self, mock_state: Mock
    ) -> None:
        """``create_project`` registers a fresh project when none exist."""
        from src.marcus_mcp.tools.nlp import create_project

        mock_state.project_registry.list_projects = AsyncMock(return_value=[])

        creator_result: Dict[str, Any] = {
            "success": True,
            "project_name": "MyAPI",
            "tasks_created": 5,
            "board": {
                "project_name": "MyAPI",
                "board_name": "Main Board",
            },
        }

        with (
            patch(
                "src.integrations.nlp_tools.NaturalLanguageProjectCreator"
            ) as mock_creator_cls,
            patch(
                "src.integrations.kanban_factory.KanbanFactory.create"
            ) as mock_factory,
        ):
            mock_factory.return_value = mock_state.kanban_client
            mock_creator = mock_creator_cls.return_value
            mock_creator.create_project_from_description = AsyncMock(
                return_value=creator_result
            )

            result = await create_project(
                description="Build a REST API",
                project_name="MyAPI",
                options={"provider": "planka"},
                state=mock_state,
            )

        assert result["success"] is True
        mock_state.project_registry.add_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_project_forces_new_even_when_named_project_exists(
        self,
        mock_state: Mock,
        sample_existing_project: ProjectConfig,
    ) -> None:
        """``create_project`` always creates a new project.

        It never reuses an existing project with the same name — the tool
        is explicitly a "new project" entry point (see the docstring on
        :func:`src.marcus_mcp.tools.nlp.create_project`).
        """
        from src.marcus_mcp.tools.nlp import create_project

        mock_state.project_registry.list_projects = AsyncMock(
            return_value=[sample_existing_project]
        )

        creator_result: Dict[str, Any] = {
            "success": True,
            "project_name": "MyAPI 2",
            "tasks_created": 5,
            "board": {
                "project_name": "MyAPI 2",
                "board_name": "Main Board",
            },
        }

        with (
            patch(
                "src.integrations.nlp_tools.NaturalLanguageProjectCreator"
            ) as mock_creator_cls,
            patch(
                "src.integrations.kanban_factory.KanbanFactory.create"
            ) as mock_factory,
        ):
            mock_factory.return_value = mock_state.kanban_client
            mock_creator = mock_creator_cls.return_value
            mock_creator.create_project_from_description = AsyncMock(
                return_value=creator_result
            )

            result = await create_project(
                description="Build a REST API v2",
                project_name="MyAPI 2",
                options={"provider": "planka"},
                state=mock_state,
            )

        assert result["success"] is True
        mock_state.project_registry.add_project.assert_called_once()
        mock_state.project_manager.switch_project.assert_called()

    @pytest.mark.asyncio
    async def test_create_project_clears_stale_config_ids(
        self, mock_state: Mock
    ) -> None:
        """Stale config IDs on the kanban client are cleared before creation.

        ``create_project`` must reset any pre-existing ``project_id`` and
        ``board_id`` on the kanban client so the creator produces a fresh
        project instead of reusing a stale board.
        """
        from src.marcus_mcp.tools.nlp import create_project

        # Simulate stale IDs left over from a previous session.
        mock_state.kanban_client.project_id = "stale-project-999"
        mock_state.kanban_client.board_id = "1555320228445946953"

        creator_result: Dict[str, Any] = {
            "success": True,
            "project_name": "Real-Time Notification System",
            "tasks_created": 5,
            "board": {
                "project_name": "Real-Time Notification System",
                "board_name": "Main Board",
            },
        }

        with (
            patch(
                "src.integrations.nlp_tools.NaturalLanguageProjectCreator"
            ) as mock_creator_cls,
            patch(
                "src.integrations.kanban_factory.KanbanFactory.create"
            ) as mock_factory,
        ):
            # After KanbanFactory.create, mimic a fresh client with new IDs.
            fresh_client = Mock()
            fresh_client.provider = "planka"
            fresh_client.project_id = "new-proj-123"
            fresh_client.board_id = "new-board-456"
            fresh_client.connect = AsyncMock()
            fresh_client.create_task = AsyncMock()
            mock_factory.return_value = fresh_client
            mock_state.project_manager.get_kanban_client = AsyncMock(
                return_value=fresh_client
            )

            mock_creator = mock_creator_cls.return_value
            mock_creator.create_project_from_description = AsyncMock(
                return_value=creator_result
            )

            result = await create_project(
                description="Build a notification system",
                project_name="Real-Time Notification System",
                options={"provider": "planka"},
                state=mock_state,
            )

        assert result["success"] is True
        mock_state.project_registry.add_project.assert_called_once()
        mock_state.project_manager.switch_project.assert_called()

    @pytest.mark.asyncio
    async def test_create_project_registers_new_project_in_registry(
        self, mock_state: Mock
    ) -> None:
        """The newly created project is registered in ``ProjectRegistry``."""
        from src.marcus_mcp.tools.nlp import create_project

        mock_state.project_registry.list_projects = AsyncMock(return_value=[])

        creator_result: Dict[str, Any] = {
            "success": True,
            "project_name": "NewAPI",
            "tasks_created": 5,
            "board": {
                "project_name": "NewAPI",
                "board_name": "Main Board",
            },
        }

        with (
            patch(
                "src.integrations.nlp_tools.NaturalLanguageProjectCreator"
            ) as mock_creator_cls,
            patch(
                "src.integrations.kanban_factory.KanbanFactory.create"
            ) as mock_factory,
        ):
            mock_factory.return_value = mock_state.kanban_client
            mock_creator = mock_creator_cls.return_value
            mock_creator.create_project_from_description = AsyncMock(
                return_value=creator_result
            )

            result = await create_project(
                description="Build a REST API for new API",
                project_name="NewAPI",
                options={"provider": "planka"},
                state=mock_state,
            )

        assert result["success"] is True
        mock_state.project_registry.add_project.assert_called_once()
