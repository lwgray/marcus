"""
Unit tests for task redundancy serialization in MCP tools.

Tests that task_redundancy results are properly serialized and
included in MCP tool responses.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.analysis.aggregator import TaskHistory
from src.analysis.analyzers.task_redundancy import (
    RedundantTaskPair,
    TaskRedundancyAnalysis,
)
from src.analysis.post_project_analyzer import PostProjectAnalysis
from src.marcus_mcp.tools.post_project_analysis import analyze_project


@pytest.mark.unit
@pytest.mark.asyncio
class TestTaskRedundancySerialization:
    """Test suite for task redundancy MCP serialization."""

    @pytest.fixture
    def mock_analysis_with_redundancy(self):
        """Create mock PostProjectAnalysis with task redundancy data."""
        redundancy = TaskRedundancyAnalysis(
            project_id="test-proj",
            redundant_pairs=[
                RedundantTaskPair(
                    task_1_id="task-100",
                    task_1_name="Set up authentication",
                    task_2_id="task-105",
                    task_2_name="Implement login system",
                    overlap_score=0.85,
                    evidence="Both tasks implemented same OAuth2 flow (task-100: 2025-11-01T10:00:00Z, task-105: 2025-11-01T14:00:00Z)",
                    time_wasted=3.2,
                ),
                RedundantTaskPair(
                    task_1_id="task-110",
                    task_1_name="Create database schema",
                    task_2_id="task-115",
                    task_2_name="Set up database tables",
                    overlap_score=0.92,
                    evidence="Duplicate work creating same tables",
                    time_wasted=2.5,
                ),
            ],
            redundancy_score=0.35,
            total_time_wasted=5.7,
            over_decomposition_detected=True,
            recommended_complexity="standard",
            raw_data={"total_tasks": 10, "quick_completions": 3},
            llm_interpretation="Project shows moderate redundancy, mainly due to over-decomposition",
            recommendations=[
                "Use 'standard' complexity instead of 'enterprise'",
                "Merge authentication tasks task-100 and task-105",
            ],
        )

        return PostProjectAnalysis(
            project_id="test-proj",
            analysis_timestamp=datetime(2025, 11, 14, 12, 0, tzinfo=timezone.utc),
            requirement_divergences=[],
            decision_impacts=[],
            instruction_quality_issues=[],
            failure_diagnoses=[],
            task_redundancy=redundancy,
            summary="Test analysis with redundancy",
            metadata={"tasks_analyzed": 10},
        )

    @pytest.fixture
    def mock_analysis_without_redundancy(self):
        """Create mock PostProjectAnalysis without task redundancy data."""
        return PostProjectAnalysis(
            project_id="test-proj",
            analysis_timestamp=datetime(2025, 11, 14, 12, 0, tzinfo=timezone.utc),
            requirement_divergences=[],
            decision_impacts=[],
            instruction_quality_issues=[],
            failure_diagnoses=[],
            task_redundancy=None,  # No redundancy analysis
            summary="Test analysis without redundancy",
            metadata={"tasks_analyzed": 5},
        )

    async def test_task_redundancy_included_in_response(
        self, mock_analysis_with_redundancy: PostProjectAnalysis
    ) -> None:
        """
        Test that task_redundancy is included in MCP response when available.

        This verifies the fix for task redundancy not being exposed via MCP.
        """
        # Arrange - Mock both the aggregator class AND the analyzer class
        mock_aggregator_instance = AsyncMock()
        mock_aggregator_instance.aggregate_project.return_value = Mock(
            tasks=[
                TaskHistory(
                    task_id="task-1",
                    name="Test",
                    description="Test",
                    status="completed",
                    estimated_hours=1.0,
                    actual_hours=1.0,
                    conversations=[],
                )
            ],
            decisions=[],
        )

        mock_analyzer_instance = AsyncMock()
        mock_analyzer_instance.analyze_project.return_value = (
            mock_analysis_with_redundancy
        )

        # Patch where classes are imported/used in the analyze_project function
        # ProjectHistoryAggregator is imported inside the function
        # PostProjectAnalyzer is imported at module level
        with patch(
            "src.analysis.aggregator.ProjectHistoryAggregator",
            return_value=mock_aggregator_instance,
        ):
            with patch(
                "src.marcus_mcp.tools.post_project_analysis.PostProjectAnalyzer",
                return_value=mock_analyzer_instance,
            ):
                # Act
                result = await analyze_project(
                    project_id="test-proj", scope=None, state=None
                )

        # Assert - response should include task_redundancy
        assert result["success"] is True
        assert (
            "task_redundancy" in result
        ), "MCP response should include task_redundancy when analysis contains it"

        # Verify redundancy data structure
        redundancy = result["task_redundancy"]
        assert redundancy["redundancy_score"] == 0.35
        assert redundancy["total_time_wasted"] == 5.7
        assert redundancy["over_decomposition_detected"] is True
        assert redundancy["recommended_complexity"] == "standard"

        # Verify redundant pairs
        assert len(redundancy["redundant_pairs"]) == 2

        pair1 = redundancy["redundant_pairs"][0]
        assert pair1["task_1_id"] == "task-100"
        assert pair1["task_1_name"] == "Set up authentication"
        assert pair1["task_2_id"] == "task-105"
        assert pair1["task_2_name"] == "Implement login system"
        assert pair1["overlap_score"] == 0.85
        assert "OAuth2 flow" in pair1["evidence"]
        assert pair1["time_wasted"] == 3.2

        # Verify recommendations
        assert len(redundancy["recommendations"]) == 2
        assert "standard" in redundancy["recommendations"][0]

    async def test_task_redundancy_omitted_when_none(
        self, mock_analysis_without_redundancy: PostProjectAnalysis
    ) -> None:
        """
        Test that task_redundancy is omitted when not available.
        """
        # Arrange - Mock both the aggregator class AND the analyzer class
        mock_aggregator_instance = AsyncMock()
        mock_aggregator_instance.aggregate_project.return_value = Mock(
            tasks=[
                TaskHistory(
                    task_id="task-1",
                    name="Test",
                    description="Test",
                    status="completed",
                    estimated_hours=1.0,
                    actual_hours=1.0,
                    conversations=[],
                )
            ],
            decisions=[],
        )

        mock_analyzer_instance = AsyncMock()
        mock_analyzer_instance.analyze_project.return_value = (
            mock_analysis_without_redundancy
        )

        # Patch where classes are imported/used in the analyze_project function
        # ProjectHistoryAggregator is imported inside the function
        # PostProjectAnalyzer is imported at module level
        with patch(
            "src.analysis.aggregator.ProjectHistoryAggregator",
            return_value=mock_aggregator_instance,
        ):
            with patch(
                "src.marcus_mcp.tools.post_project_analysis.PostProjectAnalyzer",
                return_value=mock_analyzer_instance,
            ):
                # Act
                result = await analyze_project(
                    project_id="test-proj", scope=None, state=None
                )

        # Assert - response should NOT include task_redundancy
        assert result["success"] is True
        assert (
            "task_redundancy" not in result
        ), "MCP response should not include task_redundancy when analysis doesn't have it"

    async def test_all_redundant_pair_fields_serialized(
        self, mock_analysis_with_redundancy: PostProjectAnalysis
    ) -> None:
        """
        Test that all RedundantTaskPair fields are properly serialized.
        """
        # Arrange - Mock both the aggregator class AND the analyzer class
        mock_aggregator_instance = AsyncMock()
        mock_aggregator_instance.aggregate_project.return_value = Mock(
            tasks=[
                TaskHistory(
                    task_id="task-1",
                    name="Test",
                    description="Test",
                    status="completed",
                    estimated_hours=1.0,
                    actual_hours=1.0,
                    conversations=[],
                )
            ],
            decisions=[],
        )

        mock_analyzer_instance = AsyncMock()
        mock_analyzer_instance.analyze_project.return_value = (
            mock_analysis_with_redundancy
        )

        # Patch where classes are imported/used in the analyze_project function
        # ProjectHistoryAggregator is imported inside the function
        # PostProjectAnalyzer is imported at module level
        with patch(
            "src.analysis.aggregator.ProjectHistoryAggregator",
            return_value=mock_aggregator_instance,
        ):
            with patch(
                "src.marcus_mcp.tools.post_project_analysis.PostProjectAnalyzer",
                return_value=mock_analyzer_instance,
            ):
                # Act
                result = await analyze_project(
                    project_id="test-proj", scope=None, state=None
                )

        # Assert - verify all RedundantTaskPair fields are present
        pair = result["task_redundancy"]["redundant_pairs"][0]

        required_fields = {
            "task_1_id",
            "task_1_name",
            "task_2_id",
            "task_2_name",
            "overlap_score",
            "evidence",
            "time_wasted",
        }

        assert set(pair.keys()) == required_fields, (
            f"Redundant pair should have exactly these fields: {required_fields}. "
            f"Got: {set(pair.keys())}"
        )

    async def test_task_redundancy_with_empty_pairs(self) -> None:
        """
        Test serialization when redundancy analysis found no redundant pairs.
        """
        # Arrange - Create analysis with no redundant pairs
        redundancy = TaskRedundancyAnalysis(
            project_id="test-proj",
            redundant_pairs=[],  # No redundant pairs found
            redundancy_score=0.05,
            total_time_wasted=0.0,
            over_decomposition_detected=False,
            recommended_complexity="enterprise",
            raw_data={"total_tasks": 5},
            llm_interpretation="No redundancy detected - efficient task breakdown",
            recommendations=["Continue using enterprise mode for complex projects"],
        )

        analysis = PostProjectAnalysis(
            project_id="test-proj",
            analysis_timestamp=datetime(2025, 11, 14, 12, 0, tzinfo=timezone.utc),
            requirement_divergences=[],
            decision_impacts=[],
            instruction_quality_issues=[],
            failure_diagnoses=[],
            task_redundancy=redundancy,
            summary="Efficient project - no redundancy",
            metadata={"tasks_analyzed": 5},
        )

        # Mock both the aggregator class AND the analyzer class
        mock_aggregator_instance = AsyncMock()
        mock_aggregator_instance.aggregate_project.return_value = Mock(
            tasks=[
                TaskHistory(
                    task_id="task-1",
                    name="Test",
                    description="Test",
                    status="completed",
                    estimated_hours=1.0,
                    actual_hours=1.0,
                    conversations=[],
                )
            ],
            decisions=[],
        )

        mock_analyzer_instance = AsyncMock()
        mock_analyzer_instance.analyze_project.return_value = analysis

        # Patch where classes are imported/used in the analyze_project function
        # ProjectHistoryAggregator is imported inside the function
        # PostProjectAnalyzer is imported at module level
        with patch(
            "src.analysis.aggregator.ProjectHistoryAggregator",
            return_value=mock_aggregator_instance,
        ):
            with patch(
                "src.marcus_mcp.tools.post_project_analysis.PostProjectAnalyzer",
                return_value=mock_analyzer_instance,
            ):
                # Act
                result = await analyze_project(
                    project_id="test-proj", scope=None, state=None
                )

        # Assert
        assert result["success"] is True
        assert "task_redundancy" in result

        redundancy_data = result["task_redundancy"]
        assert redundancy_data["redundancy_score"] == 0.05
        assert redundancy_data["total_time_wasted"] == 0.0
        assert redundancy_data["redundant_pairs"] == []  # Empty list, not None
        assert redundancy_data["recommended_complexity"] == "enterprise"
