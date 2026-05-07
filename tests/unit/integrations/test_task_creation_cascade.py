"""
Unit tests for task creation cascade failure in create_tasks_on_board.

Two sub-problems are tested:
1. contract_first implementation tasks fail when their dependencies reference
   a decomposer-assigned UUID that is not (yet) in tasks.id but would only
   be in tasks.original_id.
2. The original exception is invisible because nlp_base.py wraps it in
   KanbanIntegrationError and only logs the wrapped message — the root-cause
   traceback is never emitted.
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.integrations.providers.sqlite_kanban import SQLiteKanban

# ============================================================
# Fixtures (mirror test_sqlite_kanban.py patterns)
# ============================================================


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    """Provide a temporary database path."""
    return str(tmp_path / "cascade_test.db")


@pytest.fixture
def config(db_path: str) -> Dict[str, Any]:
    """Provide a standard test config."""
    return {
        "db_path": db_path,
        "project_name": "Cascade Test Project",
    }


@pytest.fixture
def kanban(config: Dict[str, Any]) -> SQLiteKanban:
    """Create an unconnected SQLiteKanban instance."""
    return SQLiteKanban(config)


@pytest.fixture
async def connected_kanban(kanban: SQLiteKanban) -> SQLiteKanban:
    """Create a connected SQLiteKanban instance."""
    await kanban.connect()
    yield kanban  # type: ignore[misc]
    await kanban.disconnect()


def _make_now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


def _design_task_data() -> Dict[str, Any]:
    """
    Build task_data for a structural design task (no dependencies).

    These tasks typically succeed regardless of foreign-key checks
    because they have no dependencies.

    Returns
    -------
    Dict[str, Any]
        Task data dict compatible with SQLiteKanban.create_task.
    """
    return {
        "name": "Design SnakeGame domain model",
        "description": "Define interfaces and contracts for the Snake game",
        "priority": "high",
        "estimated_hours": 2.0,
        "labels": ["design", "structural"],
        "dependencies": [],
        "source_type": "structural",
        "source_context": {"phase": "design"},
    }


def _contract_first_impl_task_data(design_decomposer_uuid: str) -> Dict[str, Any]:
    """
    Build task_data for a contract_first implementation task.

    The ``dependencies`` field contains the *decomposer-assigned UUID*
    of the design task — i.e. the original task.id that the NLP
    decomposer generated, NOT the kanban-assigned id that SQLiteKanban
    wrote to tasks.id.  This is the key difference from a normal task:
    the dependency UUID exists only in tasks.original_id, not in
    tasks.id, so ``PRAGMA foreign_keys=ON`` would reject an insert into
    task_dependencies if that column were a FK to tasks.id.

    Parameters
    ----------
    design_decomposer_uuid : str
        The UUID that the decomposer assigned to the design task before
        it was committed to the kanban board.

    Returns
    -------
    Dict[str, Any]
        Task data dict compatible with SQLiteKanban.create_task.
    """
    return {
        "name": "Implement SnakeEntityInterface",
        "description": "Implement the snake entity per the contract",
        "priority": "high",
        "estimated_hours": 4.0,
        "labels": ["contract_first", "implementation"],
        "dependencies": [design_decomposer_uuid],
        "source_type": "contract_first",
        "source_context": {
            "contract_file": "snake.md",
            "complexity_mode": "prototype",
            "responsibility": "SnakeEntityInterface",
            "product_intent": "moves the snake",
        },
        "provides": "SnakeEntityInterface",
        "requires": "GameBoardInterface",
        "acceptance_criteria": ["criterion1", "criterion2"],
    }


def _integration_verification_task_data(dep_ids: list[str]) -> Dict[str, Any]:
    """
    Build task_data for an integration verification task.

    Parameters
    ----------
    dep_ids : list[str]
        UUIDs of tasks this verification task depends on.

    Returns
    -------
    Dict[str, Any]
        Task data dict compatible with SQLiteKanban.create_task.
    """
    return {
        "name": "Integration Verification",
        "description": "Verify all components integrate correctly",
        "priority": "medium",
        "estimated_hours": 3.0,
        "labels": ["integration", "verification"],
        "dependencies": dep_ids,
        "source_type": "verification",
        "source_context": {"phase": "integration"},
    }


# ============================================================
# Sub-problem 1: cascade failure reproduction
# ============================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestContractFirstCascadeFailure:
    """
    Reproduce the cascade where contract_first implementation tasks fail
    while design/structural tasks succeed.

    The hypothesis is that the dependency UUID in the implementation task
    is the *decomposer-generated* UUID stored in tasks.original_id, not
    the kanban-assigned id stored in tasks.id.  With PRAGMA foreign_keys=ON
    this would cause an integrity error when inserting into
    task_dependencies because task_dependencies.task_id references tasks.id
    (not tasks.original_id).

    Actually, task_id in task_dependencies references the NEW task being
    created (which IS in tasks.id), while depends_on_id has no FK at all.
    So the FK is not the root cause.  The tests below probe the actual
    behavior to discover the real failure mode.
    """

    async def test_design_task_creation_succeeds(
        self, connected_kanban: SQLiteKanban
    ) -> None:
        """Design tasks (no deps) must be created successfully.

        This is the baseline: structural design tasks should always
        succeed because they have no dependency UUIDs that might not
        exist in tasks.id.
        """
        task = await connected_kanban.create_task(_design_task_data())

        assert task is not None
        assert task.name == "Design SnakeGame domain model"
        assert task.source_type == "structural"

    async def test_contract_first_task_with_decomposer_uuid_dep_succeeds(
        self, connected_kanban: SQLiteKanban
    ) -> None:
        """
        contract_first task with a decomposer-UUID dependency must succeed.

        The decomposer assigns a UUID to the design task *before* it is
        committed to the kanban board.  That UUID ends up in
        tasks.original_id (not tasks.id) after creation.  The
        contract_first implementation task has that UUID in its
        ``dependencies`` list.

        SQLiteKanban's task_dependencies schema is:
            depends_on_id TEXT NOT NULL   -- no FK to tasks(id)

        So there is no FK violation, and insertion should succeed.  If
        this test fails, the root cause is elsewhere (e.g. JSON
        serialisation, a None value in a NOT NULL column, etc.).
        """
        # Step 1 — Create design task; capture its kanban-assigned id.
        design_task = await connected_kanban.create_task(_design_task_data())
        assert design_task is not None

        # Simulate the decomposer UUID: a fresh UUID that was assigned
        # to the design task *before* kanban creation.  In the real flow
        # this is the original task.id that build_task_data stores as
        # task_data["original_id"].  The kanban DB stores it as
        # tasks.original_id, NOT as tasks.id.
        decomposer_uuid = uuid.uuid4().hex

        # Step 2 — Create contract_first implementation task whose
        # dependencies list contains the decomposer UUID (not the kanban id).
        impl_task = await connected_kanban.create_task(
            _contract_first_impl_task_data(decomposer_uuid)
        )

        assert impl_task is not None, (
            "contract_first implementation task creation must succeed. "
            "If this fails, run with -s to see the actual exception."
        )
        assert impl_task.name == "Implement SnakeEntityInterface"
        assert impl_task.source_type == "contract_first"
        assert impl_task.provides == "SnakeEntityInterface"
        assert impl_task.requires == "GameBoardInterface"
        assert "criterion1" in impl_task.acceptance_criteria
        assert "criterion2" in impl_task.acceptance_criteria
        # The decomposer UUID is stored verbatim in task_dependencies
        assert decomposer_uuid in impl_task.dependencies

    async def test_full_cascade_design_then_impl_then_integration(
        self, connected_kanban: SQLiteKanban
    ) -> None:
        """
        Full cascade: design → implementation → integration all succeed.

        Reproduces the exact scenario described in issue #480:
        - design task (structural, no deps): should succeed
        - contract_first impl task (deps = decomposer UUID): should succeed
        - integration verification task (deps = both above): should succeed

        If the implementation task fails here, the root cause is
        definitively in SQLiteKanban.create_task for contract_first tasks.
        """
        # Create design task
        design_task = await connected_kanban.create_task(_design_task_data())
        assert design_task is not None, "Design task must be created"

        # The decomposer UUID — this is what the NLP layer would pass as
        # task.dependencies before kanban IDs are assigned.
        decomposer_uuid = uuid.uuid4().hex

        # Create contract_first implementation task
        impl_task = await connected_kanban.create_task(
            _contract_first_impl_task_data(decomposer_uuid)
        )
        assert impl_task is not None, (
            "Implementation task must be created. "
            "cascade failure: contract_first tasks failing while design tasks succeed."
        )

        # Create integration verification task depending on both above
        integ_task = await connected_kanban.create_task(
            _integration_verification_task_data([design_task.id, impl_task.id])
        )
        assert integ_task is not None, "Integration verification task must be created"
        assert len(integ_task.dependencies) == 2

        # All three tasks should be retrievable
        all_tasks = await connected_kanban.get_all_tasks()
        assert len(all_tasks) == 3

    async def test_contract_first_source_context_is_serializable(
        self, connected_kanban: SQLiteKanban
    ) -> None:
        """
        contract_first source_context must round-trip through JSON cleanly.

        The source_context for contract_first tasks contains string-valued
        fields only, so json.dumps should never fail.  This test confirms
        the stored value matches the original.
        """
        decomposer_uuid = uuid.uuid4().hex
        task_data = _contract_first_impl_task_data(decomposer_uuid)
        task = await connected_kanban.create_task(task_data)

        assert task is not None
        assert task.source_context is not None
        assert task.source_context["contract_file"] == "snake.md"
        assert task.source_context["complexity_mode"] == "prototype"
        assert task.source_context["responsibility"] == "SnakeEntityInterface"
        assert task.source_context["product_intent"] == "moves the snake"

    async def test_acceptance_criteria_list_stored_and_retrieved(
        self, connected_kanban: SQLiteKanban
    ) -> None:
        """
        acceptance_criteria must survive the JSON round-trip.

        SQLiteKanban stores acceptance_criteria as JSON text. This test
        confirms the list is preserved for contract_first tasks which
        always have non-empty acceptance_criteria.
        """
        decomposer_uuid = uuid.uuid4().hex
        task = await connected_kanban.create_task(
            _contract_first_impl_task_data(decomposer_uuid)
        )

        assert task is not None
        assert isinstance(task.acceptance_criteria, list)
        assert task.acceptance_criteria == ["criterion1", "criterion2"]


# ============================================================
# Sub-problem 2: logging fix — original exception must be visible
# ============================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestOriginalExceptionLogging:
    """
    Verify that nlp_base.create_tasks_on_board emits the original
    exception traceback (not just the wrapped KanbanIntegrationError)
    when a task creation call fails.

    The bug: the except block wraps ``e`` in ``KanbanIntegrationError``
    and then calls ``logger.error(f"... {kanban_error}")`` — which logs
    the string representation of the *wrapper*, not the original cause.
    The fix: add ``logger.error(..., exc_info=True)`` BEFORE the wrap.
    """

    async def test_original_exception_details_are_logged_on_failure(
        self, connected_kanban: SQLiteKanban
    ) -> None:
        """
        When create_task raises, the logger must emit the original
        exception repr (not just the KanbanIntegrationError wrapper).

        Procedure
        ---------
        1. Inject a kanban client whose create_task always raises a
           ValueError with a distinctive message.
        2. Call create_tasks_on_board with one task.
        3. Capture logger calls on the nlp_base logger.
        4. Assert that at least one ERROR log contains the original
           exception text OR was called with exc_info=True (so the
           traceback would appear in a real log handler).
        """
        from src.integrations.nlp_base import NaturalLanguageTaskCreator

        # Concrete subclass to satisfy the ABC requirement
        class _ConcreteCreator(NaturalLanguageTaskCreator):
            async def process_natural_language(
                self, description: str, **kwargs: Any
            ) -> list[Task]:
                """No-op implementation for testing."""
                return []

        # Build a failing kanban client
        failing_kanban = MagicMock()
        failing_kanban.board_id = "test-board"
        SENTINEL = "distinctive_original_error_abc123"
        failing_kanban.create_task = MagicMock(side_effect=ValueError(SENTINEL))

        creator = _ConcreteCreator(kanban_client=failing_kanban)

        # Build a minimal Task to pass through
        now = _make_now()
        task = Task(
            id=uuid.uuid4().hex,
            name="Failing Task",
            description="This task will fail on creation",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=now,
            updated_at=now,
            due_date=None,
            estimated_hours=1.0,
        )

        with patch("src.integrations.nlp_base.logger") as mock_logger:
            # Silence the record_error_for_monitoring side-effect.
            # The function is imported locally inside the except block,
            # so we must patch it at its definition site.
            with patch("src.core.error_monitoring.record_error_for_monitoring"):
                # Will not raise (only one task, so batch error not
                # triggered — wait, if all tasks fail it WILL raise).
                try:
                    await creator.create_tasks_on_board(
                        [task], skip_validation=True, update_dependencies=False
                    )
                except Exception:
                    pass  # The KanbanIntegrationError batch raise is expected

        # Collect all calls to mock_logger.error
        error_calls = mock_logger.error.call_args_list

        # At least one error call must expose the original exception:
        # either the message contains the sentinel, OR exc_info=True was
        # passed so the traceback would be visible in production.
        original_exposed = any(
            (
                SENTINEL in str(call.args)
                or call.kwargs.get("exc_info") is True
                or (len(call.args) > 0 and SENTINEL in str(call.args[0]))
            )
            for call in error_calls
        )

        assert original_exposed, (
            f"Expected at least one logger.error call to expose the "
            f"original exception (sentinel={SENTINEL!r}) or use "
            f"exc_info=True. Actual calls: {error_calls}"
        )

    async def test_exc_info_true_is_passed_on_task_creation_failure(
        self, connected_kanban: SQLiteKanban
    ) -> None:
        """
        The logger.error call in the except block must include exc_info=True.

        This is the mechanical fix for sub-problem 1: adding
        ``logger.error(f"Task creation failed for '{task.name}': {e!r}",
        exc_info=True)`` before the KanbanIntegrationError wrap so the
        full traceback appears in production logs.
        """
        from src.integrations.nlp_base import NaturalLanguageTaskCreator

        class _ConcreteCreator(NaturalLanguageTaskCreator):
            async def process_natural_language(
                self, description: str, **kwargs: Any
            ) -> list[Task]:
                """No-op implementation for testing."""
                return []

        failing_kanban = MagicMock()
        failing_kanban.board_id = "test-board"
        failing_kanban.create_task = MagicMock(side_effect=RuntimeError("boom"))

        creator = _ConcreteCreator(kanban_client=failing_kanban)

        now = _make_now()
        task = Task(
            id=uuid.uuid4().hex,
            name="ExcInfoTask",
            description="task to test exc_info logging",
            status=TaskStatus.TODO,
            priority=Priority.LOW,
            assigned_to=None,
            created_at=now,
            updated_at=now,
            due_date=None,
            estimated_hours=0.5,
        )

        with patch("src.integrations.nlp_base.logger") as mock_logger:
            with patch("src.core.error_monitoring.record_error_for_monitoring"):
                try:
                    await creator.create_tasks_on_board(
                        [task], skip_validation=True, update_dependencies=False
                    )
                except Exception:
                    pass

        # Check that at least one error call used exc_info=True
        exc_info_calls = [
            call
            for call in mock_logger.error.call_args_list
            if call.kwargs.get("exc_info") is True
        ]

        assert exc_info_calls, (
            "Expected logger.error to be called with exc_info=True "
            "so the original traceback is captured in production logs. "
            f"Actual error calls: {mock_logger.error.call_args_list}"
        )
