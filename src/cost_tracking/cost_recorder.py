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


def canonical_project_id(project_id: Optional[str]) -> Optional[str]:
    """Normalize a project_id to the canonical form used in cost data.

    Marcus's ``ProjectRegistry`` stores UUIDs in canonical dashed form
    (``str(uuid.uuid4())``), while ``SQLiteKanban`` auto-discovery
    stores them in dashless hex form (``uuid.uuid4().hex``). Both can
    end up in ``data/marcus_state/projects.json`` depending on the
    code path that created the project, and downstream callers
    (PlannerContext, WorkerJSONLIngester) may receive either form.

    For ``token_events.project_id`` we pick **dashless** as the
    canonical form. Rationale: it matches the bulk of existing rows
    (created via auto-discovery) and the ``.hex`` path is the
    cheapest to keep consistent — ProjectRegistry's dashed strings
    just lose their dashes here. Dashboard joins against the cost DB
    therefore always operate on the dashless form; Cato's name
    overlay reads projects.json and indexes both forms so name
    resolution still works for either source.

    Returns ``None`` unchanged so the 'unassigned' fallback in
    :func:`CostRecorder.record_planner_call` still trips.
    """
    if project_id is None:
        return None
    # Pass through the 'unassigned' sentinel — it's not a UUID.
    if project_id == "unassigned":
        return project_id
    return project_id.replace("-", "")


@dataclass(frozen=True)
class PlannerContext:
    """Per-request context used to attribute planner LLM calls.

    ``project_id`` is normalized via :func:`canonical_project_id` on
    construction so every cost row uses the same form regardless of
    which Marcus code path produced the source id.

    Parameters
    ----------
    experiment_id : str
        Active experiment ID (use ``'unassigned'`` if the call happens
        outside an experiment lifecycle).
    project_id : str
        Active Marcus project ID. Normalized to dashless hex via
        :func:`canonical_project_id`.
    project_name : str, optional
        Human-readable name for the project. When supplied, the
        recorder snapshots ``(project_id, name)`` into ``project_names``
        on push so the dashboard can still render the right label after
        the project is deleted from the Marcus registry.
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
    project_name: Optional[str] = None
    agent_id: str = "planner"
    task_id: Optional[str] = None
    operation_override: Optional[str] = None

    def __post_init__(self) -> None:
        """Normalize project_id to the canonical cost-data form."""
        normalized = canonical_project_id(self.project_id)
        if normalized is not None and normalized != self.project_id:
            # dataclass field — assignment works after __init__.
            object.__setattr__(self, "project_id", normalized)


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
        # Process-lifetime cache of (project_id, name) pairs already
        # snapshotted into project_names. Lets planner_context() skip
        # the SQL upsert on every push when the name hasn't changed —
        # the SQL itself is idempotent, so the cache is purely a
        # hot-path optimization, not a correctness mechanism (Kaia
        # review on #515). On rename, the new pair misses the cache,
        # we upsert, and store the new pair. Bounded to ~1k entries
        # (one per project ever seen this process) which is fine.
        self._snapshotted_names: set[tuple[str, str]] = set()
        # Process-lifetime set of operation keys we've already warned
        # about. Drift detection: a call site that passes a typo (or a
        # newly-introduced operation that nobody remembered to
        # register) silently falls through to the dashboard's
        # "Unregistered operation" fallback bucket — which defeats
        # the whole point of the taxonomy. We log a single WARNING
        # the first time each unknown key shows up so the gap is
        # visible in dev logs without spamming. Kaia review on the
        # operation-taxonomy PR.
        self._unregistered_operations_warned: set[str] = set()

    # -- context management -----------------------------------------------

    @contextmanager
    def planner_context(self, ctx: PlannerContext) -> Iterator[PlannerContext]:
        """Push a planner context for the duration of the ``with`` block.

        Innermost context wins. ContextVar token returned by ``set`` is
        used to restore the previous stack on exit, preserving correct
        nesting under concurrent asyncio tasks.

        Side effect: if ``ctx.project_name`` is set, snapshot
        ``(project_id, name)`` into ``project_names`` so the dashboard
        can still render the right label after the project is deleted
        from the Marcus registry. Idempotent (upsert); negligible cost.
        Failures swallowed — never break the calling code path.
        """
        if self.enabled and ctx.project_name and ctx.project_id != "unassigned":
            pair = (ctx.project_id, ctx.project_name)
            if pair not in self._snapshotted_names:
                try:
                    self.store.upsert_project_name(ctx.project_id, ctx.project_name)
                    self._snapshotted_names.add(pair)
                except Exception:  # pragma: no cover - logged, never raised
                    logger.exception(
                        "upsert_project_name failed for %s", ctx.project_id
                    )

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

    @contextmanager
    def operation_context(self, operation: str) -> Iterator[Optional[PlannerContext]]:
        """Push a child context with ``operation_override`` set.

        Used at LLM call sites to label *which* logical operation
        (decomposition, blocker analysis, dependency inference, etc.)
        is firing. The :func:`record_planner_call` path reads
        ``operation_override`` and stamps that label onto
        ``token_events.operation`` regardless of whatever default the
        provider passed.

        If there's no active PlannerContext (e.g., a background loop
        with no project attribution), this is a no-op — the call still
        falls through to 'unassigned' with whatever default operation
        the provider stamps.

        Yields the new context (or None when no parent exists) for
        convenience; most callers ignore the yielded value.
        """
        if not operation:
            yield self.current()
            return
        parent = self.current()
        if parent is None:
            yield None
            return
        # Replace operation_override on a shallow copy. PlannerContext
        # is a frozen dataclass; build a new instance with the override.
        from dataclasses import replace

        child = replace(parent, operation_override=operation)
        stack = list(_context_stack.get())
        stack.append(child)
        token = _context_stack.set(stack)
        try:
            yield child
        finally:
            _context_stack.reset(token)

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
        # Diagnostic: when a planner LLM call lands without an active
        # PlannerContext it falls back to 'unassigned'. Logged at DEBUG
        # so it's quiet by default but still discoverable when chasing
        # attribution gaps (#409 follow-up — this is how we found the
        # OpenAI provider missing the recorder hook).
        if ctx is None:
            logger.debug(
                "cost_recorder: NO context for operation=%s provider=%s "
                "model=%s tokens=%d (call will land in 'unassigned')",
                operation,
                provider,
                model,
                input_tokens
                + cache_creation_tokens
                + cache_read_tokens
                + output_tokens,
            )
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

        # Drift detection: warn once per process if the resolved
        # operation key isn't in the taxonomy catalog. A typo at a
        # call site (or a new operation that nobody remembered to
        # register) silently lands in the dashboard's fallback
        # bucket; this WARNING surfaces it in dev logs without
        # spamming production. Local import avoids the operations
        # module at recorder construction time.
        if operation not in self._unregistered_operations_warned:
            try:
                from src.cost_tracking.operations import OPERATIONS

                if operation not in OPERATIONS:
                    logger.warning(
                        "cost_recorder: operation '%s' is not registered "
                        "in src.cost_tracking.operations.OPERATIONS — it "
                        "will render with the synthesized fallback label "
                        "on the dashboard. Add it to the catalog for a "
                        "proper description.",
                        operation,
                    )
                    self._unregistered_operations_warned.add(operation)
            except Exception:  # pragma: no cover - catalog import failed
                # Don't break recording if the catalog itself can't load —
                # the recorder is side-effect-only by contract.
                pass

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
