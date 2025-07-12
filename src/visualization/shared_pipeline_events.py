"""
Minimal stubs for pipeline event tracking

These are lightweight stubs to maintain Marcus core functionality
without the full visualization system. The actual visualization
is now handled by Seneca.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import json


class SharedPipelineEvents:
    """Minimal stub for pipeline event tracking"""
    
    def __init__(self):
        self.events = []
    
    def log_event(self, event_type: str, data: Dict[str, Any]):
        """Log a pipeline event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data
        }
        self.events.append(event)
    
    def get_events(self) -> List[Dict[str, Any]]:
        """Get all logged events"""
        return self.events.copy()
    
    def _read_events(self) -> Dict[str, Any]:
        """Internal method to read events (for backwards compatibility)"""
        return {
            "flows": {},
            "events": self.get_events()
        }


class SharedPipelineVisualizer:
    """Minimal stub for pipeline visualization"""
    
    def __init__(self):
        self.pipeline_events = SharedPipelineEvents()
    
    def log_event(self, event_type: str, data: Dict[str, Any]):
        """Log an event to the pipeline"""
        self.pipeline_events.log_event(event_type, data)
    
    def get_flow_state(self) -> Dict[str, Any]:
        """Get current flow state"""
        return {
            "events": len(self.pipeline_events.events),
            "status": "running"
        }
    
    def start_flow(self, flow_id: str, metadata: Dict[str, Any] = None):
        """Start a new pipeline flow"""
        self.log_event("flow_start", {
            "flow_id": flow_id,
            "metadata": metadata or {}
        })
    
    def end_flow(self, flow_id: str, result: Dict[str, Any] = None):
        """End a pipeline flow"""
        self.log_event("flow_end", {
            "flow_id": flow_id,
            "result": result or {}
        })


class PipelineStage:
    """Minimal stub for pipeline stage representation"""
    
    def __init__(self, name: str, stage_type: str = "general"):
        self.name = name
        self.stage_type = stage_type
        self.status = "pending"
        self.metadata = {}
    
    def start(self):
        """Mark stage as started"""
        self.status = "running"
    
    def complete(self, result: Any = None):
        """Mark stage as completed"""
        self.status = "completed"
        if result is not None:
            self.metadata["result"] = result
    
    def fail(self, error: str):
        """Mark stage as failed"""
        self.status = "failed"
        self.metadata["error"] = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "stage_type": self.stage_type,
            "status": self.status,
            "metadata": self.metadata
        }


# Global instances for backwards compatibility
shared_pipeline_events = SharedPipelineEvents()
shared_pipeline_visualizer = SharedPipelineVisualizer()