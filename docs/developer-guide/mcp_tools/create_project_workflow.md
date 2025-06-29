# Create Project Tool Workflow & Decision Tree

## Overview
The `create_project` tool converts natural language project descriptions into structured tasks on a kanban board using AI-powered parsing and intelligent task organization.

## High-Level Workflow

```mermaid
graph TD
    A[User provides project description] --> B[create_project MCP tool called]
    B --> C{Validate inputs}
    C -->|Invalid| D[Return error]
    C -->|Valid| E[Initialize kanban client]
    E --> F{Kanban client ready?}
    F -->|No| G[Initialize kanban]
    F -->|Yes| H[Check create_task support]
    G --> H
    H -->|Not supported| I[Return error: No create support]
    H -->|Supported| J[Create NaturalLanguageProjectCreator]
    J --> K[Parse description with AI]
    K --> L[Generate tasks with constraints]
    L --> M[Apply safety checks]
    M --> N[Create tasks on board]
    N --> O[Update Marcus state]
    O --> P[Return success with metadata]
```

## Detailed Decision Tree

```mermaid
graph TD
    Start([Start: create_project_from_natural_language]) --> Val1{Description empty?}
    Val1 -->|Yes| Err1[Error: Description required]
    Val1 -->|No| Val2{Project name empty?}
    Val2 -->|Yes| Err2[Error: Project name required]
    Val2 -->|No| Init1{Kanban client exists?}
    
    Init1 -->|No| InitKanban[Initialize kanban client]
    InitKanban --> Init2{Init successful?}
    Init2 -->|No| Err3[Error: Failed to initialize]
    Init2 -->|Yes| Check1
    Init1 -->|Yes| Check1{Has create_task method?}
    
    Check1 -->|No| Err4[Error: No create support]
    Check1 -->|Yes| Creator[Create NaturalLanguageProjectCreator]
    
    Creator --> Parse[Parse PRD with AI]
    Parse --> Detect{Detect board mode}
    
    Detect --> Mode1[Empty Board → Creator Mode]
    Detect --> Mode2[Active Board → Orchestrator Mode]
    Detect --> Mode3[Mixed Board → Hybrid Mode]
    
    Mode1 --> GenTasks[Generate comprehensive task list]
    Mode2 --> GenTasks2[Generate minimal starter tasks]
    Mode3 --> GenTasks3[Generate balanced task set]
    
    GenTasks --> Constraints[Apply constraints]
    GenTasks2 --> Constraints
    GenTasks3 --> Constraints
    
    Constraints --> Safety[Apply safety checks]
    Safety --> Deploy{Has deployment tasks?}
    
    Deploy -->|Yes| AddDeps[Add dependencies to deployment]
    Deploy -->|No| CreateLoop
    AddDeps --> CreateLoop
    
    CreateLoop[For each task] --> Create{Create task on board}
    Create -->|Success| Next{More tasks?}
    Create -->|Failed| LogErr[Log error, continue]
    LogErr --> Next
    
    Next -->|Yes| CreateLoop
    Next -->|No| Success{All tasks created?}
    
    Success -->|Yes| UpdateState[Update Marcus state]
    Success -->|No| PartialSuccess[Return partial success]
    
    UpdateState --> RefreshState{Refresh successful?}
    RefreshState -->|Yes| ReturnSuccess[Return success metadata]
    RefreshState -->|No| WarnLog[Log warning, return success]
    WarnLog --> ReturnSuccess
```

## Component Interactions

```mermaid
sequenceDiagram
    participant User
    participant MCP as MCP Server
    participant Creator as NaturalLanguageProjectCreator
    participant AI as AI Engine
    participant Parser as AdvancedPRDParser
    participant Kanban as KanbanClient
    participant Board as Kanban Board
    
    User->>MCP: create_project(description, name, options)
    MCP->>MCP: Validate inputs
    MCP->>MCP: Initialize kanban client if needed
    MCP->>Creator: create_project_from_description()
    
    Creator->>AI: Analyze board state
    AI->>Creator: Board context (empty/active/mixed)
    
    Creator->>Parser: parse_prd_to_tasks(description, constraints)
    Parser->>AI: Generate tasks from description
    AI->>Parser: Task list with metadata
    Parser->>Creator: ParsedPRD object
    
    Creator->>Creator: Apply safety checks
    Creator->>Creator: Ensure deployment dependencies
    
    loop For each task
        Creator->>Kanban: create_task(task_data)
        Kanban->>Board: Create card via MCP
        Board->>Kanban: Card created
        Kanban->>Creator: Task object
    end
    
    Creator->>MCP: Return result
    MCP->>MCP: refresh_project_state()
    MCP->>User: Success with metadata
```

## Key Decision Points

### 1. Input Validation
- **Description**: Must be non-empty string
- **Project Name**: Must be non-empty string
- **Options**: Optional, can include team_size, tech_stack, deadline

### 2. Kanban Client Initialization
- Check if client exists
- Verify client supports create_task method
- Use KanbanClientWithCreate for task creation

### 3. Board Context Detection
| Board State | Mode | Behavior |
|------------|------|----------|
| Empty (<3 tasks) | Creator | Generate comprehensive project plan |
| Active (3-50 tasks) | Orchestrator | Generate minimal starter tasks |
| Large (>50 tasks) | Hybrid | Balance new tasks with existing |

### 4. Task Generation Constraints
```python
constraints = {
    "max_tasks": 15,  # Based on team size
    "include_deployment": True,
    "require_testing": True,
    "tech_stack": ["Python", "React"],  # From options
    "deadline": "2025-08-01"  # From options
}
```

### 5. Safety Checks
- Deployment tasks must depend on implementation tasks
- Testing tasks should precede deployment
- No circular dependencies
- Reasonable time estimates

### 6. Error Handling Strategy
| Error Type | Action | User Impact |
|-----------|---------|-------------|
| Validation | Return immediately | Clear error message |
| Kanban init | Return error | Cannot proceed |
| AI parsing | Return error | Cannot generate tasks |
| Single task creation | Log & continue | Partial success |
| State refresh | Log warning | Success returned |

## Task Creation Flow

```mermaid
graph LR
    A[Task Data] --> B{Validate fields}
    B -->|Valid| C[Find target list]
    C --> D{List found?}
    D -->|No| E[Use first list]
    D -->|Yes| F[Create card via MCP]
    E --> F
    F --> G[Add metadata comment]
    G --> H[Convert to Task object]
    H --> I[Apply priority/labels]
    I --> J[Return Task]
```

## State Management

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Validating: create_project called
    Validating --> Initializing: Inputs valid
    Validating --> Error: Invalid inputs
    Initializing --> Ready: Kanban connected
    Initializing --> Error: Connection failed
    Ready --> Parsing: Start AI parsing
    Parsing --> Creating: Tasks generated
    Parsing --> Error: Parse failed
    Creating --> Updating: Tasks created
    Creating --> PartialSuccess: Some tasks failed
    Updating --> Success: State refreshed
    Updating --> Success: Refresh failed (logged)
    Success --> [*]
    PartialSuccess --> [*]
    Error --> [*]
```

## Error Recovery Mechanisms

1. **Dictionary Iteration Protection**
   - Use `list()` to create snapshots before iteration
   - Prevents "dictionary changed size during iteration"

2. **Partial Success Handling**
   - Continue creating remaining tasks if one fails
   - Report number of successfully created tasks

3. **Graceful Degradation**
   - If AI engine unavailable, return error early
   - If state refresh fails, still return success

4. **Retry Logic**
   - Currently none - fails fast
   - Future: Add exponential backoff for transient failures

## Performance Considerations

- **Batch Creation**: Tasks created sequentially (future: batch API)
- **AI Latency**: ~2-5 seconds for parsing complex descriptions
- **Board Size Impact**: Larger boards take longer to analyze
- **Concurrent Access**: Protected against race conditions

## Usage Examples

### Simple Project
```python
result = await create_project_from_natural_language(
    description="Create a REST API for user management",
    project_name="User API"
)
```

### Complex Project with Options
```python
result = await create_project_from_natural_language(
    description="Build an e-commerce platform with payments",
    project_name="Shop Platform",
    options={
        "team_size": 5,
        "tech_stack": ["Django", "React", "PostgreSQL"],
        "deadline": "2025-12-31"
    }
)
```

## Success Response Structure
```json
{
    "success": true,
    "project_name": "Project Name",
    "tasks_created": 10,
    "phases": ["epic_infrastructure", "epic_features"],
    "estimated_days": 30,
    "dependencies_mapped": 5,
    "risk_level": "medium",
    "confidence": 0.85,
    "created_at": "2025-06-28T20:00:00.000Z"
}
```