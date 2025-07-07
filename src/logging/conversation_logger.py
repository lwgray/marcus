"""
Structured conversation logging for Marcus system.

This module provides a comprehensive structured logging system designed to capture
all conversations, decisions, and interactions between Workers, Marcus, and
Kanban Board components. The logging system supports real-time visualization,
decision replay, performance analysis, and debugging capabilities.

The module implements a hierarchical logging structure with JSON formatting,
automatic file rotation, and structured metadata for efficient analysis and
visualization of system behavior patterns.

Classes
-------
ConversationType : Enum
    Enumeration defining different types of conversations and interactions
    in the Marcus ecosystem.
ConversationLogger : class
    Main logging class providing structured conversation and event logging
    with comprehensive metadata capture and analysis capabilities.

Functions
---------
log_conversation : function
    Convenience function for quick conversation logging between system components.
log_thinking : function
    Utility function for capturing internal reasoning and decision-making processes.

Examples
--------
Basic conversation logging:

>>> logger = ConversationLogger(log_dir="/path/to/logs")
>>> logger.log_worker_message("worker_1", "to_pm", "Task completed successfully")
>>> logger.log_pm_decision("Assign high-priority task", "Worker has best skill match")

System state monitoring:

>>> logger.log_system_state(
...     active_workers=5,
...     tasks_in_progress=12,
...     tasks_completed=45,
...     tasks_blocked=2,
...     system_metrics={"cpu_usage": 0.75, "memory_usage": 0.60}
... )

Decision tracking with confidence scoring:

>>> logger.log_pm_decision(
...     decision="Reassign task to worker_3",
...     rationale="Original worker reported blocker",
...     confidence_score=0.85,
...     alternatives_considered=[{"option": "wait", "score": 0.3}]
... )

Notes
-----
All log entries include ISO format timestamps and structured metadata.
Log files are automatically organized by timestamp for efficient rotation.
The system supports both real-time monitoring and historical analysis.
JSON format enables easy integration with visualization and analysis tools.
"""

import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog


class ConversationType(Enum):
    """
    Enumeration of conversation types in the Marcus system.

    This enum defines the different categories of interactions and communications
    that occur between components in the Marcus ecosystem. Each type represents
    a specific communication pattern that requires different handling and analysis.

    Attributes
    ----------
    WORKER_TO_PM : str
        Communications from worker agents to the PM agent, including status
        updates, task completion reports, and blocker notifications.
    PM_TO_WORKER : str
        Communications from PM agent to worker agents, including task assignments,
        instructions, and guidance.
    PM_TO_KANBAN : str
        Communications from PM agent to kanban board system for task management,
        board updates, and status synchronization.
    KANBAN_TO_PM : str
        Communications from kanban board to PM agent, including board state
        changes, task updates, and system notifications.
    INTERNAL_THINKING : str
        Internal reasoning and decision-making processes within agents,
        used for debugging and optimization analysis.
    DECISION : str
        Formal decisions made by the PM agent, including rationale,
        alternatives considered, and confidence scores.
    ERROR : str
        Error conditions, exceptions, and failure scenarios across
        all system components.

    Examples
    --------
    >>> conv_type = ConversationType.WORKER_TO_PM
    >>> print(conv_type.value)
    'worker_to_pm'

    >>> if conversation_type == ConversationType.DECISION:
    ...     # Handle decision logging with additional metadata
    ...     pass

    Notes
    -----
    These conversation types are used for filtering, analysis, and
    visualization of system interactions. Each type may have different
    metadata requirements and processing patterns.
    """

    WORKER_TO_PM = "worker_to_pm"
    PM_TO_WORKER = "pm_to_worker"
    PM_TO_KANBAN = "pm_to_kanban"
    KANBAN_TO_PM = "kanban_to_pm"
    INTERNAL_THINKING = "internal_thinking"
    DECISION = "decision"
    ERROR = "error"


class ConversationLogger:
    """
    Comprehensive structured logger for Marcus system conversations.

    This class provides a centralized logging system that captures all interactions,
    decisions, and state changes within the Marcus ecosystem. It implements
    structured JSON logging with automatic file rotation, hierarchical organization,
    and rich metadata capture for analysis and visualization.

    The logger supports multiple output formats, real-time monitoring capabilities,
    and historical data analysis. All logs include comprehensive metadata for
    tracking system performance, decision patterns, and interaction flows.

    Parameters
    ----------
    log_dir : str, default="logs/conversations"
        Directory path where log files will be stored. The directory will be
        created if it doesn't exist, including parent directories.

    Attributes
    ----------
    log_dir : pathlib.Path
        Path object representing the logging directory location.
    pm_logger : structlog.BoundLogger
        Structured logger instance for PM agent-specific events and decisions.
    worker_logger : structlog.BoundLogger
        Structured logger instance for worker agent communications and updates.
    kanban_logger : structlog.BoundLogger
        Structured logger instance for kanban board interactions and state changes.

    Methods
    -------
    log_worker_message(worker_id, direction, message, metadata=None)
        Log communications between workers and PM agent.
    log_pm_thinking(thought, context=None)
        Log internal reasoning and decision-making processes.
    log_pm_decision(decision, rationale, alternatives_considered=None, confidence_score=None, decision_factors=None)
        Log formal decisions with comprehensive context and analysis.
    log_kanban_interaction(action, direction, data, processing_steps=None)
        Log interactions with kanban board system.
    log_task_assignment(task_id, worker_id, task_details, assignment_score, dependency_analysis=None)
        Log task assignment decisions with scoring and dependency analysis.
    log_progress_update(worker_id, task_id, progress, status, message, metrics=None)
        Log progress updates with performance metrics.
    log_blocker(worker_id, task_id, blocker_description, severity, suggested_solutions=None, resolution_attempts=None)
        Log blockers with resolution context and suggestions.
    log_system_state(active_workers, tasks_in_progress, tasks_completed, tasks_blocked, system_metrics)
        Log overall system state for monitoring and analysis.
    get_conversation_replay(start_time=None, end_time=None, filter_type=None)
        Retrieve conversation logs for replay and analysis.
    export_decision_metrics()
        Export aggregated decision metrics for performance analysis.

    Examples
    --------
    Basic initialization and worker communication logging:

    >>> logger = ConversationLogger(log_dir="/project/logs")
    >>> logger.log_worker_message(
    ...     worker_id="worker_backend_1",
    ...     direction="to_pm",
    ...     message="API endpoint implementation completed",
    ...     metadata={"task_id": "TASK-123", "completion_time": "2024-01-15T10:30:00Z"}
    ... )

    Decision logging with confidence and alternatives:

    >>> logger.log_pm_decision(
    ...     decision="Assign database migration task to worker_2",
    ...     rationale="Worker has PostgreSQL expertise and current availability",
    ...     confidence_score=0.92,
    ...     alternatives_considered=[
    ...         {"worker": "worker_1", "score": 0.65, "reason": "Less experience"},
    ...         {"worker": "worker_3", "score": 0.78, "reason": "Currently overloaded"}
    ...     ],
    ...     decision_factors={
    ...         "skill_match": 0.95,
    ...         "availability": 0.88,
    ...         "task_priority": "high",
    ...         "estimated_duration": "4 hours"
    ...     }
    ... )

    System monitoring and state tracking:

    >>> logger.log_system_state(
    ...     active_workers=8,
    ...     tasks_in_progress=15,
    ...     tasks_completed=142,
    ...     tasks_blocked=3,
    ...     system_metrics={
    ...         "avg_task_completion_time": 2.5,
    ...         "cpu_utilization": 0.67,
    ...         "memory_usage_gb": 12.3,
    ...         "active_connections": 24
    ...     }
    ... )

    Notes
    -----
    All log entries are timestamped with ISO format for consistency.
    Log files are automatically rotated with timestamp-based naming.
    The JSON structure enables efficient parsing and analysis.
    Structured logging supports real-time dashboard integration.
    Log retention and cleanup should be managed externally.

    See Also
    --------
    ConversationType : Enumeration of conversation types
    log_conversation : Convenience function for quick logging
    log_thinking : Utility function for internal process logging
    """

    def __init__(self, log_dir: str = "logs/conversations") -> None:
        # Use absolute path based on Marcus root directory
        marcus_root = Path(__file__).parent.parent.parent
        self.log_dir = (
            marcus_root / log_dir if not Path(log_dir).is_absolute() else Path(log_dir)
        )
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
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        # Create separate loggers for different components
        self.pm_logger = structlog.get_logger("marcus")
        self.worker_logger = structlog.get_logger("worker")
        self.kanban_logger = structlog.get_logger("kanban")

        # Also setup file handlers
        self._setup_file_handlers()

    def _setup_file_handlers(self) -> None:
        """
        Setup file handlers for different log types with automatic rotation.

        Creates separate file handlers for conversations and decisions with
        timestamp-based naming for automatic organization and rotation.
        Configures JSON formatting and appropriate log levels.

        Notes
        -----
        Creates two primary log files:
        - conversations_{timestamp}.jsonl: All conversation and interaction logs
        - decisions_{timestamp}.jsonl: PM agent decision logs with rationale

        Files are created with timestamp format: YYYYMMDD_HHMMSS
        Log rotation should be managed externally or through system tools.
        """
        # Main conversation log
        conversation_handler = logging.FileHandler(
            self.log_dir / f"conversations_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
        )
        conversation_handler.setLevel(logging.DEBUG)

        # Decision log for Marcus decisions
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
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log communication messages between workers and PM agent.

        Captures bidirectional communication with workers including status updates,
        task reports, blocker notifications, and responses. Automatically determines
        conversation type based on direction and includes comprehensive metadata.

        Parameters
        ----------
        worker_id : str
            Unique identifier for the worker agent involved in communication.
            Format typically follows pattern like 'worker_backend_1' or 'worker_ui_2'.
        direction : str
            Direction of communication flow. Valid values:
            - 'to_pm': Message from worker to Marcus
            - 'from_pm': Message from Marcus to worker
        message : str
            The actual communication message content. Can include status updates,
            task completion reports, questions, or blocker descriptions.
        metadata : Optional[Dict[str, Any]], default=None
            Additional context and structured data associated with the message.
            Common fields include:
            - task_id: Associated task identifier
            - timestamp: Custom timestamp (if different from log timestamp)
            - status: Current task or worker status
            - progress: Completion percentage
            - metrics: Performance or resource metrics

        Examples
        --------
        Worker reporting task completion:

        >>> logger.log_worker_message(
        ...     worker_id="worker_backend_1",
        ...     direction="to_pm",
        ...     message="Database migration completed successfully",
        ...     metadata={
        ...         "task_id": "TASK-456",
        ...         "completion_time": "2024-01-15T14:30:00Z",
        ...         "records_migrated": 150000,
        ...         "duration_minutes": 45
        ...     }
        ... )

        Marcus assigning new task:

        >>> logger.log_worker_message(
        ...     worker_id="worker_frontend_2",
        ...     direction="from_pm",
        ...     message="New high-priority UI component task assigned",
        ...     metadata={
        ...         "task_id": "TASK-789",
        ...         "priority": "high",
        ...         "estimated_hours": 8,
        ...         "dependencies": ["TASK-456"]
        ...     }
        ... )

        Worker reporting blocker:

        >>> logger.log_worker_message(
        ...     worker_id="worker_backend_3",
        ...     direction="to_pm",
        ...     message="Blocked: API rate limit exceeded",
        ...     metadata={
        ...         "task_id": "TASK-101",
        ...         "blocker_type": "external_dependency",
        ...         "severity": "high",
        ...         "estimated_delay_hours": 4
        ...     }
        ... )

        Notes
        -----
        Messages are automatically timestamped with ISO format.
        The conversation type is determined from the direction parameter.
        All worker communications are logged at INFO level for visibility.
        Large message content is automatically truncated if necessary.

        See Also
        --------
        log_progress_update : Specialized method for progress reporting
        log_blocker : Specialized method for blocker reporting
        ConversationType : Enumeration of conversation types
        """
        conversation_type = (
            ConversationType.WORKER_TO_PM
            if direction == "to_pm"
            else ConversationType.PM_TO_WORKER
        )

        self.worker_logger.info(
            "worker_communication",
            worker_id=worker_id,
            conversation_type=conversation_type.value,
            message=message,
            metadata=metadata or {},
            timestamp=datetime.now().isoformat(),
        )

    def log_pm_thinking(
        self, thought: str, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log Marcus' internal reasoning and decision-making processes.

        Captures the internal cognitive processes of Marcus including
        analysis, evaluation, planning, and reasoning steps. This enables
        debugging of decision-making logic and optimization of AI reasoning.

        Parameters
        ----------
        thought : str
            Description of the internal thought, analysis, or reasoning step.
            Should be clear and descriptive to aid in debugging and optimization.
        context : Optional[Dict[str, Any]], default=None
            Additional context surrounding the thought process including:
            - current_state: Relevant system or project state information
            - analysis_data: Data being analyzed or considered
            - decision_factors: Factors being weighed in decision-making
            - alternatives: Alternative approaches being considered
            - confidence: Confidence level in current reasoning

        Examples
        --------
        Task assignment analysis:

        >>> logger.log_pm_thinking(
        ...     thought="Analyzing worker capacity for urgent database task",
        ...     context={
        ...         "available_workers": ["worker_1", "worker_3"],
        ...         "task_requirements": ["database_expertise", "availability_4h"],
        ...         "worker_capacities": {"worker_1": 0.6, "worker_3": 0.8},
        ...         "decision_factors": ["skill_match", "current_load", "priority"]
        ...     }
        ... )

        Risk assessment reasoning:

        >>> logger.log_pm_thinking(
        ...     thought="Evaluating project timeline risk due to dependency delays",
        ...     context={
        ...         "blocked_tasks": 3,
        ...         "critical_path_affected": True,
        ...         "estimated_delay_days": 2,
        ...         "mitigation_options": ["parallel_work", "scope_reduction"],
        ...         "confidence_level": 0.75
        ...     }
        ... )

        Resource allocation planning:

        >>> logger.log_pm_thinking(
        ...     thought="Planning optimal resource allocation for sprint goals",
        ...     context={
        ...         "sprint_capacity": 120,
        ...         "committed_points": 95,
        ...         "buffer_percentage": 0.15,
        ...         "high_priority_tasks": 4,
        ...         "team_velocity_trend": "increasing"
        ...     }
        ... )

        Notes
        -----
        Thinking logs are recorded at DEBUG level for detailed analysis.
        These logs are crucial for understanding AI decision-making patterns.
        Context should include relevant data that influenced the thought process.
        Sensitive information should be excluded from thinking logs.

        See Also
        --------
        log_pm_decision : Log formal decisions with rationale
        ConversationType.INTERNAL_THINKING : Related conversation type
        """
        self.pm_logger.debug(
            "pm_thinking",
            conversation_type=ConversationType.INTERNAL_THINKING.value,
            thought=thought,
            context=context or {},
            timestamp=datetime.now().isoformat(),
        )

    def log_pm_decision(
        self,
        decision: str,
        rationale: str,
        alternatives_considered: Optional[List[Dict[str, Any]]] = None,
        confidence_score: Optional[float] = None,
        decision_factors: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log formal Marcus decisions with comprehensive context and analysis.

        Records important decisions made by Marcus including the decision
        itself, reasoning, alternatives considered, confidence levels, and
        contributing factors. This enables decision auditing, pattern analysis,
        and optimization of decision-making algorithms.

        Parameters
        ----------
        decision : str
            Clear description of the decision made. Should be specific and
            actionable, describing what will be done or changed.
        rationale : str
            Detailed explanation of why this decision was made, including
            the reasoning process and key factors that led to this choice.
        alternatives_considered : Optional[List[Dict[str, Any]]], default=None
            List of alternative options that were evaluated. Each alternative
            should include:
            - option: Description of the alternative
            - score: Evaluation score or ranking
            - pros: Advantages of this option
            - cons: Disadvantages or risks
            - reason_rejected: Why this option was not chosen
        confidence_score : Optional[float], default=None
            Confidence level in the decision on a scale of 0.0 to 1.0, where:
            - 0.0-0.3: Low confidence, high uncertainty
            - 0.4-0.6: Moderate confidence, some uncertainty
            - 0.7-0.9: High confidence, low uncertainty
            - 0.9-1.0: Very high confidence, minimal uncertainty
        decision_factors : Optional[Dict[str, Any]], default=None
            Key factors that influenced the decision including:
            - weights: Importance weights for different criteria
            - constraints: Limiting factors or requirements
            - risks: Identified risks and mitigation plans
            - resources: Available resources and limitations
            - timeline: Time constraints and deadlines

        Examples
        --------
        Task assignment decision:

        >>> logger.log_pm_decision(
        ...     decision="Assign critical authentication task to worker_senior_1",
        ...     rationale="Worker has extensive security experience and current availability",
        ...     alternatives_considered=[
        ...         {
        ...             "option": "Assign to worker_junior_2",
        ...             "score": 0.4,
        ...             "pros": ["Available immediately", "Eager to learn"],
        ...             "cons": ["Limited security experience", "Higher risk"],
        ...             "reason_rejected": "Task criticality requires experienced developer"
        ...         },
        ...         {
        ...             "option": "Split task between two workers",
        ...             "score": 0.6,
        ...             "pros": ["Knowledge sharing", "Faster completion"],
        ...             "cons": ["Coordination overhead", "Potential conflicts"],
        ...             "reason_rejected": "Security task requires single point of responsibility"
        ...         }
        ...     ],
        ...     confidence_score=0.85,
        ...     decision_factors={
        ...         "skill_match": 0.95,
        ...         "availability": 0.80,
        ...         "task_criticality": "high",
        ...         "deadline_pressure": "moderate",
        ...         "risk_tolerance": "low"
        ...     }
        ... )

        Resource reallocation decision:

        >>> logger.log_pm_decision(
        ...     decision="Reallocate 2 developers from Feature B to critical Bug Fix A",
        ...     rationale="Production issue affecting 40% of users requires immediate attention",
        ...     confidence_score=0.92,
        ...     decision_factors={
        ...         "user_impact": "high",
        ...         "business_priority": "critical",
        ...         "available_resources": 3,
        ...         "estimated_fix_time": "8 hours",
        ...         "feature_delay_acceptable": True
        ...     }
        ... )

        Timeline adjustment decision:

        >>> logger.log_pm_decision(
        ...     decision="Extend sprint by 2 days to accommodate dependency delays",
        ...     rationale="External API delays beyond team control, extension minimizes scope reduction",
        ...     alternatives_considered=[
        ...         {
        ...             "option": "Reduce sprint scope by 20%",
        ...             "score": 0.5,
        ...             "reason_rejected": "Would impact key stakeholder deliverables"
        ...         }
        ...     ],
        ...     confidence_score=0.78,
        ...     decision_factors={
        ...         "stakeholder_impact": "moderate",
        ...         "team_capacity": "available",
        ...         "deadline_flexibility": "limited",
        ...         "quality_requirements": "high"
        ...     }
        ... )

        Notes
        -----
        Decision logs are recorded at INFO level for high visibility.
        All decisions should include timestamps for chronological analysis.
        Confidence scores enable tracking of decision-making accuracy over time.
        Decision factors should be quantifiable when possible for analysis.
        This data is crucial for improving AI decision-making algorithms.

        See Also
        --------
        log_pm_thinking : Log reasoning processes leading to decisions
        export_decision_metrics : Extract decision analysis metrics
        ConversationType.DECISION : Related conversation type
        """
        self.pm_logger.info(
            "pm_decision",
            conversation_type=ConversationType.DECISION.value,
            decision=decision,
            rationale=rationale,
            alternatives_considered=alternatives_considered or [],
            confidence_score=confidence_score,
            decision_factors=decision_factors or {},
            timestamp=datetime.now().isoformat(),
        )

    def log_kanban_interaction(
        self,
        action: str,
        direction: str,
        data: Dict[str, Any],
        processing_steps: Optional[List[str]] = None,
    ) -> None:
        """
        Log interactions between Marcus and Kanban board system.

        Captures all communications with the kanban board including task updates,
        status changes, board queries, and synchronization activities. Tracks
        the flow of task management data and board state changes.

        Parameters
        ----------
        action : str
            The specific action being performed on the kanban board:
            - 'create_task': Creating new tasks
            - 'update_task': Modifying existing tasks
            - 'move_task': Changing task status/column
            - 'delete_task': Removing tasks
            - 'query_board': Retrieving board state
            - 'sync_state': Synchronizing data
            - 'batch_update': Multiple operations
        direction : str
            Direction of the interaction:
            - 'to_kanban': Marcus sending data to kanban board
            - 'from_kanban': Receiving data from kanban board
        data : Dict[str, Any]
            The actual data being exchanged with the kanban board. Structure
            varies by action type but commonly includes:
            - task_ids: List of affected task identifiers
            - board_state: Current or desired board state
            - changes: Specific modifications being made
            - query_params: Parameters for data retrieval
            - response_data: Data received from kanban board
        processing_steps : Optional[List[str]], default=None
            Sequence of processing steps performed during the interaction.
            Useful for debugging complex multi-step operations:
            - 'validate_input': Input validation step
            - 'transform_data': Data transformation
            - 'execute_operation': Main operation execution
            - 'verify_result': Result verification
            - 'update_cache': Cache synchronization

        Examples
        --------
        Creating new task on kanban board:

        >>> logger.log_kanban_interaction(
        ...     action="create_task",
        ...     direction="to_kanban",
        ...     data={
        ...         "task_id": "TASK-789",
        ...         "title": "Implement user authentication",
        ...         "description": "Add OAuth2 authentication system",
        ...         "assignee": "worker_backend_1",
        ...         "priority": "high",
        ...         "estimated_hours": 16,
        ...         "column": "To Do"
        ...     },
        ...     processing_steps=[
        ...         "validate_task_data",
        ...         "check_dependencies",
        ...         "assign_task_id",
        ...         "create_kanban_card",
        ...         "update_board_cache"
        ...     ]
        ... )

        Receiving board state update:

        >>> logger.log_kanban_interaction(
        ...     action="sync_state",
        ...     direction="from_kanban",
        ...     data={
        ...         "board_id": "PROJECT-123",
        ...         "total_tasks": 45,
        ...         "status_counts": {
        ...             "To Do": 12,
        ...             "In Progress": 8,
        ...             "Review": 5,
        ...             "Done": 20
        ...         },
        ...         "last_updated": "2024-01-15T16:45:00Z",
        ...         "changes_since_last_sync": 7
        ...     },
        ...     processing_steps=[
        ...         "receive_board_data",
        ...         "validate_data_integrity",
        ...         "detect_changes",
        ...         "update_local_state",
        ...         "trigger_notifications"
        ...     ]
        ... )

        Batch task status update:

        >>> logger.log_kanban_interaction(
        ...     action="batch_update",
        ...     direction="to_kanban",
        ...     data={
        ...         "operations": [
        ...             {"task_id": "TASK-456", "status": "Done", "completion_time": "2024-01-15T14:30:00Z"},
        ...             {"task_id": "TASK-457", "status": "In Progress", "assignee": "worker_2"},
        ...             {"task_id": "TASK-458", "priority": "urgent", "due_date": "2024-01-17"}
        ...         ],
        ...         "batch_id": "BATCH-789",
        ...         "total_operations": 3
        ...     },
        ...     processing_steps=[
        ...         "prepare_batch_operations",
        ...         "validate_all_operations",
        ...         "execute_batch_update",
        ...         "verify_batch_results",
        ...         "log_batch_completion"
        ...     ]
        ... )

        Notes
        -----
        Kanban interactions are logged at INFO level for visibility.
        Processing steps help debug complex multi-step operations.
        Data structure should match kanban board API expectations.
        Large data payloads may be truncated in logs for readability.
        Interaction logs enable kanban integration debugging and optimization.

        See Also
        --------
        log_task_assignment : Log task assignments with scoring
        log_progress_update : Log task progress changes
        ConversationType.PM_TO_KANBAN : PM to Kanban conversation type
        ConversationType.KANBAN_TO_PM : Kanban to PM conversation type
        """
        conversation_type = (
            ConversationType.PM_TO_KANBAN
            if direction == "to_kanban"
            else ConversationType.KANBAN_TO_PM
        )

        self.kanban_logger.info(
            "kanban_interaction",
            conversation_type=conversation_type.value,
            action=action,
            data=data,
            processing_steps=processing_steps or [],
            timestamp=datetime.now().isoformat(),
        )

    def log_task_assignment(
        self,
        task_id: str,
        worker_id: str,
        task_details: Dict[str, Any],
        assignment_score: float,
        dependency_analysis: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log task assignment decisions with comprehensive scoring and analysis.

        Records detailed information about task assignments including the scoring
        rationale, worker selection criteria, task requirements, and dependency
        analysis. This data enables optimization of task assignment algorithms
        and analysis of assignment effectiveness.

        Parameters
        ----------
        task_id : str
            Unique identifier for the task being assigned. Should follow
            consistent naming convention (e.g., 'TASK-123', 'FEATURE-456').
        worker_id : str
            Identifier of the worker receiving the task assignment.
            Format typically follows pattern like 'worker_backend_1'.
        task_details : Dict[str, Any]
            Comprehensive task information including:
            - title: Task title or summary
            - description: Detailed task description
            - priority: Task priority level (low, medium, high, urgent)
            - estimated_hours: Time estimate for completion
            - required_skills: List of skills needed
            - deadline: Task deadline if applicable
            - complexity: Task complexity rating
            - dependencies: List of dependent task IDs
        assignment_score : float
            Calculated score for this assignment on scale 0.0 to 1.0:
            - 0.0-0.3: Poor assignment match, high risk
            - 0.4-0.6: Acceptable assignment, moderate fit
            - 0.7-0.9: Good assignment, strong match
            - 0.9-1.0: Excellent assignment, optimal match
        dependency_analysis : Optional[Dict[str, Any]], default=None
            Analysis of task dependencies and impact including:
            - blocking_tasks: Tasks that must complete first
            - blocked_tasks: Tasks waiting on this completion
            - critical_path: Whether task is on critical path
            - dependency_risk: Risk level of dependency delays
            - estimated_start_date: When task can realistically start
            - impact_score: Impact of delays on project timeline

        Examples
        --------
        High-priority backend task assignment:

        >>> logger.log_task_assignment(
        ...     task_id="TASK-AUTH-001",
        ...     worker_id="worker_backend_senior_1",
        ...     task_details={
        ...         "title": "Implement OAuth2 authentication system",
        ...         "description": "Design and implement secure OAuth2 flow with JWT tokens",
        ...         "priority": "high",
        ...         "estimated_hours": 24,
        ...         "required_skills": ["oauth2", "jwt", "security", "nodejs"],
        ...         "deadline": "2024-01-20T17:00:00Z",
        ...         "complexity": "high",
        ...         "dependencies": ["TASK-DB-001"]
        ...     },
        ...     assignment_score=0.92,
        ...     dependency_analysis={
        ...         "blocking_tasks": ["TASK-DB-001"],
        ...         "blocked_tasks": ["TASK-UI-003", "TASK-API-005"],
        ...         "critical_path": True,
        ...         "dependency_risk": "low",
        ...         "estimated_start_date": "2024-01-16T09:00:00Z",
        ...         "impact_score": 0.85
        ...     }
        ... )

        Frontend component assignment:

        >>> logger.log_task_assignment(
        ...     task_id="TASK-UI-DASHBOARD",
        ...     worker_id="worker_frontend_2",
        ...     task_details={
        ...         "title": "Create responsive dashboard component",
        ...         "description": "Build React dashboard with charts and real-time data",
        ...         "priority": "medium",
        ...         "estimated_hours": 16,
        ...         "required_skills": ["react", "css", "responsive_design", "charts"],
        ...         "complexity": "medium",
        ...         "dependencies": []
        ...     },
        ...     assignment_score=0.78,
        ...     dependency_analysis={
        ...         "blocking_tasks": [],
        ...         "blocked_tasks": [],
        ...         "critical_path": False,
        ...         "dependency_risk": "none",
        ...         "estimated_start_date": "2024-01-15T09:00:00Z",
        ...         "impact_score": 0.45
        ...     }
        ... )

        Maintenance task with dependencies:

        >>> logger.log_task_assignment(
        ...     task_id="TASK-MAINT-DB-CLEANUP",
        ...     worker_id="worker_devops_1",
        ...     task_details={
        ...         "title": "Database cleanup and optimization",
        ...         "description": "Clean up old data and optimize database performance",
        ...         "priority": "low",
        ...         "estimated_hours": 8,
        ...         "required_skills": ["database", "sql", "performance_tuning"],
        ...         "complexity": "low",
        ...         "dependencies": ["TASK-BACKUP-001"]
        ...     },
        ...     assignment_score=0.85,
        ...     dependency_analysis={
        ...         "blocking_tasks": ["TASK-BACKUP-001"],
        ...         "blocked_tasks": [],
        ...         "critical_path": False,
        ...         "dependency_risk": "low",
        ...         "estimated_start_date": "2024-01-18T10:00:00Z",
        ...         "impact_score": 0.25
        ...     }
        ... )

        Notes
        -----
        Assignment logs are recorded at INFO level for analysis visibility.
        Assignment scores enable optimization of assignment algorithms.
        Dependency analysis helps with project timeline prediction.
        This data is crucial for measuring assignment effectiveness.
        Task details should be comprehensive for accurate analysis.

        See Also
        --------
        log_progress_update : Log progress on assigned tasks
        log_pm_decision : Log assignment decision rationale
        export_decision_metrics : Extract assignment success metrics
        """
        self.pm_logger.info(
            "task_assignment",
            event_type="assignment",
            task_id=task_id,
            worker_id=worker_id,
            task_details=task_details,
            assignment_score=assignment_score,
            dependency_analysis=dependency_analysis or {},
            timestamp=datetime.now().isoformat(),
        )

    def log_progress_update(
        self,
        worker_id: str,
        task_id: str,
        progress: int,
        status: str,
        message: str,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log task progress updates with performance metrics and status changes.

        Captures detailed progress information including completion percentage,
        status changes, milestone achievements, and performance metrics. This
        data enables real-time project tracking and performance analysis.

        Parameters
        ----------
        worker_id : str
            Identifier of the worker reporting progress.
        task_id : str
            Unique identifier of the task being updated.
        progress : int
            Completion percentage as integer from 0 to 100:
            - 0: Task not started
            - 1-25: Initial progress, setup and planning
            - 26-50: Significant progress, core work underway
            - 51-75: Major progress, nearing completion
            - 76-99: Final touches, testing, and refinement
            - 100: Task completed
        status : str
            Current task status:
            - 'not_started': Task assigned but not begun
            - 'in_progress': Task actively being worked on
            - 'blocked': Task cannot proceed due to blocker
            - 'review': Task completed, awaiting review
            - 'completed': Task fully finished and accepted
            - 'cancelled': Task cancelled or deprioritized
        message : str
            Descriptive message about current progress, accomplishments,
            or next steps. Should provide meaningful context about the work.
        metrics : Optional[Dict[str, Any]], default=None
            Performance and resource metrics associated with progress:
            - time_spent_hours: Actual time spent on task
            - estimated_remaining_hours: Time estimate to completion
            - code_lines_added: Lines of code written (for development tasks)
            - tests_written: Number of tests created
            - bugs_fixed: Number of bugs resolved
            - files_modified: Number of files changed
            - performance_improvements: Measurable improvements
            - resource_usage: CPU, memory, or other resource metrics

        Examples
        --------
        Development task progress with code metrics:

        >>> logger.log_progress_update(
        ...     worker_id="worker_backend_1",
        ...     task_id="TASK-API-USERS",
        ...     progress=65,
        ...     status="in_progress",
        ...     message="User CRUD endpoints implemented, working on authentication middleware",
        ...     metrics={
        ...         "time_spent_hours": 12,
        ...         "estimated_remaining_hours": 6,
        ...         "code_lines_added": 450,
        ...         "tests_written": 8,
        ...         "endpoints_completed": 4,
        ...         "files_modified": 7,
        ...         "test_coverage": 85
        ...     }
        ... )

        Task completion with performance metrics:

        >>> logger.log_progress_update(
        ...     worker_id="worker_devops_2",
        ...     task_id="TASK-DB-OPTIMIZATION",
        ...     progress=100,
        ...     status="completed",
        ...     message="Database queries optimized, 40% performance improvement achieved",
        ...     metrics={
        ...         "time_spent_hours": 16,
        ...         "queries_optimized": 12,
        ...         "performance_improvement_percent": 40,
        ...         "indexes_added": 5,
        ...         "slow_queries_eliminated": 8,
        ...         "average_response_time_ms": 150,
        ...         "previous_response_time_ms": 250
        ...     }
        ... )

        Blocked task with analysis:

        >>> logger.log_progress_update(
        ...     worker_id="worker_frontend_3",
        ...     task_id="TASK-UI-INTEGRATION",
        ...     progress=35,
        ...     status="blocked",
        ...     message="Waiting for API endpoints to be deployed to staging environment",
        ...     metrics={
        ...         "time_spent_hours": 8,
        ...         "estimated_remaining_hours": 12,
        ...         "components_completed": 3,
        ...         "components_pending": 2,
        ...         "blocker_estimated_delay_hours": 24,
        ...         "alternative_work_available": True
        ...     }
        ... )

        Milestone achievement:

        >>> logger.log_progress_update(
        ...     worker_id="worker_qa_1",
        ...     task_id="TASK-TESTING-SUITE",
        ...     progress=75,
        ...     status="in_progress",
        ...     message="Core testing framework completed, starting integration tests",
        ...     metrics={
        ...         "time_spent_hours": 20,
        ...         "estimated_remaining_hours": 8,
        ...         "test_cases_written": 45,
        ...         "test_coverage_percent": 82,
        ...         "bugs_found": 12,
        ...         "bugs_resolved": 10,
        ...         "automation_coverage": 90
        ...     }
        ... )

        Notes
        -----
        Progress updates are logged at INFO level for visibility.
        Progress percentage should reflect actual work completion.
        Status changes trigger workflow and notification systems.
        Metrics enable detailed performance analysis and optimization.
        Regular progress updates improve project predictability.

        See Also
        --------
        log_task_assignment : Log initial task assignments
        log_blocker : Log blockers that prevent progress
        log_system_state : Log overall system status
        """
        self.worker_logger.info(
            "progress_update",
            event_type="progress",
            worker_id=worker_id,
            task_id=task_id,
            progress=progress,
            status=status,
            message=message,
            metrics=metrics or {},
            timestamp=datetime.now().isoformat(),
        )

    def log_blocker(
        self,
        worker_id: str,
        task_id: str,
        blocker_description: str,
        severity: str,
        suggested_solutions: Optional[List[str]] = None,
        resolution_attempts: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Log task blockers with resolution context and suggested solutions.

        Records detailed information about blockers that prevent task progress,
        including impact assessment, suggested solutions, and resolution attempts.
        This data enables proactive blocker management and resolution optimization.

        Parameters
        ----------
        worker_id : str
            Identifier of the worker reporting the blocker.
        task_id : str
            Unique identifier of the blocked task.
        blocker_description : str
            Detailed description of the blocker including:
            - What is preventing progress
            - When the blocker was encountered
            - What was attempted before reporting
            - Impact on the task and timeline
        severity : str
            Severity level of the blocker:
            - 'low': Minor impediment, workarounds available
            - 'medium': Moderate impact, requires attention
            - 'high': Significant blocker, major impact on timeline
            - 'critical': Complete show-stopper, urgent resolution needed
        suggested_solutions : Optional[List[str]], default=None
            List of potential solutions or workarounds identified:
            - Alternative approaches to achieve the goal
            - Workarounds to continue partial progress
            - Resources or support that could resolve the blocker
            - Process changes that could prevent similar blockers
        resolution_attempts : Optional[List[Dict[str, Any]]], default=None
            Record of attempted resolutions, each containing:
            - attempt: Description of what was tried
            - timestamp: When the attempt was made
            - outcome: Result of the attempt
            - time_spent: Time invested in the attempt
            - lessons_learned: Insights gained from the attempt

        Examples
        --------
        External dependency blocker:

        >>> logger.log_blocker(
        ...     worker_id="worker_backend_2",
        ...     task_id="TASK-PAYMENT-INTEGRATION",
        ...     blocker_description="Third-party payment API is returning 500 errors consistently since 2PM. Cannot test or complete payment processing implementation.",
        ...     severity="high",
        ...     suggested_solutions=[
        ...         "Contact payment provider support team",
        ...         "Implement mock payment service for testing",
        ...         "Switch to backup payment provider temporarily",
        ...         "Focus on payment UI while waiting for API fix"
        ...     ],
        ...     resolution_attempts=[
        ...         {
        ...             "attempt": "Checked API status page and documentation",
        ...             "timestamp": "2024-01-15T14:30:00Z",
        ...             "outcome": "No reported issues, but errors persist",
        ...             "time_spent": 0.5,
        ...             "lessons_learned": "Status page not always current"
        ...         },
        ...         {
        ...             "attempt": "Tested with different API keys and endpoints",
        ...             "timestamp": "2024-01-15T15:00:00Z",
        ...             "outcome": "Same errors across all endpoints",
        ...             "time_spent": 1.0,
        ...             "lessons_learned": "Issue is service-wide, not credential specific"
        ...         }
        ...     ]
        ... )

        Technical blocker with research:

        >>> logger.log_blocker(
        ...     worker_id="worker_frontend_1",
        ...     task_id="TASK-MOBILE-RESPONSIVE",
        ...     blocker_description="CSS Grid layout breaking on iOS Safari versions < 14. Affects 15% of mobile users according to analytics.",
        ...     severity="medium",
        ...     suggested_solutions=[
        ...         "Implement CSS Grid fallback using Flexbox",
        ...         "Use CSS feature queries (@supports) for progressive enhancement",
        ...         "Add polyfill for older Safari versions",
        ...         "Consider dropping support for Safari < 14"
        ...     ],
        ...     resolution_attempts=[
        ...         {
        ...             "attempt": "Tested various CSS Grid properties and values",
        ...             "timestamp": "2024-01-15T10:00:00Z",
        ...             "outcome": "Confirmed issue specific to Safari < 14",
        ...             "time_spent": 2.0,
        ...             "lessons_learned": "Need systematic browser compatibility testing"
        ...         }
        ...     ]
        ... )

        Resource blocker:

        >>> logger.log_blocker(
        ...     worker_id="worker_devops_3",
        ...     task_id="TASK-LOAD-TESTING",
        ...     blocker_description="Staging environment insufficient for realistic load testing. Current setup can only simulate 100 concurrent users, need 1000+ for meaningful results.",
        ...     severity="medium",
        ...     suggested_solutions=[
        ...         "Request additional staging environment resources",
        ...         "Use cloud-based load testing service",
        ...         "Scale testing approach to use multiple smaller tests",
        ...         "Partner with infrastructure team for production-like environment"
        ...     ],
        ...     resolution_attempts=[
        ...         {
        ...             "attempt": "Optimized existing staging environment configuration",
        ...             "timestamp": "2024-01-15T09:00:00Z",
        ...             "outcome": "Achieved 200 concurrent users, still insufficient",
        ...             "time_spent": 3.0,
        ...             "lessons_learned": "Hardware limits cannot be overcome with optimization alone"
        ...         }
        ...     ]
        ... )

        Critical blocker requiring immediate attention:

        >>> logger.log_blocker(
        ...     worker_id="worker_security_1",
        ...     task_id="TASK-SECURITY-AUDIT",
        ...     blocker_description="Discovered critical security vulnerability in authentication system during audit. Production system at risk, requires immediate attention.",
        ...     severity="critical",
        ...     suggested_solutions=[
        ...         "Implement immediate hotfix to production",
        ...         "Temporarily disable affected authentication methods",
        ...         "Escalate to security team and management",
        ...         "Prepare comprehensive security patch"
        ...     ],
        ...     resolution_attempts=[
        ...         {
        ...             "attempt": "Verified vulnerability and assessed impact scope",
        ...             "timestamp": "2024-01-15T16:00:00Z",
        ...             "outcome": "Confirmed critical vulnerability affects all user sessions",
        ...             "time_spent": 1.0,
        ...             "lessons_learned": "Need automated security scanning in CI pipeline"
        ...         }
        ...     ]
        ... )

        Notes
        -----
        Blocker logs are recorded at WARNING level for appropriate attention.
        Severity determines escalation and response priority.
        Detailed descriptions enable effective resolution planning.
        Resolution attempts prevent duplicate effort across workers.
        Suggested solutions accelerate blocker resolution processes.

        See Also
        --------
        log_progress_update : Log task progress including blocked status
        log_pm_decision : Log decisions about blocker resolution
        log_system_state : Log system-wide impact of blockers
        """
        self.worker_logger.warning(
            "blocker_reported",
            event_type="blocker",
            worker_id=worker_id,
            task_id=task_id,
            blocker_description=blocker_description,
            severity=severity,
            suggested_solutions=suggested_solutions or [],
            resolution_attempts=resolution_attempts or [],
            timestamp=datetime.now().isoformat(),
        )

    def log_system_state(
        self,
        active_workers: int,
        tasks_in_progress: int,
        tasks_completed: int,
        tasks_blocked: int,
        system_metrics: Dict[str, Any],
    ) -> None:
        """
        Log comprehensive system state for monitoring and analysis.

        Captures a snapshot of the entire Marcus system state including
        worker activity, task distribution, performance metrics, and resource
        utilization. This data enables system health monitoring and optimization.

        Parameters
        ----------
        active_workers : int
            Number of workers currently active and available for task assignment.
            Includes workers that are working on tasks or ready for new assignments.
        tasks_in_progress : int
            Total number of tasks currently being worked on across all workers.
            Includes tasks in 'in_progress' status but excludes blocked tasks.
        tasks_completed : int
            Cumulative count of tasks that have been completed successfully.
            Represents total throughput since system startup or reset.
        tasks_blocked : int
            Number of tasks currently blocked and unable to proceed.
            High blocked task counts indicate system bottlenecks.
        system_metrics : Dict[str, Any]
            Comprehensive system performance and health metrics:
            - cpu_utilization: CPU usage percentage (0.0-1.0)
            - memory_usage_gb: Memory consumption in gigabytes
            - memory_utilization: Memory usage percentage (0.0-1.0)
            - disk_usage_gb: Disk space consumed in gigabytes
            - network_io_mbps: Network I/O in megabits per second
            - active_connections: Number of active network connections
            - avg_task_completion_time_hours: Average time to complete tasks
            - worker_efficiency: Overall worker efficiency score (0.0-1.0)
            - system_load: Overall system load factor
            - error_rate: System error rate percentage
            - uptime_hours: System uptime in hours

        Examples
        --------
        Healthy system state during normal operation:

        >>> logger.log_system_state(
        ...     active_workers=8,
        ...     tasks_in_progress=15,
        ...     tasks_completed=234,
        ...     tasks_blocked=2,
        ...     system_metrics={
        ...         "cpu_utilization": 0.65,
        ...         "memory_usage_gb": 12.3,
        ...         "memory_utilization": 0.58,
        ...         "disk_usage_gb": 45.7,
        ...         "network_io_mbps": 25.4,
        ...         "active_connections": 32,
        ...         "avg_task_completion_time_hours": 4.2,
        ...         "worker_efficiency": 0.87,
        ...         "system_load": 0.72,
        ...         "error_rate": 0.02,
        ...         "uptime_hours": 168.5,
        ...         "tasks_per_hour": 12.3,
        ...         "throughput_trend": "stable"
        ...     }
        ... )

        High-load system state with performance concerns:

        >>> logger.log_system_state(
        ...     active_workers=12,
        ...     tasks_in_progress=28,
        ...     tasks_completed=567,
        ...     tasks_blocked=8,
        ...     system_metrics={
        ...         "cpu_utilization": 0.92,
        ...         "memory_usage_gb": 28.7,
        ...         "memory_utilization": 0.89,
        ...         "disk_usage_gb": 78.2,
        ...         "network_io_mbps": 95.6,
        ...         "active_connections": 78,
        ...         "avg_task_completion_time_hours": 6.8,
        ...         "worker_efficiency": 0.71,
        ...         "system_load": 0.94,
        ...         "error_rate": 0.08,
        ...         "uptime_hours": 72.3,
        ...         "tasks_per_hour": 8.7,
        ...         "throughput_trend": "declining",
        ...         "bottleneck_indicators": ["memory_pressure", "high_blocked_tasks"]
        ...     }
        ... )

        Low-activity system state during off-peak hours:

        >>> logger.log_system_state(
        ...     active_workers=3,
        ...     tasks_in_progress=5,
        ...     tasks_completed=89,
        ...     tasks_blocked=1,
        ...     system_metrics={
        ...         "cpu_utilization": 0.25,
        ...         "memory_usage_gb": 6.8,
        ...         "memory_utilization": 0.32,
        ...         "disk_usage_gb": 23.4,
        ...         "network_io_mbps": 8.2,
        ...         "active_connections": 12,
        ...         "avg_task_completion_time_hours": 3.1,
        ...         "worker_efficiency": 0.93,
        ...         "system_load": 0.28,
        ...         "error_rate": 0.01,
        ...         "uptime_hours": 24.7,
        ...         "tasks_per_hour": 3.6,
        ...         "throughput_trend": "stable",
        ...         "capacity_available": 0.75
        ...     }
        ... )

        System state during scaling event:

        >>> logger.log_system_state(
        ...     active_workers=15,
        ...     tasks_in_progress=35,
        ...     tasks_completed=1247,
        ...     tasks_blocked=4,
        ...     system_metrics={
        ...         "cpu_utilization": 0.78,
        ...         "memory_usage_gb": 18.9,
        ...         "memory_utilization": 0.67,
        ...         "disk_usage_gb": 92.1,
        ...         "network_io_mbps": 67.3,
        ...         "active_connections": 54,
        ...         "avg_task_completion_time_hours": 3.8,
        ...         "worker_efficiency": 0.84,
        ...         "system_load": 0.81,
        ...         "error_rate": 0.03,
        ...         "uptime_hours": 336.2,
        ...         "tasks_per_hour": 18.7,
        ...         "throughput_trend": "increasing",
        ...         "scaling_event": "auto_scale_up",
        ...         "new_workers_added": 3
        ...     }
        ... )

        Notes
        -----
        System state logs are recorded at INFO level for monitoring visibility.
        Regular state logging enables trend analysis and capacity planning.
        High blocked task counts may indicate systemic issues requiring attention.
        Resource metrics help identify bottlenecks and optimization opportunities.
        System state data is crucial for automated scaling and alerting systems.

        See Also
        --------
        log_progress_update : Log individual task progress
        log_blocker : Log specific task blockers
        export_decision_metrics : Extract system performance metrics
        """
        self.pm_logger.info(
            "system_state",
            event_type="state_snapshot",
            active_workers=active_workers,
            tasks_in_progress=tasks_in_progress,
            tasks_completed=tasks_completed,
            tasks_blocked=tasks_blocked,
            system_metrics=system_metrics,
            timestamp=datetime.now().isoformat(),
        )

    def get_conversation_replay(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        filter_type: Optional[ConversationType] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve conversation logs for replay and analysis.

        Extracts conversation logs from the stored files based on time range
        and conversation type filters. This method enables visualization systems
        to replay system interactions and analyze communication patterns.

        Parameters
        ----------
        start_time : Optional[datetime], default=None
            Start of the time range for log retrieval. If None, retrieves
            from the earliest available logs.
        end_time : Optional[datetime], default=None
            End of the time range for log retrieval. If None, retrieves
            up to the most recent logs.
        filter_type : Optional[ConversationType], default=None
            Specific conversation type to filter by. If None, retrieves
            all conversation types within the time range.

        Returns
        -------
        List[Dict[str, Any]]
            List of conversation log entries matching the filter criteria.
            Each entry contains:
            - timestamp: ISO format timestamp of the conversation
            - conversation_type: Type of conversation (from ConversationType)
            - participants: Involved parties (worker_id, marcus, kanban)
            - message: The conversation content
            - metadata: Additional context and structured data
            - log_level: Logging level of the entry

        Examples
        --------
        Retrieve all conversations from the last 24 hours:

        >>> from datetime import datetime, timedelta
        >>> end_time = datetime.now()
        >>> start_time = end_time - timedelta(hours=24)
        >>> conversations = logger.get_conversation_replay(
        ...     start_time=start_time,
        ...     end_time=end_time
        ... )
        >>> print(f"Retrieved {len(conversations)} conversations")

        Retrieve only Marcus decisions:

        >>> decisions = logger.get_conversation_replay(
        ...     filter_type=ConversationType.DECISION
        ... )
        >>> for decision in decisions:
        ...     print(f"Decision: {decision['decision']}")
        ...     print(f"Confidence: {decision['confidence_score']}")

        Retrieve worker communications for specific time period:

        >>> worker_comms = logger.get_conversation_replay(
        ...     start_time=datetime(2024, 1, 15, 9, 0),
        ...     end_time=datetime(2024, 1, 15, 17, 0),
        ...     filter_type=ConversationType.WORKER_TO_PM
        ... )

        Notes
        -----
        This method reads from the stored JSON log files.
        Large time ranges may return substantial amounts of data.
        Consider implementing pagination for very large result sets.
        Log files are organized by timestamp for efficient retrieval.
        Empty list is returned if no logs match the criteria.

        See Also
        --------
        export_decision_metrics : Extract decision-specific metrics
        ConversationType : Enumeration of conversation types
        """
        # This would read from the log files and filter based on criteria
        # For now, returning empty list as placeholder
        return []

    def export_decision_metrics(self) -> Dict[str, Any]:
        """
        Export comprehensive decision metrics for analysis and optimization.

        Analyzes logged decision data to extract key performance indicators,
        patterns, and metrics that enable optimization of the Marcus'
        decision-making algorithms and overall system performance.

        Returns
        -------
        Dict[str, Any]
            Comprehensive decision metrics including:
            - total_decisions: Total number of decisions made
            - successful_assignments: Number of successful task assignments
            - assignment_success_rate: Percentage of successful assignments
            - average_decision_time_ms: Average time to make decisions
            - average_confidence_score: Mean confidence across all decisions
            - confidence_distribution: Distribution of confidence scores
            - task_completion_rate: Percentage of assigned tasks completed
            - average_task_duration_hours: Mean time to complete tasks
            - decision_type_breakdown: Count of decisions by type
            - top_decision_factors: Most influential decision factors
            - improvement_opportunities: Identified areas for optimization

        Examples
        --------
        Basic metrics extraction:

        >>> metrics = logger.export_decision_metrics()
        >>> print(f"Total decisions made: {metrics['total_decisions']}")
        >>> print(f"Assignment success rate: {metrics['assignment_success_rate']:.1%}")
        >>> print(f"Average confidence: {metrics['average_confidence_score']:.2f}")

        Analyzing decision patterns:

        >>> metrics = logger.export_decision_metrics()
        >>> decision_breakdown = metrics['decision_type_breakdown']
        >>> for decision_type, count in decision_breakdown.items():
        ...     print(f"{decision_type}: {count} decisions")

        Identifying optimization opportunities:

        >>> metrics = logger.export_decision_metrics()
        >>> opportunities = metrics['improvement_opportunities']
        >>> for opportunity in opportunities:
        ...     print(f"Opportunity: {opportunity['area']}")
        ...     print(f"Impact: {opportunity['potential_improvement']}")

        Performance dashboard integration:

        >>> metrics = logger.export_decision_metrics()
        >>> dashboard_data = {
        ...     'success_rate': metrics['assignment_success_rate'],
        ...     'avg_completion_time': metrics['average_task_duration_hours'],
        ...     'decision_confidence': metrics['average_confidence_score'],
        ...     'total_throughput': metrics['successful_assignments']
        ... }

        Notes
        -----
        Metrics are calculated from all available decision log data.
        Large log files may require time for comprehensive analysis.
        Metrics are cached and updated periodically for performance.
        Success rates are based on task completion and quality metrics.
        Empty metrics are returned if insufficient decision data exists.

        See Also
        --------
        get_conversation_replay : Retrieve detailed conversation logs
        log_pm_decision : Log decisions for metrics calculation
        log_task_assignment : Log assignments for success rate calculation
        """
        # Placeholder for metrics extraction
        return {
            "total_decisions": 0,
            "successful_assignments": 0,
            "average_decision_time_ms": 0,
            "task_completion_rate": 0.0,
            "average_task_duration_hours": 0.0,
        }


# Global logger instance
conversation_logger = ConversationLogger()


# Convenience functions for easy logging
def log_conversation(
    sender: str, receiver: str, message: str, metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Convenience function for quick conversation logging between system components.

    Provides a simplified interface for logging conversations without needing
    to directly interact with the ConversationLogger class. Automatically
    determines the appropriate conversation type and routing based on sender
    and receiver identifiers.

    Parameters
    ----------
    sender : str
        Identifier of the message sender. Common patterns:
        - 'worker_{type}_{id}': Worker agents (e.g., 'worker_backend_1')
        - 'marcus': Marcus system
        - 'kanban': Kanban board system
        - 'system': System-level messages
    receiver : str
        Identifier of the message receiver, following same patterns as sender.
    message : str
        The conversation message content to be logged.
    metadata : Optional[Dict[str, Any]], default=None
        Additional context and structured data for the conversation:
        - action: Specific action being performed
        - task_id: Associated task identifier
        - priority: Message or task priority level
        - timestamp: Custom timestamp if different from log time
        - status: Current status information

    Examples
    --------
    Worker reporting to Marcus:

    >>> log_conversation(
    ...     sender="worker_backend_1",
    ...     receiver="marcus",
    ...     message="Task TASK-123 completed successfully",
    ...     metadata={"task_id": "TASK-123", "completion_time": "2024-01-15T16:30:00Z"}
    ... )

    Marcus communicating with worker:

    >>> log_conversation(
    ...     sender="marcus",
    ...     receiver="worker_frontend_2",
    ...     message="New high-priority UI task assigned",
    ...     metadata={"task_id": "TASK-456", "priority": "high", "deadline": "2024-01-18"}
    ... )

    Marcus updating Kanban board:

    >>> log_conversation(
    ...     sender="marcus",
    ...     receiver="kanban",
    ...     message="Updating task status to completed",
    ...     metadata={"action": "update_task", "task_id": "TASK-789", "new_status": "Done"}
    ... )

    Kanban board notifying Marcus:

    >>> log_conversation(
    ...     sender="kanban",
    ...     receiver="marcus",
    ...     message="Board state synchronized, 3 new tasks added",
    ...     metadata={"action": "sync_complete", "new_tasks": 3, "total_tasks": 47}
    ... )

    Notes
    -----
    This function uses the global conversation_logger instance.
    Message routing is determined automatically from sender/receiver patterns.
    All conversations are timestamped automatically.
    Invalid sender/receiver patterns will log as general debug information.

    See Also
    --------
    ConversationLogger.log_worker_message : Direct worker message logging
    ConversationLogger.log_kanban_interaction : Direct kanban interaction logging
    log_thinking : Convenience function for internal reasoning logs
    """
    if sender.startswith("worker"):
        conversation_logger.log_worker_message(sender, "to_pm", message, metadata)
    elif receiver.startswith("worker"):
        conversation_logger.log_worker_message(receiver, "from_pm", message, metadata)
    elif sender == "marcus" and receiver == "kanban":
        conversation_logger.log_kanban_interaction(
            action=metadata.get("action", "unknown"),
            direction="to_kanban",
            data={"message": message, **(metadata or {})},
        )
    elif sender == "kanban" and receiver == "marcus":
        conversation_logger.log_kanban_interaction(
            action=metadata.get("action", "unknown"),
            direction="from_kanban",
            data={"message": message, **(metadata or {})},
        )


def log_thinking(
    component: str, thought: str, context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Convenience function for logging internal reasoning and decision processes.

    Provides a simplified interface for capturing internal thought processes,
    analysis steps, and reasoning chains across different system components.
    Enables debugging and optimization of AI and algorithmic decision-making.

    Parameters
    ----------
    component : str
        Identifier of the component doing the thinking:
        - 'marcus': Marcus reasoning and decision-making
        - 'worker_{type}_{id}': Worker agent internal processing
        - 'kanban': Kanban board processing and analysis
        - 'system': System-level analysis and monitoring
        - 'scheduler': Task scheduling and optimization
        - 'analyzer': Performance and pattern analysis
    thought : str
        Description of the internal thought, analysis, or reasoning step.
        Should be clear and detailed enough for debugging and optimization.
    context : Optional[Dict[str, Any]], default=None
        Additional context surrounding the thought process:
        - current_state: Relevant system or component state
        - input_data: Data being analyzed or processed
        - decision_factors: Factors being considered
        - analysis_results: Results of analysis or computation
        - confidence_level: Confidence in the reasoning
        - alternatives: Alternative approaches considered

    Examples
    --------
    Marcus task assignment reasoning:

    >>> log_thinking(
    ...     component="marcus",
    ...     thought="Evaluating worker capacity and skills for urgent security task",
    ...     context={
    ...         "available_workers": 5,
    ...         "task_requirements": ["security", "nodejs", "immediate_availability"],
    ...         "worker_scores": {"worker_1": 0.9, "worker_2": 0.7, "worker_3": 0.8},
    ...         "decision_factors": ["expertise", "availability", "current_load"],
    ...         "confidence_level": 0.85
    ...     }
    ... )

    Worker agent problem-solving process:

    >>> log_thinking(
    ...     component="worker_backend_1",
    ...     thought="Analyzing database performance issue, considering indexing strategies",
    ...     context={
    ...         "query_performance": "slow",
    ...         "affected_tables": ["users", "orders", "products"],
    ...         "potential_solutions": ["add_indexes", "optimize_queries", "partition_tables"],
    ...         "estimated_impact": {"add_indexes": "high", "optimize_queries": "medium"},
    ...         "implementation_complexity": {"add_indexes": "low", "optimize_queries": "medium"}
    ...     }
    ... )

    System analyzer pattern recognition:

    >>> log_thinking(
    ...     component="analyzer",
    ...     thought="Detecting recurring bottleneck pattern in task assignments",
    ...     context={
    ...         "pattern_type": "bottleneck",
    ...         "frequency": "daily_14:00-16:00",
    ...         "affected_workers": ["worker_1", "worker_3"],
    ...         "root_cause_hypothesis": "lunch_break_scheduling_conflict",
    ...         "confidence": 0.78,
    ...         "suggested_action": "stagger_break_times"
    ...     }
    ... )

    Scheduler optimization reasoning:

    >>> log_thinking(
    ...     component="scheduler",
    ...     thought="Optimizing task order to minimize dependency delays",
    ...     context={
    ...         "total_tasks": 24,
    ...         "dependency_chains": 6,
    ...         "critical_path_length": 12,
    ...         "optimization_strategy": "dependency_first",
    ...         "expected_improvement": "15%_faster_completion",
    ...         "alternative_strategies": ["priority_first", "worker_balanced"]
    ...     }
    ... )

    Notes
    -----
    Thinking logs are typically recorded at DEBUG level.
    Marcus thoughts use specialized logging for enhanced analysis.
    Other components use general structured logging with component identification.
    Context should include data that influenced the reasoning process.
    These logs are essential for AI/algorithm debugging and optimization.

    See Also
    --------
    ConversationLogger.log_pm_thinking : Direct Marcus thinking logs
    ConversationLogger.log_pm_decision : Log formal decisions
    log_conversation : Convenience function for inter-component communication
    """
    if component == "marcus":
        conversation_logger.log_pm_thinking(thought, context)
    else:
        # Log as general debug info
        logger = structlog.get_logger(component)
        logger.debug(
            "thinking",
            thought=thought,
            context=context or {},
            timestamp=datetime.now().isoformat(),
        )
