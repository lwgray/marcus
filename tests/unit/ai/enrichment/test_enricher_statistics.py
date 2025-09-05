"""
Unit tests for Intelligent Task Enricher statistics functionality.

This module tests the enrichment statistics and metrics collection capabilities
of the IntelligentTaskEnricher, ensuring proper calculation of enhancement
rates, confidence metrics, and aggregated data.

Notes
-----
All external AI provider calls are mocked to ensure fast, reliable tests that
don't depend on external services or consume API quotas.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from src.ai.enrichment.intelligent_enricher import (
    EnhancementResult,
    IntelligentTaskEnricher,
)
from src.core.models import Priority, Task, TaskStatus


class TestIntelligentTaskEnricherStatistics:
    """Test suite for enrichment statistics functionality"""

    @pytest.fixture
    def enricher(self):
        """Create enricher instance with mocked LLM client"""
        with patch("src.ai.enrichment.intelligent_enricher.LLMAbstraction") as mock_llm:
            enricher = IntelligentTaskEnricher()
            enricher.llm_client = mock_llm.return_value
            return enricher

    @pytest.fixture
    def sample_enhancement_results(self):
        """Create sample enhancement results for statistics testing"""
        task1 = Task(
            id="task-1",
            name="Task 1",
            description="Desc 1",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=5.0,
            labels=[],
        )

        task2 = Task(
            id="task-2",
            name="Task 2",
            description="Desc 2",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=3.0,
            labels=[],
        )

        return [
            EnhancementResult(
                original_task=task1,
                enhanced_description="Enhanced description 1",
                suggested_labels=["label1", "label2"],
                estimated_hours=8.0,
                suggested_dependencies=[],
                acceptance_criteria=["Criteria 1", "Criteria 2"],
                risk_factors=[],
                confidence=0.9,
                reasoning="High confidence analysis",
                changes_made={
                    "description": {
                        "original": "Desc 1",
                        "enhanced": "Enhanced description 1",
                    },
                    "labels": {
                        "added": ["label1", "label2"],
                        "total_before": 0,
                        "total_after": 2,
                    },
                    "effort_estimate": {"original": 5.0, "ai_estimate": 8.0},
                    "acceptance_criteria": {
                        "count": 2,
                        "criteria": ["Criteria 1", "Criteria 2"],
                    },
                },
                enhancement_timestamp=datetime.now(),
            ),
            EnhancementResult(
                original_task=task2,
                enhanced_description="Enhanced description 2",
                suggested_labels=["label3"],
                estimated_hours=3.0,
                suggested_dependencies=[],
                acceptance_criteria=["Criteria 3"],
                risk_factors=[],
                confidence=0.7,
                reasoning="Medium confidence analysis",
                changes_made={
                    "description": {
                        "original": "Desc 2",
                        "enhanced": "Enhanced description 2",
                    },
                    "labels": {
                        "added": ["label3"],
                        "total_before": 0,
                        "total_after": 1,
                    },
                    "acceptance_criteria": {"count": 1, "criteria": ["Criteria 3"]},
                },
                enhancement_timestamp=datetime.now(),
            ),
        ]

    async def test_get_enrichment_statistics_comprehensive(
        self, enricher, sample_enhancement_results
    ):
        """Test comprehensive enrichment statistics generation"""
        stats = await enricher.get_enrichment_statistics(sample_enhancement_results)

        # Basic counts
        assert stats["total_tasks"] == 2

        # Enhancement rates
        assert stats["enhancement_rates"]["descriptions_enhanced"] == 1.0  # 2/2
        assert stats["enhancement_rates"]["labels_added"] == 1.0  # 2/2
        assert (
            stats["enhancement_rates"]["estimates_added"] == 0.5
        )  # 1/2 (only first task had estimate change)
        assert stats["enhancement_rates"]["criteria_added"] == 1.0  # 2/2

        # Confidence metrics
        assert stats["average_confidence"] == 0.8  # (0.9 + 0.7) / 2
        assert stats["high_confidence_count"] == 1  # Only first task > 0.8

        # Aggregated metrics
        assert stats["total_labels_added"] == 3  # 2 + 1
        assert stats["total_criteria_added"] == 3  # 2 + 1

    async def test_get_enrichment_statistics_empty_results(self, enricher):
        """Test statistics generation with empty results"""
        stats = await enricher.get_enrichment_statistics([])

        assert stats == {}

    async def test_get_enrichment_statistics_no_changes(self, enricher):
        """Test statistics generation with results that have no changes"""
        task = Task(
            id="task-1",
            name="Task 1",
            description="Desc 1",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=5.0,
            labels=[],
        )

        no_change_result = EnhancementResult(
            original_task=task,
            enhanced_description="Desc 1",  # Same as original
            suggested_labels=[],
            estimated_hours=5.0,  # Same as original
            suggested_dependencies=[],
            acceptance_criteria=[],
            risk_factors=[],
            confidence=0.5,
            reasoning="No changes needed",
            changes_made={},  # No changes
            enhancement_timestamp=datetime.now(),
        )

        stats = await enricher.get_enrichment_statistics([no_change_result])

        # Should show zero enhancement rates
        assert stats["total_tasks"] == 1
        assert stats["enhancement_rates"]["descriptions_enhanced"] == 0.0
        assert stats["enhancement_rates"]["labels_added"] == 0.0
        assert stats["enhancement_rates"]["estimates_added"] == 0.0
        assert stats["enhancement_rates"]["criteria_added"] == 0.0
        assert stats["average_confidence"] == 0.5
        assert stats["high_confidence_count"] == 0
        assert stats["total_labels_added"] == 0
        assert stats["total_criteria_added"] == 0

    async def test_get_enrichment_statistics_mixed_results(self, enricher):
        """Test statistics generation with mixed success/failure results"""
        task1 = Task(
            id="task-1",
            name="Task 1",
            description="Desc 1",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=5.0,
            labels=[],
        )

        task2 = Task(
            id="task-2",
            name="Task 2",
            description="Desc 2",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=3.0,
            labels=[],
        )

        success_result = EnhancementResult(
            original_task=task1,
            enhanced_description="Enhanced description",
            suggested_labels=["label1"],
            estimated_hours=8.0,
            suggested_dependencies=[],
            acceptance_criteria=["Criteria 1"],
            risk_factors=[],
            confidence=0.9,
            reasoning="Success",
            changes_made={
                "description": {
                    "original": "Desc 1",
                    "enhanced": "Enhanced description",
                },
                "labels": {"added": ["label1"], "total_before": 0, "total_after": 1},
                "effort_estimate": {"original": 5.0, "ai_estimate": 8.0},
                "acceptance_criteria": {"count": 1, "criteria": ["Criteria 1"]},
            },
            enhancement_timestamp=datetime.now(),
        )

        failure_result = EnhancementResult(
            original_task=task2,
            enhanced_description="Desc 2",  # No change
            suggested_labels=[],
            estimated_hours=3.0,  # No change
            suggested_dependencies=[],
            acceptance_criteria=[],
            risk_factors=["ai_enrichment_failed"],
            confidence=0.1,
            reasoning="AI enrichment failed",
            changes_made={},  # No changes
            enhancement_timestamp=datetime.now(),
        )

        results = [success_result, failure_result]
        stats = await enricher.get_enrichment_statistics(results)

        # Should show 50% success rates
        assert stats["total_tasks"] == 2
        assert stats["enhancement_rates"]["descriptions_enhanced"] == 0.5  # 1/2
        assert stats["enhancement_rates"]["labels_added"] == 0.5  # 1/2
        assert stats["enhancement_rates"]["estimates_added"] == 0.5  # 1/2
        assert stats["enhancement_rates"]["criteria_added"] == 0.5  # 1/2
        assert stats["average_confidence"] == 0.5  # (0.9 + 0.1) / 2
        assert stats["high_confidence_count"] == 1  # Only success result
        assert stats["total_labels_added"] == 1
        assert stats["total_criteria_added"] == 1
