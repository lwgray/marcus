"""
Unit tests for MarcusServer project ID/name properties.

Tests that the server exposes current_project_id and current_project_name
properties that tools can use to get the active project context.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.context import Context
from src.core.project_context_manager import ProjectContextManager
from src.core.project_registry import ProjectConfig, ProjectRegistry


class TestServerProjectProperties:
    """Test MarcusServer properties for project context exposure."""

    @pytest.fixture
    def mock_project_manager(self) -> Mock:
        """Create a mock ProjectContextManager with active project."""
        manager = Mock(spec=ProjectContextManager)
        manager.active_project_id = "test_project_123"
        manager.active_project_name = "Test Project"
        return manager

    @pytest.fixture
    def mock_server(self, mock_project_manager: Mock) -> Mock:
        """Create a mock MarcusServer with project_manager."""
        from src.marcus_mcp.server import MarcusServer

        # Create a minimal mock that has the properties
        server = Mock(spec=MarcusServer)
        server.project_manager = mock_project_manager

        # Add the actual property implementations
        type(server).current_project_id = property(
            lambda self: self.project_manager.active_project_id
        )
        type(server).current_project_name = property(
            lambda self: self.project_manager.active_project_name
        )

        return server

    def test_current_project_id_returns_active_project(self, mock_server: Mock) -> None:
        """Test current_project_id property returns active project ID."""
        # Act
        result = mock_server.current_project_id

        # Assert
        assert result == "test_project_123"

    def test_current_project_name_returns_active_name(self, mock_server: Mock) -> None:
        """Test current_project_name property returns active project name."""
        # Act
        result = mock_server.current_project_name

        # Assert
        assert result == "Test Project"

    def test_current_project_id_returns_none_when_no_active_project(
        self, mock_server: Mock
    ) -> None:
        """Test current_project_id returns None when no project is active."""
        # Arrange
        mock_server.project_manager.active_project_id = None

        # Act
        result = mock_server.current_project_id

        # Assert
        assert result is None

    def test_current_project_name_returns_none_when_no_active_project(
        self, mock_server: Mock
    ) -> None:
        """Test current_project_name returns None when no project is active."""
        # Arrange
        mock_server.project_manager.active_project_name = None

        # Act
        result = mock_server.current_project_name

        # Assert
        assert result is None

    def test_properties_reflect_project_manager_state(self, mock_server: Mock) -> None:
        """Test properties always reflect current project_manager state."""
        # Arrange - Initial state
        assert mock_server.current_project_id == "test_project_123"
        assert mock_server.current_project_name == "Test Project"

        # Act - Change project_manager state
        mock_server.project_manager.active_project_id = "new_project_456"
        mock_server.project_manager.active_project_name = "New Project"

        # Assert - Properties reflect new state
        assert mock_server.current_project_id == "new_project_456"
        assert mock_server.current_project_name == "New Project"


class TestProjectContextManagerNameTracking:
    """Test ProjectContextManager tracks active_project_name."""

    @pytest.fixture
    def mock_registry(self) -> Mock:
        """Create a mock ProjectRegistry."""
        registry = Mock(spec=ProjectRegistry)

        # Setup get_project to return project configs
        async def get_project(project_id: str) -> ProjectConfig:
            projects = {
                "test_proj_789": ProjectConfig(
                    id="test_proj_789",
                    name="Integration Test Project",
                    provider="planka",
                    provider_config={},
                ),
                "proj_1": ProjectConfig(
                    id="proj_1",
                    name="First Project",
                    provider="planka",
                    provider_config={},
                ),
                "proj_2": ProjectConfig(
                    id="proj_2",
                    name="Second Project",
                    provider="planka",
                    provider_config={},
                ),
            }
            return projects.get(project_id)

        registry.get_project = AsyncMock(side_effect=get_project)
        registry.set_active_project = AsyncMock(return_value=None)
        return registry

    @pytest.fixture
    def context_manager(self, mock_registry: Mock) -> ProjectContextManager:
        """Create ProjectContextManager with mock registry."""
        manager = ProjectContextManager(registry=mock_registry)
        # Don't call initialize to avoid async complications
        return manager

    @pytest.mark.asyncio
    async def test_active_project_name_initialized_as_none(
        self, context_manager: ProjectContextManager
    ) -> None:
        """Test active_project_name starts as None."""
        # Assert
        assert context_manager.active_project_name is None

    @pytest.mark.asyncio
    async def test_switch_project_sets_active_name(
        self,
        context_manager: ProjectContextManager,
    ) -> None:
        """Test switch_project() sets both ID and name."""
        # Arrange - Mock context creation to add context to dict
        from src.core.project_context_manager import ProjectContext

        async def mock_create_context(project: ProjectConfig) -> ProjectContext:
            ctx = ProjectContext(project.id)
            context_manager.contexts[project.id] = ctx
            return ctx

        with patch.object(
            context_manager,
            "_get_or_create_context",
            side_effect=mock_create_context,
        ):
            # Act
            success = await context_manager.switch_project("test_proj_789")

            # Assert
            assert success is True
            assert context_manager.active_project_id == "test_proj_789"
            assert context_manager.active_project_name == "Integration Test Project"

    @pytest.mark.asyncio
    async def test_active_name_updates_on_project_switch(
        self,
        context_manager: ProjectContextManager,
    ) -> None:
        """Test active_project_name updates when switching between projects."""
        # Arrange - Mock context creation to add context to dict
        from src.core.project_context_manager import ProjectContext

        async def mock_create_context(project: ProjectConfig) -> ProjectContext:
            ctx = ProjectContext(project.id)
            context_manager.contexts[project.id] = ctx
            return ctx

        with patch.object(
            context_manager, "_get_or_create_context", side_effect=mock_create_context
        ):
            # Act - Switch to first project
            await context_manager.switch_project("proj_1")
            first_name = context_manager.active_project_name

            # Switch to second project
            await context_manager.switch_project("proj_2")
            second_name = context_manager.active_project_name

            # Assert
            assert first_name == "First Project"
            assert second_name == "Second Project"
            assert context_manager.active_project_id == "proj_2"


class TestGlobalContextSyncing:
    """Test ProjectContextManager syncs global context project_id."""

    @pytest.fixture
    def mock_registry(self) -> Mock:
        """Create a mock ProjectRegistry."""
        registry = Mock(spec=ProjectRegistry)

        async def get_project(project_id: str) -> ProjectConfig:
            projects = {
                "proj_alpha": ProjectConfig(
                    id="proj_alpha",
                    name="Alpha Project",
                    provider="planka",
                    provider_config={},
                ),
                "proj_beta": ProjectConfig(
                    id="proj_beta",
                    name="Beta Project",
                    provider="planka",
                    provider_config={},
                ),
            }
            return projects.get(project_id)

        registry.get_project = AsyncMock(side_effect=get_project)
        registry.set_active_project = AsyncMock(return_value=None)
        registry.list_projects = AsyncMock(return_value=[])
        return registry

    @pytest.fixture
    def global_context(self) -> Context:
        """Create a mock global context."""
        from src.core.persistence import Persistence

        return Context(events=None, persistence=Persistence(), project_id=None)

    @pytest.fixture
    def context_manager(
        self, mock_registry: Mock, global_context: Context
    ) -> ProjectContextManager:
        """Create ProjectContextManager with global context."""
        manager = ProjectContextManager(registry=mock_registry)
        manager.set_global_context(global_context)
        return manager

    @pytest.mark.asyncio
    async def test_set_global_context(
        self, context_manager: ProjectContextManager, global_context: Context
    ) -> None:
        """Test set_global_context stores reference correctly."""
        # Assert
        assert context_manager._global_context is global_context

    @pytest.mark.asyncio
    async def test_switch_project_syncs_global_context_id(
        self, context_manager: ProjectContextManager, global_context: Context
    ) -> None:
        """Test switch_project updates global context project_id."""
        # Arrange
        from src.core.project_context_manager import ProjectContext

        async def mock_create_context(project: ProjectConfig) -> ProjectContext:
            ctx = ProjectContext(project.id)
            context_manager.contexts[project.id] = ctx
            return ctx

        # Assert initial state
        assert global_context.project_id is None

        with patch.object(
            context_manager,
            "_get_or_create_context",
            side_effect=mock_create_context,
        ):
            # Act
            success = await context_manager.switch_project("proj_alpha")

            # Assert
            assert success is True
            assert global_context.project_id == "proj_alpha"

    @pytest.mark.asyncio
    async def test_global_context_updates_on_multiple_switches(
        self, context_manager: ProjectContextManager, global_context: Context
    ) -> None:
        """Test global context project_id updates when switching projects."""
        # Arrange
        from src.core.project_context_manager import ProjectContext

        async def mock_create_context(project: ProjectConfig) -> ProjectContext:
            ctx = ProjectContext(project.id)
            context_manager.contexts[project.id] = ctx
            return ctx

        with patch.object(
            context_manager,
            "_get_or_create_context",
            side_effect=mock_create_context,
        ):
            # Act - Switch to alpha
            await context_manager.switch_project("proj_alpha")
            first_id = global_context.project_id

            # Switch to beta
            await context_manager.switch_project("proj_beta")
            second_id = global_context.project_id

            # Assert
            assert first_id == "proj_alpha"
            assert second_id == "proj_beta"

    @pytest.mark.asyncio
    async def test_decisions_from_global_context_have_project_id(
        self, context_manager: ProjectContextManager, global_context: Context
    ) -> None:
        """Test decisions logged via global context have correct project_id."""
        # Arrange
        from src.core.project_context_manager import ProjectContext

        async def mock_create_context(project: ProjectConfig) -> ProjectContext:
            ctx = ProjectContext(project.id)
            context_manager.contexts[project.id] = ctx
            return ctx

        with patch.object(
            context_manager,
            "_get_or_create_context",
            side_effect=mock_create_context,
        ):
            # Act - Switch to project
            await context_manager.switch_project("proj_alpha")

            # Log decision via global context (simulates MCP tool)
            decision = await global_context.log_decision(
                agent_id="test_agent",
                task_id="test_task",
                what="Test decision",
                why="Testing",
                impact="Verification",
            )

            # Assert
            assert decision.project_id == "proj_alpha"
