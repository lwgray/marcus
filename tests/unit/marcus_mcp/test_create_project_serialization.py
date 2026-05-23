"""Tests for #610 fix — concurrent create_project calls must not race.

Issue #610: when two ``create_project`` calls are in flight at the same
time on a single Marcus server (e.g. a slow ``create_project`` for
project A is still running when ``create_project`` for project B is
invoked), the shared ``state.kanban_client.project_id`` gets overwritten
mid-flight and project A's still-being-created tasks end up writing
under project B's ``project_id``. Both projects end up commingled on
the same board.

The fix serializes ``create_project`` calls under a per-event-loop
mutex. Concurrent callers wait for the in-flight call to finish before
their own work begins. Same name still hits the dedup cache; different
names now queue instead of racing.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, List
from unittest.mock import AsyncMock, Mock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _stub_marcus_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch the marcus_config singleton so tests are hermetic."""
    from src.config import marcus_config as mc

    stub = mc.MarcusConfig()
    stub.ai.anthropic_api_key = "test-key-for-unit-tests"
    monkeypatch.setattr(mc, "_config", stub)


@pytest.fixture(autouse=True)
def _clear_create_project_dedup_cache() -> Any:
    """Hermetic tests: clear the module-level dedup cache around each test."""
    from src.marcus_mcp.tools import nlp as nlp_module

    nlp_module._recent_create_project_calls.clear()
    yield
    nlp_module._recent_create_project_calls.clear()


def _build_state() -> Mock:
    """Minimal mock state for the wrapper path."""
    from src.integrations.kanban_interface import KanbanProvider

    state = Mock()
    state.log_event = Mock()
    state.kanban_client = Mock()
    state.kanban_client.provider = KanbanProvider.PLANKA
    state.kanban_client.project_id = "stale-id-must-not-leak-between-calls"
    state.kanban_client.board_id = "stale-board-id"
    state.ai_engine = Mock()
    state.subtask_manager = Mock()
    state.project_registry = Mock()
    state.project_manager = Mock()
    state.project_registry.add_project = AsyncMock(return_value="reg-abc")
    state.project_registry.get_active_project = AsyncMock(return_value=None)
    state.project_manager.switch_project = AsyncMock()
    state.project_manager.get_kanban_client = AsyncMock(
        return_value=state.kanban_client
    )
    state._subtasks_migrated = False
    # cost_store may be None; the wrapper degrades gracefully.
    state.cost_store = None
    return state


class TestConcurrentCreateProjectSerialization:
    """Two create_project calls running at once must not overlap.

    Without serialization, the second call's ``auto_setup_project``
    mutates ``state.kanban_client.project_id`` (line ~352 in
    ``sqlite_kanban.py``) while the first call is still creating tasks
    that reference it. The fix is a per-event-loop mutex around the
    entire create_project body — the second call simply waits.
    """

    @pytest.mark.asyncio
    async def test_concurrent_different_named_calls_do_not_overlap(self) -> None:
        """Two concurrent calls with DIFFERENT names → second waits.

        The inner work is mocked to record entry / exit timestamps.
        After both calls finish, the inner work's two execution
        windows must be disjoint (no overlap).
        """
        from src.marcus_mcp.tools import nlp as nlp_module

        # Track inner-work execution windows so the test can verify
        # they don't overlap. Each call's wrapper enters
        # ``_create_project_inner`` after acquiring the serialization
        # mutex; we record (start, end) per call.
        windows: List[tuple[str, float, float]] = []

        async def fake_inner(
            description: str,
            project_name: str,
            *_args: Any,
            **_kwargs: Any,
        ) -> dict:
            start = time.monotonic()
            # Simulate work — long enough that overlapping calls would
            # be visible at millisecond resolution.
            await asyncio.sleep(0.05)
            end = time.monotonic()
            windows.append((project_name, start, end))
            return {
                "success": True,
                "project_id": f"id-for-{project_name}",
                "tasks_created": 1,
            }

        state = _build_state()

        with patch.object(nlp_module, "_create_project_inner", side_effect=fake_inner):
            # Two calls with DIFFERENT names → no dedup-cache rejection.
            await asyncio.gather(
                nlp_module.create_project("desc one", "project-A", None, state),
                nlp_module.create_project("desc two", "project-B", None, state),
            )

        assert len(windows) == 2, f"both calls should have executed; got {windows}"
        # Sort by start so we can compare the earlier window's end to
        # the later window's start.
        windows.sort(key=lambda w: w[1])
        earlier_end = windows[0][2]
        later_start = windows[1][1]
        assert later_start >= earlier_end, (
            f"#610: concurrent create_project calls overlapped — "
            f"earlier {windows[0][0]} ended at {earlier_end:.4f}, "
            f"later {windows[1][0]} started at {later_start:.4f}"
        )

    def test_serialization_lock_is_threading_lock_not_asyncio(self) -> None:
        """Codex P1 on PR #613: lock must serialize across event loops.

        ``asyncio.Lock`` (and :class:`EventLoopLockManager` which wraps
        one per loop) only serializes within a single event loop. If
        Marcus runs uvicorn with multiple worker loops in the same
        process, two concurrent ``create_project`` requests on
        different loops would acquire different locks and the #610
        race would remain. The mutex must be process-wide
        (``threading.Lock``).
        """
        import threading as _threading

        from src.marcus_mcp.tools import nlp as nlp_module

        lock = nlp_module._create_project_serialization_lock
        # ``threading.Lock()`` is a factory that returns a
        # ``_thread.lock`` instance; compare against its class.
        assert isinstance(lock, _threading.Lock().__class__), (
            "Codex P1 on #613: create_project serialization lock must be "
            "process-wide (threading.Lock), not per-event-loop "
            "(asyncio.Lock / EventLoopLockManager). Otherwise two "
            "requests on different uvicorn worker loops would race."
        )

    @pytest.mark.asyncio
    async def test_third_call_also_serializes_behind_first_two(self) -> None:
        """Three concurrent calls — none overlap.

        Catches any "mutex held only between first two" off-by-one bug.
        All three inner-work windows must be pairwise disjoint.
        """
        from src.marcus_mcp.tools import nlp as nlp_module

        windows: List[tuple[str, float, float]] = []

        async def fake_inner(
            description: str, project_name: str, *_a: Any, **_k: Any
        ) -> dict:
            start = time.monotonic()
            await asyncio.sleep(0.03)
            end = time.monotonic()
            windows.append((project_name, start, end))
            return {
                "success": True,
                "project_id": f"id-for-{project_name}",
                "tasks_created": 1,
            }

        state = _build_state()

        with patch.object(nlp_module, "_create_project_inner", side_effect=fake_inner):
            await asyncio.gather(
                nlp_module.create_project("d1", "p-1", None, state),
                nlp_module.create_project("d2", "p-2", None, state),
                nlp_module.create_project("d3", "p-3", None, state),
            )

        assert len(windows) == 3
        # Pairwise no-overlap.
        windows.sort(key=lambda w: w[1])
        for prev, nxt in zip(windows, windows[1:]):
            assert nxt[1] >= prev[2], f"#610: overlap between {prev[0]} and {nxt[0]}"
