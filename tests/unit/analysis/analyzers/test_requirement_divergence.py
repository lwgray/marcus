"""
Unit tests for Requirement Divergence Analyzer.

Tests the analyzer that determines if implementations match original requirements
semantically, with citations and fidelity scoring.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from src.analysis.aggregator import TaskHistory
from src.analysis.analyzers.requirement_divergence import (
    Divergence,
    RequirementDivergenceAnalysis,
    RequirementDivergenceAnalyzer,
)
from src.core.project_history import ArtifactMetadata, Decision


class TestDivergence:
    """Test suite for Divergence dataclass."""

    def test_create_divergence(self):
        """Test creating a divergence."""
        # Arrange & Act
        div = Divergence(
            requirement="OAuth2 authentication with GitHub",
            implementation="Username/password with JWT (login.py:45-67)",
            severity="critical",
            citation="decision dec_001 at 2025-11-04 10:15",
            impact="Users cannot login with GitHub accounts",
        )

        # Assert
        assert div.requirement == "OAuth2 authentication with GitHub"
        assert div.severity == "critical"
        assert "dec_001" in div.citation


class TestRequirementDivergenceAnalysis:
    """Test suite for RequirementDivergenceAnalysis dataclass."""

    def test_create_analysis(self):
        """Test creating a complete analysis."""
        # Arrange & Act
        analysis = RequirementDivergenceAnalysis(
            task_id="task-123",
            fidelity_score=0.85,
            divergences=[
                Divergence(
                    requirement="Login feature",
                    implementation="Built login",
                    severity="minor",
                    citation="line 10",
                    impact="Minor styling difference",
                )
            ],
            raw_data={"task_description": "Build login"},
            llm_interpretation="Implementation matches requirements well",
            recommendations=["Add integration tests"],
        )

        # Assert
        assert analysis.task_id == "task-123"
        assert analysis.fidelity_score == 0.85
        assert len(analysis.divergences) == 1
        assert len(analysis.recommendations) == 1


class TestRequirementDivergenceAnalyzer:
    """Test suite for RequirementDivergenceAnalyzer."""

    @pytest.fixture
    def mock_ai_engine(self):
        """Create mock AI engine."""
        from src.analysis.ai_engine import AnalysisResponse, AnalysisType

        mock = AsyncMock()
        # Mock response with divergence detected
        mock.analyze = AsyncMock(
            return_value=AnalysisResponse(
                analysis_type=AnalysisType.REQUIREMENT_DIVERGENCE,
                raw_response='{"fidelity_score": 0.2, "divergences": [...]}',
                parsed_result={
                    "fidelity_score": 0.2,
                    "divergences": [
                        {
                            "requirement": "OAuth2 with GitHub",
                            "implementation": "JWT auth (login.py:45-67)",
                            "severity": "critical",
                            "citation": "decision dec_001 at 2025-11-04 10:15",
                            "impact": "Cannot login with GitHub",
                        }
                    ],
                    "recommendations": [
                        "Reimplement with OAuth2",
                        "Update requirements if JWT acceptable",
                    ],
                },
                confidence=0.9,
                timestamp=datetime.now(timezone.utc),
                model_used="claude-3-sonnet",
            )
        )
        return mock

    @pytest.fixture
    def analyzer(self, mock_ai_engine):
        """Create analyzer with mocked AI engine."""
        return RequirementDivergenceAnalyzer(ai_engine=mock_ai_engine)

    @pytest.fixture
    def sample_task(self):
        """Create sample task for testing."""
        return TaskHistory(
            task_id="task-login",
            name="Implement login",
            description="Implement user login with OAuth2 using GitHub provider",
            status="completed",
            estimated_hours=4.0,
            actual_hours=5.0,
        )

    @pytest.fixture
    def sample_decisions(self):
        """Create sample decisions for testing."""
        return [
            Decision(
                decision_id="dec_001",
                task_id="task-login",
                agent_id="agent-1",
                timestamp=datetime(2025, 11, 4, 10, 15, tzinfo=timezone.utc),
                what="Use JWT auth instead of OAuth2",
                why="Simpler to implement",
                impact="major",
                affected_tasks=[],
                confidence=0.8,
            )
        ]

    @pytest.fixture
    def sample_artifacts(self):
        """Create sample artifacts for testing."""
        return [
            ArtifactMetadata(
                artifact_id="art_001",
                task_id="task-login",
                agent_id="agent-1",
                timestamp=datetime.now(timezone.utc),
                artifact_type="code",
                filename="login.py",
                relative_path="src/auth/login.py",
                absolute_path="/project/src/auth/login.py",
                description="Login implementation",
                file_size_bytes=1024,
                sha256_hash="abc123",
            )
        ]

    @pytest.mark.asyncio
    async def test_analyze_task(
        self, analyzer, mock_ai_engine, sample_task, sample_decisions, sample_artifacts
    ):
        """Test analyzing a single task."""
        # Act
        analysis = await analyzer.analyze_task(
            task=sample_task,
            decisions=sample_decisions,
            artifacts=sample_artifacts,
        )

        # Assert
        assert isinstance(analysis, RequirementDivergenceAnalysis)
        assert analysis.task_id == "task-login"
        assert analysis.fidelity_score == 0.2
        assert len(analysis.divergences) == 1
        assert analysis.divergences[0].severity == "critical"
        assert len(analysis.recommendations) == 2

    @pytest.mark.asyncio
    async def test_analyze_task_builds_correct_prompt(
        self, analyzer, mock_ai_engine, sample_task, sample_decisions, sample_artifacts
    ):
        """Test that analyzer builds correct prompt with all context."""
        # Act
        await analyzer.analyze_task(
            task=sample_task,
            decisions=sample_decisions,
            artifacts=sample_artifacts,
        )

        # Assert
        call_args = mock_ai_engine.analyze.call_args
        request = call_args[0][0]

        # Verify context data includes all required fields
        assert "task_description" in request.context_data
        assert "decisions" in request.context_data
        assert "artifacts" in request.context_data
        assert request.context_data["task_description"] == sample_task.description

    @pytest.mark.asyncio
    async def test_analyze_task_with_no_divergences(self, mock_ai_engine):
        """Test analyzing task that matches requirements perfectly."""
        # Arrange
        from src.analysis.ai_engine import AnalysisResponse, AnalysisType

        mock_ai_engine.analyze = AsyncMock(
            return_value=AnalysisResponse(
                analysis_type=AnalysisType.REQUIREMENT_DIVERGENCE,
                raw_response='{"fidelity_score": 1.0, "divergences": []}',
                parsed_result={
                    "fidelity_score": 1.0,
                    "divergences": [],
                    "recommendations": ["Continue current approach"],
                },
                confidence=0.95,
                timestamp=datetime.now(timezone.utc),
                model_used="claude-3-sonnet",
            )
        )

        analyzer = RequirementDivergenceAnalyzer(ai_engine=mock_ai_engine)

        task = TaskHistory(
            task_id="task-perfect",
            name="Build feature X",
            description="Build feature X with spec Y",
            status="completed",
            estimated_hours=2.0,
            actual_hours=2.0,
        )

        # Act
        analysis = await analyzer.analyze_task(task, [], [])

        # Assert
        assert analysis.fidelity_score == 1.0
        assert len(analysis.divergences) == 0
        assert "Continue current approach" in analysis.recommendations

    @pytest.mark.asyncio
    async def test_analyze_task_with_progress_callback(
        self, sample_task, sample_decisions, sample_artifacts
    ):
        """Test that progress callback is passed to AI engine."""
        # Arrange
        from src.analysis.ai_engine import AnalysisResponse, AnalysisType

        progress_events = []

        async def progress_callback(event):
            progress_events.append(event)

        # Create a real AI engine (not mocked) to test progress flow
        mock_llm = AsyncMock()
        mock_llm.analyze = AsyncMock(return_value="{}")

        from unittest.mock import patch

        with patch("src.analysis.ai_engine.LLMAbstraction", return_value=mock_llm):
            from src.analysis.ai_engine import AnalysisAIEngine

            ai_engine = AnalysisAIEngine()
            analyzer = RequirementDivergenceAnalyzer(ai_engine=ai_engine)

            # Act
            await analyzer.analyze_task(
                task=sample_task,
                decisions=sample_decisions,
                artifacts=sample_artifacts,
                progress_callback=progress_callback,
            )

            # Assert
            # Progress callback should have been passed through and invoked
            assert len(progress_events) > 0

    @pytest.mark.asyncio
    async def test_analyze_task_handles_missing_artifacts(
        self, analyzer, sample_task, sample_decisions
    ):
        """Test analyzing task with no artifacts."""
        # Act
        analysis = await analyzer.analyze_task(
            task=sample_task,
            decisions=sample_decisions,
            artifacts=[],  # No artifacts
        )

        # Assert
        # Should still produce analysis
        assert isinstance(analysis, RequirementDivergenceAnalysis)
        assert "artifacts" in analysis.raw_data
        assert len(analysis.raw_data["artifacts"]) == 0

    @pytest.mark.asyncio
    async def test_analyze_task_handles_missing_decisions(
        self, analyzer, sample_task, sample_artifacts
    ):
        """Test analyzing task with no decisions."""
        # Act
        analysis = await analyzer.analyze_task(
            task=sample_task,
            decisions=[],  # No decisions
            artifacts=sample_artifacts,
        )

        # Assert
        # Should still produce analysis
        assert isinstance(analysis, RequirementDivergenceAnalysis)
        assert "decisions" in analysis.raw_data
        assert len(analysis.raw_data["decisions"]) == 0

    @pytest.mark.asyncio
    async def test_build_prompt_template(self, analyzer):
        """Test that prompt template is properly structured."""
        # Act
        template = analyzer.build_prompt_template()

        # Assert
        # Should include placeholders for context
        assert "{task_description}" in template
        assert "{decisions}" in template
        assert "{artifacts}" in template
        # Should mention fidelity score in output
        assert "fidelity_score" in template
        # Should request citations
        assert "citation" in template.lower() or "cite" in template.lower()

    @pytest.mark.asyncio
    async def test_format_decisions_for_prompt(self, analyzer, sample_decisions):
        """Test formatting decisions for LLM prompt."""
        # Act
        formatted = analyzer.format_decisions(sample_decisions)

        # Assert
        assert "Use JWT auth" in formatted
        assert "dec_001" in formatted
        assert "2025-11-04" in formatted

    @pytest.mark.asyncio
    async def test_format_artifacts_for_prompt(self, analyzer, sample_artifacts):
        """Test formatting artifacts for LLM prompt."""
        # Act
        formatted = analyzer.format_artifacts(sample_artifacts)

        # Assert
        assert "login.py" in formatted
        assert "art_001" in formatted
        assert "code" in formatted


class TestRequirementDivergenceIntegration:
    """Integration tests for requirement divergence analysis."""

    @pytest.mark.asyncio
    async def test_end_to_end_analysis_flow(self):
        """Test complete analysis flow from task to result."""
        # This would be an integration test that uses real AI engine
        # For now, we use mocks in unit tests
        pass
