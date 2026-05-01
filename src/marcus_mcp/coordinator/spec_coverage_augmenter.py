"""Wrap check_spec_coverage behind GraphAugmenter (issue #456 Stage 4).

Pre-#456, ``check_spec_coverage`` was called from
``nlp_tools.py:1336-1349`` *after* safety checks completed.  Gap
tasks synthesized by spec coverage were appended to the task list
with ``dependencies=[]``, making them orphans that bypassed both
``_infer_smart_dependencies`` and foundation wiring.  This was the
v37 orphan-failure-mode.

Stage 4 moves spec coverage into the augmenter chain that runs
*inside* the decomposer, between ``_create_detailed_tasks`` and
``_infer_smart_dependencies``.  Synthesized gap tasks are now
first-class graph members: dependency inference treats them like
any other task, foundation wiring picks them up, and downstream
integration verification finds them in the "all current tasks" pool.

Chain order matters
-------------------
``OutcomeCoverageAugmenter`` runs before ``SpecCoverageAugmenter`` so
spec coverage sees the post-outcome-coverage graph (including any
synthesized outcome gap-fill tasks).  Locked by
``test_second_augmenter_sees_first_augmenter_tasks`` in
``test_augmenter_chain.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from src.core.models import Task
from src.integrations.spec_coverage import check_spec_coverage
from src.marcus_mcp.coordinator.graph_augmentation import AugmentationResult

if TYPE_CHECKING:
    from src.ai.advanced.prd.advanced_parser import PRDAnalysis

__all__ = ["SpecCoverageAugmenter"]


class SpecCoverageAugmenter:
    """Augmenter that delegates to :func:`check_spec_coverage`.

    Satisfies the
    :class:`~src.marcus_mcp.coordinator.graph_augmentation.GraphAugmenter`
    Protocol.  Stateless — constructed without arguments; pulls the
    spec text from ``prd_analysis.original_description`` at call time.

    Attributes
    ----------
    name : str
        Stable identifier ``"spec_coverage"`` used as the telemetry
        key in the chain's namespaced result dict.

    Notes
    -----
    Stage-4 contract: behavior-preserving wrapper.  The underlying
    :func:`check_spec_coverage` retains its own broad
    ``try/except`` and returns ``[]`` on any failure (LLM error,
    timeout, parse error) — the augmenter translates an empty list
    into a no-op :class:`AugmentationResult`.

    Lifetime expectation
    --------------------
    Stateless.  Constructed per-call inside
    ``parse_prd_to_tasks`` / ``decompose_by_contract``.  See the
    matching note on :class:`OutcomeCoverageAugmenter` — the same
    tripwire applies if state is ever added.
    """

    name: str = "spec_coverage"

    async def augment(
        self,
        *,
        prd_analysis: "PRDAnalysis",
        tasks: List[Task],
        contract_artifacts: Optional[Dict[str, Any]] = None,
    ) -> AugmentationResult:
        """Run spec coverage check, append gap tasks if any.

        Parameters
        ----------
        prd_analysis : PRDAnalysis
            Source of the spec text via ``original_description``.
            Empty/missing description short-circuits to a no-op
            (avoids a needless LLM round-trip).
        tasks : list of Task
            Current task graph.  Threaded into
            :func:`check_spec_coverage` for the keyword-coverage
            scan.  Not mutated.
        contract_artifacts : dict, optional
            Part of the Protocol surface but unused — spec coverage
            operates on spec text, not contracts.  Accepted for
            interface uniformity, ignored at runtime.

        Returns
        -------
        AugmentationResult
            ``augmented_tasks`` is the input list plus any synthesized
            gap tasks.  ``synthesized_ids`` carries gap task IDs.
            ``telemetry`` is empty when no gaps were filled, otherwise
            ``{"spec_gap_count": N, "spec_gap_features": [...names]}``.
        """
        spec = prd_analysis.original_description or ""
        if not spec:
            return AugmentationResult(augmented_tasks=list(tasks))

        gap_tasks = await check_spec_coverage(
            description=spec,
            tasks=tasks,
            project_name="",  # vestigial: unused inside check_spec_coverage
        )

        if not gap_tasks:
            return AugmentationResult(augmented_tasks=list(tasks))

        return AugmentationResult(
            augmented_tasks=list(tasks) + gap_tasks,
            synthesized_ids=[t.id for t in gap_tasks],
            telemetry={
                "spec_gap_count": len(gap_tasks),
                "spec_gap_features": [t.name for t in gap_tasks],
            },
        )
