"""
Instruction Quality Analyzer for Phase 2 analysis.

Evaluates how clear and complete task instructions were, detecting:
- Ambiguous requirements
- Missing specifications
- Incomplete acceptance criteria
- Correlation between instruction quality and task delays

Usage
-----
```python
analyzer = InstructionQualityAnalyzer()

# Analyze a task's instruction quality
analysis = await analyzer.analyze_instruction_quality(
    task=my_task,
    clarifications=questions_asked,
    implementation_notes=dev_notes,
)

print(f"Overall quality: {analysis.quality_scores.overall:.2f}")
for issue in analysis.ambiguity_issues:
    print(f"Ambiguous: {issue.ambiguous_aspect}")
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

logger = logging.getLogger(__name__)


@dataclass
class QualityScore:
    """
    Multi-dimensional quality scores for task instructions.

    Each dimension scored 0.0-1.0 where 1.0 is perfect.
    """

    clarity: float  # How clear/unambiguous the instructions were
    completeness: float  # How complete the specifications were
    specificity: float  # How specific vs vague the requirements were
    overall: float  # Weighted average of all dimensions


@dataclass
class AmbiguityIssue:
    """
    A specific ambiguity found in task instructions.

    Represents unclear or missing information that caused problems.
    """

    task_id: str
    task_name: str
    ambiguous_aspect: str  # What was unclear (e.g., "auth method")
    evidence: str  # Quote from instructions showing ambiguity
    consequence: str  # What happened due to the ambiguity
    severity: str  # "critical", "major", "minor"
    citation: str  # Evidence citation


@dataclass
class InstructionQualityAnalysis:
    """
    Complete analysis of task instruction quality.

    Pairs LLM interpretation with raw data for transparency.
    """

    task_id: str
    quality_scores: QualityScore
    ambiguity_issues: list[AmbiguityIssue]
    raw_data: dict[str, Any]  # Raw input data
    llm_interpretation: str  # Full LLM response
    recommendations: list[str]  # How to improve instructions


class InstructionQualityAnalyzer:
    """
    Analyzer that evaluates task instruction quality.

    Uses LLM to assess clarity, completeness, and specificity,
    correlating instruction quality with task outcomes.
    """

    def __init__(self, ai_engine: Optional[AnalysisAIEngine] = None):
        """
        Initialize Instruction Quality Analyzer.

        Parameters
        ----------
        ai_engine : AnalysisAIEngine, optional
            AI engine for LLM calls. Creates default if not provided.
        """
        self.ai_engine = ai_engine or AnalysisAIEngine()
        logger.info("Instruction Quality Analyzer initialized")

    async def analyze_instruction_quality(
        self,
        task: TaskHistory,
        clarifications: list[dict[str, Any]],
        implementation_notes: list[str],
        progress_callback: Optional[ProgressCallback] = None,
    ) -> InstructionQualityAnalysis:
        """
        Analyze the quality of task instructions.

        Parameters
        ----------
        task : TaskHistory
            The task to analyze
        clarifications : list[dict]
            Questions that had to be asked during implementation
        implementation_notes : list[str]
            Notes from developers about unclear aspects
        progress_callback : ProgressCallback, optional
            Callback for progress updates

        Returns
        -------
        InstructionQualityAnalysis
            Complete analysis of instruction quality

        Examples
        --------
        >>> analyzer = InstructionQualityAnalyzer()
        >>> analysis = await analyzer.analyze_instruction_quality(
        ...     task=my_task,
        ...     clarifications=[],
        ...     implementation_notes=[],
        ... )
        >>> print(f"Clarity: {analysis.quality_scores.clarity:.2f}")
        """
        # Calculate time variance as quality indicator
        time_variance = self.calculate_time_variance(task)

        # Build context for LLM
        context_data = {
            "task_id": task.task_id,
            "task_name": task.name,
            "task_description": task.description,
            "task_status": task.status,
            "estimated_hours": task.estimated_hours,
            "actual_hours": task.actual_hours,
            "time_variance": time_variance,
            "clarifications": self.format_clarifications(clarifications),
            "implementation_notes": self.format_implementation_notes(
                implementation_notes
            ),
        }

        # Create analysis request
        request = AnalysisRequest(
            analysis_type=AnalysisType.INSTRUCTION_QUALITY,
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

        # Parse quality scores
        scores_data = response.parsed_result.get(
            "quality_scores",
            {"clarity": 0.5, "completeness": 0.5, "specificity": 0.5, "overall": 0.5},
        )
        quality_scores = QualityScore(**scores_data)

        # Parse ambiguity issues
        ambiguity_issues = [
            AmbiguityIssue(**issue)
            for issue in response.parsed_result.get("ambiguity_issues", [])
        ]

        # Build raw data record
        raw_data = {
            "task_description": task.description,
            "task_name": task.name,
            "estimated_hours": task.estimated_hours,
            "actual_hours": task.actual_hours,
            "time_variance": time_variance,
            "clarifications_count": len(clarifications),
            "implementation_notes_count": len(implementation_notes),
        }

        # Create analysis result
        analysis = InstructionQualityAnalysis(
            task_id=task.task_id,
            quality_scores=quality_scores,
            ambiguity_issues=ambiguity_issues,
            raw_data=raw_data,
            llm_interpretation=response.raw_response,
            recommendations=response.parsed_result.get("recommendations", []),
        )

        logger.info(
            f"Instruction quality analysis complete for {task.task_id}: "
            f"overall={analysis.quality_scores.overall:.2f}, "
            f"issues={len(analysis.ambiguity_issues)}"
        )

        return analysis

    def calculate_time_variance(self, task: TaskHistory) -> float:
        """
        Calculate ratio of actual to estimated time.

        Large variance suggests possible instruction quality issues.

        Parameters
        ----------
        task : TaskHistory
            Task to calculate variance for

        Returns
        -------
        float
            Ratio of actual/estimated (1.0 = perfect estimate)

        Examples
        --------
        >>> task = TaskHistory(
        ...     estimated_hours=4.0,
        ...     actual_hours=8.0,
        ...     ...
        ... )
        >>> variance = analyzer.calculate_time_variance(task)
        >>> assert variance == 2.0  # Took twice as long
        """
        if task.estimated_hours and task.estimated_hours > 0:
            return task.actual_hours / task.estimated_hours
        return 1.0  # No estimate, assume accurate

    def build_prompt_template(self) -> str:
        """
        Build prompt template for instruction quality analysis.

        Returns
        -------
        str
            Prompt template with placeholders for context data

        Notes
        -----
        Template emphasizes multi-dimensional quality assessment.
        """
        return """You are evaluating the quality of software task instructions.

TASK INSTRUCTIONS:
Name: {task_name}
Description: {task_description}

IMPLEMENTATION METRICS:
Status: {task_status}
Estimated: {estimated_hours}h
Actual: {actual_hours}h
Time Variance: {time_variance}x (1.0 = perfect estimate)

CLARIFICATIONS REQUESTED:
{clarifications}

DEVELOPER NOTES:
{implementation_notes}

YOUR TASK:
1. Assess instruction quality on multiple dimensions (0.0-1.0):
   - Clarity: Were instructions clear and unambiguous?
   - Completeness: Was all necessary information provided?
   - Specificity: Were requirements specific vs vague?
   - Overall: Weighted average

2. Identify ambiguity issues:
   - What aspects were unclear or missing?
   - What evidence shows the ambiguity?
   - What were the consequences?
   - Rate severity

3. Correlate quality with outcomes:
   - Did poor instructions cause delays?
   - Were clarifications needed due to ambiguity?
   - Did developers struggle with vague requirements?

4. Provide specific recommendations for improvement

OUTPUT FORMAT:
Return ONLY valid JSON, no additional text before or after.
Do not include explanations, markdown formatting, or any other content
outside the JSON structure.

{{
  "quality_scores": {{
    "clarity": 0.0-1.0,
    "completeness": 0.0-1.0,
    "specificity": 0.0-1.0,
    "overall": 0.0-1.0
  }},
  "ambiguity_issues": [
    {{
      "task_id": "task ID",
      "task_name": "task name",
      "ambiguous_aspect": "what was unclear",
      "evidence": "quote from instructions showing ambiguity",
      "consequence": "what happened due to unclear instructions",
      "severity": "critical|major|minor",
      "citation": "task task-id, description line X"
    }}
  ],
  "recommendations": ["specific improvement 1", "specific improvement 2"]
}}

IMPORTANT: Return ONLY the JSON object above. Do not add explanations
or commentary.
Cite all claims with task IDs and line references."""

    def format_clarifications(self, clarifications: list[dict[str, Any]]) -> str:
        """
        Format clarifications for LLM prompt.

        Parameters
        ----------
        clarifications : list[dict]
            Clarification questions and answers

        Returns
        -------
        str
            Formatted clarification text
        """
        if not clarifications:
            return "No clarifications were requested"

        formatted = []
        for i, clarif in enumerate(clarifications, 1):
            q = clarif.get("question", "unknown")
            a = clarif.get("answer", "unknown")
            ts = clarif.get("timestamp", "unknown")
            formatted.append(f"{i}. Q: {q}\n   A: {a}\n   Time: {ts}")

        return "\n".join(formatted)

    def format_implementation_notes(self, notes: list[str]) -> str:
        """
        Format implementation notes for LLM prompt.

        Parameters
        ----------
        notes : list[str]
            Developer notes about implementation

        Returns
        -------
        str
            Formatted notes text
        """
        if not notes:
            return "No implementation notes provided"

        return "\n".join(f"- {note}" for note in notes)
