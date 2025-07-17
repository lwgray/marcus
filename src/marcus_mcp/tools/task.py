"""
Task Management Tools for Marcus MCP.

This module contains tools for task operations in the Marcus system:
- request_next_task: Get optimal task assignment for an agent
- report_task_progress: Update progress on assigned tasks
- report_blocker: Report blockers with AI-powered suggestions
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


def build_tiered_instructions(
    base_instructions: str,
    task: Task,
    context_data: Optional[Dict[str, Any]],
    dependency_awareness: Optional[str],
    predictions: Optional[Dict[str, Any]],
) -> str:
    """
    Build tiered instructions based on task context and complexity.

    Layers:
    1. Base instructions (always included)
    2. Implementation context (if previous work exists)
    3. Dependency awareness (if task has dependents)
    4. Decision logging (if task affects others)
    5. Predictions and warnings (if available)
    """
    instructions_parts = [base_instructions]

    # Layer 2: Implementation Context
    if context_data and context_data.get("previous_implementations"):
        impl_count = len(context_data["previous_implementations"])
        instructions_parts.append(
            f"\n\n📚 IMPLEMENTATION CONTEXT:\n{impl_count} relevant implementations found. "
            "Use these patterns and interfaces to maintain consistency."
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
            "This task has significant downstream impact. When making technical choices that affect other tasks:\n"
            "Use: 'Marcus, log decision: I chose [WHAT] because [WHY]. "
            "This affects [IMPACT].'\n"
            "Examples:\n"
            "- 'I chose JWT tokens because mobile apps need stateless auth. "
            "This affects all API endpoints.'\n"
            "- 'I chose PostgreSQL because we need ACID compliance. "
            "This affects all data models.'"
        )

    # Layer 5: Predictions and Warnings
    if predictions:
        risk_parts = []

        # Success probability warning
        if predictions.get("success_probability", 1.0) < 0.6:
            risk_parts.append(
                f"⚠️ Success probability: {predictions['success_probability']:.0%} - Extra care needed"
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


async def request_next_task(agent_id: str, state: Any) -> Any:
    """
    Agents call this to request their next optimal task.

    Uses AI-powered task matching to find the best task based on:
    - Agent skills and experience
    - Task priority and dependencies
    - Current workload distribution

    Args:
        agent_id: The requesting agent's ID
        state: Marcus server state instance

    Returns
    -------
        Dict with task details and instructions if successful
    """
    # Log task request
    conversation_logger.log_worker_message(
        agent_id,
        "to_pm",
        "Requesting next task",
        {"worker_info": f"Worker {agent_id} requesting task"},
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

                # Check if we're in project creation mode (lots of tasks being created)
                if build_context and hasattr(state, "project_tasks"):
                    # If more than 5 tasks in TODO state, we're likely creating a project
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
                                f"- {dt['task_name']} (needs: {dt['expected_interface']})"
                                for dt in task_context.dependent_tasks[
                                    :3
                                ]  # Show first 3
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

                # Remove from pending assignments
                state.tasks_being_assigned.discard(optimal_task.id)

                # Log task assignment
                conversation_logger.log_worker_message(
                    agent_id,
                    "from_pm",
                    f"Assigned task: {optimal_task.name}",
                    {
                        "task_id": optimal_task.id,
                        "instructions": instructions,
                        "priority": optimal_task.priority.value,
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
                    {"error": str(e)},
                )

                return {"success": False, "error": f"Failed to assign task: {str(e)}"}

        else:
            conversation_logger.log_worker_message(
                agent_id,
                "from_pm",
                "No suitable tasks available at this time",
                {"reason": "no_matching_tasks"},
            )

            return {
                "success": False,
                "message": "No suitable tasks available at this time",
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


async def report_task_progress(
    agent_id: str, task_id: str, status: str, progress: int, message: str, state: Any
) -> Dict[str, Any]:
    """
    Agents report their task progress.

    Updates task status, progress percentage, and handles completion.
    Includes code analysis for GitHub projects.

    Args:
        agent_id: The reporting agent's ID
        task_id: ID of the task being updated
        status: Task status (in_progress, completed, blocked)
        progress: Progress percentage (0-100)
        message: Progress update message
        state: Marcus server state instance

    Returns
    -------
        Dict with success status
    """
    # Log progress update
    conversation_logger.log_worker_message(
        agent_id,
        "to_pm",
        f"Progress update: {message} ({progress}%)",
        {"task_id": task_id, "status": status, "progress": progress},
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

            # Record completion in Memory if available
            if hasattr(state, "memory") and state.memory:
                # Calculate actual hours (simplified - in real system would track actual time)
                task_assignment = state.agent_tasks.get(agent_id)
                if task_assignment:
                    start_time = task_assignment.assigned_at
                    actual_hours = (datetime.now() - start_time).total_seconds() / 3600
                else:
                    actual_hours = 1.0  # Default if no assignment found

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
                        await state.kanban_client.add_comment(
                            task_id,
                            f"🤖 Code Analysis:\n{json.dumps(analysis['findings'], indent=2)}",
                        )

        elif status == "in_progress":
            update_data["status"] = TaskStatus.IN_PROGRESS
            # Include assigned_to for Planka provider compatibility
            if agent_id:
                update_data["assigned_to"] = agent_id

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

        await state.kanban_client.update_task(task_id, update_data)

        # Update task progress (including checklist items)
        await state.kanban_client.update_task_progress(
            task_id, {"progress": progress, "status": status, "message": message}
        )

        # Log response
        conversation_logger.log_worker_message(
            agent_id,
            "from_pm",
            f"Progress update received: {status} at {progress}%",
            {"acknowledged": True},
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

    Args:
        agent_id: The reporting agent's ID
        task_id: ID of the blocked task
        blocker_description: Detailed description of the blocker
        severity: Blocker severity (low, medium, high)
        state: Marcus server state instance

    Returns
    -------
        Dict with AI suggestions and success status
    """
    # Log blocker report
    conversation_logger.log_worker_message(
        agent_id,
        "to_pm",
        f"Reporting blocker: {blocker_description}",
        {"task_id": task_id, "severity": severity},
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
            {"suggestions": suggestions, "severity": severity},
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
    """Find the best task for an agent using AI-powered analysis."""
    async with state.assignment_lock:
        agent = state.agent_status.get(agent_id)

        if not agent or not state.project_state:
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
        available_tasks = [
            t
            for t in state.project_tasks
            if t.status == TaskStatus.TODO
            and t.id not in all_assigned_ids
            and all(dep_id in completed_task_ids for dep_id in (t.dependencies or []))
        ]

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
    """Find optimal task using basic assignment logic (fallback)."""
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

    return best_task
