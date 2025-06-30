"""
Test data factories for creating consistent test objects.

These factories provide a convenient way to create test data with
sensible defaults that can be easily overridden.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import random
import string

from src.core.models import (
    Task, TaskStatus, Priority, RiskLevel,
    WorkerStatus, ProjectState, TaskAssignment,
    BlockerReport
)


class TaskFactory:
    """Factory for creating Task objects for testing."""
    
    _counter = 0
    
    @classmethod
    def create(cls, **kwargs) -> Task:
        """
        Create a Task with default values that can be overridden.
        
        Each task gets a unique ID automatically.
        """
        cls._counter += 1
        
        defaults = {
            'id': f"TASK-{cls._counter:04d}",
            'name': f"Task {cls._counter}",
            'description': f"Description for task {cls._counter}",
            'status': TaskStatus.TODO,
            'priority': Priority.MEDIUM,
            'assigned_to': None,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'due_date': datetime.now() + timedelta(days=7),
            'estimated_hours': 4.0,
            'actual_hours': 0.0,
            'dependencies': [],
            'labels': []
        }
        
        # Handle special cases
        if 'status' in kwargs and isinstance(kwargs['status'], str):
            kwargs['status'] = TaskStatus[kwargs['status'].upper()]
        if 'priority' in kwargs and isinstance(kwargs['priority'], str):
            kwargs['priority'] = Priority[kwargs['priority'].upper()]
            
        defaults.update(kwargs)
        return Task(**defaults)
    
    @classmethod
    def create_batch(cls, count: int, **kwargs) -> List[Task]:
        """Create multiple tasks with the same overrides."""
        return [cls.create(**kwargs) for _ in range(count)]
    
    @classmethod
    def create_with_dependencies(cls, dep_count: int = 2, **kwargs) -> Task:
        """Create a task with dependencies."""
        dependencies = [f"TASK-DEP-{i:03d}" for i in range(dep_count)]
        kwargs['dependencies'] = dependencies
        return cls.create(**kwargs)
    
    @classmethod
    def reset_counter(cls):
        """Reset the counter for consistent test runs."""
        cls._counter = 0


class AgentFactory:
    """Factory for creating WorkerStatus objects for testing."""
    
    _counter = 0
    _names = [
        "Alice Smith", "Bob Johnson", "Charlie Brown", "Diana Prince",
        "Eve Adams", "Frank Castle", "Grace Hopper", "Henry Ford"
    ]
    _roles = ["Developer", "Tester", "Designer", "DevOps", "Architect"]
    _skills = [
        ["python", "django", "postgres"],
        ["javascript", "react", "node"],
        ["java", "spring", "mysql"],
        ["go", "kubernetes", "docker"],
        ["rust", "webassembly", "systems"],
        ["testing", "selenium", "pytest"],
        ["ui/ux", "figma", "css"]
    ]
    
    @classmethod
    def create(cls, **kwargs) -> WorkerStatus:
        """
        Create a WorkerStatus with default values that can be overridden.
        
        Each agent gets a unique ID and randomized attributes.
        """
        cls._counter += 1
        
        defaults = {
            'worker_id': f"agent-{cls._counter:03d}",
            'name': random.choice(cls._names),
            'role': random.choice(cls._roles),
            'email': f"agent{cls._counter}@example.com",
            'current_tasks': [],
            'completed_tasks_count': random.randint(0, 50),
            'capacity': 40,
            'skills': random.choice(cls._skills),
            'availability': {
                'monday': True,
                'tuesday': True,
                'wednesday': True,
                'thursday': True,
                'friday': True,
                'saturday': False,
                'sunday': False
            },
            'performance_score': round(random.uniform(0.8, 1.2), 2)
        }
        
        defaults.update(kwargs)
        return WorkerStatus(**defaults)
    
    @classmethod
    def create_team(cls, size: int, **kwargs) -> List[WorkerStatus]:
        """Create a team of agents with diverse skills."""
        team = []
        for i in range(size):
            # Ensure diverse skills in the team
            agent_kwargs = kwargs.copy()
            if 'skills' not in agent_kwargs:
                agent_kwargs['skills'] = cls._skills[i % len(cls._skills)]
            team.append(cls.create(**agent_kwargs))
        return team
    
    @classmethod
    def create_busy_agent(cls, task_count: int = 3, **kwargs) -> WorkerStatus:
        """Create an agent with current tasks."""
        current_tasks = [f"TASK-{i:04d}" for i in range(task_count)]
        kwargs['current_tasks'] = current_tasks
        return cls.create(**kwargs)
    
    @classmethod
    def reset_counter(cls):
        """Reset the counter for consistent test runs."""
        cls._counter = 0


class ProjectStateFactory:
    """Factory for creating ProjectState objects for testing."""
    
    @classmethod
    def create(cls, **kwargs) -> ProjectState:
        """Create a ProjectState with default values."""
        total_tasks = kwargs.get('total_tasks', 20)
        completed = kwargs.get('completed_tasks', 8)
        in_progress = kwargs.get('in_progress_tasks', 5)
        blocked = kwargs.get('blocked_tasks', 2)
        
        defaults = {
            'board_id': 'board-001',
            'project_name': 'Test Project',
            'total_tasks': total_tasks,
            'completed_tasks': completed,
            'in_progress_tasks': in_progress,
            'blocked_tasks': blocked,
            'progress_percent': round((completed / total_tasks) * 100, 1),
            'overdue_tasks': [],
            'team_velocity': 2.5,
            'risk_level': RiskLevel.LOW,
            'last_updated': datetime.now()
        }
        
        # Determine risk level based on metrics
        if blocked > 5 or kwargs.get('overdue_tasks', []):
            defaults['risk_level'] = RiskLevel.HIGH
        elif blocked > 2:
            defaults['risk_level'] = RiskLevel.MEDIUM
            
        defaults.update(kwargs)
        return ProjectState(**defaults)
    
    @classmethod
    def create_healthy_project(cls) -> ProjectState:
        """Create a project in good health."""
        return cls.create(
            completed_tasks=15,
            in_progress_tasks=3,
            blocked_tasks=0,
            risk_level=RiskLevel.LOW
        )
    
    @classmethod
    def create_struggling_project(cls) -> ProjectState:
        """Create a project with issues."""
        return cls.create(
            completed_tasks=3,
            in_progress_tasks=2,
            blocked_tasks=8,
            overdue_tasks=['TASK-001', 'TASK-002', 'TASK-003'],
            risk_level=RiskLevel.HIGH
        )


class BlockerFactory:
    """Factory for creating BlockerReport objects for testing."""
    
    _counter = 0
    _blocker_descriptions = [
        "API endpoint not responding",
        "Missing documentation for integration",
        "Waiting for design approval",
        "Database migration failed",
        "External dependency not available",
        "Performance regression in latest build",
        "Security vulnerability needs addressing"
    ]
    
    @classmethod
    def create(cls, **kwargs) -> BlockerReport:
        """Create a BlockerReport with default values."""
        cls._counter += 1
        
        defaults = {
            'task_id': f"TASK-{random.randint(1, 100):04d}",
            'reporter_id': f"agent-{random.randint(1, 10):03d}",
            'description': random.choice(cls._blocker_descriptions),
            'severity': random.choice(list(RiskLevel)),
            'reported_at': datetime.now(),
            'resolved': False,
            'resolution': None,
            'resolved_at': None,
            'resolution_time_hours': None
        }
        
        # Handle resolved blockers
        if kwargs.get('resolved', False):
            defaults['resolution'] = "Issue resolved by implementing workaround"
            defaults['resolved_at'] = datetime.now()
            defaults['resolution_time_hours'] = random.uniform(1, 48)
            
        defaults.update(kwargs)
        return BlockerReport(**defaults)
    
    @classmethod
    def create_critical_blocker(cls, **kwargs) -> BlockerReport:
        """Create a critical severity blocker."""
        kwargs['severity'] = RiskLevel.CRITICAL
        kwargs['description'] = "Production system down - immediate attention required"
        return cls.create(**kwargs)


def reset_all_counters():
    """Reset all factory counters for test isolation."""
    TaskFactory.reset_counter()
    AgentFactory.reset_counter()
    BlockerFactory._counter = 0