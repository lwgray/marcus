"""
Unit tests for the project-global foundation contract in get_task_context.

Issue #595 Fix 2: ``get_task_context`` only returned artifacts from a
task's *direct* dependencies, so the shared technical contract produced
by the foundation (pre-fork synthesis) tasks never reached tasks more
than one hop away. Fix 2 adds a project-global ``project_contract`` field
that returns the foundation tasks' artifacts and decisions to *every*
task, regardless of its position in the dependency graph.

Foundation tasks are identified by ``source_type == "pre_fork_synthesis"``
— the exact, Marcus-set marker. Ordinary task artifacts keep their
existing 1-hop dependency scoping.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.tools.context import (
    _collect_foundation_contract,
    get_task_context,
)

pytestmark = pytest.mark.unit


class _MockDecision:
    """Minimal architectural-decision stand-in."""

    def __init__(self, task_id: str, what: str) -> None:
        self.task_id = task_id
        self._what = what

    def to_dict(self) -> Dict[str, Any]:
        return {"task_id": self.task_id, "what": self._what}


class _MockContextResult:
    """Result returned by MockContext.get_context."""

    def to_dict(self) -> Dict[str, Any]:
        return {"previous_implementations": {}, "architectural_decisions": []}


class _MockContext:
    """Mock Context subsystem carrying a flat decision list."""

    def __init__(self) -> None:
        self.decisions: List[_MockDecision] = []

    async def get_context(
        self, task_id: str, dependencies: List[str]
    ) -> _MockContextResult:
        return _MockContextResult()


class _MockSubtaskManager:
    """Mock SubtaskManager exposing the surface get_task_context touches."""

    def __init__(self, subtask_id: str, parent_task_id: str) -> None:
        self.subtasks = {subtask_id: object()}
        self._subtask_id = subtask_id
        self._parent_task_id = parent_task_id

    def get_subtask_context(self, task_id: str) -> Dict[str, Any]:
        return {
            "parent_task_id": self._parent_task_id,
            "subtask": {"id": task_id, "name": "Sub"},
            "shared_conventions": {},
            "dependency_artifacts": [],
            "sibling_subtasks": [],
        }

    def get_subtasks(self, parent_task_id: str, project_tasks: List[Task]) -> List[Any]:
        return []


class _MockState:
    """Mock Marcus server state."""

    def __init__(self) -> None:
        self.task_artifacts: Dict[str, List[Dict[str, Any]]] = {}
        self.project_tasks: List[Task] = []
        self.context = _MockContext()
        self.kanban_client = None
        self.events = None
        self.subtask_manager: Any = None


def _task(
    task_id: str,
    *,
    source_type: str = "",
    dependencies: List[str] | None = None,
) -> Task:
    """Build a Task with the fields get_task_context touches."""
    return Task(
        id=task_id,
        name=f"Task {task_id}",
        description="",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        due_date=None,
        estimated_hours=1.0,
        dependencies=dependencies or [],
        source_type=source_type,
    )


@pytest.fixture()
def state() -> _MockState:
    """Provide a fresh mock state per test."""
    return _MockState()


class TestCollectFoundationContract:
    """_collect_foundation_contract gathers only foundation-task output."""

    @pytest.mark.asyncio
    async def test_collects_artifacts_from_foundation_tasks(
        self, state: _MockState
    ) -> None:
        """Artifacts from pre_fork_synthesis tasks are returned."""
        state.project_tasks = [_task("f1", source_type="pre_fork_synthesis")]
        state.task_artifacts["f1"] = [
            {"filename": "tsconfig.json", "artifact_type": "specification"}
        ]

        contract = await _collect_foundation_contract(state)

        assert [a["filename"] for a in contract["artifacts"]] == ["tsconfig.json"]

    @pytest.mark.asyncio
    async def test_collects_decisions_from_foundation_tasks(
        self, state: _MockState
    ) -> None:
        """Decisions made on a foundation task are returned."""
        state.project_tasks = [_task("f1", source_type="pre_fork_synthesis")]
        state.context.decisions = [
            _MockDecision("f1", "Public API surface"),
            _MockDecision("other", "unrelated decision"),
        ]

        contract = await _collect_foundation_contract(state)

        assert [d["what"] for d in contract["decisions"]] == ["Public API surface"]

    @pytest.mark.asyncio
    async def test_excludes_non_foundation_task_artifacts(
        self, state: _MockState
    ) -> None:
        """Artifacts from ordinary (non-foundation) tasks are not global."""
        state.project_tasks = [
            _task("f1", source_type="pre_fork_synthesis"),
            _task("impl1", source_type="pre_fork_synthesis_NOT"),
            _task("design1"),  # no source_type
        ]
        state.task_artifacts["f1"] = [
            {"filename": "package.json", "artifact_type": "specification"}
        ]
        state.task_artifacts["impl1"] = [{"filename": "feature.ts"}]
        state.task_artifacts["design1"] = [{"filename": "design.md"}]

        contract = await _collect_foundation_contract(state)

        assert [a["filename"] for a in contract["artifacts"]] == ["package.json"]

    @pytest.mark.asyncio
    async def test_empty_when_no_foundation_tasks(self, state: _MockState) -> None:
        """No foundation tasks yields empty artifact and decision lists."""
        state.project_tasks = [_task("impl1")]
        state.task_artifacts["impl1"] = [{"filename": "feature.ts"}]

        contract = await _collect_foundation_contract(state)

        assert contract == {"artifacts": [], "decisions": []}


class TestGetTaskContextProjectContract:
    """get_task_context exposes project_contract regardless of DAG position."""

    @pytest.mark.asyncio
    async def test_task_with_no_foundation_dependency_still_gets_contract(
        self, state: _MockState
    ) -> None:
        """
        A task that does NOT depend on the foundation task still receives
        the foundation contract via the global project_contract field.

        This is the core #595 Fix 2 behavior: contract reaches every task,
        not only the foundation task's direct dependents.
        """
        foundation = _task("f1", source_type="pre_fork_synthesis")
        # leaf task depends on nothing — several hops from foundation
        leaf = _task("leaf", dependencies=[])
        state.project_tasks = [foundation, leaf]
        state.task_artifacts["f1"] = [
            {"filename": "tsconfig.json", "artifact_type": "specification"}
        ]
        state.context.decisions = [_MockDecision("f1", "Public API surface")]

        result = await get_task_context("leaf", state)

        assert result["success"] is True
        contract = result["context"]["project_contract"]
        assert [a["filename"] for a in contract["artifacts"]] == ["tsconfig.json"]
        assert [d["what"] for d in contract["decisions"]] == ["Public API surface"]

    @pytest.mark.asyncio
    async def test_project_contract_empty_without_foundation(
        self, state: _MockState
    ) -> None:
        """project_contract is present but empty when no foundation exists."""
        state.project_tasks = [_task("leaf")]

        result = await get_task_context("leaf", state)

        assert result["success"] is True
        assert result["context"]["project_contract"] == {
            "artifacts": [],
            "decisions": [],
        }

    @pytest.mark.asyncio
    async def test_subtask_also_receives_project_contract(
        self, state: _MockState
    ) -> None:
        """
        A subtask receives the foundation contract via project_contract.

        get_task_context has a separate code path for subtasks; Fix 2
        wires project_contract into that path too, so a subtask is not
        cut off from the project-global contract.
        """
        state.project_tasks = [_task("f1", source_type="pre_fork_synthesis")]
        state.task_artifacts["f1"] = [{"filename": "tsconfig.json"}]
        state.subtask_manager = _MockSubtaskManager("sub-1", "parent-1")

        result = await get_task_context("sub-1", state)

        assert result["success"] is True
        assert result["context"]["is_subtask"] is True
        contract = result["context"]["project_contract"]
        assert [a["filename"] for a in contract["artifacts"]] == ["tsconfig.json"]


class TestCodexFixesOnProjectContract:
    """Codex P1 + P2 regression guards on PR #622.

    Two issues flagged on the develop -> main release PR:

    - P1: skipping ``pre_fork_synthesis`` deps in the direct-dependency
      path dropped Kanban-board attachments (not just logged artifacts).
      ``_collect_foundation_contract`` must compensate by reading both
      ``state.task_artifacts`` AND ``state.kanban_client.get_attachments``
      for each foundation task.
    - P2: foundation artifacts must be filtered by
      ``_is_architectural_artifact`` like the other context tiers do,
      since the project_contract is broadcast to every task. Non-
      architectural (temporary / code-like) artifacts would otherwise
      leak project-wide.
    """

    @pytest.mark.asyncio
    async def test_p1_pulls_kanban_attachments_from_foundation_tasks(
        self, state: _MockState
    ) -> None:
        """Board-attached foundation docs must reach project_contract."""
        from unittest.mock import AsyncMock

        state.project_tasks = [_task("f1", source_type="pre_fork_synthesis")]
        state.task_artifacts["f1"] = []  # no logged artifacts

        # Mock kanban_client.get_attachments — return CANONICAL
        # provider shape per ``src/integrations/kanban_interface.py``:
        # ``{"id", "filename", "url", "content_type", "size",
        # "created_at", "created_by"}``. Codex P2 follow-up on PR
        # #623 caught the earlier mock used Planka-style raw keys
        # (``name`` / ``userId`` / ``createdAt``) which masked a
        # real field-mapping bug — the code would have read None
        # against the canonical interface.
        state.kanban_client = AsyncMock()
        state.kanban_client.get_attachments = AsyncMock(
            return_value={
                "success": True,
                "data": [
                    {
                        "id": "att-1",
                        "filename": "foundation-contract.md",
                        "url": "/storage/foundation-contract.md",
                        "content_type": "text/markdown",
                        "size": 1024,
                        "created_by": "user-1",
                        "created_at": "2026-05-23T12:00:00Z",
                    }
                ],
            }
        )

        contract = await _collect_foundation_contract(state)

        # Verify the foundation collector calls ``get_attachments``
        # with the canonical ``task_id=`` keyword — NOT Planka-style
        # ``card_id=`` which would TypeError against the documented
        # interface (Codex P1 follow-up on PR #623).
        state.kanban_client.get_attachments.assert_called_once_with(task_id="f1")

        assert any(
            a.get("filename") == "foundation-contract.md" for a in contract["artifacts"]
        ), (
            "Codex P1: Kanban-board attachments on foundation tasks "
            "must appear in project_contract. Without this, foundation "
            "documents attached on the board (not logged via "
            "log_artifact) are silently dropped."
        )
        # Stamped with the architectural type so future filter changes
        # don't accidentally exclude them.
        attach = next(
            a
            for a in contract["artifacts"]
            if a.get("filename") == "foundation-contract.md"
        )
        assert attach.get("artifact_type") == "reference"
        assert attach.get("storage_type") == "attachment"
        # Provider's canonical ``url`` field is preserved as
        # ``location`` — not overwritten with a synthetic path when
        # the real one is available.
        assert attach.get("location") == "/storage/foundation-contract.md"
        # Canonical-key reads land on the right keys: ``created_by``
        # / ``created_at`` (NOT Planka raw ``userId`` / ``createdAt``).
        assert attach.get("created_by") == "user-1"
        assert attach.get("created_at") == "2026-05-23T12:00:00Z"

    @pytest.mark.asyncio
    async def test_p2_non_architectural_artifacts_are_filtered_out(
        self, state: _MockState
    ) -> None:
        """Temporary / code-like artifacts must NOT reach project_contract.

        Other tiers (dependency, transitive) already filter to
        architectural types via :func:`_is_architectural_artifact`. The
        project_contract is broadcast to every task, so it must apply
        the same filter — otherwise non-architectural artifacts leak
        project-wide.
        """
        state.project_tasks = [_task("f1", source_type="pre_fork_synthesis")]
        state.task_artifacts["f1"] = [
            {"filename": "tsconfig.json", "artifact_type": "specification"},
            {"filename": "scratch.py", "artifact_type": "temporary"},
            {"filename": "snippet.ts", "artifact_type": "source_code"},
        ]

        contract = await _collect_foundation_contract(state)

        filenames = {a["filename"] for a in contract["artifacts"]}
        assert "tsconfig.json" in filenames
        assert "scratch.py" not in filenames, (
            "Codex P2: non-architectural artifact 'temporary' leaked "
            "into project_contract."
        )
        assert "snippet.ts" not in filenames, (
            "Codex P2: non-architectural artifact 'source_code' leaked "
            "into project_contract."
        )

    @pytest.mark.asyncio
    async def test_kanban_attachment_failure_does_not_crash_contract(
        self, state: _MockState
    ) -> None:
        """Graceful degrade when kanban backend errors fetching attachments.

        The context-delivery hot path must NEVER raise on a transient
        kanban error — degrade to logged-artifacts only, log a warning.
        """
        from unittest.mock import AsyncMock

        state.project_tasks = [_task("f1", source_type="pre_fork_synthesis")]
        state.task_artifacts["f1"] = [
            {"filename": "tsconfig.json", "artifact_type": "specification"}
        ]
        state.kanban_client = AsyncMock()
        state.kanban_client.get_attachments = AsyncMock(
            side_effect=RuntimeError("kanban transient error")
        )

        # Must NOT raise.
        contract = await _collect_foundation_contract(state)

        # Logged artifact still delivered; kanban error swallowed.
        assert [a["filename"] for a in contract["artifacts"]] == ["tsconfig.json"]
