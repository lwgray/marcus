"""
Live Pipeline Monitor - Real-time monitoring of pipeline executions

This module provides live visibility into ongoing pipeline executions with
predictive capabilities to identify potential issues before they occur.
"""

import asyncio
import json
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from src.visualization.shared_pipeline_events import SharedPipelineEvents


@dataclass
class FlowHealth:
    """Health status of a pipeline flow."""

    flow_id: str
    status: str  # healthy, warning, critical
    issues: List[str]
    metrics: Dict[str, Any]


@dataclass
class ProgressUpdate:
    """Real-time progress update for a flow."""

    flow_id: str
    progress_percentage: float
    current_stage: str
    eta: Optional[datetime]
    events_completed: int
    events_total_estimated: int
    health_status: FlowHealth


class LivePipelineMonitor:
    """
    Monitor active pipeline flows in real-time.

    Provides progress tracking, ETA estimation, and health monitoring
    with predictive issue detection.
    """

    def __init__(self):
        """Initialize the live monitor."""
        self.shared_events = SharedPipelineEvents()
        self.active_flows: Dict[str, Dict[str, Any]] = {}
        self.websocket_clients: Set[Any] = set()
        self.historical_data = self._load_historical_data()
        self.monitoring_task = None

    def _load_historical_data(self) -> Dict[str, Any]:
        """Load historical flow data for predictions."""
        # In production, load from database
        # For now, analyze existing flows
        all_data = self.shared_events._read_events()

        historical = {
            "avg_durations_by_stage": defaultdict(list),
            "failure_patterns": [],
            "avg_events_per_flow": [],
        }

        # Analyze completed flows
        for flow_id, flow_info in all_data["flows"].items():
            if flow_info.get("completed_at"):
                flow_events = [
                    e for e in all_data["events"] if e.get("flow_id") == flow_id
                ]

                # Track stage durations
                for event in flow_events:
                    if "duration_ms" in event:
                        stage = event.get("stage", "unknown")
                        historical["avg_durations_by_stage"][stage].append(
                            event["duration_ms"]
                        )

                # Track event counts
                historical["avg_events_per_flow"].append(len(flow_events))

        return historical

    async def start_monitoring(self):
        """Start the monitoring loop."""
        if self.monitoring_task:
            return

        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

    async def stop_monitoring(self):
        """Stop the monitoring loop."""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            self.monitoring_task = None

    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while True:
            try:
                # Update all active flows
                active_flows = self.shared_events.get_active_flows()

                for flow_info in active_flows:
                    flow_id = flow_info["id"]

                    # Track flow if new
                    if flow_id not in self.active_flows:
                        self.active_flows[flow_id] = {
                            "start_time": datetime.fromisoformat(
                                flow_info["started_at"]
                            ),
                            "project_name": flow_info["project_name"],
                            "events": [],
                        }

                    # Update progress
                    progress = await self.track_flow_progress(flow_id)

                    # Broadcast to clients
                    await self.broadcast_update(progress)

                # Clean up completed flows
                self._cleanup_completed_flows()

                await asyncio.sleep(1)  # Update every second

            except Exception as e:
                import sys
                print(f"Monitoring error: {e}", file=sys.stderr)
                await asyncio.sleep(5)

    async def track_flow_progress(self, flow_id: str) -> ProgressUpdate:
        """
        Track progress of a specific flow.

        Parameters
        ----------
        flow_id : str
            The flow ID to track

        Returns
        -------
        ProgressUpdate
            Current progress and health status
        """
        # Get current events
        events = self.shared_events.get_flow_events(flow_id)
        flow_data = self.active_flows.get(flow_id, {})

        # Calculate progress
        progress = self.calculate_progress(flow_id, events)

        # Estimate completion
        eta = self.estimate_completion(flow_id, events, progress)

        # Check health
        health = self.check_health(flow_id, events)

        # Determine current stage
        current_stage = events[-1].get("stage", "unknown") if events else "starting"

        return ProgressUpdate(
            flow_id=flow_id,
            progress_percentage=progress,
            current_stage=current_stage,
            eta=eta,
            events_completed=len(events),
            events_total_estimated=self._estimate_total_events(),
            health_status=health,
        )

    def calculate_progress(self, flow_id: str, events: List[Dict[str, Any]]) -> float:
        """
        Calculate completion percentage.

        Uses historical data to estimate total expected events.
        """
        if not events:
            return 0.0

        # Check if completed
        for event in events:
            if event.get("event_type") == "pipeline_completed":
                return 100.0

        # Estimate based on stages completed
        stages_completed = set()
        expected_stages = [
            "mcp_request",
            "ai_analysis",
            "prd_parsing",
            "task_generation",
            "task_creation",
            "task_completion",
        ]

        for event in events:
            stage = event.get("stage")
            if stage:
                stages_completed.add(stage)

        # Basic progress calculation
        stage_progress = len(stages_completed) / len(expected_stages) * 100

        # Refine with event count
        avg_events = (
            statistics.mean(self.historical_data["avg_events_per_flow"])
            if self.historical_data["avg_events_per_flow"]
            else 20
        )
        event_progress = min(len(events) / avg_events * 100, 95)

        # Weight both factors
        return min((stage_progress + event_progress) / 2, 95)

    def estimate_completion(
        self, flow_id: str, events: List[Dict[str, Any]], current_progress: float
    ) -> Optional[datetime]:
        """
        Estimate completion time using historical data.

        Analyzes similar past flows and current progress rate.
        """
        if current_progress >= 100:
            return None

        flow_data = self.active_flows.get(flow_id, {})
        start_time = flow_data.get("start_time")

        if not start_time:
            return None

        # Calculate elapsed time
        elapsed = (datetime.now() - start_time).total_seconds()

        if current_progress > 0:
            # Simple linear estimation
            total_estimated = elapsed / (current_progress / 100)
            remaining = total_estimated - elapsed

            # Adjust based on current stage
            current_stage = events[-1].get("stage") if events else None
            if (
                current_stage
                and current_stage in self.historical_data["avg_durations_by_stage"]
            ):
                # Add expected duration for remaining stages
                remaining_stages = self._get_remaining_stages(current_stage)
                for stage in remaining_stages:
                    if stage in self.historical_data["avg_durations_by_stage"]:
                        avg_duration = statistics.mean(
                            self.historical_data["avg_durations_by_stage"][stage]
                        )
                        remaining += avg_duration / 1000  # Convert to seconds

            return datetime.now() + timedelta(seconds=remaining)

        return None

    def _get_remaining_stages(self, current_stage: str) -> List[str]:
        """Get stages that come after the current stage."""
        stage_order = [
            "mcp_request",
            "ai_analysis",
            "prd_parsing",
            "task_generation",
            "task_creation",
            "task_assignment",
            "work_progress",
            "task_completion",
        ]

        try:
            current_index = stage_order.index(current_stage)
            return stage_order[current_index + 1 :]
        except ValueError:
            return []

    def check_health(self, flow_id: str, events: List[Dict[str, Any]]) -> FlowHealth:
        """
        Check health status of a flow.

        Identifies issues and potential problems.
        """
        issues = []
        metrics = {}

        # Check for errors
        error_count = 0
        for event in events:
            if event.get("status") == "failed" or event.get("error"):
                error_count += 1
                issues.append(f"Error in {event.get('event_type', 'unknown')}")

        metrics["error_count"] = error_count

        # Check for slow stages
        slow_stages = []
        for event in events:
            if "duration_ms" in event:
                stage = event.get("stage", "unknown")
                duration = event["duration_ms"]

                # Compare to historical average
                if stage in self.historical_data["avg_durations_by_stage"]:
                    avg_duration = statistics.mean(
                        self.historical_data["avg_durations_by_stage"][stage]
                    )
                    if duration > avg_duration * 1.5:  # 50% slower than average
                        slow_stages.append(stage)
                        issues.append(f"Stage '{stage}' is running slowly")

        metrics["slow_stages"] = slow_stages

        # Check for stalls
        if events:
            last_event_time = datetime.fromisoformat(events[-1].get("timestamp", ""))
            stall_duration = (datetime.now() - last_event_time).total_seconds()

            if stall_duration > 60:  # No events for 60 seconds
                issues.append(f"Flow stalled for {int(stall_duration)}s")
                metrics["stall_duration"] = stall_duration

        # Determine overall status
        if error_count > 0 or len(slow_stages) > 2:
            status = "critical"
        elif len(issues) > 0:
            status = "warning"
        else:
            status = "healthy"

        return FlowHealth(
            flow_id=flow_id, status=status, issues=issues, metrics=metrics
        )

    def _estimate_total_events(self) -> int:
        """Estimate total number of events based on historical data."""
        if self.historical_data["avg_events_per_flow"]:
            return int(statistics.mean(self.historical_data["avg_events_per_flow"]))
        return 20  # Default estimate

    def _cleanup_completed_flows(self):
        """Remove completed flows from active tracking."""
        completed_flows = []

        for flow_id, flow_data in self.active_flows.items():
            # Check if flow is completed
            events = self.shared_events.get_flow_events(flow_id)
            for event in events:
                if event.get("event_type") == "pipeline_completed":
                    completed_flows.append(flow_id)
                    break

        # Remove completed flows
        for flow_id in completed_flows:
            del self.active_flows[flow_id]

    async def broadcast_update(self, update: ProgressUpdate):
        """
        Broadcast update to all connected clients.

        Parameters
        ----------
        update : ProgressUpdate
            The update to broadcast
        """
        # Convert to dict for JSON serialization
        update_dict = asdict(update)

        # Convert datetime to ISO format
        if update.eta:
            update_dict["eta"] = update.eta.isoformat()

        # In production, broadcast via WebSocket
        # For now, just track internally
        self.last_updates = getattr(self, "last_updates", {})
        self.last_updates[update.flow_id] = update_dict

    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get current dashboard data.

        Returns
        -------
        Dict[str, Any]
            Complete dashboard state
        """
        active_count = len(self.active_flows)

        # Aggregate health statuses
        health_summary = {"healthy": 0, "warning": 0, "critical": 0}

        flow_updates = []

        for flow_id in self.active_flows:
            # Get latest update
            if hasattr(self, "last_updates") and flow_id in self.last_updates:
                update = self.last_updates[flow_id]
                health_status = update["health_status"]["status"]
                health_summary[health_status] += 1
                flow_updates.append(update)

        # Calculate system metrics
        system_metrics = {
            "active_flows": active_count,
            "flows_per_hour": self._calculate_throughput(),
            "avg_completion_time": self._calculate_avg_completion_time(),
            "success_rate": self._calculate_success_rate(),
        }

        return {
            "timestamp": datetime.now().isoformat(),
            "active_flows": flow_updates,
            "health_summary": health_summary,
            "system_metrics": system_metrics,
            "alerts": self._get_current_alerts(),
        }

    def _calculate_throughput(self) -> float:
        """Calculate flows per hour."""
        # In production, track over time
        # For now, estimate from historical data
        all_data = self.shared_events._read_events()

        completed_last_hour = 0
        one_hour_ago = datetime.now() - timedelta(hours=1)

        for flow_info in all_data["flows"].values():
            if flow_info.get("completed_at"):
                completed_time = datetime.fromisoformat(flow_info["completed_at"])
                if completed_time > one_hour_ago:
                    completed_last_hour += 1

        return completed_last_hour

    def _calculate_avg_completion_time(self) -> float:
        """Calculate average completion time in minutes."""
        all_data = self.shared_events._read_events()
        completion_times = []

        for flow_info in all_data["flows"].values():
            if flow_info.get("completed_at") and flow_info.get("started_at"):
                start = datetime.fromisoformat(flow_info["started_at"])
                end = datetime.fromisoformat(flow_info["completed_at"])
                duration_minutes = (end - start).total_seconds() / 60
                completion_times.append(duration_minutes)

        return statistics.mean(completion_times) if completion_times else 0

    def _calculate_success_rate(self) -> float:
        """Calculate success rate of flows."""
        all_data = self.shared_events._read_events()
        total_completed = 0
        successful = 0

        for flow_id, flow_info in all_data["flows"].items():
            if flow_info.get("completed_at"):
                total_completed += 1

                # Check if successful
                flow_events = [
                    e for e in all_data["events"] if e.get("flow_id") == flow_id
                ]
                for event in flow_events:
                    if event.get("event_type") == "pipeline_completed":
                        if event.get("data", {}).get("success", False):
                            successful += 1
                        break

        return (successful / total_completed * 100) if total_completed > 0 else 0

    def _get_current_alerts(self) -> List[Dict[str, Any]]:
        """Get current system alerts."""
        alerts = []

        # Check for critical flows
        critical_count = sum(
            1
            for update in getattr(self, "last_updates", {}).values()
            if update["health_status"]["status"] == "critical"
        )

        if critical_count > 0:
            alerts.append(
                {
                    "level": "error",
                    "message": f"{critical_count} flows in critical state",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Check for high error rate
        error_flows = sum(
            1
            for update in getattr(self, "last_updates", {}).values()
            if update["health_status"]["metrics"].get("error_count", 0) > 0
        )

        if error_flows > len(self.active_flows) * 0.3:  # 30% error rate
            alerts.append(
                {
                    "level": "warning",
                    "message": "High error rate detected",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        return alerts
