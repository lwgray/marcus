# Task Information Creation Flow

## Overview
This document traces the complete flow of how task information is created in Marcus, from initial project request to final task assignment.

## Task Information Creation Flow

| **Stage** | **Who Creates** | **What Information** | **Code Snippet** | **Where It Goes** |
|-----------|-----------------|---------------------|------------------|-------------------|
| **1. Project Request** | User | Project description | `"Create a simple CLI todo app with features like adding tasks, listing tasks..."` | Input to create_project |
| **2. PRD Analysis** | AI (Claude) | Structured requirements | ```python<br># advanced_parser.py:_analyze_prd_deeply()<br>prompt = f"""Analyze this project requirements document...<br>Extract:<br>- functional_requirements<br>- non_functional_requirements<br>- business_objectives"""``` | Internal processing |
| **3. Task Name Generation** | AI (Claude) | Task names based on type | ```python<br># advanced_parser.py:_generate_design_task()<br>if domain == "crud_operations":<br>    name = "Design CRUD API Architecture"<br>elif domain == "authentication":<br>    name = "Design Authentication Flow"``` | Task object |
| **4. Task Description** | AI (Claude) | Detailed task description | ```python<br># advanced_parser.py:_generate_design_task()<br>description = f"Create architectural design and documentation for {feature_context}. This includes data models, API endpoints, integration patterns..."``` | Task object → Planka card |
| **5. Acceptance Criteria** | AI (Claude) | 5 specific criteria | ```python<br># advanced_parser.py:_generate_acceptance_criteria()<br>criteria = [<br>    "API endpoints documented with request/response formats",<br>    "Data models defined with all fields and relationships",<br>    "Error handling strategies outlined"<br>]``` | Planka checklist |
| **6. Subtasks** | AI (Claude) | 7 breakdown items | ```python<br># advanced_parser.py:_generate_subtasks()<br>subtasks = [<br>    "Define data model structure",<br>    "Design API endpoint specifications",<br>    "Plan database schema"<br>]``` | Planka checklist |
| **7. Planka Card** | Kanban Client | Physical card creation | ```python<br># kanban_client_with_create.py:create_task()<br>await session.call_tool(<br>    "mcp_kanban_card_manager",<br>    {<br>        "action": "create",<br>        "name": card_name,<br>        "description": card_description<br>    }<br>)``` | Planka board |
| **8. Instructions** | AI (Claude) | Detailed work instructions | ```python<br># ai_analysis_engine.py:generate_task_instructions()<br>prompt = f"""Generate detailed instructions for: {task.name}<br>Task type: {task_type}<br>Include:<br>- Step-by-step guide<br>- Technical specifications<br>- Best practices"""``` | Agent assignment only |
| **9. Enhanced Context** | Marcus | Dependencies, predictions | ```python<br># task.py:build_tiered_instructions()<br>if dependency_awareness:<br>    instructions_parts.append(<br>        f"🔗 DEPENDENCY AWARENESS:\n{dependency_awareness}"<br>    )``` | Agent assignment only |

## Complete Flow Details

### 1. Entry Point: create_project MCP Command
- User calls `create_project` with:
  - `description`: Natural language project description
  - `project_name`: Name for the project
  - `options`: Complexity, deployment, team_size, tech_stack, deadline

### 2. Pipeline Tracking Initialization
- `src/marcus_mcp/tools/nlp.py`: Creates flow_id, initializes pipeline tracking
- `src/integrations/pipeline_tracked_nlp.py`: Wraps NLP tools with pipeline visualization

### 3. PRD Analysis Phase
- `src/ai/advanced/prd/advanced_parser.py`: `_analyze_prd_deeply()`
  - Uses Claude to analyze project description
  - Extracts functional requirements, non-functional requirements, constraints
  - Generates structured analysis with business objectives and technical constraints

### 4. Task Generation Phase
- `src/ai/advanced/prd/advanced_parser.py`: `parse_prd_to_tasks()`
  - **Task Hierarchy Creation**: `_generate_task_hierarchy()`
    - Creates epics from functional requirements
    - Breaks down each epic into tasks (design, implement, test)
    - Filters based on project size/complexity

  - **Detailed Task Creation**: `_create_detailed_tasks()`
    - For each task in hierarchy:
      - Calls `_generate_detailed_task()`
      - Which calls `_enhance_task_with_ai()`
      - Which generates task name and description using methods like:
        - `_generate_design_task()`: Creates design task names/descriptions
        - `_generate_implementation_task()`: Creates implementation task names/descriptions
        - `_generate_testing_task()`: Creates testing task names/descriptions

### 5. Task Name Generation
The task names are generated based on:
- **Task Type** (design/implement/test)
- **Feature Context** from PRD analysis
- **Domain Detection** (CRUD, authentication, frontend, etc.)

### 6. Task Enhancement
Each task gets:
- **Name**: Context-aware, descriptive title
- **Description**: Detailed explanation of what to do
- **Labels**: Component, type, priority, skill, complexity labels
- **Acceptance Criteria**: 5 specific criteria for completion
- **Subtasks**: 7 breakdown items as checklist
- **Estimated Hours**: Based on task type
- **Dependencies**: Inferred by AI

### 7. Safety Checks & Kanban Creation
- `src/integrations/nlp_base.py`: `create_tasks_on_board()`
  - Applies safety checks (deployment depends on testing, etc.)
  - For each task, calls kanban client

### 8. Planka Task Creation
- `src/integrations/kanban_client_with_create.py`: `create_task()`
  - Finds target list (Backlog/TODO)
  - Creates card with name and description
  - Adds labels (creates if needed)
  - Adds checklist items (acceptance criteria + subtasks)
  - Adds metadata comment (priority, estimated hours, dependencies)

### 9. Task Assignment & Instructions
When an agent requests a task:
- `src/marcus_mcp/tools/task.py`: `request_next_task()`
  - Finds optimal task for agent
  - Calls `generate_task_instructions()` on AI engine

- `src/integrations/ai_analysis_engine.py`: `generate_task_instructions()`
  - Uses Claude with task-type specific prompt
  - Generates detailed, contextual instructions for the agent
  - Builds tiered instructions with context, dependencies, predictions

### 10. What Gets Stored in Planka
The final task in Planka contains:
- **Title**: The generated task name (e.g., "Design CRUD API Architecture")
- **Description**: The generated detailed description
- **Labels**: All the generated labels
- **Checklist Items**:
  - Acceptance criteria (prefixed with ✓)
  - Subtasks (prefixed with •)
- **Comments**: Metadata like priority, estimated hours, dependencies

## Key Insights

1. **Task names are AI-generated** based on PRD analysis and context
2. **Instructions are generated separately** when tasks are assigned to agents
3. **The description stored in Planka** is the initial task description, not the full instructions
4. **Full instructions are only generated** when an agent requests the task
5. **Instructions are enhanced** with context, dependencies, and predictions at assignment time

## Identified Issues

### The Truncation Problem
The **truncated description** ending with "...kjjkj" appears to be happening in stage 4, where the AI generates the task description. This could be due to:
1. Token limits in the AI response
2. String truncation in the processing
3. A bug in the task enhancement process

The **instructions** (stage 8) are much more detailed because they're generated separately with a different prompt specifically for the agent when they request work.

## Potential Solutions

1. **Fix the truncation issue** - Debug the AI task generation to prevent description truncation
2. **Add instructions to the card** - Modify task creation to include both description AND instructions
3. **Use comments for detailed instructions** - Extend metadata comments to include full instructions
4. **Improve task description generation** - Enhance the AI prompts to generate better initial descriptions

## Full Example: CLI Todo App

### 1. User Input
```python
create_project(
    description="Create a simple CLI todo app with features like adding tasks, listing tasks, marking tasks as complete, and deleting tasks",
    project_name="CLI Todo App",
    options={"complexity": "prototype", "tech_stack": ["Python", "Click"]}
)
```

### 2. PRD Analysis Result
```json
{
  "functional_requirements": [
    {
      "name": "Task Management",
      "description": "Core CRUD operations for managing todo items",
      "sub_features": [
        "Add new tasks with descriptions",
        "List all tasks with status indicators",
        "Mark tasks as complete/incomplete",
        "Delete existing tasks"
      ]
    },
    {
      "name": "CLI Interface",
      "description": "Command-line interface for user interactions",
      "sub_features": [
        "Command parsing and validation",
        "Help documentation",
        "Error handling and user feedback"
      ]
    },
    {
      "name": "Data Persistence",
      "description": "Store tasks between sessions",
      "sub_features": [
        "Save tasks to local file",
        "Load tasks on startup",
        "Handle file corruption gracefully"
      ]
    }
  ],
  "non_functional_requirements": [
    "Simple and intuitive command syntax",
    "Fast response times",
    "Cross-platform compatibility"
  ]
}
```

### 3. Generated Task Hierarchy
```
Epic: Task Management
├── Design Task Management System
├── Implement Task Management Operations
└── Test Task Management Features

Epic: CLI Interface
├── Design CLI Command Structure
├── Implement CLI Interface
└── Test CLI Commands

Epic: Data Persistence
├── Design Data Storage Format
├── Implement File Persistence
└── Test Data Persistence
```

### 4. Example Task Generation: "Design Add Tasks"

**Generated by AI:**
```python
{
  "name": "Design Add Tasks",
  "description": "Design the architecture for adding new tasks to the todo list. Define the data model for tasks including required fields (id, description, status, created_at). Plan the command syntax for the 'add' command. Document the workflow from user input to task storage.",
  "priority": "high",
  "estimated_hours": 2,
  "labels": ["design", "backend", "task-management"],
  "acceptance_criteria": [
    "Task data model documented with all fields",
    "CLI command syntax defined (e.g., 'todo add \"Buy groceries\"')",
    "Error scenarios identified and documented",
    "Storage format specified (JSON structure)",
    "Input validation rules defined"
  ],
  "subtasks": [
    "Define task data structure (id, description, status, timestamps)",
    "Design CLI command syntax for add operation",
    "Plan input validation and error handling",
    "Document storage format for tasks",
    "Create workflow diagram for add operation",
    "Define success/error messages for users",
    "Plan integration with persistence layer"
  ]
}
```

### 5. What Gets Created in Planka

**Card Title:** "Design Add Tasks"

**Card Description:**
```
Design the architecture for adding new tasks to the todo list. Define the data model for tasks including required fields (id, description, status, created_at). Plan the command syntax for the 'add' command. Document the workflow from user input to task storage.
```

**Labels:** `design`, `backend`, `task-management`, `high-priority`

**Checklist:**
```
✓ Task data model documented with all fields
✓ CLI command syntax defined (e.g., 'todo add "Buy groceries"')
✓ Error scenarios identified and documented
✓ Storage format specified (JSON structure)
✓ Input validation rules defined
• Define task data structure (id, description, status, timestamps)
• Design CLI command syntax for add operation
• Plan input validation and error handling
• Document storage format for tasks
• Create workflow diagram for add operation
• Define success/error messages for users
• Plan integration with persistence layer
```

**Comment:**
```
📋 Task Metadata
Priority: high
Estimated Hours: 2.0
Dependencies: []
Type: design
Component: task-management
```

### 6. When Agent Requests This Task

**Generated Instructions (NOT in Planka):**
```
Since the task type is "design", here are the instructions:

# Design Add Tasks

**Objective:** Plan and design the architecture and specifications for allowing users to add new tasks to the todo list in the CLI application.

**Steps:**

1. **Define Data Model**
   - Design the data structure to represent a task
   - Required fields: id (unique identifier), description (task text), status (complete/incomplete), created_at (timestamp)
   - Consider optional fields: due_date, priority, tags
   - Document as Python dataclass or dictionary structure

2. **Plan CLI Command Syntax**
   - Design intuitive command: `todo add "Task description"`
   - Consider options: `--priority high`, `--due tomorrow`
   - Document all command variations and options

3. **Design Storage Format**
   - Specify JSON structure for tasks file
   - Example:
     ```json
     {
       "tasks": [
         {
           "id": "uuid-here",
           "description": "Buy groceries",
           "status": "incomplete",
           "created_at": "2024-01-15T10:00:00Z"
         }
       ]
     }
     ```

4. **Plan Error Handling**
   - Empty task description
   - File access errors
   - Duplicate task handling

5. **Document Design Decisions**
   - Create a design document with all specifications
   - Include data flow diagram
   - Justify technology choices

**Acceptance Criteria:**
- Detailed design documentation covering data model, CLI syntax, and storage format
- Error scenarios documented with handling strategies
- Clear specifications that can be directly implemented

**Dependencies:**
- Understanding of Click framework for Python CLI apps
- Knowledge of JSON file handling in Python

🔗 DEPENDENCY AWARENESS:
2 future tasks depend on your work:
- Test List Tasks (needs: Documented endpoints with example requests/responses for testing)
- Test Add Tasks (needs: Documented endpoints with example requests/responses for testing)

Consider these future needs when making implementation decisions.
```

### 7. The Truncation Issue

In your case, the description is showing as:
```
"Research and design architecture for data analytics platform. Create documentation defining approach, patterns, and specifications. Plan component structure and integration points. Deliverables: design documentation, architectural diagrams, and technical specifications. Goal: Provide a simple and efficient way to manage tasks and todo lists. Specific requirement: Allow users to add new tasks to the todo list...kjjkj"
```

This appears to be:
1. A mix of generic task description template
2. Partially correct content about todo lists
3. Truncated ending with "...kjjkj"

The issue is likely in the `_generate_design_task()` method where the AI response is being truncated or corrupted during processing.
