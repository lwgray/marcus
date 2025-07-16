"""
Minimal stubs for pipeline event tracking

These are lightweight stubs to maintain Marcus core functionality
without the full visualization system. The actual visualization
is now handled by Seneca.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional


class SharedPipelineEvents:
    """Minimal stub for pipeline event tracking"""

    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []

    def log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log a pipeline event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data,
        }
        self.events.append(event)

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all logged events"""
        return self.events.copy()

    def _read_events(self) -> Dict[str, Any]:
        """Internal method to read events (for backwards compatibility)"""
        return {"flows": {}, "events": self.get_events()}


class SharedPipelineVisualizer:
    """Minimal stub for pipeline visualization"""

    def __init__(self) -> None:
        self.pipeline_events = SharedPipelineEvents()

    def log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log an event to the pipeline"""
        self.pipeline_events.log_event(event_type, data)

    def get_flow_state(self) -> Dict[str, Any]:
        """Get current flow state"""
        return {"events": len(self.pipeline_events.events), "status": "running"}

    def start_flow(
        self, flow_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Start a new pipeline flow"""
        self.log_event("flow_start", {"flow_id": flow_id, "metadata": metadata or {}})

    def end_flow(self, flow_id: str, result: Optional[Dict[str, Any]] = None) -> None:
        """End a pipeline flow"""
        self.log_event("flow_end", {"flow_id": flow_id, "result": result or {}})

    def complete_flow(
        self, flow_id: str, result: Optional[Dict[str, Any]] = None
    ) -> None:
        """Complete a pipeline flow (alias for end_flow for compatibility)"""
        self.end_flow(flow_id, result)

    def add_event(
        self,
        flow_id: str,
        stage: Any,
        event_type: str = "info",
        data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        status: Optional[str] = None,
        error: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Add an event to the pipeline flow (compatibility method)"""
        event_data = {
            "flow_id": flow_id,
            "stage": getattr(stage, "name", str(stage)),
            "event_type": event_type,
        }
        if data:
            event_data.update(data)
        if duration_ms is not None:
            event_data["duration_ms"] = duration_ms
        if status is not None:
            event_data["status"] = status
        if error is not None:
            event_data["error"] = error
        # Include any additional kwargs
        event_data.update(kwargs)
        self.log_event("pipeline_event", event_data)


class PipelineStage:
    """Minimal stub for pipeline stage representation"""

    # Stage constants for compatibility
    MCP_REQUEST = "mcp_request"
    AI_ANALYSIS = "ai_analysis"
    PRD_PARSING = "prd_parsing"
    TASK_GENERATION = "task_generation"
    TASK_CREATION = "task_creation"
    TASK_COMPLETION = "task_completion"

    def __init__(self, name: str, stage_type: str = "general") -> None:
        self.name = name
        self.stage_type = stage_type
        self.status = "pending"
        self.metadata: Dict[str, Any] = {}

    def start(self) -> None:
        """Mark stage as started"""
        self.status = "running"

    def complete(self, result: Any = None) -> None:
        """Mark stage as completed"""
        self.status = "completed"
        if result is not None:
            self.metadata["result"] = result

    def fail(self, error: str) -> None:
        """Mark stage as failed"""
        self.status = "failed"
        self.metadata["error"] = error

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "stage_type": self.stage_type,
            "status": self.status,
            "metadata": self.metadata,
        }


# Global instances for backwards compatibility
shared_pipeline_events = SharedPipelineEvents()
shared_pipeline_visualizer = SharedPipelineVisualizer()
