"""
Event-Integrated Pipeline Visualizer

Connects the Events system to the visualization pipeline for real-time updates
without polling. This provides instant visualization updates when tasks change.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

from src.core.events import Events, EventTypes, Event
from src.core.models import TaskStatus
from src.visualization.shared_pipeline_events import SharedPipelineEvents
from src.visualization.pipeline_flow import PipelineStage

logger = logging.getLogger(__name__)


class EventIntegratedVisualizer:
    """
    Bridges the Events system with the visualization pipeline.
    
    Instead of polling for updates, this subscribes to events and
    updates the visualization in real-time.
    """
    
    def __init__(self, events_system: Optional[Events] = None):
        """
        Initialize the event-integrated visualizer.
        
        Args:
            events_system: The Events system to subscribe to
        """
        self.events = events_system
        self.shared_pipeline = SharedPipelineEvents()
        self.active_flows: Dict[str, Dict[str, Any]] = {}
        self._subscribed = False
        
    async def initialize(self):
        """Initialize and subscribe to events"""
        if self.events and not self._subscribed:
            # Subscribe to all relevant events
            event_types = [
                EventTypes.PROJECT_CREATED,
                EventTypes.TASK_REQUESTED,
                EventTypes.TASK_ASSIGNED,
                EventTypes.TASK_STARTED,
                EventTypes.TASK_PROGRESS,
                EventTypes.TASK_COMPLETED,
                EventTypes.TASK_BLOCKED,
                EventTypes.AGENT_REGISTERED,
                EventTypes.AGENT_STATUS_CHANGED,
                EventTypes.CONTEXT_UPDATED,
                EventTypes.DECISION_LOGGED,
            ]
            
            for event_type in event_types:
                self.events.subscribe(event_type, self._handle_event)
                
            # Also subscribe to all events for catch-all
            self.events.subscribe("*", self._handle_any_event)
            
            self._subscribed = True
            logger.info("Visualization subscribed to Events system")
            
    async def _handle_event(self, event: Event):
        """Handle specific events and update visualization"""
        try:
            # Map event types to pipeline stages
            stage_mapping = {
                EventTypes.PROJECT_CREATED: PipelineStage.PRD_ANALYSIS,
                EventTypes.TASK_REQUESTED: PipelineStage.TASK_MATCHING,
                EventTypes.TASK_ASSIGNED: PipelineStage.ASSIGNMENT,
                EventTypes.TASK_STARTED: PipelineStage.EXECUTION,
                EventTypes.TASK_PROGRESS: PipelineStage.EXECUTION,
                EventTypes.TASK_COMPLETED: PipelineStage.COMPLETION,
                EventTypes.TASK_BLOCKED: PipelineStage.EXECUTION,
            }
            
            stage = stage_mapping.get(event.event_type, PipelineStage.ORCHESTRATION)
            
            # Create or get flow ID
            flow_id = self._get_or_create_flow(event)
            
            # Convert event to pipeline format
            pipeline_event = {
                "event_id": event.event_id,
                "stage": stage.value,
                "event_type": event.event_type,
                "actor": event.source,
                "action": self._get_action_from_event(event),
                "details": event.data,
                "metadata": {
                    **event.metadata,
                    "original_event_type": event.event_type,
                    "timestamp": event.timestamp.isoformat()
                }
            }
            
            # Add special handling for different event types
            if event.event_type == EventTypes.TASK_ASSIGNED:
                pipeline_event["task_info"] = {
                    "task_id": event.data.get("task_id"),
                    "task_name": event.data.get("task_name"),
                    "agent_id": event.data.get("agent_id"),
                    "has_context": event.data.get("has_context", False),
                    "has_predictions": event.data.get("has_predictions", False)
                }
                
            elif event.event_type == EventTypes.TASK_PROGRESS:
                pipeline_event["progress_info"] = {
                    "task_id": event.data.get("task_id"),
                    "progress": event.data.get("progress", 0),
                    "status": event.data.get("status"),
                    "message": event.data.get("message")
                }
                
            elif event.event_type == EventTypes.CONTEXT_UPDATED:
                pipeline_event["context_info"] = {
                    "task_id": event.data.get("task_id"),
                    "context_size": event.data.get("context_size", {})
                }
                
            # Add to shared pipeline
            self.shared_pipeline.add_event(flow_id, pipeline_event)
            
            # Update flow status
            if event.event_type == EventTypes.TASK_COMPLETED:
                # Check if all tasks are completed
                if self._check_flow_completion(flow_id):
                    self.shared_pipeline.complete_flow(flow_id)
                    
        except Exception as e:
            logger.error(f"Error handling event {event.event_type}: {e}")
            
    async def _handle_any_event(self, event: Event):
        """Handle any event for logging and monitoring"""
        # Log all events for debugging
        logger.debug(f"Event: {event.event_type} from {event.source}")
        
        # Track event statistics
        if not hasattr(self, "_event_stats"):
            self._event_stats = {}
            
        if event.event_type not in self._event_stats:
            self._event_stats[event.event_type] = 0
        self._event_stats[event.event_type] += 1
        
    def _get_or_create_flow(self, event: Event) -> str:
        """Get or create a flow ID for the event"""
        # Try to extract flow ID from event data
        flow_id = event.data.get("flow_id")
        if flow_id:
            return flow_id
            
        # Try to get project/task context
        project_id = event.data.get("project_id")
        task_id = event.data.get("task_id")
        
        if project_id:
            flow_id = f"project_{project_id}"
        elif task_id:
            # Find flow by task
            for fid, flow in self.active_flows.items():
                if task_id in flow.get("tasks", []):
                    return fid
            # Create new flow for task
            flow_id = f"task_flow_{task_id}"
        else:
            # Default flow
            flow_id = "default_flow"
            
        # Create flow if it doesn't exist
        if flow_id not in self.active_flows:
            self.active_flows[flow_id] = {
                "created_at": datetime.now(),
                "tasks": [],
                "events": []
            }
            
            project_name = event.data.get("project_name", flow_id)
            self.shared_pipeline.add_flow(flow_id, project_name)
            
        # Track task if present
        if task_id and task_id not in self.active_flows[flow_id]["tasks"]:
            self.active_flows[flow_id]["tasks"].append(task_id)
            
        return flow_id
        
    def _get_action_from_event(self, event: Event) -> str:
        """Convert event type to human-readable action"""
        action_map = {
            EventTypes.PROJECT_CREATED: "Project created",
            EventTypes.TASK_REQUESTED: "Task requested",
            EventTypes.TASK_ASSIGNED: "Task assigned",
            EventTypes.TASK_STARTED: "Task started",
            EventTypes.TASK_PROGRESS: "Progress update",
            EventTypes.TASK_COMPLETED: "Task completed",
            EventTypes.TASK_BLOCKED: "Task blocked",
            EventTypes.AGENT_REGISTERED: "Agent registered",
            EventTypes.CONTEXT_UPDATED: "Context prepared",
            EventTypes.DECISION_LOGGED: "Decision logged",
        }
        
        return action_map.get(event.event_type, event.event_type.replace("_", " ").title())
        
    def _check_flow_completion(self, flow_id: str) -> bool:
        """Check if a flow is complete"""
        # Simple heuristic - could be enhanced
        flow = self.active_flows.get(flow_id, {})
        
        # If we have task tracking, check if all are done
        if "tasks" in flow and flow["tasks"]:
            # Would need to query task status
            # For now, return False
            return False
            
        # Otherwise, use event count heuristic
        event_count = len(flow.get("events", []))
        return event_count > 10  # Arbitrary threshold
        
    def get_event_statistics(self) -> Dict[str, Any]:
        """Get statistics about processed events"""
        return {
            "subscribed": self._subscribed,
            "active_flows": len(self.active_flows),
            "event_counts": getattr(self, "_event_stats", {}),
            "total_events": sum(getattr(self, "_event_stats", {}).values())
        }
        
    async def create_context_visualization(self, task_id: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create visualization data for task context.
        
        This formats the context data for display in the UI.
        """
        viz_data = {
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "dependencies": {
                "explicit": [],
                "inferred": [],
                "dependent_tasks": []
            },
            "implementations": [],
            "decisions": [],
            "patterns": []
        }
        
        # Extract dependency information
        if "previous_implementations" in context_data:
            for impl_id, impl_data in context_data["previous_implementations"].items():
                viz_data["implementations"].append({
                    "task_id": impl_id,
                    "summary": self._summarize_implementation(impl_data),
                    "timestamp": impl_data.get("timestamp")
                })
                
        # Extract decisions
        if "architectural_decisions" in context_data:
            for decision in context_data["architectural_decisions"]:
                viz_data["decisions"].append({
                    "what": decision.get("what"),
                    "why": decision.get("why"),
                    "impact": decision.get("impact"),
                    "agent": decision.get("agent_id"),
                    "timestamp": decision.get("timestamp")
                })
                
        # Extract dependent tasks
        if "dependent_tasks" in context_data:
            for dep in context_data["dependent_tasks"]:
                viz_data["dependencies"]["dependent_tasks"].append({
                    "task_id": dep.get("task_id"),
                    "task_name": dep.get("task_name"),
                    "expected_interface": dep.get("expected_interface")
                })
                
        return viz_data
        
    def _summarize_implementation(self, impl_data: Dict[str, Any]) -> str:
        """Create a summary of implementation details"""
        summary_parts = []
        
        if "apis" in impl_data:
            summary_parts.append(f"{len(impl_data['apis'])} APIs")
        if "models" in impl_data:
            summary_parts.append(f"{len(impl_data['models'])} models")
        if "patterns" in impl_data:
            summary_parts.append(f"{len(impl_data['patterns'])} patterns")
            
        return ", ".join(summary_parts) if summary_parts else "Implementation details available"