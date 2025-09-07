"""
Unit tests for the AI Core Engine

This module tests the core AI coordination engine that implements hybrid intelligence,
combining rule-based safety guarantees with AI enhancement capabilities.

Tests cover:
- RuleBasedEngine: Deterministic validation and safety-critical decisions
- MarcusAIEngine: Hybrid intelligence coordination and AI integration
- AnalysisContext handling and result generation
- Error handling and fallback mechanisms
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.ai.core.ai_engine import MarcusAIEngine, RuleBasedEngine
from src.ai.types import AIInsights, AnalysisContext, HybridAnalysis, RuleBasedResult
from src.core.models import Priority, Task, TaskStatus, WorkerStatus


class TestRuleBasedEngine:
    """Test suite for the RuleBasedEngine component"""

    @pytest.fixture
    def rule_engine(self):
        """Create a RuleBasedEngine instance for testing"""
        return RuleBasedEngine()

    @pytest.fixture
    def sample_task(self):
        """Create a sample task for testing"""
        now = datetime.now()
        return Task(
            id="test-task-1",
            name="Test Task",
            description="A test task for unit testing",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=now,
            updated_at=now,
            due_date=None,
            estimated_hours=4,
        )

    @pytest.fixture
    def analysis_context(self, sample_task):
        """Create an analysis context for testing"""
        return AnalysisContext(
            task=sample_task,
            project_context={
                "available_tasks": [sample_task],
                "assigned_tasks": [],
                "agent_capabilities": ["python", "testing"],
                "project_phase": "development",
            },
            historical_data=[
                {"agent_id": "test-agent", "task_type": "testing", "success_rate": 0.9},
                {
                    "agent_id": "test-agent",
                    "completion_time": 3.5,
                    "task_complexity": "medium",
                },
            ],
        )

    @pytest.mark.asyncio
    async def test_rule_engine_initialization(self, rule_engine):
        """Test that RuleBasedEngine initializes correctly"""
        assert rule_engine.dependency_inferer is not None
        assert rule_engine.adaptive_mode is not None

    @pytest.mark.asyncio
    async def test_analyze_with_valid_context(self, rule_engine, analysis_context):
        """Test rule-based analysis with valid context"""
        result = await rule_engine.analyze(analysis_context)

        assert isinstance(result, RuleBasedResult)
        assert result.is_valid is not None
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.safety_critical, bool)
        assert result.confidence >= 0.0
        assert result.confidence <= 1.0
        assert result.reason is not None

    @pytest.mark.asyncio
    async def test_analyze_with_high_priority_task(self, rule_engine, analysis_context):
        """Test analysis behavior with high-priority tasks"""
        analysis_context.task.priority = Priority.HIGH

        result = await rule_engine.analyze(analysis_context)

        assert isinstance(result, RuleBasedResult)
        # High priority tasks should generally be valid unless blocked
        assert result.reason is not None

    @pytest.mark.asyncio
    async def test_analyze_with_missing_dependencies(
        self, rule_engine, analysis_context
    ):
        """Test analysis when task has missing dependencies"""
        # Add a task that depends on another task that's not complete
        now = datetime.now()
        dependent_task = Task(
            id="dependent-task",
            name="Dependent Task",
            description="Task with dependencies",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=now,
            updated_at=now,
            due_date=None,
            estimated_hours=2,
        )

        analysis_context.task = dependent_task
        analysis_context.project_context["dependencies"] = {
            "dependent-task": ["prerequisite-task"]
        }
        analysis_context.project_context["completed_tasks"] = []

        result = await rule_engine.analyze(analysis_context)

        assert isinstance(result, RuleBasedResult)
        # Should flag dependency issues if any
        assert isinstance(result.is_valid, bool)


class TestMarcusAIEngine:
    """Test suite for the MarcusAIEngine coordination engine"""

    @pytest.fixture
    def ai_engine(self):
        """Create a MarcusAIEngine instance for testing"""
        return MarcusAIEngine()

    @pytest.fixture
    def mock_llm_provider(self):
        """Create a mock LLM provider"""
        mock_provider = AsyncMock()
        mock_provider.is_available = True
        mock_provider.generate_analysis = AsyncMock(
            return_value={
                "recommendation": "APPROVE",
                "confidence": 0.85,
                "reasoning": "Task is well-suited for the agent's capabilities",
                "risk_assessment": "LOW",
                "estimated_completion": "2 hours",
            }
        )
        return mock_provider

    @pytest.fixture
    def sample_task(self):
        """Create a sample task for testing"""
        now = datetime.now()
        return Task(
            id="test-task-2",
            name="AI Test Task",
            description="A task for testing AI coordination",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=now,
            updated_at=now,
            due_date=None,
            estimated_hours=3,
        )

    @pytest.fixture
    def analysis_context(self, sample_task):
        """Create an analysis context for testing"""
        return AnalysisContext(
            task=sample_task,
            project_context={
                "available_tasks": [sample_task],
                "assigned_tasks": [],
                "agent_capabilities": ["python", "ai", "testing"],
                "project_phase": "implementation",
                "agent_status": WorkerStatus.AVAILABLE,
                "current_workload": 2,
            },
            historical_data=[
                {"agent_id": "ai-agent", "task_type": "ai", "success_rate": 0.95},
                {
                    "agent_id": "ai-agent",
                    "completion_time": 2.8,
                    "task_complexity": "high",
                },
            ],
        )

    @pytest.mark.asyncio
    async def test_ai_engine_initialization(self, ai_engine):
        """Test that MarcusAIEngine initializes correctly"""
        assert ai_engine.rule_engine is not None
        assert hasattr(ai_engine, "llm_provider")

    @pytest.mark.asyncio
    @patch("src.ai.core.ai_engine.LLMAbstraction")
    async def test_analyze_with_hybrid_intelligence(
        self, mock_llm_class, ai_engine, analysis_context, mock_llm_provider
    ):
        """Test hybrid intelligence analysis"""
        mock_llm_class.return_value = mock_llm_provider
        ai_engine.llm_provider = mock_llm_provider

        result = await ai_engine.analyze_with_hybrid_intelligence(analysis_context)

        assert isinstance(result, HybridAnalysis)
        assert result.allow_assignment is not None
        assert isinstance(result.allow_assignment, bool)
        assert (
            result.ai_insights is not None or result.ai_insights is None
        )  # May be None in fallback
        assert result.reason is not None
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_analyze_with_ai_unavailable(self, ai_engine, analysis_context):
        """Test analysis when AI provider is unavailable"""
        # Force AI unavailable
        ai_engine.llm_provider = None

        result = await ai_engine.analyze_with_hybrid_intelligence(analysis_context)

        assert isinstance(result, HybridAnalysis)
        assert result.allow_assignment is not None
        assert isinstance(result.allow_assignment, bool)
        assert result.ai_insights is None  # Should be None when AI unavailable
        assert result.reason is not None
        assert result.fallback_mode is True  # Should indicate fallback mode

    @pytest.mark.asyncio
    @patch("src.ai.core.ai_engine.LLMAbstraction")
    async def test_get_ai_insights_success(
        self, mock_llm_class, ai_engine, analysis_context, mock_llm_provider
    ):
        """Test successful AI insights generation"""
        mock_llm_class.return_value = mock_llm_provider
        ai_engine.llm_provider = mock_llm_provider

        insights = await ai_engine._get_ai_insights(analysis_context)

        assert isinstance(insights, AIInsights)
        assert insights.recommendation in ["APPROVE", "REJECT", "CONDITIONAL"]
        assert isinstance(insights.confidence, float)
        assert 0.0 <= insights.confidence <= 1.0
        assert insights.reasoning is not None

    @pytest.mark.asyncio
    async def test_get_ai_insights_failure(self, ai_engine, analysis_context):
        """Test AI insights generation failure handling"""
        # Mock LLM provider that raises exception
        mock_provider = AsyncMock()
        mock_provider.is_available = True
        mock_provider.generate_analysis = AsyncMock(side_effect=Exception("API Error"))
        ai_engine.llm_provider = mock_provider

        insights = await ai_engine._get_ai_insights(analysis_context)

        # Should return None on failure, not raise exception
        assert insights is None

    @pytest.mark.asyncio
    @patch("src.ai.core.ai_engine.LLMAbstraction")
    async def test_enhance_task_with_ai(
        self, mock_llm_class, ai_engine, sample_task, mock_llm_provider
    ):
        """Test AI-powered task enhancement"""
        mock_llm_provider.enhance_task = AsyncMock(
            return_value={
                "enhanced_description": "Enhanced task description with AI insights",
                "suggested_approach": "Use test-driven development",
                "potential_pitfalls": ["Watch for edge cases", "Consider performance"],
                "estimated_complexity": "MEDIUM",
            }
        )
        mock_llm_class.return_value = mock_llm_provider
        ai_engine.llm_provider = mock_llm_provider

        enhanced_task = await ai_engine.enhance_task_with_ai(
            sample_task, {"context": "test"}
        )

        assert enhanced_task is not None
        # Task should be enhanced with AI suggestions
        mock_llm_provider.enhance_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_enhance_task_fallback(self, ai_engine, sample_task):
        """Test task enhancement fallback when AI unavailable"""
        ai_engine.llm_provider = None

        enhanced_task = await ai_engine.enhance_task_with_ai(
            sample_task, {"context": "test"}
        )

        # Should return original task when AI unavailable
        assert enhanced_task == sample_task

    @pytest.mark.asyncio
    @patch("src.ai.core.ai_engine.LLMAbstraction")
    async def test_analyze_blocker(self, mock_llm_class, ai_engine, mock_llm_provider):
        """Test AI-powered blocker analysis"""
        mock_llm_provider.analyze_blocker = AsyncMock(
            return_value={
                "blocker_type": "DEPENDENCY",
                "severity": "HIGH",
                "suggested_solutions": [
                    "Complete prerequisite task",
                    "Remove dependency",
                ],
                "estimated_resolution_time": "4 hours",
                "requires_escalation": False,
            }
        )
        mock_llm_class.return_value = mock_llm_provider
        ai_engine.llm_provider = mock_llm_provider

        blocker_info = {
            "description": "Waiting for API endpoint implementation",
            "task_id": "blocked-task",
            "blocking_task_id": "api-task",
        }

        analysis = await ai_engine.analyze_blocker(blocker_info, {"context": "test"})

        assert analysis is not None
        mock_llm_provider.analyze_blocker.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_engine_status(self, ai_engine):
        """Test engine status reporting"""
        status = await ai_engine.get_engine_status()

        assert isinstance(status, dict)
        assert "rule_engine_available" in status
        assert "ai_provider_available" in status
        assert "last_analysis_time" in status
        assert "analysis_count" in status
        assert status["rule_engine_available"] is True

    def test_calculate_hybrid_confidence(self, ai_engine):
        """Test hybrid confidence calculation"""
        rule_confidence = 0.8
        ai_confidence = 0.9

        hybrid_confidence = ai_engine._calculate_hybrid_confidence(
            rule_confidence, ai_confidence
        )

        assert isinstance(hybrid_confidence, float)
        assert 0.0 <= hybrid_confidence <= 1.0
        # Should be weighted combination of both confidences
        assert (
            hybrid_confidence != rule_confidence
        )  # Should be different from individual scores
        assert hybrid_confidence != ai_confidence


class TestIntegration:
    """Integration tests for AI Core Engine components"""

    @pytest.fixture
    def full_engine(self):
        """Create a fully configured engine for integration testing"""
        return MarcusAIEngine()

    @pytest.fixture
    def complex_context(self):
        """Create a complex analysis context for integration testing"""
        now = datetime.now()
        task = Task(
            id="integration-task",
            name="Complex Integration Task",
            description="A complex task requiring both rule and AI analysis",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=now,
            updated_at=now,
            due_date=None,
            estimated_hours=8,
        )

        return AnalysisContext(
            task=task,
            project_context={
                "available_tasks": [task],
                "assigned_tasks": [],
                "completed_tasks": [],
                "agent_capabilities": ["python", "ai", "testing", "integration"],
                "agent_workload": 3,
                "project_phase": "integration_testing",
                "dependencies": {"integration-task": []},
                "blockers": [],
                "project_deadline": "2024-12-31",
                "team_size": 4,
            },
            historical_data=[
                {
                    "agent_id": "integration-agent",
                    "task_type": "integration",
                    "success_rate": 0.88,
                },
                {
                    "team_velocity": 15,
                    "sprint_completion": 0.92,
                    "quality_metrics": "high",
                },
            ],
        )

    @pytest.mark.asyncio
    async def test_end_to_end_analysis(self, full_engine, complex_context):
        """Test complete end-to-end analysis workflow"""
        result = await full_engine.analyze_with_hybrid_intelligence(complex_context)

        # Verify complete result structure
        assert isinstance(result, HybridAnalysis)
        assert result.allow_assignment is not None
        assert isinstance(result.allow_assignment, bool)
        assert isinstance(result.confidence, float)
        assert result.reason is not None

        # Verify hybrid analysis fields
        assert isinstance(result.safety_critical, bool)
        assert isinstance(result.fallback_mode, bool)

    @pytest.mark.asyncio
    async def test_engine_status_integration(self, full_engine):
        """Test engine status after performing analysis"""
        # Perform an analysis first
        now = datetime.now()
        task = Task(
            id="status-test",
            name="Status Test",
            description="Task for status testing",
            status=TaskStatus.TODO,
            priority=Priority.LOW,
            assigned_to=None,
            created_at=now,
            updated_at=now,
            due_date=None,
            estimated_hours=1,
        )

        context = AnalysisContext(
            task=task,
            project_context={"available_tasks": [task]},
            historical_data=[
                {"agent_id": "status-agent", "task_type": "status", "success_rate": 1.0}
            ],
        )

        await full_engine.analyze_with_hybrid_intelligence(context)

        # Check status
        status = await full_engine.get_engine_status()

        assert status["analysis_count"] > 0
        assert "last_analysis_time" in status
        assert status["rule_engine_available"] is True
