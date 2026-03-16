"""
Contextual Learning System for Marcus Phase 3.

Learns patterns specific to teams, technologies, and project types
to provide intelligent, context-aware recommendations.
"""

import logging
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class TeamLearnings:
    """Learnings specific to a team."""

    team_id: str
    velocity_patterns: Dict[str, float]  # task_type -> avg completion time
    skill_strengths: Dict[str, float]  # skill -> proficiency score
    preferred_task_types: Dict[str, float]  # task_type -> preference score
    collaboration_patterns: Dict[str, Any]
    quality_metrics: Dict[str, float]
    last_updated: datetime


@dataclass
class TechnologyLearnings:
    """Learnings specific to technology stacks."""

    tech_stack: str
    typical_patterns: Dict[str, Any]
    estimation_multipliers: Dict[str, float]  # task_type -> multiplier
    common_dependencies: List[Tuple[str, str]]  # (prerequisite, dependent)
    risk_factors: Dict[str, float]  # risk_type -> probability
    best_practices: List[str]
    last_updated: datetime


@dataclass
class ProjectTypeLearnings:
    """Learnings specific to project types."""

    project_type: str
    typical_phases: List[str]
    phase_dependencies: Dict[str, List[str]]
    success_patterns: Dict[str, Any]
    common_pitfalls: List[str]
    resource_requirements: Dict[str, float]
    last_updated: datetime


@dataclass
class AdaptedTemplate:
    """Template adapted based on learnings."""

    template_id: str
    original_template: Dict[str, Any]
    adaptations: Dict[str, Any]
    adaptation_reasoning: str
    confidence: float
    usage_count: int
    success_rate: float
    last_used: datetime


class ContextualLearningSystem:
    """

    Learns patterns specific to teams, technologies, and project types.

    Provides intelligent adaptation based on context-specific learnings
    rather than generic patterns.
    """

    def __init__(self) -> None:
        # Learning storage
        self.team_learnings: Dict[str, TeamLearnings] = {}
        self.technology_learnings: Dict[str, TechnologyLearnings] = {}
        self.project_type_learnings: Dict[str, ProjectTypeLearnings] = {}
        self.adapted_templates: Dict[str, AdaptedTemplate] = {}

        # Learning parameters
        self.min_samples_for_learning = 3
        self.learning_decay_days = 90  # Learning becomes less relevant after 90 days
        self.confidence_threshold = 0.7

        # Context tracking
        self.context_performance: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        logger.info("Contextual learning system initialized")

    async def learn_team_patterns(
        self, team_id: str, completed_projects: List[Dict[str, Any]]
    ) -> TeamLearnings:
        """
        Learn team-specific patterns from completed projects.

        Args
        ----
            team_id: Unique team identifier
            completed_projects: List of completed project data

        Returns
        -------
            Team learnings with patterns and preferences
        """
        logger.info(f"Learning patterns for team: {team_id}")

        if len(completed_projects) < self.min_samples_for_learning:
            logger.warning(
                f"Insufficient data for team {team_id} learning: "
                f"{len(completed_projects)} projects"
            )
            return self._create_default_team_learnings(team_id)

        # Analyze velocity patterns
        velocity_patterns = self._analyze_team_velocity(completed_projects)

        # Analyze skill strengths
        skill_strengths = self._analyze_team_skills(completed_projects)

        # Analyze task preferences
        preferred_task_types = self._analyze_task_preferences(completed_projects)

        # Analyze collaboration patterns
        collaboration_patterns = self._analyze_collaboration_patterns(
            completed_projects
        )

        # Analyze quality metrics
        quality_metrics = self._analyze_team_quality(completed_projects)

        team_learnings = TeamLearnings(
            team_id=team_id,
            velocity_patterns=velocity_patterns,
            skill_strengths=skill_strengths,
            preferred_task_types=preferred_task_types,
            collaboration_patterns=collaboration_patterns,
            quality_metrics=quality_metrics,
            last_updated=datetime.now(timezone.utc),
        )

        self.team_learnings[team_id] = team_learnings

        logger.info(
            f"Learned {len(velocity_patterns)} velocity patterns for team {team_id}"
        )
        return team_learnings

    async def learn_technology_patterns(
        self, tech_stack: str, project_outcomes: List[Dict[str, Any]]
    ) -> TechnologyLearnings:
        """
        Learn technology-specific patterns from project outcomes.

        Args
        ----
            tech_stack: Technology stack identifier (e.g., "react-python-postgres")
            project_outcomes: List of project outcome data

        Returns
        -------
            Technology learnings with patterns and multipliers
        """
        logger.info(f"Learning patterns for tech stack: {tech_stack}")

        if len(project_outcomes) < self.min_samples_for_learning:
            tech_learnings = self._create_default_tech_learnings(tech_stack)
            self.technology_learnings[tech_stack] = tech_learnings
            return tech_learnings

        # Analyze typical patterns
        typical_patterns = self._analyze_tech_patterns(project_outcomes)

        # Calculate estimation multipliers
        estimation_multipliers = self._calculate_estimation_multipliers(
            project_outcomes
        )

        # Identify common dependencies
        common_dependencies = self._identify_tech_dependencies(project_outcomes)

        # Analyze risk factors
        risk_factors = self._analyze_tech_risks(project_outcomes)

        # Extract best practices
        best_practices = self._extract_best_practices(project_outcomes)

        tech_learnings = TechnologyLearnings(
            tech_stack=tech_stack,
            typical_patterns=typical_patterns,
            estimation_multipliers=estimation_multipliers,
            common_dependencies=common_dependencies,
            risk_factors=risk_factors,
            best_practices=best_practices,
            last_updated=datetime.now(timezone.utc),
        )

        self.technology_learnings[tech_stack] = tech_learnings

        logger.info(
            f"Learned patterns for {tech_stack} from {len(project_outcomes)} projects"
        )
        return tech_learnings

    async def adapt_templates_intelligently(
        self, project_context: Dict[str, Any]
    ) -> Dict[str, AdaptedTemplate]:
        """
        Adapt templates based on learned patterns.

        Args
        ----
            project_context: Current project context

        Returns
        -------
            Dictionary of adapted templates
        """
        team_id = project_context.get("team_id")
        tech_stack = project_context.get("tech_stack_key")
        project_type = project_context.get("project_type", "general")

        # Get relevant learnings
        team_learning = self.team_learnings.get(team_id) if team_id else None
        tech_learning = (
            self.technology_learnings.get(tech_stack) if tech_stack else None
        )
        project_learning = self.project_type_learnings.get(project_type)

        adapted_templates = {}

        # Adapt estimation template
        if team_learning and tech_learning:
            estimation_template = await self._adapt_estimation_template(
                team_learning, tech_learning, project_context
            )
            adapted_templates["estimation"] = estimation_template

        # Adapt task generation template
        if project_learning and team_learning:
            task_template = await self._adapt_task_generation_template(
                project_learning, team_learning, project_context
            )
            adapted_templates["task_generation"] = task_template

        # Adapt dependency template
        if tech_learning:
            dependency_template = await self._adapt_dependency_template(
                tech_learning, project_context
            )
            adapted_templates["dependencies"] = dependency_template

        logger.info(f"Adapted {len(adapted_templates)} templates for project context")
        return adapted_templates

    async def get_contextual_recommendations(
        self, project_context: Dict[str, Any], current_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get contextual recommendations based on learnings.

        Args
        ----
            project_context: Project context information
            current_state: Current project state

        Returns
        -------
            Context-specific recommendations
        """
        recommendations: Dict[str, List[str]] = {
            "team_recommendations": [],
            "technology_recommendations": [],
            "process_recommendations": [],
            "risk_mitigations": [],
        }

        # Team-specific recommendations
        team_id = project_context.get("team_id")
        if team_id in self.team_learnings:
            team_recs = await self._get_team_recommendations(
                self.team_learnings[team_id], current_state
            )
            recommendations["team_recommendations"] = team_recs

        # Technology-specific recommendations
        tech_stack = project_context.get("tech_stack_key")
        if tech_stack in self.technology_learnings:
            tech_recs = await self._get_technology_recommendations(
                self.technology_learnings[tech_stack], current_state
            )
            recommendations["technology_recommendations"] = tech_recs

        # Process recommendations based on project type
        project_type = project_context.get("project_type")
        if project_type in self.project_type_learnings:
            process_recs = await self._get_process_recommendations(
                self.project_type_learnings[project_type], current_state
            )
            recommendations["process_recommendations"] = process_recs

        return recommendations

    def _analyze_team_velocity(
        self, projects: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Analyze team velocity by task type."""
        velocity_data = defaultdict(list)

        for project in projects:
            for task_data in project.get("tasks", []):
                task_type = task_data.get("type", "general")
                estimated_hours = task_data.get("estimated_hours", 0)
                actual_hours = task_data.get("actual_hours", 0)

                # Ensure we have numeric values
                try:
                    estimated_hours = float(estimated_hours)
                    actual_hours = float(actual_hours)
                except (ValueError, TypeError):
                    continue

                if estimated_hours > 0 and actual_hours > 0:
                    velocity_ratio = actual_hours / estimated_hours
                    velocity_data[task_type].append(velocity_ratio)

        # Calculate average velocity per task type
        velocity_patterns = {}
        for task_type, ratios in list(velocity_data.items()):
            if len(ratios) >= 2:  # Need at least 2 samples
                velocity_patterns[task_type] = statistics.mean(ratios)

        return velocity_patterns

    def _analyze_team_skills(self, projects: List[Dict[str, Any]]) -> Dict[str, float]:
        """Analyze team skill strengths."""
        skill_performance = defaultdict(list)

        for project in projects:
            tech_stack = project.get("tech_stack", [])
            success_rate = project.get("success_metrics", {}).get(
                "completion_rate", 0.8
            )

            for tech in tech_stack:
                skill_performance[tech].append(success_rate)

        # Calculate average performance per skill
        skill_strengths = {}
        for skill, performances in list(skill_performance.items()):
            if len(performances) >= 2:
                skill_strengths[skill] = statistics.mean(performances)

        return skill_strengths

    def _analyze_task_preferences(
        self, projects: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Analyze team preferences for task types."""
        task_type_performance = defaultdict(list)

        for project in projects:
            for task_data in project.get("tasks", []):
                task_type = task_data.get("type", "general")
                quality_score = task_data.get("quality_score", 0.8)
                completion_time_ratio = task_data.get("completion_time_ratio", 1.0)

                # Preference score based on quality and efficiency
                preference_score = (quality_score + (2.0 - completion_time_ratio)) / 2
                task_type_performance[task_type].append(preference_score)

        # Calculate preferences
        preferences = {}
        for task_type, scores in list(task_type_performance.items()):
            if len(scores) >= 2:
                preferences[task_type] = statistics.mean(scores)

        return preferences

    def _analyze_collaboration_patterns(
        self, projects: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze team collaboration patterns."""
        patterns = {
            "avg_team_size": 0,
            "parallel_task_preference": 0.5,
            "communication_frequency": "medium",
            "review_thoroughness": 0.8,
        }

        team_sizes = []
        parallel_tasks = []

        for project in projects:
            team_size = project.get("team_size", 3)
            team_sizes.append(team_size)

            # Analyze parallel vs sequential work
            tasks = project.get("tasks", [])
            if tasks:
                overlapping_tasks = sum(
                    1 for task in tasks if task.get("status") == "IN_PROGRESS"
                )
                parallel_ratio = overlapping_tasks / len(tasks)
                parallel_tasks.append(parallel_ratio)

        if team_sizes:
            patterns["avg_team_size"] = statistics.mean(team_sizes)

        if parallel_tasks:
            patterns["parallel_task_preference"] = statistics.mean(parallel_tasks)

        return patterns

    def _analyze_team_quality(self, projects: List[Dict[str, Any]]) -> Dict[str, float]:
        """Analyze team quality metrics."""
        quality_metrics = {}

        all_quality_scores = []
        bug_rates = []
        review_coverage = []

        for project in projects:
            success_metrics = project.get("success_metrics", {})

            quality_score = success_metrics.get("quality_score", 0.8)
            all_quality_scores.append(quality_score)

            bug_rate = success_metrics.get("bug_rate", 0.1)
            bug_rates.append(bug_rate)

            review_cov = success_metrics.get("review_coverage", 0.8)
            review_coverage.append(review_cov)

        if all_quality_scores:
            quality_metrics["average_quality"] = statistics.mean(all_quality_scores)
        if bug_rates:
            quality_metrics["average_bug_rate"] = statistics.mean(bug_rates)
        if review_coverage:
            quality_metrics["review_coverage"] = statistics.mean(review_coverage)

        return quality_metrics

    def _analyze_tech_patterns(self, outcomes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze technology-specific patterns."""
        patterns = {}

        # Analyze common project structures
        structures: Counter[str] = Counter()
        for outcome in outcomes:
            structure = outcome.get("project_structure", "standard")
            structures[structure] += 1

        patterns["common_structures"] = dict(structures.most_common(3))

        # Analyze typical timeline patterns
        durations = [
            o.get("duration_days", 30) for o in outcomes if o.get("duration_days")
        ]
        if durations:
            patterns["typical_duration"] = {
                "mean": statistics.mean(durations),
                "median": statistics.median(durations),
                "std_dev": statistics.stdev(durations) if len(durations) > 1 else 0,
            }

        return patterns

    def _calculate_estimation_multipliers(
        self, outcomes: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate estimation multipliers for different task types."""
        multipliers = {}
        task_type_ratios = defaultdict(list)

        for outcome in outcomes:
            for task_data in outcome.get("tasks", []):
                task_type = task_data.get("type", "general")
                estimated = task_data.get("estimated_hours", 0)
                actual = task_data.get("actual_hours", 0)

                if estimated > 0 and actual > 0:
                    ratio = actual / estimated
                    task_type_ratios[task_type].append(ratio)

        # Calculate multipliers
        for task_type, ratios in list(task_type_ratios.items()):
            if len(ratios) >= 2:
                multipliers[task_type] = statistics.mean(ratios)

        return multipliers

    def _identify_tech_dependencies(
        self, outcomes: List[Dict[str, Any]]
    ) -> List[Tuple[str, str]]:
        """Identify common technology dependencies."""
        dependencies = []
        dependency_counter: Counter[Tuple[str, str]] = Counter()

        for outcome in outcomes:
            project_deps = outcome.get("dependencies", [])
            for dep in project_deps:
                if (
                    isinstance(dep, dict)
                    and "prerequisite" in dep
                    and "dependent" in dep
                ):
                    dep_pair = (dep["prerequisite"], dep["dependent"])
                    dependency_counter[dep_pair] += 1

        # Return most common dependencies
        for (prereq, dep), count in dependency_counter.most_common(10):
            if count >= 2:  # Appeared in at least 2 projects
                dependencies.append((prereq, dep))

        return dependencies

    def _analyze_tech_risks(self, outcomes: List[Dict[str, Any]]) -> Dict[str, float]:
        """Analyze technology-specific risks."""
        risks: defaultdict[str, int] = defaultdict(int)
        total_projects = len(outcomes)

        for outcome in outcomes:
            encountered_risks = outcome.get("risks_encountered", [])
            for risk in encountered_risks:
                risks[risk] += 1

        # Convert to probabilities
        risk_probabilities = {}
        for risk, count in list(risks.items()):
            if count >= 2:  # Risk appeared in at least 2 projects
                risk_probabilities[risk] = count / total_projects

        return risk_probabilities

    def _extract_best_practices(self, outcomes: List[Dict[str, Any]]) -> List[str]:
        """Extract best practices from successful projects."""
        practices: Counter[str] = Counter()

        for outcome in outcomes:
            success_rate = outcome.get("success_metrics", {}).get(
                "completion_rate", 0.8
            )
            if success_rate > 0.85:  # Only from successful projects
                project_practices = outcome.get("practices_used", [])
                for practice in project_practices:
                    practices[practice] += 1

        # Return practices used in multiple successful projects
        return [practice for practice, count in practices.most_common(10) if count >= 2]

    def _create_default_team_learnings(self, team_id: str) -> TeamLearnings:
        """Create default team learnings when insufficient data."""
        return TeamLearnings(
            team_id=team_id,
            velocity_patterns={"general": 1.2},  # Assume 20% overrun by default
            skill_strengths={},
            preferred_task_types={},
            collaboration_patterns={
                "avg_team_size": 3,
                "parallel_task_preference": 0.5,
            },
            quality_metrics={"average_quality": 0.8},
            last_updated=datetime.now(timezone.utc),
        )

    def _create_default_tech_learnings(self, tech_stack: str) -> TechnologyLearnings:
        """Create default technology learnings when insufficient data."""
        return TechnologyLearnings(
            tech_stack=tech_stack,
            typical_patterns={"typical_duration": {"mean": 30, "median": 28}},
            estimation_multipliers={"general": 1.3},
            common_dependencies=[],
            risk_factors={},
            best_practices=["Follow coding standards", "Write tests", "Code review"],
            last_updated=datetime.now(timezone.utc),
        )

    async def _adapt_estimation_template(
        self,
        team_learning: TeamLearnings,
        tech_learning: TechnologyLearnings,
        context: Dict[str, Any],
    ) -> AdaptedTemplate:
        """Adapt estimation template based on learnings."""
        adaptations = {}

        # Combine team velocity and tech multipliers
        for task_type in team_learning.velocity_patterns:
            team_velocity = team_learning.velocity_patterns[task_type]
            tech_multiplier = tech_learning.estimation_multipliers.get(task_type, 1.0)

            # Weighted combination
            combined_multiplier = (team_velocity * 0.6) + (tech_multiplier * 0.4)
            adaptations[f"{task_type}_multiplier"] = combined_multiplier

        return AdaptedTemplate(
            template_id="estimation_adapted",
            original_template={"base_multiplier": 1.0},
            adaptations=adaptations,
            adaptation_reasoning=(
                "Combined team velocity patterns with "
                "technology-specific multipliers"
            ),
            confidence=0.8,
            usage_count=0,
            success_rate=0.0,
            last_used=datetime.now(timezone.utc),
        )

    async def _adapt_task_generation_template(
        self,
        project_learning: ProjectTypeLearnings,
        team_learning: TeamLearnings,
        context: Dict[str, Any],
    ) -> AdaptedTemplate:
        """Adapt task generation template based on learnings."""
        adaptations = {
            "preferred_task_types": list(team_learning.preferred_task_types.keys()),
            "typical_phases": project_learning.typical_phases,
            "team_preferences": team_learning.preferred_task_types,
        }

        return AdaptedTemplate(
            template_id="task_generation_adapted",
            original_template={
                "standard_phases": ["design", "implement", "test", "deploy"]
            },
            adaptations=adaptations,
            adaptation_reasoning=(
                "Adapted based on team preferences and project type patterns"
            ),
            confidence=0.75,
            usage_count=0,
            success_rate=0.0,
            last_used=datetime.now(timezone.utc),
        )

    async def _adapt_dependency_template(
        self, tech_learning: TechnologyLearnings, context: Dict[str, Any]
    ) -> AdaptedTemplate:
        """Adapt dependency template based on technology learnings."""
        adaptations = {
            "common_dependencies": tech_learning.common_dependencies,
            "risk_factors": tech_learning.risk_factors,
        }

        return AdaptedTemplate(
            template_id="dependencies_adapted",
            original_template={"basic_dependencies": []},
            adaptations=adaptations,
            adaptation_reasoning="Added technology-specific dependency patterns",
            confidence=0.7,
            usage_count=0,
            success_rate=0.0,
            last_used=datetime.now(timezone.utc),
        )

    async def _get_team_recommendations(
        self, team_learning: TeamLearnings, current_state: Dict[str, Any]
    ) -> List[str]:
        """Get team-specific recommendations."""
        recommendations = []

        # Velocity recommendations
        for task_type, velocity in team_learning.velocity_patterns.items():
            if velocity > 1.5:
                percent = (velocity - 1) * 100
                recommendations.append(
                    f"Team tends to underestimate {task_type} tasks by "
                    f"{percent:.0f}% - consider adding buffer"
                )

        # Skill recommendations
        strong_skills = [
            skill
            for skill, strength in team_learning.skill_strengths.items()
            if strength > 0.85
        ]
        if strong_skills:
            recommendations.append(
                f"Leverage team's strong skills in: {', '.join(strong_skills)}"
            )

        return recommendations

    async def _get_technology_recommendations(
        self, tech_learning: TechnologyLearnings, current_state: Dict[str, Any]
    ) -> List[str]:
        """Get technology-specific recommendations."""
        recommendations = []

        # Risk mitigation
        for risk, probability in tech_learning.risk_factors.items():
            if probability > 0.3:
                percent = probability * 100
                recommendations.append(
                    f"Monitor for {risk} (occurs in {percent:.0f}% of "
                    f"{tech_learning.tech_stack} projects)"
                )

        # Best practices
        recommendations.extend(
            [
                f"Recommended practice: {practice}"
                for practice in tech_learning.best_practices[:3]
            ]
        )

        return recommendations

    async def _get_process_recommendations(
        self, project_learning: ProjectTypeLearnings, current_state: Dict[str, Any]
    ) -> List[str]:
        """Get process recommendations based on project type."""
        recommendations = []

        # Phase recommendations
        if project_learning.typical_phases:
            phases = ", ".join(project_learning.typical_phases)
            recommendations.append(
                f"For {project_learning.project_type} projects, "
                f"consider phases: {phases}"
            )

        # Pitfall warnings
        for pitfall in project_learning.common_pitfalls[:2]:
            recommendations.append(f"Watch out for: {pitfall}")

        return recommendations
