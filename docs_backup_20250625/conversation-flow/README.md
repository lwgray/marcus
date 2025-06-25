# PM Agent Conversation Flow Documentation

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
