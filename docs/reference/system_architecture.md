# Marcus System Architecture Reference

> **Type**: Component  
> **Version**: 2.0.0  
> **Last Updated**: 2025-06-25

## Overview

This document provides a comprehensive technical reference for the Marcus system architecture, detailing all components, their interactions, data flows, and integration points.

## Synopsis

```
┌─────────────────┐     MCP Protocol      ┌──────────────────┐
│  Worker Agents  │◄────────────────────►│    Marcus      │
│  (Claude, etc)  │                       │   MCP Server     │
└─────────────────┘                       └────────┬─────────┘
                                                   │
                                          ┌────────▼─────────┐
                                          │  Kanban Provider │
                                          │ (Planka/GitHub)  │
                                          └──────────────────┘
```

## Description

Marcus is a sophisticated project management system that orchestrates autonomous AI agents to complete software development tasks. The system uses the Model Context Protocol (MCP) for agent communication, integrates with various kanban providers for task management, and employs AI for intelligent task assignment and blocker resolution.

## Core Components

### Marcus MCP Server

The central orchestration component that manages all agent interactions.

| Component | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `Server` | class | Yes | - | Main MCP server instance handling all protocol communication |
| `PMAgentState` | class | Yes | - | Global state manager for agents, tasks, and project status |
| `KanbanInterface` | interface | Yes | - | Abstract interface for kanban provider integration |
| `AIAnalysisEngine` | class | Yes | - | AI-powered analysis for task instructions and blockers |

### Component Details

#### Server Component
```python
class Server:
    """MCP Protocol server implementation"""
    - Handles tool registration and invocation
    - Manages bidirectional communication
    - Implements protocol handshake
    - Provides error handling and recovery
```

Key responsibilities:
- Tool registration via `@server.list_tools()`
- Request handling via `@server.call_tool()`
- Protocol compliance and validation
- Connection lifecycle management

#### PMAgentState Component
```python
class PMAgentState:
    """Global state management"""
    - agent_tasks: Dict[str, TaskAssignment]
    - agent_status: Dict[str, WorkerStatus]
    - project_state: Optional[ProjectState]
    - project_tasks: List[Task]
```

State tracking includes:
- Active worker registrations
- Current task assignments
- Project progress metrics
- System health indicators

### Data Models

Core data structures used throughout the system:

#### Task Model
```python
@dataclass
class Task:
    id: str                          # Unique identifier
    name: str                        # Task title
    description: str                 # Detailed description
    status: TaskStatus              # Current status
    priority: Priority              # Urgency level
    assigned_to: Optional[str]      # Assigned worker ID
    estimated_hours: float          # Time estimate
    dependencies: List[str]         # Dependent task IDs
    labels: List[str]              # Skill/category tags
```

#### WorkerStatus Model
```python
@dataclass
class WorkerStatus:
    worker_id: str                  # Unique identifier
    name: str                       # Display name
    role: str                       # Job role
    current_tasks: List[Task]       # Active assignments
    skills: List[str]              # Technical skills
    capacity: int                   # Weekly hours
    performance_score: float        # Performance metric
```

### Integration Layer

#### Kanban Providers

Supported providers with their integration requirements:

| Provider | Protocol | Authentication | Features |
|----------|----------|----------------|----------|
| Planka | REST API | Username/Password | Full CRUD, Comments, Real-time |
| GitHub | GraphQL/REST | Personal Token | Issues, Projects, Code Context |
| Trello | REST API | API Key/Token | Cards, Lists, Webhooks |

#### Provider Factory
```python
class KanbanFactory:
    @staticmethod
    def create_default() -> KanbanInterface:
        """Creates appropriate provider based on environment"""
        provider = os.getenv('KANBAN_PROVIDER', 'planka')
        return factory_map[provider]()
```

### AI Analysis Engine

Intelligent task management powered by Claude AI:

#### Core Functions
```python
class AIAnalysisEngine:
    async def generate_task_instructions(
        task: Task,
        worker: WorkerStatus,
        context: Optional[Dict]
    ) -> str:
        """Generate detailed, personalized instructions"""
        
    async def analyze_blocker(
        description: str,
        task: Task,
        worker: WorkerStatus,
        severity: str
    ) -> str:
        """Provide actionable blocker solutions"""
```

#### AI Features
- Context-aware instruction generation
- Skill-based task matching
- Intelligent blocker analysis
- Performance optimization suggestions

## Data Flow

### Task Assignment Flow

```
1. Agent Registration
   └─> WorkerStatus created
       └─> Skills indexed

2. Task Request
   └─> refresh_project_state()
       └─> Fetch tasks from kanban
           └─> find_optimal_task_for_agent()
               └─> Score by skills + priority
                   └─> AI generates instructions
                       └─> TaskAssignment created

3. Progress Updates
   └─> Update kanban status
       └─> Update progress metrics
           └─> Log to conversation history
```

### Blocker Resolution Flow

```
1. Blocker Reported
   └─> Severity assessment
       └─> AI analysis triggered
           └─> Context gathering
               └─> Solution generation
                   └─> Kanban comment added
                       └─> Agent notified
```

## Communication Protocol

### MCP Message Format

Request:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "register_agent",
    "arguments": {
      "agent_id": "backend-dev-001",
      "name": "Backend Developer",
      "role": "Backend Developer",
      "skills": ["Python", "Django"]
    }
  },
  "id": 1
}
```

Response:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "message": "Agent registered successfully",
    "agent_id": "backend-dev-001"
  },
  "id": 1
}
```

### Protocol Handshake

```
Client → Server: Initialize
Server → Client: Capabilities
Client → Server: Tool Discovery
Server → Client: Tool List
Client → Server: Ready
```

## Logging and Monitoring

### Conversation Logger

Structured logging system for debugging and analytics:

```python
conversation_logger.log_worker_message(
    agent_id="backend-dev-001",
    direction="to_pm",
    message="Requesting next task",
    metadata={"timestamp": "2024-01-20T10:30:00Z"}
)
```

### Log Types
- Worker messages (bidirectional)
- PM decisions with rationale
- System state changes
- Kanban interactions
- Performance metrics

### Real-time Event Log

```json
{
  "timestamp": "2024-01-20T10:30:00Z",
  "type": "task_assignment",
  "worker_id": "backend-dev-001",
  "task_id": "task-123",
  "source": "pm_agent"
}
```

## Examples

### Basic Architecture Implementation
```python
# Initialize core components
server = Server("pm-agent")
state = PMAgentState()

# Register MCP tools
@server.list_tools()
async def handle_list_tools():
    return [/* tool definitions */]

# Handle tool calls
@server.call_tool()
async def handle_call_tool(name, arguments):
    if name == "register_agent":
        return await register_agent(**arguments)
```

### Advanced Integration Example
```python
# Custom kanban provider
class CustomKanbanProvider(KanbanInterface):
    async def connect(self):
        """Establish connection"""
        
    async def get_available_tasks(self) -> List[Task]:
        """Fetch unassigned tasks"""
        
    async def update_task(self, task_id: str, updates: Dict):
        """Update task status"""

# Register with factory
KanbanFactory.register("custom", CustomKanbanProvider)
```

### Real-World Deployment
```yaml
# docker-compose.yml
version: '3.8'
services:
  pm-agent:
    image: pm-agent:latest
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - KANBAN_PROVIDER=planka
    volumes:
      - ./logs:/app/logs
    ports:
      - "8080:8080"
    
  planka:
    image: ghcr.io/plankanban/planka:latest
    environment:
      - DATABASE_URL=postgresql://planka:planka@db/planka
    depends_on:
      - db
      
  db:
    image: postgres:14-alpine
    environment:
      - POSTGRES_DB=planka
      - POSTGRES_USER=planka
      - POSTGRES_PASSWORD=planka
```

## Performance Characteristics

### Scalability Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Max concurrent agents | 50 | Limited by kanban API rate limits |
| Task assignment time | <2s | Including AI instruction generation |
| State refresh interval | 15min | Configurable via monitoring_interval |
| Memory usage per agent | ~10MB | Includes task history and state |

### Optimization Strategies

1. **Caching**: Task and worker states cached for 5 minutes
2. **Batching**: Kanban updates batched when possible
3. **Connection pooling**: Reuse kanban API connections
4. **Async operations**: All I/O operations are non-blocking

## Security Architecture

### Authentication Flow
```
Worker Agent → MCP Server (No auth required)
MCP Server → Kanban Provider (API key/token)
MCP Server → AI Engine (API key)
```

### Security Measures
- API keys stored in environment variables
- No sensitive data in logs
- Workspace isolation for file access
- Rate limiting on all endpoints

## Error Handling

### Error Propagation
```
Kanban API Error
  └─> KanbanInterface catches
      └─> Returns error to PMAgentState
          └─> MCP Server formats error
              └─> Agent receives structured error
```

### Recovery Mechanisms
- Automatic retry with exponential backoff
- Graceful degradation on service failures
- State persistence across restarts
- Health check endpoints

## Notes

- The system is designed for horizontal scalability
- All components are stateless except PMAgentState
- Kanban provider can be switched without code changes
- AI model can be configured per deployment
- Supports both push and pull communication patterns

## Version History

| Version | Changes |
|---------|---------|
| 2.0.0 | Added workspace isolation and GitHub integration |
| 1.5.0 | Introduced plugin architecture for providers |
| 1.2.0 | Added real-time event streaming |
| 1.0.0 | Initial architecture with MCP support |

## See Also

- [MCP Tools API Reference](/reference/mcp_tools_api)
- [Configuration Guide](/reference/configuration_guide)
- [Deployment Guide](/how-to/deployment)
- [Kanban Provider Integration](/how-to/kanban_integration)