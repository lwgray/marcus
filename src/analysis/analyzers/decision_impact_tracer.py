"""
Decision Impact Tracer for Phase 2 analysis.

Traces how architectural decisions cascade through a project, showing:
- Direct vs indirect impacts
- Anticipated vs unexpected consequences
- Decision depth and scope
- Impact prediction accuracy

Usage
-----
```python
tracer = DecisionImpactTracer()

# Trace a specific decision
analysis = await tracer.trace_decision_impact(
    decision=my_decision,
    related_decisions=other_decisions,
    all_tasks=project_tasks,
)

for chain in analysis.impact_chains:
    print(f"Decision {chain.decision_id} affected {len(chain.direct_impacts)} tasks")

for unexpected in analysis.unexpected_impacts:
    print(f"Unexpected: {unexpected.actual_impact}")
```
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional

from src.analysis.ai_engine import (
    AnalysisAIEngine,
    AnalysisRequest,
    AnalysisType,
)
from src.analysis.helpers.progress import ProgressCallback
from src.core.project_history import Decision

logger = logging.getLogger(__name__)


@dataclass
class ImpactChain:
    """
    A chain of impacts from a decision.

    Represents how a decision cascaded through the project,
    affecting tasks directly and indirectly.
    """

    decision_id: str
    decision_summary: str
    direct_impacts: list[str]  # Task IDs directly affected
    indirect_impacts: list[str]  # Task IDs indirectly affected
    depth: int  # How many levels deep the impact chain goes
    citation: str  # Evidence citation


@dataclass
class UnexpectedImpact:
    """
    An impact that was not anticipated when the decision was made.

    Represents a gap between predicted and actual consequences.
    """

    decision_id: str
    decision_summary: str
    affected_task_id: str
    affected_task_name: str
    anticipated: bool  # Was this impact predicted?
    actual_impact: str  # What actually happened
    severity: str  # "critical", "major", "minor"
    citation: str  # Evidence citation


@dataclass
class DecisionImpactAnalysis:
    """
    Complete analysis of a decision's impact cascade.

    Pairs LLM interpretation with raw data for transparency.
    """

    decision_id: str
    impact_chains: list[ImpactChain]
    unexpected_impacts: list[UnexpectedImpact]
    raw_data: dict[str, Any]  # Raw input data
    llm_interpretation: str  # Full LLM response
    recommendations: list[str]  # Actionable advice


class DecisionImpactTracer:
    """
    Analyzer that traces how decisions cascade through a project.

    Uses LLM to analyze decision impacts, comparing anticipated
    vs actual effects, and mapping impact chains.
    """

    def __init__(self, ai_engine: Optional[AnalysisAIEngine] = None):
        """
        Initialize Decision Impact Tracer.

        Parameters
        ----------
        ai_engine : AnalysisAIEngine, optional
            AI engine for LLM calls. Creates default if not provided.
        """
        self.ai_engine = ai_engine or AnalysisAIEngine()
        logger.info("Decision Impact Tracer initialized")

    async def trace_decision_impact(
        self,
        decision: Decision,
        related_decisions: list[Decision],
        all_tasks: list[dict[str, Any]],
        progress_callback: Optional[ProgressCallback] = None,
    ) -> DecisionImpactAnalysis:
        """
        Trace the impact cascade of a decision.

        Parameters
        ----------
        decision : Decision
            The decision to analyze
        related_decisions : list[Decision]
            Other decisions that might interact with this one
        all_tasks : list[dict]
            All tasks in the project (for impact tracing)
        progress_callback : ProgressCallback, optional
            Callback for progress updates

        Returns
        -------
        DecisionImpactAnalysis
            Complete analysis of decision impacts

        Examples
        --------
        >>> tracer = DecisionImpactTracer()
        >>> analysis = await tracer.trace_decision_impact(
        ...     decision=my_decision,
        ...     related_decisions=[],
        ...     all_tasks=tasks,
        ... )
        >>> print(f"Impact depth: {analysis.impact_chains[0].depth}")
        """
        # Build context for LLM
        context_data = {
            "decision_id": decision.decision_id,
            "decision_what": decision.what,
            "decision_why": decision.why,
            "decision_impact": decision.impact,
            "decision_confidence": decision.confidence,
            "decision_timestamp": decision.timestamp.isoformat(),
            "anticipated_impacts": decision.affected_tasks,
            "related_decisions": self.format_decisions(related_decisions),
            "all_tasks": self.format_tasks(all_tasks),
        }

        # Create analysis request
        request = AnalysisRequest(
            analysis_type=AnalysisType.DECISION_IMPACT,
            project_id="",  # Not needed for this analysis
            task_id=decision.task_id,
            context_data=context_data,
            prompt_template=self.build_prompt_template(),
        )

        # Execute analysis
        response = await self.ai_engine.analyze(
            request,
            progress_callback=progress_callback,
            use_cache=True,
        )

        # Parse impact chains
        impact_chains = [
            ImpactChain(**chain)
            for chain in response.parsed_result.get("impact_chains", [])
        ]

        # Parse unexpected impacts
        unexpected_impacts = [
            UnexpectedImpact(**impact)
            for impact in response.parsed_result.get("unexpected_impacts", [])
        ]

        # Build raw data record
        raw_data = {
            "decision_id": decision.decision_id,
            "decision_what": decision.what,
            "decision_why": decision.why,
            "anticipated_impacts": decision.affected_tasks,
            "related_decisions": len(related_decisions),
            "all_tasks": len(all_tasks),
        }

        # Create analysis result
        analysis = DecisionImpactAnalysis(
            decision_id=decision.decision_id,
            impact_chains=impact_chains,
            unexpected_impacts=unexpected_impacts,
            raw_data=raw_data,
            llm_interpretation=response.raw_response,
            recommendations=response.parsed_result.get("recommendations", []),
        )

        logger.info(
            f"Decision impact analysis complete for {decision.decision_id}: "
            f"chains={len(analysis.impact_chains)}, "
            f"unexpected={len(analysis.unexpected_impacts)}"
        )

        return analysis

    def build_prompt_template(self) -> str:
        """
        Build prompt template for decision impact tracing.

        Returns
        -------
        str
            Prompt template with placeholders for context data

        Notes
        -----
        Template emphasizes impact chains and prediction accuracy.
        """
        return """You are tracing how an architectural decision cascaded
through a software project.

ORIGINAL DECISION:
What: {decision_what}
Why: {decision_why}
Predicted Impact: {decision_impact}
Confidence: {decision_confidence}
Timestamp: {decision_timestamp}

ANTICIPATED IMPACTS:
Tasks expected to be affected:
{anticipated_impacts}

RELATED DECISIONS:
{related_decisions}

ALL PROJECT TASKS:
{all_tasks}

YOUR TASK:
1. Map the impact chain:
   - Identify tasks DIRECTLY affected by this decision
   - Identify tasks INDIRECTLY affected (cascade effects)
   - Calculate chain depth (how many levels of impact)
2. Find unexpected impacts:
   - Which tasks were affected but NOT anticipated?
   - Compare anticipated vs actual impacts
   - Assess severity of unexpected impacts
3. Evaluate prediction accuracy:
   - Were the anticipated impacts accurate?
   - What was missed in the original impact assessment?
4. Provide actionable recommendations

OUTPUT FORMAT:
Return ONLY valid JSON, no additional text before or after.
Do not include explanations, markdown formatting, or any other content
outside the JSON structure.

{{
  "impact_chains": [
    {{
      "decision_id": "decision ID",
      "decision_summary": "brief summary of decision",
      "direct_impacts": ["task-id-1", "task-id-2"],
      "indirect_impacts": ["task-id-3", "task-id-4"],
      "depth": 2,
      "citation": "decision dec_uuid at timestamp, tasks task-id-1, task-id-2"
    }}
  ],
  "unexpected_impacts": [
    {{
      "decision_id": "decision ID",
      "decision_summary": "brief summary",
      "affected_task_id": "task-id",
      "affected_task_name": "task name",
      "anticipated": false,
      "actual_impact": "description of what actually happened",
      "severity": "critical|major|minor",
      "citation": "task task-id, decision dec_uuid"
    }}
  ],
  "recommendations": ["action 1", "action 2"]
}}

IMPORTANT: Return ONLY the JSON object above. Do not add explanations
or commentary.
Cite all claims with decision IDs, task IDs, and timestamps."""

    def format_tasks(self, tasks: list[dict[str, Any]]) -> str:
        """
        Format tasks for LLM prompt.

        Parameters
        ----------
        tasks : list[dict]
            Tasks to format

        Returns
        -------
        str
            Formatted task text for prompt
        """
        if not tasks:
            return "No tasks provided"

        formatted = []
        for task in tasks:
            task_id = task.get("task_id", "unknown")
            name = task.get("name", "unnamed")
            status = task.get("status", "unknown")
            formatted.append(f"Task {task_id}: {name} (status: {status})")

        return "\n".join(formatted)

    def format_decisions(self, decisions: list[Decision]) -> str:
        """
        Format decisions for LLM prompt.

        Parameters
        ----------
        decisions : list[Decision]
            Decisions to format

        Returns
        -------
        str
            Formatted decision text for prompt
        """
        if not decisions:
            return "No related decisions"

        formatted = []
        for d in decisions:
            formatted.append(
                f"""Decision {d.decision_id}:
  What: {d.what}
  Why: {d.why}
  Impact: {d.impact}
  Timestamp: {d.timestamp.isoformat()}
  Affected: {', '.join(d.affected_tasks) if d.affected_tasks else 'none specified'}"""
            )

        return "\n\n".join(formatted)
