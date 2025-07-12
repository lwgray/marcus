"""
Pipeline Flow Manager

Manages pipeline flow data and events for visualization.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


class PipelineFlowManager:
    """Manages pipeline flows and their events."""

    def __init__(self) -> None:
        self.flows: Dict[str, Any] = {}
        self.events: Dict[str, List[Dict[str, Any]]] = {}

    def create_flow(
        self, project_name: str, project_type: str, description: str = ""
    ) -> str:
        """Create a new pipeline flow."""
        flow_id = str(uuid.uuid4())

        flow = {
            "flow_id": flow_id,
            "project_name": project_name,
            "project_type": project_type,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "status": "active",
            "current_stage": "initialization",
            "progress_percentage": 0,
            "health_status": {"status": "healthy", "message": "Flow initialized"},
            "metrics": {
                "task_count": 0,
                "completed_count": 0,
                "duration_seconds": 0,
                "cost": 0.0,
                "quality_score": 1.0,
                "complexity": 1.0,
            },
        }

        self.flows[flow_id] = flow
        self.events[flow_id] = []

        # Add initial event
        self.add_event(
            flow_id,
            {
                "event_type": "flow_created",
                "timestamp": datetime.now().isoformat(),
                "stage": "initialization",
                "message": f"Started pipeline flow for {project_name}",
            },
        )

        return flow_id

    def add_event(self, flow_id: str, event: Dict[str, Any]) -> bool:
        """Add an event to a flow."""
        if flow_id not in self.flows:
            return False

        event["event_id"] = str(uuid.uuid4())
        self.events[flow_id].append(event)

        # Update flow metrics based on event
        self._update_flow_metrics(flow_id, event)

        return True

    def update_flow_stage(
        self, flow_id: str, stage: str, progress: Optional[int] = None
    ) -> bool:
        """Update the current stage of a flow."""
        if flow_id not in self.flows:
            return False

        self.flows[flow_id]["current_stage"] = stage
        if progress is not None:
            self.flows[flow_id]["progress_percentage"] = progress

        self.add_event(
            flow_id,
            {
                "event_type": "stage_changed",
                "timestamp": datetime.now().isoformat(),
                "stage": stage,
                "progress": progress,
            },
        )

        return True

    def complete_flow(self, flow_id: str) -> bool:
        """Mark a flow as completed."""
        if flow_id not in self.flows:
            return False

        self.flows[flow_id]["status"] = "completed"
        self.flows[flow_id]["completed_at"] = datetime.now().isoformat()
        self.flows[flow_id]["progress_percentage"] = 100

        self.add_event(
            flow_id,
            {
                "event_type": "flow_completed",
                "timestamp": datetime.now().isoformat(),
                "stage": "completion",
                "message": "Pipeline flow completed successfully",
            },
        )

        return True

    def get_flow(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific flow."""
        return self.flows.get(flow_id)

    def get_flow_events(self, flow_id: str) -> List[Dict[str, Any]]:
        """Get events for a specific flow."""
        return self.events.get(flow_id, [])  # type: ignore[no-any-return]

    def get_active_flows(self) -> List[Dict[str, Any]]:
        """Get all active flows."""
        return [flow for flow in self.flows.values() if flow.get("status") == "active"]

    def get_all_flows(self) -> List[Dict[str, Any]]:
        """Get all flows."""
        return list(self.flows.values())

    def _update_flow_metrics(self, flow_id: str, event: Dict[str, Any]) -> None:
        """Update flow metrics based on event."""
        flow = self.flows[flow_id]
        metrics = flow["metrics"]

        event_type = event.get("event_type", "")

        if event_type == "task_created":
            metrics["task_count"] += 1
        elif event_type == "task_completed":
            metrics["completed_count"] += 1

        # Update duration
        created_at = datetime.fromisoformat(flow["created_at"])
        duration = (datetime.now() - created_at).total_seconds()
        metrics["duration_seconds"] = duration

        # Update health status
        if metrics["task_count"] > 0:
            completion_rate = metrics["completed_count"] / metrics["task_count"]
            if completion_rate >= 0.8:
                flow["health_status"] = {"status": "healthy", "message": "On track"}
            elif completion_rate >= 0.5:
                flow["health_status"] = {
                    "status": "warning",
                    "message": "Some delays",
                }
            else:
                flow["health_status"] = {
                    "status": "critical",
                    "message": "Behind schedule",
                }
