# PM Agent Architecture & Workflows

## System Architecture

```mermaid
graph TB
    subgraph "Workers (Agents)"
        W1[Worker 1<br/>Backend Dev]
        W2[Worker 2<br/>Frontend Dev]
        W3[Worker 3<br/>QA Engineer]
    end
    
    subgraph "PM Agent System"
        MCP[MCP Server<br/>Interface]
        
        subgraph "In-Memory State"
            AS[Agent Status<br/>Dict]
            AT[Agent Tasks<br/>Dict]
            PT[Project Tasks<br/>List]
            PS[Project State<br/>Object]
        end
        
        TAE[Task Assignment<br/>Engine]
        AIE[AI Engine<br/>Claude]
    end
    
    subgraph "External Systems"
        KB[Kanban Board<br/>Planka/Linear/GitHub]
        GH[GitHub<br/>Code Analysis]
    end
    
    W1 & W2 & W3 -.->|MCP Protocol| MCP
    MCP --> AS & AT
    TAE --> PT & AS
    TAE <--> AIE
    MCP <--> TAE
    MCP <--> KB
    KB --> PT & PS
    GH --> PS
    
    style AS fill:#e1f5fe
    style AT fill:#e1f5fe
    style PT fill:#e1f5fe
    style PS fill:#e1f5fe
    style AIE fill:#fff3e0
    style KB fill:#e8f5e9
```

## Data Flow: How PM Agent Remembers Tasks

```mermaid
graph LR
    subgraph "Task Memory System"
        KB[Kanban Board<br/>Source of Truth]
        PM[PM Agent<br/>In-Memory Cache]
        
        KB -->|refresh_project_state()| PM
        PM -->|update_task()| KB
    end
    
    subgraph "State Components"
        PT[project_tasks<br/>All tasks from kanban]
        AT[agent_tasks<br/>Current assignments]
        AS[agent_status<br/>Worker info]
    end
    
    PM --> PT & AT & AS
    
    Note1[No Persistence!<br/>State rebuilt from<br/>kanban on restart]
    
    style KB fill:#4caf50
    style PM fill:#2196f3
    style Note1 fill:#ffeb3b
```

## Workflow 1: Worker Registration

```mermaid
sequenceDiagram
    participant W as Worker
    participant MCP as MCP Server
    participant S as State Manager
    participant L as Logger
    
    W->>MCP: register_agent(agent_id, name, role, skills)
    MCP->>S: Create WorkerStatus object
    Note over S: Initialize:<br/>- capacity: 40 hrs/week<br/>- current_tasks: []<br/>- performance: 1.0
    S->>S: Store in agent_status[agent_id]
    MCP->>L: Log registration event
    MCP-->>W: {"status": "registered", "message": "Success"}
```

## Workflow 2: Requesting Work

```mermaid
sequenceDiagram
    participant W as Worker
    participant MCP as PM Agent
    participant KB as Kanban API
    participant AI as AI Engine
    participant S as State
    
    W->>MCP: request_next_task(agent_id)
    MCP->>KB: get_available_tasks()
    KB-->>MCP: List of TODO tasks
    MCP->>S: Update project_tasks
    
    MCP->>MCP: find_optimal_task_for_agent()
    Note over MCP: Score tasks by:<br/>- Skill match (60%)<br/>- Priority (40%)
    
    alt Task Found
        MCP->>AI: Generate instructions(task, agent)
        AI-->>MCP: Detailed instructions
        MCP->>S: Create TaskAssignment
        MCP->>KB: Update task status → IN_PROGRESS
        MCP->>S: Store in agent_tasks[agent_id]
        MCP-->>W: TaskAssignment with instructions
    else No Task
        MCP-->>W: None (no suitable tasks)
    end
```

## Workflow 3: Progress Reporting

```mermaid
sequenceDiagram
    participant W as Worker
    participant MCP as PM Agent
    participant KB as Kanban API
    participant S as State
    
    W->>MCP: report_task_progress(agent_id, task_id, status, progress)
    
    alt Status = "in_progress"
        MCP->>KB: Update task progress
        MCP->>KB: Add progress comment
    else Status = "completed"
        MCP->>KB: Update task → DONE
        MCP->>S: Clear from agent_tasks
        MCP->>S: Increment completed_tasks_count
        Note over MCP: Optional: Run code analysis
    else Status = "blocked"
        MCP->>KB: Update task → BLOCKED
        MCP->>KB: Add blocker description
    end
    
    MCP->>KB: refresh_project_state()
    KB-->>MCP: Updated project data
    MCP-->>W: {"status": "updated"}
```

## Workflow 4: Task Completion

```mermaid
sequenceDiagram
    participant W as Worker
    participant MCP as PM Agent
    participant KB as Kanban
    participant S as State
    
    rect rgb(200, 230, 200)
        Note over W,KB: Task Completion Phase
        W->>MCP: report_task_progress(task_id, "completed", 100)
        MCP->>KB: Update task status → DONE
        MCP->>KB: Add completion timestamp
        MCP->>S: Remove from agent_tasks[agent_id]
        MCP->>S: worker.completed_tasks_count++
        MCP-->>W: {"status": "completed"}
    end
    
    rect rgb(200, 200, 230)
        Note over W,KB: Next Task Request
        W->>MCP: request_next_task(agent_id)
        MCP->>KB: Refresh all tasks
        MCP->>MCP: Find next optimal task
        MCP-->>W: New TaskAssignment
    end
```

## Task Assignment Algorithm

```mermaid
flowchart TD
    Start([Worker requests task])
    Refresh[Refresh tasks from kanban]
    Filter[Filter TODO tasks]
    Assigned{Already<br/>assigned?}
    Skills[Calculate skill match score]
    Priority[Calculate priority score]
    Score[Total Score = <br/>Skills×0.6 + Priority×0.4]
    Best{Best<br/>task?}
    Instructions[Generate AI instructions]
    Assign[Create TaskAssignment]
    Update[Update kanban → IN_PROGRESS]
    Return[Return to worker]
    NoTask[Return None]
    
    Start --> Refresh
    Refresh --> Filter
    Filter --> Assigned
    Assigned -->|Yes| Filter
    Assigned -->|No| Skills
    Skills --> Priority
    Priority --> Score
    Score --> Best
    Best -->|Yes| Instructions
    Best -->|No| NoTask
    Instructions --> Assign
    Assign --> Update
    Update --> Return
```

## Key Design Principles

1. **Stateless Operation**: PM Agent doesn't persist state between restarts
2. **Kanban as Database**: All task data lives in the kanban system
3. **Real-time Refresh**: State is refreshed from kanban on every operation
4. **AI-Powered Instructions**: Claude generates context-aware task instructions
5. **Skill-Based Assignment**: Tasks matched to workers based on skills and priority
6. **Autonomous Workers**: Workers operate independently without coordination