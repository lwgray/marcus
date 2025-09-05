"""
Unit tests for Intelligent Task Enricher private helper methods.

This module tests the internal helper methods of the IntelligentTaskEnricher
including semantic analysis, description generation, label generation,
and dependency suggestion logic.

Notes
-----
All external AI provider calls are mocked to ensure fast, reliable tests that
don't depend on external services or consume API quotas.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.ai.enrichment.intelligent_enricher import (
    IntelligentTaskEnricher,
    ProjectContext,
)
from src.ai.providers.base_provider import EffortEstimate, SemanticAnalysis
from src.core.models import Priority, Task, TaskStatus


class TestIntelligentTaskEnricherPrivateMethods:
    """Test suite for private helper methods"""

    @pytest.fixture
    def enricher(self):
        """Create enricher instance with mocked LLM client"""
        with patch("src.ai.enrichment.intelligent_enricher.LLMAbstraction") as mock_llm:
            enricher = IntelligentTaskEnricher()
            enricher.llm_client = mock_llm.return_value
            return enricher

    @pytest.fixture
    def sample_task(self):
        """Create sample task for testing"""
        return Task(
            id="task-123",
            name="Implement search feature",
            description="Add search functionality",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=5.0,
            labels=["frontend", "feature"],
        )

    @pytest.fixture
    def sample_project_context(self):
        """Create sample project context for testing"""
        return ProjectContext(
            project_type="web_application",
            tech_stack=["python", "react"],
            team_size=3,
            existing_tasks=[],
            project_standards={},
            historical_data=[],
            quality_requirements={"testing_required": True},
        )

    async def test_get_semantic_analysis_context_building(
        self, enricher, sample_task, sample_project_context
    ):
        """Test semantic analysis context building"""
        # Add existing tasks to context
        existing_task = Task(
            id="task-456",
            name="Database setup",
            description="Set up database",
            status=TaskStatus.DONE,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=4.0,
            labels=["backend"],
        )
        sample_project_context.existing_tasks = [existing_task]

        # Mock the LLM client response
        mock_analysis = SemanticAnalysis(
            task_intent="implement search functionality",
            semantic_dependencies=[],
            risk_factors=[],
            suggestions=[],
            confidence=0.8,
            reasoning="Search feature analysis",
            risk_assessment={},
        )
        enricher.llm_client.analyze_task_semantics = AsyncMock(
            return_value=mock_analysis
        )

        result = await enricher._get_semantic_analysis(
            sample_task, sample_project_context
        )

        # Verify context was built correctly
        enricher.llm_client.analyze_task_semantics.assert_called_once()
        call_args = enricher.llm_client.analyze_task_semantics.call_args
        task_arg, context_arg = call_args[0]

        assert task_arg == sample_task
        assert context_arg["project_type"] == "web_application"
        assert context_arg["tech_stack"] == ["python", "react"]
        assert context_arg["team_size"] == 3
        assert len(context_arg["existing_tasks"]) == 1
        assert context_arg["existing_tasks"][0]["name"] == "Database setup"
        assert context_arg["existing_tasks"][0]["description"] == "Set up database"

        assert result == mock_analysis

    async def test_generate_enhanced_description_success(
        self, enricher, sample_task, sample_project_context
    ):
        """Test enhanced description generation success"""
        mock_analysis = SemanticAnalysis(
            task_intent="implement comprehensive search",
            semantic_dependencies=[],
            risk_factors=[],
            suggestions=[],
            confidence=0.8,
            reasoning="Search analysis",
            risk_assessment={},
        )

        enhanced_desc = "Enhanced search functionality with filters and sorting"
        enricher.llm_client.generate_enhanced_description = AsyncMock(
            return_value=enhanced_desc
        )

        result = await enricher._generate_enhanced_description(
            sample_task, sample_project_context, mock_analysis
        )

        assert result == enhanced_desc

        # Verify context was built correctly
        enricher.llm_client.generate_enhanced_description.assert_called_once()
        call_args = enricher.llm_client.generate_enhanced_description.call_args
        task_arg, context_arg = call_args[0]

        assert task_arg == sample_task
        assert context_arg["project_type"] == "web_application"
        assert context_arg["tech_stack"] == ["python", "react"]
        assert context_arg["quality_standards"] == {"testing_required": True}
        assert context_arg["semantic_intent"] == "implement comprehensive search"

    async def test_generate_enhanced_description_failure_fallback(
        self, enricher, sample_task, sample_project_context
    ):
        """Test enhanced description generation with failure fallback"""
        mock_analysis = SemanticAnalysis(
            task_intent="implement search",
            semantic_dependencies=[],
            risk_factors=[],
            suggestions=[],
            confidence=0.8,
            reasoning="Analysis",
            risk_assessment={},
        )

        enricher.llm_client.generate_enhanced_description = AsyncMock(
            side_effect=Exception("AI failed")
        )

        result = await enricher._generate_enhanced_description(
            sample_task, sample_project_context, mock_analysis
        )

        # Should fallback to original description
        assert result == sample_task.description

    async def test_generate_enhanced_description_no_description_fallback(
        self, enricher, sample_project_context
    ):
        """Test enhanced description generation when task has no description"""
        task_without_desc = Task(
            id="task-123",
            name="Task name only",
            description=None,
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=5.0,
            labels=[],
        )

        mock_analysis = SemanticAnalysis(
            task_intent="implement feature",
            semantic_dependencies=[],
            risk_factors=[],
            suggestions=[],
            confidence=0.8,
            reasoning="Analysis",
            risk_assessment={},
        )

        enricher.llm_client.generate_enhanced_description = AsyncMock(
            side_effect=Exception("AI failed")
        )

        result = await enricher._generate_enhanced_description(
            task_without_desc, sample_project_context, mock_analysis
        )

        # Should fallback to task name
        assert result == task_without_desc.name

    async def test_generate_enhanced_description_truncation(
        self, enricher, sample_task, sample_project_context
    ):
        """Test enhanced description truncation for long descriptions"""
        mock_analysis = SemanticAnalysis(
            task_intent="implement search",
            semantic_dependencies=[],
            risk_factors=[],
            suggestions=[],
            confidence=0.8,
            reasoning="Analysis",
            risk_assessment={},
        )

        # Generate description longer than max length
        long_description = "Very long description " * 100
        enricher.llm_client.generate_enhanced_description = AsyncMock(
            return_value=long_description
        )

        result = await enricher._generate_enhanced_description(
            sample_task, sample_project_context, mock_analysis
        )

        # Should be truncated
        assert len(result) <= enricher.max_description_length + 3  # +3 for "..."
        assert result.endswith("...")

    async def test_generate_intelligent_labels_bugfix_detection(
        self, enricher, sample_project_context
    ):
        """Test intelligent label generation for bugfix tasks"""
        bug_task = Task(
            id="task-123",
            name="Fix login bug",
            description="Fix issue with login",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=2.0,
            labels=[],
        )

        mock_analysis = SemanticAnalysis(
            task_intent="fix authentication bug in login system",
            semantic_dependencies=[],
            risk_factors=["critical system impact"],
            suggestions=[],
            confidence=0.9,
            reasoning="Bug fix analysis",
            risk_assessment={},
        )

        result = await enricher._generate_intelligent_labels(
            bug_task, sample_project_context, mock_analysis
        )

        # Should detect bugfix type
        assert "bugfix" in result
        assert "high" in result  # From priority
        assert "simple" in result  # From single risk factor

    async def test_generate_intelligent_labels_test_detection(
        self, enricher, sample_project_context
    ):
        """Test intelligent label generation for test tasks"""
        test_task = Task(
            id="task-123",
            name="Test user authentication",
            description="Write tests for auth",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=3.0,
            labels=[],
        )

        mock_analysis = SemanticAnalysis(
            task_intent="test and verify authentication functionality",
            semantic_dependencies=[],
            risk_factors=["test coverage", "edge cases"],
            suggestions=[],
            confidence=0.8,
            reasoning="Test analysis",
            risk_assessment={},
        )

        result = await enricher._generate_intelligent_labels(
            test_task, sample_project_context, mock_analysis
        )

        # Should detect test type
        assert "test" in result
        assert "medium" in result  # From priority
        assert "moderate" in result  # From two risk factors

    async def test_generate_intelligent_labels_documentation_detection(
        self, enricher, sample_project_context
    ):
        """Test intelligent label generation for documentation tasks"""
        doc_task = Task(
            id="task-123",
            name="Document API endpoints",
            description="Create API documentation",
            status=TaskStatus.TODO,
            priority=Priority.LOW,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=4.0,
            labels=[],
        )

        mock_analysis = SemanticAnalysis(
            task_intent="document api endpoints and usage examples",
            semantic_dependencies=[],
            risk_factors=[],
            suggestions=[],
            confidence=0.7,
            reasoning="Documentation analysis",
            risk_assessment={},
        )

        result = await enricher._generate_intelligent_labels(
            doc_task, sample_project_context, mock_analysis
        )

        # Should detect documentation type
        assert "documentation" in result
        assert "api" in result  # From task content
        assert "low" in result  # From priority
        # Note: complexity assessment only happens if there are risk factors
        # With empty risk factors, no complexity label is added

    async def test_generate_intelligent_labels_complexity_assessment(
        self, enricher, sample_project_context
    ):
        """Test complexity assessment in label generation"""
        complex_task = Task(
            id="task-123",
            name="Implement complex feature",
            description="Complex implementation",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=20.0,
            labels=[],
        )

        mock_analysis = SemanticAnalysis(
            task_intent="implement complex feature with multiple components",
            semantic_dependencies=[],
            risk_factors=[
                "technical complexity",
                "integration challenges",
                "performance concerns",
            ],
            suggestions=[],
            confidence=0.6,
            reasoning="Complex analysis",
            risk_assessment={},
        )

        result = await enricher._generate_intelligent_labels(
            complex_task, sample_project_context, mock_analysis
        )

        # Should assess as complex
        assert "complex" in result  # From multiple risk factors
        assert "feature" in result  # Default type
        assert "high" in result  # From priority

    async def test_generate_intelligent_labels_refactor_detection(
        self, enricher, sample_project_context
    ):
        """Test intelligent label generation for refactor tasks"""
        refactor_task = Task(
            id="task-123",
            name="Refactor authentication module",
            description="Cleanup authentication code",
            status=TaskStatus.TODO,
            priority=Priority.URGENT,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=6.0,
            labels=[],
        )

        mock_analysis = SemanticAnalysis(
            task_intent="refactor and cleanup authentication module",
            semantic_dependencies=[],
            risk_factors=["code complexity"],
            suggestions=[],
            confidence=0.8,
            reasoning="Refactor analysis",
            risk_assessment={},
        )

        result = await enricher._generate_intelligent_labels(
            refactor_task, sample_project_context, mock_analysis
        )

        # Should detect refactor type
        assert "refactor" in result
        assert "urgent" in result  # From URGENT priority
        assert "simple" in result  # From single risk factor

    async def test_estimate_effort_with_ai_success(
        self, enricher, sample_task, sample_project_context
    ):
        """Test AI effort estimation success"""
        mock_analysis = SemanticAnalysis(
            task_intent="implement search",
            semantic_dependencies=[],
            risk_factors=["complexity", "testing"],
            suggestions=[],
            confidence=0.8,
            reasoning="Analysis",
            risk_assessment={},
        )

        mock_estimate = EffortEstimate(
            estimated_hours=8.0,
            confidence=0.75,
            factors=["complexity", "testing requirements"],
            similar_tasks=["previous search", "filtering feature"],
            risk_multiplier=1.1,
        )

        enricher.llm_client.estimate_effort_intelligently = AsyncMock(
            return_value=mock_estimate
        )

        result = await enricher._estimate_effort_with_ai(
            sample_task, sample_project_context, mock_analysis
        )

        assert result == mock_estimate

        # Verify context was built correctly
        enricher.llm_client.estimate_effort_intelligently.assert_called_once()
        call_args = enricher.llm_client.estimate_effort_intelligently.call_args
        task_arg, context_arg = call_args[0]

        assert task_arg == sample_task
        assert context_arg["project_type"] == "web_application"
        assert context_arg["tech_stack"] == ["python", "react"]
        assert context_arg["historical_data"] == []
        assert context_arg["semantic_analysis"]["intent"] == "implement search"
        assert context_arg["semantic_analysis"]["risk_factors"] == [
            "complexity",
            "testing",
        ]
        assert (
            context_arg["semantic_analysis"]["complexity"] == 2
        )  # Number of risk factors

    async def test_estimate_effort_with_ai_failure(
        self, enricher, sample_task, sample_project_context
    ):
        """Test AI effort estimation failure"""
        mock_analysis = SemanticAnalysis(
            task_intent="implement search",
            semantic_dependencies=[],
            risk_factors=[],
            suggestions=[],
            confidence=0.8,
            reasoning="Analysis",
            risk_assessment={},
        )

        enricher.llm_client.estimate_effort_intelligently = AsyncMock(
            side_effect=Exception("AI failed")
        )

        result = await enricher._estimate_effort_with_ai(
            sample_task, sample_project_context, mock_analysis
        )

        # Should return None on failure
        assert result is None

    async def test_generate_acceptance_criteria_basic(
        self, enricher, sample_task, sample_project_context
    ):
        """Test basic acceptance criteria generation"""
        mock_analysis = SemanticAnalysis(
            task_intent="implement basic feature",
            semantic_dependencies=[],
            risk_factors=[],
            suggestions=[],
            confidence=0.8,
            reasoning="Analysis",
            risk_assessment={},
        )

        result = await enricher._generate_acceptance_criteria(
            sample_task, sample_project_context, mock_analysis
        )

        # Should generate basic criteria
        assert len(result) > 0
        assert len(result) <= enricher.max_acceptance_criteria

        # Should include completion criteria
        assert any("functionally complete" in criteria.lower() for criteria in result)

        # Should include quality criteria based on project requirements
        assert any("unit tests" in criteria.lower() for criteria in result)

    async def test_generate_acceptance_criteria_api_specific(
        self, enricher, sample_task, sample_project_context
    ):
        """Test API-specific acceptance criteria generation"""
        mock_analysis = SemanticAnalysis(
            task_intent="implement api endpoint for user management",
            semantic_dependencies=[],
            risk_factors=[],
            suggestions=[],
            confidence=0.8,
            reasoning="API analysis",
            risk_assessment={},
        )

        result = await enricher._generate_acceptance_criteria(
            sample_task, sample_project_context, mock_analysis
        )

        # Should include API-specific criteria
        assert any("api endpoints" in criteria.lower() for criteria in result)
        assert any("error handling" in criteria.lower() for criteria in result)

    async def test_generate_acceptance_criteria_ui_specific(
        self, enricher, sample_task, sample_project_context
    ):
        """Test UI-specific acceptance criteria generation"""
        mock_analysis = SemanticAnalysis(
            task_intent="implement user interface for dashboard",
            semantic_dependencies=[],
            risk_factors=[],
            suggestions=[],
            confidence=0.8,
            reasoning="UI analysis",
            risk_assessment={},
        )

        result = await enricher._generate_acceptance_criteria(
            sample_task, sample_project_context, mock_analysis
        )

        # Should include UI-specific criteria
        assert any("responsive" in criteria.lower() for criteria in result)
        assert any("user interactions" in criteria.lower() for criteria in result)

    async def test_generate_acceptance_criteria_test_specific(
        self, enricher, sample_task, sample_project_context
    ):
        """Test test-specific acceptance criteria generation"""
        mock_analysis = SemanticAnalysis(
            task_intent="test user authentication functionality",
            semantic_dependencies=[],
            risk_factors=[],
            suggestions=[],
            confidence=0.8,
            reasoning="Test analysis",
            risk_assessment={},
        )

        result = await enricher._generate_acceptance_criteria(
            sample_task, sample_project_context, mock_analysis
        )

        # Should include test-specific criteria
        assert any("test cases pass" in criteria.lower() for criteria in result)
        assert any("code coverage" in criteria.lower() for criteria in result)

    async def test_suggest_dependencies_matching(
        self, enricher, sample_task, sample_project_context
    ):
        """Test dependency suggestion with matching tasks"""
        # Add existing tasks that should match semantic dependencies
        existing_tasks = [
            Task(
                id="task-456",
                name="Database setup",
                description="Set up database",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
                labels=[],
            ),
            Task(
                id="task-789",
                name="User model creation",
                description="Create user model",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=3.0,
                labels=[],
            ),
        ]
        sample_project_context.existing_tasks = existing_tasks

        mock_analysis = SemanticAnalysis(
            task_intent="implement search",
            semantic_dependencies=["database setup", "user model"],
            risk_factors=[],
            suggestions=[],
            confidence=0.8,
            reasoning="Analysis",
            risk_assessment={},
        )

        result = await enricher._suggest_dependencies(
            sample_task, sample_project_context, mock_analysis
        )

        # Should suggest matching tasks
        assert "task-456" in result  # Matches "database setup"
        assert "task-789" in result  # Matches "user model"

    async def test_suggest_dependencies_no_matches(
        self, enricher, sample_task, sample_project_context
    ):
        """Test dependency suggestion with no matching tasks"""
        mock_analysis = SemanticAnalysis(
            task_intent="implement search",
            semantic_dependencies=["nonexistent dependency"],
            risk_factors=[],
            suggestions=[],
            confidence=0.8,
            reasoning="Analysis",
            risk_assessment={},
        )

        result = await enricher._suggest_dependencies(
            sample_task, sample_project_context, mock_analysis
        )

        # Should return empty list
        assert result == []

    def test_track_changes_description_change(self, enricher):
        """Test change tracking for description changes"""
        original_task = Task(
            id="task-123",
            name="Task name",
            description="Original description",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=5.0,
            labels=["original"],
        )

        enhanced_description = "Enhanced description with more details"
        suggested_labels = ["original", "enhanced", "ai-generated"]
        estimated_hours = 8.0
        acceptance_criteria = ["Criteria 1", "Criteria 2"]

        result = enricher._track_changes(
            original_task,
            enhanced_description,
            suggested_labels,
            estimated_hours,
            acceptance_criteria,
        )

        # Should track description change
        assert "description" in result
        assert result["description"]["original"] == "Original description"
        assert result["description"]["enhanced"] == enhanced_description
        assert result["description"]["length_change"] == len(
            enhanced_description
        ) - len("Original description")

        # Should track label changes
        assert "labels" in result
        assert set(result["labels"]["added"]) == {"enhanced", "ai-generated"}
        assert result["labels"]["total_before"] == 1
        assert result["labels"]["total_after"] == 3

        # Should track effort estimate change
        assert "effort_estimate" in result
        assert result["effort_estimate"]["original"] == 5.0
        assert result["effort_estimate"]["ai_estimate"] == 8.0

        # Should track acceptance criteria
        assert "acceptance_criteria" in result
        assert result["acceptance_criteria"]["count"] == 2
        assert result["acceptance_criteria"]["criteria"] == acceptance_criteria

    def test_track_changes_no_changes(self, enricher):
        """Test change tracking when no changes are made"""
        original_task = Task(
            id="task-123",
            name="Task name",
            description="Same description",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=5.0,
            labels=["original"],
        )

        # Same values as original
        enhanced_description = "Same description"
        suggested_labels = ["original"]
        estimated_hours = 5.0
        acceptance_criteria = []

        result = enricher._track_changes(
            original_task,
            enhanced_description,
            suggested_labels,
            estimated_hours,
            acceptance_criteria,
        )

        # Should not track any changes
        assert "description" not in result
        assert "labels" not in result
        assert "effort_estimate" not in result
        assert "acceptance_criteria" not in result

    def test_create_fallback_result(self, enricher):
        """Test fallback result creation"""
        task = Task(
            id="task-123",
            name="Failed task",
            description="Task description",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=5.0,
            labels=["original"],
        )

        result = enricher._create_fallback_result(task)

        # Should create minimal result
        assert result.original_task == task
        assert result.enhanced_description == task.description
        assert result.suggested_labels == task.labels
        assert result.estimated_hours == task.estimated_hours
        assert result.suggested_dependencies == []
        assert result.acceptance_criteria == []
        assert result.risk_factors == ["ai_enrichment_failed"]
        assert result.confidence == 0.1
        assert result.reasoning == "AI enrichment failed, using original task data"
        assert result.changes_made == {}
        assert isinstance(result.enhancement_timestamp, datetime)
