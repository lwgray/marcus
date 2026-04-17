"""Context Tools for Marcus MCP.

This module contains tools for context management:
- log_decision: Log architectural decisions
- get_task_context: Get context for a specific task
"""

import logging
from typing import Any, Dict, List

from src.core.project_history import Decision as HistoryDecision
from src.core.project_history import (
    ProjectHistoryPersistence,
)
from src.logging.agent_events import log_agent_event

logger = logging.getLogger(__name__)


async def log_decision(
    agent_id: str, task_id: str, decision: str, state: Any
) -> Dict[str, Any]:
    """
    Log an architectural decision made during task implementation.

    Agents use this to document important technical choices that might
    affect other tasks. Decisions are automatically cross-referenced
    to dependent tasks.

    Parameters
    ----------
    agent_id : str
        The agent making the decision
    task_id : str
        Current task ID
    decision : str
        Natural language description of the decision
    state : Any
        Marcus server state instance

    Returns
    -------
    Dict[str, Any]
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
            try:
                comment = f"🏗️ ARCHITECTURAL DECISION by {agent_id}\\n"
                comment += f"Decision: {what}\\n"
                comment += f"Reasoning: {why}\\n"
                comment += f"Impact: {impact}"

                await state.kanban_client.add_comment(task_id, comment)
            except Exception as e:
                # Don't fail if kanban comment fails - decision is still logged
                logger.warning(f"Failed to add kanban comment for decision: {e}")

        # Log event (non-blocking)
        if hasattr(state, "events") and state.events:
            await state.events.publish_nowait(
                "decision_logged", agent_id, logged_decision.to_dict()
            )

        # Record in active experiment if one is running
        from src.experiments.live_experiment_monitor import get_active_monitor

        monitor = get_active_monitor()
        if monitor and monitor.is_running:
            monitor.record_decision(
                agent_id=agent_id, task_id=task_id, decision=decision
            )

        # Persist to project history for post-project analysis
        await _persist_decision_to_history(logged_decision, state)

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

    For subtasks, includes parent task context and shared conventions.

    Parameters
    ----------
    task_id : str
        The task to get context for (can be regular task or subtask ID)
    state : Any
        Marcus server state instance

    Returns
    -------
    Dict[str, Any]
        Dict with task context including implementations, dependencies, and
        decisions. For subtasks, includes parent_task, shared_conventions,
        and dependency_artifacts.
    """
    # Log to agent events — proof the agent called get_task_context
    # Resolve agent_id: try authenticated client first, then task assignment
    agent_id = getattr(state, "_current_client_id", None)
    if not agent_id and hasattr(state, "project_tasks"):
        for t in state.project_tasks:
            if t.id == task_id and t.assigned_to:
                agent_id = t.assigned_to
                break
    agent_id = agent_id or "unknown"
    project_name = getattr(state, "current_project_name", None) or "unknown"
    log_agent_event(
        "context_requested",
        {
            "agent_id": agent_id,
            "task_id": task_id,
            "project": project_name,
        },
    )

    try:
        # Check if this is a subtask
        if hasattr(state, "subtask_manager") and state.subtask_manager:
            # Check if task_id is a subtask
            if task_id in state.subtask_manager.subtasks:
                # Get subtask context
                subtask_context = state.subtask_manager.get_subtask_context(task_id)

                # Get parent task context
                parent_task_id = subtask_context["parent_task_id"]
                parent_task = None
                for t in state.project_tasks:
                    if t.id == parent_task_id:
                        parent_task = t
                        break

                # Build enriched context
                context_dict = {
                    "is_subtask": True,
                    "subtask_info": subtask_context["subtask"],
                    "parent_task": (
                        {
                            "id": parent_task_id,
                            "name": parent_task.name if parent_task else "Unknown",
                            "description": (
                                parent_task.description if parent_task else ""
                            ),
                            "labels": parent_task.labels if parent_task else [],
                        }
                        if parent_task
                        else {"id": parent_task_id}
                    ),
                    "shared_conventions": subtask_context["shared_conventions"],
                    "dependency_artifacts": subtask_context["dependency_artifacts"],
                    "sibling_subtasks": subtask_context["sibling_subtasks"],
                }

                # CRITICAL: Add artifacts and decisions from sibling subtasks
                # This allows subtasks to see what their siblings have produced
                # Optimized: Single pass through siblings collecting both
                sibling_context = await _collect_sibling_subtask_context(
                    task_id, parent_task_id, state
                )
                context_dict["sibling_artifacts"] = sibling_context["artifacts"]
                context_dict["sibling_decisions"] = sibling_context["decisions"]

                # Add parent task's context if Context system is available
                if hasattr(state, "context") and state.context and parent_task:
                    parent_context = await state.context.get_context(
                        parent_task_id, parent_task.dependencies or []
                    )
                    context_dict["parent_context"] = parent_context.to_dict()

                return {"success": True, "context": context_dict}

        # Standard task context (not a subtask)
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
        context_dict = context.to_dict()
        context_dict["is_subtask"] = False

        # Add artifact information
        artifacts = await _collect_task_artifacts(task_id, task, state)
        context_dict["artifacts"] = artifacts

        # Add recovery information if present
        if task.recovery_info:
            context_dict["recovery_info"] = task.recovery_info.to_dict()

        return {"success": True, "context": context_dict}

    except Exception as e:
        return {"success": False, "error": str(e)}


_COORDINATION_REFERENCE_GUIDANCE = (
    "COORDINATION REFERENCE: This artifact defines the interface boundary "
    "between domains. Build the complete, working feature implementation. "
    "Treat this as a constraint on what your code must expose at integration "
    "points — not as your implementation spec."
)

_IMPLEMENTATION_GUIDE_GUIDANCE = (
    "IMPLEMENTATION GUIDE: This artifact provides data shapes and design "
    "patterns. Use it to understand the expected structure and patterns — "
    "adapt as needed for your complete feature."
)

_FOUNDATION_USAGE_GUIDANCE = (
    "SHARED FOUNDATION: This artifact was produced by a shared setup task "
    "that completed before parallel work began. Use it directly — import it, "
    "consume its exports, and extend it if needed. Do not recreate or "
    "duplicate what it already provides."
)


def _inject_usage_guidance(
    artifact: Dict[str, Any],
    is_design_dep: bool,
    is_contract_first_ghost: bool,
) -> None:
    """
    Inject usage_guidance into a dependency artifact dict in-place.

    Priority (highest to lowest):

    1. ``artifact_role`` field — role-aware guidance (Option C).
    2. ``_is_foundation_dep`` marker — pre-fork synthesis tasks (GH-355).
       Set by ``_collect_task_artifacts`` when ``source_type == "pre_fork_synthesis"``.
    3. ``is_design_dep`` label-based fallback for feature_based design
       artifacts that predate the ``artifact_role`` field (Option B).

    Parameters
    ----------
    artifact : Dict[str, Any]
        Artifact dict from ``state.task_artifacts``.  Modified in-place.
    is_design_dep : bool
        True when the dependency task has ``"design"`` in its labels.
    is_contract_first_ghost : bool
        True when the dependency task also has ``"auto_completed"`` in its
        labels (contract_first ghost tasks).  These already get framing from
        ``build_tiered_instructions`` and must not be overridden here.
    """
    role = artifact.get("artifact_role")
    if role == "interface_contract":
        artifact.setdefault("usage_guidance", _COORDINATION_REFERENCE_GUIDANCE)
    elif role == "implementation_spec":
        artifact.setdefault("usage_guidance", _IMPLEMENTATION_GUIDE_GUIDANCE)
    elif artifact.get("_is_foundation_dep"):
        # Pre-fork synthesis artifacts (GH-355): shared setup that
        # completed before domain work began.  Consumption guidance
        # delivered here, not in the task description, so Marcus
        # stays on the coordination side of the bright line.
        artifact.setdefault("usage_guidance", _FOUNDATION_USAGE_GUIDANCE)
    elif is_design_dep and not is_contract_first_ghost:
        # Option B label-based fallback: feature_based design artifacts
        artifact.setdefault("usage_guidance", _COORDINATION_REFERENCE_GUIDANCE)


async def _collect_task_artifacts(
    task_id: str, task: Any, state: Any
) -> List[Dict[str, Any]]:
    """
    Collect all artifacts available for this task from tracked sources.

    Returns artifacts from:
    1. Artifacts logged via log_artifact for this task (in state.task_artifacts)
    2. Kanban attachments for this task
    3. Artifacts from dependency tasks (both logged and attached)

    Does NOT scan filesystem - only returns explicitly tracked artifacts.
    """
    artifacts = []

    try:
        # 1. Get artifacts logged via log_artifact
        if hasattr(state, "task_artifacts") and task_id in state.task_artifacts:
            artifacts.extend(state.task_artifacts[task_id].copy())

        # 2. Get Kanban attachments for this task
        if state.kanban_client:
            try:
                card_id = getattr(task, "kanban_card_id", None) or task.id
                result = await state.kanban_client.get_attachments(card_id=card_id)
                if result.get("success", False):
                    attachments = result.get("data", [])
                    for attachment in attachments:
                        artifacts.append(
                            {
                                "filename": attachment.get("name"),
                                "location": (
                                    f"./attachments/{attachment.get('id')}/"
                                    f"{attachment.get('name')}"
                                ),
                                "storage_type": "attachment",
                                "artifact_type": "reference",
                                "created_by": attachment.get("userId"),
                                "created_at": attachment.get("createdAt"),
                                "description": f"Attachment from task {task_id}",
                            }
                        )
            except Exception as e:
                # Don't fail the whole operation if kanban is unavailable
                print(
                    f"Warning: Failed to get kanban attachments for task {task_id}: {e}"
                )

        # 3. Get artifacts from dependency tasks
        #
        # GH-356 scope annotation: determine which domain the requesting
        # task owns by extracting its ``domain:X`` labels.  These labels
        # are added by the contract-first path in nlp_tools for both
        # ghost (design) and implementation tasks.  Feature-based tasks
        # carry no ``domain:`` labels, so ``requesting_domain_labels``
        # will be empty for that path.
        requesting_domain_labels = {
            label
            for label in (getattr(task, "labels", []) or [])
            if label.startswith("domain:")
        }
        if task.dependencies:
            for dep_id in task.dependencies:
                dep_task = next(
                    (t for t in state.project_tasks if t.id == dep_id), None
                )
                if dep_task:
                    # Logged artifacts from dependency
                    if (
                        hasattr(state, "task_artifacts")
                        and dep_id in state.task_artifacts
                    ):
                        # P1 fix (GH-356 Codex review): deep-copy each
                        # artifact dict so scope_annotation mutations
                        # don't bleed back into state.task_artifacts.
                        # The list .copy() was shallow — dict objects
                        # were shared, so A's annotation persisted into
                        # B's stored artifact for subsequent callers.
                        dep_artifacts = [dict(a) for a in state.task_artifacts[dep_id]]
                        dep_labels = getattr(dep_task, "labels", []) or []
                        is_design_dep = "design" in dep_labels
                        # contract_first ghost tasks carry both "design" and
                        # "auto_completed" labels.  They already receive framing
                        # from the contract_notice layer in
                        # build_tiered_instructions, so we skip guidance here.
                        is_contract_first_ghost = "auto_completed" in dep_labels
                        is_foundation_dep = (
                            getattr(dep_task, "source_type", None)
                            == "pre_fork_synthesis"
                        )
                        # GH-356: ``domain:`` labels on the dep task for
                        # scope_annotation comparison.
                        dep_domain_labels = {
                            label for label in dep_labels if label.startswith("domain:")
                        }
                        for artifact in dep_artifacts:
                            artifact["dependency_task_id"] = dep_id
                            artifact["dependency_task_name"] = dep_task.name
                            artifact["description"] = (
                                f"{artifact.get('description', '')} "
                                f"(from dependency: {dep_task.name})"
                            )
                            # Mark foundation artifacts so _inject_usage_guidance
                            # can apply GH-355 consumption guidance without
                            # widening the function signature.
                            if is_foundation_dep:
                                artifact["_is_foundation_dep"] = True
                            # Option C: artifact_role field takes precedence.
                            # Option B: fall back to label-based detection.
                            _inject_usage_guidance(
                                artifact, is_design_dep, is_contract_first_ghost
                            )
                            artifact.pop("_is_foundation_dep", None)
                            # GH-356: scope annotation at retrieval time.
                            # The same artifact is in_scope for one agent and
                            # reference_only for another — annotation cannot be
                            # set at generation time.
                            #
                            # contract_first (requesting task has domain: labels):
                            #   same domain as dep → in_scope (agent owns it)
                            #   different domain   → reference_only (coordinate only)
                            #
                            # feature_based (no domain: labels):
                            #   all deps → reference_only (no domain ownership)
                            if requesting_domain_labels:
                                if requesting_domain_labels & dep_domain_labels:
                                    artifact["scope_annotation"] = "in_scope"
                                else:
                                    artifact["scope_annotation"] = "reference_only"
                            else:
                                artifact["scope_annotation"] = "reference_only"
                        artifacts.extend(dep_artifacts)

                    # Kanban attachments from dependency
                    if state.kanban_client:
                        try:
                            dep_card_id = (
                                getattr(dep_task, "kanban_card_id", None) or dep_task.id
                            )
                            result = await state.kanban_client.get_attachments(
                                card_id=dep_card_id
                            )
                            if result.get("success", False):
                                attachments = result.get("data", [])
                                for attachment in attachments:
                                    # P2 fix (GH-356 Codex review):
                                    # Kanban dep attachments also need
                                    # scope_annotation so the data layer
                                    # matches the prompt contract.
                                    dep_attachment_labels = (
                                        getattr(dep_task, "labels", []) or []
                                    )
                                    dep_attachment_domains = {
                                        lbl
                                        for lbl in dep_attachment_labels
                                        if lbl.startswith("domain:")
                                    }
                                    if requesting_domain_labels:
                                        attachment_scope = (
                                            "in_scope"
                                            if requesting_domain_labels
                                            & dep_attachment_domains
                                            else "reference_only"
                                        )
                                    else:
                                        attachment_scope = "reference_only"
                                    artifacts.append(
                                        {
                                            "filename": attachment.get("name"),
                                            "location": (
                                                f"./attachments/{attachment.get('id')}/"
                                                f"{attachment.get('name')}"
                                            ),
                                            "storage_type": "attachment",
                                            "artifact_type": "reference",
                                            "created_by": attachment.get("userId"),
                                            "created_at": attachment.get("createdAt"),
                                            "dependency_task_id": dep_id,
                                            "dependency_task_name": dep_task.name,
                                            "description": (
                                                f"Attachment from dependency: "
                                                f"{dep_task.name}"
                                            ),
                                            "scope_annotation": attachment_scope,
                                        }
                                    )
                        except Exception as e:
                            # Don't fail if kanban is unavailable
                            print(
                                f"Warning: Failed to get kanban attachments "
                                f"for dependency {dep_id}: {e}"
                            )

    except Exception as e:
        # Don't fail the whole context operation if artifact collection fails
        print(f"Warning: Artifact collection encountered an error: {e}")

    return artifacts


async def _collect_sibling_subtask_context(
    current_subtask_id: str, parent_task_id: str, state: Any
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Collect both artifacts AND decisions from sibling subtasks in one pass.

    OPTIMIZED: Single loop through siblings collecting both artifacts and
    decisions, reducing from 2 separate calls to 1.

    When Task B's subtask 1 calls get_task_context, it should see
    artifacts and decisions produced by Task B's subtask 2, 3, etc.

    Parameters
    ----------
    current_subtask_id : str
        The current subtask requesting context
    parent_task_id : str
        The parent task ID
    state : Any
        Marcus server state

    Returns
    -------
    Dict[str, List[Dict[str, Any]]]
        Dict with "artifacts" and "decisions" keys containing sibling context
    """
    sibling_artifacts: List[Dict[str, Any]] = []
    sibling_decisions: List[Dict[str, Any]] = []

    if not hasattr(state, "subtask_manager") or not state.subtask_manager:
        return {"artifacts": sibling_artifacts, "decisions": sibling_decisions}

    # Get all subtasks for this parent from unified storage
    subtasks = state.subtask_manager.get_subtasks(parent_task_id, state.project_tasks)

    # Single pass: collect both artifacts and decisions from siblings
    for subtask in subtasks:
        if subtask.id == current_subtask_id:
            continue  # Skip current subtask

        # Collect artifacts from this sibling
        if hasattr(state, "task_artifacts") and subtask.id in state.task_artifacts:
            for artifact in state.task_artifacts[subtask.id]:
                # Add sibling context to artifact
                sibling_artifact = artifact.copy()
                sibling_artifact["from_sibling_subtask"] = subtask.id
                sibling_artifact["from_sibling_subtask_name"] = subtask.name
                sibling_artifact["description"] = (
                    f"[From sibling subtask: {subtask.name}] "
                    f"{sibling_artifact.get('description', '')}"
                )
                sibling_artifacts.append(sibling_artifact)

        # Collect decisions from this sibling
        if hasattr(state, "context") and state.context:
            subtask_decisions = [
                d.to_dict() for d in state.context.decisions if d.task_id == subtask.id
            ]

            for decision in subtask_decisions:
                # Add sibling context
                decision["from_sibling_subtask"] = subtask.id
                decision["from_sibling_subtask_name"] = subtask.name
                decision["what"] = f"[From sibling: {subtask.name}] {decision['what']}"
                sibling_decisions.append(decision)

    return {"artifacts": sibling_artifacts, "decisions": sibling_decisions}


async def _persist_decision_to_history(logged_decision: Any, state: Any) -> None:
    """
    Persist decision to project history for post-project analysis.

    Converts the Context system's Decision to ProjectHistory's Decision format
    and stores it persistently.

    Parameters
    ----------
    logged_decision : Decision
        The decision from the Context system
    state : Any
        Marcus server state

    Notes
    -----
    Fails gracefully - errors are logged but don't interrupt the main flow.
    """
    try:
        # Get project info from state
        if not hasattr(state, "current_project_id") or not state.current_project_id:
            logger.debug("No active project - skipping project history persistence")
            return

        project_id = state.current_project_id
        project_name = getattr(state, "current_project_name", project_id)

        # Initialize project history persistence if not already done
        if not hasattr(state, "project_history_persistence"):
            state.project_history_persistence = ProjectHistoryPersistence()

        # Get kanban comment URL if decision was posted to kanban
        kanban_comment_url = None
        if hasattr(state, "last_kanban_comment_url"):
            kanban_comment_url = state.last_kanban_comment_url

        # Find affected tasks by checking task dependencies
        affected_tasks: list[str] = []
        if hasattr(state, "project_tasks"):
            for task in state.project_tasks:
                if (
                    hasattr(task, "dependencies")
                    and task.dependencies
                    and logged_decision.task_id in task.dependencies
                ):
                    affected_tasks.append(task.id)

        # Convert Context Decision to ProjectHistory Decision
        history_decision = HistoryDecision(
            decision_id=logged_decision.decision_id,
            task_id=logged_decision.task_id,
            agent_id=logged_decision.agent_id,
            timestamp=logged_decision.timestamp,
            what=logged_decision.what,
            why=logged_decision.why,
            impact=logged_decision.impact,
            affected_tasks=affected_tasks,
            confidence=0.8,  # Default confidence
            kanban_comment_url=kanban_comment_url,
            project_id=project_id,
        )

        # Persist to project history
        await state.project_history_persistence.append_decision(
            project_id, project_name, history_decision
        )

        logger.info(
            f"Persisted decision {logged_decision.decision_id} "
            f"to project history for {project_id}"
        )

    except Exception as e:
        # Graceful degradation - log but don't fail
        logger.warning(f"Failed to persist decision to project history: {e}")
