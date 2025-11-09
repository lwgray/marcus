"""
Unit tests for PostProjectAnalyzer orchestrator.

Tests the main orchestrator that coordinates all Phase 2 analyzers
(Requirement Divergence, Decision Impact, Instruction Quality,
Failure Diagnosis) to provide comprehensive post-project analysis.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from src.analysis.aggregator import TaskHistory
from src.analysis.analyzers.decision_impact_tracer import (
    DecisionImpactAnalysis,
    ImpactChain,
)
from src.analysis.analyzers.failure_diagnosis import (
    FailureCause,
    FailureDiagnosis,
    PreventionStrategy,
)
from src.analysis.analyzers.instruction_quality import (
    AmbiguityIssue,
    InstructionQualityAnalysis,
    QualityScore,
)
from src.analysis.analyzers.requirement_divergence import (
    Divergence,
    RequirementDivergenceAnalysis,
)
from src.analysis.post_project_analyzer import (
    AnalysisScope,
    PostProjectAnalysis,
    PostProjectAnalyzer,
)
from src.core.project_history import Decision


class TestAnalysisScope:
    """Test suite for AnalysisScope dataclass."""

    def test_create_default_scope(self):
        """Test creating default analysis scope (all analyzers enabled)."""
        # Arrange & Act
        scope = AnalysisScope()

        # Assert
        assert scope.requirement_divergence is True
        assert scope.decision_impact is True
        assert scope.instruction_quality is True
        assert scope.failure_diagnosis is True

    def test_create_custom_scope(self):
        """Test creating custom analysis scope."""
        # Arrange & Act
        scope = AnalysisScope(
            requirement_divergence=True,
            decision_impact=False,
            instruction_quality=True,
            failure_diagnosis=False,
        )

        # Assert
        assert scope.requirement_divergence is True
        assert scope.decision_impact is False
        assert scope.instruction_quality is True
        assert scope.failure_diagnosis is False


class TestPostProjectAnalysis:
    """Test suite for PostProjectAnalysis dataclass."""

    def test_create_complete_analysis(self):
        """Test creating a complete post-project analysis."""
        # Arrange & Act
        analysis = PostProjectAnalysis(
            project_id="proj-001",
            analysis_timestamp=datetime.now(timezone.utc),
            requirement_divergences=[],
            decision_impacts=[],
            instruction_quality_issues=[],
            failure_diagnoses=[],
            summary="Analysis complete",
        )

        # Assert
        assert analysis.project_id == "proj-001"
        assert len(analysis.requirement_divergences) == 0
        assert len(analysis.decision_impacts) == 0
        assert len(analysis.instruction_quality_issues) == 0
        assert len(analysis.failure_diagnoses) == 0


class TestPostProjectAnalyzer:
    """Test suite for PostProjectAnalyzer orchestrator."""

    @pytest.fixture
    def mock_requirement_analyzer(self):
        """Create mock requirement divergence analyzer."""
        mock = Mock()
        mock.analyze_task = AsyncMock(
            return_value=RequirementDivergenceAnalysis(
                task_id="task-001",
                fidelity_score=0.7,
                divergences=[
                    Divergence(
                        requirement="Use OAuth2 for authentication",
                        implementation="Implemented JWT tokens instead",
                        severity="major",
                        citation="task task-001, implementation line 45",
                        impact="Different auth mechanism than specified",
                    )
                ],
                raw_data={},
                llm_interpretation="Found divergence",
                recommendations=["Align implementation with requirements"],
            )
        )
        return mock

    @pytest.fixture
    def mock_decision_tracer(self):
        """Create mock decision impact tracer."""
        mock = Mock()
        mock.trace_decision_impact = AsyncMock(
            return_value=DecisionImpactAnalysis(
                decision_id="dec-001",
                impact_chains=[
                    ImpactChain(
                        decision_id="dec-001",
                        decision_summary="Use microservices",
                        direct_impacts=["task-002"],
                        indirect_impacts=[],
                        depth=1,
                        citation="dec-001",
                    )
                ],
                unexpected_impacts=[],
                raw_data={},
                llm_interpretation="Impact traced",
                recommendations=[],
            )
        )
        return mock

    @pytest.fixture
    def mock_instruction_analyzer(self):
        """Create mock instruction quality analyzer."""
        mock = Mock()
        mock.analyze_instruction_quality = AsyncMock(
            return_value=InstructionQualityAnalysis(
                task_id="task-001",
                quality_scores=QualityScore(
                    clarity=0.8,
                    completeness=0.7,
                    specificity=0.6,
                    overall=0.7,
                ),
                ambiguity_issues=[
                    AmbiguityIssue(
                        task_id="task-001",
                        task_name="Build auth",
                        ambiguous_aspect="auth method",
                        evidence="Not specified",
                        consequence="Had to ask",
                        severity="major",
                        citation="task-001",
                    )
                ],
                raw_data={},
                llm_interpretation="Quality analyzed",
                recommendations=[],
            )
        )
        return mock

    @pytest.fixture
    def mock_failure_generator(self):
        """Create mock failure diagnosis generator."""
        mock = Mock()
        mock.generate_diagnosis = AsyncMock(
            return_value=FailureDiagnosis(
                task_id="task-001",
                failure_causes=[
                    FailureCause(
                        category="technical",
                        root_cause="Timeout",
                        contributing_factors=[],
                        evidence="Logs",
                        citation="task-001",
                    )
                ],
                prevention_strategies=[
                    PreventionStrategy(
                        strategy="Add retries",
                        rationale="Handle transient failures",
                        effort="low",
                        priority="high",
                    )
                ],
                raw_data={},
                llm_interpretation="Diagnosis complete",
                lessons_learned=[],
            )
        )
        return mock

    @pytest.fixture
    def analyzer(
        self,
        mock_requirement_analyzer,
        mock_decision_tracer,
        mock_instruction_analyzer,
        mock_failure_generator,
    ):
        """Create analyzer with all mocked analyzers."""
        return PostProjectAnalyzer(
            requirement_analyzer=mock_requirement_analyzer,
            decision_tracer=mock_decision_tracer,
            instruction_analyzer=mock_instruction_analyzer,
            failure_generator=mock_failure_generator,
        )

    @pytest.fixture
    def sample_tasks(self):
        """Create sample tasks for testing."""
        return [
            TaskHistory(
                task_id="task-001",
                name="Build auth",
                description="Implement authentication",
                status="completed",
                estimated_hours=4.0,
                actual_hours=8.0,
            ),
            TaskHistory(
                task_id="task-002",
                name="Add tests",
                description="Write unit tests",
                status="completed",
                estimated_hours=2.0,
                actual_hours=3.0,
            ),
        ]

    @pytest.fixture
    def sample_decisions(self):
        """Create sample decisions for testing."""
        return [
            Decision(
                decision_id="dec-001",
                task_id="task-001",
                agent_id="agent-1",
                timestamp=datetime.now(timezone.utc),
                what="Use microservices",
                why="Better scalability",
                impact="major",
                affected_tasks=["task-002"],
                confidence=0.8,
            )
        ]

    @pytest.mark.asyncio
    async def test_analyze_project_complete(
        self, analyzer, sample_tasks, sample_decisions
    ):
        """Test running complete post-project analysis."""
        # Act
        analysis = await analyzer.analyze_project(
            project_id="proj-001",
            tasks=sample_tasks,
            decisions=sample_decisions,
        )

        # Assert
        assert isinstance(analysis, PostProjectAnalysis)
        assert analysis.project_id == "proj-001"
        assert len(analysis.requirement_divergences) > 0
        assert len(analysis.decision_impacts) > 0
        assert len(analysis.instruction_quality_issues) > 0
        # No failure diagnoses expected since sample tasks are all "completed"
        assert len(analysis.failure_diagnoses) == 0

    @pytest.mark.asyncio
    async def test_analyze_project_with_custom_scope(
        self, analyzer, sample_tasks, sample_decisions
    ):
        """Test running analysis with custom scope (selective analyzers)."""
        # Arrange
        scope = AnalysisScope(
            requirement_divergence=True,
            decision_impact=False,
            instruction_quality=False,
            failure_diagnosis=False,
        )

        # Act
        analysis = await analyzer.analyze_project(
            project_id="proj-001",
            tasks=sample_tasks,
            decisions=sample_decisions,
            scope=scope,
        )

        # Assert
        assert len(analysis.requirement_divergences) > 0
        assert len(analysis.decision_impacts) == 0
        assert len(analysis.instruction_quality_issues) == 0
        assert len(analysis.failure_diagnoses) == 0

    @pytest.mark.asyncio
    async def test_analyze_project_filters_failed_tasks(
        self, analyzer, sample_decisions
    ):
        """Test that failure diagnosis only runs on failed tasks."""
        # Arrange
        tasks = [
            TaskHistory(
                task_id="task-001",
                name="Build auth",
                description="Auth",
                status="completed",
                estimated_hours=4.0,
                actual_hours=4.0,
            ),
            TaskHistory(
                task_id="task-002",
                name="Add feature",
                description="Feature",
                status="failed",
                estimated_hours=2.0,
                actual_hours=5.0,
            ),
        ]

        # Act
        analysis = await analyzer.analyze_project(
            project_id="proj-001",
            tasks=tasks,
            decisions=sample_decisions,
        )

        # Assert - Should only have 1 failure diagnosis (for failed task)
        assert len(analysis.failure_diagnoses) == 1

    @pytest.mark.asyncio
    async def test_analyze_project_with_progress_callback(
        self, analyzer, sample_tasks, sample_decisions
    ):
        """Test that progress callback is called during analysis."""
        # Arrange
        progress_events = []

        async def progress_callback(event):
            progress_events.append(event)

        # Act
        await analyzer.analyze_project(
            project_id="proj-001",
            tasks=sample_tasks,
            decisions=sample_decisions,
            progress_callback=progress_callback,
        )

        # Assert
        assert len(progress_events) > 0

    @pytest.mark.asyncio
    async def test_analyze_project_with_no_tasks(self, analyzer, sample_decisions):
        """Test analyzing project with no tasks."""
        # Act
        analysis = await analyzer.analyze_project(
            project_id="proj-001",
            tasks=[],
            decisions=sample_decisions,
        )

        # Assert
        assert len(analysis.requirement_divergences) == 0
        assert len(analysis.failure_diagnoses) == 0

    @pytest.mark.asyncio
    async def test_analyze_project_with_no_decisions(self, analyzer, sample_tasks):
        """Test analyzing project with no decisions."""
        # Act
        analysis = await analyzer.analyze_project(
            project_id="proj-001",
            tasks=sample_tasks,
            decisions=[],
        )

        # Assert
        assert len(analysis.decision_impacts) == 0

    @pytest.mark.asyncio
    async def test_generate_summary(self, analyzer, sample_tasks, sample_decisions):
        """Test that summary is generated from analysis results."""
        # Act
        analysis = await analyzer.analyze_project(
            project_id="proj-001",
            tasks=sample_tasks,
            decisions=sample_decisions,
        )

        # Assert
        assert analysis.summary is not None
        assert len(analysis.summary) > 0
        assert "divergence" in analysis.summary.lower()

    @pytest.mark.asyncio
    async def test_analyzer_creates_default_analyzers_if_none_provided(self):
        """Test that analyzer creates default analyzers if not provided."""
        # Act
        analyzer = PostProjectAnalyzer()

        # Assert
        assert analyzer.requirement_analyzer is not None
        assert analyzer.decision_tracer is not None
        assert analyzer.instruction_analyzer is not None
        assert analyzer.failure_generator is not None
