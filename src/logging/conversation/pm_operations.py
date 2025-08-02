"""
PM operations logger for Marcus conversation logging system.

This module provides specialized logging for Marcus PM operations including
internal thinking processes and formal decision-making with comprehensive
context and analysis.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import ConversationLoggerBase
from .conversation_types import ConversationType


class PMOperationsLogger(ConversationLoggerBase):
    """
    Specialized logger for Marcus PM operations.

    Handles internal thinking processes and formal decision-making
    with comprehensive metadata capture and analysis capabilities.
    """

    def _setup_file_handlers(self) -> None:
        """Setup file handlers for PM operations logging."""
        # Handler for thinking logs
        thinking_handler = self._create_rotating_handler("pm_thinking.jsonl")
        thinking_handler.name = "thinking"
        self.logger.addHandler(thinking_handler)

        # Handler for decision logs
        decision_handler = self._create_rotating_handler("pm_decisions.jsonl")
        decision_handler.name = "decisions"
        self.logger.addHandler(decision_handler)

    def log_pm_thinking(
        self, thought: str, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log Marcus' internal reasoning and decision-making processes.

        Captures the internal cognitive processes of Marcus including
        analysis, evaluation, planning, and reasoning steps. This enables
        debugging of decision-making logic and optimization of AI reasoning.

        Parameters
        ----------
        thought : str
            Description of the internal thought, analysis, or reasoning step.
            Should be clear and descriptive to aid in debugging and optimization.
        context : Optional[Dict[str, Any]], default=None
            Additional context surrounding the thought process including:
            - current_state: Relevant system or project state information
            - analysis_data: Data being analyzed or considered
            - decision_factors: Factors being weighed in decision-making
            - alternatives: Alternative approaches being considered
            - confidence: Confidence level in current reasoning

        Examples
        --------
        Task assignment analysis:

        >>> logger.log_pm_thinking(
        ...     thought="Analyzing worker capacity for urgent database task",
        ...     context={
        ...         "available_workers": ["worker_1", "worker_3"],
        ...         "task_requirements": ["database_expertise", "availability_4h"],
        ...         "worker_capacities": {"worker_1": 0.6, "worker_3": 0.8},
        ...         "decision_factors": ["skill_match", "current_load", "priority"]
        ...     }
        ... )

        Risk assessment reasoning:

        >>> logger.log_pm_thinking(
        ...     thought="Evaluating project timeline risk due to dependency delays",
        ...     context={
        ...         "blocked_tasks": 3,
        ...         "critical_path_affected": True,
        ...         "estimated_delay_days": 2,
        ...         "mitigation_options": ["parallel_work", "scope_reduction"],
        ...         "confidence_level": 0.75
        ...     }
        ... )

        Resource allocation planning:

        >>> logger.log_pm_thinking(
        ...     thought="Planning optimal resource allocation for sprint goals",
        ...     context={
        ...         "sprint_capacity": 120,
        ...         "committed_points": 95,
        ...         "buffer_percentage": 0.15,
        ...         "high_priority_tasks": 4,
        ...         "team_velocity_trend": "increasing"
        ...     }
        ... )

        Notes
        -----
        Thinking logs are recorded at DEBUG level for detailed analysis.
        These logs are crucial for understanding AI decision-making patterns.
        Context should include relevant data that influenced the thought process.
        Sensitive information should be excluded from thinking logs.

        See Also
        --------
        log_pm_decision : Log formal decisions with rationale
        ConversationType.INTERNAL_THINKING : Related conversation type
        """
        entry = {
            "event_type": "pm_thinking",
            "conversation_type": ConversationType.INTERNAL_THINKING.value,
            "thought": thought,
            "context": self._sanitize_metadata(context),
        }

        self._log_entry(entry, "thinking")

    def log_pm_decision(
        self,
        decision: str,
        rationale: str,
        alternatives_considered: Optional[List[Dict[str, Any]]] = None,
        confidence_score: Optional[float] = None,
        decision_factors: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log formal Marcus decisions with comprehensive context and analysis.

        Records important decisions made by Marcus including the decision
        itself, reasoning, alternatives considered, confidence levels, and
        contributing factors. This enables decision auditing, pattern analysis,
        and optimization of decision-making algorithms.

        Parameters
        ----------
        decision : str
            Clear description of the decision made. Should be specific and
            actionable, describing what will be done or changed.
        rationale : str
            Detailed explanation of why this decision was made, including
            the reasoning process and key factors that led to this choice.
        alternatives_considered : Optional[List[Dict[str, Any]]], default=None
            List of alternative options that were evaluated. Each alternative
            should include:
            - option: Description of the alternative
            - score: Evaluation score or ranking
            - pros: Advantages of this option
            - cons: Disadvantages or risks
            - reason_rejected: Why this option was not chosen
        confidence_score : Optional[float], default=None
            Confidence level in the decision on a scale of 0.0 to 1.0, where:
            - 0.0-0.3: Low confidence, high uncertainty
            - 0.4-0.6: Moderate confidence, some uncertainty
            - 0.7-0.9: High confidence, low uncertainty
            - 0.9-1.0: Very high confidence, minimal uncertainty
        decision_factors : Optional[Dict[str, Any]], default=None
            Key factors that influenced the decision including:
            - weights: Importance weights for different criteria
            - constraints: Limiting factors or requirements
            - risks: Identified risks and mitigation plans
            - resources: Available resources and limitations
            - timeline: Time constraints and deadlines

        Examples
        --------
        Task assignment decision:

        >>> logger.log_pm_decision(
        ...     decision="Assign critical authentication task to worker_senior_1",
        ...     rationale="Worker has extensive security experience and current availability",
        ...     alternatives_considered=[
        ...         {
        ...             "option": "Assign to worker_junior_2",
        ...             "score": 0.4,
        ...             "pros": ["Available immediately", "Eager to learn"],
        ...             "cons": ["Limited security experience", "Higher risk"],
        ...             "reason_rejected": "Task criticality requires experienced developer"
        ...         },
        ...         {
        ...             "option": "Split task between two workers",
        ...             "score": 0.6,
        ...             "pros": ["Knowledge sharing", "Faster completion"],
        ...             "cons": ["Coordination overhead", "Potential conflicts"],
        ...             "reason_rejected": "Security task requires single point of responsibility"
        ...         }
        ...     ],
        ...     confidence_score=0.85,
        ...     decision_factors={
        ...         "skill_match": 0.95,
        ...         "availability": 0.80,
        ...         "task_criticality": "high",
        ...         "deadline_pressure": "moderate",
        ...         "risk_tolerance": "low"
        ...     }
        ... )

        Resource reallocation decision:

        >>> logger.log_pm_decision(
        ...     decision="Reallocate 2 developers from Feature B to critical Bug Fix A",
        ...     rationale="Production issue affecting 40% of users requires immediate attention",
        ...     confidence_score=0.92,
        ...     decision_factors={
        ...         "user_impact": "high",
        ...         "business_priority": "critical",
        ...         "available_resources": 3,
        ...         "estimated_fix_time": "8 hours",
        ...         "feature_delay_acceptable": True
        ...     }
        ... )

        Timeline adjustment decision:

        >>> logger.log_pm_decision(
        ...     decision="Extend sprint by 2 days to accommodate dependency delays",
        ...     rationale="External API delays beyond team control, extension minimizes scope reduction",
        ...     alternatives_considered=[
        ...         {
        ...             "option": "Reduce sprint scope by 20%",
        ...             "score": 0.5,
        ...             "reason_rejected": "Would impact key stakeholder deliverables"
        ...         }
        ...     ],
        ...     confidence_score=0.78,
        ...     decision_factors={
        ...         "stakeholder_impact": "moderate",
        ...         "team_capacity": "available",
        ...         "deadline_flexibility": "limited",
        ...         "quality_requirements": "high"
        ...     }
        ... )

        Notes
        -----
        Decision logs are recorded at INFO level for high visibility.
        All decisions should include timestamps for chronological analysis.
        Confidence scores enable tracking of decision-making accuracy over time.
        Decision factors should be quantifiable when possible for analysis.
        This data is crucial for improving AI decision-making algorithms.

        See Also
        --------
        log_pm_thinking : Log reasoning processes leading to decisions
        ConversationType.DECISION : Related conversation type
        """
        entry = {
            "event_type": "pm_decision",
            "conversation_type": ConversationType.DECISION.value,
            "decision": decision,
            "rationale": rationale,
            "alternatives_considered": alternatives_considered or [],
            "confidence_score": confidence_score,
            "decision_factors": self._sanitize_metadata(decision_factors),
        }

        self._log_entry(entry, "decisions")
