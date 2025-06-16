import pytest
from datetime import datetime, timedelta

from src.core.models import (
    Task, TaskStatus, Priority, RiskLevel,
    ProjectState, WorkerStatus, TaskAssignment
)


class TestTaskModel:
    def test_task_creation(self):
        task = Task(
            id="TASK-001",
            name="Implement login feature",
            description="Add user authentication",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=3),
            estimated_hours=8.0
        )
        
        assert task.id == "TASK-001"
        assert task.status == TaskStatus.TODO
        assert task.priority == Priority.HIGH
        assert task.actual_hours == 0.0
        assert task.dependencies == []
        assert task.labels == []
    
    def test_task_with_dependencies(self):
        task = Task(
            id="TASK-002",
            name="Deploy to production",
            description="Deploy the application",
            status=TaskStatus.TODO,
            priority=Priority.URGENT,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=2.0,
            dependencies=["TASK-001", "TASK-003"]
        )
        
        assert len(task.dependencies) == 2
        assert "TASK-001" in task.dependencies


class TestProjectState:
    def test_project_state_creation(self):
        now = datetime.now()
        overdue_task = Task(
            id="TASK-001",
            name="Overdue task",
            description="This task is overdue",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            assigned_to="dev1",
            created_at=now - timedelta(days=7),
            updated_at=now - timedelta(days=2),
            due_date=now - timedelta(days=1),
            estimated_hours=4.0
        )
        
        state = ProjectState(
            board_id="BOARD-001",
            project_name="Test Project",
            total_tasks=10,
            completed_tasks=3,
            in_progress_tasks=4,
            blocked_tasks=1,
            progress_percent=30.0,
            overdue_tasks=[overdue_task],
            team_velocity=5.0,
            risk_level=RiskLevel.MEDIUM,
            last_updated=now
        )
        
        assert state.board_id == "BOARD-001"
        assert state.progress_percent == 30.0
        assert len(state.overdue_tasks) == 1
        assert state.risk_level == RiskLevel.MEDIUM
    
    def test_project_health_calculation(self):
        state = ProjectState(
            board_id="BOARD-001",
            project_name="Healthy Project",
            total_tasks=100,
            completed_tasks=75,
            in_progress_tasks=20,
            blocked_tasks=0,
            progress_percent=75.0,
            overdue_tasks=[],
            team_velocity=10.0,
            risk_level=RiskLevel.LOW,
            last_updated=datetime.now()
        )
        
        assert state.progress_percent == 75.0
        assert state.risk_level == RiskLevel.LOW
        assert len(state.overdue_tasks) == 0


class TestWorkerStatus:
    def test_worker_creation(self):
        task1 = Task(
            id="TASK-001",
            name="Current task",
            description="Working on this",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.MEDIUM,
            assigned_to="worker1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=4.0
        )
        
        worker = WorkerStatus(
            worker_id="worker1",
            name="John Doe",
            role="Backend Developer",
            email="john@example.com",
            current_tasks=[task1],
            completed_tasks_count=15,
            capacity=40,  # hours per week
            skills=["python", "django", "postgresql"],
            availability={"monday": True, "tuesday": True}
        )
        
        assert worker.worker_id == "worker1"
        assert len(worker.current_tasks) == 1
        assert worker.performance_score == 1.0
        assert "python" in worker.skills
    
    def test_worker_capacity_check(self):
        worker = WorkerStatus(
            worker_id="worker2",
            name="Jane Smith",
            role="Frontend Developer",
            email=None,
            current_tasks=[],
            completed_tasks_count=20,
            capacity=35,
            skills=["react", "typescript"],
            availability={},
            performance_score=1.2
        )
        
        assert worker.capacity == 35
        assert worker.performance_score == 1.2
        assert len(worker.current_tasks) == 0


class TestTaskAssignment:
    def test_assignment_creation(self):
        now = datetime.now()
        due_date = now + timedelta(days=5)
        
        assignment = TaskAssignment(
            task_id="TASK-001",
            task_name="Implement API endpoint",
            description="Create REST API for user management",
            instructions="1. Design the API schema\n2. Implement endpoints\n3. Add tests",
            estimated_hours=12.0,
            priority=Priority.HIGH,
            dependencies=["TASK-000"],
            assigned_to="dev1",
            assigned_at=now,
            due_date=due_date
        )
        
        assert assignment.task_id == "TASK-001"
        assert assignment.assigned_to == "dev1"
        assert assignment.estimated_hours == 12.0
        assert len(assignment.dependencies) == 1
        assert assignment.due_date == due_date