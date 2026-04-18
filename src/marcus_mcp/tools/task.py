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
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.ai_powered_task_assignment import find_optimal_task_for_agent_ai_powered
from src.core.models import Priority, Task, TaskAssignment, TaskStatus
from src.logging.agent_events import log_agent_event
from src.logging.conversation_logger import conversation_logger, log_thinking
from src.marcus_mcp.utils import serialize_for_mcp

logger = logging.getLogger(__name__)

# Module-level singletons for validation system (initialized lazily)
_work_analyzer: Optional[Any] = None
_retry_tracker: Optional[Any] = None

# Retry ceiling: after this many validation failures on the same
# task, stop blocking and route the task through the normal
# completion path with an escalation annotation. See
# ``report_task_progress`` for the inline check — the ceiling must
# be evaluated BEFORE calling ``_handle_validation_failure`` so the
# escalated task still goes through the kanban-completion, memory
# recording, and branch-merge steps. Codex P1 on PR #337: returning
# a success response from the failure path left tasks incomplete
# in kanban and reintroduced the workflow stall the ceiling was
# meant to prevent.
MAX_VALIDATION_RETRIES = 3
_singleton_lock = threading.Lock()  # Thread-safe initialization


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


def _get_task_type(task: Task) -> str:
    """
    Determine task type using the same logic as AI instruction generation.

    This function mirrors the task type determination logic from
    ai_analysis_engine.generate_task_instructions() to ensure consistency
    between instruction generation and workflow enforcement.

    Parameters
    ----------
    task : Task
        Task to check

    Returns
    -------
    str
        Task type: "implementation", "design", or "testing"

    Notes
    -----
    Task type priority:
    1. _parent_task_type attribute (for subtasks)
    2. Inference from name/labels
    3. Defaults to "implementation"

    This matches the logic in src/integrations/ai_analysis_engine.py:460-473
    """
    # CRITICAL: Check parent task type first for subtasks (same as ai_analysis_engine)
    if hasattr(task, "_parent_task_type"):
        parent_type = getattr(task, "_parent_task_type")
        return str(parent_type)

    # Fall back to inferring from name or labels (same logic as ai_analysis_engine)
    task_type = "implementation"  # default
    task_labels = getattr(task, "labels", []) or []

    if "design" in task.name.lower() or "type:design" in task_labels:
        task_type = "design"
    elif "test" in task.name.lower() or "type:testing" in task_labels:
        task_type = "testing"

    return task_type


def _build_mandatory_workflow_prompt(task: Task) -> str:
    """
    Build mandatory workflow prompt that agents MUST follow.

    This prompt creates a forcing function by requiring agents to
    write a todo list with enumerated workflow steps.

    Parameters
    ----------
    task : Task
        Task being assigned (used to insert task description)

    Returns
    -------
    str
        Formatted mandatory workflow prompt

    Notes
    -----
    This addresses Issue #168: Agents not following CLAUDE.md workflow.
    The todo list requirement makes workflow visible and trackable.
    """
    workflow_prompt = f"""🔴 MANDATORY WORKFLOW 🔴

Before starting work, you MUST write a todo list with these steps:

1. Call get_task_context to check dependencies and artifacts
2. Read artifacts from dependency tasks
3. [TASK WORK: {task.name}]
   {task.description}
4. Report progress at 25%, 50%, 75% milestones
5. Log decisions (log_decision) and artifacts (log_artifact) as needed
6. BEFORE reporting "completed", verify:
   - Does your code actually run without errors?
   - Do all the tests for this task pass?
7. Report completion with implementation summary
8. Be prepared for remediation work if validation fails and resubmit progress
9. Immediately request next task

⚠️ CRITICAL BEHAVIORS:
- Check dependencies with get_task_context BEFORE starting work
- Read artifacts from dependency tasks to understand prior work
- Report progress at each milestone (not just at completion)
- Log decisions as they're made (not after task completion)
- VERIFY code runs and tests pass BEFORE reporting completed
- Be ready to address validation feedback and resubmit

This workflow ensures coordination with other agents and prevents
incomplete implementations."""
    return workflow_prompt


def _is_integration_task(task: Task) -> bool:
    """Detect whether a task is an integration verification task.

    Integration verification tasks are produced by
    ``IntegrationTaskGenerator.create_integration_task`` and carry
    the ``"type:integration"`` label as a stable type marker. They
    are NOT validated by the citation-based LLM validator (which
    only runs on implementation tasks) — instead they are gated by
    the product smoke verifier, which runs subprocess-level checks
    that the assembled product builds.

    Parameters
    ----------
    task : Task
        Task to inspect.

    Returns
    -------
    bool
        True if the task carries ``type:integration`` in its labels.
        Defensive: returns False if labels is missing or not a
        sequence.
    """
    labels = getattr(task, "labels", None)
    if not labels:
        return False
    try:
        return "type:integration" in labels
    except TypeError:
        return False


async def _run_product_smoke_gate(
    task: Task,
    agent_id: str,
    state: Any,
    start_command: Optional[str],
    readiness_probe: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Run deliverable verification for a completing integration task.

    Resolves the project root from the kanban workspace state, runs
    the agent-declared start_command (and optional readiness_probe) as
    subprocess, and returns either ``None`` (verification passed —
    completion may proceed) or a rejection dict that the caller
    returns directly to the agent.

    **Strict enforcement**: integration tasks MUST declare a
    start_command. Completions that omit it are rejected with the
    missing-declaration blocker message, regardless of any other
    state. This is the explicit design choice locked in Simon decision
    967555f6 — no fallback auto-detection. Agents own stack knowledge.

    Parameters
    ----------
    task : Task
        The integration verification task being completed.
    agent_id : str
        Agent reporting completion.
    state : Any
        Marcus server state (provides kanban_client for workspace
        state lookup).
    start_command : Optional[str]
        Agent-declared shell command that starts the deliverable.
        Required — missing → rejection.
    readiness_probe : Optional[str]
        Agent-declared probe command for long-running servers.
        Optional — absent means the start_command is treated as a
        one-shot that must exit 0 within the configured timeout.

    Returns
    -------
    Optional[Dict[str, Any]]
        ``None`` if verification passed. A rejection dict with
        ``success=False``, ``status="smoke_verification_failed"``,
        and a ``blocker`` payload if verification failed or the
        start_command was missing.

    Notes
    -----
    Verification system errors (programmer errors in the runner
    itself, not deliverable failures) propagate as exceptions so the
    caller can log-and-continue. Deliverable failures return a
    rejection dict.
    """
    from pathlib import Path as _Path

    from src.integrations.product_smoke import verify_deliverable

    # Resolve project root via the kanban client's workspace state.
    # This is the same source of truth used by
    # ``_merge_agent_branch_to_main`` so the smoke gate sees the
    # same project root that the agent's git operations target.
    project_root: Optional[str] = None
    if hasattr(state, "kanban_client") and state.kanban_client:
        try:
            ws_state = state.kanban_client._load_workspace_state()
            if ws_state and "project_root" in ws_state:
                project_root = ws_state["project_root"]
        except Exception as ws_err:
            logger.warning(
                f"PRODUCT SMOKE GATE: Failed to load workspace state "
                f"for {task.id}: {ws_err}. Skipping smoke verification."
            )
            return None

    if not project_root:
        logger.warning(
            f"PRODUCT SMOKE GATE: No project_root resolved for "
            f"{task.id}. Skipping smoke verification."
        )
        return None

    project_root_path = _Path(project_root)
    if not project_root_path.is_dir():
        logger.warning(
            f"PRODUCT SMOKE GATE: project_root {project_root!r} is "
            f"not a directory. Skipping smoke verification for {task.id}."
        )
        return None

    logger.info(
        f"PRODUCT SMOKE GATE: Running deliverable verification for "
        f"integration task {task.id} at {project_root_path}. "
        f"start_command={start_command!r} "
        f"readiness_probe={readiness_probe!r}"
    )
    result = await verify_deliverable(
        start_command=start_command,
        readiness_probe=readiness_probe,
        cwd=project_root_path,
    )

    if result.success:
        logger.info(
            f"PRODUCT SMOKE GATE: Verification passed for {task.id} "
            f"({len(result.steps)} step(s))"
        )
        return None

    # Verification failed — reject the completion and surface the
    # blocker message.
    logger.warning(
        f"PRODUCT SMOKE GATE: Verification FAILED for {task.id}. "
        f"Failure: {result.failure_summary}. Rejecting completion."
    )
    return {
        "success": False,
        "status": "smoke_verification_failed",
        "error": "product_smoke_failed",
        "agent_id": agent_id,
        "task_id": task.id,
        "failure_summary": result.failure_summary,
        "blocker": result.blocker_message,
        "smoke_result": result.to_dict(),
        "message": (
            "Marcus rejected this integration-task completion. Either "
            "the declared start_command failed, the readiness_probe "
            "never passed, or the start_command was not declared at "
            "all. See the `blocker` field for details."
        ),
    }


def _parse_contract_metadata(task: Task) -> Dict[str, str]:
    """
    Resolve contract-first metadata from a task across storage layers.

    GH-320 PR 2 introduces the ``Task.responsibility`` field and
    stores ``contract_file`` in ``Task.source_context``. Some kanban
    providers don't persist these fields through their round-trip:

    - SQLite (``src/integrations/providers/sqlite_kanban.py``) persists
      ``source_context`` but not ``responsibility`` as a top-level
      column.
    - Planka (``src/integrations/kanban_client.py``) persists neither
      — the provider's ``_card_to_task`` mapping constructs ``Task``
      with a minimal field set.

    To make the CONTRACT RESPONSIBILITY layer work for tasks reloaded
    from any kanban provider, ``decompose_by_contract`` also embeds
    the metadata as a structured HTML comment marker in the task
    description (which every provider round-trips as the core field).

    This helper looks in three places, in priority order:

    1. ``task.responsibility`` + ``task.source_context["contract_file"]``
       / ``["product_intent"]`` (set by fresh decomposer output, best
       signal)
    2. ``task.source_context["responsibility"]`` + ``["contract_file"]``
       / ``["product_intent"]`` (belt-and-suspenders for SQLite)
    3. Parsed from the ``MARCUS_CONTRACT_FIRST`` marker in
       ``task.description`` — last-resort fallback for providers that
       only persist description, like Planka. The marker carries
       responsibility, contract_file, and (when present) product_intent.

    Parameters
    ----------
    task : Task
        The task to inspect.

    Returns
    -------
    Dict[str, str]
        Dict with keys ``"responsibility"``, ``"contract_file"``, and
        ``"product_intent"``. Values are empty strings when not found.
        Callers can treat an empty ``responsibility`` as "this task is
        not contract-first" without needing a separate boolean flag.

    Notes
    -----
    Codex caught the persistence gap on PR #327 review. Without this
    helper, the CONTRACT RESPONSIBILITY layer would silently never
    fire for tasks reloaded from the board even though the task was
    born contract-first, defeating the whole point of PR 2.

    Phase 1 (GH-320 framing layer) added ``product_intent`` to the
    metadata so the agent prompt can surface WHY the task exists
    from the user's perspective alongside WHAT the contract
    boundary is.
    """
    # Priority 1: direct Task.responsibility field
    responsibility = getattr(task, "responsibility", None)
    source_context = getattr(task, "source_context", None) or {}

    if responsibility:
        return {
            "responsibility": str(responsibility),
            "contract_file": str(source_context.get("contract_file", "") or ""),
            "product_intent": str(source_context.get("product_intent", "") or ""),
        }

    # Priority 2: responsibility stored in source_context
    sc_responsibility = source_context.get("responsibility")
    if sc_responsibility:
        return {
            "responsibility": str(sc_responsibility),
            "contract_file": str(source_context.get("contract_file", "") or ""),
            "product_intent": str(source_context.get("product_intent", "") or ""),
        }

    # Priority 3: parse HTML comment marker from description
    description = getattr(task, "description", "") or ""
    marker_start = description.find("<!-- MARCUS_CONTRACT_FIRST")
    if marker_start == -1:
        return {"responsibility": "", "contract_file": "", "product_intent": ""}
    marker_end = description.find("-->", marker_start)
    if marker_end == -1:
        return {"responsibility": "", "contract_file": "", "product_intent": ""}

    marker_body = description[marker_start:marker_end]
    parsed_resp = ""
    parsed_file = ""
    parsed_intent = ""
    for line in marker_body.splitlines():
        line = line.strip()
        if line.startswith("responsibility:"):
            parsed_resp = line[len("responsibility:") :].strip()
        elif line.startswith("contract_file:"):
            parsed_file = line[len("contract_file:") :].strip()
        elif line.startswith("product_intent:"):
            parsed_intent = line[len("product_intent:") :].strip()

    return {
        "responsibility": parsed_resp,
        "contract_file": parsed_file,
        "product_intent": parsed_intent,
    }


def build_tiered_instructions(
    base_instructions: str,
    task: Task,
    context_data: Optional[Dict[str, Any]],
    dependency_awareness: Optional[str],
    predictions: Optional[Dict[str, Any]],
    state: Optional[Any] = None,
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
    state : Optional[Any]
        Marcus server state.  When provided, Layer 1.4 can look up
        dependency tasks to detect feature-based design deps and add
        up-front framing so agents know to build the complete feature
        rather than just implementing the interface contract.  Callers
        that omit ``state`` silently skip Layer 1.4 (backward compat).

    Returns
    -------
    str
        Tiered instructions with appropriate layers

    Notes
    -----
    Instruction layers:
    0. Mandatory workflow (ONLY for implementation tasks - Issue #168)
    1. Base instructions (always included)
    1.1. Recovery handoff (if task was recovered from another agent)
    1.3. Contract responsibility (contract_first tasks only - GH-320)
    1.4. Feature-based design artifact framing (feature_based tasks with
         design deps — mirrors 1.3 but for the coordination-reference role)
    2. Subtask context (if this is a subtask)
    3. Implementation context (if previous work exists)
    4. Dependency awareness (if task has dependents)
    5. Decision logging (if task affects others)
    6. Predictions and warnings (if available)
    7. Task-specific guidance (based on labels)
    """
    instructions_parts = []

    # Layer 0: Mandatory Workflow (ONLY for implementation tasks)
    # Use same task type logic as AI instruction generation
    task_type = _get_task_type(task)
    if task_type == "implementation":
        workflow_prompt = _build_mandatory_workflow_prompt(task)
        instructions_parts.append(workflow_prompt)

    # Layer 1: Base instructions
    instructions_parts.append(base_instructions)

    # Layer 1.1: Recovery Handoff (if task was recovered from another agent)
    recovery = getattr(task, "recovery_info", None)
    if recovery is not None:
        # Check if recovery info has expired (stale after 24h)
        is_expired = (
            recovery.recovery_expires_at is not None
            and datetime.now(timezone.utc) > recovery.recovery_expires_at
        )
        if not is_expired:
            instructions_parts.append(
                f"\n\n🔄 RECOVERY HANDOFF:\n"
                f"{recovery.instructions}\n"
                f"- Time spent by previous agent: "
                f"{recovery.time_spent_minutes:.0f} minutes\n"
                f"- Previous progress: {recovery.previous_progress}%\n"
                f"- Recovery reason: {recovery.recovery_reason}"
            )

    # Layer 1.3: Contract Responsibility (GH-320 PR 2)
    # When a task owns a contract interface (contract-first
    # decomposition), surface that ownership with high signal. This
    # layer fires BEFORE subtask context because contract ownership
    # is structural — the agent must understand the contract before
    # considering the task's subtask-vs-standalone status.
    #
    # Metadata is resolved via ``_parse_contract_metadata`` which
    # checks Task.responsibility, Task.source_context, and the
    # MARCUS_CONTRACT_FIRST description marker in priority order.
    # This makes the layer robust to kanban providers that don't
    # round-trip Task.responsibility or source_context — Codex P1
    # from PR #327 review.
    contract_meta = _parse_contract_metadata(task)
    responsibility = contract_meta["responsibility"]
    if responsibility:
        contract_file = contract_meta["contract_file"]
        product_intent = contract_meta.get("product_intent", "")
        contract_notice = (
            f"\n\n📜 CONTRACT RESPONSIBILITY (contract-first decomposition):\n"
            f"You OWN: {responsibility}\n"
        )
        # Phase 1 framing layer (GH-320). When the decomposer
        # supplied a product_intent string, surface it ABOVE the
        # contract-file details so the agent reads the user-facing
        # reason the task exists before reading the interface
        # boundary. The autonomy directive that follows reframes
        # the contract as a coordination guardrail rather than a
        # prescriptive spec — agents working contract-first should
        # use professional judgment for everything the contract
        # doesn't explicitly govern (UI, error handling, helper
        # methods, internal structure). Without this layer the
        # contract dominates the prompt and agents lose the
        # "build a real product" instinct, which is what
        # dashboard-v70's "forgot what a dashboard was" regression
        # was tracking.
        if product_intent:
            contract_notice += (
                f"\n🎯 WHY THIS EXISTS: {product_intent}\n"
                f"\nUse judgment. The contract is a COORDINATION "
                f"BOUNDARY, not a build spec. You choose the "
                f"implementation, helper methods, UI details, error "
                f"handling, loading states, styling, and anything "
                f"else the contract doesn't explicitly govern. Build "
                f"it like a normal engineer building this feature — "
                f"the contract just keeps you from colliding with "
                f"other agents on the shared surface.\n"
            )
        if contract_file:
            contract_notice += (
                f"\nContract file: {contract_file}\n\n"
                f"BEFORE writing any code, Read() the contract file at "
                f"{contract_file}. The contract defines the interface "
                f"boundary your implementation must satisfy. Other agents "
                f"are implementing other sides of this same contract in "
                f"parallel — if you diverge from its data shapes or "
                f"method signatures, the integration fails.\n\n"
                f"Conform to the contract at the boundary. Everything "
                f"else is yours to design. If the contract is missing "
                f"something you need, report a blocker — do NOT silently "
                f"modify the contract file."
            )
        else:
            contract_notice += (
                "\nRead the shared contract artifacts in docs/ before "
                "writing code. Conform to them at the boundary; design "
                "everything else yourself."
            )
        # GH-356: surface scope_annotation semantics so agents know
        # how to interpret the field on each dependency artifact.
        contract_notice += (
            "\n\nEach dependency artifact in your context carries a "
            "``scope_annotation`` field:\n"
            "- ``in_scope``      — you OWN this interface, implement it "
            "completely\n"
            "- ``reference_only`` — coordination boundary only; do NOT "
            "implement this interface"
        )
        # Keep-alive reminder (experiment 66 fix): contract-first
        # agents go heads-down implementing and skip the logging /
        # progress guidance from the earlier workflow layer. The
        # lease system treats silence as abandonment and reassigns
        # the task. Terse reminder adjacent to the contract
        # instructions so it survives the agent's attention budget.
        contract_notice += (
            "\n\n⏱️  KEEP THE LEASE ALIVE:\n"
            "Silence >3 min = task reclaimed and reassigned.\n"
            "- report_task_progress at 25/50/75%\n"
            "- log_decision for each architectural choice "
            "(as you make it, not after)\n"
            "- log_artifact for each intermediate output "
            "other agents might consume"
        )
        instructions_parts.append(contract_notice)

    # Layer 1.4: Feature-based design artifact framing
    # Mirrors Layer 1.3 for the opposite decomposer mode.  When a
    # feature_based task depends on a design task (has "design" label
    # but NOT "auto_completed"), agents need up-front guidance that
    # those design artifacts are coordination references — not their
    # implementation spec.  Without this, agents read the interface
    # contract and build a stub that satisfies the interface but
    # ignores the user-visible feature requirement (v76 failure mode).
    #
    # Skipped when:
    # - ``responsibility`` is set (Layer 1.3 already covers contract_first)
    # - ``state`` is None (backward compat for callers without state)
    # - task has no dependencies (nothing to look up)
    if not responsibility and state is not None and task.dependencies:
        dep_tasks = getattr(state, "project_tasks", []) or []
        has_feature_based_design_dep = any(
            dep.id in task.dependencies
            and "design" in (getattr(dep, "labels", []) or [])
            and "auto_completed" not in (getattr(dep, "labels", []) or [])
            for dep in dep_tasks
        )
        if has_feature_based_design_dep:
            instructions_parts.append(
                "\n\n📐 DESIGN ARTIFACTS IN YOUR DEPENDENCIES:\n"
                "Your dependency tasks produced design artifacts (interface\n"
                "contracts, data models, API shapes). Read them before\n"
                "writing code to understand the boundary you must expose.\n\n"
                "Your job is to build the COMPLETE, WORKING FEATURE — not\n"
                "just implement the interface. Contracts are coordination\n"
                "constraints on what your code must expose at integration\n"
                "points. Everything else — UI details, error handling,\n"
                "internal structure, helper methods — is yours to design.\n"
                "Build it like a normal engineer building this feature.\n\n"
                "Each dependency artifact carries a ``scope_annotation`` field:\n"
                "- ``reference_only`` — coordination boundary; read it, do not "
                "reimplement it"
            )

    # Layer 1.5: Subtask Context (if this is a subtask)
    if hasattr(task, "_is_subtask") and task._is_subtask:
        parent_name = getattr(task, "_parent_task_name", "parent task")

        # Calculate realistic time budget for subtask
        # estimated_hours is already in reality-based format (minutes/60)
        # Guard against None to prevent TypeError
        estimated_minutes = (task.estimated_hours or 0) * 60

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

    # Layer 6: Task-specific guidance based on labels and task name.
    # Guards use ``or []`` / ``or ""`` so the block runs safely even when
    # task.labels is None or task.name is None.
    _labels = [lbl.lower() for lbl in (task.labels or [])]
    _name = (task.name or "").lower()
    guidance_parts = []

    # API tasks
    if any(lbl in ["api", "endpoint", "rest"] for lbl in _labels):
        guidance_parts.append(
            "🌐 API Guidelines: Follow RESTful conventions, "
            "include proper error handling, document response formats"
        )

    # Frontend tasks
    if any(lbl in ["frontend", "ui", "react", "vue"] for lbl in _labels):
        guidance_parts.append(
            "🎨 Frontend Guidelines: Ensure responsive design, "
            "follow component patterns, handle loading/error states"
        )

    # Database tasks
    if any(lbl in ["database", "migration", "schema"] for lbl in _labels):
        guidance_parts.append(
            "🗄️ Database Guidelines: Include rollback migrations, "
            "test with sample data, document schema changes"
        )

    # Security tasks
    if any(lbl in ["security", "auth", "authentication"] for lbl in _labels):
        guidance_parts.append(
            "🔒 Security Guidelines: Follow OWASP best practices, "
            "implement proper validation, use secure defaults"
        )

    # Documentation tasks — fire on label OR task name.
    # dashboard-v82 post-mortem: Agent 1 documented WeatherWidget props
    # from the design spec instead of the actual implementation, causing
    # README/code drift. Instruction-level reminder to read source first.
    _doc_labels = {"documentation", "docs", "readme"}
    _doc_name_keywords = ("readme", "document", "docs")
    if any(lbl in _doc_labels for lbl in _labels) or any(
        kw in _name for kw in _doc_name_keywords
    ):
        guidance_parts.append(
            "📖 Documentation Guidelines: For every component, function, "
            "or API you document — read the actual source file first. "
            "Verify every prop name, parameter name, type, and default "
            "value against the implementation, not the design spec. "
            "Document the API that exists in the code, not the intended "
            "one. Design specs and implementations diverge; code is truth."
        )

    if guidance_parts:
        instructions_parts.append(
            "\n\n💡 TASK-SPECIFIC GUIDANCE:\n" + "\n".join(guidance_parts)
        )

    return "\n".join(instructions_parts)


async def calculate_retry_after_seconds(state: Any) -> Dict[str, Any]:
    """
    Calculate intelligent wait time before next task request.

    Strategy:
    - Prioritizes tasks that unlock parallel work for idle agents
    - Uses 60% of ETA for early completion detection
    - Caps at 5 minutes for regular re-polling

    Uses:
    - Current progress of IN_PROGRESS tasks
    - Historical median task duration
    - Task dependencies and parallel work potential
    - Idle agent capacity

    Parameters
    ----------
    state : Any
        Marcus server state instance

    Returns
    -------
    Dict[str, Any]
        Dictionary with:
        - retry_after_seconds: int (wait time in seconds, max 300s)
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
            "retry_after_seconds": 30,  # 30 seconds
            "reason": "No tasks currently in progress - check back soon",
            "blocking_task": None,
        }

    # Get historical median duration
    global_median_hours = 1.0  # Default fallback
    if hasattr(state, "memory") and state.memory:
        global_median_hours = await state.memory.get_global_median_duration()

    # Calculate ETA for each in-progress task
    completion_estimates = []
    now = datetime.now(timezone.utc)

    for item in in_progress_tasks:
        task = item["task"]
        assignment = item["assignment"]

        # Get current progress (0-100)
        progress = getattr(task, "progress", 0) or 0

        # Calculate elapsed time in seconds
        # Ensure assignment.assigned_at is timezone-aware
        assigned_at = assignment.assigned_at
        if assigned_at.tzinfo is None:
            # Make naive datetime timezone-aware (assume UTC)
            assigned_at = assigned_at.replace(tzinfo=timezone.utc)
        elapsed_seconds = (now - assigned_at).total_seconds()

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

    # Count idle agents (registered but not currently working)
    total_agents = len(state.agent_status)
    busy_agents = len([a for a in state.agent_tasks.values() if a.task_id])
    idle_agents = max(0, total_agents - busy_agents)

    # Prioritize tasks that unlock parallel work for idle agents
    # This prevents waking up for sequential work that current workers can handle
    high_value_tasks = [
        est for est in completion_estimates if est["unlocks_count"] >= idle_agents
    ]

    # If we have tasks that unlock enough parallel work, prioritize those
    # Otherwise fall back to any task completion (sequential work is still work)
    candidate_tasks = high_value_tasks if high_value_tasks else completion_estimates

    # Sort candidates by ETA (soonest first)
    candidate_tasks.sort(key=lambda x: x["eta_seconds"])

    # Get the best task to wait for
    target_task = candidate_tasks[0]

    # Use 60% of ETA for retry to catch early completions
    # This accounts for tasks finishing faster than estimated
    retry_after = int(target_task["eta_seconds"] * 0.6)

    # Minimum 30 seconds to avoid excessive polling
    retry_after = max(30, retry_after)

    # Cap at 30 seconds for re-polling (catch unexpected early completions)
    retry_after = min(retry_after, 30)

    # Format reason
    eta_minutes = int(target_task["eta_seconds"] / 60)
    unlocks_info = (
        f" (unlocks {target_task['unlocks_count']} tasks)"
        if target_task["unlocks_count"] > 0
        else ""
    )
    reason = (
        f"Waiting for '{target_task['task_name']}' to complete "
        f"(~{eta_minutes} min, {target_task['progress']}% done){unlocks_info}"
    )

    return {
        "retry_after_seconds": retry_after,
        "reason": reason,
        "blocking_task": {
            "id": target_task["task_id"],
            "name": target_task["task_name"],
            "progress": target_task["progress"],
            "eta_seconds": int(target_task["eta_seconds"]),
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
    # Ensure lease monitor is running on the active event loop
    # (In HTTP mode, setup runs on a temporary loop that's abandoned)
    if hasattr(state, "ensure_lease_monitor_running"):
        await state.ensure_lease_monitor_running()

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
        # Phase timing for performance monitoring (GH-228)
        _perf_start = time.perf_counter()
        _perf_marks: Dict[str, float] = {}

        def _mark(name: str) -> None:
            _perf_marks[name] = (time.perf_counter() - _perf_start) * 1000

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
        _mark("state_refresh")

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
        _mark("task_selection")

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

                _mark("context_building")

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

                _mark("memory_predictions")

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
                        state=state,
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

                _mark("instruction_generation")

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
                    assigned_at=datetime.now(timezone.utc),
                    due_date=optimal_task.due_date,
                )

                # Update kanban FIRST (fail fast if kanban is down)
                await state.kanban_client.update_task(
                    optimal_task.id,
                    {"status": TaskStatus.IN_PROGRESS, "assigned_to": agent_id},
                )

                _mark("kanban_update")

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
                        "labels": (
                            optimal_task.labels
                            if hasattr(optimal_task, "labels")
                            else []
                        ),
                        "completion_criteria": (
                            optimal_task.completion_criteria
                            if hasattr(optimal_task, "completion_criteria")
                            else []
                        ),
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

                # Log phase timings (GH-228)
                _mark("total")
                task_count = len(state.project_tasks) if state.project_tasks else 0
                # total_ms is the cumulative wall-clock time
                total_ms = round(_perf_marks["total"], 2)
                # Convert cumulative marks to per-phase deltas
                _phases = list(_perf_marks.items())
                _phase_durations: Dict[str, float] = {}
                for i, (name, cumulative_ms) in enumerate(_phases):
                    prev_ms = _phases[i - 1][1] if i > 0 else 0.0
                    _phase_durations[name] = round(cumulative_ms - prev_ms, 2)
                logger.info(
                    "request_next_task timing: "
                    f"agent={agent_id} "
                    f"task={optimal_task.name!r} "
                    f"task_count={task_count} "
                    f"total_ms={total_ms} "
                    f"phases={_phase_durations}"
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
            # Only run diagnostics for LOGGING if tasks exist but can't be assigned
            # DO NOT send diagnostics to agents - they interpret them as reasons to stop
            todo_tasks = [t for t in state.project_tasks if t.status == TaskStatus.TODO]

            if todo_tasks:
                # Tasks exist but can't be assigned - run diagnostics FOR LOGGING ONLY
                logger.warning(
                    f"No tasks assignable but {len(todo_tasks)} TODO tasks exist - "
                    "running diagnostics for logs"
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

                # Run diagnostics FOR LOGGING ONLY - don't send to agents
                try:
                    diagnostic_report = await run_automatic_diagnostics(
                        project_tasks=state.project_tasks,
                        completed_task_ids=completed_task_ids,
                        assigned_task_ids=assigned_task_ids,
                    )

                    # Format report for logging (operators can see this)
                    formatted_report = format_diagnostic_report(diagnostic_report)
                    logger.info(
                        f"Diagnostic Report (for operators):\n{formatted_report}"
                    )

                except Exception as diag_error:
                    logger.error(
                        f"Diagnostic system error: {diag_error}", exc_info=True
                    )
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

            # Return ONLY the essential retry information
            # DO NOT include diagnostics or blocking_task info - agents interpret
            # these as reasons to stop working instead of retrying
            response = {
                "success": False,
                "message": instructions,
                "retry_after_seconds": retry_seconds,
                "retry_reason": retry_info["reason"],
            }

            return response

    except Exception as e:
        return {"success": False, "error": str(e)}


async def _validate_task_completion(task: Task, agent_id: str, state: Any) -> Any:
    """Validate task completion using WorkAnalyzer.

    Parameters
    ----------
    task : Task
        Task to validate
    agent_id : str
        Agent ID for logging
    state : Any
        Marcus server state

    Returns
    -------
    ValidationResult
        Validation result with pass/fail and issues
    """
    global _work_analyzer, _retry_tracker

    # Lazy imports to avoid circular dependency
    from src.ai.validation.retry_tracker import RetryTracker
    from src.ai.validation.work_analyzer import WorkAnalyzer

    # Initialize singletons with double-checked locking pattern
    if _work_analyzer is None or _retry_tracker is None:
        with _singleton_lock:
            if _work_analyzer is None:
                _work_analyzer = WorkAnalyzer()
            if _retry_tracker is None:
                _retry_tracker = RetryTracker()

    # Run validation
    validation_result = await _work_analyzer.validate_implementation_task(task, state)

    return validation_result


async def _handle_validation_failure(
    task: Task, agent_id: str, validation_result: Any, state: Any
) -> Dict[str, Any]:
    """Handle validation failure with hybrid remediation.

    First failure: Return response (task stays IN_PROGRESS, agent can retry)
    Retry with same issues: Create blocker

    The retry ceiling is evaluated by the caller BEFORE this function
    is invoked — when the ceiling is hit, the caller routes the task
    through the normal completion path with an escalation annotation
    rather than calling this function. See Codex P1 on PR #337 for
    the rationale.

    Parameters
    ----------
    task : Task
        Task that failed validation
    agent_id : str
        Agent ID
    validation_result : ValidationResult
        Validation result with issues
    state : Any
        Marcus server state

    Returns
    -------
    Dict[str, Any]
        Response indicating validation failure
    """
    current_attempts = (
        _retry_tracker.get_attempt_count(task.id) if _retry_tracker is not None else 0
    )

    # Check if this is a retry with same issues BEFORE recording
    is_retry_with_same_issues = False
    if _retry_tracker is not None:
        is_retry_with_same_issues = _retry_tracker.is_retry_with_same_issues(
            task.id, validation_result
        )

    # Format issues for response
    issues_list = [issue.to_dict() for issue in validation_result.issues]

    if is_retry_with_same_issues:
        # Agent is stuck - create blocker
        blocker_description = _format_blocker_description(validation_result)

        # Call report_blocker with WorkAnalyzer's validation advice
        await report_blocker(
            agent_id=agent_id,
            task_id=task.id,
            blocker_description=blocker_description,
            severity="high",
            state=state,
            skip_ai_analysis=True,  # Use WorkAnalyzer's advice, not Marcus's AI
        )

        # Record the attempt even when we create a blocker so the
        # retry ceiling can trip on the next attempt.
        if _retry_tracker is not None:
            _retry_tracker.record_attempt(task.id, validation_result)

        return {
            "success": False,
            "status": "validation_failed",
            "issues": issues_list,
            "blocker_created": True,
            "attempt_count": current_attempts + 1,
            "message": "Validation failed with same issues - blocker created. Review AI suggestions in blocker.",  # noqa: E501
        }
    else:
        # First failure or different issues - record attempt and return response
        if _retry_tracker is not None:
            _retry_tracker.record_attempt(task.id, validation_result)

        return {
            "success": False,
            "status": "validation_failed",
            "issues": issues_list,
            "attempt_count": current_attempts + 1,
            "message": "Task did not pass validation. Fix issues and retry completion.",
        }


def _format_blocker_description(validation_result: Any) -> str:
    """Format validation issues as blocker description.

    Parameters
    ----------
    validation_result : ValidationResult
        Validation result with issues

    Returns
    -------
    str
        Formatted blocker description
    """
    lines = [
        "🚫 VALIDATION BLOCKER - REPEATED FAILURES",
        "",
        "You've attempted to complete this task multiple times with the same issues.",
        "This suggests you may be stuck. Please carefully review the issues below:",
        "",
    ]

    for i, issue in enumerate(validation_result.issues, 1):
        lines.append(f"{i}. ❌ {issue.issue}")
        lines.append(f"   SEVERITY: {issue.severity.value.upper()}")
        lines.append(f"   EVIDENCE: {issue.evidence}")
        lines.append(f"   REMEDIATION: {issue.remediation}")
        lines.append(f"   CRITERION: {issue.criterion}")
        lines.append("")

    lines.append("IMPORTANT:")
    lines.append("- READ the remediation carefully - it tells you EXACTLY what to fix")
    lines.append("- Don't rebuild everything - fix the SPECIFIC issues listed above")
    lines.append("- If you're unsure, ask for help understanding the requirements")
    lines.append("")
    lines.append("Once you've fixed the issues, report progress to unblock the task.")

    return "\n".join(lines)


async def _merge_agent_branch_to_main(
    agent_id: str,
    task_id: str,
    state: Any,
) -> Optional[Dict[str, Any]]:
    """
    Merge agent's worktree branch to main after task completion.

    Convention: if branch marcus/{agent_id} exists, the agent used
    a worktree. Merge it to main so dependent tasks can see the code.

    If merge conflicts, abort and return failure — the agent must
    resolve conflicts and report completion again.

    Returns None if no merge needed, success dict if merged,
    or failure dict if conflicts.

    See: https://github.com/lwgray/marcus/issues/250
    """
    import subprocess as _sp
    from pathlib import Path

    # Find the main repo (implementation/ directory)
    # Use workspace state file to get project_root, then use
    # git rev-parse to find the actual repo root regardless
    # of whether we're in a worktree or the main repo.
    project_root = None
    if hasattr(state, "kanban_client") and state.kanban_client:
        ws_state = state.kanban_client._load_workspace_state()
        if ws_state and "project_root" in ws_state:
            project_root = ws_state["project_root"]

    if not project_root:
        return None

    # project_root points to implementation/ (main repo).
    # Use it directly — git commands run here.
    repo = Path(project_root)
    if not repo.exists():
        return None

    # Verify it's a git repo (or inside one)
    try:
        check = _sp.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        if check.returncode != 0:
            return None
    except Exception:
        return None

    branch = f"marcus/{agent_id}"

    # Check if this agent's branch exists
    try:
        result = _sp.run(
            ["git", "branch", "--list", branch],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        if not result.stdout.strip():
            # No worktree branch — agent worked on main directly
            return None
    except Exception:
        return None

    logger.info(
        f"[worktree] Merging {branch} to main " f"after task {task_id} completion"
    )

    try:
        # Checkout main
        _sp.run(
            ["git", "checkout", "main"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Attempt merge
        merge = _sp.run(
            [
                "git",
                "merge",
                branch,
                "--no-ff",
                "-m",
                f"Merge {branch} (task {task_id} by {agent_id})",
            ],
            cwd=repo,
            capture_output=True,
            text=True,
        )

        if merge.returncode == 0:
            logger.info(f"[worktree] Successfully merged {branch} to main")
            return {"success": True}
        else:
            # Merge conflict — abort and send agent back
            _sp.run(
                ["git", "merge", "--abort"],
                cwd=repo,
                capture_output=True,
            )
            logger.warning(
                f"[worktree] Merge conflict for {branch}: " f"{merge.stderr}"
            )
            return {
                "success": False,
                "error": "merge_conflict",
                "message": (
                    f"Your task passed validation but merging "
                    f"your branch ({branch}) to main has "
                    f"conflicts. Please resolve them:\n"
                    f"  git merge main\n"
                    f"  (resolve conflicts in your editor)\n"
                    f"  git add . && git commit\n"
                    f"Then report completion again."
                ),
            }

    except Exception as e:
        logger.warning(f"[worktree] Merge failed: {e}")
        # Don't block completion if git is unavailable
        return None


async def report_task_progress(
    agent_id: str,
    task_id: str,
    status: str,
    progress: int,
    message: str,
    state: Any,
    start_command: Optional[str] = None,
    readiness_probe: Optional[str] = None,
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
    start_command : Optional[str]
        Shell-style command that Marcus should run to verify the
        deliverable actually starts. REQUIRED when completing an
        integration verification task (``"type:integration"`` label);
        ignored on all other tasks. Examples:

        - ``"npm run build"`` for a Node build
        - ``"python -m mypackage --help"`` for a Python CLI
        - ``"tsc --noEmit"`` for a TypeScript type check
        - ``"uvicorn main:app --port 8000"`` for a long-running server
          (pair with a ``readiness_probe``)

        When the agent declares this on an integration task, Marcus
        runs it as a subprocess with a 60s timeout (one-shot mode) or
        15s readiness window (server mode). Missing on an integration
        task completion → the completion is rejected.
    readiness_probe : Optional[str]
        Optional shell-style command that Marcus polls to detect when
        a long-running server is ready. When provided alongside
        ``start_command``, Marcus starts the command in the background
        and polls the probe every 1s for up to 15s. Pass requires the
        probe to return exit 0 at least once within that window.
        Marcus always kills the background process before accepting
        the completion. Examples:

        - ``"curl -f http://localhost:8000/health"``
        - ``"curl -f http://localhost:3000/"``

        Absent ``readiness_probe``, Marcus treats the start_command as
        a one-shot that must exit 0 within 60s.

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

    # Escalation flag — set when the retry ceiling is hit during
    # validation. The task is routed through the normal completion
    # path (kanban update, lease cleanup, branch merge) but the
    # final response surfaces the escalation so the caller and any
    # downstream observers know the validator's complaints were
    # overridden. See MAX_VALIDATION_RETRIES constant above.
    validation_escalated: bool = False
    escalation_payload: Optional[Dict[str, Any]] = None

    try:
        # Initialize kanban if needed
        await state.initialize_kanban()

        # Log Marcus thinking
        log_thinking(
            "marcus",
            f"Processing progress update from {agent_id}",
            {"task_id": task_id, "status": status, "progress": progress},
        )

        # Stale-completion guard for recovered tasks (Issue #343).
        # When a task's lease expires and is recovered to another
        # agent, the original agent's in-memory assignment is
        # cleared by ``on_recovery_callback`` (see server.py:699).
        # If that original agent keeps working locally and later
        # reports completion (unaware their assignment was revoked),
        # Marcus must reject the stale completion — otherwise we
        # accept a second completion on a task another agent is
        # actively working on, and the two implementations collide
        # at merge time. Dashboard-v70 produced 341 lines of ghost
        # source + 506 lines of ghost tests this way.
        #
        # The guard fires on ``status == "completed"`` only. Agents
        # can still report intermediate progress even if their
        # assignment was cleared — that path recreates the lease
        # (see "No active lease" fallback below) rather than
        # producing a persistent kanban mutation. Completions, by
        # contrast, write DONE to kanban and trigger branch merges
        # that cannot be undone cleanly.
        if status == "completed":
            current_assignment = state.agent_tasks.get(agent_id)
            assignment_task_id = (
                getattr(current_assignment, "task_id", None)
                if current_assignment is not None
                else None
            )
            if assignment_task_id != task_id:
                # Cold-cache fallback (Codex P1 review on PR #345).
                # ``state.agent_tasks`` is in-memory only and starts
                # empty on Marcus restart; ``MarcusServer.__init__``
                # never rehydrates it from ``assignment_persistence``.
                # The lease manager, by contrast, IS rebuilt from
                # persistence on startup (see
                # ``AssignmentLeaseManager`` setup in server.py),
                # which makes it the authoritative source for
                # "who currently holds this task" across a restart.
                #
                # Without this fallback, every legitimate post-
                # restart completion would be rejected as stale
                # and the task would stay stuck in progress until
                # manual intervention. We only declare the
                # completion stale when BOTH in-memory cache AND
                # the lease manager say this agent isn't the holder.
                lease_holder_matches = False
                if hasattr(state, "lease_manager") and state.lease_manager is not None:
                    try:
                        lease = state.lease_manager.active_leases.get(task_id)
                        if (
                            lease is not None
                            and getattr(lease, "agent_id", None) == agent_id
                        ):
                            lease_holder_matches = True
                            logger.info(
                                f"Stale completion guard: in-memory "
                                f"agent_tasks cache miss for "
                                f"{agent_id}/{task_id}, but lease "
                                f"manager confirms this agent holds "
                                f"the task — allowing completion "
                                f"(cold-cache recovery, Codex P1 on "
                                f"PR #345)"
                            )
                    except Exception as lease_err:
                        # Lease lookup failed for some reason.
                        # Don't crash the completion path; fall
                        # through to the rejection. Worst case the
                        # agent retries and we eventually rebuild
                        # the cache.
                        logger.warning(
                            f"Stale completion guard: lease lookup "
                            f"raised for {task_id}: {lease_err}. "
                            f"Falling through to default rejection."
                        )

                if not lease_holder_matches:
                    logger.warning(
                        f"Rejecting stale completion: agent {agent_id} "
                        f"tried to complete task {task_id} but is no "
                        f"longer assigned to it (current assignment: "
                        f"{assignment_task_id!r}, lease holder check "
                        f"failed). This usually means the task's "
                        f"lease expired and was recovered to another "
                        f"agent while the original agent was still "
                        f"working on it. Issue #343."
                    )
                    return {
                        "success": False,
                        "status": "stale_completion",
                        "error": "task_recovered",
                        "message": (
                            f"Cannot complete task {task_id}: your "
                            f"assignment was revoked because the "
                            f"lease expired and another agent took "
                            f"ownership. Your work on branch "
                            f"marcus/{agent_id} is preserved in git "
                            f"— request your next task to continue."
                        ),
                    }

        # Update task in kanban
        update_data: Dict[str, Any] = {"progress": progress}

        # VALIDATION GATE: Check if implementation task needs validation
        if status == "completed":
            # CRITICAL: Fetch fresh task from Kanban to get current labels
            # state.project_tasks has stale data from project initialization
            # Labels are added AFTER task creation, so we need fresh data
            fresh_tasks = await state.kanban_client.get_all_tasks()
            task = next((t for t in fresh_tasks if t.id == task_id), None)

            logger.info(
                f"VALIDATION GATE: Task {task_id} completed, "
                f"found task object: {task is not None}"
            )

            # Lazy import to avoid circular dependency
            from src.ai.validation.task_filter import should_validate_task

            if task:
                task_labels = task.labels if hasattr(task, "labels") else None
                should_validate = should_validate_task(task)
                logger.info(
                    f"VALIDATION GATE: Task {task_id} ({task.name}) - "
                    f"labels={task_labels}, should_validate={should_validate}"
                )

                if should_validate:
                    try:
                        logger.info(
                            f"VALIDATION GATE: Starting validation for {task_id}"
                        )
                        # Run validation
                        validation_result = await _validate_task_completion(
                            task, agent_id, state
                        )

                        # Handle failure
                        if not validation_result.passed:
                            # Retry ceiling check (Codex P1 on PR #337).
                            # Must run INLINE, before the failure
                            # handler, so escalated tasks fall through
                            # to the normal completion path below —
                            # otherwise the escalation response
                            # short-circuits kanban completion and
                            # leaves the task stuck IN_PROGRESS.
                            current_attempts = (
                                _retry_tracker.get_attempt_count(task.id)
                                if _retry_tracker is not None
                                else 0
                            )
                            if current_attempts >= MAX_VALIDATION_RETRIES:
                                logger.warning(
                                    f"VALIDATION ESCALATION: task "
                                    f"{task.id} ({task.name}) hit "
                                    f"{MAX_VALIDATION_RETRIES} validation "
                                    f"failures. Routing through normal "
                                    f"completion path with escalation "
                                    f"annotation. Final issues: "
                                    f"{[i.issue[:80] for i in validation_result.issues]}"  # noqa: E501
                                )
                                # Record this attempt so history is
                                # complete.
                                if _retry_tracker is not None:
                                    _retry_tracker.record_attempt(
                                        task.id, validation_result
                                    )
                                validation_escalated = True
                                escalation_payload = {
                                    "status": "validation_escalated",
                                    "escalated": True,
                                    "attempt_count": current_attempts + 1,
                                    "issues": [
                                        issue.to_dict()
                                        for issue in validation_result.issues
                                    ],
                                    "message": (
                                        f"Validation escalated after "
                                        f"{MAX_VALIDATION_RETRIES} failed "
                                        f"attempts. Task auto-passed via "
                                        f"the completion pipeline; "
                                        f"validator complaints logged for "
                                        f"review. This usually means the "
                                        f"validator is hallucinating or "
                                        f"the criteria need refinement."
                                    ),
                                }
                                # Fall through to the completion path.
                            else:
                                return await _handle_validation_failure(
                                    task, agent_id, validation_result, state
                                )
                    except Exception as e:
                        # Validation system failed - log and allow completion
                        logger.error(f"Validation system error: {e}")
                        logger.exception("Validation exception details:")
                else:
                    logger.info(
                        f"VALIDATION GATE: Skipping validation for {task_id} "
                        f"(not an implementation task)"
                    )

            # PRODUCT SMOKE GATE (Layer 1 of the systemic
            # integration-verification fix). Integration verification
            # tasks have label "type:integration" and are NOT
            # validated by the citation-based LLM validator above
            # (they aren't implementation tasks). Their entire job
            # is to assemble the deliverable and prove it works —
            # so the right gate for them is a deterministic
            # Marcus-side check that the declared start_command
            # actually runs. This catches the dashboard-v71 class
            # of bug where the integration agent self-reports
            # success but the assembled deliverable fails to boot
            # (e.g. missing public/index.html).
            #
            # The smoke gate runs ``verify_deliverable`` as a
            # subprocess-level check against the agent-declared
            # start_command + optional readiness_probe. If the
            # start_command is missing (strict enforcement) or the
            # declared command fails, the task is rejected. This is
            # the same machine-beats-prompt pattern as PR #337's
            # runtime tests overriding LLM validation opinions.
            if task is not None and _is_integration_task(task):
                try:
                    smoke_response = await _run_product_smoke_gate(
                        task=task,
                        agent_id=agent_id,
                        state=state,
                        start_command=start_command,
                        readiness_probe=readiness_probe,
                    )
                    if smoke_response is not None:
                        return smoke_response
                except Exception as smoke_err:
                    # Smoke verification system error (not a smoke
                    # failure — those return a response above). Log
                    # and allow completion to proceed rather than
                    # blocking on infrastructure problems we don't
                    # understand. This matches the validation-error
                    # fallthrough policy above.
                    logger.error(
                        f"Product smoke verification system error "
                        f"for task {task_id}: {smoke_err}"
                    )
                    logger.exception("Smoke verification exception details:")

        if status == "completed":
            update_data["status"] = TaskStatus.DONE
            update_data["completed_at"] = datetime.now(timezone.utc).isoformat()

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
                # Ensure start_time is timezone-aware
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)
                now_utc = datetime.now(timezone.utc)
                actual_hours = (now_utc - start_time).total_seconds() / 3600
                duration_seconds = (now_utc - start_time).total_seconds()
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

            # Merge agent's worktree branch to main (GH-250)
            # Convention: if branch marcus/{agent_id} exists,
            # the agent used a worktree and needs merging.
            # If merge conflicts, send agent back to resolve
            # (same pattern as validation failure).
            merge_result = await _merge_agent_branch_to_main(agent_id, task_id, state)
            if merge_result and not merge_result.get("success"):
                return merge_result

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
                    # Ensure start_time is timezone-aware
                    if start_time.tzinfo is None:
                        start_time = start_time.replace(tzinfo=timezone.utc)
                    actual_hours = (
                        datetime.now(timezone.utc) - start_time
                    ).total_seconds() / 3600
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
                # No active lease (likely recovered via false positive).
                # Recreate it so the monitor can continue watching for
                # real agent death.
                task_obj = next(
                    (t for t in state.project_tasks if t.id == task_id), None
                )
                new_lease = await state.lease_manager.create_lease(
                    task_id, agent_id, task_obj
                )
                logger.info(
                    f"Recreated lease for task {task_id} "
                    f"after recovery (expires: "
                    f"{new_lease.lease_expires.isoformat()})"
                )

        # Log response
        conversation_logger.log_worker_message(
            agent_id,
            "from_pm",
            f"Progress update received: {status} at {progress}%",
            {"acknowledged": True, **project_context},
        )

        # DON'T refresh after task updates - causes race condition with Kanban
        # Parent task completion updates Kanban asynchronously, refresh may
        # fetch stale data and overwrite in-memory DONE status, causing tasks
        # to revert to TODO. Let refresh happen on next request_next_task
        # instead. NOTE: This may affect README documentation task visibility -
        # monitor for that

        # If the validation retry ceiling was hit, surface the
        # escalation details on the success response. The task has
        # already been routed through the full completion path
        # (kanban DONE, memory recorded, lease cleared, branch
        # merged) so the agent can move on, but the escalation
        # annotation tells observers the validator's complaints
        # were overridden.
        if validation_escalated and escalation_payload is not None:
            return {
                "success": True,
                "message": ("Progress updated successfully (validation escalated)"),
                **escalation_payload,
            }

        return {"success": True, "message": "Progress updated successfully"}

    except Exception as e:
        # Atomicity guarantee for the escalation path (review of
        # PR #337 post-Codex): if the retry ceiling was hit during
        # validation and the completion pipeline raised partway
        # through, the escalation signal would otherwise be lost
        # from the response. Preserve escalation context so the
        # caller can distinguish "validation escalated AND pipeline
        # failed" from "generic completion error." The retry
        # tracker has already recorded the escalation attempt, so
        # the next completion request will hit the ceiling again
        # and re-run the pipeline.
        if validation_escalated and escalation_payload is not None:
            logger.error(
                f"Completion pipeline error AFTER escalation for "
                f"task {task_id}: {e}. Escalation was recorded; "
                f"task may be in partially-updated kanban state. "
                f"Next completion attempt will re-run the pipeline."
            )
            return _build_escalation_error_response(e, escalation_payload)
        return {"success": False, "error": str(e)}


def _build_escalation_error_response(
    exc: BaseException, escalation_payload: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge escalation context into an error response.

    Used when the validation retry ceiling was hit (escalation
    decided) but the completion pipeline subsequently raised. The
    returned dict carries both failure context and the escalation
    annotation so downstream consumers can tell the two states
    apart and so the agent knows the task was escalated even
    though the pipeline didn't finish. See the escalation
    atomicity guarantee in ``report_task_progress``.

    Parameters
    ----------
    exc : BaseException
        The exception raised by the completion pipeline.
    escalation_payload : Dict[str, Any]
        The escalation payload assembled at retry-ceiling time.

    Returns
    -------
    Dict[str, Any]
        Error response with escalation context merged in.
    """
    return {
        "success": False,
        "error": str(exc),
        "validation_escalated": True,
        "escalation_pipeline_error": True,
        **escalation_payload,
        "message": (
            f"Validation was escalated after "
            f"{MAX_VALIDATION_RETRIES} failed attempts, but the "
            f"completion pipeline failed: {exc}. Task state may "
            f"be inconsistent — retry completion to re-run the "
            f"pipeline."
        ),
    }


async def report_blocker(
    agent_id: str,
    task_id: str,
    blocker_description: str,
    severity: str,
    state: Any,
    skip_ai_analysis: bool = False,
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
    skip_ai_analysis : bool, default=False
        If True, skip Marcus's AI analysis (use when blocker_description
        already contains WorkAnalyzer's validation advice)

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
        # (skip if WorkAnalyzer already provided validation advice)
        if skip_ai_analysis:
            suggestions = blocker_description  # Use WorkAnalyzer's advice directly
        else:
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
            "board_assigned": 0,
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

        # Build slug-to-ID mapping for dependency resolution
        # Bundled design tasks are created with slug IDs like
        # "design_productivity_tools" but get replaced with numeric Planka IDs
        # when synced to the board. Dependencies still reference the slug, so
        # we need to map slug → numeric ID.
        slug_to_id: dict[str, str] = {}
        for t in state.project_tasks:
            # Look for Design tasks - they have labels like:
            # ['design', 'architecture', 'productivity tools']
            if (
                t.name
                and "Design" in t.name
                and hasattr(t, "labels")
                and t.labels
                and len(t.labels) >= 3
            ):
                # Extract domain from labels
                # (last non-design/architecture label)
                domain_labels = [
                    label
                    for label in t.labels
                    if label.lower() not in ["design", "architecture"]
                ]
                if domain_labels:
                    # Create slug from domain label:
                    # "productivity tools" → "design_productivity_tools"
                    domain = domain_labels[-1]
                    slug = f"design_{domain.lower().replace(' ', '_')}"
                    slug_to_id[slug] = str(t.id)
                    logger.debug(f"Mapped slug '{slug}' → task ID {t.id} ('{t.name}')")

        logger.info(
            f"Built slug-to-ID mapping with {len(slug_to_id)} entries: "
            f"{dict(list(slug_to_id.items())[:5])}"  # Show first 5
        )

        # Filter tasks: TODO, not assigned, and all dependencies completed
        available_tasks = []
        for t in state.project_tasks:
            if t.status != TaskStatus.TODO:
                filtering_stats["todo_status"] += 1
                continue
            if t.id in all_assigned_ids:
                filtering_stats["already_assigned"] += 1
                continue

            # Skip tasks owned on the board (assigned_to is set).
            # Design tasks are assigned to "Marcus" and handled
            # internally. Agent tasks get assigned_to set on
            # assignment. Recovery clears assigned_to to release
            # tasks back to the pool.
            if t.assigned_to:
                filtering_stats["board_assigned"] += 1
                logger.debug(
                    f"Skipping '{t.name}' — assigned to " f"'{t.assigned_to}' on board"
                )
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

            # Check dependencies - resolve slugs to actual IDs first
            deps = t.dependencies or []
            resolved_deps = []
            for dep_id in deps:
                # If it's a slug, try to resolve it; otherwise use as-is
                if dep_id in slug_to_id:
                    resolved_deps.append(slug_to_id[dep_id])
                else:
                    resolved_deps.append(dep_id)

            all_deps_complete = all(
                dep_id in completed_task_ids for dep_id in resolved_deps
            )

            if not all_deps_complete:
                filtering_stats["incomplete_dependencies"] += 1
                # Log which dependencies are not complete
                incomplete_deps = [
                    dep_id
                    for dep_id in resolved_deps
                    if dep_id not in completed_task_ids
                ]
                logger.info(
                    f"Task '{t.name}' has incomplete dependencies: {incomplete_deps} "
                    f"(original: {deps}, resolved: {resolved_deps})"
                )
                continue

            # CRITICAL: If this is a subtask, also check parent's dependencies
            # Subtasks should not start until their parent's dependencies are met
            if t.is_subtask and t.parent_task_id:
                parent_task = next(
                    (p for p in state.project_tasks if p.id == t.parent_task_id), None
                )
                if parent_task:
                    parent_deps = parent_task.dependencies or []
                    parent_resolved_deps = []
                    for dep_id in parent_deps:
                        if dep_id in slug_to_id:
                            parent_resolved_deps.append(slug_to_id[dep_id])
                        else:
                            parent_resolved_deps.append(dep_id)

                    parent_deps_complete = all(
                        dep_id in completed_task_ids for dep_id in parent_resolved_deps
                    )

                    if not parent_deps_complete:
                        incomplete_parent_deps = [
                            dep_id
                            for dep_id in parent_resolved_deps
                            if dep_id not in completed_task_ids
                        ]
                        logger.info(
                            f"Subtask '{t.name}' blocked: parent task "
                            f"'{parent_task.name}' has incomplete dependencies: "
                            f"{incomplete_parent_deps}"
                        )
                        filtering_stats["incomplete_dependencies"] += 1
                        continue

            available_tasks.append(t)

        # Special handling for README documentation
        # Calculate project completion percentage
        # Exclude README documentation tasks from the calculation since they should only
        # be assigned after other tasks are complete
        total_non_doc_tasks = len(
            [
                t
                for t in state.project_tasks
                if "README" not in t.name
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
                and "README" not in t.name
                and not any(
                    label in (t.labels or [])
                    for label in ["documentation", "final", "verification"]
                )
            ]
        )

        # Special case: If README documentation is the only task left, make it available
        readme_doc_tasks = [t for t in available_tasks if "README" in t.name]
        if readme_doc_tasks and len(available_tasks) == len(readme_doc_tasks):
            # All available tasks are README documentation tasks, don't filter them
            logger.debug(
                "README documentation is the only available task - making it assignable"
            )
        elif total_non_doc_tasks > 0:
            completion_percentage = (
                completed_non_doc_tasks / total_non_doc_tasks
            ) * 100

            # Filter out README documentation tasks if not nearly complete
            # Using 90% threshold since some tasks might be blocked
            if completion_percentage < 90:
                available_tasks = [t for t in available_tasks if "README" not in t.name]
                logger.debug(
                    f"Filtering out README documentation tasks - project only "
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
