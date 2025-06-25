"""
Scaled PM Agent Server Implementation

This module provides a scalable HTTP/WebSocket server implementation
that can handle multiple concurrent agent connections.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis.asyncio as redis
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from starlette.responses import Response

from pm_agent.core.agent_manager import PMAgentState
from pm_agent.tools.mcp_tools import AgentTools
from pm_agent.config import settings


# Metrics
active_connections = Gauge('pm_agent_active_connections', 'Number of active WebSocket connections')
total_connections = Counter('pm_agent_total_connections', 'Total number of connections')
messages_received = Counter('pm_agent_messages_received', 'Total messages received')
messages_sent = Counter('pm_agent_messages_sent', 'Total messages sent')
request_duration = Histogram('pm_agent_request_duration', 'Request duration in seconds')

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for agents."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.active_connections: Dict[str, WebSocket] = {}
        self.redis = redis_client
        self._connection_limit = settings.get('max_connections', 1000)
    
    async def connect(self, agent_id: str, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        if len(self.active_connections) >= self._connection_limit:
            await websocket.close(code=1008, reason="Connection limit reached")
            raise HTTPException(status_code=503, detail="Connection limit reached")
        
        await websocket.accept()
        self.active_connections[agent_id] = websocket
        active_connections.inc()
        total_connections.inc()
        
        # Store connection info in Redis if available
        if self.redis:
            await self.redis.hset(
                f"agent:connections:{agent_id}",
                mapping={
                    "connected_at": datetime.utcnow().isoformat(),
                    "server_id": settings.get('server_id', 'default')
                }
            )
        
        logger.info(f"Agent {agent_id} connected. Total connections: {len(self.active_connections)}")
    
    async def disconnect(self, agent_id: str):
        """Remove a WebSocket connection."""
        if agent_id in self.active_connections:
            del self.active_connections[agent_id]
            active_connections.dec()
            
            # Remove from Redis if available
            if self.redis:
                await self.redis.hdel(f"agent:connections:{agent_id}")
            
            logger.info(f"Agent {agent_id} disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_message(self, agent_id: str, message: dict):
        """Send a message to a specific agent."""
        if agent_id in self.active_connections:
            websocket = self.active_connections[agent_id]
            await websocket.send_json(message)
            messages_sent.inc()
    
    async def broadcast(self, message: dict, exclude: Optional[Set[str]] = None):
        """Broadcast a message to all connected agents."""
        exclude = exclude or set()
        disconnected = []
        
        for agent_id, websocket in self.active_connections.items():
            if agent_id not in exclude:
                try:
                    await websocket.send_json(message)
                    messages_sent.inc()
                except:
                    disconnected.append(agent_id)
        
        # Clean up disconnected clients
        for agent_id in disconnected:
            await self.disconnect(agent_id)


class StateManager:
    """Manages PM Agent state with Redis backing."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        self._local_cache = {}
        self._cache_ttl = 300  # 5 minutes
    
    async def get_agent_status(self, agent_id: str) -> Optional[dict]:
        """Get agent status from cache or Redis."""
        # Check local cache first
        if agent_id in self._local_cache:
            return self._local_cache[agent_id]
        
        # Check Redis
        if self.redis:
            data = await self.redis.hgetall(f"agent:status:{agent_id}")
            if data:
                status = {k.decode(): json.loads(v.decode()) if v else None 
                         for k, v in data.items()}
                self._local_cache[agent_id] = status
                return status
        
        return None
    
    async def set_agent_status(self, agent_id: str, status: dict):
        """Set agent status in cache and Redis."""
        self._local_cache[agent_id] = status
        
        if self.redis:
            # Serialize complex objects to JSON
            serialized = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) 
                         for k, v in status.items()}
            await self.redis.hset(f"agent:status:{agent_id}", mapping=serialized)
            await self.redis.expire(f"agent:status:{agent_id}", self._cache_ttl)
    
    async def get_project_state(self, project_id: str) -> Optional[dict]:
        """Get project state from Redis."""
        if self.redis:
            data = await self.redis.get(f"project:state:{project_id}")
            if data:
                return json.loads(data)
        return None
    
    async def set_project_state(self, project_id: str, state: dict):
        """Set project state in Redis."""
        if self.redis:
            await self.redis.set(
                f"project:state:{project_id}",
                json.dumps(state),
                ex=self._cache_ttl
            )


# Request/Response Models
class AgentRegisterRequest(BaseModel):
    agent_id: str
    name: str
    capabilities: Dict[str, Any]


class TaskRequest(BaseModel):
    agent_id: str
    task_type: Optional[str] = None


class TaskProgressReport(BaseModel):
    agent_id: str
    task_id: str
    progress: int
    status: str
    message: Optional[str] = None


class BlockerReport(BaseModel):
    agent_id: str
    task_id: str
    blocker_type: str
    description: str
    attempted_solutions: Optional[List[str]] = None


# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Startup
    logger.info("Starting PM Agent Scaled Server...")
    
    # Initialize Redis connection
    try:
        app.state.redis = await redis.from_url(
            settings.get('redis_url', 'redis://localhost:6379'),
            encoding="utf-8",
            decode_responses=False
        )
        await app.state.redis.ping()
        logger.info("Connected to Redis")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Running without Redis.")
        app.state.redis = None
    
    # Initialize managers
    app.state.connection_manager = ConnectionManager(app.state.redis)
    app.state.state_manager = StateManager(app.state.redis)
    app.state.pm_agent_state = PMAgentState()
    app.state.agent_tools = AgentTools(app.state.pm_agent_state)
    
    yield
    
    # Shutdown
    logger.info("Shutting down PM Agent Scaled Server...")
    
    # Close all WebSocket connections
    for agent_id in list(app.state.connection_manager.active_connections.keys()):
        await app.state.connection_manager.disconnect(agent_id)
    
    # Close Redis connection
    if app.state.redis:
        await app.state.redis.close()


# Create FastAPI app
app = FastAPI(
    title="PM Agent Scaled Server",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get('cors_origins', ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# HTTP Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "connections": len(app.state.connection_manager.active_connections),
        "redis": "connected" if app.state.redis else "disconnected"
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain")


@app.post("/api/v1/agents/register")
@request_duration.time()
async def register_agent(request: AgentRegisterRequest):
    """Register a new agent."""
    try:
        result = await app.state.agent_tools.register_agent(
            request.agent_id,
            request.name,
            request.capabilities
        )
        
        # Store in state manager
        await app.state.state_manager.set_agent_status(request.agent_id, {
            "id": request.agent_id,
            "name": request.name,
            "capabilities": request.capabilities,
            "status": "idle",
            "registered_at": datetime.utcnow().isoformat()
        })
        
        return {"success": True, "agent_id": request.agent_id}
    except Exception as e:
        logger.error(f"Error registering agent {request.agent_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/tasks/request")
@request_duration.time()
async def request_task(request: TaskRequest):
    """Request next task for an agent."""
    try:
        task = await app.state.agent_tools.request_next_task(request.agent_id)
        
        if task:
            # Update agent status
            status = await app.state.state_manager.get_agent_status(request.agent_id) or {}
            status["status"] = "working"
            status["current_task"] = task["id"]
            await app.state.state_manager.set_agent_status(request.agent_id, status)
            
            return {"success": True, "task": task}
        else:
            return {"success": True, "task": None}
    except Exception as e:
        logger.error(f"Error requesting task for agent {request.agent_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/tasks/progress")
@request_duration.time()
async def report_progress(report: TaskProgressReport):
    """Report task progress."""
    try:
        await app.state.agent_tools.report_task_progress(
            report.agent_id,
            report.task_id,
            report.progress,
            report.status,
            report.message
        )
        
        # Broadcast progress to other agents if needed
        await app.state.connection_manager.broadcast({
            "type": "task_progress",
            "agent_id": report.agent_id,
            "task_id": report.task_id,
            "progress": report.progress
        }, exclude={report.agent_id})
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Error reporting progress: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/tasks/blocker")
@request_duration.time()
async def report_blocker(report: BlockerReport):
    """Report a blocker."""
    try:
        suggestions = await app.state.agent_tools.report_blocker(
            report.agent_id,
            report.task_id,
            report.blocker_type,
            report.description,
            report.attempted_solutions
        )
        
        return {"success": True, "suggestions": suggestions}
    except Exception as e:
        logger.error(f"Error reporting blocker: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/agents/{agent_id}/status")
async def get_agent_status(agent_id: str):
    """Get agent status."""
    status = await app.state.state_manager.get_agent_status(agent_id)
    if not status:
        raise HTTPException(status_code=404, detail="Agent not found")
    return status


@app.get("/api/v1/project/status")
async def get_project_status():
    """Get overall project status."""
    try:
        status = await app.state.agent_tools.get_project_status()
        return status
    except Exception as e:
        logger.error(f"Error getting project status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket Endpoint
@app.websocket("/ws/agent/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    """WebSocket endpoint for real-time agent communication."""
    try:
        # Connect the agent
        await app.state.connection_manager.connect(agent_id, websocket)
        
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": f"Agent {agent_id} connected successfully"
        })
        
        # Listen for messages
        while True:
            data = await websocket.receive_json()
            messages_received.inc()
            
            # Handle different message types
            message_type = data.get("type")
            
            if message_type == "register":
                await register_agent(AgentRegisterRequest(
                    agent_id=agent_id,
                    name=data.get("name", agent_id),
                    capabilities=data.get("capabilities", {})
                ))
                await websocket.send_json({"type": "registered", "agent_id": agent_id})
            
            elif message_type == "request_task":
                task = await app.state.agent_tools.request_next_task(agent_id)
                await websocket.send_json({"type": "task_assignment", "task": task})
            
            elif message_type == "report_progress":
                await app.state.agent_tools.report_task_progress(
                    agent_id,
                    data["task_id"],
                    data["progress"],
                    data.get("status", "in_progress"),
                    data.get("message")
                )
                await websocket.send_json({"type": "progress_acknowledged"})
            
            elif message_type == "report_blocker":
                suggestions = await app.state.agent_tools.report_blocker(
                    agent_id,
                    data["task_id"],
                    data["blocker_type"],
                    data["description"],
                    data.get("attempted_solutions")
                )
                await websocket.send_json({
                    "type": "blocker_suggestions",
                    "suggestions": suggestions
                })
            
            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })
                
    except WebSocketDisconnect:
        await app.state.connection_manager.disconnect(agent_id)
    except Exception as e:
        logger.error(f"WebSocket error for agent {agent_id}: {e}")
        await app.state.connection_manager.disconnect(agent_id)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host=settings.get('host', '0.0.0.0'),
        port=settings.get('port', 8000),
        log_level=settings.get('log_level', 'info'),
        # Enable multiple workers for production
        workers=settings.get('workers', 1)
    )