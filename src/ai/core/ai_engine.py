"""
Marcus AI Engine - Core AI coordination engine.

This module implements hybrid intelligence that combines rule-based safety with AI enhancement.
Key principle: Rules provide safety guarantees, AI provides intelligence enhancement.

The engine consists of two main components:
1. RuleBasedEngine: Provides deterministic, safety-critical validation
2. MarcusAIEngine: Coordinates rule-based and AI-powered analysis

Classes
-------
RuleBasedEngine
    Rule-based analysis engine using existing Phase 1-2 logic
MarcusAIEngine
    Central AI coordination engine implementing hybrid intelligence

Examples
--------
>>> from src.ai.core.ai_engine import MarcusAIEngine
>>> from src.ai.types import AnalysisContext
>>>
>>> engine = MarcusAIEngine()
>>> context = AnalysisContext(task=task, project_context=project_data)
>>> result = await engine.analyze_with_hybrid_intelligence(context)
>>> print(f"Assignment allowed: {result.allow_assignment}")
"""

import logging
import os
from typing import Any, Dict, List, Optional

from src.ai.providers.llm_abstraction import LLMAbstraction
from src.ai.types import (
    AIInsights,
    AnalysisContext,
    HybridAnalysis,
    RuleBasedResult,
)
from src.core.models import Task, TaskStatus

logger = logging.getLogger(__name__)


class RuleBasedEngine:
    """
    Rule-based analysis engine using existing Phase 1-2 logic.

    Provides deterministic validation using established rules and patterns.
    This engine ensures safety-critical decisions are made with predictable,
    auditable logic that cannot be overridden by AI suggestions.

    Attributes
    ----------
    dependency_inferer : DependencyInferer
        Infers task dependencies based on patterns
    adaptive_mode : BasicAdaptiveMode
        Implements adaptive assignment logic

    Methods
    -------
    analyze(context)
        Perform rule-based analysis on task assignment

    Notes
    -----
    This engine provides the safety foundation for Marcus. All decisions
    made by this engine are considered mandatory and cannot be overridden
    by AI suggestions.
    """

    def __init__(self) -> None:
        # Import existing dependency inferer and mode logic
        from src.intelligence.dependency_inferer import DependencyInferer
        from src.modes.adaptive.basic_adaptive import BasicAdaptiveMode

        self.dependency_inferer = DependencyInferer()
        self.adaptive_mode = BasicAdaptiveMode()

    async def analyze(self, context: AnalysisContext) -> RuleBasedResult:
        """
        Perform rule-based analysis using existing Phase 1-2 logic.

        Validates task assignment based on:
        - Logical consistency (no obviously illogical assignments)
        - Dependency satisfaction (all prerequisites complete)
        - Mandatory patterns (e.g., test before deploy)

        Parameters
        ----------
        context : AnalysisContext
            Analysis context containing:
            - task: Task to analyze
            - project_context: Dict with available_tasks, assigned_tasks

        Returns
        -------
        RuleBasedResult
            Analysis result containing:
            - is_valid: Whether assignment is allowed
            - confidence: Confidence level (0.0-1.0)
            - reason: Human-readable explanation
            - safety_critical: Whether this is a safety rule
            - mandatory: Whether rule cannot be overridden

        Examples
        --------
        >>> context = AnalysisContext(task=deploy_task, project_context=project)
        >>> result = await engine.analyze(context)
        >>> if not result.is_valid:
        ...     print(f"Assignment blocked: {result.reason}")
        """
        task = context.task

        # Use existing dependency checking logic
        # Simulate validation by checking if task can be assigned
        available_tasks = context.project_context.get("available_tasks", [])
        assigned_tasks = context.project_context.get("assigned_tasks", {})

        # Check if this task would be obviously illogical
        is_illogical = await self.adaptive_mode._is_obviously_illogical(
            task, available_tasks
        )

        if is_illogical:
            return RuleBasedResult(
                is_valid=False,
                confidence=1.0,
                reason="Illogical task assignment blocked by rule engine",
                safety_critical=True,
                mandatory=True,
            )

        # Check if task is unblocked
        is_unblocked = await self.adaptive_mode._is_task_unblocked(
            task, available_tasks, assigned_tasks
        )

        if not is_unblocked:
            return RuleBasedResult(
                is_valid=False,
                confidence=0.95,
                reason="Task blocked by dependencies",
                safety_critical=True,
                mandatory=True,
            )

        # Check for mandatory dependency patterns
        dependencies_valid = await self._check_mandatory_dependencies(task, context)

        if not dependencies_valid["valid"]:
            return RuleBasedResult(
                is_valid=False,
                confidence=0.95,
                reason=dependencies_valid["reason"],
                safety_critical=True,
                mandatory=True,
            )

        return RuleBasedResult(
            is_valid=True, confidence=0.8, reason="All rule-based checks passed"
        )

    async def _check_mandatory_dependencies(
        self, task: Task, context: AnalysisContext
    ) -> Dict[str, Any]:
        """
        Check mandatory dependency patterns.

        Enforces critical safety patterns like ensuring tests complete
        before deployment tasks can be assigned.

        Parameters
        ----------
        task : Task
            Task to check dependencies for
        context : AnalysisContext
            Analysis context with project information

        Returns
        -------
        dict
            Validation result with keys:
            - valid (bool): Whether dependencies are satisfied
            - reason (str): Explanation if invalid

        Notes
        -----
        Currently implements deployment safety check: deployment tasks
        cannot be assigned until all testing tasks are complete.
        """
        task_text = f"{task.name} {task.description or ''}".lower()

        # Check deployment before testing pattern
        if any(
            word in task_text for word in ["deploy", "release", "launch", "production"]
        ):
            # Check if testing tasks exist and are complete
            available_tasks = context.project_context.get("available_tasks", [])
            testing_tasks = [
                t
                for t in available_tasks
                if any(
                    test_word in f"{t.name} {t.description or ''}".lower()
                    for test_word in ["test", "qa", "quality", "verify"]
                )
            ]

            if testing_tasks:
                incomplete_tests = [
                    t for t in testing_tasks if t.status != TaskStatus.DONE
                ]
                if incomplete_tests:
                    return {
                        "valid": False,
                        "reason": f"Deployment blocked: {len(incomplete_tests)} testing tasks incomplete",
                    }

        return {"valid": True, "reason": "All mandatory dependencies satisfied"}


class MarcusAIEngine:
    """
    Central AI coordination engine implementing hybrid intelligence.

    Combines rule-based safety guarantees with AI-powered semantic understanding
    and intelligent optimization while ensuring rules are never overridden.

    The engine follows a strict precedence model:
    1. Rule-based validation (mandatory, safety-critical)
    2. AI enhancement (optional, additive only)
    3. Hybrid confidence calculation (weighted combination)

    Parameters
    ----------
    None

    Attributes
    ----------
    llm_client : LLMAbstraction
        AI provider abstraction for semantic analysis
    rule_engine : RuleBasedEngine
        Rule-based validation engine
    hybrid_coordinator : HybridDecisionFramework
        Coordinates hybrid decision making
    ai_enabled : bool
        Whether AI enhancement is enabled
    fallback_on_ai_failure : bool
        Whether to fallback to rules on AI failure
    rule_safety_override : bool
        Whether AI can override rules (always False)

    Methods
    -------
    analyze_with_hybrid_intelligence(context)
        Perform hybrid analysis on task assignment
    enhance_task_with_ai(task, context)
        Enhance task descriptions using AI
    analyze_blocker(task_id, blocker_description, severity, agent, task)
        Analyze blockers and suggest solutions
    get_engine_status()
        Get current engine status and configuration

    Examples
    --------
    >>> engine = MarcusAIEngine()
    >>> # Analyze task assignment
    >>> result = await engine.analyze_with_hybrid_intelligence(context)
    >>> if result.allow_assignment:
    ...     print(f"Assignment allowed with {result.confidence:.0%} confidence")
    ...
    >>> # Get AI suggestions for blocker
    >>> suggestions = await engine.analyze_blocker(
    ...     task_id="task-123",
    ...     blocker_description="Database connection failed",
    ...     severity="high",
    ...     agent=agent_info,
    ...     task=blocked_task
    ... )

    Notes
    -----
    AI enhancement is controlled by the MARCUS_AI_ENABLED environment variable.
    The engine always falls back to rule-based decisions if AI fails, ensuring
    system reliability.
    """

    def __init__(self) -> None:
        self.llm_client = LLMAbstraction()
        self.rule_engine = RuleBasedEngine()

        # Import lazily to avoid circular dependency
        from src.ai.decisions.hybrid_framework import HybridDecisionFramework

        self.hybrid_coordinator = HybridDecisionFramework()

        # Configuration - get from config first, env var as override
        from src.config.config_loader import get_config

        config = get_config()
        ai_config = config.get("ai", {})

        # Check config first, then env var, default to true
        self.ai_enabled = ai_config.get("enabled", True)
        if os.getenv("MARCUS_AI_ENABLED") is not None:
            self.ai_enabled = os.getenv("MARCUS_AI_ENABLED", "true").lower() == "true"

        self.fallback_on_ai_failure = True
        self.rule_safety_override = False  # Never allow AI to override safety rules

        logger.info(f"Marcus AI Engine initialized (AI enabled: {self.ai_enabled})")

    async def analyze_with_hybrid_intelligence(
        self, context: AnalysisContext
    ) -> HybridAnalysis:
        """
        Perform hybrid analysis combining rule-based safety with AI intelligence.

        Executes a multi-step analysis process:
        1. Rule-based validation (mandatory)
        2. AI enhancement (if enabled and rules pass)
        3. Confidence calculation (weighted combination)

        Parameters
        ----------
        context : AnalysisContext
            Analysis context containing:
            - task: Task to analyze for assignment
            - project_context: Project state and metadata

        Returns
        -------
        HybridAnalysis
            Complete analysis result containing:
            - allow_assignment: Final decision on assignment
            - confidence: Combined confidence score (0.0-1.0)
            - reason: Human-readable explanation
            - ai_confidence: AI model confidence (if available)
            - ai_insights: Detailed AI analysis (if available)
            - fallback_mode: Whether AI was unavailable
            - confidence_breakdown: Component confidence scores

        Raises
        ------
        Exception
            Only if AI fails and fallback_on_ai_failure is False

        Notes
        -----
        Rule violations always result in assignment rejection, regardless
        of AI analysis. AI can only enhance allowed assignments, never
        override safety rules.

        Examples
        --------
        >>> context = AnalysisContext(
        ...     task=Task(id="1", name="Deploy to production"),
        ...     project_context={"available_tasks": tasks}
        ... )
        >>> result = await engine.analyze_with_hybrid_intelligence(context)
        >>> if not result.allow_assignment:
        ...     print(f"Blocked: {result.reason}")
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
                safety_critical=rule_result.safety_critical,
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
            rule_result.confidence, ai_confidence
        )

        # Step 5: Build confidence breakdown
        confidence_breakdown = {
            "rule_weight": 0.7 if ai_confidence else 1.0,
            "ai_weight": 0.3 if ai_confidence else 0.0,
            "rule_component": rule_result.confidence,
            "ai_component": ai_confidence or 0.0,
        }

        return HybridAnalysis(
            allow_assignment=True,
            confidence=final_confidence,
            reason=f"Rules passed. {f'AI confidence: {ai_confidence:.2f}' if ai_confidence else 'Rule-based only'}",
            ai_confidence=ai_confidence,
            ai_insights=ai_insights,
            fallback_mode=fallback_mode,
            confidence_breakdown=confidence_breakdown,
        )

    async def _get_ai_insights(self, context: AnalysisContext) -> AIInsights:
        """
        Get AI insights for the task.

        Parameters
        ----------
        context : AnalysisContext
            Analysis context with task and project information

        Returns
        -------
        AIInsights
            AI-generated insights including intent, dependencies, and risks
        """
        semantic_analysis = await self.llm_client.analyze_task_semantics(
            context.task, context.project_context
        )

        return AIInsights(
            task_intent=semantic_analysis.task_intent,
            semantic_dependencies=semantic_analysis.semantic_dependencies,
            risk_factors=semantic_analysis.risk_factors,
            suggestions=semantic_analysis.suggestions,
            confidence=semantic_analysis.confidence,
            reasoning=semantic_analysis.reasoning,
            risk_assessment=semantic_analysis.risk_assessment,
        )

    def _calculate_hybrid_confidence(
        self, rule_confidence: float, ai_confidence: Optional[float]
    ) -> float:
        """
        Calculate final confidence by weighting rule and AI confidence.

        Rule confidence is weighted higher (70%) for safety-critical decisions
        to ensure system reliability.

        Parameters
        ----------
        rule_confidence : float
            Confidence from rule-based analysis (0.0-1.0)
        ai_confidence : float, optional
            Confidence from AI analysis (0.0-1.0)

        Returns
        -------
        float
            Weighted confidence score (0.0-1.0)

        Notes
        -----
        Current weighting: 70% rules, 30% AI
        """
        if ai_confidence is None:
            return rule_confidence

        # Weight rule confidence higher (70%) for safety
        rule_weight = 0.7
        ai_weight = 0.3

        return (rule_confidence * rule_weight) + (ai_confidence * ai_weight)

    async def enhance_task_with_ai(
        self, task: Task, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhance a task with AI-generated improvements.

        Uses AI to generate enhanced descriptions and effort estimates
        that provide more context and clarity for task execution.

        Parameters
        ----------
        task : Task
            Task to enhance with AI insights
        context : dict
            Project context for understanding task relationships

        Returns
        -------
        dict
            Enhanced task data containing:
            - enhanced_description: Improved task description
            - ai_effort_estimate: AI-based effort estimation
            - enhancement_confidence: Confidence in enhancements

        Notes
        -----
        Returns empty dict if AI is disabled or enhancement fails.
        Enhancements are suggestions only and don't affect task execution.

        Examples
        --------
        >>> enhancements = await engine.enhance_task_with_ai(
        ...     task=Task(name="Setup CI"),
        ...     context=project_context
        ... )
        >>> print(enhancements.get('enhanced_description'))
        """
        if not self.ai_enabled:
            return {}

        try:
            enhanced = await self.llm_client.generate_enhanced_description(
                task, context
            )
            estimates = await self.llm_client.estimate_effort_intelligently(
                task, context
            )

            return {
                "enhanced_description": enhanced,
                "ai_effort_estimate": estimates,
                "enhancement_confidence": 0.8,  # Base confidence for enhancements
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
        task: Optional[Task],
    ) -> List[str]:
        """
        Analyze a blocker and suggest solutions using AI.

        Uses AI to understand the blocker context and generate actionable
        suggestions for resolution. Falls back to generic suggestions if
        AI is unavailable.

        Parameters
        ----------
        task_id : str
            ID of the blocked task
        blocker_description : str
            Detailed description of what's blocking progress
        severity : str
            Severity level: 'low', 'medium', or 'high'
        agent : dict, optional
            Information about the agent encountering the blocker
        task : Task, optional
            The blocked task object for context

        Returns
        -------
        list of str
            Prioritized list of suggested solutions

        Notes
        -----
        Always returns at least 3 suggestions, even if AI fails.
        High-severity blockers receive more detailed analysis.

        Examples
        --------
        >>> suggestions = await engine.analyze_blocker(
        ...     task_id="task-123",
        ...     blocker_description="PostgreSQL connection timeout",
        ...     severity="high",
        ...     agent={"id": "agent-1", "name": "Backend Dev"},
        ...     task=database_task
        ... )
        >>> for i, suggestion in enumerate(suggestions, 1):
        ...     print(f"{i}. {suggestion}")
        """
        if not self.ai_enabled or not task:
            return [
                "Review task dependencies",
                "Check if prerequisite tasks are complete",
                "Consult team lead for guidance",
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
                "Escalate to team lead if blocker persists",
            ]

    async def get_engine_status(self) -> Dict[str, Any]:
        """
        Get current AI engine status and configuration.

        Returns
        -------
        dict
            Engine status containing:
            - ai_enabled: Whether AI enhancement is active
            - llm_provider: Current LLM provider name
            - fallback_mode: Whether fallback is enabled
            - safety_override_disabled: Confirms rules can't be overridden
            - components: Status of each engine component

        Examples
        --------
        >>> status = await engine.get_engine_status()
        >>> print(f"AI enabled: {status['ai_enabled']}")
        >>> print(f"Provider: {status['llm_provider']}")
        """
        return {
            "ai_enabled": self.ai_enabled,
            "llm_provider": self.llm_client.current_provider,
            "fallback_mode": self.fallback_on_ai_failure,
            "safety_override_disabled": not self.rule_safety_override,
            "components": {
                "rule_engine": "active",
                "llm_client": "active" if self.ai_enabled else "disabled",
                "hybrid_coordinator": "active",
            },
        }
