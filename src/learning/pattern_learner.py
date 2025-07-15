"""
Pattern Learner for Marcus Phase 2

Learns patterns from completed projects to improve future recommendations.
"""

import json
import logging
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.core.models import Priority, Task, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class CompletedProject:
    """Data from a completed project"""

    project_id: str
    name: str
    tasks: List[Task]
    completion_date: datetime
    success_metrics: Dict[str, Any]
    team_size: int
    duration_days: int
    project_type: str


@dataclass
class ProjectLearnings:
    """Extracted learnings from a project"""

    estimation_accuracy: Dict[str, float]  # task_type -> accuracy ratio
    dependency_patterns: List[Dict[str, Any]]
    workflow_patterns: Dict[str, Any]
    success_factors: List[str]
    failure_points: List[str]
    team_performance: Dict[str, Any]


@dataclass
class Pattern:
    """A learned pattern"""

    pattern_id: str
    pattern_type: str  # 'estimation', 'dependency', 'workflow', etc.
    description: str
    conditions: Dict[str, Any]
    recommendations: Dict[str, Any]
    confidence: float
    evidence_count: int
    last_updated: datetime


class PatternLearner:
    """Learns patterns from completed projects"""

    def __init__(self):
        self.patterns: Dict[str, Pattern] = {}
        self.project_history: List[CompletedProject] = []

        # Task type mappings for learning
        self.task_type_patterns = {
            "setup": r"(setup|init|configure|install)",
            "design": r"(design|architect|plan|wireframe)",
            "backend": r"(backend|api|server|endpoint)",
            "frontend": r"(frontend|ui|client|interface)",
            "testing": r"(test|qa|quality|verify)",
            "deployment": r"(deploy|release|launch|production)",
            "documentation": r"(document|docs|readme|guide)",
            "bugfix": r"(fix|bug|issue|error)",
        }

    async def learn_from_project(self, project: CompletedProject):
        """
        Extract learnings from a completed project

        Args:
            project: Completed project data
        """
        logger.info(f"Learning from completed project: {project.name}")

        # Add to history
        self.project_history.append(project)

        # Extract various types of learnings
        learnings = ProjectLearnings(
            estimation_accuracy=await self._analyze_estimation_accuracy(project),
            dependency_patterns=await self._analyze_dependency_patterns(project),
            workflow_patterns=await self._analyze_workflow_patterns(project),
            success_factors=await self._identify_success_factors(project),
            failure_points=await self._identify_failure_points(project),
            team_performance=await self._analyze_team_performance(project),
        )

        # Update patterns based on learnings
        await self.update_patterns(learnings)

        logger.info(f"Updated {len(self.patterns)} patterns from project learnings")

    async def update_patterns(self, learnings: ProjectLearnings):
        """
        Update pattern library based on new learnings

        Args:
            learnings: Extracted learnings from a project
        """
        # Update estimation patterns
        await self._update_estimation_patterns(learnings.estimation_accuracy)

        # Update dependency patterns
        await self._update_dependency_patterns(learnings.dependency_patterns)

        # Update workflow patterns
        await self._update_workflow_patterns(learnings.workflow_patterns)

        # Update success/failure patterns
        await self._update_outcome_patterns(
            learnings.success_factors, learnings.failure_points
        )

        # Prune old or low-confidence patterns
        await self._prune_patterns()

    async def _analyze_estimation_accuracy(
        self, project: CompletedProject
    ) -> Dict[str, float]:
        """Analyze how accurate task estimates were"""
        accuracy_by_type = {}

        for task in project.tasks:
            if not task.estimated_hours or not hasattr(task, "actual_hours"):
                continue

            task_type = self._classify_task_type(task)
            estimated = task.estimated_hours
            actual = getattr(task, "actual_hours", estimated)

            if actual > 0:
                accuracy = min(estimated, actual) / max(estimated, actual)

                if task_type not in accuracy_by_type:
                    accuracy_by_type[task_type] = []
                accuracy_by_type[task_type].append(accuracy)

        # Calculate average accuracy per type
        return {
            task_type: sum(accuracies) / len(accuracies)
            for task_type, accuracies in accuracy_by_type.items()
        }

    async def _analyze_dependency_patterns(
        self, project: CompletedProject
    ) -> List[Dict[str, Any]]:
        """Analyze dependency patterns that worked well"""
        patterns = []

        # Analyze task completion order
        completed_tasks = [t for t in project.tasks if t.status == TaskStatus.DONE]
        completed_tasks.sort(key=lambda t: t.completed_at or t.updated_at)

        # Look for sequential patterns
        for i in range(len(completed_tasks) - 1):
            current_task = completed_tasks[i]
            next_task = completed_tasks[i + 1]

            current_type = self._classify_task_type(current_task)
            next_type = self._classify_task_type(next_task)

            if current_type != next_type:
                patterns.append(
                    {
                        "pattern": f"{current_type}_before_{next_type}",
                        "description": f"{current_type} tasks typically complete before {next_type} tasks",
                        "confidence": 0.7,
                        "evidence": {
                            "current_task": current_task.name,
                            "next_task": next_task.name,
                        },
                    }
                )

        return patterns

    async def _analyze_workflow_patterns(
        self, project: CompletedProject
    ) -> Dict[str, Any]:
        """Analyze workflow patterns"""
        patterns = {}

        # Analyze parallelism
        max_concurrent = 0
        daily_progress = defaultdict(int)

        for task in project.tasks:
            if task.completed_at:
                completion_day = task.completed_at.date()
                daily_progress[completion_day] += 1
                max_concurrent = max(max_concurrent, daily_progress[completion_day])

        patterns["max_parallelism"] = max_concurrent
        patterns["avg_daily_completions"] = (
            sum(daily_progress.values()) / len(daily_progress) if daily_progress else 0
        )

        # Analyze phase distribution
        phase_distribution = defaultdict(int)
        for task in project.tasks:
            task_type = self._classify_task_type(task)
            phase_distribution[task_type] += 1

        patterns["phase_distribution"] = dict(phase_distribution)

        return patterns

    async def _identify_success_factors(self, project: CompletedProject) -> List[str]:
        """Identify factors that contributed to project success"""
        factors = []

        # Check if project completed on time
        if project.duration_days <= project.success_metrics.get(
            "planned_duration", float("inf")
        ):
            factors.append("completed_on_time")

        # Check task completion rate
        completed_tasks = len([t for t in project.tasks if t.status == TaskStatus.DONE])
        completion_rate = completed_tasks / len(project.tasks) if project.tasks else 0

        if completion_rate > 0.9:
            factors.append("high_completion_rate")

        # Check for good estimation accuracy
        total_estimated = sum(t.estimated_hours or 0 for t in project.tasks)
        total_actual = sum(
            getattr(t, "actual_hours", t.estimated_hours or 0) for t in project.tasks
        )

        if total_estimated > 0:
            estimation_accuracy = min(total_estimated, total_actual) / max(
                total_estimated, total_actual
            )
            if estimation_accuracy > 0.8:
                factors.append("accurate_estimation")

        # Check for balanced workload
        if project.team_size >= 2:
            factors.append("team_collaboration")

        return factors

    async def _identify_failure_points(self, project: CompletedProject) -> List[str]:
        """Identify points where the project struggled"""
        failure_points = []

        # Check for blocked tasks
        blocked_tasks = [
            t for t in project.tasks if t.status.value in ["BLOCKED", "CANCELLED"]
        ]
        if len(blocked_tasks) > len(project.tasks) * 0.1:
            failure_points.append("high_blocked_task_rate")

        # Check for overrun tasks
        overrun_count = 0
        for task in project.tasks:
            if (
                task.estimated_hours
                and hasattr(task, "actual_hours")
                and getattr(task, "actual_hours", 0) > task.estimated_hours * 1.5
            ):
                overrun_count += 1

        if overrun_count > len(project.tasks) * 0.2:
            failure_points.append("frequent_estimation_overruns")

        # Check for late completion
        if (
            project.duration_days
            > project.success_metrics.get("planned_duration", 0) * 1.2
        ):
            failure_points.append("project_delay")

        return failure_points

    async def _analyze_team_performance(
        self, project: CompletedProject
    ) -> Dict[str, Any]:
        """Analyze team performance metrics"""
        performance = {}

        # Calculate velocity (tasks per day)
        if project.duration_days > 0:
            performance["velocity"] = len(project.tasks) / project.duration_days

        # Calculate team efficiency
        performance["team_size"] = project.team_size
        performance["tasks_per_person"] = (
            len(project.tasks) / project.team_size if project.team_size > 0 else 0
        )

        # Analyze task distribution by type
        task_type_counts = defaultdict(int)
        for task in project.tasks:
            task_type = self._classify_task_type(task)
            task_type_counts[task_type] += 1

        performance["task_type_distribution"] = dict(task_type_counts)

        return performance

    async def _update_estimation_patterns(self, accuracy_data: Dict[str, float]):
        """Update estimation accuracy patterns"""
        for task_type, accuracy in accuracy_data.items():
            pattern_id = f"estimation_{task_type}"

            if pattern_id in self.patterns:
                # Update existing pattern
                pattern = self.patterns[pattern_id]
                # Weighted average with existing data
                weight = 0.3  # New data weight
                old_accuracy = pattern.recommendations.get("accuracy_multiplier", 1.0)
                new_accuracy = old_accuracy * (1 - weight) + accuracy * weight

                pattern.recommendations["accuracy_multiplier"] = new_accuracy
                pattern.evidence_count += 1
                pattern.confidence = min(0.95, pattern.confidence + 0.05)
                pattern.last_updated = datetime.now()
            else:
                # Create new pattern
                self.patterns[pattern_id] = Pattern(
                    pattern_id=pattern_id,
                    pattern_type="estimation",
                    description=f"Estimation accuracy for {task_type} tasks",
                    conditions={"task_type": task_type},
                    recommendations={"accuracy_multiplier": accuracy},
                    confidence=0.6,
                    evidence_count=1,
                    last_updated=datetime.now(),
                )

    async def _update_dependency_patterns(
        self, dependency_patterns: List[Dict[str, Any]]
    ):
        """Update dependency patterns"""
        for pattern_data in dependency_patterns:
            pattern_id = f"dependency_{pattern_data['pattern']}"

            if pattern_id in self.patterns:
                pattern = self.patterns[pattern_id]
                pattern.evidence_count += 1
                pattern.confidence = min(0.95, pattern.confidence + 0.02)
                pattern.last_updated = datetime.now()
            else:
                self.patterns[pattern_id] = Pattern(
                    pattern_id=pattern_id,
                    pattern_type="dependency",
                    description=pattern_data["description"],
                    conditions=pattern_data.get("conditions", {}),
                    recommendations={"pattern": pattern_data["pattern"]},
                    confidence=pattern_data.get("confidence", 0.7),
                    evidence_count=1,
                    last_updated=datetime.now(),
                )

    async def _update_workflow_patterns(self, workflow_data: Dict[str, Any]):
        """Update workflow patterns"""
        pattern_id = "workflow_characteristics"

        if pattern_id in self.patterns:
            pattern = self.patterns[pattern_id]
            # Update with weighted average
            weight = 0.2
            for key, value in workflow_data.items():
                if isinstance(value, (int, float)):
                    old_value = pattern.recommendations.get(key, value)
                    pattern.recommendations[key] = (
                        old_value * (1 - weight) + value * weight
                    )

            pattern.evidence_count += 1
            pattern.last_updated = datetime.now()
        else:
            self.patterns[pattern_id] = Pattern(
                pattern_id=pattern_id,
                pattern_type="workflow",
                description="Workflow characteristics and patterns",
                conditions={},
                recommendations=workflow_data,
                confidence=0.7,
                evidence_count=1,
                last_updated=datetime.now(),
            )

    async def _update_outcome_patterns(
        self, success_factors: List[str], failure_points: List[str]
    ):
        """Update success and failure patterns"""
        # Update success patterns
        for factor in success_factors:
            pattern_id = f"success_{factor}"

            if pattern_id in self.patterns:
                pattern = self.patterns[pattern_id]
                pattern.evidence_count += 1
                pattern.confidence = min(0.95, pattern.confidence + 0.03)
                pattern.last_updated = datetime.now()
            else:
                self.patterns[pattern_id] = Pattern(
                    pattern_id=pattern_id,
                    pattern_type="success_factor",
                    description=f"Success factor: {factor.replace('_', ' ')}",
                    conditions={},
                    recommendations={"factor": factor, "positive_impact": True},
                    confidence=0.6,
                    evidence_count=1,
                    last_updated=datetime.now(),
                )

        # Update failure patterns
        for failure in failure_points:
            pattern_id = f"failure_{failure}"

            if pattern_id in self.patterns:
                pattern = self.patterns[pattern_id]
                pattern.evidence_count += 1
                pattern.confidence = min(0.95, pattern.confidence + 0.03)
                pattern.last_updated = datetime.now()
            else:
                self.patterns[pattern_id] = Pattern(
                    pattern_id=pattern_id,
                    pattern_type="failure_point",
                    description=f"Failure point: {failure.replace('_', ' ')}",
                    conditions={},
                    recommendations={"factor": failure, "negative_impact": True},
                    confidence=0.6,
                    evidence_count=1,
                    last_updated=datetime.now(),
                )

    async def _prune_patterns(self):
        """Remove old or low-confidence patterns"""
        cutoff_date = datetime.now() - timedelta(days=180)  # 6 months old
        min_confidence = 0.3
        min_evidence = 2

        patterns_to_remove = []

        for pattern_id, pattern in self.patterns.items():
            # Remove if too old and low evidence
            if (
                pattern.last_updated < cutoff_date
                and pattern.evidence_count < min_evidence
            ):
                patterns_to_remove.append(pattern_id)

            # Remove if very low confidence
            elif pattern.confidence < min_confidence:
                patterns_to_remove.append(pattern_id)

        for pattern_id in patterns_to_remove:
            del self.patterns[pattern_id]
            logger.info(f"Pruned low-confidence pattern: {pattern_id}")

    async def calculate_confidence(self, pattern: Pattern) -> float:
        """
        Calculate pattern confidence based on evidence

        Args:
            pattern: Pattern to calculate confidence for

        Returns:
            Confidence score between 0 and 1
        """
        base_confidence = pattern.confidence

        # Increase confidence with more evidence
        evidence_bonus = min(0.2, pattern.evidence_count * 0.02)

        # Decrease confidence if pattern is old
        days_old = (datetime.now() - pattern.last_updated).days
        age_penalty = min(0.3, days_old * 0.001)

        final_confidence = base_confidence + evidence_bonus - age_penalty
        return max(0.1, min(0.95, final_confidence))

    def _classify_task_type(self, task: Task) -> str:
        """Classify task type for pattern learning"""
        task_text = f"{task.name} {task.description or ''}".lower()

        import re

        for task_type, pattern in self.task_type_patterns.items():
            if re.search(pattern, task_text):
                return task_type

        return "general"

    async def get_patterns_for_context(self, context: Dict[str, Any]) -> List[Pattern]:
        """
        Get patterns relevant to a specific context

        Args:
            context: Context information (project type, team size, etc.)

        Returns:
            List of relevant patterns
        """
        relevant_patterns = []

        for pattern in self.patterns.values():
            # Check if pattern conditions match context
            is_relevant = True

            for condition_key, condition_value in pattern.conditions.items():
                if (
                    condition_key in context
                    and context[condition_key] != condition_value
                ):
                    is_relevant = False
                    break

            if is_relevant:
                # Update confidence based on current evidence
                pattern.confidence = await self.calculate_confidence(pattern)
                relevant_patterns.append(pattern)

        # Sort by confidence
        relevant_patterns.sort(key=lambda p: p.confidence, reverse=True)

        return relevant_patterns

    async def export_patterns(self) -> Dict[str, Any]:
        """Export patterns for persistence"""
        return {
            "patterns": {
                pattern_id: asdict(pattern)
                for pattern_id, pattern in self.patterns.items()
            },
            "export_timestamp": datetime.now().isoformat(),
            "pattern_count": len(self.patterns),
        }

    async def import_patterns(self, pattern_data: Dict[str, Any]):
        """Import patterns from persistence"""
        for pattern_id, pattern_dict in pattern_data.get("patterns", {}).items():
            # Convert datetime strings back to datetime objects
            if "last_updated" in pattern_dict:
                pattern_dict["last_updated"] = datetime.fromisoformat(
                    pattern_dict["last_updated"]
                )

            pattern = Pattern(**pattern_dict)
            self.patterns[pattern_id] = pattern

        logger.info(f"Imported {len(self.patterns)} patterns")
