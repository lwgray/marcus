"""
Failure Diagnosis Generator for Phase 2 analysis.

Generates comprehensive diagnoses for failed tasks, explaining:
- Root causes (technical, requirements, process, etc.)
- Contributing factors
- Prevention strategies
- Lessons learned

Usage
-----
```python
generator = FailureDiagnosisGenerator()

# Analyze a failed task
diagnosis = await generator.generate_diagnosis(
    task=failed_task,
    error_logs=error_logs,
    related_decisions=decisions,
    context_notes=notes,
)

for cause in diagnosis.failure_causes:
    print(f"Root cause: {cause.root_cause}")
    print(f"Category: {cause.category}")

for strategy in diagnosis.prevention_strategies:
    print(f"Prevention: {strategy.strategy}")
    print(f"Priority: {strategy.priority}")
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
from src.core.project_history import Decision

logger = logging.getLogger(__name__)


@dataclass
class FailureCause:
    """
    A specific cause of task failure.

    Represents one root cause with contributing factors,
    evidence, and categorization.
    """

    category: str  # "technical", "requirements", "process", "communication"
    root_cause: str  # What fundamentally went wrong
    contributing_factors: list[str]  # Additional factors that contributed
    evidence: str  # Evidence from logs, decisions, etc.
    citation: str  # Evidence citation


@dataclass
class PreventionStrategy:
    """
    A strategy to prevent similar failures in the future.

    Represents an actionable recommendation with rationale,
    effort estimate, and priority.
    """

    strategy: str  # What to do differently
    rationale: str  # Why this would help
    effort: str  # "low", "medium", "high"
    priority: str  # "low", "medium", "high"


@dataclass
class FailureDiagnosis:
    """
    Complete diagnosis of a failed task.

    Pairs LLM interpretation with raw data for transparency.
    """

    task_id: str
    failure_causes: list[FailureCause]
    prevention_strategies: list[PreventionStrategy]
    raw_data: dict[str, Any]  # Raw input data
    llm_interpretation: str  # Full LLM response
    lessons_learned: list[str]  # Key takeaways


class FailureDiagnosisGenerator:
    """
    Analyzer that generates comprehensive diagnoses for failed tasks.

    Uses LLM to analyze failure causes, contributing factors,
    and prevention strategies based on task history, error logs,
    and related decisions.
    """

    def __init__(self, ai_engine: Optional[AnalysisAIEngine] = None):
        """
        Initialize Failure Diagnosis Generator.

        Parameters
        ----------
        ai_engine : AnalysisAIEngine, optional
            AI engine for LLM calls. Creates default if not provided.
        """
        self.ai_engine = ai_engine or AnalysisAIEngine()
        logger.info("Failure Diagnosis Generator initialized")

    async def generate_diagnosis(
        self,
        task: TaskHistory,
        error_logs: list[str],
        related_decisions: list[Decision],
        context_notes: list[str],
        progress_callback: Optional[ProgressCallback] = None,
    ) -> FailureDiagnosis:
        """
        Generate comprehensive diagnosis for a failed task.

        Parameters
        ----------
        task : TaskHistory
            The failed task to diagnose
        error_logs : list[str]
            Error messages and logs from the failure
        related_decisions : list[Decision]
            Decisions that may have contributed to the failure
        context_notes : list[str]
            Additional context about the failure
        progress_callback : ProgressCallback, optional
            Callback for progress updates

        Returns
        -------
        FailureDiagnosis
            Complete diagnosis with causes and prevention strategies

        Examples
        --------
        >>> generator = FailureDiagnosisGenerator()
        >>> diagnosis = await generator.generate_diagnosis(
        ...     task=failed_task,
        ...     error_logs=["ERROR: Connection timeout"],
        ...     related_decisions=[],
        ...     context_notes=["Deployed during peak traffic"],
        ... )
        >>> print(f"Found {len(diagnosis.failure_causes)} root causes")
        """
        # Build context for LLM
        context_data = {
            "task_id": task.task_id,
            "task_name": task.name,
            "task_description": task.description,
            "task_status": task.status,
            "estimated_hours": task.estimated_hours,
            "actual_hours": task.actual_hours,
            "error_logs": self.format_error_logs(error_logs),
            "related_decisions": self.format_decisions(related_decisions),
            "context_notes": self.format_context_notes(context_notes),
        }

        # Create analysis request
        request = AnalysisRequest(
            analysis_type=AnalysisType.FAILURE_DIAGNOSIS,
            project_id="",
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

        # Parse failure causes
        failure_causes = [
            FailureCause(**cause)
            for cause in response.parsed_result.get("failure_causes", [])
        ]

        # Parse prevention strategies
        prevention_strategies = [
            PreventionStrategy(**strategy)
            for strategy in response.parsed_result.get("prevention_strategies", [])
        ]

        # Build raw data record
        raw_data = {
            "task_name": task.name,
            "task_description": task.description,
            "estimated_hours": task.estimated_hours,
            "actual_hours": task.actual_hours,
            "error_logs_count": len(error_logs),
            "related_decisions_count": len(related_decisions),
            "context_notes_count": len(context_notes),
        }

        # Create diagnosis result
        diagnosis = FailureDiagnosis(
            task_id=task.task_id,
            failure_causes=failure_causes,
            prevention_strategies=prevention_strategies,
            raw_data=raw_data,
            llm_interpretation=response.raw_response,
            lessons_learned=response.parsed_result.get("lessons_learned", []),
        )

        logger.info(
            f"Failure diagnosis complete for {task.task_id}: "
            f"causes={len(diagnosis.failure_causes)}, "
            f"strategies={len(diagnosis.prevention_strategies)}, "
            f"lessons={len(diagnosis.lessons_learned)}"
        )

        return diagnosis

    def build_prompt_template(self) -> str:
        """
        Build prompt template for failure diagnosis.

        Returns
        -------
        str
            Prompt template with placeholders for context data

        Notes
        -----
        Template emphasizes root cause analysis and prevention strategies.
        """
        return r"""You are diagnosing why a software task failed.

FAILED TASK:
Name: {task_name}
Description: {task_description}
Status: {task_status}

TIME METRICS:
Estimated: {estimated_hours}h
Actual: {actual_hours}h

ERROR LOGS:
{error_logs}

RELATED DECISIONS:
{related_decisions}

ADDITIONAL CONTEXT:
{context_notes}

YOUR TASK:
1. Identify root causes:
   - Categorize each cause (technical, requirements, process, communication)
   - Distinguish root causes from contributing factors
   - Provide specific evidence for each cause
   - Cite sources (task IDs, log lines, decision IDs)

2. Trace contributing factors:
   - What made the situation worse?
   - What conditions enabled the failure?
   - Were there warning signs that were missed?

3. Develop prevention strategies:
   - How to prevent similar failures?
   - What's the effort required (low/medium/high)?
   - What's the priority (low/medium/high)?
   - Provide clear rationale for each strategy

4. Extract lessons learned:
   - What are the key takeaways?
   - What patterns emerge?
   - What should be done differently?

OUTPUT FORMAT:
Return ONLY valid JSON, no additional text before or after.
Do not include explanations, markdown formatting, or any other content
outside the JSON structure.

{{
  "failure_causes": [
    {{
      "category": "technical|requirements|process|communication",
      "root_cause": "fundamental cause of failure",
      "contributing_factors": ["factor 1", "factor 2"],
      "evidence": "specific evidence from logs/decisions",
      "citation": "task task-id, log line X, decision dec-id"
    }}
  ],
  "prevention_strategies": [
    {{
      "strategy": "specific action to take",
      "rationale": "why this would prevent similar failures",
      "effort": "low|medium|high",
      "priority": "low|medium|high"
    }}
  ],
  "lessons_learned": [
    "lesson 1",
    "lesson 2"
  ]
}}

IMPORTANT: Return ONLY the JSON object above. Do not add explanations
or commentary.
Cite all claims with task IDs, decision IDs, log line numbers, and timestamps."""

    def format_error_logs(self, logs: list[str]) -> str:
        """
        Format error logs for LLM prompt.

        Parameters
        ----------
        logs : list[str]
            Error log messages

        Returns
        -------
        str
            Formatted error log text
        """
        if not logs:
            return "No error logs available"

        return "\n".join(f"- {log}" for log in logs)

    def format_decisions(self, decisions: list[Decision]) -> str:
        """
        Format related decisions for LLM prompt.

        Parameters
        ----------
        decisions : list[Decision]
            Related decisions

        Returns
        -------
        str
            Formatted decision text
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
  Confidence: {d.confidence}
  Timestamp: {d.timestamp.isoformat()}"""
            )

        return "\n\n".join(formatted)

    def format_context_notes(self, notes: list[str]) -> str:
        """
        Format context notes for LLM prompt.

        Parameters
        ----------
        notes : list[str]
            Context notes

        Returns
        -------
        str
            Formatted context text
        """
        if not notes:
            return "No additional context"

        return "\n".join(f"- {note}" for note in notes)
