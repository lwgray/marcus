"""
Lightweight recording layer between AI providers and the cost store.

Providers call :meth:`CostRecorder.record_planner_call` after every
successful LLM request. The recorder writes a single ``token_events`` row,
attaching whichever planner context is currently active (set by Marcus's
MCP request handlers via :meth:`CostRecorder.planner_context`).

The recorder is intentionally:

- **Side-effect only.** Never raises; provider call paths must not be
  affected by store failures.
- **Disable-able.** A no-op mode keeps tests / minimal deployments fast.
- **Singleton-friendly.** A module-level instance is exposed via
  :func:`get_recorder` / :func:`set_recorder` so providers don't need
  dependency injection.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator, List, Optional

from src.cost_tracking.cost_store import CostStore, TokenEvent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlannerContext:
    """Per-request context used to attribute planner LLM calls.

    Parameters
    ----------
    experiment_id : str
        Active experiment ID (use ``'unassigned'`` if the call happens
        outside an experiment lifecycle).
    project_id : str
        Active Marcus project ID.
    agent_id : str, default ``'planner'``
        Logical agent name. Marcus's own LLM calls are attributed to
        ``'planner'`` by default; specialized callers can override.
    task_id : str, optional
        Current task ID, when known.
    operation_override : str, optional
        Force a specific ``operation`` value regardless of caller.
    """

    experiment_id: str
    project_id: str
    agent_id: str = "planner"
    task_id: Optional[str] = None
    operation_override: Optional[str] = None


# Stack of active contexts (innermost wins). ContextVar makes this
# safe across asyncio tasks and threads.
_context_stack: ContextVar[List[PlannerContext]] = ContextVar(
    "_cost_recorder_context_stack", default=[]
)


# ---------------------------------------------------------------------------
# Recorder
# ---------------------------------------------------------------------------


class CostRecorder:
    """Side-effect-only recorder of planner-side LLM calls.

    Parameters
    ----------
    store : CostStore
        Backing store for ``token_events`` writes.
    enabled : bool, default True
        When False, all ``record_*`` calls are no-ops.
    """

    def __init__(self, store: CostStore, enabled: bool = True) -> None:
        self.store = store
        self.enabled = enabled

    # -- context management -----------------------------------------------

    @contextmanager
    def planner_context(self, ctx: PlannerContext) -> Iterator[PlannerContext]:
        """Push a planner context for the duration of the ``with`` block.

        Innermost context wins. ContextVar token returned by ``set`` is
        used to restore the previous stack on exit, preserving correct
        nesting under concurrent asyncio tasks.
        """
        stack = list(_context_stack.get())
        stack.append(ctx)
        token = _context_stack.set(stack)
        try:
            yield ctx
        finally:
            _context_stack.reset(token)

    def current(self) -> Optional[PlannerContext]:
        """Return the active context (innermost), or None."""
        stack = _context_stack.get()
        return stack[-1] if stack else None

    # -- writes -----------------------------------------------------------

    def record_planner_call(
        self,
        *,
        operation: str,
        provider: str,
        model: str,
        input_tokens: int = 0,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: Optional[int] = None,
        request_id: Optional[str] = None,
        status: str = "ok",
        error_type: Optional[str] = None,
    ) -> None:
        """Write one ``token_events`` row attributed to the active context.

        Parameters
        ----------
        operation : str
            High-level op name (``'parse_prd'``, ``'analyze_blocker'``,
            ``'generate_instructions'``, ...). Overridden if the active
            context sets ``operation_override``.
        provider, model : str
            Provider key and model identifier.
        input_tokens, cache_creation_tokens, cache_read_tokens,
        output_tokens : int
            Token counts, all default to 0.
        latency_ms, request_id, status, error_type : optional
            Trace metadata.

        Notes
        -----
        Never raises. Failures are logged at WARNING and swallowed so
        that store outages cannot break the provider call path.
        """
        if not self.enabled:
            return
        ctx = self.current()
        if ctx is not None:
            experiment_id = ctx.experiment_id
            project_id = ctx.project_id
            agent_id = ctx.agent_id
            task_id = ctx.task_id
            if ctx.operation_override is not None:
                operation = ctx.operation_override
        else:
            experiment_id = "unassigned"
            project_id = "unassigned"
            agent_id = "planner"
            task_id = None

        event = TokenEvent(
            experiment_id=experiment_id,
            project_id=project_id,
            agent_id=agent_id,
            agent_role="planner",
            task_id=task_id,
            operation=operation,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            cache_creation_tokens=cache_creation_tokens,
            cache_read_tokens=cache_read_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            request_id=request_id,
            status=status,
            error_type=error_type,
        )
        try:
            self.store.record_event(event)
        except Exception as exc:  # pragma: no cover - logged, swallowed
            logger.warning("cost recorder swallowed store error: %s", exc)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_singleton: Optional[CostRecorder] = None


def get_recorder() -> CostRecorder:
    """Return the module-level recorder, lazily creating a no-op default.

    The default singleton is **disabled** and uses an in-memory store.
    Marcus's startup wires a real recorder via :func:`set_recorder` once
    the cost DB path is known.
    """
    global _singleton
    if _singleton is None:
        from pathlib import Path

        # Default: disabled in-memory store. Real wiring happens at startup.
        _singleton = CostRecorder(
            store=CostStore(db_path=Path(":memory:")),
            enabled=False,
        )
    return _singleton


def set_recorder(recorder: Optional[CostRecorder]) -> None:
    """Replace the module-level recorder.

    Pass ``None`` to clear and force the next :func:`get_recorder` call to
    rebuild a fresh no-op default (used by tests).
    """
    global _singleton
    _singleton = recorder
