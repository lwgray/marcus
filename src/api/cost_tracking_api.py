"""
Cost Tracking API endpoints for token-based project costs
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from typing import Dict, Any

from src.cost_tracking.token_tracker import token_tracker
from src.cost_tracking.ai_usage_middleware import ai_usage_middleware

cost_tracking_bp = Blueprint('cost_tracking', __name__)


@cost_tracking_bp.route('/api/costs/project/<project_id>', methods=['GET'])
def get_project_costs(project_id: str):
    """
    Get real-time cost information for a project.
    
    Returns:
        - Total tokens used
        - Total cost so far
        - Current burn rate (tokens/hour)
        - Projected total cost
        - Cost per hour at current rate
    """
    try:
        stats = token_tracker.get_project_stats(project_id)
        
        # Add historical chart data
        history = list(token_tracker.token_history.get(project_id, []))
        
        # Group by time buckets for charting
        time_buckets = []
        if history:
            # Create 10-minute buckets for the last 2 hours
            now = datetime.now()
            for i in range(12):  # 12 buckets of 10 minutes = 2 hours
                bucket_start = now - timedelta(minutes=(i+1)*10)
                bucket_end = now - timedelta(minutes=i*10)
                
                bucket_tokens = sum(
                    event['tokens'] 
                    for event in history 
                    if bucket_start <= event['timestamp'] < bucket_end
                )
                bucket_cost = sum(
                    event['cost'] 
                    for event in history 
                    if bucket_start <= event['timestamp'] < bucket_end
                )
                
                time_buckets.append({
                    'timestamp': bucket_end.isoformat(),
                    'tokens': bucket_tokens,
                    'cost': round(bucket_cost, 4)
                })
        
        time_buckets.reverse()  # Oldest to newest
        
        return jsonify({
            'success': True,
            'project_id': project_id,
            'stats': stats,
            'history': time_buckets,
            'comparison': {
                'naive_estimate': _get_naive_estimate(project_id),
                'actual_cost': stats['total_cost'],
                'variance': _calculate_variance(project_id, stats['total_cost'])
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@cost_tracking_bp.route('/api/costs/summary', methods=['GET'])
def get_cost_summary():
    """Get cost summary for all projects."""
    try:
        summary = token_tracker.get_all_projects_summary()
        
        # Add comparison with naive estimates
        for project_id, stats in summary['projects'].items():
            naive = _get_naive_estimate(project_id)
            stats['naive_estimate'] = naive
            stats['cost_accuracy'] = _calculate_variance(project_id, stats['total_cost'])
        
        return jsonify({
            'success': True,
            'summary': summary,
            'insights': _generate_cost_insights(summary)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@cost_tracking_bp.route('/api/costs/set-context', methods=['POST'])
def set_cost_context():
    """Set project context for token tracking."""
    try:
        data = request.json
        agent_id = data.get('agent_id')
        project_id = data.get('project_id')
        task_id = data.get('task_id')
        
        if not agent_id or not project_id:
            return jsonify({
                'success': False, 
                'error': 'agent_id and project_id required'
            }), 400
        
        ai_usage_middleware.set_project_context(agent_id, project_id, task_id)
        
        return jsonify({
            'success': True,
            'message': f'Context set for {agent_id} on project {project_id}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@cost_tracking_bp.route('/api/costs/live-feed', methods=['GET'])
def get_live_cost_feed():
    """
    Get live feed of token usage across all projects.
    
    Returns most recent token usage events for real-time monitoring.
    """
    try:
        # Get last 50 events across all projects
        all_events = []
        
        for project_id, history in token_tracker.token_history.items():
            for event in list(history)[-10:]:  # Last 10 per project
                all_events.append({
                    'project_id': project_id,
                    'timestamp': event['timestamp'].isoformat(),
                    'tokens': event['tokens'],
                    'cost': event['cost'],
                    'metadata': event.get('metadata', {})
                })
        
        # Sort by timestamp
        all_events.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'success': True,
            'events': all_events[:50],  # Most recent 50
            'active_projects': len([
                p for p, s in token_tracker.get_all_projects_summary()['projects'].items()
                if s['current_spend_rate'] > 0
            ])
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def _get_naive_estimate(project_id: str) -> float:
    """Get the naive hourly estimate for comparison."""
    # This would integrate with your project management to get estimated hours
    # For now, return a placeholder
    # In reality, this would query the project's estimated_hours from the database
    
    # Placeholder: assume 40 hours at $150/hour
    return 40 * 150


def _calculate_variance(project_id: str, actual_cost: float) -> Dict[str, Any]:
    """Calculate variance between naive estimate and actual cost."""
    naive = _get_naive_estimate(project_id)
    
    if naive == 0:
        return {
            'percentage': 0,
            'direction': 'accurate',
            'amount': 0
        }
    
    variance_pct = ((actual_cost - naive) / naive) * 100
    
    return {
        'percentage': abs(round(variance_pct, 1)),
        'direction': 'over' if variance_pct > 0 else 'under',
        'amount': round(abs(actual_cost - naive), 2)
    }


def _generate_cost_insights(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Generate insights from cost data."""
    insights = {
        'most_expensive_project': None,
        'highest_burn_rate': None,
        'total_vs_naive_variance': 0,
        'recommendations': []
    }
    
    if not summary['projects']:
        return insights
    
    # Find most expensive project
    projects_by_cost = sorted(
        summary['projects'].items(),
        key=lambda x: x[1]['total_cost'],
        reverse=True
    )
    
    if projects_by_cost:
        insights['most_expensive_project'] = {
            'id': projects_by_cost[0][0],
            'cost': projects_by_cost[0][1]['total_cost']
        }
    
    # Find highest burn rate
    projects_by_rate = sorted(
        summary['projects'].items(),
        key=lambda x: x[1]['current_spend_rate'],
        reverse=True
    )
    
    if projects_by_rate and projects_by_rate[0][1]['current_spend_rate'] > 0:
        insights['highest_burn_rate'] = {
            'id': projects_by_rate[0][0],
            'rate': projects_by_rate[0][1]['current_spend_rate'],
            'cost_per_hour': projects_by_rate[0][1]['cost_per_hour']
        }
    
    # Calculate total variance
    total_actual = sum(p['total_cost'] for p in summary['projects'].values())
    total_naive = sum(p.get('naive_estimate', 0) for p in summary['projects'].values())
    
    if total_naive > 0:
        insights['total_vs_naive_variance'] = round(
            ((total_actual - total_naive) / total_naive) * 100, 1
        )
    
    # Generate recommendations
    for project_id, stats in summary['projects'].items():
        if stats['current_spend_rate'] > 50000:  # More than 50k tokens/hour
            insights['recommendations'].append({
                'project_id': project_id,
                'type': 'high_burn_rate',
                'message': f"Project {project_id} burning {stats['current_spend_rate']:.0f} tokens/hour"
            })
        
        if stats.get('cost_accuracy', {}).get('percentage', 0) > 200:
            insights['recommendations'].append({
                'project_id': project_id,
                'type': 'cost_overrun',
                'message': f"Project {project_id} is {stats['cost_accuracy']['percentage']:.0f}% over estimate"
            })
    
    return insights