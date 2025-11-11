"""
PostProjectAnalyzer orchestrator for Phase 2 analysis.

Coordinates all Phase 2 analyzers to provide comprehensive post-project
analysis, including:
- Requirement divergence detection
- Decision impact tracing
- Instruction quality evaluation
- Failure diagnosis

Usage
-----
```python
analyzer = PostProjectAnalyzer()

# Run complete analysis
analysis = await analyzer.analyze_project(
    project_id="proj-123",
    tasks=project_tasks,
    decisions=project_decisions,
)

# Access specific results
for divergence in analysis.requirement_divergences:
    print(f"Fidelity: {divergence.fidelity_score}")

for impact in analysis.decision_impacts:
    print(f"Decision {impact.decision_id} had {len(impact.impact_chains)} chains")

# Run selective analysis
scope = AnalysisScope(
    requirement_divergence=True,
    decision_impact=False,
    instruction_quality=True,
    failure_diagnosis=False,
)
analysis = await analyzer.analyze_project(
    project_id="proj-123",
    tasks=tasks,
    decisions=decisions,
    scope=scope,
)
```
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from src.analysis.aggregator import TaskHistory
from src.analysis.analyzers.decision_impact_tracer import (
    DecisionImpactAnalysis,
    DecisionImpactTracer,
)
from src.analysis.analyzers.failure_diagnosis import (
    FailureDiagnosis,
    FailureDiagnosisGenerator,
)
from src.analysis.analyzers.instruction_quality import (
    InstructionQualityAnalysis,
    InstructionQualityAnalyzer,
)
from src.analysis.analyzers.requirement_divergence import (
    RequirementDivergenceAnalysis,
    RequirementDivergenceAnalyzer,
)
from src.analysis.analyzers.task_redundancy import (
    TaskRedundancyAnalysis,
    TaskRedundancyAnalyzer,
)
from src.analysis.helpers.progress import ProgressCallback, ProgressEvent
from src.core.project_history import Decision

logger = logging.getLogger(__name__)


@dataclass
class AnalysisScope:
    """
    Defines which analyzers to run.

    Allows selective analysis when full analysis is not needed.
    """

    requirement_divergence: bool = True
    decision_impact: bool = True
    instruction_quality: bool = True
    failure_diagnosis: bool = True
    task_redundancy: bool = True


@dataclass
class PostProjectAnalysis:
    """
    Complete post-project analysis results.

    Aggregates results from all Phase 2 analyzers into a single
    comprehensive report.
    """

    project_id: str
    analysis_timestamp: datetime
    requirement_divergences: list[RequirementDivergenceAnalysis]
    decision_impacts: list[DecisionImpactAnalysis]
    instruction_quality_issues: list[InstructionQualityAnalysis]
    failure_diagnoses: list[FailureDiagnosis]
    task_redundancy: Optional[TaskRedundancyAnalysis]
    summary: str
    metadata: dict[str, Any] = field(default_factory=dict)


class PostProjectAnalyzer:
    """
    Orchestrator for Phase 2 post-project analysis.

    Coordinates all four Phase 2 analyzers to provide comprehensive
    analysis of what went right and wrong in a completed project.
    """

    def __init__(
        self,
        requirement_analyzer: Optional[RequirementDivergenceAnalyzer] = None,
        decision_tracer: Optional[DecisionImpactTracer] = None,
        instruction_analyzer: Optional[InstructionQualityAnalyzer] = None,
        failure_generator: Optional[FailureDiagnosisGenerator] = None,
        redundancy_analyzer: Optional[TaskRedundancyAnalyzer] = None,
    ):
        """
        Initialize PostProjectAnalyzer.

        Parameters
        ----------
        requirement_analyzer : RequirementDivergenceAnalyzer, optional
            Analyzer for requirement divergence. Creates default if not provided.
        decision_tracer : DecisionImpactTracer, optional
            Tracer for decision impacts. Creates default if not provided.
        instruction_analyzer : InstructionQualityAnalyzer, optional
            Analyzer for instruction quality. Creates default if not provided.
        failure_generator : FailureDiagnosisGenerator, optional
            Generator for failure diagnoses. Creates default if not provided.
        redundancy_analyzer : TaskRedundancyAnalyzer, optional
            Analyzer for task redundancy. Creates default if not provided.
        """
        self.requirement_analyzer = (
            requirement_analyzer or RequirementDivergenceAnalyzer()
        )
        self.decision_tracer = decision_tracer or DecisionImpactTracer()
        self.instruction_analyzer = instruction_analyzer or InstructionQualityAnalyzer()
        self.failure_generator = failure_generator or FailureDiagnosisGenerator()
        self.redundancy_analyzer = redundancy_analyzer or TaskRedundancyAnalyzer()
        logger.info("PostProjectAnalyzer initialized")

    async def analyze_project(
        self,
        project_id: str,
        tasks: list[TaskHistory],
        decisions: list[Decision],
        scope: Optional[AnalysisScope] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> PostProjectAnalysis:
        """
        Run comprehensive post-project analysis.

        Parameters
        ----------
        project_id : str
            Unique identifier for the project
        tasks : list[TaskHistory]
            All tasks from the project
        decisions : list[Decision]
            All decisions made during the project
        scope : AnalysisScope, optional
            Which analyzers to run. Defaults to all analyzers.
        progress_callback : ProgressCallback, optional
            Callback for progress updates

        Returns
        -------
        PostProjectAnalysis
            Complete analysis results from all enabled analyzers

        Examples
        --------
        >>> analyzer = PostProjectAnalyzer()
        >>> analysis = await analyzer.analyze_project(
        ...     project_id="proj-123",
        ...     tasks=project_tasks,
        ...     decisions=project_decisions,
        ... )
        >>> print(f"Found {len(analysis.requirement_divergences)} divergences")
        """
        scope = scope or AnalysisScope()
        analysis_start = datetime.now(timezone.utc)

        logger.info(
            f"Starting post-project analysis for {project_id}: "
            f"{len(tasks)} tasks, {len(decisions)} decisions"
        )

        # Initialize result collections
        requirement_divergences: list[RequirementDivergenceAnalysis] = []
        decision_impacts: list[DecisionImpactAnalysis] = []
        instruction_quality_issues: list[InstructionQualityAnalysis] = []
        failure_diagnoses: list[FailureDiagnosis] = []
        task_redundancy_analysis: Optional[TaskRedundancyAnalysis] = None

        # 1. Analyze requirement divergence for each task
        if scope.requirement_divergence and tasks:
            logger.info("Analyzing requirement divergence...")
            for idx, task in enumerate(tasks):
                if progress_callback:
                    await progress_callback(
                        ProgressEvent(
                            operation="requirement_divergence",
                            current=idx + 1,
                            total=len(tasks),
                            message=f"Analyzing {task.name}",
                            timestamp=datetime.now(timezone.utc),
                        )
                    )

                divergence_analysis = await self.requirement_analyzer.analyze_task(
                    task=task,
                    decisions=self._find_related_decisions(task, decisions),
                    artifacts=[],  # TODO: Extract artifacts from history
                    progress_callback=progress_callback,
                )
                requirement_divergences.append(divergence_analysis)

        # 2. Trace decision impacts
        if scope.decision_impact and decisions:
            logger.info("Tracing decision impacts...")
            for idx, decision in enumerate(decisions):
                if progress_callback:
                    await progress_callback(
                        ProgressEvent(
                            operation="decision_impact",
                            current=idx + 1,
                            total=len(decisions),
                            message=f"Tracing {decision.what}",
                            timestamp=datetime.now(timezone.utc),
                        )
                    )

                # Convert tasks to dict format expected by tracer
                all_tasks_dict = [
                    {
                        "task_id": t.task_id,
                        "name": t.name,
                        "status": t.status,
                    }
                    for t in tasks
                ]

                impact_analysis = await self.decision_tracer.trace_decision_impact(
                    decision=decision,
                    related_decisions=[
                        d for d in decisions if d.decision_id != decision.decision_id
                    ],
                    all_tasks=all_tasks_dict,
                    progress_callback=progress_callback,
                )
                decision_impacts.append(impact_analysis)

        # 3. Analyze instruction quality for each task
        if scope.instruction_quality and tasks:
            logger.info("Analyzing instruction quality...")
            for idx, task in enumerate(tasks):
                if progress_callback:
                    await progress_callback(
                        ProgressEvent(
                            operation="instruction_quality",
                            current=idx + 1,
                            total=len(tasks),
                            message=f"Evaluating {task.name}",
                            timestamp=datetime.now(timezone.utc),
                        )
                    )

                # TODO: Extract clarifications and implementation notes from history
                # For now, pass empty lists
                quality_analysis = (
                    await self.instruction_analyzer.analyze_instruction_quality(
                        task=task,
                        clarifications=[],
                        implementation_notes=[],
                        progress_callback=progress_callback,
                    )
                )
                instruction_quality_issues.append(quality_analysis)

        # 4. Generate failure diagnoses for failed tasks
        if scope.failure_diagnosis and tasks:
            logger.info("Generating failure diagnoses...")
            failed_tasks = [t for t in tasks if t.status == "failed"]
            logger.info(f"Found {len(failed_tasks)} failed tasks")

            for idx, task in enumerate(failed_tasks):
                if progress_callback:
                    await progress_callback(
                        ProgressEvent(
                            operation="failure_diagnosis",
                            current=idx + 1,
                            total=len(failed_tasks),
                            message=f"Diagnosing {task.name}",
                            timestamp=datetime.now(timezone.utc),
                        )
                    )

                # TODO: Extract error logs and context notes from history
                # For now, pass empty lists
                diagnosis = await self.failure_generator.generate_diagnosis(
                    task=task,
                    error_logs=[],
                    related_decisions=self._find_related_decisions(task, decisions),
                    context_notes=[],
                    progress_callback=progress_callback,
                )
                failure_diagnoses.append(diagnosis)

        # 5. Analyze task redundancy across entire project
        if scope.task_redundancy and tasks:
            logger.info("Analyzing task redundancy...")
            if progress_callback:
                await progress_callback(
                    ProgressEvent(
                        operation="task_redundancy",
                        current=0,
                        total=len(tasks),
                        message="Analyzing redundant work patterns",
                        timestamp=datetime.now(timezone.utc),
                    )
                )

            # TODO: Extract conversations from history
            # For now, pass empty list
            task_redundancy_analysis = await self.redundancy_analyzer.analyze_project(
                tasks=tasks,
                conversations=[],
                progress_callback=progress_callback,
            )

        # 6. Generate summary
        summary = self._generate_summary(
            requirement_divergences=requirement_divergences,
            decision_impacts=decision_impacts,
            instruction_quality_issues=instruction_quality_issues,
            failure_diagnoses=failure_diagnoses,
            task_redundancy=task_redundancy_analysis,
        )

        # Build final analysis
        analysis = PostProjectAnalysis(
            project_id=project_id,
            analysis_timestamp=analysis_start,
            requirement_divergences=requirement_divergences,
            decision_impacts=decision_impacts,
            instruction_quality_issues=instruction_quality_issues,
            failure_diagnoses=failure_diagnoses,
            task_redundancy=task_redundancy_analysis,
            summary=summary,
            metadata={
                "tasks_analyzed": len(tasks),
                "decisions_analyzed": len(decisions),
                "failed_tasks": len([t for t in tasks if t.status == "failed"]),
                "scope": {
                    "requirement_divergence": scope.requirement_divergence,
                    "decision_impact": scope.decision_impact,
                    "instruction_quality": scope.instruction_quality,
                    "failure_diagnosis": scope.failure_diagnosis,
                    "task_redundancy": scope.task_redundancy,
                },
            },
        )

        redundancy_info = ""
        if task_redundancy_analysis:
            redundancy_info = (
                f", redundancy_score={task_redundancy_analysis.redundancy_score:.2f}"
            )

        logger.info(
            f"Post-project analysis complete for {project_id}: "
            f"divergences={len(requirement_divergences)}, "
            f"impacts={len(decision_impacts)}, "
            f"quality_issues={len(instruction_quality_issues)}, "
            f"diagnoses={len(failure_diagnoses)}"
            f"{redundancy_info}"
        )

        return analysis

    def _find_related_decisions(
        self, task: TaskHistory, all_decisions: list[Decision]
    ) -> list[Decision]:
        """
        Find decisions related to a specific task.

        Parameters
        ----------
        task : TaskHistory
            Task to find decisions for
        all_decisions : list[Decision]
            All decisions in the project

        Returns
        -------
        list[Decision]
            Decisions related to the task
        """
        return [d for d in all_decisions if d.task_id == task.task_id]

    def _generate_summary(
        self,
        requirement_divergences: list[RequirementDivergenceAnalysis],
        decision_impacts: list[DecisionImpactAnalysis],
        instruction_quality_issues: list[InstructionQualityAnalysis],
        failure_diagnoses: list[FailureDiagnosis],
        task_redundancy: Optional[TaskRedundancyAnalysis],
    ) -> str:
        """
        Generate executive summary of analysis results.

        Parameters
        ----------
        requirement_divergences : list[RequirementDivergenceAnalysis]
            Requirement divergence analyses
        decision_impacts : list[DecisionImpactAnalysis]
            Decision impact analyses
        instruction_quality_issues : list[InstructionQualityAnalysis]
            Instruction quality analyses
        failure_diagnoses : list[FailureDiagnosis]
            Failure diagnoses
        task_redundancy : Optional[TaskRedundancyAnalysis]
            Task redundancy analysis

        Returns
        -------
        str
            Executive summary text
        """
        summary_parts = []

        # Requirement divergence summary
        if requirement_divergences:
            avg_fidelity = sum(d.fidelity_score for d in requirement_divergences) / len(
                requirement_divergences
            )
            total_divergences = sum(len(d.divergences) for d in requirement_divergences)
            summary_parts.append(
                f"Requirement Fidelity: {avg_fidelity:.2f} average "
                f"({total_divergences} divergences found)"
            )

        # Decision impact summary
        if decision_impacts:
            total_unexpected = sum(len(d.unexpected_impacts) for d in decision_impacts)
            summary_parts.append(
                f"Decision Impact: {len(decision_impacts)} decisions analyzed, "
                f"{total_unexpected} unexpected impacts found"
            )

        # Instruction quality summary
        if instruction_quality_issues:
            avg_quality = sum(
                i.quality_scores.overall for i in instruction_quality_issues
            ) / len(instruction_quality_issues)
            total_ambiguities = sum(
                len(i.ambiguity_issues) for i in instruction_quality_issues
            )
            summary_parts.append(
                f"Instruction Quality: {avg_quality:.2f} average "
                f"({total_ambiguities} ambiguities found)"
            )

        # Failure diagnosis summary
        if failure_diagnoses:
            total_causes = sum(len(d.failure_causes) for d in failure_diagnoses)
            total_strategies = sum(
                len(d.prevention_strategies) for d in failure_diagnoses
            )
            summary_parts.append(
                f"Failures: {len(failure_diagnoses)} tasks failed, "
                f"{total_causes} root causes identified, "
                f"{total_strategies} prevention strategies recommended"
            )

        # Task redundancy summary
        if task_redundancy:
            total_pairs = len(task_redundancy.redundant_pairs)
            summary_parts.append(
                f"Redundancy: {task_redundancy.redundancy_score:.2f} score, "
                f"{total_pairs} redundant pairs, "
                f"{task_redundancy.total_time_wasted:.1f}h wasted, "
                f"recommend {task_redundancy.recommended_complexity} complexity"
            )

        if not summary_parts:
            return "No analysis performed (empty scope or no data)"

        return " | ".join(summary_parts)
