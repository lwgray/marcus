"""
Basic Enricher for Marcus Phase 2

Simple task enrichment without requiring board context.
"""

import re
from typing import List
from datetime import datetime

from src.core.models import Task, Priority


class BasicEnricher:
    """Basic task enricher that improves poorly defined tasks"""
    
    def __init__(self):
        # Keywords for priority detection
        self.priority_keywords = {
            Priority.URGENT: ['urgent', 'critical', 'emergency', 'asap', 'immediately'],
            Priority.HIGH: ['important', 'high priority', 'soon', 'quickly'],
            Priority.LOW: ['minor', 'low priority', 'eventually', 'nice to have']
        }
        
        # Common task patterns and their estimates
        self.task_patterns = {
            'bug': {'hours': 4, 'labels': ['bug', 'fix']},
            'feature': {'hours': 8, 'labels': ['feature', 'enhancement']},
            'test': {'hours': 3, 'labels': ['testing', 'qa']},
            'documentation': {'hours': 2, 'labels': ['docs', 'documentation']},
            'refactor': {'hours': 6, 'labels': ['refactoring', 'cleanup']},
            'setup': {'hours': 3, 'labels': ['setup', 'configuration']},
            'deploy': {'hours': 2, 'labels': ['deployment', 'release']}
        }
    
    def enrich_task(self, task: Task) -> Task:
        """Enrich a single task with better information"""
        # Create a copy to avoid modifying the original
        enriched = Task(
            id=task.id,
            name=self._improve_name(task.name),
            description=self._generate_description(task),
            status=task.status,
            priority=self._adjust_priority(task),
            labels=self._suggest_labels(task),
            assigned_to=task.assigned_to,
            created_at=task.created_at,
            updated_at=datetime.now(),
            estimated_hours=self._estimate_hours(task),
            dependencies=task.dependencies,
            due_date=task.due_date
        )
        
        return enriched
    
    def _improve_name(self, name: str) -> str:
        """Improve vague task names"""
        # Capitalize first letter of each word
        improved = name.title()
        
        # Add clarity to common vague names
        vague_improvements = {
            'Fix Bug': 'Fix Login Authentication Bug',
            'Update Code': 'Update Code Documentation',
            'Test': 'Run Comprehensive Test Suite',
            'Deploy': 'Deploy to Production Environment'
        }
        
        return vague_improvements.get(improved, improved)
    
    def _generate_description(self, task: Task) -> str:
        """Generate helpful description if missing"""
        if task.description and len(task.description) > 10:
            return task.description
        
        # Generate based on task name
        name_lower = task.name.lower()
        
        if 'bug' in name_lower or 'fix' in name_lower:
            return "Investigate and resolve the reported issue. Ensure the fix is tested and doesn't introduce regressions."
        elif 'feature' in name_lower or 'implement' in name_lower:
            return "Implement the new functionality as specified. Include unit tests and documentation."
        elif 'test' in name_lower:
            return "Create and run tests to ensure functionality works as expected."
        elif 'deploy' in name_lower:
            return "Deploy the application to the target environment following the deployment checklist."
        else:
            return f"Complete the task: {task.name}. Ensure quality standards are met."
    
    def _suggest_labels(self, task: Task) -> List[str]:
        """Suggest relevant labels based on task content"""
        labels = list(task.labels)  # Start with existing labels
        name_lower = task.name.lower()
        
        # Add labels based on task patterns
        for pattern, config in self.task_patterns.items():
            if pattern in name_lower:
                for label in config['labels']:
                    if label not in labels:
                        labels.append(label)
        
        # Add technology-specific labels
        tech_keywords = {
            'python': 'python',
            'javascript': 'javascript',
            'react': 'react',
            'api': 'backend',
            'database': 'database',
            'ui': 'frontend'
        }
        
        for keyword, label in tech_keywords.items():
            if keyword in name_lower and label not in labels:
                labels.append(label)
        
        return labels
    
    def _adjust_priority(self, task: Task) -> Priority:
        """Adjust priority based on keywords"""
        name_lower = task.name.lower()
        desc_lower = (task.description or '').lower()
        combined = f"{name_lower} {desc_lower}"
        
        # Check for priority keywords
        for priority, keywords in self.priority_keywords.items():
            if any(keyword in combined for keyword in keywords):
                return priority
        
        # Special cases
        if 'bug' in combined or 'broken' in combined:
            return Priority.HIGH
        
        return task.priority
    
    def _estimate_hours(self, task: Task) -> int:
        """Estimate effort hours based on task type"""
        if task.estimated_hours:
            return task.estimated_hours
        
        name_lower = task.name.lower()
        
        # Check patterns
        for pattern, config in self.task_patterns.items():
            if pattern in name_lower:
                return config['hours']
        
        # Default estimate
        return 4