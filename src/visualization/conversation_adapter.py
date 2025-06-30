#!/usr/bin/env python3
"""
Conversation Adapter for Marcus Visualization

This module creates conversation-style logs from Marcus MCP events for the 
visualization system. It monitors the real-time log stream and converts 
task/kanban events into conversation format expected by the UI.

This module is designed to be completely independent of NetworkX to avoid
import-time dependencies on heavy visualization libraries.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


class ConversationAdapter:
    """Converts Marcus events to visualization-compatible conversation logs"""
    
    def __init__(self, log_dir: str = "logs/conversations"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create real-time conversation log
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.conversation_file = self.log_dir / f"realtime_{timestamp}.jsonl"
        
    def log_conversation_event(
        self, 
        source: str, 
        target: str, 
        message: str, 
        event_type: str = "message",
        metadata: Dict[str, Any] = None
    ):
        """Log a conversation event in visualization format"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "conversation_type": self._determine_conversation_type(source, target),
            "source": source,
            "target": target,
            "message": message,
            "metadata": metadata or {}
        }
        
        # Append to conversation log
        with open(self.conversation_file, 'a') as f:
            json.dump(event, f)
            f.write('\n')
            f.flush()
            
    def _determine_conversation_type(self, source: str, target: str) -> str:
        """Determine conversation type based on source and target"""
        if source.startswith("worker") and target == "marcus":
            return "worker_to_pm"
        elif source == "marcus" and target.startswith("worker"):
            return "pm_to_worker"
        elif source == "marcus" and target == "kanban_board":
            return "pm_to_kanban"
        elif source == "kanban_board" and target == "marcus":
            return "kanban_to_pm"
        else:
            return "system_event"
    
    def convert_worker_registration(self, event_data: Dict[str, Any]):
        """Convert worker registration to conversation format"""
        worker_id = event_data.get("worker_id", "unknown_worker")
        name = event_data.get("name", worker_id)
        skills = event_data.get("skills", [])
        
        self.log_conversation_event(
            source=worker_id,
            target="marcus",
            message=f"Worker {name} registering with skills: {', '.join(skills)}",
            event_type="worker_registration",
            metadata={
                "capabilities": skills,
                "role": event_data.get("role", "worker")
            }
        )
        
        # Marcus acknowledges registration
        self.log_conversation_event(
            source="marcus",
            target=worker_id,
            message=f"Registration confirmed for {name}",
            event_type="registration_ack",
            metadata={"status": "registered"}
        )
    
    def convert_task_request(self, event_data: Dict[str, Any]):
        """Convert task request to conversation format"""
        worker_id = event_data.get("worker_id", "unknown_worker")
        
        self.log_conversation_event(
            source=worker_id,
            target="marcus",
            message="Requesting next available task",
            event_type="task_request"
        )
    
    def convert_task_assignment(self, worker_id: str, task_data: Dict[str, Any]):
        """Convert task assignment to conversation format"""
        task_name = task_data.get("name", "Unknown Task")
        task_id = task_data.get("id", "unknown")
        priority = task_data.get("priority", "medium")
        
        self.log_conversation_event(
            source="marcus",
            target=worker_id,
            message=f"Assigned task: {task_name}",
            event_type="task_assignment",
            metadata={
                "task_id": task_id,
                "priority": priority,
                "estimated_hours": task_data.get("estimated_hours", 0)
            }
        )
        
        # Log kanban update
        self.log_conversation_event(
            source="marcus",
            target="kanban_board",
            message=f"Moving task {task_name} to In Progress",
            event_type="kanban_interaction",
            metadata={
                "task_id": task_id,
                "from_status": "todo",
                "to_status": "in_progress",
                "assigned_to": worker_id
            }
        )
    
    def convert_progress_update(self, event_data: Dict[str, Any]):
        """Convert progress update to conversation format"""
        worker_id = event_data.get("agent_id", "unknown_worker")
        task_id = event_data.get("task_id", "unknown")
        status = event_data.get("status", "unknown")
        progress = event_data.get("progress", 0)
        message = event_data.get("message", "Progress update")
        
        self.log_conversation_event(
            source=worker_id,
            target="marcus",
            message=f"Task progress: {progress}% - {message}",
            event_type="progress_update",
            metadata={
                "task_id": task_id,
                "status": status,
                "progress": progress
            }
        )
        
        # If completed, log kanban update
        if status == "completed":
            self.log_conversation_event(
                source="marcus",
                target="kanban_board",
                message=f"Moving task {task_id} to Done",
                event_type="kanban_interaction",
                metadata={
                    "task_id": task_id,
                    "from_status": "in_progress",
                    "to_status": "done"
                }
            )
    
    def convert_ping(self, event_data: Dict[str, Any]):
        """Convert ping to conversation format"""
        echo = event_data.get("echo", "ping")
        source = event_data.get("source", "system")
        
        self.log_conversation_event(
            source=source,
            target="marcus",
            message=f"Ping: {echo}",
            event_type="ping",
            metadata={"echo": echo}
        )
        
        # Marcus responds
        self.log_conversation_event(
            source="marcus", 
            target=source,
            message=f"Pong: {echo}",
            event_type="ping_response",
            metadata={"echo": echo, "status": "online"}
        )


# Global adapter instance
conversation_adapter = ConversationAdapter()


def log_agent_event(event_type: str, event_data: Dict[str, Any]):
    """Log an agent event in conversation format"""
    if event_type == "worker_registration":
        conversation_adapter.convert_worker_registration(event_data)
    elif event_type == "task_request":
        conversation_adapter.convert_task_request(event_data)
    elif event_type == "task_assignment":
        worker_id = event_data.get("worker_id")
        task_data = event_data.get("task", {})
        if worker_id:
            conversation_adapter.convert_task_assignment(worker_id, task_data)
    elif event_type == "progress_update":
        conversation_adapter.convert_progress_update(event_data)
    elif event_type == "ping_request":
        conversation_adapter.convert_ping(event_data)