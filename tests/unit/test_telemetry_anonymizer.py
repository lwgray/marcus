"""
Unit tests for the Data Anonymization Pipeline

Tests privacy-preserving data anonymization techniques including
differential privacy, k-anonymity, data generalization, and validation.
"""

import pytest
import json
import hashlib
from datetime import datetime, timedelta

from src.telemetry.anonymizer import DataAnonymizer
from src.telemetry.strategic_collector import StrategicInsight, InsightCategory


class TestDataAnonymizer:
    """Test suite for the DataAnonymizer class"""
    
    @pytest.fixture
    def anonymizer(self):
        """Create a test anonymizer with known parameters"""
        return DataAnonymizer(privacy_budget=1.0, k_anonymity=5)
    
    @pytest.fixture
    def sample_failure_prediction_insight(self):
        """Create sample failure prediction insight"""
        return StrategicInsight(
            category=InsightCategory.FAILURE_PREDICTION,
            data={
                'health_trend': -0.25,
                'volatility_score': 0.4,
                'failure_probability': 0.7,
                'pattern_type': 'steady_decline',
                'early_warning_signals': ['high_blocked_tasks', 'low_velocity'],
                'project_id': 'PROJECT-123',
                'team_name': 'Backend Team Alpha'
            },
            timestamp_bucket=datetime.now().isoformat(),
            confidence_score=0.85,
            sample_size_hint=15
        )
    
    @pytest.fixture
    def sample_team_optimization_insight(self):
        """Create sample team optimization insight"""
        return StrategicInsight(
            category=InsightCategory.TEAM_OPTIMIZATION,
            data={
                'team_structure': {
                    'size_bucket': 'small',
                    'role_diversity': 4,
                    'skill_diversity': 12,
                    'capacity_distribution': ['high', 'medium', 'high', 'low'],
                    'experience_distribution': [25, 18, 32, 8]
                },
                'performance_score': 0.82,
                'optimal_indicators': {
                    'high_performance_indicators': {
                        'size_bucket': 'small',
                        'role_diversity': 4,
                        'skill_diversity': 12
                    }
                },
                'user_id': 'user-456',
                'company_name': 'TechCorp Inc'
            },
            timestamp_bucket=datetime.now().isoformat(),
            confidence_score=0.78,
            sample_size_hint=8
        )
    
    @pytest.fixture
    def sample_ai_effectiveness_insight(self):
        """Create sample AI effectiveness insight"""
        return StrategicInsight(
            category=InsightCategory.AI_EFFECTIVENESS,
            data={
                'recommendation_type': 'task_assignment',
                'confidence_score': 0.87,
                'user_accepted': True,
                'outcome_success': True,
                'context': {
                    'project_size_bucket': 'medium',
                    'team_size_bucket': 'small',
                    'risk_level': 'medium',
                    'industry_hint': 'software_development'
                },
                'improvement_potential': 0.13,
                'session_id': 'session-789',
                'user_name': 'Alice Johnson'
            },
            timestamp_bucket=datetime.now().isoformat(),
            confidence_score=0.9,
            sample_size_hint=1
        )
    
    def test_anonymizer_initialization(self, anonymizer):
        """Test anonymizer initializes with proper parameters"""
        assert anonymizer.privacy_budget == 1.0
        assert anonymizer.k_anonymity == 5
        assert anonymizer.secret_key is not None
        assert len(anonymizer.noise_params) > 0
        assert len(anonymizer.generalization_rules) > 0
    
    def test_differential_privacy_noise_addition(self, anonymizer):
        """Test differential privacy noise is properly added"""
        original_value = 0.5
        
        # Add noise multiple times and check variance
        noisy_values = []
        for _ in range(100):
            noisy_value = anonymizer._add_differential_privacy_noise(
                original_value, 'confidence_score'
            )
            noisy_values.append(noisy_value)
        
        # Values should be different (noise added)
        unique_values = set(noisy_values)
        assert len(unique_values) > 1
        
        # Values should be clamped to valid range
        for value in noisy_values:
            assert 0.0 <= value <= 1.0
        
        # Mean should be approximately the original value
        mean_value = sum(noisy_values) / len(noisy_values)
        assert abs(mean_value - original_value) < 0.1
    
    def test_value_generalization(self, anonymizer):
        """Test value generalization to categories"""
        # Test team size generalization
        assert anonymizer._generalize_value(3, 'team_size') == 'micro'
        assert anonymizer._generalize_value(10, 'team_size') == 'small'
        assert anonymizer._generalize_value(25, 'team_size') == 'medium'
        assert anonymizer._generalize_value(100, 'team_size') == 'large'
        assert anonymizer._generalize_value(500, 'team_size') == 'enterprise'
        
        # Test velocity generalization
        assert anonymizer._generalize_value(1.5, 'velocity') == 'slow'
        assert anonymizer._generalize_value(3.5, 'velocity') == 'moderate'
        assert anonymizer._generalize_value(7.5, 'velocity') == 'fast'
        assert anonymizer._generalize_value(15.0, 'velocity') == 'rapid'
        
        # Test confidence generalization
        assert anonymizer._generalize_value(0.2, 'confidence') == 'low'
        assert anonymizer._generalize_value(0.5, 'confidence') == 'medium'
        assert anonymizer._generalize_value(0.9, 'confidence') == 'high'
    
    def test_sample_size_generalization(self, anonymizer):
        """Test sample size generalization to prevent fingerprinting"""
        assert anonymizer._generalize_sample_size(5) == 'small'
        assert anonymizer._generalize_sample_size(50) == 'medium'
        assert anonymizer._generalize_sample_size(500) == 'large'
        assert anonymizer._generalize_sample_size(5000) == 'very_large'
    
    def test_timestamp_anonymization(self, anonymizer):
        """Test timestamp anonymization to hour buckets"""
        # Test with specific timestamp
        original_timestamp = "2024-01-15T14:23:45.123456"
        anonymized = anonymizer._anonymize_timestamp(original_timestamp)
        
        # Should be rounded to hour
        assert anonymized.endswith(":00:00")
        assert "14:00:00" in anonymized
        
        # Test with ISO format
        now = datetime.now()
        timestamp_iso = now.isoformat()
        anonymized_iso = anonymizer._anonymize_timestamp(timestamp_iso)
        
        # Should maintain date but round time to hour
        expected_hour = now.replace(minute=0, second=0, microsecond=0)
        assert expected_hour.isoformat() == anonymized_iso
    
    def test_identifier_hashing(self, anonymizer):
        """Test consistent identifier hashing"""
        identifier = "project-123-sensitive-name"
        
        # Hash should be consistent
        hash1 = anonymizer._hash_identifier(identifier)
        hash2 = anonymizer._hash_identifier(identifier)
        assert hash1 == hash2
        
        # Hash should be different for different identifiers
        hash3 = anonymizer._hash_identifier("different-identifier")
        assert hash1 != hash3
        
        # Hash should be short and anonymous
        assert len(hash1) == 8
        assert "project" not in hash1.lower()
        assert "sensitive" not in hash1.lower()
    
    def test_failure_prediction_anonymization(self, anonymizer, sample_failure_prediction_insight):
        """Test anonymization of failure prediction insights"""
        anonymized = anonymizer.anonymize_insight(sample_failure_prediction_insight)
        
        # Should preserve category and basic structure
        assert anonymized.category == InsightCategory.FAILURE_PREDICTION
        assert 'health_trend' in anonymized.data
        assert 'volatility_score' in anonymized.data
        
        # Numerical values should have noise added
        assert anonymized.data['health_trend'] != sample_failure_prediction_insight.data['health_trend']
        assert anonymized.data['volatility_score'] != sample_failure_prediction_insight.data['volatility_score']
        
        # Sensitive identifiers should be removed or hashed
        assert 'project_id' not in anonymized.data or len(str(anonymized.data['project_id'])) == 8
        assert 'team_name' not in anonymized.data or len(str(anonymized.data['team_name'])) == 8
        
        # Pattern type should be generalized
        assert anonymized.data['pattern_type'] in ['gradual_degradation', 'volatile_degradation', 'unknown_pattern']
        
        # Warning signals should be generalized
        if 'early_warning_signals' in anonymized.data:
            for signal in anonymized.data['early_warning_signals']:
                assert signal in ['workflow_issues', 'timeline_issues', 'productivity_issues', 'resource_issues', 'general_issue']
        
        # Timestamp should be bucketed
        assert anonymized.timestamp_bucket.endswith(':00:00')
        
        # Confidence should have noise
        assert anonymized.confidence_score != sample_failure_prediction_insight.confidence_score
        
        # Sample size should be generalized
        assert anonymized.sample_size_hint in ['small', 'medium', 'large', 'very_large']
    
    def test_team_optimization_anonymization(self, anonymizer, sample_team_optimization_insight):
        """Test anonymization of team optimization insights"""
        anonymized = anonymizer.anonymize_insight(sample_team_optimization_insight)
        
        # Should preserve category
        assert anonymized.category == InsightCategory.TEAM_OPTIMIZATION
        
        # Team structure should be anonymized
        if 'team_structure' in anonymized.data:
            structure = anonymized.data['team_structure']
            
            # Size should be bucketed (potentially with noise)
            if 'size_bucket' in structure:
                assert structure['size_bucket'] in ['micro', 'small', 'medium', 'large', 'enterprise']
            
            # Diversity metrics should be generalized
            if 'role_diversity' in structure:
                assert isinstance(structure['role_diversity'], str)
            
            # Experience distribution should be generalized
            if 'experience_distribution' in structure:
                for exp in structure['experience_distribution']:
                    assert isinstance(exp, str)
        
        # Performance score should have noise
        if 'performance_score' in anonymized.data:
            assert anonymized.data['performance_score'] != sample_team_optimization_insight.data['performance_score']
        
        # Sensitive identifiers should be removed
        assert 'user_id' not in anonymized.data or len(str(anonymized.data['user_id'])) == 8
        assert 'company_name' not in anonymized.data or len(str(anonymized.data['company_name'])) == 8
    
    def test_ai_effectiveness_anonymization(self, anonymizer, sample_ai_effectiveness_insight):
        """Test anonymization of AI effectiveness insights"""
        anonymized = anonymizer.anonymize_insight(sample_ai_effectiveness_insight)
        
        # Should preserve category and basic metrics
        assert anonymized.category == InsightCategory.AI_EFFECTIVENESS
        assert 'recommendation_type' in anonymized.data
        assert 'user_accepted' in anonymized.data
        assert 'outcome_success' in anonymized.data
        
        # Confidence score should have noise
        if 'confidence_score' in anonymized.data:
            assert anonymized.data['confidence_score'] != sample_ai_effectiveness_insight.data['confidence_score']
        
        # Context should be anonymized
        if 'context' in anonymized.data:
            context = anonymized.data['context']
            
            # Buckets should remain but possibly with noise
            for key in ['project_size_bucket', 'team_size_bucket']:
                if key in context:
                    assert isinstance(context[key], str)
            
            # Industry should be generalized
            if 'industry_hint' in context:
                assert context['industry_hint'] == 'tech_sector'
        
        # Sensitive identifiers should be removed
        assert 'session_id' not in anonymized.data or len(str(anonymized.data['session_id'])) == 8
        assert 'user_name' not in anonymized.data or len(str(anonymized.data['user_name'])) == 8
    
    def test_common_anonymization_removes_identifiers(self, anonymizer):
        """Test that common anonymization removes sensitive identifiers"""
        data_with_identifiers = {
            'user_id': 'user-123',
            'project_id': 'proj-456',
            'team_id': 'team-789',
            'name': 'John Doe',
            'company_name': 'Secret Corp',
            'safe_metric': 42,
            'nested': {
                'user_id': 'nested-user',
                'safe_data': 'ok'
            },
            'list_of_objects': [
                {'user_id': 'list-user-1', 'value': 1},
                {'user_id': 'list-user-2', 'value': 2}
            ]
        }
        
        anonymized = anonymizer._apply_common_anonymization(data_with_identifiers)
        
        # Sensitive identifiers should be hashed or removed
        for key in ['user_id', 'project_id', 'team_id', 'name', 'company_name']:
            if key in anonymized:
                # If present, should be hashed (8 characters)
                assert len(str(anonymized[key])) == 8
        
        # Safe data should be preserved
        assert anonymized['safe_metric'] == 42
        
        # Nested anonymization should work
        if 'nested' in anonymized:
            assert anonymized['nested']['safe_data'] == 'ok'
            if 'user_id' in anonymized['nested']:
                assert len(str(anonymized['nested']['user_id'])) == 8
        
        # List anonymization should work
        if 'list_of_objects' in anonymized:
            for item in anonymized['list_of_objects']:
                assert item['value'] in [1, 2]  # Safe data preserved
                if 'user_id' in item:
                    assert len(str(item['user_id'])) == 8
    
    def test_distribution_anonymization_k_anonymity(self, anonymizer):
        """Test distribution anonymization respects k-anonymity"""
        # Distribution with some buckets below k-anonymity threshold
        distribution = ['high', 'high', 'high', 'high', 'high',  # 5 items (>= k_anonymity)
                      'medium', 'medium', 'medium',               # 3 items (< k_anonymity)
                      'low', 'low']                               # 2 items (< k_anonymity)
        
        anonymized_dist = anonymizer._anonymize_distribution(distribution)
        
        # Should only include buckets with sufficient count
        assert 'high' in anonymized_dist  # Has 5 items >= k_anonymity (5)
        assert 'medium' not in anonymized_dist  # Has 3 items < k_anonymity (5)
        assert 'low' not in anonymized_dist     # Has 2 items < k_anonymity (5)
    
    def test_bucket_noise_addition(self, anonymizer):
        """Test semantic noise addition to bucket categories"""
        team_size_bucket = 'medium'
        
        # Apply noise multiple times
        noisy_buckets = []
        for _ in range(50):
            noisy_bucket = anonymizer._add_noise_to_bucket(team_size_bucket, 'team_size')
            noisy_buckets.append(noisy_bucket)
        
        # Should sometimes return neighboring buckets
        unique_buckets = set(noisy_buckets)
        assert 'medium' in unique_buckets  # Original should be most common
        
        # Might occasionally see neighboring buckets
        size_buckets = ['micro', 'small', 'medium', 'large', 'enterprise']
        for bucket in unique_buckets:
            assert bucket in size_buckets
    
    def test_pattern_type_generalization(self, anonymizer):
        """Test generalization of failure pattern types"""
        patterns = {
            'steady_decline': 'gradual_degradation',
            'erratic_decline': 'volatile_degradation',
            'volatile_instability': 'volatile_degradation',
            'gradual_degradation': 'gradual_degradation',
            'unknown_pattern': 'unknown_pattern'
        }
        
        for original, expected in patterns.items():
            generalized = anonymizer._generalize_pattern_type(original)
            assert generalized == expected
    
    def test_warning_signals_generalization(self, anonymizer):
        """Test generalization of warning signal types"""
        signals = ['high_blocked_tasks', 'overdue_accumulation', 'low_velocity', 'resource_constraints']
        generalized = anonymizer._generalize_warning_signals(signals)
        
        expected_types = ['workflow_issues', 'timeline_issues', 'productivity_issues', 'resource_issues']
        
        for signal in generalized:
            assert signal in expected_types
    
    def test_bottleneck_type_generalization(self, anonymizer):
        """Test generalization of bottleneck types"""
        bottlenecks = {
            'review_bottleneck': 'process_bottleneck',
            'dependency_bottleneck': 'coordination_bottleneck',
            'resource_bottleneck': 'capacity_bottleneck',
            'technical_bottleneck': 'implementation_bottleneck',
            'unknown_bottleneck': 'process_bottleneck'
        }
        
        for original, expected in bottlenecks.items():
            generalized = anonymizer._generalize_bottleneck_type(original)
            assert generalized == expected
    
    def test_feature_name_generalization(self, anonymizer):
        """Test feature name generalization to categories"""
        features = ['dashboard_v2', 'ai_recommendations', 'team_analytics', 'custom_reports']
        
        for feature in features:
            generalized = anonymizer._generalize_feature_name(feature)
            
            # Should be mapped to one of the broad categories
            categories = [
                'workflow_feature', 'analytics_feature', 'integration_feature',
                'automation_feature', 'collaboration_feature', 'monitoring_feature'
            ]
            assert generalized in categories
            
            # Same feature should map to same category (consistency)
            generalized2 = anonymizer._generalize_feature_name(feature)
            assert generalized == generalized2
    
    def test_anonymization_validation(self, anonymizer, sample_failure_prediction_insight):
        """Test anonymization validation detects issues"""
        anonymized = anonymizer.anonymize_insight(sample_failure_prediction_insight)
        
        # Validate the anonymization
        validation = anonymizer.validate_anonymization(sample_failure_prediction_insight, anonymized)
        
        # Should pass privacy checks
        assert validation['privacy_preserved'] is True
        
        # Should maintain utility
        assert validation['utility_maintained'] is True
        
        # Should have no critical issues
        critical_issues = [issue for issue in validation['issues'] if 'critical' in issue.lower()]
        assert len(critical_issues) == 0
    
    def test_anonymization_with_missing_data(self, anonymizer):
        """Test anonymization handles missing or malformed data gracefully"""
        incomplete_insight = StrategicInsight(
            category=InsightCategory.FAILURE_PREDICTION,
            data={
                'health_trend': None,
                'missing_field': 'test'
            },
            timestamp_bucket="invalid-timestamp",
            confidence_score=1.5,  # Out of range
            sample_size_hint=-1    # Invalid
        )
        
        # Should not raise exception
        try:
            anonymized = anonymizer.anonymize_insight(incomplete_insight)
            
            # Should handle invalid values gracefully
            assert anonymized.confidence_score >= 0.0
            assert anonymized.confidence_score <= 1.0
            assert anonymized.sample_size_hint in ['small', 'medium', 'large', 'very_large']
            
        except Exception as e:
            pytest.fail(f"Anonymization should handle invalid data gracefully: {e}")
    
    def test_anonymization_preserves_statistical_utility(self, anonymizer):
        """Test that anonymization preserves statistical utility"""
        # Create multiple similar insights
        insights = []
        for i in range(20):
            insight = StrategicInsight(
                category=InsightCategory.FAILURE_PREDICTION,
                data={
                    'health_trend': -0.2 + (i * 0.02),  # Range from -0.2 to 0.18
                    'volatility_score': 0.3 + (i * 0.01),  # Range from 0.3 to 0.49
                    'failure_probability': 0.5 + (i * 0.01)  # Range from 0.5 to 0.69
                },
                timestamp_bucket=datetime.now().isoformat(),
                confidence_score=0.8,
                sample_size_hint=10
            )
            insights.append(insight)
        
        # Anonymize all insights
        anonymized_insights = [anonymizer.anonymize_insight(insight) for insight in insights]
        
        # Extract anonymized health trends
        original_trends = [i.data['health_trend'] for i in insights]
        anonymized_trends = [i.data['health_trend'] for i in anonymized_insights]
        
        # Statistical properties should be approximately preserved
        original_mean = sum(original_trends) / len(original_trends)
        anonymized_mean = sum(anonymized_trends) / len(anonymized_trends)
        
        # Mean should be close (within 0.1 due to noise)
        assert abs(original_mean - anonymized_mean) < 0.1
        
        # Should preserve general ordering relationships
        original_sorted = sorted(original_trends)
        anonymized_sorted = sorted(anonymized_trends)
        
        # Correlation should be positive (preserving general relationships)
        correlation = sum((o - original_mean) * (a - anonymized_mean) 
                         for o, a in zip(original_sorted, anonymized_sorted))
        assert correlation > 0  # Positive correlation indicates preserved relationships
    
    def test_multiple_anonymization_consistency(self, anonymizer, sample_failure_prediction_insight):
        """Test that multiple anonymizations of the same insight are different (preventing correlation)"""
        # Anonymize the same insight multiple times
        anonymizations = []
        for _ in range(5):
            anonymized = anonymizer.anonymize_insight(sample_failure_prediction_insight)
            anonymizations.append(anonymized)
        
        # Numerical values should be different due to noise
        health_trends = [a.data['health_trend'] for a in anonymizations]
        confidence_scores = [a.confidence_score for a in anonymizations]
        
        # Should have some variation due to noise
        assert len(set(health_trends)) > 1
        assert len(set(confidence_scores)) > 1
        
        # But categories should be consistently generalized
        pattern_types = [a.data.get('pattern_type') for a in anonymizations if 'pattern_type' in a.data]
        if pattern_types:
            # Pattern types should be consistently generalized to the same category
            assert len(set(pattern_types)) == 1