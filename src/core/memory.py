"""
Memory System for Marcus.

Multi-tier memory system that enables learning from past experiences and
predictive task assignment. Inspired by cognitive memory models with working,
episodic, semantic, and procedural memory layers.
"""

import asyncio
import logging
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.core.events import Events, EventTypes
from src.core.models import Task
from src.core.persistence import Persistence

logger = logging.getLogger(__name__)


@dataclass
class TaskOutcome:
    """Record of a task execution outcome."""

    task_id: str
    agent_id: str
    task_name: str
    estimated_hours: float
    actual_hours: float
    success: bool
    blockers: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def estimation_accuracy(self) -> float:
        """Calculate how accurate the time estimate was."""
        if self.estimated_hours == 0:
            return 0.0
        return min(self.estimated_hours, self.actual_hours) / max(
            self.estimated_hours, self.actual_hours
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "task_name": self.task_name,
            "estimated_hours": self.estimated_hours,
            "actual_hours": self.actual_hours,
            "success": self.success,
            "blockers": self.blockers,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "estimation_accuracy": self.estimation_accuracy,
        }


@dataclass
class AgentProfile:
    """Learned profile of an agent's capabilities."""

    agent_id: str
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    blocked_tasks: int = 0
    skill_success_rates: Dict[str, float] = field(default_factory=dict)
    average_estimation_accuracy: float = 0.0
    common_blockers: Dict[str, int] = field(default_factory=dict)
    peak_performance_hours: List[int] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Overall success rate."""
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks

    @property
    def blockage_rate(self) -> float:
        """Rate of encountering blockers."""
        if self.total_tasks == 0:
            return 0.0
        return self.blocked_tasks / self.total_tasks


@dataclass
class TaskPattern:
    """Learned pattern about task types."""

    pattern_type: str
    task_labels: List[str]
    recent_durations: List[float]  # Last N actual_hours (for median calculation)
    success_rate: float
    common_blockers: List[str]
    prerequisites: List[str]
    best_agents: List[str]
    max_samples: int = 100  # Keep last 100 samples for median

    @property
    def median_duration(self) -> float:
        """Calculate median duration from recent samples."""
        if not self.recent_durations:
            return 0.0
        sorted_durations = sorted(self.recent_durations)
        n = len(sorted_durations)
        if n % 2 == 0:
            return (sorted_durations[n // 2 - 1] + sorted_durations[n // 2]) / 2
        else:
            return sorted_durations[n // 2]

    @property
    def average_duration(self) -> float:
        """Calculate average duration (for backward compatibility)."""
        if not self.recent_durations:
            return 0.0
        return sum(self.recent_durations) / len(self.recent_durations)


class Memory:
    """
    Multi-tier memory system for Marcus.

    Tiers:
    - Working Memory: Current state and active tasks
    - Episodic Memory: Specific task execution records
    - Semantic Memory: Extracted facts and patterns
    - Procedural Memory: Learned workflows and strategies
    """

    def __init__(
        self, events: Optional[Events] = None, persistence: Optional[Persistence] = None
    ):
        """
        Initialize the Memory system.

        Parameters
        ----------
            events
                Optional Events system for integration.
            persistence
                Optional Persistence for long-term storage.
        """
        self.events = events
        self.persistence = persistence

        # Working Memory (volatile, current state)
        self.working: Dict[str, Any] = {
            "active_tasks": {},  # agent_id -> current task
            "recent_events": [],  # last N events
            "system_state": {},  # current system metrics
        }

        # Episodic Memory (task execution history)
        self.episodic: Dict[str, Any] = {
            "outcomes": [],  # List of TaskOutcome
            "timeline": defaultdict(list),  # date -> events
        }

        # Semantic Memory (learned facts)
        self.semantic: Dict[str, Any] = {
            "agent_profiles": {},  # agent_id -> AgentProfile
            "task_patterns": {},  # pattern_id -> TaskPattern
            "success_factors": {},  # factor -> impact
        }

        # Procedural Memory (workflows and strategies)
        self.procedural: Dict[str, Any] = {
            "workflows": {},  # workflow_id -> steps
            "strategies": {},  # situation -> strategy
            "optimizations": {},  # pattern -> optimization
        }

        # Learning parameters
        self.learning_rate = 0.1
        self.memory_decay = 0.95  # How much to weight recent vs old experiences

        # Load persisted memory if available
        if self.persistence:
            asyncio.create_task(self._load_persisted_memory())

    async def _load_persisted_memory(self) -> None:
        """Load memory from persistence."""
        try:
            # Load recent outcomes
            if self.persistence:
                outcomes_data = await self.persistence.query("task_outcomes", limit=500)
            else:
                outcomes_data = []
            for data in outcomes_data:
                # Reconstruct TaskOutcome
                outcome = TaskOutcome(
                    task_id=data["task_id"],
                    agent_id=data["agent_id"],
                    task_name=data["task_name"],
                    estimated_hours=data["estimated_hours"],
                    actual_hours=data["actual_hours"],
                    success=data["success"],
                    blockers=data.get("blockers", []),
                    started_at=(
                        datetime.fromisoformat(data["started_at"])
                        if data.get("started_at")
                        else None
                    ),
                    completed_at=(
                        datetime.fromisoformat(data["completed_at"])
                        if data.get("completed_at")
                        else None
                    ),
                )
                self.episodic["outcomes"].append(outcome)

            # Load agent profiles
            if self.persistence:
                profiles_data = await self.persistence.query(
                    "agent_profiles", limit=100
                )
            else:
                profiles_data = []
            for data in profiles_data:
                # Filter out internal fields (like _key) that Redis adds
                profile_data = {k: v for k, v in data.items() if not k.startswith("_")}
                self.semantic["agent_profiles"][data["agent_id"]] = AgentProfile(
                    **profile_data
                )

            logger.info(
                f"Loaded {len(self.episodic['outcomes'])} outcomes and "
                f"{len(self.semantic['agent_profiles'])} profiles from memory"
            )

        except Exception as e:
            logger.error(f"Failed to load persisted memory: {e}")

    async def record_task_start(self, agent_id: str, task: Task) -> None:
        """Record that an agent started a task."""
        # Update working memory
        self.working["active_tasks"][agent_id] = {
            "task": task,
            "started_at": datetime.now(),
            "events": [],
        }

        # Emit event
        if self.events:
            await self.events.publish(
                EventTypes.TASK_STARTED,
                agent_id,
                {
                    "task_id": task.id,
                    "task_name": task.name,
                    "estimated_hours": task.estimated_hours,
                },
            )

    async def record_task_completion(
        self,
        agent_id: str,
        task_id: str,
        success: bool,
        actual_hours: float,
        blockers: Optional[List[str]] = None,
    ) -> Optional[TaskOutcome]:
        """Record task completion and learn from it."""
        # Get task info from working memory
        active_task = self.working["active_tasks"].get(agent_id, {})
        if not active_task or active_task["task"].id != task_id:
            logger.warning(f"No active task found for agent {agent_id}")
            return None

        task = active_task["task"]
        started_at = active_task["started_at"]

        # Create outcome record
        outcome = TaskOutcome(
            task_id=task_id,
            agent_id=agent_id,
            task_name=task.name,
            estimated_hours=task.estimated_hours,
            actual_hours=actual_hours,
            success=success,
            blockers=blockers or [],
            started_at=started_at,
            completed_at=datetime.now(),
        )

        # Store in episodic memory
        self.episodic["outcomes"].append(outcome)
        self.episodic["timeline"][datetime.now().date()].append(outcome)

        # Update semantic memory (agent profile)
        await self._update_agent_profile(agent_id, outcome, task)

        # Learn patterns
        await self._learn_task_patterns(outcome, task)

        # Persist if available
        if self.persistence:
            await self.persistence.store(
                "task_outcomes",
                f"{task_id}_{agent_id}_{datetime.now().timestamp()}",
                outcome.to_dict(),
            )

        # Clear from working memory
        del self.working["active_tasks"][agent_id]

        # Emit event
        if self.events:
            await self.events.publish(
                EventTypes.TASK_COMPLETED, agent_id, outcome.to_dict()
            )

        return outcome

    async def _update_agent_profile(
        self, agent_id: str, outcome: TaskOutcome, task: Task
    ) -> None:
        """Update agent's learned profile."""
        if agent_id not in self.semantic["agent_profiles"]:
            self.semantic["agent_profiles"][agent_id] = AgentProfile(agent_id=agent_id)

        profile = self.semantic["agent_profiles"][agent_id]

        # Update basic stats
        profile.total_tasks += 1
        if outcome.success:
            profile.successful_tasks += 1
        else:
            profile.failed_tasks += 1

        if outcome.blockers:
            profile.blocked_tasks += 1
            for blocker in outcome.blockers:
                profile.common_blockers[blocker] = (
                    profile.common_blockers.get(blocker, 0) + 1
                )

        # Update skill success rates
        if task.labels:
            for label in task.labels:
                if label not in profile.skill_success_rates:
                    profile.skill_success_rates[label] = 0.0

                # Exponential moving average
                old_rate = profile.skill_success_rates[label]
                new_value = 1.0 if outcome.success else 0.0
                profile.skill_success_rates[label] = (
                    old_rate * (1 - self.learning_rate) + new_value * self.learning_rate
                )

        # Update estimation accuracy
        old_accuracy = profile.average_estimation_accuracy
        profile.average_estimation_accuracy = (
            old_accuracy * (1 - self.learning_rate)
            + outcome.estimation_accuracy * self.learning_rate
        )

        # Persist profile
        if self.persistence:
            await self.persistence.store("agent_profiles", agent_id, profile.__dict__)

    async def _learn_task_patterns(self, outcome: TaskOutcome, task: Task) -> None:
        """Learn patterns from task execution."""
        # Pattern key based on task labels
        if task.labels:
            pattern_key = "_".join(sorted(task.labels))

            if pattern_key not in self.semantic["task_patterns"]:
                self.semantic["task_patterns"][pattern_key] = TaskPattern(
                    pattern_type=pattern_key,
                    task_labels=task.labels,
                    recent_durations=[outcome.actual_hours],
                    success_rate=1.0 if outcome.success else 0.0,
                    common_blockers=outcome.blockers,
                    prerequisites=[],
                    best_agents=[outcome.agent_id] if outcome.success else [],
                )
            else:
                pattern = self.semantic["task_patterns"][pattern_key]

                # Append new duration and keep last max_samples
                pattern.recent_durations.append(outcome.actual_hours)
                if len(pattern.recent_durations) > pattern.max_samples:
                    pattern.recent_durations = pattern.recent_durations[
                        -pattern.max_samples :
                    ]

                # Update success rate (exponential moving average)
                pattern.success_rate = (
                    pattern.success_rate * 0.9 + (1.0 if outcome.success else 0.0) * 0.1
                )

                # Track successful agents
                if outcome.success and outcome.agent_id not in pattern.best_agents:
                    pattern.best_agents.append(outcome.agent_id)

    async def predict_task_outcome(self, agent_id: str, task: Task) -> Dict[str, Any]:
        """
        Predict likely outcome for agent-task combination.

        Returns
        -------
            Dictionary with predictions:
            - success_probability: 0-1
            - estimated_duration: hours
            - blockage_risk: 0-1
            - risk_factors: list of potential issues
        """
        predictions: Dict[str, Any] = {
            "success_probability": 0.5,  # Default
            "estimated_duration": task.estimated_hours,
            "blockage_risk": 0.3,
            "risk_factors": [],
        }

        # Get agent profile
        if agent_id in self.semantic["agent_profiles"]:
            profile = self.semantic["agent_profiles"][agent_id]

            # Base success probability on agent's overall rate
            predictions["success_probability"] = profile.success_rate

            # Adjust based on skill match
            if task.labels:
                skill_matches = [
                    profile.skill_success_rates.get(label, 0.5) for label in task.labels
                ]
                if skill_matches:
                    predictions["success_probability"] = sum(skill_matches) / len(
                        skill_matches
                    )

            # Predict blockage risk
            predictions["blockage_risk"] = profile.blockage_rate

            # Duration adjustment based on estimation accuracy
            if profile.average_estimation_accuracy > 0:
                predictions["estimated_duration"] = (
                    task.estimated_hours / profile.average_estimation_accuracy
                )

        # Check task patterns
        if task.labels:
            pattern_key = "_".join(sorted(task.labels))
            if pattern_key in self.semantic["task_patterns"]:
                pattern = self.semantic["task_patterns"][pattern_key]

                # Use pattern median (more robust to outliers than average)
                predictions["estimated_duration"] = pattern.median_duration
                if isinstance(pattern.common_blockers, list):
                    risk_factors = predictions["risk_factors"]
                    if isinstance(risk_factors, list):
                        risk_factors.extend(pattern.common_blockers)

        return predictions

    async def predict_completion_time(
        self, agent_id: str, task: Task
    ) -> Dict[str, Any]:
        """
        Predict task completion time with confidence intervals.

        Returns
        -------
            Dictionary with:
            - expected_hours: Most likely duration
            - confidence_interval: {lower, upper} bounds
            - factors: What influences the prediction
            - confidence: Overall confidence in prediction (0-1)
        """
        # Get base prediction
        base_pred = await self.predict_task_outcome(agent_id, task)
        expected_hours = base_pred["estimated_duration"]

        # Calculate confidence based on historical data
        similar_outcomes = await self.find_similar_outcomes(task, limit=10)
        agent_outcomes = [o for o in similar_outcomes if o.agent_id == agent_id]

        confidence = 0.5  # Default medium confidence
        variance_factor = 0.3  # Default 30% variance

        if len(agent_outcomes) >= 5:
            # High confidence with agent-specific data
            confidence = 0.8
            # Calculate actual variance from history
            durations = [o.actual_hours for o in agent_outcomes]
            avg_duration = sum(durations) / len(durations)
            variance = sum((d - avg_duration) ** 2 for d in durations) / len(durations)
            variance_factor = (
                (variance**0.5) / avg_duration if avg_duration > 0 else 0.3
            )

        elif len(similar_outcomes) >= 3:
            # Medium confidence with similar tasks
            confidence = 0.6
            variance_factor = 0.25

        # Calculate confidence interval
        lower_bound = expected_hours * (1 - variance_factor)
        upper_bound = expected_hours * (1 + variance_factor)

        # Identify influencing factors
        factors = []
        if base_pred["blockage_risk"] > 0.5:
            factors.append(f"High blockage risk ({base_pred['blockage_risk']:.0%})")

        profile = self.semantic["agent_profiles"].get(agent_id)
        if profile and profile.average_estimation_accuracy < 0.8:
            factors.append(
                f"Agent tends to underestimate "
                f"({profile.average_estimation_accuracy:.0%} accuracy)"
            )

        # Time of day factor
        current_hour = datetime.now().hour
        if current_hour >= 15:  # After 3 PM
            factors.append("Late day tasks often take longer")
            upper_bound *= 1.1

        return {
            "expected_hours": expected_hours,
            "confidence_interval": {
                "lower": max(0.5, lower_bound),
                "upper": upper_bound,
            },
            "factors": factors,
            "confidence": confidence,
            "sample_size": len(agent_outcomes),
        }

    def get_median_duration_by_type(self, task_type: str) -> Optional[float]:
        """
        Get median task duration for a given task type.

        Parameters
        ----------
        task_type : str
            Task type label (e.g., "design", "implement", "test")

        Returns
        -------
        Optional[float]
            Median duration in hours, or None if no data available

        Examples
        --------
        >>> memory.get_median_duration_by_type("design")
        0.1  # 6 minutes

        Notes
        -----
        Uses median instead of average to be robust to outliers
        (tasks that sat for hours waiting for user input, etc.)
        """
        # Try exact match first
        if task_type in self.semantic["task_patterns"]:
            pattern: TaskPattern = self.semantic["task_patterns"][task_type]
            if pattern.recent_durations:
                median: float = pattern.median_duration
                return median

        # Try patterns that contain this task type
        for pattern_key, pattern_obj in self.semantic["task_patterns"].items():
            pattern_typed: TaskPattern = pattern_obj
            if task_type in pattern_key.split("_"):
                if pattern_typed.recent_durations:
                    median_val: float = pattern_typed.median_duration
                    return median_val

        return None

    async def predict_blockage_probability(
        self, agent_id: str, task: Task
    ) -> Dict[str, Any]:
        """
        Predict likelihood and types of blockages.

        Returns
        -------
            Dictionary with:
            - overall_risk: 0-1 probability
            - risk_breakdown: Dict of blockage type to probability
            - preventive_measures: Suggested actions to reduce risk
            - historical_blockers: Common blockers for similar tasks
        """
        profile = self.semantic["agent_profiles"].get(agent_id, None)

        # Initialize risk assessment
        risk_breakdown = {}
        preventive_measures = []

        # Base blockage risk
        base_risk = profile.blockage_rate if profile else 0.3

        # Analyze task-specific risks
        if task.labels:
            # Check for high-risk labels
            risk_labels = {
                "integration": 0.4,
                "deployment": 0.35,
                "migration": 0.5,
                "authentication": 0.45,
                "third-party": 0.55,
            }

            for label in task.labels:
                label_lower = label.lower()
                for risk_label, risk_value in risk_labels.items():
                    if risk_label in label_lower:
                        risk_breakdown[f"{risk_label}_complexity"] = risk_value

        # Check dependency risks
        if task.dependencies:
            dep_count = len(task.dependencies)
            if dep_count > 3:
                risk_breakdown["multiple_dependencies"] = 0.3 + (dep_count * 0.05)
                preventive_measures.append(
                    "Verify all dependencies are complete before starting"
                )

        # Agent-specific risks
        if profile and profile.common_blockers:
            for blocker, count in profile.common_blockers.items():
                frequency = (
                    count / profile.total_tasks if profile.total_tasks > 0 else 0
                )
                if frequency > 0.1:  # More than 10% occurrence
                    risk_breakdown[blocker] = frequency

        # Historical blockers from similar tasks
        similar_outcomes = await self.find_similar_outcomes(task, limit=20)
        historical_blockers: Dict[str, int] = {}
        for outcome in similar_outcomes:
            for blocker in outcome.blockers:
                historical_blockers[blocker] = historical_blockers.get(blocker, 0) + 1

        # Sort by frequency
        historical_blockers = dict(
            sorted(historical_blockers.items(), key=lambda x: x[1], reverse=True)[:5]
        )

        # Calculate overall risk
        if risk_breakdown:
            # Combine risks (not simply additive - use probability theory)
            combined_risk = 1.0
            for risk in risk_breakdown.values():
                combined_risk *= 1 - risk
            overall_risk = 1 - combined_risk
        else:
            overall_risk = base_risk

        # Generate preventive measures based on risks
        if "authentication_complexity" in risk_breakdown:
            preventive_measures.append(
                "Ensure API credentials and auth documentation are available"
            )
        if "integration_complexity" in risk_breakdown:
            preventive_measures.append(
                "Review integration points and API contracts before starting"
            )
        if "multiple_dependencies" in risk_breakdown:
            preventive_measures.append(
                "Check dependency completion status and interfaces"
            )

        return {
            "overall_risk": min(0.95, overall_risk),  # Cap at 95%
            "risk_breakdown": risk_breakdown,
            "preventive_measures": preventive_measures,
            "historical_blockers": historical_blockers,
        }

    async def predict_cascade_effects(
        self, task_id: str, delay_hours: float
    ) -> Dict[str, Any]:
        """
        Predict impact of task delay on dependent tasks.

        Returns
        -------
            Dictionary with:
            - affected_tasks: List of tasks that will be impacted
            - total_delay: Cumulative delay across all tasks
            - critical_path_impact: Whether this affects project completion
            - mitigation_options: Ways to reduce impact
        """
        affected_tasks = []
        total_delay = delay_hours

        # Get all tasks from project (need to be passed in or stored)
        all_tasks = self.working.get("all_tasks", [])

        # If no tasks stored, try to get from persistence
        if not all_tasks and self.persistence:
            try:
                task_data = await self.persistence.query("project_tasks", limit=1000)
                all_tasks = task_data
            except Exception as e:
                logger.warning(
                    "Failed to retrieve tasks from persistence for "
                    "dependency analysis: %s",
                    str(e),
                )
                all_tasks = []

        # Build dependency map
        dependency_map = defaultdict(list)
        task_map = {}
        for task in all_tasks:
            task_map[task.id if hasattr(task, "id") else task.get("id")] = task
            deps = (
                task.dependencies
                if hasattr(task, "dependencies")
                else task.get("dependencies", [])
            )
            for dep in deps:
                dependency_map[dep].append(
                    task.id if hasattr(task, "id") else task.get("id")
                )

        # Calculate cascade effect using BFS
        visited = set()
        to_process = [(task_id, delay_hours)]

        while to_process:
            current_id, current_delay = to_process.pop(0)
            if current_id in visited:
                continue

            visited.add(current_id)

            # Find tasks depending on current task
            for dependent_id in dependency_map.get(current_id, []):
                if dependent_id not in visited and dependent_id in task_map:
                    dependent_task = task_map[dependent_id]

                    # Estimate propagated delay (may be less than full delay)
                    propagation_factor = 0.8  # 80% of delay propagates
                    propagated_delay = current_delay * propagation_factor

                    task_name = (
                        dependent_task.name
                        if hasattr(dependent_task, "name")
                        else dependent_task.get("name", "Unknown")
                    )

                    affected_tasks.append(
                        {
                            "task_id": dependent_id,
                            "task_name": task_name,
                            "delay_hours": propagated_delay,
                            "new_start": datetime.now()
                            + timedelta(hours=propagated_delay),
                        }
                    )

                    total_delay += propagated_delay
                    to_process.append((dependent_id, propagated_delay))

        # Determine critical path impact
        critical_path_impact = len(affected_tasks) > 3 or total_delay > 24

        # Suggest mitigation options
        mitigation_options = []
        if len(affected_tasks) > 2:
            mitigation_options.append(
                "Consider parallel execution of independent dependent tasks"
            )
        if total_delay > 16:
            mitigation_options.append("Allocate additional agents to affected tasks")
        if critical_path_impact:
            mitigation_options.append("Re-prioritize to focus on critical path tasks")

        return {
            "affected_tasks": affected_tasks,
            "total_delay": total_delay,
            "critical_path_impact": critical_path_impact,
            "mitigation_options": mitigation_options,
        }

    async def calculate_agent_performance_trajectory(
        self, agent_id: str
    ) -> Dict[str, Any]:
        """
        Calculate agent's skill development trajectory.

        Returns
        -------
            Dictionary with:
            - current_skills: Current skill levels
            - improving_skills: Skills showing improvement
            - struggling_skills: Skills needing attention
            - projected_skills: Predicted skill levels in 30 days
            - recommendations: Training/task recommendations
        """
        profile = self.semantic["agent_profiles"].get(agent_id)
        if not profile:
            return {
                "error": "No profile found for agent",
                "recommendations": ["Complete more tasks to build performance history"],
            }

        # Analyze recent performance trends
        recent_outcomes = [
            o
            for o in self.episodic["outcomes"]
            if o.agent_id == agent_id
            and o.completed_at
            and (datetime.now() - o.completed_at).days <= 30
        ]

        # Group by skill/label
        skill_performance = defaultdict(list)
        for outcome in recent_outcomes:
            task = next(
                (
                    t
                    for t in self.working.get("all_tasks", [])
                    if t.id == outcome.task_id
                ),
                None,
            )
            if task and task.labels:
                for label in task.labels:
                    skill_performance[label].append(
                        {
                            "success": outcome.success,
                            "efficiency": outcome.estimation_accuracy,
                            "date": outcome.completed_at,
                        }
                    )

        # Calculate trajectories
        current_skills = {}
        improving_skills = {}
        struggling_skills = {}
        projected_skills = {}

        for skill, performances in skill_performance.items():
            if len(performances) < 2:
                continue

            # Sort by date
            performances.sort(key=lambda x: x["date"])

            # Current skill level
            recent_success_rate = sum(
                1 for p in performances[-5:] if p["success"]
            ) / min(5, len(performances))
            current_skills[skill] = recent_success_rate

            # Calculate trend (simple linear regression would be better)
            if len(performances) >= 3:
                first_half = performances[: len(performances) // 2]
                second_half = performances[len(performances) // 2 :]

                first_rate = sum(1 for p in first_half if p["success"]) / len(
                    first_half
                )
                second_rate = sum(1 for p in second_half if p["success"]) / len(
                    second_half
                )

                improvement = second_rate - first_rate

                if improvement > 0.1:
                    improving_skills[skill] = improvement
                elif improvement < -0.1:
                    struggling_skills[skill] = improvement

                # Simple projection (could use more sophisticated methods)
                projected_rate = second_rate + (
                    improvement * 0.5
                )  # Conservative projection
                projected_skills[skill] = max(0, min(1, projected_rate))

        # Generate recommendations
        recommendations = []

        # For improving skills
        for skill, improvement in improving_skills.items():
            recommendations.append(
                f"Continue building on {skill} skills - "
                f"showing {improvement:.0%} improvement"
            )

        # For struggling skills
        for skill, decline in struggling_skills.items():
            recommendations.append(
                f"Provide additional support for {skill} tasks - "
                f"performance declining"
            )

        # For consistent high performers
        high_performers = [s for s, r in current_skills.items() if r > 0.85]
        if high_performers:
            recommendations.append(
                f"Consider more complex {', '.join(high_performers[:2])} tasks"
            )

        return {
            "current_skills": current_skills,
            "improving_skills": improving_skills,
            "struggling_skills": struggling_skills,
            "projected_skills": projected_skills,
            "recommendations": recommendations,
            "sample_size": len(recent_outcomes),
        }

    async def find_similar_outcomes(
        self, task: Task, limit: int = 5
    ) -> List[TaskOutcome]:
        """Find similar past task executions."""
        similar = []

        for outcome in reversed(self.episodic["outcomes"]):  # Recent first
            # Simple similarity based on task name and labels
            similarity = 0.0

            # Name similarity (simple word overlap)
            task_words = set(task.name.lower().split())
            outcome_words = set(outcome.task_name.lower().split())
            if task_words and outcome_words:
                similarity += len(task_words & outcome_words) / len(
                    task_words | outcome_words
                )

            similar.append((similarity, outcome))

        # Sort by similarity and return top N
        similar.sort(key=lambda x: x[0], reverse=True)
        return [outcome for _, outcome in similar[:limit]]

    async def get_global_median_duration(self) -> float:
        """
        Get the global median task duration from all completed tasks.

        Returns
        -------
        float
            Median task duration in hours. Returns 1.0 if no historical data.

        Notes
        -----
        Uses SQL-based median calculation for efficiency and scalability.
        Queries ALL historical data from persistence layer, not just in-memory cache.
        Uses median instead of mean to be more robust to outliers.
        """
        # Prefer persistence layer calculation (SQL-based, more efficient)
        if self.persistence and hasattr(
            self.persistence.backend, "calculate_median_task_duration"
        ):
            try:
                median_hours = float(
                    await self.persistence.backend.calculate_median_task_duration()
                )
                logger.debug(
                    f"Global median duration from persistence: {median_hours:.2f} hours"
                )
                return median_hours
            except Exception as e:
                logger.warning(
                    f"Failed to calculate median from persistence: {e}, "
                    "falling back to in-memory calculation"
                )

        # Fallback: in-memory calculation (less efficient, limited to loaded outcomes)
        outcomes = self.episodic.get("outcomes", [])

        if not outcomes:
            logger.debug("No historical task outcomes - returning default 1.0 hours")
            return 1.0

        # Filter to successful completions only
        successful_outcomes = [o for o in outcomes if o.success and o.actual_hours > 0]

        if not successful_outcomes:
            logger.debug(
                "No successful outcomes with duration - returning default 1.0 hours"
            )
            return 1.0

        # Calculate median (more robust to outliers than mean)
        durations = [o.actual_hours for o in successful_outcomes]
        median_hours = float(statistics.median(durations))

        logger.debug(
            f"In-memory median duration: {median_hours:.2f} hours "
            f"(from {len(successful_outcomes)} successful tasks)"
        )

        return median_hours

    def get_working_memory_summary(self) -> Dict[str, Any]:
        """Get current working memory state."""
        return {
            "active_agents": len(self.working["active_tasks"]),
            "active_tasks": [
                {
                    "agent_id": agent_id,
                    "task_name": info["task"].name,
                    "duration": (datetime.now() - info["started_at"]).total_seconds()
                    / 3600,
                }
                for agent_id, info in self.working["active_tasks"].items()
            ],
        }

    def update_project_tasks(self, tasks: List[Task]) -> None:
        """Update working memory with current project tasks for cascade analysis."""
        self.working["all_tasks"] = tasks
        logger.info(f"Updated working memory with {len(tasks)} project tasks")

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        return {
            "working_memory": {
                "active_tasks": len(self.working["active_tasks"]),
                "recent_events": len(self.working["recent_events"]),
                "project_tasks": len(self.working.get("all_tasks", [])),
            },
            "episodic_memory": {
                "total_outcomes": len(self.episodic["outcomes"]),
                "days_tracked": len(self.episodic["timeline"]),
            },
            "semantic_memory": {
                "agent_profiles": len(self.semantic["agent_profiles"]),
                "task_patterns": len(self.semantic["task_patterns"]),
            },
            "procedural_memory": {
                "workflows": len(self.procedural["workflows"]),
                "strategies": len(self.procedural["strategies"]),
            },
        }
