"""
Unit tests for Phase 2 AI engine integration.

Tests the analysis-specific AI engine wrapper that provides structured prompts
and response parsing for post-project analysis.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.analysis.ai_engine import (
    AnalysisAIEngine,
    AnalysisRequest,
    AnalysisResponse,
    AnalysisType,
)


class TestAnalysisRequest:
    """Test suite for AnalysisRequest dataclass."""

    def test_create_analysis_request(self):
        """Test creating an analysis request."""
        # Arrange & Act
        request = AnalysisRequest(
            analysis_type=AnalysisType.REQUIREMENT_DIVERGENCE,
            project_id="proj-123",
            task_id="task-456",
            context_data={"requirement": "Build login", "implementation": "Built auth"},
            prompt_template="Compare {requirement} vs {implementation}",
        )

        # Assert
        assert request.analysis_type == AnalysisType.REQUIREMENT_DIVERGENCE
        assert request.project_id == "proj-123"
        assert request.task_id == "task-456"
        assert "requirement" in request.context_data
        assert "{requirement}" in request.prompt_template


class TestAnalysisResponse:
    """Test suite for AnalysisResponse dataclass."""

    def test_create_analysis_response(self):
        """Test creating an analysis response."""
        # Arrange & Act
        response = AnalysisResponse(
            analysis_type=AnalysisType.REQUIREMENT_DIVERGENCE,
            raw_response="LLM output here",
            parsed_result={"fidelity_score": 0.85, "divergences": []},
            confidence=0.9,
            timestamp=datetime.now(timezone.utc),
            model_used="claude-3-sonnet",
        )

        # Assert
        assert response.analysis_type == AnalysisType.REQUIREMENT_DIVERGENCE
        assert response.raw_response == "LLM output here"
        assert response.parsed_result["fidelity_score"] == 0.85
        assert response.confidence == 0.9
        assert response.model_used == "claude-3-sonnet"


class TestAnalysisAIEngine:
    """Test suite for AnalysisAIEngine."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM abstraction."""
        mock = AsyncMock()
        mock.analyze = AsyncMock(return_value="Analysis result from LLM")
        return mock

    @pytest.fixture
    def engine(self, mock_llm):
        """Create AI engine with mocked LLM."""
        with patch("src.analysis.ai_engine.LLMAbstraction", return_value=mock_llm):
            return AnalysisAIEngine()

    @pytest.mark.asyncio
    async def test_analyze_basic_request(self, engine, mock_llm):
        """Test basic analysis request."""
        # Arrange
        request = AnalysisRequest(
            analysis_type=AnalysisType.REQUIREMENT_DIVERGENCE,
            project_id="proj-1",
            task_id="task-1",
            context_data={"req": "feature X", "impl": "built feature X"},
            prompt_template="Compare {req} vs {impl}",
        )

        # Act
        response = await engine.analyze(request)

        # Assert
        assert isinstance(response, AnalysisResponse)
        assert response.analysis_type == AnalysisType.REQUIREMENT_DIVERGENCE
        assert response.raw_response == "Analysis result from LLM"
        assert mock_llm.analyze.call_count == 1

    @pytest.mark.asyncio
    async def test_analyze_formats_prompt_with_context(self, engine, mock_llm):
        """Test that context data is properly formatted into prompts."""
        # Arrange
        request = AnalysisRequest(
            analysis_type=AnalysisType.DECISION_IMPACT,
            project_id="proj-1",
            task_id=None,
            context_data={
                "decision": "Use PostgreSQL",
                "affected_tasks": ["backend", "deployment"],
            },
            prompt_template="Decision: {decision}. Affected: {affected_tasks}",
        )

        # Act
        await engine.analyze(request)

        # Assert
        # Verify prompt was formatted with context data
        call_args = mock_llm.analyze.call_args
        prompt = call_args.kwargs["prompt"]
        assert "Use PostgreSQL" in prompt
        assert "affected_tasks" in prompt or "backend" in prompt

    @pytest.mark.asyncio
    async def test_analyze_includes_system_instructions(self, engine, mock_llm):
        """Test that analysis includes critical system instructions."""
        # Arrange
        request = AnalysisRequest(
            analysis_type=AnalysisType.REQUIREMENT_DIVERGENCE,
            project_id="proj-1",
            task_id="task-1",
            context_data={"data": "test"},
            prompt_template="Analyze {data}",
        )

        # Act
        await engine.analyze(request)

        # Assert
        call_args = mock_llm.analyze.call_args
        prompt = call_args.kwargs["prompt"]
        # System instructions should emphasize citations
        assert "cite" in prompt.lower() or "citation" in prompt.lower()

    @pytest.mark.asyncio
    async def test_analyze_with_progress_callback(self, engine, mock_llm):
        """Test analysis with progress reporting."""
        # Arrange
        progress_events = []

        async def progress_callback(event):
            progress_events.append(event)

        request = AnalysisRequest(
            analysis_type=AnalysisType.INSTRUCTION_QUALITY,
            project_id="proj-1",
            task_id="task-1",
            context_data={"instruction": "test"},
            prompt_template="Analyze {instruction}",
        )

        # Act
        await engine.analyze(request, progress_callback=progress_callback)

        # Assert
        # Should have at least start and end progress events
        assert len(progress_events) >= 2
        assert progress_events[0].current == 0  # Start
        assert progress_events[-1].current == progress_events[-1].total  # Complete

    @pytest.mark.asyncio
    async def test_analyze_caches_results(self, engine, mock_llm):
        """Test that identical requests use cached results."""
        # Arrange
        request = AnalysisRequest(
            analysis_type=AnalysisType.REQUIREMENT_DIVERGENCE,
            project_id="proj-1",
            task_id="task-1",
            context_data={"data": "test"},
            prompt_template="Analyze {data}",
        )

        # Act - make same request twice
        response1 = await engine.analyze(request, use_cache=True)
        response2 = await engine.analyze(request, use_cache=True)

        # Assert
        # LLM should only be called once (second uses cache)
        assert mock_llm.analyze.call_count == 1
        assert response1.raw_response == response2.raw_response

    @pytest.mark.asyncio
    async def test_analyze_skip_cache_when_disabled(self, engine, mock_llm):
        """Test that cache can be bypassed."""
        # Arrange
        request = AnalysisRequest(
            analysis_type=AnalysisType.REQUIREMENT_DIVERGENCE,
            project_id="proj-1",
            task_id="task-1",
            context_data={"data": "test"},
            prompt_template="Analyze {data}",
        )

        # Act - make same request twice with cache disabled
        await engine.analyze(request, use_cache=False)
        await engine.analyze(request, use_cache=False)

        # Assert
        # LLM should be called twice (cache bypassed)
        assert mock_llm.analyze.call_count == 2

    @pytest.mark.asyncio
    async def test_analyze_handles_llm_failure(self, engine, mock_llm):
        """Test graceful handling of LLM failures."""
        # Arrange
        mock_llm.analyze.side_effect = Exception("API rate limit exceeded")
        request = AnalysisRequest(
            analysis_type=AnalysisType.FAILURE_DIAGNOSIS,
            project_id="proj-1",
            task_id="task-1",
            context_data={"error": "test"},
            prompt_template="Diagnose {error}",
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await engine.analyze(request)

        assert "rate limit" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_parse_json_response(self, engine):
        """Test parsing JSON from LLM response."""
        # Arrange
        json_response = '{"fidelity_score": 0.85, "divergences": ["missing auth"]}'

        # Act
        parsed = engine.parse_json_response(json_response)

        # Assert
        assert parsed["fidelity_score"] == 0.85
        assert "missing auth" in parsed["divergences"]

    @pytest.mark.asyncio
    async def test_parse_json_response_with_markdown(self, engine):
        """Test parsing JSON wrapped in markdown code blocks."""
        # Arrange
        markdown_response = """```json
{
  "fidelity_score": 0.85,
  "divergences": []
}
```"""

        # Act
        parsed = engine.parse_json_response(markdown_response)

        # Assert
        assert parsed["fidelity_score"] == 0.85
        assert parsed["divergences"] == []

    @pytest.mark.asyncio
    async def test_parse_json_response_invalid(self, engine):
        """Test handling of invalid JSON responses."""
        # Arrange
        invalid_json = "This is not JSON"

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            engine.parse_json_response(invalid_json)

        assert "JSON" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_build_system_prompt_includes_citations(self, engine):
        """Test that system prompt emphasizes citations."""
        # Act
        system_prompt = engine.build_system_prompt(AnalysisType.REQUIREMENT_DIVERGENCE)

        # Assert
        assert "task_id" in system_prompt.lower()
        assert "decision_id" in system_prompt.lower() or "cite" in system_prompt.lower()
        assert "timestamp" in system_prompt.lower()

    @pytest.mark.asyncio
    async def test_build_system_prompt_different_per_type(self, engine):
        """Test that different analysis types get specialized instructions."""
        # Act
        req_prompt = engine.build_system_prompt(AnalysisType.REQUIREMENT_DIVERGENCE)
        decision_prompt = engine.build_system_prompt(AnalysisType.DECISION_IMPACT)

        # Assert
        # Each type should have specific instructions
        assert req_prompt != decision_prompt
        assert "requirement" in req_prompt.lower() or "fidelity" in req_prompt.lower()
        assert (
            "decision" in decision_prompt.lower() or "impact" in decision_prompt.lower()
        )

    @pytest.mark.asyncio
    async def test_get_cache_key(self, engine):
        """Test cache key generation."""
        # Arrange
        request = AnalysisRequest(
            analysis_type=AnalysisType.REQUIREMENT_DIVERGENCE,
            project_id="proj-1",
            task_id="task-1",
            context_data={"data": "test"},
            prompt_template="Analyze {data}",
        )

        # Act
        cache_key1 = engine.get_cache_key(request)

        # Different request should have different key
        request2 = AnalysisRequest(
            analysis_type=AnalysisType.REQUIREMENT_DIVERGENCE,
            project_id="proj-1",
            task_id="task-2",  # Different task
            context_data={"data": "test"},
            prompt_template="Analyze {data}",
        )
        cache_key2 = engine.get_cache_key(request2)

        # Assert
        assert cache_key1 != cache_key2
        assert isinstance(cache_key1, str)
        assert len(cache_key1) > 10  # Should be a hash


class TestAnalysisType:
    """Test suite for AnalysisType enum."""

    def test_all_analysis_types_defined(self):
        """Test that all required analysis types are defined."""
        # Assert
        assert hasattr(AnalysisType, "REQUIREMENT_DIVERGENCE")
        assert hasattr(AnalysisType, "DECISION_IMPACT")
        assert hasattr(AnalysisType, "INSTRUCTION_QUALITY")
        assert hasattr(AnalysisType, "FAILURE_DIAGNOSIS")
        assert hasattr(AnalysisType, "OVERALL_ASSESSMENT")

    def test_analysis_type_values(self):
        """Test analysis type string values."""
        # Assert
        assert AnalysisType.REQUIREMENT_DIVERGENCE.value == "requirement_divergence"
        assert AnalysisType.DECISION_IMPACT.value == "decision_impact"
        assert AnalysisType.INSTRUCTION_QUALITY.value == "instruction_quality"
        assert AnalysisType.FAILURE_DIAGNOSIS.value == "failure_diagnosis"
        assert AnalysisType.OVERALL_ASSESSMENT.value == "overall_assessment"
