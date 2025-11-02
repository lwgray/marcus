"""
Unit tests for Intelligent Task Enricher integration scenarios.

This module tests the integration between different components of the
IntelligentTaskEnricher, ensuring consistency across methods and
proper error handling throughout the system.

Notes
-----
These are integration tests that verify component interaction patterns
and system-wide consistency, with mocked external dependencies.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from src.ai.enrichment.intelligent_enricher import (
    EnhancementResult,
    IntelligentTaskEnricher,
    ProjectContext,
)
from src.core.models import Priority, Task, TaskStatus


@pytest.mark.unit
class TestIntelligentTaskEnricherIntegration:
    """Integration tests for IntelligentTaskEnricher components"""

    @pytest.fixture
    def enricher(self):
        """Create enricher instance with mocked LLM client"""
        with patch("src.ai.enrichment.intelligent_enricher.LLMAbstraction") as mock_llm:
            enricher = IntelligentTaskEnricher()
            enricher.llm_client = mock_llm.return_value
            return enricher

    def test_standard_label_categories_consistency(self, enricher):
        """Test all label generation methods use consistent categories"""
        # Test that all expected categories are present
        expected_categories = ["component", "type", "priority", "complexity", "phase"]

        for category in expected_categories:
            assert category in enricher.standard_labels
            assert isinstance(enricher.standard_labels[category], list)
            assert len(enricher.standard_labels[category]) > 0

    def test_configuration_limits_consistency(self, enricher):
        """Test configuration limits are reasonable and consistent"""
        # Test that limits are reasonable
        assert enricher.enhancement_confidence_threshold > 0.0
        assert enricher.enhancement_confidence_threshold <= 1.0
        assert enricher.max_description_length > 0
        assert enricher.max_acceptance_criteria > 0

        # Test that limits are consistent with functionality
        assert (
            enricher.enhancement_confidence_threshold < 1.0
        )  # Should allow some uncertainty
        assert (
            enricher.max_description_length >= 100
        )  # Should allow meaningful descriptions
        assert (
            enricher.max_acceptance_criteria >= 3
        )  # Should allow reasonable criteria count

    async def test_error_handling_consistency(self, enricher):
        """Test error handling is consistent across all methods"""
        task = Task(
            id="task-123",
            name="Test task",
            description="Test description",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=5.0,
            labels=[],
        )

        context = ProjectContext(
            project_type="test",
            tech_stack=["python"],
            team_size=1,
            existing_tasks=[],
            project_standards={},
            historical_data=[],
            quality_requirements={},
        )

        # Test that fallback methods don't raise exceptions
        fallback_result = enricher._create_fallback_result(task)
        assert isinstance(fallback_result, EnhancementResult)
        assert fallback_result.confidence == 0.1
        assert "ai_enrichment_failed" in fallback_result.risk_factors

        # Test change tracking with None values
        changes = enricher._track_changes(task, task.description, task.labels, None, [])
        assert isinstance(changes, dict)

    def test_data_structure_compatibility(self, enricher):
        """Test that all data structures are compatible with expected interfaces"""
        # Test that enricher accepts all expected Task fields
        task = Task(
            id="task-123",
            name="Test task",
            description="Test description",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to="user1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
            estimated_hours=5.0,
            labels=["existing", "labels"],
        )

        # Test that enricher accepts all expected ProjectContext fields
        context = ProjectContext(
            project_type="web_application",
            tech_stack=["python", "react"],
            team_size=5,
            existing_tasks=[task],
            project_standards={"style": "pep8"},
            historical_data=[{"type": "feature", "hours": 8}],
            quality_requirements={"testing": True},
        )

        # Test that fallback result has all required fields
        fallback_result = enricher._create_fallback_result(task)
        required_fields = [
            "original_task",
            "enhanced_description",
            "suggested_labels",
            "estimated_hours",
            "suggested_dependencies",
            "acceptance_criteria",
            "risk_factors",
            "confidence",
            "reasoning",
            "changes_made",
            "enhancement_timestamp",
        ]

        for field in required_fields:
            assert hasattr(fallback_result, field)
