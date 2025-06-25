"""
Strategic Intelligence Collector for PM Agent Telemetry

Collects anonymized patterns and metrics that provide competitive intelligence
while respecting user privacy. Focuses on discovering insights that can
improve product decisions and maintain market leadership.
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from src.core.models import ProjectState, WorkerStatus, RiskLevel, Task, TaskStatus


class InsightCategory(Enum):
    """Categories of strategic insights we can collect"""
    FAILURE_PREDICTION = "failure_patterns"
    TEAM_OPTIMIZATION = "team_composition"
    WORKFLOW_EFFICIENCY = "workflow_patterns"
    AI_EFFECTIVENESS = "ai_feedback"
    RESOURCE_OPTIMIZATION = "resource_patterns"
    MARKET_TRENDS = "usage_trends"


@dataclass
class StrategicInsight:
    """A strategic insight collected from anonymized data"""
    category: InsightCategory
    data: Dict[str, Any]
    timestamp_bucket: str  # Hour bucket, not exact time
    confidence_score: float
    sample_size_hint: int  # Rough size for statistical validity


class StrategicIntelligenceCollector:
    """
    Collects strategic intelligence while preserving privacy
    
    This collector focuses on patterns and insights that can provide
    competitive advantages:
    
    1. Project failure prediction patterns
    2. Optimal team composition insights  
    3. Workflow efficiency benchmarks
    4. AI decision quality feedback
    5. Resource allocation optimization
    """
    
    def __init__(self):
        self.insights: List[StrategicInsight] = []
        self.project_history: Dict[str, List[Dict]] = {}  # Hashed project -> history
        
    def collect_project_lifecycle_insight(
        self, 
        project_state: ProjectState,
        health_history: List[Dict[str, Any]],
        team_status: List[WorkerStatus]
    ) -> List[StrategicInsight]:
        """
        Collect insights from complete project lifecycle data
        
        Strategic Value: Understanding what makes projects succeed/fail
        """
        insights = []
        
        # 1. Failure Prediction Patterns
        if len(health_history) >= 5:  # Need history for patterns
            failure_insight = self._analyze_failure_patterns(health_history, project_state)
            if failure_insight:
                insights.append(failure_insight)
        
        # 2. Team Composition Effectiveness
        team_insight = self._analyze_team_composition(team_status, project_state)
        if team_insight:
            insights.append(team_insight)
            
        # 3. Workflow Velocity Patterns
        velocity_insight = self._analyze_velocity_patterns(project_state, health_history)
        if velocity_insight:
            insights.append(velocity_insight)
            
        return insights
    
    def collect_ai_decision_feedback(
        self,
        ai_recommendation: Dict[str, Any],
        user_action: str,
        outcome_success: bool,
        context: Dict[str, Any]
    ) -> StrategicInsight:
        """
        Collect feedback on AI recommendation quality
        
        Strategic Value: Improve AI accuracy faster than competitors
        Competitive Edge: Self-improving AI system
        """
        # Anonymize the context
        anonymous_context = {
            'project_size_bucket': self._bucket_size(context.get('total_tasks', 0)),
            'team_size_bucket': self._bucket_size(context.get('team_size', 0)),
            'risk_level': context.get('risk_level', 'unknown'),
            'industry_hint': self._hash_to_category(context.get('project_type', 'unknown'))
        }
        
        return StrategicInsight(
            category=InsightCategory.AI_EFFECTIVENESS,
            data={
                'recommendation_type': ai_recommendation.get('type', 'unknown'),
                'confidence_score': ai_recommendation.get('confidence', 0.0),
                'user_accepted': user_action == 'accepted',
                'outcome_success': outcome_success,
                'context': anonymous_context,
                'improvement_potential': 1.0 - ai_recommendation.get('confidence', 0.5)
            },
            timestamp_bucket=self._get_hour_bucket(),
            confidence_score=0.9,  # High confidence in direct feedback
            sample_size_hint=1
        )
    
    def collect_workflow_bottleneck_patterns(
        self,
        task_transitions: List[Dict[str, Any]],
        resolution_times: Dict[str, float],
        team_structure: Dict[str, Any]
    ) -> StrategicInsight:
        """
        Collect workflow efficiency insights
        
        Strategic Value: Identify optimal workflow patterns
        Competitive Edge: Industry-specific workflow optimization
        """
        # Analyze bottleneck patterns
        bottleneck_analysis = self._analyze_bottlenecks(task_transitions, resolution_times)
        
        # Anonymous team structure
        anonymous_structure = {
            'size_bucket': self._bucket_size(team_structure.get('total_members', 0)),
            'role_distribution': self._anonymize_roles(team_structure.get('roles', {})),
            'experience_distribution': self._bucket_experience(team_structure.get('experience', []))
        }
        
        return StrategicInsight(
            category=InsightCategory.WORKFLOW_EFFICIENCY,
            data={
                'bottleneck_frequency': bottleneck_analysis['frequency'],
                'avg_resolution_time_bucket': self._bucket_time(bottleneck_analysis['avg_time']),
                'most_common_bottleneck_type': bottleneck_analysis['common_type'],
                'team_structure': anonymous_structure,
                'efficiency_score': bottleneck_analysis['efficiency_score']
            },
            timestamp_bucket=self._get_hour_bucket(),
            confidence_score=0.8,
            sample_size_hint=len(task_transitions)
        )
    
    def collect_resource_optimization_patterns(
        self,
        capacity_utilization: List[float],
        performance_outcomes: List[float],
        team_satisfaction: Optional[List[float]] = None
    ) -> StrategicInsight:
        """
        Collect resource allocation optimization insights
        
        Strategic Value: Discover optimal capacity utilization
        Competitive Edge: Prevent burnout while maximizing performance
        """
        # Find the sweet spot between utilization and performance
        optimization_analysis = self._analyze_resource_optimization(
            capacity_utilization, performance_outcomes, team_satisfaction
        )
        
        return StrategicInsight(
            category=InsightCategory.RESOURCE_OPTIMIZATION,
            data={
                'optimal_utilization_range': optimization_analysis['optimal_range'],
                'performance_correlation': optimization_analysis['correlation'],
                'burnout_threshold': optimization_analysis['burnout_threshold'],
                'efficiency_peak': optimization_analysis['peak_efficiency'],
                'sustainability_score': optimization_analysis['sustainability']
            },
            timestamp_bucket=self._get_hour_bucket(),
            confidence_score=optimization_analysis['confidence'],
            sample_size_hint=len(capacity_utilization)
        )
    
    def collect_market_trend_signals(
        self,
        feature_usage: Dict[str, int],
        user_behavior: Dict[str, Any],
        adoption_patterns: Dict[str, float]
    ) -> StrategicInsight:
        """
        Collect market trend signals
        
        Strategic Value: Predict feature demand and market shifts
        Competitive Edge: Build features before competitors know they're needed
        """
        trend_analysis = self._analyze_market_trends(
            feature_usage, user_behavior, adoption_patterns
        )
        
        return StrategicInsight(
            category=InsightCategory.MARKET_TRENDS,
            data={
                'emerging_patterns': trend_analysis['emerging'],
                'declining_features': trend_analysis['declining'],
                'adoption_velocity': trend_analysis['velocity'],
                'user_segment_hints': trend_analysis['segments'],
                'future_demand_signals': trend_analysis['predictions']
            },
            timestamp_bucket=self._get_hour_bucket(),
            confidence_score=trend_analysis['confidence'],
            sample_size_hint=sum(feature_usage.values())
        )
    
    # Private helper methods for analysis
    def _analyze_failure_patterns(
        self, 
        history: List[Dict[str, Any]], 
        current_state: ProjectState
    ) -> Optional[StrategicInsight]:
        """Analyze patterns that lead to project failure"""
        # Look for declining health patterns
        health_scores = [self._health_to_score(h['overall_health']) for h in history[-10:]]
        
        if len(health_scores) < 3:
            return None
            
        # Calculate trend
        trend = self._calculate_trend(health_scores)
        volatility = self._calculate_volatility(health_scores)
        
        # Determine failure risk
        failure_probability = self._calculate_failure_probability(
            trend, volatility, current_state
        )
        
        return StrategicInsight(
            category=InsightCategory.FAILURE_PREDICTION,
            data={
                'health_trend': trend,
                'volatility_score': volatility,
                'failure_probability': failure_probability,
                'pattern_type': self._classify_failure_pattern(health_scores),
                'early_warning_signals': self._identify_warning_signals(history)
            },
            timestamp_bucket=self._get_hour_bucket(),
            confidence_score=min(0.9, len(health_scores) / 10),
            sample_size_hint=len(history)
        )
    
    def _analyze_team_composition(
        self, 
        team_status: List[WorkerStatus], 
        project_state: ProjectState
    ) -> Optional[StrategicInsight]:
        """Analyze optimal team composition patterns"""
        if not team_status:
            return None
            
        # Anonymous team metrics
        team_metrics = {
            'size_bucket': self._bucket_size(len(team_status)),
            'role_diversity': len(set(w.role for w in team_status)),
            'skill_diversity': len(set().union(*[w.skills for w in team_status if w.skills])),
            'capacity_distribution': [self._bucket_capacity(w.capacity) for w in team_status],
            'experience_distribution': [w.completed_tasks_count for w in team_status]
        }
        
        # Performance correlation
        performance_score = self._calculate_team_performance(project_state)
        
        return StrategicInsight(
            category=InsightCategory.TEAM_OPTIMIZATION,
            data={
                'team_structure': team_metrics,
                'performance_score': performance_score,
                'optimal_indicators': self._identify_optimal_indicators(team_metrics, performance_score),
                'scaling_patterns': self._analyze_scaling_patterns(team_status, project_state)
            },
            timestamp_bucket=self._get_hour_bucket(),
            confidence_score=0.7,
            sample_size_hint=len(team_status)
        )
    
    def _analyze_velocity_patterns(
        self, 
        project_state: ProjectState, 
        history: List[Dict[str, Any]]
    ) -> Optional[StrategicInsight]:
        """Analyze velocity and workflow patterns"""
        if len(history) < 3:
            return None
            
        velocity_data = [h.get('velocity', 0) for h in history[-10:]]
        velocity_trend = self._calculate_trend(velocity_data)
        
        return StrategicInsight(
            category=InsightCategory.WORKFLOW_EFFICIENCY,
            data={
                'velocity_trend': velocity_trend,
                'current_velocity_bucket': self._bucket_velocity(project_state.team_velocity),
                'consistency_score': 1.0 - self._calculate_volatility(velocity_data),
                'acceleration_patterns': self._identify_acceleration_patterns(velocity_data),
                'optimal_velocity_range': self._estimate_optimal_velocity(history)
            },
            timestamp_bucket=self._get_hour_bucket(),
            confidence_score=0.8,
            sample_size_hint=len(history)
        )
    
    # Utility methods for privacy and anonymization
    def _bucket_size(self, size: int) -> str:
        """Convert exact size to privacy-preserving bucket"""
        if size <= 5:
            return "micro"
        elif size <= 15:
            return "small"
        elif size <= 50:
            return "medium"
        elif size <= 200:
            return "large"
        else:
            return "enterprise"
    
    def _bucket_time(self, hours: float) -> str:
        """Convert exact time to privacy-preserving bucket"""
        if hours <= 1:
            return "immediate"
        elif hours <= 8:
            return "same_day"
        elif hours <= 24:
            return "next_day"
        elif hours <= 72:
            return "few_days"
        else:
            return "week_plus"
    
    def _bucket_capacity(self, capacity: float) -> str:
        """Convert capacity to privacy-preserving bucket"""
        if capacity < 0.5:
            return "low"
        elif capacity < 0.8:
            return "moderate"
        elif capacity < 1.0:
            return "high"
        else:
            return "overloaded"
    
    def _bucket_velocity(self, velocity: float) -> str:
        """Convert velocity to privacy-preserving bucket"""
        if velocity < 2:
            return "slow"
        elif velocity < 5:
            return "moderate"
        elif velocity < 10:
            return "fast"
        else:
            return "rapid"
    
    def _hash_to_category(self, value: str) -> str:
        """Convert identifying string to anonymous category"""
        # Use hash to create consistent but anonymous categories
        hash_val = int(hashlib.md5(value.encode()).hexdigest()[:8], 16)
        categories = ["type_a", "type_b", "type_c", "type_d", "type_e"]
        return categories[hash_val % len(categories)]
    
    def _get_hour_bucket(self) -> str:
        """Get current hour bucket for temporal anonymization"""
        now = datetime.now()
        # Round to nearest hour for privacy
        hour_bucket = now.replace(minute=0, second=0, microsecond=0)
        return hour_bucket.isoformat()
    
    def _health_to_score(self, health: str) -> float:
        """Convert health status to numeric score"""
        mapping = {"red": 0.0, "yellow": 0.5, "green": 1.0}
        return mapping.get(health, 0.5)
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate simple trend from list of values"""
        if len(values) < 2:
            return 0.0
        return (values[-1] - values[0]) / len(values)
    
    def _calculate_volatility(self, values: List[float]) -> float:
        """Calculate volatility (normalized standard deviation)"""
        if len(values) < 2:
            return 0.0
        
        mean_val = sum(values) / len(values)
        variance = sum((x - mean_val) ** 2 for x in values) / len(values)
        
        # Normalize by mean to get relative volatility
        if mean_val == 0:
            return 0.0
        return (variance ** 0.5) / abs(mean_val)
    
    def _calculate_failure_probability(
        self, 
        trend: float, 
        volatility: float, 
        state: ProjectState
    ) -> float:
        """Calculate probability of project failure based on patterns"""
        # Simple heuristic - would be ML model in production
        base_risk = 0.1
        
        # Negative trend increases risk
        if trend < -0.1:
            base_risk += 0.3
        
        # High volatility increases risk
        if volatility > 0.3:
            base_risk += 0.2
            
        # Blocked tasks increase risk
        if state.blocked_tasks > 2:
            base_risk += 0.2
            
        # Risk level factor
        risk_multipliers = {
            RiskLevel.LOW: 0.5,
            RiskLevel.MEDIUM: 1.0,
            RiskLevel.HIGH: 1.5,
            RiskLevel.CRITICAL: 2.0
        }
        base_risk *= risk_multipliers.get(state.risk_level, 1.0)
        
        return min(1.0, base_risk)
    
    def _classify_failure_pattern(self, health_scores: List[float]) -> str:
        """Classify the pattern of health decline"""
        if len(health_scores) < 3:
            return "insufficient_data"
            
        # Simple pattern classification
        trend = self._calculate_trend(health_scores)
        volatility = self._calculate_volatility(health_scores)
        
        if trend < -0.2 and volatility < 0.1:
            return "steady_decline"
        elif trend < -0.1 and volatility > 0.3:
            return "erratic_decline"
        elif volatility > 0.5:
            return "volatile_instability"
        else:
            return "gradual_degradation"
    
    def _identify_warning_signals(self, history: List[Dict[str, Any]]) -> List[str]:
        """Identify early warning signals from history"""
        signals = []
        
        # Look for common warning patterns
        for record in history[-5:]:  # Last 5 records
            if record.get('blocked_tasks', 0) > 3:
                signals.append("high_blocked_tasks")
            if record.get('overdue_tasks', 0) > 2:
                signals.append("overdue_accumulation")
            if record.get('team_velocity', 0) < 2:
                signals.append("low_velocity")
                
        return list(set(signals))  # Remove duplicates
    
    def _calculate_team_performance(self, project_state: ProjectState) -> float:
        """Calculate overall team performance score"""
        # Composite score based on multiple factors
        completion_rate = project_state.completed_tasks / max(project_state.total_tasks, 1)
        velocity_score = min(1.0, project_state.team_velocity / 10)  # Normalize
        quality_score = 1.0 - (project_state.blocked_tasks / max(project_state.total_tasks, 1))
        
        return (completion_rate + velocity_score + quality_score) / 3
    
    def _identify_optimal_indicators(
        self, 
        team_metrics: Dict[str, Any], 
        performance: float
    ) -> Dict[str, Any]:
        """Identify indicators of optimal team performance"""
        # This would use ML in production to find correlations
        return {
            'high_performance_indicators': {
                'size_bucket': team_metrics['size_bucket'] if performance > 0.8 else None,
                'role_diversity': team_metrics['role_diversity'] if performance > 0.8 else None,
                'skill_diversity': team_metrics['skill_diversity'] if performance > 0.8 else None
            },
            'performance_threshold': 0.8,
            'correlation_strength': 0.7  # Placeholder
        }
    
    def _analyze_scaling_patterns(
        self, 
        team_status: List[WorkerStatus], 
        project_state: ProjectState
    ) -> Dict[str, Any]:
        """Analyze how team scaling affects performance"""
        return {
            'current_efficiency': project_state.team_velocity / len(team_status) if team_status else 0,
            'scaling_recommendation': "maintain" if project_state.team_velocity > 5 else "scale_up",
            'bottleneck_indicators': ["capacity"] if any(w.capacity > 0.9 for w in team_status) else []
        }
    
    def _identify_acceleration_patterns(self, velocity_data: List[float]) -> List[str]:
        """Identify patterns in velocity acceleration"""
        patterns = []
        
        if len(velocity_data) >= 3:
            recent_trend = self._calculate_trend(velocity_data[-3:])
            overall_trend = self._calculate_trend(velocity_data)
            
            if recent_trend > overall_trend + 0.1:
                patterns.append("accelerating")
            elif recent_trend < overall_trend - 0.1:
                patterns.append("decelerating")
            else:
                patterns.append("stable")
                
        return patterns
    
    def _estimate_optimal_velocity(self, history: List[Dict[str, Any]]) -> Tuple[float, float]:
        """Estimate optimal velocity range based on history"""
        velocities = [h.get('velocity', 0) for h in history if h.get('velocity')]
        
        if not velocities:
            return (3.0, 8.0)  # Default range
            
        # Find range where performance was best
        avg_velocity = sum(velocities) / len(velocities)
        std_velocity = (sum((v - avg_velocity) ** 2 for v in velocities) / len(velocities)) ** 0.5
        
        return (max(0, avg_velocity - std_velocity), avg_velocity + std_velocity)
    
    # Placeholder methods for additional analysis
    def _analyze_bottlenecks(self, transitions, times):
        """Placeholder for bottleneck analysis"""
        return {
            'frequency': 0.3,
            'avg_time': 24.0,
            'common_type': 'review_bottleneck',
            'efficiency_score': 0.7
        }
    
    def _anonymize_roles(self, roles):
        """Anonymize role information"""
        return {self._hash_to_category(role): count for role, count in roles.items()}
    
    def _bucket_experience(self, experience_list):
        """Bucket experience levels"""
        return [self._bucket_size(exp) for exp in experience_list]
    
    def _analyze_resource_optimization(self, utilization, performance, satisfaction):
        """Analyze resource optimization patterns"""
        return {
            'optimal_range': (0.7, 0.85),
            'correlation': 0.8,
            'burnout_threshold': 0.9,
            'peak_efficiency': 0.8,
            'sustainability': 0.75,
            'confidence': 0.8
        }
    
    def _analyze_market_trends(self, usage, behavior, adoption):
        """Analyze market trend signals"""
        return {
            'emerging': ['feature_x', 'pattern_y'],
            'declining': ['old_feature'],
            'velocity': 0.15,
            'segments': ['segment_a', 'segment_b'],
            'predictions': ['trend_1', 'trend_2'],
            'confidence': 0.6
        }