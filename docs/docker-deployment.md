# Docker Deployment Guide for PM Agent

## Why Docker for PM Agent?

While PM Agent uses MCP (Model Context Protocol) which communicates via stdio rather than network protocols, Docker still provides valuable benefits:

1. **Consistent Environment**: Ensures all dependencies are correctly installed
2. **Easy Deployment**: Single command to start PM Agent with all requirements
3. **Resource Management**: Control CPU and memory usage
4. **Isolation**: Keep PM Agent separate from system Python
5. **Scalability**: Easy to run multiple instances for different projects

## Current Architecture vs Docker

### Current (Direct Execution)
```
Worker Agents <--stdio--> PM Agent <--stdio--> Kanban MCP <--HTTP--> Planka
```

### With Docker
```
Worker Agents <--stdio--> PM Agent Container <--network--> Kanban MCP Container <--HTTP--> Planka
```

## Setting Up Board Configuration

### Method 1: Using Configure Script
```bash
# After creating a board in Planka, configure PM Agent:
python scripts/setup/configure_board.py YOUR_BOARD_ID

# Example with your board:
python scripts/setup/configure_board.py 1533859887128249584
```

### Method 2: Direct Configuration
Edit `config_pm_agent.json`:
```json
{
  "project_id": "1533678301472621705",
  "board_id": "1533859887128249584",
  "project_name": "Task Master Test",
  "auto_find_board": false,
  "planka": {
    "base_url": "http://localhost:3333",
    "email": "demo@demo.demo",
    "password": "demo"
  }
}
```

### Method 3: Environment Variables
```bash
export PM_AGENT_BOARD_ID="1533859887128249584"
export PM_AGENT_PROJECT_ID="1533678301472621705"
```

## Running PM Agent in Docker

### Quick Start
```bash
# Build the image
docker build -t pm-agent .

# Run with your configuration
docker run -it \
  -v $(pwd)/config_pm_agent.json:/app/config_pm_agent.json \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  pm-agent
```

### Using Docker Compose
```bash
# Create .env file
cat > .env << EOF
ANTHROPIC_API_KEY=your-key-here
PM_AGENT_BOARD_ID=1533859887128249584
PM_AGENT_PROJECT_ID=1533678301472621705
EOF

# Start PM Agent
docker-compose -f docker-compose.pm-agent.yml up -d

# View logs
docker-compose -f docker-compose.pm-agent.yml logs -f pm-agent
```

## Worker Agent Connection to Dockerized PM Agent

Since MCP uses stdio, connecting worker agents to a Dockerized PM Agent requires special handling:

### Option 1: Docker Exec (Recommended for Testing)
```python
# Worker agent connecting to Docker PM Agent
import subprocess

class DockerPMAgentConnection:
    def __init__(self, container_name="pm-agent"):
        self.container_name = container_name
    
    async def connect(self):
        # Execute inside the container
        process = await asyncio.create_subprocess_exec(
            "docker", "exec", "-i", self.container_name,
            "python", "pm_agent_mvp_fixed.py",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        return process
```

### Option 2: Network Bridge (Future Enhancement)
Create an MCP-over-HTTP bridge for network communication:
```python
# Future: MCP HTTP Bridge
class MCPHttpBridge:
    """Convert MCP stdio to HTTP for Docker networking"""
    def __init__(self, mcp_command, port=8765):
        self.mcp_command = mcp_command
        self.port = port
    
    async def start(self):
        # Bridge stdio MCP to HTTP endpoints
        # This would require protocol adaptation
```

## Why We Don't Use Docker by Default

1. **MCP Protocol Limitation**: MCP uses stdio (stdin/stdout) for communication, not network sockets. This makes containerization more complex for the server component.

2. **Development Workflow**: Direct execution is simpler for development and debugging.

3. **Worker Agent Complexity**: Worker agents would need to use `docker exec` or a bridge protocol to communicate with containerized PM Agent.

4. **Performance**: Direct execution has lower overhead than container communication.

## Future Docker Improvements

### 1. MCP Network Transport
```python
# Proposed: Network-enabled MCP
class NetworkMCPServer:
    def __init__(self, host="0.0.0.0", port=8765):
        self.server = await asyncio.start_server(
            self.handle_connection, host, port
        )
    
    async def handle_connection(self, reader, writer):
        # Adapt stdio protocol to network
```

### 2. All-in-One Container
```dockerfile
# Future: Combined PM Agent + Kanban MCP
FROM python:3.11-node:18

# Install both Python and Node.js dependencies
# Run both services with supervisor
```

### 3. Kubernetes Deployment
```yaml
# Future: K8s deployment for scale
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pm-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pm-agent
  template:
    spec:
      containers:
      - name: pm-agent
        image: pm-agent:latest
        env:
        - name: MCP_TRANSPORT
          value: "network"  # Future network transport
```

## Current Best Practice

For now, the recommended approach is:

1. **Development**: Run PM Agent directly for easy debugging
   ```bash
   python pm_agent_mvp_fixed.py
   ```

2. **Testing**: Use Docker for consistent environment
   ```bash
   docker-compose -f docker-compose.pm-agent.yml up
   ```

3. **Production**: Wait for network transport support or use process managers
   ```bash
   # Using supervisor or systemd
   sudo systemctl start pm-agent
   ```

## Troubleshooting Docker Issues

### Container Won't Start
```bash
# Check logs
docker logs pm-agent

# Common issues:
# - Missing ANTHROPIC_API_KEY
# - Can't connect to Planka
# - Invalid configuration
```

### Can't Connect to Planka
```bash
# If Planka is on host machine
- PLANKA_BASE_URL=http://host.docker.internal:3333

# If Planka is in Docker network
- PLANKA_BASE_URL=http://planka:3000
```

### Worker Agents Can't Connect
```bash
# Ensure container is running
docker ps | grep pm-agent

# Test connection
docker exec -it pm-agent python -c "print('PM Agent is accessible')"
```