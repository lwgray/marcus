"""
Natural Language Processing Tools for Marcus MCP

This module contains tools for natural language project/task creation:
- create_project: Create complete project from natural language description
- add_feature: Add feature to existing project using natural language
"""

from typing import Dict, Any, List, Optional
from src.integrations.mcp_natural_language_tools import (
    create_project_from_natural_language,
    add_feature_natural_language
)


async def create_project(
    description: str,
    project_name: str,
    options: Optional[Dict[str, Any]],
    state: Any
) -> Dict[str, Any]:
    """
    Create a complete project from natural language description.
    
    Uses AI to parse natural language project requirements and automatically:
    - Breaks down into tasks and subtasks
    - Assigns priorities and dependencies
    - Estimates time requirements
    - Creates organized kanban board structure
    
    Args:
        description: Natural language project description
        project_name: Name for the project board
        options: Optional configuration (deadline, team_size, tech_stack)
        state: Marcus server state instance
        
    Returns:
        Dict with created project details and task list
    """
    # Initialize kanban client if needed
    await state.initialize_kanban()
    
    # Create project using natural language processing
    return await create_project_from_natural_language(
        description=description,
        project_name=project_name,
        state=state,
        options=options
    )


async def add_feature(
    feature_description: str,
    integration_point: str,
    state: Any
) -> Dict[str, Any]:
    """
    Add a feature to existing project using natural language.
    
    Uses AI to understand feature requirements and:
    - Creates appropriate tasks for implementation
    - Integrates with existing project structure
    - Sets dependencies and priorities
    - Updates project timeline
    
    Args:
        feature_description: Natural language description of the feature
        integration_point: How to integrate (auto_detect, after_current, parallel, new_phase)
        state: Marcus server state instance
        
    Returns:
        Dict with created feature tasks and integration details
    """
    # Initialize kanban client if needed
    await state.initialize_kanban()
    
    # Add feature using natural language processing
    return await add_feature_natural_language(
        feature_description=feature_description,
        integration_point=integration_point,
        state=state
    )