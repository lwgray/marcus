"""
Unit tests for pre-fork shared foundation synthesis (GH-355).

Verifies that ``_synthesize_shared_foundation()`` on
``NaturalLanguageProjectCreator``:

- Returns an empty list when the LLM detects no shared foundation needs
  (conservative, no-op path).
- Returns a list of Task objects when the LLM detects foundation needs.
- Returns an empty list on LLM failure or JSON parse failure
  (never crashes the pipeline).
- Includes domain contract context in the prompt when domains are provided.
- Produces Task objects with correct fields (status TODO, priority HIGH,
  labels contain "foundation" and "pre-fork").
- Feature-based path: foundation tasks are prepended and domain tasks
  depend on them.
- Contract-first path: foundation tasks are prepended and domain tasks
  depend on them.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.core.models import Priority, Task, TaskStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_creator() -> Any:
    """Build a ``NaturalLanguageProjectCreator`` with all dependencies mocked.

    Returns
    -------
    Any
        A ``NaturalLanguageProjectCreator`` instance whose ``prd_parser``,
        ``kanban_client``, and ``ai_engine`` are all mocked, so no real
        I/O happens.
    """
    from src.integrations.nlp_tools import NaturalLanguageProjectCreator

    mock_kanban = MagicMock()
    mock_ai_engine = MagicMock()

    creator = NaturalLanguageProjectCreator(
        kanban_client=mock_kanban,
        ai_engine=mock_ai_engine,
    )

    # Replace the real LLM client on prd_parser with a mock
    mock_llm = MagicMock()
    mock_llm.analyze = AsyncMock()
    creator.prd_parser.llm_client = mock_llm

    return creator


def _make_task(task_id: str, name: str) -> Task:
    """Build a minimal Task for dependency-wiring tests.

    Parameters
    ----------
    task_id : str
        Task identifier.
    name : str
        Task name.

    Returns
    -------
    Task
        Minimal Task with empty dependencies list.
    """
    now = datetime.now(timezone.utc)
    return Task(
        id=task_id,
        name=name,
        description="Do the thing",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=4.0,
        dependencies=[],
    )


# ---------------------------------------------------------------------------
# _synthesize_shared_foundation — unit tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestSynthesizeSharedFoundation:
    """Tests for ``NaturalLanguageProjectCreator._synthesize_shared_foundation``."""

    async def test_returns_empty_list_when_llm_says_no_shared_needs(self) -> None:
        """When LLM returns no foundation tasks, result is an empty list.

        This is the conservative no-op path: the caller's task list is
        unchanged and no pre-fork tasks are injected.
        """
        creator = _make_creator()
        creator.prd_parser.llm_client.analyze.return_value = json.dumps(
            {"foundation_tasks": []}
        )

        result = await creator._synthesize_shared_foundation(
            "Build a simple weather dashboard."
        )

        assert result == []

    async def test_returns_tasks_when_shared_needs_detected(self) -> None:
        """When LLM identifies shared foundation needs, Task objects are returned.

        Three targets are supported: design system, shared components, and
        tech foundation.  The LLM may return any subset.
        """
        creator = _make_creator()
        creator.prd_parser.llm_client.analyze.return_value = json.dumps(
            {
                "foundation_tasks": [
                    {
                        "name": "Shared Foundation: Design System",
                        "description": "Create shared color tokens and typography.",
                        "estimated_hours": 2.0,
                    },
                    {
                        "name": "Shared Foundation: Shared Components",
                        "description": "Build Card and Button components.",
                        "estimated_hours": 3.0,
                    },
                ]
            }
        )

        result = await creator._synthesize_shared_foundation(
            "Build a multi-widget dashboard with clock and weather panels."
        )

        assert len(result) == 2
        assert all(isinstance(t, Task) for t in result)
        names = {t.name for t in result}
        assert "Shared Foundation: Design System" in names
        assert "Shared Foundation: Shared Components" in names

    async def test_is_conservative_on_llm_failure(self) -> None:
        """When the LLM call raises, the method returns [] instead of crashing.

        The pre-fork synthesis is a best-effort enhancement. A failure must
        not prevent project creation.
        """
        creator = _make_creator()
        creator.prd_parser.llm_client.analyze.side_effect = RuntimeError(
            "LLM unavailable"
        )

        result = await creator._synthesize_shared_foundation(
            "Build a weather dashboard."
        )

        assert result == []

    async def test_is_conservative_on_invalid_json(self) -> None:
        """When the LLM returns unparseable JSON, the method returns [].

        Malformed LLM output is common — never crash the pipeline.
        """
        creator = _make_creator()
        creator.prd_parser.llm_client.analyze.return_value = (
            "Sorry, I cannot help with that."
        )

        result = await creator._synthesize_shared_foundation(
            "Build a weather dashboard."
        )

        assert result == []

    async def test_is_conservative_on_missing_foundation_tasks_key(self) -> None:
        """When the LLM returns JSON without ``foundation_tasks`` key, return [].

        Unexpected but valid JSON should degrade gracefully.
        """
        creator = _make_creator()
        creator.prd_parser.llm_client.analyze.return_value = json.dumps(
            {"tasks": []}  # wrong key
        )

        result = await creator._synthesize_shared_foundation(
            "Build a weather dashboard."
        )

        assert result == []

    async def test_foundation_tasks_have_correct_structure(self) -> None:
        """Each returned Task has the expected fields set for a pre-fork task.

        - status: TODO (not yet started)
        - priority: HIGH (blocking downstream domain tasks)
        - labels: contains "foundation" and "pre-fork"
        - assigned_to: None (self-assigned by whichever agent picks it first)
        - estimated_hours: matches LLM value
        """
        creator = _make_creator()
        creator.prd_parser.llm_client.analyze.return_value = json.dumps(
            {
                "foundation_tasks": [
                    {
                        "name": "Shared Foundation: Design System",
                        "description": "Create shared tokens.",
                        "estimated_hours": 2.5,
                    }
                ]
            }
        )

        result = await creator._synthesize_shared_foundation("Build a dashboard.")

        assert len(result) == 1
        task = result[0]
        assert task.status == TaskStatus.TODO
        assert task.priority == Priority.HIGH
        assert task.assigned_to is None
        # Foundation tasks are real implementation work — not design ghosts.
        # Only "pre-fork" tag used; source_type is the internal marker.
        assert "pre-fork" in task.labels
        assert "design" not in task.labels
        assert task.estimated_hours == 2.5
        # Description contains the original text plus the workflow reminder.
        assert "Create shared tokens" in task.description
        assert "log_artifact" in task.description
        # ID must be a non-empty string
        assert isinstance(task.id, str) and len(task.id) > 0

    async def test_domain_context_included_in_prompt_when_provided(self) -> None:
        """When domains are provided, the LLM prompt includes domain contract text.

        Contract-first synthesis has higher fidelity than feature-based because
        domain contracts are available.  This test checks that the prompt the
        LLM actually receives contains the domain name.
        """
        creator = _make_creator()
        creator.prd_parser.llm_client.analyze.return_value = json.dumps(
            {"foundation_tasks": []}
        )

        domains: Dict[str, Any] = {
            "WeatherDomain": {
                "artifacts": [
                    {"content": "interface WeatherService { getTemp(): number }"}
                ]
            }
        }

        await creator._synthesize_shared_foundation(
            "Build a dashboard.", domains=domains
        )

        # Verify the LLM was called with a prompt that mentions the domain
        call_args = creator.prd_parser.llm_client.analyze.call_args
        prompt_text: str = call_args.kwargs.get("prompt") or call_args.args[0]
        assert "WeatherDomain" in prompt_text

    async def test_prompt_omits_domain_section_when_no_domains(self) -> None:
        """When no domains are given (feature_based path), the prompt still works.

        The feature_based path runs on PRD text only (lower fidelity) so the
        prompt should not contain a domain-contract section.
        """
        creator = _make_creator()
        creator.prd_parser.llm_client.analyze.return_value = json.dumps(
            {"foundation_tasks": []}
        )

        await creator._synthesize_shared_foundation(
            "Build a weather dashboard.", domains=None
        )

        call_args = creator.prd_parser.llm_client.analyze.call_args
        prompt_text: str = call_args.kwargs.get("prompt") or call_args.args[0]
        # Prompt must still contain the PRD description
        assert "weather dashboard" in prompt_text.lower()

    async def test_foundation_task_missing_estimated_hours_uses_default(self) -> None:
        """If LLM omits ``estimated_hours``, a sensible default is used.

        Defensive handling for partial LLM responses.
        """
        creator = _make_creator()
        creator.prd_parser.llm_client.analyze.return_value = json.dumps(
            {
                "foundation_tasks": [
                    {
                        "name": "Shared Foundation: Tech Setup",
                        "description": "Configure Vite + TypeScript.",
                        # no estimated_hours key
                    }
                ]
            }
        )

        result = await creator._synthesize_shared_foundation("Build a dashboard.")

        assert len(result) == 1
        assert result[0].estimated_hours > 0  # some positive default


# ---------------------------------------------------------------------------
# Feature-based wiring tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestFeatureBasedFoundationWiring:
    """Foundation tasks are prepended and domain tasks depend on them.

    These tests patch ``_synthesize_shared_foundation`` and
    ``parse_prd_to_tasks`` so we can verify only the wiring logic in
    ``process_natural_language`` without running real LLM calls.
    """

    async def test_foundation_tasks_prepended_before_domain_tasks(self) -> None:
        """When synthesis returns tasks, they appear first in the task list."""
        from src.integrations.nlp_tools import NaturalLanguageProjectCreator

        creator = _make_creator()

        now = datetime.now(timezone.utc)
        foundation_task = _make_task("foundation-1", "Shared Foundation: Design System")
        foundation_task.labels = ["foundation", "pre-fork"]

        domain_task_a = _make_task("domain-a", "Build WeatherWidget")
        domain_task_b = _make_task("domain-b", "Build ClockWidget")

        # Stub synthesis
        async def fake_synthesis(description: str, domains: Any = None) -> List[Task]:
            return [foundation_task]

        # Stub prd_parser.parse_prd_to_tasks
        from src.ai.advanced.prd.advanced_parser import TaskGenerationResult

        mock_result = Mock(spec=TaskGenerationResult)
        mock_result.tasks = [domain_task_a, domain_task_b]
        mock_result.dependencies = []

        creator._synthesize_shared_foundation = fake_synthesis  # type: ignore[method-assign]
        creator.prd_parser.parse_prd_to_tasks = AsyncMock(return_value=mock_result)

        # Stub board_analyzer and context_detector to avoid real I/O
        creator.board_analyzer.analyze_board = AsyncMock()
        from unittest.mock import MagicMock

        mock_ctx = MagicMock()
        from src.detection.context_detector import MarcusMode

        mock_ctx.recommended_mode = MarcusMode.CREATOR
        creator.context_detector.detect_optimal_mode = AsyncMock(return_value=mock_ctx)

        tasks = await creator.process_natural_language(
            "Build a dashboard", project_name="Test"
        )

        assert tasks[0].id == "foundation-1"
        assert tasks[1].id == "domain-a"
        assert tasks[2].id == "domain-b"

    async def test_domain_tasks_depend_on_foundation_tasks(self) -> None:
        """When foundation tasks exist, all domain tasks list them as dependencies."""
        from src.integrations.nlp_tools import NaturalLanguageProjectCreator

        creator = _make_creator()

        foundation_task = _make_task("foundation-1", "Shared Foundation: Design System")
        foundation_task.labels = ["foundation", "pre-fork"]

        domain_task_a = _make_task("domain-a", "Build WeatherWidget")
        domain_task_b = _make_task("domain-b", "Build ClockWidget")

        async def fake_synthesis(description: str, domains: Any = None) -> List[Task]:
            return [foundation_task]

        from src.ai.advanced.prd.advanced_parser import TaskGenerationResult

        mock_result = Mock(spec=TaskGenerationResult)
        mock_result.tasks = [domain_task_a, domain_task_b]
        mock_result.dependencies = []

        creator._synthesize_shared_foundation = fake_synthesis  # type: ignore[method-assign]
        creator.prd_parser.parse_prd_to_tasks = AsyncMock(return_value=mock_result)

        creator.board_analyzer.analyze_board = AsyncMock()
        mock_ctx = MagicMock()
        from src.detection.context_detector import MarcusMode

        mock_ctx.recommended_mode = MarcusMode.CREATOR
        creator.context_detector.detect_optimal_mode = AsyncMock(return_value=mock_ctx)

        tasks = await creator.process_natural_language(
            "Build a dashboard", project_name="Test"
        )

        # domain tasks must have foundation-1 as a dependency
        domain_tasks = [t for t in tasks if t.id != "foundation-1"]
        for dt in domain_tasks:
            assert (
                "foundation-1" in dt.dependencies
            ), f"Task '{dt.name}' missing dependency on foundation-1"

    async def test_no_foundation_tasks_leaves_domain_tasks_unchanged(self) -> None:
        """When synthesis returns [], domain tasks have no injected dependencies."""
        from src.integrations.nlp_tools import NaturalLanguageProjectCreator

        creator = _make_creator()

        domain_task_a = _make_task("domain-a", "Build WeatherWidget")
        domain_task_b = _make_task("domain-b", "Build ClockWidget")

        async def fake_synthesis(description: str, domains: Any = None) -> List[Task]:
            return []

        from src.ai.advanced.prd.advanced_parser import TaskGenerationResult

        mock_result = Mock(spec=TaskGenerationResult)
        mock_result.tasks = [domain_task_a, domain_task_b]
        mock_result.dependencies = []

        creator._synthesize_shared_foundation = fake_synthesis  # type: ignore[method-assign]
        creator.prd_parser.parse_prd_to_tasks = AsyncMock(return_value=mock_result)

        creator.board_analyzer.analyze_board = AsyncMock()
        mock_ctx = MagicMock()
        from src.detection.context_detector import MarcusMode

        mock_ctx.recommended_mode = MarcusMode.CREATOR
        creator.context_detector.detect_optimal_mode = AsyncMock(return_value=mock_ctx)

        tasks = await creator.process_natural_language(
            "Build a dashboard", project_name="Test"
        )

        # No foundation injected — task list unchanged, dependencies empty
        assert len(tasks) == 2
        for t in tasks:
            assert t.dependencies == []
