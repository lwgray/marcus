# Marcus MCP Tools Overview

## How Claude Interacts with Marcus via MCP

Marcus operates as an MCP server that Claude connects to. The interaction happens through two layers of MCP tools:

### 1. Marcus MCP Tools (What Claude Calls)

These are the tools exposed by `marcus_mcp_server.py` that Claude directly uses:

```
📥 MARCUS TOOLS (Claude → Marcus)
├── register_agent           - Register a new agent with Marcus
├── request_next_task        - Request optimal task assignment for an agent  
├── report_task_progress     - Report progress on a task (25%, 50%, 75%, 100%)
├── report_blocker          - Report a blocker with description and severity
├── get_project_status      - Get overall project status and metrics
├── get_agent_status        - Get specific agent's current assignments
├── list_registered_agents  - List all registered agents and their status
├── ping                    - Health check
└── check_assignment_health - Check for stuck assignments or issues
```

### 2. Planka MCP Tools (What Marcus Uses Internally)

Marcus internally connects to the Planka MCP server to manage the actual kanban board:

```
📤 PLANKA TOOLS (Marcus → Planka)
├── mcp_kanban_project_board_manager
│   ├── get_projects        - List all projects
│   └── get_boards          - List boards in a project
├── mcp_kanban_list_manager
│   └── get_all             - Get all lists on a board
├── mcp_kanban_card_manager
│   ├── get_all             - Get all cards in a list
│   ├── create              - Create a new card (task)
│   ├── update              - Update card details
│   ├── move                - Move card between lists
│   └── add_labels          - Add labels to cards
└── mcp_kanban_comment_manager
    └── create              - Add comments to cards
```

## Real Interaction Flow

Here's how a typical natural language interaction works:

### Example: "I want to build a todo app"

```
1. USER → CLAUDE: "I want to build a todo app with React"

2. CLAUDE → MARCUS (MCP):
   - Calls: register_agent("claude-1", "Claude Assistant", "Full Stack")
   
3. MARCUS (Internal):
   - Detects empty board → Creator Mode
   - Generates tasks from template
   - Uses Planka MCP tools:
     * mcp_kanban_card_manager.create() × 20 tasks
     * mcp_kanban_card_manager.add_labels() for each task

4. CLAUDE → MARCUS (MCP):
   - Calls: request_next_task("claude-1")
   
5. MARCUS → CLAUDE:
   - Returns: Task("Setup development environment")
   
6. CLAUDE → USER: 
   "I've created a project structure with 20 tasks. 
    Starting with: Setup development environment"
```

### Example: "Deploy to production"

```
1. USER → CLAUDE: "Let's deploy this to production"

2. CLAUDE → MARCUS (MCP):
   - Calls: request_next_task("claude-1")
   
3. MARCUS (Internal Logic):
   - Checks dependencies via AI engine
   - Finds incomplete implementation tasks
   - Safety check BLOCKS deployment
   
4. MARCUS → CLAUDE:
   - Returns: null (no task available)
   - Message: "Cannot deploy - implementation incomplete"
   
5. CLAUDE → USER:
   "❌ Cannot deploy to production yet. These tasks must be completed first:
    - Implement user authentication (16h)
    - Add database migrations (4h)
    - Write integration tests (8h)"
```

### Example: "What should I work on?"

```
1. USER → CLAUDE: "What should I work on next?"

2. CLAUDE → MARCUS (MCP):
   - Calls: get_project_status()
   - Calls: request_next_task("claude-1")
   
3. MARCUS (Internal):
   - Analyzes dependencies
   - Checks team velocity
   - Uses AI to prioritize
   
4. MARCUS → CLAUDE:
   - Status: 35% complete, 3 blockers
   - Next task: "Implement user model"
   - Reason: "Blocking 8 other tasks"
   
5. CLAUDE → USER:
   "Based on dependencies, work on 'Implement user model' next.
    This will unblock 8 other tasks including authentication."
```

## How Natural Language Works

The magic happens in this flow:

1. **User speaks naturally** to Claude
2. **Claude interprets** the intent
3. **Claude calls Marcus MCP tools** to execute
4. **Marcus uses AI** to understand context
5. **Marcus calls Planka MCP** to update board
6. **Results flow back** through the chain

## Key Architecture Points

- **Claude never directly calls Planka** - only Marcus tools
- **Marcus is the intelligence layer** between Claude and Planka
- **Natural language processing** happens at both Claude and Marcus levels
- **Safety checks** are enforced by Marcus before any Planka operations
- **The user never sees MCP tools** - just natural conversation

This is why users can say "build me an app" and get a full project plan - Claude understands the request and Marcus handles all the complex project management logic!