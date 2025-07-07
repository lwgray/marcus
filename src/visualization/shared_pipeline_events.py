"""
Shared Pipeline Events - File-based event sharing between MCP and UI servers

Uses a JSON file to share pipeline events between processes.
"""

import fcntl
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .pipeline_flow import PipelineStage

# Use absolute path based on Marcus root directory
MARCUS_ROOT = Path(__file__).parent.parent.parent
PIPELINE_EVENTS_FILE = MARCUS_ROOT / "logs" / "pipeline_events.json"


class SharedPipelineEvents:
    """Manages shared pipeline events between processes"""

    def __init__(self):
        self.events_file = PIPELINE_EVENTS_FILE
        self.events_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize file if it doesn't exist
        if not self.events_file.exists():
            self._write_events({"flows": {}, "events": []})

    def _read_events(self) -> Dict[str, Any]:
        """Read events from file with locking"""
        try:
            with open(self.events_file, "r") as f:
                # Acquire shared lock for reading
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return {"flows": {}, "events": []}

    def _write_events(self, data: Dict[str, Any]):
        """Write events to file with locking"""
        with open(self.events_file, "w") as f:
            # Acquire exclusive lock for writing
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(data, f, indent=2, default=str)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def add_flow(self, flow_id: str, project_name: str):
        """Add a new flow"""
        data = self._read_events()
        data["flows"][flow_id] = {
            "id": flow_id,
            "project_name": project_name,
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "is_active": True,
        }
        self._write_events(data)

    def add_event(self, flow_id: str, event: Dict[str, Any]):
        """Add an event to a flow"""
        data = self._read_events()

        # Ensure flow exists
        if flow_id not in data["flows"]:
            return

        # Add event with enhanced metadata support
        event_data = {
            "flow_id": flow_id,
            "timestamp": datetime.now().isoformat(),
            **event,
        }

        # Add event ID if not present
        if "event_id" not in event_data:
            event_data[
                "event_id"
            ] = f"{flow_id}_{len([e for e in data['events'] if e.get('flow_id') == flow_id])}"

        data["events"].append(event_data)

        # Update flow's current stage
        if "stage" in event:
            data["flows"][flow_id]["current_stage"] = event["stage"]

        self._write_events(data)

    def complete_flow(self, flow_id: str):
        """Mark a flow as completed"""
        data = self._read_events()
        if flow_id in data["flows"]:
            data["flows"][flow_id]["completed_at"] = datetime.now().isoformat()
            data["flows"][flow_id]["is_active"] = False
            self._write_events(data)

    def get_active_flows(self) -> List[Dict[str, Any]]:
        """Get all active flows (including recently completed)"""
        data = self._read_events()
        active_flows = []

        for flow_id, flow_data in data["flows"].items():
            # Include active flows and recently completed flows (last hour)
            is_recent = True
            if flow_data.get("completed_at"):
                completed_time = datetime.fromisoformat(flow_data["completed_at"])
                age_minutes = (datetime.now() - completed_time).total_seconds() / 60
                is_recent = age_minutes < 60  # Show flows from last hour

            if flow_data.get("is_active", False) or is_recent:
                # Count events for this flow
                event_count = sum(
                    1 for e in data["events"] if e.get("flow_id") == flow_id
                )

                # Get current stage from last event
                flow_events = [e for e in data["events"] if e.get("flow_id") == flow_id]
                current_stage = flow_events[-1].get("stage") if flow_events else None

                active_flows.append(
                    {
                        "id": flow_id,
                        "project_name": flow_data["project_name"],
                        "started_at": flow_data["started_at"],
                        "event_count": event_count,
                        "current_stage": current_stage,
                    }
                )

        return active_flows

    def get_flow_events(self, flow_id: str) -> List[Dict[str, Any]]:
        """Get all events for a specific flow"""
        data = self._read_events()
        return [e for e in data["events"] if e.get("flow_id") == flow_id]

    def clear_old_events(self, hours: int = 24):
        """Clear events older than specified hours"""
        data = self._read_events()
        cutoff = datetime.now().timestamp() - (hours * 3600)

        # Filter flows
        active_flows = {}
        for flow_id, flow_data in data["flows"].items():
            started_at = datetime.fromisoformat(flow_data["started_at"]).timestamp()
            if started_at > cutoff:
                active_flows[flow_id] = flow_data

        # Filter events
        active_events = []
        for event in data["events"]:
            if event["flow_id"] in active_flows:
                active_events.append(event)

        data["flows"] = active_flows
        data["events"] = active_events
        self._write_events(data)


class SharedPipelineVisualizer:
    """Pipeline visualizer that uses shared file storage"""

    def __init__(self):
        self.shared_events = SharedPipelineEvents()

    def start_flow(self, flow_id: str, project_name: str):
        """Start a new flow"""
        self.shared_events.add_flow(flow_id, project_name)

    def add_event(
        self,
        flow_id: str,
        stage: PipelineStage,
        event_type: str,
        data: Dict[str, Any],
        status: str = "in_progress",
        duration_ms: Optional[int] = None,
        error: Optional[str] = None,
    ):
        """Add an event"""
        event = {
            "stage": stage.value,
            "event_type": event_type,
            "data": data,
            "status": status,
        }

        if duration_ms is not None:
            event["duration_ms"] = duration_ms
        if error is not None:
            event["error"] = error

        self.shared_events.add_event(flow_id, event)

    def complete_flow(self, flow_id: str):
        """Complete a flow"""
        self.shared_events.complete_flow(flow_id)

    def track_ai_analysis(
        self,
        flow_id: str,
        prd_text: str,
        analysis_result: Dict[str, Any],
        duration_ms: int,
    ):
        """Track AI analysis stage with enhanced insights"""
        self.add_event(
            flow_id=flow_id,
            stage=PipelineStage.AI_ANALYSIS,
            event_type="ai_prd_analysis",
            data={
                "prd_length": len(prd_text),
                "functional_requirements": len(
                    analysis_result.get("functionalRequirements", [])
                ),
                "confidence": analysis_result.get("confidence", 0),
                # Enhanced insights
                "extracted_requirements": analysis_result.get(
                    "extractedRequirements", []
                ),
                "ambiguities": analysis_result.get("ambiguities", []),
                "assumptions": analysis_result.get("assumptions", []),
                "similar_projects": analysis_result.get("similarProjects", []),
                "ai_metrics": {
                    "model": analysis_result.get("model", "unknown"),
                    "tokens_used": analysis_result.get("tokensUsed", 0),
                    "temperature": analysis_result.get("temperature", 0.7),
                },
            },
            duration_ms=duration_ms,
            status="completed",
        )

    def track_task_generation(
        self,
        flow_id: str,
        task_count: int,
        tasks: List[Dict[str, Any]],
        duration_ms: int,
        generation_context: Optional[Dict[str, Any]] = None,
    ):
        """Track task generation stage with reasoning"""
        self.add_event(
            flow_id=flow_id,
            stage=PipelineStage.TASK_GENERATION,
            event_type="tasks_generated",
            data={
                "task_count": task_count,
                "task_names": [t.get("name", "Unnamed") for t in tasks[:5]],  # First 5
                "has_more": len(tasks) > 5,
                # Enhanced insights
                "task_breakdown_reasoning": generation_context.get("reasoning", "")
                if generation_context
                else "",
                "dependency_graph": generation_context.get("dependencies", {})
                if generation_context
                else {},
                "effort_estimates": generation_context.get("effort_estimates", {})
                if generation_context
                else {},
                "risk_factors": generation_context.get("risk_factors", [])
                if generation_context
                else [],
                "alternative_structures": generation_context.get(
                    "alternatives_considered", []
                )
                if generation_context
                else [],
                "complexity_score": generation_context.get("complexity_score", 0)
                if generation_context
                else 0,
            },
            duration_ms=duration_ms,
            status="completed",
        )

    def track_task_creation(
        self,
        flow_id: str,
        task_id: str,
        task_name: str,
        success: bool,
        error: Optional[str] = None,
    ):
        """Track individual task creation"""
        self.add_event(
            flow_id=flow_id,
            stage=PipelineStage.TASK_CREATION,
            event_type="task_created" if success else "task_creation_failed",
            data={"task_id": task_id, "task_name": task_name},
            status="completed" if success else "failed",
            error=error,
        )

    def get_active_flows(self) -> List[Dict[str, Any]]:
        """Get active flows"""
        return self.shared_events.get_active_flows()

    def track_decision_point(
        self,
        flow_id: str,
        stage: PipelineStage,
        decision: str,
        rationale: str,
        confidence: float,
        alternatives: List[Dict[str, Any]],
    ):
        """Track a decision point in the pipeline"""
        self.add_event(
            flow_id=flow_id,
            stage=stage,
            event_type="decision_point",
            data={
                "decision": decision,
                "rationale": rationale,
                "confidence": confidence,
                "alternatives_considered": alternatives,
                "timestamp": datetime.now().isoformat(),
            },
            status="completed",
        )

    def track_quality_metrics(self, flow_id: str, metrics: Dict[str, Any]):
        """Track quality metrics for the pipeline execution"""
        self.add_event(
            flow_id=flow_id,
            stage=PipelineStage.TASK_COMPLETION,
            event_type="quality_metrics",
            data={
                "task_completeness_score": metrics.get("task_completeness", 0),
                "requirement_coverage": metrics.get("requirement_coverage", {}),
                "complexity_analysis": metrics.get("complexity_analysis", {}),
                "missing_considerations": metrics.get("missing_considerations", []),
                "overall_quality_score": metrics.get("overall_quality", 0),
            },
            status="completed",
        )

    def track_performance_metrics(
        self, flow_id: str, stage: PipelineStage, metrics: Dict[str, Any]
    ):
        """Track performance metrics for a pipeline stage"""
        self.add_event(
            flow_id=flow_id,
            stage=stage,
            event_type="performance_metrics",
            data={
                "token_usage": metrics.get("tokens", 0),
                "response_time_ms": metrics.get("response_time", 0),
                "retry_attempts": metrics.get("retries", 0),
                "cost_estimate": metrics.get("cost", 0),
                "provider": metrics.get("provider", "unknown"),
            },
            status="completed",
        )

    def get_flow_visualization(self, flow_id: str) -> Dict[str, Any]:
        """Get visualization data for a flow"""
        events = self.shared_events.get_flow_events(flow_id)

        if not events:
            return {"error": f"Flow {flow_id} not found"}

        # Build nodes and edges
        nodes = []
        edges = []

        for i, event in enumerate(events):
            node = {
                "id": f"{flow_id}_{i}",
                "label": event["event_type"],
                "stage": event.get("stage", "unknown"),
                "timestamp": event["timestamp"],
                "status": event.get("status", "unknown"),
                "data": event.get("data", {}),
            }

            if "error" in event:
                node["error"] = event["error"]
            if "duration_ms" in event:
                node["duration_ms"] = event["duration_ms"]

            nodes.append(node)

            # Add edge from previous node
            if i > 0:
                edges.append({"from": f"{flow_id}_{i-1}", "to": f"{flow_id}_{i}"})

        return {
            "flow_id": flow_id,
            "nodes": nodes,
            "edges": edges,
            "total_events": len(events),
        }
