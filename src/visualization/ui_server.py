"""
Web UI server for Marcus visualization

Provides real-time visualization of:
- Agent conversations
- Decision-making processes
- Knowledge graph
- System metrics
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from aiohttp import web
import aiohttp_cors
import socketio
from jinja2 import Environment, FileSystemLoader

from .conversation_stream import ConversationStreamProcessor, ConversationEvent
# Lazy imports to avoid NetworkX until needed
# from .decision_visualizer import DecisionVisualizer
# from .knowledge_graph import KnowledgeGraphBuilder
from .health_monitor import HealthMonitor
from .pipeline_flow import PipelineFlowVisualizer, PipelineStage
from .shared_pipeline_events import SharedPipelineVisualizer


class VisualizationServer:
    """
    Web server for Marcus visualization interface.
    
    Provides a real-time web UI for visualizing agent conversations,
    decision-making processes, knowledge graphs, and system health metrics.
    Uses Socket.IO for real-time bidirectional communication.
    
    Attributes
    ----------
    host : str
        Server host address
    port : int
        Server port number
    app : web.Application
        aiohttp web application instance
    sio : socketio.AsyncServer
        Socket.IO server for real-time communication
    conversation_processor : ConversationStreamProcessor
        Processes conversation events
    decision_visualizer : DecisionVisualizer (property)
        Lazy-loaded visualizer for decision-making processes
    knowledge_graph : KnowledgeGraphBuilder (property)
        Lazy-loaded knowledge graph builder
    health_monitor : HealthMonitor
        Monitors system health metrics
    active_sessions : Set[str]
        Set of active client session IDs
    
    Examples
    --------
    >>> server = VisualizationServer(host="localhost", port=8080)
    >>> await server.start()
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        """
        Initialize the visualization server.
        
        Parameters
        ----------
        host : str, default="0.0.0.0"
            Host address to bind the server to
        port : int, default=8080
            Port number to listen on
        """
        self.host = host
        self.port = port
        self.app = web.Application()
        self.sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')
        
        # Attach socket.io AFTER route setup to avoid CORS conflicts
        # self.sio.attach(self.app)  # Will be done after routes are set up
        
        # Components
        self.conversation_processor = ConversationStreamProcessor()
        self._decision_visualizer = None  # Lazy loaded
        self._knowledge_graph = None      # Lazy loaded
        self.health_monitor = HealthMonitor()
        # Use shared pipeline visualizer for cross-process communication
        self.pipeline_visualizer = SharedPipelineVisualizer()
        
        # Active connections
        self.active_sessions: Set[str] = set()
        
        # Setup (synchronous parts only)
        self._setup_socketio()
        self._setup_templates()
        
        # Routes need to be set up via async setup_routes() method
        # Socket.io will be attached after routes are set up
        
        # Add conversation event handler
        self.conversation_processor.add_event_handler(self._handle_conversation_event)
        
        # Note: Pipeline events are shared via file system, no direct handler needed
    
    @property
    def decision_visualizer(self):
        """Lazy load DecisionVisualizer to avoid NetworkX import"""
        if self._decision_visualizer is None:
            from .decision_visualizer import DecisionVisualizer
            self._decision_visualizer = DecisionVisualizer()
        return self._decision_visualizer
    
    @property
    def knowledge_graph(self):
        """Lazy load KnowledgeGraphBuilder to avoid NetworkX import"""
        if self._knowledge_graph is None:
            from .knowledge_graph import KnowledgeGraphBuilder
            self._knowledge_graph = KnowledgeGraphBuilder()
        return self._knowledge_graph
        
        # Routes will be set up via setup_routes() method
        
    async def setup_routes(self) -> None:
        """
        Setup HTTP routes and CORS configuration.
        
        Configures static file serving, API endpoints, and CORS settings
        for cross-origin requests. Socket.IO routes are excluded from
        CORS setup as they handle it internally.
        """
        # Static files
        static_dir = Path(__file__).parent / 'static'
        if static_dir.exists():
            self.app.router.add_static('/static', static_dir)
        
        # API routes
        self.app.router.add_get('/', self._index_handler)
        self.app.router.add_get('/pipeline', self._pipeline_handler)
        self.app.router.add_get('/pipeline-debug', self._pipeline_debug_handler)
        self.app.router.add_get('/api/status', self._status_handler)
        # Add both full paths and shortcuts for compatibility
        self.app.router.add_get('/api/conversations', self._conversation_history_handler)
        self.app.router.add_get('/api/conversations/history', self._conversation_history_handler)
        self.app.router.add_get('/api/decisions', self._decision_analytics_handler)
        self.app.router.add_get('/api/decisions/analytics', self._decision_analytics_handler)
        self.app.router.add_get('/api/knowledge', self._knowledge_graph_handler)
        self.app.router.add_get('/api/knowledge/graph', self._knowledge_graph_handler)
        self.app.router.add_get('/api/knowledge/statistics', self._knowledge_stats_handler)
        self.app.router.add_post('/api/decisions/{decision_id}/outcome', self._update_decision_outcome)
        
        # Health analysis routes
        self.app.router.add_get('/api/health', self._health_current_handler)  # Shortcut
        self.app.router.add_get('/api/health/current', self._health_current_handler)
        self.app.router.add_get('/api/health/history', self._health_history_handler)
        self.app.router.add_get('/api/health/summary', self._health_summary_handler)
        self.app.router.add_post('/api/health/analyze', self._health_analyze_handler)
        
        # Debug endpoint for streaming
        self.app.router.add_get('/api/debug/streaming', self._debug_streaming_handler)
        
        # Enable CORS
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        for route in list(self.app.router.routes()):
            # Skip socket.io routes as they handle CORS internally
            if not str(route.resource).startswith('/socket.io'):
                cors.add(route)
                
        # Attach socket.io after routes are set up
        self.sio.attach(self.app)
            
    def _setup_socketio(self) -> None:
        """
        Setup Socket.IO event handlers.
        
        Defines handlers for client connections, disconnections,
        subscriptions, and various data requests. Each handler is
        decorated as a Socket.IO event.
        """
        
        @self.sio.event
        async def connect(sid, environ):
            """Handle client connection"""
            self.active_sessions.add(sid)
            logging.info(f"Client connected: {sid}")
            
            # Send initial data
            await self.sio.emit('connection_established', {
                'session_id': sid,
                'timestamp': datetime.now().isoformat()
            }, room=sid)
            
            # Send conversation summary
            summary = self.conversation_processor.get_conversation_summary()
            await self.sio.emit('conversation_summary', summary, room=sid)
            
        @self.sio.event
        async def disconnect(sid):
            """Handle client disconnection"""
            self.active_sessions.discard(sid)
            logging.info(f"Client disconnected: {sid}")
            
        @self.sio.event
        async def subscribe_conversations(sid, data):
            """Subscribe to real-time conversation updates"""
            await self.sio.emit('subscription_confirmed', {
                'type': 'conversations',
                'status': 'active'
            }, room=sid)
            
        @self.sio.event
        async def request_decision_tree(sid, data):
            """Generate and send decision tree visualization"""
            decision_id = data.get('decision_id')
            if decision_id:
                output_file = f"decision_tree_{decision_id}.html"
                self.decision_visualizer.generate_decision_tree_html(decision_id, output_file)
                
                # Read and send the HTML content
                with open(output_file, 'r') as f:
                    html_content = f.read()
                    
                await self.sio.emit('decision_tree_ready', {
                    'decision_id': decision_id,
                    'html': html_content
                }, room=sid)
                
        @self.sio.event
        async def request_knowledge_graph(sid, data):
            """Generate and send knowledge graph visualization"""
            filter_types = data.get('filter_types', None)
            output_file = "knowledge_graph.html"
            
            self.knowledge_graph.generate_interactive_graph(output_file, filter_types)
            
            # Read and send the HTML content
            with open(output_file, 'r') as f:
                html_content = f.read()
                
            await self.sio.emit('knowledge_graph_ready', {
                'html': html_content,
                'statistics': self.knowledge_graph.get_graph_statistics()
            }, room=sid)
            
        @self.sio.event
        async def subscribe_health_updates(sid, data):
            """Subscribe to real-time health updates"""
            await self.sio.emit('subscription_confirmed', {
                'type': 'health',
                'status': 'active'
            }, room=sid)
            
            # Send current health if available
            if self.health_monitor.last_analysis:
                await self.sio.emit('health_update', 
                    self.health_monitor.last_analysis, 
                    room=sid)
                    
        @self.sio.event
        async def request_health_analysis(sid, data):
            """Request immediate health analysis"""
            # In production, gather actual project state
            # For now, send last analysis or error
            if self.health_monitor.last_analysis:
                await self.sio.emit('health_analysis_complete',
                    self.health_monitor.last_analysis,
                    room=sid)
            else:
                await self.sio.emit('health_analysis_error', {
                    'error': 'No health data available',
                    'message': 'Run a health analysis first'
                }, room=sid)
        
        @self.sio.event
        async def subscribe_pipeline_flow(sid, data):
            """Subscribe to real-time pipeline flow updates"""
            logging.info(f"Client {sid} subscribing to pipeline flow")
            
            await self.sio.emit('subscription_confirmed', {
                'type': 'pipeline_flow',
                'status': 'active'
            }, room=sid)
            
            # Send active flows
            active_flows = self.pipeline_visualizer.get_active_flows()
            logging.info(f"Sending {len(active_flows)} active flows to client {sid}")
            
            await self.sio.emit('active_flows_update', {
                'flows': active_flows
            }, room=sid)
        
        @self.sio.event
        async def request_flow_visualization(sid, data):
            """Request visualization for a specific flow"""
            flow_id = data.get('flow_id')
            if not flow_id:
                await self.sio.emit('flow_visualization_error', {
                    'error': 'flow_id is required'
                }, room=sid)
                return
            
            visualization = self.pipeline_visualizer.get_flow_visualization(flow_id)
            
            if 'error' in visualization:
                await self.sio.emit('flow_visualization_error', visualization, room=sid)
            else:
                await self.sio.emit('flow_visualization_ready', visualization, room=sid)
            
    def _setup_templates(self) -> None:
        """
        Setup Jinja2 template environment.
        
        Configures the template loader to use the templates directory
        relative to this module's location.
        """
        template_dir = Path(__file__).parent / 'templates'
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
    
    # Public wrapper methods for tests
    async def handle_conversation_event(self, event: ConversationEvent) -> None:
        """Public wrapper for _handle_conversation_event (for tests)"""
        await self._handle_conversation_event(event)
    
    async def emit_decision_update(self, decision_id: str) -> None:
        """Emit decision update to all clients"""
        decision = self.decision_visualizer.decisions.get(decision_id)
        if decision:
            await self.sio.emit('decision_update', {
                'decision_id': decision_id,
                'data': {
                    'decision': decision.decision,
                    'confidence': decision.confidence_score,
                    'outcome': decision.outcome
                }
            })
    
    async def emit_health_update(self, health_data: Dict[str, Any]) -> None:
        """Emit health update to all clients"""
        await self.sio.emit('health_update', health_data)
    
        
    async def _handle_conversation_event(self, event: ConversationEvent) -> None:
        """
        Handle new conversation events and broadcast to clients.
        
        Processes different event types (Marcus decisions, worker messages,
        task assignments) and updates relevant visualization components
        before broadcasting to all connected clients.
        
        Parameters
        ----------
        event : ConversationEvent
            The conversation event to process
        
        Notes
        -----
        Event types handled:
        - pm_decision: Updates decision visualizer
        - worker_message: Extracts worker registration info
        - task_assignment: Updates knowledge graph
        """
        # Process event for visualization components
        if event.event_type == 'pm_decision':
            self.decision_visualizer.add_decision({
                'id': event.id,
                'timestamp': event.timestamp.isoformat(),
                'decision': event.message,
                'rationale': event.metadata.get('rationale', ''),
                'confidence_score': event.confidence or 0.5,
                'alternatives_considered': event.metadata.get('alternatives', []),
                'decision_factors': event.metadata.get('decision_factors', {})
            })
            
        elif event.event_type == 'worker_message' and 'Registering' in event.message:
            # Extract worker registration info
            metadata = event.metadata
            if 'name' in metadata and 'role' in metadata:
                self.knowledge_graph.add_worker(
                    event.source,
                    metadata['name'],
                    metadata['role'],
                    metadata.get('skills', [])
                )
        
        elif event.event_type == 'worker_registration':
            # Handle direct worker registration events
            self.knowledge_graph.add_worker(
                event.metadata.get('worker_id', event.source),
                event.metadata.get('name', 'Unknown'),
                event.metadata.get('role', 'Agent'),
                event.metadata.get('skills', [])
            )
                
        elif event.event_type == 'task_assignment':
            # Update knowledge graph with assignment
            task_details = event.metadata.get('task_details', {})
            self.knowledge_graph.add_task(
                event.metadata.get('task_id', 'unknown'),
                task_details.get('name', 'Unknown Task'),
                task_details
            )
            self.knowledge_graph.assign_task(
                event.metadata.get('task_id', 'unknown'),
                event.target,
                event.metadata.get('assignment_score', 0.5)
            )
            
        # Broadcast to all connected clients
        await self._broadcast_event(event)
    
    async def _handle_pipeline_event(self, flow_id: str, event: Any) -> None:
        """
        Handle pipeline flow events.
        
        Processes pipeline events and broadcasts updates to connected clients.
        
        Parameters
        ----------
        flow_id : str
            The flow ID this event belongs to
        event : PipelineEvent
            The pipeline event to process
        """
        # Convert event to dict for broadcasting
        event_data = {
            'flow_id': flow_id,
            'event_id': event.id,
            'stage': event.stage.value,
            'timestamp': event.timestamp.isoformat(),
            'event_type': event.event_type,
            'status': event.status,
            'data': event.data
        }
        
        if event.error:
            event_data['error'] = event.error
        if event.duration_ms:
            event_data['duration_ms'] = event.duration_ms
            
        # Emit pipeline event to all connected clients
        await self.sio.emit('pipeline_event', event_data)
        
    async def _broadcast_event(self, event: ConversationEvent) -> None:
        """
        Broadcast event to all connected clients.
        
        Converts the event to a dictionary and emits it through
        Socket.IO. Also emits type-specific events for targeted
        client-side handling.
        
        Parameters
        ----------
        event : ConversationEvent
            The event to broadcast
        """
        event_data = event.to_dict()
        
        # Emit to all connected clients
        await self.sio.emit('conversation_event', event_data)
        
        # Also emit specific event types for targeted handling
        if event.event_type == 'pm_decision':
            await self.sio.emit('decision_event', event_data)
        elif event.event_type == 'task_assignment':
            await self.sio.emit('assignment_event', event_data)
        elif event.event_type == 'blocker_report':
            await self.sio.emit('blocker_event', event_data)
            
    async def _index_handler(self, request):
        """Serve main visualization page"""
        template = self.jinja_env.get_template('index.html')
        html = template.render(
            title="Marcus Visualization",
            server_url=f"http://{self.host}:{self.port}"
        )
        return web.Response(text=html, content_type='text/html')
    
    async def _pipeline_handler(self, request):
        """Serve pipeline visualization page"""
        template = self.jinja_env.get_template('pipeline.html')
        html = template.render(
            title="Marcus Pipeline Flow",
            server_url=f"http://{self.host}:{self.port}"
        )
        return web.Response(text=html, content_type='text/html')
    
    async def _pipeline_debug_handler(self, request):
        """Serve pipeline debug page"""
        template = self.jinja_env.get_template('pipeline_debug.html')
        html = template.render(
            title="Pipeline Debug",
            server_url=f"http://{self.host}:{self.port}"
        )
        return web.Response(text=html, content_type='text/html')
        
    async def _status_handler(self, request):
        """Get server status"""
        return web.json_response({
            'status': 'running',
            'active_sessions': len(self.active_sessions),
            'conversation_summary': self.conversation_processor.get_conversation_summary(),
            'decision_count': len(self.decision_visualizer.decisions),
            'knowledge_nodes': len(self.knowledge_graph.nodes)
        })
        
    async def _conversation_history_handler(self, request):
        """Get conversation history"""
        limit = int(request.query.get('limit', 100))
        history = self.conversation_processor.conversation_history[-limit:]
        
        return web.json_response({
            'events': [event.to_dict() for event in history],  # Changed from 'history' to 'events'
            'total': len(self.conversation_processor.conversation_history)
        })
        
    async def _decision_analytics_handler(self, request):
        """Handle analytics data requests with proper error handling"""
        try:
            # Get analytics from decision visualizer
            analytics = self.decision_visualizer.get_decision_analytics()
            
            # Ensure we have valid data
            if not analytics:
                analytics = {
                    'total_decisions': 0,
                    'average_confidence': 0.0,
                    'decision_distribution': {},
                    'confidence_trends': []
                }
            
            # Convert Decision objects to dictionaries if needed
            decisions_dict = {}
            if hasattr(self.decision_visualizer, 'decisions'):
                for decision_id, decision in self.decision_visualizer.decisions.items():
                    if hasattr(decision, '__dict__'):
                        # It's an object, convert to dict
                        decisions_dict[decision_id] = {
                            'id': getattr(decision, 'id', decision_id),
                            'timestamp': getattr(decision, 'timestamp', datetime.now()).isoformat(),
                            'decision': getattr(decision, 'decision', ''),
                            'rationale': getattr(decision, 'rationale', ''),
                            'confidence_score': getattr(decision, 'confidence_score', 0.0),
                            'alternatives': getattr(decision, 'alternatives', []),
                            'decision_factors': getattr(decision, 'decision_factors', {}),
                            'outcome': getattr(decision, 'outcome', None),
                            'outcome_timestamp': getattr(decision, 'outcome_timestamp', datetime.now()).isoformat() if getattr(decision, 'outcome_timestamp', None) else None
                        }
                    else:
                        # It's already a dict
                        decisions_dict[decision_id] = decision
            
            # Prepare response
            response_data = {
                'analytics': analytics,
                'decisions': decisions_dict,
                'confidence_trends': analytics.get('confidence_trends', [])
            }
            
            return web.json_response(response_data)
            
        except Exception as e:
            logging.error(f"Error in analytics handler: {str(e)}")
            # Return valid JSON error response
            return web.json_response({
                'error': 'Internal server error',
                'analytics': {
                    'total_decisions': 0,
                    'average_confidence': 0.0,
                    'decision_distribution': {},
                    'confidence_trends': []
                },
                'decisions': {},
                'confidence_trends': []
            }, status=500)
    async def _knowledge_graph_handler(self, request):
        """Get knowledge graph data"""
        format = request.query.get('format', 'json')
        data = self.knowledge_graph.export_graph_data(format)
        
        if format == 'json':
            return web.json_response(json.loads(data))
        else:
            return web.Response(text=data, content_type='application/json')
            
    async def _knowledge_stats_handler(self, request):
        """Get knowledge graph statistics"""
        stats = self.knowledge_graph.get_graph_statistics()
        skill_gaps = self.knowledge_graph.find_skill_gaps()
        
        return web.json_response({
            'statistics': stats,
            'skill_gaps': skill_gaps
        })
        
    async def _update_decision_outcome(self, request):
        """Update decision outcome"""
        decision_id = request.match_info['decision_id']
        data = await request.json()
        outcome = data.get('outcome')
        
        if outcome:
            self.decision_visualizer.update_decision_outcome(decision_id, outcome)
            
        return web.json_response({'success': True})
        
    
    
    async def _debug_streaming_handler(self, request: web.Request) -> web.Response:
        """Debug endpoint to check streaming status"""
        return web.json_response({
            'streaming_active': self.conversation_processor._running,
            'event_handlers': len(self.conversation_processor.event_handlers),
            'history_size': len(self.conversation_processor.conversation_history),
            'last_events': [
                {
                    'type': e.event_type,
                    'source': e.source,
                    'target': e.target,
                    'message': e.message[:50] if e.message else 'No message'
                }
                for e in self.conversation_processor.conversation_history[-5:]
            ] if self.conversation_processor.conversation_history else []
        })

    async def _health_current_handler(self, request):
        """Get current health analysis"""
        if self.health_monitor.last_analysis:
            return web.json_response(self.health_monitor.last_analysis)
        else:
            return web.json_response({
                'status': 'no_data',
                'message': 'No health analysis available yet',
                'overall_health': 'unknown',
                'trends': [],
                'alerts': []
            })
            
    async def _health_history_handler(self, request):
        """Get health analysis history"""
        hours = int(request.query.get('hours', 24))
        history = self.health_monitor.get_health_history(hours)
        
        return web.json_response({
            'history': history,
            'count': len(history),
            'hours': hours
        })
        
    async def _health_summary_handler(self, request):
        """Get health summary statistics"""
        summary = self.health_monitor.get_health_summary()
        return web.json_response(summary)
        
    async def _health_analyze_handler(self, request):
        """Run health analysis with provided data"""
        try:
            data = await request.json()
            
            # Extract project state, activities, and team status from request
            # In production, this would come from actual system state
            from src.core.models import ProjectState, RiskLevel
            
            # Create ProjectState from request data
            project_data = data.get('project_state', {})
            project_state = ProjectState(
                board_id=project_data.get('board_id', 'BOARD-001'),
                project_name=project_data.get('project_name', 'Unknown Project'),
                total_tasks=project_data.get('total_tasks', 0),
                completed_tasks=project_data.get('completed_tasks', 0),
                in_progress_tasks=project_data.get('in_progress_tasks', 0),
                blocked_tasks=project_data.get('blocked_tasks', 0),
                progress_percent=project_data.get('progress_percent', 0.0),
                overdue_tasks=[],  # Would be populated from actual data
                team_velocity=project_data.get('team_velocity', 0.0),
                risk_level=RiskLevel[project_data.get('risk_level', 'MEDIUM').upper()],
                last_updated=datetime.now()
            )
            
            recent_activities = data.get('recent_activities', [])
            team_status = data.get('team_status', [])
            
            # Run analysis
            health_analysis = await self.health_monitor.get_project_health(
                project_state,
                recent_activities,
                team_status
            )
            
            # Broadcast to all connected clients
            await self.sio.emit('health_update', health_analysis)
            
            return web.json_response(health_analysis)
            
        except Exception as e:
            logging.error(f"Health analysis failed: {e}")
            return web.json_response({
                'error': 'Analysis failed',
                'message': str(e)
            }, status=500)
        
    async def start(self):
        """Start the visualization server"""
        # Setup routes first
        await self.setup_routes()
        
        # Initialize health monitor
        await self.health_monitor.initialize()
        
        # Start conversation streaming
        # Start streaming and capture any errors
        async def start_streaming_with_logging():
            try:
                await self.conversation_processor.start_streaming()
            except Exception as e:
                logging.error(f"Conversation streaming failed: {e}")
        
        asyncio.create_task(start_streaming_with_logging())
        logging.info("Started conversation streaming task")
        
        # Start health monitoring (it runs independently)
        await self.health_monitor.start_monitoring()
        
        # Start pipeline event polling
        async def poll_pipeline_events():
            """Poll for pipeline events and broadcast to clients"""
            poll_count = 0
            while True:
                try:
                    # Get active flows
                    active_flows = self.pipeline_visualizer.get_active_flows()
                    
                    # Log every 10th poll to avoid spam
                    if poll_count % 10 == 0:
                        logging.info(f"Pipeline poll #{poll_count}: {len(active_flows)} active flows")
                    
                    # Broadcast to all clients
                    if len(self.active_sessions) > 0:
                        await self.sio.emit('active_flows_update', {
                            'flows': active_flows
                        })
                    
                    poll_count += 1
                    await asyncio.sleep(1)  # Poll every second
                except Exception as e:
                    logging.error(f"Pipeline polling error: {e}")
                    await asyncio.sleep(5)  # Back off on error
        
        asyncio.create_task(poll_pipeline_events())
        logging.info("Started pipeline event polling")
        
        # Start web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        logging.info(f"Visualization server running at http://{self.host}:{self.port}")
        
        # Keep server running
        try:
            await asyncio.Event().wait()
        finally:
            await runner.cleanup()
            self.conversation_processor.stop_streaming()
            
    def run(self):
        """Run the server (blocking)"""
        asyncio.run(self.start())


def main():
    """Run the visualization server"""
    logging.basicConfig(level=logging.INFO)
    server = VisualizationServer()
    server.run()


if __name__ == "__main__":
    main()