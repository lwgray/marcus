"""
Unit tests for helpers in ``src.integrations.nlp_tools``.

These tests cover small, pure helpers that can be exercised without
spinning up a kanban client or AI engine. Integration behavior of
``NaturalLanguageProjectCreator`` is covered in the integration test
suite.
"""

from datetime import datetime
from pathlib import Path

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.integrations.enhanced_task_classifier import EnhancedTaskClassifier
from src.integrations.nlp_tools import _resolve_project_root, _task_type_breakdown

pytestmark = pytest.mark.unit


def _make_task(
    *,
    task_id: str,
    name: str,
    labels: list[str],
    description: str = "",
) -> Task:
    """
    Build a minimal Task instance for classifier tests.

    Parameters
    ----------
    task_id : str
        Unique task identifier.
    name : str
        Task name — strong classifier signal.
    labels : list[str]
        Task labels — strongest classifier signal.
    description : str, optional
        Task description — weak classifier signal.

    Returns
    -------
    Task
        Populated Task dataclass ready for classification.
    """
    return Task(
        id=task_id,
        name=name,
        description=description,
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        due_date=None,
        estimated_hours=1.0,
        labels=labels,
    )


class TestTaskTypeBreakdown:
    """Test suite for ``_task_type_breakdown``."""

    @pytest.fixture
    def classifier(self) -> EnhancedTaskClassifier:
        """Return a real classifier — fast, no external deps."""
        return EnhancedTaskClassifier()

    def test_contract_first_tasks_classify_as_implementation(
        self, classifier: EnhancedTaskClassifier
    ) -> None:
        """
        Regression test: contract-first tasks must not be labeled
        'unknown' in the task-type breakdown.

        Before this fix, the breakdown loop used
        ``getattr(task, "task_type", "unknown")`` which always fell
        back to ``"unknown"`` because Task has no ``task_type``
        attribute. The fix routes through the EnhancedTaskClassifier,
        which correctly recognizes the ``implementation`` label on
        contract-first tasks.
        """
        tasks = [
            _make_task(
                task_id="t1",
                name="Implement WeatherWidget",
                labels=["contract_first", "implementation"],
                description=(
                    "implements WeatherWidget module from "
                    "weather-information-system-interface-contracts.md"
                ),
            ),
            _make_task(
                task_id="t2",
                name="Implement TimeWidget",
                labels=["contract_first", "implementation"],
                description=(
                    "implements TimeWidget module from "
                    "time-display-system-interface-contracts.md"
                ),
            ),
            _make_task(
                task_id="t3",
                name="Implement Dashboard Container",
                labels=["contract_first", "implementation"],
                description=(
                    "implements Dashboard Container from "
                    "dashboard-presentation-layer-interface-contracts.md"
                ),
            ),
        ]

        breakdown = _task_type_breakdown(tasks, classifier)

        assert "unknown" not in breakdown, (
            f"Contract-first tasks must not classify as 'unknown': " f"{breakdown}"
        )
        assert (
            breakdown.get("implementation", 0) == 3
        ), f"Expected 3 implementation tasks, got: {breakdown}"

    def test_mixed_task_types_produce_accurate_histogram(
        self, classifier: EnhancedTaskClassifier
    ) -> None:
        """
        Breakdown counts by TaskType enum value, not by string
        attribute. A mix of design/implement/test tasks produces a
        histogram with three non-zero buckets.
        """
        tasks = [
            _make_task(
                task_id="d1",
                name="Design the API schema",
                labels=["design"],
            ),
            _make_task(
                task_id="i1",
                name="Implement user authentication",
                labels=["implementation"],
            ),
            _make_task(
                task_id="i2",
                name="Build the dashboard component",
                labels=["implementation"],
            ),
            _make_task(
                task_id="t1",
                name="Write integration tests for auth",
                labels=["testing"],
            ),
        ]

        breakdown = _task_type_breakdown(tasks, classifier)

        assert breakdown.get("design", 0) == 1, breakdown
        assert breakdown.get("implementation", 0) == 2, breakdown
        assert breakdown.get("testing", 0) == 1, breakdown
        assert "unknown" not in breakdown, breakdown

    def test_empty_task_list_returns_empty_breakdown(
        self, classifier: EnhancedTaskClassifier
    ) -> None:
        """No tasks → empty histogram, not an error."""
        assert _task_type_breakdown([], classifier) == {}


class TestResolveProjectRoot:
    """
    Test suite for ``_resolve_project_root`` (GH-588).

    The design auto-completion phase that marks design tasks DONE on
    the board is gated on ``project_root`` being truthy. Before #588,
    callers that omitted ``project_root`` got ``None``, which silently
    skipped design auto-completion and deadlocked any project whose
    feature tasks depended on design tasks.
    """

    def test_explicit_project_root_is_returned_unchanged(self, tmp_path: Path) -> None:
        """
        Caller-supplied ``project_root`` wins — the helper does not
        override it even when ``project_id`` is also available.
        """
        explicit = str(tmp_path / "caller_supplied")
        result = _resolve_project_root({"project_root": explicit}, project_id="abc123")
        assert result == explicit

    def test_missing_options_falls_back_to_marcus_projects_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        ``options=None`` and a known ``project_id`` produce a default
        rooted at ``<home>/.marcus/projects/<project_id>`` (GH-588).
        """
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = _resolve_project_root(None, project_id="abc123")
        assert result == str(tmp_path / ".marcus" / "projects" / "abc123")

    def test_options_without_project_root_key_falls_back(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty options dict triggers the same fallback as ``None``."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = _resolve_project_root({}, project_id="xyz789")
        assert result == str(tmp_path / ".marcus" / "projects" / "xyz789")

    def test_default_directory_is_created_on_disk(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        The defaulted directory must exist after the call so
        ``_run_design_phase`` can write artifacts into it without a
        ``FileNotFoundError``.
        """
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        _resolve_project_root(None, project_id="abc123")
        expected = tmp_path / ".marcus" / "projects" / "abc123"
        assert expected.is_dir()

    def test_no_project_id_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Without a stable ``project_id`` we cannot derive a default
        path — return ``None`` rather than guess. The caller (currently
        ``create_project_from_description``) ensures ``active_project_id``
        is set well before this is invoked, so this branch is defensive.
        """
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert _resolve_project_root(None, project_id=None) is None
        assert _resolve_project_root({}, project_id="") is None

    def test_mkdir_failure_degrades_gracefully(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        ``OSError`` from ``mkdir`` (read-only home, NFS quota, restricted
        container) must NOT propagate out of ``create_project``. The
        helper returns ``None`` and logs a warning so the operator can
        see why design auto-completion was skipped.
        """
        import logging

        def _explode(*args: object, **kwargs: object) -> None:
            raise PermissionError("read-only filesystem")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setattr(Path, "mkdir", _explode)

        with caplog.at_level(logging.WARNING, logger="src.integrations.nlp_tools"):
            result = _resolve_project_root(None, project_id="abc123")

        assert result is None
        assert any(
            "failed to create default project root" in rec.message
            and "abc123" in rec.message
            for rec in caplog.records
        ), [rec.message for rec in caplog.records]

    def test_default_root_is_truthy_so_design_phase_gate_runs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Regression guard for the user-visible #588 claim.

        ``_run_design_phase`` is gated on ``if project_root and
        has_design_tasks`` (``src/integrations/nlp_tools.py`` ~L2057).
        The whole point of this helper is that callers omitting
        ``options["project_root"]`` must still get a truthy value
        here so the gate passes and design tasks transition TODO →
        DONE on the board. Without this, agents calling
        ``request_next_task`` get nothing (the original deadlock).

        Pinning the truthy contract directly catches the regression
        without needing to mock ``create_project_from_description``'s
        full setup chain. The end-to-end integration is exercised by
        the manual smoke test described in PR #590's "How to verify"
        section.
        """
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = _resolve_project_root(None, project_id="abc123")
        assert result, (
            "helper returned a falsy value — design-phase gate would "
            "be skipped and create_project would deadlock for callers "
            "that omit options['project_root']"
        )

    def test_home_unresolved_degrades_gracefully(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        ``Path.home()`` raises ``RuntimeError`` when ``$HOME`` (or the
        platform equivalent) is unset — common in container/service
        environments. The helper must catch that alongside ``OSError``,
        return ``None``, and log a warning. Without this guard,
        ``create_project`` hard-fails before design-phase scheduling
        for callers that omit ``options["project_root"]`` (Codex P1
        on PR #590).
        """
        import logging

        def _no_home() -> Path:
            raise RuntimeError("Could not determine home directory")

        monkeypatch.setattr(Path, "home", _no_home)

        with caplog.at_level(logging.WARNING, logger="src.integrations.nlp_tools"):
            result = _resolve_project_root(None, project_id="abc123")

        assert result is None
        assert any(
            "failed to create default project root" in rec.message
            and "abc123" in rec.message
            for rec in caplog.records
        ), [rec.message for rec in caplog.records]
