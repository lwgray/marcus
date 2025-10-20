"""
Cross-parent dependency wiring for Marcus.

This module handles automatic creation of dependencies between subtasks
of different parent tasks using a hybrid approach:
1. Embedding-based filtering for fast candidate selection
2. LLM reasoning for accurate dependency decisions
3. Sanity checks to prevent graph corruption
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from src.core.models import Task

logger = logging.getLogger(__name__)


def filter_candidates_by_embeddings(
    subtask: Task,
    all_tasks: List[Task],
    embedding_model: Any,
    similarity_threshold: float = 0.6,
    max_candidates: int = 10,
) -> List[Tuple[Task, float]]:
    """
    Filter potential dependency candidates using semantic embeddings.

    Uses sentence transformers to compute semantic similarity between
    the subtask's requires field and other tasks' provides fields.
    This is a fast first-pass filter to reduce the search space before
    calling the expensive LLM.

    Parameters
    ----------
    subtask : Task
        The subtask we're analyzing
    all_tasks : List[Task]
        All tasks in the project
    embedding_model : Any
        Sentence transformer model for computing embeddings
    similarity_threshold : float
        Minimum cosine similarity to consider (default 0.6)
    max_candidates : int
        Maximum number of candidates to return (default 10)

    Returns
    -------
    List[Tuple[Task, float]]
        List of (task, similarity_score) tuples, sorted by similarity
    """
    if not subtask.requires:
        return []

    # Skip if no embedding model available
    if embedding_model is None:
        logger.warning("No embedding model available, skipping embedding filter")
        return [(task, 1.0) for task in all_tasks if task.is_subtask][:max_candidates]

    # Compute embedding for requires text
    try:
        requires_embedding = embedding_model.encode(subtask.requires)
    except Exception as e:
        logger.error(f"Failed to encode requires text: {e}")
        return []

    candidates = []

    for task in all_tasks:
        # Skip non-subtasks, self, and tasks without provides
        if not task.is_subtask or task.id == subtask.id or not task.provides:
            continue

        # Skip subtasks from same parent (handled by intra-parent deps)
        if task.parent_task_id == subtask.parent_task_id:
            continue

        try:
            # Compute embedding for provides text
            provides_embedding = embedding_model.encode(task.provides)

            # Calculate cosine similarity
            similarity = np.dot(requires_embedding, provides_embedding) / (
                np.linalg.norm(requires_embedding) * np.linalg.norm(provides_embedding)
            )

            if similarity >= similarity_threshold:
                candidates.append((task, float(similarity)))

        except Exception as e:
            logger.warning(f"Failed to compute similarity for task {task.id}: {e}")
            continue

    # Sort by similarity descending and limit to max_candidates
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[:max_candidates]


async def resolve_dependencies_with_llm(
    subtask: Task,
    candidates: List[Task],
    ai_engine: Any,
) -> Dict[str, Any]:
    """
    Use LLM to determine which candidates are true dependencies.

    Given a subtask and a list of candidate provider tasks (from embedding filter),
    asks the LLM to reason about which ones should actually be dependencies.

    Parameters
    ----------
    subtask : Task
        The subtask we're analyzing
    candidates : List[Task]
        Candidate provider tasks (from embedding filter)
    ai_engine : Any
        AI engine for LLM reasoning

    Returns
    -------
    Dict[str, Any]
        Dictionary with:
        - dependencies: List[str] of task IDs to add as dependencies
        - reasoning: Dict[str, str] explaining each decision
    """
    if not candidates:
        return {"dependencies": [], "reasoning": {}}

    # Build prompt with candidate information
    prompt = f"""You are analyzing task dependencies for a project management system.

**Task to analyze:**
- ID: {subtask.id}
- Name: {subtask.name}
- Parent Task ID: {subtask.parent_task_id}
- Description: {subtask.description}
- Requires: {subtask.requires}
- Current dependencies: {subtask.dependencies}

**Candidate provider tasks (potential dependencies):**
"""

    for idx, candidate in enumerate(candidates, 1):
        prompt += f"""
{idx}. ID: {candidate.id}
   Name: {candidate.name}
   Parent Task ID: {candidate.parent_task_id}
   Provides: {candidate.provides}
   Description: {candidate.description}
"""

    prompt += """
**Your task:**
Determine which (if any) of these candidates should be added as dependencies for the task being analyzed.  # noqa: E501

**Critical rules:**
1. Only create dependency if the task TRULY NEEDS the output/artifact from the candidate  # noqa: E501
2. Match the "Requires" field semantically with "Provides" fields
3. DO NOT create dependencies on tasks from the same parent (same parent_task_id) - these are already handled  # noqa: E501
4. Consider task workflow: Design → Implement → Test
   - Implementation tasks should depend on Design tasks
   - Test tasks should depend on Implementation tasks
   - Design tasks should NOT depend on Implementation
5. Conservative approach: When in doubt, DON'T create the dependency (false negative is better than false positive)  # noqa: E501
6. A task requiring "API specification" should depend on the task that provides the actual specification, not the research that informed it  # noqa: E501

**Examples of good matches:**
- Requires: "User model schema from Design phase" + Provides: "Complete user data schema with field definitions" → MATCH  # noqa: E501
- Requires: "API specification" + Provides: "Detailed API specification for endpoint" → MATCH

**Examples of bad matches:**
- Requires: "User API schema" + Provides: "Product API schema" → NO MATCH (different domains)  # noqa: E501
- Requires: "API specification" + Provides: "Research findings on API design" → NO MATCH (research ≠ specification)  # noqa: E501
- Requires: "Integration test results" + Provides: "Unit test results" → NO MATCH (different test types)  # noqa: E501

**Response format (JSON only, no markdown):**
{{
  "dependencies": ["task_id1", "task_id2"],
  "reasoning": {{
    "task_id1": "Brief explanation why this IS a dependency",
    "task_id2": "Brief explanation why this IS a dependency",
    "rejected_task_id3": "Brief explanation why this was REJECTED"
  }}
}}
"""

    try:
        response = await ai_engine.generate_structured_response(
            prompt=prompt,
            system_prompt=(
                "You are an expert at analyzing task dependencies and data flow "
                "in software projects. Respond with valid JSON only."
            ),
            response_format={
                "type": "object",
                "properties": {
                    "dependencies": {"type": "array", "items": {"type": "string"}},
                    "reasoning": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                },
                "required": ["dependencies", "reasoning"],
            },
        )

        # Cast response to Dict[str, Any] for type safety
        typed_response: Dict[str, Any] = dict(response)
        return typed_response

    except Exception as e:
        logger.error(f"LLM dependency resolution failed for {subtask.id}: {e}")
        result: Dict[str, Any] = {"dependencies": [], "reasoning": {"error": str(e)}}
        return result


def would_create_cycle(
    from_task_id: str, to_task_id: str, all_tasks: List[Task]
) -> bool:
    """
    Check if adding a dependency would create a circular dependency.

    Uses depth-first search to detect if adding edge from_task_id → to_task_id
    would create a cycle in the dependency graph.

    Parameters
    ----------
    from_task_id : str
        The task that would gain a new dependency
    to_task_id : str
        The task being added as a dependency
    all_tasks : List[Task]
        All tasks in the project

    Returns
    -------
    bool
        True if adding this dependency would create a cycle
    """
    # Build adjacency list
    graph: Dict[str, List[str]] = {}
    for task in all_tasks:
        if task.dependencies:
            graph[task.id] = list(task.dependencies)
        else:
            graph[task.id] = []

    # Add proposed edge
    if from_task_id not in graph:
        graph[from_task_id] = []
    graph[from_task_id].append(to_task_id)

    # DFS to detect cycle
    visited: Set[str] = set()
    rec_stack: Set[str] = set()

    def has_cycle_dfs(node: str) -> bool:
        visited.add(node)
        rec_stack.add(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if has_cycle_dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                # Back edge found - cycle detected!
                return True

        rec_stack.remove(node)
        return False

    return has_cycle_dfs(from_task_id)


def validate_phase_order(subtask: Task, dependency_task: Task) -> bool:
    """
    Validate that dependency follows proper phase ordering.

    Ensures dependencies follow Design → Implement → Test workflow.
    For example, Implementation can depend on Design, but Design
    cannot depend on Implementation.

    Parameters
    ----------
    subtask : Task
        The task that would gain the dependency
    dependency_task : Task
        The task being added as a dependency

    Returns
    -------
    bool
        True if phase ordering is valid
    """
    phase_order = {"design": 0, "implement": 1, "test": 2, "integration": 3}

    def extract_phase(task_name: str) -> Optional[str]:
        """Extract phase from task name (e.g., 'Design API' → 'design')."""
        name_lower = task_name.lower()
        for phase in phase_order.keys():
            if name_lower.startswith(phase):
                return phase
        return None

    subtask_phase = extract_phase(subtask.name)
    dep_phase = extract_phase(dependency_task.name)

    # If we can't determine phases, allow the dependency
    if subtask_phase is None or dep_phase is None:
        return True

    # Check phase ordering
    if phase_order[subtask_phase] < phase_order[dep_phase]:
        logger.warning(
            f"Invalid phase order: {subtask.name} ({subtask_phase}) "
            f"cannot depend on {dependency_task.name} ({dep_phase})"
        )
        return False

    return True


async def hybrid_dependency_resolution(
    subtask: Task,
    all_tasks: List[Task],
    ai_engine: Any,
    embedding_model: Optional[Any] = None,
) -> List[str]:
    """
    Find cross-parent dependencies using hybrid approach.

    Combines embeddings (fast filtering) with LLM reasoning (accurate decisions)
    and sanity checks (prevent errors).

    Parameters
    ----------
    subtask : Task
        The subtask to analyze
    all_tasks : List[Task]
        All tasks in the project
    ai_engine : Any
        AI engine for LLM reasoning
    embedding_model : Optional[Any]
        Sentence transformer model for embeddings (optional)

    Returns
    -------
    List[str]
        List of task IDs to add as dependencies
    """
    # Stage 1: Filter candidates using embeddings
    candidates_with_scores = filter_candidates_by_embeddings(
        subtask, all_tasks, embedding_model
    )

    if not candidates_with_scores:
        logger.debug(f"No embedding candidates found for {subtask.name}")
        return []

    candidates = [task for task, _ in candidates_with_scores]

    logger.info(
        f"Found {len(candidates)} embedding candidates for {subtask.name}: "
        f"{[c.name for c in candidates]}"
    )

    # Stage 2: Use LLM to make final decision
    llm_result = await resolve_dependencies_with_llm(subtask, candidates, ai_engine)

    proposed_deps = llm_result.get("dependencies", [])
    reasoning = llm_result.get("reasoning", {})

    logger.info(f"LLM proposed {len(proposed_deps)} dependencies for {subtask.name}")
    for dep_id, reason in reasoning.items():
        logger.debug(f"  {dep_id}: {reason}")

    # Stage 3: Sanity checks
    validated_deps = []

    for dep_id in proposed_deps:
        # Check: Dependency exists
        dep_task = next((t for t in all_tasks if t.id == dep_id), None)
        if not dep_task:
            logger.warning(f"Dependency {dep_id} not found, skipping")
            continue

        # Check: Not same parent (should be filtered earlier, but double-check)
        if dep_task.parent_task_id == subtask.parent_task_id:
            logger.info(f"Skipping {dep_id} - same parent task")
            continue

        # Check: Would not create cycle
        if would_create_cycle(subtask.id, dep_id, all_tasks):
            logger.error(f"Rejecting {dep_id} - would create circular dependency!")
            continue

        # Check: Valid phase ordering
        if not validate_phase_order(subtask, dep_task):
            logger.warning(f"Rejecting {dep_id} - invalid phase order")
            continue

        # All checks passed
        validated_deps.append(dep_id)

    return validated_deps


async def wire_cross_parent_dependencies(
    project_tasks: List[Task],
    ai_engine: Any,
    embedding_model: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Create cross-parent dependencies using hybrid matching.

    After all tasks have been decomposed, this function analyzes each subtask's
    'requires' field and matches it against other subtasks' 'provides' fields
    to create fine-grained cross-parent dependencies.

    Parameters
    ----------
    project_tasks : List[Task]
        All tasks in the project (parents and subtasks)
    ai_engine : Any
        AI engine for LLM reasoning
    embedding_model : Optional[Any]
        Sentence transformer model for embeddings (optional)

    Returns
    -------
    Dict[str, Any]
        Statistics about dependency wiring:
        - subtasks_analyzed: Number of subtasks analyzed
        - dependencies_created: Number of cross-parent deps created
        - llm_calls: Number of LLM calls made
        - rejected_cycles: Number of deps rejected due to cycles
        - total_time: Time taken in seconds
    """
    import time

    start_time = time.time()

    stats: Dict[str, Any] = {
        "subtasks_analyzed": 0,
        "dependencies_created": 0,
        "llm_calls": 0,
        "rejected_cycles": 0,
        "skipped_no_requires": 0,
        "skipped_no_candidates": 0,
    }

    logger.info(
        f"Starting cross-parent dependency wiring for {len(project_tasks)} tasks"
    )

    for task in project_tasks:
        # Only analyze subtasks with requires field
        if not task.is_subtask:
            continue

        if not task.requires:
            stats["skipped_no_requires"] += 1
            continue

        # CRITICAL: If parent task has NO dependencies, subtask can't have
        # cross-parent dependencies (only intra-parent dependencies allowed)
        parent_task = next(
            (t for t in project_tasks if t.id == task.parent_task_id), None
        )
        if parent_task and (
            not parent_task.dependencies or len(parent_task.dependencies) == 0
        ):
            logger.debug(
                f"Skipping {task.name} - parent '{parent_task.name}' has no "
                "dependencies, so this subtask can only have intra-parent dependencies"
            )
            if "skipped_parent_no_deps" not in stats:
                stats["skipped_parent_no_deps"] = 0
            stats["skipped_parent_no_deps"] += 1
            continue

        stats["subtasks_analyzed"] += 1

        logger.debug(f"Analyzing {task.name} (requires: {task.requires})")

        # Find dependencies using hybrid approach
        new_deps = await hybrid_dependency_resolution(
            subtask=task,
            all_tasks=project_tasks,
            ai_engine=ai_engine,
            embedding_model=embedding_model,
        )

        if not new_deps:
            stats["skipped_no_candidates"] += 1

        stats["llm_calls"] += 1

        # Add new dependencies (preserving existing intra-parent deps)
        for dep_id in new_deps:
            if dep_id not in task.dependencies:
                task.dependencies.append(dep_id)
                stats["dependencies_created"] += 1
                logger.info(f"Added cross-parent dependency: {task.name} → {dep_id}")

    elapsed_time = time.time() - start_time
    stats["total_time_seconds"] = round(elapsed_time, 2)

    logger.info(f"Cross-parent dependency wiring complete: {stats}")

    return stats
