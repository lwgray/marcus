"""
Unit tests for the Strategic Intelligence Collector

Tests the strategic intelligence collection capabilities including
failure prediction patterns, team optimization insights, and AI effectiveness feedback.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from src.telemetry.strategic_collector import StrategicIntelligenceCollector, InsightCategory, StrategicInsight
from src.core.models import ProjectState, WorkerStatus, RiskLevel


class TestStrategicIntelligenceCollector:
    """Test suite for the StrategicIntelligenceCollector class"""
    
    @pytest.fixture
    def collector(self):
        """Create a test strategic collector"""
        return StrategicIntelligenceCollector()
    
    @pytest.fixture
    def sample_project_state(self):
        """Create sample project state"""
        return ProjectState(
            board_id="TEST-001",
            project_name="Test Project",
            total_tasks=100,
            completed_tasks=60,
            in_progress_tasks=25,
            blocked_tasks=15,
            progress_percent=60.0,
            overdue_tasks=[],
            team_velocity=7.5,
            risk_level=RiskLevel.MEDIUM,
            last_updated=datetime.now()
        )
    
    @pytest.fixture
    def sample_team_status(self):
        """Create sample team status"""
        return [
            WorkerStatus(
                worker_id="worker-1",
                name="Alice",
                role="backend_developer",
                email="alice@test.com",
                current_tasks=[],
                completed_tasks_count=30,
                capacity=40,
                skills=["python", "postgresql"],
                availability={"monday": True, "tuesday": True, "wednesday": True},
                performance_score=1.1
            ),
            WorkerStatus(
                worker_id="worker-2",
                name="Bob",
                role="frontend_developer", 
                email="bob@test.com",
                current_tasks=[],
                completed_tasks_count=25,
                capacity=35,
                skills=["react", "typescript"],
                availability={"monday": True, "tuesday": True, "wednesday": True},
                performance_score=0.9
            )
        ]
    
    @pytest.fixture
    def sample_health_history(self):
        """Create sample health history"""
        return [
            {
                'overall_health': 'green',
                'timestamp': datetime.now().isoformat(),
                'velocity': 8.0,
                'blocked_tasks': 2,
                'overdue_tasks': 1
            },
            {
                'overall_health': 'yellow',
                'timestamp': (datetime.now() - timedelta(hours=1)).isoformat(),
                'velocity': 6.5,
                'blocked_tasks': 5,
                'overdue_tasks': 3
            },
            {
                'overall_health': 'green',
                'timestamp': (datetime.now() - timedelta(hours=2)).isoformat(),
                'velocity': 7.0,
                'blocked_tasks': 1,
                'overdue_tasks': 0
            }
        ]
    
    def test_collector_initialization(self, collector):
        """Test strategic collector initializes correctly"""
        assert collector.insights == []
        assert collector.project_history == {}
    
    def test_ai_decision_feedback_collection(self, collector):
        """Test collection of AI decision feedback"""
        ai_recommendation = {
            'type': 'task_assignment',
            'confidence': 0.85
        }
        
        context = {
            'total_tasks': 50,
            'team_size': 5,
            'risk_level': 'medium',
            'project_type': 'web_application'
        }
        
        insight = collector.collect_ai_decision_feedback(
            ai_recommendation=ai_recommendation,
            user_action='accepted',
            outcome_success=True,
            context=context
        )
        
        # Should return a strategic insight
        assert isinstance(insight, StrategicInsight)
        assert insight.category == InsightCategory.AI_EFFECTIVENESS
        
        # Should contain anonymized context
        assert 'recommendation_type' in insight.data
        assert 'user_accepted' in insight.data
        assert 'outcome_success' in insight.data
        assert 'context' in insight.data
        
        # Context should be anonymized
        anonymous_context = insight.data['context']
        assert 'project_size_bucket' in anonymous_context
        assert 'team_size_bucket' in anonymous_context
        assert 'industry_hint' in anonymous_context
    
    def test_workflow_bottleneck_collection(self, collector):
        """Test collection of workflow bottleneck patterns"""
        task_transitions = [
            {'from': 'todo', 'to': 'in_progress', 'duration': 2.0},
            {'from': 'in_progress', 'to': 'review', 'duration': 16.0},
            {'from': 'review', 'to': 'done', 'duration': 4.0}
        ]
        
        resolution_times = {
            'implementation': 16.0,
            'review': 4.0,
            'testing': 8.0
        }
        
        team_structure = {
            'total_members': 5,
            'roles': {'developer': 3, 'reviewer': 2},
            'experience': [2, 5, 8, 3, 1]
        }
        
        insight = collector.collect_workflow_bottleneck_patterns(
            task_transitions=task_transitions,
            resolution_times=resolution_times,
            team_structure=team_structure
        )
        
        # Should return workflow efficiency insight
        assert isinstance(insight, StrategicInsight)
        assert insight.category == InsightCategory.WORKFLOW_EFFICIENCY
        
        # Should contain bottleneck analysis
        assert 'bottleneck_frequency' in insight.data
        assert 'avg_resolution_time_bucket' in insight.data
        assert 'team_structure' in insight.data
        assert 'efficiency_score' in insight.data
    
    def test_resource_optimization_collection(self, collector):
        """Test collection of resource optimization patterns"""
        capacity_utilization = [0.7, 0.8, 0.9, 0.85, 0.75]
        performance_outcomes = [0.8, 0.9, 0.7, 0.85, 0.9]
        team_satisfaction = [0.8, 0.7, 0.6, 0.75, 0.85]
        
        insight = collector.collect_resource_optimization_patterns(
            capacity_utilization=capacity_utilization,
            performance_outcomes=performance_outcomes,
            team_satisfaction=team_satisfaction
        )
        
        # Should return resource optimization insight
        assert isinstance(insight, StrategicInsight)
        assert insight.category == InsightCategory.RESOURCE_OPTIMIZATION
        
        # Should contain optimization analysis
        assert 'optimal_utilization_range' in insight.data
        assert 'performance_correlation' in insight.data
        assert 'burnout_threshold' in insight.data
        assert 'sustainability_score' in insight.data
    
    def test_market_trend_collection(self, collector):
        """Test collection of market trend signals"""
        feature_usage = {
            'health_monitoring': 85,
            'ai_recommendations': 62,
            'team_analytics': 34,
            'workflow_automation': 78
        }
        
        user_behavior = {
            'session_duration': 45.5,
            'features_per_session': 3.2,
            'power_user_indicators': ['custom_dashboards', 'api_usage']
        }
        
        adoption_patterns = {
            'onboarding_completion': 0.78,
            'feature_discovery_rate': 0.65,
            'retention_indicators': 0.89
        }
        
        insight = collector.collect_market_trend_signals(
            feature_usage=feature_usage,
            user_behavior=user_behavior,
            adoption_patterns=adoption_patterns
        )
        
        # Should return market trends insight
        assert isinstance(insight, StrategicInsight)
        assert insight.category == InsightCategory.MARKET_TRENDS
        
        # Should contain trend analysis
        assert 'emerging_patterns' in insight.data
        assert 'declining_features' in insight.data
        assert 'adoption_velocity' in insight.data
        assert 'user_segment_hints' in insight.data
        assert 'future_demand_signals' in insight.data
    
    def test_project_lifecycle_collection_insufficient_data(self, collector, sample_project_state, sample_team_status):
        """Test project lifecycle collection with insufficient history"""
        # Provide minimal history (less than 5 records)
        minimal_history = [
            {'overall_health': 'green', 'velocity': 8.0},
            {'overall_health': 'yellow', 'velocity': 6.0}
        ]
        
        insights = collector.collect_project_lifecycle_insight(
            project_state=sample_project_state,
            health_history=minimal_history,
            team_status=sample_team_status
        )
        
        # Should still return some insights (team composition, but not failure patterns)
        assert isinstance(insights, list)
        # May have team and velocity insights but not failure prediction
        insight_categories = [insight.category for insight in insights]
        # Should not include failure prediction with insufficient data
        assert InsightCategory.FAILURE_PREDICTION not in insight_categories
    
    def test_project_lifecycle_collection_sufficient_data(self, collector, sample_project_state, sample_team_status, sample_health_history):
        """Test project lifecycle collection with sufficient history"""
        # Extend history to meet minimum requirements
        extended_history = sample_health_history * 2  # 6 records total
        
        insights = collector.collect_project_lifecycle_insight(
            project_state=sample_project_state,
            health_history=extended_history,
            team_status=sample_team_status
        )
        
        # Should return multiple insights
        assert isinstance(insights, list)
        assert len(insights) > 0
        
        # Should include various insight types
        insight_categories = [insight.category for insight in insights]
        expected_categories = [
            InsightCategory.FAILURE_PREDICTION,
            InsightCategory.TEAM_OPTIMIZATION,
            InsightCategory.WORKFLOW_EFFICIENCY
        ]
        
        # At least some expected categories should be present
        assert any(cat in insight_categories for cat in expected_categories)
    
    def test_privacy_bucketing_methods(self, collector):
        """Test privacy-preserving bucketing methods"""
        # Test size bucketing
        assert collector._bucket_size(3) == "micro"
        assert collector._bucket_size(10) == "small"
        assert collector._bucket_size(30) == "medium"
        assert collector._bucket_size(100) == "large"
        assert collector._bucket_size(500) == "enterprise"
        
        # Test time bucketing
        assert collector._bucket_time(0.5) == "immediate"
        assert collector._bucket_time(4) == "same_day"
        assert collector._bucket_time(12) == "next_day"
        assert collector._bucket_time(48) == "few_days"
        assert collector._bucket_time(168) == "week_plus"
        
        # Test velocity bucketing
        assert collector._bucket_velocity(1) == "slow"
        assert collector._bucket_velocity(3) == "moderate"
        assert collector._bucket_velocity(7) == "fast"
        assert collector._bucket_velocity(15) == "rapid"
    
    def test_hash_to_category_consistency(self, collector):
        """Test that hash to category mapping is consistent"""
        # Same input should always map to same category
        category1 = collector._hash_to_category("test_value")
        category2 = collector._hash_to_category("test_value")
        assert category1 == category2
        
        # Should be one of the expected categories
        expected_categories = ["type_a", "type_b", "type_c", "type_d", "type_e"]
        assert category1 in expected_categories
    
    def test_hour_bucket_anonymization(self, collector):
        """Test timestamp anonymization to hour buckets"""
        bucket = collector._get_hour_bucket()
        
        # Should be a valid ISO format timestamp
        assert isinstance(bucket, str)
        
        # Should end with :00:00 (rounded to hour)
        assert bucket.endswith(":00:00")
    
    def test_health_to_score_conversion(self, collector):
        """Test health status to numeric score conversion"""
        assert collector._health_to_score("red") == 0.0
        assert collector._health_to_score("yellow") == 0.5
        assert collector._health_to_score("green") == 1.0
        assert collector._health_to_score("unknown") == 0.5  # Default
    
    def test_trend_calculation(self, collector):
        """Test trend calculation from value series"""
        # Upward trend
        upward_values = [1.0, 2.0, 3.0, 4.0]
        upward_trend = collector._calculate_trend(upward_values)
        assert upward_trend > 0
        
        # Downward trend
        downward_values = [4.0, 3.0, 2.0, 1.0]
        downward_trend = collector._calculate_trend(downward_values)
        assert downward_trend < 0
        
        # Stable values
        stable_values = [2.0, 2.0, 2.0, 2.0]
        stable_trend = collector._calculate_trend(stable_values)
        assert stable_trend == 0.0
    
    def test_volatility_calculation(self, collector):
        """Test volatility calculation"""
        # High volatility
        volatile_values = [1.0, 5.0, 2.0, 8.0, 1.0]
        high_volatility = collector._calculate_volatility(volatile_values)
        
        # Low volatility  
        stable_values = [3.0, 3.1, 2.9, 3.0, 3.05]
        low_volatility = collector._calculate_volatility(stable_values)
        
        # High volatility should be greater than low volatility
        assert high_volatility > low_volatility
    
    def test_failure_probability_calculation(self, collector, sample_project_state):
        """Test failure probability calculation"""
        # High risk scenario
        high_risk_prob = collector._calculate_failure_probability(
            trend=-0.3,  # Negative trend
            volatility=0.5,  # High volatility
            state=sample_project_state
        )
        
        # Low risk scenario
        low_risk_prob = collector._calculate_failure_probability(
            trend=0.1,  # Positive trend
            volatility=0.1,  # Low volatility
            state=sample_project_state
        )
        
        # High risk should have higher probability
        assert high_risk_prob > low_risk_prob
        
        # Probabilities should be between 0 and 1
        assert 0 <= high_risk_prob <= 1
        assert 0 <= low_risk_prob <= 1