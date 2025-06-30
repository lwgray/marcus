"""
Marcus Error Monitoring and Correlation System

Provides comprehensive error tracking, pattern analysis, and correlation
capabilities for autonomous agent environments.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Set, Union
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from enum import Enum
import threading
import logging
from pathlib import Path

from .error_framework import MarcusBaseError, ErrorSeverity, ErrorCategory
from .error_responses import ErrorResponseFormatter, ResponseFormat

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ErrorMetrics:
    """Error metrics for monitoring."""
    total_errors: int = 0
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    errors_by_severity: Dict[str, int] = field(default_factory=dict)
    errors_by_category: Dict[str, int] = field(default_factory=dict)
    errors_by_agent: Dict[str, int] = field(default_factory=dict)
    errors_by_operation: Dict[str, int] = field(default_factory=dict)
    retryable_errors: int = 0
    critical_errors: int = 0
    error_rate_per_minute: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class ErrorPattern:
    """Detected error pattern."""
    pattern_id: str
    pattern_type: str
    description: str
    frequency: int
    first_seen: datetime
    last_seen: datetime
    affected_agents: Set[str] = field(default_factory=set)
    affected_operations: Set[str] = field(default_factory=set)
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    sample_errors: List[str] = field(default_factory=list)


@dataclass
class CorrelationGroup:
    """Group of correlated errors."""
    group_id: str
    correlation_key: str
    errors: List[str] = field(default_factory=list)  # Error correlation IDs
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    pattern: Optional[str] = None
    root_cause: Optional[str] = None


class ErrorMonitor:
    """
    Comprehensive error monitoring system.
    
    Tracks error patterns, provides real-time metrics, and enables
    proactive issue detection for autonomous agents.
    """
    
    def __init__(
        self,
        storage_path: str = "logs/error_monitoring.json",
        metrics_window_minutes: int = 60,
        pattern_detection_enabled: bool = True,
        correlation_timeout_minutes: int = 30
    ):
        self.storage_path = Path(storage_path)
        self.metrics_window_minutes = metrics_window_minutes
        self.pattern_detection_enabled = pattern_detection_enabled
        self.correlation_timeout_minutes = correlation_timeout_minutes
        
        # Error storage
        self.error_history: deque = deque(maxlen=10000)  # Keep last 10k errors
        self.error_index: Dict[str, Dict[str, Any]] = {}  # correlation_id -> error data
        
        # Metrics
        self.current_metrics = ErrorMetrics()
        self.metrics_history: List[ErrorMetrics] = []
        
        # Pattern detection
        self.detected_patterns: Dict[str, ErrorPattern] = {}
        self.pattern_thresholds = {
            'frequency_threshold': 5,      # Same error 5+ times
            'burst_threshold': 10,         # 10+ errors in short time
            'agent_error_threshold': 20,   # 20+ errors from same agent
            'cascade_threshold': 3         # 3+ related errors in sequence
        }
        
        # Correlation tracking
        self.correlation_groups: Dict[str, CorrelationGroup] = {}
        self.active_correlations: Dict[str, str] = {}  # correlation_id -> group_id
        
        # Alert callbacks
        self.alert_callbacks: List[Callable[[ErrorPattern], None]] = []
        
        # Background task management
        self._monitoring_task: Optional[asyncio.Task] = None
        self._lock = threading.Lock()
        
        # Initialize storage
        self._initialize_storage()
    
    def _initialize_storage(self):
        """Initialize error monitoring storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing data if available
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    self._load_from_storage(data)
            except Exception as e:
                logger.warning(f"Failed to load error monitoring data: {e}")
    
    def _load_from_storage(self, data: Dict[str, Any]):
        """Load monitoring data from storage."""
        # Load metrics history
        if 'metrics_history' in data:
            for metrics_data in data['metrics_history'][-100:]:  # Keep last 100
                # Convert ISO string to datetime if needed
                if 'last_updated' in metrics_data and isinstance(metrics_data['last_updated'], str):
                    metrics_data['last_updated'] = datetime.fromisoformat(metrics_data['last_updated'])
                metrics = ErrorMetrics(**metrics_data)
                self.metrics_history.append(metrics)
        
        # Load detected patterns
        if 'patterns' in data:
            for pattern_data in data['patterns'].values():
                # Convert ISO strings to datetime objects
                if 'first_seen' in pattern_data and isinstance(pattern_data['first_seen'], str):
                    pattern_data['first_seen'] = datetime.fromisoformat(pattern_data['first_seen'])
                if 'last_seen' in pattern_data and isinstance(pattern_data['last_seen'], str):
                    pattern_data['last_seen'] = datetime.fromisoformat(pattern_data['last_seen'])
                if 'severity' in pattern_data and isinstance(pattern_data['severity'], str):
                    pattern_data['severity'] = ErrorSeverity(pattern_data['severity'])
                    
                pattern = ErrorPattern(**pattern_data)
                pattern.affected_agents = set(pattern.affected_agents)
                pattern.affected_operations = set(pattern.affected_operations)
                self.detected_patterns[pattern.pattern_id] = pattern
    
    def _save_to_storage(self):
        """Save monitoring data to storage."""
        try:
            # Convert patterns for JSON serialization
            patterns_data = {}
            for pattern_id, pattern in self.detected_patterns.items():
                pattern_dict = asdict(pattern)
                pattern_dict['affected_agents'] = list(pattern.affected_agents)
                pattern_dict['affected_operations'] = list(pattern.affected_operations)
                pattern_dict['first_seen'] = pattern.first_seen.isoformat()
                pattern_dict['last_seen'] = pattern.last_seen.isoformat()
                pattern_dict['severity'] = pattern.severity.value
                patterns_data[pattern_id] = pattern_dict
            
            # Convert metrics for JSON serialization
            metrics_data = []
            for metrics in self.metrics_history[-100:]:  # Keep last 100
                metrics_dict = asdict(metrics)
                metrics_dict['last_updated'] = metrics.last_updated.isoformat()
                metrics_data.append(metrics_dict)
            
            data = {
                'patterns': patterns_data,
                'metrics_history': metrics_data,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save error monitoring data: {e}")
    
    def record_error(self, error: MarcusBaseError):
        """Record an error for monitoring and analysis."""
        with self._lock:
            # Create error record
            error_record = {
                'correlation_id': error.context.correlation_id,
                'error_code': error.error_code,
                'error_type': error.__class__.__name__,
                'message': error.message,
                'severity': error.severity.value,
                'category': error.category.value,
                'retryable': error.retryable,
                'timestamp': error.context.timestamp,
                'operation': error.context.operation,
                'agent_id': error.context.agent_id,
                'task_id': error.context.task_id,
                'integration_name': error.context.integration_name,
                'custom_context': error.context.custom_context or {}
            }
            
            # Store error
            self.error_history.append(error_record)
            self.error_index[error.context.correlation_id] = error_record
            
            # Update metrics
            self._update_metrics(error_record)
            
            # Pattern detection
            if self.pattern_detection_enabled:
                self._detect_patterns(error_record)
            
            # Correlation tracking
            self._track_correlations(error_record)
            
            # Log for debugging
            logger.debug(f"Recorded error: {error.error_code} ({error.context.correlation_id})")
    
    def _update_metrics(self, error_record: Dict[str, Any]):
        """Update error metrics."""
        metrics = self.current_metrics
        
        # Update counters
        metrics.total_errors += 1
        
        # By type
        error_type = error_record['error_type']
        metrics.errors_by_type[error_type] = metrics.errors_by_type.get(error_type, 0) + 1
        
        # By severity
        severity = error_record['severity']
        metrics.errors_by_severity[severity] = metrics.errors_by_severity.get(severity, 0) + 1
        
        # By category
        category = error_record['category']
        metrics.errors_by_category[category] = metrics.errors_by_category.get(category, 0) + 1
        
        # By agent
        if error_record['agent_id']:
            agent_id = error_record['agent_id']
            metrics.errors_by_agent[agent_id] = metrics.errors_by_agent.get(agent_id, 0) + 1
        
        # By operation
        if error_record['operation']:
            operation = error_record['operation']
            metrics.errors_by_operation[operation] = metrics.errors_by_operation.get(operation, 0) + 1
        
        # Special counters
        if error_record['retryable']:
            metrics.retryable_errors += 1
        
        if error_record['severity'] == 'critical':
            metrics.critical_errors += 1
        
        # Update timestamp
        metrics.last_updated = datetime.now()
        
        # Calculate error rate
        self._calculate_error_rate()
    
    def _calculate_error_rate(self):
        """Calculate current error rate per minute."""
        now = datetime.now()
        cutoff_time = now - timedelta(minutes=self.metrics_window_minutes)
        
        # Count errors in time window
        recent_errors = sum(
            1 for error in self.error_history
            if error['timestamp'] > cutoff_time
        )
        
        self.current_metrics.error_rate_per_minute = recent_errors / self.metrics_window_minutes
    
    def _detect_patterns(self, error_record: Dict[str, Any]):
        """Detect error patterns for proactive alerting."""
        now = datetime.now()
        
        # Pattern 1: Frequency-based (same error type recurring)
        self._detect_frequency_pattern(error_record, now)
        
        # Pattern 2: Burst pattern (many errors in short time)
        self._detect_burst_pattern(error_record, now)
        
        # Pattern 3: Agent-specific error pattern
        self._detect_agent_pattern(error_record, now)
        
        # Pattern 4: Cascade pattern (related errors in sequence)
        self._detect_cascade_pattern(error_record, now)
    
    def _detect_frequency_pattern(self, error_record: Dict[str, Any], now: datetime):
        """Detect frequency-based error patterns."""
        error_type = error_record['error_type']
        
        # Count recent occurrences of this error type
        recent_count = sum(
            1 for error in self.error_history
            if (error['error_type'] == error_type and
                now - error['timestamp'] < timedelta(minutes=10))
        )
        
        if recent_count >= self.pattern_thresholds['frequency_threshold']:
            pattern_id = f"frequency_{error_type}_{now.strftime('%Y%m%d_%H%M')}"
            
            if pattern_id not in self.detected_patterns:
                pattern = ErrorPattern(
                    pattern_id=pattern_id,
                    pattern_type="frequency",
                    description=f"High frequency of {error_type} errors ({recent_count} in 10 minutes)",
                    frequency=recent_count,
                    first_seen=now,
                    last_seen=now,
                    severity=ErrorSeverity.MEDIUM if recent_count < 10 else ErrorSeverity.HIGH
                )
                
                self.detected_patterns[pattern_id] = pattern
                self._notify_pattern_detected(pattern)
            else:
                # Update existing pattern
                pattern = self.detected_patterns[pattern_id]
                pattern.frequency = recent_count
                pattern.last_seen = now
    
    def _detect_burst_pattern(self, error_record: Dict[str, Any], now: datetime):
        """Detect burst error patterns."""
        # Count all errors in last 5 minutes
        burst_count = sum(
            1 for error in self.error_history
            if now - error['timestamp'] < timedelta(minutes=5)
        )
        
        if burst_count >= self.pattern_thresholds['burst_threshold']:
            pattern_id = f"burst_{now.strftime('%Y%m%d_%H%M')}"
            
            if pattern_id not in self.detected_patterns:
                pattern = ErrorPattern(
                    pattern_id=pattern_id,
                    pattern_type="burst",
                    description=f"Error burst detected ({burst_count} errors in 5 minutes)",
                    frequency=burst_count,
                    first_seen=now,
                    last_seen=now,
                    severity=ErrorSeverity.HIGH if burst_count < 20 else ErrorSeverity.CRITICAL
                )
                
                self.detected_patterns[pattern_id] = pattern
                self._notify_pattern_detected(pattern)
    
    def _detect_agent_pattern(self, error_record: Dict[str, Any], now: datetime):
        """Detect agent-specific error patterns."""
        agent_id = error_record.get('agent_id')
        if not agent_id:
            return
        
        # Count errors from this agent in last 30 minutes
        agent_errors = sum(
            1 for error in self.error_history
            if (error.get('agent_id') == agent_id and
                now - error['timestamp'] < timedelta(minutes=30))
        )
        
        if agent_errors >= self.pattern_thresholds['agent_error_threshold']:
            pattern_id = f"agent_{agent_id}_{now.strftime('%Y%m%d_%H%M')}"
            
            if pattern_id not in self.detected_patterns:
                pattern = ErrorPattern(
                    pattern_id=pattern_id,
                    pattern_type="agent_specific",
                    description=f"High error rate from agent {agent_id} ({agent_errors} errors in 30 minutes)",
                    frequency=agent_errors,
                    first_seen=now,
                    last_seen=now,
                    severity=ErrorSeverity.MEDIUM,
                    affected_agents={agent_id}
                )
                
                self.detected_patterns[pattern_id] = pattern
                self._notify_pattern_detected(pattern)
    
    def _detect_cascade_pattern(self, error_record: Dict[str, Any], now: datetime):
        """Detect cascade error patterns (related errors in sequence)."""
        # Look for errors with similar context that occurred recently
        similar_errors = []
        for error in list(self.error_history)[-50:]:  # Check last 50 errors
            if (now - error['timestamp'] < timedelta(minutes=5) and
                error['correlation_id'] != error_record['correlation_id']):
                
                # Check for similarity
                similarity_score = self._calculate_error_similarity(error, error_record)
                if similarity_score > 0.7:  # 70% similarity threshold
                    similar_errors.append(error)
        
        if len(similar_errors) >= self.pattern_thresholds['cascade_threshold']:
            pattern_id = f"cascade_{now.strftime('%Y%m%d_%H%M%S')}"
            
            pattern = ErrorPattern(
                pattern_id=pattern_id,
                pattern_type="cascade",
                description=f"Cascade pattern detected ({len(similar_errors)} related errors)",
                frequency=len(similar_errors),
                first_seen=now,
                last_seen=now,
                severity=ErrorSeverity.MEDIUM
            )
            
            self.detected_patterns[pattern_id] = pattern
            self._notify_pattern_detected(pattern)
    
    def _calculate_error_similarity(self, error1: Dict[str, Any], error2: Dict[str, Any]) -> float:
        """Calculate similarity between two errors (0.0 to 1.0)."""
        similarity_factors = []
        
        # Same error type
        if error1['error_type'] == error2['error_type']:
            similarity_factors.append(0.4)
        
        # Same operation
        if error1.get('operation') == error2.get('operation'):
            similarity_factors.append(0.3)
        
        # Same integration
        if error1.get('integration_name') == error2.get('integration_name'):
            similarity_factors.append(0.2)
        
        # Similar timestamp (within 1 minute)
        time_diff = abs((error1['timestamp'] - error2['timestamp']).total_seconds())
        if time_diff < 60:
            similarity_factors.append(0.1)
        
        return sum(similarity_factors)
    
    def _track_correlations(self, error_record: Dict[str, Any]):
        """Track error correlations for root cause analysis."""
        correlation_id = error_record['correlation_id']
        
        # Find correlation key (operation + agent + integration)
        correlation_key = f"{error_record.get('operation', 'unknown')}_{error_record.get('agent_id', 'unknown')}_{error_record.get('integration_name', 'unknown')}"
        
        # Find or create correlation group
        group_id = None
        for gid, group in self.correlation_groups.items():
            if (group.correlation_key == correlation_key and 
                datetime.now() - group.start_time < timedelta(minutes=self.correlation_timeout_minutes)):
                group_id = gid
                break
        
        if not group_id:
            group_id = f"corr_{int(time.time())}_{correlation_key[:20]}"
            self.correlation_groups[group_id] = CorrelationGroup(
                group_id=group_id,
                correlation_key=correlation_key
            )
        
        # Add error to group
        group = self.correlation_groups[group_id]
        group.errors.append(correlation_id)
        group.end_time = datetime.now()
        
        self.active_correlations[correlation_id] = group_id
    
    def _notify_pattern_detected(self, pattern: ErrorPattern):
        """Notify about detected error pattern."""
        logger.warning(f"Error pattern detected: {pattern.description}")
        
        # Call registered callbacks
        for callback in self.alert_callbacks:
            try:
                callback(pattern)
            except Exception as e:
                logger.error(f"Error in pattern alert callback: {e}")
    
    def add_alert_callback(self, callback: Callable[[ErrorPattern], None]):
        """Add callback for pattern alerts."""
        self.alert_callbacks.append(callback)
    
    def get_current_metrics(self) -> ErrorMetrics:
        """Get current error metrics."""
        return self.current_metrics
    
    def get_metrics_history(self, hours: int = 24) -> List[ErrorMetrics]:
        """Get metrics history for specified hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            metrics for metrics in self.metrics_history
            if metrics.last_updated > cutoff_time
        ]
    
    def get_detected_patterns(self, active_only: bool = True) -> List[ErrorPattern]:
        """Get detected error patterns."""
        if not active_only:
            return list(self.detected_patterns.values())
        
        # Return only patterns from last 24 hours
        cutoff_time = datetime.now() - timedelta(hours=24)
        return [
            pattern for pattern in self.detected_patterns.values()
            if pattern.last_seen > cutoff_time
        ]
    
    def get_correlation_groups(self, active_only: bool = True) -> List[CorrelationGroup]:
        """Get error correlation groups."""
        if not active_only:
            return list(self.correlation_groups.values())
        
        # Return only active correlations
        cutoff_time = datetime.now() - timedelta(minutes=self.correlation_timeout_minutes)
        return [
            group for group in self.correlation_groups.values()
            if group.end_time and group.end_time > cutoff_time
        ]
    
    def get_error_details(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific error."""
        return self.error_index.get(correlation_id)
    
    def search_errors(
        self,
        error_type: str = None,
        agent_id: str = None,
        operation: str = None,
        severity: str = None,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Search errors with specified criteria."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        results = []
        for error in self.error_history:
            if error['timestamp'] < cutoff_time:
                continue
            
            # Apply filters
            if error_type and error['error_type'] != error_type:
                continue
            if agent_id and error.get('agent_id') != agent_id:
                continue
            if operation and error.get('operation') != operation:
                continue
            if severity and error['severity'] != severity:
                continue
            
            results.append(error)
        
        return results
    
    def generate_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report."""
        current_metrics = self.get_current_metrics()
        active_patterns = self.get_detected_patterns(active_only=True)
        active_correlations = self.get_correlation_groups(active_only=True)
        
        # Health score calculation (0-100)
        health_score = 100
        if current_metrics.error_rate_per_minute > 10:
            health_score -= 30
        elif current_metrics.error_rate_per_minute > 5:
            health_score -= 15
        elif current_metrics.error_rate_per_minute > 2:
            health_score -= 5
        
        if current_metrics.critical_errors > 0:
            health_score -= 25
        
        if len(active_patterns) > 0:
            health_score -= len(active_patterns) * 10
        
        health_score = max(0, health_score)
        
        # Determine health status
        if health_score >= 90:
            health_status = "excellent"
        elif health_score >= 75:
            health_status = "good"
        elif health_score >= 50:
            health_status = "fair"
        elif health_score >= 25:
            health_status = "poor"
        else:
            health_status = "critical"
        
        return {
            "health_score": health_score,
            "health_status": health_status,
            "timestamp": datetime.now().isoformat(),
            "metrics": asdict(current_metrics),
            "active_patterns": len(active_patterns),
            "active_correlations": len(active_correlations),
            "top_error_types": dict(
                sorted(current_metrics.errors_by_type.items(), 
                      key=lambda x: x[1], reverse=True)[:5]
            ),
            "recommendations": self._generate_recommendations(current_metrics, active_patterns)
        }
    
    def _generate_recommendations(
        self, 
        metrics: ErrorMetrics, 
        patterns: List[ErrorPattern]
    ) -> List[str]:
        """Generate health recommendations."""
        recommendations = []
        
        if metrics.error_rate_per_minute > 5:
            recommendations.append("High error rate detected - investigate recent changes")
        
        if metrics.critical_errors > 0:
            recommendations.append("Critical errors present - immediate attention required")
        
        if len(patterns) > 3:
            recommendations.append("Multiple error patterns detected - system instability likely")
        
        # Agent-specific recommendations
        top_error_agents = sorted(
            metrics.errors_by_agent.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:3]
        
        for agent_id, error_count in top_error_agents:
            if error_count > 10:
                recommendations.append(f"Agent {agent_id} has high error count ({error_count}) - review agent configuration")
        
        # Integration-specific recommendations
        integration_errors = defaultdict(int)
        # Get last 1000 errors from deque
        recent_errors = list(self.error_history)[-1000:] if len(self.error_history) > 1000 else list(self.error_history)
        for error in recent_errors:
            if error.get('integration_name'):
                integration_errors[error['integration_name']] += 1
        
        for integration, count in integration_errors.items():
            if count > 20:
                recommendations.append(f"Integration {integration} has high error count - check service health")
        
        if not recommendations:
            recommendations.append("System health is good - continue monitoring")
        
        return recommendations
    
    async def start_monitoring(self):
        """Start background monitoring tasks."""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Error monitoring started")
    
    async def stop_monitoring(self):
        """Stop background monitoring tasks."""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            logger.info("Error monitoring stopped")
    
    async def _monitoring_loop(self):
        """Background monitoring loop."""
        while True:
            try:
                # Save metrics snapshot
                self.metrics_history.append(ErrorMetrics(**asdict(self.current_metrics)))
                
                # Cleanup old data
                self._cleanup_old_data()
                
                # Save to storage
                self._save_to_storage()
                
                # Sleep for next iteration
                await asyncio.sleep(300)  # 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    def _cleanup_old_data(self):
        """Clean up old monitoring data."""
        now = datetime.now()
        
        # Clean old patterns (older than 7 days)
        cutoff_time = now - timedelta(days=7)
        old_patterns = [
            pattern_id for pattern_id, pattern in self.detected_patterns.items()
            if pattern.last_seen < cutoff_time
        ]
        for pattern_id in old_patterns:
            del self.detected_patterns[pattern_id]
        
        # Clean old correlation groups (older than 24 hours)
        cutoff_time = now - timedelta(hours=24)
        old_groups = [
            group_id for group_id, group in self.correlation_groups.items()
            if group.end_time and group.end_time < cutoff_time
        ]
        for group_id in old_groups:
            del self.correlation_groups[group_id]
        
        # Keep only last 1000 metrics
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]


# =============================================================================
# GLOBAL MONITOR INSTANCE
# =============================================================================

# Global error monitor instance
error_monitor = ErrorMonitor()


# =============================================================================
# INTEGRATION HELPERS
# =============================================================================

def setup_error_monitoring(
    storage_path: str = "logs/error_monitoring.json",
    enable_patterns: bool = True,
    alert_callback: Callable[[ErrorPattern], None] = None
) -> ErrorMonitor:
    """Set up global error monitoring."""
    global error_monitor
    
    error_monitor = ErrorMonitor(
        storage_path=storage_path,
        pattern_detection_enabled=enable_patterns
    )
    
    if alert_callback:
        error_monitor.add_alert_callback(alert_callback)
    
    return error_monitor


def record_error_for_monitoring(error: MarcusBaseError):
    """Convenience function to record error in global monitor."""
    error_monitor.record_error(error)


def get_error_health_status() -> Dict[str, Any]:
    """Get current error health status."""
    return error_monitor.generate_health_report()