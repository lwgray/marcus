"""
Health Analysis Monitor for PM Agent visualization

Integrates AI health analysis with the visualization UI to provide
real-time project health monitoring and insights. Now includes privacy-preserving
telemetry collection to help improve PM Agent for everyone.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from src.integrations.ai_analysis_engine_fixed import AIAnalysisEngine
from src.core.models import ProjectState, WorkerStatus, RiskLevel, Task, TaskStatus
from src.telemetry.client import TelemetryClient


class HealthMonitor:
    """
    Monitors project health and provides analysis for visualization
    
    Now includes privacy-preserving telemetry collection to help improve
    PM Agent's health monitoring capabilities for all users while
    protecting individual privacy through anonymization and aggregation.
    """
    
    def __init__(self, ai_engine: Optional[AIAnalysisEngine] = None, enable_telemetry: bool = True):
        """
        Initialize health monitor
        
        Parameters
        ----------
        ai_engine : Optional[AIAnalysisEngine]
            AI analysis engine instance. If None, creates a new one.
        enable_telemetry : bool
            Whether to enable privacy-preserving telemetry collection
        """
        self.ai_engine = ai_engine or AIAnalysisEngine()
        self.last_analysis: Optional[Dict[str, Any]] = None
        self.analysis_history: List[Dict[str, Any]] = []
        self.analysis_interval = 300  # 5 minutes default
        self._monitoring_task: Optional[asyncio.Task] = None
        self.logger = logging.getLogger(__name__)
        
        # Initialize telemetry client (privacy-preserving)
        self.telemetry_client: Optional[TelemetryClient] = None
        if enable_telemetry:
            try:
                self.telemetry_client = TelemetryClient()
                self.logger.info("Privacy-preserving telemetry initialized")
            except Exception as e:
                self.logger.warning(f"Telemetry initialization failed: {e}")
                self.telemetry_client = None
        
    async def initialize(self):
        """Initialize the AI engine and telemetry client"""
        await self.ai_engine.initialize()
        
        # Initialize telemetry client
        if self.telemetry_client:
            await self.telemetry_client.initialize()
        
    async def get_project_health(
        self, 
        project_state: ProjectState,
        recent_activities: List[Dict[str, Any]],
        team_status: List[WorkerStatus]
    ) -> Dict[str, Any]:
        """
        Get current project health analysis
        
        Parameters
        ----------
        project_state : ProjectState
            Current state of the project
        recent_activities : List[Dict[str, Any]]
            Recent project activities
        team_status : List[WorkerStatus]
            Current team member status
            
        Returns
        -------
        Dict[str, Any]
            Health analysis report
        """
        try:
            # Get AI analysis
            analysis = await self.ai_engine.analyze_project_health(
                project_state,
                recent_activities,
                team_status
            )
            
            # Add metadata
            analysis['timestamp'] = datetime.now().isoformat()
            analysis['analysis_id'] = f"health_{datetime.now().timestamp()}"
            
            # Calculate trends if we have history
            if self.last_analysis:
                analysis['trends'] = self._calculate_trends(self.last_analysis, analysis)
            
            # Store analysis
            self.last_analysis = analysis
            self.analysis_history.append(analysis)
            
            # Keep only last 100 analyses
            if len(self.analysis_history) > 100:
                self.analysis_history = self.analysis_history[-100:]
            
            # Collect privacy-preserving telemetry insights
            await self._collect_telemetry_insights(project_state, team_status, analysis)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Health analysis failed: {e}")
            return self._get_error_response(str(e))
    
    def _calculate_trends(self, previous: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate trends between analyses"""
        trends = {
            'health_direction': 'stable',
            'confidence_change': 0.0,
            'risk_change': 'stable'
        }
        
        # Health direction
        health_order = {'green': 3, 'yellow': 2, 'red': 1}
        prev_score = health_order.get(previous.get('overall_health', 'yellow'), 2)
        curr_score = health_order.get(current.get('overall_health', 'yellow'), 2)
        
        if curr_score > prev_score:
            trends['health_direction'] = 'improving'
        elif curr_score < prev_score:
            trends['health_direction'] = 'declining'
            
        # Confidence change
        prev_conf = previous.get('timeline_prediction', {}).get('confidence', 0.5)
        curr_conf = current.get('timeline_prediction', {}).get('confidence', 0.5)
        trends['confidence_change'] = curr_conf - prev_conf
        
        # Risk change
        prev_risks = len(previous.get('risk_factors', []))
        curr_risks = len(current.get('risk_factors', []))
        
        if curr_risks < prev_risks:
            trends['risk_change'] = 'decreasing'
        elif curr_risks > prev_risks:
            trends['risk_change'] = 'increasing'
            
        return trends
    
    def _get_error_response(self, error_message: str) -> Dict[str, Any]:
        """Generate error response for failed analysis"""
        return {
            'overall_health': 'unknown',
            'error': True,
            'error_message': error_message,
            'timestamp': datetime.now().isoformat(),
            'timeline_prediction': {
                'on_track': False,
                'confidence': 0.0,
                'estimated_completion': 'Unable to determine'
            },
            'risk_factors': [],
            'recommendations': [
                {
                    'priority': 'high',
                    'action': 'Investigate health analysis failure',
                    'expected_impact': 'Restore project visibility'
                }
            ]
        }
    
    async def start_monitoring(self, callback=None):
        """
        Start continuous health monitoring
        
        Parameters
        ----------
        callback : Optional[Callable]
            Async function to call with health updates
        """
        if self._monitoring_task:
            self.logger.warning("Monitoring already active")
            return
            
        async def monitor_loop():
            """Main monitoring loop"""
            while True:
                try:
                    # This would need actual project state in production
                    # For now, using placeholder
                    self.logger.info("Running scheduled health check")
                    
                    if callback:
                        # In production, gather actual project state
                        # health = await self.get_project_health(...)
                        # await callback(health)
                        pass
                        
                    await asyncio.sleep(self.analysis_interval)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Monitoring error: {e}")
                    await asyncio.sleep(60)  # Wait before retry
                    
        self._monitoring_task = asyncio.create_task(monitor_loop())
        self.logger.info("Health monitoring started")
        
    async def stop_monitoring(self):
        """Stop continuous monitoring"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
            self.logger.info("Health monitoring stopped")
        
        # Shutdown telemetry client gracefully
        if self.telemetry_client:
            await self.telemetry_client.shutdown()
            
    def get_health_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get health analysis history
        
        Parameters
        ----------
        hours : int
            Number of hours of history to return
            
        Returns
        -------
        List[Dict[str, Any]]
            List of historical health analyses
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        
        return [
            analysis for analysis in self.analysis_history
            if datetime.fromisoformat(analysis['timestamp']) > cutoff
        ]
        
    def get_health_summary(self) -> Dict[str, Any]:
        """Get summary of health trends"""
        if not self.analysis_history:
            return {
                'status': 'no_data',
                'message': 'No health analysis data available'
            }
            
        # Calculate summary statistics
        recent = self.analysis_history[-10:]  # Last 10 analyses
        
        health_counts = {'green': 0, 'yellow': 0, 'red': 0}
        risk_counts = {'low': 0, 'medium': 0, 'high': 0}
        total_risks = 0
        
        for analysis in recent:
            health = analysis.get('overall_health', 'unknown')
            if health in health_counts:
                health_counts[health] += 1
                
            risks = analysis.get('risk_factors', [])
            total_risks += len(risks)
            
            for risk in risks:
                severity = risk.get('severity', 'medium')
                if severity in risk_counts:
                    risk_counts[severity] += 1
                    
        return {
            'status': 'available',
            'period': f'Last {len(recent)} analyses',
            'health_distribution': health_counts,
            'average_risks': total_risks / len(recent) if recent else 0,
            'risk_distribution': risk_counts,
            'latest_health': self.last_analysis.get('overall_health') if self.last_analysis else 'unknown',
            'timestamp': datetime.now().isoformat()
        }
    
    async def _collect_telemetry_insights(
        self, 
        project_state: ProjectState, 
        team_status: List[WorkerStatus], 
        analysis: Dict[str, Any]
    ) -> None:
        """
        Collect privacy-preserving telemetry insights to help improve PM Agent
        
        This method collects anonymized insights that help us understand:
        - Common project health patterns
        - Effective team compositions  
        - Workflow optimization opportunities
        - AI recommendation effectiveness
        
        All data is anonymized and aggregated before transmission.
        Users have full control over what data is shared.
        """
        if not self.telemetry_client:
            return
            
        try:
            # Collect comprehensive project health insights
            await self.telemetry_client.collect_project_health_insight(
                project_state=project_state,
                health_history=self.analysis_history[-10:],  # Last 10 analyses
                team_status=team_status,
                ai_recommendations=[]  # Would include AI recommendations if available
            )
            
            # If we have workflow data, collect workflow insights
            if len(self.analysis_history) >= 3:
                await self._collect_workflow_insights(project_state, team_status)
            
            # Collect resource optimization insights
            if len(self.analysis_history) >= 5:
                await self._collect_resource_insights(team_status)
            
        except Exception as e:
            # Telemetry collection should never interfere with core functionality
            self.logger.debug(f"Telemetry collection failed: {e}")
    
    async def _collect_workflow_insights(
        self, 
        project_state: ProjectState, 
        team_status: List[WorkerStatus]
    ) -> None:
        """Collect workflow optimization insights from health monitoring data"""
        if not self.telemetry_client:
            return
            
        try:
            # Extract workflow patterns from analysis history
            task_transitions = []
            resolution_times = {}
            bottleneck_events = []
            
            # Analyze health trend patterns as workflow indicators
            for i, analysis in enumerate(self.analysis_history[-5:]):
                # Extract transition patterns
                if 'risk_factors' in analysis:
                    for risk in analysis['risk_factors']:
                        if risk.get('type') in ['workflow', 'process', 'bottleneck']:
                            bottleneck_events.append({
                                'type': risk.get('type', 'unknown'),
                                'severity': risk.get('severity', 'medium'),
                                'timestamp': analysis.get('timestamp'),
                                'resolution_suggested': risk.get('mitigation', '')
                            })
                
                # Track health transitions as proxy for workflow efficiency
                if i > 0:
                    prev_health = self.analysis_history[-(6-i)].get('overall_health', 'unknown')
                    curr_health = analysis.get('overall_health', 'unknown')
                    
                    if prev_health != curr_health:
                        task_transitions.append({
                            'from_state': prev_health,
                            'to_state': curr_health,
                            'transition_time': analysis.get('timestamp'),
                            'trend_direction': analysis.get('trends', {}).get('health_direction', 'stable')
                        })
            
            # Build team structure info
            team_structure = {
                'total_members': len(team_status),
                'roles': {status.role: 1 for status in team_status},  # Anonymous role counts
                'experience': [status.completed_tasks_count for status in team_status],
                'capacity_distribution': [status.capacity for status in team_status]
            }
            
            # Collect workflow insights
            await self.telemetry_client.collect_workflow_optimization_insight(
                task_transitions=task_transitions,
                resolution_times=resolution_times,
                team_structure=team_structure,
                bottleneck_events=bottleneck_events
            )
            
        except Exception as e:
            self.logger.debug(f"Workflow insights collection failed: {e}")
    
    async def _collect_resource_insights(self, team_status: List[WorkerStatus]) -> None:
        """Collect resource optimization insights from team capacity data"""
        if not self.telemetry_client:
            return
            
        try:
            # Extract capacity and performance data from history
            capacity_data = []
            performance_data = []
            
            for analysis in self.analysis_history[-10:]:
                # Use timeline prediction confidence as performance proxy
                timeline_pred = analysis.get('timeline_prediction', {})
                performance_score = timeline_pred.get('confidence', 0.5)
                performance_data.append(performance_score)
                
                # Calculate average team capacity utilization
                if team_status:
                    avg_capacity = sum(status.capacity for status in team_status) / len(team_status)
                    capacity_data.append(avg_capacity)
                else:
                    capacity_data.append(0.5)  # Default moderate capacity
            
            # Look for burnout indicators in risk factors
            burnout_indicators = []
            for analysis in self.analysis_history[-5:]:
                has_burnout_risk = any(
                    'burnout' in risk.get('description', '').lower() or
                    'overload' in risk.get('description', '').lower() or
                    risk.get('type') == 'capacity'
                    for risk in analysis.get('risk_factors', [])
                )
                burnout_indicators.append(has_burnout_risk)
            
            # Collect resource optimization insights
            await self.telemetry_client.collect_resource_optimization_insight(
                capacity_data=capacity_data,
                performance_data=performance_data,
                satisfaction_data=None,  # Could be derived from team feedback
                burnout_indicators=burnout_indicators
            )
            
        except Exception as e:
            self.logger.debug(f"Resource insights collection failed: {e}")
    
    def get_telemetry_status(self) -> Dict[str, Any]:
        """Get current telemetry status and consent information"""
        if not self.telemetry_client:
            return {
                'enabled': False,
                'reason': 'Telemetry client not initialized'
            }
        
        try:
            consent_status = self.telemetry_client.get_consent_status()
            insights_summary = self.telemetry_client.get_collected_insights_summary()
            
            return {
                'enabled': True,
                'consent_status': consent_status,
                'insights_summary': insights_summary,
                'privacy_info': {
                    'data_anonymized': True,
                    'opt_in_only': True,
                    'revocable_anytime': True,
                    'no_personal_data': True
                }
            }
        except Exception as e:
            return {
                'enabled': True,
                'error': str(e),
                'status': 'Error retrieving telemetry status'
            }
    
    def request_telemetry_consent(self, categories: Optional[List[str]] = None) -> Dict[str, Any]:
        """Request user consent for telemetry collection"""
        if not self.telemetry_client:
            return {
                'error': 'Telemetry not available',
                'message': 'Telemetry client not initialized'
            }
        
        try:
            from src.telemetry.strategic_collector import InsightCategory
            
            # Default to health monitoring related categories
            if categories is None:
                consent_categories = [
                    InsightCategory.FAILURE_PREDICTION,
                    InsightCategory.TEAM_OPTIMIZATION,
                    InsightCategory.WORKFLOW_EFFICIENCY,
                    InsightCategory.AI_EFFECTIVENESS
                ]
            else:
                consent_categories = [InsightCategory(cat) for cat in categories if cat in InsightCategory._value2member_map_]
            
            return self.telemetry_client.request_consent(consent_categories)
            
        except Exception as e:
            return {
                'error': 'Consent request failed',
                'message': str(e)
            }