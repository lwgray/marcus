"""
Minimal stubs for pipeline flow management
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from .shared_pipeline_events import PipelineStage


class PipelineFlow:
    """Minimal stub for pipeline flow tracking"""
    
    def __init__(self, flow_id: str, flow_type: str = "general"):
        self.flow_id = flow_id
        self.flow_type = flow_type
        self.stages: List[PipelineStage] = []
        self.status = "created"
        self.created_at = datetime.now().isoformat()
        self.metadata = {}
    
    def add_stage(self, stage: PipelineStage):
        """Add a stage to the flow"""
        self.stages.append(stage)
    
    def start(self):
        """Start the flow"""
        self.status = "running"
    
    def complete(self):
        """Complete the flow"""
        self.status = "completed"
    
    def fail(self, error: str):
        """Fail the flow"""
        self.status = "failed"
        self.metadata["error"] = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "flow_id": self.flow_id,
            "flow_type": self.flow_type,
            "status": self.status,
            "created_at": self.created_at,
            "stages": [stage.to_dict() for stage in self.stages],
            "metadata": self.metadata
        }