"""
Test suite for Marcus AI Engine - TDD approach

Tests the core AI coordination engine that merges rule-based logic
with AI intelligence while maintaining safety guarantees.
"""

import pytest
import pytest_asyncio
import os
from unittest.mock import AsyncMock, Mock, patch
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# Will implement these after tests
from src.ai.core.ai_engine import MarcusAIEngine
from src.ai.providers.llm_abstraction import LLMAbstraction
from src.ai.providers.base_provider import SemanticAnalysis
from src.ai.decisions.hybrid_framework import HybridDecisionFramework
from src.ai.types import HybridAnalysis, AnalysisContext, AssignmentDecision
from src.core.models import Task, TaskStatus, Priority


@dataclass
class MockAnalysisContext:
    """Mock analysis context for testing"""
    task: Task
    project_context: Dict[str, Any]
    historical_data: List[Dict[str, Any]]


class TestMarcusAIEngine:
    """Test the core AI engine with hybrid intelligence"""
    
    @pytest_asyncio.fixture
    async def ai_engine(self):
        """Create AI engine with mocked dependencies"""
        # Set environment variable to disable real AI for testing
        with patch.dict(os.environ, {'MARCUS_AI_ENABLED': 'false'}):
            with patch('src.ai.providers.llm_abstraction.LLMAbstraction') as mock_llm:
                engine = MarcusAIEngine()
                engine.llm_client = mock_llm.return_value
                
                # Mock the rule engine methods directly
                rule_engine_mock = Mock()
                rule_engine_mock.analyze = AsyncMock()
                engine.rule_engine = rule_engine_mock
                
                return engine
    
    @pytest.fixture
    def sample_task(self):
        """Create sample task for testing"""
        return Task(
            id="test-123",
            name="Deploy to production",
            description="Deploy the application to production environment",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=None,
            updated_at=None,
            due_date=None,
            estimated_hours=8.0
        )
    
    @pytest.fixture
    def analysis_context(self, sample_task):
        """Create analysis context"""
        return AnalysisContext(
            task=sample_task,
            project_context={
                'project_type': 'web',
                'tech_stack': ['react', 'python', 'postgres'],
                'team_size': 3
            },
            historical_data=[
                {'task_type': 'deployment', 'success_rate': 0.85},
                {'dependency_pattern': 'testing_before_deployment', 'confidence': 0.95}
            ]
        )

    @pytest.mark.asyncio
    async def test_hybrid_analysis_rule_safety_preserved(self, ai_engine, analysis_context):
        """Test that rule-based safety constraints are never overridden"""
        from src.ai.types import RuleBasedResult
        
        # Mock rule engine to reject deployment
        ai_engine.rule_engine.analyze.return_value = RuleBasedResult(
            is_valid=False,
            confidence=1.0,
            reason="No testing dependencies found",
            safety_critical=True
        )
        
        # Mock AI to suggest it's okay (should be ignored)
        ai_engine.llm_client.analyze_task_semantics.return_value = Mock(
            confidence=0.9,
            recommendation="safe_to_deploy"
        )
        
        result = await ai_engine.analyze_with_hybrid_intelligence(analysis_context)
        
        # Assert rule-based rejection is preserved
        assert not result.allow_assignment
        assert "rule violation" in result.reason.lower()
        assert result.confidence == 1.0  # Rule-based confidence preserved
        assert result.safety_critical is True

    @pytest.mark.asyncio
    async def test_hybrid_analysis_ai_enhancement_when_safe(self, ai_engine, analysis_context):
        """Test AI enhancement when rule-based validation passes"""
        # Mock rule engine to allow
        ai_engine.rule_engine.analyze.return_value = Mock(
            is_valid=True,
            confidence=0.8,
            reason="All dependencies satisfied",
            safety_critical=False
        )
        
        # Mock AI enhancement
        ai_engine.llm_client.analyze_task_semantics.return_value = Mock(
            confidence=0.95,
            risk_factors=['database_migration_risk'],
            suggestions=['run_backup_first', 'use_blue_green_deployment']
        )
        
        result = await ai_engine.analyze_with_hybrid_intelligence(analysis_context)
        
        # Assert AI enhancement is included
        assert result.allow_assignment is True
        assert result.ai_confidence == 0.95
        assert 'database_migration_risk' in result.ai_insights.risk_factors
        assert len(result.ai_insights.suggestions) == 2

    @pytest.mark.asyncio
    async def test_fallback_when_ai_unavailable(self, ai_engine, analysis_context):
        """Test system works when AI services are unavailable"""
        # Mock rule engine to work normally
        ai_engine.rule_engine.analyze.return_value = Mock(
            is_valid=True,
            confidence=0.9,
            reason="Dependencies satisfied"
        )
        
        # Mock AI to fail
        ai_engine.llm_client.analyze_task_semantics.side_effect = Exception("AI service unavailable")
        
        result = await ai_engine.analyze_with_hybrid_intelligence(analysis_context)
        
        # Assert system falls back gracefully
        assert result.allow_assignment is True
        assert result.confidence == 0.9  # Rule-based confidence used
        assert result.fallback_mode is True
        assert "ai service unavailable" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_confidence_weighting_logic(self, ai_engine, analysis_context):
        """Test how rule-based and AI confidence scores are weighted"""
        # High rule confidence, low AI confidence
        ai_engine.rule_engine.analyze.return_value = Mock(
            is_valid=True,
            confidence=0.95,
            reason="Strong rule match"
        )
        
        ai_engine.llm_client.analyze_task_semantics.return_value = Mock(
            confidence=0.3,
            reasoning="Uncertain semantic analysis"
        )
        
        result = await ai_engine.analyze_with_hybrid_intelligence(analysis_context)
        
        # Final confidence should be weighted appropriately
        # Rule confidence should dominate for safety-critical decisions
        assert 0.7 <= result.confidence <= 0.95
        assert result.confidence_breakdown['rule_weight'] > result.confidence_breakdown['ai_weight']

    @pytest.mark.asyncio
    async def test_semantic_understanding_enhancement(self, ai_engine, analysis_context):
        """Test AI's semantic understanding enhances rule-based logic"""
        # Modify task to test semantic understanding
        analysis_context.task.name = "Ship the new user authentication feature"
        analysis_context.task.description = "Make the login system available to users"
        
        # Mock rule engine with basic pattern matching
        ai_engine.rule_engine.analyze.return_value = Mock(
            is_valid=True,
            confidence=0.6,
            reason="Basic keyword match"
        )
        
        # Mock AI with semantic understanding
        ai_engine.llm_client.analyze_task_semantics.return_value = Mock(
            confidence=0.9,
            task_intent="deployment_of_authentication_feature",
            semantic_dependencies=["authentication_testing", "security_review"],
            risk_assessment={
                'security_risk': 'high',
                'user_impact': 'medium',
                'rollback_complexity': 'low'
            }
        )
        
        result = await ai_engine.analyze_with_hybrid_intelligence(analysis_context)
        
        # Assert AI semantic understanding enhances analysis
        assert result.ai_insights.task_intent == "deployment_of_authentication_feature"
        assert "authentication_testing" in result.ai_insights.semantic_dependencies
        assert result.ai_insights.risk_assessment['security_risk'] == 'high'


class TestLLMAbstraction:
    """Test the multi-provider LLM abstraction layer"""
    
    @pytest.fixture
    def llm_abstraction(self):
        """Create LLM abstraction with mocked providers"""
        with patch('src.ai.providers.llm_abstraction.AnthropicProvider') as mock_anthropic, \
             patch('src.ai.providers.llm_abstraction.OpenAIProvider') as mock_openai:
            
            abstraction = LLMAbstraction()
            abstraction.providers['anthropic'] = mock_anthropic.return_value
            abstraction.providers['openai'] = mock_openai.return_value
            
            return abstraction
    
    @pytest.mark.asyncio
    async def test_provider_switching(self, llm_abstraction):
        """Test switching between different LLM providers"""
        # Test Anthropic provider
        llm_abstraction.current_provider = 'anthropic'
        llm_abstraction.providers['anthropic'].analyze_task.return_value = Mock(
            intent="test_anthropic_response"
        )
        
        result = await llm_abstraction.analyze_task_semantics(Mock(), Mock())
        assert result.intent == "test_anthropic_response"
        
        # Test OpenAI provider
        llm_abstraction.current_provider = 'openai'
        llm_abstraction.providers['openai'].analyze_task.return_value = Mock(
            intent="test_openai_response"
        )
        
        result = await llm_abstraction.analyze_task_semantics(Mock(), Mock())
        assert result.intent == "test_openai_response"

    @pytest.mark.asyncio
    async def test_provider_fallback(self, llm_abstraction):
        """Test fallback when primary provider fails"""
        # Primary fails, fallback succeeds
        llm_abstraction.current_provider = 'anthropic'
        llm_abstraction.providers['anthropic'].analyze_task.side_effect = Exception("API rate limit")
        llm_abstraction.providers['openai'].analyze_task.return_value = Mock(
            intent="fallback_response"
        )
        
        result = await llm_abstraction.analyze_task_semantics(Mock(), Mock())
        assert result.intent == "fallback_response"
        assert result.fallback_used is True

    @pytest.mark.asyncio
    async def test_semantic_dependency_inference(self, llm_abstraction):
        """Test AI-powered semantic dependency inference"""
        # Mock semantic analysis
        llm_abstraction.providers['anthropic'].infer_dependencies.return_value = [
            {
                'dependent_task': 'deploy_api',
                'dependency_task': 'test_api_endpoints',
                'confidence': 0.9,
                'reasoning': 'API deployment requires endpoint testing'
            },
            {
                'dependent_task': 'deploy_api',
                'dependency_task': 'database_migration',
                'confidence': 0.85,
                'reasoning': 'API depends on database schema changes'
            }
        ]
        
        tasks = [Mock(), Mock(), Mock()]
        result = await llm_abstraction.infer_dependencies_semantic(tasks)
        
        assert len(result) == 2
        assert result[0]['confidence'] == 0.9
        assert 'endpoint testing' in result[0]['reasoning']


class TestHybridDecisionFramework:
    """Test the hybrid decision framework that merges rule and AI decisions"""
    
    @pytest.fixture
    def decision_framework(self):
        """Create decision framework with mocked engines"""
        with patch('src.ai.decisions.hybrid_framework.RuleBasedEngine') as mock_rules, \
             patch('src.ai.decisions.hybrid_framework.AIEngine') as mock_ai:
            
            framework = HybridDecisionFramework()
            framework.rule_engine = mock_rules.return_value
            framework.ai_engine = mock_ai.return_value
            
            return framework
    
    @pytest.mark.asyncio
    async def test_mandatory_rule_enforcement(self, decision_framework):
        """Test that mandatory rules always override AI suggestions"""
        # Mock mandatory rule violation
        decision_framework.rule_engine.validate_assignment.return_value = Mock(
            is_valid=False,
            reason="Mandatory pattern violation: deployment before testing",
            confidence=1.0,
            mandatory=True
        )
        
        # AI suggests it's fine (should be ignored)
        decision_framework.ai_engine.analyze_assignment_optimality.return_value = Mock(
            confidence=0.9,
            recommendation="proceed"
        )
        
        result = await decision_framework.make_assignment_decision(Mock(), Mock())
        
        assert result.allow is False
        assert "mandatory pattern violation" in result.reason.lower()
        assert result.confidence == 1.0

    @pytest.mark.asyncio
    async def test_ai_optimization_when_rules_pass(self, decision_framework):
        """Test AI optimization suggestions when rules allow assignment"""
        # Rules pass
        decision_framework.rule_engine.validate_assignment.return_value = Mock(
            is_valid=True,
            confidence=0.8,
            reason="All rule checks passed"
        )
        
        # AI provides optimization
        decision_framework.ai_engine.analyze_assignment_optimality.return_value = Mock(
            confidence=0.95,
            optimization_score=0.85,
            improvements=[
                "Consider running during low-traffic hours",
                "Enable monitoring alerts",
                "Prepare rollback plan"
            ]
        )
        
        result = await decision_framework.make_assignment_decision(Mock(), Mock())
        
        assert result.allow is True
        assert result.ai_suggestions is not None
        assert len(result.ai_suggestions.improvements) == 3
        assert result.optimization_score == 0.85

    @pytest.mark.asyncio
    async def test_confidence_scoring_algorithm(self, decision_framework):
        """Test the confidence scoring algorithm that combines rule and AI confidence"""
        # Medium rule confidence, high AI confidence
        decision_framework.rule_engine.validate_assignment.return_value = Mock(
            is_valid=True,
            confidence=0.6,
            reason="Partial rule match"
        )
        
        decision_framework.ai_engine.analyze_assignment_optimality.return_value = Mock(
            confidence=0.9,
            semantic_confidence=0.95
        )
        
        result = await decision_framework.make_assignment_decision(Mock(), Mock())
        
        # Test weighted confidence calculation
        assert 0.6 <= result.confidence <= 0.9
        assert result.confidence_breakdown['rule_component'] == 0.6
        assert result.confidence_breakdown['ai_component'] == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])