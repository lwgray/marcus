"""
Composition task synthesis for multi-domain contract-first projects.

Issue #463 — Marcus's task decomposer can produce a multi-domain
project where every domain ships correctly but no task owns wiring
them into the application's composition root.  v38 audit case
(snake-game-v38, 2026-04-29): three domain implementations
(engine, bus, renderer) shipped clean but ``App.tsx`` returned
``null``.  Unit tests passed.  The bundle built.  But the rendered
DOM was empty — the integration verification catch-all rescued it
at the cost of ~15 min cleanup absorbed by an agent on top of
their other work.

Fix (Variant V3 per Kaia review checkpoint #1): synthesize a
dedicated composition task when ``len(impl_tasks) >= 2``.  Marcus
says WHAT (a wiring task with explicit deliverables — log_decision
+ log_artifact); the agent picks HOW (which file is the entry
point, which wiring strategy).  Multiple framework examples are
included in the description so Marcus is not picking a single
file.

Bright-line check: two foundation agents handed this task can
produce legitimately different wirings — different file choices,
different mounting strategies.  Coordination, not control.

Layering with ``enhance_project_with_integration``: composition
is **narrow scope** (entry-point wiring only), assigned **early**
when impls complete.  Integration verification is the **broad
catch-all** (orphan scan, missing components, contract
verification), assigned **late**.  Intentional layered safety,
not redundant — composition makes wiring an explicit deliverable
with explicit ownership; IV catches anything composition missed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from src.core.models import Priority, Task, TaskStatus

__all__ = ["build_composition_task"]


def _has_existing_composition_task(impl_tasks: List[Task]) -> bool:
    """Return True if a composition task is already present in the list.

    Idempotency guard: skip synthesis if the caller already has a
    composition task in the input list.  Two detection routes:

    1. ``"composition"`` label present (canonical Marcus tag)
    2. ``source_type == "composition_synthesis"`` (canonical source
       marker — survives kanban round-trips that strip labels)
    """
    for task in impl_tasks:
        labels = task.labels or []
        if "composition" in labels:
            return True
        if getattr(task, "source_type", None) == "composition_synthesis":
            return True
    return False


def _build_composition_description(project_name: str) -> str:
    """Render the composition task description (Variant V3).

    The description must:

    - List multiple framework entry-point examples (so Marcus is not
      picking one — agents legitimately use different framework
      conventions)
    - Tell the agent to **discover** the entry point from the scaffold
    - Require ``log_decision`` titled ``"Entry point wired"`` so
      downstream tools can verify wiring happened
    - Require ``log_artifact`` for the wired file (file-level surface
      for the structured-decision metadata)

    Bright-line guard: the description must NOT name a specific entry
    point file (e.g., ``"the entry point is App.tsx"``).  Multiple
    examples are listed; the agent picks which applies to their
    scaffold.
    """
    return (
        f"Wire {project_name}'s implementation domains into a working "
        f"composition root.  The entry point is the file that boots "
        f"the project — discover it from the scaffold (e.g. App.tsx "
        f"for Vite/CRA, main.py for Python, index.ts for Node — "
        f"whichever your scaffold uses).\n\n"
        f"Required deliverables:\n"
        f"1. Wire all domain implementations into the entry point so "
        f"the composed product is functionally end-to-end.\n"
        f"2. Call log_decision titled 'Entry point wired' with the "
        f"actual file path you chose, the domains you composed, and "
        f"the wiring approach (DI container, direct mounting, etc.).\n"
        f"3. Call log_artifact for the entry-point file you modified "
        f"so downstream verification can locate it.\n"
        f"4. Verify the composed product runs (smoke test the "
        f"composition root)."
    )


def build_composition_task(
    *,
    project_name: str,
    impl_tasks: List[Task],
) -> Optional[Task]:
    """Synthesize a composition task when ``len(impl_tasks) >= 2``.

    Issue #463 — multi-domain projects need an explicit wiring task
    or domains ship correctly while ``App.tsx`` returns ``null``.

    The synthesized task carries hard dependencies on every input
    impl task; the agent that picks it up must wait until all impls
    complete before wiring.  Foundation deps are NOT direct — they
    flow transitively via impl deps already wired at
    ``nlp_tools.py:332``.

    Parameters
    ----------
    project_name : str
        Project name, used in the task name and description so the
        agent has context.
    impl_tasks : List[Task]
        Contract-first implementation tasks the caller has already
        produced.  Caller filters to impl tasks (excluding foundation,
        design ghosts, etc.) before passing.  This list is **not
        mutated** — the helper is a pure function.

    Returns
    -------
    Optional[Task]
        A new composition task with hard deps on every input impl
        task, or ``None`` when:

        - ``len(impl_tasks) < 2`` (no need for explicit composition;
          single-impl projects compose naturally)
        - A composition task is already present in ``impl_tasks``
          (idempotency guard)

    Notes
    -----
    Bright-line: Marcus says WHAT must be produced (a coordination
    task with explicit deliverables); agent picks HOW (which file,
    which wiring strategy).  Two agents handed this task can produce
    legitimately different implementations.  Coordination, not
    control.
    """
    if len(impl_tasks) < 2:
        return None
    if _has_existing_composition_task(impl_tasks):
        return None

    now = datetime.now(timezone.utc)
    return Task(
        id=f"composition_{uuid4().hex[:12]}",
        name=f"Compose {project_name} entry point",
        description=_build_composition_description(project_name),
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        assigned_to=None,
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=1.5,
        # Hard deps on every impl task — composition must wait until
        # all implementations complete (nothing to wire otherwise).
        dependencies=[t.id for t in impl_tasks],
        labels=["composition", "marcus_synthesized"],
        source_type="composition_synthesis",
        # responsibility surfaces in build_tiered_instructions as the
        # CONTRACT RESPONSIBILITY layer so the agent prompt frames
        # this as a coordination boundary, not a prescriptive spec.
        responsibility="Wires the application entry point",
    )
