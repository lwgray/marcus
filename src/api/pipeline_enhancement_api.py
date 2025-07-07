"""
Pipeline Enhancement API Endpoints

Provides REST API endpoints for pipeline replay, what-if analysis,
comparison, monitoring, error prediction, and recommendations.
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any

from src.mcp.tools.pipeline_enhancement_tools import pipeline_tools
from src.api.async_wrapper import async_route

# Create blueprint
pipeline_api = Blueprint('pipeline_enhancement', __name__, url_prefix='/api/pipeline')


# ==================== Pipeline Replay Endpoints ====================

@pipeline_api.route('/replay/start', methods=['POST'])
@async_route
async def start_replay():
    """Start replay session for a pipeline flow."""
    data = request.get_json()
    flow_id = data.get('flow_id')
    
    if not flow_id:
        return jsonify({"error": "flow_id is required"}), 400
        
    result = await pipeline_tools.start_replay(flow_id)
    return jsonify(result)


@pipeline_api.route('/replay/forward', methods=['POST'])
@async_route
async def replay_forward():
    """Step forward in pipeline replay."""
    result = await pipeline_tools.replay_step_forward()
    return jsonify(result)


@pipeline_api.route('/replay/backward', methods=['POST'])
@async_route
async def replay_backward():
    """Step backward in pipeline replay."""
    result = await pipeline_tools.replay_step_backward()
    return jsonify(result)


@pipeline_api.route('/replay/jump', methods=['POST'])
@async_route
async def replay_jump():
    """Jump to specific position in replay."""
    data = request.get_json()
    position = data.get('position')
    
    if position is None:
        return jsonify({"error": "position is required"}), 400
        
    result = await pipeline_tools.replay_jump_to(position)
    return jsonify(result)


# ==================== What-If Analysis Endpoints ====================

@pipeline_api.route('/whatif/start', methods=['POST'])
@async_route
async def start_whatif():
    """Start what-if analysis session."""
    data = request.get_json()
    flow_id = data.get('flow_id')
    
    if not flow_id:
        return jsonify({"error": "flow_id is required"}), 400
        
    result = await pipeline_tools.start_what_if_analysis(flow_id)
    return jsonify(result)


@pipeline_api.route('/whatif/simulate', methods=['POST'])
@async_route
async def simulate_whatif():
    """Simulate pipeline with modifications."""
    data = request.get_json()
    modifications = data.get('modifications', [])
    
    if not modifications:
        return jsonify({"error": "modifications are required"}), 400
        
    result = await pipeline_tools.simulate_modification(modifications)
    return jsonify(result)


@pipeline_api.route('/whatif/compare', methods=['GET'])
@async_route
async def compare_whatif():
    """Compare all what-if scenarios."""
    result = await pipeline_tools.compare_what_if_scenarios()
    return jsonify(result)


# ==================== Comparison Endpoints ====================

@pipeline_api.route('/compare', methods=['POST'])
@async_route
async def compare_flows():
    """Compare multiple pipeline flows."""
    data = request.get_json()
    flow_ids = data.get('flow_ids', [])
    
    if not flow_ids or len(flow_ids) < 2:
        return jsonify({"error": "At least 2 flow_ids are required"}), 400
        
    result = await pipeline_tools.compare_pipelines(flow_ids)
    return jsonify(result)


@pipeline_api.route('/report/<flow_id>', methods=['GET'])
@async_route
async def generate_report(flow_id):
    """Generate pipeline report."""
    format = request.args.get('format', 'html')
    
    if format not in ['html', 'markdown', 'json']:
        return jsonify({"error": "Invalid format. Use html, markdown, or json"}), 400
        
    result = await pipeline_tools.generate_report(flow_id, format)
    
    if result.get('success'):
        if format == 'html':
            return result['content'], 200, {'Content-Type': 'text/html'}
        elif format == 'markdown':
            return result['content'], 200, {'Content-Type': 'text/plain'}
        else:
            return jsonify(result)
    else:
        return jsonify(result), 500


# ==================== Monitoring Endpoints ====================

@pipeline_api.route('/monitor/dashboard', methods=['GET'])
@async_route
async def get_dashboard():
    """Get live monitoring dashboard data."""
    result = await pipeline_tools.get_live_dashboard()
    return jsonify(result)


@pipeline_api.route('/monitor/flow/<flow_id>', methods=['GET'])
@async_route
async def track_flow(flow_id):
    """Track specific flow progress."""
    result = await pipeline_tools.track_flow_progress(flow_id)
    return jsonify(result)


@pipeline_api.route('/monitor/risk/<flow_id>', methods=['GET'])
@async_route
async def predict_risk(flow_id):
    """Predict failure risk for a flow."""
    result = await pipeline_tools.predict_failure_risk(flow_id)
    return jsonify(result)


# ==================== Recommendation Endpoints ====================

@pipeline_api.route('/recommendations/<flow_id>', methods=['GET'])
@async_route
async def get_recommendations(flow_id):
    """Get recommendations for a pipeline flow."""
    result = await pipeline_tools.get_recommendations(flow_id)
    return jsonify(result)


@pipeline_api.route('/similar/<flow_id>', methods=['GET'])
@async_route
async def find_similar(flow_id):
    """Find similar pipeline flows."""
    limit = request.args.get('limit', 5, type=int)
    result = await pipeline_tools.find_similar_flows(flow_id, limit)
    return jsonify(result)


# ==================== WebSocket Support for Live Updates ====================

def setup_websocket_handlers(socketio):
    """Setup WebSocket handlers for real-time updates."""
    
    @socketio.on('subscribe_flow')
    def handle_subscribe_flow(data):
        """Subscribe to real-time updates for a flow."""
        flow_id = data.get('flow_id')
        if flow_id:
            # Add client to room for this flow
            from flask_socketio import join_room
            join_room(f'flow_{flow_id}')
            
    @socketio.on('unsubscribe_flow')
    def handle_unsubscribe_flow(data):
        """Unsubscribe from flow updates."""
        flow_id = data.get('flow_id')
        if flow_id:
            from flask_socketio import leave_room
            leave_room(f'flow_{flow_id}')
            
    # Background task to emit updates
    async def emit_flow_updates():
        """Emit flow updates to subscribed clients."""
        while True:
            dashboard = await pipeline_tools.get_live_dashboard()
            
            if dashboard.get('success'):
                # Emit to all connected clients
                socketio.emit('dashboard_update', dashboard['dashboard'])
                
                # Emit flow-specific updates
                for flow in dashboard['dashboard'].get('active_flows', []):
                    flow_id = flow['flow_id']
                    socketio.emit('flow_update', flow, room=f'flow_{flow_id}')
                    
            await asyncio.sleep(1)  # Update every second
            
    return emit_flow_updates