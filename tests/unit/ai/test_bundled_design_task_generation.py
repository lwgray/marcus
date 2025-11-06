"""
Unit tests for bundled design Task object generation.

Tests that bundled design tasks are properly converted from metadata dicts
to Task objects in _generate_detailed_task (fix for bundled designs not being created).
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.ai.advanced.prd.advanced_parser import (
    AdvancedPRDParser,
    PRDAnalysis,
    ProjectConstraints,
)
from src.core.models import Priority, Task, TaskStatus


class TestBundledDesignTaskGeneration:
    """Test suite for bundled design Task object generation"""

    @pytest.fixture
    def parser(self):
        """Create AdvancedPRDParser with mocked dependencies"""
        with patch(
            "src.ai.advanced.prd.advanced_parser.LLMAbstraction"
        ) as mock_llm_class:
            with patch(
                "src.ai.advanced.prd.advanced_parser.HybridDependencyInferer"
            ) as mock_dep_class:
                mock_llm = Mock()
                mock_llm.analyze = AsyncMock()
                mock_llm_class.return_value = mock_llm

                mock_dep = Mock()
                mock_dep.infer_dependencies = AsyncMock(return_value=Mock(edges=[]))
                mock_dep_class.return_value = mock_dep

                parser = AdvancedPRDParser()
                parser.llm_client = mock_llm
                parser.dependency_inferer = mock_dep

                # Mock _get_learned_task_duration to avoid DB access
                parser._get_learned_task_duration = Mock(return_value=6.0)

                return parser

    @pytest.fixture
    def bundled_design_metadata(self):
        """Sample bundled design task metadata"""
        return {
            "original_name": "Design Task Management",
            "type": "design",
            "epic_id": "epic_design_architecture",
            "domain_name": "Task Management",
            "feature_ids": ["feature_create_task", "feature_view_tasks"],
            "description": """Design the architecture for the Task Management \
which encompasses the following features:

1. CREATE TASK
   Create new tasks with title and description

2. VIEW TASKS
   Display list of all tasks

Your design should define:
- Component boundaries (what components exist and their responsibilities)
- Data flows (how data moves between components)
- Integration points (how components communicate)
- Shared data models (schemas, entities, etc.)

Create design artifacts such as:
- Architecture diagrams (component relationships, data flow)
- API contracts (endpoint definitions, request/response schemas)
- Data models (database schemas, entity relationships)
- Integration specifications (how components communicate)""",
            "estimated_hours": 0.2,
            "labels": ["design", "architecture", "task management"],
            "priority": "high",
        }

    @pytest.fixture
    def prd_analysis(self):
        """Sample PRD analysis"""
        return PRDAnalysis(
            functional_requirements=[
                {
                    "id": "feature_create_task",
                    "name": "Create Task",
                    "description": "Create new tasks",
                },
                {
                    "id": "feature_view_tasks",
                    "name": "View Tasks",
                    "description": "Display tasks",
                },
            ],
            non_functional_requirements=[],
            technical_constraints=[],
            business_objectives=[],
            user_personas=[],
            success_metrics=[],
            implementation_approach="agile",
            complexity_assessment={},
            risk_factors=[],
            confidence=0.85,
            original_description="Create a task management application",
        )

    @pytest.fixture
    def project_constraints(self):
        """Sample project constraints"""
        return ProjectConstraints(team_size=1, complexity_mode="standard")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bundled_design_task_converted_to_task_object(
        self, parser, bundled_design_metadata, prd_analysis, project_constraints
    ):
        """
        Test that bundled design task metadata is properly converted to Task object.

        This is the core fix - bundled design tasks don't have matching requirements,
        so they need special handling in _generate_detailed_task.
        """
        # Arrange
        task_id = "design_task_management"
        epic_id = "epic_design_architecture"

        # Store bundled design metadata (simulating what _create_bundled_design_tasks does)
        parser._task_metadata = {task_id: bundled_design_metadata}

        # Act
        result_task = await parser._generate_detailed_task(
            task_id=task_id,
            epic_id=epic_id,
            analysis=prd_analysis,
            constraints=project_constraints,
            sequence=1,
        )

        # Assert
        assert isinstance(result_task, Task)
        assert result_task.id == task_id
        assert result_task.name == "Design Task Management"
        assert "Task Management" in result_task.description
        assert "CREATE TASK" in result_task.description
        assert "VIEW TASKS" in result_task.description
        assert result_task.status == TaskStatus.TODO
        assert result_task.priority == Priority.HIGH
        assert result_task.estimated_hours == 0.2
        assert "design" in result_task.labels
        assert "architecture" in result_task.labels
        assert result_task.source_type == "bundled_design"
        assert result_task.source_context["domain_name"] == "Task Management"
        assert len(result_task.source_context["feature_ids"]) == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bundled_design_task_uses_stored_description(
        self, parser, bundled_design_metadata, prd_analysis, project_constraints
    ):
        """
        Test that bundled design uses the detailed description from metadata.

        The description from _create_bundled_design_tasks includes all features
        in the domain - we must preserve this, not generate a new generic one.
        """
        # Arrange
        task_id = "design_task_management"
        parser._task_metadata = {task_id: bundled_design_metadata}

        # Act
        result_task = await parser._generate_detailed_task(
            task_id=task_id,
            epic_id="epic_design_architecture",
            analysis=prd_analysis,
            constraints=project_constraints,
            sequence=1,
        )

        # Assert - should use the exact description from metadata
        assert result_task.description == bundled_design_metadata["description"]
        assert "CREATE TASK" in result_task.description
        assert "VIEW TASKS" in result_task.description
        assert "Component boundaries" in result_task.description

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bundled_design_task_uses_correct_estimated_hours(
        self, parser, bundled_design_metadata, prd_analysis, project_constraints
    ):
        """
        Test that bundled design uses estimated hours from metadata.

        Estimated hours are scaled by number of features in the domain during
        _create_bundled_design_tasks - we must use that value, not recalculate.
        """
        # Arrange
        task_id = "design_task_management"
        # Set custom estimated hours (scaled for 2 features)
        bundled_design_metadata["estimated_hours"] = 0.3
        parser._task_metadata = {task_id: bundled_design_metadata}

        # Act
        result_task = await parser._generate_detailed_task(
            task_id=task_id,
            epic_id="epic_design_architecture",
            analysis=prd_analysis,
            constraints=project_constraints,
            sequence=1,
        )

        # Assert - should use the scaled estimated hours from metadata
        assert result_task.estimated_hours == 0.3

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bundled_design_task_preserves_labels(
        self, parser, bundled_design_metadata, prd_analysis, project_constraints
    ):
        """Test that bundled design preserves labels from metadata"""
        # Arrange
        task_id = "design_task_management"
        custom_labels = ["design", "architecture", "core", "task management"]
        bundled_design_metadata["labels"] = custom_labels
        parser._task_metadata = {task_id: bundled_design_metadata}

        # Act
        result_task = await parser._generate_detailed_task(
            task_id=task_id,
            epic_id="epic_design_architecture",
            analysis=prd_analysis,
            constraints=project_constraints,
            sequence=1,
        )

        # Assert
        assert result_task.labels == custom_labels

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bundled_design_task_maps_priority_correctly(
        self, parser, bundled_design_metadata, prd_analysis, project_constraints
    ):
        """Test that bundled design correctly maps priority string to enum"""
        # Arrange
        task_id = "design_task_management"
        parser._task_metadata = {task_id: bundled_design_metadata}

        # Test high priority
        bundled_design_metadata["priority"] = "high"
        result_high = await parser._generate_detailed_task(
            task_id, "epic_design_architecture", prd_analysis, project_constraints, 1
        )
        assert result_high.priority == Priority.HIGH

        # Test medium priority
        bundled_design_metadata["priority"] = "medium"
        result_medium = await parser._generate_detailed_task(
            task_id, "epic_design_architecture", prd_analysis, project_constraints, 1
        )
        assert result_medium.priority == Priority.MEDIUM

        # Test low priority
        bundled_design_metadata["priority"] = "low"
        result_low = await parser._generate_detailed_task(
            task_id, "epic_design_architecture", prd_analysis, project_constraints, 1
        )
        assert result_low.priority == Priority.LOW

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bundled_design_with_missing_description_uses_fallback(
        self, parser, bundled_design_metadata, prd_analysis, project_constraints
    ):
        """Test bundled design with missing description gets fallback"""
        # Arrange
        task_id = "design_task_management"
        # Remove description to test fallback
        del bundled_design_metadata["description"]
        parser._task_metadata = {task_id: bundled_design_metadata}

        # Act
        result_task = await parser._generate_detailed_task(
            task_id=task_id,
            epic_id="epic_design_architecture",
            analysis=prd_analysis,
            constraints=project_constraints,
            sequence=1,
        )

        # Assert - should use fallback description
        assert "Design the architecture for Task Management" in result_task.description

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bundled_design_stores_feature_ids_in_context(
        self, parser, bundled_design_metadata, prd_analysis, project_constraints
    ):
        """Test that bundled design stores feature_ids for dependency tracking"""
        # Arrange
        task_id = "design_task_management"
        parser._task_metadata = {task_id: bundled_design_metadata}

        # Act
        result_task = await parser._generate_detailed_task(
            task_id=task_id,
            epic_id="epic_design_architecture",
            analysis=prd_analysis,
            constraints=project_constraints,
            sequence=1,
        )

        # Assert
        assert "feature_ids" in result_task.source_context
        assert result_task.source_context["feature_ids"] == [
            "feature_create_task",
            "feature_view_tasks",
        ]
