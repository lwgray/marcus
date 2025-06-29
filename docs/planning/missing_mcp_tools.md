# Missing MCP Tools in Marcus

## The Problem

Marcus has incredible AI capabilities for project management, but Claude can't access them because the MCP interface only exposes agent/task execution tools, not project creation tools.

## Current Tools (Agent-focused)
```
✅ register_agent
✅ request_next_task  
✅ report_task_progress
✅ report_blocker
✅ get_project_status
```

## Missing Tools (Project Management)

### 1. create_project_from_description
```python
{
    "name": "create_project_from_description",
    "description": "Create a new project from natural language description",
    "inputSchema": {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "Natural language project description or PRD"
            },
            "constraints": {
                "type": "object",
                "properties": {
                    "team_size": {"type": "integer"},
                    "deadline": {"type": "string"},
                    "tech_stack": {"type": "array", "items": {"type": "string"}}
                }
            }
        },
        "required": ["description"]
    }
}
```

### 2. add_feature
```python
{
    "name": "add_feature",
    "description": "Add a new feature to existing project",
    "inputSchema": {
        "type": "object",
        "properties": {
            "feature_description": {
                "type": "string",
                "description": "Natural language description of the feature"
            },
            "project_context": {
                "type": "object",
                "description": "Current project state"
            }
        },
        "required": ["feature_description"]
    }
}
```

### 3. analyze_board
```python
{
    "name": "analyze_board",
    "description": "Analyze current board and suggest improvements",
    "inputSchema": {
        "type": "object",
        "properties": {
            "analysis_type": {
                "type": "string",
                "enum": ["health", "dependencies", "blockers", "optimization"]
            }
        }
    }
}
```

### 4. enrich_tasks
```python
{
    "name": "enrich_tasks",
    "description": "Enhance vague tasks with AI-powered details",
    "inputSchema": {
        "type": "object",
        "properties": {
            "task_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "IDs of tasks to enrich"
            }
        }
    }
}
```

### 5. check_deployment_readiness
```python
{
    "name": "check_deployment_readiness",
    "description": "Check if project is ready for deployment",
    "inputSchema": {
        "type": "object",
        "properties": {
            "environment": {
                "type": "string",
                "enum": ["staging", "production"]
            }
        }
    }
}
```

## Why This Matters

Without these tools, users can't:
- Start new projects with natural language
- Add features naturally
- Get Marcus's intelligent analysis
- Use the AI-powered features from Phases 1-4

The entire intelligent system is hidden behind an agent-only interface!

## Quick Fix

Add a single tool that exposes the core functionality:

```python
{
    "name": "process_natural_language",
    "description": "Process any natural language project management request",
    "inputSchema": {
        "type": "object", 
        "properties": {
            "request": {
                "type": "string",
                "description": "Natural language request (create project, add feature, etc.)"
            },
            "context": {
                "type": "object",
                "description": "Current project/board context"
            }
        },
        "required": ["request"]
    }
}
```

This would let Claude say:
- "process_natural_language": {"request": "Create a todo app with React"}
- "process_natural_language": {"request": "Add user authentication"} 
- "process_natural_language": {"request": "Can we deploy?"}