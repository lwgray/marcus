"""
Unit tests for the Consent Management System

Tests consent request generation, user consent management, data subject rights,
audit trails, and privacy compliance functionality.
"""

import pytest
import json
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

from src.telemetry.consent import ConsentManager, ConsentLevel, DataSubjectRights
from src.telemetry.strategic_collector import InsightCategory


class TestConsentManager:
    """Test suite for the ConsentManager class"""
    
    @pytest.fixture
    def consent_manager(self):
        """Create a fresh consent manager for testing"""
        return ConsentManager()
    
    @pytest.fixture
    def consent_manager_with_data(self):
        """Create consent manager with some existing consent data"""
        existing_data = {
            'failure_prediction': {
                'consent_level': ConsentLevel.BASIC.value,
                'granted_at': datetime.now().isoformat(),
                'version': '1.0',
                'explicit_consent': True,
                'conditions': []
            },
            'global': {
                'last_updated': datetime.now().isoformat(),
                'version': '1.0',
                'audit_trail': []
            }
        }
        return ConsentManager(existing_data)
    
    @pytest.fixture
    def sample_categories(self):
        """Sample insight categories for testing"""
        return [
            InsightCategory.FAILURE_PREDICTION,
            InsightCategory.TEAM_OPTIMIZATION,
            InsightCategory.WORKFLOW_EFFICIENCY
        ]
    
    def test_default_consent_structure(self, consent_manager):
        """Test that consent manager initializes with proper default structure"""
        # All categories should default to denied
        for category in InsightCategory:
            consent_data = consent_manager.get_consent_for_category(category)
            assert consent_data['consent_level'] == ConsentLevel.DENIED.value
            assert consent_data['explicit_consent'] is False
            assert consent_data['granted_at'] is None
        
        # Global structure should exist
        assert 'global' in consent_manager.consent_data
        assert 'audit_trail' in consent_manager.consent_data['global']
    
    def test_consent_request_generation(self, consent_manager, sample_categories):
        """Test generation of comprehensive consent request"""
        consent_request = consent_manager.create_consent_request(sample_categories)
        
        # Should have all required sections
        assert 'version' in consent_request
        assert 'overview' in consent_request
        assert 'categories' in consent_request
        assert 'user_rights' in consent_request
        assert 'recommendations' in consent_request
        
        # Overview should explain privacy principles
        overview = consent_request['overview']
        assert 'title' in overview
        assert 'description' in overview
        assert 'key_principles' in overview
        assert len(overview['key_principles']) > 0
        
        # Each category should have detailed explanation
        for category in sample_categories:
            category_info = consent_request['categories'][category.value]
            assert 'title' in category_info
            assert 'description' in category_info
            assert 'data_collected' in category_info
            assert 'benefits' in category_info
            assert 'retention' in category_info
            assert 'sharing' in category_info
            assert 'current_consent' in category_info
            assert 'recommended_level' in category_info
            
            # Benefits should list competitive advantages
            assert len(category_info['benefits']) > 0
            
            # Data collection should be specific
            assert len(category_info['data_collected']) > 0
        
        # User rights should be explained
        user_rights = consent_request['user_rights']
        expected_rights = ['access', 'deletion', 'portability', 'objection', 'rectification']
        for right in expected_rights:
            assert right in user_rights
            assert len(user_rights[right]) > 10  # Should have meaningful explanation
        
        # Should include contact and legal information
        assert 'privacy_policy_url' in consent_request
        assert 'contact_email' in consent_request
        assert 'legal_basis' in consent_request
        assert 'data_retention' in consent_request
        assert 'third_party_sharing' in consent_request
    
    def test_consent_update_and_storage(self, consent_manager):
        """Test consent decision storage and update"""
        consent_response = {
            'categories': {
                'failure_prediction': {
                    'level': ConsentLevel.BASIC.value,
                    'conditions': ['review_annually']
                },
                'team_optimization': {
                    'level': ConsentLevel.DENIED.value
                },
                'workflow_efficiency': {
                    'level': ConsentLevel.ENHANCED.value,
                    'conditions': ['anonymize_extra']
                }
            },
            'contact_preferences': {
                'email_updates': False,
                'product_announcements': True
            },
            'data_retention': 'minimal'
        }
        
        consent_manager.update_consent(consent_response)
        
        # Check individual category consent
        failure_consent = consent_manager.get_consent_for_category(InsightCategory.FAILURE_PREDICTION)
        assert failure_consent['consent_level'] == ConsentLevel.BASIC.value
        assert failure_consent['explicit_consent'] is True
        assert failure_consent['conditions'] == ['review_annually']
        assert failure_consent['granted_at'] is not None
        
        team_consent = consent_manager.get_consent_for_category(InsightCategory.TEAM_OPTIMIZATION)
        assert team_consent['consent_level'] == ConsentLevel.DENIED.value
        
        workflow_consent = consent_manager.get_consent_for_category(InsightCategory.WORKFLOW_EFFICIENCY)
        assert workflow_consent['consent_level'] == ConsentLevel.ENHANCED.value
        assert workflow_consent['conditions'] == ['anonymize_extra']
        
        # Check global preferences
        global_data = consent_manager.consent_data['global']
        assert global_data['contact_preferences'] == consent_response['contact_preferences']
        assert global_data['data_retention_preference'] == 'minimal'
        
        # Check audit trail
        audit_trail = global_data['audit_trail']
        assert len(audit_trail) > 0
        latest_entry = audit_trail[-1]
        assert latest_entry['action'] == 'consent_updated'
        assert 'timestamp' in latest_entry
        assert 'categories_changed' in latest_entry
    
    def test_consent_status_checking(self, consent_manager_with_data):
        """Test consent status checking functionality"""
        # Check individual category consent
        assert consent_manager_with_data.has_consent_for(InsightCategory.FAILURE_PREDICTION) is True
        assert consent_manager_with_data.has_consent_for(InsightCategory.TEAM_OPTIMIZATION) is False
        
        # Get comprehensive status
        status = consent_manager_with_data.get_consent_status()
        
        assert status['any_consent_given'] is True
        assert 'consent_version' in status
        assert 'last_updated' in status
        assert 'categories' in status
        assert 'global_preferences' in status
        assert 'next_review_due' in status
        
        # Check category-specific status
        categories_status = status['categories']
        assert categories_status['failure_prediction']['has_consent'] is True
        assert categories_status['failure_prediction']['level'] == ConsentLevel.BASIC.value
        assert categories_status['failure_prediction']['explicit'] is True
        
        # Other categories should be denied by default
        assert categories_status['team_optimization']['has_consent'] is False
        assert categories_status['team_optimization']['level'] == ConsentLevel.DENIED.value
    
    def test_consent_revocation(self, consent_manager_with_data):
        """Test consent revocation functionality"""
        # Initially has consent
        assert consent_manager_with_data.has_consent_for(InsightCategory.FAILURE_PREDICTION) is True
        
        # Revoke specific category
        consent_manager_with_data.revoke_category_consent(
            InsightCategory.FAILURE_PREDICTION, 
            "privacy_concerns"
        )
        
        # Should no longer have consent
        assert consent_manager_with_data.has_consent_for(InsightCategory.FAILURE_PREDICTION) is False
        
        # Check revocation is recorded
        consent_data = consent_manager_with_data.get_consent_for_category(InsightCategory.FAILURE_PREDICTION)
        assert consent_data['consent_level'] == ConsentLevel.DENIED.value
        assert consent_data['revoked_at'] is not None
        assert consent_data['revocation_reason'] == "privacy_concerns"
        
        # Check audit trail
        audit_trail = consent_manager_with_data.get_consent_audit_trail()
        revocation_entries = [entry for entry in audit_trail if entry['action'] == 'category_consent_revoked']
        assert len(revocation_entries) > 0
        latest_revocation = revocation_entries[-1]
        assert latest_revocation['category'] == InsightCategory.FAILURE_PREDICTION.value
        assert latest_revocation['reason'] == "privacy_concerns"
    
    def test_revoke_all_consent(self, consent_manager_with_data):
        """Test complete consent revocation"""
        # Initially has some consent
        status_before = consent_manager_with_data.get_consent_status()
        assert status_before['any_consent_given'] is True
        
        # Revoke all consent
        consent_manager_with_data.revoke_all_consent()
        
        # Should have no consent for any category
        for category in InsightCategory:
            assert consent_manager_with_data.has_consent_for(category) is False
        
        # Check global revocation flag
        global_data = consent_manager_with_data.consent_data['global']
        assert global_data['all_consent_revoked'] is True
        assert global_data['revoked_at'] is not None
        
        # Check audit trail
        audit_trail = consent_manager_with_data.get_consent_audit_trail()
        revocation_entries = [entry for entry in audit_trail if entry['action'] == 'all_consent_revoked']
        assert len(revocation_entries) > 0
        latest_revocation = revocation_entries[-1]
        assert len(latest_revocation['categories_affected']) == len(InsightCategory)
    
    def test_data_subject_rights_exercise(self, consent_manager):
        """Test exercise of data subject rights"""
        # Exercise right to access
        access_request = consent_manager.exercise_data_right(
            DataSubjectRights.ACCESS,
            {'request_type': 'full_export', 'format': 'json'}
        )
        
        assert 'request_id' in access_request
        assert access_request['status'] == 'submitted'
        assert 'expected_completion' in access_request
        assert 'instructions' in access_request
        assert 'contact_info' in access_request
        
        # Exercise right to deletion
        deletion_request = consent_manager.exercise_data_right(
            DataSubjectRights.ERASURE
        )
        
        assert deletion_request['request_id'] != access_request['request_id']
        assert deletion_request['status'] == 'submitted'
        
        # Exercise right to portability
        portability_request = consent_manager.exercise_data_right(
            DataSubjectRights.PORTABILITY,
            {'destination': 'email'}
        )
        
        assert 'request_id' in portability_request
        
        # Check that all requests are recorded
        global_data = consent_manager.consent_data['global']
        rights_requests = global_data['rights_requests']
        assert len(rights_requests) == 3
        
        # Verify each request is properly recorded
        request_types = [req['right'] for req in rights_requests]
        assert DataSubjectRights.ACCESS.value in request_types
        assert DataSubjectRights.ERASURE.value in request_types
        assert DataSubjectRights.PORTABILITY.value in request_types
        
        # Check audit trail includes rights exercise
        audit_trail = consent_manager.get_consent_audit_trail()
        rights_entries = [entry for entry in audit_trail if entry['action'] == 'data_right_exercised']
        assert len(rights_entries) == 3
    
    def test_consent_audit_trail(self, consent_manager):
        """Test comprehensive audit trail functionality"""
        # Perform various consent operations
        
        # 1. Initial consent
        consent_response = {
            'categories': {
                'failure_prediction': {'level': ConsentLevel.BASIC.value}
            }
        }
        consent_manager.update_consent(consent_response)
        
        # 2. Update consent
        updated_response = {
            'categories': {
                'failure_prediction': {'level': ConsentLevel.ENHANCED.value},
                'team_optimization': {'level': ConsentLevel.BASIC.value}
            }
        }
        consent_manager.update_consent(updated_response)
        
        # 3. Exercise a right
        consent_manager.exercise_data_right(DataSubjectRights.ACCESS)
        
        # 4. Revoke specific consent
        consent_manager.revoke_category_consent(InsightCategory.TEAM_OPTIMIZATION)
        
        # Check audit trail
        audit_trail = consent_manager.get_consent_audit_trail()
        assert len(audit_trail) >= 4
        
        # Verify trail contains expected actions
        actions = [entry['action'] for entry in audit_trail]
        assert 'consent_updated' in actions
        assert 'data_right_exercised' in actions
        assert 'category_consent_revoked' in actions
        
        # Each entry should have required fields
        for entry in audit_trail:
            assert 'action' in entry
            assert 'timestamp' in entry
            assert 'version' in entry
            
            # Timestamp should be valid ISO format
            datetime.fromisoformat(entry['timestamp'])
    
    def test_consent_expiration_checking(self, consent_manager):
        """Test consent expiration functionality"""
        # New consent should not be expired
        assert consent_manager.is_consent_expired() is False
        
        # Manually set old timestamp
        old_timestamp = datetime.now() - timedelta(days=800)  # Over 2 years ago
        consent_manager.last_updated = old_timestamp
        
        # Should now be expired
        assert consent_manager.is_consent_expired() is True
    
    def test_consent_data_export(self, consent_manager_with_data):
        """Test consent data export for portability"""
        exported_data = consent_manager_with_data.export_consent_data()
        
        # Should contain all necessary information
        assert 'version' in exported_data
        assert 'exported_at' in exported_data
        assert 'consent_data' in exported_data
        assert 'explanations' in exported_data
        assert 'format_version' in exported_data
        
        # Consent data should be complete
        consent_data = exported_data['consent_data']
        assert 'failure_prediction' in consent_data
        assert 'global' in consent_data
        
        # Explanations should include category details
        explanations = exported_data['explanations']
        for category in InsightCategory:
            assert category in explanations
            category_explanation = explanations[category]
            assert 'title' in category_explanation
            assert 'description' in category_explanation
            assert 'data_collected' in category_explanation
            assert 'benefits' in category_explanation
    
    def test_file_persistence(self):
        """Test saving and loading consent data from file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "consent_test.json")
            
            # Create manager and give some consent
            manager1 = ConsentManager()
            consent_response = {
                'categories': {
                    'failure_prediction': {'level': ConsentLevel.BASIC.value},
                    'ai_effectiveness': {'level': ConsentLevel.ENHANCED.value}
                }
            }
            manager1.update_consent(consent_response)
            
            # Save to file
            manager1.save_to_file(file_path)
            
            # Load from file
            manager2 = ConsentManager.load_from_file(file_path)
            
            # Should have same consent status
            assert manager2.has_consent_for(InsightCategory.FAILURE_PREDICTION) is True
            assert manager2.has_consent_for(InsightCategory.AI_EFFECTIVENESS) is True
            assert manager2.has_consent_for(InsightCategory.TEAM_OPTIMIZATION) is False
            
            # Consent levels should match
            failure_consent = manager2.get_consent_for_category(InsightCategory.FAILURE_PREDICTION)
            ai_consent = manager2.get_consent_for_category(InsightCategory.AI_EFFECTIVENESS)
            
            assert failure_consent['consent_level'] == ConsentLevel.BASIC.value
            assert ai_consent['consent_level'] == ConsentLevel.ENHANCED.value
    
    def test_file_loading_error_handling(self):
        """Test error handling when loading consent files"""
        # Test with non-existent file
        manager = ConsentManager.load_from_file("/non/existent/path.json")
        assert isinstance(manager, ConsentManager)
        assert not manager.has_consent_for(InsightCategory.FAILURE_PREDICTION)
        
        # Test with invalid JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_file.write("invalid json content")
            temp_file.flush()
            
            try:
                manager = ConsentManager.load_from_file(temp_file.name)
                assert isinstance(manager, ConsentManager)
                # Should default to no consent
                assert not manager.has_consent_for(InsightCategory.FAILURE_PREDICTION)
            finally:
                os.unlink(temp_file.name)
    
    def test_consent_recommendations(self, consent_manager, sample_categories):
        """Test consent recommendation generation"""
        consent_request = consent_manager.create_consent_request(sample_categories)
        
        recommendations = consent_request['recommendations']
        assert 'recommended_categories' in recommendations
        assert 'rationale' in recommendations
        assert 'start_small' in recommendations
        assert 'privacy_impact' in recommendations
        
        # Should recommend basic, low-risk categories
        recommended_categories = recommendations['recommended_categories']
        assert InsightCategory.FAILURE_PREDICTION.value in recommended_categories
        assert InsightCategory.WORKFLOW_EFFICIENCY.value in recommended_categories
        
        # Each category should have recommended level
        for category in sample_categories:
            category_info = consent_request['categories'][category.value]
            recommended_level = category_info['recommended_level']
            assert recommended_level in [level.value for level in ConsentLevel]
    
    def test_category_explanation_completeness(self, consent_manager):
        """Test that all insight categories have complete explanations"""
        for category in InsightCategory:
            explanation = consent_manager.category_explanations[category]
            
            # Each category should have all required fields
            required_fields = [
                'title', 'description', 'data_collected', 'benefits',
                'retention', 'sharing'
            ]
            
            for field in required_fields:
                assert field in explanation, f"Category {category.value} missing {field}"
                assert len(str(explanation[field])) > 0, f"Category {category.value} has empty {field}"
            
            # Benefits should explain competitive advantages
            benefits = explanation['benefits']
            assert len(benefits) > 0
            
            # At least one benefit should mention improvement or optimization
            benefit_text = ' '.join(benefits).lower()
            improvement_keywords = ['improve', 'optimize', 'better', 'enhance', 'increase']
            assert any(keyword in benefit_text for keyword in improvement_keywords)
            
            # Data collected should be specific and anonymous
            data_collected = explanation['data_collected']
            assert len(data_collected) > 0
            
            # Should emphasize anonymity
            data_text = ' '.join(data_collected).lower()
            privacy_keywords = ['anonymous', 'no individual', 'no personal', 'aggregated', 'generalized']
            assert any(keyword in data_text for keyword in privacy_keywords)
    
    def test_privacy_principles_enforcement(self, consent_manager, sample_categories):
        """Test that privacy principles are properly enforced"""
        consent_request = consent_manager.create_consent_request(sample_categories)
        
        # Overview should emphasize privacy
        overview = consent_request['overview']
        key_principles = overview['key_principles']
        
        # Should include key privacy principles
        principles_text = ' '.join(key_principles).lower()
        privacy_keywords = ['private', 'anonymous', 'control', 'revoke', 'transparent']
        
        for keyword in privacy_keywords:
            assert keyword in principles_text, f"Missing privacy principle: {keyword}"
        
        # Should emphasize user control
        assert any('control' in principle.lower() for principle in key_principles)
        assert any('revoke' in principle.lower() or 'exit' in principle.lower() for principle in key_principles)
        
        # Data retention should be clearly stated
        assert 'data_retention' in consent_request
        retention_policy = consent_request['data_retention']
        assert len(retention_policy) > 10  # Should be meaningful explanation
        
        # Third party sharing should be explicitly addressed
        assert 'third_party_sharing' in consent_request
        sharing_policy = consent_request['third_party_sharing']
        assert 'no data shared' in sharing_policy.lower() or 'not shared' in sharing_policy.lower()
    
    def test_gdpr_compliance_features(self, consent_manager):
        """Test GDPR compliance features"""
        # Test all required GDPR rights are supported
        gdpr_rights = [
            DataSubjectRights.ACCESS,
            DataSubjectRights.RECTIFICATION,
            DataSubjectRights.ERASURE,
            DataSubjectRights.RESTRICTION,
            DataSubjectRights.PORTABILITY,
            DataSubjectRights.OBJECTION
        ]
        
        for right in gdpr_rights:
            # Should be able to exercise each right
            result = consent_manager.exercise_data_right(right)
            assert result['status'] == 'submitted'
            assert 'request_id' in result
            assert 'expected_completion' in result
        
        # Should have audit trail for compliance
        audit_trail = consent_manager.get_consent_audit_trail()
        assert len(audit_trail) == len(gdpr_rights)  # One entry per right exercised
        
        # Should support data export (portability)
        export_data = consent_manager.export_consent_data()
        assert 'consent_data' in export_data
        assert 'format_version' in export_data
        
        # Should track consent versions for compliance
        status = consent_manager.get_consent_status()
        assert 'consent_version' in status
        assert 'last_updated' in status
    
    def test_consent_granularity(self, consent_manager):
        """Test granular consent controls"""
        # Should be able to give consent to some categories but not others
        mixed_consent = {
            'categories': {
                'failure_prediction': {'level': ConsentLevel.BASIC.value},
                'team_optimization': {'level': ConsentLevel.DENIED.value},
                'workflow_efficiency': {'level': ConsentLevel.ENHANCED.value},
                'ai_effectiveness': {'level': ConsentLevel.BASIC.value},
                'resource_optimization': {'level': ConsentLevel.DENIED.value},
                'market_trends': {'level': ConsentLevel.DENIED.value}
            }
        }
        
        consent_manager.update_consent(mixed_consent)
        
        # Check that consent is properly granular
        assert consent_manager.has_consent_for(InsightCategory.FAILURE_PREDICTION) is True
        assert consent_manager.has_consent_for(InsightCategory.TEAM_OPTIMIZATION) is False
        assert consent_manager.has_consent_for(InsightCategory.WORKFLOW_EFFICIENCY) is True
        assert consent_manager.has_consent_for(InsightCategory.AI_EFFECTIVENESS) is True
        assert consent_manager.has_consent_for(InsightCategory.RESOURCE_OPTIMIZATION) is False
        assert consent_manager.has_consent_for(InsightCategory.MARKET_TRENDS) is False
        
        # Status should reflect mixed consent
        status = consent_manager.get_consent_status()
        assert status['any_consent_given'] is True
        
        categories_status = status['categories']
        assert categories_status['failure_prediction']['has_consent'] is True
        assert categories_status['team_optimization']['has_consent'] is False
        assert categories_status['workflow_efficiency']['has_consent'] is True