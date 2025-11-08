# Diagnostics Tools

Debugging and analysis utilities for diagnosing issues in Marcus multi-agent projects.

## Tools Overview

| Tool | Purpose | Use Case |
|------|---------|----------|
| `analyze_stall.py` | Capture and replay project stalls | Projects stop making progress |
| `diagnose_task_descriptions.py` | Validate task descriptions | Tasks seem unclear or malformed |
| `show_ai_input.py` | Display AI reasoning context | Understanding agent decisions |
| `preview_project_plan.py` | Show planned project structure | Validating before creation |
| `query_memory_data.py` | Query stored memory/context | Investigating context issues |
| `view_experiment_data.py` | View experiment metadata | Analyzing experiment results |

## Quick Reference

### Analyze Project Stalls
```bash
# Capture current stall state
python analyze_stall.py capture

# List captured snapshots
python analyze_stall.py list

# Replay a specific stall
python analyze_stall.py replay <snapshot_file>
```

### Diagnose Task Issues
```bash
# Check task descriptions
python diagnose_task_descriptions.py

# With specific project
python diagnose_task_descriptions.py --project "My Project"
```

### View AI Context
```bash
# Show AI input for current context
python show_ai_input.py

# With specific agent or task
python show_ai_input.py --agent agent_123
```

### Preview Project Structure
```bash
# Preview project before creation
python preview_project_plan.py --spec project_spec.md

# Show detailed breakdown
python preview_project_plan.py --spec project_spec.md --detailed
```

## Detailed Tool Documentation

### analyze_stall.py

Captures project state when agents stop making progress, allowing you to replay and analyze the scenario.

**Features**:
- Snapshot-based: Captures complete project state
- Replay capability: Re-run stall scenarios
- Time-stamped: Track when stalls occurred
- Exportable: Share snapshots for debugging

**Usage**:
```bash
# Basic capture
python analyze_stall.py capture

# Capture with description
python analyze_stall.py capture --description "Agents stuck after task 5"

# List all snapshots
python analyze_stall.py list

# Show snapshot details
python analyze_stall.py show <snapshot_id>

# Replay snapshot
python analyze_stall.py replay <snapshot_file>

# Clean old snapshots
python analyze_stall.py clean --older-than 7  # days
```

**Output**:
Creates snapshots in `~/.marcus/stall_snapshots/` with:
- Board state (all tasks)
- Agent states
- Project metadata
- Timestamp and description

**When to Use**:
- Agents stop picking up tasks
- Tasks stuck in "in_progress" state
- Board appears frozen
- Agents repeatedly fail same task

---

### diagnose_task_descriptions.py

Validates task descriptions for clarity, completeness, and potential issues.

**Features**:
- Checks for ambiguous language
- Validates task dependencies
- Identifies missing information
- Suggests improvements

**Usage**:
```bash
# Check all tasks in current project
python diagnose_task_descriptions.py

# Check specific project
python diagnose_task_descriptions.py --project "Task Management API"

# Check specific board
python diagnose_task_descriptions.py --board-id 12345

# Detailed analysis
python diagnose_task_descriptions.py --verbose

# Export report
python diagnose_task_descriptions.py --output report.json
```

**Checks Performed**:
- Description length (too short/long)
- Clarity (vague terms like "handle", "deal with")
- Specificity (actionable vs abstract)
- Dependencies (valid references)
- Acceptance criteria (clear success conditions)

**Output Example**:
```
Task #5: "Handle user authentication"
❌ ISSUES FOUND:
  - Vague verb: "Handle" - prefer specific actions
  - Missing acceptance criteria
  - No mention of auth method (JWT, OAuth, etc.)

✅ SUGGESTED REWRITE:
  "Implement JWT-based user authentication with login endpoint
   that accepts email/password and returns access token"
```

**When to Use**:
- Before starting project (validate task breakdown)
- Agents seem confused about task requirements
- Tasks frequently reassigned or rewritten
- High task failure rate

---

### show_ai_input.py

Displays the context and prompts sent to AI agents, helping understand their reasoning.

**Features**:
- Shows complete AI context
- Displays prompt templates used
- Reveals context limitations
- Helps identify missing information

**Usage**:
```bash
# Show current AI context
python show_ai_input.py

# Show for specific agent
python show_ai_input.py --agent agent_backend_001

# Show for specific task
python show_ai_input.py --task task_42

# Include full context (may be large)
python show_ai_input.py --full-context

# Export to file
python show_ai_input.py --output ai_context.txt
```

**Output**:
```
=== AI INPUT CONTEXT ===
Agent: agent_backend_001
Task: task_42 - Implement user authentication

SYSTEM PROMPT:
You are a backend developer agent...

TASK CONTEXT:
Description: Implement JWT-based authentication
Dependencies: [task_15: Database setup]
Requirements:
  - Use bcrypt for password hashing
  - Generate JWT tokens
  ...

CODE CONTEXT:
[Shows relevant files and code snippets]

CONVERSATION HISTORY:
[Recent agent interactions]

CONTEXT SIZE: 15,234 tokens
```

**When to Use**:
- Agent makes unexpected decisions
- Need to understand why agent skipped information
- Debugging context window issues
- Validating prompt engineering

---

### preview_project_plan.py

Shows the planned project structure before Marcus creates it, allowing validation.

**Features**:
- Previews task breakdown
- Shows dependency graph
- Estimates effort and complexity
- Identifies potential issues

**Usage**:
```bash
# Preview from spec file
python preview_project_plan.py --spec project_spec.md

# Preview with detailed breakdown
python preview_project_plan.py --spec project_spec.md --detailed

# Show as JSON
python preview_project_plan.py --spec project_spec.md --format json

# Include dependency graph
python preview_project_plan.py --spec project_spec.md --show-deps

# Estimate timeline
python preview_project_plan.py --spec project_spec.md --estimate-time
```

**Output**:
```
=== PROJECT PREVIEW ===
Name: Task Management API
Complexity: MEDIUM

TASK BREAKDOWN (15 tasks):

Foundation (3 tasks):
  ✓ task_1: Setup project structure
  ✓ task_2: Configure database
  ✓ task_3: Setup testing framework

Authentication (2 tasks):
  → task_4: User model and migrations
    Depends on: [task_2]
  → task_5: JWT authentication endpoints
    Depends on: [task_4]

...

DEPENDENCY GRAPH:
task_1 → task_2 → task_4 → task_5
              ↘ → task_6 → task_7

ESTIMATES:
  Total Tasks: 15
  Parallelizable: 8 (53%)
  Sequential: 7 (47%)
  Estimated Time: 4-6 hours (with 3 agents)
```

**When to Use**:
- Before creating project (validation)
- Estimating project complexity
- Identifying problematic dependencies
- Optimizing agent allocation

---

### query_memory_data.py

Queries Marcus's stored memory and context data for debugging.

**Features**:
- Search conversation history
- Query decision logs
- Filter by time/agent/project
- Export for analysis

**Usage**:
```bash
# Query recent memories
python query_memory_data.py --recent 24h

# Search by keyword
python query_memory_data.py --search "authentication"

# Filter by agent
python query_memory_data.py --agent agent_backend_001

# Export results
python query_memory_data.py --recent 7d --output memories.json
```

**When to Use**:
- Tracking down when decisions were made
- Understanding agent learning
- Debugging context persistence
- Analyzing conversation patterns

---

### view_experiment_data.py

Views experiment metadata and results from MLflow tracking.

**Features**:
- List all experiments
- Show metrics and parameters
- Compare experiment runs
- Export data for analysis

**Usage**:
```bash
# List recent experiments
python view_experiment_data.py --list

# Show specific experiment
python view_experiment_data.py --experiment-id 12345

# Compare multiple runs
python view_experiment_data.py --compare run1,run2,run3

# Export to CSV
python view_experiment_data.py --experiment-id 12345 --export results.csv
```

**When to Use**:
- Analyzing experiment results
- Comparing configurations
- Generating reports
- Troubleshooting experiment tracking

## Diagnostic Workflows

### Workflow: Agent Stopped Working

```bash
# 1. Capture current state
python analyze_stall.py capture --description "Agent stuck on task 10"

# 2. Check what AI sees
python show_ai_input.py --agent <agent_id>

# 3. Validate task description
python diagnose_task_descriptions.py --task 10

# 4. Check conversation history
cd ../conversation-debugger
python app.py
# Filter by agent and check last messages
```

### Workflow: Poor Task Quality

```bash
# 1. Preview project structure
python preview_project_plan.py --spec project_spec.md

# 2. Diagnose tasks
python diagnose_task_descriptions.py --verbose

# 3. Review problematic tasks
python diagnose_task_descriptions.py --task <task_id> --detailed

# 4. Revise spec and re-preview
vim project_spec.md
python preview_project_plan.py --spec project_spec.md --show-deps
```

### Workflow: Understanding Agent Behavior

```bash
# 1. Check AI context
python show_ai_input.py --agent <agent_id> --full-context

# 2. Query memory
python query_memory_data.py --agent <agent_id> --recent 1h

# 3. View conversation
cd ../conversation-debugger
python app.py
# Filter by agent

# 4. Replay if stalled
cd ../diagnostics
python analyze_stall.py replay <snapshot>
```

## Best Practices

### When to Diagnose

**Proactive** (before issues):
- Preview projects before creation
- Validate task descriptions during planning
- Check AI context regularly during development

**Reactive** (when issues occur):
- Capture stalls immediately when noticed
- Diagnose tasks when agents seem confused
- Query memory when behavior seems inconsistent

### Reading Diagnostic Output

1. **Look for patterns**: Multiple similar issues indicate systemic problems
2. **Check dependencies**: Often root cause is upstream
3. **Validate context**: Ensure AI has necessary information
4. **Compare timelines**: Correlate issues with specific events

### Sharing Diagnostics

When reporting issues:
1. Capture stall snapshot
2. Run diagnose_task_descriptions.py
3. Export show_ai_input.py output
4. Include conversation debugger filters used
5. Note exact timestamps

## Troubleshooting

### "No snapshots found"
- Ensure you've run `analyze_stall.py capture` first
- Check `~/.marcus/stall_snapshots/` exists and has files

### "Cannot connect to board"
- Verify Marcus MCP server is running
- Check credentials in environment variables
- Ensure board exists (use utilities/clear_board.py to verify)

### "Task not found"
- Task may have been deleted or completed
- Check board directly
- Try without `--task` flag to see all tasks

### AI context truncated
- Context may exceed token limits
- Use `--summary` flag instead of `--full-context`
- Check conversation debugger for full history

## Requirements

- Python 3.8+
- Marcus MCP server running
- Access to Marcus project directory
- Kanban board credentials (for board-related operations)

## Support

For diagnostic tool issues:
- Check tool-specific `--help` output
- Review tool logs if available
- Ensure prerequisites are met
- See main dev-tools/README.md for general troubleshooting
