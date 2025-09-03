"""
Project Pattern Learner

This module extracts patterns from completed projects to improve future recommendations.
It analyzes project outcomes, team performance, and quality metrics to identify
successful patterns and common pitfalls.
"""

import json
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.core.code_analyzer import CodeAnalyzer
from src.core.models import ProjectState, Task, TaskStatus, WorkerStatus
from src.integrations.ai_analysis_engine import AIAnalysisEngine
from src.quality.board_quality_validator import BoardQualityValidator, QualityReport
from src.recommendations.recommendation_engine import PatternDatabase, ProjectOutcome


@dataclass
class ProjectPattern:
    """Comprehensive pattern extracted from a project."""

    project_id: str
    project_name: str
    outcome: ProjectOutcome
    quality_metrics: Dict[str, float]
    team_composition: Dict[str, Any]
    velocity_pattern: Dict[str, float]
    task_patterns: Dict[str, Any]
    blocker_patterns: Dict[str, Any]
    technology_stack: List[str]
    implementation_patterns: Dict[str, Any]
    success_factors: List[str]
    risk_factors: List[str]
    extracted_at: datetime
    confidence_score: float


@dataclass
class TeamPerformanceMetrics:
    """Metrics for team performance analysis."""

    average_velocity: float
    task_completion_rate: float
    blocker_resolution_time: float
    collaboration_score: float
    skill_utilization: Dict[str, float]
    agent_performance: Dict[str, Any]


class ProjectPatternLearner:
    """
    Extracts and learns patterns from completed projects.

    This class analyzes completed projects to identify patterns that lead to
    success or failure, helping Marcus make better decisions for future projects.
    """

    def __init__(
        self,
        pattern_db: Optional[PatternDatabase] = None,
        ai_engine: Optional[AIAnalysisEngine] = None,
        code_analyzer: Optional[CodeAnalyzer] = None,
    ) -> None:
        """
        Initialize the pattern learner.

        Parameters
        ----------
        pattern_db : Optional[PatternDatabase]
            Database for storing patterns. Creates new if not provided.
        ai_engine : Optional[AIAnalysisEngine]
            AI engine for analysis. Creates new if not provided.
        code_analyzer : Optional[CodeAnalyzer]
            Code analyzer for GitHub integration.
        """
        self.pattern_db = pattern_db or PatternDatabase()
        self.ai_engine = ai_engine or AIAnalysisEngine()
        self.code_analyzer = code_analyzer
        self.quality_validator = BoardQualityValidator()

        # Pattern storage
        self.learned_patterns: List[ProjectPattern] = []
        self._load_existing_patterns()

        # Update pattern database with pattern learner reference
        if hasattr(self.pattern_db, "pattern_learner"):
            self.pattern_db.pattern_learner = self

    def _load_existing_patterns(self) -> None:
        """Load previously learned patterns from storage."""
        patterns_file = (
            Path(__file__).parent.parent.parent / "data" / "learned_patterns.json"
        )
        if patterns_file.exists():
            with open(patterns_file, "r") as f:
                data = json.load(f)
                # Reconstruct patterns from JSON
                for pattern_data in data.get("patterns", []):
                    # Convert datetime strings back to datetime objects
                    pattern_data["extracted_at"] = datetime.fromisoformat(
                        pattern_data["extracted_at"]
                    )
                    # Reconstruct ProjectOutcome
                    outcome_data = pattern_data["outcome"]
                    pattern_data["outcome"] = ProjectOutcome(**outcome_data)

                    self.learned_patterns.append(ProjectPattern(**pattern_data))

    async def learn_from_project(
        self,
        project_state: ProjectState,
        tasks: List[Task],
        team_members: List[WorkerStatus],
        outcome: ProjectOutcome,
        github_owner: Optional[str] = None,
        github_repo: Optional[str] = None,
    ) -> ProjectPattern:
        """
        Extract patterns from a completed project.

        Parameters
        ----------
        project_state : ProjectState
            Final state of the completed project
        tasks : List[Task]
            All tasks from the project
        team_members : List[WorkerStatus]
            Team members who worked on the project
        outcome : ProjectOutcome
            Actual project outcome metrics
        github_owner : Optional[str]
            GitHub repository owner for code analysis
        github_repo : Optional[str]
            GitHub repository name for code analysis

        Returns
        -------
        ProjectPattern
            Extracted pattern from the project
        """
        # Analyze project quality
        quality_report = self.quality_validator.validate_board(tasks)
        quality_metrics = self._extract_quality_metrics(quality_report, tasks)

        # Analyze team performance
        team_metrics = self._analyze_team_performance(tasks, team_members)
        team_composition = self._analyze_team_composition(team_members)

        # Analyze task patterns
        task_patterns = self._analyze_task_patterns(tasks)
        velocity_pattern = self._analyze_velocity_pattern(tasks)

        # Analyze blockers and risks
        blocker_patterns = self._analyze_blocker_patterns(tasks)

        # Analyze implementation if GitHub integration available
        implementation_patterns = {}
        technology_stack = []
        if self.code_analyzer and github_owner and github_repo:
            implementation_patterns = await self._analyze_implementation(
                tasks, github_owner, github_repo
            )
            technology_stack = await self._detect_technology_stack(
                github_owner, github_repo
            )

        # Use AI to identify success/risk factors
        success_factors, risk_factors = await self._identify_key_factors(
            project_state, quality_metrics, team_metrics, outcome
        )

        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(
            quality_report.score, outcome.quality_score, len(tasks), len(team_members)
        )

        # Create pattern
        pattern = ProjectPattern(
            project_id=project_state.board_id,
            project_name=project_state.project_name,
            outcome=outcome,
            quality_metrics=quality_metrics,
            team_composition=team_composition,
            velocity_pattern=velocity_pattern,
            task_patterns=task_patterns,
            blocker_patterns=blocker_patterns,
            technology_stack=technology_stack,
            implementation_patterns=implementation_patterns,
            success_factors=success_factors,
            risk_factors=risk_factors,
            extracted_at=datetime.now(),
            confidence_score=confidence_score,
        )

        # Store pattern
        self._store_pattern(pattern)

        # Update pattern database
        if outcome.successful:
            self.pattern_db.add_success_pattern(self._pattern_to_flow_data(pattern))
        else:
            self.pattern_db.add_failure_pattern(
                self._pattern_to_flow_data(pattern), outcome.failure_reasons or []
            )

        return pattern

    def _extract_quality_metrics(
        self, quality_report: QualityReport, tasks: List[Task]
    ) -> Dict[str, float]:
        """Extract detailed quality metrics from the project."""
        completed_tasks = [t for t in tasks if t.status == TaskStatus.DONE]

        metrics = {
            "board_quality_score": quality_report.score,
            "description_quality": quality_report.metrics.get(
                "description_coverage", 0
            ),
            "label_quality": quality_report.metrics.get("label_coverage", 0),
            "estimate_accuracy": self._calculate_estimate_accuracy(completed_tasks),
            "completion_rate": len(completed_tasks) / len(tasks) if tasks else 0,
            "on_time_delivery": self._calculate_on_time_delivery(completed_tasks),
            "rework_rate": self._calculate_rework_rate(tasks),
            "blocker_rate": (
                len([t for t in tasks if t.status == TaskStatus.BLOCKED]) / len(tasks)
                if tasks
                else 0
            ),
        }

        return metrics

    def _analyze_team_performance(
        self, tasks: List[Task], team_members: List[WorkerStatus]
    ) -> TeamPerformanceMetrics:
        """Analyze team performance metrics."""
        # Calculate velocity
        completed_tasks = [t for t in tasks if t.status == TaskStatus.DONE]

        # Group tasks by week
        tasks_by_week = defaultdict(list)
        for task in completed_tasks:
            if task.updated_at:
                week = task.updated_at.isocalendar()[1]
                tasks_by_week[week].append(task)

        weekly_velocities = [len(tasks) for tasks in tasks_by_week.values()]
        avg_velocity = statistics.mean(weekly_velocities) if weekly_velocities else 0

        # Calculate completion rate
        completion_rate = len(completed_tasks) / len(tasks) if tasks else 0

        # Calculate blocker resolution time (simplified)
        blocker_times = []
        for task in tasks:
            if task.status == TaskStatus.DONE and hasattr(task, "blocker_duration"):
                blocker_times.append(task.blocker_duration)

        avg_blocker_time = statistics.mean(blocker_times) if blocker_times else 0

        # Calculate collaboration score (based on task handoffs)
        collaboration_score = self._calculate_collaboration_score(tasks, team_members)

        # Calculate skill utilization
        skill_utilization = self._calculate_skill_utilization(tasks, team_members)

        # Calculate per-agent performance
        agent_performance = {}
        for member in team_members:
            member_tasks = [
                t for t in completed_tasks if t.assigned_to == member.worker_id
            ]
            if member_tasks:
                agent_performance[member.worker_id] = {
                    "completed_tasks": len(member_tasks),
                    "avg_completion_time": (
                        statistics.mean(
                            [
                                (t.updated_at - t.created_at).days
                                for t in member_tasks
                                if t.updated_at and t.created_at
                            ]
                        )
                        if member_tasks
                        else 0
                    ),
                    "quality_score": member.performance_score,
                }

        return TeamPerformanceMetrics(
            average_velocity=avg_velocity,
            task_completion_rate=completion_rate,
            blocker_resolution_time=avg_blocker_time,
            collaboration_score=collaboration_score,
            skill_utilization=skill_utilization,
            agent_performance=agent_performance,
        )

    def _analyze_team_composition(
        self, team_members: List[WorkerStatus]
    ) -> Dict[str, Any]:
        """Analyze team composition and skills."""
        roles: Dict[str, int] = defaultdict(int)
        skill_coverage: Dict[str, int] = defaultdict(int)
        experience_distribution: Dict[str, int] = {"senior": 0, "mid": 0, "junior": 0}
        
        composition = {
            "team_size": len(team_members),
            "roles": roles,
            "skill_coverage": skill_coverage,
            "experience_distribution": experience_distribution,
        }

        for member in team_members:
            # Count roles
            roles[member.role] += 1

            # Count skills
            for skill in member.skills:
                skill_coverage[skill] += 1

            # Estimate experience level based on completed tasks
            if member.completed_tasks_count > 50:
                experience_distribution["senior"] += 1
            elif member.completed_tasks_count > 20:
                experience_distribution["mid"] += 1
            else:
                experience_distribution["junior"] += 1

        # Convert defaultdicts to regular dicts for JSON serialization
        composition["roles"] = dict(roles)
        composition["skill_coverage"] = dict(skill_coverage)

        return composition

    def _analyze_task_patterns(self, tasks: List[Task]) -> Dict[str, Any]:
        """Analyze patterns in task structure and organization."""
        patterns = {
            "task_size_distribution": self._get_task_size_distribution(tasks),
            "dependency_depth": self._calculate_dependency_depth(tasks),
            "parallel_work_ratio": self._calculate_parallel_work_ratio(tasks),
            "task_type_distribution": self._get_task_type_distribution(tasks),
            "priority_distribution": self._get_priority_distribution(tasks),
            "phase_structure": self._analyze_phase_structure(tasks),
        }

        return patterns

    def _analyze_velocity_pattern(self, tasks: List[Task]) -> Dict[str, float]:
        """Analyze velocity patterns throughout the project."""
        completed_tasks = [t for t in tasks if t.status == TaskStatus.DONE]

        if not completed_tasks:
            return {}

        # Sort by completion date
        completed_tasks.sort(key=lambda t: t.updated_at or datetime.now())

        # Calculate velocity by project phase (quartiles)
        total_tasks = len(completed_tasks)
        quartile_size = total_tasks // 4

        velocity_pattern = {}
        phases = ["start", "early", "middle", "end"]

        for i, phase in enumerate(phases):
            start_idx = i * quartile_size
            end_idx = (i + 1) * quartile_size if i < 3 else total_tasks

            phase_tasks = completed_tasks[start_idx:end_idx]
            if phase_tasks:
                # Calculate tasks per day for this phase
                duration = (phase_tasks[-1].updated_at - phase_tasks[0].updated_at).days
                velocity = len(phase_tasks) / max(duration, 1)
                velocity_pattern[phase] = velocity

        return velocity_pattern

    def _analyze_blocker_patterns(self, tasks: List[Task]) -> Dict[str, Any]:
        """Analyze patterns in blockers and impediments."""
        blocked_tasks = [
            t for t in tasks if hasattr(t, "was_blocked") and t.was_blocked
        ]

        patterns = {
            "blocker_frequency": len(blocked_tasks) / len(tasks) if tasks else 0,
            "blocker_categories": self._categorize_blockers(blocked_tasks),
            "blocker_timing": self._analyze_blocker_timing(blocked_tasks, tasks),
            "recurring_blockers": self._identify_recurring_blockers(blocked_tasks),
        }

        return patterns

    async def _analyze_implementation(
        self, tasks: List[Task], owner: str, repo: str
    ) -> Dict[str, Any]:
        """Analyze implementation patterns from GitHub."""
        if not self.code_analyzer:
            return {}

        endpoints_created: List[str] = []
        models_created: List[str] = []
        
        patterns: Dict[str, Any] = {
            "endpoints_created": endpoints_created,
            "models_created": models_created,
            "test_coverage": 0,
            "code_review_metrics": {},
            "refactoring_rate": 0,
        }

        # Analyze implementation details for completed tasks
        for task in tasks:
            if task.status == TaskStatus.DONE and task.assigned_to:
                # Get implementation details
                worker = WorkerStatus(
                    worker_id=task.assigned_to,
                    name=task.assigned_to,
                    role="developer",
                    email=f"{task.assigned_to}@example.com",
                    current_tasks=[],
                    completed_tasks_count=0,
                    capacity=40,
                    skills=[],
                    availability={},
                )

                analysis = await self.code_analyzer.analyze_task_completion(
                    task, worker, owner, repo
                )

                # Extract patterns
                if analysis.get("findings", {}).get("implementations"):
                    impl = analysis["findings"]["implementations"]
                    endpoints_created.extend(impl.get("endpoints", []))
                    models_created.extend(impl.get("models", []))

        return patterns

    async def _detect_technology_stack(self, owner: str, repo: str) -> List[str]:
        """Detect technology stack from repository."""
        # This would analyze package files, imports, etc.
        # Simplified for now
        return ["python", "fastapi", "postgresql", "react"]

    async def _identify_key_factors(
        self,
        project_state: ProjectState,
        quality_metrics: Dict[str, float],
        team_metrics: TeamPerformanceMetrics,
        outcome: ProjectOutcome,
    ) -> Tuple[List[str], List[str]]:
        """Use AI to identify key success and risk factors."""
        if not self.ai_engine.client:
            # Fallback analysis
            return self._identify_key_factors_fallback(
                quality_metrics, team_metrics, outcome
            )

        prompt = f"""Analyze this completed project and identify key success factors and risk factors.

Project Outcome:
- Success: {outcome.successful}
- Duration: {outcome.completion_time_days} days
- Quality Score: {outcome.quality_score}
- Cost: ${outcome.cost}

Quality Metrics:
{json.dumps(quality_metrics, indent=2)}

Team Performance:
- Average Velocity: {team_metrics.average_velocity} tasks/week
- Completion Rate: {team_metrics.task_completion_rate:.2%}
- Collaboration Score: {team_metrics.collaboration_score:.2f}

Identify:
1. 3-5 key factors that contributed to the outcome
2. 3-5 risk factors or issues that impacted the project

Return JSON:
{{
    "success_factors": ["factor1", "factor2", ...],
    "risk_factors": ["risk1", "risk2", ...]
}}"""

        try:
            response = await self.ai_engine._call_claude(prompt)
            result = json.loads(response)
            return (result.get("success_factors", []), result.get("risk_factors", []))
        except Exception:
            return self._identify_key_factors_fallback(
                quality_metrics, team_metrics, outcome
            )

    def _identify_key_factors_fallback(
        self,
        quality_metrics: Dict[str, float],
        team_metrics: TeamPerformanceMetrics,
        outcome: ProjectOutcome,
    ) -> Tuple[List[str], List[str]]:
        """Fallback method to identify key factors."""
        success_factors = []
        risk_factors = []

        # Analyze quality metrics
        if quality_metrics["board_quality_score"] > 0.8:
            success_factors.append("High quality task definitions and organization")
        elif quality_metrics["board_quality_score"] < 0.5:
            risk_factors.append("Poor task definition and organization")

        if quality_metrics["on_time_delivery"] > 0.8:
            success_factors.append("Excellent time estimation and delivery")
        elif quality_metrics["on_time_delivery"] < 0.5:
            risk_factors.append("Poor time estimation leading to delays")

        # Analyze team metrics
        if team_metrics.average_velocity > 10:
            success_factors.append("High team velocity and productivity")
        elif team_metrics.average_velocity < 3:
            risk_factors.append("Low team velocity impacting progress")

        if team_metrics.collaboration_score > 0.7:
            success_factors.append("Strong team collaboration")

        # Analyze outcome
        if outcome.successful and outcome.quality_score > 0.8:
            success_factors.append("Focus on quality throughout development")

        if outcome.failure_reasons:
            risk_factors.extend(outcome.failure_reasons[:3])

        return success_factors[:5], risk_factors[:5]

    def _calculate_confidence_score(
        self,
        board_quality: float,
        outcome_quality: float,
        task_count: int,
        team_size: int,
    ) -> float:
        """Calculate confidence score for the extracted pattern."""
        # Base confidence on data quality and completeness
        scores = []

        # Board quality contribution
        scores.append(board_quality)

        # Outcome quality contribution
        scores.append(outcome_quality)

        # Task count contribution (more tasks = more data)
        task_score = min(task_count / 50, 1.0)  # Normalize to 50 tasks
        scores.append(task_score)

        # Team size contribution
        team_score = min(team_size / 5, 1.0)  # Normalize to 5 team members
        scores.append(team_score)

        return statistics.mean(scores)

    def _store_pattern(self, pattern: ProjectPattern) -> None:
        """Store the learned pattern."""
        self.learned_patterns.append(pattern)

        # Save to disk
        patterns_file = (
            Path(__file__).parent.parent.parent / "data" / "learned_patterns.json"
        )
        patterns_file.parent.mkdir(exist_ok=True)

        # Convert patterns to JSON-serializable format
        patterns_data = []
        for p in self.learned_patterns:
            pattern_dict = asdict(p)
            # Convert datetime to ISO format
            pattern_dict["extracted_at"] = p.extracted_at.isoformat()
            # Convert ProjectOutcome to dict
            pattern_dict["outcome"] = asdict(p.outcome)
            patterns_data.append(pattern_dict)

        with open(patterns_file, "w") as f:
            json.dump({"patterns": patterns_data}, f, indent=2)

    def _pattern_to_flow_data(self, pattern: ProjectPattern) -> Dict[str, Any]:
        """Convert pattern to flow data format for pattern database."""
        return {
            "flow_id": pattern.project_id,
            "project_name": pattern.project_name,
            "metrics": {
                "task_count": pattern.task_patterns.get("task_count", 0),
                "complexity_score": pattern.quality_metrics.get(
                    "board_quality_score", 0
                ),
                "confidence_avg": pattern.confidence_score,
                "total_cost": pattern.outcome.cost,
                "total_duration_ms": pattern.outcome.completion_time_days
                * 24
                * 60
                * 60
                * 1000,
            },
            "requirements": [],  # Would need to extract from tasks
            "tasks": [],  # Would need to include task details
            "decisions": [],  # Would need to extract from project history
        }

    # Helper methods for analysis

    def _calculate_estimate_accuracy(self, completed_tasks: List[Task]) -> float:
        """Calculate how accurate time estimates were."""
        # This would need actual vs estimated time data
        # Placeholder for now
        return 0.75

    def _calculate_on_time_delivery(self, completed_tasks: List[Task]) -> float:
        """Calculate percentage of tasks delivered on time."""
        on_time = 0
        total_with_due_date = 0

        for task in completed_tasks:
            if task.due_date and task.updated_at:
                total_with_due_date += 1
                if task.updated_at <= task.due_date:
                    on_time += 1

        return on_time / total_with_due_date if total_with_due_date > 0 else 1.0

    def _calculate_rework_rate(self, tasks: List[Task]) -> float:
        """Calculate rate of tasks that needed rework."""
        # This would need to track task state changes
        # Placeholder for now
        return 0.1

    def _calculate_collaboration_score(
        self, tasks: List[Task], team_members: List[WorkerStatus]
    ) -> float:
        """Calculate collaboration score based on task handoffs."""
        if len(team_members) < 2:
            return 0.0

        # Count tasks that involved multiple team members
        collaborative_tasks = 0
        for task in tasks:
            # This would need task history to track reassignments
            # Placeholder logic
            if task.labels and any("collaborative" in label for label in task.labels):
                collaborative_tasks += 1

        return min(collaborative_tasks / (len(tasks) * 0.3), 1.0) if tasks else 0.0

    def _calculate_skill_utilization(
        self, tasks: List[Task], team_members: List[WorkerStatus]
    ) -> Dict[str, float]:
        """Calculate how well team skills were utilized."""
        skill_usage: Dict[str, int] = defaultdict(int)
        skill_availability: Dict[str, int] = defaultdict(int)

        # Count available skills
        for member in team_members:
            for skill in member.skills:
                skill_availability[skill] += 1

        # Count skill usage in tasks
        for task in tasks:
            if task.labels:
                for label in task.labels:
                    if label.startswith("skill:"):
                        skill = label.replace("skill:", "")
                        skill_usage[skill] += 1

        # Calculate utilization
        utilization = {}
        for skill, available in skill_availability.items():
            used = skill_usage.get(skill, 0)
            utilization[skill] = min(
                used / (available * 5), 1.0
            )  # Assume 5 tasks per skill

        return utilization

    def _get_task_size_distribution(self, tasks: List[Task]) -> Dict[str, int]:
        """Get distribution of task sizes."""
        distribution = {
            "small": 0,  # < 4 hours
            "medium": 0,  # 4-8 hours
            "large": 0,  # 8-16 hours
            "xlarge": 0,  # > 16 hours
        }

        for task in tasks:
            if task.estimated_hours:
                if task.estimated_hours < 4:
                    distribution["small"] += 1
                elif task.estimated_hours < 8:
                    distribution["medium"] += 1
                elif task.estimated_hours < 16:
                    distribution["large"] += 1
                else:
                    distribution["xlarge"] += 1

        return distribution

    def _calculate_dependency_depth(self, tasks: List[Task]) -> int:
        """Calculate maximum dependency chain depth."""
        max_depth = 0

        def get_depth(task_id: str, current_depth: int = 0) -> int:
            task = next((t for t in tasks if t.id == task_id), None)
            if not task or not task.dependencies:
                return current_depth

            max_dep_depth = current_depth
            for dep_id in task.dependencies:
                dep_depth = get_depth(dep_id, current_depth + 1)
                max_dep_depth = max(max_dep_depth, dep_depth)

            return max_dep_depth

        for task in tasks:
            depth = get_depth(task.id)
            max_depth = max(max_depth, depth)

        return max_depth

    def _calculate_parallel_work_ratio(self, tasks: List[Task]) -> float:
        """Calculate ratio of tasks that can be done in parallel."""
        if not tasks:
            return 0.0

        # Tasks without dependencies can be done in parallel
        parallel_tasks = len([t for t in tasks if not t.dependencies])

        return parallel_tasks / len(tasks)

    def _get_task_type_distribution(self, tasks: List[Task]) -> Dict[str, int]:
        """Get distribution of task types."""
        distribution: Dict[str, int] = defaultdict(int)

        for task in tasks:
            if task.labels:
                for label in task.labels:
                    if label.startswith("type:"):
                        task_type = label.replace("type:", "")
                        distribution[task_type] += 1
                        break
                else:
                    distribution["untyped"] += 1
            else:
                distribution["untyped"] += 1

        return dict(distribution)

    def _get_priority_distribution(self, tasks: List[Task]) -> Dict[str, int]:
        """Get distribution of priorities."""
        distribution: Dict[str, int] = defaultdict(int)

        for task in tasks:
            # Priority is always present in the Task model, so no need for None check
            distribution[task.priority.value] += 1

        return dict(distribution)

    def _analyze_phase_structure(self, tasks: List[Task]) -> Dict[str, Any]:
        """Analyze how project was structured in phases."""
        phases = defaultdict(list)

        for task in tasks:
            if task.labels:
                for label in task.labels:
                    if label.startswith("phase:"):
                        phase = label.replace("phase:", "")
                        phases[phase].append(task)
                        break
                else:
                    phases["unphased"].append(task)
            else:
                phases["unphased"].append(task)

        # Analyze phase characteristics
        phase_info = {}
        for phase_name, phase_tasks in phases.items():
            phase_info[phase_name] = {
                "task_count": len(phase_tasks),
                "completion_rate": (
                    len([t for t in phase_tasks if t.status == TaskStatus.DONE])
                    / len(phase_tasks)
                    if phase_tasks
                    else 0
                ),
                "avg_task_size": (
                    statistics.mean(
                        [t.estimated_hours for t in phase_tasks if t.estimated_hours]
                    )
                    if any(t.estimated_hours for t in phase_tasks)
                    else 0
                ),
            }

        return phase_info

    def _categorize_blockers(self, blocked_tasks: List[Task]) -> Dict[str, int]:
        """Categorize blockers by type."""
        categories: Dict[str, int] = defaultdict(int)

        # This would need actual blocker descriptions
        # Placeholder categorization
        for task in blocked_tasks:
            if task.labels:
                if any("technical" in label for label in task.labels):
                    categories["technical"] += 1
                elif any("dependency" in label for label in task.labels):
                    categories["dependency"] += 1
                elif any("external" in label for label in task.labels):
                    categories["external"] += 1
                else:
                    categories["other"] += 1
            else:
                categories["unknown"] += 1

        return dict(categories)

    def _analyze_blocker_timing(
        self, blocked_tasks: List[Task], all_tasks: List[Task]
    ) -> Dict[str, float]:
        """Analyze when blockers tend to occur in project lifecycle."""
        if not all_tasks:
            return {}

        # Divide project into quartiles
        quartiles: Dict[str, float] = {"q1": 0.0, "q2": 0.0, "q3": 0.0, "q4": 0.0}

        # This would need actual timeline data
        # Placeholder distribution
        total_blocked = len(blocked_tasks)
        if total_blocked > 0:
            quartiles["q1"] = 0.2  # 20% in first quarter
            quartiles["q2"] = 0.4  # 40% in second quarter
            quartiles["q3"] = 0.3  # 30% in third quarter
            quartiles["q4"] = 0.1  # 10% in final quarter

        return quartiles

    def _identify_recurring_blockers(self, blocked_tasks: List[Task]) -> List[str]:
        """Identify patterns in recurring blockers."""
        # This would analyze blocker descriptions for patterns
        # Placeholder for now
        return [
            "Waiting for API documentation",
            "Database schema changes",
            "External service integration",
        ]

    def find_similar_projects(
        self, target_pattern: ProjectPattern, min_similarity: float = 0.7
    ) -> List[Tuple[ProjectPattern, float]]:
        """
        Find similar projects based on patterns.

        Parameters
        ----------
        target_pattern : ProjectPattern
            Pattern to match against
        min_similarity : float
            Minimum similarity score (0-1)

        Returns
        -------
        List[Tuple[ProjectPattern, float]]
            List of (pattern, similarity_score) tuples
        """
        similar_projects = []

        for pattern in self.learned_patterns:
            similarity = self._calculate_pattern_similarity(target_pattern, pattern)

            if similarity >= min_similarity:
                similar_projects.append((pattern, similarity))

        # Sort by similarity
        similar_projects.sort(key=lambda x: x[1], reverse=True)

        return similar_projects

    def _calculate_pattern_similarity(
        self, pattern1: ProjectPattern, pattern2: ProjectPattern
    ) -> float:
        """Calculate similarity between two project patterns."""
        scores = []

        # Team composition similarity
        team_sim = self._calculate_team_similarity(
            pattern1.team_composition, pattern2.team_composition
        )
        scores.append(team_sim * 0.2)  # 20% weight

        # Task pattern similarity
        task_sim = self._calculate_task_pattern_similarity(
            pattern1.task_patterns, pattern2.task_patterns
        )
        scores.append(task_sim * 0.3)  # 30% weight

        # Technology stack similarity
        tech_sim = self._calculate_tech_stack_similarity(
            pattern1.technology_stack, pattern2.technology_stack
        )
        scores.append(tech_sim * 0.2)  # 20% weight

        # Quality metrics similarity
        quality_sim = self._calculate_quality_similarity(
            pattern1.quality_metrics, pattern2.quality_metrics
        )
        scores.append(quality_sim * 0.3)  # 30% weight

        return sum(scores)

    def _calculate_team_similarity(
        self, team1: Dict[str, Any], team2: Dict[str, Any]
    ) -> float:
        """Calculate similarity between team compositions."""
        scores = []

        # Team size similarity
        size1 = team1.get("team_size", 0)
        size2 = team2.get("team_size", 0)
        size_sim = 1 - abs(size1 - size2) / max(size1, size2, 1)
        scores.append(size_sim)

        # Role overlap
        roles1 = set(team1.get("roles", {}).keys())
        roles2 = set(team2.get("roles", {}).keys())
        if roles1 or roles2:
            role_sim = len(roles1 & roles2) / len(roles1 | roles2)
            scores.append(role_sim)

        # Skill overlap
        skills1 = set(team1.get("skill_coverage", {}).keys())
        skills2 = set(team2.get("skill_coverage", {}).keys())
        if skills1 or skills2:
            skill_sim = len(skills1 & skills2) / len(skills1 | skills2)
            scores.append(skill_sim)

        return statistics.mean(scores) if scores else 0.0

    def _calculate_task_pattern_similarity(
        self, pattern1: Dict[str, Any], pattern2: Dict[str, Any]
    ) -> float:
        """Calculate similarity between task patterns."""
        scores = []

        # Task size distribution similarity
        size_dist1 = pattern1.get("task_size_distribution", {})
        size_dist2 = pattern2.get("task_size_distribution", {})

        for size in ["small", "medium", "large", "xlarge"]:
            val1 = size_dist1.get(size, 0)
            val2 = size_dist2.get(size, 0)
            total = val1 + val2
            if total > 0:
                scores.append(1 - abs(val1 - val2) / total)

        # Dependency depth similarity
        depth1 = pattern1.get("dependency_depth", 0)
        depth2 = pattern2.get("dependency_depth", 0)
        if depth1 or depth2:
            depth_sim = 1 - abs(depth1 - depth2) / max(depth1, depth2)
            scores.append(depth_sim)

        # Parallel work ratio similarity
        parallel1 = pattern1.get("parallel_work_ratio", 0)
        parallel2 = pattern2.get("parallel_work_ratio", 0)
        scores.append(1 - abs(parallel1 - parallel2))

        return statistics.mean(scores) if scores else 0.0

    def _calculate_tech_stack_similarity(
        self, stack1: List[str], stack2: List[str]
    ) -> float:
        """Calculate similarity between technology stacks."""
        if not stack1 and not stack2:
            return 1.0
        if not stack1 or not stack2:
            return 0.0

        set1 = set(stack1)
        set2 = set(stack2)

        return len(set1 & set2) / len(set1 | set2)

    def _calculate_quality_similarity(
        self, metrics1: Dict[str, float], metrics2: Dict[str, float]
    ) -> float:
        """Calculate similarity between quality metrics."""
        scores = []

        # Compare each metric
        for metric in ["board_quality_score", "completion_rate", "on_time_delivery"]:
            val1 = metrics1.get(metric, 0)
            val2 = metrics2.get(metric, 0)
            scores.append(1 - abs(val1 - val2))

        return statistics.mean(scores) if scores else 0.0

    def get_recommendations_from_patterns(
        self, current_project: Dict[str, Any], max_recommendations: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get recommendations based on learned patterns.

        Parameters
        ----------
        current_project : Dict[str, Any]
            Current project information
        max_recommendations : int
            Maximum number of recommendations to return

        Returns
        -------
        List[Dict[str, Any]]
            List of recommendations with confidence scores
        """
        recommendations = []

        # Find similar successful projects
        successful_patterns = [
            p
            for p in self.learned_patterns
            if p.outcome.successful and p.confidence_score > 0.7
        ]

        # Extract recommendations from successful patterns
        for pattern in successful_patterns[:max_recommendations]:
            recommendations_list: List[Dict[str, str]] = []
            rec: Dict[str, Any] = {
                "type": "pattern_based",
                "source_project": pattern.project_name,
                "confidence": pattern.confidence_score,
                "success_factors": pattern.success_factors,
                "recommendations": recommendations_list,
            }

            # Team composition recommendations
            if pattern.team_composition["team_size"] > 0:
                recommendations_list.append(
                    {
                        "category": "team",
                        "suggestion": f"Consider team size of {pattern.team_composition['team_size']} with roles: {', '.join(pattern.team_composition['roles'].keys())}",
                    }
                )

            # Task organization recommendations
            if pattern.task_patterns.get("parallel_work_ratio", 0) > 0.3:
                recommendations_list.append(
                    {
                        "category": "planning",
                        "suggestion": f"Structure {pattern.task_patterns['parallel_work_ratio']:.0%} of tasks for parallel execution",
                    }
                )

            # Quality recommendations
            if pattern.quality_metrics["board_quality_score"] > 0.8:
                recommendations_list.append(
                    {
                        "category": "quality",
                        "suggestion": "Maintain high task definition quality with detailed descriptions and clear acceptance criteria",
                    }
                )

            recommendations.append(rec)

        return recommendations
