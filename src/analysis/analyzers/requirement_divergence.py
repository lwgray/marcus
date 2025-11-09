"""
Requirement Divergence Analyzer for Phase 2.

Determines if implementation matches original requirements semantically, with
citations and fidelity scoring. Always pairs raw data with LLM interpretation.

Usage
-----
```python
analyzer = RequirementDivergenceAnalyzer()

analysis = await analyzer.analyze_task(
    task=task_history,
    decisions=decisions_for_task,
    artifacts=artifacts_for_task,
)

print(f"Fidelity Score: {analysis.fidelity_score}")
for div in analysis.divergences:
    print(f"  - {div.severity}: {div.requirement} vs {div.implementation}")
```
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional

from src.analysis.aggregator import TaskHistory
from src.analysis.ai_engine import (
    AnalysisAIEngine,
    AnalysisRequest,
    AnalysisType,
)
from src.analysis.helpers.progress import ProgressCallback
from src.core.project_history import ArtifactMetadata, Decision

logger = logging.getLogger(__name__)


@dataclass
class Divergence:
    """
    A specific divergence from requirements.

    Attributes
    ----------
    requirement : str
        What was required (exact quote from task description)
    implementation : str
        What was actually implemented (exact quote with line reference)
    severity : str
        "critical" (changes core functionality), "major" (changes behavior
        significantly), or "minor" (cosmetic/optimization)
    citation : str
        Line/section reference with decision IDs and timestamps
    impact : str
        How this affects functionality
    """

    requirement: str
    implementation: str
    severity: str
    citation: str
    impact: str


@dataclass
class RequirementDivergenceAnalysis:
    """
    Analysis of how implementation diverged from requirements.

    Attributes
    ----------
    task_id : str
        Task that was analyzed
    fidelity_score : float
        0.0 (complete divergence) to 1.0 (perfect match)
    divergences : list[Divergence]
        Specific divergences detected
    raw_data : dict
        Raw data analyzed (task description, artifacts, decisions, outcome)
    llm_interpretation : str
        LLM's analysis and reasoning
    recommendations : list[str]
        Actionable recommendations
    """

    task_id: str
    fidelity_score: float
    divergences: list[Divergence]
    raw_data: dict[str, Any]
    llm_interpretation: str
    recommendations: list[str]


class RequirementDivergenceAnalyzer:
    """
    Analyzer for requirement-implementation divergence.

    Uses LLM to determine if implementations match original requirements
    semantically, with citations and fidelity scoring.

    Parameters
    ----------
    ai_engine : Optional[AnalysisAIEngine]
        AI engine for LLM calls (creates default if None)

    Examples
    --------
    ```python
    analyzer = RequirementDivergenceAnalyzer()

    # Analyze single task
    analysis = await analyzer.analyze_task(
        task=task_history,
        decisions=task_decisions,
        artifacts=task_artifacts,
    )

    if analysis.fidelity_score < 0.7:
        print("ALERT: Significant divergence detected!")
        for div in analysis.divergences:
            if div.severity == "critical":
                print(f"  CRITICAL: {div.impact}")
    ```
    """

    def __init__(self, ai_engine: Optional[AnalysisAIEngine] = None):
        """
        Initialize analyzer.

        Parameters
        ----------
        ai_engine : Optional[AnalysisAIEngine]
            AI engine to use (creates default if None)
        """
        self.ai_engine = ai_engine or AnalysisAIEngine()
        logger.info("Requirement Divergence Analyzer initialized")

    async def analyze_task(
        self,
        task: TaskHistory,
        decisions: list[Decision],
        artifacts: list[ArtifactMetadata],
        progress_callback: Optional[ProgressCallback] = None,
    ) -> RequirementDivergenceAnalysis:
        """
        Analyze requirement-implementation divergence for a task.

        Parameters
        ----------
        task : TaskHistory
            Task to analyze
        decisions : list[Decision]
            Architectural decisions made during task execution
        artifacts : list[ArtifactMetadata]
            Implementation artifacts (code, designs, specs)
        progress_callback : Optional[ProgressCallback]
            Callback for progress updates

        Returns
        -------
        RequirementDivergenceAnalysis
            Complete analysis with fidelity score and divergences

        Examples
        --------
        ```python
        analyzer = RequirementDivergenceAnalyzer()

        analysis = await analyzer.analyze_task(
            task=task_history,
            decisions=task_decisions,
            artifacts=task_artifacts,
        )

        print(f"Fidelity: {analysis.fidelity_score:.2%}")
        for rec in analysis.recommendations:
            print(f"  - {rec}")
        ```
        """
        logger.debug(f"Analyzing requirement divergence for task {task.task_id}")

        # Build context data
        context_data = {
            "task_description": task.description or "",
            "task_name": task.name,
            "task_status": task.status,
            "estimated_hours": task.estimated_hours,
            "actual_hours": task.actual_hours,
            "decisions": self.format_decisions(decisions),
            "artifacts": self.format_artifacts(artifacts),
        }

        # Create analysis request
        request = AnalysisRequest(
            analysis_type=AnalysisType.REQUIREMENT_DIVERGENCE,
            project_id="",  # Will be set by orchestrator
            task_id=task.task_id,
            context_data=context_data,
            prompt_template=self.build_prompt_template(),
        )

        # Execute analysis
        response = await self.ai_engine.analyze(
            request,
            progress_callback=progress_callback,
            use_cache=True,
        )

        # Parse divergences
        divergences = [
            Divergence(**d) for d in response.parsed_result.get("divergences", [])
        ]

        # Build raw data record
        raw_data = {
            "task_description": task.description,
            "task_name": task.name,
            "task_status": task.status,
            "estimated_hours": task.estimated_hours,
            "actual_hours": task.actual_hours,
            "decisions": [self._decision_to_dict(d) for d in decisions],
            "artifacts": [self._artifact_to_dict(a) for a in artifacts],
        }

        # Create analysis result
        analysis = RequirementDivergenceAnalysis(
            task_id=task.task_id,
            fidelity_score=float(response.parsed_result.get("fidelity_score", 0.0)),
            divergences=divergences,
            raw_data=raw_data,
            llm_interpretation=response.raw_response,
            recommendations=response.parsed_result.get("recommendations", []),
        )

        logger.info(
            f"Requirement divergence analysis complete for {task.task_id}: "
            f"fidelity={analysis.fidelity_score:.2f}, "
            f"divergences={len(analysis.divergences)}"
        )

        return analysis

    def build_prompt_template(self) -> str:
        """
        Build prompt template for requirement divergence analysis.

        Returns
        -------
        str
            Prompt template with placeholders for context data

        Notes
        -----
        Template emphasizes citations and pairs raw data with interpretation.
        """
        return """You are analyzing whether a software implementation matches
its original requirements.

ORIGINAL REQUIREMENT:
Task: {task_name}
Description: {task_description}

IMPLEMENTATION DETAILS:
Task Status: {task_status}
Time: {actual_hours}h (estimated {estimated_hours}h)

ARCHITECTURAL DECISIONS MADE:
{decisions}

IMPLEMENTATION ARTIFACTS:
{artifacts}

YOUR TASK:
1. Identify any divergences between requirement and implementation
2. For each divergence:
   - Quote the specific requirement text
   - Quote the specific implementation code/design with line reference
   - Assess severity: critical (changes core functionality),
     major (changes behavior significantly),
     minor (cosmetic/optimization)
   - Cite line numbers, decision IDs, timestamps
   - Explain impact on functionality
3. Calculate fidelity score (0.0 = complete divergence, 1.0 = perfect match)
4. Provide actionable recommendations

OUTPUT FORMAT:
Return ONLY valid JSON, no additional text before or after.
Do not include explanations, markdown formatting, or any other content
outside the JSON structure.

{{
  "fidelity_score": 0.0-1.0,
  "divergences": [
    {{
      "requirement": "exact quote",
      "implementation": "exact quote with line ref",
      "severity": "critical|major|minor",
      "citation": "line X, decision dec_uuid_Y at timestamp Z",
      "impact": "description"
    }}
  ],
  "recommendations": ["action 1", "action 2"]
}}

IMPORTANT: Return ONLY the JSON object above. Do not add explanations or commentary."""

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
            return "No architectural decisions recorded"

        formatted = []
        for d in decisions:
            formatted.append(
                f"""Decision {d.decision_id}:
  What: {d.what}
  Why: {d.why}
  Impact: {d.impact}
  Confidence: {d.confidence}
  Timestamp: {d.timestamp.isoformat()}
  Logged by: {d.agent_id}"""
            )

        return "\n\n".join(formatted)

    def format_artifacts(self, artifacts: list[ArtifactMetadata]) -> str:
        """
        Format artifacts for LLM prompt.

        Parameters
        ----------
        artifacts : list[ArtifactMetadata]
            Artifacts to format

        Returns
        -------
        str
            Formatted artifact text for prompt
        """
        if not artifacts:
            return "No implementation artifacts found"

        formatted = []
        for a in artifacts:
            formatted.append(
                f"""Artifact {a.artifact_id}:
  Type: {a.artifact_type}
  File: {a.relative_path}
  Description: {a.description}
  Size: {a.file_size_bytes} bytes
  Timestamp: {a.timestamp.isoformat()}"""
            )

        return "\n\n".join(formatted)

    def _decision_to_dict(self, decision: Decision) -> dict[str, Any]:
        """Convert Decision to dictionary for raw data storage."""
        return {
            "decision_id": decision.decision_id,
            "what": decision.what,
            "why": decision.why,
            "impact": decision.impact,
            "confidence": decision.confidence,
            "timestamp": decision.timestamp.isoformat(),
            "agent_id": decision.agent_id,
            "affected_tasks": decision.affected_tasks,
        }

    def _artifact_to_dict(self, artifact: ArtifactMetadata) -> dict[str, Any]:
        """Convert ArtifactMetadata to dictionary for raw data storage."""
        return {
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type,
            "filename": artifact.filename,
            "relative_path": artifact.relative_path,
            "description": artifact.description,
            "file_size_bytes": artifact.file_size_bytes,
            "timestamp": artifact.timestamp.isoformat(),
            "agent_id": artifact.agent_id,
        }
