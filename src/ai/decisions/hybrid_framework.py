"""
Hybrid Decision Framework for Marcus AI

Merges rule-based safety constraints with AI intelligence to make
optimal task assignment decisions while never compromising safety.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime

from src.core.models import Task, TaskStatus
from src.ai.types import (
    RuleBasedResult, AIOptimizationResult, AssignmentDecision, 
    AssignmentContext, AnalysisContext
)

logger = logging.getLogger(__name__)


class AIEngine:
    """Mock AI engine interface for hybrid framework"""
    
    async def analyze_assignment_optimality(
        self, 
        task: Task, 
        context: AssignmentContext
    ) -> AIOptimizationResult:
        """
        Analyze assignment optimality using AI
        
        Args:
            task: Task to analyze
            context: Assignment context
            
        Returns:
            AI optimization result
        """
        # This would be implemented by the actual AI engine
        # For now, return reasonable defaults
        task_text = f"{task.name} {task.description or ''}".lower()
        
        # Analyze task complexity
        complexity_indicators = ['complex', 'advanced', 'integration', 'migration']
        is_complex = any(indicator in task_text for indicator in complexity_indicators)
        
        # Analyze risk factors
        risk_indicators = ['deploy', 'production', 'migration', 'critical']
        is_risky = any(indicator in task_text for indicator in risk_indicators)
        
        # Generate suggestions based on analysis
        improvements = []
        
        if is_complex:
            improvements.extend([
                "Consider breaking down into smaller tasks",
                "Ensure sufficient time allocation",
                "Plan for thorough testing"
            ])
        
        if is_risky:
            improvements.extend([
                "Implement monitoring and rollback plan",
                "Schedule during low-traffic hours",
                "Have backup ready"
            ])
        
        # Default suggestions
        if not improvements:
            improvements = [
                "Follow established coding standards",
                "Update documentation as needed",
                "Run tests before completion"
            ]
        
        optimization_score = 0.8
        if is_complex:
            optimization_score -= 0.1
        if is_risky:
            optimization_score -= 0.1
        
        return AIOptimizationResult(
            confidence=0.85,
            optimization_score=optimization_score,
            improvements=improvements,
            semantic_confidence=0.8,
            risk_mitigation=["Follow standard procedures", "Test thoroughly"],
            estimated_completion_time=8.0 if not is_complex else 12.0
        )


class HybridDecisionFramework:
    """
    Hybrid decision framework that merges rule-based safety with AI optimization
    
    Core principle: Rules provide mandatory safety constraints that AI cannot override.
    AI provides optimization and enhancement when rules allow the assignment.
    """
    
    def __init__(self):
        # Initialize will be done lazily to avoid circular imports
        self.rule_engine = None
        self.ai_engine = AIEngine()  # Mock for now, will be replaced with real AI
        
        # Decision weights
        self.rule_weight = 0.7  # Rules weighted higher for safety
        self.ai_weight = 0.3    # AI provides enhancement
        
        # Safety settings
        self.allow_ai_override = False  # Never allow AI to override safety rules
        self.require_rule_validation = True  # Always validate with rules first
        
        logger.info("Hybrid decision framework initialized")
    
    async def make_assignment_decision(
        self, 
        task: Task, 
        context: AssignmentContext
    ) -> AssignmentDecision:
        """
        Make hybrid assignment decision combining rule-based safety with AI optimization
        
        Args:
            task: Task to assign
            context: Assignment context
            
        Returns:
            Assignment decision with reasoning and AI enhancements
        """
        logger.debug(f"Making assignment decision for task: {task.name}")
        
        # Step 1: Mandatory rule-based validation (never bypassed)
        rule_result = await self._validate_with_rules(task, context)
        
        # Step 2: If rules reject, return immediately (safety first)
        if not rule_result.is_valid:
            return AssignmentDecision(
                allow=False,
                confidence=rule_result.confidence,
                reason=f"Rule violation: {rule_result.reason}",
                safety_critical=rule_result.safety_critical,
                mandatory_rule_applied=rule_result.mandatory,
                confidence_breakdown={
                    'rule_component': rule_result.confidence,
                    'ai_component': 0.0,
                    'rule_weight': 1.0,
                    'ai_weight': 0.0
                }
            )
        
        # Step 3: Rules allow assignment - get AI optimization
        ai_result = None
        try:
            ai_result = await self.ai_engine.analyze_assignment_optimality(task, context)
        except Exception as e:
            logger.warning(f"AI optimization failed, proceeding with rule-based decision: {e}")
        
        # Step 4: Calculate hybrid confidence
        final_confidence = self._calculate_hybrid_confidence(
            rule_result.confidence,
            ai_result.confidence if ai_result else None
        )
        
        # Step 5: Build confidence breakdown
        confidence_breakdown = {
            'rule_component': rule_result.confidence,
            'ai_component': ai_result.confidence if ai_result else 0.0,
            'rule_weight': self.rule_weight,
            'ai_weight': self.ai_weight if ai_result else 0.0
        }
        
        # Step 6: Build final decision
        reason_parts = [f"Rules passed ({rule_result.confidence:.2f})"]
        if ai_result:
            reason_parts.append(f"AI optimization ({ai_result.confidence:.2f})")
        
        return AssignmentDecision(
            allow=True,
            confidence=final_confidence,
            reason="; ".join(reason_parts),
            ai_suggestions=ai_result,
            optimization_score=ai_result.optimization_score if ai_result else None,
            confidence_breakdown=confidence_breakdown,
            safety_critical=False,
            mandatory_rule_applied=False
        )
    
    async def _validate_with_rules(self, task: Task, context: AssignmentContext) -> RuleBasedResult:
        """
        Validate assignment using rule-based logic
        
        Args:
            task: Task to validate
            context: Assignment context
            
        Returns:
            Rule-based validation result
        """
        # Initialize rule engine lazily
        if self.rule_engine is None:
            from src.ai.core.ai_engine import RuleBasedEngine
            self.rule_engine = RuleBasedEngine()
        
        # Convert context to format expected by rule engine
        analysis_context_data = {
            'task': task,
            'project_context': {
                'available_tasks': context.available_tasks,
                'project_type': context.project_context.get('project_type', 'general'),
                'tech_stack': context.project_context.get('tech_stack', []),
                'team_size': context.project_context.get('team_size', 1)
            },
            'historical_data': context.project_context.get('historical_data', [])
        }
        
        analysis_context = AnalysisContext(**analysis_context_data)
        
        return await self.rule_engine.analyze(analysis_context)
    
    def _calculate_hybrid_confidence(
        self, 
        rule_confidence: float, 
        ai_confidence: Optional[float]
    ) -> float:
        """
        Calculate hybrid confidence score
        
        Rule confidence is weighted higher to prioritize safety.
        AI confidence provides enhancement when available.
        
        Args:
            rule_confidence: Confidence from rule-based analysis
            ai_confidence: Confidence from AI analysis (optional)
            
        Returns:
            Weighted confidence score
        """
        if ai_confidence is None:
            return rule_confidence
        
        # Weighted average with rule bias for safety
        hybrid_confidence = (
            rule_confidence * self.rule_weight + 
            ai_confidence * self.ai_weight
        )
        
        # Ensure confidence stays within bounds
        return max(0.0, min(1.0, hybrid_confidence))
    
    async def evaluate_assignment_quality(
        self, 
        task: Task, 
        agent_id: str, 
        assignment_outcome: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate the quality of a completed assignment for learning
        
        Args:
            task: Completed task
            agent_id: Agent who completed the task
            assignment_outcome: Outcome data (success, time, quality, etc.)
            
        Returns:
            Assignment quality evaluation
        """
        evaluation = {
            'task_id': task.id,
            'agent_id': agent_id,
            'completion_success': assignment_outcome.get('success', True),
            'actual_time': assignment_outcome.get('completion_time'),
            'quality_score': assignment_outcome.get('quality_score', 0.8),
            'blockers_encountered': assignment_outcome.get('blockers', []),
            'evaluation_timestamp': datetime.now()
        }
        
        # Calculate assignment effectiveness
        estimated_time = assignment_outcome.get('estimated_time', 8.0)
        actual_time = assignment_outcome.get('completion_time', 8.0)
        
        if estimated_time > 0:
            time_accuracy = min(estimated_time, actual_time) / max(estimated_time, actual_time)
            evaluation['time_estimation_accuracy'] = time_accuracy
        
        # Evaluate decision quality
        if assignment_outcome.get('success', True) and not assignment_outcome.get('blockers'):
            evaluation['decision_quality'] = 'excellent'
        elif assignment_outcome.get('success', True):
            evaluation['decision_quality'] = 'good'
        else:
            evaluation['decision_quality'] = 'poor'
        
        # Extract learnings
        learnings = []
        
        if evaluation['decision_quality'] == 'excellent':
            learnings.append("Assignment criteria were well-matched")
        
        if assignment_outcome.get('blockers'):
            learnings.append("Consider better dependency checking")
        
        if time_accuracy and time_accuracy < 0.7:
            learnings.append("Improve time estimation accuracy")
        
        evaluation['learnings'] = learnings
        
        logger.debug(f"Assignment quality evaluation for {task.id}: {evaluation['decision_quality']}")
        
        return evaluation
    
    async def get_framework_stats(self) -> Dict[str, Any]:
        """Get framework performance statistics"""
        return {
            'rule_weight': self.rule_weight,
            'ai_weight': self.ai_weight,
            'safety_settings': {
                'allow_ai_override': self.allow_ai_override,
                'require_rule_validation': self.require_rule_validation
            },
            'components': {
                'rule_engine': 'active',
                'ai_engine': 'active'
            }
        }
    
    async def adjust_weights(self, rule_weight: float, ai_weight: float) -> bool:
        """
        Adjust confidence weights (with safety constraints)
        
        Args:
            rule_weight: New rule weight
            ai_weight: New AI weight
            
        Returns:
            True if weights were adjusted, False if rejected for safety
        """
        # Safety constraint: Rule weight must be >= 0.5 for safety
        if rule_weight < 0.5:
            logger.warning(f"Rejected weight adjustment: rule weight {rule_weight} < 0.5 minimum")
            return False
        
        # Normalize weights
        total_weight = rule_weight + ai_weight
        if total_weight <= 0:
            logger.warning("Rejected weight adjustment: total weight <= 0")
            return False
        
        self.rule_weight = rule_weight / total_weight
        self.ai_weight = ai_weight / total_weight
        
        logger.info(f"Adjusted weights: rule={self.rule_weight:.2f}, ai={self.ai_weight:.2f}")
        return True