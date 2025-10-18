# Task & Subtask Timing Chart

This sequence diagram shows the temporal order of events during task creation, decomposition, and assignment.

```mermaid
sequenceDiagram
    participant User
    participant MCP as MCP Server
    participant NLP as NLP Pipeline
    participant AI as AI Engine
    participant Provider as Kanban Provider
    participant Registry as Project Registry
    participant Agent
    participant Decomposer
    participant Assigner as Assignment Engine

    Note over User,Registry: PROJECT CREATION PHASE
    User->>MCP: create_project(description, name)
    MCP->>NLP: Initialize pipeline
    NLP->>AI: Analyze PRD
    AI-->>NLP: Requirements + tasks
    NLP->>AI: Generate dependencies
    AI-->>NLP: Dependency graph
    NLP->>Provider: Create board
    Provider-->>NLP: board_id
    NLP->>Provider: Upload tasks (batch)
    Provider-->>NLP: task_ids

    Note over NLP,AI: IMMEDIATE DECOMPOSITION PHASE
    loop For each task
        NLP->>NLP: Check if should decompose (>4hrs, not deployment)
        alt Task needs decomposition
            NLP->>AI: Generate subtasks
            AI-->>NLP: 3-5 subtasks + contracts
            NLP->>NLP: Register subtasks in unified graph
            NLP->>AI: Cross-wire dependencies
            AI-->>NLP: Additional deps
            NLP->>Provider: Create subtasks on board
        end
    end

    NLP->>Registry: Register project
    Registry-->>NLP: project_id
    NLP->>MCP: Refresh state (load tasks + subtasks)
    MCP-->>User: Project created (tasks + subtasks)

    Note over Agent,Assigner: AGENT REGISTRATION PHASE
    Agent->>MCP: register_agent(id, skills)
    MCP->>Registry: Store agent info
    Registry-->>MCP: Registered
    MCP-->>Agent: Ready for tasks

    Note over Agent,Assigner: TASK ASSIGNMENT PHASE (Loop)
    Agent->>MCP: request_next_task()
    MCP->>Assigner: Find optimal task

    Assigner->>Assigner: Check for existing subtasks first
    Assigner->>Assigner: Filter by dependencies
    Assigner->>AI: Score & match skills
    AI-->>Assigner: Ranked candidates
    Assigner->>Assigner: Immediate reservation
    Assigner->>Registry: Persist assignment
    Assigner-->>MCP: Optimal task
    MCP-->>Agent: Task + context + instructions

    Note over Agent,Provider: TASK EXECUTION PHASE
    loop Work on task
        Agent->>MCP: report_task_progress(25%)
        MCP->>Provider: Update status
        Agent->>MCP: report_task_progress(50%)
        MCP->>Provider: Update status

        alt Blocker encountered
            Agent->>MCP: report_blocker(description)
            MCP->>AI: Generate suggestions
            AI-->>MCP: Recovery strategies
            MCP-->>Agent: Suggestions
        end
    end

    Agent->>MCP: report_task_progress(completed)
    MCP->>Provider: Mark DONE
    MCP->>Registry: Update metrics
    MCP->>MCP: Refresh state
    MCP-->>Agent: Task completed

    Note over Agent,Assigner: LOOP CONTINUES
    Agent->>MCP: request_next_task()
    Note over MCP: Cycle repeats...
```

## Timeline Phases

### Phase 1: Project Creation with Decomposition (Seconds 0-20)
- User initiates project with natural language description
- NLP Pipeline processes requirements through AI
- Tasks generated (8-15 tasks typical)
- Dependencies inferred and wired
- Board created on Kanban provider
- All tasks uploaded in batch
- **CRITICAL**: Immediately after upload, eligible tasks are decomposed:
  - Heuristics check (>4 hours AND not deployment)
  - AI generates 3-5 subtasks per eligible task
  - Subtasks registered in unified graph
  - Cross-parent dependencies wired
  - Subtasks created on Kanban board
- Project registered in Marcus state
- **Duration**: ~15-20 seconds (task creation ~8s + decomposition ~8s in parallel)

### Phase 2: Agent Registration (Second 11)
- Agent registers with Marcus
- Provides agent_id, name, role, skills
- Stored in project registry
- Agent marked ready for assignment
- **Duration**: <1 second

### Phase 3: Task Assignment Loop (Ongoing)
Each iteration:
1. **Request** (~100ms): Agent calls `request_next_task()`
2. **Assignment Selection** (~2-3s):
   - Priority check: Search existing subtasks first
   - Dependency filtering (both task and subtask dependencies)
   - AI skill matching and scoring
   - Immediate reservation
   - Persistence to assignments.json
3. **Return** (~100ms): Task + context returned to agent

**Note**: No decomposition happens during assignment - subtasks were already created during project creation phase

### Phase 4: Task Execution (Variable Duration)
- Agent works autonomously on assigned task
- Progress reports at milestones (25%, 50%, 75%, 100%)
- Each report syncs to Kanban provider
- Optional blocker reporting with AI recovery suggestions
- Completion triggers state refresh
- **Duration**: Minutes to hours depending on task complexity

### Phase 5: Loop Continuation
- Agent immediately requests next task
- System returns to Phase 3
- Continues until all tasks completed

## Timing Observations

1. **Parallel AI Calls**: Project creation AND decomposition optimized with concurrent API calls (10x speedup)
2. **Eager Decomposition**: Subtasks created immediately during project creation, NOT during assignment
3. **Immediate Reservation**: Assignment happens instantly to prevent race conditions
4. **Continuous Sync**: Every state change persisted to Kanban provider
5. **State Refresh**: Triggered on completion to ensure dependency accuracy
6. **Assignment Speed**: Fast (<3s) because subtasks already exist - just filtering and scoring
