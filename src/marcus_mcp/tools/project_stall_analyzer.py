"""
Project Stall Analyzer - Comprehensive diagnostics for development stalls.

This module provides tools to diagnose why project development has stalled,
including snapshot capture, conversation replay, dependency lock visualization,
and task completion pattern analysis.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from src.core.task_diagnostics import (
    DependencyChainAnalyzer,
    DiagnosticReport,
    TaskDiagnosticCollector,
)

logger = logging.getLogger(__name__)


@dataclass
class ConversationEvent:
    """Represents a single conversation event from logs."""

    timestamp: str
    event_type: str
    data: Dict[str, Any]
    source: Optional[str] = None


@dataclass
class TaskCompletionEvent:
    """Represents a task completion event."""

    task_id: str
    task_name: str
    timestamp: str
    completed_by: Optional[str] = None
    sequence_number: int = 0


@dataclass
class ProjectStallSnapshot:
    """
    Complete snapshot of project state when development stalls.

    Attributes
    ----------
    timestamp : str
        When the snapshot was taken
    project_id : Optional[str]
        ID of the project
    project_name : Optional[str]
        Name of the project
    diagnostic_report : DiagnosticReport
        Full diagnostic report
    conversation_history : List[ConversationEvent]
        Recent conversation events leading up to stall
    task_completion_timeline : List[TaskCompletionEvent]
        Timeline of task completions
    dependency_locks : List[Dict[str, Any]]
        Active dependency locks preventing progress
    early_completions : List[Dict[str, Any]]
        Tasks completed earlier than expected (e.g., "Project Success")
    stall_reason : str
        Primary reason for the stall
    recommendations : List[str]
        Actionable recommendations to resolve the stall
    """

    timestamp: str
    project_id: Optional[str]
    project_name: Optional[str]
    diagnostic_report: Dict[str, Any]  # Serialized DiagnosticReport
    conversation_history: List[Dict[str, Any]]  # Serialized ConversationEvents
    task_completion_timeline: List[Dict[str, Any]]  # Serialized TaskCompletionEvents
    dependency_locks: List[Dict[str, Any]]
    early_completions: List[Dict[str, Any]]
    stall_reason: str
    recommendations: List[str]


class ConversationReplayAnalyzer:
    """Analyzes conversation logs to identify patterns leading to stalls."""

    def __init__(self, log_dir: Path):
        """
        Initialize conversation replay analyzer.

        Parameters
        ----------
        log_dir : Path
            Directory containing conversation logs
        """
        self.log_dir = log_dir

    def load_recent_events(
        self, lookback_hours: int = 24
    ) -> List[ConversationEvent]:
        """
        Load recent conversation events from logs.

        Parameters
        ----------
        lookback_hours : int
            How many hours of history to load

        Returns
        -------
        List[ConversationEvent]
            List of conversation events
        """
        cutoff_time = datetime.now() - timedelta(hours=lookback_hours)
        events = []

        # Find realtime log files
        realtime_logs = sorted(self.log_dir.glob("realtime_*.jsonl"), reverse=True)

        for log_file in realtime_logs:
            try:
                with open(log_file, "r") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            event_data = json.loads(line)
                            event_time = datetime.fromisoformat(
                                event_data.get("timestamp", "")
                            )

                            if event_time >= cutoff_time:
                                events.append(
                                    ConversationEvent(
                                        timestamp=event_data.get("timestamp", ""),
                                        event_type=event_data.get("type", "unknown"),
                                        data=event_data,
                                        source=event_data.get("source"),
                                    )
                                )
                        except (json.JSONDecodeError, ValueError):
                            continue
            except Exception as e:
                logger.warning(f"Failed to read log file {log_file}: {e}")
                continue

        return sorted(events, key=lambda e: e.timestamp)

    def identify_stall_patterns(
        self, events: List[ConversationEvent]
    ) -> List[Dict[str, Any]]:
        """
        Identify patterns in conversation history that indicate stalls.

        Parameters
        ----------
        events : List[ConversationEvent]
            Conversation events to analyze

        Returns
        -------
        List[Dict[str, Any]]
            List of identified patterns
        """
        patterns = []

        # Pattern 1: Repeated "no tasks available" messages
        no_task_events = [
            e for e in events if "no_task" in e.event_type or "no task" in str(e.data)
        ]
        if len(no_task_events) > 3:
            patterns.append(
                {
                    "pattern": "repeated_no_tasks",
                    "count": len(no_task_events),
                    "description": f"Agent requested tasks {len(no_task_events)} times but none available",
                    "severity": "high",
                }
            )

        # Pattern 2: Same task repeatedly failing
        task_errors = {}
        for e in events:
            if "error" in e.event_type or "failed" in e.event_type:
                task_id = e.data.get("task_id")
                if task_id:
                    task_errors[task_id] = task_errors.get(task_id, 0) + 1

        for task_id, count in task_errors.items():
            if count > 2:
                patterns.append(
                    {
                        "pattern": "repeated_task_failure",
                        "task_id": task_id,
                        "count": count,
                        "description": f"Task {task_id} failed {count} times",
                        "severity": "high",
                    }
                )

        # Pattern 3: Long gaps in activity
        if len(events) > 1:
            last_event_time = datetime.fromisoformat(events[-1].timestamp)
            first_event_time = datetime.fromisoformat(events[0].timestamp)
            gap_hours = (last_event_time - first_event_time).total_seconds() / 3600

            if gap_hours > 1 and len(events) < 10:
                patterns.append(
                    {
                        "pattern": "low_activity",
                        "gap_hours": round(gap_hours, 2),
                        "event_count": len(events),
                        "description": f"Only {len(events)} events in {gap_hours:.1f} hours",
                        "severity": "medium",
                    }
                )

        return patterns


class TaskCompletionAnalyzer:
    """Analyzes task completion patterns to detect anomalies."""

    def __init__(self, task_list: List[Any]):
        """
        Initialize task completion analyzer.

        Parameters
        ----------
        task_list : List[Any]
            List of tasks from the project
        """
        self.tasks = task_list
        self.task_map = {t.id: t for t in task_list}

    def build_completion_timeline(self) -> List[TaskCompletionEvent]:
        """
        Build timeline of task completions.

        Returns
        -------
        List[TaskCompletionEvent]
            Ordered list of task completion events
        """
        from src.core.models import TaskStatus

        completed_tasks = [t for t in self.tasks if t.status == TaskStatus.DONE]

        # Sort by completion time if available
        timeline = []
        for idx, task in enumerate(completed_tasks):
            completion_time = getattr(task, "completed_at", None)
            if not completion_time:
                # Use created_at as fallback
                completion_time = getattr(task, "created_at", datetime.now())

            timeline.append(
                TaskCompletionEvent(
                    task_id=task.id,
                    task_name=task.name,
                    timestamp=completion_time.isoformat(),
                    completed_by=getattr(task, "assignee", None),
                    sequence_number=idx + 1,
                )
            )

        return sorted(timeline, key=lambda e: e.timestamp)

    def detect_early_completions(
        self, timeline: List[TaskCompletionEvent]
    ) -> List[Dict[str, Any]]:
        """
        Detect tasks completed earlier than expected.

        Flags tasks like "Project Success" being completed before all other tasks.

        Parameters
        ----------
        timeline : List[TaskCompletionEvent]
            Task completion timeline

        Returns
        -------
        List[Dict[str, Any]]
            List of anomalous early completions
        """
        early_completions = []

        # Check for "success" or "complete" tasks completed early
        for event in timeline:
            task_name_lower = event.task_name.lower()
            is_final_task = any(
                keyword in task_name_lower
                for keyword in ["success", "complete", "finish", "done", "deployment"]
            )

            if is_final_task:
                # Check if this was completed before 80% of other tasks
                total_tasks = len(self.tasks)
                completed_before = event.sequence_number
                completion_percentage = (completed_before / total_tasks) * 100

                if completion_percentage < 80:
                    early_completions.append(
                        {
                            "task_id": event.task_id,
                            "task_name": event.task_name,
                            "completed_at": event.timestamp,
                            "sequence": event.sequence_number,
                            "total_tasks": total_tasks,
                            "completion_percentage": round(completion_percentage, 1),
                            "issue": f"Final task completed at {completion_percentage:.0f}% progress",
                            "severity": "high",
                        }
                    )

        return early_completions


class DependencyLockVisualizer:
    """Visualizes dependency locks blocking task progress."""

    def __init__(self, dependency_analyzer: DependencyChainAnalyzer):
        """
        Initialize dependency lock visualizer.

        Parameters
        ----------
        dependency_analyzer : DependencyChainAnalyzer
            Analyzer with dependency graph data
        """
        self.analyzer = dependency_analyzer

    def generate_lock_visualization(self) -> Dict[str, Any]:
        """
        Generate visualization of dependency locks.

        Returns
        -------
        Dict[str, Any]
            Visualization data including ASCII graph and metrics
        """
        from src.core.models import TaskStatus

        # Find all locks (TODO tasks blocked by incomplete dependencies)
        locks = []
        for task in self.analyzer.project_tasks:
            if task.status != TaskStatus.TODO:
                continue

            if task.dependencies:
                incomplete_deps = [
                    dep_id
                    for dep_id in task.dependencies
                    if dep_id in self.analyzer.task_map
                    and self.analyzer.task_map[dep_id].status != TaskStatus.DONE
                ]

                if incomplete_deps:
                    locks.append(
                        {
                            "blocked_task": {
                                "id": task.id,
                                "name": task.name,
                                "status": task.status.value,
                            },
                            "blocking_tasks": [
                                {
                                    "id": dep_id,
                                    "name": self.analyzer.task_map[dep_id].name,
                                    "status": self.analyzer.task_map[dep_id].status.value,
                                }
                                for dep_id in incomplete_deps
                            ],
                            "lock_depth": len(incomplete_deps),
                        }
                    )

        # Generate ASCII visualization
        ascii_viz = self._generate_ascii_graph(locks)

        return {
            "total_locks": len(locks),
            "locks": locks,
            "ascii_visualization": ascii_viz,
            "metrics": {
                "average_lock_depth": (
                    sum(l["lock_depth"] for l in locks) / len(locks)
                    if locks
                    else 0
                ),
                "max_lock_depth": max((l["lock_depth"] for l in locks), default=0),
            },
        }

    def _generate_ascii_graph(self, locks: List[Dict[str, Any]]) -> str:
        """
        Generate ASCII art visualization of dependency locks.

        Parameters
        ----------
        locks : List[Dict[str, Any]]
            Lock data

        Returns
        -------
        str
            ASCII art visualization
        """
        if not locks:
            return "No dependency locks found."

        lines = []
        lines.append("Dependency Lock Visualization:")
        lines.append("=" * 70)

        for lock in locks[:10]:  # Show top 10 locks
            blocked = lock["blocked_task"]
            blockers = lock["blocking_tasks"]

            lines.append(f"\n🔒 BLOCKED: {blocked['name']} (Status: {blocked['status']})")
            lines.append("   Waiting for:")
            for blocker in blockers:
                status_symbol = "⏳" if blocker["status"] == "in_progress" else "❌"
                lines.append(f"   {status_symbol} {blocker['name']} ({blocker['status']})")

        if len(locks) > 10:
            lines.append(f"\n... and {len(locks) - 10} more locks")

        return "\n".join(lines)


async def capture_project_stall_snapshot(
    state: Any, include_conversation_hours: int = 24
) -> Dict[str, Any]:
    """
    Capture complete snapshot of project state during a stall.

    This is the main entry point for stall analysis.

    Parameters
    ----------
    state : Any
        Marcus server state
    include_conversation_hours : int
        How many hours of conversation history to include

    Returns
    -------
    Dict[str, Any]
        Complete stall snapshot
    """
    from src.core.models import TaskStatus
    from src.core.task_diagnostics import (
        DiagnosticReportGenerator,
        format_diagnostic_report,
    )

    try:
        # Get project tasks
        if not state.kanban_client:
            await state.initialize_kanban()

        project_tasks = await state.kanban_client.get_all_tasks()

        # Get completed and assigned task IDs
        completed_task_ids = {
            t.id for t in project_tasks if t.status == TaskStatus.DONE
        }
        assigned_task_ids = set(state.agent_tasks.keys())

        # Run diagnostics
        collector = TaskDiagnosticCollector(project_tasks)
        filtering_stats = collector.collect_filtering_stats(
            completed_task_ids, assigned_task_ids
        )

        dependency_analyzer = DependencyChainAnalyzer(project_tasks)
        report_generator = DiagnosticReportGenerator(
            project_tasks, filtering_stats, dependency_analyzer
        )
        diagnostic_report = report_generator.generate_report()

        # Analyze conversations
        log_dir = Path("logs/conversations")
        conversation_analyzer = ConversationReplayAnalyzer(log_dir)
        conversation_history = conversation_analyzer.load_recent_events(
            include_conversation_hours
        )
        stall_patterns = conversation_analyzer.identify_stall_patterns(
            conversation_history
        )

        # Analyze task completions
        completion_analyzer = TaskCompletionAnalyzer(project_tasks)
        completion_timeline = completion_analyzer.build_completion_timeline()
        early_completions = completion_analyzer.detect_early_completions(
            completion_timeline
        )

        # Visualize dependency locks
        lock_visualizer = DependencyLockVisualizer(dependency_analyzer)
        dependency_locks = lock_visualizer.generate_lock_visualization()

        # Determine primary stall reason
        stall_reason = "Unknown"
        if diagnostic_report.issues:
            top_issue = diagnostic_report.issues[0]
            stall_reason = f"{top_issue.issue_type}: {top_issue.description}"
        elif stall_patterns:
            top_pattern = stall_patterns[0]
            stall_reason = f"{top_pattern['pattern']}: {top_pattern['description']}"

        # Build recommendations
        recommendations = list(diagnostic_report.recommendations)
        if early_completions:
            recommendations.insert(
                0,
                f"⚠️ {len(early_completions)} tasks completed prematurely - review completion criteria",
            )
        for pattern in stall_patterns[:3]:
            recommendations.append(f"Pattern detected: {pattern['description']}")

        # Get project info
        active_project = await state.project_registry.get_active_project()
        project_id = active_project.id if active_project else None
        project_name = active_project.name if active_project else None

        # Create snapshot
        snapshot = ProjectStallSnapshot(
            timestamp=datetime.now().isoformat(),
            project_id=project_id,
            project_name=project_name,
            diagnostic_report={
                "timestamp": diagnostic_report.timestamp,
                "total_tasks": diagnostic_report.total_tasks,
                "available_tasks": diagnostic_report.available_tasks,
                "blocked_tasks": diagnostic_report.blocked_tasks,
                "task_breakdown": diagnostic_report.task_breakdown,
                "issues": [
                    {
                        "type": i.issue_type,
                        "severity": i.severity,
                        "description": i.description,
                        "recommendation": i.recommendation,
                        "affected_count": len(i.affected_tasks),
                    }
                    for i in diagnostic_report.issues
                ],
                "formatted_report": format_diagnostic_report(diagnostic_report),
            },
            conversation_history=[
                {
                    "timestamp": e.timestamp,
                    "type": e.event_type,
                    "source": e.source,
                    "data": e.data,
                }
                for e in conversation_history[-50:]  # Last 50 events
            ],
            task_completion_timeline=[
                {
                    "task_id": e.task_id,
                    "task_name": e.task_name,
                    "timestamp": e.timestamp,
                    "sequence": e.sequence_number,
                }
                for e in completion_timeline
            ],
            dependency_locks=dependency_locks,
            early_completions=early_completions,
            stall_reason=stall_reason,
            recommendations=recommendations,
        )

        # Save snapshot to file
        snapshot_dir = Path("logs/stall_snapshots")
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_file = snapshot_dir / f"stall_snapshot_{timestamp_str}.json"

        with open(snapshot_file, "w") as f:
            json.dump(asdict(snapshot), f, indent=2, default=str)

        logger.info(f"Stall snapshot saved to {snapshot_file}")

        return {
            "success": True,
            "snapshot_file": str(snapshot_file),
            "snapshot": asdict(snapshot),
            "summary": {
                "stall_reason": stall_reason,
                "total_issues": len(diagnostic_report.issues),
                "dependency_locks": dependency_locks["total_locks"],
                "early_completions": len(early_completions),
                "conversation_events": len(conversation_history),
                "recommendations_count": len(recommendations),
            },
        }

    except Exception as e:
        logger.error(f"Failed to capture stall snapshot: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to capture snapshot: {str(e)}",
        }


async def replay_stall_conversations(
    snapshot_file: str,
) -> Dict[str, Any]:
    """
    Replay conversations from a stall snapshot.

    Parameters
    ----------
    snapshot_file : str
        Path to the snapshot file

    Returns
    -------
    Dict[str, Any]
        Conversation replay analysis
    """
    try:
        with open(snapshot_file, "r") as f:
            snapshot_data = json.load(f)

        conversation_history = snapshot_data.get("conversation_history", [])

        # Analyze conversation flow
        analysis = {
            "total_events": len(conversation_history),
            "events_by_type": {},
            "timeline": [],
            "key_events": [],
        }

        for event in conversation_history:
            event_type = event.get("type", "unknown")
            analysis["events_by_type"][event_type] = (
                analysis["events_by_type"].get(event_type, 0) + 1
            )

            # Identify key events
            if any(
                keyword in event_type
                for keyword in ["error", "blocker", "no_task", "failed"]
            ):
                analysis["key_events"].append(
                    {
                        "timestamp": event.get("timestamp"),
                        "type": event_type,
                        "summary": str(event.get("data", {}))[:200],
                    }
                )

            analysis["timeline"].append(
                {
                    "timestamp": event.get("timestamp"),
                    "type": event_type,
                }
            )

        return {
            "success": True,
            "snapshot_file": snapshot_file,
            "analysis": analysis,
        }

    except Exception as e:
        logger.error(f"Failed to replay conversations: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to replay: {str(e)}",
        }
