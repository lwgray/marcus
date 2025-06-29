# Marcus Natural Language and AI Features Documentation

## Overview

Marcus now supports natural language project creation and AI-powered task assignment, exposing the intelligent capabilities built in Phases 1-4. This document explains how these features work and how to use them.

## Table of Contents

1. [Natural Language MCP Tools](#natural-language-mcp-tools)
2. [AI-Powered Task Assignment](#ai-powered-task-assignment)
3. [Architecture](#architecture)
4. [Usage Examples](#usage-examples)
5. [Safety Features](#safety-features)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

## Natural Language MCP Tools

### 1. Create Project From Natural Language

**Tool Name**: `create_project_from_natural_language`

**Purpose**: Create a complete project structure from a natural language description.

**How It Works**:
1. **Context Detection** (Phase 1): Detects empty board and activates Creator Mode
2. **PRD Parsing** (Phase 4): Uses AI to parse natural language into structured requirements
3. **Task Generation**: Creates tasks with proper phases and structure
4. **Dependency Inference** (Phase 2): Automatically maps task dependencies
5. **Safety Checks** (Phase 1+3): Ensures deployment tasks depend on implementation
6. **Board Creation**: Creates all tasks on the Kanban board

**Parameters**:
```json
{
  "description": "string - Natural language project description",
  "project_name": "string - Name for the project board",
  "options": {
    "team_size": "integer - Number of developers (default: 3)",
    "tech_stack": ["array of strings - Technologies to use"],
    "deadline": "string - ISO date format deadline"
  }
}
```

**Example Usage**:
```python
result = await create_project_from_natural_language(
    description="I need an e-commerce platform with user accounts, product catalog, shopping cart, and Stripe payments",
    project_name="E-commerce MVP",
    options={
        "team_size": 4,
        "tech_stack": ["React", "Node.js", "PostgreSQL", "Stripe"],
        "deadline": "2024-06-01"
    }
)
```

**Response**:
```json
{
  "success": true,
  "project_name": "E-commerce MVP",
  "tasks_created": 38,
  "phases": ["foundation", "backend", "frontend", "integration", "testing", "deployment"],
  "estimated_days": 45,
  "dependencies_mapped": 27,
  "risk_level": "medium",
  "confidence": 0.87
}
```

### 2. Add Feature Natural Language

**Tool Name**: `add_feature_natural_language`

**Purpose**: Add a new feature to an existing project using natural language.

**How It Works**:
1. **Context Detection** (Phase 1): Detects existing project and activates Adaptive Mode
2. **Feature Parsing**: AI understands the feature requirements
3. **Integration Detection** (Phase 3): Finds where feature connects to existing code
4. **Dependency Mapping** (Phase 2): Links new tasks to existing ones
5. **Safety Checks**: Ensures proper ordering for any deployment tasks
6. **Board Update**: Adds tasks in the appropriate phase

**Parameters**:
```json
{
  "feature_description": "string - Natural language feature description",
  "integration_point": "string - How to integrate (auto_detect|after_current|parallel|new_phase)"
}
```

**Example Usage**:
```python
result = await add_feature_natural_language(
    feature_description="Add wishlist functionality where users can save products for later",
    integration_point="auto_detect"
)
```

**Response**:
```json
{
  "success": true,
  "tasks_created": 5,
  "integration_points": ["user-auth-task-id", "product-model-task-id"],
  "integration_detected": true,
  "confidence": 0.92,
  "feature_phase": "current"
}
```

## AI-Powered Task Assignment

### How It Works

When an agent calls `request_next_task`, Marcus now uses AI to select the optimal task:

1. **Safety Filtering** (Phase 1):
   - Filters out deployment tasks if implementation is incomplete
   - Checks task prerequisites
   - Ensures logical ordering

2. **Dependency Analysis** (Phase 2):
   - Prioritizes tasks that unblock others
   - Identifies critical path tasks
   - Calculates dependency impact scores

3. **AI Matching** (Phase 3):
   - Analyzes agent skills vs task requirements
   - Considers current project phase
   - Evaluates task complexity for the agent

4. **Impact Prediction** (Phase 4):
   - Predicts timeline impact of completing each task
   - Assesses risk reduction
   - Calculates project acceleration potential

5. **Intelligent Selection**:
   - Combines all scores with weighted factors
   - Selects task with highest combined score
   - Falls back to basic logic if AI fails

### Scoring Weights

```python
weights = {
    "skill_match": 0.15,      # Basic skill compatibility
    "priority": 0.15,         # Task priority level
    "dependencies": 0.25,     # Unblocking potential
    "ai_recommendation": 0.30, # AI suitability score
    "impact": 0.15           # Project impact prediction
}
```

## Architecture

### Component Integration

```
┌─────────────────┐
│  Claude Desktop │
└────────┬────────┘
         │ MCP Protocol
         ▼
┌─────────────────────────────────┐
│      Marcus MCP Server          │
│                                 │
│  ┌─────────────────────────┐   │
│  │   New NLP Tools         │   │
│  ├─────────────────────────┤   │
│  │ • create_project_from_  │   │
│  │   natural_language      │   │
│  │ • add_feature_natural_  │   │
│  │   language              │   │
│  └───────────┬─────────────┘   │
│              │                  │
│  ┌───────────▼─────────────┐   │
│  │  Enhanced Task Assignment│   │
│  ├─────────────────────────┤   │
│  │ • Safety checks         │   │
│  │ • Dependency analysis   │   │
│  │ • AI recommendations    │   │
│  │ • Impact prediction     │   │
│  └───────────┬─────────────┘   │
│              │                  │
└──────────────┼──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│     Phase 1-4 Components        │
├─────────────────────────────────┤
│ • Context Detector              │
│ • PRD Parser                    │
│ • Dependency Inferer            │
│ • AI Engine                     │
│ • Safety Checker                │
└─────────────────────────────────┘
```

### Data Flow

1. **Project Creation Flow**:
   ```
   Natural Language → PRD Parser → Task Generator → Dependency Mapper → Safety Checker → Kanban Board
   ```

2. **Task Assignment Flow**:
   ```
   Agent Request → Safety Filter → Dependency Analysis → AI Scoring → Impact Prediction → Task Selection
   ```

## Usage Examples

### Complete Project Creation Workflow

```python
# 1. User describes project to Claude
"I need a recipe sharing platform where users can:
- Create and share recipes with photos
- Rate and comment on recipes  
- Search by ingredients or cuisine
- Save favorites
- Get weekly meal plans

Use React for frontend and Django for backend"

# 2. Claude calls Marcus
result = await create_project_from_natural_language(
    description=user_input,
    project_name="Recipe Platform MVP",
    options={
        "team_size": 3,
        "tech_stack": ["React", "Django", "PostgreSQL"],
        "deadline": "2024-05-15"
    }
)

# 3. Marcus creates structured project
- 42 tasks across 6 phases
- Dependencies mapped (e.g., auth before favorites)
- No deployment without testing
- Estimated 8 weeks with 3 developers
```

### Intelligent Task Assignment Example

```python
# Agent requests task
task = await request_next_task("agent-123")

# Marcus's internal decision process:
1. Available tasks: ["Deploy API", "Write tests", "Fix auth bug"]
2. Safety check: "Deploy API" blocked - tests not complete ❌
3. Dependency check: "Fix auth bug" unblocks 3 tasks ⭐
4. AI analysis: Agent has auth experience (0.9 match)
5. Impact: Fixing auth accelerates project by 2 days
6. Decision: Assign "Fix auth bug" ✅
```

## Safety Features

### Deployment Protection

Marcus enforces these rules:
- **No deployment before implementation**: Deploy tasks automatically depend on all implementation tasks
- **No release without testing**: Release tasks require test completion
- **No production changes without review**: Production tasks need approval tasks

### Example Safety Check

```python
# User tries to deploy incomplete project
if task_name.contains("deploy"):
    incomplete_deps = check_dependencies(task)
    if incomplete_deps:
        return {
            "blocked": True,
            "reason": f"Cannot deploy - {len(incomplete_deps)} tasks incomplete",
            "required": incomplete_deps
        }
```

## Testing

### Running Tests

```bash
# Unit tests (with mocks)
pytest tests/test_mcp_natural_language_tools.py -v

# Test AI task assignment
pytest tests/test_mcp_natural_language_tools.py::TestOptimalTaskAssignmentWithAI -v

# Integration tests (creates real tasks on board)
pytest tests/test_nlp_board_integration.py -v

# Quick verification script
python experiments/verify_nlp_board_creation.py

# Full integration test with detailed output
python tests/test_integration_nlp_board.py
```

### Key Test Scenarios

1. **Unit Tests** (using mocks):
   - Simple project creation
   - Deployment safety enforcement
   - Constraint handling
   - Error recovery
   - Feature parsing
   - Integration detection
   - Dependency mapping
   - Safety checks

2. **Integration Tests** (real board):
   - Project appears on actual Kanban board
   - Feature tasks are created correctly
   - Task properties (labels, priority) preserved
   - Correct task count and structure

3. **AI Assignment Tests**:
   - Unsafe task filtering
   - Dependency prioritization
   - Skill matching
   - Impact prediction

### Board Integration Testing

The integration tests demonstrate that NLP-created projects actually appear on your configured Kanban board:

```python
# Example from test_nlp_board_integration.py
result = await create_project_from_natural_language(
    description="I need a chat application with real-time messaging",
    project_name="Test Project"
)

# Verify on actual board
tasks = await kanban.get_tasks()
our_tasks = [t for t in tasks if "Test Project" in t.title]
assert len(our_tasks) == result["tasks_created"]
```

These tests create real tasks, so they:
- Require a configured Kanban provider (.env file)
- Actually create tasks on your board
- Should be run carefully in production environments
- Leave tasks on the board for manual verification

## Troubleshooting

### Common Issues

1. **"PRD Parser Failed"**
   - Check if description is too vague
   - Ensure tech stack is specified
   - Verify AI engine is initialized

2. **"No tasks assigned"**
   - Check if all tasks are blocked
   - Verify agent skills match available tasks
   - Ensure project state is refreshed

3. **"Integration point not found"**
   - Feature may be too disconnected
   - Try manual integration point selection
   - Check if dependent tasks exist

### Debug Mode

Enable debug logging:
```python
import logging
logging.getLogger("marcus").setLevel(logging.DEBUG)
```

### Fallback Behavior

If AI components fail:
1. Project creation falls back to template-based generation
2. Task assignment falls back to skill/priority matching
3. Feature addition falls back to simple task creation

## Performance Considerations

- **PRD Parsing**: ~2-5 seconds for complex projects
- **Task Assignment**: <500ms with AI analysis
- **Feature Addition**: ~1-2 seconds
- **Caching**: AI responses cached for 5 minutes

## Future Enhancements

1. **Multi-language PRD support**
2. **Visual project timeline generation**
3. **Risk mitigation suggestions**
4. **Team allocation optimization**
5. **Budget estimation**

## API Reference

### Types

```typescript
interface ProjectCreationResult {
  success: boolean;
  project_name: string;
  tasks_created: number;
  phases: string[];
  estimated_days: number;
  dependencies_mapped: number;
  risk_level: "low" | "medium" | "high";
  confidence: number;
  error?: string;
}

interface FeatureAdditionResult {
  success: boolean;
  tasks_created: number;
  integration_points: string[];
  integration_detected: boolean;
  confidence: number;
  feature_phase: string;
  error?: string;
}
```

---

## Summary

Marcus now intelligently handles natural language project creation and uses AI for optimal task assignment. The system prevents common mistakes (like deploying before implementing) while maximizing team productivity through intelligent task selection.

Key benefits:
- **Natural project creation**: Describe what you want, get a structured project
- **Smart feature addition**: Features integrate properly with existing work  
- **Intelligent assignment**: Right task to right person at right time
- **Safety guaranteed**: No more accidental production disasters