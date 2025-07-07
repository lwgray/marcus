"""
Marcus Pipeline Enhancement API Server

Main Flask application that serves the pipeline enhancement features
through REST API and WebSocket connections.
"""

import asyncio
import os
from flask import Flask, render_template, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO

# Import API blueprints
from src.api.pipeline_enhancement_api import pipeline_api, setup_websocket_handlers
from src.api.agent_management_api import agent_api, setup_agent_websocket_handlers
from src.api.project_management_api import project_api
from src.api.cost_tracking_api import cost_tracking_bp

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Enable CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Register blueprints
app.register_blueprint(pipeline_api)
app.register_blueprint(agent_api)
app.register_blueprint(project_api)
app.register_blueprint(cost_tracking_bp)

# Static file serving for frontend
@app.route('/')
def index():
    """Serve the main frontend application."""
    return render_template('index.html')

@app.route('/test')
def test():
    """Serve test page."""
    return render_template('test.html')


@app.route('/static/<path:path>')
def serve_static(path):
    """Serve static files."""
    return send_from_directory('static', path)


# Health check endpoint
@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "marcus-pipeline-api"}


# Setup WebSocket handlers
emit_updates_task = setup_websocket_handlers(socketio)
setup_agent_websocket_handlers(socketio)


def run_server(host='0.0.0.0', port=5000, debug=False):
    """Run the API server."""
    # Start background task for WebSocket updates
    socketio.start_background_task(emit_updates_task)
    
    # Run the server
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    run_server(debug=True)