"""
Unit tests for Intelligent Task Enricher data classes.

This module tests the data classes used by the IntelligentTaskEnricher
including EnhancementResult and ProjectContext classes, ensuring proper
creation, validation, and behavior.

Notes
-----
These are unit tests for data structure validation and do not require
mocking of external services.
"""

from datetime import datetime

from src.ai.enrichment.intelligent_enricher import (
    EnhancementResult,
    ProjectContext,
)
from src.core.models import Priority, Task, TaskStatus


class TestEnhancementResultDataClass:
    """Test suite for EnhancementResult data class"""

    def test_enhancement_result_creation(self):
        """Test EnhancementResult creation with all fields"""
        task = Task(
            id="task-123",
            name="Test task",
            description="Test description",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=5.0,
            labels=[],
        )

        result = EnhancementResult(
            original_task=task,
            enhanced_description="Enhanced description",
            suggested_labels=["label1", "label2"],
            estimated_hours=8.0,
            suggested_dependencies=["dep1"],
            acceptance_criteria=["criteria1", "criteria2"],
            risk_factors=["risk1"],
            confidence=0.8,
            reasoning="Test reasoning",
            changes_made={"description": "changed"},
            enhancement_timestamp=datetime.now(),
        )

        assert result.original_task == task
        assert result.enhanced_description == "Enhanced description"
        assert result.suggested_labels == ["label1", "label2"]
        assert result.estimated_hours == 8.0
        assert result.suggested_dependencies == ["dep1"]
        assert result.acceptance_criteria == ["criteria1", "criteria2"]
        assert result.risk_factors == ["risk1"]
        assert result.confidence == 0.8
        assert result.reasoning == "Test reasoning"
        assert result.changes_made == {"description": "changed"}
        assert isinstance(result.enhancement_timestamp, datetime)

    def test_enhancement_result_post_init_timestamp(self):
        """Test EnhancementResult post_init sets timestamp if not provided"""
        task = Task(
            id="task-123",
            name="Test task",
            description="Test description",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=5.0,
            labels=[],
        )

        # Create without timestamp - the post_init should set it
        result = EnhancementResult(
            original_task=task,
            enhanced_description="Enhanced description",
            suggested_labels=[],
            estimated_hours=None,
            suggested_dependencies=[],
            acceptance_criteria=[],
            risk_factors=[],
            confidence=0.5,
            reasoning="Test reasoning",
            changes_made={},
            enhancement_timestamp=None,  # Explicitly set to None to test post_init
        )

        # Should have timestamp set automatically by post_init
        assert isinstance(result.enhancement_timestamp, datetime)
        assert result.enhancement_timestamp is not None


class TestProjectContextDataClass:
    """Test suite for ProjectContext data class"""

    def test_project_context_creation(self):
        """Test ProjectContext creation with all fields"""
        existing_task = Task(
            id="task-1",
            name="Existing task",
            description="Existing description",
            status=TaskStatus.DONE,
            priority=Priority.LOW,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=2.0,
            labels=[],
        )

        context = ProjectContext(
            project_type="web_application",
            tech_stack=["python", "react", "postgresql"],
            team_size=5,
            existing_tasks=[existing_task],
            project_standards={"style": "pep8", "testing": "pytest"},
            historical_data=[{"type": "feature", "avg_hours": 8.0}],
            quality_requirements={
                "testing_required": True,
                "documentation_required": True,
            },
        )

        assert context.project_type == "web_application"
        assert context.tech_stack == ["python", "react", "postgresql"]
        assert context.team_size == 5
        assert len(context.existing_tasks) == 1
        assert context.existing_tasks[0] == existing_task
        assert context.project_standards == {"style": "pep8", "testing": "pytest"}
        assert context.historical_data == [{"type": "feature", "avg_hours": 8.0}]
        assert context.quality_requirements == {
            "testing_required": True,
            "documentation_required": True,
        }
