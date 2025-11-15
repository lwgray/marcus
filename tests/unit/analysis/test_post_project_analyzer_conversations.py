"""
Unit tests for PostProjectAnalyzer conversation extraction.

Tests that conversations are properly extracted from task histories
and passed to the task redundancy analyzer.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.analysis.aggregator import Message, TaskHistory
from src.analysis.analyzers.task_redundancy import TaskRedundancyAnalysis
from src.analysis.post_project_analyzer import (
    AnalysisScope,
    PostProjectAnalyzer,
)
from src.core.project_history import Decision


@pytest.mark.unit
@pytest.mark.asyncio
class TestConversationExtraction:
    """Test suite for conversation extraction in PostProjectAnalyzer."""

    @pytest.fixture
    def tasks_with_conversations(self):
        """Create task histories with conversation data."""
        return [
            TaskHistory(
                task_id="task-1",
                name="Task 1",
                description="First task",
                status="completed",
                estimated_hours=2.0,
                actual_hours=2.1,
                conversations=[
                    Message(
                        timestamp=datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc),
                        direction="from_pm",
                        agent_id="agent-1",
                        content="Please implement authentication",
                        metadata={"task_id": "task-1"},
                    ),
                    Message(
                        timestamp=datetime(2025, 11, 1, 11, 0, tzinfo=timezone.utc),
                        direction="to_pm",
                        agent_id="agent-1",
                        content="Authentication is already implemented in task-0",
                        metadata={"task_id": "task-1"},
                    ),
                ],
            ),
            TaskHistory(
                task_id="task-2",
                name="Task 2",
                description="Second task",
                status="completed",
                estimated_hours=3.0,
                actual_hours=3.2,
                conversations=[
                    Message(
                        timestamp=datetime(2025, 11, 1, 12, 0, tzinfo=timezone.utc),
                        direction="from_pm",
                        agent_id="agent-2",
                        content="Build user dashboard",
                        metadata={"task_id": "task-2"},
                    ),
                ],
            ),
            TaskHistory(
                task_id="task-3",
                name="Task 3",
                description="Third task",
                status="completed",
                estimated_hours=1.0,
                actual_hours=1.0,
                conversations=[],  # No conversations
            ),
        ]

    async def test_conversations_extracted_from_tasks(
        self, tasks_with_conversations: list[TaskHistory]
    ) -> None:
        """
        Test that conversations are extracted from task histories.

        This verifies the fix for task redundancy showing "no data" -
        conversations must be extracted from tasks and passed to analyzer.
        """
        # Arrange
        analyzer = PostProjectAnalyzer()

        # Mock the redundancy analyzer to capture what conversations it receives
        mock_redundancy_analyzer = AsyncMock()
        mock_redundancy_analysis = TaskRedundancyAnalysis(
            project_id="test-proj",
            redundant_pairs=[],
            redundancy_score=0.1,
            total_time_wasted=0.0,
            over_decomposition_detected=False,
            recommended_complexity="standard",
            raw_data={},
            llm_interpretation="No redundancy detected",
            recommendations=[],
        )
        mock_redundancy_analyzer.analyze_project.return_value = mock_redundancy_analysis
        analyzer.redundancy_analyzer = mock_redundancy_analyzer

        # Mock other analyzers to avoid LLM calls
        analyzer.requirement_analyzer = AsyncMock()
        analyzer.decision_tracer = AsyncMock()
        analyzer.instruction_analyzer = AsyncMock()
        analyzer.failure_generator = AsyncMock()

        # Mock their return values
        analyzer.requirement_analyzer.analyze_task.return_value = Mock()
        analyzer.decision_tracer.trace_decision_impact.return_value = Mock()
        analyzer.instruction_analyzer.analyze_instruction_quality.return_value = Mock()

        # Act
        scope = AnalysisScope(
            requirement_divergence=False,
            decision_impact=False,
            instruction_quality=False,
            failure_diagnosis=False,
            task_redundancy=True,  # Only run redundancy analysis
        )

        await analyzer.analyze_project(
            project_id="test-proj",
            tasks=tasks_with_conversations,
            decisions=[],
            scope=scope,
        )

        # Assert - redundancy analyzer should have been called with extracted conversations
        mock_redundancy_analyzer.analyze_project.assert_called_once()

        # Get the actual call arguments
        call_args = mock_redundancy_analyzer.analyze_project.call_args
        actual_conversations = call_args.kwargs["conversations"]

        # Verify we got all 3 conversations (2 from task-1, 1 from task-2, 0 from task-3)
        assert len(actual_conversations) == 3, (
            f"Expected 3 conversations, got {len(actual_conversations)}. "
            "Conversations should be extracted from all tasks."
        )

        # Verify the conversations are the correct ones
        assert actual_conversations[0].content == "Please implement authentication"
        assert (
            actual_conversations[1].content
            == "Authentication is already implemented in task-0"
        )
        assert actual_conversations[2].content == "Build user dashboard"

    async def test_empty_conversations_when_no_tasks(self) -> None:
        """
        Test that empty conversation list is passed when there are no tasks.
        """
        # Arrange
        analyzer = PostProjectAnalyzer()

        # Mock analyzers
        mock_redundancy_analyzer = AsyncMock()
        mock_redundancy_analysis = TaskRedundancyAnalysis(
            project_id="test-proj",
            redundant_pairs=[],
            redundancy_score=0.0,
            total_time_wasted=0.0,
            over_decomposition_detected=False,
            recommended_complexity="prototype",
            raw_data={},
            llm_interpretation="No tasks to analyze",
            recommendations=[],
        )
        mock_redundancy_analyzer.analyze_project.return_value = mock_redundancy_analysis
        analyzer.redundancy_analyzer = mock_redundancy_analyzer

        # Mock other analyzers
        analyzer.requirement_analyzer = AsyncMock()
        analyzer.decision_tracer = AsyncMock()
        analyzer.instruction_analyzer = AsyncMock()
        analyzer.failure_generator = AsyncMock()

        # Act
        scope = AnalysisScope(
            requirement_divergence=False,
            decision_impact=False,
            instruction_quality=False,
            failure_diagnosis=False,
            task_redundancy=True,
        )

        await analyzer.analyze_project(
            project_id="test-proj",
            tasks=[],  # No tasks
            decisions=[],
            scope=scope,
        )

        # Assert - redundancy analyzer should NOT be called when no tasks
        mock_redundancy_analyzer.analyze_project.assert_not_called()

    async def test_conversations_preserve_order(
        self, tasks_with_conversations: list[TaskHistory]
    ) -> None:
        """
        Test that conversations maintain chronological order when extracted.
        """
        # Arrange
        analyzer = PostProjectAnalyzer()

        # Mock analyzers
        mock_redundancy_analyzer = AsyncMock()
        mock_redundancy_analysis = TaskRedundancyAnalysis(
            project_id="test-proj",
            redundant_pairs=[],
            redundancy_score=0.0,
            total_time_wasted=0.0,
            over_decomposition_detected=False,
            recommended_complexity="standard",
            raw_data={},
            llm_interpretation="Test",
            recommendations=[],
        )
        mock_redundancy_analyzer.analyze_project.return_value = mock_redundancy_analysis
        analyzer.redundancy_analyzer = mock_redundancy_analyzer

        # Mock other analyzers
        analyzer.requirement_analyzer = AsyncMock()
        analyzer.decision_tracer = AsyncMock()
        analyzer.instruction_analyzer = AsyncMock()
        analyzer.failure_generator = AsyncMock()

        # Act
        scope = AnalysisScope(
            requirement_divergence=False,
            decision_impact=False,
            instruction_quality=False,
            failure_diagnosis=False,
            task_redundancy=True,
        )

        await analyzer.analyze_project(
            project_id="test-proj",
            tasks=tasks_with_conversations,
            decisions=[],
            scope=scope,
        )

        # Assert
        call_args = mock_redundancy_analyzer.analyze_project.call_args
        actual_conversations = call_args.kwargs["conversations"]

        # Verify chronological order (timestamps should be in order)
        timestamps = [msg.timestamp for msg in actual_conversations]
        assert timestamps == sorted(
            timestamps
        ), "Conversations should maintain chronological order across all tasks"
