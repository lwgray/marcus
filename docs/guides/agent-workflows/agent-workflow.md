# The Complete Agent-Marcus Interaction Flow

## 1. Agent Lifecycle & Core Loop

```
STARTUP → REGISTER → [CONTINUOUS WORK LOOP] → NO TASKS AVAILABLE
```

The agent operates in a perpetual work cycle:
1. **Register once** with Marcus (`register_agent`)
2. **Request task** (`request_next_task`)
3. **Get context** if needed (`get_task_context`)
4. **Work on task** autonomously
5. **Report progress** at 25%, 50%, 75% (`report_task_progress`)
6. **Log decisions** as they're made (`log_decision`)
7. **Create artifacts** for other agents (`log_artifact`)
8. **Report completion** at 100%
9. **Immediately request next task** (loop continues)

## 2. Available Tools & Decision Criteria

Agents have access to these Marcus tools:

### Core Workflow Tools
- `register_agent` - Used ONCE at startup
- `request_next_task` - Called IMMEDIATELY after any task completion
- `report_task_progress` - Called at 25%, 50%, 75%, 100% milestones
- `report_blocker` - When stuck and need AI-powered suggestions

### Context & Information Tools
- `get_task_context` - Used when:
  - Task has listed dependencies
  - Task mentions "integrate", "extend", "based on", "following"
  - Need to understand what was previously built
  - Want to check available artifacts

- `get_agent_status` - Check own status and capabilities

### Documentation Tools
- `log_decision` - Used IMMEDIATELY when making architectural choices:
  - Database selection
  - Framework choices
  - API design decisions
  - Naming conventions
  - Format: "I chose X because Y. This affects Z."

- `log_artifact` - Used when creating shareable documents:
  - API specifications → `docs/api/`
  - Design documents → `docs/design/`
  - Architecture decisions → `docs/architecture/`
  - Technical specs → `docs/specifications/`
  - Documentation → `docs/`

### Dependency Tools
- `check_task_dependencies` - Verify dependency status before starting
- `create_project` - Create new projects using natural language (NLP)

## 3. Context Flow & Decision Making

When an agent receives a task, Marcus provides:

```json
{
  "task": {
    "id": "task-123",
    "name": "Implement user API",
    "instructions": "Tiered instructions with context",
    "implementation_context": "Previous work from GitHub",
    "dependency_awareness": "3 tasks depend on your work:\n- Frontend (needs: REST endpoints)\n- Mobile (needs: JWT auth)",
    "full_context": {
      "previous_implementations": {...},
      "dependent_tasks": [...],
      "related_patterns": [...],
      "architectural_decisions": [...]
    },
    "predictions": {
      "success_probability": 0.85,
      "completion_time": {"expected_hours": 4.2},
      "blockage_analysis": {"overall_risk": 0.3}
    }
  }
}
```

## 4. Agent Decision Process

The agent follows this decision tree:

```
Task Received
├── Has dependencies? → get_task_context()
│   ├── Read new artifacts
│   └── Skip known artifacts
├── Making architectural choice? → log_decision()
├── Creating shareable docs? → log_artifact()
├── Hit 25/50/75% milestone? → report_task_progress()
├── Blocked? → report_blocker()
│   └── Try AI suggestions
└── Complete? → report_task_progress(100)
    └── IMMEDIATELY → request_next_task()
```

## 5. Smart Artifact Management

Agents interact with artifacts intelligently:

```python
# Example flow when task has dependencies
1. get_task_context() returns:
   artifacts: [
     {filename: "user-api.yaml", location: "docs/api/user-api.yaml"},
     {filename: "auth-design.md", location: "docs/design/auth-design.md"}
   ]

2. Agent decides:
   - Read("docs/api/user-api.yaml")     # Haven't seen this
   - Skip auth-design.md                # Already know JWT with 24h expiry

3. Creates new artifacts:
   - log_artifact("user-impl.md", content, "documentation")
   - log_artifact("user-model.ts", model, "specification")
```

## 6. Critical Behaviors

### ALWAYS:
- Complete tasks before requesting new ones
- Request next task IMMEDIATELY after completion
- Log decisions AS they're made, not after
- Follow existing patterns from context
- Report specific implementation details

### NEVER:
- Wait for user permission
- Skip tasks or leave incomplete
- Ask for clarification
- Coordinate directly with other agents
- Stop the work loop

## 7. Integration with Marcus Systems

The agent's actions trigger Marcus's internal systems:
- **Context System** - Builds rich context from dependencies
- **Memory System** - Predicts outcomes and learns from performance
- **Dependency System** - Ensures logical task ordering
- **Event System** - Broadcasts agent activities
- **Persistence System** - Stores decisions and artifacts

## 8. How Marcus Establishes Context

Marcus establishes context through a sophisticated multi-layered system:

### Context Collection Sources
Marcus gathers context from multiple sources:
- **Previous implementations** from completed dependency tasks
- **Dependent tasks** that will need the agent's work
- **Architectural decisions** made by other agents
- **Related patterns** from similar tasks
- **GitHub code analysis** (when using GitHub provider)
- **Kanban attachments** and artifacts

### Context Delivery Mechanism
When an agent calls `request_next_task`, Marcus:
1. Finds the optimal task for the agent
2. Analyzes task dependencies (both explicit and inferred)
3. Builds a `TaskContext` object containing:
   - Previous implementations from dependencies
   - Tasks that depend on this work
   - Related patterns and architectural decisions
   - Predictions about success probability and completion time
4. Generates tiered instructions that include all context

### Dependency Inference System
Marcus uses three levels of dependency inference:
- **Pattern-based rules**: Common patterns like "frontend depends on API"
- **AI-enhanced analysis**: Using Claude to understand complex relationships
- **Adaptive learning**: Learning from user feedback and project patterns

### Context Delivery Format
The context is delivered in the task assignment response as shown in Section 3 above. The system ensures agents have the full picture of what came before, what's needed now, and what will depend on their work - enabling them to make informed implementation decisions without constant back-and-forth communication.

## Summary

The agent workflow is a carefully orchestrated system where agents operate autonomously in a continuous loop, making intelligent decisions about when to gather context, log decisions, create artifacts, and report progress - all while Marcus provides rich contextual information and predictions to guide their work.
