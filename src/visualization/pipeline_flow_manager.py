"""
Pipeline Flow Manager

Manages pipeline flow data and events for visualization.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional


class PipelineFlowManager:
    """Manages pipeline flows and their events."""
    
    def __init__(self):
        self.flows = {}
        self.events = {}
        
    def create_flow(self, project_name: str, project_type: str, description: str = "") -> str:
        """Create a new pipeline flow."""
        flow_id = str(uuid.uuid4())
        
        flow = {
            'flow_id': flow_id,
            'project_name': project_name,
            'project_type': project_type,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'status': 'active',
            'current_stage': 'initialization',
            'progress_percentage': 0,
            'health_status': {
                'status': 'healthy',
                'message': 'Flow initialized'
            },
            'metrics': {
                'task_count': 0,
                'completed_count': 0,
                'duration_seconds': 0,
                'cost': 0.0,
                'quality_score': 1.0,
                'complexity': 1.0
            }
        }
        
        self.flows[flow_id] = flow
        self.events[flow_id] = []
        
        # Add initial event
        self.add_event(flow_id, {
            'type': 'flow_created',
            'timestamp': datetime.now().isoformat(),
            'data': {
                'project_name': project_name,
                'project_type': project_type
            }
        })
        
        return flow_id
    
    def add_event(self, flow_id: str, event: Dict[str, Any]):
        """Add an event to a flow."""
        if flow_id not in self.events:
            self.events[flow_id] = []
        
        # Ensure event has timestamp
        if 'timestamp' not in event:
            event['timestamp'] = datetime.now().isoformat()
        
        # Add sequential ID
        event['id'] = len(self.events[flow_id])
        
        self.events[flow_id].append(event)
        
        # Update flow based on event type
        if flow_id in self.flows:
            self._update_flow_from_event(flow_id, event)
    
    def _update_flow_from_event(self, flow_id: str, event: Dict[str, Any]):
        """Update flow state based on event."""
        flow = self.flows[flow_id]
        event_type = event.get('type')
        
        if event_type == 'workflow_started':
            flow['current_stage'] = 'workflow_active'
            flow['progress_percentage'] = 5
            
        elif event_type == 'task_assigned':
            flow['current_stage'] = 'tasks_in_progress'
            flow['metrics']['task_count'] += 1
            
        elif event_type == 'task_completed':
            flow['metrics']['completed_count'] += 1
            total = flow['metrics']['task_count']
            if total > 0:
                flow['progress_percentage'] = int((flow['metrics']['completed_count'] / total) * 100)
                
        elif event_type == 'workflow_metrics':
            metrics = event.get('metrics', {})
            flow['progress_percentage'] = metrics.get('progress_percent', flow['progress_percentage'])
            flow['metrics'].update({
                'task_count': metrics.get('total_tasks', flow['metrics']['task_count']),
                'completed_count': metrics.get('completed_tasks', flow['metrics']['completed_count'])
            })
            
        elif event_type == 'workflow_completed':
            flow['status'] = 'completed'
            flow['current_stage'] = 'completed'
            flow['progress_percentage'] = 100
            flow['health_status'] = {
                'status': 'healthy',
                'message': 'Workflow completed successfully'
            }
            
        elif event_type == 'error':
            flow['health_status'] = {
                'status': 'critical',
                'message': event.get('message', 'Error occurred')
            }
    
    def get_flow(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific flow."""
        return self.flows.get(flow_id)
    
    def get_active_flows(self) -> List[Dict[str, Any]]:
        """Get all active flows."""
        return [
            flow for flow in self.flows.values()
            if flow['status'] == 'active'
        ]
    
    def get_flow_events(self, flow_id: str) -> List[Dict[str, Any]]:
        """Get all events for a flow."""
        return self.events.get(flow_id, [])
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data for all flows."""
        active_flows = self.get_active_flows()
        
        # Calculate system metrics
        total_flows = len(active_flows)
        success_count = sum(1 for f in self.flows.values() if f['status'] == 'completed')
        total_count = len(self.flows)
        
        system_metrics = {
            'flows_per_hour': total_flows * 2,  # Mock metric
            'success_rate': int((success_count / total_count * 100) if total_count > 0 else 0),
            'avg_completion_time': 45.5,  # Mock metric in minutes
            'active_agents': 3  # Mock metric
        }
        
        return {
            'active_flows': active_flows,
            'system_metrics': system_metrics,
            'health_summary': {
                'healthy': sum(1 for f in active_flows if f['health_status']['status'] == 'healthy'),
                'warning': sum(1 for f in active_flows if f['health_status']['status'] == 'warning'),
                'critical': sum(1 for f in active_flows if f['health_status']['status'] == 'critical')
            },
            'alerts': []  # TODO: Implement alerts
        }