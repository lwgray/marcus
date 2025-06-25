"""
Health Analysis Monitor for PM Agent visualization

Integrates AI health analysis with the visualization UI to provide
real-time project health monitoring and insights.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from src.integrations.ai_analysis_engine_fixed import AIAnalysisEngine
from src.core.models import ProjectState, WorkerStatus, RiskLevel, Task, TaskStatus


class HealthMonitor:
    """
    Monitors project health and provides analysis for visualization
    """
    
    def __init__(self, ai_engine: Optional[AIAnalysisEngine] = None):
        """
        Initialize health monitor
        
        Parameters
        ----------
        ai_engine : Optional[AIAnalysisEngine]
            AI analysis engine instance. If None, creates a new one.
        """
        self.ai_engine = ai_engine or AIAnalysisEngine()
        self.last_analysis: Optional[Dict[str, Any]] = None
        self.analysis_history: List[Dict[str, Any]] = []
        self.analysis_interval = 300  # 5 minutes default
        self._monitoring_task: Optional[asyncio.Task] = None
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """Initialize the AI engine"""
        await self.ai_engine.initialize()
        
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