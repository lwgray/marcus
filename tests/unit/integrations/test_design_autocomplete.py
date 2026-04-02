"""
Unit tests for design task auto-completion (GH-297).

Tests the two-phase approach:
- Phase A (_generate_design_content): LLM generates content, writes
  files to disk, sets task status=DONE before board creation.
- Phase B (_register_design_via_mcp): Registers artifacts + decisions
  via MCP tools after state is available.

See: https://github.com/lwgray/marcus/issues/297
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.integrations.nlp_tools import (
    _generate_design_content,
    _register_design_via_mcp,
)


def _make_task(
    name: str,
    labels: list = None,
    status: TaskStatus = TaskStatus.TODO,
    description: str = "",
    task_id: str = None,
) -> Task:
    return Task(
        id=task_id or name.lower().replace(" ", "_"),
        name=name,
        description=description or f"Description for {name}",
        status=status,
        priority=Priority.HIGH,
        assigned_to=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        due_date=None,
        estimated_hours=0.1,
        labels=labels or [],
        dependencies=[],
    )


DESIGN_DESCRIPTION = """\
Design the architecture for Authentication which encompasses:

1. USER LOGIN
   Allow users to log in with email and password

Your design should define:
- Component boundaries
- Data flows
- Integration points
- Shared data models

Create design artifacts such as:
- Architecture diagrams
- API contracts
- Data models
- Integration specifications"""

MOCK_LLM_RESPONSE = json.dumps(
    {
        "artifacts": [
            {
                "filename": "auth-architecture.md",
                "artifact_type": "architecture",
                "content": "# Auth Architecture\n\n## Components\n...",
                "description": "Auth component boundaries",
            },
            {
                "filename": "auth-api.yaml",
                "artifact_type": "api",
                "content": "openapi: 3.0.0\npaths:\n  /login:\n...",
                "description": "Auth API contract",
            },
        ],
        "decisions": [
            {
                "what": "Chose JWT for auth tokens",
                "why": "Stateless, no server sessions needed",
                "impact": "All API endpoints must validate JWT",
            },
        ],
    }
)


# ---- Phase A Tests ----


class TestGenerateDesignContent:
    """Tests for Phase A: _generate_design_content."""

    @pytest.mark.asyncio
    @patch("src.ai.providers.llm_abstraction.LLMAbstraction")
    async def test_sets_design_task_status_to_done(self, mock_llm_cls, tmp_path):
        """Design tasks must be status=DONE after Phase A."""
        mock_llm = AsyncMock()
        mock_llm.analyze.return_value = MOCK_LLM_RESPONSE
        mock_llm_cls.return_value = mock_llm

        design_task = _make_task(
            "Design Authentication",
            labels=["design", "architecture"],
            description=DESIGN_DESCRIPTION,
        )
        impl_task = _make_task(
            "Implement Auth",
            labels=["backend"],
        )
        tasks = [design_task, impl_task]

        await _generate_design_content(
            tasks=tasks,
            project_description="Build auth system",
            project_name="Auth App",
            project_root=str(tmp_path),
        )

        # Design task is DONE
        assert design_task.status == TaskStatus.DONE
        assert "auto_completed" in design_task.labels
        # Implementation task is unchanged
        assert impl_task.status == TaskStatus.TODO

    @pytest.mark.asyncio
    @patch("src.ai.providers.llm_abstraction.LLMAbstraction")
    async def test_writes_artifact_files_to_disk(self, mock_llm_cls, tmp_path):
        """Artifact files must exist on disk after Phase A."""
        mock_llm = AsyncMock()
        mock_llm.analyze.return_value = MOCK_LLM_RESPONSE
        mock_llm_cls.return_value = mock_llm

        tasks = [
            _make_task(
                "Design Authentication",
                labels=["design", "architecture"],
                description=DESIGN_DESCRIPTION,
            )
        ]

        await _generate_design_content(
            tasks=tasks,
            project_description="Build auth",
            project_name="Auth",
            project_root=str(tmp_path),
        )

        assert (tmp_path / "docs" / "architecture" / "auth-architecture.md").exists()
        assert (tmp_path / "docs" / "api" / "auth-api.yaml").exists()

    @pytest.mark.asyncio
    @patch("src.ai.providers.llm_abstraction.LLMAbstraction")
    async def test_returns_content_for_phase_b(self, mock_llm_cls, tmp_path):
        """Phase A returns content dict keyed by task name for Phase B."""
        mock_llm = AsyncMock()
        mock_llm.analyze.return_value = MOCK_LLM_RESPONSE
        mock_llm_cls.return_value = mock_llm

        tasks = [
            _make_task(
                "Design Authentication",
                labels=["design", "architecture"],
                description=DESIGN_DESCRIPTION,
            )
        ]

        content = await _generate_design_content(
            tasks=tasks,
            project_description="Build auth",
            project_name="Auth",
            project_root=str(tmp_path),
        )

        assert "Design Authentication" in content
        assert len(content["Design Authentication"]["artifacts"]) == 2
        assert len(content["Design Authentication"]["decisions"]) == 1

    @pytest.mark.asyncio
    @patch("src.ai.providers.llm_abstraction.LLMAbstraction")
    async def test_llm_failure_leaves_task_as_todo(self, mock_llm_cls, tmp_path):
        """If LLM fails, task stays TODO for worker fallback."""
        mock_llm = AsyncMock()
        mock_llm.analyze.side_effect = Exception("LLM timeout")
        mock_llm_cls.return_value = mock_llm

        design_task = _make_task(
            "Design Authentication",
            labels=["design", "architecture"],
            description=DESIGN_DESCRIPTION,
        )

        content = await _generate_design_content(
            tasks=[design_task],
            project_description="Build auth",
            project_name="Auth",
            project_root=str(tmp_path),
        )

        assert design_task.status == TaskStatus.TODO
        assert "auto_completed" not in (design_task.labels or [])
        assert content == {}

    @pytest.mark.asyncio
    async def test_skips_non_design_tasks(self, tmp_path):
        """Only design tasks are processed."""
        impl_task = _make_task(
            "Implement API",
            labels=["backend"],
        )

        content = await _generate_design_content(
            tasks=[impl_task],
            project_description="Test",
            project_name="Test",
            project_root=str(tmp_path),
        )

        assert content == {}
        assert impl_task.status == TaskStatus.TODO

    @pytest.mark.asyncio
    @patch("src.ai.providers.llm_abstraction.LLMAbstraction")
    async def test_bad_json_leaves_task_as_todo(self, mock_llm_cls, tmp_path):
        """Unparseable LLM response leaves task as TODO."""
        mock_llm = AsyncMock()
        mock_llm.analyze.return_value = "This is not JSON at all"
        mock_llm_cls.return_value = mock_llm

        design_task = _make_task(
            "Design Auth",
            labels=["design", "architecture"],
            description=DESIGN_DESCRIPTION,
        )

        content = await _generate_design_content(
            tasks=[design_task],
            project_description="Test",
            project_name="Test",
            project_root=str(tmp_path),
        )

        assert design_task.status == TaskStatus.TODO
        assert content == {}


# ---- Phase B Tests ----


class TestRegisterDesignViaMcp:
    """Tests for Phase B: _register_design_via_mcp."""

    @pytest.fixture
    def mock_state(self):
        state = MagicMock()
        state.project_tasks = [
            _make_task(
                "Design Authentication",
                labels=["design", "auto_completed"],
                status=TaskStatus.DONE,
                task_id="real_uuid_001",
            ),
            _make_task(
                "Implement Auth",
                labels=["backend"],
                task_id="real_uuid_002",
            ),
        ]
        state.kanban_client = AsyncMock()
        state.context = MagicMock()
        state.current_project_id = "proj_123"
        state.current_project_name = "Test"
        state.task_artifacts = {}
        return state

    @pytest.fixture
    def sample_design_content(self):
        return {
            "Design Authentication": {
                "artifacts": [
                    {
                        "filename": "auth-architecture.md",
                        "artifact_type": "architecture",
                        "content": "# Auth\n...",
                        "description": "Auth design",
                        "relative_path": "docs/architecture/auth-architecture.md",
                    },
                ],
                "decisions": [
                    {
                        "what": "Chose JWT",
                        "why": "Stateless auth",
                        "impact": "API endpoints",
                    },
                ],
            }
        }

    @pytest.mark.asyncio
    @patch("src.marcus_mcp.tools.attachment.log_artifact")
    @patch("src.marcus_mcp.tools.context.log_decision")
    async def test_calls_log_artifact_with_real_uuid(
        self,
        mock_dec,
        mock_art,
        mock_state,
        sample_design_content,
    ):
        """Phase B calls log_artifact with the real kanban UUID."""
        mock_art.return_value = {
            "success": True,
            "data": {"location": "docs/architecture/auth-architecture.md"},
        }
        mock_dec.return_value = {
            "success": True,
            "decision_id": "dec_1",
        }

        result = await _register_design_via_mcp(
            state=mock_state,
            design_content=sample_design_content,
            project_root="/var/folders/test",  # nosec B108
        )

        mock_art.assert_called_once()
        call = mock_art.call_args
        assert call.kwargs["task_id"] == "real_uuid_001"
        assert call.kwargs["state"] is mock_state
        assert result["artifacts_registered"] == 1

    @pytest.mark.asyncio
    @patch("src.marcus_mcp.tools.attachment.log_artifact")
    @patch("src.marcus_mcp.tools.context.log_decision")
    async def test_calls_log_decision_with_real_uuid(
        self,
        mock_dec,
        mock_art,
        mock_state,
        sample_design_content,
    ):
        """Phase B calls log_decision with the real kanban UUID."""
        mock_art.return_value = {
            "success": True,
            "data": {"location": "docs/x"},
        }
        mock_dec.return_value = {
            "success": True,
            "decision_id": "dec_1",
        }

        result = await _register_design_via_mcp(
            state=mock_state,
            design_content=sample_design_content,
            project_root="/var/folders/test",  # nosec B108
        )

        mock_dec.assert_called_once()
        call = mock_dec.call_args
        assert call.kwargs["task_id"] == "real_uuid_001"
        assert call.kwargs["agent_id"] == "marcus_planner"
        assert "JWT" in call.kwargs["decision"]
        assert call.kwargs["state"] is mock_state
        assert result["decisions_logged"] == 1

    @pytest.mark.asyncio
    async def test_empty_content_returns_zeros(self, mock_state):
        """No design content → no MCP calls, zero counts."""
        result = await _register_design_via_mcp(
            state=mock_state,
            design_content={},
        )
        assert result["tasks_completed"] == 0

    @pytest.mark.asyncio
    @patch("src.marcus_mcp.tools.attachment.log_artifact")
    @patch("src.marcus_mcp.tools.context.log_decision")
    async def test_does_not_call_report_task_progress(
        self,
        mock_dec,
        mock_art,
        mock_state,
        sample_design_content,
    ):
        """Phase B must NOT call report_task_progress — task is already DONE."""
        mock_art.return_value = {
            "success": True,
            "data": {"location": "docs/x"},
        }
        mock_dec.return_value = {
            "success": True,
            "decision_id": "dec_1",
        }

        with patch("src.marcus_mcp.tools.task.report_task_progress") as mock_progress:
            await _register_design_via_mcp(
                state=mock_state,
                design_content=sample_design_content,
                project_root="/var/folders/test",  # nosec B108
            )
            mock_progress.assert_not_called()
