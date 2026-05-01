"""Wrap the legacy outcome-coverage helpers behind GraphAugmenter (issue #456 Stage 2).

Pre-#456, ``_apply_outcome_coverage_to_graph`` (feature-based) and
``_apply_outcome_coverage_to_contract_graph`` (contract-first) were
called directly from ``AdvancedPRDParser`` decompose paths.  This
augmenter wraps both behind a single
:class:`~src.marcus_mcp.coordinator.graph_augmentation.GraphAugmenter`
surface so Stage-3 can route every decomposer through one
augmenter chain instead of two parallel call sites.

Stage-2 scope
-------------
Wrapper only — the underlying helpers are unchanged.  The wrapper
delegates to whichever helper matches the path
(``contract_artifacts is None`` → feature-based; else
contract-first), then translates the helper's
:class:`ParserOutcomeCoverage` return into an
:class:`AugmentationResult` shaped for the Protocol.

Telemetry-key contract
----------------------
``AugmentationResult.telemetry`` keys are pinned to the existing
``PLANNING_INTENT_FIDELITY`` event payload at
``src/integrations/nlp_tools.py:391-400`` so Cato consumers continue
to read the same shape after Stage-3 routes the call through this
augmenter:

* ``intent_fidelity_score`` (``Optional[float]``)
* ``coverage_before_fill`` (``Dict[str, List[str]]``)
* ``coverage_after_fill`` (``Optional[Dict[str, List[str]]]``)
* ``gap_filled_outcomes`` (``List[str]`` — outcome IDs)

Silent key drift would break Cato silently; the
``TestTelemetryKeyPinning`` suite locks these explicitly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from src.core.models import Task
from src.marcus_mcp.coordinator.graph_augmentation import AugmentationResult

if TYPE_CHECKING:
    # Imported only for type-checking to avoid the runtime circular
    # import: ``advanced_parser`` already imports from
    # ``marcus_mcp.coordinator``; importing AdvancedPRDParser /
    # PRDAnalysis at module load time here would close the cycle.
    from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser, PRDAnalysis

__all__ = ["OutcomeCoverageAugmenter"]


class OutcomeCoverageAugmenter:
    """Augmenter that delegates to the existing outcome-coverage helpers.

    Satisfies the
    :class:`~src.marcus_mcp.coordinator.graph_augmentation.GraphAugmenter`
    Protocol.  Constructed with a parser instance whose private
    ``_apply_outcome_coverage_to_graph`` and
    ``_apply_outcome_coverage_to_contract_graph`` methods carry the
    real coverage logic; the wrapper picks the right helper based on
    whether ``contract_artifacts`` is provided.

    Attributes
    ----------
    name : str
        Stable identifier ``"outcome_coverage"`` used as the telemetry
        event key, in log lines, and (Stage-3) as the augmenter chain
        registration name.

    Parameters
    ----------
    parser : AdvancedPRDParser
        The parser whose helpers this augmenter delegates to.  Typed
        as ``Any`` to keep the runtime import out of this module
        (advanced_parser already imports from ``marcus_mcp.coordinator``
        and would close the cycle).

    Notes
    -----
    Stage-2 contract: behavior-preserving wrapper.  The underlying
    helpers retain their own exception handling — they catch broadly
    and return ``None`` on failure, which the wrapper translates into
    a no-op :class:`AugmentationResult` (input tasks, empty
    ``synthesized_ids``, empty ``telemetry``).

    .. warning:: TRANSITIONAL DEBT — Stage 5 cleanup is mandatory

       This wrapper deliberately reaches into ``AdvancedPRDParser``'s
       private ``_apply_outcome_coverage_to_*`` methods to preserve
       behavior across the Stage-3 cutover (Kaia review #3, Simon
       ``4453bd2c``).  This soft coupling is acceptable only as a
       transitional state.  Stage 5 of issue #456 **must** either:

       - inline the helper logic into this augmenter and delete the
         parser-side methods, or
       - lift the helpers to public coordinator-module functions and
         call them by name (no underscore reach-in).

       Do not merge the issue #456 PR while this wrapper still
       depends on private methods of another class.  ``git grep
       _apply_outcome_coverage`` should return zero hits at PR time.
    """

    name: str = "outcome_coverage"

    def __init__(self, *, parser: "AdvancedPRDParser") -> None:
        self._parser = parser

    async def augment(
        self,
        *,
        prd_analysis: "PRDAnalysis",
        tasks: List[Task],
        contract_artifacts: Optional[Dict[str, Any]] = None,
    ) -> AugmentationResult:
        """Delegate to the appropriate outcome-coverage helper.

        Parameters
        ----------
        prd_analysis : PRDAnalysis
            Deep PRD analysis (carries ``original_description`` and
            ``user_outcomes`` the underlying helpers consume).
        tasks : list of Task
            Current task graph from the decomposer.  Not mutated.
        contract_artifacts : dict, optional
            Contract-first artifact map (``{domain: {"artifacts": [...]}}``).
            ``None`` for the feature-based path.  Presence selects
            which helper runs.

        Returns
        -------
        AugmentationResult
            ``augmented_tasks`` is the helper's return list (or the
            input list verbatim on no-op); ``synthesized_ids`` lists
            IDs of any tasks the helper appended; ``telemetry`` carries
            the canonical PLANNING_INTENT_FIDELITY keys when coverage
            ran, empty otherwise.
        """
        if contract_artifacts is not None:
            parser_result = (
                await self._parser._apply_outcome_coverage_to_contract_graph(
                    prd_analysis=prd_analysis,
                    tasks=tasks,
                    contract_artifacts=contract_artifacts,
                )
            )
        else:
            parser_result = await self._parser._apply_outcome_coverage_to_graph(
                prd_analysis=prd_analysis,
                tasks=tasks,
            )

        if parser_result is None:
            # Helper returned None: flag off, no outcomes, or LLM error.
            # Per Stage-2 contract, this is a no-op — the decomposer
            # continues with the input task graph unchanged.
            return AugmentationResult(augmented_tasks=list(tasks))

        input_ids = {t.id for t in tasks}
        synthesized_ids = [
            t.id for t in parser_result.augmented_tasks if t.id not in input_ids
        ]

        telemetry: Dict[str, Any] = {}
        coverage = parser_result.coverage
        if coverage is not None:
            # Pin keys to PLANNING_INTENT_FIDELITY event payload.
            # Drift here breaks Cato consumers silently — see
            # TestTelemetryKeyPinning for the locked contract.
            telemetry = {
                "intent_fidelity_score": coverage.intent_fidelity_score,
                "coverage_before_fill": coverage.coverage_before_fill,
                "coverage_after_fill": coverage.coverage_after_fill,
                "gap_filled_outcomes": [g.id for g in coverage.gaps],
            }

        return AugmentationResult(
            augmented_tasks=parser_result.augmented_tasks,
            synthesized_ids=synthesized_ids,
            telemetry=telemetry,
        )
