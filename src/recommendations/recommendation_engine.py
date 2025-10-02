"""
Pipeline Recommendation Engine - Learn from past executions to provide recommendations

This module builds an intelligent system that learns from past pipeline executions
to provide actionable recommendations for future projects.
"""

import difflib
import json
import statistics
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.analysis.pipeline_comparison import PipelineComparator
from src.visualization.shared_pipeline_events import SharedPipelineEvents


@dataclass
class Recommendation:
    """Individual recommendation with context."""

    type: str
    confidence: float
    message: str
    impact: str
    action: Optional[Callable[[], Any]] = None
    supporting_data: Optional[Dict[str, Any]] = None


@dataclass
class ProjectOutcome:
    """Outcome of a project execution."""

    successful: bool
    completion_time_days: float
    quality_score: float
    cost: float
    failure_reasons: Optional[List[str]] = None


class PatternDatabase:
    """Database of successful and failure patterns."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize pattern database."""
        if db_path is None:
            # Use absolute path to ensure it works regardless of working directory
            marcus_root = Path(__file__).parent.parent.parent
            db_path = str(marcus_root / "data" / "pattern_db.json")
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.patterns = self._load_patterns()

    def _load_patterns(self) -> Dict[str, Any]:
        """Load patterns from disk."""
        if self.db_path.exists() and self.db_path.stat().st_size > 0:
            try:
                with open(self.db_path, "r") as f:
                    loaded_data: Dict[str, Any] = json.load(f)
                    return loaded_data
            except json.JSONDecodeError:
                # File exists but has invalid JSON, return default
                pass

        return {
            "success_patterns": [],
            "failure_patterns": [],
            "templates": {},
            "optimization_rules": [],
        }

    def save_patterns(self) -> None:
        """Save patterns to disk."""
        with open(self.db_path, "w") as f:
            json.dump(self.patterns, f, indent=2, default=str)

    def add_success_pattern(self, flow_data: Dict[str, Any]) -> None:
        """Add a successful flow pattern."""
        pattern = self._extract_pattern(flow_data)
        self.patterns["success_patterns"].append(pattern)
        self.save_patterns()

    def add_failure_pattern(
        self, flow_data: Dict[str, Any], reasons: List[str]
    ) -> None:
        """Add a failure pattern with reasons."""
        pattern = self._extract_pattern(flow_data)
        pattern["failure_reasons"] = reasons
        self.patterns["failure_patterns"].append(pattern)
        self.save_patterns()

    def _extract_pattern(self, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract reusable pattern from flow data."""
        return {
            "project_type": self._infer_project_type(flow_data),
            "task_count": flow_data["metrics"]["task_count"],
            "complexity": flow_data["metrics"]["complexity_score"],
            "confidence": flow_data["metrics"]["confidence_avg"],
            "task_categories": self._categorize_tasks(flow_data["tasks"]),
            "decisions": [
                {
                    "stage": d["stage"],
                    "decision": d["decision"],
                    "confidence": d["confidence"],
                }
                for d in flow_data["decisions"]
            ],
            "requirements_summary": self._summarize_requirements(
                flow_data["requirements"]
            ),
            "timestamp": datetime.now().isoformat(),
        }

    def _infer_project_type(self, flow_data: Dict[str, Any]) -> str:
        """Infer project type from requirements and tasks."""
        keywords = []

        # Extract keywords from requirements
        for req in flow_data.get("requirements", []):
            keywords.extend(req.get("requirement", "").lower().split())

        # Extract keywords from tasks
        for task in flow_data.get("tasks", []):
            keywords.extend(task.get("name", "").lower().split())

        # Common project types
        project_types = {
            "api": ["api", "rest", "endpoint", "crud"],
            "webapp": ["web", "frontend", "ui", "dashboard"],
            "mobile": ["mobile", "ios", "android", "app"],
            "data": ["data", "etl", "pipeline", "analytics"],
            "ml": ["ml", "machine", "learning", "model", "ai"],
            "infrastructure": ["infrastructure", "devops", "deployment", "ci/cd"],
        }

        # Score each type
        type_scores = {}
        for ptype, type_keywords in project_types.items():
            score = sum(1 for k in keywords if k in type_keywords)
            if score > 0:
                type_scores[ptype] = score

        # Return highest scoring type
        if type_scores:
            return max(type_scores, key=lambda x: type_scores[x])
        return "general"

    def _categorize_tasks(self, tasks: List[Dict[str, Any]]) -> Dict[str, int]:
        """Categorize tasks by type."""
        categories: Dict[str, int] = defaultdict(int)

        for task in tasks:
            name = task.get("name", "").lower()

            if any(word in name for word in ["test", "testing", "qa"]):
                categories["testing"] += 1
            elif any(word in name for word in ["doc", "documentation"]):
                categories["documentation"] += 1
            elif any(word in name for word in ["design", "architect"]):
                categories["design"] += 1
            elif any(
                word in name for word in ["implement", "build", "create", "setup"]
            ):
                categories["implementation"] += 1
            elif any(word in name for word in ["deploy", "ci", "cd"]):
                categories["deployment"] += 1
            else:
                categories["other"] += 1

        return dict(categories)

    def _summarize_requirements(
        self, requirements: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Summarize requirements."""
        return {
            "total": len(requirements),
            "functional": len(
                [r for r in requirements if r.get("category") == "functional"]
            ),
            "non_functional": len(
                [r for r in requirements if r.get("category") == "non-functional"]
            ),
            "avg_confidence": (
                statistics.mean([r.get("confidence", 0) for r in requirements])
                if requirements
                else 0
            ),
        }


class SuccessAnalyzer:
    """Analyze what makes projects successful."""

    def __init__(self, pattern_db: PatternDatabase):
        """Initialize success analyzer."""
        self.pattern_db = pattern_db

    def analyze_success_factors(self) -> Dict[str, Any]:
        """Analyze common factors in successful projects."""
        success_patterns = self.pattern_db.patterns["success_patterns"]

        if not success_patterns:
            return {}

        # Aggregate success factors
        factors: Dict[str, Any] = {
            "optimal_task_count": [],
            "optimal_complexity": [],
            "min_confidence": [],
            "task_distribution": defaultdict(list),
            "common_decisions": defaultdict(int),
        }

        for pattern in success_patterns:
            task_count_list: List[int] = factors["optimal_task_count"]
            task_count_list.append(pattern["task_count"])

            complexity_list: List[float] = factors["optimal_complexity"]
            complexity_list.append(pattern["complexity"])

            confidence_list: List[float] = factors["min_confidence"]
            confidence_list.append(pattern["confidence"])

            # Task distribution
            total_tasks = sum(pattern["task_categories"].values())
            if total_tasks > 0:
                task_dist: Dict[str, List[float]] = factors["task_distribution"]
                for category, count in pattern["task_categories"].items():
                    task_dist[category].append(count / total_tasks)

            # Common decisions
            common_decisions: Dict[str, int] = factors["common_decisions"]
            for decision in pattern["decisions"]:
                key = f"{decision['stage']}:{decision['decision']}"
                common_decisions[key] += 1

        # Calculate optimal ranges
        return {
            "optimal_task_count_range": (
                (
                    statistics.mean(factors["optimal_task_count"])
                    - statistics.stdev(factors["optimal_task_count"]),
                    statistics.mean(factors["optimal_task_count"])
                    + statistics.stdev(factors["optimal_task_count"]),
                )
                if len(factors["optimal_task_count"]) > 1
                else (10, 30)
            ),
            "optimal_complexity_range": (0.3, 0.7),
            "min_confidence_threshold": (
                min(factors["min_confidence"]) if factors["min_confidence"] else 0.7
            ),
            "ideal_task_distribution": {
                category: statistics.mean(ratios) if ratios else 0
                for category, ratios in task_dist.items()
            },
            "proven_decisions": [
                decision
                for decision, count in factors["common_decisions"].items()
                if count > len(success_patterns) * 0.5
            ],
        }


class PipelineRecommendationEngine:
    """
    Main recommendation engine that provides actionable recommendations.
    """

    def __init__(self, pattern_learner: Optional[Any] = None) -> None:
        """Initialize recommendation engine."""
        self.shared_events = SharedPipelineEvents()
        self.comparator = PipelineComparator()
        self.pattern_db = PatternDatabase()
        self.success_analyzer = SuccessAnalyzer(self.pattern_db)
        self.pattern_learner = pattern_learner

    def get_recommendations(self, flow_id: str) -> List[Recommendation]:
        """
        Get recommendations for a pipeline flow.

        Parameters
        ----------
        flow_id : str
            The flow ID to analyze

        Returns
        -------
        List[Recommendation]
            Prioritized list of recommendations
        """
        # Load current flow
        current_flow = self._load_flow_data(flow_id)

        if not current_flow:
            return []

        recommendations = []

        # Find similar past projects
        similar_flows = self.find_similar_flows(current_flow)

        # Check for template usage
        template_rec = self._check_template_usage(current_flow, similar_flows)
        if template_rec:
            recommendations.append(template_rec)

        # Analyze complexity
        complexity_rec = self._analyze_complexity(current_flow)
        if complexity_rec:
            recommendations.append(complexity_rec)

        # Check task distribution
        distribution_recs = self._check_task_distribution(current_flow)
        recommendations.extend(distribution_recs)

        # Analyze decisions
        decision_recs = self._analyze_decisions(current_flow)
        recommendations.extend(decision_recs)

        # Performance optimizations
        perf_recs = self._suggest_performance_optimizations(current_flow)
        recommendations.extend(perf_recs)

        # Sort by confidence
        recommendations.sort(key=lambda r: r.confidence, reverse=True)

        return recommendations[:10]  # Top 10 recommendations

    def _load_flow_data(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """Load complete flow data."""
        return self.comparator._load_flow_with_metadata(flow_id)

    def find_similar_flows(self, current_flow: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find similar past projects."""
        similar_flows = []

        # Get all completed flows
        all_data = self.shared_events._read_events()

        for flow_id, flow_info in all_data["flows"].items():
            if flow_id == current_flow["flow_id"] or not flow_info.get("completed_at"):
                continue

            # Load flow data
            flow_data = self._load_flow_data(flow_id)
            if not flow_data:
                continue

            # Calculate similarity
            similarity = self._calculate_similarity(current_flow, flow_data)

            if similarity > 0.7:  # 70% similarity threshold
                similar_flows.append({"flow": flow_data, "similarity": similarity})

        # Sort by similarity
        similar_flows.sort(
            key=lambda x: (
                x["similarity"] if isinstance(x["similarity"], (int, float)) else 0.0
            ),
            reverse=True,
        )

        return similar_flows[:5]  # Top 5 similar flows

    def _calculate_similarity(
        self, flow1: Dict[str, Any], flow2: Dict[str, Any]
    ) -> float:
        """Calculate similarity between two flows."""
        scores = []

        # Project name similarity
        name_similarity = difflib.SequenceMatcher(
            None, flow1["project_name"].lower(), flow2["project_name"].lower()
        ).ratio()
        scores.append(name_similarity)

        # Task count similarity
        task_diff = abs(flow1["metrics"]["task_count"] - flow2["metrics"]["task_count"])
        task_similarity = 1.0 - (
            task_diff
            / max(flow1["metrics"]["task_count"], flow2["metrics"]["task_count"])
        )
        scores.append(task_similarity)

        # Requirements similarity
        req1_text = " ".join(r.get("requirement", "") for r in flow1["requirements"])
        req2_text = " ".join(r.get("requirement", "") for r in flow2["requirements"])
        req_similarity = difflib.SequenceMatcher(None, req1_text, req2_text).ratio()
        scores.append(req_similarity)

        return statistics.mean(scores)

    def should_use_template(
        self, current_flow: Dict[str, Any], similar_flows: List[Dict[str, Any]]
    ) -> bool:
        """Determine if a template should be used."""
        if not similar_flows:
            return False

        # Check if top similar flows are very similar
        top_similarities = [sf["similarity"] for sf in similar_flows[:3]]

        return len(top_similarities) >= 3 and statistics.mean(top_similarities) > 0.85

    def _check_template_usage(
        self, current_flow: Dict[str, Any], similar_flows: List[Dict[str, Any]]
    ) -> Optional[Recommendation]:
        """Check if a template should be used."""
        if not self.should_use_template(current_flow, similar_flows):
            return None

        best_match = similar_flows[0]["flow"]

        return Recommendation(
            type="use_template",
            confidence=0.9,
            message=f"Similar to '{best_match['project_name']}' - consider using as template",
            impact="Save 30-40% of task generation time",
            action=lambda: self.apply_template(best_match),
            supporting_data={
                "template_flow_id": best_match["flow_id"],
                "similarity": similar_flows[0]["similarity"],
            },
        )

    def detect_high_complexity(self, current_flow: Dict[str, Any]) -> bool:
        """Detect if project has high complexity."""
        metrics = current_flow["metrics"]
        if not isinstance(metrics, dict):
            return False

        complexity_score = metrics.get("complexity_score", 0)
        task_count = metrics.get("task_count", 0)

        return bool(
            complexity_score > 0.8
            or task_count > 40
            or (task_count > 25 and complexity_score > 0.6)
        )

    def _analyze_complexity(
        self, current_flow: Dict[str, Any]
    ) -> Optional[Recommendation]:
        """Analyze project complexity."""
        if not self.detect_high_complexity(current_flow):
            return None

        return Recommendation(
            type="phase_project",
            confidence=0.85,
            message="High complexity detected - recommend phased approach",
            impact="Reduce risk by 40%, improve manageability",
            action=lambda: self.suggest_phases(current_flow),
            supporting_data={
                "complexity_score": current_flow["metrics"]["complexity_score"],
                "task_count": current_flow["metrics"]["task_count"],
            },
        )

    def _check_task_distribution(
        self, current_flow: Dict[str, Any]
    ) -> List[Recommendation]:
        """Check task distribution for missing categories."""
        recommendations = []

        # Categorize current tasks
        task_categories: Dict[str, int] = defaultdict(int)
        for task in current_flow["tasks"]:
            name = task.get("name", "").lower()

            if any(word in name for word in ["test", "testing"]):
                task_categories["testing"] += 1
            elif any(word in name for word in ["doc", "documentation"]):
                task_categories["documentation"] += 1

        total_tasks = current_flow["metrics"]["task_count"]

        # Check testing coverage
        testing_ratio = (
            task_categories["testing"] / total_tasks if total_tasks > 0 else 0
        )
        if testing_ratio < 0.15:  # Less than 15% testing
            recommendations.append(
                Recommendation(
                    type="add_testing",
                    confidence=0.9,
                    message="Low test coverage - only {:.0%} of tasks are tests".format(
                        testing_ratio
                    ),
                    impact="Improve quality, reduce bugs by 30-50%",
                    action=lambda: self.suggest_testing_tasks(current_flow),
                )
            )

        # Check documentation
        doc_ratio = (
            task_categories["documentation"] / total_tasks if total_tasks > 0 else 0
        )
        if doc_ratio < 0.05:  # Less than 5% documentation
            recommendations.append(
                Recommendation(
                    type="add_documentation",
                    confidence=0.8,
                    message="Missing documentation tasks",
                    impact="Improve maintainability, reduce onboarding time",
                    action=lambda: self.suggest_documentation_tasks(current_flow),
                )
            )

        return recommendations

    def _analyze_decisions(self, current_flow: Dict[str, Any]) -> List[Recommendation]:
        """Analyze decisions for improvements."""
        recommendations = []
        success_factors = self.success_analyzer.analyze_success_factors()

        # Check confidence levels
        low_confidence_decisions = [
            d for d in current_flow["decisions"] if d.get("confidence", 0) < 0.7
        ]

        if low_confidence_decisions:
            recommendations.append(
                Recommendation(
                    type="review_decisions",
                    confidence=0.75,
                    message=f"{len(low_confidence_decisions)} decisions have low confidence",
                    impact="Reduce uncertainty, improve success rate",
                    supporting_data={"decisions": low_confidence_decisions},
                )
            )

        # Check against proven decisions
        proven_decisions = success_factors.get("proven_decisions", [])
        current_decision_keys = [
            f"{d['stage']}:{d['decision']}" for d in current_flow["decisions"]
        ]

        missing_proven = [
            pd for pd in proven_decisions if pd not in current_decision_keys
        ]
        if missing_proven:
            recommendations.append(
                Recommendation(
                    type="consider_proven_approaches",
                    confidence=0.7,
                    message="Consider proven approaches used in similar successful projects",
                    impact="Increase success likelihood by 20%",
                    supporting_data={"proven_approaches": missing_proven},
                )
            )

        return recommendations

    def _suggest_performance_optimizations(
        self, current_flow: Dict[str, Any]
    ) -> List[Recommendation]:
        """Suggest performance optimizations."""
        recommendations = []
        metrics = current_flow["metrics"]

        # Cost optimization
        if metrics["total_cost"] > 0.5:
            recommendations.append(
                Recommendation(
                    type="optimize_cost",
                    confidence=0.8,
                    message=f"Cost is ${metrics['total_cost']:.2f} - consider optimization",
                    impact=f"Save up to ${metrics['total_cost'] * 0.3:.2f}",
                    supporting_data={
                        "current_cost": metrics["total_cost"],
                        "suggestions": [
                            "Use GPT-3.5 for non-critical analysis",
                            "Batch API calls where possible",
                            "Cache common patterns",
                        ],
                    },
                )
            )

        # Speed optimization
        if metrics["total_duration_ms"] > 30000:  # 30 seconds
            recommendations.append(
                Recommendation(
                    type="optimize_speed",
                    confidence=0.7,
                    message="Pipeline taking {:.1f}s - can be optimized".format(
                        metrics["total_duration_ms"] / 1000
                    ),
                    impact="Reduce execution time by 30-40%",
                    supporting_data={
                        "current_duration": metrics["total_duration_ms"],
                        "suggestions": [
                            "Parallelize independent operations",
                            "Use caching for repeated patterns",
                            "Optimize AI prompts for faster responses",
                        ],
                    },
                )
            )

        return recommendations

    def apply_template(self, template_flow: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a template from a successful flow."""
        # In production, this would modify the current flow
        # For now, return template structure
        return {
            "template_applied": True,
            "source_flow": template_flow["flow_id"],
            "task_structure": template_flow["tasks"],
            "proven_decisions": template_flow["decisions"],
        }

    def suggest_phases(self, current_flow: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest project phases."""
        tasks = current_flow["tasks"]
        task_count = len(tasks)

        # Simple phase splitting
        phases = []

        if task_count > 30:
            # Split into 3 phases
            phase_size = task_count // 3
            phases = [
                {
                    "phase": "Foundation",
                    "tasks": tasks[:phase_size],
                    "focus": "Core infrastructure and setup",
                },
                {
                    "phase": "Implementation",
                    "tasks": tasks[phase_size : phase_size * 2],
                    "focus": "Main feature development",
                },
                {
                    "phase": "Polish & Deploy",
                    "tasks": tasks[phase_size * 2 :],
                    "focus": "Testing, optimization, and deployment",
                },
            ]
        else:
            # Split into 2 phases
            phase_size = task_count // 2
            phases = [
                {
                    "phase": "Core Development",
                    "tasks": tasks[:phase_size],
                    "focus": "Essential features",
                },
                {
                    "phase": "Enhancement & Deploy",
                    "tasks": tasks[phase_size:],
                    "focus": "Polish and deployment",
                },
            ]

        return phases

    def suggest_testing_tasks(
        self, current_flow: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Suggest testing tasks to add."""
        testing_tasks = []

        # Analyze existing tasks to suggest tests
        for task in current_flow["tasks"]:
            if "api" in task["name"].lower():
                testing_tasks.append(
                    {
                        "name": f"Test {task['name']}",
                        "type": "testing",
                        "priority": "high",
                    }
                )
            elif "database" in task["name"].lower():
                testing_tasks.append(
                    {
                        "name": f"Test database operations for {task['name']}",
                        "type": "testing",
                        "priority": "medium",
                    }
                )

        # Add general testing tasks
        testing_tasks.extend(
            [
                {"name": "Unit test coverage", "type": "testing", "priority": "high"},
                {"name": "Integration testing", "type": "testing", "priority": "high"},
                {
                    "name": "Performance testing",
                    "type": "testing",
                    "priority": "medium",
                },
            ]
        )

        return testing_tasks[:5]  # Return top 5 suggestions

    def suggest_documentation_tasks(
        self, current_flow: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Suggest documentation tasks."""
        return [
            {"name": "API documentation", "type": "documentation", "priority": "high"},
            {
                "name": "Setup and deployment guide",
                "type": "documentation",
                "priority": "high",
            },
            {
                "name": "Architecture documentation",
                "type": "documentation",
                "priority": "medium",
            },
            {"name": "User guide", "type": "documentation", "priority": "medium"},
        ]

    def learn_from_outcome(self, flow_id: str, outcome: ProjectOutcome) -> None:
        """
        Update patterns based on project outcome.

        Parameters
        ----------
        flow_id : str
            The flow ID that completed
        outcome : ProjectOutcome
            The actual project outcome
        """
        flow_data = self._load_flow_data(flow_id)
        if not flow_data:
            return

        if outcome.successful:
            self.pattern_db.add_success_pattern(flow_data)
        else:
            self.pattern_db.add_failure_pattern(
                flow_data, outcome.failure_reasons or []
            )

        # Update recommendation weights based on outcome
        self.update_recommendation_weights(flow_data, outcome)

    def update_recommendation_weights(
        self, flow_data: Dict[str, Any], outcome: ProjectOutcome
    ) -> None:
        """Update recommendation confidence based on outcomes."""
        # In production, this would update ML model weights
        # For now, track in pattern database

        update_record = {
            "flow_id": flow_data["flow_id"],
            "outcome": asdict(outcome),
            "timestamp": datetime.now().isoformat(),
        }

        if "optimization_rules" not in self.pattern_db.patterns:
            self.pattern_db.patterns["optimization_rules"] = []

        self.pattern_db.patterns["optimization_rules"].append(update_record)
        self.pattern_db.save_patterns()

    def export_recommendations_report(
        self, recommendations: List[Recommendation]
    ) -> str:
        """Export recommendations as formatted report."""
        report = f"""
# Pipeline Recommendations Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Recommendations:** {len(recommendations)}

## Priority Recommendations

"""

        for i, rec in enumerate(recommendations, 1):
            report += f"### {i}. {rec.message}\n"
            report += f"- **Type:** {rec.type.replace('_', ' ').title()}\n"
            report += f"- **Confidence:** {rec.confidence * 100:.0f}%\n"
            report += f"- **Expected Impact:** {rec.impact}\n"

            if rec.supporting_data:
                report += "- **Supporting Data:**\n"
                for key, value in rec.supporting_data.items():
                    report += f"  - {key}: {value}\n"

            report += "\n"

        return report

    def get_pattern_based_recommendations(
        self, project_context: Dict[str, Any]
    ) -> List[Recommendation]:
        """
        Get recommendations based on learned patterns from ProjectPatternLearner.

        Parameters
        ----------
        project_context : Dict[str, Any]
            Current project context (tasks, progress, team, etc.)

        Returns
        -------
        List[Recommendation]
            Pattern-based recommendations
        """
        if not self.pattern_learner or not self.pattern_learner.learned_patterns:
            return []

        recommendations = []

        # Find similar successful projects
        successful_patterns = [
            p
            for p in self.pattern_learner.learned_patterns
            if p.outcome.successful and p.confidence_score > 0.7
        ]

        if not successful_patterns:
            return []

        # Analyze team composition recommendations
        team_rec = self._get_team_composition_recommendation(
            project_context, successful_patterns
        )
        if team_rec:
            recommendations.append(team_rec)

        # Analyze velocity recommendations
        velocity_rec = self._get_velocity_recommendation(
            project_context, successful_patterns
        )
        if velocity_rec:
            recommendations.append(velocity_rec)

        # Analyze quality recommendations
        quality_rec = self._get_quality_recommendation(
            project_context, successful_patterns
        )
        if quality_rec:
            recommendations.append(quality_rec)

        # Analyze risk mitigation
        risk_recs = self._get_risk_mitigation_recommendations(
            project_context, self.pattern_learner.learned_patterns
        )
        recommendations.extend(risk_recs)

        return sorted(recommendations, key=lambda r: r.confidence, reverse=True)

    def _get_team_composition_recommendation(
        self, context: Dict[str, Any], patterns: List[Any]
    ) -> Optional[Recommendation]:
        """Get team composition recommendation based on successful patterns."""
        current_team_size = context.get("team_size", 0)

        # Get optimal team sizes from successful projects
        optimal_sizes = [p.team_composition["team_size"] for p in patterns]

        if not optimal_sizes:
            return None

        avg_optimal = statistics.mean(optimal_sizes)

        if abs(current_team_size - avg_optimal) > 2:
            return Recommendation(
                type="team_optimization",
                confidence=0.8,
                message=f"Consider adjusting team size to {int(avg_optimal)} members",
                impact="Improved productivity and reduced coordination overhead",
                supporting_data={
                    "current_size": current_team_size,
                    "optimal_range": f"{int(min(optimal_sizes))}-{int(max(optimal_sizes))}",
                    "successful_projects": len(patterns),
                },
            )

        return None

    def _get_velocity_recommendation(
        self, context: Dict[str, Any], patterns: List[Any]
    ) -> Optional[Recommendation]:
        """Get velocity recommendation based on successful patterns."""
        current_velocity = context.get("velocity", 0)

        # Get velocity patterns from successful projects
        target_velocities = []
        for pattern in patterns:
            if "middle" in pattern.velocity_pattern:
                target_velocities.append(pattern.velocity_pattern["middle"])

        if not target_velocities:
            return None

        avg_target = statistics.mean(target_velocities)

        if current_velocity < avg_target * 0.7:
            return Recommendation(
                type="velocity_improvement",
                confidence=0.75,
                message=f"Team velocity ({current_velocity:.1f} tasks/week) below successful project average",
                impact="Faster delivery and improved project momentum",
                supporting_data={
                    "current_velocity": current_velocity,
                    "target_velocity": f"{avg_target:.1f}",
                    "improvement_needed": f"{((avg_target - current_velocity) / current_velocity * 100):.0f}%",
                },
            )

        return None

    def _get_quality_recommendation(
        self, context: Dict[str, Any], patterns: List[Any]
    ) -> Optional[Recommendation]:
        """Get quality recommendation based on successful patterns."""
        # Extract quality metrics from successful patterns
        quality_scores = [p.outcome.quality_score for p in patterns]
        avg_quality = statistics.mean(quality_scores)

        # Key quality factors from successful projects
        key_factors = []
        for pattern in patterns:
            if pattern.quality_metrics.get("test_coverage", 0) > 0.8:
                key_factors.append("high test coverage")
            if pattern.quality_metrics.get("code_review_coverage", 0) > 0.9:
                key_factors.append("comprehensive code reviews")
            if pattern.quality_metrics.get("documentation_coverage", 0) > 0.7:
                key_factors.append("thorough documentation")

        if key_factors:
            most_common = Counter(key_factors).most_common(2)

            return Recommendation(
                type="quality_assurance",
                confidence=0.85,
                message=f"Focus on {most_common[0][0]} to achieve {avg_quality:.0%} quality score",
                impact="Higher project success rate and maintainability",
                supporting_data={
                    "success_factors": [f[0] for f in most_common],
                    "average_quality_score": f"{avg_quality:.1%}",
                    "based_on_projects": len(patterns),
                },
            )

        return None

    def _get_risk_mitigation_recommendations(
        self, context: Dict[str, Any], all_patterns: List[Any]
    ) -> List[Recommendation]:
        """Get risk mitigation recommendations from failed patterns."""
        recommendations: List[Recommendation] = []

        # Find failed patterns
        failed_patterns = [p for p in all_patterns if not p.outcome.successful]

        if not failed_patterns:
            return recommendations

        # Analyze common failure reasons
        failure_reasons = []
        for pattern in failed_patterns:
            failure_reasons.extend(pattern.risk_factors)

        common_risks = Counter(failure_reasons).most_common(3)

        for risk, count in common_risks:
            if count > len(failed_patterns) * 0.3:  # Risk appears in >30% of failures
                recommendations.append(
                    Recommendation(
                        type="risk_mitigation",
                        confidence=0.7,
                        message=f"Proactively address: {risk}",
                        impact="Reduced project failure risk",
                        supporting_data={
                            "occurrence_rate": f"{count / len(failed_patterns):.0%}",
                            "failed_projects": count,
                        },
                    )
                )

        return recommendations[:2]  # Limit to top 2 risk recommendations
