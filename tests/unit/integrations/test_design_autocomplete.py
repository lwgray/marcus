"""
Unit tests for design task auto-completion via MCP tools.

Tests _autocomplete_design_tasks() which generates artifacts and decisions
through proper MCP tool codepaths (log_artifact, log_decision,
report_task_progress) during create_project.

See: https://github.com/lwgray/marcus/issues/297
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.integrations.nlp_tools import _autocomplete_design_tasks


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


DESIGN_DESCRIPTION = """Design the architecture for Authentication which encompasses:

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


@pytest.fixture
def mock_state():
    """Create a mock MCP state with all required attributes."""
    state = MagicMock()
    state.project_tasks = [
        _make_task(
            "Design Authentication",
            labels=["design", "architecture"],
            description=DESIGN_DESCRIPTION,
            task_id="uuid_design_auth",
        ),
        _make_task(
            "Implement Auth Endpoints",
            labels=["backend", "implementation"],
            task_id="uuid_impl_auth",
        ),
    ]
    state.kanban_client = AsyncMock()
    state.kanban_client.update_task = AsyncMock()
    state.context = MagicMock()
    state.current_project_id = "proj_123"
    state.current_project_name = "Test Project"
    state.task_artifacts = {}
    return state


class TestAutocompleteDesignTasks:

    @pytest.mark.asyncio
    @patch("src.ai.providers.llm_abstraction.LLMAbstraction")
    @patch("src.marcus_mcp.tools.attachment.log_artifact")
    @patch("src.marcus_mcp.tools.context.log_decision")
    @patch("src.marcus_mcp.tools.task.report_task_progress")
    async def test_calls_log_artifact_for_each_artifact(
        self, mock_progress, mock_dec, mock_art, mock_llm_cls, mock_state
    ):
        """Artifacts are logged through the MCP log_artifact tool."""
        mock_llm = AsyncMock()
        mock_llm.analyze.return_value = MOCK_LLM_RESPONSE
        mock_llm_cls.return_value = mock_llm
        mock_art.return_value = {
            "success": True,
            "data": {"location": "docs/architecture/auth-architecture.md"},
        }
        mock_dec.return_value = {"success": True, "decision_id": "dec_1"}
        mock_progress.return_value = {"success": True}

        result = await _autocomplete_design_tasks(
            state=mock_state,
            project_description="Build an auth system",
            project_name="Auth App",
            project_root="/var/folders/test_project",  # nosec B108
        )

        assert mock_art.call_count == 2
        # First artifact
        first_call = mock_art.call_args_list[0]
        assert first_call.kwargs["task_id"] == "uuid_design_auth"
        assert first_call.kwargs["filename"] == "auth-architecture.md"
        assert first_call.kwargs["artifact_type"] == "architecture"
        assert first_call.kwargs["state"] is mock_state
        # Second artifact
        second_call = mock_art.call_args_list[1]
        assert second_call.kwargs["filename"] == "auth-api.yaml"
        assert result["artifacts_generated"] == 2

    @pytest.mark.asyncio
    @patch("src.ai.providers.llm_abstraction.LLMAbstraction")
    @patch("src.marcus_mcp.tools.attachment.log_artifact")
    @patch("src.marcus_mcp.tools.context.log_decision")
    @patch("src.marcus_mcp.tools.task.report_task_progress")
    async def test_calls_log_decision_for_each_decision(
        self, mock_progress, mock_dec, mock_art, mock_llm_cls, mock_state
    ):
        """Decisions are logged through the MCP log_decision tool."""
        mock_llm = AsyncMock()
        mock_llm.analyze.return_value = MOCK_LLM_RESPONSE
        mock_llm_cls.return_value = mock_llm
        mock_art.return_value = {"success": True, "data": {"location": "docs/x"}}
        mock_dec.return_value = {"success": True, "decision_id": "dec_1"}
        mock_progress.return_value = {"success": True}

        result = await _autocomplete_design_tasks(
            state=mock_state,
            project_description="Build an auth system",
            project_name="Auth App",
            project_root="/var/folders/test_project",  # nosec B108
        )

        assert mock_dec.call_count == 1
        call = mock_dec.call_args_list[0]
        assert call.kwargs["agent_id"] == "marcus_planner"
        assert call.kwargs["task_id"] == "uuid_design_auth"
        assert "JWT" in call.kwargs["decision"]
        assert call.kwargs["state"] is mock_state
        assert result["decisions_logged"] == 1

    @pytest.mark.asyncio
    @patch("src.ai.providers.llm_abstraction.LLMAbstraction")
    @patch("src.marcus_mcp.tools.attachment.log_artifact")
    @patch("src.marcus_mcp.tools.context.log_decision")
    @patch("src.marcus_mcp.tools.task.report_task_progress")
    async def test_calls_report_task_progress_completed(
        self, mock_progress, mock_dec, mock_art, mock_llm_cls, mock_state
    ):
        """Task is completed through MCP report_task_progress."""
        mock_llm = AsyncMock()
        mock_llm.analyze.return_value = MOCK_LLM_RESPONSE
        mock_llm_cls.return_value = mock_llm
        mock_art.return_value = {"success": True, "data": {"location": "docs/x"}}
        mock_dec.return_value = {"success": True, "decision_id": "dec_1"}
        mock_progress.return_value = {"success": True}

        await _autocomplete_design_tasks(
            state=mock_state,
            project_description="Build an auth system",
            project_name="Auth App",
            project_root="/var/folders/test_project",  # nosec B108
        )

        mock_progress.assert_called_once()
        call = mock_progress.call_args_list[0]
        assert call.kwargs["agent_id"] == "marcus_planner"
        assert call.kwargs["task_id"] == "uuid_design_auth"
        assert call.kwargs["status"] == "completed"
        assert call.kwargs["progress"] == 100
        assert call.kwargs["state"] is mock_state

    @pytest.mark.asyncio
    @patch("src.ai.providers.llm_abstraction.LLMAbstraction")
    async def test_llm_failure_graceful_degradation(self, mock_llm_cls, mock_state):
        """LLM failure leaves task as TODO — graceful degradation."""
        mock_llm = AsyncMock()
        mock_llm.analyze.side_effect = Exception("LLM timeout")
        mock_llm_cls.return_value = mock_llm

        result = await _autocomplete_design_tasks(
            state=mock_state,
            project_description="Test",
            project_name="Test",
            project_root="/var/folders/test",  # nosec B108
        )

        assert result["tasks_completed"] == 0
        assert result["artifacts_generated"] == 0

    @pytest.mark.asyncio
    async def test_skips_non_design_tasks(self, mock_state):
        """Only design tasks are processed."""
        # Remove design task, keep only implementation
        mock_state.project_tasks = [
            _make_task("Implement API", labels=["backend"], task_id="k1"),
        ]

        result = await _autocomplete_design_tasks(
            state=mock_state,
            project_description="Test",
            project_name="Test",
        )

        assert result["tasks_completed"] == 0

    @pytest.mark.asyncio
    async def test_skips_already_done_design_tasks(self, mock_state):
        """Design tasks already DONE are not re-processed."""
        mock_state.project_tasks = [
            _make_task(
                "Design Auth",
                labels=["design"],
                status=TaskStatus.DONE,
                task_id="k1",
            ),
        ]

        result = await _autocomplete_design_tasks(
            state=mock_state,
            project_description="Test",
            project_name="Test",
        )

        assert result["tasks_completed"] == 0

    @pytest.mark.asyncio
    async def test_no_project_tasks(self):
        """Empty project_tasks returns early."""
        state = MagicMock()
        state.project_tasks = []

        result = await _autocomplete_design_tasks(
            state=state,
            project_description="Test",
            project_name="Test",
        )

        assert result["tasks_completed"] == 0

    @pytest.mark.asyncio
    @patch("src.ai.providers.llm_abstraction.LLMAbstraction")
    @patch("src.marcus_mcp.tools.attachment.log_artifact")
    @patch("src.marcus_mcp.tools.context.log_decision")
    @patch("src.marcus_mcp.tools.task.report_task_progress")
    async def test_adds_auto_completed_label(
        self, mock_progress, mock_dec, mock_art, mock_llm_cls, mock_state
    ):
        """auto_completed label is added to kanban task."""
        mock_llm = AsyncMock()
        mock_llm.analyze.return_value = MOCK_LLM_RESPONSE
        mock_llm_cls.return_value = mock_llm
        mock_art.return_value = {"success": True, "data": {"location": "docs/x"}}
        mock_dec.return_value = {"success": True, "decision_id": "dec_1"}
        mock_progress.return_value = {"success": True}

        await _autocomplete_design_tasks(
            state=mock_state,
            project_description="Test",
            project_name="Test",
            project_root="/var/folders/test",  # nosec B108
        )

        mock_state.kanban_client.update_task.assert_called_once()
        call_args = mock_state.kanban_client.update_task.call_args
        assert call_args[0][0] == "uuid_design_auth"
        assert "auto_completed" in call_args[0][1]["labels"]
