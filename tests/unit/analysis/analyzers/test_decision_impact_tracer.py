"""
Unit tests for Decision Impact Tracer.

Tests the analyzer that traces how architectural decisions cascade through
the project, showing which tasks were affected and whether impacts were
anticipated.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from src.analysis.analyzers.decision_impact_tracer import (
    DecisionImpactAnalysis,
    DecisionImpactTracer,
    ImpactChain,
    UnexpectedImpact,
)
from src.core.project_history import Decision


class TestImpactChain:
    """Test suite for ImpactChain dataclass."""

    def test_create_impact_chain(self):
        """Test creating an impact chain."""
        # Arrange & Act
        chain = ImpactChain(
            decision_id="dec-001",
            decision_summary="Use microservices architecture",
            direct_impacts=["task-002", "task-003"],
            indirect_impacts=["task-005", "task-006"],
            depth=2,
            citation="decision dec-001 at 2025-11-01",
        )

        # Assert
        assert chain.decision_id == "dec-001"
        assert len(chain.direct_impacts) == 2
        assert len(chain.indirect_impacts) == 2
        assert chain.depth == 2


class TestUnexpectedImpact:
    """Test suite for UnexpectedImpact dataclass."""

    def test_create_unexpected_impact(self):
        """Test creating an unexpected impact."""
        # Arrange & Act
        impact = UnexpectedImpact(
            decision_id="dec-001",
            decision_summary="Use microservices",
            affected_task_id="task-007",
            affected_task_name="Update login",
            anticipated=False,
            actual_impact="Had to refactor auth across 3 services",
            severity="major",
            citation="task task-007, decision dec-001",
        )

        # Assert
        assert impact.decision_id == "dec-001"
        assert impact.affected_task_id == "task-007"
        assert impact.anticipated is False
        assert impact.severity == "major"


class TestDecisionImpactAnalysis:
    """Test suite for DecisionImpactAnalysis dataclass."""

    def test_create_analysis(self):
        """Test creating a complete analysis."""
        # Arrange & Act
        analysis = DecisionImpactAnalysis(
            decision_id="dec-001",
            impact_chains=[
                ImpactChain(
                    decision_id="dec-001",
                    decision_summary="Use GraphQL",
                    direct_impacts=["task-002"],
                    indirect_impacts=[],
                    depth=1,
                    citation="dec-001",
                )
            ],
            unexpected_impacts=[],
            raw_data={"decision": "Use GraphQL"},
            llm_interpretation="Decision had limited scope",
            recommendations=["Document API changes"],
        )

        # Assert
        assert analysis.decision_id == "dec-001"
        assert len(analysis.impact_chains) == 1
        assert len(analysis.unexpected_impacts) == 0
        assert len(analysis.recommendations) == 1


class TestDecisionImpactTracer:
    """Test suite for DecisionImpactTracer."""

    @pytest.fixture
    def mock_ai_engine(self):
        """Create mock AI engine."""
        from src.analysis.ai_engine import AnalysisResponse, AnalysisType

        mock = AsyncMock()
        mock.analyze = AsyncMock(
            return_value=AnalysisResponse(
                analysis_type=AnalysisType.DECISION_IMPACT,
                raw_response='{"impact_chains": [...], "unexpected_impacts": [...]}',
                parsed_result={
                    "impact_chains": [
                        {
                            "decision_id": "dec-001",
                            "decision_summary": "Use microservices architecture",
                            "direct_impacts": ["task-002", "task-003"],
                            "indirect_impacts": ["task-005"],
                            "depth": 2,
                            "citation": "decision dec-001 at 2025-11-01T10:00:00",
                        }
                    ],
                    "unexpected_impacts": [
                        {
                            "decision_id": "dec-001",
                            "decision_summary": "Use microservices",
                            "affected_task_id": "task-007",
                            "affected_task_name": "Update login flow",
                            "anticipated": False,
                            "actual_impact": "Had to refactor across services",
                            "severity": "major",
                            "citation": "task task-007",
                        }
                    ],
                    "recommendations": [
                        "Better impact prediction needed",
                        "Document cross-service dependencies",
                    ],
                },
                confidence=0.85,
                timestamp=datetime.now(timezone.utc),
                model_used="claude-3-sonnet",
            )
        )
        return mock

    @pytest.fixture
    def tracer(self, mock_ai_engine):
        """Create tracer with mocked AI engine."""
        return DecisionImpactTracer(ai_engine=mock_ai_engine)

    @pytest.fixture
    def sample_decision(self):
        """Create sample decision for testing."""
        return Decision(
            decision_id="dec-001",
            task_id="task-001",
            agent_id="agent-1",
            timestamp=datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc),
            what="Use microservices architecture",
            why="Better scalability and team autonomy",
            impact="major",
            affected_tasks=["task-002", "task-003"],
            confidence=0.8,
        )

    @pytest.mark.asyncio
    async def test_trace_decision_impact(self, tracer, mock_ai_engine, sample_decision):
        """Test tracing impact of a single decision."""
        # Arrange
        related_decisions: list[Decision] = []
        all_tasks = [
            {"task_id": "task-002", "name": "Build API gateway"},
            {"task_id": "task-003", "name": "Setup service mesh"},
            {"task_id": "task-005", "name": "Configure monitoring"},
            {"task_id": "task-007", "name": "Update login flow"},
        ]

        # Act
        analysis = await tracer.trace_decision_impact(
            decision=sample_decision,
            related_decisions=related_decisions,
            all_tasks=all_tasks,
        )

        # Assert
        assert isinstance(analysis, DecisionImpactAnalysis)
        assert analysis.decision_id == "dec-001"
        assert len(analysis.impact_chains) == 1
        assert len(analysis.unexpected_impacts) == 1
        assert len(analysis.recommendations) == 2

        # Verify impact chain
        chain = analysis.impact_chains[0]
        assert chain.decision_id == "dec-001"
        assert len(chain.direct_impacts) == 2
        assert len(chain.indirect_impacts) == 1
        assert chain.depth == 2

        # Verify unexpected impact
        unexpected = analysis.unexpected_impacts[0]
        assert unexpected.decision_id == "dec-001"
        assert unexpected.affected_task_id == "task-007"
        assert unexpected.anticipated is False
        assert unexpected.severity == "major"

    @pytest.mark.asyncio
    async def test_trace_decision_builds_correct_prompt(
        self, tracer, mock_ai_engine, sample_decision
    ):
        """Test that tracer builds correct prompt with all context."""
        # Act
        await tracer.trace_decision_impact(
            decision=sample_decision,
            related_decisions=[],
            all_tasks=[],
        )

        # Assert
        call_args = mock_ai_engine.analyze.call_args
        request = call_args[0][0]

        # Verify context data includes required fields
        assert "decision_what" in request.context_data
        assert "decision_why" in request.context_data
        assert "anticipated_impacts" in request.context_data
        assert "related_decisions" in request.context_data
        assert "all_tasks" in request.context_data

    @pytest.mark.asyncio
    async def test_trace_decision_with_no_unexpected_impacts(self, mock_ai_engine):
        """Test tracing decision where all impacts were anticipated."""
        # Arrange
        from src.analysis.ai_engine import AnalysisResponse, AnalysisType

        mock_ai_engine.analyze = AsyncMock(
            return_value=AnalysisResponse(
                analysis_type=AnalysisType.DECISION_IMPACT,
                raw_response='{"impact_chains": [...], "unexpected_impacts": []}',
                parsed_result={
                    "impact_chains": [
                        {
                            "decision_id": "dec-002",
                            "decision_summary": "Use PostgreSQL",
                            "direct_impacts": ["task-010"],
                            "indirect_impacts": [],
                            "depth": 1,
                            "citation": "decision dec-002",
                        }
                    ],
                    "unexpected_impacts": [],
                    "recommendations": ["Good impact prediction"],
                },
                confidence=0.9,
                timestamp=datetime.now(timezone.utc),
                model_used="claude-3-sonnet",
            )
        )

        tracer = DecisionImpactTracer(ai_engine=mock_ai_engine)

        decision = Decision(
            decision_id="dec-002",
            task_id="task-009",
            agent_id="agent-1",
            timestamp=datetime.now(timezone.utc),
            what="Use PostgreSQL for database",
            why="Better ACID guarantees",
            impact="low",
            affected_tasks=["task-010"],
            confidence=0.9,
        )

        # Act
        analysis = await tracer.trace_decision_impact(
            decision=decision,
            related_decisions=[],
            all_tasks=[],
        )

        # Assert
        assert len(analysis.impact_chains) == 1
        assert len(analysis.unexpected_impacts) == 0
        assert "Good impact prediction" in analysis.recommendations

    @pytest.mark.asyncio
    async def test_trace_decision_with_progress_callback(self, sample_decision):
        """Test that progress callback is passed to AI engine."""
        # Arrange
        from src.analysis.ai_engine import AnalysisResponse, AnalysisType

        progress_events = []

        async def progress_callback(event):
            progress_events.append(event)

        # Create real AI engine (not fully mocked) for progress flow
        mock_llm = AsyncMock()
        mock_llm.analyze = AsyncMock(return_value="{}")

        from unittest.mock import patch

        with patch("src.analysis.ai_engine.LLMAbstraction", return_value=mock_llm):
            from src.analysis.ai_engine import AnalysisAIEngine

            ai_engine = AnalysisAIEngine()
            tracer = DecisionImpactTracer(ai_engine=ai_engine)

            # Act
            await tracer.trace_decision_impact(
                decision=sample_decision,
                related_decisions=[],
                all_tasks=[],
                progress_callback=progress_callback,
            )

            # Assert
            assert len(progress_events) > 0

    @pytest.mark.asyncio
    async def test_build_prompt_template(self, tracer):
        """Test that prompt template is properly structured."""
        # Act
        template = tracer.build_prompt_template()

        # Assert
        # Should include placeholders for context
        assert "{decision_what}" in template
        assert "{decision_why}" in template
        assert "{anticipated_impacts}" in template
        assert "{all_tasks}" in template
        # Should request impact chains
        assert "impact_chains" in template
        # Should request unexpected impacts
        assert "unexpected_impacts" in template or "unexpected" in template.lower()
        # Should request citations
        assert "citation" in template.lower() or "cite" in template.lower()

    @pytest.mark.asyncio
    async def test_format_tasks_for_prompt(self, tracer):
        """Test formatting tasks for LLM prompt."""
        # Arrange
        tasks = [
            {"task_id": "task-001", "name": "Build API", "status": "completed"},
            {"task_id": "task-002", "name": "Add tests", "status": "completed"},
        ]

        # Act
        formatted = tracer.format_tasks(tasks)

        # Assert
        assert "task-001" in formatted
        assert "Build API" in formatted
        assert "task-002" in formatted
        assert "Add tests" in formatted

    @pytest.mark.asyncio
    async def test_format_decisions_for_prompt(self, tracer):
        """Test formatting related decisions for LLM prompt."""
        # Arrange
        decisions = [
            Decision(
                decision_id="dec-002",
                task_id="task-002",
                agent_id="agent-1",
                timestamp=datetime.now(timezone.utc),
                what="Use REST API",
                why="Standard approach",
                impact="low",
                affected_tasks=[],
                confidence=0.8,
            )
        ]

        # Act
        formatted = tracer.format_decisions(decisions)

        # Assert
        assert "dec-002" in formatted
        assert "Use REST API" in formatted
        assert "Standard approach" in formatted
