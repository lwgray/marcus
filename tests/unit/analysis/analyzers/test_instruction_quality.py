"""
Unit tests for Instruction Quality Analyzer.

Tests the analyzer that evaluates how clear and complete task instructions
were, and whether ambiguity caused delays or errors.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from src.analysis.aggregator import TaskHistory
from src.analysis.analyzers.instruction_quality import (
    AmbiguityIssue,
    InstructionQualityAnalysis,
    InstructionQualityAnalyzer,
    QualityScore,
)


class TestQualityScore:
    """Test suite for QualityScore dataclass."""

    def test_create_quality_score(self):
        """Test creating a quality score."""
        # Arrange & Act
        score = QualityScore(
            clarity=0.8,
            completeness=0.9,
            specificity=0.7,
            overall=0.8,
        )

        # Assert
        assert score.clarity == 0.8
        assert score.completeness == 0.9
        assert score.specificity == 0.7
        assert score.overall == 0.8


class TestAmbiguityIssue:
    """Test suite for AmbiguityIssue dataclass."""

    def test_create_ambiguity_issue(self):
        """Test creating an ambiguity issue."""
        # Arrange & Act
        issue = AmbiguityIssue(
            task_id="task-001",
            task_name="Build login",
            ambiguous_aspect="authentication method",
            evidence="No specification of OAuth vs JWT",
            consequence="Had to guess, chose JWT, client wanted OAuth",
            severity="major",
            citation="task task-001 description",
        )

        # Assert
        assert issue.task_id == "task-001"
        assert issue.ambiguous_aspect == "authentication method"
        assert issue.severity == "major"


class TestInstructionQualityAnalysis:
    """Test suite for InstructionQualityAnalysis dataclass."""

    def test_create_analysis(self):
        """Test creating a complete analysis."""
        # Arrange & Act
        analysis = InstructionQualityAnalysis(
            task_id="task-001",
            quality_scores=QualityScore(
                clarity=0.8, completeness=0.9, specificity=0.7, overall=0.8
            ),
            ambiguity_issues=[],
            raw_data={"task_description": "Build login feature"},
            llm_interpretation="Instructions were mostly clear",
            recommendations=["Add auth method specification"],
        )

        # Assert
        assert analysis.task_id == "task-001"
        assert analysis.quality_scores.overall == 0.8
        assert len(analysis.ambiguity_issues) == 0
        assert len(analysis.recommendations) == 1


class TestInstructionQualityAnalyzer:
    """Test suite for InstructionQualityAnalyzer."""

    @pytest.fixture
    def mock_ai_engine(self):
        """Create mock AI engine."""
        from src.analysis.ai_engine import AnalysisResponse, AnalysisType

        mock = AsyncMock()
        mock.analyze = AsyncMock(
            return_value=AnalysisResponse(
                analysis_type=AnalysisType.INSTRUCTION_QUALITY,
                raw_response='{"quality_scores": {...}, "ambiguity_issues": [...]}',
                parsed_result={
                    "quality_scores": {
                        "clarity": 0.6,
                        "completeness": 0.5,
                        "specificity": 0.4,
                        "overall": 0.5,
                    },
                    "ambiguity_issues": [
                        {
                            "task_id": "task-001",
                            "task_name": "Build login",
                            "ambiguous_aspect": "authentication method not specified",
                            "evidence": "Description says 'user login' without method",
                            "consequence": "Had to ask for clarification, 2 day delay",
                            "severity": "major",
                            "citation": "task task-001 description line 1",
                        }
                    ],
                    "recommendations": [
                        "Specify authentication method (OAuth, JWT, etc.)",
                        "Add acceptance criteria for login flow",
                    ],
                },
                confidence=0.85,
                timestamp=datetime.now(timezone.utc),
                model_used="claude-3-sonnet",
            )
        )
        return mock

    @pytest.fixture
    def analyzer(self, mock_ai_engine):
        """Create analyzer with mocked AI engine."""
        return InstructionQualityAnalyzer(ai_engine=mock_ai_engine)

    @pytest.fixture
    def sample_task(self):
        """Create sample task for testing."""
        return TaskHistory(
            task_id="task-001",
            name="Build login feature",
            description="Implement user login",
            status="completed",
            estimated_hours=4.0,
            actual_hours=8.0,  # Took longer - possible ambiguity indicator
        )

    @pytest.mark.asyncio
    async def test_analyze_instruction_quality(
        self, analyzer, mock_ai_engine, sample_task
    ):
        """Test analyzing instruction quality for a task."""
        # Arrange
        clarifications = [
            {
                "question": "Which auth method to use?",
                "answer": "Use OAuth2",
                "timestamp": "2025-11-01T10:00:00Z",
            }
        ]
        implementation_notes = [
            "Had to research OAuth2 implementation",
            "Unclear if session-based or token-based",
        ]

        # Act
        analysis = await analyzer.analyze_instruction_quality(
            task=sample_task,
            clarifications=clarifications,
            implementation_notes=implementation_notes,
        )

        # Assert
        assert isinstance(analysis, InstructionQualityAnalysis)
        assert analysis.task_id == "task-001"

        # Verify quality scores
        scores = analysis.quality_scores
        assert scores.clarity == 0.6
        assert scores.completeness == 0.5
        assert scores.specificity == 0.4
        assert scores.overall == 0.5

        # Verify ambiguity issues
        assert len(analysis.ambiguity_issues) == 1
        issue = analysis.ambiguity_issues[0]
        assert issue.task_id == "task-001"
        assert "authentication method" in issue.ambiguous_aspect
        assert issue.severity == "major"

        # Verify recommendations
        assert len(analysis.recommendations) == 2

    @pytest.mark.asyncio
    async def test_analyze_high_quality_instructions(self, mock_ai_engine):
        """Test analyzing task with clear, complete instructions."""
        # Arrange
        from src.analysis.ai_engine import AnalysisResponse, AnalysisType

        mock_ai_engine.analyze = AsyncMock(
            return_value=AnalysisResponse(
                analysis_type=AnalysisType.INSTRUCTION_QUALITY,
                raw_response='{"quality_scores": {...}, "ambiguity_issues": []}',
                parsed_result={
                    "quality_scores": {
                        "clarity": 0.95,
                        "completeness": 0.9,
                        "specificity": 0.9,
                        "overall": 0.92,
                    },
                    "ambiguity_issues": [],
                    "recommendations": ["Excellent instructions, no changes needed"],
                },
                confidence=0.9,
                timestamp=datetime.now(timezone.utc),
                model_used="claude-3-sonnet",
            )
        )

        analyzer = InstructionQualityAnalyzer(ai_engine=mock_ai_engine)

        task = TaskHistory(
            task_id="task-002",
            name="Add logout endpoint",
            description=(
                "Create POST /api/logout endpoint that:\n"
                "1. Accepts JWT token in Authorization header\n"
                "2. Invalidates the token in Redis\n"
                "3. Returns 200 OK with {success: true}\n"
                "4. Returns 401 if token invalid\n"
                "Tech: Express.js, Redis client"
            ),
            status="completed",
            estimated_hours=2.0,
            actual_hours=2.5,
        )

        # Act
        analysis = await analyzer.analyze_instruction_quality(
            task=task,
            clarifications=[],
            implementation_notes=[],
        )

        # Assert
        assert analysis.quality_scores.overall > 0.9
        assert len(analysis.ambiguity_issues) == 0
        assert "Excellent" in analysis.recommendations[0]

    @pytest.mark.asyncio
    async def test_analyze_builds_correct_prompt(
        self, analyzer, mock_ai_engine, sample_task
    ):
        """Test that analyzer builds correct prompt with all context."""
        # Act
        await analyzer.analyze_instruction_quality(
            task=sample_task,
            clarifications=[],
            implementation_notes=[],
        )

        # Assert
        call_args = mock_ai_engine.analyze.call_args
        request = call_args[0][0]

        # Verify context data includes required fields
        assert "task_description" in request.context_data
        assert "task_name" in request.context_data
        assert "clarifications" in request.context_data
        assert "implementation_notes" in request.context_data
        assert "time_variance" in request.context_data

    @pytest.mark.asyncio
    async def test_analyze_with_progress_callback(self, sample_task):
        """Test that progress callback is passed to AI engine."""
        # Arrange
        progress_events = []

        async def progress_callback(event):
            progress_events.append(event)

        # Create real AI engine for progress flow
        mock_llm = AsyncMock()
        mock_llm.analyze = AsyncMock(return_value="{}")

        from unittest.mock import patch

        with patch("src.analysis.ai_engine.LLMAbstraction", return_value=mock_llm):
            from src.analysis.ai_engine import AnalysisAIEngine

            ai_engine = AnalysisAIEngine()
            analyzer = InstructionQualityAnalyzer(ai_engine=ai_engine)

            # Act
            await analyzer.analyze_instruction_quality(
                task=sample_task,
                clarifications=[],
                implementation_notes=[],
                progress_callback=progress_callback,
            )

            # Assert
            assert len(progress_events) > 0

    @pytest.mark.asyncio
    async def test_build_prompt_template(self, analyzer):
        """Test that prompt template is properly structured."""
        # Act
        template = analyzer.build_prompt_template()

        # Assert
        # Should include placeholders
        assert "{task_description}" in template
        assert "{task_name}" in template
        assert "{clarifications}" in template
        assert "{implementation_notes}" in template

        # Should request quality scores
        assert "clarity" in template
        assert "completeness" in template
        assert "specificity" in template

        # Should request ambiguity issues
        assert "ambiguity" in template.lower()

        # Should request citations
        assert "citation" in template.lower() or "cite" in template.lower()

    @pytest.mark.asyncio
    async def test_format_clarifications(self, analyzer):
        """Test formatting clarifications for LLM prompt."""
        # Arrange
        clarifications = [
            {
                "question": "Which database to use?",
                "answer": "PostgreSQL",
                "timestamp": "2025-11-01T10:00:00Z",
            },
            {
                "question": "What auth method?",
                "answer": "JWT",
                "timestamp": "2025-11-01T11:00:00Z",
            },
        ]

        # Act
        formatted = analyzer.format_clarifications(clarifications)

        # Assert
        assert "Which database to use?" in formatted
        assert "PostgreSQL" in formatted
        assert "What auth method?" in formatted
        assert "JWT" in formatted

    @pytest.mark.asyncio
    async def test_format_implementation_notes(self, analyzer):
        """Test formatting implementation notes for LLM prompt."""
        # Arrange
        notes = [
            "Had to research OAuth2 flow",
            "Unclear about token expiration policy",
            "No spec for error messages",
        ]

        # Act
        formatted = analyzer.format_implementation_notes(notes)

        # Assert
        assert "Had to research OAuth2 flow" in formatted
        assert "Unclear about token expiration" in formatted
        assert "No spec for error messages" in formatted

    @pytest.mark.asyncio
    async def test_calculate_time_variance(self, analyzer):
        """Test calculating time variance indicator."""
        # Test case 1: Took twice as long
        task1 = TaskHistory(
            task_id="task-001",
            name="Test",
            description="Test",
            status="completed",
            estimated_hours=4.0,
            actual_hours=8.0,
        )
        variance1 = analyzer.calculate_time_variance(task1)
        assert variance1 == 2.0  # 100% over estimate

        # Test case 2: Exactly on time
        task2 = TaskHistory(
            task_id="task-002",
            name="Test",
            description="Test",
            status="completed",
            estimated_hours=4.0,
            actual_hours=4.0,
        )
        variance2 = analyzer.calculate_time_variance(task2)
        assert variance2 == 1.0  # Exactly as estimated

        # Test case 3: Faster than expected
        task3 = TaskHistory(
            task_id="task-003",
            name="Test",
            description="Test",
            status="completed",
            estimated_hours=4.0,
            actual_hours=2.0,
        )
        variance3 = analyzer.calculate_time_variance(task3)
        assert variance3 == 0.5  # 50% under estimate
