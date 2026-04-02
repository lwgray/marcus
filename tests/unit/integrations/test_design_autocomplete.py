"""
Unit tests for design task auto-completion (GH-297, GH-300).

Tests the two-phase approach:
- Phase A (_generate_design_content): Separate LLM calls per artifact
  document, writes files to disk, sets task status=DONE.
- Phase B (_register_design_via_mcp): Registers artifacts + decisions
  via MCP tools after state is available.

See: https://github.com/lwgray/marcus/issues/297
"""

import json
from datetime import datetime, timezone
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
    """Create a minimal Task for testing."""
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


# ---- Phase A Tests ----


class TestGenerateDesignContent:
    """Tests for Phase A: separate LLM calls per artifact."""

    def _mock_llm_responses(self, mock_llm):
        """Set up LLM to return different content per call.

        Calls 1-3 are artifact documents (markdown).
        Call 4 is decisions (JSON array).
        """
        mock_llm.analyze.side_effect = [
            # Architecture doc
            "# Authentication Architecture\n\n"
            "## Components\n- AuthService\n- UserStore\n",
            # API contracts doc
            "# Auth API Contracts\n\n" "## POST /login\nRequest: {email, password}\n",
            # Data models doc
            "# Auth Data Models\n\n" "## User\n- id: uuid\n- email: string\n",
            # Decisions (JSON array)
            json.dumps(
                [
                    {
                        "what": "Chose JWT for auth",
                        "why": "Stateless",
                        "impact": "API endpoints",
                    }
                ]
            ),
        ]

    @pytest.mark.asyncio
    @patch("src.ai.providers.llm_abstraction.LLMAbstraction")
    async def test_sets_design_task_to_done(self, mock_llm_cls, tmp_path):
        """Design task status must be DONE after Phase A."""
        mock_llm = AsyncMock()
        self._mock_llm_responses(mock_llm)
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

        await _generate_design_content(
            tasks=[design_task, impl_task],
            project_description="Build auth system",
            project_name="Auth App",
            project_root=str(tmp_path),
        )

        assert design_task.status == TaskStatus.DONE
        assert "auto_completed" in design_task.labels
        assert impl_task.status == TaskStatus.TODO

    @pytest.mark.asyncio
    @patch("src.ai.providers.llm_abstraction.LLMAbstraction")
    async def test_writes_separate_artifact_files(self, mock_llm_cls, tmp_path):
        """Each artifact is a separate file on disk."""
        mock_llm = AsyncMock()
        self._mock_llm_responses(mock_llm)
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

        arch = tmp_path / "docs" / "architecture"
        api = tmp_path / "docs" / "api"
        spec = tmp_path / "docs" / "specifications"
        assert (arch / "authentication-architecture.md").exists()
        assert (api / "authentication-api-contracts.md").exists()
        assert (spec / "authentication-data-models.md").exists()

    @pytest.mark.asyncio
    @patch("src.ai.providers.llm_abstraction.LLMAbstraction")
    async def test_makes_separate_llm_calls(self, mock_llm_cls, tmp_path):
        """One LLM call per artifact + one for decisions = 4 total."""
        mock_llm = AsyncMock()
        self._mock_llm_responses(mock_llm)
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

        # 3 artifacts + 1 decisions = 4 calls
        assert mock_llm.analyze.call_count == 4

    @pytest.mark.asyncio
    @patch("src.ai.providers.llm_abstraction.LLMAbstraction")
    async def test_returns_content_for_phase_b(self, mock_llm_cls, tmp_path):
        """Returns artifacts + decisions keyed by task name."""
        mock_llm = AsyncMock()
        self._mock_llm_responses(mock_llm)
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
        assert len(content["Design Authentication"]["artifacts"]) == 3
        assert len(content["Design Authentication"]["decisions"]) == 1

    @pytest.mark.asyncio
    @patch("src.ai.providers.llm_abstraction.LLMAbstraction")
    async def test_llm_failure_leaves_task_todo(self, mock_llm_cls, tmp_path):
        """If all LLM calls fail, task stays TODO."""
        mock_llm = AsyncMock()
        mock_llm.analyze.side_effect = Exception("LLM timeout")
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

    @pytest.mark.asyncio
    async def test_skips_non_design_tasks(self, tmp_path):
        """Only design tasks are processed."""
        impl_task = _make_task("Implement API", labels=["backend"])

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
    async def test_partial_artifact_failure_still_completes(
        self, mock_llm_cls, tmp_path
    ):
        """If some artifacts succeed, task is still marked DONE."""
        mock_llm = AsyncMock()
        mock_llm.analyze.side_effect = [
            # Architecture doc succeeds
            "# Auth Architecture\n\n## Components\n...",
            # API doc fails (empty)
            "",
            # Data models succeeds
            "# Auth Data Models\n\n## User\n...",
            # Decisions
            json.dumps([]),
        ]
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

        # 2 of 3 artifacts succeeded — task should be DONE
        assert design_task.status == TaskStatus.DONE
        assert len(content["Design Auth"]["artifacts"]) == 2


# ---- Phase B Tests ----


class TestRegisterDesignViaMcp:
    """Tests for Phase B: register via MCP tools."""

    @pytest.fixture
    def mock_state(self):
        """MCP state with design task that has real UUID."""
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
    def sample_content(self):
        """Phase A output for Phase B to register."""
        return {
            "Design Authentication": {
                "artifacts": [
                    {
                        "filename": "authentication-architecture.md",
                        "artifact_type": "architecture",
                        "content": "# Auth Architecture\n...",
                        "description": "Auth components",
                        "relative_path": (
                            "docs/architecture/" "authentication-architecture.md"
                        ),
                    },
                ],
                "decisions": [
                    {
                        "what": "Chose JWT",
                        "why": "Stateless",
                        "impact": "API endpoints",
                    },
                ],
            }
        }

    @pytest.mark.asyncio
    @patch("src.marcus_mcp.tools.attachment.log_artifact")
    @patch("src.marcus_mcp.tools.context.log_decision")
    async def test_registers_artifact_with_real_uuid(
        self, mock_dec, mock_art, mock_state, sample_content
    ):
        """log_artifact called with real kanban UUID."""
        mock_art.return_value = {
            "success": True,
            "data": {"location": "docs/architecture/x.md"},
        }
        mock_dec.return_value = {
            "success": True,
            "decision_id": "d1",
        }

        result = await _register_design_via_mcp(
            state=mock_state,
            design_content=sample_content,
            project_root="/var/folders/test",  # nosec B108
        )

        mock_art.assert_called_once()
        assert mock_art.call_args.kwargs["task_id"] == "real_uuid_001"
        assert mock_art.call_args.kwargs["state"] is mock_state
        assert result["artifacts_registered"] == 1

    @pytest.mark.asyncio
    @patch("src.marcus_mcp.tools.attachment.log_artifact")
    @patch("src.marcus_mcp.tools.context.log_decision")
    async def test_registers_decision_with_real_uuid(
        self, mock_dec, mock_art, mock_state, sample_content
    ):
        """log_decision called with real kanban UUID."""
        mock_art.return_value = {
            "success": True,
            "data": {"location": "docs/x"},
        }
        mock_dec.return_value = {
            "success": True,
            "decision_id": "d1",
        }

        result = await _register_design_via_mcp(
            state=mock_state,
            design_content=sample_content,
            project_root="/var/folders/test",  # nosec B108
        )

        mock_dec.assert_called_once()
        assert mock_dec.call_args.kwargs["task_id"] == "real_uuid_001"
        assert mock_dec.call_args.kwargs["agent_id"] == "Marcus"
        assert "JWT" in mock_dec.call_args.kwargs["decision"]
        assert result["decisions_logged"] == 1

    @pytest.mark.asyncio
    async def test_empty_content_returns_zeros(self, mock_state):
        """No content -> no MCP calls."""
        result = await _register_design_via_mcp(state=mock_state, design_content={})
        assert result["tasks_completed"] == 0

    @pytest.mark.asyncio
    @patch("src.marcus_mcp.tools.attachment.log_artifact")
    @patch("src.marcus_mcp.tools.context.log_decision")
    async def test_does_not_call_report_task_progress(
        self, mock_dec, mock_art, mock_state, sample_content
    ):
        """Phase B must NOT call report_task_progress."""
        mock_art.return_value = {
            "success": True,
            "data": {"location": "docs/x"},
        }
        mock_dec.return_value = {
            "success": True,
            "decision_id": "d1",
        }

        with patch("src.marcus_mcp.tools.task.report_task_progress") as mock_prog:
            await _register_design_via_mcp(
                state=mock_state,
                design_content=sample_content,
                project_root="/var/folders/test",  # nosec B108
            )
            mock_prog.assert_not_called()


# ---- Scoped Artifact Tests (GH-300) ----


class TestScopedArtifactGeneration:
    """Tests for per-implementation-task scoped design artifacts."""

    def _mock_llm_responses_with_scoped(self, mock_llm):
        """LLM responses for domain artifacts + scoped artifacts.

        4 calls for domain design (3 artifacts + 1 decisions)
        + 3 calls per impl task (scoped artifacts).
        For 2 impl tasks: 4 + 3 + 3 = 10 total calls.
        """
        mock_llm.analyze.side_effect = [
            # Domain: architecture
            "# Dashboard Architecture\n\n## Components\n...",
            # Domain: API contracts
            "# Dashboard API\n\n## Endpoints\n...",
            # Domain: data models
            "# Dashboard Models\n\n## Schemas\n...",
            # Domain: decisions
            json.dumps([{"what": "React", "why": "SPA", "impact": "Frontend"}]),
            # Scoped for Implement Time Widget: architecture
            "# Time Widget Architecture\n\nOnly time stuff.",
            # Scoped for Implement Time Widget: API
            "# Time Widget API\n\nOnly time endpoints.",
            # Scoped for Implement Time Widget: data models
            "# Time Widget Models\n\nOnly time data.",
            # Scoped for Implement Weather Widget: architecture
            "# Weather Widget Architecture\n\nOnly weather stuff.",
            # Scoped for Implement Weather Widget: API
            "# Weather Widget API\n\nOnly weather endpoints.",
            # Scoped for Implement Weather Widget: data models
            "# Weather Widget Models\n\nOnly weather data.",
        ]

    @pytest.mark.asyncio
    @patch("src.ai.providers.llm_abstraction.LLMAbstraction")
    async def test_generates_scoped_artifacts_per_impl_task(
        self, mock_llm_cls, tmp_path
    ):
        """Each implementation task gets its own scoped artifacts."""
        mock_llm = AsyncMock()
        self._mock_llm_responses_with_scoped(mock_llm)
        mock_llm_cls.return_value = mock_llm

        design_task = _make_task(
            "Design Dashboard",
            labels=["design", "architecture"],
            description=DESIGN_DESCRIPTION,
            task_id="design_dashboard",
        )
        impl_time = _make_task(
            "Implement Time Widget",
            labels=["implementation"],
            task_id="impl_time",
        )
        impl_time.dependencies = ["design_dashboard"]
        impl_weather = _make_task(
            "Implement Weather Widget",
            labels=["implementation"],
            task_id="impl_weather",
        )
        impl_weather.dependencies = ["design_dashboard"]

        content = await _generate_design_content(
            tasks=[design_task, impl_time, impl_weather],
            project_description="Build a dashboard",
            project_name="Dashboard",
            project_root=str(tmp_path),
        )

        # Domain design content
        assert "Design Dashboard" in content
        # Scoped content per impl task
        assert "Implement Time Widget" in content
        assert "Implement Weather Widget" in content

    @pytest.mark.asyncio
    @patch("src.ai.providers.llm_abstraction.LLMAbstraction")
    async def test_scoped_files_written_to_disk(self, mock_llm_cls, tmp_path):
        """Scoped artifact files use impl task slug."""
        mock_llm = AsyncMock()
        self._mock_llm_responses_with_scoped(mock_llm)
        mock_llm_cls.return_value = mock_llm

        design_task = _make_task(
            "Design Dashboard",
            labels=["design", "architecture"],
            description=DESIGN_DESCRIPTION,
            task_id="design_dashboard",
        )
        impl_time = _make_task(
            "Implement Time Widget",
            labels=["implementation"],
            task_id="impl_time",
        )
        impl_time.dependencies = ["design_dashboard"]
        impl_weather = _make_task(
            "Implement Weather Widget",
            labels=["implementation"],
            task_id="impl_weather",
        )
        impl_weather.dependencies = ["design_dashboard"]

        await _generate_design_content(
            tasks=[design_task, impl_time, impl_weather],
            project_description="Build a dashboard",
            project_name="Dashboard",
            project_root=str(tmp_path),
        )

        # Domain files
        arch = tmp_path / "docs" / "architecture"
        assert (arch / "dashboard-architecture.md").exists()

        # Scoped files
        assert (arch / "time-widget-architecture.md").exists()
        assert (arch / "weather-widget-architecture.md").exists()

    @pytest.mark.asyncio
    @patch("src.ai.providers.llm_abstraction.LLMAbstraction")
    async def test_scoped_content_is_different(self, mock_llm_cls, tmp_path):
        """Scoped artifacts contain only their component's content."""
        mock_llm = AsyncMock()
        self._mock_llm_responses_with_scoped(mock_llm)
        mock_llm_cls.return_value = mock_llm

        design_task = _make_task(
            "Design Dashboard",
            labels=["design", "architecture"],
            description=DESIGN_DESCRIPTION,
            task_id="design_dashboard",
        )
        impl_time = _make_task(
            "Implement Time Widget",
            labels=["implementation"],
            task_id="impl_time",
        )
        impl_time.dependencies = ["design_dashboard"]
        impl_weather = _make_task(
            "Implement Weather Widget",
            labels=["implementation"],
            task_id="impl_weather",
        )
        impl_weather.dependencies = ["design_dashboard"]

        content = await _generate_design_content(
            tasks=[design_task, impl_time, impl_weather],
            project_description="Build a dashboard",
            project_name="Dashboard",
            project_root=str(tmp_path),
        )

        time_arch = content["Implement Time Widget"]["artifacts"][0]
        weather_arch = content["Implement Weather Widget"]["artifacts"][0]
        assert "time" in time_arch["content"].lower()
        assert "weather" in weather_arch["content"].lower()

    @pytest.mark.asyncio
    @patch("src.marcus_mcp.tools.attachment.log_artifact")
    @patch("src.marcus_mcp.tools.context.log_decision")
    async def test_phase_b_registers_scoped_against_impl_uuid(
        self, mock_dec, mock_art, tmp_path
    ):
        """Phase B registers scoped artifacts against impl task UUID."""
        mock_art.return_value = {
            "success": True,
            "data": {"location": "docs/architecture/time-widget-architecture.md"},
        }
        mock_dec.return_value = {"success": True, "decision_id": "d1"}

        state = MagicMock()
        state.project_tasks = [
            _make_task(
                "Design Dashboard",
                labels=["design", "auto_completed"],
                status=TaskStatus.DONE,
                task_id="design_uuid",
            ),
            _make_task(
                "Implement Time Widget",
                labels=["implementation"],
                task_id="impl_time_uuid",
            ),
        ]
        state.kanban_client = AsyncMock()
        state.context = MagicMock()
        state.current_project_id = "proj"
        state.task_artifacts = {}

        design_content = {
            "Design Dashboard": {
                "artifacts": [
                    {
                        "filename": "dashboard-architecture.md",
                        "artifact_type": "architecture",
                        "content": "# Full domain",
                        "description": "Domain design",
                    }
                ],
                "decisions": [],
            },
            "Implement Time Widget": {
                "artifacts": [
                    {
                        "filename": "time-widget-architecture.md",
                        "artifact_type": "architecture",
                        "content": "# Time only",
                        "description": "Scoped for time widget",
                    }
                ],
                "decisions": [],
            },
        }

        result = await _register_design_via_mcp(
            state=state,
            design_content=design_content,
            project_root="/var/folders/test",  # nosec B108
        )

        # Should have registered artifacts for both tasks
        assert mock_art.call_count == 2
        call_task_ids = [c.kwargs["task_id"] for c in mock_art.call_args_list]
        assert "design_uuid" in call_task_ids
        assert "impl_time_uuid" in call_task_ids
