"""
Data Anonymization Pipeline for PM Agent Telemetry

Implements privacy-preserving techniques to anonymize strategic insights:

1. Differential Privacy - Adds calibrated noise to numerical data
2. K-Anonymity - Ensures minimum group sizes
3. Data Generalization - Converts specific values to ranges/categories
4. Identifier Hashing - Replaces identifying strings with consistent hashes
5. Temporal Bucketing - Groups timestamps to prevent timing attacks

The goal is to preserve statistical utility while protecting individual privacy.
"""

import hashlib
import hmac
import json
import math
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import asdict
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    # Fallback for testing
    import random
    HAS_NUMPY = False
    
    class np:
        random = type('random', (), {
            'laplace': lambda loc, scale: random.gauss(loc, scale * 1.4)  # Approximate laplace with gaussian
        })()

from .strategic_collector import StrategicInsight, InsightCategory


class DataAnonymizer:
    """
    Privacy-preserving data anonymization for telemetry
    
    Implements multiple privacy techniques:
    - Differential privacy with calibrated noise
    - K-anonymity for group protection
    - Data generalization and bucketing
    - Secure identifier hashing
    """
    
    def __init__(self, privacy_budget: float = 1.0, k_anonymity: int = 5):
        """
        Initialize anonymizer with privacy parameters
        
        Parameters
        ----------
        privacy_budget : float
            Differential privacy epsilon parameter (lower = more private)
        k_anonymity : int
            Minimum group size for k-anonymity
        """
        self.privacy_budget = privacy_budget
        self.k_anonymity = k_anonymity
        self.secret_key = self._generate_secret_key()
        
        # Noise parameters for different data types
        self.noise_params = {
            'confidence_score': {'sensitivity': 1.0, 'epsilon': 0.1},
            'performance_score': {'sensitivity': 1.0, 'epsilon': 0.1},
            'velocity': {'sensitivity': 10.0, 'epsilon': 0.2},
            'team_size': {'sensitivity': 1.0, 'epsilon': 0.2},
            'task_count': {'sensitivity': 5.0, 'epsilon': 0.2},
            'time_duration': {'sensitivity': 24.0, 'epsilon': 0.2}  # Hours
        }
        
        # Generalization mappings
        self.generalization_rules = {
            'team_size': [(0, 5, 'micro'), (6, 15, 'small'), (16, 50, 'medium'), (51, 200, 'large'), (201, float('inf'), 'enterprise')],
            'velocity': [(0, 2, 'slow'), (2, 5, 'moderate'), (5, 10, 'fast'), (10, float('inf'), 'rapid')],
            'confidence': [(0, 0.3, 'low'), (0.3, 0.7, 'medium'), (0.7, 1.0, 'high')],
            'risk_count': [(0, 2, 'few'), (3, 5, 'some'), (6, 10, 'many'), (11, float('inf'), 'excessive')]
        }
    
    def anonymize_insight(self, insight: StrategicInsight) -> StrategicInsight:
        """
        Anonymize a strategic insight while preserving utility
        
        Parameters
        ----------
        insight : StrategicInsight
            Original insight to anonymize
            
        Returns
        -------
        StrategicInsight
            Anonymized version of the insight
        """
        # Deep copy the insight data
        anonymized_data = json.loads(json.dumps(insight.data))
        
        # Apply anonymization based on insight category
        if insight.category == InsightCategory.FAILURE_PREDICTION:
            anonymized_data = self._anonymize_failure_prediction(anonymized_data)
        elif insight.category == InsightCategory.TEAM_OPTIMIZATION:
            anonymized_data = self._anonymize_team_optimization(anonymized_data)
        elif insight.category == InsightCategory.WORKFLOW_EFFICIENCY:
            anonymized_data = self._anonymize_workflow_efficiency(anonymized_data)
        elif insight.category == InsightCategory.AI_EFFECTIVENESS:
            anonymized_data = self._anonymize_ai_effectiveness(anonymized_data)
        elif insight.category == InsightCategory.RESOURCE_OPTIMIZATION:
            anonymized_data = self._anonymize_resource_optimization(anonymized_data)
        elif insight.category == InsightCategory.MARKET_TRENDS:
            anonymized_data = self._anonymize_market_trends(anonymized_data)
        
        # Apply common anonymization
        anonymized_data = self._apply_common_anonymization(anonymized_data)
        
        # Create anonymized insight
        return StrategicInsight(
            category=insight.category,
            data=anonymized_data,
            timestamp_bucket=self._anonymize_timestamp(insight.timestamp_bucket),
            confidence_score=self._add_differential_privacy_noise(
                insight.confidence_score, 'confidence_score'
            ),
            sample_size_hint=self._generalize_sample_size(insight.sample_size_hint)
        )
    
    def _anonymize_failure_prediction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize failure prediction data"""
        # Add noise to trend and volatility
        if 'health_trend' in data:
            data['health_trend'] = self._add_differential_privacy_noise(
                data['health_trend'], 'confidence_score'
            )
        
        if 'volatility_score' in data:
            data['volatility_score'] = self._add_differential_privacy_noise(
                data['volatility_score'], 'confidence_score'
            )
            
        if 'failure_probability' in data:
            data['failure_probability'] = self._add_differential_privacy_noise(
                data['failure_probability'], 'confidence_score'
            )
        
        # Generalize pattern types to broader categories
        if 'pattern_type' in data:
            data['pattern_type'] = self._generalize_pattern_type(data['pattern_type'])
            
        # Keep early warning signals but generalize them
        if 'early_warning_signals' in data:
            data['early_warning_signals'] = self._generalize_warning_signals(
                data['early_warning_signals']
            )
        
        return data
    
    def _anonymize_team_optimization(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize team optimization data"""
        if 'team_structure' in data:
            structure = data['team_structure']
            
            # Generalize team size
            if 'size_bucket' in structure:
                # Already bucketed, but add noise to preserve privacy
                structure['size_bucket'] = self._add_noise_to_bucket(
                    structure['size_bucket'], 'team_size'
                )
            
            # Generalize diversity metrics
            if 'role_diversity' in structure:
                structure['role_diversity'] = self._generalize_value(
                    structure['role_diversity'], 'team_size'
                )
                
            if 'skill_diversity' in structure:
                structure['skill_diversity'] = self._generalize_value(
                    structure['skill_diversity'], 'team_size'
                )
            
            # Anonymize capacity and experience distributions
            if 'capacity_distribution' in structure:
                structure['capacity_distribution'] = self._anonymize_distribution(
                    structure['capacity_distribution']
                )
                
            if 'experience_distribution' in structure:
                structure['experience_distribution'] = [
                    self._generalize_value(exp, 'task_count') 
                    for exp in structure['experience_distribution']
                ]
        
        # Add noise to performance score
        if 'performance_score' in data:
            data['performance_score'] = self._add_differential_privacy_noise(
                data['performance_score'], 'performance_score'
            )
        
        return data
    
    def _anonymize_workflow_efficiency(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize workflow efficiency data"""
        # Add noise to bottleneck frequency
        if 'bottleneck_frequency' in data:
            data['bottleneck_frequency'] = self._add_differential_privacy_noise(
                data['bottleneck_frequency'], 'confidence_score'
            )
        
        # Keep resolution time bucket as-is (already bucketed)
        # Generalize bottleneck types
        if 'most_common_bottleneck_type' in data:
            data['most_common_bottleneck_type'] = self._generalize_bottleneck_type(
                data['most_common_bottleneck_type']
            )
        
        # Add noise to efficiency score
        if 'efficiency_score' in data:
            data['efficiency_score'] = self._add_differential_privacy_noise(
                data['efficiency_score'], 'confidence_score'
            )
        
        # Anonymize team structure if present
        if 'team_structure' in data:
            data['team_structure'] = self._anonymize_team_optimization(
                {'team_structure': data['team_structure']}
            )['team_structure']
        
        return data
    
    def _anonymize_ai_effectiveness(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize AI effectiveness data"""
        # Keep recommendation type as-is (already categorical)
        
        # Add noise to confidence score
        if 'confidence_score' in data:
            data['confidence_score'] = self._add_differential_privacy_noise(
                data['confidence_score'], 'confidence_score'
            )
        
        # Keep boolean values as-is (already anonymized)
        
        # Anonymize context
        if 'context' in data:
            context = data['context']
            
            # Keep bucketed values as-is but add slight noise
            for key in ['project_size_bucket', 'team_size_bucket']:
                if key in context:
                    context[key] = self._add_noise_to_bucket(context[key], 'team_size')
            
            # Generalize industry hint further
            if 'industry_hint' in context:
                context['industry_hint'] = self._generalize_industry(context['industry_hint'])
        
        # Add noise to improvement potential
        if 'improvement_potential' in data:
            data['improvement_potential'] = self._add_differential_privacy_noise(
                data['improvement_potential'], 'confidence_score'
            )
        
        return data
    
    def _anonymize_resource_optimization(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize resource optimization data"""
        # Add noise to utilization ranges
        if 'optimal_utilization_range' in data:
            range_data = data['optimal_utilization_range']
            if isinstance(range_data, (list, tuple)) and len(range_data) == 2:
                data['optimal_utilization_range'] = [
                    self._add_differential_privacy_noise(range_data[0], 'confidence_score'),
                    self._add_differential_privacy_noise(range_data[1], 'confidence_score')
                ]
        
        # Add noise to correlation values
        for key in ['performance_correlation', 'burnout_threshold', 'efficiency_peak', 'sustainability_score']:
            if key in data:
                data[key] = self._add_differential_privacy_noise(
                    data[key], 'confidence_score'
                )
        
        return data
    
    def _anonymize_market_trends(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize market trends data"""
        # Generalize emerging patterns to broader categories
        if 'emerging_patterns' in data:
            data['emerging_patterns'] = [
                self._generalize_feature_name(pattern) 
                for pattern in data['emerging_patterns']
            ]
        
        if 'declining_features' in data:
            data['declining_features'] = [
                self._generalize_feature_name(feature)
                for feature in data['declining_features']
            ]
        
        # Add noise to adoption velocity
        if 'adoption_velocity' in data:
            data['adoption_velocity'] = self._add_differential_privacy_noise(
                data['adoption_velocity'], 'confidence_score'
            )
        
        # Generalize user segments
        if 'user_segment_hints' in data:
            data['user_segment_hints'] = [
                self._generalize_user_segment(segment)
                for segment in data['user_segment_hints']
            ]
        
        return data
    
    def _apply_common_anonymization(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply common anonymization techniques to all data"""
        # Remove or hash any remaining identifiers
        sensitive_keys = ['id', 'user_id', 'project_id', 'team_id', 'name']
        
        for key in list(data.keys()):
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                if isinstance(data[key], str):
                    data[key] = self._hash_identifier(data[key])
                else:
                    # Remove non-string identifiers
                    del data[key]
        
        # Recursively apply to nested dictionaries
        for key, value in data.items():
            if isinstance(value, dict):
                data[key] = self._apply_common_anonymization(value)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                data[key] = [self._apply_common_anonymization(item) for item in value]
        
        return data
    
    def _add_differential_privacy_noise(self, value: float, data_type: str) -> float:
        """Add calibrated Laplace noise for differential privacy"""
        params = self.noise_params.get(data_type, {'sensitivity': 1.0, 'epsilon': 0.1})
        
        # Laplace mechanism: noise scale = sensitivity / epsilon
        scale = params['sensitivity'] / params['epsilon']
        noise = np.random.laplace(0, scale)
        
        # Add noise and clamp to reasonable bounds
        noisy_value = value + noise
        
        # Clamp based on data type
        if data_type in ['confidence_score', 'performance_score']:
            return max(0.0, min(1.0, noisy_value))
        elif data_type == 'velocity':
            return max(0.0, noisy_value)
        else:
            return noisy_value
    
    def _generalize_value(self, value: Union[int, float], category: str) -> str:
        """Generalize a numeric value to a category"""
        if category not in self.generalization_rules:
            return str(value)  # Fallback
        
        rules = self.generalization_rules[category]
        for min_val, max_val, label in rules:
            if min_val <= value < max_val:
                return label
        
        return rules[-1][2]  # Return highest category if value exceeds all ranges
    
    def _generalize_sample_size(self, size: int) -> str:
        """Generalize sample size to protect against fingerprinting"""
        if size <= 10:
            return 'small'
        elif size <= 100:
            return 'medium'
        elif size <= 1000:
            return 'large'
        else:
            return 'very_large'
    
    def _anonymize_timestamp(self, timestamp: str) -> str:
        """Anonymize timestamp to hour bucket"""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            # Round to nearest hour
            rounded = dt.replace(minute=0, second=0, microsecond=0)
            return rounded.isoformat()
        except Exception:
            return timestamp  # Return as-is if parsing fails
    
    def _anonymize_distribution(self, distribution: List[str]) -> List[str]:
        """Anonymize a distribution by shuffling and generalizing"""
        # Count occurrences of each bucket
        bucket_counts = {}
        for bucket in distribution:
            bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
        
        # Only return buckets with sufficient count (k-anonymity)
        filtered_buckets = [
            bucket for bucket, count in bucket_counts.items() 
            if count >= self.k_anonymity
        ]
        
        return filtered_buckets
    
    def _hash_identifier(self, identifier: str) -> str:
        """Create a secure, consistent hash of an identifier"""
        return hmac.new(
            self.secret_key.encode(),
            identifier.encode(),
            hashlib.sha256
        ).hexdigest()[:8]  # Use first 8 characters for brevity
    
    def _generate_secret_key(self) -> str:
        """Generate a secret key for consistent hashing"""
        return hashlib.sha256(f"pm-agent-anonymizer-{random.random()}".encode()).hexdigest()
    
    def _add_noise_to_bucket(self, bucket: str, category: str) -> str:
        """Add semantic noise to bucket categories"""
        # For some categories, occasionally return a neighboring bucket
        if random.random() < 0.1:  # 10% chance of semantic noise
            if category == 'team_size':
                size_buckets = ['micro', 'small', 'medium', 'large', 'enterprise']
                if bucket in size_buckets:
                    idx = size_buckets.index(bucket)
                    # Move to adjacent bucket occasionally
                    if idx > 0 and random.random() < 0.5:
                        return size_buckets[idx - 1]
                    elif idx < len(size_buckets) - 1:
                        return size_buckets[idx + 1]
        
        return bucket
    
    # Generalization helper methods
    def _generalize_pattern_type(self, pattern: str) -> str:
        """Generalize failure pattern types"""
        generalization_map = {
            'steady_decline': 'gradual_degradation',
            'erratic_decline': 'volatile_degradation',
            'volatile_instability': 'volatile_degradation',
            'gradual_degradation': 'gradual_degradation'
        }
        return generalization_map.get(pattern, 'unknown_pattern')
    
    def _generalize_warning_signals(self, signals: List[str]) -> List[str]:
        """Generalize warning signal types"""
        signal_map = {
            'high_blocked_tasks': 'workflow_issues',
            'overdue_accumulation': 'timeline_issues',
            'low_velocity': 'productivity_issues',
            'resource_constraints': 'resource_issues'
        }
        
        return [signal_map.get(signal, 'general_issue') for signal in signals]
    
    def _generalize_bottleneck_type(self, bottleneck: str) -> str:
        """Generalize bottleneck types"""
        type_map = {
            'review_bottleneck': 'process_bottleneck',
            'dependency_bottleneck': 'coordination_bottleneck',
            'resource_bottleneck': 'capacity_bottleneck',
            'technical_bottleneck': 'implementation_bottleneck'
        }
        return type_map.get(bottleneck, 'process_bottleneck')
    
    def _generalize_industry(self, industry: str) -> str:
        """Generalize industry hints to broader categories"""
        # Map specific industries to broader technology categories
        return 'tech_sector'  # Very broad generalization
    
    def _generalize_feature_name(self, feature: str) -> str:
        """Generalize feature names to broad categories"""
        feature_categories = [
            'workflow_feature', 'analytics_feature', 'integration_feature',
            'automation_feature', 'collaboration_feature', 'monitoring_feature'
        ]
        
        # Use hash to consistently map features to categories
        hash_val = int(hashlib.md5(feature.encode()).hexdigest()[:8], 16)
        return feature_categories[hash_val % len(feature_categories)]
    
    def _generalize_user_segment(self, segment: str) -> str:
        """Generalize user segments"""
        segment_map = {
            'segment_a': 'enterprise_users',
            'segment_b': 'small_teams',
            'segment_c': 'individual_users'
        }
        return segment_map.get(segment, 'general_users')
    
    def validate_anonymization(self, original: StrategicInsight, anonymized: StrategicInsight) -> Dict[str, Any]:
        """Validate that anonymization preserved privacy while maintaining utility"""
        validation_results = {
            'privacy_preserved': True,
            'utility_maintained': True,
            'issues': []
        }
        
        # Check for remaining identifiers
        anonymized_str = json.dumps(anonymized.data)
        if any(keyword in anonymized_str.lower() for keyword in ['user', 'project', 'team', 'company']):
            validation_results['privacy_preserved'] = False
            validation_results['issues'].append('Potential identifiers remain')
        
        # Check that confidence scores are still reasonable
        if anonymized.confidence_score < 0 or anonymized.confidence_score > 1:
            validation_results['utility_maintained'] = False
            validation_results['issues'].append('Confidence score out of bounds')
        
        # Check timestamp bucketing
        try:
            orig_time = datetime.fromisoformat(original.timestamp_bucket.replace('Z', '+00:00'))
            anon_time = datetime.fromisoformat(anonymized.timestamp_bucket.replace('Z', '+00:00'))
            
            # Should be rounded to hour
            if anon_time.minute != 0 or anon_time.second != 0:
                validation_results['privacy_preserved'] = False
                validation_results['issues'].append('Timestamp not properly bucketed')
                
        except Exception:
            validation_results['issues'].append('Timestamp validation failed')
        
        return validation_results