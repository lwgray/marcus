"""Augmenter that runs outcome-coverage gap-fill (issue #456 Stage 5).

Dispatches between the feature-based and contract-first lifted helpers
in :mod:`src.marcus_mcp.coordinator.outcome_coverage` based on whether
``contract_artifacts`` is provided.  All behavior — flag check, no-op
on missing outcomes, LLM exception handling, gap-fill task synthesis,
canonical telemetry shape — lives in those module functions.  This
class is a thin Protocol-satisfying dispatcher.

Telemetry-key contract
----------------------
``AugmentationResult.telemetry`` keys are pinned to the existing
``PLANNING_INTENT_FIDELITY`` event payload at
``src/integrations/nlp_tools.py:391-400``:

* ``intent_fidelity_score`` (``Optional[float]``)
* ``coverage_before_fill`` (``Dict[str, List[str]]``)
* ``coverage_after_fill`` (``Optional[Dict[str, List[str]]]``)
* ``gap_filled_outcomes`` (``List[str]`` — outcome IDs)

Cato consumers read this slice via
``decompose_result.telemetry["outcome_coverage"]``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from src.core.models import Task
from src.marcus_mcp.coordinator.graph_augmentation import AugmentationResult
from src.marcus_mcp.coordinator.outcome_coverage import (
    apply_outcome_coverage_to_contract_graph,
    apply_outcome_coverage_to_feature_graph,
)

if TYPE_CHECKING:
    from src.ai.advanced.prd.advanced_parser import PRDAnalysis

__all__ = ["OutcomeCoverageAugmenter"]


class OutcomeCoverageAugmenter:
    """Augmenter that dispatches to the outcome-coverage module helpers.

    Satisfies the
    :class:`~src.marcus_mcp.coordinator.graph_augmentation.GraphAugmenter`
    Protocol.  Constructed with an LLM client and dispatches by
    presence of ``contract_artifacts`` to one of the lifted module
    functions.

    Attributes
    ----------
    name : str
        Stable identifier ``"outcome_coverage"`` used as the telemetry
        event key, in log lines, and as the augmenter chain
        registration name.

    Parameters
    ----------
    llm_client : Any
        The LLM client to thread into the coverage pipeline.  Typed
        as ``Any`` because Marcus uses several LLM client shapes
        (parser's ``LLMAbstraction``, test ``AsyncMock``s) and the
        coverage pipeline duck-types against ``analyze``.

    Lifetime expectation
    --------------------
    Stateless apart from the LLM client reference.  Constructed
    per-call inside ``parse_prd_to_tasks`` / ``decompose_by_contract``.
    If future enhancements add real state (caches, retry budgets),
    audit the construction sites in ``advanced_parser.py`` and move
    construction to per-decomposer-instance or per-process so the
    state is preserved across calls.
    """

    name: str = "outcome_coverage"

    def __init__(self, *, llm_client: Any) -> None:
        self._llm_client = llm_client

    async def augment(
        self,
        *,
        prd_analysis: "PRDAnalysis",
        tasks: List[Task],
        contract_artifacts: Optional[Dict[str, Any]] = None,
    ) -> AugmentationResult:
        """Dispatch to the matching coverage helper.

        Parameters
        ----------
        prd_analysis : PRDAnalysis
            Carries ``original_description`` and ``user_outcomes`` the
            helpers consume.
        tasks : list of Task
            Current task graph.  Not mutated.
        contract_artifacts : dict, optional
            Contract-first artifact map (``{domain: {"artifacts": [...]}}``).
            ``None`` for the feature-based path.  Presence selects
            which helper runs.

        Returns
        -------
        AugmentationResult
            Carries augmented_tasks (input plus any synthesized
            gap-fill), synthesized_ids of the new tasks, and
            telemetry with the canonical PLANNING_INTENT_FIDELITY
            keys when coverage ran (empty when it didn't).
        """
        if contract_artifacts is not None:
            return await apply_outcome_coverage_to_contract_graph(
                prd_analysis=prd_analysis,
                tasks=tasks,
                contract_artifacts=contract_artifacts,
                llm_client=self._llm_client,
            )
        return await apply_outcome_coverage_to_feature_graph(
            prd_analysis=prd_analysis,
            tasks=tasks,
            llm_client=self._llm_client,
        )
