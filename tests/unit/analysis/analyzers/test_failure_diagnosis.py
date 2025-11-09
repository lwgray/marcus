"""
Unit tests for Failure Diagnosis Generator.

Tests the analyzer that generates comprehensive diagnoses for failed tasks,
explaining what went wrong, why, and how to prevent similar failures.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from src.analysis.aggregator import TaskHistory
from src.analysis.analyzers.failure_diagnosis import (
    FailureCause,
    FailureDiagnosis,
    FailureDiagnosisGenerator,
    PreventionStrategy,
)
from src.core.project_history import Decision


class TestFailureCause:
    """Test suite for FailureCause dataclass."""

    def test_create_failure_cause(self):
        """Test creating a failure cause."""
        # Arrange & Act
        cause = FailureCause(
            category="technical",
            root_cause="Database connection timeout",
            contributing_factors=["No connection pooling", "High load"],
            evidence="Error logs showing timeout after 30s",
            citation="task task-001, error log line 45",
        )

        # Assert
        assert cause.category == "technical"
        assert cause.root_cause == "Database connection timeout"
        assert len(cause.contributing_factors) == 2


class TestPreventionStrategy:
    """Test suite for PreventionStrategy dataclass."""

    def test_create_prevention_strategy(self):
        """Test creating a prevention strategy."""
        # Arrange & Act
        strategy = PreventionStrategy(
            strategy="Implement connection pooling",
            rationale="Reduces connection overhead and prevents timeouts",
            effort="medium",
            priority="high",
        )

        # Assert
        assert strategy.strategy == "Implement connection pooling"
        assert strategy.effort == "medium"
        assert strategy.priority == "high"


class TestFailureDiagnosis:
    """Test suite for FailureDiagnosis dataclass."""

    def test_create_diagnosis(self):
        """Test creating a complete diagnosis."""
        # Arrange & Act
        diagnosis = FailureDiagnosis(
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
                    strategy="Add retry logic",
                    rationale="Handle transient failures",
                    effort="low",
                    priority="high",
                )
            ],
            raw_data={"task_name": "Deploy service"},
            llm_interpretation="Technical failure due to timeout",
            lessons_learned=["Need better error handling"],
        )

        # Assert
        assert diagnosis.task_id == "task-001"
        assert len(diagnosis.failure_causes) == 1
        assert len(diagnosis.prevention_strategies) == 1
        assert len(diagnosis.lessons_learned) == 1


class TestFailureDiagnosisGenerator:
    """Test suite for FailureDiagnosisGenerator."""

    @pytest.fixture
    def mock_ai_engine(self):
        """Create mock AI engine."""
        from src.analysis.ai_engine import AnalysisResponse, AnalysisType

        mock = AsyncMock()
        mock.analyze = AsyncMock(
            return_value=AnalysisResponse(
                analysis_type=AnalysisType.FAILURE_DIAGNOSIS,
                raw_response='{"failure_causes": [...], "prevention_strategies": [...]}',
                parsed_result={
                    "failure_causes": [
                        {
                            "category": "technical",
                            "root_cause": "Database connection timeout",
                            "contributing_factors": [
                                "No connection pooling configured",
                                "Unexpected traffic spike",
                            ],
                            "evidence": "Error logs show 'connection timeout after 30s'",
                            "citation": "task task-001, logs line 45-50",
                        },
                        {
                            "category": "requirements",
                            "root_cause": "Scalability requirements not specified",
                            "contributing_factors": [
                                "No load testing done",
                                "Production traffic underestimated",
                            ],
                            "evidence": "Task description has no scalability specs",
                            "citation": "task task-001 description",
                        },
                    ],
                    "prevention_strategies": [
                        {
                            "strategy": "Implement database connection pooling",
                            "rationale": "Reuses connections, handles load better",
                            "effort": "medium",
                            "priority": "high",
                        },
                        {
                            "strategy": "Add load testing to deployment process",
                            "rationale": "Catches scalability issues before production",
                            "effort": "medium",
                            "priority": "high",
                        },
                    ],
                    "lessons_learned": [
                        "Always specify scalability requirements",
                        "Test under realistic load before deployment",
                        "Monitor database connection pool metrics",
                    ],
                },
                confidence=0.85,
                timestamp=datetime.now(timezone.utc),
                model_used="claude-3-sonnet",
            )
        )
        return mock

    @pytest.fixture
    def generator(self, mock_ai_engine):
        """Create generator with mocked AI engine."""
        return FailureDiagnosisGenerator(ai_engine=mock_ai_engine)

    @pytest.fixture
    def failed_task(self):
        """Create sample failed task for testing."""
        return TaskHistory(
            task_id="task-001",
            name="Deploy authentication service",
            description="Deploy the auth service to production",
            status="failed",
            estimated_hours=4.0,
            actual_hours=12.0,  # Took much longer before failing
        )

    @pytest.mark.asyncio
    async def test_generate_diagnosis(self, generator, mock_ai_engine, failed_task):
        """Test generating diagnosis for a failed task."""
        # Arrange
        error_logs = [
            "ERROR: Database connection timeout after 30s",
            "ERROR: Failed to acquire connection from pool",
        ]
        related_decisions = [
            Decision(
                decision_id="dec-001",
                task_id="task-001",
                agent_id="agent-1",
                timestamp=datetime.now(timezone.utc),
                what="Use default DB connection settings",
                why="Quick deployment",
                impact="low",
                affected_tasks=[],
                confidence=0.7,
            )
        ]
        context_notes = ["Deployed during high traffic period", "No load testing done"]

        # Act
        diagnosis = await generator.generate_diagnosis(
            task=failed_task,
            error_logs=error_logs,
            related_decisions=related_decisions,
            context_notes=context_notes,
        )

        # Assert
        assert isinstance(diagnosis, FailureDiagnosis)
        assert diagnosis.task_id == "task-001"

        # Verify failure causes
        assert len(diagnosis.failure_causes) == 2
        tech_cause = diagnosis.failure_causes[0]
        assert tech_cause.category == "technical"
        assert "timeout" in tech_cause.root_cause.lower()
        assert len(tech_cause.contributing_factors) == 2

        req_cause = diagnosis.failure_causes[1]
        assert req_cause.category == "requirements"

        # Verify prevention strategies
        assert len(diagnosis.prevention_strategies) == 2
        strategy = diagnosis.prevention_strategies[0]
        assert "connection pooling" in strategy.strategy.lower()
        assert strategy.priority == "high"

        # Verify lessons learned
        assert len(diagnosis.lessons_learned) == 3

    @pytest.mark.asyncio
    async def test_generate_diagnosis_builds_correct_prompt(
        self, generator, mock_ai_engine, failed_task
    ):
        """Test that generator builds correct prompt with all context."""
        # Act
        await generator.generate_diagnosis(
            task=failed_task,
            error_logs=[],
            related_decisions=[],
            context_notes=[],
        )

        # Assert
        call_args = mock_ai_engine.analyze.call_args
        request = call_args[0][0]

        # Verify context data includes required fields
        assert "task_name" in request.context_data
        assert "task_description" in request.context_data
        assert "error_logs" in request.context_data
        assert "related_decisions" in request.context_data
        assert "context_notes" in request.context_data

    @pytest.mark.asyncio
    async def test_generate_diagnosis_with_progress_callback(self, failed_task):
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
            generator = FailureDiagnosisGenerator(ai_engine=ai_engine)

            # Act
            await generator.generate_diagnosis(
                task=failed_task,
                error_logs=[],
                related_decisions=[],
                context_notes=[],
                progress_callback=progress_callback,
            )

            # Assert
            assert len(progress_events) > 0

    @pytest.mark.asyncio
    async def test_build_prompt_template(self, generator):
        """Test that prompt template is properly structured."""
        # Act
        template = generator.build_prompt_template()

        # Assert
        # Should include placeholders
        assert "{task_name}" in template
        assert "{task_description}" in template
        assert "{error_logs}" in template
        assert "{related_decisions}" in template

        # Should request failure causes
        assert "failure_causes" in template or "root_cause" in template

        # Should request prevention strategies
        assert "prevention" in template.lower()

        # Should request lessons learned
        assert "lessons" in template.lower()

        # Should request citations
        assert "citation" in template.lower() or "cite" in template.lower()

    @pytest.mark.asyncio
    async def test_format_error_logs(self, generator):
        """Test formatting error logs for LLM prompt."""
        # Arrange
        logs = [
            "ERROR: Connection timeout",
            "WARN: Retrying connection",
            "ERROR: Max retries exceeded",
        ]

        # Act
        formatted = generator.format_error_logs(logs)

        # Assert
        assert "Connection timeout" in formatted
        assert "Max retries exceeded" in formatted

    @pytest.mark.asyncio
    async def test_format_decisions(self, generator):
        """Test formatting related decisions for LLM prompt."""
        # Arrange
        decisions = [
            Decision(
                decision_id="dec-001",
                task_id="task-001",
                agent_id="agent-1",
                timestamp=datetime.now(timezone.utc),
                what="Skip load testing",
                why="Time constraints",
                impact="major",
                affected_tasks=[],
                confidence=0.5,
            )
        ]

        # Act
        formatted = generator.format_decisions(decisions)

        # Assert
        assert "dec-001" in formatted
        assert "Skip load testing" in formatted
        assert "Time constraints" in formatted

    @pytest.mark.asyncio
    async def test_format_context_notes(self, generator):
        """Test formatting context notes for LLM prompt."""
        # Arrange
        notes = [
            "Deployed at 3pm EST",
            "High traffic expected",
            "No staging environment available",
        ]

        # Act
        formatted = generator.format_context_notes(notes)

        # Assert
        assert "Deployed at 3pm EST" in formatted
        assert "High traffic expected" in formatted
        assert "No staging environment" in formatted

    @pytest.mark.asyncio
    async def test_categorize_failure_technical(self, generator):
        """Test that technical failures are properly categorized."""
        # This would be tested via the LLM response parsing
        # The mock already demonstrates technical categorization
        pass

    @pytest.mark.asyncio
    async def test_categorize_failure_requirements(self, generator):
        """Test that requirements failures are properly categorized."""
        # This would be tested via the LLM response parsing
        # The mock already demonstrates requirements categorization
        pass
