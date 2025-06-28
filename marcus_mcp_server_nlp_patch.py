"""
Patch to add Natural Language MCP tools to marcus_mcp_server.py

This adds the new tools and updates the task assignment logic.
"""

# Add these imports at the top of marcus_mcp_server.py
additional_imports = """
from mcp_natural_language_tools import (
    create_project_from_natural_language,
    add_feature_natural_language
)
from ai_powered_task_assignment import find_optimal_task_for_agent_ai_powered
"""

# Add these tools to the handle_list_tools() function after the existing tools
additional_tools = """
        types.Tool(
            name="create_project_from_natural_language",
            description="Create a complete project from natural language description",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Natural language project description or requirements"
                    },
                    "project_name": {
                        "type": "string",
                        "description": "Name for the project board"
                    },
                    "options": {
                        "type": "object",
                        "description": "Optional project configuration",
                        "properties": {
                            "team_size": {
                                "type": "integer",
                                "description": "Number of developers",
                                "default": 3
                            },
                            "tech_stack": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Technologies to use"
                            },
                            "deadline": {
                                "type": "string",
                                "description": "Project deadline (ISO date format)"
                            }
                        }
                    }
                },
                "required": ["description", "project_name"]
            }
        ),
        types.Tool(
            name="add_feature_natural_language",
            description="Add a feature to existing project using natural language",
            inputSchema={
                "type": "object",
                "properties": {
                    "feature_description": {
                        "type": "string",
                        "description": "Natural language description of the feature to add"
                    },
                    "integration_point": {
                        "type": "string",
                        "description": "How to integrate the feature",
                        "enum": ["auto_detect", "after_current", "parallel", "new_phase"],
                        "default": "auto_detect"
                    }
                },
                "required": ["feature_description"]
            }
        ),
"""

# Add these handlers to the handle_call_tool() function
additional_handlers = """
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
"""

# Replace the find_optimal_task_for_agent function with this enhanced version
enhanced_find_optimal_task = """
async def find_optimal_task_for_agent(agent_id: str) -> Optional[Task]:
    '''Find the best task for an agent using AI-powered analysis'''
    async with state.assignment_lock:
        agent = state.agent_status.get(agent_id)
        
        if not agent or not state.project_state:
            return None
            
        # Get available tasks
        assigned_task_ids = [a.task_id for a in state.agent_tasks.values()]
        persisted_assigned_ids = await state.assignment_persistence.get_all_assigned_task_ids()
        all_assigned_ids = set(assigned_task_ids) | persisted_assigned_ids | state.tasks_being_assigned
        
        available_tasks = [
            t for t in state.project_tasks
            if t.status == TaskStatus.TODO and
            t.id not in all_assigned_ids
        ]
        
        if not available_tasks:
            return None
        
        # Use AI-powered task selection if AI engine is available
        if state.ai_engine:
            try:
                optimal_task = await find_optimal_task_for_agent_ai_powered(
                    agent_id=agent_id,
                    agent_status=agent.__dict__,
                    project_tasks=state.project_tasks,
                    available_tasks=available_tasks,
                    assigned_task_ids=all_assigned_ids,
                    ai_engine=state.ai_engine
                )
                
                if optimal_task:
                    state.tasks_being_assigned.add(optimal_task.id)
                    return optimal_task
            except Exception as e:
                logger.error(f"AI task assignment failed, falling back to basic: {e}")
        
        # Fallback to basic assignment if AI fails
        return await find_optimal_task_basic(agent_id, available_tasks)


async def find_optimal_task_basic(agent_id: str, available_tasks: List[Task]) -> Optional[Task]:
    '''Basic task assignment logic (fallback)'''
    agent = state.agent_status.get(agent_id)
    if not agent:
        return None
        
    best_task = None
    best_score = -1
    
    for task in available_tasks:
        # Calculate skill match score
        skill_score = 0
        if agent.skills and task.labels:
            matching_skills = set(agent.skills) & set(task.labels)
            skill_score = len(matching_skills) / len(task.labels) if task.labels else 0
            
        # Priority score
        priority_score = {
            Priority.URGENT: 1.0,
            Priority.HIGH: 0.8,
            Priority.MEDIUM: 0.5,
            Priority.LOW: 0.2
        }.get(task.priority, 0.5)
        
        # Combined score
        total_score = (skill_score * 0.6) + (priority_score * 0.4)
        
        if total_score > best_score:
            best_score = total_score
            best_task = task
            
    if best_task:
        state.tasks_being_assigned.add(best_task.id)
        
    return best_task
"""

# Instructions for applying the patch
patch_instructions = """
To apply this patch to marcus_mcp_server.py:

1. Add the imports at the top of the file
2. Add the new tools to the handle_list_tools() function
3. Add the handlers to handle_call_tool() function
4. Replace the find_optimal_task_for_agent() function with the enhanced version

The server will now support:
- Creating projects from natural language descriptions
- Adding features to existing projects
- AI-powered task assignment with safety checks
"""

print(patch_instructions)