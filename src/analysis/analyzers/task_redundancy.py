"""
Task Redundancy Analyzer for Phase 2.

Detects redundant and duplicate work between tasks, including:
- Multiple tasks accomplishing the same goal
- Tasks assigned when work already completed
- Over-decomposition from Enterprise mode
- Quick completions (< 30 seconds - likely already done)

Usage
-----
```python
analyzer = TaskRedundancyAnalyzer()

analysis = await analyzer.analyze_project(
    tasks=task_histories,
    conversations=conversation_messages,
)

print(f"Redundancy Score: {analysis.redundancy_score}")
for pair in analysis.redundant_pairs:
    print(f"  - {pair.task_1_name} overlaps {pair.task_2_name}")
    print(f"    Evidence: {pair.evidence}")
```
"""

import logging
from dataclasses import dataclass, field
from datetime import timedelta, timezone
from typing import Any, Optional

from src.analysis.aggregator import Message, TaskHistory
from src.analysis.ai_engine import (
    AnalysisAIEngine,
    AnalysisRequest,
    AnalysisType,
)
from src.analysis.helpers.progress import ProgressCallback

logger = logging.getLogger(__name__)


@dataclass
class RedundantTaskPair:
    """
    Pair of tasks doing redundant work.

    Attributes
    ----------
    task_1_id : str
        ID of first task in redundant pair
    task_1_name : str
        Name of first task
    task_2_id : str
        ID of second task in redundant pair
    task_2_name : str
        Name of second task
    overlap_score : float
        How much they overlap (0.0-1.0, where 1.0 is complete overlap)
    evidence : str
        Why they're redundant with citations (task_id, timestamps)
    time_wasted : float
        Hours wasted on redundant work
    """

    task_1_id: str
    task_1_name: str
    task_2_id: str
    task_2_name: str
    overlap_score: float
    evidence: str
    time_wasted: float


@dataclass
class TaskRedundancyAnalysis:
    """
    Analysis of redundant/duplicate work in project.

    Attributes
    ----------
    project_id : str
        Project being analyzed
    redundant_pairs : list[RedundantTaskPair]
        Pairs of tasks doing redundant work
    redundancy_score : float
        Overall redundancy (0.0-1.0, where 1.0 is all tasks redundant)
    total_time_wasted : float
        Total hours wasted on redundant work
    over_decomposition_detected : bool
        Whether Enterprise mode created unnecessary task breakdowns
    recommended_complexity : str
        Recommended complexity mode: "prototype", "standard", or "enterprise"
    raw_data : dict[str, Any]
        Raw data analyzed (tasks, quick completions, etc.)
    llm_interpretation : str
        LLM's analysis and reasoning
    recommendations : list[str]
        Actionable recommendations to reduce redundancy
    """

    project_id: str
    redundant_pairs: list[RedundantTaskPair]
    redundancy_score: float
    total_time_wasted: float
    over_decomposition_detected: bool
    recommended_complexity: str
    raw_data: dict[str, Any]
    llm_interpretation: str
    recommendations: list[str] = field(default_factory=list)


class TaskRedundancyAnalyzer:
    """
    Analyzer for detecting redundant and duplicate work between tasks.

    Detects when:
    - Multiple tasks accomplish the same goal
    - Tasks are assigned for work already completed
    - Enterprise mode creates unnecessary task breakdowns
    - Tasks complete too quickly (< 30 seconds - likely already done)

    Parameters
    ----------
    ai_engine : Optional[AnalysisAIEngine]
        AI engine for LLM calls (creates default if None)
    quick_completion_threshold : float
        Threshold in seconds for "quick" completion (default: 30.0)

    Examples
    --------
    ```python
    analyzer = TaskRedundancyAnalyzer()

    # Analyze entire project
    analysis = await analyzer.analyze_project(
        tasks=task_histories,
        conversations=conversation_messages,
    )

    if analysis.redundancy_score > 0.3:
        print("WARNING: High redundancy detected!")
        for rec in analysis.recommendations:
            print(f"  - {rec}")
    ```
    """

    def __init__(
        self,
        ai_engine: Optional[AnalysisAIEngine] = None,
        quick_completion_threshold: float = 30.0,
    ):
        """
        Initialize analyzer.

        Parameters
        ----------
        ai_engine : Optional[AnalysisAIEngine]
            AI engine to use (creates default if None)
        quick_completion_threshold : float
            Threshold in seconds for "quick" completion (default: 30.0)
        """
        self.ai_engine = ai_engine or AnalysisAIEngine()
        self.quick_completion_threshold = quick_completion_threshold
        logger.info("Task Redundancy Analyzer initialized")

    async def analyze_project(
        self,
        tasks: list[TaskHistory],
        conversations: list[Message],
        progress_callback: Optional[ProgressCallback] = None,
    ) -> TaskRedundancyAnalysis:
        """
        Analyze entire project for redundant work.

        Parameters
        ----------
        tasks : list[TaskHistory]
            All tasks in the project
        conversations : list[Message]
            Conversation history (to find evidence of already-completed work)
        progress_callback : Optional[ProgressCallback]
            Callback for progress updates

        Returns
        -------
        TaskRedundancyAnalysis
            Analysis results with redundancy score and recommendations

        Examples
        --------
        ```python
        analyzer = TaskRedundancyAnalyzer()

        analysis = await analyzer.analyze_project(
            tasks=project_history.tasks,
            conversations=project_history.timeline,
        )

        print(f"Redundancy: {analysis.redundancy_score:.2%}")
        print(f"Time wasted: {analysis.total_time_wasted:.1f} hours")
        print(f"Recommended: {analysis.recommended_complexity} mode")
        ```
        """
        logger.debug(f"Analyzing redundancy for {len(tasks)} tasks")

        # Find quick completions
        quick_completions = self._find_quick_completions(tasks)

        # Build context data for LLM
        context_data = {
            "total_tasks": len(tasks),
            "quick_completions": len(quick_completions),
            "quick_completion_details": self._format_quick_completions(
                quick_completions
            ),
            "task_summaries": self._format_task_summaries(tasks),
            "conversation_excerpts": self._format_conversations(conversations),
        }

        # Create analysis request
        request = AnalysisRequest(
            analysis_type=AnalysisType.TASK_REDUNDANCY,
            project_id="",  # Will be set by orchestrator
            task_id=None,  # Project-level analysis
            context_data=context_data,
            prompt_template=self.build_prompt_template(),
        )

        # Execute analysis
        response = await self.ai_engine.analyze(
            request,
            progress_callback=progress_callback,
            use_cache=True,
        )

        # Parse redundant pairs
        redundant_pairs = [
            RedundantTaskPair(**pair)
            for pair in response.parsed_result.get("redundant_pairs", [])
        ]

        # Calculate total time wasted
        total_time_wasted = sum(pair.time_wasted for pair in redundant_pairs)

        # Determine if over-decomposition detected
        over_decomposition = (
            len(quick_completions) > len(tasks) * 0.3
            or len(redundant_pairs) > len(tasks) * 0.2
        )

        # Recommend complexity level
        redundancy_score = float(response.parsed_result.get("redundancy_score", 0.0))
        recommended_complexity = self._recommend_complexity(
            tasks, redundancy_score, quick_completions
        )

        # Build raw data record
        raw_data = {
            "total_tasks": len(tasks),
            "quick_completions_count": len(quick_completions),
            "quick_completions": [
                {
                    "task_id": t.task_id,
                    "name": t.name,
                    "actual_hours": t.actual_hours,
                    "estimated_hours": t.estimated_hours,
                }
                for t in quick_completions
            ],
            "task_summaries": [
                {
                    "task_id": t.task_id,
                    "name": t.name,
                    "description": t.description[:200] if t.description else "",
                    "status": t.status,
                    "actual_hours": t.actual_hours,
                    "estimated_hours": t.estimated_hours,
                }
                for t in tasks
            ],
        }

        # Create analysis result
        analysis = TaskRedundancyAnalysis(
            project_id=response.parsed_result.get("project_id", ""),
            redundant_pairs=redundant_pairs,
            redundancy_score=redundancy_score,
            total_time_wasted=total_time_wasted,
            over_decomposition_detected=over_decomposition,
            recommended_complexity=recommended_complexity,
            raw_data=raw_data,
            llm_interpretation=response.raw_response,
            recommendations=response.parsed_result.get("recommendations", []),
        )

        logger.info(
            f"Task redundancy analysis complete: "
            f"redundancy={analysis.redundancy_score:.2f}, "
            f"redundant_pairs={len(analysis.redundant_pairs)}, "
            f"time_wasted={analysis.total_time_wasted:.1f}h"
        )

        return analysis

    def _find_quick_completions(self, tasks: list[TaskHistory]) -> list[TaskHistory]:
        """
        Find tasks that completed in less than threshold.

        Quick completions likely indicate work was already done.

        Parameters
        ----------
        tasks : list[TaskHistory]
            All tasks to analyze

        Returns
        -------
        list[TaskHistory]
            Tasks that completed quickly
        """
        quick_tasks = []

        for task in tasks:
            # Calculate actual duration
            if task.started_at and task.completed_at:
                duration = task.completed_at - task.started_at
                duration_seconds = duration.total_seconds()

                if duration_seconds < self.quick_completion_threshold:
                    quick_tasks.append(task)
            elif task.actual_hours > 0:
                # Use actual_hours if timestamps not available
                duration_seconds = task.actual_hours * 3600
                if duration_seconds < self.quick_completion_threshold:
                    quick_tasks.append(task)

        logger.debug(
            f"Found {len(quick_tasks)} quick completions "
            f"(< {self.quick_completion_threshold}s)"
        )
        return quick_tasks

    def _recommend_complexity(
        self,
        tasks: list[TaskHistory],
        redundancy_score: float,
        quick_completions: list[TaskHistory],
    ) -> str:
        """
        Recommend appropriate complexity level.

        Parameters
        ----------
        tasks : list[TaskHistory]
            All tasks
        redundancy_score : float
            Overall redundancy score
        quick_completions : list[TaskHistory]
            Tasks that completed quickly

        Returns
        -------
        str
            Recommended complexity: "prototype", "standard", or "enterprise"
        """
        quick_completion_rate = len(quick_completions) / len(tasks) if tasks else 0.0

        # High redundancy or quick completions suggest over-decomposition
        if redundancy_score > 0.4 or quick_completion_rate > 0.4:
            return "prototype"
        elif redundancy_score > 0.2 or quick_completion_rate > 0.2:
            return "standard"
        else:
            return "enterprise"

    def build_prompt_template(self) -> str:
        """
        Build prompt template for task redundancy analysis.

        Returns
        -------
        str
            Prompt template with placeholders for context data

        Notes
        -----
        Template emphasizes detecting duplicate work and over-decomposition.
        """
        return """You are analyzing a software project for redundant
and duplicate work between tasks.

PROJECT OVERVIEW:
Total Tasks: {total_tasks}
Quick Completions: {quick_completions} tasks finished in < 30 seconds

QUICK COMPLETION DETAILS:
{quick_completion_details}

TASK SUMMARIES:
{task_summaries}

CONVERSATION EXCERPTS (Evidence of Already-Completed Work):
{conversation_excerpts}

YOUR TASK:
1. Identify redundant task pairs:
   - Tasks with overlapping goals/deliverables
   - Tasks assigned when work already completed
   - Tasks that duplicate previous work
2. For each redundant pair:
   - Calculate overlap score (0.0-1.0)
   - Provide evidence with citations (task_id, timestamps)
   - Estimate time wasted
3. Calculate overall redundancy score (0.0-1.0):
   - 0.0 = no redundancy detected
   - 1.0 = all tasks redundant
4. Detect over-decomposition:
   - Enterprise mode breaking down simple work unnecessarily
   - Task breakdowns where 1 task would suffice
5. Provide actionable recommendations

OUTPUT FORMAT:
Return ONLY valid JSON, no additional text before or after.
Do not include explanations, markdown formatting, or any other content
outside the JSON structure.

{{
  "redundancy_score": 0.0-1.0,
  "redundant_pairs": [
    {{
      "task_1_id": "task_id",
      "task_1_name": "task name",
      "task_2_id": "task_id",
      "task_2_name": "task name",
      "overlap_score": 0.0-1.0,
      "evidence": "citation with task_id, timestamps",
      "time_wasted": 0.0
    }}
  ],
  "recommendations": [
    "Merge tasks X and Y",
    "Use prototype mode instead of enterprise",
    "Task Z was already completed when assigned"
  ]
}}

IMPORTANT: Return ONLY the JSON object above. Do not add explanations
or commentary."""

    def _format_quick_completions(self, quick_tasks: list[TaskHistory]) -> str:
        """
        Format quick completions for LLM prompt.

        Parameters
        ----------
        quick_tasks : list[TaskHistory]
            Tasks that completed quickly

        Returns
        -------
        str
            Formatted text for prompt
        """
        if not quick_tasks:
            return "No quick completions detected"

        formatted = []
        for task in quick_tasks:
            duration = ""
            if task.started_at and task.completed_at:
                delta = task.completed_at - task.started_at
                duration = f"{delta.total_seconds():.1f}s"
            else:
                duration = f"{task.actual_hours * 3600:.1f}s"

            formatted.append(
                f"""Task {task.task_id}:
  Name: {task.name}
  Duration: {duration}
  Estimated: {task.estimated_hours}h
  Status: {task.status}
  Description: {task.description[:150] if task.description else 'N/A'}"""
            )

        return "\n\n".join(formatted)

    def _format_task_summaries(self, tasks: list[TaskHistory]) -> str:
        """
        Format task summaries for LLM prompt.

        Parameters
        ----------
        tasks : list[TaskHistory]
            All tasks to format

        Returns
        -------
        str
            Formatted text for prompt
        """
        if not tasks:
            return "No tasks found"

        formatted = []
        for task in tasks:
            formatted.append(
                f"""Task {task.task_id}:
  Name: {task.name}
  Status: {task.status}
  Time: {task.actual_hours}h (estimated {task.estimated_hours}h)
  Description: {task.description[:200] if task.description else 'N/A'}"""
            )

        return "\n\n".join(formatted)

    def _format_conversations(self, conversations: list[Message]) -> str:
        """
        Format conversation excerpts for LLM prompt.

        Parameters
        ----------
        conversations : list[Message]
            Conversation messages

        Returns
        -------
        str
            Formatted text for prompt
        """
        if not conversations:
            return "No conversations available"

        # Limit to most relevant conversations
        # Focus on messages mentioning "already", "completed", "done", etc.
        relevant_keywords = [
            "already",
            "completed",
            "done",
            "finished",
            "duplicate",
            "redundant",
        ]

        relevant_convos = [
            msg
            for msg in conversations
            if any(kw in msg.content.lower() for kw in relevant_keywords)
        ]

        # Limit to 20 most recent relevant messages
        relevant_convos = sorted(
            relevant_convos, key=lambda m: m.timestamp, reverse=True
        )[:20]

        if not relevant_convos:
            return "No relevant conversation excerpts found"

        formatted = []
        for msg in relevant_convos:
            formatted.append(
                f"""[{msg.timestamp.isoformat()}] {msg.direction} "
                f"(agent: {msg.agent_id}):
  {msg.content[:300]}"""
            )

        return "\n\n".join(formatted)
