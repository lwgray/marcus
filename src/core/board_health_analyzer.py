"""
Board Health Analyzer for detecting project-level deadlocks and bottlenecks.

This module analyzes the overall health of the project board by detecting:
- Skill mismatches between available tasks and agent capabilities
- Circular dependencies that create deadlocks
- Bottleneck tasks that block many others
- Chain blocks where sequential dependencies create long waits
"""

import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from src.core.models import Task, TaskStatus, WorkerStatus
from src.integrations.kanban_interface import KanbanInterface

logger = logging.getLogger(__name__)


class HealthIssueType(Enum):
    """Types of board health issues."""

    SKILL_MISMATCH = "skill_mismatch"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    BOTTLENECK = "bottleneck"
    CHAIN_BLOCK = "chain_block"
    STALE_TASKS = "stale_tasks"
    OVERLOADED_AGENTS = "overloaded_agents"
    IDLE_AGENTS = "idle_agents"


class IssueSeverity(Enum):
    """Severity levels for health issues."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class HealthIssue:
    """Represents a board health issue."""

    type: HealthIssueType
    severity: IssueSeverity
    description: str
    affected_tasks: List[str]
    affected_agents: List[str]
    recommendations: List[str]
    details: Dict[str, Any]


@dataclass
class BoardHealth:
    """Overall board health assessment."""

    health_score: float  # 0-100
    issues: List[HealthIssue]
    metrics: Dict[str, Any]
    recommendations: List[str]
    timestamp: datetime


class BoardHealthAnalyzer:
    """Analyzes board-level health and detects various types of deadlocks."""

    def __init__(
        self,
        kanban_client: KanbanInterface,
        stale_task_days: int = 7,
        max_tasks_per_agent: int = 3,
    ):
        """
        Initialize the board health analyzer.

        Args:
            kanban_client: Interface to kanban board
            stale_task_days: Days before considering a task stale
            max_tasks_per_agent: Maximum recommended tasks per agent
        """
        self.kanban_client = kanban_client
        self.stale_task_days = stale_task_days
        self.max_tasks_per_agent = max_tasks_per_agent

    async def analyze_board_health(
        self,
        agents: Dict[str, WorkerStatus],
        active_assignments: Dict[str, str],  # agent_id -> task_id
    ) -> BoardHealth:
        """
        Perform comprehensive board health analysis.

        Args:
            agents: Dictionary of active agents
            active_assignments: Current task assignments

        Returns:
            BoardHealth object with analysis results
        """
        logger.info("Starting board health analysis")

        # Get all tasks
        all_tasks = await self.kanban_client.get_all_tasks()

        # Perform various health checks
        issues = []

        # Check for skill mismatches
        skill_issues = await self._detect_skill_mismatches(all_tasks, agents)
        issues.extend(skill_issues)

        # Check for circular dependencies
        circular_deps = await self._detect_circular_dependencies(all_tasks)
        issues.extend(circular_deps)

        # Check for bottlenecks
        bottlenecks = await self._detect_bottlenecks(all_tasks)
        issues.extend(bottlenecks)

        # Check for chain blocks
        chain_blocks = await self._detect_chain_blocks(all_tasks, active_assignments)
        issues.extend(chain_blocks)

        # Check for stale tasks
        stale_tasks = await self._detect_stale_tasks(all_tasks)
        issues.extend(stale_tasks)

        # Check agent workload
        workload_issues = await self._analyze_agent_workload(agents, active_assignments)
        issues.extend(workload_issues)

        # Calculate metrics
        metrics = self._calculate_health_metrics(all_tasks, agents, issues)

        # Generate overall recommendations
        recommendations = self._generate_overall_recommendations(issues, metrics)

        # Calculate health score
        health_score = self._calculate_health_score(issues, metrics)

        return BoardHealth(
            health_score=health_score,
            issues=issues,
            metrics=metrics,
            recommendations=recommendations,
            timestamp=datetime.now(),
        )

    async def _detect_skill_mismatches(
        self, tasks: List[Task], agents: Dict[str, WorkerStatus]
    ) -> List[HealthIssue]:
        """Detect tasks that cannot be handled by available agents."""
        issues = []

        # Get available skills from all agents
        available_skills = set()
        for agent in agents.values():
            available_skills.update(agent.skills)

        # Find unassigned tasks
        unassigned_tasks = [t for t in tasks if t.status == TaskStatus.TODO]

        # Check each unassigned task for skill requirements
        unmatchable_tasks = []
        skill_gaps = defaultdict(list)

        for task in unassigned_tasks:
            # Extract required skills from labels/description
            required_skills = self._extract_required_skills(task)

            # Check if any agent can handle this task
            can_handle = False
            for agent in agents.values():
                if any(skill in agent.skills for skill in required_skills):
                    can_handle = True
                    break

            if not can_handle and required_skills:
                unmatchable_tasks.append(task)
                for skill in required_skills:
                    if skill not in available_skills:
                        skill_gaps[skill].append(task.id)

        if unmatchable_tasks:
            severity = (
                IssueSeverity.HIGH
                if len(unmatchable_tasks) > 3
                else IssueSeverity.MEDIUM
            )

            issue = HealthIssue(
                type=HealthIssueType.SKILL_MISMATCH,
                severity=severity,
                description=f"{len(unmatchable_tasks)} tasks cannot be assigned due to skill mismatches",
                affected_tasks=[t.id for t in unmatchable_tasks],
                affected_agents=[],
                recommendations=[
                    f"Add agent with skills: {', '.join(skill_gaps.keys())}",
                    "Consider reassigning tasks to match available skills",
                    "Update task requirements to be more flexible",
                ],
                details={
                    "missing_skills": dict(skill_gaps),
                    "available_skills": list(available_skills),
                },
            )
            issues.append(issue)

        return issues

    async def _detect_circular_dependencies(
        self, tasks: List[Task]
    ) -> List[HealthIssue]:
        """Detect circular dependencies using DFS."""
        issues = []

        # Build dependency graph
        task_map = {t.id: t for t in tasks}
        graph = defaultdict(list)

        for task in tasks:
            if task.dependencies:
                for dep_id in task.dependencies:
                    graph[dep_id].append(task.id)

        # Find cycles using DFS
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph[node]:
                if neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:]
                    cycles.append(cycle)
                elif neighbor not in visited:
                    dfs(neighbor, path.copy())

            rec_stack.remove(node)

        # Check each task
        for task_id in task_map:
            if task_id not in visited:
                dfs(task_id, [])

        # Create issues for cycles
        for cycle in cycles:
            issue = HealthIssue(
                type=HealthIssueType.CIRCULAR_DEPENDENCY,
                severity=IssueSeverity.CRITICAL,
                description=f"Circular dependency detected: {' -> '.join(cycle)} -> {cycle[0]}",
                affected_tasks=cycle,
                affected_agents=[],
                recommendations=[
                    "Break the circular dependency by removing one of the links",
                    "Restructure tasks to avoid mutual dependencies",
                    "Consider merging related tasks",
                ],
                details={"cycle": cycle, "cycle_length": len(cycle)},
            )
            issues.append(issue)

        return issues

    async def _detect_bottlenecks(self, tasks: List[Task]) -> List[HealthIssue]:
        """Detect tasks that block many others."""
        issues = []

        # Count how many tasks depend on each task
        blocking_count = defaultdict(int)
        blocked_by = defaultdict(list)

        for task in tasks:
            if task.dependencies:
                for dep_id in task.dependencies:
                    blocking_count[dep_id] += 1
                    blocked_by[dep_id].append(task.id)

        # Find tasks blocking more than threshold
        bottleneck_threshold = 3
        bottlenecks = []

        for task_id, count in blocking_count.items():
            if count >= bottleneck_threshold:
                task = next((t for t in tasks if t.id == task_id), None)
                if task and task.status != TaskStatus.DONE:
                    bottlenecks.append(
                        {
                            "task_id": task_id,
                            "task_name": task.name if task else "Unknown",
                            "blocking_count": count,
                            "blocked_tasks": blocked_by[task_id],
                            "status": task.status if task else "Unknown",
                        }
                    )

        if bottlenecks:
            # Sort by blocking count
            bottlenecks.sort(key=lambda x: x["blocking_count"], reverse=True)

            for bottleneck in bottlenecks:
                severity = (
                    IssueSeverity.CRITICAL
                    if bottleneck["blocking_count"] > 5
                    else IssueSeverity.HIGH
                )

                issue = HealthIssue(
                    type=HealthIssueType.BOTTLENECK,
                    severity=severity,
                    description=(
                        f"Task '{bottleneck['task_name']}' blocks "
                        f"{bottleneck['blocking_count']} other tasks"
                    ),
                    affected_tasks=[bottleneck["task_id"]]
                    + bottleneck["blocked_tasks"],
                    affected_agents=[],
                    recommendations=[
                        f"Prioritize completion of task {bottleneck['task_id']}",
                        "Consider breaking down the bottleneck task",
                        "Assign your best agent to this task",
                        "Review if all dependencies are necessary",
                    ],
                    details=bottleneck,
                )
                issues.append(issue)

        return issues

    async def _detect_chain_blocks(
        self, tasks: List[Task], active_assignments: Dict[str, str]
    ) -> List[HealthIssue]:
        """Detect long dependency chains that might cause delays."""
        issues = []
        task_map = {t.id: t for t in tasks}

        # Find longest chains
        def find_chain_length(task_id: str, visited: Set[str]) -> int:
            if task_id in visited:
                return 0
            visited.add(task_id)

            task = task_map.get(task_id)
            if not task or not task.dependencies:
                return 1

            max_length = 0
            for dep_id in task.dependencies:
                length = find_chain_length(dep_id, visited.copy())
                max_length = max(max_length, length)

            return max_length + 1

        # Check each task
        long_chains = []
        for task in tasks:
            if task.status == TaskStatus.TODO:
                chain_length = find_chain_length(task.id, set())
                if chain_length > 3:  # Chains longer than 3 are concerning
                    long_chains.append(
                        {
                            "task_id": task.id,
                            "task_name": task.name,
                            "chain_length": chain_length,
                        }
                    )

        if long_chains:
            long_chains.sort(key=lambda x: x["chain_length"], reverse=True)

            for chain in long_chains[:3]:  # Report top 3 longest chains
                issue = HealthIssue(
                    type=HealthIssueType.CHAIN_BLOCK,
                    severity=IssueSeverity.MEDIUM,
                    description=(
                        f"Task '{chain['task_name']}' has a dependency chain "
                        f"of length {chain['chain_length']}"
                    ),
                    affected_tasks=[chain["task_id"]],
                    affected_agents=[],
                    recommendations=[
                        "Consider parallelizing some dependencies",
                        "Review if all dependencies are truly sequential",
                        "Break down tasks to reduce chain length",
                    ],
                    details=chain,
                )
                issues.append(issue)

        return issues

    async def _detect_stale_tasks(self, tasks: List[Task]) -> List[HealthIssue]:
        """Detect tasks that haven't progressed in a while."""
        issues = []

        stale_threshold = datetime.now() - timedelta(days=self.stale_task_days)
        stale_tasks = []

        for task in tasks:
            if task.status == TaskStatus.IN_PROGRESS:
                # Check last update time
                if task.updated_at < stale_threshold:
                    stale_tasks.append(
                        {
                            "task_id": task.id,
                            "task_name": task.name,
                            "assigned_to": task.assigned_to,
                            "days_stale": (datetime.now() - task.updated_at).days,
                        }
                    )

        if stale_tasks:
            stale_tasks.sort(key=lambda x: x["days_stale"], reverse=True)

            issue = HealthIssue(
                type=HealthIssueType.STALE_TASKS,
                severity=(
                    IssueSeverity.HIGH if len(stale_tasks) > 5 else IssueSeverity.MEDIUM
                ),
                description=f"{len(stale_tasks)} tasks haven't progressed in over {self.stale_task_days} days",
                affected_tasks=[t["task_id"] for t in stale_tasks],
                affected_agents=list(
                    set(t["assigned_to"] for t in stale_tasks if t["assigned_to"])
                ),
                recommendations=[
                    "Check in with agents on stale tasks",
                    "Consider reassigning stuck tasks",
                    "Review if tasks are blocked by external factors",
                ],
                details={"stale_tasks": stale_tasks},
            )
            issues.append(issue)

        return issues

    async def _analyze_agent_workload(
        self, agents: Dict[str, WorkerStatus], active_assignments: Dict[str, str]
    ) -> List[HealthIssue]:
        """Analyze agent workload distribution."""
        issues = []

        # Count assignments per agent
        assignment_count = defaultdict(int)
        for agent_id, task_id in active_assignments.items():
            assignment_count[agent_id] += 1

        # Find overloaded agents
        overloaded = []
        idle = []

        for agent_id, agent in agents.items():
            count = assignment_count.get(agent_id, 0)

            if count > self.max_tasks_per_agent:
                overloaded.append(
                    {
                        "agent_id": agent_id,
                        "agent_name": agent.name,
                        "task_count": count,
                    }
                )
            elif count == 0:
                idle.append(
                    {
                        "agent_id": agent_id,
                        "agent_name": agent.name,
                        "skills": agent.skills,
                    }
                )

        if overloaded:
            issue = HealthIssue(
                type=HealthIssueType.OVERLOADED_AGENTS,
                severity=IssueSeverity.MEDIUM,
                description=f"{len(overloaded)} agents are overloaded with tasks",
                affected_tasks=[],
                affected_agents=[a["agent_id"] for a in overloaded],
                recommendations=[
                    "Redistribute tasks from overloaded agents",
                    "Add more agents to handle workload",
                    "Prioritize critical tasks for overloaded agents",
                ],
                details={"overloaded_agents": overloaded},
            )
            issues.append(issue)

        if idle and len(idle) > len(agents) * 0.3:  # More than 30% idle
            issue = HealthIssue(
                type=HealthIssueType.IDLE_AGENTS,
                severity=IssueSeverity.LOW,
                description=f"{len(idle)} agents are idle",
                affected_tasks=[],
                affected_agents=[a["agent_id"] for a in idle],
                recommendations=[
                    "Review if idle agents have skills for available tasks",
                    "Consider cross-training agents",
                    "Check for skill mismatch issues",
                ],
                details={"idle_agents": idle},
            )
            issues.append(issue)

        return issues

    def _extract_required_skills(self, task: Task) -> List[str]:
        """Extract required skills from task labels and description."""
        skills = []

        # Common skill keywords
        skill_keywords = {
            "python",
            "javascript",
            "java",
            "golang",
            "rust",
            "react",
            "vue",
            "angular",
            "frontend",
            "backend",
            "database",
            "api",
            "devops",
            "testing",
            "design",
            "documentation",
            "security",
            "performance",
        }

        # Check labels
        for label in task.labels:
            label_lower = label.lower()
            for skill in skill_keywords:
                if skill in label_lower:
                    skills.append(skill)

        # Check description (simple keyword matching)
        desc_lower = task.description.lower()
        for skill in skill_keywords:
            if skill in desc_lower and skill not in skills:
                skills.append(skill)

        return skills

    def _calculate_health_metrics(
        self,
        tasks: List[Task],
        agents: Dict[str, WorkerStatus],
        issues: List[HealthIssue],
    ) -> Dict[str, Any]:
        """Calculate various health metrics."""
        total_tasks = len(tasks)

        status_counts = defaultdict(int)
        for task in tasks:
            status_counts[task.status.value] += 1

        return {
            "total_tasks": total_tasks,
            "tasks_by_status": dict(status_counts),
            "completion_rate": (
                status_counts[TaskStatus.DONE.value] / total_tasks * 100
                if total_tasks > 0
                else 0
            ),
            "blocked_rate": (
                status_counts[TaskStatus.BLOCKED.value] / total_tasks * 100
                if total_tasks > 0
                else 0
            ),
            "total_agents": len(agents),
            "total_issues": len(issues),
            "critical_issues": len(
                [i for i in issues if i.severity == IssueSeverity.CRITICAL]
            ),
            "high_issues": len([i for i in issues if i.severity == IssueSeverity.HIGH]),
        }

    def _generate_overall_recommendations(
        self, issues: List[HealthIssue], metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate high-level recommendations based on analysis."""
        recommendations = []

        # Check for critical issues
        critical_issues = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
        if critical_issues:
            recommendations.append(
                "🚨 Address critical issues immediately to unblock progress"
            )

        # Check completion rate
        if metrics.get("completion_rate", 0) < 20:
            recommendations.append(
                "📈 Focus on completing in-progress tasks before starting new ones"
            )

        # Check blocked rate
        if metrics.get("blocked_rate", 0) > 20:
            recommendations.append(
                "🚧 High number of blocked tasks - review and resolve blockers"
            )

        # Check for specific issue types
        issue_types = {i.type for i in issues}

        if HealthIssueType.SKILL_MISMATCH in issue_types:
            recommendations.append("🎯 Consider hiring or training for missing skills")

        if HealthIssueType.BOTTLENECK in issue_types:
            recommendations.append(
                "🔧 Prioritize bottleneck tasks to unblock dependencies"
            )

        if HealthIssueType.OVERLOADED_AGENTS in issue_types:
            recommendations.append("⚖️ Rebalance workload across agents")

        return recommendations

    def _calculate_health_score(
        self, issues: List[HealthIssue], metrics: Dict[str, Any]
    ) -> float:
        """Calculate overall health score (0-100)."""
        score = 100.0

        # Deduct points for issues based on severity
        severity_penalties = {
            IssueSeverity.CRITICAL: 20,
            IssueSeverity.HIGH: 10,
            IssueSeverity.MEDIUM: 5,
            IssueSeverity.LOW: 2,
        }

        for issue in issues:
            score -= severity_penalties[issue.severity]

        # Factor in completion rate
        completion_rate = metrics.get("completion_rate", 0)
        if completion_rate < 10:
            score -= 10
        elif completion_rate < 30:
            score -= 5

        # Factor in blocked rate
        blocked_rate = metrics.get("blocked_rate", 0)
        if blocked_rate > 30:
            score -= 10
        elif blocked_rate > 15:
            score -= 5

        # Ensure score stays in bounds
        return max(0, min(100, score))
