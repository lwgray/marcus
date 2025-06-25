"""
Unit tests for the Privacy-Preserving Telemetry Client

Tests the telemetry client's privacy features, consent management,
data anonymization, and strategic intelligence collection capabilities.
"""

import pytest
import asyncio
import json
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from pathlib import Path

from src.telemetry.client import TelemetryClient
from src.telemetry.strategic_collector import InsightCategory, StrategicInsight
from src.telemetry.consent import ConsentLevel, DataSubjectRights
from src.core.models import ProjectState, WorkerStatus, RiskLevel


class TestTelemetryClient:
    """Test suite for the TelemetryClient class"""
    
    @pytest.fixture
    def temp_config_path(self):
        """Create a temporary config file path"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "telemetry_test.json")
            yield config_path
    
    @pytest.fixture
    def telemetry_client(self, temp_config_path):
        """Create a test telemetry client with temporary config"""
        return TelemetryClient(config_path=temp_config_path)
    
    @pytest.fixture
    def sample_project_state(self):
        """Create sample project state for testing"""
        return ProjectState(
            board_id="TEST-BOARD-001",
            project_name="Test Project",
            total_tasks=50,
            completed_tasks=30,
            in_progress_tasks=15,
            blocked_tasks=5,
            progress_percent=60.0,
            overdue_tasks=[],
            team_velocity=8.5,
            risk_level=RiskLevel.MEDIUM,
            last_updated=datetime.now()
        )
    
    @pytest.fixture
    def sample_team_status(self):
        """Create sample team status for testing"""
        return [
            WorkerStatus(
                worker_id="worker-001",
                name="Alice",
                role="backend_developer",
                email="alice@example.com",
                current_tasks=[],
                completed_tasks_count=25,
                capacity=40,
                skills=["python", "postgresql", "aws"],
                availability={"monday": True, "tuesday": True, "wednesday": True, "thursday": True, "friday": True},
                performance_score=1.2
            ),
            WorkerStatus(
                worker_id="worker-002", 
                name="Bob",
                role="frontend_developer",
                email="bob@example.com",
                current_tasks=[],
                completed_tasks_count=18,
                capacity=35,
                skills=["react", "typescript", "css"],
                availability={"monday": True, "tuesday": True, "wednesday": True, "thursday": True, "friday": True},
                performance_score=1.0
            )
        ]
    
    @pytest.fixture
    def sample_health_history(self):
        """Create sample health analysis history"""
        return [
            {
                'overall_health': 'green',
                'timestamp': datetime.now().isoformat(),
                'risk_factors': [],
                'timeline_prediction': {'confidence': 0.9}
            },
            {
                'overall_health': 'yellow',
                'timestamp': (datetime.now() - timedelta(hours=1)).isoformat(),
                'risk_factors': [{'type': 'resource', 'severity': 'medium'}],
                'timeline_prediction': {'confidence': 0.7}
            }
        ]
    
    def test_client_initialization_default_config(self, temp_config_path):
        """Test client initializes with default privacy-first configuration"""
        client = TelemetryClient(config_path=temp_config_path)
        
        # Should be disabled by default (opt-in only)
        assert not client.enabled
        assert client.config['enabled'] is False
        
        # Should have privacy-first defaults
        assert client.config['auto_transmit'] is True
        assert client.config['transmission_interval'] == 86400  # 24 hours
        assert client.config['min_batch_size'] == 10
        
        # Should have encryption key
        assert 'encryption_key' in client.config
        assert 'installation_id' in client.config
    
    def test_client_initialization_with_existing_config(self, temp_config_path):
        """Test client loads existing configuration correctly"""
        # Create existing config
        existing_config = {
            'enabled': True,
            'consent': {'failure_prediction': True},
            'installation_id': 'test-installation-123',
            'encryption_key': 'test-key'
        }
        
        with open(temp_config_path, 'w') as f:
            json.dump(existing_config, f)
        
        client = TelemetryClient(config_path=temp_config_path)
        
        # Should load existing settings
        assert client.config['installation_id'] == 'test-installation-123'
        assert client.config['encryption_key'] == 'test-key'
    
    @pytest.mark.asyncio
    async def test_client_initialization_and_shutdown(self, telemetry_client):
        """Test client initialization and graceful shutdown"""
        # Mock transmission task to avoid real network calls
        with patch('asyncio.create_task') as mock_create_task:
            await telemetry_client.initialize()
            
            # Should create transmission task if enabled
            if telemetry_client.enabled:
                mock_create_task.assert_called_once()
        
        # Test graceful shutdown
        await telemetry_client.shutdown()
        
        # Should not have any pending tasks
        assert telemetry_client.transmission_task is None or telemetry_client.transmission_task.cancelled()
    
    @pytest.mark.asyncio
    async def test_collect_project_health_insight_without_consent(
        self, 
        telemetry_client, 
        sample_project_state, 
        sample_team_status, 
        sample_health_history
    ):
        """Test that no data is collected without user consent"""
        # Ensure no consent given
        assert not telemetry_client.enabled
        
        await telemetry_client.collect_project_health_insight(
            sample_project_state,
            sample_health_history,
            sample_team_status
        )
        
        # Should not collect any insights without consent
        assert len(telemetry_client.pending_insights) == 0
    
    @pytest.mark.asyncio 
    async def test_collect_project_health_insight_with_consent(
        self,
        telemetry_client,
        sample_project_state,
        sample_team_status,
        sample_health_history
    ):
        """Test data collection with proper consent"""
        # Give consent for health insights
        consent_response = {
            'categories': {
                'failure_prediction': {'level': ConsentLevel.BASIC.value},
                'team_optimization': {'level': ConsentLevel.BASIC.value}
            }
        }
        telemetry_client.update_consent(consent_response)
        
        # Verify consent was updated properly
        assert telemetry_client.enabled is True
        assert telemetry_client._has_consent_for(InsightCategory.FAILURE_PREDICTION) is True
        
        # Mock the strategic collector to avoid complex analysis
        with patch.object(telemetry_client.strategic_collector, 'collect_project_lifecycle_insight') as mock_collect:
            mock_collect.return_value = [
                StrategicInsight(
                    category=InsightCategory.FAILURE_PREDICTION,
                    data={'test': 'data'},
                    timestamp_bucket=datetime.now().isoformat(),
                    confidence_score=0.8,
                    sample_size_hint=10
                )
            ]
            
            await telemetry_client.collect_project_health_insight(
                sample_project_state,
                sample_health_history,
                sample_team_status
            )
            
            # Should have collected insights
            assert len(telemetry_client.pending_insights) > 0
            mock_collect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_collect_workflow_optimization_insight(
        self,
        telemetry_client,
        sample_project_state,
        sample_team_status
    ):
        """Test workflow optimization insight collection"""
        # Give consent for workflow optimization
        consent_response = {
            'categories': {
                'workflow_efficiency': {'level': ConsentLevel.BASIC.value}
            }
        }
        telemetry_client.update_consent(consent_response)
        
        task_transitions = [
            {'from': 'todo', 'to': 'in_progress', 'duration': 2.5},
            {'from': 'in_progress', 'to': 'done', 'duration': 24.0}
        ]
        resolution_times = {'review': 4.0, 'implementation': 16.0}
        team_structure = {
            'size': len(sample_team_status),
            'roles': ['backend_developer', 'frontend_developer']
        }
        bottleneck_events = []
        
        with patch.object(telemetry_client.strategic_collector, 'collect_workflow_bottleneck_patterns') as mock_collect:
            mock_collect.return_value = StrategicInsight(
                category=InsightCategory.WORKFLOW_EFFICIENCY,
                data={'workflow': 'optimized'},
                timestamp_bucket=datetime.now().isoformat(),
                confidence_score=0.7,
                sample_size_hint=5
            )
            
            await telemetry_client.collect_workflow_optimization_insight(
                task_transitions,
                resolution_times,
                team_structure,
                bottleneck_events
            )
            
            mock_collect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_collect_ai_decision_outcome(self, telemetry_client):
        """Test AI decision outcome recording"""
        # Give consent for AI effectiveness
        consent_response = {
            'categories': {
                'ai_effectiveness': {'level': ConsentLevel.BASIC.value}
            }
        }
        telemetry_client.update_consent(consent_response)
        
        recommendation = {
            'type': 'task_assignment',
            'confidence': 0.85,
            'reasoning': 'skill match'
        }
        
        context = {
            'total_tasks': 50,
            'team_size': 5,
            'risk_level': 'medium',
            'project_type': 'web_application'
        }
        
        with patch.object(telemetry_client.strategic_collector, 'collect_ai_decision_feedback') as mock_collect:
            mock_collect.return_value = StrategicInsight(
                category=InsightCategory.AI_EFFECTIVENESS,
                data={'ai_feedback': 'positive'},
                timestamp_bucket=datetime.now().isoformat(),
                confidence_score=0.9,
                sample_size_hint=1
            )
            
            await telemetry_client.record_ai_decision_outcome(
                decision_id="decision-123",
                recommendation=recommendation,
                user_action="accepted",
                outcome_success=True,
                context=context
            )
            
            mock_collect.assert_called_once()
    
    def test_consent_management(self, telemetry_client):
        """Test consent request and management"""
        categories = [InsightCategory.FAILURE_PREDICTION, InsightCategory.TEAM_OPTIMIZATION]
        
        # Request consent
        consent_request = telemetry_client.request_consent(categories)
        
        # Should contain detailed information
        assert 'overview' in consent_request
        assert 'categories' in consent_request
        assert 'user_rights' in consent_request
        assert len(consent_request['categories']) == 2
        
        # Update consent
        consent_response = {
            'categories': {
                'failure_prediction': {'level': ConsentLevel.BASIC.value},
                'team_optimization': {'level': ConsentLevel.DENIED.value}
            }
        }
        
        telemetry_client.update_consent(consent_response)
        
        # Check consent status
        status = telemetry_client.get_consent_status()
        assert status['any_consent_given'] is True
        assert status['categories']['failure_prediction']['has_consent'] is True
        assert status['categories']['team_optimization']['has_consent'] is False
    
    def test_consent_revocation(self, telemetry_client):
        """Test consent revocation functionality"""
        # Give initial consent
        consent_response = {
            'categories': {
                'failure_prediction': {'level': ConsentLevel.BASIC.value},
                'ai_effectiveness': {'level': ConsentLevel.BASIC.value}
            }
        }
        telemetry_client.update_consent(consent_response)
        
        # Verify consent given
        assert telemetry_client.enabled is True
        
        # Revoke all consent
        telemetry_client.revoke_all_consent()
        
        # Should be disabled and all consent revoked
        assert telemetry_client.enabled is False
        assert len(telemetry_client.pending_insights) == 0
        
        status = telemetry_client.get_consent_status()
        assert status['any_consent_given'] is False
    
    def test_privacy_protection_checks(self, telemetry_client):
        """Test that privacy protection mechanisms are in place"""
        # Check encryption
        assert telemetry_client.encryption_key is not None
        assert telemetry_client.cipher is not None
        
        # Check anonymization
        assert telemetry_client.anonymizer is not None
        
        # Check consent manager
        assert telemetry_client.consent_manager is not None
        
        # Installation ID should be anonymous
        assert telemetry_client.installation_id != ""
        assert len(telemetry_client.installation_id) == 36  # UUID length
    
    @pytest.mark.asyncio
    async def test_data_transmission_disabled_by_default(self, telemetry_client):
        """Test that data transmission is disabled by default"""
        # Add some mock insights
        insight = StrategicInsight(
            category=InsightCategory.FAILURE_PREDICTION,
            data={'test': 'data'},
            timestamp_bucket=datetime.now().isoformat(),
            confidence_score=0.8,
            sample_size_hint=1
        )
        telemetry_client.pending_insights.append(insight)
        
        # Try to transmit (should do nothing without consent)
        with patch('aiohttp.ClientSession') as mock_session:
            await telemetry_client._transmit_insights(force=True)
            
            # Should not make any HTTP requests without consent
            mock_session.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_data_transmission_with_consent(self, telemetry_client):
        """Test data transmission when user has given consent"""
        # Give consent
        consent_response = {
            'categories': {
                'failure_prediction': {'level': ConsentLevel.BASIC.value}
            }
        }
        telemetry_client.update_consent(consent_response)
        
        # Add mock insights
        insight = StrategicInsight(
            category=InsightCategory.FAILURE_PREDICTION,
            data={'anonymized': 'data'},
            timestamp_bucket=datetime.now().isoformat(),
            confidence_score=0.8,
            sample_size_hint=1
        )
        telemetry_client.pending_insights.append(insight)
        
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status = 200
        
        mock_session = Mock()
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            await telemetry_client._transmit_insights(force=True)
            
            # Should have made HTTP request
            mock_session.post.assert_called_once()
            
            # Should have cleared transmitted insights
            assert len(telemetry_client.pending_insights) == 0
    
    def test_insights_summary_generation(self, telemetry_client):
        """Test generation of insights summary for transparency"""
        # Without consent
        summary = telemetry_client.get_collected_insights_summary()
        assert summary['status'] == 'disabled'
        
        # With consent and some insights
        consent_response = {
            'categories': {
                'failure_prediction': {'level': ConsentLevel.BASIC.value},
                'workflow_efficiency': {'level': ConsentLevel.BASIC.value}
            }
        }
        telemetry_client.update_consent(consent_response)
        
        # Add some mock insights
        insights = [
            StrategicInsight(
                category=InsightCategory.FAILURE_PREDICTION,
                data={'test': 'data1'},
                timestamp_bucket=datetime.now().isoformat(),
                confidence_score=0.8,
                sample_size_hint=1
            ),
            StrategicInsight(
                category=InsightCategory.WORKFLOW_EFFICIENCY,
                data={'test': 'data2'},
                timestamp_bucket=datetime.now().isoformat(),
                confidence_score=0.7,
                sample_size_hint=1
            )
        ]
        telemetry_client.pending_insights.extend(insights)
        
        summary = telemetry_client.get_collected_insights_summary()
        assert summary['status'] == 'active'
        assert summary['pending_insights'] == 2
        assert 'failure_patterns' in summary['categories']
        assert 'workflow_patterns' in summary['categories']
        assert summary['privacy_level'] == 'maximum'
    
    def test_queue_size_management(self, telemetry_client):
        """Test that insight queue size is properly managed"""
        # Give consent
        consent_response = {
            'categories': {
                'failure_prediction': {'level': ConsentLevel.BASIC.value}
            }
        }
        telemetry_client.update_consent(consent_response)
        
        # Set small max queue size for testing
        telemetry_client.config['max_queue_size'] = 5
        
        # Add more insights than max queue size
        for i in range(10):
            insight = StrategicInsight(
                category=InsightCategory.FAILURE_PREDICTION,
                data={'test': f'data{i}'},
                timestamp_bucket=datetime.now().isoformat(),
                confidence_score=0.8,
                sample_size_hint=1
            )
            telemetry_client._queue_insight(insight)
        
        # Should not exceed max queue size
        assert len(telemetry_client.pending_insights) <= 5
    
    def test_error_handling_in_collection(self, telemetry_client, sample_project_state, sample_team_status):
        """Test error handling during insight collection"""
        # Give consent
        consent_response = {
            'categories': {
                'failure_prediction': {'level': ConsentLevel.BASIC.value}
            }
        }
        telemetry_client.update_consent(consent_response)
        
        # Mock strategic collector to raise exception
        with patch.object(telemetry_client.strategic_collector, 'collect_project_lifecycle_insight', side_effect=Exception("Test error")):
            # Should not raise exception - errors should be handled gracefully
            try:
                asyncio.run(telemetry_client.collect_project_health_insight(
                    sample_project_state,
                    [],
                    sample_team_status
                ))
            except Exception as e:
                pytest.fail(f"Telemetry collection should handle errors gracefully: {e}")
        
        # Should not have collected any insights due to error
        assert len(telemetry_client.pending_insights) == 0
    
    def test_config_file_persistence(self, temp_config_path):
        """Test that configuration is properly persisted to file"""
        client = TelemetryClient(config_path=temp_config_path)
        
        # Update consent
        consent_response = {
            'categories': {
                'failure_prediction': {'level': ConsentLevel.BASIC.value}
            }
        }
        client.update_consent(consent_response)
        
        # Create new client with same config path
        client2 = TelemetryClient(config_path=temp_config_path)
        
        # Should load the same consent settings
        status = client2.get_consent_status()
        assert status['any_consent_given'] is True
    
    def test_data_subject_rights_exercise(self, telemetry_client):
        """Test data subject rights functionality"""
        # Give consent first
        consent_response = {
            'categories': {
                'failure_prediction': {'level': ConsentLevel.BASIC.value}
            }
        }
        telemetry_client.update_consent(consent_response)
        
        # Exercise right to access
        response = telemetry_client.consent_manager.exercise_data_right(
            DataSubjectRights.ACCESS,
            {'request_type': 'full_export'}
        )
        
        assert 'request_id' in response
        assert response['status'] == 'submitted'
        assert 'expected_completion' in response
        
        # Exercise right to deletion
        deletion_response = telemetry_client.consent_manager.exercise_data_right(
            DataSubjectRights.ERASURE
        )
        
        assert 'request_id' in deletion_response
        assert deletion_response['status'] == 'submitted'
    
    def test_consent_audit_trail(self, telemetry_client):
        """Test that consent decisions are properly audited"""
        # Give initial consent
        consent_response = {
            'categories': {
                'failure_prediction': {'level': ConsentLevel.BASIC.value}
            }
        }
        telemetry_client.update_consent(consent_response)
        
        # Update consent
        updated_response = {
            'categories': {
                'failure_prediction': {'level': ConsentLevel.DENIED.value},
                'team_optimization': {'level': ConsentLevel.BASIC.value}
            }
        }
        telemetry_client.update_consent(updated_response)
        
        # Check audit trail
        audit_trail = telemetry_client.consent_manager.get_consent_audit_trail()
        assert len(audit_trail) >= 2  # At least 2 consent updates
        
        for entry in audit_trail:
            assert 'action' in entry
            assert 'timestamp' in entry
            assert 'version' in entry
    
    def test_strategic_value_validation(self, telemetry_client):
        """Test that collected insights have strategic value"""
        # This test validates that our telemetry focuses on strategic insights
        # rather than just collecting random data
        
        strategic_categories = [
            InsightCategory.FAILURE_PREDICTION,  # Competitive edge: predict failures earlier
            InsightCategory.TEAM_OPTIMIZATION,   # Competitive edge: optimal team composition
            InsightCategory.WORKFLOW_EFFICIENCY,  # Competitive edge: eliminate bottlenecks
            InsightCategory.AI_EFFECTIVENESS,    # Competitive edge: self-improving AI
            InsightCategory.RESOURCE_OPTIMIZATION, # Competitive edge: prevent burnout
            InsightCategory.MARKET_TRENDS        # Competitive edge: predict feature demand
        ]
        
        # Verify all strategic categories are supported
        for category in strategic_categories:
            assert category in InsightCategory
        
        # Verify consent request includes strategic explanations
        consent_request = telemetry_client.request_consent(strategic_categories)
        
        for category in strategic_categories:
            category_info = consent_request['categories'][category.value]
            assert 'benefits' in category_info
            assert 'data_collected' in category_info
            assert len(category_info['benefits']) > 0  # Should list competitive benefits
    
    @pytest.mark.asyncio
    async def test_feature_usage_insight_collection(self, telemetry_client):
        """Test collection of feature usage insights for market trends"""
        # Give consent for market trends
        consent_response = {
            'categories': {
                'market_trends': {'level': ConsentLevel.BASIC.value}
            }
        }
        telemetry_client.update_consent(consent_response)
        
        feature_usage = {
            'health_monitoring': 45,
            'ai_recommendations': 32,
            'team_analytics': 18,
            'workflow_automation': 25
        }
        
        user_behavior = {
            'session_duration': 45.5,
            'features_per_session': 3.2,
            'power_user_indicators': ['custom_dashboards', 'api_usage']
        }
        
        adoption_patterns = {
            'onboarding_completion': 0.85,
            'feature_discovery_rate': 0.67,
            'retention_indicators': 0.92
        }
        
        with patch.object(telemetry_client.strategic_collector, 'collect_market_trend_signals') as mock_collect:
            mock_collect.return_value = StrategicInsight(
                category=InsightCategory.MARKET_TRENDS,
                data={'market_signals': 'positive'},
                timestamp_bucket=datetime.now().isoformat(),
                confidence_score=0.6,
                sample_size_hint=100
            )
            
            await telemetry_client.collect_feature_usage_insight(
                feature_usage,
                user_behavior,
                adoption_patterns
            )
            
            mock_collect.assert_called_once()
            args = mock_collect.call_args[0]
            assert args[0] == feature_usage
            assert args[1] == user_behavior
            assert args[2] == adoption_patterns