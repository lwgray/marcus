"""Unit tests for ``_kanban_init_lock_manager`` in ``create_project`` (issue #461).

Closes the verification gap left by PR #452: the lock that prevents the
807s stall under concurrent ``create_project`` calls had no test
exercising the concurrent path.  Without this test, future refactors of
``nlp.py`` could remove or move the lock without anyone noticing
(Track 2 / #442 will rebuild this whole area).

The 807s stall was caused by N concurrent callers each detecting
``need_new_client=True`` and racing to overwrite ``state.kanban_client``,
leaving earlier callers with orphaned connections and triggering the
dedup-guard loop.  The lock makes "check provider then maybe init"
atomic per event loop.

These tests exercise the contract:

1. N concurrent ``create_project`` calls → kanban factory init runs
   exactly once
2. All N calls complete within a bounded wall-clock budget (no stall)
3. ``state.kanban_client`` is fully-initialized for every call
   (no half-init exposure)
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _make_state_no_client() -> MagicMock:
    """Build a state mock with kanban_client=None to force init.

    The lock-protected block detects need_new_client=True when
    ``state.kanban_client`` is falsy or its provider doesn't match
    ``requested_provider``.  Setting client to None forces the init
    path on every concurrent caller, which is the regression scenario.
    """
    state = MagicMock()
    state.kanban_client = None
    state.ai_engine = MagicMock()
    state.subtask_manager = None
    state.log_event = MagicMock()
    state.events = None
    return state


def _stub_creator_result(project_id: str) -> dict[str, Any]:
    """Build a minimal create_project return for the NLPC mock."""
    return {
        "success": True,
        "project_id": project_id,
        "tasks_created": 1,
        "recommended_agents": 1,
    }


class TestKanbanInitLockUnderConcurrency:
    """``_kanban_init_lock_manager`` makes "check provider, maybe init"
    atomic per event loop.  These tests pin the contract.
    """

    @pytest.mark.asyncio
    async def test_kanban_factory_create_called_exactly_once_under_3_concurrent(
        self, tmp_path: Path
    ) -> None:
        """Three concurrent create_project calls → KanbanFactory.create
        runs exactly once.

        Pre-#452 the second and third callers would both observe
        ``state.kanban_client is None``, both call ``KanbanFactory.create``,
        and the later assignments would overwrite the earlier — leaving
        orphaned connections and racing with the dedup guard.  The lock
        serializes the check-and-init so only the first caller initializes.
        """
        from src.marcus_mcp.tools import nlp as nlp_module

        state = _make_state_no_client()

        # Track how many times KanbanFactory.create runs.  The lock
        # contract: exactly once across all concurrent callers.
        factory_create_calls = 0

        def _counted_factory_create(provider: str) -> Any:
            nonlocal factory_create_calls
            factory_create_calls += 1
            client = MagicMock()
            client.provider = provider
            client.connect = AsyncMock()
            client.board_id = "board-test"
            return client

        # Stub NaturalLanguageProjectCreator so create_project completes
        # quickly without running real decomposition / LLM / persistence.
        # The lock contract is exercised before NLPC is constructed.
        mock_creator_class = MagicMock()
        mock_creator_instance = MagicMock()
        mock_creator_instance.create_project_from_description = AsyncMock(
            side_effect=lambda **kwargs: _stub_creator_result(
                f"proj-{kwargs['project_name']}"
            )
        )
        mock_creator_class.return_value = mock_creator_instance

        # Stub get_config to bypass marcus_config.json validation
        # (kanban.provider is the only field create_project reads).
        cfg = MagicMock()
        cfg.kanban = MagicMock()
        cfg.kanban.provider = "sqlite"

        with (
            patch(
                "src.config.marcus_config.get_config",
                return_value=cfg,
            ),
            patch(
                "src.integrations.kanban_factory.KanbanFactory.create",
                side_effect=_counted_factory_create,
            ),
            patch(
                "src.integrations.nlp_tools.NaturalLanguageProjectCreator",
                mock_creator_class,
            ),
        ):
            results = await asyncio.gather(
                *[
                    nlp_module.create_project(
                        description=f"description {i}",
                        project_name=f"proj_{i}",
                        options={
                            "provider": "sqlite",
                            "project_root": str(tmp_path / f"impl_{i}"),
                        },
                        state=state,
                    )
                    for i in range(3)
                ]
            )

        # All 3 calls completed
        assert len(results) == 3
        for r in results:
            assert r.get("success") is True

        # KanbanFactory.create ran exactly once — the lock prevented
        # the second and third callers from re-initializing.
        assert factory_create_calls == 1, (
            f"KanbanFactory.create must run exactly once under "
            f"concurrent create_project; ran {factory_create_calls} times"
        )

    @pytest.mark.asyncio
    async def test_concurrent_calls_complete_within_wall_clock_budget(
        self, tmp_path: Path
    ) -> None:
        """3 concurrent calls finish in seconds, not the 807s pre-fix stall.

        The original bug had three concurrent callers triggering a
        ~720s dedup-guard loop after racing on kanban_client init.
        Post-fix the lock-protected block adds at most one connect()
        latency to the slowest caller.  Budget is generous (5s) so the
        test isn't flaky on slow CI; the regression we're catching is
        order-of-magnitude.
        """
        from src.marcus_mcp.tools import nlp as nlp_module

        state = _make_state_no_client()

        def _factory_create(provider: str) -> Any:
            client = MagicMock()
            client.provider = provider
            client.connect = AsyncMock()
            client.board_id = "board-test"
            return client

        mock_creator_class = MagicMock()
        mock_creator_instance = MagicMock()
        mock_creator_instance.create_project_from_description = AsyncMock(
            side_effect=lambda **kwargs: _stub_creator_result(
                f"proj-{kwargs['project_name']}"
            )
        )
        mock_creator_class.return_value = mock_creator_instance

        start = time.monotonic()
        # Stub get_config to bypass marcus_config.json validation
        # (kanban.provider is the only field create_project reads).
        cfg = MagicMock()
        cfg.kanban = MagicMock()
        cfg.kanban.provider = "sqlite"

        with (
            patch(
                "src.config.marcus_config.get_config",
                return_value=cfg,
            ),
            patch(
                "src.integrations.kanban_factory.KanbanFactory.create",
                side_effect=_factory_create,
            ),
            patch(
                "src.integrations.nlp_tools.NaturalLanguageProjectCreator",
                mock_creator_class,
            ),
        ):
            await asyncio.gather(
                *[
                    nlp_module.create_project(
                        description=f"description {i}",
                        project_name=f"budget_test_{i}",
                        options={
                            "provider": "sqlite",
                            "project_root": str(tmp_path / f"impl_{i}"),
                        },
                        state=state,
                    )
                    for i in range(3)
                ]
            )
        elapsed = time.monotonic() - start

        # 5s is generous — the actual happy path is ~10ms with mocks.
        # Catches order-of-magnitude regression (807s stall would be
        # multiple orders over budget).
        assert elapsed < 5.0, (
            f"Concurrent create_project should complete in seconds, "
            f"not stall.  Elapsed: {elapsed:.1f}s"
        )

    @pytest.mark.asyncio
    async def test_no_caller_observes_half_initialized_client(
        self, tmp_path: Path
    ) -> None:
        """Every concurrent call sees a fully-initialized kanban_client.

        Pre-fix, a caller could observe state.kanban_client right after
        ``KanbanFactory.create(...)`` returned but before ``connect()``
        completed, leaving the caller with a partially-initialized
        client.  The lock makes create + connect atomic.

        Test verifies this by making ``connect()`` slow (await
        asyncio.sleep) — without the lock, callers 2 and 3 would
        observe state.kanban_client populated with a not-yet-connected
        instance.  Under the lock, they wait until connect() finishes.
        """
        from src.marcus_mcp.tools import nlp as nlp_module

        state = _make_state_no_client()

        # Track whether any caller observed a state.kanban_client
        # whose connect() hadn't completed.
        half_init_observed = []

        connected_event = asyncio.Event()

        async def _slow_connect() -> None:
            # Yield to other coroutines so they can race if not locked
            await asyncio.sleep(0.01)
            connected_event.set()

        def _factory_create(provider: str) -> Any:
            client = MagicMock()
            client.provider = provider
            client.connect = AsyncMock(side_effect=_slow_connect)
            client.board_id = "board-test"
            return client

        mock_creator_class = MagicMock()

        async def _check_client_state(**kwargs: Any) -> dict[str, Any]:
            # By the time NLPC runs, state.kanban_client must be fully
            # initialized (connect() finished).  If a half-init slipped
            # through, connected_event would still be unset on a caller
            # that bypassed the lock.
            if not connected_event.is_set():
                half_init_observed.append(kwargs["project_name"])
            return _stub_creator_result(f"proj-{kwargs['project_name']}")

        mock_creator_instance = MagicMock()
        mock_creator_instance.create_project_from_description = AsyncMock(
            side_effect=_check_client_state
        )
        mock_creator_class.return_value = mock_creator_instance

        # Stub get_config to bypass marcus_config.json validation
        # (kanban.provider is the only field create_project reads).
        cfg = MagicMock()
        cfg.kanban = MagicMock()
        cfg.kanban.provider = "sqlite"

        with (
            patch(
                "src.config.marcus_config.get_config",
                return_value=cfg,
            ),
            patch(
                "src.integrations.kanban_factory.KanbanFactory.create",
                side_effect=_factory_create,
            ),
            patch(
                "src.integrations.nlp_tools.NaturalLanguageProjectCreator",
                mock_creator_class,
            ),
        ):
            await asyncio.gather(
                *[
                    nlp_module.create_project(
                        description=f"description {i}",
                        project_name=f"half_init_test_{i}",
                        options={
                            "provider": "sqlite",
                            "project_root": str(tmp_path / f"impl_{i}"),
                        },
                        state=state,
                    )
                    for i in range(3)
                ]
            )

        assert half_init_observed == [], (
            f"No caller should observe a half-initialized kanban_client; "
            f"these callers did: {half_init_observed}"
        )

    @pytest.mark.asyncio
    async def test_existing_matching_client_skips_factory_call(
        self, tmp_path: Path
    ) -> None:
        """When state.kanban_client already matches requested provider,
        no concurrent caller calls KanbanFactory.create.

        Pins the second branch of need_new_client: identity check
        on provider.  If state already has a sqlite client and all
        callers request sqlite, none should re-init.  The lock still
        serializes the check, but the check returns "no init needed"
        and KanbanFactory.create is never called.
        """
        from src.integrations.kanban_interface import KanbanProvider
        from src.marcus_mcp.tools import nlp as nlp_module

        state = MagicMock()
        # Pre-populate with a sqlite client so need_new_client is False
        existing_client = MagicMock()
        existing_client.provider = KanbanProvider.SQLITE
        existing_client.board_id = "board-existing"
        state.kanban_client = existing_client
        state.ai_engine = MagicMock()
        state.subtask_manager = None
        state.log_event = MagicMock()
        state.events = None

        factory_create_calls = 0

        def _counted_factory_create(provider: str) -> Any:
            nonlocal factory_create_calls
            factory_create_calls += 1
            client = MagicMock()
            client.provider = provider
            client.connect = AsyncMock()
            client.board_id = "board-test"
            return client

        mock_creator_class = MagicMock()
        mock_creator_instance = MagicMock()
        mock_creator_instance.create_project_from_description = AsyncMock(
            side_effect=lambda **kwargs: _stub_creator_result(
                f"proj-{kwargs['project_name']}"
            )
        )
        mock_creator_class.return_value = mock_creator_instance

        # Stub get_config to bypass marcus_config.json validation
        # (kanban.provider is the only field create_project reads).
        cfg = MagicMock()
        cfg.kanban = MagicMock()
        cfg.kanban.provider = "sqlite"

        with (
            patch(
                "src.config.marcus_config.get_config",
                return_value=cfg,
            ),
            patch(
                "src.integrations.kanban_factory.KanbanFactory.create",
                side_effect=_counted_factory_create,
            ),
            patch(
                "src.integrations.nlp_tools.NaturalLanguageProjectCreator",
                mock_creator_class,
            ),
        ):
            await asyncio.gather(
                *[
                    nlp_module.create_project(
                        description=f"description {i}",
                        project_name=f"existing_client_{i}",
                        options={
                            "provider": "sqlite",
                            "project_root": str(tmp_path / f"impl_{i}"),
                        },
                        state=state,
                    )
                    for i in range(3)
                ]
            )

        assert factory_create_calls == 0, (
            f"KanbanFactory.create must NOT run when state already has a "
            f"matching client; ran {factory_create_calls} times"
        )
