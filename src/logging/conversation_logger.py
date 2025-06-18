"""
Structured conversation logging for PM Agent system

This module provides a structured logging system to capture all conversations
between Workers, PM Agent, and Kanban Board for later analysis and visualization.
"""

import json
import logging
import structlog
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from pathlib import Path


class ConversationType(Enum):
    """Types of conversations in the system"""
    WORKER_TO_PM = "worker_to_pm"
    PM_TO_WORKER = "pm_to_worker"
    PM_TO_KANBAN = "pm_to_kanban"
    KANBAN_TO_PM = "kanban_to_pm"
    INTERNAL_THINKING = "internal_thinking"
    DECISION = "decision"
    ERROR = "error"


class ConversationLogger:
    """
    Structured logger for capturing all system conversations
    
    Logs are structured to enable:
    - Real-time visualization of data flow
    - Decision replay and analysis
    - Performance metrics extraction
    - Debugging and optimization
    """
    
    def __init__(self, log_dir: str = "logs/conversations"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure structlog for structured JSON logging
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
        # Create separate loggers for different components
        self.pm_logger = structlog.get_logger("pm_agent")
        self.worker_logger = structlog.get_logger("worker")
        self.kanban_logger = structlog.get_logger("kanban")
        
        # Also setup file handlers
        self._setup_file_handlers()
        
    def _setup_file_handlers(self):
        """Setup file handlers for different log types"""
        # Main conversation log
        conversation_handler = logging.FileHandler(
            self.log_dir / f"conversations_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
        )
        conversation_handler.setLevel(logging.DEBUG)
        
        # Decision log for PM Agent decisions
        decision_handler = logging.FileHandler(
            self.log_dir / f"decisions_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
        )
        decision_handler.setLevel(logging.INFO)
        
        # Add handlers to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(conversation_handler)
        root_logger.addHandler(decision_handler)
        
    def log_worker_message(
        self,
        worker_id: str,
        direction: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log worker communication"""
        conversation_type = (
            ConversationType.WORKER_TO_PM if direction == "to_pm"
            else ConversationType.PM_TO_WORKER
        )
        
        self.worker_logger.info(
            "worker_communication",
            worker_id=worker_id,
            conversation_type=conversation_type.value,
            message=message,
            metadata=metadata or {},
            timestamp=datetime.now().isoformat()
        )
        
    def log_pm_thinking(
        self,
        thought: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """Log PM Agent's internal thinking process"""
        self.pm_logger.debug(
            "pm_thinking",
            conversation_type=ConversationType.INTERNAL_THINKING.value,
            thought=thought,
            context=context or {},
            timestamp=datetime.now().isoformat()
        )
        
    def log_pm_decision(
        self,
        decision: str,
        rationale: str,
        alternatives_considered: Optional[List[Dict[str, Any]]] = None,
        confidence_score: Optional[float] = None,
        decision_factors: Optional[Dict[str, Any]] = None
    ):
        """Log PM Agent's decisions with full context"""
        self.pm_logger.info(
            "pm_decision",
            conversation_type=ConversationType.DECISION.value,
            decision=decision,
            rationale=rationale,
            alternatives_considered=alternatives_considered or [],
            confidence_score=confidence_score,
            decision_factors=decision_factors or {},
            timestamp=datetime.now().isoformat()
        )
        
    def log_kanban_interaction(
        self,
        action: str,
        direction: str,
        data: Dict[str, Any],
        processing_steps: Optional[List[str]] = None
    ):
        """Log Kanban board interactions"""
        conversation_type = (
            ConversationType.PM_TO_KANBAN if direction == "to_kanban"
            else ConversationType.KANBAN_TO_PM
        )
        
        self.kanban_logger.info(
            "kanban_interaction",
            conversation_type=conversation_type.value,
            action=action,
            data=data,
            processing_steps=processing_steps or [],
            timestamp=datetime.now().isoformat()
        )
        
    def log_task_assignment(
        self,
        task_id: str,
        worker_id: str,
        task_details: Dict[str, Any],
        assignment_score: float,
        dependency_analysis: Optional[Dict[str, Any]] = None
    ):
        """Log task assignment details for later analysis"""
        self.pm_logger.info(
            "task_assignment",
            event_type="assignment",
            task_id=task_id,
            worker_id=worker_id,
            task_details=task_details,
            assignment_score=assignment_score,
            dependency_analysis=dependency_analysis or {},
            timestamp=datetime.now().isoformat()
        )
        
    def log_progress_update(
        self,
        worker_id: str,
        task_id: str,
        progress: int,
        status: str,
        message: str,
        metrics: Optional[Dict[str, Any]] = None
    ):
        """Log progress updates with metrics"""
        self.worker_logger.info(
            "progress_update",
            event_type="progress",
            worker_id=worker_id,
            task_id=task_id,
            progress=progress,
            status=status,
            message=message,
            metrics=metrics or {},
            timestamp=datetime.now().isoformat()
        )
        
    def log_blocker(
        self,
        worker_id: str,
        task_id: str,
        blocker_description: str,
        severity: str,
        suggested_solutions: Optional[List[str]] = None,
        resolution_attempts: Optional[List[Dict[str, Any]]] = None
    ):
        """Log blockers with resolution context"""
        self.worker_logger.warning(
            "blocker_reported",
            event_type="blocker",
            worker_id=worker_id,
            task_id=task_id,
            blocker_description=blocker_description,
            severity=severity,
            suggested_solutions=suggested_solutions or [],
            resolution_attempts=resolution_attempts or [],
            timestamp=datetime.now().isoformat()
        )
        
    def log_system_state(
        self,
        active_workers: int,
        tasks_in_progress: int,
        tasks_completed: int,
        tasks_blocked: int,
        system_metrics: Dict[str, Any]
    ):
        """Log overall system state for monitoring"""
        self.pm_logger.info(
            "system_state",
            event_type="state_snapshot",
            active_workers=active_workers,
            tasks_in_progress=tasks_in_progress,
            tasks_completed=tasks_completed,
            tasks_blocked=tasks_blocked,
            system_metrics=system_metrics,
            timestamp=datetime.now().isoformat()
        )
        
    def get_conversation_replay(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        filter_type: Optional[ConversationType] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve conversation logs for replay/analysis
        
        This method would be used by the visualization system
        to replay conversations and decisions
        """
        # This would read from the log files and filter based on criteria
        # For now, returning empty list as placeholder
        return []
        
    def export_decision_metrics(self) -> Dict[str, Any]:
        """
        Export decision metrics for analysis
        
        Used by the visualization system to show:
        - Decision success rates
        - Average decision time
        - Task assignment patterns
        - Bottleneck identification
        """
        # Placeholder for metrics extraction
        return {
            "total_decisions": 0,
            "successful_assignments": 0,
            "average_decision_time_ms": 0,
            "task_completion_rate": 0.0,
            "average_task_duration_hours": 0.0
        }


# Global logger instance
conversation_logger = ConversationLogger()


# Convenience functions for easy logging
def log_conversation(sender: str, receiver: str, message: str, metadata: Optional[Dict] = None):
    """Quick function to log a conversation"""
    if sender.startswith("worker"):
        conversation_logger.log_worker_message(sender, "to_pm", message, metadata)
    elif receiver.startswith("worker"):
        conversation_logger.log_worker_message(receiver, "from_pm", message, metadata)
    elif sender == "pm_agent" and receiver == "kanban":
        conversation_logger.log_kanban_interaction(
            action=metadata.get("action", "unknown"),
            direction="to_kanban",
            data={"message": message, **(metadata or {})}
        )
    elif sender == "kanban" and receiver == "pm_agent":
        conversation_logger.log_kanban_interaction(
            action=metadata.get("action", "unknown"),
            direction="from_kanban",
            data={"message": message, **(metadata or {})}
        )


def log_thinking(component: str, thought: str, context: Optional[Dict] = None):
    """Quick function to log thinking/processing"""
    if component == "pm_agent":
        conversation_logger.log_pm_thinking(thought, context)
    else:
        # Log as general debug info
        logger = structlog.get_logger(component)
        logger.debug(
            "thinking",
            thought=thought,
            context=context or {},
            timestamp=datetime.now().isoformat()
        )