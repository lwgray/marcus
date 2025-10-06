"""Agent Management Tools for Marcus MCP.

This module contains tools for managing AI agents in the Marcus system:
- register_agent: Register a new agent with skills and role
- get_agent_status: Get current status and tasks for an agent
- list_registered_agents: List all registered agents
"""

from typing import Any, Dict, List

from src.core.models import WorkerStatus
from src.logging.agent_events import log_agent_event
from src.logging.conversation_logger import conversation_logger, log_thinking


async def register_agent(
    agent_id: str, name: str, role: str, skills: List[str], state: Any
) -> Dict[str, Any]:
    """
    Register a new agent with the Marcus system.

    Parameters
    ----------
    agent_id : str
        Unique identifier for the agent
    name : str
        Display name for the agent
    role : str
        Agent's role (e.g., 'Backend Developer')
    skills : List[str]
        List of agent's technical skills
    state : Any
        Marcus server state instance

    Returns
    -------
    Dict[str, Any]
        Dict with success status and registration details
    """
    # Log incoming registration request
    conversation_logger.log_worker_message(
        agent_id,
        "to_pm",
        f"Registering as {role} with skills: {skills}",
        {"name": name, "role": role, "skills": skills},
    )

    try:
        # Log Marcus thinking
        log_thinking(
            "marcus",
            f"New agent registration request from {name}",
            {"agent_id": agent_id, "role": role, "skills": skills},
        )

        # Create worker status with correct field names
        status = WorkerStatus(
            worker_id=agent_id,
            name=name,
            role=role,
            email=None,
            current_tasks=[],
            completed_tasks_count=0,
            capacity=40,  # Default 40 hours/week
            skills=skills or [],
            availability={
                "monday": True,
                "tuesday": True,
                "wednesday": True,
                "thursday": True,
                "friday": True,
                "saturday": False,
                "sunday": False,
            },
            performance_score=1.0,
        )

        state.agent_status[agent_id] = status

        # Log registration event immediately
        state.log_event(
            "worker_registration",
            {
                "worker_id": agent_id,
                "name": name,
                "role": role,
                "skills": skills,
                "source": "mcp_client",
                "target": "marcus",
            },
        )

        # Record in active experiment if one is running
        from src.experiments.live_experiment_monitor import get_active_monitor

        monitor = get_active_monitor()
        if monitor and monitor.is_running:
            monitor.record_agent_registration(
                agent_id=agent_id, name=name, role=role, skills=skills
            )

        # Log conversation event for visualization
        log_agent_event(
            "worker_registration",
            {"worker_id": agent_id, "name": name, "role": role, "skills": skills},
        )

        # Log decision
        conversation_logger.log_pm_decision(
            decision=f"Register agent {name}",
            rationale="Agent skills match project requirements",
            confidence_score=0.95,
            decision_factors={
                "skills_match": True,
                "capacity_available": True,
                "role_needed": True,
            },
        )

        # Log response
        conversation_logger.log_worker_message(
            agent_id,
            "from_pm",
            f"Registration successful. Welcome {name}!",
            {"status": "registered"},
        )

        return {
            "success": True,
            "message": f"Agent {name} registered successfully",
            "agent_id": agent_id,
        }

    except Exception as e:
        conversation_logger.log_worker_message(
            agent_id, "from_pm", f"Registration failed: {str(e)}", {"error": str(e)}
        )
        return {"success": False, "error": str(e)}


async def get_agent_status(agent_id: str, state: Any) -> Dict[str, Any]:
    """
    Get status and current assignment for an agent.

    Parameters
    ----------
    agent_id : str
        The agent's unique identifier
    state : Any
        Marcus server state instance

    Returns
    -------
    Dict[str, Any]
        Dict with agent status, current tasks, and assignment details
    """
    try:
        agent = state.agent_status.get(agent_id)
        if agent:
            result = {
                "success": True,
                "agent": {
                    "id": agent.worker_id,
                    "name": agent.name,
                    "role": agent.role,
                    "skills": agent.skills,
                    "status": (
                        "working" if len(agent.current_tasks) > 0 else "available"
                    ),
                    "current_tasks": [t.id for t in agent.current_tasks],
                    "total_completed": agent.completed_tasks_count,
                    "performance_score": agent.performance_score,
                },
            }

            # Add current assignment details if any
            if len(agent.current_tasks) > 0 and agent.worker_id in state.agent_tasks:
                assignment = state.agent_tasks[agent.worker_id]
                result["current_assignment"] = {
                    "task_id": assignment.task_id,
                    "task_name": assignment.task_name,
                    "assigned_at": assignment.assigned_at.isoformat(),
                    "instructions": assignment.instructions,
                }

            return result
        else:
            return {"success": False, "message": f"Agent {agent_id} not found"}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_registered_agents(state: Any) -> Dict[str, Any]:
    """
    List all registered agents and their current status.

    Parameters
    ----------
    state : Any
        Marcus server state instance

    Returns
    -------
    Dict[str, Any]
        Dict with list of all agents and their details
    """
    try:
        agents = []
        for agent in list(state.agent_status.values()):
            agents.append(
                {
                    "id": agent.worker_id,
                    "name": agent.name,
                    "role": agent.role,
                    "status": (
                        "working" if len(agent.current_tasks) > 0 else "available"
                    ),
                    "skills": agent.skills,
                    "current_tasks": [t.id for t in agent.current_tasks],
                    "total_completed": agent.completed_tasks_count,
                }
            )

        return {"success": True, "agents": agents, "total": len(agents)}

    except Exception as e:
        return {"success": False, "error": str(e)}
