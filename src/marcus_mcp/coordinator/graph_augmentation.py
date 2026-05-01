"""
Graph augmentation Protocol for pre-inference task synthesis (issue #456).

Marcus's task decomposers (``parse_prd_to_tasks`` and
``decompose_by_contract``) produce an initial task graph.  Before
``_infer_smart_dependencies`` runs and foundation wiring fires, that
graph can pass through one or more **augmenters** that synthesize
additional tasks to fill gaps:

* ``OutcomeCoverageAugmenter`` (Stage 2) — catches missing
  user-visible outcomes (the v32 narrative; #449)
* ``SpecCoverageAugmenter`` (Stage 4) — catches spec features
  with no covering task (the v37 ``Implement Speed Progression``
  orphan failure mode)

Future augmenters (NFR coverage, security checks, etc.) can join
the chain by satisfying the :class:`GraphAugmenter` Protocol.

Why this Protocol exists
------------------------
Pre-#456, ``outcome_coverage`` and ``spec_coverage`` were parallel
pipelines with divergent integration:

* ``outcome_coverage`` ran *inside* the decomposer between
  ``_create_detailed_tasks`` and ``_infer_smart_dependencies`` —
  synthesized tasks correctly participated in dependency inference
  and foundation wiring.
* ``spec_coverage`` ran *after* the decomposer + safety checks
  (``nlp_tools.py:1341``) — synthesized tasks were orphans
  (``dependencies=[]``) bypassing both inference and foundation
  wiring.

The unified Protocol moves both pipelines to the same correct
location, removes the parallel-implementation smell, and gives
future augmenters a single plug-in point.

Bright-line check
-----------------
Augmenters synthesize tasks Marcus thinks should exist (coordination
contract).  Each task says WHAT to build; the agent picks HOW.
Same authority Marcus already exercises via ``_synthesize_shared_foundation``.
Coordination, not control.

Stage 1 scope
-------------
This module defines only the abstract surface (``GraphAugmenter``
Protocol + :class:`AugmentationResult` dataclass).  No augmenter
implementation, no decomposer call-site change.  Stages 2-4 progressively
migrate ``outcome_coverage`` and ``spec_coverage`` to use this
interface.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Protocol,
    Sequence,
    runtime_checkable,
)

from src.core.models import Task

if TYPE_CHECKING:
    # Imported only for type-checking to avoid the runtime circular
    # import: ``advanced_parser`` already imports from
    # ``marcus_mcp.coordinator``; importing PRDAnalysis at module
    # load time here would close the cycle.
    from src.ai.advanced.prd.advanced_parser import PRDAnalysis

logger = logging.getLogger(__name__)

__all__ = ["AugmentationResult", "GraphAugmenter", "run_augmenter_chain"]


@dataclass
class AugmentationResult:
    """Result of running a :class:`GraphAugmenter` against a task graph.

    Attributes
    ----------
    augmented_tasks : list of Task
        Original tasks plus any synthesized.  This is the list the
        decomposer continues with — passed to
        ``_infer_smart_dependencies`` and downstream wiring.
    synthesized_ids : list of str
        IDs of newly-synthesized tasks (subset of
        ``augmented_tasks``).  Useful for logging, telemetry, and
        downstream filtering (e.g., "don't run augmenter X on
        tasks augmenter Y just synthesized").
    telemetry : dict
        Augmenter-specific metrics for event emission.
        Generic ``Dict[str, Any]`` keeps the Protocol simple — typed
        Union would force every augmenter to declare a typed payload
        upfront, premature when augmenter shapes are still evolving.
    """

    augmented_tasks: List[Task]
    synthesized_ids: List[str] = field(default_factory=list)
    telemetry: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class GraphAugmenter(Protocol):
    """Pre-inference task graph augmenter.

    Implementations run inside ``parse_prd_to_tasks`` /
    ``decompose_by_contract`` between ``_create_detailed_tasks`` and
    ``_infer_smart_dependencies``, so synthesized tasks are
    first-class participants in dependency inference and foundation
    wiring.

    Implementation contract
    -----------------------
    * ``name``: short identifier used as the telemetry event key
      and in log lines (e.g. ``"outcome_coverage"``,
      ``"spec_coverage"``).
    * ``augment``: async method that takes the current state
      (PRDAnalysis + task list + optional contract artifacts) and
      returns the augmented task list plus telemetry.  **Must be a
      pure function w.r.t. its inputs** — no mutation of ``tasks``,
      no side effects beyond LLM calls.

    Bright-line note
    ----------------
    Augmenters synthesize tasks Marcus thinks should exist.  Each
    task's description must say WHAT to build (a coordination
    contract), never HOW (which library, file, pattern).  Two agents
    handed the same synthesized task must produce legitimately
    different implementations.

    See Also
    --------
    AugmentationResult : the typed return shape augmenters produce.
    """

    name: str

    async def augment(
        self,
        *,
        prd_analysis: "PRDAnalysis",
        tasks: List[Task],
        contract_artifacts: Optional[Dict[str, Any]] = None,
    ) -> AugmentationResult:
        """Synthesize tasks for any gaps the augmenter detects.

        Parameters
        ----------
        prd_analysis
            Deep PRD analysis from ``_analyze_prd_deeply``, including
            ``original_description``, ``user_outcomes``, and
            ``functional_requirements``.  Augmenters may use any of
            these for gap detection.
        tasks
            Current task graph after ``_create_detailed_tasks`` (or
            after ``decompose_by_contract`` for contract-first path).
            **Must not be mutated** — return a new list.
        contract_artifacts
            Contract-first artifact dict from
            ``_generate_contracts_by_domain``, or ``None`` for the
            feature-based path.  Augmenters that ground gap-fill in
            existing contracts (currently outcome_coverage) read this;
            others may ignore.

        Returns
        -------
        AugmentationResult
            Augmented task list + synthesized IDs + telemetry.

        Notes
        -----
        Implementations should catch their own exceptions and return
        a no-op result (``augmented_tasks=tasks, synthesized_ids=[]``)
        on failure — graceful degradation is each augmenter's primary
        responsibility, matching the
        :func:`apply_outcome_coverage_to_feature_graph` pattern which
        catches broadly and downgrades to a logged warning.

        The chain orchestrator (:func:`run_augmenter_chain`) provides
        defense-in-depth: it wraps every ``augment`` call in
        ``try/except`` so an unexpected raise (programming error,
        new code path that forgot to catch) cannot crash the
        decomposer.  Augmenters must not rely on this — the
        orchestrator catch is a safety net, not the primary contract.
        """
        ...


async def run_augmenter_chain(
    augmenters: Sequence[GraphAugmenter],
    *,
    prd_analysis: "PRDAnalysis",
    tasks: List[Task],
    contract_artifacts: Optional[Dict[str, Any]] = None,
) -> AugmentationResult:
    """Run augmenters sequentially over a task graph.

    Each augmenter sees the post-previous-augmenter task list, so
    synthesized tasks flow forward through the chain
    (e.g., ``outcome_coverage``'s gap-fill task is visible to
    ``spec_coverage``'s coverage check).  Telemetry is namespaced by
    ``augmenter.name`` so future augmenters add their payload
    alongside without key collisions.

    Defense-in-depth (Kaia review #2, Simon ``c26c7ec5``): every
    ``augment`` call is wrapped in ``try/except``.  Augmenters
    catching their own exceptions remain the primary contract; the
    chain catch is the last line of defense for programming errors
    or future augmenters that forgot to catch.  Failures log a
    warning naming the augmenter and continue with prior tasks
    (no-op for that step).

    Parameters
    ----------
    augmenters : sequence of GraphAugmenter
        The chain, executed in iteration order.  Empty sequence is
        valid and produces a passthrough result.
    prd_analysis : PRDAnalysis
        Forwarded to every augmenter.  Some augmenters
        (``outcome_coverage``) require it; others may ignore.
    tasks : list of Task
        Initial task graph.  Not mutated.
    contract_artifacts : dict, optional
        Forwarded to every augmenter.  ``None`` for the feature-based
        decomposer path; non-None for contract-first.

    Returns
    -------
    AugmentationResult
        ``augmented_tasks`` is the post-chain task list (input plus
        any synthesized).  ``synthesized_ids`` is the union of IDs
        each augmenter reported.  ``telemetry`` is ``{augmenter.name:
        augmenter_telemetry}`` for every augmenter that ran and
        produced non-empty telemetry; failed or empty-telemetry
        augmenters contribute no key.
    """
    # Validate name uniqueness before running any augmenter.  Telemetry
    # is namespaced by ``augmenter.name``; duplicate names would
    # silently overwrite each other's slice in the result dict.  Fail
    # fast at chain entry so the diagnostic is "wiring bug, fix the
    # registration" rather than "augmenter A's data is gone, why?"
    # (Kaia review #4, Simon ``f36c49c4``).
    seen_names: Dict[str, int] = {}
    for augmenter in augmenters:
        seen_names[augmenter.name] = seen_names.get(augmenter.name, 0) + 1
    duplicates = [name for name, count in seen_names.items() if count > 1]
    if duplicates:
        raise ValueError(
            f"Augmenter chain has duplicate name(s): {sorted(duplicates)}. "
            f"Each augmenter must have a unique ``name`` so its "
            f"telemetry slice is addressable in the result."
        )

    current_tasks: List[Task] = list(tasks)
    accumulated_synthesized_ids: List[str] = []
    namespaced_telemetry: Dict[str, Any] = {}

    for augmenter in augmenters:
        try:
            result = await augmenter.augment(
                prd_analysis=prd_analysis,
                tasks=current_tasks,
                contract_artifacts=contract_artifacts,
            )
        except Exception as exc:
            # Defense-in-depth: a buggy or future augmenter that
            # forgot to catch must not crash the decomposer.  Skip
            # this augmenter, keep prior tasks, continue chain.  Log
            # with augmenter name so the failure is diagnosable.
            logger.warning(
                "Augmenter %r raised %s; skipping: %s",
                augmenter.name,
                type(exc).__name__,
                exc,
            )
            continue

        current_tasks = result.augmented_tasks
        accumulated_synthesized_ids.extend(result.synthesized_ids)
        # Omit empty-telemetry augmenters from the namespace so
        # consumers can distinguish "augmenter ran, no data" from
        # "augmenter didn't run."
        if result.telemetry:
            namespaced_telemetry[augmenter.name] = result.telemetry

    return AugmentationResult(
        augmented_tasks=current_tasks,
        synthesized_ids=accumulated_synthesized_ids,
        telemetry=namespaced_telemetry,
    )
