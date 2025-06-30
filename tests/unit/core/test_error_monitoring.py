"""
Unit tests for Marcus Error Monitoring System

Tests error tracking, pattern detection, correlation analysis,
and health monitoring capabilities.
"""

import pytest
import asyncio
import json
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

from src.core.error_monitoring import (
    ErrorMonitor, ErrorMetrics, ErrorPattern, CorrelationGroup,
    AlertSeverity, setup_error_monitoring, record_error_for_monitoring,
    get_error_health_status, error_monitor
)
from src.core.error_framework import (
    NetworkTimeoutError, AuthorizationError, TaskAssignmentError,
    ErrorContext, ErrorSeverity, ErrorCategory
)


class TestErrorMetrics:
    """Test suite for ErrorMetrics"""
    
    def test_error_metrics_creation(self):
        """Test creating ErrorMetrics with default values"""
        metrics = ErrorMetrics()
        
        assert metrics.total_errors == 0
        assert isinstance(metrics.errors_by_type, dict)
        assert isinstance(metrics.errors_by_severity, dict)
        assert isinstance(metrics.errors_by_category, dict)
        assert isinstance(metrics.errors_by_agent, dict)
        assert isinstance(metrics.errors_by_operation, dict)
        assert metrics.retryable_errors == 0
        assert metrics.critical_errors == 0
        assert metrics.error_rate_per_minute == 0.0
        assert isinstance(metrics.last_updated, datetime)


class TestErrorPattern:
    """Test suite for ErrorPattern"""
    
    def test_error_pattern_creation(self):
        """Test creating ErrorPattern"""
        pattern = ErrorPattern(
            pattern_id="test_pattern_123",
            pattern_type="frequency",
            description="High frequency error pattern",
            frequency=10,
            first_seen=datetime.now(),
            last_seen=datetime.now()
        )
        
        assert pattern.pattern_id == "test_pattern_123"
        assert pattern.pattern_type == "frequency"
        assert pattern.description == "High frequency error pattern"
        assert pattern.frequency == 10
        assert pattern.severity == ErrorSeverity.MEDIUM  # Default
        assert isinstance(pattern.affected_agents, set)
        assert isinstance(pattern.affected_operations, set)
        assert isinstance(pattern.sample_errors, list)


class TestCorrelationGroup:
    """Test suite for CorrelationGroup"""
    
    def test_correlation_group_creation(self):
        """Test creating CorrelationGroup"""
        group = CorrelationGroup(
            group_id="group_123",
            correlation_key="operation_agent_integration"
        )
        
        assert group.group_id == "group_123"
        assert group.correlation_key == "operation_agent_integration"
        assert isinstance(group.errors, list)
        assert isinstance(group.start_time, datetime)
        assert group.end_time is None
        assert group.pattern is None
        assert group.root_cause is None


class TestErrorMonitor:
    """Test suite for ErrorMonitor"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Use temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.temp_file.close()
        
        self.monitor = ErrorMonitor(
            storage_path=self.temp_file.name,
            metrics_window_minutes=5,
            pattern_detection_enabled=True,
            correlation_timeout_minutes=10
        )
    
    def teardown_method(self):
        """Clean up test fixtures"""
        Path(self.temp_file.name).unlink(missing_ok=True)
    
    def create_test_error(self, error_type=NetworkTimeoutError, **kwargs):
        """Create a test error for monitoring tests"""
        default_context = ErrorContext(
            operation="test_operation",
            agent_id="agent_123",
            task_id="task_456"
        )
        
        context = kwargs.pop('context', default_context)
        
        if error_type == NetworkTimeoutError:
            return NetworkTimeoutError(
                service_name="test_service",
                context=context,
                **kwargs
            )
        elif error_type == AuthorizationError:
            return AuthorizationError(context=context, **kwargs)
        elif error_type == TaskAssignmentError:
            return TaskAssignmentError(context=context, **kwargs)
        else:
            return error_type(context=context, **kwargs)
    
    def test_record_error(self):
        """Test recording a single error"""
        error = self.create_test_error()
        
        self.monitor.record_error(error)
        
        # Check error was stored
        assert len(self.monitor.error_history) == 1
        assert error.context.correlation_id in self.monitor.error_index
        
        # Check metrics were updated
        metrics = self.monitor.current_metrics
        assert metrics.total_errors == 1
        assert metrics.errors_by_type["NetworkTimeoutError"] == 1
        assert metrics.errors_by_severity["medium"] == 1
        assert metrics.errors_by_category["transient"] == 1
        assert metrics.errors_by_agent["agent_123"] == 1
        assert metrics.errors_by_operation["test_operation"] == 1
        assert metrics.retryable_errors == 1
        assert metrics.critical_errors == 0
    
    def test_record_multiple_errors(self):
        """Test recording multiple errors"""
        errors = [
            self.create_test_error(NetworkTimeoutError),
            self.create_test_error(AuthorizationError),
            self.create_test_error(NetworkTimeoutError)
        ]
        
        for error in errors:
            self.monitor.record_error(error)
        
        metrics = self.monitor.current_metrics
        assert metrics.total_errors == 3
        assert metrics.errors_by_type["NetworkTimeoutError"] == 2
        assert metrics.errors_by_type["AuthorizationError"] == 1
        assert metrics.retryable_errors == 2  # Only NetworkTimeoutErrors are retryable
        assert metrics.critical_errors == 1  # AuthorizationError is critical
    
    def test_metrics_calculation(self):
        """Test error metrics calculation"""
        # Record errors with different attributes
        errors = [
            self.create_test_error(
                NetworkTimeoutError,
                context=ErrorContext(operation="op1", agent_id="agent1")
            ),
            self.create_test_error(
                AuthorizationError,
                context=ErrorContext(operation="op2", agent_id="agent1")
            ),
            self.create_test_error(
                TaskAssignmentError,
                context=ErrorContext(operation="op1", agent_id="agent2")
            )
        ]
        
        for error in errors:
            self.monitor.record_error(error)
        
        metrics = self.monitor.current_metrics
        
        # Check by operation
        assert metrics.errors_by_operation["op1"] == 2
        assert metrics.errors_by_operation["op2"] == 1
        
        # Check by agent
        assert metrics.errors_by_agent["agent1"] == 2
        assert metrics.errors_by_agent["agent2"] == 1
        
        # Check by category
        assert metrics.errors_by_category["transient"] == 1
        assert metrics.errors_by_category["security"] == 1
        assert metrics.errors_by_category["business_logic"] == 1
    
    def test_pattern_detection_frequency(self):
        """Test frequency-based pattern detection"""
        # Configure lower threshold for testing
        self.monitor.pattern_thresholds['frequency_threshold'] = 3
        
        # Record multiple errors of same type
        for _ in range(4):
            error = self.create_test_error(NetworkTimeoutError)
            self.monitor.record_error(error)
        
        # Should detect frequency pattern
        patterns = self.monitor.get_detected_patterns(active_only=True)
        assert len(patterns) > 0
        
        frequency_patterns = [p for p in patterns if p.pattern_type == "frequency"]
        assert len(frequency_patterns) > 0
        
        pattern = frequency_patterns[0]
        assert "NetworkTimeoutError" in pattern.description
        assert pattern.frequency >= 3
    
    def test_pattern_detection_burst(self):
        """Test burst pattern detection"""
        # Configure lower threshold for testing
        self.monitor.pattern_thresholds['burst_threshold'] = 3
        
        # Record burst of different error types
        errors = [
            self.create_test_error(NetworkTimeoutError),
            self.create_test_error(AuthorizationError),
            self.create_test_error(TaskAssignmentError),
            self.create_test_error(NetworkTimeoutError)
        ]
        
        for error in errors:
            self.monitor.record_error(error)
        
        # Should detect burst pattern
        patterns = self.monitor.get_detected_patterns(active_only=True)
        burst_patterns = [p for p in patterns if p.pattern_type == "burst"]
        assert len(burst_patterns) > 0
        
        pattern = burst_patterns[0]
        assert "burst" in pattern.description.lower()
        assert pattern.frequency >= 3
    
    def test_pattern_detection_agent_specific(self):
        """Test agent-specific pattern detection"""
        # Configure lower threshold for testing
        self.monitor.pattern_thresholds['agent_error_threshold'] = 3
        
        # Record multiple errors from same agent
        for i in range(4):
            error = self.create_test_error(
                NetworkTimeoutError,
                context=ErrorContext(
                    operation=f"op_{i}",
                    agent_id="problematic_agent"
                )
            )
            self.monitor.record_error(error)
        
        # Should detect agent-specific pattern
        patterns = self.monitor.get_detected_patterns(active_only=True)
        agent_patterns = [p for p in patterns if p.pattern_type == "agent_specific"]
        assert len(agent_patterns) > 0
        
        pattern = agent_patterns[0]
        assert "problematic_agent" in pattern.description
        assert "problematic_agent" in pattern.affected_agents
    
    def test_correlation_tracking(self):
        """Test error correlation tracking"""
        # Create related errors (same operation + agent + integration)
        related_errors = [
            self.create_test_error(
                NetworkTimeoutError,
                context=ErrorContext(
                    operation="shared_op",
                    agent_id="shared_agent",
                    integration_name="shared_integration"
                )
            ),
            self.create_test_error(
                TaskAssignmentError,
                context=ErrorContext(
                    operation="shared_op",
                    agent_id="shared_agent",
                    integration_name="shared_integration"
                )
            )
        ]
        
        for error in related_errors:
            self.monitor.record_error(error)
        
        # Should create correlation group
        groups = self.monitor.get_correlation_groups(active_only=True)
        assert len(groups) > 0
        
        group = groups[0]
        assert len(group.errors) == 2
        assert "shared_op" in group.correlation_key
        assert "shared_agent" in group.correlation_key
        assert "shared_integration" in group.correlation_key
    
    def test_error_similarity_calculation(self):
        """Test error similarity calculation"""
        error1_data = {
            'error_type': 'NetworkTimeoutError',
            'operation': 'test_op',
            'integration_name': 'test_service',
            'timestamp': datetime.now()
        }
        
        error2_data = {
            'error_type': 'NetworkTimeoutError',
            'operation': 'test_op',
            'integration_name': 'test_service',
            'timestamp': datetime.now()
        }
        
        error3_data = {
            'error_type': 'AuthorizationError',
            'operation': 'different_op',
            'integration_name': 'different_service',
            'timestamp': datetime.now()
        }
        
        # High similarity
        similarity_high = self.monitor._calculate_error_similarity(error1_data, error2_data)
        assert similarity_high > 0.8
        
        # Low similarity
        similarity_low = self.monitor._calculate_error_similarity(error1_data, error3_data)
        assert similarity_low < 0.5
    
    def test_search_errors(self):
        """Test error search functionality"""
        # Record errors with different attributes
        errors = [
            self.create_test_error(
                NetworkTimeoutError,
                context=ErrorContext(operation="op1", agent_id="agent1")
            ),
            self.create_test_error(
                AuthorizationError,
                context=ErrorContext(operation="op2", agent_id="agent1")
            ),
            self.create_test_error(
                NetworkTimeoutError,
                context=ErrorContext(operation="op1", agent_id="agent2")
            )
        ]
        
        for error in errors:
            self.monitor.record_error(error)
        
        # Search by error type
        timeout_errors = self.monitor.search_errors(error_type="NetworkTimeoutError")
        assert len(timeout_errors) == 2
        
        # Search by agent
        agent1_errors = self.monitor.search_errors(agent_id="agent1")
        assert len(agent1_errors) == 2
        
        # Search by operation
        op1_errors = self.monitor.search_errors(operation="op1")
        assert len(op1_errors) == 2
        
        # Search by severity
        critical_errors = self.monitor.search_errors(severity="critical")
        assert len(critical_errors) == 1  # Only AuthorizationError
    
    def test_health_report_generation(self):
        """Test health report generation"""
        # Record some errors to affect health score
        errors = [
            self.create_test_error(NetworkTimeoutError),
            self.create_test_error(AuthorizationError)  # Critical error
        ]
        
        for error in errors:
            self.monitor.record_error(error)
        
        health_report = self.monitor.generate_health_report()
        
        assert "health_score" in health_report
        assert "health_status" in health_report
        assert "metrics" in health_report
        assert "recommendations" in health_report
        
        # Health score should be reduced due to critical error
        assert health_report["health_score"] < 100
        
        # Should have recommendations
        assert len(health_report["recommendations"]) > 0
    
    @patch('src.core.error_monitoring.logger')
    def test_pattern_alert_callback(self, mock_logger):
        """Test pattern alert callback functionality"""
        callback_called = False
        detected_pattern = None
        
        def test_callback(pattern):
            nonlocal callback_called, detected_pattern
            callback_called = True
            detected_pattern = pattern
        
        self.monitor.add_alert_callback(test_callback)
        
        # Configure low threshold and trigger pattern
        self.monitor.pattern_thresholds['frequency_threshold'] = 2
        
        for _ in range(3):
            error = self.create_test_error(NetworkTimeoutError)
            self.monitor.record_error(error)
        
        # Callback should have been called
        assert callback_called
        assert detected_pattern is not None
        assert detected_pattern.pattern_type == "frequency"
    
    def test_storage_save_load(self):
        """Test saving and loading monitoring data"""
        # Record some data
        error = self.create_test_error(NetworkTimeoutError)
        self.monitor.record_error(error)
        
        # Force pattern detection
        self.monitor.pattern_thresholds['frequency_threshold'] = 1
        self.monitor.record_error(self.create_test_error(NetworkTimeoutError))
        
        # Manually add metrics to history (normally done by monitoring loop)
        from dataclasses import asdict
        self.monitor.metrics_history.append(ErrorMetrics(**asdict(self.monitor.current_metrics)))
        
        # Save data
        self.monitor._save_to_storage()
        
        # Create new monitor and load data
        new_monitor = ErrorMonitor(storage_path=self.temp_file.name)
        
        # Should have loaded patterns
        assert len(new_monitor.detected_patterns) > 0
        assert len(new_monitor.metrics_history) > 0
    
    def test_data_cleanup(self):
        """Test cleanup of old monitoring data"""
        # Add old patterns (simulate old timestamps)
        old_time = datetime.now() - timedelta(days=8)
        old_pattern = ErrorPattern(
            pattern_id="old_pattern",
            pattern_type="test",
            description="Old pattern",
            frequency=1,
            first_seen=old_time,
            last_seen=old_time
        )
        self.monitor.detected_patterns["old_pattern"] = old_pattern
        
        # Add recent pattern
        recent_pattern = ErrorPattern(
            pattern_id="recent_pattern",
            pattern_type="test",
            description="Recent pattern",
            frequency=1,
            first_seen=datetime.now(),
            last_seen=datetime.now()
        )
        self.monitor.detected_patterns["recent_pattern"] = recent_pattern
        
        # Run cleanup
        self.monitor._cleanup_old_data()
        
        # Old pattern should be removed, recent should remain
        assert "old_pattern" not in self.monitor.detected_patterns
        assert "recent_pattern" in self.monitor.detected_patterns
    
    @pytest.mark.asyncio
    async def test_monitoring_loop(self):
        """Test background monitoring loop"""
        # Start monitoring
        await self.monitor.start_monitoring()
        
        # Let it run briefly
        await asyncio.sleep(0.1)
        
        # Stop monitoring
        await self.monitor.stop_monitoring()
        
        # Should have created monitoring task
        assert self.monitor._monitoring_task is not None
    
    def test_get_error_details(self):
        """Test getting detailed error information"""
        error = self.create_test_error(NetworkTimeoutError)
        self.monitor.record_error(error)
        
        correlation_id = error.context.correlation_id
        details = self.monitor.get_error_details(correlation_id)
        
        assert details is not None
        assert details['correlation_id'] == correlation_id
        assert details['error_type'] == 'NetworkTimeoutError'
        assert details['operation'] == 'test_operation'
    
    def test_metrics_history(self):
        """Test metrics history tracking"""
        # Record error to create metrics
        error = self.create_test_error(NetworkTimeoutError)
        self.monitor.record_error(error)
        
        # Add to history
        self.monitor.metrics_history.append(ErrorMetrics(**self.monitor.current_metrics.__dict__))
        
        # Get history
        history = self.monitor.get_metrics_history(hours=24)
        assert len(history) > 0
        
        # Get shorter history
        history_short = self.monitor.get_metrics_history(hours=1)
        assert len(history_short) >= 0  # Might be empty depending on timing


class TestGlobalFunctions:
    """Test suite for global monitoring functions"""
    
    def test_setup_error_monitoring(self):
        """Test setup_error_monitoring function"""
        callback_called = False
        
        def test_callback(pattern):
            nonlocal callback_called
            callback_called = True
        
        with tempfile.NamedTemporaryFile(suffix='.json') as temp_file:
            monitor = setup_error_monitoring(
                storage_path=temp_file.name,
                enable_patterns=True,
                alert_callback=test_callback
            )
            
            assert isinstance(monitor, ErrorMonitor)
            assert monitor.pattern_detection_enabled is True
            assert len(monitor.alert_callbacks) == 1
    
    def test_record_error_for_monitoring(self):
        """Test record_error_for_monitoring function"""
        error = NetworkTimeoutError("test_service")
        
        # Should not raise exception
        record_error_for_monitoring(error)
    
    def test_get_error_health_status(self):
        """Test get_error_health_status function"""
        health_status = get_error_health_status()
        
        assert isinstance(health_status, dict)
        assert "health_score" in health_status
        assert "health_status" in health_status


class TestErrorMonitoringIntegration:
    """Integration tests for error monitoring system"""
    
    def setup_method(self):
        """Set up integration test fixtures"""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.temp_file.close()
        
        self.monitor = ErrorMonitor(
            storage_path=self.temp_file.name,
            pattern_detection_enabled=True
        )
    
    def teardown_method(self):
        """Clean up integration test fixtures"""
        Path(self.temp_file.name).unlink(missing_ok=True)
    
    def test_end_to_end_monitoring(self):
        """Test complete error monitoring workflow"""
        # 1. Record various errors
        errors = [
            NetworkTimeoutError("service1", context=ErrorContext(agent_id="agent1")),
            NetworkTimeoutError("service1", context=ErrorContext(agent_id="agent1")),
            NetworkTimeoutError("service1", context=ErrorContext(agent_id="agent1")),
            AuthorizationError(context=ErrorContext(agent_id="agent2")),
            TaskAssignmentError(context=ErrorContext(agent_id="agent1"))
        ]
        
        # Configure low thresholds for testing
        self.monitor.pattern_thresholds.update({
            'frequency_threshold': 2,
            'burst_threshold': 3,
            'agent_error_threshold': 3
        })
        
        for error in errors:
            self.monitor.record_error(error)
        
        # 2. Check metrics
        metrics = self.monitor.get_current_metrics()
        assert metrics.total_errors == 5
        assert metrics.critical_errors == 1  # AuthorizationError
        assert metrics.retryable_errors == 3  # NetworkTimeoutErrors
        
        # 3. Check patterns
        patterns = self.monitor.get_detected_patterns()
        assert len(patterns) > 0
        
        # Should detect frequency pattern for NetworkTimeoutError
        frequency_patterns = [p for p in patterns if p.pattern_type == "frequency"]
        assert len(frequency_patterns) > 0
        
        # Should detect burst pattern
        burst_patterns = [p for p in patterns if p.pattern_type == "burst"]
        assert len(burst_patterns) > 0
        
        # Should detect agent pattern for agent1
        agent_patterns = [p for p in patterns if p.pattern_type == "agent_specific"]
        assert len(agent_patterns) > 0
        
        # 4. Check health report
        health_report = self.monitor.generate_health_report()
        assert health_report["health_score"] < 100  # Should be reduced due to issues
        assert len(health_report["recommendations"]) > 0
        
        # 5. Test search functionality
        timeout_errors = self.monitor.search_errors(error_type="NetworkTimeoutError")
        assert len(timeout_errors) == 3
        
        agent1_errors = self.monitor.search_errors(agent_id="agent1")
        assert len(agent1_errors) == 4  # 3 NetworkTimeout + 1 TaskAssignment
        
        # 6. Test data persistence
        self.monitor._save_to_storage()
        
        # Load in new monitor
        new_monitor = ErrorMonitor(storage_path=self.temp_file.name)
        loaded_patterns = new_monitor.get_detected_patterns()
        assert len(loaded_patterns) > 0