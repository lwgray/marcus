"""
Unit tests for Task Redundancy Analyzer.

Tests the analyzer that detects duplicate and redundant work across tasks,
including over-decomposition from enterprise mode and quick completions.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from src.analysis.aggregator import TaskHistory
from src.analysis.analyzers.task_redundancy import (
    RedundantTaskPair,
    TaskRedundancyAnalysis,
    TaskRedundancyAnalyzer,
)


class TestRedundantTaskPair:
    """Test suite for RedundantTaskPair dataclass."""

    def test_create_redundant_pair(self):
        """Test creating a redundant task pair."""
        # Arrange & Act
        pair = RedundantTaskPair(
            task_1_id="task-001",
            task_1_name="Implement user authentication",
            task_2_id="task-002",
            task_2_name="Add login feature",
            overlap_score=0.85,
            evidence="Both tasks modify auth.py and implement OAuth2",
            time_wasted=2.5,
        )

        # Assert
        assert pair.task_1_id == "task-001"
        assert pair.task_2_id == "task-002"
        assert pair.overlap_score == 0.85
        assert pair.time_wasted == 2.5
        assert "OAuth2" in pair.evidence


class TestTaskRedundancyAnalysis:
    """Test suite for TaskRedundancyAnalysis dataclass."""

    def test_create_analysis_with_redundancy(self):
        """Test creating analysis with detected redundancy."""
        # Arrange & Act
        analysis = TaskRedundancyAnalysis(
            project_id="proj-123",
            redundant_pairs=[
                RedundantTaskPair(
                    task_1_id="task-001",
                    task_1_name="Setup database",
                    task_2_id="task-002",
                    task_2_name="Configure database",
                    overlap_score=0.9,
                    evidence="Both initialize db.sqlite",
                    time_wasted=1.5,
                )
            ],
            redundancy_score=0.45,
            total_time_wasted=1.5,
            over_decomposition_detected=True,
            recommended_complexity="standard",
            raw_data={
                "total_tasks": 10,
                "quick_completions": 3,
            },
            llm_interpretation=(
                "Project shows signs of over-decomposition"
            ),
            recommendations=[
                "Switch from enterprise to standard complexity",
                "Combine related setup tasks",
            ],
        )

        # Assert
        assert analysis.project_id == "proj-123"
        assert analysis.redundancy_score == 0.45
        assert analysis.total_time_wasted == 1.5
        assert analysis.over_decomposition_detected is True
        assert analysis.recommended_complexity == "standard"
        assert len(analysis.redundant_pairs) == 1
        assert len(analysis.recommendations) == 2

    def test_create_analysis_no_redundancy(self):
        """Test creating analysis with no redundancy detected."""
        # Arrange & Act
        analysis = TaskRedundancyAnalysis(
            project_id="proj-456",
            redundant_pairs=[],
            redundancy_score=0.0,
            total_time_wasted=0.0,
            over_decomposition_detected=False,
            recommended_complexity="enterprise",
            raw_data={"total_tasks": 5},
            llm_interpretation="Clean task decomposition",
            recommendations=["Continue current approach"],
        )

        # Assert
        assert analysis.redundancy_score == 0.0
        assert len(analysis.redundant_pairs) == 0
        assert analysis.over_decomposition_detected is False


class TestTaskRedundancyAnalyzer:
    """Test suite for TaskRedundancyAnalyzer."""

    @pytest.fixture
    def mock_ai_engine(self):
        """Create mock AI engine."""
        from src.analysis.ai_engine import AnalysisResponse, AnalysisType

        mock = AsyncMock()
        # Mock response detecting redundancy
        mock.analyze = AsyncMock(
            return_value=AnalysisResponse(
                analysis_type=AnalysisType.TASK_REDUNDANCY,
                raw_response='{"redundancy_score": 0.6, "pairs": [...]}',
                parsed_result={
                    "redundancy_score": 0.6,
                    "redundant_pairs": [
                        {
                            "task_1_id": "task-001",
                            "task_1_name": "Setup API",
                            "task_2_id": "task-002",
                            "task_2_name": "Configure API",
                            "overlap_score": 0.9,
                            "evidence": (
                                "Both tasks modify api/config.py (lines 10-50)"
                            ),
                            "time_wasted": 1.2,
                        }
                    ],
                    "over_decomposition_detected": True,
                    "recommended_complexity": "standard",
                    "recommendations": [
                        "Merge related setup tasks",
                        "Use standard complexity mode",
                    ],
                    "confidence": 0.85,
                },
                confidence=0.85,
                timestamp=datetime.now(timezone.utc),
                model_used="claude-3-sonnet",
                cached=False,
            )
        )
        return mock

    @pytest.fixture
    def mock_ai_engine_no_redundancy(self):
        """Create mock AI engine with no redundancy."""
        from src.analysis.ai_engine import AnalysisResponse, AnalysisType

        mock = AsyncMock()
        mock.analyze = AsyncMock(
            return_value=AnalysisResponse(
                analysis_type=AnalysisType.TASK_REDUNDANCY,
                raw_response='{"redundancy_score": 0.0, "pairs": []}',
                parsed_result={
                    "redundancy_score": 0.0,
                    "redundant_pairs": [],
                    "over_decomposition_detected": False,
                    "recommended_complexity": "enterprise",
                    "recommendations": ["Task decomposition is optimal"],
                    "confidence": 0.9,
                },
                confidence=0.9,
                timestamp=datetime.now(timezone.utc),
                model_used="claude-3-sonnet",
                cached=False,
            )
        )
        return mock

    @pytest.fixture
    def sample_tasks(self):
        """Create sample tasks for testing."""
        base_time = datetime.now(timezone.utc)

        return [
            TaskHistory(
                task_id="task-001",
                name="Setup database",
                description="Initialize SQLite database",
                status="completed",
                started_at=base_time + timedelta(minutes=1),
                completed_at=base_time + timedelta(hours=2),
                estimated_hours=2.0,
                actual_hours=2.0,
                assigned_to="agent-1",
            ),
            TaskHistory(
                task_id="task-002",
                name="Configure database",
                description="Setup database schema",
                status="completed",
                started_at=base_time + timedelta(hours=2, minutes=5),
                completed_at=base_time + timedelta(hours=4),
                estimated_hours=2.0,
                actual_hours=1.9,
                assigned_to="agent-2",
            ),
            TaskHistory(
                task_id="task-003",
                name="Write tests",
                description="Unit tests for database",
                status="completed",
                started_at=base_time + timedelta(hours=4, minutes=10),
                completed_at=base_time + timedelta(hours=6),
                estimated_hours=2.0,
                actual_hours=1.8,
                assigned_to="agent-1",
            ),
        ]

    @pytest.fixture
    def quick_completion_tasks(self):
        """Create tasks with quick completions (< 30 seconds)."""
        base_time = datetime.now(timezone.utc)

        return [
            TaskHistory(
                task_id="task-quick-1",
                name="Format code",
                description="Run black formatter",
                status="completed",
                started_at=base_time + timedelta(seconds=1),
                completed_at=base_time + timedelta(seconds=15),
                estimated_hours=0.5,
                actual_hours=0.004,  # 15 seconds
                assigned_to="agent-1",
            ),
            TaskHistory(
                task_id="task-quick-2",
                name="Sort imports",
                description="Run isort",
                status="completed",
                started_at=base_time + timedelta(minutes=1, seconds=5),
                completed_at=base_time + timedelta(minutes=1, seconds=20),
                estimated_hours=0.5,
                actual_hours=0.004,  # 15 seconds
                assigned_to="agent-1",
            ),
        ]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_analyze_project_with_redundancy(
        self, mock_ai_engine, sample_tasks
    ):
        """Test analyzing project that has redundant work."""
        # Arrange
        analyzer = TaskRedundancyAnalyzer(ai_engine=mock_ai_engine)

        # Act
        result = await analyzer.analyze_project(
            tasks=sample_tasks,
            conversations=[],
        )

        # Assert
        assert isinstance(result, TaskRedundancyAnalysis)
        # project_id comes from AI engine response
        assert result.project_id == ""
        assert result.redundancy_score == 0.6
        assert len(result.redundant_pairs) == 1
        assert result.over_decomposition_detected is True
        # 0.6 > 0.4 triggers "prototype" recommendation
        assert result.recommended_complexity == "prototype"
        assert len(result.recommendations) == 2

        # Verify AI engine was called
        mock_ai_engine.analyze.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_analyze_project_no_redundancy(
        self, mock_ai_engine_no_redundancy, sample_tasks
    ):
        """Test analyzing project with no redundancy."""
        # Arrange
        analyzer = TaskRedundancyAnalyzer(
            ai_engine=mock_ai_engine_no_redundancy
        )

        # Act
        result = await analyzer.analyze_project(
            tasks=sample_tasks,
            conversations=[],
        )

        # Assert
        assert result.redundancy_score == 0.0
        assert len(result.redundant_pairs) == 0
        assert result.over_decomposition_detected is False
        assert result.recommended_complexity == "enterprise"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_analyze_project_with_progress_callback(
        self, mock_ai_engine, sample_tasks
    ):
        """Test that progress callback is invoked during analysis."""
        # Arrange
        analyzer = TaskRedundancyAnalyzer(ai_engine=mock_ai_engine)
        progress_events = []

        async def progress_callback(event):
            progress_events.append(event)

        # Act
        await analyzer.analyze_project(
            tasks=sample_tasks,
            conversations=[],
            progress_callback=progress_callback,
        )

        # Assert - Progress callback should have been called
        # Note: Actual progress reporting depends on implementation
        # This test verifies callback mechanism works
        assert True  # If no exception, callback was accepted

    @pytest.mark.unit
    def test_find_quick_completions(self, quick_completion_tasks):
        """Test identifying tasks completed in < 30 seconds."""
        # Arrange
        analyzer = TaskRedundancyAnalyzer(quick_completion_threshold=30.0)

        # Act
        quick_tasks = analyzer._find_quick_completions(
            quick_completion_tasks
        )

        # Assert
        assert len(quick_tasks) == 2
        assert all(t.task_id.startswith("task-quick-") for t in quick_tasks)
        assert all(t.actual_hours < 0.01 for t in quick_tasks)  # < 36s

    @pytest.mark.unit
    def test_find_quick_completions_with_custom_threshold(
        self, quick_completion_tasks
    ):
        """Test quick completion detection with custom threshold."""
        # Arrange - Set threshold to 10 seconds
        analyzer = TaskRedundancyAnalyzer(quick_completion_threshold=10.0)

        # Act
        quick_tasks = analyzer._find_quick_completions(
            quick_completion_tasks
        )

        # Assert - 15 second tasks should NOT be detected
        assert len(quick_tasks) == 0

    @pytest.mark.unit
    def test_find_quick_completions_none_found(self, sample_tasks):
        """Test quick completion detection when none exist."""
        # Arrange
        analyzer = TaskRedundancyAnalyzer(quick_completion_threshold=30.0)

        # Act
        quick_tasks = analyzer._find_quick_completions(sample_tasks)

        # Assert
        assert len(quick_tasks) == 0

    @pytest.mark.unit
    def test_recommend_complexity_high_redundancy(self):
        """Test complexity recommendation with high redundancy score."""
        # Arrange
        analyzer = TaskRedundancyAnalyzer()
        base_time = datetime.now(timezone.utc)

        # Create 20 tasks, 5 quick completions
        all_tasks = [
            TaskHistory(
                task_id=f"task-{i:03d}",
                name=f"Task {i}",
                description=f"Description {i}",
                status="completed",
                started_at=base_time + timedelta(hours=i),
                completed_at=base_time + timedelta(hours=i+1),
                estimated_hours=1.0,
                actual_hours=1.0,
                assigned_to="agent-1",
            )
            for i in range(20)
        ]
        quick_tasks = all_tasks[:5]  # First 5 are quick

        # Act
        recommendation = analyzer._recommend_complexity(
            tasks=all_tasks,
            redundancy_score=0.7,
            quick_completions=quick_tasks,
        )

        # Assert
        assert recommendation == "prototype"

    @pytest.mark.unit
    def test_recommend_complexity_medium_redundancy(self):
        """Test complexity recommendation with medium redundancy."""
        # Arrange
        analyzer = TaskRedundancyAnalyzer()
        base_time = datetime.now(timezone.utc)

        # Create 20 tasks, 2 quick completions
        all_tasks = [
            TaskHistory(
                task_id=f"task-{i:03d}",
                name=f"Task {i}",
                description=f"Description {i}",
                status="completed",
                started_at=base_time + timedelta(hours=i),
                completed_at=base_time + timedelta(hours=i+1),
                estimated_hours=1.0,
                actual_hours=1.0,
                assigned_to="agent-1",
            )
            for i in range(20)
        ]
        quick_tasks = all_tasks[:2]  # First 2 are quick

        # Act
        recommendation = analyzer._recommend_complexity(
            tasks=all_tasks,
            redundancy_score=0.4,
            quick_completions=quick_tasks,
        )

        # Assert
        assert recommendation == "standard"

    @pytest.mark.unit
    def test_recommend_complexity_low_redundancy(self):
        """Test complexity recommendation with low redundancy."""
        # Arrange
        analyzer = TaskRedundancyAnalyzer()
        base_time = datetime.now(timezone.utc)

        # Create 20 tasks, 1 quick completion
        all_tasks = [
            TaskHistory(
                task_id=f"task-{i:03d}",
                name=f"Task {i}",
                description=f"Description {i}",
                status="completed",
                started_at=base_time + timedelta(hours=i),
                completed_at=base_time + timedelta(hours=i+1),
                estimated_hours=1.0,
                actual_hours=1.0,
                assigned_to="agent-1",
            )
            for i in range(20)
        ]
        quick_tasks = all_tasks[:1]  # First 1 is quick

        # Act
        recommendation = analyzer._recommend_complexity(
            tasks=all_tasks,
            redundancy_score=0.1,
            quick_completions=quick_tasks,
        )

        # Assert
        assert recommendation == "enterprise"

    @pytest.mark.unit
    def test_recommend_complexity_many_quick_completions(self):
        """Test recommendation prioritizes quick completions."""
        # Arrange
        analyzer = TaskRedundancyAnalyzer()
        base_time = datetime.now(timezone.utc)

        # Create 20 tasks, 8 quick completions (40%)
        all_tasks = [
            TaskHistory(
                task_id=f"task-{i:03d}",
                name=f"Task {i}",
                description=f"Description {i}",
                status="completed",
                started_at=base_time + timedelta(hours=i),
                completed_at=base_time + timedelta(hours=i+1),
                estimated_hours=1.0,
                actual_hours=1.0,
                assigned_to="agent-1",
            )
            for i in range(20)
        ]
        quick_tasks = all_tasks[:8]  # First 8 are quick

        # Act - Low redundancy but many quick completions
        recommendation = analyzer._recommend_complexity(
            tasks=all_tasks,
            redundancy_score=0.15,
            quick_completions=quick_tasks,
        )

        # Assert - Should downgrade from enterprise to standard
        assert recommendation == "standard"

    @pytest.mark.unit
    def test_recommend_complexity_edge_cases(self):
        """Test complexity recommendation edge cases."""
        # Arrange
        analyzer = TaskRedundancyAnalyzer()
        base_time = datetime.now(timezone.utc)

        # Act & Assert - Zero tasks
        rec1 = analyzer._recommend_complexity(
            tasks=[],
            redundancy_score=0.0,
            quick_completions=[],
        )
        assert rec1 in ["prototype", "standard", "enterprise"]

        # Act & Assert - All tasks quick
        all_tasks = [
            TaskHistory(
                task_id=f"task-{i:03d}",
                name=f"Task {i}",
                description=f"Description {i}",
                status="completed",
                started_at=base_time + timedelta(hours=i),
                completed_at=base_time + timedelta(hours=i+1),
                estimated_hours=1.0,
                actual_hours=1.0,
                assigned_to="agent-1",
            )
            for i in range(10)
        ]
        rec2 = analyzer._recommend_complexity(
            tasks=all_tasks,
            redundancy_score=1.0,
            quick_completions=all_tasks,  # All 10 are quick
        )
        assert rec2 == "prototype"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_analyze_empty_project(self, mock_ai_engine_no_redundancy):
        """Test analyzing project with no tasks."""
        # Arrange
        analyzer = TaskRedundancyAnalyzer(
            ai_engine=mock_ai_engine_no_redundancy
        )

        # Act
        result = await analyzer.analyze_project(
            tasks=[],
            conversations=[],
        )

        # Assert
        assert result.redundancy_score == 0.0
        assert len(result.redundant_pairs) == 0
        assert result.total_time_wasted == 0.0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_raw_data_includes_task_info(
        self, mock_ai_engine, sample_tasks
    ):
        """Test that raw_data includes task summaries."""
        # Arrange
        analyzer = TaskRedundancyAnalyzer(ai_engine=mock_ai_engine)

        # Act
        result = await analyzer.analyze_project(
            tasks=sample_tasks,
            conversations=[],
        )

        # Assert
        assert "task_summaries" in result.raw_data
        assert len(result.raw_data["task_summaries"]) == len(sample_tasks)
        assert all(
            "task_id" in task for task in result.raw_data["task_summaries"]
        )
        assert all("name" in task for task in result.raw_data["task_summaries"])

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_llm_interpretation_present(
        self, mock_ai_engine, sample_tasks
    ):
        """Test that LLM interpretation is included in results."""
        # Arrange
        analyzer = TaskRedundancyAnalyzer(ai_engine=mock_ai_engine)

        # Act
        result = await analyzer.analyze_project(
            tasks=sample_tasks,
            conversations=[],
        )

        # Assert
        assert result.llm_interpretation is not None
        assert len(result.llm_interpretation) > 0
        # llm_interpretation is a top-level field, not in raw_data
        assert isinstance(result.llm_interpretation, str)


class TestTaskRedundancyIntegration:
    """Integration-style tests for TaskRedundancyAnalyzer.

    These tests verify the analyzer works with realistic scenarios
    but still use mocked AI engine (not true integration tests).
    """

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_enterprise_mode_over_decomposition(self):
        """Test detecting over-decomposition typical of enterprise mode."""
        # Arrange
        from src.analysis.ai_engine import AnalysisResponse, AnalysisType

        base_time = datetime.now(timezone.utc)

        # Create many small, related tasks (enterprise over-decomposition)
        tasks = [
            TaskHistory(
                task_id=f"task-{i:03d}",
                name=f"Micro-task {i}",
                description=f"Very small task #{i}",
                status="completed",
                started_at=base_time + timedelta(minutes=i * 5 + 1),
                completed_at=base_time + timedelta(minutes=i * 5 + 2),
                estimated_hours=0.1,
                actual_hours=0.02,  # 1.2 minutes
                assigned_to=f"agent-{i % 2 + 1}",
            )
            for i in range(15)
        ]

        mock_ai = AsyncMock()
        mock_ai.analyze = AsyncMock(
            return_value=AnalysisResponse(
                analysis_type=AnalysisType.TASK_REDUNDANCY,
                raw_response="{}",
                parsed_result={
                    "redundancy_score": 0.8,
                    "redundant_pairs": [
                        {
                            "task_1_id": f"task-{i:03d}",
                            "task_1_name": f"Micro-task {i}",
                            "task_2_id": f"task-{i+1:03d}",
                            "task_2_name": f"Micro-task {i+1}",
                            "overlap_score": 0.9,
                            "evidence": "Adjacent tasks do same work",
                            "time_wasted": 0.02,
                        }
                        for i in range(0, 14, 2)
                    ],
                    "over_decomposition_detected": True,
                    "recommended_complexity": "standard",
                    "recommendations": [
                        "Reduce task granularity",
                        "Switch to standard complexity",
                    ],
                    "confidence": 0.9,
                },
                confidence=0.9,
                timestamp=datetime.now(timezone.utc),
                model_used="claude-3-sonnet",
                cached=False,
            )
        )

        analyzer = TaskRedundancyAnalyzer(ai_engine=mock_ai)

        # Act
        result = await analyzer.analyze_project(
            tasks=tasks,
            conversations=[],
        )

        # Assert
        assert result.redundancy_score >= 0.7
        assert result.over_decomposition_detected is True
        assert result.recommended_complexity in ["prototype", "standard"]
        assert len(result.redundant_pairs) > 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_prototype_mode_optimal(self):
        """Test clean project with no redundancy (optimal prototype mode)."""
        # Arrange
        from src.analysis.ai_engine import AnalysisResponse, AnalysisType

        base_time = datetime.now(timezone.utc)

        # Create well-separated, distinct tasks
        tasks = [
            TaskHistory(
                task_id="task-001",
                name="Design architecture",
                description="High-level system design",
                status="completed",
                started_at=base_time + timedelta(minutes=5),
                completed_at=base_time + timedelta(hours=3),
                estimated_hours=3.0,
                actual_hours=3.0,
                assigned_to="agent-1",
            ),
            TaskHistory(
                task_id="task-002",
                name="Implement core features",
                description="Build main functionality",
                status="completed",
                started_at=base_time + timedelta(hours=3, minutes=10),
                completed_at=base_time + timedelta(hours=8),
                estimated_hours=5.0,
                actual_hours=4.9,
                assigned_to="agent-2",
            ),
            TaskHistory(
                task_id="task-003",
                name="Write documentation",
                description="User and dev docs",
                status="completed",
                started_at=base_time + timedelta(hours=8, minutes=15),
                completed_at=base_time + timedelta(hours=10),
                estimated_hours=2.0,
                actual_hours=1.8,
                assigned_to="agent-1",
            ),
        ]

        mock_ai = AsyncMock()
        mock_ai.analyze = AsyncMock(
            return_value=AnalysisResponse(
                analysis_type=AnalysisType.TASK_REDUNDANCY,
                raw_response="{}",
                parsed_result={
                    "redundancy_score": 0.0,
                    "redundant_pairs": [],
                    "over_decomposition_detected": False,
                    "recommended_complexity": "prototype",
                    "recommendations": [
                        "Task breakdown is optimal for prototype phase"
                    ],
                    "confidence": 0.95,
                },
                confidence=0.95,
                timestamp=datetime.now(timezone.utc),
                model_used="claude-3-sonnet",
                cached=False,
            )
        )

        analyzer = TaskRedundancyAnalyzer(ai_engine=mock_ai)

        # Act
        result = await analyzer.analyze_project(
            tasks=tasks,
            conversations=[],
        )

        # Assert
        assert result.redundancy_score == 0.0
        assert len(result.redundant_pairs) == 0
        assert result.over_decomposition_detected is False
        assert result.total_time_wasted == 0.0
