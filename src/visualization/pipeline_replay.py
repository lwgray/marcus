"""
Pipeline Replay Controller - Step through pipeline execution chronologically

This module provides replay functionality for pipeline flows, allowing users
to understand each decision point and its impact step by step.
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from .shared_pipeline_events import SharedPipelineEvents


class PipelineReplayController:
    """
    Controls replay functionality for pipeline flows.
    
    Allows stepping through events chronologically with full context
    at each decision point.
    """
    
    def __init__(self, flow_id: str):
        """
        Initialize replay controller for a specific flow.
        
        Parameters
        ----------
        flow_id : str
            The pipeline flow ID to replay
        """
        self.flow_id = flow_id
        self.shared_events = SharedPipelineEvents()
        self.events = self._load_flow_events(flow_id)
        self.current_position = 0
        self.max_position = len(self.events)
        
    def _load_flow_events(self, flow_id: str) -> List[Dict[str, Any]]:
        """Load all events for the specified flow."""
        all_events = self.shared_events.get_flow_events(flow_id)
        # Sort by timestamp to ensure chronological order
        return sorted(all_events, key=lambda e: e.get('timestamp', ''))
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get the current replay state."""
        return {
            "flow_id": self.flow_id,
            "current_position": self.current_position,
            "max_position": self.max_position,
            "is_at_start": self.current_position == 0,
            "is_at_end": self.current_position >= self.max_position,
            "current_event": self.get_current_event(),
            "visible_events": self.get_state_at_position(self.current_position)
        }
    
    def get_current_event(self) -> Optional[Dict[str, Any]]:
        """Get the event at current position."""
        if 0 <= self.current_position < len(self.events):
            return self.events[self.current_position]
        return None
    
    def get_state_at_position(self, position: int) -> List[Dict[str, Any]]:
        """
        Return pipeline state up to given position.
        
        Parameters
        ----------
        position : int
            The position up to which to return events
            
        Returns
        -------
        List[Dict[str, Any]]
            Events up to and including the specified position
        """
        if position < 0:
            return []
        return self.events[:min(position + 1, len(self.events))]
    
    def get_decision_context(self, position: int) -> Dict[str, Any]:
        """
        Get full context for decision at position.
        
        Includes surrounding events, alternatives considered,
        and impact of the decision.
        
        Parameters
        ----------
        position : int
            The position of the decision event
            
        Returns
        -------
        Dict[str, Any]
            Context including previous state, decision details, and outcomes
        """
        if position < 0 or position >= len(self.events):
            return {}
            
        event = self.events[position]
        
        # Get previous events for context
        previous_events = self.events[max(0, position - 5):position]
        
        # Get subsequent events to show impact
        subsequent_events = self.events[position + 1:min(position + 6, len(self.events))]
        
        # Extract decision-specific information
        context = {
            "position": position,
            "event": event,
            "event_type": event.get("event_type", ""),
            "timestamp": event.get("timestamp", ""),
            "previous_context": previous_events,
            "subsequent_impact": subsequent_events
        }
        
        # Add specific context based on event type
        if event.get("event_type") == "decision_point":
            context["decision_details"] = {
                "decision": event.get("data", {}).get("decision", ""),
                "rationale": event.get("data", {}).get("rationale", ""),
                "confidence": event.get("data", {}).get("confidence", 0),
                "alternatives": event.get("data", {}).get("alternatives_considered", [])
            }
        elif event.get("event_type") == "ai_prd_analysis":
            context["analysis_details"] = {
                "requirements_extracted": len(event.get("data", {}).get("extracted_requirements", [])),
                "confidence": event.get("data", {}).get("confidence", 0),
                "ambiguities": event.get("data", {}).get("ambiguities", [])
            }
        elif event.get("event_type") == "tasks_generated":
            context["generation_details"] = {
                "task_count": event.get("data", {}).get("task_count", 0),
                "reasoning": event.get("data", {}).get("task_breakdown_reasoning", ""),
                "complexity": event.get("data", {}).get("complexity_score", 0)
            }
            
        return context
    
    def step_forward(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Step forward one event in the replay.
        
        Returns
        -------
        Tuple[bool, Dict[str, Any]]
            Success status and the new current state
        """
        if self.current_position < self.max_position - 1:
            self.current_position += 1
            return True, self.get_current_state()
        return False, self.get_current_state()
    
    def step_back(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Step back one event in the replay.
        
        Returns
        -------
        Tuple[bool, Dict[str, Any]]
            Success status and the new current state
        """
        if self.current_position > 0:
            self.current_position -= 1
            return True, self.get_current_state()
        return False, self.get_current_state()
    
    def seek_to(self, position: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Seek to a specific position in the replay.
        
        Parameters
        ----------
        position : int
            The position to seek to
            
        Returns
        -------
        Tuple[bool, Dict[str, Any]]
            Success status and the new current state
        """
        if 0 <= position < self.max_position:
            self.current_position = position
            return True, self.get_current_state()
        return False, self.get_current_state()
    
    def find_decision_points(self) -> List[int]:
        """
        Find all decision points in the flow.
        
        Returns
        -------
        List[int]
            Positions of all decision point events
        """
        decision_positions = []
        for i, event in enumerate(self.events):
            if event.get("event_type") == "decision_point":
                decision_positions.append(i)
        return decision_positions
    
    def find_key_events(self) -> Dict[str, List[int]]:
        """
        Find positions of all key event types.
        
        Returns
        -------
        Dict[str, List[int]]
            Mapping of event types to their positions
        """
        key_event_types = [
            "decision_point",
            "ai_prd_analysis",
            "tasks_generated",
            "quality_metrics",
            "performance_metrics"
        ]
        
        key_events = {event_type: [] for event_type in key_event_types}
        
        for i, event in enumerate(self.events):
            event_type = event.get("event_type", "")
            if event_type in key_events:
                key_events[event_type].append(i)
                
        return key_events
    
    def get_timeline_data(self) -> List[Dict[str, Any]]:
        """
        Get timeline data for visualization.
        
        Returns
        -------
        List[Dict[str, Any]]
            Timeline entries with position, timestamp, and summary
        """
        timeline = []
        
        for i, event in enumerate(self.events):
            # Calculate relative time from start
            if i == 0:
                start_time = datetime.fromisoformat(event.get("timestamp", ""))
                relative_ms = 0
            else:
                event_time = datetime.fromisoformat(event.get("timestamp", ""))
                relative_ms = int((event_time - start_time).total_seconds() * 1000)
            
            timeline.append({
                "position": i,
                "timestamp": event.get("timestamp", ""),
                "relative_ms": relative_ms,
                "event_type": event.get("event_type", ""),
                "stage": event.get("stage", ""),
                "status": event.get("status", ""),
                "summary": self._get_event_summary(event)
            })
            
        return timeline
    
    def _get_event_summary(self, event: Dict[str, Any]) -> str:
        """Generate a concise summary of an event."""
        event_type = event.get("event_type", "")
        data = event.get("data", {})
        
        if event_type == "decision_point":
            return f"Decision: {data.get('decision', 'Unknown')[:50]}..."
        elif event_type == "ai_prd_analysis":
            return f"AI Analysis: {data.get('confidence', 0) * 100:.0f}% confidence"
        elif event_type == "tasks_generated":
            return f"Generated {data.get('task_count', 0)} tasks"
        elif event_type == "task_created":
            return f"Created: {data.get('task_name', 'Unknown task')}"
        elif event_type == "quality_metrics":
            return f"Quality: {data.get('overall_quality_score', 0) * 100:.0f}%"
        else:
            return event_type.replace('_', ' ').title()
    
    def export_replay_data(self) -> Dict[str, Any]:
        """
        Export replay data for external visualization tools.
        
        Returns
        -------
        Dict[str, Any]
            Complete replay data including events, timeline, and metadata
        """
        return {
            "flow_id": self.flow_id,
            "total_events": len(self.events),
            "events": self.events,
            "timeline": self.get_timeline_data(),
            "key_events": self.find_key_events(),
            "decision_points": self.find_decision_points(),
            "metadata": {
                "start_time": self.events[0].get("timestamp") if self.events else None,
                "end_time": self.events[-1].get("timestamp") if self.events else None,
                "total_duration_ms": self.events[-1].get("data", {}).get("total_duration_ms", 0) if self.events else 0
            }
        }