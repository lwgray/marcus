"""
Marcus AI Engine - Core AI coordination engine

Implements hybrid intelligence that combines rule-based safety with AI enhancement.
Key principle: Rules provide safety guarantees, AI provides intelligence enhancement.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import os

from src.ai.providers.llm_abstraction import LLMAbstraction
from src.ai.providers.base_provider import SemanticAnalysis
from src.ai.types import (
    AnalysisContext, AIInsights, HybridAnalysis, RuleBasedResult, 
    AssignmentDecision, AssignmentContext
)
from src.core.models import Task, TaskStatus, Priority

logger = logging.getLogger(__name__)


class RuleBasedEngine:
    """Rule-based analysis engine (existing logic from Phases 1-2)"""
    
    def __init__(self):
        # Import existing dependency inferer and mode logic
        from src.intelligence.dependency_inferer import DependencyInferer
        from src.modes.adaptive.basic_adaptive import BasicAdaptiveMode
        
        self.dependency_inferer = DependencyInferer()
        self.adaptive_mode = BasicAdaptiveMode()
    
    async def analyze(self, context: AnalysisContext) -> RuleBasedResult:
        """
        Perform rule-based analysis using existing Phase 1-2 logic
        
        Args:
            context: Analysis context with task and project info
            
        Returns:
            Rule-based analysis result
        """
        task = context.task
        
        # Use existing dependency checking logic
        # Simulate validation by checking if task can be assigned
        available_tasks = context.project_context.get('available_tasks', [])
        assigned_tasks = context.project_context.get('assigned_tasks', {})
        
        # Check if this task would be obviously illogical
        is_illogical = await self.adaptive_mode._is_obviously_illogical(task, available_tasks)
        
        if is_illogical:
            return RuleBasedResult(
                is_valid=False,
                confidence=1.0,
                reason="Illogical task assignment blocked by rule engine",
                safety_critical=True,
                mandatory=True
            )
        
        # Check if task is unblocked
        is_unblocked = await self.adaptive_mode._is_task_unblocked(task, available_tasks, assigned_tasks)
        
        if not is_unblocked:
            return RuleBasedResult(
                is_valid=False,
                confidence=0.95,
                reason="Task blocked by dependencies",
                safety_critical=True,
                mandatory=True
            )
        
        # Check for mandatory dependency patterns
        dependencies_valid = await self._check_mandatory_dependencies(task, context)
        
        if not dependencies_valid['valid']:
            return RuleBasedResult(
                is_valid=False,
                confidence=0.95,
                reason=dependencies_valid['reason'],
                safety_critical=True,
                mandatory=True
            )
        
        return RuleBasedResult(
            is_valid=True,
            confidence=0.8,
            reason="All rule-based checks passed"
        )
    
    async def _check_mandatory_dependencies(self, task: Task, context: AnalysisContext) -> Dict[str, Any]:
        """Check mandatory dependency patterns"""
        task_text = f"{task.name} {task.description or ''}".lower()
        
        # Check deployment before testing pattern
        if any(word in task_text for word in ['deploy', 'release', 'launch', 'production']):
            # Check if testing tasks exist and are complete
            available_tasks = context.project_context.get('available_tasks', [])
            testing_tasks = [
                t for t in available_tasks 
                if any(test_word in f"{t.name} {t.description or ''}".lower() 
                      for test_word in ['test', 'qa', 'quality', 'verify'])
            ]
            
            if testing_tasks:
                incomplete_tests = [t for t in testing_tasks if t.status != TaskStatus.DONE]
                if incomplete_tests:
                    return {
                        'valid': False,
                        'reason': f"Deployment blocked: {len(incomplete_tests)} testing tasks incomplete"
                    }
        
        return {'valid': True, 'reason': 'All mandatory dependencies satisfied'}


class MarcusAIEngine:
    """
    Central AI coordination engine that implements hybrid intelligence.
    
    Combines rule-based safety guarantees with AI-powered semantic understanding
    and intelligent optimization while ensuring rules are never overridden.
    """
    
    def __init__(self):
        self.llm_client = LLMAbstraction()
        self.rule_engine = RuleBasedEngine()
        
        # Import lazily to avoid circular dependency
        from src.ai.decisions.hybrid_framework import HybridDecisionFramework
        self.hybrid_coordinator = HybridDecisionFramework()
        
        # Configuration
        self.ai_enabled = os.getenv('MARCUS_AI_ENABLED', 'true').lower() == 'true'
        self.fallback_on_ai_failure = True
        self.rule_safety_override = False  # Never allow AI to override safety rules
        
        logger.info(f"Marcus AI Engine initialized (AI enabled: {self.ai_enabled})")
    
    async def analyze_with_hybrid_intelligence(self, context: AnalysisContext) -> HybridAnalysis:
        """
        Perform hybrid analysis combining rule-based safety with AI intelligence
        
        Args:
            context: Analysis context with task and project information
            
        Returns:
            Hybrid analysis result with safety guarantees and AI insights
        """
        logger.debug(f"Starting hybrid analysis for task: {context.task.name}")
        
        # Step 1: Rule-based analysis (mandatory, never bypassed)
        rule_result = await self.rule_engine.analyze(context)
        
        # Step 2: If rules reject, return immediately (safety first)
        if not rule_result.is_valid:
            return HybridAnalysis(
                allow_assignment=False,
                confidence=rule_result.confidence,
                reason=f"Rule violation: {rule_result.reason}",
                safety_critical=rule_result.safety_critical
            )
        
        # Step 3: AI enhancement (only when rules allow)
        ai_insights = None
        ai_confidence = None
        fallback_mode = False
        
        if self.ai_enabled:
            try:
                ai_result = await self._get_ai_insights(context)
                ai_insights = ai_result
                ai_confidence = ai_result.confidence
                
            except Exception as e:
                logger.warning(f"AI analysis failed, falling back to rule-based: {e}")
                fallback_mode = True
                if not self.fallback_on_ai_failure:
                    raise
        else:
            fallback_mode = True
        
        # Step 4: Merge rule and AI confidence
        final_confidence = self._calculate_hybrid_confidence(
            rule_result.confidence, 
            ai_confidence
        )
        
        # Step 5: Build confidence breakdown
        confidence_breakdown = {
            'rule_weight': 0.7 if ai_confidence else 1.0,
            'ai_weight': 0.3 if ai_confidence else 0.0,
            'rule_component': rule_result.confidence,
            'ai_component': ai_confidence or 0.0
        }
        
        return HybridAnalysis(
            allow_assignment=True,
            confidence=final_confidence,
            reason=f"Rules passed. {f'AI confidence: {ai_confidence:.2f}' if ai_confidence else 'Rule-based only'}",
            ai_confidence=ai_confidence,
            ai_insights=ai_insights,
            fallback_mode=fallback_mode,
            confidence_breakdown=confidence_breakdown
        )
    
    async def _get_ai_insights(self, context: AnalysisContext) -> AIInsights:
        """Get AI insights for the task"""
        semantic_analysis = await self.llm_client.analyze_task_semantics(
            context.task, 
            context.project_context
        )
        
        return AIInsights(
            task_intent=semantic_analysis.task_intent,
            semantic_dependencies=semantic_analysis.semantic_dependencies,
            risk_factors=semantic_analysis.risk_factors,
            suggestions=semantic_analysis.suggestions,
            confidence=semantic_analysis.confidence,
            reasoning=semantic_analysis.reasoning,
            risk_assessment=semantic_analysis.risk_assessment
        )
    
    def _calculate_hybrid_confidence(
        self, 
        rule_confidence: float, 
        ai_confidence: Optional[float]
    ) -> float:
        """
        Calculate final confidence by weighting rule and AI confidence
        
        Rule confidence is weighted higher for safety-critical decisions
        """
        if ai_confidence is None:
            return rule_confidence
        
        # Weight rule confidence higher (70%) for safety
        rule_weight = 0.7
        ai_weight = 0.3
        
        return (rule_confidence * rule_weight) + (ai_confidence * ai_weight)
    
    async def enhance_task_with_ai(self, task: Task, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance a task with AI-generated improvements
        
        Args:
            task: Task to enhance
            context: Project context
            
        Returns:
            Enhanced task data
        """
        if not self.ai_enabled:
            return {}
        
        try:
            enhanced = await self.llm_client.generate_enhanced_description(task, context)
            estimates = await self.llm_client.estimate_effort_intelligently(task, context)
            
            return {
                'enhanced_description': enhanced,
                'ai_effort_estimate': estimates,
                'enhancement_confidence': 0.8  # Base confidence for enhancements
            }
            
        except Exception as e:
            logger.warning(f"AI enhancement failed for task {task.id}: {e}")
            return {}
    
    async def analyze_blocker(
        self, 
        task_id: str, 
        blocker_description: str, 
        severity: str,
        agent: Optional[Dict[str, Any]], 
        task: Optional[Task]
    ) -> List[str]:
        """
        Analyze a blocker and suggest solutions using AI
        
        Args:
            task_id: ID of blocked task
            blocker_description: Description of the blocker
            severity: Severity level
            agent: Agent encountering the blocker
            task: The blocked task
            
        Returns:
            List of suggested solutions
        """
        if not self.ai_enabled or not task:
            return [
                "Review task dependencies",
                "Check if prerequisite tasks are complete",
                "Consult team lead for guidance"
            ]
        
        try:
            suggestions = await self.llm_client.analyze_blocker_and_suggest_solutions(
                task, blocker_description, severity, agent
            )
            return suggestions
            
        except Exception as e:
            logger.warning(f"AI blocker analysis failed: {e}")
            return [
                "Review task requirements and dependencies",
                "Check documentation for similar issues",
                "Escalate to team lead if blocker persists"
            ]
    
    async def get_engine_status(self) -> Dict[str, Any]:
        """Get current AI engine status"""
        return {
            'ai_enabled': self.ai_enabled,
            'llm_provider': self.llm_client.current_provider,
            'fallback_mode': self.fallback_on_ai_failure,
            'safety_override_disabled': not self.rule_safety_override,
            'components': {
                'rule_engine': 'active',
                'llm_client': 'active' if self.ai_enabled else 'disabled',
                'hybrid_coordinator': 'active'
            }
        }