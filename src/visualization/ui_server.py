"""
Web UI server for PM Agent visualization

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
from .decision_visualizer import DecisionVisualizer
from .knowledge_graph import KnowledgeGraphBuilder


class VisualizationServer:
    """
    Web server for PM Agent visualization interface
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')
        self.sio.attach(self.app)
        
        # Components
        self.conversation_processor = ConversationStreamProcessor()
        self.decision_visualizer = DecisionVisualizer()
        self.knowledge_graph = KnowledgeGraphBuilder()
        
        # Active connections
        self.active_sessions: Set[str] = set()
        
        # Setup
        self._setup_routes()
        self._setup_socketio()
        self._setup_templates()
        
        # Add conversation event handler
        self.conversation_processor.add_event_handler(self._handle_conversation_event)
        
    def _setup_routes(self):
        """Setup HTTP routes"""
        # Static files
        static_dir = Path(__file__).parent / 'static'
        self.app.router.add_static('/static', static_dir)
        
        # API routes
        self.app.router.add_get('/', self._index_handler)
        self.app.router.add_get('/api/status', self._status_handler)
        self.app.router.add_get('/api/conversations/history', self._conversation_history_handler)
        self.app.router.add_get('/api/decisions/analytics', self._decision_analytics_handler)
        self.app.router.add_get('/api/knowledge/graph', self._knowledge_graph_handler)
        self.app.router.add_get('/api/knowledge/statistics', self._knowledge_stats_handler)
        self.app.router.add_post('/api/decisions/{decision_id}/outcome', self._update_decision_outcome)
        
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
            cors.add(route)
            
    def _setup_socketio(self):
        """Setup Socket.IO events"""
        
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
            
    def _setup_templates(self):
        """Setup Jinja2 templates"""
        template_dir = Path(__file__).parent / 'templates'
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
        
    async def _handle_conversation_event(self, event: ConversationEvent):
        """Handle new conversation events and broadcast to clients"""
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
        
    async def _broadcast_event(self, event: ConversationEvent):
        """Broadcast event to all connected clients"""
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
            title="PM Agent Visualization",
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
            'history': [event.to_dict() for event in history],
            'total': len(self.conversation_processor.conversation_history)
        })
        
    async def _decision_analytics_handler(self, request):
        """Get decision analytics"""
        analytics = self.decision_visualizer.get_decision_analytics()
        trends = self.decision_visualizer.get_confidence_trends()
        
        return web.json_response({
            'analytics': analytics,
            'confidence_trends': [
                {'timestamp': t.isoformat(), 'confidence': c}
                for t, c in trends
            ]
        })
        
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
        
    async def start(self):
        """Start the visualization server"""
        # Start conversation streaming
        asyncio.create_task(self.conversation_processor.start_streaming())
        
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