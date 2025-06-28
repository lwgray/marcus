"""
Board Quality Validator

Validates boards against Marcus quality standards and provides
actionable feedback for improvement.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from src.core.models import Task, TaskStatus, Priority


class QualityLevel(Enum):
    """Board quality levels"""
    POOR = "poor"
    BASIC = "basic" 
    GOOD = "good"
    EXCELLENT = "excellent"


@dataclass
class QualityIssue:
    """Represents a quality issue found in board/task"""
    task_id: Optional[str]
    issue_type: str
    severity: str  # "error", "warning", "info"
    message: str
    suggestion: str


@dataclass
class QualityReport:
    """Complete quality assessment report"""
    score: float
    level: QualityLevel
    issues: List[QualityIssue]
    metrics: Dict[str, Any]
    suggestions: List[str]


class BoardQualityValidator:
    """Validates board quality against Marcus standards"""
    
    # Minimum requirements
    MIN_DESCRIPTION_LENGTH = 50
    MIN_LABELS_PER_TASK = 2
    REQUIRED_LABEL_CATEGORIES = ["phase", "component", "type"]
    
    # Quality weights
    WEIGHTS = {
        "descriptions": 0.25,
        "labels": 0.20,
        "estimates": 0.25,
        "priorities": 0.15,
        "dependencies": 0.15
    }
    
    def validate_board(self, tasks: List[Task]) -> QualityReport:
        """
        Validate entire board quality
        
        Args:
            tasks: List of tasks on the board
            
        Returns:
            QualityReport with score, issues, and suggestions
        """
        if not tasks:
            return QualityReport(
                score=0.0,
                level=QualityLevel.POOR,
                issues=[QualityIssue(
                    task_id=None,
                    issue_type="empty_board",
                    severity="error",
                    message="Board has no tasks",
                    suggestion="Create tasks to define project scope"
                )],
                metrics={},
                suggestions=["Start by creating high-level epics or phases"]
            )
        
        # Validate individual tasks
        task_issues = []
        task_scores = []
        
        for task in tasks:
            score, issues = self.validate_task(task)
            task_scores.append(score)
            task_issues.extend(issues)
        
        # Calculate metrics
        metrics = self._calculate_board_metrics(tasks)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(tasks, metrics)
        
        # Determine quality level
        level = self._determine_quality_level(overall_score)
        
        # Generate suggestions
        suggestions = self._generate_board_suggestions(metrics, task_issues)
        
        return QualityReport(
            score=overall_score,
            level=level,
            issues=task_issues,
            metrics=metrics,
            suggestions=suggestions
        )
    
    def validate_task(self, task: Task) -> Tuple[float, List[QualityIssue]]:
        """
        Validate individual task quality
        
        Returns:
            Tuple of (score, list of issues)
        """
        issues = []
        scores = {}
        
        # Check description
        desc_score, desc_issues = self._validate_description(task)
        scores["description"] = desc_score
        issues.extend(desc_issues)
        
        # Check labels
        label_score, label_issues = self._validate_labels(task)
        scores["labels"] = label_score
        issues.extend(label_issues)
        
        # Check estimates
        estimate_score, estimate_issues = self._validate_estimates(task)
        scores["estimates"] = estimate_score
        issues.extend(estimate_issues)
        
        # Check priority
        priority_score, priority_issues = self._validate_priority(task)
        scores["priority"] = priority_score
        issues.extend(priority_issues)
        
        # Calculate task score
        task_score = sum(scores.values()) / len(scores)
        
        return task_score, issues
    
    def _validate_description(self, task: Task) -> Tuple[float, List[QualityIssue]]:
        """Validate task description"""
        issues = []
        
        if not task.description:
            issues.append(QualityIssue(
                task_id=task.id,
                issue_type="missing_description",
                severity="error",
                message=f"Task '{task.title}' has no description",
                suggestion="Add a description explaining what needs to be done and why"
            ))
            return 0.0, issues
        
        if len(task.description) < self.MIN_DESCRIPTION_LENGTH:
            issues.append(QualityIssue(
                task_id=task.id,
                issue_type="short_description",
                severity="warning",
                message=f"Task '{task.title}' has a very short description ({len(task.description)} chars)",
                suggestion=f"Expand description to at least {self.MIN_DESCRIPTION_LENGTH} characters with context"
            ))
            return 0.5, issues
        
        # Check for acceptance criteria
        if "acceptance criteria" not in task.description.lower() and \
           len(task.description) < 200:
            issues.append(QualityIssue(
                task_id=task.id,
                issue_type="missing_acceptance_criteria",
                severity="info",
                message=f"Task '{task.title}' lacks acceptance criteria",
                suggestion="Add acceptance criteria to define 'done'"
            ))
            return 0.8, issues
        
        return 1.0, issues
    
    def _validate_labels(self, task: Task) -> Tuple[float, List[QualityIssue]]:
        """Validate task labels"""
        issues = []
        
        if not task.labels:
            issues.append(QualityIssue(
                task_id=task.id,
                issue_type="missing_labels",
                severity="error",
                message=f"Task '{task.title}' has no labels",
                suggestion="Add labels for phase, component, type, and skills"
            ))
            return 0.0, issues
        
        if len(task.labels) < self.MIN_LABELS_PER_TASK:
            issues.append(QualityIssue(
                task_id=task.id,
                issue_type="insufficient_labels",
                severity="warning",
                message=f"Task '{task.title}' has only {len(task.labels)} label(s)",
                suggestion=f"Add at least {self.MIN_LABELS_PER_TASK} labels for better categorization"
            ))
            return 0.5, issues
        
        # Check for required categories
        label_categories = [label.split(':')[0] for label in task.labels if ':' in label]
        missing_categories = set(self.REQUIRED_LABEL_CATEGORIES) - set(label_categories)
        
        if missing_categories:
            issues.append(QualityIssue(
                task_id=task.id,
                issue_type="missing_label_categories",
                severity="info",
                message=f"Task '{task.title}' missing label categories: {', '.join(missing_categories)}",
                suggestion=f"Add labels for: {', '.join(missing_categories)}"
            ))
            return 0.7, issues
        
        return 1.0, issues
    
    def _validate_estimates(self, task: Task) -> Tuple[float, List[QualityIssue]]:
        """Validate task time estimates"""
        issues = []
        
        if not hasattr(task, 'estimated_hours') or not task.estimated_hours:
            issues.append(QualityIssue(
                task_id=task.id,
                issue_type="missing_estimate",
                severity="error",
                message=f"Task '{task.title}' has no time estimate",
                suggestion="Add estimated hours based on complexity"
            ))
            return 0.0, issues
        
        # Check for unrealistic estimates
        if task.estimated_hours > 40:
            issues.append(QualityIssue(
                task_id=task.id,
                issue_type="large_estimate",
                severity="warning",
                message=f"Task '{task.title}' estimated at {task.estimated_hours} hours",
                suggestion="Consider breaking into smaller sub-tasks"
            ))
            return 0.7, issues
        
        if task.estimated_hours < 0.5:
            issues.append(QualityIssue(
                task_id=task.id,
                issue_type="tiny_estimate",
                severity="info",
                message=f"Task '{task.title}' estimated at {task.estimated_hours} hours",
                suggestion="Verify if task is too granular or estimate is realistic"
            ))
            return 0.9, issues
        
        return 1.0, issues
    
    def _validate_priority(self, task: Task) -> Tuple[float, List[QualityIssue]]:
        """Validate task priority"""
        issues = []
        
        if not task.priority:
            issues.append(QualityIssue(
                task_id=task.id,
                issue_type="missing_priority",
                severity="warning",
                message=f"Task '{task.title}' has no priority set",
                suggestion="Set priority (urgent/high/medium/low) to guide sequencing"
            ))
            return 0.0, issues
        
        return 1.0, issues
    
    def _calculate_board_metrics(self, tasks: List[Task]) -> Dict[str, Any]:
        """Calculate board-level metrics"""
        total_tasks = len(tasks)
        
        metrics = {
            "total_tasks": total_tasks,
            "tasks_with_descriptions": sum(1 for t in tasks if t.description),
            "tasks_with_labels": sum(1 for t in tasks if t.labels),
            "tasks_with_estimates": sum(1 for t in tasks if hasattr(t, 'estimated_hours') and t.estimated_hours),
            "tasks_with_dependencies": sum(1 for t in tasks if t.dependencies),
            "tasks_with_priority": sum(1 for t in tasks if t.priority),
            "average_labels_per_task": sum(len(t.labels) for t in tasks) / total_tasks if total_tasks > 0 else 0,
            "priority_distribution": self._get_priority_distribution(tasks),
            "label_categories": self._get_label_categories(tasks),
            "phase_distribution": self._get_phase_distribution(tasks)
        }
        
        # Calculate percentages
        metrics["description_coverage"] = metrics["tasks_with_descriptions"] / total_tasks if total_tasks > 0 else 0
        metrics["label_coverage"] = metrics["tasks_with_labels"] / total_tasks if total_tasks > 0 else 0
        metrics["estimate_coverage"] = metrics["tasks_with_estimates"] / total_tasks if total_tasks > 0 else 0
        metrics["dependency_coverage"] = metrics["tasks_with_dependencies"] / total_tasks if total_tasks > 0 else 0
        
        return metrics
    
    def _calculate_overall_score(self, tasks: List[Task], metrics: Dict[str, Any]) -> float:
        """Calculate weighted overall score"""
        scores = {
            "descriptions": metrics["description_coverage"],
            "labels": min(metrics["average_labels_per_task"] / self.MIN_LABELS_PER_TASK, 1.0),
            "estimates": metrics["estimate_coverage"],
            "priorities": 1.0 if len(metrics["priority_distribution"]) > 1 else 0.5,
            "dependencies": min(metrics["dependency_coverage"] * 2, 1.0)  # Less weight on 100% coverage
        }
        
        # Apply weights
        weighted_score = sum(scores[key] * self.WEIGHTS[key] for key in scores)
        
        return round(weighted_score, 2)
    
    def _determine_quality_level(self, score: float) -> QualityLevel:
        """Determine quality level from score"""
        if score >= 0.8:
            return QualityLevel.EXCELLENT
        elif score >= 0.6:
            return QualityLevel.GOOD
        elif score >= 0.3:
            return QualityLevel.BASIC
        else:
            return QualityLevel.POOR
    
    def _generate_board_suggestions(self, metrics: Dict[str, Any], issues: List[QualityIssue]) -> List[str]:
        """Generate board-level improvement suggestions"""
        suggestions = []
        
        # Based on metrics
        if metrics["description_coverage"] < 0.8:
            suggestions.append("Add descriptions to all tasks to provide context")
        
        if metrics["average_labels_per_task"] < self.MIN_LABELS_PER_TASK:
            suggestions.append(f"Increase labeling - aim for {self.MIN_LABELS_PER_TASK}+ labels per task")
        
        if metrics["estimate_coverage"] < 0.9:
            suggestions.append("Add time estimates to enable better planning")
        
        if len(metrics["priority_distribution"]) == 1:
            suggestions.append("Vary task priorities - not everything can be 'high'")
        
        if metrics["dependency_coverage"] < 0.3:
            suggestions.append("Map task dependencies to understand workflow")
        
        # Based on common issues
        error_count = sum(1 for issue in issues if issue.severity == "error")
        if error_count > 5:
            suggestions.append(f"Focus on fixing {error_count} critical issues first")
        
        # Phase organization
        if not metrics.get("phase_distribution"):
            suggestions.append("Organize tasks into development phases")
        
        return suggestions
    
    def _get_priority_distribution(self, tasks: List[Task]) -> Dict[str, int]:
        """Get distribution of priorities"""
        distribution = {}
        for task in tasks:
            if task.priority:
                priority_name = task.priority.value if hasattr(task.priority, 'value') else str(task.priority)
                distribution[priority_name] = distribution.get(priority_name, 0) + 1
        return distribution
    
    def _get_label_categories(self, tasks: List[Task]) -> Dict[str, int]:
        """Get distribution of label categories"""
        categories = {}
        for task in tasks:
            for label in task.labels:
                if ':' in label:
                    category = label.split(':')[0]
                    categories[category] = categories.get(category, 0) + 1
        return categories
    
    def _get_phase_distribution(self, tasks: List[Task]) -> Dict[str, int]:
        """Get distribution of tasks by phase"""
        phases = {}
        for task in tasks:
            phase_labels = [l for l in task.labels if l.startswith('phase:')]
            if phase_labels:
                phase = phase_labels[0].replace('phase:', '')
                phases[phase] = phases.get(phase, 0) + 1
        return phases


# Convenience function
def validate_board_quality(tasks: List[Task]) -> QualityReport:
    """
    Validate board quality and return report
    
    Args:
        tasks: List of tasks on the board
        
    Returns:
        QualityReport with score, issues, and suggestions
    """
    validator = BoardQualityValidator()
    return validator.validate_board(tasks)