"""
Automatic Task Assignment Diagnostics System.

This module automatically diagnoses why tasks aren't being assigned or completed.
It runs whenever no suitable tasks are found and generates actionable reports.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from src.core.models import Task, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class DiagnosticIssue:
    """
    Represents a diagnosed issue blocking task assignment.

    Attributes
    ----------
    issue_type : str
        Type of issue (circular_dependency, missing_task, etc.)
    severity : str
        Severity level: critical, high, medium, low
    affected_tasks : List[str]
        Task IDs affected by this issue
    description : str
        Human-readable description of the issue
    recommendation : str
        Actionable recommendation to fix the issue
    details : Dict[str, Any]
        Additional diagnostic details
    """

    issue_type: str
    severity: str
    affected_tasks: List[str]
    description: str
    recommendation: str
    details: Dict[str, Any]


@dataclass
class ProjectSnapshot:
    """
    Snapshot of the project/board state at diagnostic time.

    Provides a holistic view of the project for context.

    Attributes
    ----------
    project_name : Optional[str]
        Name of the project
    board_name : Optional[str]
        Name of the board
    total_tasks : int
        Total number of tasks
    completion_percentage : float
        Percentage of tasks completed
    velocity : float
        Average tasks completed per day (if calculable)
    oldest_task_age_days : Optional[int]
        Age of the oldest incomplete task in days
    average_task_age_days : Optional[float]
        Average age of incomplete tasks in days
    tasks_by_priority : Dict[str, int]
        Count of tasks by priority level
    """

    project_name: Optional[str]
    board_name: Optional[str]
    total_tasks: int
    completion_percentage: float
    velocity: float
    oldest_task_age_days: Optional[int]
    average_task_age_days: Optional[float]
    tasks_by_priority: Dict[str, int]


@dataclass
class DiagnosticReport:
    """
    Complete diagnostic report for task assignment issues.

    Attributes
    ----------
    timestamp : str
        When the diagnostic was run
    project_snapshot : ProjectSnapshot
        Holistic view of the project state
    total_tasks : int
        Total number of tasks in the project
    available_tasks : int
        Number of tasks that could be assigned
    blocked_tasks : int
        Number of tasks blocked by dependencies
    issues : List[DiagnosticIssue]
        List of identified issues
    task_breakdown : Dict[str, int]
        Breakdown of tasks by status
    dependency_graph : Dict[str, List[str]]
        Visual representation of dependencies
    recommendations : List[str]
        Prioritized list of recommendations
    """

    timestamp: str
    project_snapshot: ProjectSnapshot
    total_tasks: int
    available_tasks: int
    blocked_tasks: int
    issues: List[DiagnosticIssue]
    task_breakdown: Dict[str, int]
    dependency_graph: Dict[str, List[str]]
    recommendations: List[str]


class TaskDiagnosticCollector:
    """
    Collects diagnostic data during task assignment.

    This runs automatically when request_next_task finds no suitable tasks.
    """

    def __init__(self, project_tasks: List[Task]) -> None:
        """
        Initialize the diagnostic collector.

        Parameters
        ----------
        project_tasks : List[Task]
            All tasks in the current project
        """
        self.project_tasks = project_tasks
        self.task_map = {t.id: t for t in project_tasks}

    def create_project_snapshot(self) -> ProjectSnapshot:
        """
        Create a snapshot of the current project/board state.

        Returns
        -------
        ProjectSnapshot
            Holistic view of the project
        """
        from datetime import datetime

        # Calculate completion percentage
        completed_count = len(
            [t for t in self.project_tasks if t.status == TaskStatus.DONE]
        )
        total_count = len(self.project_tasks)
        completion_pct = (completed_count / total_count * 100) if total_count > 0 else 0

        # Calculate task ages (for incomplete tasks only)
        now = datetime.now()
        incomplete_tasks = [
            t for t in self.project_tasks if t.status != TaskStatus.DONE
        ]

        oldest_age_days = None
        average_age_days = None

        if incomplete_tasks:
            ages_days = [
                (now - t.created_at).days
                for t in incomplete_tasks
                if hasattr(t, "created_at") and t.created_at
            ]
            if ages_days:
                oldest_age_days = max(ages_days)
                average_age_days = sum(ages_days) / len(ages_days)

        # Count tasks by priority
        priority_counts: Dict[str, int] = {}
        for task in self.project_tasks:
            priority_str = task.priority.value if task.priority else "unknown"
            priority_counts[priority_str] = priority_counts.get(priority_str, 0) + 1

        # Try to extract project/board name from tasks
        project_name = None
        board_name = None
        if self.project_tasks:
            first_task = self.project_tasks[0]
            if hasattr(first_task, "project_name") and first_task.project_name:
                project_name = first_task.project_name
            if hasattr(first_task, "board_name") and first_task.board_name:
                board_name = first_task.board_name

        # Calculate velocity (placeholder - would need historical data)
        velocity = 0.0  # Would need time series data to calculate

        return ProjectSnapshot(
            project_name=project_name,
            board_name=board_name,
            total_tasks=total_count,
            completion_percentage=completion_pct,
            velocity=velocity,
            oldest_task_age_days=oldest_age_days,
            average_task_age_days=average_age_days,
            tasks_by_priority=priority_counts,
        )

    def collect_filtering_stats(
        self,
        completed_task_ids: Set[str],
        assigned_task_ids: Set[str],
    ) -> Dict[str, Any]:
        """
        Collect detailed statistics about task filtering.

        Parameters
        ----------
        completed_task_ids : Set[str]
            IDs of completed tasks
        assigned_task_ids : Set[str]
            IDs of currently assigned tasks

        Returns
        -------
        Dict[str, Any]
            Detailed filtering statistics
        """
        # Use typed variables for better type inference
        total_tasks = len(self.project_tasks)
        completed = len(completed_task_ids)
        assigned = len(assigned_task_ids)
        todo_count = 0
        in_progress_count = 0
        blocked_by_dependencies: List[Dict[str, Any]] = []
        blocked_by_assignment: List[Dict[str, Any]] = []
        available: List[Dict[str, Any]] = []

        for task in self.project_tasks:
            # Count by status
            if task.status == TaskStatus.TODO:
                todo_count += 1
            elif task.status == TaskStatus.IN_PROGRESS:
                in_progress_count += 1

            # Skip non-TODO tasks
            if task.status != TaskStatus.TODO:
                continue

            # Check if already assigned
            if task.id in assigned_task_ids:
                blocked_by_assignment.append(
                    {
                        "id": task.id,
                        "name": task.name,
                        "reason": "already_assigned",
                    }
                )
                continue

            # Check dependencies
            deps = task.dependencies or []
            incomplete_deps = [d for d in deps if d not in completed_task_ids]

            if incomplete_deps:
                blocked_by_dependencies.append(
                    {
                        "id": task.id,
                        "name": task.name,
                        "blocked_by": incomplete_deps,
                        "blocked_by_names": [
                            self.task_map[d].name
                            for d in incomplete_deps
                            if d in self.task_map
                        ],
                    }
                )
            else:
                available.append(
                    {"id": task.id, "name": task.name, "priority": task.priority.value}
                )

        stats = {
            "total_tasks": total_tasks,
            "completed": completed,
            "assigned": assigned,
            "todo": todo_count,
            "in_progress": in_progress_count,
            "blocked_by_dependencies": blocked_by_dependencies,
            "blocked_by_assignment": blocked_by_assignment,
            "available": available,
        }

        return stats


class DependencyChainAnalyzer:
    """
    Analyzes dependency chains to find circular dependencies and bottlenecks.

    Uses graph algorithms to detect cycles and identify problematic patterns.
    """

    def __init__(self, project_tasks: List[Task]) -> None:
        """
        Initialize the dependency analyzer.

        Parameters
        ----------
        project_tasks : List[Task]
            All tasks in the current project
        """
        self.project_tasks = project_tasks
        self.task_map = {t.id: t for t in project_tasks}
        self.dependency_graph = self._build_dependency_graph()

    def _build_dependency_graph(self) -> Dict[str, List[str]]:
        """
        Build adjacency list representation of task dependencies.

        Returns
        -------
        Dict[str, List[str]]
            Map of task_id -> [dependent_task_ids]
        """
        graph = defaultdict(list)
        for task in self.project_tasks:
            if task.dependencies:
                for dep_id in task.dependencies:
                    graph[dep_id].append(task.id)
        return dict(graph)

    def find_circular_dependencies(self) -> List[List[str]]:
        """
        Find all circular dependency cycles using DFS.

        Returns
        -------
        List[List[str]]
            List of cycles, where each cycle is a list of task IDs
        """
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(task_id: str) -> bool:
            """Depth-first search to detect cycles."""
            visited.add(task_id)
            rec_stack.add(task_id)
            path.append(task_id)

            # Check dependencies (reverse direction)
            task = self.task_map.get(task_id)
            if task and task.dependencies:
                for dep_id in task.dependencies:
                    if dep_id not in visited:
                        if dfs(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        # Found a cycle
                        cycle_start = path.index(dep_id)
                        cycle = path[cycle_start:] + [dep_id]
                        cycles.append(cycle)
                        return True

            path.pop()
            rec_stack.remove(task_id)
            return False

        for task in self.project_tasks:
            if task.id not in visited:
                dfs(task.id)

        return cycles

    def find_bottlenecks(self, threshold: int = 3) -> List[Dict[str, Any]]:
        """
        Find tasks that block many other tasks.

        Parameters
        ----------
        threshold : int
            Minimum number of blocked tasks to be considered a bottleneck

        Returns
        -------
        List[Dict[str, Any]]
            List of bottleneck tasks with details
        """
        bottlenecks = []

        for task_id, dependents in self.dependency_graph.items():
            if len(dependents) >= threshold:
                task = self.task_map.get(task_id)
                if task and task.status != TaskStatus.DONE:
                    bottlenecks.append(
                        {
                            "task_id": task_id,
                            "task_name": task.name if task else "Unknown",
                            "status": task.status.value if task else "unknown",
                            "blocks_count": len(dependents),
                            "blocks_tasks": [
                                self.task_map[d].name
                                for d in dependents
                                if d in self.task_map
                            ],
                        }
                    )

        return sorted(bottlenecks, key=lambda x: x["blocks_count"], reverse=True)

    def find_missing_dependencies(self) -> List[Dict[str, Any]]:
        """
        Find tasks that reference non-existent dependencies.

        Returns
        -------
        List[Dict[str, Any]]
            List of tasks with missing dependencies
        """
        missing = []

        for task in self.project_tasks:
            if task.dependencies:
                missing_deps = [d for d in task.dependencies if d not in self.task_map]
                if missing_deps:
                    missing.append(
                        {
                            "task_id": task.id,
                            "task_name": task.name,
                            "missing_dependency_ids": missing_deps,
                        }
                    )

        return missing

    def find_long_chains(self, min_length: int = 4) -> List[List[str]]:
        """
        Find long dependency chains that might cause delays.

        Parameters
        ----------
        min_length : int
            Minimum chain length to report

        Returns
        -------
        List[List[str]]
            List of dependency chains (task ID sequences)
        """
        chains = []

        def find_longest_path(task_id: str, visited: Set[str]) -> List[str]:
            """Find longest path from this task."""
            task = self.task_map.get(task_id)
            if not task or not task.dependencies:
                return [task_id]

            longest = [task_id]
            for dep_id in task.dependencies:
                if dep_id not in visited:
                    path = find_longest_path(dep_id, visited | {task_id})
                    if len(path) + 1 > len(longest):
                        longest = [task_id] + path

            return longest

        for task in self.project_tasks:
            chain = find_longest_path(task.id, set())
            if len(chain) >= min_length:
                chains.append(chain)

        return chains


class DiagnosticReportGenerator:
    """
    Generates actionable diagnostic reports from collected data.

    Creates human-readable reports with prioritized recommendations.
    """

    def __init__(
        self,
        project_tasks: List[Task],
        filtering_stats: Dict[str, Any],
        dependency_analyzer: DependencyChainAnalyzer,
    ) -> None:
        """
        Initialize the report generator.

        Parameters
        ----------
        project_tasks : List[Task]
            All tasks in the project
        filtering_stats : Dict[str, Any]
            Statistics from task filtering
        dependency_analyzer : DependencyChainAnalyzer
            Analyzer for dependency issues
        """
        self.project_tasks = project_tasks
        self.filtering_stats = filtering_stats
        self.analyzer = dependency_analyzer
        self.task_map = {t.id: t for t in project_tasks}

    def generate_report(self) -> DiagnosticReport:
        """
        Generate complete diagnostic report.

        Returns
        -------
        DiagnosticReport
            Complete diagnostic report with issues and recommendations
        """
        from datetime import datetime

        issues = self._identify_issues()
        recommendations = self._generate_recommendations(issues)

        # Create project snapshot for holistic view
        collector = TaskDiagnosticCollector(self.project_tasks)
        project_snapshot = collector.create_project_snapshot()

        return DiagnosticReport(
            timestamp=datetime.now().isoformat(),
            project_snapshot=project_snapshot,
            total_tasks=self.filtering_stats["total_tasks"],
            available_tasks=len(self.filtering_stats["available"]),
            blocked_tasks=len(self.filtering_stats["blocked_by_dependencies"]),
            issues=issues,
            task_breakdown={
                "todo": self.filtering_stats["todo"],
                "in_progress": self.filtering_stats["in_progress"],
                "completed": self.filtering_stats["completed"],
                "assigned": self.filtering_stats["assigned"],
            },
            dependency_graph=self.analyzer.dependency_graph,
            recommendations=recommendations,
        )

    def _identify_issues(self) -> List[DiagnosticIssue]:
        """
        Identify all diagnostic issues.

        Returns
        -------
        List[DiagnosticIssue]
            List of identified issues
        """
        issues = []

        # Check for circular dependencies
        cycles = self.analyzer.find_circular_dependencies()
        for cycle in cycles:
            task_names = [
                self.task_map[tid].name for tid in cycle if tid in self.task_map
            ]
            issues.append(
                DiagnosticIssue(
                    issue_type="circular_dependency",
                    severity="critical",
                    affected_tasks=cycle,
                    description=(
                        f"Circular dependency: {' → '.join(task_names[:3])}..."
                    ),
                    recommendation=(
                        "Break the circular dependency by removing one link. "
                        f"Consider removing '{task_names[0]}' → "
                        f"'{task_names[-1]}'"
                    ),
                    details={"cycle": cycle, "cycle_length": len(cycle)},
                )
            )

        # Check for bottlenecks
        bottlenecks = self.analyzer.find_bottlenecks()
        for bottleneck in bottlenecks:
            issues.append(
                DiagnosticIssue(
                    issue_type="bottleneck",
                    severity="high" if bottleneck["blocks_count"] > 5 else "medium",
                    affected_tasks=[bottleneck["task_id"]],
                    description=(
                        f"Task '{bottleneck['task_name']}' is blocking "
                        f"{bottleneck['blocks_count']} other tasks"
                    ),
                    recommendation=(
                        f"Prioritize completing '{bottleneck['task_name']}' "
                        f"to unblock {bottleneck['blocks_count']} tasks"
                    ),
                    details=bottleneck,
                )
            )

        # Check for missing dependencies
        missing = self.analyzer.find_missing_dependencies()
        for item in missing:
            issues.append(
                DiagnosticIssue(
                    issue_type="missing_dependency",
                    severity="high",
                    affected_tasks=[item["task_id"]],
                    description=(
                        f"Task '{item['task_name']}' references "
                        f"non-existent dependencies: {item['missing_dependency_ids']}"
                    ),
                    recommendation=(
                        f"Remove invalid dependencies from "
                        f"'{item['task_name']}' or create missing tasks"
                    ),
                    details=item,
                )
            )

        # Check for long dependency chains
        chains = self.analyzer.find_long_chains()
        for chain in chains:
            task_names = [
                self.task_map[tid].name for tid in chain if tid in self.task_map
            ]
            issues.append(
                DiagnosticIssue(
                    issue_type="long_dependency_chain",
                    severity="medium",
                    affected_tasks=chain,
                    description=(
                        f"Long dependency chain detected ({len(chain)} tasks): "
                        f"{' → '.join(task_names[:3])}..."
                    ),
                    recommendation=(
                        "Consider parallelizing work by breaking this chain "
                        "into independent sub-tasks where possible"
                    ),
                    details={"chain": chain, "chain_length": len(chain)},
                )
            )

        # Check if all tasks are blocked
        if (
            self.filtering_stats["available"] == []
            and self.filtering_stats["blocked_by_dependencies"]
        ):
            blocked_tasks = self.filtering_stats["blocked_by_dependencies"]
            issues.append(
                DiagnosticIssue(
                    issue_type="all_tasks_blocked",
                    severity="critical",
                    affected_tasks=[t["id"] for t in blocked_tasks],
                    description=(
                        f"All {len(blocked_tasks)} TODO tasks blocked by "
                        "dependencies"
                    ),
                    recommendation=(
                        "Likely a circular dependency or missing tasks. "
                        "Check circular dependency issues above."
                    ),
                    details={"blocked_tasks": blocked_tasks},
                )
            )

        return sorted(issues, key=lambda x: self._severity_rank(x.severity))

    def _severity_rank(self, severity: str) -> int:
        """Rank severity for sorting."""
        return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(severity, 4)

    def _generate_recommendations(self, issues: List[DiagnosticIssue]) -> List[str]:
        """
        Generate prioritized recommendations.

        Parameters
        ----------
        issues : List[DiagnosticIssue]
            List of identified issues

        Returns
        -------
        List[str]
            Prioritized list of recommendations
        """
        recommendations = []

        # Add issue-specific recommendations
        for issue in issues:
            if issue.severity in ["critical", "high"]:
                recommendations.append(
                    f"[{issue.severity.upper()}] {issue.recommendation}"
                )

        # Add general recommendations
        if self.filtering_stats["available"]:
            recommendations.append(
                f"✓ {len(self.filtering_stats['available'])} tasks are available "
                "for assignment (check agent skills)"
            )

        if self.filtering_stats["blocked_by_dependencies"]:
            recommendations.append(
                f"⚠ {len(self.filtering_stats['blocked_by_dependencies'])} tasks "
                "are blocked by incomplete dependencies"
            )

        return recommendations


async def run_automatic_diagnostics(
    project_tasks: List[Task],
    completed_task_ids: Set[str],
    assigned_task_ids: Set[str],
) -> DiagnosticReport:
    """
    Run automatic diagnostics on task assignment.

    This is called automatically when no suitable tasks are found.

    Parameters
    ----------
    project_tasks : List[Task]
        All tasks in the current project
    completed_task_ids : Set[str]
        IDs of completed tasks
    assigned_task_ids : Set[str]
        IDs of currently assigned tasks

    Returns
    -------
    DiagnosticReport
        Complete diagnostic report
    """
    logger.info("Running automatic task assignment diagnostics...")

    # Collect data
    collector = TaskDiagnosticCollector(project_tasks)
    filtering_stats = collector.collect_filtering_stats(
        completed_task_ids, assigned_task_ids
    )

    # Analyze dependencies
    analyzer = DependencyChainAnalyzer(project_tasks)

    # Generate report
    generator = DiagnosticReportGenerator(project_tasks, filtering_stats, analyzer)
    report = generator.generate_report()

    # Log summary
    logger.info(f"Diagnostic complete: Found {len(report.issues)} issues")
    for issue in report.issues[:3]:  # Log top 3 issues
        logger.warning(f"[{issue.severity}] {issue.description}")

    return report


def format_diagnostic_report(report: DiagnosticReport) -> str:
    """
    Format diagnostic report as human-readable text.

    Parameters
    ----------
    report : DiagnosticReport
        Diagnostic report to format

    Returns
    -------
    str
        Formatted report text
    """
    lines = []
    lines.append("=" * 70)
    lines.append("🔍 TASK ASSIGNMENT DIAGNOSTIC REPORT")
    lines.append("=" * 70)
    lines.append(f"Timestamp: {report.timestamp}")
    lines.append("")

    # Project Snapshot
    snapshot = report.project_snapshot
    lines.append("📸 PROJECT SNAPSHOT")
    lines.append("-" * 70)
    if snapshot.project_name:
        lines.append(f"Project: {snapshot.project_name}")
    if snapshot.board_name:
        lines.append(f"Board: {snapshot.board_name}")
    lines.append(f"Total tasks: {snapshot.total_tasks}")
    lines.append(f"Completion: {snapshot.completion_percentage:.1f}%")
    if snapshot.oldest_task_age_days is not None:
        lines.append(
            f"Oldest incomplete task: {snapshot.oldest_task_age_days} days old"
        )
    if snapshot.average_task_age_days is not None:
        lines.append(f"Average task age: {snapshot.average_task_age_days:.1f} days")
    lines.append("\nTasks by priority:")
    for priority, count in snapshot.tasks_by_priority.items():
        lines.append(f"  {priority}: {count}")
    lines.append("")

    # Summary
    lines.append("📊 DIAGNOSTIC SUMMARY")
    lines.append("-" * 70)
    lines.append(f"Available for assignment: {report.available_tasks}")
    lines.append(f"Blocked by dependencies: {report.blocked_tasks}")
    lines.append(f"Issues found: {len(report.issues)}")
    lines.append("")

    # Task breakdown
    lines.append("📈 TASK BREAKDOWN BY STATUS")
    lines.append("-" * 70)
    for status, count in report.task_breakdown.items():
        lines.append(f"  {status}: {count}")
    lines.append("")

    # Issues
    if report.issues:
        lines.append("⚠️  ISSUES DETECTED")
        lines.append("-" * 70)
        for i, issue in enumerate(report.issues, 1):
            issue_title = issue.issue_type.replace("_", " ").title()
            lines.append(f"{i}. [{issue.severity.upper()}] {issue_title}")
            lines.append(f"   {issue.description}")
            lines.append(f"   Affected tasks: {len(issue.affected_tasks)}")
            lines.append(f"   💡 {issue.recommendation}")
            lines.append("")

    # Recommendations
    if report.recommendations:
        lines.append("💡 RECOMMENDATIONS")
        lines.append("-" * 70)
        for rec in report.recommendations:
            lines.append(f"  • {rec}")
        lines.append("")

    lines.append("=" * 70)

    return "\n".join(lines)


# test
