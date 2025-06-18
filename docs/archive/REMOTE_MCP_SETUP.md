# 🌐 PM Agent Remote MCP Server Setup

## Overview

This guide explains how to set up PM Agent as a remote MCP server using SSE (Server-Sent Events) transport, allowing AI agents to connect from anywhere while keeping sensitive services (like Planka) isolated.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Claude/AI      │────▶│  PM Agent MCP    │────▶│ Kanban Provider │
│  (Remote)       │ SSE │  (Public)        │     │ (Private)       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              Docker                 - GitHub (API)
                                                    - Linear (API)
                                                    - Planka (Local)
```

## 🚀 Quick Start with Docker

### 1. Create SSE-enabled PM Agent Server

Create `pm_agent_sse_server.py`:

```python
"""
PM Agent SSE Server - Remote MCP access via Server-Sent Events
"""
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
import uvicorn
import os
from dotenv import load_dotenv

# Import our PM Agent components
from pm_agent_mcp_server_v2 import (
    state, register_agent, request_next_task, 
    report_task_progress, report_blocker,
    get_project_status, get_agent_status,
    list_registered_agents, ping
)

load_dotenv()

app = FastAPI(title="PM Agent Remote MCP Server")
security = HTTPBearer()

# Session storage
sessions: Dict[str, Dict[str, Any]] = {}

# Simple token validation (replace with proper auth in production)
VALID_TOKENS = os.getenv("MCP_AUTH_TOKENS", "").split(",")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify bearer token"""
    if not VALID_TOKENS or credentials.credentials not in VALID_TOKENS:
        raise HTTPException(status_code=403, detail="Invalid authentication token")
    return credentials.credentials

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "pm-agent-sse"}

@app.get("/sse")
async def sse_endpoint(token: str = Depends(verify_token)):
    """SSE endpoint for MCP connection"""
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "created": datetime.now(),
        "token": token,
        "active": True
    }
    
    async def event_generator():
        # Send initial endpoint
        yield {
            "event": "endpoint",
            "data": f"/sse/messages?session_id={session_id}"
        }
        
        # Keep connection alive
        while sessions.get(session_id, {}).get("active", False):
            await asyncio.sleep(30)
            yield {
                "event": "ping",
                "data": json.dumps({"timestamp": datetime.now().isoformat()})
            }
    
    return EventSourceResponse(event_generator())

@app.post("/sse/messages")
async def handle_messages(request: Request, session_id: str):
    """Handle MCP messages"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Invalid session")
    
    try:
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})
        
        # Route to appropriate handler
        if method == "initialize":
            response = {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": True},
                    "prompts": {"listChanged": False},
                    "resources": {"listChanged": False}
                },
                "serverInfo": {
                    "name": "pm-agent-remote",
                    "version": "1.0.0"
                }
            }
        
        elif method == "tools/list":
            # Return our available tools
            response = {
                "tools": [
                    {
                        "name": "register_agent",
                        "description": "Register a new agent with the PM system",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "agent_id": {"type": "string"},
                                "name": {"type": "string"},
                                "role": {"type": "string"},
                                "skills": {"type": "array", "items": {"type": "string"}}
                            },
                            "required": ["agent_id", "name", "role"]
                        }
                    },
                    {
                        "name": "request_next_task",
                        "description": "Request the next optimal task",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "agent_id": {"type": "string"}
                            },
                            "required": ["agent_id"]
                        }
                    },
                    # Add other tools here...
                ]
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            # Call the appropriate PM Agent function
            if tool_name == "register_agent":
                result = await register_agent(**arguments)
            elif tool_name == "request_next_task":
                result = await request_next_task(**arguments)
            elif tool_name == "report_task_progress":
                result = await report_task_progress(**arguments)
            elif tool_name == "report_blocker":
                result = await report_blocker(**arguments)
            elif tool_name == "get_project_status":
                result = await get_project_status()
            elif tool_name == "get_agent_status":
                result = await get_agent_status(**arguments)
            elif tool_name == "list_registered_agents":
                result = await list_registered_agents()
            elif tool_name == "ping":
                result = await ping(**arguments)
            else:
                result = {"error": f"Unknown tool: {tool_name}"}
            
            response = {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2)
                    }
                ]
            }
        
        else:
            response = {"error": f"Unknown method: {method}"}
        
        # Add JSON-RPC fields
        return {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": response
        }
        
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": body.get("id", 1),
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }

@app.delete("/sessions/{session_id}")
async def close_session(session_id: str, token: str = Depends(verify_token)):
    """Close an SSE session"""
    if session_id in sessions:
        sessions[session_id]["active"] = False
        del sessions[session_id]
    return {"status": "closed"}

if __name__ == "__main__":
    # Get port from environment or default
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"Starting PM Agent SSE Server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
```

### 2. Enhanced Docker Setup

Create `Dockerfile.sse`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install SSE dependencies
RUN pip install fastapi uvicorn sse-starlette python-multipart

# Copy application
COPY . .

# Create directories
RUN mkdir -p logs/conversations logs/raw

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose SSE port
EXPOSE 8000

# Run SSE server
CMD ["python", "pm_agent_sse_server.py"]
```

### 3. Docker Compose for Remote Access

Update `docker-compose.yml`:

```yaml
version: '3.8'

services:
  # PM Agent SSE Server (Public-facing)
  pm-agent-sse:
    build:
      context: .
      dockerfile: Dockerfile.sse
    container_name: pm-agent-sse-server
    ports:
      - "8000:8000"  # Expose for remote access
    environment:
      # Authentication tokens (comma-separated)
      - MCP_AUTH_TOKENS=${MCP_AUTH_TOKENS:-token1,token2,token3}
      
      # Kanban provider
      - KANBAN_PROVIDER=${KANBAN_PROVIDER:-github}
      
      # Provider credentials (kept secure in container)
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - GITHUB_OWNER=${GITHUB_OWNER}
      - GITHUB_REPO=${GITHUB_REPO}
      - LINEAR_API_KEY=${LINEAR_API_KEY}
      - LINEAR_TEAM_ID=${LINEAR_TEAM_ID}
      
      # AI configuration
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    networks:
      - pm-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Nginx reverse proxy with SSL (optional but recommended)
  nginx:
    image: nginx:alpine
    container_name: pm-agent-nginx
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - pm-agent-sse
    networks:
      - pm-network
    profiles:
      - production

  # Local Planka (only accessible within Docker network)
  planka:
    image: planka/planka:latest
    container_name: pm-agent-planka
    environment:
      - DATABASE_URL=postgresql://planka:planka@planka-db/planka
      - SECRET_KEY=${PLANKA_SECRET_KEY:-your-secret-key}
    volumes:
      - planka-data:/app/data
    networks:
      - pm-network
    profiles:
      - planka
    # NO PORTS EXPOSED - only accessible within Docker network

  planka-db:
    image: postgres:14-alpine
    container_name: pm-agent-planka-db
    environment:
      - POSTGRES_DB=planka
      - POSTGRES_USER=planka
      - POSTGRES_PASSWORD=planka
    volumes:
      - planka-db-data:/var/lib/postgresql/data
    networks:
      - pm-network
    profiles:
      - planka

networks:
  pm-network:
    driver: bridge

volumes:
  planka-data:
  planka-db-data:
```

### 4. Nginx Configuration (nginx.conf)

```nginx
events {
    worker_connections 1024;
}

http {
    upstream pm-agent {
        server pm-agent-sse:8000;
    }

    server {
        listen 443 ssl;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        # SSE specific settings
        location /sse {
            proxy_pass http://pm-agent;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            proxy_buffering off;
            proxy_cache off;
            
            # SSE headers
            proxy_set_header Accept-Encoding gzip;
            proxy_read_timeout 86400;
            
            # CORS headers (adjust as needed)
            add_header Access-Control-Allow-Origin "*";
            add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
            add_header Access-Control-Allow-Headers "Authorization, Content-Type";
        }

        location / {
            proxy_pass http://pm-agent;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }

    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }
}
```

### 5. Client Configuration

For Claude Desktop or other MCP clients:

```json
{
  "mcpServers": {
    "pm-agent-remote": {
      "url": "https://your-domain.com/sse",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer your-auth-token"
      }
    }
  }
}
```

For local development:

```json
{
  "mcpServers": {
    "pm-agent-local": {
      "url": "http://localhost:8000/sse",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer token1"
      }
    }
  }
}
```

## 🔒 Security Considerations

1. **Authentication**: The example uses bearer tokens. For production, implement:
   - OAuth 2.0 with PKCE
   - JWT tokens with expiration
   - API key management per user

2. **Network Isolation**: 
   - Planka remains completely internal (no exposed ports)
   - Only PM Agent SSE server is exposed
   - All kanban operations go through PM Agent

3. **SSL/TLS**: Always use HTTPS in production

4. **Rate Limiting**: Add rate limiting to prevent abuse

## 🚀 Deployment Options

### Local Development
```bash
docker-compose up pm-agent-sse
```

### Production with SSL
```bash
docker-compose --profile production up -d
```

### With Local Planka
```bash
docker-compose --profile planka up -d
```

## 📊 Monitoring

Check SSE connections:
```bash
# View active sessions
curl -H "Authorization: Bearer token1" http://localhost:8000/sessions

# Health check
curl http://localhost:8000/health
```

## 🎯 Benefits

1. **Remote Access**: AI agents can connect from anywhere
2. **Security**: Sensitive services (Planka) stay isolated
3. **Flexibility**: Support multiple kanban providers
4. **Scalability**: Can handle multiple concurrent connections
5. **Standards-based**: Uses SSE transport per MCP spec

This setup allows PM Agent to be accessed remotely while keeping Planka (or any other sensitive service) completely isolated within the Docker network.