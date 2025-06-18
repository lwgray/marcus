#!/usr/bin/env python3
"""
Generate visual diagrams of the PM Agent conversation flow
"""

import os
from datetime import datetime


def generate_mermaid_diagram():
    """Generate Mermaid diagram of conversation flow"""
    
    diagram = """
# PM Agent Conversation Flow

## Overview Diagram

```mermaid
graph TB
    subgraph "Worker Layer"
        W1[Claude Backend Dev]
        W2[Claude Frontend Dev]
        W3[Claude Fullstack Dev]
    end
    
    subgraph "PM Agent Core"
        PM[PM Agent]
        AI[AI Analysis Engine]
        MON[Project Monitor]
    end
    
    subgraph "Kanban Board"
        KB[Planka/GitHub Projects]
        BL[Backlog]
        RD[Ready]
        IP[In Progress]
        DN[Done]
    end
    
    W1 <-->|"MCP Protocol"| PM
    W2 <-->|"MCP Protocol"| PM
    W3 <-->|"MCP Protocol"| PM
    
    PM <-->|"MCP Protocol"| KB
    PM --> AI
    PM --> MON
    
    KB --> BL
    KB --> RD
    KB --> IP
    KB --> DN
```

## Detailed Conversation Flow

```mermaid
sequenceDiagram
    participant W as Worker
    participant PM as PM Agent
    participant KB as Kanban Board
    
    Note over W,KB: 1. Worker Registration
    W->>PM: Register (skills, role)
    PM->>PM: Validate & store worker info
    PM->>W: Registration confirmed
    
    Note over W,KB: 2. Task Request
    W->>PM: Request next task
    PM->>PM: Check worker skills
    PM->>KB: Get available tasks
    KB->>KB: Query Backlog/Ready
    KB->>PM: Return unassigned tasks
    PM->>PM: Match tasks to skills
    PM->>KB: Assign task to worker
    KB->>KB: Move to In Progress
    KB->>PM: Assignment confirmed
    PM->>W: Task details & instructions
    
    Note over W,KB: 3. Progress Updates
    W->>PM: Report progress (50%)
    PM->>KB: Update task progress
    KB->>KB: Add comment, update %
    KB->>PM: Update confirmed
    PM->>W: Acknowledged
    
    Note over W,KB: 4. Blocker Handling
    W->>PM: Report blocker
    PM->>PM: Analyze blocker
    PM->>KB: Mark task blocked
    KB->>KB: Add blocked label
    KB->>PM: Blocker recorded
    PM->>W: Provide solutions
    
    Note over W,KB: 5. Task Completion
    W->>PM: Task complete (100%)
    PM->>KB: Move task to Done
    KB->>KB: Update status & metrics
    KB->>PM: Completion confirmed
    PM->>KB: Get project metrics
    KB->>PM: Return metrics
    PM->>W: Next task ready?
```

## Communication Patterns

```mermaid
graph LR
    subgraph "Worker Messages"
        WM1[Register with skills]
        WM2[Request task]
        WM3[Report progress]
        WM4[Report blocker]
        WM5[Complete task]
    end
    
    subgraph "PM Agent Decisions"
        PMD1[Match skills to tasks]
        PMD2[Prioritize assignments]
        PMD3[Analyze blockers]
        PMD4[Track velocity]
        PMD5[Balance workload]
    end
    
    subgraph "Kanban Operations"
        KBO1[Query tasks]
        KBO2[Update assignments]
        KBO3[Move cards]
        KBO4[Track metrics]
        KBO5[Record history]
    end
    
    WM1 --> PMD1
    WM2 --> PMD1
    PMD1 --> KBO1
    
    WM3 --> PMD4
    PMD4 --> KBO2
    
    WM4 --> PMD3
    PMD3 --> KBO3
    
    WM5 --> PMD5
    PMD5 --> KBO4
```

## State Transitions

```mermaid
stateDiagram-v2
    [*] --> Available: Worker Registered
    Available --> Working: Task Assigned
    Working --> Blocked: Blocker Reported
    Blocked --> Working: Blocker Resolved
    Working --> Available: Task Completed
    Available --> [*]: Worker Offline
    
    note right of Working
        Worker actively working
        Sending progress updates
        PM Agent monitoring
    end note
    
    note right of Blocked
        Waiting for resolution
        PM Agent providing help
        May reassign if needed
    end note
```

## Data Flow

```mermaid
graph TD
    subgraph "Input Data"
        ID1[Worker Skills]
        ID2[Task Requirements]
        ID3[Progress Updates]
        ID4[Blocker Reports]
    end
    
    subgraph "PM Agent Processing"
        P1[Skill Matching Algorithm]
        P2[Priority Calculation]
        P3[Workload Balancing]
        P4[Blocker Analysis]
        P5[Performance Tracking]
    end
    
    subgraph "Output Actions"
        OA1[Task Assignments]
        OA2[Board Updates]
        OA3[Status Reports]
        OA4[Resolution Suggestions]
        OA5[Metrics Dashboard]
    end
    
    ID1 --> P1
    ID2 --> P1
    P1 --> OA1
    
    ID3 --> P5
    P5 --> OA2
    P5 --> OA3
    
    ID4 --> P4
    P4 --> OA4
    
    P2 --> OA1
    P3 --> OA1
```

## Error Handling Flow

```mermaid
graph TB
    E1[Connection Error] --> R1[Retry with backoff]
    E2[Task Assignment Fail] --> R2[Find alternative task]
    E3[Board Update Fail] --> R3[Queue for retry]
    E4[Worker Timeout] --> R4[Reassign task]
    
    R1 --> S1{Success?}
    S1 -->|Yes| C1[Continue]
    S1 -->|No| A1[Alert Admin]
    
    R2 --> S2{Found?}
    S2 -->|Yes| C2[Assign new task]
    S2 -->|No| A2[Worker idle]
    
    R3 --> S3{Retry OK?}
    S3 -->|Yes| C3[Update board]
    S3 -->|No| A3[Log inconsistency]
    
    R4 --> C4[Notify original worker]
```
"""
    
    return diagram


def generate_conversation_examples():
    """Generate example conversations"""
    
    examples = """
# Example Conversations

## 1. Worker Registration

**Worker → PM Agent:**
```
{
  "action": "register_agent",
  "agent_id": "claude-backend-001",
  "name": "Claude Backend Dev",
  "role": "Backend Developer",
  "skills": ["python", "api", "database", "testing"]
}
```

**PM Agent Thinking:**
- New agent registration request
- Validating skills against project needs
- Checking for duplicate registration
- Adding to available worker pool

**PM Agent → Worker:**
```
{
  "success": true,
  "message": "Welcome Claude Backend Dev! You're registered and ready to receive tasks.",
  "agent_id": "claude-backend-001"
}
```

## 2. Task Request & Assignment

**Worker → PM Agent:**
```
{
  "action": "request_next_task",
  "agent_id": "claude-backend-001"
}
```

**PM Agent → Kanban Board:**
```
{
  "action": "get_available_tasks",
  "filters": {
    "status": ["Backlog", "Ready"],
    "assigned_to": null
  }
}
```

**Kanban Board → PM Agent:**
```
{
  "tasks": [
    {
      "id": "task-123",
      "title": "Implement user authentication",
      "priority": "High",
      "labels": ["backend", "security"],
      "estimated_hours": 8
    },
    {
      "id": "task-124", 
      "title": "Create API documentation",
      "priority": "Medium",
      "labels": ["documentation"],
      "estimated_hours": 4
    }
  ]
}
```

**PM Agent Thinking:**
- Analyzing 2 available tasks
- Task-123: High priority, matches skills (backend, security)
- Task-124: Medium priority, partial match
- Decision: Assign task-123 due to priority and skill match

**PM Agent → Kanban Board:**
```
{
  "action": "assign_task",
  "task_id": "task-123",
  "agent_id": "claude-backend-001",
  "updates": {
    "assigned_to": "claude-backend-001",
    "status": "In Progress",
    "started_at": "2024-01-15T10:30:00Z"
  }
}
```

**PM Agent → Worker:**
```
{
  "has_task": true,
  "task": {
    "id": "task-123",
    "title": "Implement user authentication",
    "description": "Create secure login system with JWT tokens",
    "priority": "High",
    "estimated_hours": 8,
    "instructions": "1. Set up user model\\n2. Implement JWT auth\\n3. Create login/logout endpoints\\n4. Add password hashing\\n5. Write tests"
  }
}
```

## 3. Progress Update

**Worker → PM Agent:**
```
{
  "action": "report_task_progress",
  "agent_id": "claude-backend-001",
  "task_id": "task-123",
  "status": "in_progress",
  "progress": 50,
  "message": "User model and JWT implementation complete. Working on endpoints."
}
```

**PM Agent → Kanban Board:**
```
{
  "action": "update_task",
  "task_id": "task-123",
  "updates": {
    "progress": 50,
    "last_updated": "2024-01-15T14:30:00Z"
  },
  "comment": "Progress: 50% - User model and JWT implementation complete. Working on endpoints."
}
```

## 4. Blocker Report

**Worker → PM Agent:**
```
{
  "action": "report_blocker",
  "agent_id": "claude-backend-001",
  "task_id": "task-123",
  "blocker_description": "Missing OAuth provider credentials for social login",
  "severity": "medium"
}
```

**PM Agent Thinking:**
- Blocker type: External dependency
- Severity: Medium (can work around)
- Analyzing possible solutions

**PM Agent → Kanban Board:**
```
{
  "action": "add_comment",
  "task_id": "task-123",
  "comment": "BLOCKER: Missing OAuth provider credentials\\nSeverity: Medium\\nAssigned agent blocked on external dependency"
}
```

**PM Agent → Worker:**
```
{
  "success": true,
  "suggestions": [
    "Implement local authentication first, add OAuth later",
    "Use mock OAuth provider for development",
    "Request credentials from DevOps team via separate task"
  ],
  "escalated": false
}
```

## 5. Task Completion

**Worker → PM Agent:**
```
{
  "action": "report_task_progress",
  "agent_id": "claude-backend-001",
  "task_id": "task-123",
  "status": "completed",
  "progress": 100,
  "message": "Authentication system complete. All tests passing, documentation updated."
}
```

**PM Agent → Kanban Board:**
```
{
  "action": "move_card",
  "task_id": "task-123",
  "to_list": "Done",
  "comment": "Completed by claude-backend-001. All tests passing."
}
```

**PM Agent → Kanban Board:**
```
{
  "action": "get_project_metrics"
}
```

**Kanban Board → PM Agent:**
```
{
  "metrics": {
    "total_tasks": 25,
    "completed": 11,
    "in_progress": 4,
    "completion_rate": "44%",
    "velocity": "2.8 tasks/day"
  }
}
```

**PM Agent → Worker:**
```
{
  "success": true,
  "message": "Excellent work! Task completed successfully. Ready for next assignment?"
}
```
"""
    
    return examples


def main():
    """Generate documentation files"""
    
    # Create output directory
    os.makedirs("docs/conversation-flow", exist_ok=True)
    
    # Generate Mermaid diagrams
    with open("docs/conversation-flow/DIAGRAMS.md", "w") as f:
        f.write(generate_mermaid_diagram())
    
    # Generate conversation examples
    with open("docs/conversation-flow/EXAMPLES.md", "w") as f:
        f.write(generate_conversation_examples())
    
    # Generate README
    readme = """# PM Agent Conversation Flow Documentation

This directory contains detailed documentation of the conversation flow between Workers, PM Agent, and the Kanban Board.

## Files

1. **DIAGRAMS.md** - Visual diagrams showing:
   - System architecture
   - Conversation sequence flows
   - State transitions
   - Data flow patterns

2. **EXAMPLES.md** - Detailed conversation examples:
   - Worker registration
   - Task assignment
   - Progress updates
   - Blocker handling
   - Task completion

## Key Concepts

### Three-Way Communication

1. **Worker ↔ PM Agent**
   - Workers request tasks
   - PM Agent assigns based on skills
   - Progress and blocker reports
   - Task completion notifications

2. **PM Agent ↔ Kanban Board**
   - Query available tasks
   - Update task assignments
   - Move cards between columns
   - Track project metrics

3. **PM Agent Decision Making**
   - Skill matching algorithms
   - Priority-based assignment
   - Workload balancing
   - Blocker resolution

### Message Flow

All communication follows a request-response pattern:
- Workers initiate requests
- PM Agent processes and may query Kanban
- Kanban provides data
- PM Agent makes decisions
- Response flows back to worker

### Logging Levels

- **🧠 Thinking**: Internal PM Agent logic
- **💬 Messages**: Inter-component communication  
- **📋 Decisions**: PM Agent choices with reasons
- **🔌 Kanban Ops**: Board queries and updates
- **🚫 Blockers**: Issues requiring resolution

## Viewing Diagrams

The Mermaid diagrams can be viewed:
1. In GitHub/GitLab (automatic rendering)
2. In VS Code with Mermaid extension
3. Online at mermaid.live
4. In documentation tools supporting Mermaid

## Running Demos

See the scripts directory for interactive demos:
- `test_conversation.py` - Basic flow
- `test_full_conversation.py` - Complete simulation
- `mock_claude_worker_verbose.py` - Live worker with logging
"""
    
    with open("docs/conversation-flow/README.md", "w") as f:
        f.write(readme)
    
    print("✅ Conversation flow documentation generated!")
    print("📁 Files created in: docs/conversation-flow/")
    print("   - DIAGRAMS.md (Mermaid diagrams)")
    print("   - EXAMPLES.md (Conversation examples)")
    print("   - README.md (Overview)")


if __name__ == "__main__":
    main()