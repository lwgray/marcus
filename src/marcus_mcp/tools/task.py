"""
Task Management Tools for Marcus MCP.

This module contains tools for task operations in the Marcus system:
- request_next_task: Get optimal task assignment for an agent
- report_task_progress: Update progress on assigned tasks
- report_blocker: Report blockers with AI-powered suggestions
- unassign_task: Manually unassign a task from an agent
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.ai_powered_task_assignment import find_optimal_task_for_agent_ai_powered
from src.core.models import Priority, Task, TaskAssignment, TaskStatus
from src.logging.agent_events import log_agent_event
from src.logging.conversation_logger import conversation_logger, log_thinking
from src.marcus_mcp.utils import serialize_for_mcp

logger = logging.getLogger(__name__)


async def get_project_board_context(state: Any) -> Dict[str, Optional[str]]:
    """
    Extract project and board context from state.

    Parameters
    ----------
    state : Any
        Marcus server state instance

    Returns
    -------
    Dict[str, Optional[str]]
        Dictionary with project_id, project_name, board_id, board_name
        (values are None if not available)
    """
    context: Dict[str, Optional[str]] = {
        "project_id": None,
        "project_name": None,
        "board_id": None,
        "board_name": None,
    }

    try:
        # Get active project from registry
        if hasattr(state, "project_registry") and state.project_registry:
            active_project = await state.project_registry.get_active_project()
            if active_project:
                context["project_id"] = active_project.id
                context["project_name"] = active_project.name

                # Extract board_id from provider_config
                provider_config = active_project.provider_config or {}

                if active_project.provider == "planka":
                    context["board_id"] = provider_config.get("board_id")
                    # Board name might not be available, we could fetch it
                    # from kanban client if needed
                elif active_project.provider == "github":
                    # GitHub uses repo as the "board"
                    context["board_id"] = provider_config.get("repo")
                    context["board_name"] = provider_config.get("repo")
                elif active_project.provider == "linear":
                    # Linear uses team_id and project_id
                    context["board_id"] = provider_config.get("team_id")
                    context["board_name"] = provider_config.get("team_id")

    except Exception as e:
        logger.debug(f"Error extracting project/board context: {e}")

    return context


def build_tiered_instructions(
    base_instructions: str,
    task: Task,
    context_data: Optional[Dict[str, Any]],
    dependency_awareness: Optional[str],
    predictions: Optional[Dict[str, Any]],
) -> str:
    """
    Build tiered instructions based on task context and complexity.

    Parameters
    ----------
    base_instructions : str
        Base instructions always included
    task : Task
        Task to build instructions for
    context_data : Optional[Dict[str, Any]]
        Context data including previous implementations
    dependency_awareness : Optional[str]
        Dependency awareness message if task has dependents
    predictions : Optional[Dict[str, Any]]
        AI predictions and warnings if available

    Returns
    -------
    str
        Tiered instructions with appropriate layers

    Notes
    -----
    Instruction layers:
    1. Base instructions (always included)
    2. Subtask context (if this is a subtask)
    3. Implementation context (if previous work exists)
    4. Dependency awareness (if task has dependents)
    5. Decision logging (if task affects others)
    6. Predictions and warnings (if available)
    """
    instructions_parts = [base_instructions]

    # Layer 1.5: Subtask Context (if this is a subtask)
    if hasattr(task, "_is_subtask") and task._is_subtask:
        parent_name = getattr(task, "_parent_task_name", "parent task")

        # Calculate realistic time budget for subtask
        # estimated_hours is already in reality-based format (minutes/60)
        estimated_minutes = task.estimated_hours * 60

        # Get complexity level (default to standard if not set)
        complexity = getattr(task, "_complexity", "standard")

        # Complexity-specific guidance (generic for all task types)
        COMPLEXITY_GUIDANCE = {
            "prototype": {
                "scope": "Minimal - core functionality only",
                "quality": "Works for the happy path",
                "effort": "Quick implementation",
            },
            "standard": {
                "scope": "Complete - production-ready",
                "quality": "Handles errors, maintainable",
                "effort": "Thorough implementation",
            },
            "enterprise": {
                "scope": "Comprehensive - all edge cases",
                "quality": "Production-grade, extensively validated",
                "effort": "Complete with reviews",
            },
        }

        guidance = COMPLEXITY_GUIDANCE.get(complexity, COMPLEXITY_GUIDANCE["standard"])

        instructions_parts.append(
            f"\n\n⏱️ TIME BUDGET: {estimated_minutes:.0f} MINUTES\n"
            f"Complexity Mode: {complexity.upper()}\n\n"
            f"This is a SUBTASK - complete it in ~{estimated_minutes:.0f} minutes.\n\n"
            f"{complexity.upper()} MODE EXPECTATIONS:\n"
            f"- Scope: {guidance['scope']}\n"
            f"- Quality: {guidance['quality']}\n"
            f"- Effort: {guidance['effort']}\n\n"
            f"📋 SUBTASK CONTEXT:\n"
            f"This is a SUBTASK of the larger task: '{parent_name}'\n\n"
            f"FOCUS ONLY on completing this specific subtask:\n"
            f"  Task: {task.name}\n"
            f"  Description: {task.description}\n\n"
            f"Do NOT work on the full parent task - only complete this "
            f"specific subtask. Other agents will handle the remaining subtasks."
        )

    # Layer 2: Implementation Context
    if context_data and context_data.get("previous_implementations"):
        impl_count = len(context_data["previous_implementations"])
        instructions_parts.append(
            f"\n\n📚 IMPLEMENTATION CONTEXT:\n{impl_count} relevant "
            "implementations found. Use these patterns and interfaces to "
            "maintain consistency."
        )

    # Layer 3: Dependency Awareness
    if dependency_awareness:
        instructions_parts.append(
            f"\n\n🔗 DEPENDENCY AWARENESS:\n{dependency_awareness}\n\n"
            "Consider these future needs when making implementation decisions. "
            "Your choices will directly impact these dependent tasks."
        )

    # Layer 4: Decision Logging Prompt
    if context_data and len(context_data.get("dependent_tasks", [])) > 2:
        # High-impact task with many dependents
        instructions_parts.append(
            "\n\n📝 ARCHITECTURAL DECISIONS:\n"
            "This task has significant downstream impact. When making "
            "technical choices that affect other tasks:\n"
            "Use: 'Marcus, log decision: I chose [WHAT] because [WHY]. "
            "This affects [IMPACT].'\n"
            "Examples:\n"
            "- 'I chose JWT tokens because mobile apps need stateless "
            "auth. This affects all API endpoints.'\n"
            "- 'I chose PostgreSQL because we need ACID compliance. "
            "This affects all data models.'"
        )

    # Layer 5: Predictions and Warnings
    if predictions:
        risk_parts = []

        # Success probability warning
        if predictions.get("success_probability", 1.0) < 0.6:
            risk_parts.append(
                f"⚠️ Success probability: "
                f"{predictions['success_probability']:.0%} - Extra care needed"
            )

        # Enhanced completion time prediction
        if predictions.get("completion_time"):
            ct = predictions["completion_time"]
            risk_parts.append(
                f"⏱️ Expected duration: {ct['expected_hours']:.1f} hours "
                + f"({ct['confidence_interval']['lower']:.1f}-"
                + f"{ct['confidence_interval']['upper']:.1f} hours)"
            )
            if ct.get("factors"):
                risk_parts.append("   Time factors: " + "; ".join(ct["factors"][:2]))

        # Detailed blockage analysis
        if predictions.get("blockage_analysis"):
            ba = predictions["blockage_analysis"]
            if ba["overall_risk"] > 0.5:
                risk_parts.append(f"⚠️ High blockage risk: {ba['overall_risk']:.0%}")
                # Show top blockers
                if ba.get("risk_breakdown"):
                    top_risks = sorted(
                        ba["risk_breakdown"].items(), key=lambda x: x[1], reverse=True
                    )[:2]
                    for risk_type, probability in top_risks:
                        risk_parts.append(f"   • {risk_type}: {probability:.0%} chance")
                # Add preventive measures
                if ba.get("preventive_measures"):
                    risk_parts.append("💡 Prevention tips:")
                    for measure in ba["preventive_measures"][:2]:
                        risk_parts.append(f"   • {measure}")

        # Cascade effects warning
        if predictions.get("cascade_effects") and predictions["cascade_effects"].get(
            "critical_path_impact"
        ):
            ce = predictions["cascade_effects"]
            risk_parts.append(
                f"🌊 CASCADE WARNING: Delays will impact "
                f"{len(ce['affected_tasks'])} dependent tasks"
            )
            if ce.get("mitigation_options"):
                risk_parts.append(f"   Mitigation: {ce['mitigation_options'][0]}")

        # Performance trajectory insights
        if predictions.get("performance_trajectory"):
            pt = predictions["performance_trajectory"]
            if pt.get("improving_skills"):
                skill_names = list(pt["improving_skills"].keys())[:1]
                if skill_names:
                    risk_parts.append(
                        f"📈 You're improving in {skill_names[0]} - "
                        "great opportunity to excel!"
                    )
            if pt.get("recommendations"):
                risk_parts.append(f"💡 {pt['recommendations'][0]}")

        if risk_parts:
            instructions_parts.append(
                "\n\n⚡ PREDICTIONS & INSIGHTS:\n" + "\n".join(risk_parts)
            )

    # Layer 6: Task-specific guidance based on labels
    if task.labels:
        guidance_parts = []

        # API tasks
        if any(label.lower() in ["api", "endpoint", "rest"] for label in task.labels):
            guidance_parts.append(
                "🌐 API Guidelines: Follow RESTful conventions, "
                "include proper error handling, document response formats"
            )

        # Frontend tasks
        if any(
            label.lower() in ["frontend", "ui", "react", "vue"] for label in task.labels
        ):
            guidance_parts.append(
                "🎨 Frontend Guidelines: Ensure responsive design, "
                "follow component patterns, handle loading/error states"
            )

        # Database tasks
        if any(
            label.lower() in ["database", "migration", "schema"]
            for label in task.labels
        ):
            guidance_parts.append(
                "🗄️ Database Guidelines: Include rollback migrations, "
                "test with sample data, document schema changes"
            )

        # Security tasks
        if any(
            label.lower() in ["security", "auth", "authentication"]
            for label in task.labels
        ):
            guidance_parts.append(
                "🔒 Security Guidelines: Follow OWASP best practices, "
                "implement proper validation, use secure defaults"
            )

        if guidance_parts:
            instructions_parts.append(
                "\n\n💡 TASK-SPECIFIC GUIDANCE:\n" + "\n".join(guidance_parts)
            )

    return "\n".join(instructions_parts)


async def calculate_retry_after_seconds(state: Any) -> Dict[str, Any]:
    """
    Calculate intelligent wait time before next task request.

    Uses:
    - Current progress of IN_PROGRESS tasks
    - Historical median task duration
    - Task dependencies to find soonest unblocking event

    Parameters
    ----------
    state : Any
        Marcus server state instance

    Returns
    -------
    Dict[str, Any]
        Dictionary with:
        - retry_after_seconds: int (wait time in seconds)
        - reason: str (explanation for the wait time)
        - blocking_task: Optional[Dict] (task that's blocking progress)
    """
    # Get all IN_PROGRESS tasks with their assignments
    in_progress_tasks = []
    for agent_id, assignment in state.agent_tasks.items():
        task = next(
            (t for t in state.project_tasks if t.id == assignment.task_id), None
        )
        if task and task.status == TaskStatus.IN_PROGRESS:
            in_progress_tasks.append({"task": task, "assignment": assignment})

    # If no tasks in progress, use default wait time
    if not in_progress_tasks:
        return {
            "retry_after_seconds": 300,  # 5 minutes
            "reason": "No tasks currently in progress - check back soon",
            "blocking_task": None,
        }

    # Get historical median duration
    global_median_hours = 1.0  # Default fallback
    if hasattr(state, "memory") and state.memory:
        global_median_hours = await state.memory.get_global_median_duration()

    # Calculate ETA for each in-progress task
    completion_estimates = []
    now = datetime.now()

    for item in in_progress_tasks:
        task = item["task"]
        assignment = item["assignment"]

        # Get current progress (0-100)
        progress = getattr(task, "progress", 0) or 0

        # Calculate elapsed time in seconds
        elapsed_seconds = (now - assignment.assigned_at).total_seconds()

        # Estimate remaining time
        if progress > 0 and progress < 100:
            # Use actual progress to estimate
            estimated_total_seconds = (elapsed_seconds / progress) * 100
            remaining_seconds = estimated_total_seconds - elapsed_seconds
        else:
            # Fall back to historical median
            remaining_seconds = global_median_hours * 3600  # Convert hours to seconds

        # Ensure non-negative
        remaining_seconds = max(0, remaining_seconds)

        # Check how many tasks this will unblock
        dependent_task_ids = [
            t.id for t in state.project_tasks if task.id in (t.dependencies or [])
        ]

        completion_estimates.append(
            {
                "task_id": task.id,
                "task_name": task.name,
                "progress": progress,
                "eta_seconds": remaining_seconds,
                "unlocks_count": len(dependent_task_ids),
            }
        )

    # Sort by ETA (soonest first)
    completion_estimates.sort(key=lambda x: x["eta_seconds"])

    # Get the soonest completion
    soonest = completion_estimates[0]

    # Add a buffer (minimum 30 seconds, or 10% of estimate)
    buffer_seconds = max(30, soonest["eta_seconds"] * 0.1)
    retry_after = int(soonest["eta_seconds"] + buffer_seconds)

    # Cap maximum wait time at 1 hour
    retry_after = min(retry_after, 3600)

    # Format reason
    eta_minutes = int(soonest["eta_seconds"] / 60)
    reason = (
        f"Waiting for '{soonest['task_name']}' to complete "
        f"(~{eta_minutes} min, {soonest['progress']}% done)"
    )

    return {
        "retry_after_seconds": retry_after,
        "reason": reason,
        "blocking_task": {
            "id": soonest["task_id"],
            "name": soonest["task_name"],
            "progress": soonest["progress"],
            "eta_seconds": int(soonest["eta_seconds"]),
        },
    }


async def request_next_task(agent_id: str, state: Any) -> Any:
    """
    Agents call this to request their next optimal task.

    Uses AI-powered task matching to find the best task based on:
    - Agent skills and experience
    - Task priority and dependencies
    - Current workload distribution

    Parameters
    ----------
    agent_id : str
        The requesting agent's ID
    state : Any
        Marcus server state instance

    Returns
    -------
    Any
        Dict with task details and instructions if successful
    """
    # Get project/board context
    project_context = await get_project_board_context(state)

    # Log task request
    conversation_logger.log_worker_message(
        agent_id,
        "to_pm",
        "Requesting next task",
        {"worker_info": f"Worker {agent_id} requesting task", **project_context},
    )

    try:
        # Log the task request immediately
        state.log_event(
            "task_request",
            {"worker_id": agent_id, "source": agent_id, "target": "marcus"},
        )

        # Log conversation event for visualization
        log_agent_event("task_request", {"worker_id": agent_id})

        # Initialize kanban if needed
        await state.initialize_kanban()

        # Log Marcus thinking about refreshing state
        log_thinking("marcus", "Need to check current project state")

        # Get current project state
        await state.refresh_project_state()

        # Log thinking about finding task
        agent = state.agent_status.get(agent_id)
        if agent:
            log_thinking(
                "marcus",
                f"Finding optimal task for {agent.name}",
                {
                    "agent_skills": agent.skills,
                    "current_workload": len(agent.current_tasks),
                },
            )

            # CRITICAL: Enforce one-task-per-agent rule
            if agent.current_tasks:
                logger.warning(
                    f"Agent {agent_id} ({agent.name}) already has "
                    f"{len(agent.current_tasks)} task(s): "
                    f"{[t.name for t in agent.current_tasks]}. "
                    "Rejecting new task request."
                )
                conversation_logger.log_worker_message(
                    agent_id,
                    "from_pm",
                    "Task request denied - complete current task first",
                    {
                        "current_tasks": [t.id for t in agent.current_tasks],
                        "reason": "one_task_per_agent_rule",
                        **project_context,
                    },
                )
                return {
                    "success": False,
                    "error": (
                        "You already have a task assigned. Please complete "
                        "or report blocker on current task before "
                        "requesting another."
                    ),
                    "current_task": {
                        "id": agent.current_tasks[0].id,
                        "name": agent.current_tasks[0].name,
                        "status": agent.current_tasks[0].status.value,
                    },
                }

        # Find optimal task for this agent
        optimal_task = await find_optimal_task_for_agent(agent_id, state)

        if optimal_task:
            try:
                # Get implementation context if using GitHub
                previous_implementations = None
                if state.provider == "github" and state.code_analyzer:
                    owner = os.getenv("GITHUB_OWNER")
                    repo = os.getenv("GITHUB_REPO")
                    impl_details = await state.code_analyzer.get_implementation_details(
                        optimal_task.dependencies, owner, repo
                    )
                    if impl_details:
                        previous_implementations = impl_details

                # Get enhanced context if Context system is available
                context_data = None
                dependency_awareness = None

                # Skip context building during project creation to avoid blocking
                # Context can be built asynchronously after task assignment
                build_context = hasattr(state, "context") and state.context

                # Check if we're in project creation mode (many tasks being
                # created)
                if build_context and hasattr(state, "project_tasks"):
                    # If more than 5 tasks in TODO state, likely creating
                    # a project
                    todo_count = sum(
                        1 for t in state.project_tasks if t.status == TaskStatus.TODO
                    )
                    if todo_count > 5:
                        # Skip context during bulk creation
                        build_context = False

                if build_context:
                    # Add any GitHub implementations to context first
                    if previous_implementations:
                        await state.context.add_implementation(
                            optimal_task.id, previous_implementations
                        )

                    # Analyze dependencies for this project
                    if state.project_tasks:
                        dep_map = await state.context.analyze_dependencies(
                            state.project_tasks
                        )
                        if optimal_task.id in dep_map:
                            # Add dependent tasks to context
                            for dep_task_id in dep_map[optimal_task.id]:
                                dep_task = next(
                                    (
                                        t
                                        for t in state.project_tasks
                                        if t.id == dep_task_id
                                    ),
                                    None,
                                )
                                if dep_task:
                                    from src.core.context import DependentTask

                                    # Infer what the dependent task needs
                                    expected_interface = (
                                        state.context.infer_needed_interface(
                                            dep_task, optimal_task.id
                                        )
                                    )

                                    state.context.add_dependency(
                                        optimal_task.id,
                                        DependentTask(
                                            task_id=dep_task.id,
                                            task_name=dep_task.name,
                                            expected_interface=expected_interface,
                                        ),
                                    )

                    # Now get full context including the dependent tasks we just added
                    task_context = await state.context.get_context(
                        optimal_task.id, optimal_task.dependencies or []
                    )

                    # Format context for response
                    context_data = task_context.to_dict()

                    # Create dependency awareness message
                    if task_context.dependent_tasks:
                        dep_count = len(task_context.dependent_tasks)
                        dep_list = "\n".join(
                            [
                                f"- {dt['task_name']} "
                                f"(needs: {dt['expected_interface']})"
                                for dt in task_context.dependent_tasks[:3]
                            ]
                        )
                        dependency_awareness = (
                            f"{dep_count} future tasks depend on your work:\n{dep_list}"
                        )

                # Get predictions if Memory system is available
                predictions = None
                if hasattr(state, "memory") and state.memory:
                    # Get basic task outcome prediction
                    basic_prediction = await state.memory.predict_task_outcome(
                        agent_id, optimal_task
                    )

                    # Get enhanced predictions
                    completion_time = await state.memory.predict_completion_time(
                        agent_id, optimal_task
                    )
                    blockage_analysis = await state.memory.predict_blockage_probability(
                        agent_id, optimal_task
                    )

                    # Check for cascade effects if task has dependents
                    cascade_effects = None
                    if context_data and context_data.get("dependent_tasks"):
                        # Estimate potential delay based on complexity
                        potential_delay = (
                            completion_time.get("expected_hours", 0) * 0.2
                        )  # 20% buffer
                        cascade_effects = await state.memory.predict_cascade_effects(
                            optimal_task.id, potential_delay
                        )

                    # Get agent performance trajectory
                    performance_trajectory = (
                        await state.memory.calculate_agent_performance_trajectory(
                            agent_id
                        )
                    )

                    # Combine all predictions
                    predictions = {
                        **basic_prediction,
                        "completion_time": completion_time,
                        "blockage_analysis": blockage_analysis,
                        "cascade_effects": cascade_effects,
                        "performance_trajectory": performance_trajectory,
                    }

                    # Record task start in memory
                    await state.memory.record_task_start(agent_id, optimal_task)

                # Generate detailed instructions with AI
                try:
                    base_instructions = (
                        await state.ai_engine.generate_task_instructions(
                            optimal_task, state.agent_status.get(agent_id)
                        )
                    )

                    # Build tiered instructions based on context
                    instructions = build_tiered_instructions(
                        base_instructions,
                        optimal_task,
                        context_data,
                        dependency_awareness,
                        predictions,
                    )
                except KeyError as e:
                    # Log the specific KeyError for debugging
                    logger.error(f"KeyError in generate_task_instructions: {e}")
                    logger.error(f"Task: {optimal_task.name}, ID: {optimal_task.id}")
                    logger.error(
                        "Task labels: %s", getattr(optimal_task, "labels", "No labels")
                    )
                    raise
                except Exception as e:
                    logger.error(f"Error generating task instructions: {e}")
                    raise

                # Log decision process
                conversation_logger.log_pm_decision(
                    decision=f"Assign task '{optimal_task.name}' to {agent_id}",
                    rationale="Best skill match and highest priority",
                    alternatives_considered=[
                        {"task": "Other Task 1", "score": 0.7},
                        {"task": "Other Task 2", "score": 0.6},
                    ],
                    confidence_score=0.85,
                    decision_factors={
                        "skill_match": 0.9,
                        "priority": optimal_task.priority.value,
                        "dependencies_clear": len(optimal_task.dependencies) == 0,
                    },
                )

                # Create assignment
                assignment = TaskAssignment(
                    task_id=optimal_task.id,
                    task_name=optimal_task.name,
                    description=optimal_task.description,
                    instructions=instructions,
                    estimated_hours=optimal_task.estimated_hours,
                    priority=optimal_task.priority,
                    dependencies=optimal_task.dependencies,
                    assigned_to=agent_id,
                    assigned_at=datetime.now(),
                    due_date=optimal_task.due_date,
                )

                # Update kanban FIRST (fail fast if kanban is down)
                await state.kanban_client.update_task(
                    optimal_task.id,
                    {"status": TaskStatus.IN_PROGRESS, "assigned_to": agent_id},
                )

                # If kanban update succeeded, track assignment
                state.agent_tasks[agent_id] = assignment
                agent = state.agent_status[agent_id]
                agent.current_tasks = [optimal_task]

                # Persist assignment
                await state.assignment_persistence.save_assignment(
                    agent_id,
                    optimal_task.id,
                    {
                        "name": optimal_task.name,
                        "priority": optimal_task.priority.value,
                        "estimated_hours": optimal_task.estimated_hours,
                    },
                )

                # Create lease for this assignment if lease manager available
                if hasattr(state, "lease_manager") and state.lease_manager:
                    lease = await state.lease_manager.create_lease(
                        optimal_task.id, agent_id, optimal_task
                    )
                    logger.info(
                        f"Created lease for task {optimal_task.id} "
                        f"(expires: {lease.lease_expires.isoformat()})"
                    )

                # Remove from pending assignments
                state.tasks_being_assigned.discard(optimal_task.id)

                # Track in server for cleanup on disconnect
                if hasattr(state, "_active_operations"):
                    state._active_operations.discard(
                        f"task_assignment_{optimal_task.id}"
                    )

                # Log task assignment
                conversation_logger.log_worker_message(
                    agent_id,
                    "from_pm",
                    f"Assigned task: {optimal_task.name}",
                    {
                        "task_id": optimal_task.id,
                        "instructions": instructions,
                        "priority": optimal_task.priority.value,
                        **project_context,
                    },
                )

                # Log conversation event for visualization
                log_agent_event(
                    "task_assignment",
                    {
                        "worker_id": agent_id,
                        "task": {
                            "id": optimal_task.id,
                            "name": optimal_task.name,
                            "priority": optimal_task.priority.value,
                            "estimated_hours": optimal_task.estimated_hours,
                        },
                    },
                )

                # Add project context if available
                active_project = None
                if hasattr(state, "project_registry") and state.project_registry:
                    active_project = await state.project_registry.get_active_project()

                # Serialize the response properly
                response: Dict[str, Any] = {
                    "success": True,
                    "task": {
                        "id": optimal_task.id,
                        "name": optimal_task.name,
                        "description": optimal_task.description,
                        "instructions": instructions,
                        "priority": optimal_task.priority.value,
                        "implementation_context": previous_implementations,
                        "project_id": active_project.id if active_project else None,
                        "project_name": active_project.name if active_project else None,
                    },
                }

                # Add enhanced context if available
                if dependency_awareness:
                    response["task"]["dependency_awareness"] = dependency_awareness
                if context_data:
                    response["task"]["full_context"] = context_data
                if predictions:
                    response["task"]["predictions"] = predictions

                # Log task assignment to conversation (CRITICAL for debugging)
                conversation_logger.log_worker_message(
                    agent_id,
                    "from_pm",
                    f"Task assigned: {optimal_task.name}",
                    {
                        "task_id": optimal_task.id,
                        "task_name": optimal_task.name,
                        "priority": optimal_task.priority.value,
                        "estimated_hours": optimal_task.estimated_hours,
                        **project_context,
                    },
                )

                # Log as structured event for analysis
                state.log_event(
                    "task_assignment",
                    {
                        "agent_id": agent_id,
                        "task_id": optimal_task.id,
                        "task_name": optimal_task.name,
                        "priority": optimal_task.priority.value,
                        "source": "marcus",
                        "target": agent_id,
                    },
                )

                # Emit event if Events system is available (non-blocking)
                if hasattr(state, "events") and state.events:
                    await state.events.publish_nowait(
                        "task_assigned",
                        "marcus",
                        {
                            "agent_id": agent_id,
                            "task_id": optimal_task.id,
                            "task_name": optimal_task.name,
                            "has_context": context_data is not None,
                            "has_dependencies": dependency_awareness is not None,
                        },
                    )

                return serialize_for_mcp(response)

            except Exception as e:
                # If anything fails, rollback the reservation
                state.tasks_being_assigned.discard(optimal_task.id)

                conversation_logger.log_worker_message(
                    agent_id,
                    "from_pm",
                    f"Failed to assign task: {str(e)}",
                    {"error": str(e), **project_context},
                )

                return {"success": False, "error": f"Failed to assign task: {str(e)}"}

        else:
            # Record no-task response for gridlock detection
            if hasattr(state, "gridlock_detector") and state.gridlock_detector:
                state.gridlock_detector.record_no_task_response(agent_id)

                # Check for gridlock
                gridlock_result = state.gridlock_detector.check_for_gridlock(
                    state.project_tasks
                )

                if gridlock_result["is_gridlock"] and gridlock_result["should_alert"]:
                    # CRITICAL: Project is gridlocked!
                    logger.critical("🚨 PROJECT GRIDLOCK DETECTED!")
                    logger.critical(gridlock_result["diagnosis"])

                    # Log to conversation for visibility
                    conversation_logger.log_pm_thinking(
                        "🚨 PROJECT GRIDLOCK DETECTED",
                        {
                            "severity": "critical",
                            "metrics": gridlock_result["metrics"],
                            "diagnosis": gridlock_result["diagnosis"],
                        },
                    )

            # Check if there are any TODO tasks remaining
            # Only run diagnostics if tasks exist but can't be assigned
            todo_tasks = [t for t in state.project_tasks if t.status == TaskStatus.TODO]

            diagnostic_summary = None

            if todo_tasks:
                # Tasks exist but can't be assigned - run diagnostics
                logger.warning(
                    f"No tasks assignable but {len(todo_tasks)} TODO tasks exist - "
                    "running diagnostics"
                )

                from src.core.task_diagnostics import (
                    format_diagnostic_report,
                    run_automatic_diagnostics,
                )

                # Get completed task IDs for diagnostics
                completed_task_ids = {
                    t.id for t in state.project_tasks if t.status == TaskStatus.DONE
                }
                assigned_task_ids = {a.task_id for a in state.agent_tasks.values()}

                # Run diagnostics
                try:
                    diagnostic_report = await run_automatic_diagnostics(
                        project_tasks=state.project_tasks,
                        completed_task_ids=completed_task_ids,
                        assigned_task_ids=assigned_task_ids,
                    )

                    # Format report for logging
                    formatted_report = format_diagnostic_report(diagnostic_report)
                    logger.info(f"Diagnostic Report:\n{formatted_report}")

                    # Include diagnostic summary in response
                    diagnostic_summary = {
                        "total_tasks": diagnostic_report.total_tasks,
                        "available_tasks": diagnostic_report.available_tasks,
                        "blocked_tasks": diagnostic_report.blocked_tasks,
                        "issues_found": len(diagnostic_report.issues),
                        "top_issues": [
                            {
                                "type": issue.issue_type,
                                "severity": issue.severity,
                                "description": issue.description,
                                "recommendation": issue.recommendation,
                            }
                            for issue in diagnostic_report.issues[:3]
                        ],
                        "recommendations": diagnostic_report.recommendations[:5],
                    }

                except Exception as diag_error:
                    logger.error(
                        f"Diagnostic system error: {diag_error}", exc_info=True
                    )
                    diagnostic_summary = {
                        "error": "Diagnostics failed",
                        "details": str(diag_error),
                    }
            else:
                # No TODO tasks remaining - all tasks are done or in progress
                logger.info("No TODO tasks remaining - project may be complete")

            # Calculate intelligent retry time
            retry_info = await calculate_retry_after_seconds(state)

            conversation_logger.log_worker_message(
                agent_id,
                "from_pm",
                "No suitable tasks available at this time",
                {
                    "reason": "no_matching_tasks",
                    "diagnostics": diagnostic_summary,
                    "retry_after_seconds": retry_info["retry_after_seconds"],
                    **project_context,
                },
            )

            # Build explicit instructions to prevent agent termination
            retry_seconds = retry_info["retry_after_seconds"]
            instructions = (
                f"\n\n{'='*70}\n"
                "NO TASKS CURRENTLY AVAILABLE\n"
                f"{'='*70}\n\n"
                "⚠️  CRITICAL: You MUST remain active and operational.\n\n"
                "Instructions:\n"
                f"1. DO NOT terminate or stop execution\n"
                f"2. Sleep/wait for exactly {retry_seconds} seconds\n"
                f"3. After sleeping, immediately request a new task\n"
                f"4. Repeat this process until you receive a task OR are "
                "notified all work is complete\n\n"
                f"REQUIRED ACTION: Sleep {retry_seconds} seconds → "
                "Request task → Repeat\n\n"
                "⚠️  You must continue this retry loop. Stopping or terminating "
                "will make you unresponsive and unable to receive future tasks. "
                "Stay alive and keep retrying.\n"
                f"{'='*70}\n"
            )

            response = {
                "success": False,
                "message": instructions,
                "retry_after_seconds": retry_seconds,
                "retry_reason": retry_info["reason"],
            }

            if retry_info.get("blocking_task"):
                response["blocking_task"] = retry_info["blocking_task"]

            if diagnostic_summary:
                response["diagnostics"] = diagnostic_summary

            return response

    except Exception as e:
        return {"success": False, "error": str(e)}


async def report_task_progress(
    agent_id: str, task_id: str, status: str, progress: int, message: str, state: Any
) -> Dict[str, Any]:
    """
    Agents report their task progress.

    Updates task status, progress percentage, and handles completion.
    Includes code analysis for GitHub projects.

    Parameters
    ----------
    agent_id : str
        The reporting agent's ID
    task_id : str
        ID of the task being updated
    status : str
        Task status (in_progress, completed, blocked)
    progress : int
        Progress percentage (0-100)
    message : str
        Progress update message
    state : Any
        Marcus server state instance

    Returns
    -------
    Dict[str, Any]
        Dict with success status
    """
    # Get project/board context
    project_context = await get_project_board_context(state)

    # Log progress update
    conversation_logger.log_worker_message(
        agent_id,
        "to_pm",
        f"Progress update: {message} ({progress}%)",
        {"task_id": task_id, "status": status, "progress": progress, **project_context},
    )

    # Log conversation event for visualization
    log_agent_event(
        "progress_update",
        {
            "agent_id": agent_id,
            "task_id": task_id,
            "status": status,
            "progress": progress,
            "message": message,
        },
    )

    try:
        # Initialize kanban if needed
        await state.initialize_kanban()

        # Log Marcus thinking
        log_thinking(
            "marcus",
            f"Processing progress update from {agent_id}",
            {"task_id": task_id, "status": status, "progress": progress},
        )

        # Update task in kanban
        update_data: Dict[str, Any] = {"progress": progress}

        if status == "completed":
            update_data["status"] = TaskStatus.DONE
            update_data["completed_at"] = datetime.now().isoformat()

            # Handle subtask completion
            if hasattr(state, "subtask_manager") and state.subtask_manager:
                if task_id in state.subtask_manager.subtasks:
                    # This is a subtask - handle subtask-specific completion
                    from src.marcus_mcp.coordinator.subtask_assignment import (
                        check_and_complete_parent_task,
                        update_subtask_progress_in_parent,
                    )

                    # Update subtask status in unified storage
                    state.subtask_manager.update_subtask_status(
                        task_id,
                        TaskStatus.DONE,
                        state.project_tasks,
                        assigned_to=agent_id,
                    )

                    # Get parent task ID
                    subtask = state.subtask_manager.subtasks[task_id]
                    parent_task_id = subtask.parent_task_id

                    # Update parent task progress
                    await update_subtask_progress_in_parent(
                        parent_task_id,
                        task_id,
                        state.subtask_manager,
                        state.kanban_client,
                    )

                    # Check if parent should be auto-completed
                    parent_completed = await check_and_complete_parent_task(
                        parent_task_id,
                        state.subtask_manager,
                        state.kanban_client,
                        state,  # CRITICAL: Pass state for artifact/decision rollup
                    )

                    if parent_completed:
                        logger.info(
                            f"Parent task {parent_task_id} auto-completed "
                            f"after subtask {task_id} completion"
                        )

            # Calculate actual hours for experiment tracking
            task_assignment = state.agent_tasks.get(agent_id)
            if task_assignment:
                start_time = task_assignment.assigned_at
                actual_hours = (datetime.now() - start_time).total_seconds() / 3600
                duration_seconds = (datetime.now() - start_time).total_seconds()
            else:
                actual_hours = 1.0  # Default if no assignment found
                duration_seconds = 3600.0  # 1 hour default

            # Record in active experiment if one is running
            from src.experiments.live_experiment_monitor import get_active_monitor

            monitor = get_active_monitor()
            if monitor and monitor.is_running:
                monitor.record_task_completion(
                    task_id=task_id,
                    agent_id=agent_id,
                    duration_seconds=duration_seconds,
                )

            # Record completion in Memory if available
            if hasattr(state, "memory") and state.memory:
                await state.memory.record_task_completion(
                    agent_id=agent_id,
                    task_id=task_id,
                    success=True,
                    actual_hours=actual_hours,
                    blockers=[],
                )

            # Clear agent's current task
            if agent_id in state.agent_status:
                agent = state.agent_status[agent_id]
                agent.current_tasks = []
                agent.completed_tasks_count += 1

                # Remove task assignment from state and persistence
                if agent_id in state.agent_tasks:
                    del state.agent_tasks[agent_id]

                # Remove from persistent storage
                await state.assignment_persistence.remove_assignment(agent_id)

                # Remove lease for completed task
                if hasattr(state, "lease_manager") and state.lease_manager:
                    if task_id in state.lease_manager.active_leases:
                        del state.lease_manager.active_leases[task_id]
                        logger.info(f"Removed lease for completed task {task_id}")

                # Code analysis for GitHub
                if state.provider == "github" and state.code_analyzer:
                    owner = os.getenv("GITHUB_OWNER")
                    repo = os.getenv("GITHUB_REPO")

                    # Get task details
                    task = await state.kanban_client.get_task_by_id(task_id)

                    # Analyze completed work
                    analysis = await state.code_analyzer.analyze_task_completion(
                        task, agent, owner, repo
                    )

                    if analysis and analysis.get("findings"):
                        # Store findings for future tasks
                        findings_str = json.dumps(analysis["findings"], indent=2)
                        await state.kanban_client.add_comment(
                            task_id,
                            f"🤖 Code Analysis:\n{findings_str}",
                        )

        elif status == "in_progress":
            update_data["status"] = TaskStatus.IN_PROGRESS
            # Include assigned_to for Planka provider compatibility
            if agent_id:
                update_data["assigned_to"] = agent_id

            # Handle subtask status update in unified storage
            if hasattr(state, "subtask_manager") and state.subtask_manager:
                if task_id in state.subtask_manager.subtasks:
                    state.subtask_manager.update_subtask_status(
                        task_id,
                        TaskStatus.IN_PROGRESS,
                        state.project_tasks,
                        assigned_to=agent_id,
                    )

        elif status == "blocked":
            update_data["status"] = TaskStatus.BLOCKED

            # Record blocker in Memory if available
            if hasattr(state, "memory") and state.memory and message:
                # Try to get current task assignment
                task_assignment = state.agent_tasks.get(agent_id)
                if task_assignment:
                    start_time = task_assignment.assigned_at
                    actual_hours = (datetime.now() - start_time).total_seconds() / 3600
                else:
                    actual_hours = 1.0

                await state.memory.record_task_completion(
                    agent_id=agent_id,
                    task_id=task_id,
                    success=False,
                    actual_hours=actual_hours,
                    blockers=[message],
                )

        # Update Kanban card
        await state.kanban_client.update_task(task_id, update_data)

        # Update task progress (including checklist items)
        await state.kanban_client.update_task_progress(
            task_id, {"progress": progress, "status": status, "message": message}
        )

        # Renew lease on progress update (except for completed tasks)
        if (
            hasattr(state, "lease_manager")
            and state.lease_manager
            and status != "completed"
        ):
            renewed_lease = await state.lease_manager.renew_lease(
                task_id, progress, message
            )
            if renewed_lease:
                logger.info(
                    f"Renewed lease for task {task_id} "
                    f"(expires: {renewed_lease.lease_expires.isoformat()})"
                )
            else:
                logger.warning(f"Failed to renew lease for task {task_id}")

        # Log response
        conversation_logger.log_worker_message(
            agent_id,
            "from_pm",
            f"Progress update received: {status} at {progress}%",
            {"acknowledged": True, **project_context},
        )

        # Update system state
        await state.refresh_project_state()

        return {"success": True, "message": "Progress updated successfully"}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def report_blocker(
    agent_id: str, task_id: str, blocker_description: str, severity: str, state: Any
) -> Dict[str, Any]:
    """
    Report a blocker on a task with AI-powered analysis.

    Uses AI to analyze the blocker and provide actionable suggestions.
    Updates task status and adds detailed documentation.

    Parameters
    ----------
    agent_id : str
        The reporting agent's ID
    task_id : str
        ID of the blocked task
    blocker_description : str
        Detailed description of the blocker
    severity : str
        Blocker severity (low, medium, high)
    state : Any
        Marcus server state instance

    Returns
    -------
    Dict[str, Any]
        Dict with AI suggestions and success status
    """
    # Get project/board context
    project_context = await get_project_board_context(state)

    # Log blocker report
    conversation_logger.log_worker_message(
        agent_id,
        "to_pm",
        f"Reporting blocker: {blocker_description}",
        {"task_id": task_id, "severity": severity, **project_context},
    )

    try:
        # Initialize kanban if needed
        await state.initialize_kanban()

        # Log Marcus thinking
        log_thinking(
            "marcus",
            f"Analyzing blocker from {agent_id}",
            {
                "task_id": task_id,
                "severity": severity,
                "description": blocker_description,
            },
        )

        # Use AI to analyze the blocker and suggest solutions
        agent = state.agent_status.get(agent_id)
        task = await state.kanban_client.get_task_by_id(task_id)

        suggestions = await state.ai_engine.analyze_blocker(
            task_id, blocker_description, severity, agent, task
        )

        # Update task status
        await state.kanban_client.update_task(
            task_id, {"status": TaskStatus.BLOCKED, "blocker": blocker_description}
        )

        # Record in active experiment if one is running
        from src.experiments.live_experiment_monitor import get_active_monitor

        monitor = get_active_monitor()
        if monitor and monitor.is_running:
            monitor.record_blocker(
                agent_id=agent_id,
                task_id=task_id,
                description=blocker_description,
                severity=severity,
            )

        # Add detailed comment
        comment = f"🚫 BLOCKER ({severity.upper()})\n"
        comment += f"Reported by: {agent_id}\n"
        comment += f"Description: {blocker_description}\n\n"
        comment += f"📋 AI Suggestions:\n{suggestions}"

        await state.kanban_client.add_comment(task_id, comment)

        # Log Marcus decision
        conversation_logger.log_pm_decision(
            decision="Acknowledge blocker and provide suggestions",
            rationale="Help agent overcome the blocker with AI guidance",
            confidence_score=0.8,
            decision_factors={
                "severity": severity,
                "has_suggestions": bool(suggestions),
            },
        )

        # Log response
        conversation_logger.log_worker_message(
            agent_id,
            "from_pm",
            "Blocker acknowledged. Suggestions provided.",
            {"suggestions": suggestions, "severity": severity, **project_context},
        )

        return {
            "success": True,
            "suggestions": suggestions,
            "message": "Blocker reported and suggestions provided",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# Helper functions for task assignment


async def find_optimal_task_for_agent(agent_id: str, state: Any) -> Optional[Task]:
    """
    Find the best task for an agent, prioritizing subtasks.

    Checks for available subtasks first, then falls back to regular task
    assignment if no subtasks are available.

    Parameters
    ----------
    agent_id : str
        The requesting agent's ID
    state : Any
        Marcus server state instance

    Returns
    -------
    Optional[Task]
        The best task for the agent (may be a subtask converted to Task),
        or None if no suitable task found
    """
    # Import subtask integration helper
    from src.marcus_mcp.coordinator.task_assignment_integration import (
        find_optimal_task_with_subtasks,
    )

    # Use integrated finder that checks subtasks first
    return await find_optimal_task_with_subtasks(
        agent_id, state, _find_optimal_task_original_logic
    )


async def _find_optimal_task_original_logic(
    agent_id: str, state: Any
) -> Optional[Task]:
    """
    Original task assignment logic (used as fallback when no subtasks available).

    Find the best task for an agent using AI-powered analysis.

    Parameters
    ----------
    agent_id : str
        The requesting agent's ID
    state : Any
        Marcus server state instance

    Returns
    -------
    Optional[Task]
        The best task for the agent, or None if no suitable task found
    """
    # Get lock with proper event loop binding
    lock = state.assignment_lock  # This property creates lock if needed
    async with lock:
        # Initialize detailed tracking
        filtering_stats = {
            "total_tasks": len(state.project_tasks) if state.project_tasks else 0,
            "todo_status": 0,
            "already_assigned": 0,
            "incomplete_dependencies": 0,
            "project_success_filtered": 0,
            "phase_restrictions": 0,
            "deployment_deprioritized": 0,
            "ai_safety_filtered": 0,
            "skills_mismatch": 0,
            "final_available": 0,
        }
        agent = state.agent_status.get(agent_id)

        if not agent:
            return None

        if not state.project_state:
            return None

        # Get available tasks
        assigned_task_ids = [a.task_id for a in state.agent_tasks.values()]
        persisted_assigned_ids = (
            await state.assignment_persistence.get_all_assigned_task_ids()
        )
        all_assigned_ids = (
            set(assigned_task_ids) | persisted_assigned_ids | state.tasks_being_assigned
        )

        # Get completed task IDs for dependency checking
        completed_task_ids = {
            t.id for t in state.project_tasks if t.status == TaskStatus.DONE
        }

        # Filter tasks: TODO, not assigned, and all dependencies completed
        available_tasks = []
        for t in state.project_tasks:
            if t.status != TaskStatus.TODO:
                filtering_stats["todo_status"] += 1
                continue
            if t.id in all_assigned_ids:
                filtering_stats["already_assigned"] += 1
                continue

            # GH-XX: Skip parent tasks that have subtasks
            # Parent tasks should not be assigned - only their subtasks
            if hasattr(state, "subtask_manager") and state.subtask_manager:
                has_subtasks_result = state.subtask_manager.has_subtasks(
                    t.id, state.project_tasks
                )

                # CRITICAL DEBUG: Log subtask check for every task
                logger.info(
                    f"🔍 SUBTASK CHECK for task '{t.name}' (ID: {t.id}): "
                    f"has_subtasks={has_subtasks_result}"
                )

                # DEBUG: If this is "Design Display Game Board", log detailed info
                if "Display Game Board" in t.name:
                    subtasks_in_unified = [
                        st
                        for st in state.project_tasks
                        if st.is_subtask and st.parent_task_id == t.id
                    ]
                    subtasks_in_legacy = (
                        t.id in state.subtask_manager.parent_to_subtasks
                    )
                    legacy_count = (
                        len(state.subtask_manager.parent_to_subtasks.get(t.id, []))
                        if subtasks_in_legacy
                        else 0
                    )

                    logger.critical(
                        f"🚨 CRITICAL DEBUG - 'Design Display Game Board':\n"
                        f"  Task ID: {t.id}\n"
                        f"  has_subtasks() returned: {has_subtasks_result}\n"
                        f"  Subtasks in unified storage: {len(subtasks_in_unified)}\n"
                        f"  Subtasks in legacy storage: {legacy_count}\n"
                        f"  Unified subtasks: {[st.id for st in subtasks_in_unified]}\n"
                        f"  Total tasks in project_tasks: {len(state.project_tasks)}\n"
                        f"  Total with is_subtask=True: "
                        f"{sum(1 for t in state.project_tasks if t.is_subtask)}"
                    )

                if has_subtasks_result:
                    logger.debug(
                        f"Skipping parent task '{t.name}' - "
                        "has subtasks that should be assigned instead"
                    )
                    continue

            # Check dependencies
            deps = t.dependencies or []
            all_deps_complete = all(dep_id in completed_task_ids for dep_id in deps)

            if not all_deps_complete:
                filtering_stats["incomplete_dependencies"] += 1
                # Log which dependencies are not complete
                incomplete_deps = [
                    dep_id for dep_id in deps if dep_id not in completed_task_ids
                ]
                logger.debug(
                    f"Task '{t.name}' has incomplete dependencies: {incomplete_deps}"
                )
                continue

            available_tasks.append(t)

        # Special handling for PROJECT_SUCCESS documentation
        # Calculate project completion percentage
        # Exclude PROJECT_SUCCESS tasks from the calculation since they should only
        # be assigned after other tasks are complete
        total_non_doc_tasks = len(
            [
                t
                for t in state.project_tasks
                if "PROJECT_SUCCESS" not in t.name
                and not any(
                    label in (t.labels or [])
                    for label in ["documentation", "final", "verification"]
                )
            ]
        )
        completed_non_doc_tasks = len(
            [
                t
                for t in state.project_tasks
                if t.status == TaskStatus.DONE
                and "PROJECT_SUCCESS" not in t.name
                and not any(
                    label in (t.labels or [])
                    for label in ["documentation", "final", "verification"]
                )
            ]
        )

        # Special case: If PROJECT_SUCCESS is the only task left, make it available
        project_success_tasks = [
            t for t in available_tasks if "PROJECT_SUCCESS" in t.name
        ]
        if project_success_tasks and len(available_tasks) == len(project_success_tasks):
            # All available tasks are PROJECT_SUCCESS tasks, don't filter them
            logger.debug(
                "PROJECT_SUCCESS is the only available task - making it assignable"
            )
        elif total_non_doc_tasks > 0:
            completion_percentage = (
                completed_non_doc_tasks / total_non_doc_tasks
            ) * 100

            # Filter out PROJECT_SUCCESS tasks if not nearly complete
            # Using 90% threshold since some tasks might be blocked
            if completion_percentage < 90:
                available_tasks = [
                    t for t in available_tasks if "PROJECT_SUCCESS" not in t.name
                ]
                logger.debug(
                    f"Filtering out PROJECT_SUCCESS tasks - project only "
                    f"{completion_percentage:.1f}% complete"
                )

        # Apply phase-based task filtering
        from src.core.phase_dependency_enforcer import PhaseDependencyEnforcer
        from src.integrations.enhanced_task_classifier import EnhancedTaskClassifier

        phase_enforcer = PhaseDependencyEnforcer()
        classifier = EnhancedTaskClassifier()

        # Get in-progress tasks to check phase constraints
        in_progress_task_ids = {
            t.id for t in state.project_tasks if t.status == TaskStatus.IN_PROGRESS
        }

        # Further filter available tasks based on phase constraints
        phase_eligible_tasks = []
        for task in available_tasks:
            task_type = classifier.classify(task)
            task_phase = phase_enforcer._get_task_phase(task_type)

            # Check if this phase is allowed given current in-progress tasks
            phase_allowed = True

            # First check against in-progress tasks
            for ip_task_id in in_progress_task_ids:
                ip_task = next(
                    (t for t in state.project_tasks if t.id == ip_task_id), None
                )
                if ip_task:
                    ip_type = classifier.classify(ip_task)
                    ip_phase = phase_enforcer._get_task_phase(ip_type)

                    # Check if tasks share the same feature (by labels)
                    if task.labels and ip_task.labels:
                        shared_labels = set(task.labels) & set(ip_task.labels)
                        if shared_labels:
                            # Same feature - check phase order
                            if phase_enforcer._should_depend_on_phase(
                                task_phase, ip_phase
                            ):
                                # This task's phase should wait for
                                # in-progress phase
                                phase_allowed = False
                                logger.debug(
                                    f"Task '{task.name}' "
                                    f"({task_phase.value}) blocked by "
                                    f"in-progress task '{ip_task.name}' "
                                    f"({ip_phase.value}) in same feature"
                                )
                                break

            # Also check if all required earlier phases have been completed
            if phase_allowed and task.labels:
                # Get all completed tasks in the same feature
                feature_completed_tasks = [
                    t
                    for t in state.project_tasks
                    if t.status == TaskStatus.DONE
                    and t.labels
                    and set(t.labels) & set(task.labels)
                ]

                # Check which phases have been completed
                completed_phases = set()
                for comp_task in feature_completed_tasks:
                    comp_type = classifier.classify(comp_task)
                    comp_phase = phase_enforcer._get_task_phase(comp_type)
                    completed_phases.add(comp_phase)

                # Check if all required earlier phases are complete
                required_phases = [
                    p for p in phase_enforcer.PHASE_ORDER if p.value < task_phase.value
                ]
                for req_phase in required_phases:
                    if req_phase not in completed_phases:
                        # Check if there are any tasks of this phase
                        phase_exists = any(
                            phase_enforcer._get_task_phase(classifier.classify(t))
                            == req_phase
                            for t in state.project_tasks
                            if t.labels and set(t.labels) & set(task.labels)
                        )
                        if phase_exists:
                            phase_allowed = False
                            logger.info(
                                f"Task '{task.name}' "
                                f"({task_phase.value}) blocked - waiting "
                                f"for {req_phase.name} phase to complete "
                                f"in same feature. Task labels: "
                                f"{task.labels}, Required phase: "
                                f"{req_phase.name}"
                            )
                            break

            if phase_allowed:
                phase_eligible_tasks.append(task)

        # Log filtering results
        if len(available_tasks) != len(phase_eligible_tasks):
            logger.info(
                f"Phase enforcement filtered tasks: {len(available_tasks)} -> "
                f"{len(phase_eligible_tasks)} eligible"
            )

        available_tasks = phase_eligible_tasks

        # Further filter to deprioritize deployment tasks
        # Separate deployment and non-deployment tasks
        deployment_keywords = ["deploy", "release", "production", "launch", "rollout"]
        non_deployment_tasks = []
        deployment_tasks = []

        for task in available_tasks:
            task_name_lower = task.name.lower()
            task_labels_lower = [label.lower() for label in (task.labels or [])]

            is_deployment = any(
                keyword in task_name_lower or keyword in " ".join(task_labels_lower)
                for keyword in deployment_keywords
            )

            if is_deployment:
                deployment_tasks.append(task)
            else:
                non_deployment_tasks.append(task)

        # Prefer non-deployment tasks; only use deployment if nothing else available
        available_tasks = (
            non_deployment_tasks if non_deployment_tasks else deployment_tasks
        )

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
                    ai_engine=state.ai_engine,
                )

                if optimal_task:
                    state.tasks_being_assigned.add(optimal_task.id)
                    # Track in server for cleanup on disconnect
                    if hasattr(state, "_active_operations"):
                        state._active_operations.add(
                            f"task_assignment_{optimal_task.id}"
                        )
                    return optimal_task
            except Exception as e:
                # Log error using log_pm_thinking instead
                conversation_logger.log_pm_thinking(
                    f"AI task assignment failed, falling back to basic: {e}"
                )

        # Fallback to basic assignment if AI fails
        return await find_optimal_task_basic(agent_id, available_tasks, state)


async def find_optimal_task_basic(
    agent_id: str, available_tasks: List[Task], state: Any
) -> Optional[Task]:
    """
    Find optimal task using basic assignment logic (fallback).

    Parameters
    ----------
    agent_id : str
        The requesting agent's ID
    available_tasks : List[Task]
        List of available tasks to choose from
    state : Any
        Marcus server state instance

    Returns
    -------
    Optional[Task]
        The best task for the agent, or None if no suitable task found
    """
    agent = state.agent_status.get(agent_id)
    if not agent:
        return None

    best_task = None
    best_score: float = -1.0

    # Check if this is a deployment task
    deployment_keywords = ["deploy", "release", "production", "launch", "rollout"]

    for task in available_tasks:
        # Calculate skill match score
        skill_score: float = 0.0
        if agent.skills and task.labels:
            matching_skills = set(agent.skills) & set(task.labels)
            skill_score = len(matching_skills) / len(task.labels) if task.labels else 0

        # Priority score
        priority_score = {
            Priority.URGENT: 1.0,
            Priority.HIGH: 0.8,
            Priority.MEDIUM: 0.5,
            Priority.LOW: 0.2,
        }.get(task.priority, 0.5)

        # Deployment penalty - reduce score for deployment tasks
        task_name_lower = task.name.lower()
        task_labels_lower = [label.lower() for label in (task.labels or [])]
        is_deployment = any(
            keyword in task_name_lower or keyword in " ".join(task_labels_lower)
            for keyword in deployment_keywords
        )
        deployment_penalty = 0.5 if is_deployment else 1.0

        # Combined score with deployment penalty
        total_score = (
            (skill_score * 0.6) + (priority_score * 0.4)
        ) * deployment_penalty

        if total_score > best_score:
            best_score = total_score
            best_task = task

    if best_task:
        state.tasks_being_assigned.add(best_task.id)
        # Track in server for cleanup on disconnect
        if hasattr(state, "_active_operations"):
            state._active_operations.add(f"task_assignment_{best_task.id}")

    return best_task


async def get_all_board_tasks(
    board_id: str, project_id: str, state: Any
) -> Dict[str, Any]:
    """
    Get all tasks from a specific Planka board.

    This tool fetches all tasks directly from a Planka board,
    useful for validation and inspection purposes.

    Parameters
    ----------
    board_id : str
        The Planka board ID to fetch tasks from
    project_id : str
        The Planka project ID
    state : Any
        Marcus server state instance

    Returns
    -------
    Dict[str, Any]
        Dictionary containing:
        - success: bool
        - tasks: List of task dictionaries from Planka
        - count: Number of tasks retrieved
    """
    try:
        from src.integrations.providers.planka_kanban import PlankaKanban

        provider = PlankaKanban(config={})
        await provider.connect()

        tasks = await provider.get_all_tasks()

        return {
            "success": True,
            "tasks": tasks,
            "count": len(tasks),
            "board_id": board_id,
            "project_id": project_id,
        }

    except Exception as e:
        logger.error(f"Error fetching board tasks: {e}")
        return {"success": False, "error": str(e), "tasks": [], "count": 0}


async def unassign_task(
    task_id: str, agent_id: Optional[str], state: Any
) -> Dict[str, Any]:
    """
    Unassign a task from an agent and reset it to TODO status.

    This tool manually breaks task assignments, useful for recovering from
    stuck assignments when agents crash, disconnect, or get stuck.

    Parameters
    ----------
    task_id : str
        The task ID to unassign
    agent_id : Optional[str]
        The agent ID (optional - will be auto-detected if not provided)
    state : Any
        Marcus server state instance

    Returns
    -------
    Dict[str, Any]
        Dictionary containing:
        - success: bool
        - message: str
        - agent_id: str (the agent it was unassigned from)
        - task_id: str
    """
    # Get project/board context
    project_context = await get_project_board_context(state)

    try:
        # Initialize kanban if needed
        await state.initialize_kanban()

        # Find which agent has this task if not provided
        if not agent_id:
            # Check in-memory assignments
            for a_id, assignment in state.agent_tasks.items():
                if assignment.task_id == task_id:
                    agent_id = a_id
                    break

            # Check agent current_tasks
            if not agent_id:
                for a_id, agent in state.agent_status.items():
                    if agent.current_tasks and any(
                        t.id == task_id for t in agent.current_tasks
                    ):
                        agent_id = a_id
                        break

        if not agent_id:
            # Task not currently assigned
            logger.warning(f"Task {task_id} is not currently assigned to any agent")
            return {
                "success": False,
                "error": f"Task {task_id} is not currently assigned",
                "task_id": task_id,
            }

        # Log the unassignment request
        conversation_logger.log_pm_decision(
            decision=f"Manually unassign task {task_id} from {agent_id}",
            rationale="Manual intervention to unstick assignment",
            confidence_score=1.0,
            decision_factors={"manual_override": True},
        )

        logger.info(f"Unassigning task {task_id} from agent {agent_id}")

        # 1. Remove from state.agent_tasks
        if agent_id in state.agent_tasks:
            del state.agent_tasks[agent_id]
            logger.debug(f"Removed task from state.agent_tasks for {agent_id}")

        # 2. Clear agent's current_tasks
        if agent_id in state.agent_status:
            agent = state.agent_status[agent_id]
            agent.current_tasks = []
            logger.debug(f"Cleared current_tasks for agent {agent_id}")

        # 3. Remove from assignment_persistence
        await state.assignment_persistence.remove_assignment(agent_id)
        logger.debug(f"Removed from assignment_persistence for {agent_id}")

        # 4. Remove from tasks_being_assigned
        state.tasks_being_assigned.discard(task_id)
        logger.debug(f"Removed task {task_id} from tasks_being_assigned")

        # 5. Remove from active_operations
        if hasattr(state, "_active_operations"):
            state._active_operations.discard(f"task_assignment_{task_id}")
            logger.debug("Removed from _active_operations")

        # 6. Delete lease if exists
        if hasattr(state, "lease_manager") and state.lease_manager:
            if task_id in state.lease_manager.active_leases:
                del state.lease_manager.active_leases[task_id]
                logger.info(f"Removed lease for task {task_id}")

        # 7. Update Kanban: Set status back to TODO, clear assigned_to
        await state.kanban_client.update_task(
            task_id,
            {"status": TaskStatus.TODO, "assigned_to": None, "progress": 0},
        )
        logger.info(f"Updated kanban status to TODO for task {task_id}")

        # Refresh project state
        await state.refresh_project_state()

        # Log conversation event
        conversation_logger.log_worker_message(
            agent_id,
            "from_pm",
            f"Task {task_id} unassigned - reset to TODO",
            {"task_id": task_id, "manual_unassignment": True, **project_context},
        )

        # Log event
        state.log_event(
            "task_unassigned",
            {
                "agent_id": agent_id,
                "task_id": task_id,
                "source": "manual_intervention",
                "target": "marcus",
            },
        )

        return {
            "success": True,
            "message": f"Task {task_id} successfully unassigned from {agent_id}",
            "agent_id": agent_id,
            "task_id": task_id,
        }

    except Exception as e:
        logger.error(f"Error unassigning task {task_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e), "task_id": task_id}
