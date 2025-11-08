"""
Prediction and AI intelligence tools for Marcus MCP.

This module exposes Marcus's AI prediction capabilities for project completion,
task outcomes, blockage probability, and cascade effects analysis.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from mcp.types import Tool

from ...core.models import Task


async def predict_completion_time(
    project_id: Optional[str] = None,
    include_confidence: bool = True,
    state: Any = None,
) -> Dict[str, Any]:
    """
    Predict project completion time with confidence intervals.

    Parameters
    ----------
    project_id : Optional[str]
        Project ID to predict completion for. Uses current project if not provided.
    include_confidence : bool
        Whether to include confidence intervals in the prediction
    state : Any
        Marcus server state

    Returns
    -------
    Dict[str, Any]
        Prediction results including:
        - predicted_completion: ISO format datetime
        - confidence_interval: {low, high} dates
        - current_velocity: tasks per day
        - required_velocity: tasks per day to meet deadline
        - risk_factors: list of high-risk tasks
    """
    if not project_id and state.current_project:
        project_id = state.current_project.id

    if not project_id:
        return {
            "success": False,
            "error": "No project specified or active",
        }

    # Get project context
    project_context = state.get_project_context(project_id)
    if not project_context:
        return {
            "success": False,
            "error": f"Project {project_id} not found",
        }

    # Get memory system
    memory = project_context.memory

    # Use enhanced memory capabilities if available
    if hasattr(memory, "predict_completion_time"):
        prediction = await memory.predict_completion_time(
            project_id, include_confidence=include_confidence
        )
        return {
            "success": True,
            "project_id": project_id,
            **prediction,
        }

    # Fallback to basic prediction
    tasks = await project_context.kanban_provider.get_tasks()
    completed_tasks = [t for t in tasks if t.status == "completed"]
    remaining_tasks = [
        t for t in tasks if t.status in ["todo", "in_progress", "blocked"]
    ]

    if not completed_tasks:
        return {
            "success": True,
            "project_id": project_id,
            "predicted_completion": None,
            "message": "No completed tasks to base prediction on",
        }

    # Calculate velocity
    velocity = len(completed_tasks) / max(
        1, (datetime.now() - project_context.created_at).days
    )

    # Predict completion
    days_to_complete = len(remaining_tasks) / max(0.1, velocity)
    predicted_completion = datetime.now() + timedelta(days=days_to_complete)

    return {
        "success": True,
        "project_id": project_id,
        "predicted_completion": predicted_completion.isoformat(),
        "current_velocity": velocity,
        "remaining_tasks": len(remaining_tasks),
        "estimated_days": days_to_complete,
    }


async def predict_task_outcome(
    task_id: str,
    agent_id: Optional[str] = None,
    state: Any = None,
) -> Dict[str, Any]:
    """
    Predict the outcome of a specific task assignment.

    Parameters
    ----------
    task_id : str
        ID of the task to predict outcome for
    agent_id : Optional[str]
        Agent to evaluate for this task. Uses assigned agent if not provided.
    state : Any
        Marcus server state

    Returns
    -------
    Dict[str, Any]
        Prediction results including:
        - success_probability: 0-1 probability of successful completion
        - estimated_duration: hours to complete
        - blockage_risk: probability of becoming blocked
        - confidence_score: how confident the prediction is
    """
    project_context = state.get_current_project_context()
    if not project_context:
        return {
            "success": False,
            "error": "No active project",
        }

    # Get task details
    task = await project_context.kanban_provider.get_task(task_id)
    if not task:
        return {
            "success": False,
            "error": f"Task {task_id} not found",
        }

    # Use agent_id if provided, otherwise use assigned agent
    if not agent_id and task.assigned_to:
        agent_id = task.assigned_to

    if not agent_id:
        return {
            "success": False,
            "error": "No agent specified for prediction",
        }

    # Get agent details
    agent = project_context.assignment_persistence.get_agent(agent_id)
    if not agent:
        return {
            "success": False,
            "error": f"Agent {agent_id} not found",
        }

    # Use memory system for prediction
    memory = project_context.memory
    if hasattr(memory, "predict_task_outcome"):
        prediction = await memory.predict_task_outcome(agent_id, task)
        return {
            "success": True,
            "task_id": task_id,
            "agent_id": agent_id,
            **prediction,
        }

    # Fallback prediction based on agent history
    agent_stats = await project_context.assignment_persistence.get_agent_statistics(
        agent_id
    )

    return {
        "success": True,
        "task_id": task_id,
        "agent_id": agent_id,
        "success_probability": agent_stats.get("success_rate", 0.8),
        "estimated_duration": agent_stats.get("avg_completion_time", 24),
        "blockage_risk": agent_stats.get("blockage_rate", 0.2),
        "confidence_score": 0.6,  # Lower confidence for fallback
        "method": "statistical_fallback",
    }


async def predict_blockage_probability(
    task_id: str,
    include_mitigation: bool = True,
    state: Any = None,
) -> Dict[str, Any]:
    """
    Predict the probability of a task becoming blocked.

    Parameters
    ----------
    task_id : str
        ID of the task to analyze
    include_mitigation : bool
        Whether to include mitigation suggestions
    state : Any
        Marcus server state

    Returns
    -------
    Dict[str, Any]
        Blockage analysis including:
        - probability: 0-1 probability of blockage
        - likely_causes: list of potential blockers
        - suggested_mitigations: ways to prevent blockage
        - dependencies_at_risk: tasks that might block this one
    """
    project_context = state.get_current_project_context()
    if not project_context:
        return {
            "success": False,
            "error": "No active project",
        }

    # Get task details
    task = await project_context.kanban_provider.get_task(task_id)
    if not task:
        return {
            "success": False,
            "error": f"Task {task_id} not found",
        }

    memory = project_context.memory
    if hasattr(memory, "predict_blockage_probability"):
        prediction = await memory.predict_blockage_probability(
            task, include_mitigation=include_mitigation
        )
        return {
            "success": True,
            "task_id": task_id,
            **prediction,
        }

    # Fallback analysis
    blockers = []
    probability = 0.1  # Base probability

    # Check dependencies
    dependencies = await project_context.kanban_provider.get_task_dependencies(task_id)
    incomplete_deps = [d for d in dependencies if d.status != "completed"]

    if incomplete_deps:
        probability += 0.2 * len(incomplete_deps)
        blockers.extend([f"Waiting for task: {d.name}" for d in incomplete_deps])

    # Check historical blockage patterns
    similar_tasks = await project_context.kanban_provider.find_similar_tasks(task.name)
    blocked_similar = [t for t in similar_tasks if t.blocker]
    if blocked_similar:
        probability += 0.3
        blockers.append(f"Similar tasks had {len(blocked_similar)} blockages")

    mitigations = []
    if include_mitigation and blockers:
        mitigations = [
            "Prioritize dependent tasks",
            "Assign senior developers to dependencies",
            "Break down complex tasks",
            "Schedule regular check-ins",
        ]

    return {
        "success": True,
        "task_id": task_id,
        "probability": min(probability, 0.95),
        "likely_causes": blockers,
        "suggested_mitigations": mitigations,
        "confidence_score": 0.7,
    }


async def predict_cascade_effects(
    task_id: str,
    delay_days: int = 1,
    state: Any = None,
) -> Dict[str, Any]:
    """
    Predict cascade effects if a task is delayed.

    Parameters
    ----------
    task_id : str
        ID of the task to analyze
    delay_days : int
        Number of days of delay to simulate
    state : Any
        Marcus server state

    Returns
    -------
    Dict[str, Any]
        Cascade analysis including:
        - affected_tasks: list of tasks that would be delayed
        - total_delay_impact: cumulative delay in days
        - critical_path_changes: whether critical path is affected
        - project_completion_impact: new predicted completion date
    """
    project_context = state.get_current_project_context()
    if not project_context:
        return {
            "success": False,
            "error": "No active project",
        }

    # Get task and its dependents
    task = await project_context.kanban_provider.get_task(task_id)
    if not task:
        return {
            "success": False,
            "error": f"Task {task_id} not found",
        }

    # Find all dependent tasks
    all_tasks = await project_context.kanban_provider.get_tasks()

    def find_dependents(task_id: str, tasks: List[Task]) -> List[Task]:
        dependents = []
        for t in tasks:
            if task_id in (t.dependencies or []):
                dependents.append(t)
                # Recursively find transitive dependents
                dependents.extend(find_dependents(t.id, tasks))
        return dependents

    affected = find_dependents(task_id, all_tasks)

    # Calculate impact
    total_delay = delay_days * len(affected)

    # Check if on critical path
    critical_tasks = [
        t for t in all_tasks if t.priority == "critical" or t.priority == "high"
    ]
    critical_path_affected = any(t in critical_tasks for t in affected)

    # Calculate new completion date
    current_prediction = await predict_completion_time(
        state.current_project.id, state=state
    )
    if current_prediction.get("predicted_completion"):
        current_date = datetime.fromisoformat(
            current_prediction["predicted_completion"]
        )
        new_completion = current_date + timedelta(days=total_delay)
    else:
        new_completion = None

    return {
        "success": True,
        "task_id": task_id,
        "delay_days": delay_days,
        "affected_tasks": [
            {
                "id": t.id,
                "title": t.name,
                "estimated_delay": delay_days,
            }
            for t in affected
        ],
        "total_delay_impact": total_delay,
        "critical_path_affected": critical_path_affected,
        "project_completion_impact": (
            new_completion.isoformat() if new_completion else None
        ),
        "affected_count": len(affected),
    }


async def get_task_assignment_score(
    task_id: str,
    agent_id: str,
    state: Any = None,
) -> Dict[str, Any]:
    """
    Get assignment score for a specific agent-task pairing.

    Parameters
    ----------
    task_id : str
        ID of the task to evaluate
    agent_id : str
        ID of the agent to evaluate
    state : Any
        Marcus server state

    Returns
    -------
    Dict[str, Any]
        Assignment scoring including:
        - overall_score: 0-100 assignment fitness score
        - skill_match: how well agent skills match task
        - availability_score: agent's current capacity
        - historical_performance: past performance on similar tasks
        - recommendation: whether to assign or not
    """
    project_context = state.get_current_project_context()
    if not project_context:
        return {
            "success": False,
            "error": "No active project",
        }

    # Get task and agent details
    task = await project_context.kanban_provider.get_task(task_id)
    if not task:
        return {
            "success": False,
            "error": f"Task {task_id} not found",
        }

    agent = project_context.assignment_persistence.get_agent(agent_id)
    if not agent:
        return {
            "success": False,
            "error": f"Agent {agent_id} not found",
        }

    # Calculate scores
    skill_match = 0.8  # Default score
    if hasattr(task, "required_skills") and hasattr(agent, "skills"):
        matching_skills = set(task.required_skills) & set(agent.skills)
        skill_match = len(matching_skills) / max(len(task.required_skills), 1)

    # Check availability
    active_tasks = await project_context.assignment_persistence.get_agent_active_tasks(
        agent_id
    )
    availability_score = max(
        0, 1 - (len(active_tasks) / 3)
    )  # Assume 3 tasks is full capacity

    # Historical performance
    agent_stats = await project_context.assignment_persistence.get_agent_statistics(
        agent_id
    )
    historical_score = agent_stats.get("success_rate", 0.8)

    # Calculate overall score
    overall_score = (
        skill_match * 0.4 + availability_score * 0.3 + historical_score * 0.3
    ) * 100

    return {
        "success": True,
        "task_id": task_id,
        "agent_id": agent_id,
        "overall_score": round(overall_score, 1),
        "skill_match": round(skill_match, 2),
        "availability_score": round(availability_score, 2),
        "historical_performance": round(historical_score, 2),
        "active_tasks": len(active_tasks),
        "recommendation": (
            "assign" if overall_score >= 70 else "consider alternatives"
        ),
        "reasoning": (
            f"Agent has {round(skill_match*100)}% skill match and "
            f"{len(active_tasks)} active tasks"
        ),
    }


# Tool definitions for MCP
prediction_tools = [
    Tool(
        name="predict_completion_time",
        description="Predict project completion time with confidence intervals",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project ID (uses current if not provided)",
                },
                "include_confidence": {
                    "type": "boolean",
                    "description": "Include confidence intervals",
                    "default": True,
                },
            },
        },
    ),
    Tool(
        name="predict_task_outcome",
        description="Predict the outcome of a task assignment",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID to predict",
                },
                "agent_id": {
                    "type": "string",
                    "description": "Agent to evaluate (uses assigned if not provided)",
                },
            },
            "required": ["task_id"],
        },
    ),
    Tool(
        name="predict_blockage_probability",
        description="Predict probability of task becoming blocked",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID to analyze",
                },
                "include_mitigation": {
                    "type": "boolean",
                    "description": "Include mitigation suggestions",
                    "default": True,
                },
            },
            "required": ["task_id"],
        },
    ),
    Tool(
        name="predict_cascade_effects",
        description="Predict cascade effects of task delays",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID to analyze",
                },
                "delay_days": {
                    "type": "integer",
                    "description": "Days of delay to simulate",
                    "default": 1,
                },
            },
            "required": ["task_id"],
        },
    ),
    Tool(
        name="get_task_assignment_score",
        description="Get assignment fitness score for agent-task pairing",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID to evaluate",
                },
                "agent_id": {
                    "type": "string",
                    "description": "Agent ID to evaluate",
                },
            },
            "required": ["task_id", "agent_id"],
        },
    ),
]
