# Marcus Architecture

## System Design

Marcus implements a dual MCP (Model Context Protocol) architecture, serving as both a server and client to enable seamless coordination between AI workers and project management tools.

```{note}
For a comprehensive visual guide to the complete system architecture, see [System Architecture Overview](system_architecture.md).
For detailed information about the AI Engine, see [AI Engine Comprehensive Guide](ai_engine_guide.md).
```

## Core Components

### 1. MCP Server (Worker Interface)
Provides tools for worker agents to interact with the project management system.

```python
# Key server tools exposed to workers:
- register_agent        # Worker registration
- request_next_task    # Task assignment
- report_task_progress # Progress updates
- report_blocker       # Blocker reporting
- get_project_status   # Project visibility
- get_agent_status     # Agent status check
```

### 2. MCP Client (Kanban Interface)
Connects to Kanban MCP server to manage boards, tasks, and progress.

```python
# Kanban MCP tools used:
- mcp_kanban_project_board_manager  # Board management
- mcp_kanban_card_manager          # Task CRUD operations
- mcp_kanban_list_manager          # List management
- mcp_kanban_comment_manager       # Progress comments
- mcp_kanban_label_manager         # Task labeling
```

### 3. AI Analysis Engine
Leverages Claude for intelligent task analysis and instruction generation.

```python
# AI capabilities:
- Task instruction generation
- Blocker resolution suggestions
- Task-to-agent matching scores
- Project health analysis
```

## Data Models

### Task Assignment
```python
@dataclass
class TaskAssignment:
    task_id: str
    task_name: str
    description: str
    instructions: str  # AI-generated
    estimated_hours: float
    priority: Priority
    dependencies: List[str]
    assigned_to: str
    assigned_at: datetime
    due_date: Optional[datetime]
```

### Worker Status
```python
@dataclass
class WorkerStatus:
    worker_id: str
    name: str
    role: str
    current_tasks: List[str]
    completed_tasks_count: int
    capacity: float
    skills: List[str]
    performance_score: float
```

## Communication Flow

### 1. Worker Registration Flow
```
Worker Agent ──register_agent──► Marcus
                                     │
                                     ├─► Create WorkerStatus
                                     │
                                     └─► Return confirmation
```

### 2. Task Assignment Flow
```
Worker Agent ──request_next_task──► Marcus
                                        │
                                        ├─► Query Kanban MCP
                                        │
                                        ├─► Analyze available tasks
                                        │
                                        ├─► Generate instructions (AI)
                                        │
                                        ├─► Update Kanban board
                                        │
                                        └─► Return TaskAssignment
```

### 3. Progress Reporting Flow
```
Worker Agent ──report_progress──► Marcus
                                      │
                                      ├─► Add comment to Kanban
                                      │
                                      ├─► Update task status
                                      │
                                      └─► Acknowledge report
```

## Configuration Architecture

### Environment Configuration
```bash
# Kanban MCP Connection
PLANKA_BASE_URL=http://localhost:3333
PLANKA_AGENT_EMAIL=demo@demo.demo
PLANKA_AGENT_PASSWORD=demo

# AI Configuration
ANTHROPIC_API_KEY=your-api-key
```

### Project Configuration
```json
{
  "project_id": "1533678301472621705",
  "board_id": "1533822098756076745",
  "project_name": "Task Master Test",
  "auto_find_board": true,
  "planka": {
    "base_url": "http://localhost:3333",
    "email": "demo@demo.demo",
    "password": "demo"
  }
}
```

## Deployment Architecture

### Local Development
```
┌─────────────────┐
│  Marcus MVP   │
│  (Python)       │
├─────────────────┤
│ MCP Server:8765 │
└────────┬────────┘
         │
    MCP Protocol
         │
┌────────▼────────┐
│  Worker Agents  │
│  (Various)      │
└─────────────────┘
```

### Production Deployment
```
┌─────────────────────┐
│    Marcus         │
│  Container/Service  │
├─────────────────────┤
│ • Auto-scaling      │
│ • Health checks     │
│ • Metric export     │
└──────────┬──────────┘
           │
     Load Balancer
           │
    ┌──────┴──────┬──────────┐
    │             │          │
Worker Pool 1  Worker Pool 2  Worker Pool N
```

## Security Architecture

### Authentication Layers
1. **Worker-to-PM**: Token-based authentication (future)
2. **PM-to-Kanban**: Planka credentials
3. **PM-to-AI**: API key authentication

### Data Protection
- Sensitive data never logged
- Credentials stored in environment variables
- Secure communication channels (HTTPS in production)

## Scalability Considerations

### Horizontal Scaling
- Multiple Marcus instances can manage different projects
- Worker agents can be distributed across machines
- Kanban MCP can be load-balanced

### Performance Optimization
- Async operations throughout
- Connection pooling for Kanban MCP
- Caching for frequently accessed data
- Batch operations where possible