from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class TaskStatus(Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Task:
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
    dependencies: List[str] = None
    labels: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.labels is None:
            self.labels = []


@dataclass
class ProjectState:
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


@dataclass
class BlockerReport:
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
    risk_type: str
    description: str
    severity: RiskLevel
    probability: float
    impact: str
    mitigation_strategy: str
    identified_at: datetime