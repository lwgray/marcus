"""
Enhanced Memory System for Marcus

Extends the base Memory system with advanced prediction capabilities including
confidence intervals, complexity adjustments, and time-based relevance weighting.
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

from src.core.memory import Memory, TaskOutcome, AgentProfile
from src.core.models import Task
from src.core.resilience import with_fallback
import logging

logger = logging.getLogger(__name__)


class MemoryEnhanced(Memory):
    """
    Enhanced memory system with improved predictions and learning algorithms.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize enhanced memory system"""
        super().__init__(*args, **kwargs)
        
        # Enhanced configuration
        self.confidence_threshold = 20  # Minimum samples for high confidence
        self.complexity_baseline = 10.0  # Hours for baseline complexity
        self.recency_decay = 0.95  # Weight decay per week
        
    async def predict_task_outcome_v2(self, agent_id: str, task: Task) -> Dict[str, Any]:
        """
        Enhanced prediction with confidence intervals and complexity adjustments.
        
        Returns predictions with:
        - Confidence intervals based on sample size
        - Complexity-adjusted success probability
        - Time-based relevance weighting
        - Risk factor analysis
        """
        # Get base predictions
        base_predictions = await self.predict_task_outcome(agent_id, task)
        
        # Calculate enhanced metrics
        agent_history = self._get_agent_task_history(agent_id)
        sample_size = len(agent_history)
        
        # Calculate confidence based on sample size
        confidence = self._calculate_confidence(sample_size)
        
        # Calculate complexity factor
        complexity_factor = self._calculate_complexity_factor(task, agent_history)
        
        # Calculate time-based relevance
        recency_weight = self._calculate_recency_weight(agent_history)
        
        # Adjust success probability for complexity and recency
        adjusted_success = base_predictions["success_probability"]
        adjusted_success *= (1.0 / complexity_factor) if complexity_factor > 1 else 1.0
        adjusted_success *= recency_weight
        adjusted_success = max(0.1, min(0.95, adjusted_success))  # Clamp to reasonable range
        
        # Calculate confidence intervals
        confidence_margin = (1 - confidence) * 0.3  # Max 30% margin
        confidence_interval = {
            "lower": max(0, adjusted_success - confidence_margin),
            "upper": min(1, adjusted_success + confidence_margin)
        }
        
        # Enhance duration estimate
        enhanced_duration = self._calculate_enhanced_duration(
            task, agent_id, agent_history, complexity_factor
        )
        
        # Identify risk factors
        risk_factors = self._analyze_risk_factors(agent_id, task, agent_history)
        
        # Build enhanced predictions
        enhanced_predictions = {
            **base_predictions,  # Keep all original fields
            "success_probability_adjusted": adjusted_success,
            "confidence": confidence,
            "confidence_interval": confidence_interval,
            "complexity_factor": complexity_factor,
            "sample_size": sample_size,
            "recency_weight": recency_weight,
            "estimated_duration_enhanced": enhanced_duration,
            "duration_confidence_interval": {
                "lower": enhanced_duration * 0.8,
                "upper": enhanced_duration * 1.3
            },
            "risk_analysis": {
                "factors": risk_factors,
                "mitigation_suggestions": self._get_mitigation_suggestions(risk_factors)
            },
            "reliability_score": confidence * recency_weight,
            "prediction_metadata": {
                "method": "enhanced_v2",
                "timestamp": datetime.now().isoformat(),
                "based_on_tasks": sample_size
            }
        }
        
        return enhanced_predictions
        
    def _get_agent_task_history(self, agent_id: str) -> List[TaskOutcome]:
        """Get all task outcomes for an agent"""
        return [
            outcome for outcome in self.episodic["outcomes"]
            if outcome.agent_id == agent_id
        ]
        
    def _calculate_confidence(self, sample_size: int) -> float:
        """
        Calculate confidence based on sample size.
        
        Uses logarithmic growth that plateaus at 95% confidence.
        """
        if sample_size == 0:
            return 0.1
            
        # Logarithmic growth with plateau
        # At 10 samples, confidence should be around 0.5-0.6
        # At 20 samples (threshold), confidence should be around 0.8
        if sample_size >= self.confidence_threshold:
            confidence = min(0.95, 0.8 + (0.15 * (sample_size - self.confidence_threshold) / self.confidence_threshold))
        else:
            # Scale from 0.1 to 0.8 based on samples
            confidence = 0.1 + (0.7 * math.log(sample_size + 1) / math.log(self.confidence_threshold + 1))
        
        return max(0.1, min(0.95, confidence))
        
    def _calculate_complexity_factor(self, task: Task, agent_history: List[TaskOutcome]) -> float:
        """
        Calculate task complexity relative to agent's typical tasks.
        
        Returns a factor where:
        - 1.0 = normal complexity
        - > 1.0 = more complex than usual
        - < 1.0 = simpler than usual
        """
        if not agent_history:
            # No history, use task hours vs baseline
            return task.estimated_hours / self.complexity_baseline
            
        # Calculate agent's typical task duration
        avg_hours = sum(o.estimated_hours for o in agent_history) / len(agent_history)
        
        # Compare this task to agent's average
        complexity_factor = task.estimated_hours / avg_hours if avg_hours > 0 else 1.0
        
        # Also consider task labels for complexity hints
        complexity_labels = {"complex", "advanced", "expert", "difficult", "integration"}
        simplicity_labels = {"simple", "basic", "trivial", "easy", "minor"}
        
        if task.labels:
            task_labels_lower = {label.lower() for label in task.labels}
            if task_labels_lower & complexity_labels:
                complexity_factor *= 1.2
            elif task_labels_lower & simplicity_labels:
                complexity_factor *= 0.8
                
        return max(0.5, min(3.0, complexity_factor))  # Reasonable bounds
        
    def _calculate_recency_weight(self, agent_history: List[TaskOutcome]) -> float:
        """
        Calculate weight based on how recent the agent's experience is.
        
        More recent experience is weighted higher.
        """
        if not agent_history:
            return 0.5  # No history = low confidence
            
        now = datetime.now()
        weights = []
        
        for outcome in agent_history:
            if outcome.completed_at:
                age_days = (now - outcome.completed_at).days
                weeks_old = age_days / 7.0
                weight = self.recency_decay ** weeks_old
                weights.append(weight)
                
        return sum(weights) / len(weights) if weights else 0.5
        
    def _calculate_enhanced_duration(self, task: Task, agent_id: str, agent_history: List[TaskOutcome], 
                                   complexity_factor: float) -> float:
        """
        Calculate enhanced duration estimate considering multiple factors.
        """
        base_duration = task.estimated_hours
        
        if not agent_history:
            # No history, adjust by complexity only
            return base_duration * complexity_factor
            
        # Find similar tasks
        similar_tasks = self._find_similar_tasks(task, agent_history)
        
        if similar_tasks:
            # Use similar task data
            actual_durations = [t.actual_hours for t in similar_tasks if t.actual_hours > 0]
            if actual_durations:
                avg_actual = sum(actual_durations) / len(actual_durations)
                estimated_durations = [t.estimated_hours for t in similar_tasks]
                avg_estimated = sum(estimated_durations) / len(estimated_durations)
                
                # Calculate adjustment factor
                if avg_estimated > 0:
                    adjustment_factor = avg_actual / avg_estimated
                else:
                    adjustment_factor = 1.0
                    
                # Apply adjustment
                enhanced_duration = base_duration * adjustment_factor
            else:
                enhanced_duration = base_duration * complexity_factor
        else:
            # No similar tasks, use agent's general accuracy
            profile = self.semantic["agent_profiles"].get(agent_id)
            if profile and profile.average_estimation_accuracy > 0:
                enhanced_duration = base_duration / profile.average_estimation_accuracy
            else:
                enhanced_duration = base_duration * complexity_factor
                
        return max(0.5, enhanced_duration)  # Minimum 30 minutes
        
    def _find_similar_tasks(self, task: Task, history: List[TaskOutcome], 
                           similarity_threshold: float = 0.3) -> List[TaskOutcome]:
        """Find tasks similar to the given task in the history"""
        similar = []
        
        task_labels = set(task.labels) if task.labels else set()
        task_words = set(task.name.lower().split())
        
        for outcome in history:
            similarity_score = 0.0
            
            # Name similarity
            outcome_words = set(outcome.task_name.lower().split())
            if task_words and outcome_words:
                word_overlap = len(task_words & outcome_words) / len(task_words | outcome_words)
                similarity_score += word_overlap * 0.7
                
            # Label similarity (if we stored them)
            # For now, check if task names share technical terms
            technical_terms = {"api", "database", "frontend", "backend", "test", "auth", "ui"}
            task_technical = task_words & technical_terms
            outcome_technical = outcome_words & technical_terms
            if task_technical and outcome_technical:
                tech_overlap = len(task_technical & outcome_technical) / len(task_technical | outcome_technical)
                similarity_score += tech_overlap * 0.3
                
            if similarity_score >= similarity_threshold:
                similar.append(outcome)
                
        return similar
        
    def _analyze_risk_factors(self, agent_id: str, task: Task, 
                            agent_history: List[TaskOutcome]) -> List[Dict[str, Any]]:
        """Analyze potential risk factors for this task assignment"""
        risk_factors = []
        
        profile = self.semantic["agent_profiles"].get(agent_id)
        if not profile:
            risk_factors.append({
                "type": "new_agent",
                "severity": "medium",
                "description": "Agent has no tracked history"
            })
            return risk_factors
            
        # Check for common blockers
        if profile.common_blockers:
            most_common = sorted(
                profile.common_blockers.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:3]
            for blocker, count in most_common:
                if count > 2:  # Repeated blocker
                    risk_factors.append({
                        "type": "recurring_blocker",
                        "severity": "high",
                        "description": f"Agent frequently blocked by: {blocker}",
                        "occurrences": count
                    })
                    
        # Check skill match
        if task.labels and profile.skill_success_rates:
            for label in task.labels:
                if label in profile.skill_success_rates:
                    success_rate = profile.skill_success_rates[label]
                    if success_rate < 0.5:
                        risk_factors.append({
                            "type": "low_skill_match",
                            "severity": "medium",
                            "description": f"Low success rate with {label}: {success_rate:.0%}",
                            "skill": label,
                            "success_rate": success_rate
                        })
                        
        # Check complexity
        complexity_factor = self._calculate_complexity_factor(task, agent_history)
        if complexity_factor > 2.0:
            risk_factors.append({
                "type": "high_complexity",
                "severity": "medium",
                "description": f"Task is {complexity_factor:.1f}x more complex than usual",
                "complexity_factor": complexity_factor
            })
            
        # Check for first-time task type
        similar_tasks = self._find_similar_tasks(task, agent_history)
        if not similar_tasks:
            risk_factors.append({
                "type": "unfamiliar_task",
                "severity": "low",
                "description": "Agent hasn't done similar tasks before"
            })
            
        return risk_factors
        
    def _get_mitigation_suggestions(self, risk_factors: List[Dict[str, Any]]) -> List[str]:
        """Suggest mitigations for identified risks"""
        suggestions = []
        
        for risk in risk_factors:
            if risk["type"] == "recurring_blocker":
                suggestions.append(f"Proactively address '{risk['description']}' before it blocks progress")
            elif risk["type"] == "low_skill_match":
                suggestions.append(f"Consider pairing with someone experienced in {risk['skill']}")
            elif risk["type"] == "high_complexity":
                suggestions.append("Break down into smaller subtasks and add buffer time")
            elif risk["type"] == "unfamiliar_task":
                suggestions.append("Review similar completed tasks for patterns and approaches")
            elif risk["type"] == "new_agent":
                suggestions.append("Provide extra guidance and check in more frequently")
                
        return suggestions
        
    @with_fallback(lambda self, *args: {"error": "Prediction service unavailable"})
    async def predict_with_ml(self, agent_id: str, task: Task) -> Dict[str, Any]:
        """
        Future: Use ML model for predictions (placeholder for now)
        """
        # This would integrate with a trained model
        # For now, returns enhanced predictions
        return await self.predict_task_outcome_v2(agent_id, task)