"""
Context Tools for Marcus MCP

This module contains tools for context management:
- log_decision: Log architectural decisions
- get_task_context: Get context for a specific task
"""

from typing import Any, Dict


async def log_decision(
    agent_id: str, task_id: str, decision: str, state: Any
) -> Dict[str, Any]:
    """
    Log an architectural decision made during task implementation.

    Agents use this to document important technical choices that might
    affect other tasks. Decisions are automatically cross-referenced
    to dependent tasks.

    Args:
        agent_id: The agent making the decision
        task_id: Current task ID
        decision: Natural language description of the decision
        state: Marcus server state instance

    Returns:
        Dict with success status and decision details
    """
    try:
        # Check if Context system is available
        if not hasattr(state, "context") or not state.context:
            return {"success": False, "error": "Context system not enabled"}

        # Parse decision from natural language
        # Expected format: "I chose X because Y. This affects Z."
        parts = decision.split(".", 2)

        what = decision  # Default to full decision
        why = "Not specified"
        impact = "May affect dependent tasks"

        # Try to parse structured format
        if len(parts) >= 1 and "because" in parts[0]:
            what_parts = parts[0].split("because", 1)
            what = what_parts[0].strip()
            if len(what_parts) > 1:
                why = what_parts[1].strip()

        if len(parts) >= 2 and any(
            word in parts[1].lower() for word in ["affect", "impact", "require"]
        ):
            impact = parts[1].strip()

        # Log the decision
        logged_decision = await state.context.log_decision(
            agent_id=agent_id, task_id=task_id, what=what, why=why, impact=impact
        )

        # Add comment to task if kanban is available
        if state.kanban_client:
            comment = f"🏗️ ARCHITECTURAL DECISION by {agent_id}\\n"
            comment += f"Decision: {what}\\n"
            comment += f"Reasoning: {why}\\n"
            comment += f"Impact: {impact}"

            await state.kanban_client.add_comment(task_id, comment)

        # Log event (non-blocking)
        if hasattr(state, "events") and state.events:
            await state.events.publish_nowait(
                "decision_logged", agent_id, logged_decision.to_dict()
            )

        return {
            "success": True,
            "decision_id": logged_decision.decision_id,
            "message": "Decision logged and cross-referenced to dependent tasks",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_task_context(task_id: str, state: Any) -> Dict[str, Any]:
    """
    Get the full context for a specific task.

    This is useful for agents who want to understand the broader
    context of their work or review decisions made on dependencies.

    Args:
        task_id: The task to get context for
        state: Marcus server state instance

    Returns:
        Dict with task context including implementations, dependencies, and decisions
    """
    try:
        # Check if Context system is available
        if not hasattr(state, "context") or not state.context:
            return {"success": False, "error": "Context system not enabled"}

        # Find the task
        task = None
        for t in state.project_tasks:
            if t.id == task_id:
                task = t
                break

        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        # Get context
        context = await state.context.get_context(task_id, task.dependencies or [])

        return {"success": True, "context": context.to_dict()}

    except Exception as e:
        return {"success": False, "error": str(e)}
