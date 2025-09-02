"""
Integration tests for artifact working directory handling.

These tests verify that artifacts are created in the correct directories
and that Marcus installation directory is never used for artifact storage.
No mocking - uses real file system operations.
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

from src.marcus_mcp.tools.attachment import (
    _discover_artifacts_in_standard_locations,
    get_task_context,
    log_artifact,
)


class MockState:
    """Minimal state object for testing."""

    def __init__(self):
        self.task_artifacts = {}
        self.task_decisions = {}
        self.task_blockers = {}
        self.project_tasks = []
        self.kanban_client = None


class TestArtifactWorkingDirectory:
    """Test suite for artifact working directory handling."""

    @pytest.mark.asyncio
    async def test_log_artifact_with_working_directory(self):
        """Test that artifacts are created in the specified working directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            working_dir = Path(temp_dir)
            state = MockState()

            # Create artifact with working_directory
            result = await log_artifact(
                task_id="test-task-1",
                filename="api_spec.md",
                content="# API Specification\n\nTest content",
                artifact_type="api",
                working_directory=str(working_dir),
                description="Test API spec",
                state=state,
            )

            # Verify success
            assert result["success"] is True
            assert "error" not in result

            # Verify file was created in correct location
            expected_path = working_dir / "docs" / "api" / "api_spec.md"
            assert expected_path.exists()
            assert expected_path.read_text() == "# API Specification\n\nTest content"

            # Verify artifact was logged in state
            assert "test-task-1" in state.task_artifacts
            artifacts = state.task_artifacts["test-task-1"]
            assert len(artifacts) == 1
            assert artifacts[0]["filename"] == "api_spec.md"
            assert artifacts[0]["location"] == "docs/api/api_spec.md"

    @pytest.mark.asyncio
    async def test_log_artifact_without_working_directory_fails(self):
        """Test that log_artifact fails when working_directory is not provided."""
        state = MockState()

        # Try to create artifact without working_directory
        result = await log_artifact(
            task_id="test-task-2",
            filename="design.md",
            content="# Design Doc",
            artifact_type="design",
            state=state,
        )

        # Should fail
        assert result["success"] is False
        assert "working_directory is required" in result["error"]

        # No artifacts should be created
        assert "test-task-2" not in state.task_artifacts

    @pytest.mark.asyncio
    async def test_log_artifact_never_uses_marcus_directory(self):
        """Test that Marcus installation directory is never used for artifacts."""
        state = MockState()
        marcus_dir = Path(__file__).parent.parent.parent  # Marcus root

        # Try various ways that might default to Marcus directory
        # 1. Without working_directory
        result1 = await log_artifact(
            task_id="test-task-3",
            filename="test1.md",
            content="Test",
            artifact_type="documentation",
            state=state,
        )
        assert result1["success"] is False

        # 2. With empty string
        result2 = await log_artifact(
            task_id="test-task-3",
            filename="test2.md",
            content="Test",
            artifact_type="documentation",
            working_directory="",
            state=state,
        )
        assert result2["success"] is False

        # 3. With None (if parameter accepts it)
        result3 = await log_artifact(
            task_id="test-task-3",
            filename="test3.md",
            content="Test",
            artifact_type="documentation",
            working_directory=None,
            state=state,
        )
        assert result3["success"] is False

        # Verify no files were created in Marcus directory
        marcus_docs = marcus_dir / "docs"
        if marcus_docs.exists():
            # Check that no test files were created
            for test_file in ["test1.md", "test2.md", "test3.md"]:
                assert not any(
                    marcus_docs.rglob(test_file)
                ), f"{test_file} should not exist in Marcus directory"

    @pytest.mark.asyncio
    async def test_get_task_context_with_working_directory(self):
        """Test that get_task_context only returns artifacts from specified directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            working_dir = Path(temp_dir)
            state = MockState()

            # Create a task
            from datetime import datetime

            from src.core.models import Priority, Task, TaskStatus

            task = Task(
                id="test-task-4",
                name="Test Task",
                description="Test task for context",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=1.0,
            )
            state.project_tasks = [task]

            # Create some artifacts in the working directory
            await log_artifact(
                task_id="test-task-4",
                filename="spec.md",
                content="# Specification",
                artifact_type="specification",
                working_directory=str(working_dir),
                state=state,
            )

            # Create artifact in a different directory (should not be found)
            with tempfile.TemporaryDirectory() as other_dir:
                other_working_dir = Path(other_dir)
                other_state = MockState()
                await log_artifact(
                    task_id="other-task",
                    filename="other.md",
                    content="# Other",
                    artifact_type="documentation",
                    working_directory=str(other_working_dir),
                    state=other_state,
                )

                # Get context with working_directory
                result = await get_task_context(
                    task_id="test-task-4",
                    working_directory=str(working_dir),
                    state=state,
                )

                assert result["success"] is True
                context = result["context"]
                assert "artifacts" in context

                # Should only find artifacts from working_dir
                artifacts = context["artifacts"]
                assert len(artifacts) >= 1  # At least the one we created
                assert all(
                    "spec.md" in a["filename"] or a.get("discovered", False)
                    for a in artifacts
                )
                # Should not find artifacts from other directory
                assert not any("other.md" in a["filename"] for a in artifacts)

    @pytest.mark.asyncio
    async def test_get_task_context_without_working_directory_returns_empty(self):
        """Test that get_task_context returns empty artifacts without working_directory."""
        state = MockState()

        # Create a task
        from datetime import datetime

        from src.core.models import Priority, Task, TaskStatus

        task = Task(
            id="test-task-5",
            name="Test Task",
            description="Test task",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=1.0,
        )
        state.project_tasks = [task]

        # Get context without working_directory
        result = await get_task_context(
            task_id="test-task-5",
            state=state,
        )

        # Should succeed but with no discovered artifacts
        assert result["success"] is True
        context = result["context"]
        assert "artifacts" in context
        assert context["artifacts"] == []  # No artifacts without working directory

    @pytest.mark.asyncio
    async def test_multiple_agents_artifact_isolation(self):
        """Test that artifacts from different agents remain isolated."""
        # Create separate directories for two agents
        with (
            tempfile.TemporaryDirectory() as agent1_dir,
            tempfile.TemporaryDirectory() as agent2_dir,
        ):
            agent1_working = Path(agent1_dir)
            agent2_working = Path(agent2_dir)

            state1 = MockState()
            state2 = MockState()

            # Agent 1 creates artifacts
            await log_artifact(
                task_id="task-agent1",
                filename="agent1_design.md",
                content="# Agent 1 Design",
                artifact_type="design",
                working_directory=str(agent1_working),
                state=state1,
            )

            # Agent 2 creates artifacts
            await log_artifact(
                task_id="task-agent2",
                filename="agent2_design.md",
                content="# Agent 2 Design",
                artifact_type="design",
                working_directory=str(agent2_working),
                state=state2,
            )

            # Verify isolation - Agent 1's artifacts only in agent1_dir
            agent1_design = agent1_working / "docs" / "design" / "agent1_design.md"
            assert agent1_design.exists()
            assert not (
                agent1_working / "docs" / "design" / "agent2_design.md"
            ).exists()

            # Verify isolation - Agent 2's artifacts only in agent2_dir
            agent2_design = agent2_working / "docs" / "design" / "agent2_design.md"
            assert agent2_design.exists()
            assert not (
                agent2_working / "docs" / "design" / "agent1_design.md"
            ).exists()

            # Verify artifact discovery is isolated
            discovered1 = await _discover_artifacts_in_standard_locations(
                working_dir=agent1_working
            )
            discovered2 = await _discover_artifacts_in_standard_locations(
                working_dir=agent2_working
            )

            # Each should only find their own artifacts
            assert any("agent1_design.md" in a["filename"] for a in discovered1)
            assert not any("agent2_design.md" in a["filename"] for a in discovered1)

            assert any("agent2_design.md" in a["filename"] for a in discovered2)
            assert not any("agent1_design.md" in a["filename"] for a in discovered2)

    @pytest.mark.asyncio
    async def test_invalid_working_directory_paths(self):
        """Test that invalid working directory paths are rejected."""
        state = MockState()

        # Test with relative path
        result = await log_artifact(
            task_id="test-task-6",
            filename="test.md",
            content="Test",
            artifact_type="documentation",
            working_directory="./relative/path",
            state=state,
        )
        assert result["success"] is False
        assert "must be absolute path" in result["error"]

        # Test with non-existent directory
        result = await log_artifact(
            task_id="test-task-7",
            filename="test.md",
            content="Test",
            artifact_type="documentation",
            working_directory="/nonexistent/directory/path",
            state=state,
        )
        assert result["success"] is False
        assert "does not exist" in result["error"]

    @pytest.mark.asyncio
    async def test_artifact_with_custom_location_within_working_directory(self):
        """Test that custom locations are still relative to working directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            working_dir = Path(temp_dir)
            state = MockState()

            # Create artifact with custom location
            result = await log_artifact(
                task_id="test-task-8",
                filename="custom.md",
                content="# Custom Location",
                artifact_type="documentation",
                working_directory=str(working_dir),
                location="custom/path/to/custom.md",  # Custom relative path including filename
                state=state,
            )

            assert result["success"] is True

            # Verify file was created in working_dir + custom location
            expected_path = working_dir / "custom" / "path" / "to" / "custom.md"
            assert expected_path.exists()
            assert expected_path.read_text() == "# Custom Location"

            # Verify it's not in the default location
            default_path = working_dir / "docs" / "custom.md"
            assert not default_path.exists()
