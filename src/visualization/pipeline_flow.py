"""
Pipeline Flow Visualization for Marcus

Visualizes the complete MCP request → AI → Task Generation → Progress pipeline
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Stages in the Marcus pipeline"""
    MCP_REQUEST = "mcp_request"
    AI_ANALYSIS = "ai_analysis"
    PRD_PARSING = "prd_parsing"
    TASK_GENERATION = "task_generation"
    TASK_CREATION = "task_creation"
    TASK_ASSIGNMENT = "task_assignment"
    WORK_PROGRESS = "work_progress"
    TASK_COMPLETION = "task_completion"


@dataclass
class PipelineEvent:
    """Event in the pipeline flow"""
    id: str
    stage: PipelineStage
    timestamp: datetime
    event_type: str
    data: Dict[str, Any]
    parent_id: Optional[str] = None
    duration_ms: Optional[int] = None
    status: str = "in_progress"
    error: Optional[str] = None


@dataclass
class PipelineFlow:
    """Complete pipeline flow from request to completion"""
    id: str
    project_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    events: List[PipelineEvent] = None
    
    def __post_init__(self):
        if self.events is None:
            self.events = []


class PipelineFlowVisualizer:
    """
    Visualizes the Marcus pipeline flow from MCP request to task completion.
    
    Tracks and visualizes:
    - MCP tool calls and responses
    - AI analysis and PRD parsing
    - Task generation and creation
    - Work assignment and progress
    - Task completion status
    """
    
    def __init__(self):
        """Initialize the pipeline flow visualizer"""
        self.active_flows: Dict[str, PipelineFlow] = {}
        self.completed_flows: List[PipelineFlow] = []
        self.event_handlers = []
        
    def start_flow(self, flow_id: str, project_name: str) -> PipelineFlow:
        """Start tracking a new pipeline flow"""
        flow = PipelineFlow(
            id=flow_id,
            project_name=project_name,
            started_at=datetime.now()
        )
        self.active_flows[flow_id] = flow
        
        # Add initial MCP request event
        self.add_event(
            flow_id=flow_id,
            stage=PipelineStage.MCP_REQUEST,
            event_type="create_project_request",
            data={"project_name": project_name}
        )
        
        return flow
    
    def add_event(
        self,
        flow_id: str,
        stage: PipelineStage,
        event_type: str,
        data: Dict[str, Any],
        parent_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
        status: str = "in_progress",
        error: Optional[str] = None
    ) -> Optional[PipelineEvent]:
        """Add an event to the pipeline flow"""
        if flow_id not in self.active_flows:
            logger.warning(f"Flow {flow_id} not found")
            return None
            
        flow = self.active_flows[flow_id]
        
        # Generate event ID
        event_id = f"{flow_id}_{stage.value}_{len(flow.events)}"
        
        event = PipelineEvent(
            id=event_id,
            stage=stage,
            timestamp=datetime.now(),
            event_type=event_type,
            data=data,
            parent_id=parent_id,
            duration_ms=duration_ms,
            status=status,
            error=error
        )
        
        flow.events.append(event)
        
        # Notify handlers
        self._notify_handlers(flow_id, event)
        
        return event
    
    def complete_flow(self, flow_id: str) -> Optional[PipelineFlow]:
        """Mark a flow as completed"""
        if flow_id not in self.active_flows:
            return None
            
        flow = self.active_flows.pop(flow_id)
        flow.completed_at = datetime.now()
        self.completed_flows.append(flow)
        
        # Add completion event
        self.add_event(
            flow_id=flow_id,
            stage=PipelineStage.TASK_COMPLETION,
            event_type="pipeline_completed",
            data={"total_duration_seconds": (flow.completed_at - flow.started_at).total_seconds()},
            status="completed"
        )
        
        return flow
    
    def get_flow_visualization(self, flow_id: str) -> Dict[str, Any]:
        """Get visualization data for a specific flow"""
        flow = self.active_flows.get(flow_id)
        if not flow:
            # Check completed flows
            flow = next((f for f in self.completed_flows if f.id == flow_id), None)
            
        if not flow:
            return {"error": f"Flow {flow_id} not found"}
        
        # Build visualization data
        nodes = []
        edges = []
        
        # Create nodes for each event
        for event in flow.events:
            node = {
                "id": event.id,
                "label": event.event_type,
                "stage": event.stage.value,
                "timestamp": event.timestamp.isoformat(),
                "status": event.status,
                "data": event.data
            }
            
            if event.error:
                node["error"] = event.error
                
            if event.duration_ms:
                node["duration_ms"] = event.duration_ms
                
            nodes.append(node)
            
            # Create edge to parent
            if event.parent_id:
                edges.append({
                    "from": event.parent_id,
                    "to": event.id,
                    "label": f"{event.duration_ms}ms" if event.duration_ms else ""
                })
        
        # Group nodes by stage for layout
        stages = {}
        for node in nodes:
            stage = node["stage"]
            if stage not in stages:
                stages[stage] = []
            stages[stage].append(node)
        
        return {
            "flow_id": flow.id,
            "project_name": flow.project_name,
            "started_at": flow.started_at.isoformat(),
            "completed_at": flow.completed_at.isoformat() if flow.completed_at else None,
            "nodes": nodes,
            "edges": edges,
            "stages": stages,
            "total_events": len(flow.events),
            "is_active": flow_id in self.active_flows
        }
    
    def get_active_flows(self) -> List[Dict[str, Any]]:
        """Get summary of all active flows"""
        return [
            {
                "id": flow.id,
                "project_name": flow.project_name,
                "started_at": flow.started_at.isoformat(),
                "event_count": len(flow.events),
                "current_stage": flow.events[-1].stage.value if flow.events else None
            }
            for flow in self.active_flows.values()
        ]
    
    def add_event_handler(self, handler):
        """Add handler for pipeline events"""
        self.event_handlers.append(handler)
    
    def _notify_handlers(self, flow_id: str, event: PipelineEvent):
        """Notify all handlers of a new event"""
        for handler in self.event_handlers:
            try:
                handler(flow_id, event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
    
    def track_ai_analysis(self, flow_id: str, prd_text: str, analysis_result: Dict[str, Any], duration_ms: int):
        """Track AI analysis stage"""
        self.add_event(
            flow_id=flow_id,
            stage=PipelineStage.AI_ANALYSIS,
            event_type="ai_prd_analysis",
            data={
                "prd_length": len(prd_text),
                "functional_requirements": len(analysis_result.get("functionalRequirements", [])),
                "confidence": analysis_result.get("confidence", 0)
            },
            duration_ms=duration_ms,
            status="completed"
        )
    
    def track_task_generation(self, flow_id: str, task_count: int, tasks: List[Dict[str, Any]], duration_ms: int):
        """Track task generation stage"""
        self.add_event(
            flow_id=flow_id,
            stage=PipelineStage.TASK_GENERATION,
            event_type="tasks_generated",
            data={
                "task_count": task_count,
                "task_names": [t.get("name", "Unnamed") for t in tasks[:5]],  # First 5
                "has_more": len(tasks) > 5
            },
            duration_ms=duration_ms,
            status="completed"
        )
    
    def track_task_creation(self, flow_id: str, task_id: str, task_name: str, success: bool, error: Optional[str] = None):
        """Track individual task creation"""
        self.add_event(
            flow_id=flow_id,
            stage=PipelineStage.TASK_CREATION,
            event_type="task_created" if success else "task_creation_failed",
            data={
                "task_id": task_id,
                "task_name": task_name
            },
            status="completed" if success else "failed",
            error=error
        )
    
    def track_work_progress(self, flow_id: str, task_id: str, agent_id: str, progress: int):
        """Track work progress on tasks"""
        self.add_event(
            flow_id=flow_id,
            stage=PipelineStage.WORK_PROGRESS,
            event_type="progress_update",
            data={
                "task_id": task_id,
                "agent_id": agent_id,
                "progress": progress
            },
            status="in_progress" if progress < 100 else "completed"
        )