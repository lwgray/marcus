# Marcus Natural Language Integration Guide

## Quick Start

### 1. Apply the Changes to marcus_mcp_server.py

Add these imports at the top:
```python
from mcp_natural_language_tools import (
    create_project_from_natural_language,
    add_feature_natural_language
)
from ai_powered_task_assignment import find_optimal_task_for_agent_ai_powered
```

### 2. Add New Tools to handle_list_tools()

Add these after the existing tools:
```python
types.Tool(
    name="create_project_from_natural_language",
    description="Create a complete project from natural language description",
    inputSchema={...}  # See full schema in patch file
),
types.Tool(
    name="add_feature_natural_language", 
    description="Add a feature to existing project using natural language",
    inputSchema={...}  # See full schema in patch file
)
```

### 3. Add Handlers to handle_call_tool()

Add these cases:
```python
elif name == "create_project_from_natural_language":
    result = await create_project_from_natural_language(
        description=arguments.get("description"),
        project_name=arguments.get("project_name"),
        options=arguments.get("options", {})
    )
elif name == "add_feature_natural_language":
    result = await add_feature_natural_language(
        feature_description=arguments.get("feature_description"),
        integration_point=arguments.get("integration_point", "auto_detect")
    )
```

### 4. Update find_optimal_task_for_agent()

Replace the existing function with the AI-powered version that:
- Uses safety filtering to prevent bad assignments
- Analyzes dependencies to prioritize unblocking tasks
- Uses AI to match agents to tasks
- Predicts task impact on project timeline
- Falls back to basic logic if AI fails

## Usage in Claude Desktop

### Creating a Project

```
You: "I need a task management app with teams, projects, and real-time updates"

Claude: I'll create that project for you.
[Calls create_project_from_natural_language]

Result: Created 35 tasks in 5 phases with an estimated timeline of 6 weeks.
```

### Adding Features

```
You: "Add email notifications when tasks are assigned"

Claude: I'll add that feature to your project.
[Calls add_feature_natural_language]

Result: Added 4 tasks for email notifications, integrated with user auth and task assignment.
```

### Task Assignment (Automatic)

When agents request tasks, Marcus now:
1. Filters out unsafe tasks (no deploy before implement)
2. Prioritizes tasks that unblock others
3. Matches agent skills using AI
4. Predicts project impact
5. Assigns the optimal task

## Testing Your Integration

1. **Test Project Creation**:
```bash
# Start Marcus
python marcus.py

# In another terminal
python test_natural_language_integration.py
```

2. **Verify Safety**:
- Create a project
- Try to assign deployment task before implementation
- Should be blocked with clear reason

3. **Check AI Assignment**:
- Register an agent with specific skills
- Request tasks
- Should get tasks matching their skills

## Troubleshooting

### "Module not found" Errors
- Ensure `mcp_natural_language_tools.py` is in the same directory
- Check Python path includes current directory

### "AI engine not initialized"
- Make sure MarcusAIEngine is initialized in state
- Check environment variables for API keys (if using real AI)

### "No tasks assigned"
- Verify project has TODO tasks
- Check agent is registered properly
- Enable debug logging to see decision process

## Next Steps

1. **Customize for Your Needs**:
   - Adjust scoring weights in AI assignment
   - Add domain-specific safety rules
   - Enhance feature parsing for your use cases

2. **Monitor Performance**:
   - Track task assignment efficiency
   - Measure project completion rates
   - Gather agent feedback

3. **Extend Capabilities**:
   - Add more natural language commands
   - Integrate with CI/CD for auto-deployment
   - Add project templates for common types