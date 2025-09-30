# Marcus MCP Server System

## Overview

The Marcus MCP (Model Context Protocol) Server is the core communication layer that enables AI agents to interact with the Marcus project management system. It exposes a rich set of tools through the MCP protocol, allowing both human users and autonomous agents to coordinate project work, manage tasks, and track progress.

## System Architecture

### Core Components

#### 1. MarcusServer (`src/marcus_mcp/server.py`)
The main MCP server implementation that orchestrates all Marcus functionality:

```python
class MarcusServer:
    """Marcus MCP Server with modularized architecture"""
```

**Key Features:**
- Multi-project support with project context switching
- Configurable enhancement systems (Events, Context, Memory, Visualization)
- Real-time logging and event publishing
- Assignment persistence and locking mechanisms
- Integration with multiple kanban providers (Planka, Linear, GitHub)

**Initialization Layers:**
1. **Configuration Layer**: Loads Marcus config and feature flags
2. **Project Management**: Initializes project registry and context manager
3. **Provider Integration**: Connects to kanban services
4. **Enhancement Systems**: Optionally enables Events, Context, Memory systems
5. **Monitoring**: Sets up assignment monitoring and visualization

#### 2. Tool Handler System (`src/marcus_mcp/handlers.py`)
Centralized tool registration and routing with role-based access control:

```python
def get_tool_definitions(role: str = "agent") -> List[types.Tool]:
    """Return list of available tool definitions for MCP based on role."""
```

**Role-Based Tool Access:**
- **Agent Role**: Limited to essential task and coordination tools
- **Human Role**: Full access including project management and pipeline tools

#### 3. Modular Tool Architecture (`src/marcus_mcp/tools/`)
Tools are organized into specialized modules:

- **`agent.py`**: Agent registration and status management
- **`task.py`**: Task assignment, progress tracking, and blocker reporting
- **`project.py`**: Project status and metrics
- **`context.py`**: Decision logging and task context retrieval
- **`nlp.py`**: Natural language project creation
- **`system.py`**: Health checks and diagnostics
- **`project_management.py`**: Multi-project operations
- **`pipeline.py`**: Pipeline enhancement tools

## Position in Marcus Workflow

The MCP server sits at the heart of the typical Marcus workflow:

```
create_project → register_agent → request_next_task → report_progress → report_blocker → finish_task
       ↓              ↓                ↓                   ↓              ↓            ↓
   NLP Tools    Agent Tools      Task Tools        Task Tools    Blocker Tools  Task Tools
```

### Workflow Integration Points

1. **Project Creation Phase**
   - `create_project`: Uses NLP to break down requirements into tasks
   - Integrates with pipeline visualization to track creation flow
   - Supports complexity levels (prototype/standard/enterprise)

2. **Agent Registration Phase**
   - `register_agent`: Records agent capabilities and availability
   - Creates worker status tracking
   - Logs registration events for visualization

3. **Task Assignment Phase**
   - `request_next_task`: AI-powered optimal task matching
   - Contextual instructions with dependency awareness
   - Implementation context for GitHub projects

4. **Execution Phase**
   - `report_task_progress`: Real-time progress tracking
   - Code analysis integration for completed work
   - Memory system learning from outcomes

5. **Problem Resolution Phase**
   - `report_blocker`: AI-powered blocker analysis and suggestions
   - Automatic task status updates and documentation

## What Makes This System Special

### 1. **Tiered Instruction System**
The task assignment builds context-aware instructions in layers:

```python
def build_tiered_instructions(
    base_instructions: str,
    task: Task,
    context_data: Optional[Dict[str, Any]],
    dependency_awareness: Optional[str],
    predictions: Optional[Dict[str, Any]],
) -> str:
```

**Instruction Layers:**
- **Layer 1**: Base AI-generated instructions
- **Layer 2**: Implementation context from previous work
- **Layer 3**: Dependency awareness for downstream impact
- **Layer 4**: Decision logging prompts for high-impact tasks
- **Layer 5**: AI predictions and risk warnings
- **Layer 6**: Task-specific guidance based on labels

### 2. **AI-Powered Task Assignment**
Advanced matching algorithm considers:
- Agent skills vs task requirements
- Historical performance patterns
- Current workload distribution
- Task dependencies and priorities
- Predicted completion times and risks

### 3. **Enhanced Context System**
When enabled, provides:
- Cross-task dependency tracking
- Implementation pattern reuse
- Architectural decision logging
- Future impact analysis

### 4. **Memory and Learning**
Optional memory system that:
- Learns from task completion patterns
- Predicts blockers and completion times
- Analyzes cascade effects of delays
- Tracks agent performance trajectories

### 5. **Real-time Pipeline Visualization**
Tracks project creation and execution flows:
```python
# Pipeline tracking during project creation
state.pipeline_visualizer.start_flow(flow_id, project_name)
state.pipeline_visualizer.add_event(...)
```

## Technical Implementation Details

### MCP Protocol Integration

The server implements the full MCP specification:

```python
@self.server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """Return list of available tools"""
    role = "agent"  # Role-based tool filtering
    return get_tool_definitions(role)

@self.server.call_tool()
async def handle_call_tool(name: str, arguments: Optional[Dict[str, Any]]) -> List[types.TextContent]:
    """Handle tool calls"""
    return await handle_tool_call(name, arguments, self)
```

### Error Handling Framework
Uses Marcus Error Framework for robust error handling:

```python
from src.core.error_framework import KanbanIntegrationError, ErrorContext

try:
    await operation()
except Exception as e:
    raise KanbanIntegrationError(
        board_name=self.provider,
        operation="operation_name",
        context=ErrorContext(...)
    )
```

### Serialization and Data Safety
Custom serialization for MCP responses:

```python
def serialize_for_mcp(data: Any) -> Any:
    """Serialize data for MCP response, handling enums and dataclasses."""
    return json.loads(json.dumps(data, cls=MarcusJSONEncoder))
```

### Assignment Concurrency Control
Thread-safe task assignment with locking:

```python
async def find_optimal_task_for_agent(agent_id: str, state: Any) -> Optional[Task]:
    async with state.assignment_lock:
        # Prevent race conditions in task assignment
        state.tasks_being_assigned.add(optimal_task.id)
```

## Simple vs Complex Task Handling

### Simple Tasks (Prototype Projects)
- **Task Count**: 3-8 tasks
- **Instructions**: Basic AI-generated guidance
- **Dependencies**: Minimal cross-task coordination
- **Tools Used**: Core agent, task, and project tools

### Complex Tasks (Enterprise Projects)
- **Task Count**: 25+ tasks
- **Instructions**: Full tiered instruction system
- **Dependencies**: Rich context with dependency awareness
- **Tools Used**: Full tool suite including context, memory, and pipeline tools
- **Features**:
  - Architectural decision logging
  - Cascade effect analysis
  - Performance trajectory tracking
  - Implementation pattern reuse

## Board-Specific Considerations

### Planka Integration
- Direct API integration with task creation/updates
- Real-time comment posting for decisions and blockers
- Progress tracking through task status updates

### GitHub Integration
- **Code Analysis**: Analyzes completed work for patterns
- **Implementation Context**: Provides previous implementations to new tasks
- **Branch Management**: Each agent works on dedicated branches
- **Commit Integration**: Links commits to tasks via task IDs

### Linear Integration
- API-based task management
- Rich label and project support
- Advanced filtering and querying capabilities

## Seneca Integration

The MCP server is designed to work seamlessly with Seneca, Marcus's deployment companion:

### Service Discovery
```python
service_info = register_marcus_service(
    mcp_command=sys.executable + " " + " ".join(sys.argv),
    log_dir=str(Path(server.realtime_log.name).parent),
    project_name=current_project,
    provider=server.provider,
)
```

### Client Type Detection
```python
# Automatic client identification
if "seneca" in echo_lower:
    client_type = "seneca"
elif "claude" in echo_lower or "desktop" in echo_lower:
    client_type = "claude_desktop"
```

### Real-time Communication
- JSON Lines logging for real-time updates
- Event publishing to visualization systems
- Service registration for discovery

## Pros and Cons

### Advantages

1. **Modular Architecture**: Clean separation of concerns across tool modules
2. **Role-Based Security**: Different tool access levels for agents vs humans
3. **Enhanced Context**: Rich task context with dependency awareness
4. **AI-Powered Assignment**: Intelligent task matching and prediction
5. **Multi-Provider Support**: Works with different kanban systems
6. **Real-time Monitoring**: Live project visualization and tracking
7. **Extensible Design**: Easy to add new tools and enhancements
8. **Error Resilience**: Comprehensive error handling and recovery

### Disadvantages

1. **Complexity**: Many optional systems can be overwhelming
2. **Configuration Overhead**: Requires careful setup of feature flags
3. **Resource Usage**: Memory and context systems consume additional resources
4. **Learning Curve**: Rich instruction system requires understanding
5. **Dependency Chains**: Many interconnected components can fail
6. **Performance Impact**: AI analysis adds latency to task assignment

## Why This Approach Was Chosen

### 1. **MCP Protocol Standardization**
- Industry-standard protocol for AI tool communication
- Better than custom APIs for agent integration
- Compatible with Claude Desktop and other MCP clients

### 2. **Modular Tool Design**
- Easier to maintain and test individual tool categories
- Clear separation of agent vs human capabilities
- Allows selective feature enablement

### 3. **Context-Aware Instructions**
- Addresses the "blank page" problem for agents
- Provides just enough context without overwhelming
- Scales from simple to complex projects

### 4. **AI-Enhanced Assignment**
- Better task-agent matching than simple rules
- Learns from historical patterns
- Predicts and prevents common issues

## Future Evolution

### Planned Enhancements

1. **Advanced Role Management**
   - Fine-grained permissions per agent type
   - Dynamic role assignment based on capabilities
   - Team-based access controls

2. **Enhanced AI Integration**
   - Real-time code quality analysis
   - Automated code review suggestions
   - Intelligent refactoring recommendations

3. **Cross-Project Learning**
   - Pattern transfer between similar projects
   - Best practice recommendations
   - Template project generation

4. **Advanced Visualization**
   - 3D project topology visualization
   - Real-time collaboration maps
   - Predictive timeline analysis

5. **Multi-Modal Communication**
   - Voice command integration
   - Visual task description support
   - Diagram-based project planning

### Scalability Improvements

1. **Distributed Architecture**
   - Multiple MCP server instances
   - Load balancing for large teams
   - Federated project management

2. **Performance Optimization**
   - Caching layers for frequent operations
   - Async processing for heavy computations
   - Database optimization for large projects

3. **Enterprise Features**
   - SSO integration
   - Audit logging and compliance
   - Advanced reporting and analytics

## Integration Examples

### Human User Workflow
```bash
# List available projects
marcus list_projects

# Switch to a project
marcus switch_project --project_id "web-app-2024"

# Create a new feature
marcus create_project --description "Add user authentication system"
```

### Agent Workflow
```python
# Agent connects and registers
await client.call_tool("register_agent", {
    "agent_id": "backend-dev-001",
    "name": "Backend Developer",
    "role": "Backend Developer",
    "skills": ["Python", "FastAPI", "PostgreSQL"]
})

# Request next task
task = await client.call_tool("request_next_task", {
    "agent_id": "backend-dev-001"
})

# Report progress
await client.call_tool("report_task_progress", {
    "agent_id": "backend-dev-001",
    "task_id": task["task"]["id"],
    "status": "completed",
    "progress": 100,
    "message": "Authentication system implemented with JWT tokens"
})
```

## Monitoring and Debugging

### Real-time Logs
All MCP interactions are logged in JSON Lines format:
```json
{"timestamp": "2024-07-14T10:30:00Z", "type": "task_assignment", "agent_id": "dev-001", "task_id": "auth-123"}
```

### Health Checks
Built-in diagnostics for system health:
```python
# Check assignment system health
health = await client.call_tool("check_assignment_health", {})
```

### Pipeline Visualization
Real-time flow tracking through the UI at `http://localhost:8080`

The Marcus MCP Server represents a sophisticated yet practical approach to AI-human collaboration in software development, providing the tools and intelligence needed for autonomous development teams while maintaining human oversight and control.
