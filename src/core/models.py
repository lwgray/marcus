"""
Core data models for PM Agent.

This module defines the fundamental data structures used throughout the PM Agent system,
including tasks, workers, assignments, and project state tracking.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class TaskStatus(Enum):
    """
    Enumeration of possible task states.
    
    Attributes
    ----------
    TODO : str
        Task is created but not started
    IN_PROGRESS : str
        Task is actively being worked on
    DONE : str
        Task is completed
    BLOCKED : str
        Task cannot proceed due to dependencies or issues
    """
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class RiskLevel(Enum):
    """
    Enumeration of risk severity levels.
    
    Attributes
    ----------
    LOW : str
        Minimal impact on project timeline or quality
    MEDIUM : str
        Moderate impact requiring attention
    HIGH : str
        Significant impact requiring immediate action
    CRITICAL : str
        Severe impact threatening project success
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Priority(Enum):
    """
    Enumeration of task priority levels.
    
    Attributes
    ----------
    LOW : str
        Can be deferred without impact
    MEDIUM : str
        Should be completed in normal course
    HIGH : str
        Should be prioritized over medium/low tasks
    URGENT : str
        Requires immediate attention
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Task:
    """
    Represents a work item in the project management system.
    
    Parameters
    ----------
    id : str
        Unique identifier for the task
    name : str
        Short descriptive name of the task
    description : str
        Detailed description of what needs to be done
    status : TaskStatus
        Current state of the task
    priority : Priority
        Urgency level of the task
    assigned_to : Optional[str]
        ID of the worker assigned to this task
    created_at : datetime
        Timestamp when task was created
    updated_at : datetime
        Timestamp of last modification
    due_date : Optional[datetime]
        Target completion date
    estimated_hours : float
        Estimated time to complete in hours
    actual_hours : float, default=0.0
        Actual time spent on task
    dependencies : List[str], optional
        List of task IDs that must be completed first
    labels : List[str], optional
        Tags for categorizing the task
    
    Notes
    -----
    Dependencies and labels are initialized as empty lists if not provided.
    """
    id: str
    name: str
    description: str
    status: TaskStatus
    priority: Priority
    assigned_to: Optional[str]
    created_at: datetime
    updated_at: datetime
    due_date: Optional[datetime]
    estimated_hours: float
    actual_hours: float = 0.0
    dependencies: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)


@dataclass
class ProjectState:
    """
    Represents the current state of the entire project.
    
    Parameters
    ----------
    board_id : str
        Unique identifier of the project board
    project_name : str
        Name of the project
    total_tasks : int
        Total number of tasks in the project
    completed_tasks : int
        Number of tasks marked as done
    in_progress_tasks : int
        Number of tasks currently being worked on
    blocked_tasks : int
        Number of tasks that are blocked
    progress_percent : float
        Overall project completion percentage (0-100)
    overdue_tasks : List[Task]
        Tasks that have passed their due date
    team_velocity : float
        Average tasks completed per time period
    risk_level : RiskLevel
        Overall project risk assessment
    last_updated : datetime
        Timestamp of last state update
    """
    board_id: str
    project_name: str
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    blocked_tasks: int
    progress_percent: float
    overdue_tasks: List[Task]
    team_velocity: float
    risk_level: RiskLevel
    last_updated: datetime


@dataclass
class WorkerStatus:
    """
    Represents the current state and capabilities of a worker agent.
    
    Parameters
    ----------
    worker_id : str
        Unique identifier for the worker
    name : str
        Display name of the worker
    role : str
        Job role or specialization (e.g., "Frontend Developer")
    email : Optional[str]
        Contact email for the worker
    current_tasks : List[Task]
        Tasks currently assigned to this worker
    completed_tasks_count : int
        Total number of tasks completed by this worker
    capacity : int
        Maximum hours per week the worker can work
    skills : List[str]
        Technical skills and competencies
    availability : Dict[str, bool]
        Days of week when worker is available
    performance_score : float, default=1.0
        Performance rating (0.0-2.0, where 1.0 is baseline)
    
    Examples
    --------
    >>> worker = WorkerStatus(
    ...     worker_id="dev-001",
    ...     name="Alice Smith",
    ...     role="Backend Developer",
    ...     email="alice@example.com",
    ...     current_tasks=[],
    ...     completed_tasks_count=15,
    ...     capacity=40,
    ...     skills=["Python", "Django", "PostgreSQL"],
    ...     availability={"monday": True, "tuesday": True, ...}
    ... )
    """
    worker_id: str
    name: str
    role: str
    email: Optional[str]
    current_tasks: List[Task]
    completed_tasks_count: int
    capacity: int
    skills: List[str]
    availability: Dict[str, bool]
    performance_score: float = 1.0


@dataclass
class TaskAssignment:
    """
    Represents a task assignment to a specific worker.
    
    Parameters
    ----------
    task_id : str
        Unique identifier of the task
    task_name : str
        Name of the task being assigned
    description : str
        What needs to be done
    instructions : str
        Detailed instructions for completing the task
    estimated_hours : float
        Expected time to complete
    priority : Priority
        Task urgency level
    dependencies : List[str]
        Other tasks that must be completed first
    assigned_to : str
        Worker ID receiving the assignment
    assigned_at : datetime
        Timestamp of assignment
    due_date : Optional[datetime]
        Target completion date
    workspace_path : Optional[str], default=None
        Path to the workspace directory for this task
    forbidden_paths : List[str], optional
        Paths the worker should not access
    
    Notes
    -----
    The workspace_path and forbidden_paths are used for security isolation
    to prevent workers from accessing unauthorized directories.
    """
    task_id: str
    task_name: str
    description: str
    instructions: str
    estimated_hours: float
    priority: Priority
    dependencies: List[str]
    assigned_to: str
    assigned_at: datetime
    due_date: Optional[datetime]
    workspace_path: Optional[str] = None
    forbidden_paths: List[str] = field(default_factory=list)


@dataclass
class BlockerReport:
    """
    Represents a blocker or impediment reported by a worker.
    
    Parameters
    ----------
    task_id : str
        ID of the blocked task
    reporter_id : str
        ID of the worker reporting the blocker
    description : str
        Detailed description of the blocker
    severity : RiskLevel
        How severely this impacts the task
    reported_at : datetime
        When the blocker was reported
    resolved : bool, default=False
        Whether the blocker has been resolved
    resolution : Optional[str], default=None
        Description of how the blocker was resolved
    resolved_at : Optional[datetime], default=None
        When the blocker was resolved
    
    Examples
    --------
    >>> blocker = BlockerReport(
    ...     task_id="TASK-123",
    ...     reporter_id="dev-001",
    ...     description="Cannot access production database",
    ...     severity=RiskLevel.HIGH,
    ...     reported_at=datetime.now()
    ... )
    """
    task_id: str
    reporter_id: str
    description: str
    severity: RiskLevel
    reported_at: datetime
    resolved: bool = False
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None


@dataclass
class ProjectRisk:
    """
    Represents an identified risk to the project.
    
    Parameters
    ----------
    risk_type : str
        Category of risk (e.g., "technical", "resource", "timeline")
    description : str
        Detailed description of the risk
    severity : RiskLevel
        Potential impact severity
    probability : float
        Likelihood of occurrence (0.0-1.0)
    impact : str
        Description of potential impact if risk materializes
    mitigation_strategy : str
        Plan to reduce or eliminate the risk
    identified_at : datetime
        When the risk was identified
    
    Examples
    --------
    >>> risk = ProjectRisk(
    ...     risk_type="technical",
    ...     description="Legacy API may be deprecated",
    ...     severity=RiskLevel.MEDIUM,
    ...     probability=0.3,
    ...     impact="Would require rewriting integration layer",
    ...     mitigation_strategy="Begin migration to new API",
    ...     identified_at=datetime.now()
    ... )
    """
    risk_type: str
    description: str
    severity: RiskLevel
    probability: float
    impact: str
    mitigation_strategy: str
    identified_at: datetime