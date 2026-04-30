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

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol, runtime_checkable

from src.core.models import Task

if TYPE_CHECKING:
    # Imported only for type-checking to avoid the runtime circular
    # import: ``advanced_parser`` already imports from
    # ``marcus_mcp.coordinator``; importing PRDAnalysis at module
    # load time here would close the cycle.
    from src.ai.advanced.prd.advanced_parser import PRDAnalysis

__all__ = ["AugmentationResult", "GraphAugmenter"]


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
        Implementations must catch their own exceptions and return a
        no-op result (``augmented_tasks=tasks, synthesized_ids=[]``)
        on failure.  The orchestrator does not catch — graceful
        degradation is each augmenter's responsibility.  This matches
        the existing ``_apply_outcome_coverage_to_graph`` pattern
        which catches broadly and downgrades to a logged warning.
        """
        ...
