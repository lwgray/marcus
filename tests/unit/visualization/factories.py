"""
Factory functions for creating test data
"""
from datetime import datetime, timedelta
import random
import uuid
import json
from typing import Dict, Any, List, Optional

from src.core.models import (
    Task, TaskStatus, Priority, WorkerStatus, 
    ProjectState, RiskLevel, BlockerReport
)
from src.visualization.conversation_stream import ConversationEvent


def create_mock_conversation_event(
    event_type: str = "WORKER_MESSAGE",
    source: str = None,
    target: str = None,
    message: str = None
) -> ConversationEvent:
    """Create a mock conversation event"""
    if source is None:
        source = f"worker-{uuid.uuid4().hex[:8]}"
    if target is None:
        target = "pm_agent"
    if message is None:
        message = "Test message"
    
    return ConversationEvent(
        id=f"event-{uuid.uuid4().hex[:8]}",
        timestamp=datetime.now(),
        source=source,
        target=target,
        event_type=event_type,
        message=message,
        metadata={
            "task_id": f"task-{uuid.uuid4().hex[:8]}",
            "confidence": random.uniform(0.5, 1.0)
        }
    )


def create_mock_decision(
    decision_type: str = "task_assignment",
    confidence: float = 0.85
) -> Dict[str, Any]:
    """Create a mock decision data structure for DecisionVisualizer"""
    decision_id = f"dec-{uuid.uuid4().hex[:8]}"
    
    # Match the structure expected by DecisionVisualizer.add_decision()
    return {
        "id": decision_id,
        "timestamp": datetime.now().isoformat(),
        "decision": f"Assign task to worker based on {decision_type}",
        "rationale": "Based on skill match and availability",
        "confidence_score": confidence,
        "alternatives_considered": [
            {"task": f"option-{i}", "score": random.uniform(0.3, 0.8)} 
            for i in range(3)
        ],
        "decision_factors": {
            "skill_match": random.uniform(0.7, 1.0),
            "availability": random.uniform(0.5, 1.0),
            "workload": random.uniform(0.3, 0.8)
        }
    }


def create_mock_worker_status(
    worker_id: Optional[str] = None,
    name: Optional[str] = None,
    skills: Optional[List[str]] = None
) -> WorkerStatus:
    """Create a mock WorkerStatus object"""
    if worker_id is None:
        worker_id = f"worker-{uuid.uuid4().hex[:8]}"
    if name is None:
        name = f"Worker {random.choice(['Alice', 'Bob', 'Charlie', 'David'])}"
    if skills is None:
        skills = random.sample(
            ["python", "javascript", "api", "database", "testing", "docker"],
            k=random.randint(2, 4)
        )
    
    return WorkerStatus(
        worker_id=worker_id,
        name=name,
        role=random.choice(["Developer", "Senior Developer", "Tech Lead"]),
        email=f"{name.lower().replace(' ', '.')}@example.com",
        current_tasks=[f"task-{uuid.uuid4().hex[:8]}" for _ in range(random.randint(0, 2))],
        completed_tasks_count=random.randint(0, 20),
        capacity=random.uniform(0.5, 1.0),
        skills=skills,
        availability="online",
        performance_score=random.uniform(0.7, 1.0)
    )


def create_mock_project_state(
    total_tasks: int = 20,
    risk_level: RiskLevel = RiskLevel.MEDIUM
) -> ProjectState:
    """Create a mock ProjectState object"""
    completed = random.randint(0, total_tasks // 2)
    in_progress = random.randint(0, total_tasks - completed)
    blocked = random.randint(0, 3)
    
    return ProjectState(
        board_id=f"board-{uuid.uuid4().hex[:8]}",
        project_name=f"Project {random.choice(['Alpha', 'Beta', 'Gamma', 'Delta'])}",
        total_tasks=total_tasks,
        completed_tasks=completed,
        in_progress_tasks=in_progress,
        blocked_tasks=blocked,
        progress_percent=(completed / total_tasks) * 100 if total_tasks > 0 else 0,
        overdue_tasks=[],
        team_velocity=random.uniform(0.5, 2.5),
        risk_level=risk_level,
        last_updated=datetime.now()
    )


def create_mock_health_data(
    overall_health: str = "good",
    alerts: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Create mock health analysis data"""
    if alerts is None:
        alerts = []
        
    return {
        "timestamp": datetime.now().isoformat(),
        "overall_health": overall_health,
        "risk_level": random.choice(["low", "medium", "high"]),
        "metrics": {
            "velocity": random.uniform(0.5, 2.5),
            "blocked_tasks": random.randint(0, 5),
            "worker_utilization": random.uniform(0.5, 0.95),
            "completion_rate": random.uniform(0.6, 0.95),
            "average_cycle_time": random.uniform(1, 10)
        },
        "alerts": alerts,
        "recommendations": [
            "Consider reassigning blocked tasks",
            "Review worker capacity",
            "Update project timeline"
        ][:random.randint(0, 3)]
    }


def create_mock_task(
    task_id: Optional[str] = None,
    status: TaskStatus = TaskStatus.TODO
) -> Task:
    """Create a mock Task object"""
    if task_id is None:
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        
    task_names = [
        "Implement user authentication",
        "Create API endpoints",
        "Set up database schema",
        "Write unit tests",
        "Deploy to staging",
        "Fix bug in payment flow"
    ]
    
    return Task(
        id=task_id,
        name=random.choice(task_names),
        description="Detailed description of the task requirements",
        status=status,
        priority=random.choice(list(Priority)),
        assigned_to=f"worker-{uuid.uuid4().hex[:8]}" if status != TaskStatus.TODO else None,
        created_at=datetime.now() - timedelta(days=random.randint(1, 30)),
        updated_at=datetime.now(),
        due_date=datetime.now() + timedelta(days=random.randint(1, 14)),
        estimated_hours=random.uniform(1, 16),
        actual_hours=random.uniform(0, 20) if status == TaskStatus.DONE else 0,
        dependencies=[],
        labels=random.sample(["backend", "frontend", "api", "database", "urgent"], k=2)
    )


def create_mock_blocker(
    task_id: Optional[str] = None,
    severity: RiskLevel = RiskLevel.HIGH
) -> BlockerReport:
    """Create a mock BlockerReport object"""
    if task_id is None:
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        
    descriptions = [
        "Database connection timeout",
        "API key not configured",
        "Dependency not available",
        "Unclear requirements",
        "Waiting for design approval",
        "Test environment down"
    ]
    
    return BlockerReport(
        task_id=task_id,
        reporter_id=f"worker-{uuid.uuid4().hex[:8]}",
        description=random.choice(descriptions),
        severity=severity,
        reported_at=datetime.now() - timedelta(hours=random.randint(1, 48)),
        resolved=False,
        resolution=None,
        resolved_at=None
    )


def create_knowledge_graph_data() -> Dict[str, Any]:
    """Create mock data for knowledge graph testing"""
    workers = [create_mock_worker_status() for _ in range(5)]
    tasks = [create_mock_task() for _ in range(10)]
    
    # Create relationships
    skills_to_tasks = {}
    for task in tasks:
        for label in task.labels:
            if label not in skills_to_tasks:
                skills_to_tasks[label] = []
            skills_to_tasks[label].append(task.id)
    
    return {
        "workers": workers,
        "tasks": tasks,
        "skills": list(set(skill for w in workers for skill in w.skills)),
        "relationships": {
            "worker_skills": {w.worker_id: w.skills for w in workers},
            "task_assignments": {t.id: t.assigned_to for t in tasks if t.assigned_to},
            "skill_requirements": skills_to_tasks
        }
    }


def create_mock_log_entry(event_type: str, event_name: str) -> str:
    """Create a mock log entry in JSONL format"""
    # Create proper log entry structure that matches ConversationStreamProcessor expectations
    if event_type == "simple":
        # Simple format from realtime logs
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_name,
            "source": "mcp_client",
            "echo": "test",
            "status": "ok"
        }
    else:
        # Legacy format
        event = {
            "timestamp": datetime.now().isoformat(),
            "event": event_name,
            "worker_id": f"worker-{uuid.uuid4().hex[:8]}",
            "conversation_type": "worker_to_pm",
            "message": "Test message",
            "metadata": {}
        }
    return json.dumps(event)