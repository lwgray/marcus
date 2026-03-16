"""
Unit tests for NFR and infrastructure task generation.

Tests that NFR and infrastructure tasks are properly converted from metadata
to Task objects in _generate_detailed_task (regression test for #139).
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


class TestNFRTaskGeneration:
    """Test suite for NFR task generation"""

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
                parser._get_learned_task_duration = Mock(return_value=8.0)

                return parser

    @pytest.fixture
    def nfr_metadata(self):
        """Sample NFR task metadata"""
        return {
            "original_name": "Implement Performance Monitoring",
            "type": "nfr",
            "epic_id": "epic_nfr",
            "description": "Add comprehensive performance monitoring",
            "nfr_data": {
                "id": "nfr_performance",
                "name": "Performance Monitoring",
                "description": "Monitor application performance metrics",
            },
        }

    @pytest.fixture
    def prd_analysis(self):
        """Sample PRD analysis without matching NFR requirement"""
        return PRDAnalysis(
            functional_requirements=[
                {
                    "id": "feature_create_task",
                    "name": "Create Task",
                    "description": "Create new tasks",
                }
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
    async def test_nfr_task_converted_to_task_object(
        self, parser, nfr_metadata, prd_analysis, project_constraints
    ):
        """
        Test that NFR task metadata is properly converted to Task object.

        Regression test: NFR tasks don't match functional requirements,
        so they need special handling via metadata path.
        """
        # Arrange
        task_id = "nfr_task_performance"
        epic_id = "epic_nfr"

        # Store NFR metadata (simulating what _create_nfr_tasks does)
        parser._task_metadata = {task_id: nfr_metadata}

        # Mock AI description generation for NFR tasks
        parser.llm_client.analyze = AsyncMock(
            return_value="Enhanced: Add comprehensive performance monitoring"
        )

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
        assert result_task.name == "Implement Performance Monitoring"
        assert result_task.status == TaskStatus.TODO
        assert result_task.estimated_hours > 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_nfr_task_uses_ai_enhanced_description(
        self, parser, nfr_metadata, prd_analysis, project_constraints
    ):
        """Test that NFR tasks get AI-enhanced descriptions"""
        # Arrange
        task_id = "nfr_task_performance"
        parser._task_metadata = {task_id: nfr_metadata}

        # Mock AI enhancement
        enhanced_desc = "Enhanced: Monitor performance with detailed metrics"
        parser.llm_client.analyze = AsyncMock(return_value=enhanced_desc)

        # Act
        result_task = await parser._generate_detailed_task(
            task_id=task_id,
            epic_id="epic_nfr",
            analysis=prd_analysis,
            constraints=project_constraints,
            sequence=1,
        )

        # Assert
        assert enhanced_desc in result_task.description


class TestInfrastructureTaskGeneration:
    """Test suite for infrastructure task generation"""

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
                parser._get_learned_task_duration = Mock(return_value=8.0)

                return parser

    @pytest.fixture
    def infra_metadata(self):
        """Sample infrastructure task metadata"""
        return {
            "original_name": "Set up development environment",
            "type": "setup",
            "epic_id": "epic_infrastructure",
        }

    @pytest.fixture
    def prd_analysis(self):
        """Sample PRD analysis without matching infrastructure requirement"""
        return PRDAnalysis(
            functional_requirements=[
                {
                    "id": "feature_create_task",
                    "name": "Create Task",
                    "description": "Create new tasks",
                }
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
    async def test_infrastructure_task_converted_to_task_object(
        self, parser, infra_metadata, prd_analysis, project_constraints
    ):
        """
        Test infrastructure task metadata is converted to Task object.

        Regression test: Infrastructure tasks don't match functional
        requirements, so they need special handling via metadata path.
        """
        # Arrange
        task_id = "infra_setup"
        epic_id = "epic_infrastructure"

        # Store infrastructure metadata
        parser._task_metadata = {task_id: infra_metadata}

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
        assert result_task.name == "Set up development environment"
        assert result_task.status == TaskStatus.TODO
        assert result_task.estimated_hours > 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_infrastructure_task_with_no_description_gets_default(
        self, parser, infra_metadata, prd_analysis, project_constraints
    ):
        """Test infrastructure task without description gets default"""
        # Arrange
        task_id = "infra_ci_cd"
        # Create metadata without description
        metadata = {
            "original_name": "Configure CI/CD pipeline",
            "type": "infrastructure",
            "epic_id": "epic_infrastructure",
        }
        parser._task_metadata = {task_id: metadata}

        # Act
        result_task = await parser._generate_detailed_task(
            task_id=task_id,
            epic_id="epic_infrastructure",
            analysis=prd_analysis,
            constraints=project_constraints,
            sequence=1,
        )

        # Assert
        assert isinstance(result_task, Task)
        assert "Configure CI/CD pipeline" in result_task.description

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_task_without_requirement_or_metadata_raises_error(
        self, parser, prd_analysis, project_constraints
    ):
        """
        Test that task without requirement OR metadata raises AIProviderError.

        This is the true error case - task_id doesn't match any requirement
        AND there's no stored metadata.
        """
        from src.core.error_framework import AIProviderError

        # Arrange
        task_id = "unknown_task"
        epic_id = "epic_features"

        # No metadata stored
        parser._task_metadata = {}

        # Act & Assert
        with pytest.raises(AIProviderError) as exc_info:
            await parser._generate_detailed_task(
                task_id=task_id,
                epic_id=epic_id,
                analysis=prd_analysis,
                constraints=project_constraints,
                sequence=1,
            )

        # Verify it's an AIProviderError (the correct error type)
        assert isinstance(exc_info.value, AIProviderError)
