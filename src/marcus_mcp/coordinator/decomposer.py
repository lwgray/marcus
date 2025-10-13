"""
Task Decomposer for Marcus.

This module handles intelligent task decomposition using AI,
breaking complex tasks into manageable subtasks with clear interfaces.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from src.core.models import Task

logger = logging.getLogger(__name__)


def should_decompose(task: Task) -> bool:
    """
    Decide whether a task should be decomposed into subtasks.

    Uses heuristics to determine if decomposition would be beneficial:
    - Task size (estimated hours)
    - Task complexity (description length, multiple components)
    - Task type (not bugfix, not deployment)

    Parameters
    ----------
    task : Task
        The task to evaluate

    Returns
    -------
    bool
        True if task should be decomposed
    """
    # Don't decompose small tasks
    if task.estimated_hours < 3.0:
        logger.debug(
            f"Task {task.name} too small ({task.estimated_hours}h) - no decomposition"
        )
        return False

    # Don't decompose certain task types
    labels_lower = [label.lower() for label in (task.labels or [])]
    skip_labels = ["bugfix", "hotfix", "refactor", "documentation"]
    if any(skip_label in labels_lower for skip_label in skip_labels):
        logger.debug(f"Task {task.name} type ({task.labels}) - no decomposition")
        return False

    # Don't decompose deployment tasks
    deployment_keywords = ["deploy", "release", "production", "launch", "rollout"]
    task_name_lower = task.name.lower()
    if any(keyword in task_name_lower for keyword in deployment_keywords):
        logger.debug(f"Task {task.name} is deployment - no decomposition")
        return False

    # Decompose if estimated time is long
    if task.estimated_hours >= 4.0:
        logger.info(
            f"Task {task.name} large ({task.estimated_hours}h) - will decompose"
        )
        return True

    # Decompose if description suggests multiple components
    description_lower = task.description.lower()
    multi_component_indicators = [
        " and ",
        "then",
        "including",
        "as well as",
        "plus",
        "endpoint",
        "api",
        "database",
        "model",
        "ui",
        "frontend",
        "backend",
    ]

    indicator_count = sum(
        1 for indicator in multi_component_indicators if indicator in description_lower
    )

    if indicator_count >= 3:
        logger.info(
            f"Task {task.name} has multiple components ({indicator_count} indicators) "
            "- will decompose"
        )
        return True

    logger.debug(f"Task {task.name} - no decomposition needed")
    return False


async def decompose_task(
    task: Task, ai_engine: Any, project_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Decompose a task into subtasks using AI.

    Creates a structured breakdown with:
    - Sequential or independent subtasks
    - Clear dependencies
    - File artifacts and interfaces
    - Shared conventions
    - Final integration subtask

    Parameters
    ----------
    task : Task
        The task to decompose
    ai_engine : Any
        AI engine for generating decomposition
    project_context : Optional[Dict[str, Any]]
        Additional project context for better decomposition

    Returns
    -------
    Dict[str, Any]
        Decomposition result with:
        - subtasks: List of subtask definitions
        - shared_conventions: Shared file structure and patterns
        - success: bool indicating if decomposition succeeded
    """
    try:
        # Build decomposition prompt
        prompt = _build_decomposition_prompt(task, project_context)

        # Extract task type for system prompt
        task_type = task.name.split()[0].lower() if task.name else "implement"

        # Call AI to generate decomposition
        response = await ai_engine.generate_structured_response(
            prompt=prompt,
            system_prompt=_get_decomposition_system_prompt(task_type),
            response_format={
                "type": "object",
                "properties": {
                    "subtasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "estimated_hours": {"type": "number"},
                                "dependencies": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                },
                                "dependency_types": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                        "enum": ["hard", "soft"],
                                    },
                                    "description": (
                                        "Type for each dependency: 'hard' "
                                        "(blocks start) or 'soft' "
                                        "(can use mock/contract)"
                                    ),
                                },
                                "file_artifacts": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "provides": {"type": "string"},
                                "requires": {"type": "string"},
                            },
                            "required": [
                                "name",
                                "description",
                                "estimated_hours",
                                "dependency_types",
                            ],
                        },
                    },
                    "shared_conventions": {
                        "type": "object",
                        "properties": {
                            "base_path": {"type": "string"},
                            "file_structure": {"type": "string"},
                            "response_format": {"type": "object"},
                            "naming_conventions": {"type": "object"},
                        },
                    },
                },
                "required": ["subtasks", "shared_conventions"],
            },
        )

        # Parse response
        if isinstance(response, str):
            decomposition = json.loads(response)
        else:
            decomposition = response

        # DEBUG: Log what AI returned BEFORE fixing
        logger.info(f"AI returned decomposition for {task.name}:")
        for idx, st in enumerate(decomposition.get("subtasks", [])):
            deps = st.get("dependencies", [])
            dep_types = [type(d).__name__ for d in deps]
            logger.info(f"  Subtask {idx}: deps={deps} (types: {dep_types})")

        # Add final integration subtask automatically
        integration_subtask = _create_integration_subtask(
            task, decomposition.get("subtasks", [])
        )
        decomposition["subtasks"].append(integration_subtask)

        # Validate decomposition
        if not _validate_decomposition(decomposition):
            logger.error(f"Invalid decomposition for task {task.name}")
            return {
                "success": False,
                "error": "Invalid decomposition structure",
            }

        # Adjust subtask dependencies to use subtask IDs
        decomposition = _adjust_subtask_dependencies(task.id, decomposition)

        # Analyze parallelism potential
        parallelism_analysis = _analyze_parallelism(decomposition)
        decomposition["parallelism_analysis"] = parallelism_analysis

        # DEBUG: Log what dependencies look like AFTER fixing
        logger.info(f"After adjustment for {task.name}:")
        for idx, st in enumerate(decomposition.get("subtasks", [])):
            deps = st.get("dependencies", [])
            dep_types = [type(d).__name__ for d in deps]
            logger.info(f"  Subtask {idx}: deps={deps} (types: {dep_types})")

        # Log parallelism metrics
        logger.info(f"Parallelism analysis for {task.name}:")
        logger.info(
            f"  Parallelizable: {parallelism_analysis['parallelizable_percentage']}%"
        )
        logger.info(
            f"  Max parallel workers: {parallelism_analysis['max_parallel_workers']}"
        )
        logger.info(f"  Chain depth: {parallelism_analysis['dependency_chain_depth']}")
        logger.info(
            f"  Soft deps: {parallelism_analysis['soft_dependency_count']}, "
            f"Hard deps: {parallelism_analysis['hard_dependency_count']}"
        )
        logger.info(
            f"  Parallelism score: {parallelism_analysis['parallelism_score']}/100"
        )

        logger.info(
            f"Successfully decomposed task {task.name} into "
            f"{len(decomposition['subtasks'])} subtasks"
        )

        return {"success": True, **decomposition}

    except Exception as e:
        logger.error(f"Error decomposing task {task.name}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def _build_decomposition_prompt(
    task: Task, project_context: Optional[Dict[str, Any]]
) -> str:
    """Build the AI prompt for task decomposition."""
    # Extract task type from task name (first word: Design/Implement/Test)
    task_type = task.name.split()[0].lower() if task.name else "implement"

    prompt = f"""Decompose the following task into subtasks:

**Task Name:** {task.name}

**Task Type:** {task_type.upper()}

**Description:** {task.description}

**Estimated Hours:** {task.estimated_hours}

**Labels:** {', '.join(task.labels or [])}

**Priority:** {task.priority.value}
"""

    if project_context:
        prompt += f"\n\n**Project Context:**\n{json.dumps(project_context, indent=2)}\n"

    # Add parallelization strategy guidance
    prompt += """

**PARALLELIZATION STRATEGY:**

When breaking down this task, follow these principles to maximize parallelism:

1. **Interface-First Approach**: Use Design specifications as contracts
   - Subtasks should depend on DESIGN SPECIFICATIONS, not each other
   - If Design phase produced API specs/schemas, use those contracts directly
   - Example: Multiple API endpoints can be built in parallel using the same API spec

2. **Minimize Hard Dependencies**: Create independent subtasks where possible
   - Hard dependency = Must complete before work can start
   - Soft dependency = Can start using mock/contract, integrate later
   - Aim for 70%+ of subtasks having 0-1 dependencies

3. **Component Boundaries**: Separate concerns cleanly
   - Database models vs API logic vs UI components
   - Each subtask focuses on one component with clear interface
   - Integration happens in final subtask

4. **Shared Conventions**: Define upfront to avoid integration issues
   - Standard response formats, error handling patterns
   - Naming conventions, file structure
   - This enables parallel work without conflicts

**TARGET**: Break task so that 70%+ subtasks can run in parallel
"""

    # Add type-specific guidance
    if task_type == "test":
        prompt += """

**CRITICAL: This is a TESTING task. ALL subtasks MUST be testing-related:**

Break this TESTING task into 3-5 testing subtasks. Each subtask must focus
on writing tests, NOT implementing features.

**PARALLELIZATION FOCUS FOR TESTING:**
- Test suites can often run in parallel (unit, integration, e2e)
- Break by test type or component being tested
- Most test subtasks should be independent (0 dependencies)
- Example: Unit tests for Model A, Model B, API endpoints can all be
  written in parallel
- Only sequential when tests build on each other (unit → integration → e2e)

Valid testing subtask types:
- Write unit tests for specific components
- Create integration test scenarios
- Write end-to-end test cases
- Set up test fixtures and mock data
- Perform security/performance testing
- Create test documentation

INVALID subtask types (DO NOT create these):
- "Implement X" or "Build Y" or "Create Z" (implementation tasks)
- "Design X" (this is a design task)
- Any subtask that involves writing production code

"""
    elif task_type == "design":
        prompt += """

**CRITICAL: This is a DESIGN task. ALL subtasks MUST be
design/planning-related:**

Break this DESIGN task into 3-5 design subtasks. Each subtask must focus
on planning and documentation, NOT implementation.

Valid design subtask types:
- Research existing solutions and best practices
- Create wireframes, mockups, or diagrams
- Define API specifications and contracts
- Design data models and schemas
- Document architectural decisions
- Create design system components

INVALID subtask types (DO NOT create these):
- "Implement X" or "Build Y" (these are implementation tasks)
- "Test X" (this is a testing task)
- Any subtask that involves writing production code

"""
    elif task_type == "implement":
        prompt += """

**CRITICAL: This is an IMPLEMENTATION task. ALL subtasks MUST be
implementation-related:**

Break this IMPLEMENTATION task into 3-5 implementation subtasks. Each
subtask must focus on building features, NOT testing or design.

**PARALLELIZATION FOCUS FOR IMPLEMENTATION:**
- Use Design specifications as contracts - don't wait for other subtasks
- Break by component boundaries (models, API, business logic, UI)
- Each subtask should be independently implementable using Design specs
- Example: All API endpoints can be built in parallel if they follow
  the same API specification from Design phase
- Minimize sequential dependencies - most subtasks should have 0-1 deps

Valid implementation subtask types:
- Create/implement data models or database schemas
- Build API endpoints or services
- Implement business logic
- Create UI components
- Integrate with external services
- Add validation and error handling

INVALID subtask types (DO NOT create these):
- "Test X" or "Write tests for Y" (these are testing tasks)
- "Design X" (this is a design task)
- Any subtask focused purely on testing or planning

"""
    else:
        prompt += """

Break this task into 3-5 manageable subtasks that can be worked on
independently or sequentially.

For each subtask, specify:
1. **name**: Clear, action-oriented name
2. **description**: Detailed description of what needs to be done
3. **estimated_hours**: Time estimate (0.5-3 hours per subtask)
4. **dependencies**: List of subtask indices that must complete first
   (use 0-based indexing)
5. **dependency_types**: REQUIRED - For each dependency, specify type:
   - "hard": Must wait for subtask to complete before starting (blocks execution)
   - "soft": Can start using Design specs as contract, integrate at final step
   MUST have same length as dependencies array. Empty array if no dependencies.
   Prefer "soft" when Design phase provided clear specifications/contracts.
6. **file_artifacts**: List of files this subtask will create/modify
7. **provides**: What interface/functionality this subtask provides for others
8. **requires**: What this subtask needs from dependencies

Also define **shared_conventions** that all subtasks must follow:
- **base_path**: Base directory for file outputs
- **file_structure**: Directory structure pattern
- **response_format**: Standard API response format (if applicable)
- **naming_conventions**: File and function naming patterns

**Guidelines:**
- Prefer sequential subtasks for tightly coupled work (backend → API → frontend)
- Use independent subtasks only if truly parallelizable
- Keep each subtask focused on one component/file
- Ensure clear interfaces between subtasks
- DO NOT create more than 5 subtasks (excluding final integration)
- Each subtask should be testable independently
"""

    # Add type-specific example
    if task_type == "test":
        prompt += """
**Example for TESTING task:**
```json
{
  "subtasks": [
    {
      "name": "Write unit tests for authentication logic",
      "description": "Create unit tests for login, logout, and token validation",
      "estimated_hours": 2.0,
      "dependencies": [],
      "dependency_types": [],
      "file_artifacts": ["tests/unit/test_auth.py"],
      "provides": "Unit test coverage for auth functions",
      "requires": "None"
    },
    {
      "name": "Create integration tests for auth API endpoints",
      "description": "Test POST /api/login and /api/logout with various scenarios",
      "estimated_hours": 2.5,
      "dependencies": [0],
      "dependency_types": ["soft"],
      "file_artifacts": ["tests/integration/test_auth_endpoints.py"],
      "provides": "Integration tests for auth API",
      "requires": "Unit test patterns from subtask 1"
    }
  ],
  "shared_conventions": {
    "base_path": "tests/",
    "file_structure": "tests/{test_type}/test_{feature}.py",
    "test_framework": "pytest",
    "naming_conventions": {
      "files": "test_*.py",
      "classes": "Test*",
      "functions": "test_*"
    }
  }
}
```
"""
    elif task_type == "design":
        prompt += """
**Example for DESIGN task:**
```json
{
  "subtasks": [
    {
      "name": "Research authentication best practices",
      "description": "Research OAuth2, JWT, and security best practices for auth",
      "estimated_hours": 1.5,
      "dependencies": [],
      "dependency_types": [],
      "file_artifacts": ["docs/research/auth_research.md"],
      "provides": "Research findings and recommendations",
      "requires": "None"
    },
    {
      "name": "Design authentication API specification",
      "description": "Define API endpoints, request/response, and error handling",
      "estimated_hours": 2.0,
      "dependencies": [0],
      "dependency_types": ["hard"],
      "file_artifacts": ["docs/design/auth_api_spec.md"],
      "provides": "Complete API specification with examples",
      "requires": "Research findings from subtask 1"
    }
  ],
  "shared_conventions": {
    "base_path": "docs/design/",
    "file_structure": "docs/{type}/{feature}.md",
    "documentation_format": "Markdown with diagrams",
    "naming_conventions": {
      "files": "snake_case.md",
      "sections": "Title Case Headers"
    }
  }
}
```
"""
    else:  # implement
        prompt += """
**Example for IMPLEMENTATION task:**
```json
{
  "subtasks": [
    {
      "name": "Create User model",
      "description": "Define User model in src/models/user.py with email validation",
      "estimated_hours": 2.0,
      "dependencies": [],
      "dependency_types": [],
      "file_artifacts": ["src/models/user.py"],
      "provides": "User model with fields: id, email, password_hash",
      "requires": "None"
    },
    {
      "name": "Build login endpoint",
      "description": "Create POST /api/login endpoint that authenticates users",
      "estimated_hours": 2.5,
      "dependencies": [0],
      "dependency_types": ["soft"],
      "file_artifacts": ["src/api/auth/login.py"],
      "provides": "POST /api/login returning {token, user}",
      "requires": "User model schema from Design phase"
    },
    {
      "name": "Build registration endpoint",
      "description": "Create POST /api/register endpoint for new users",
      "estimated_hours": 2.5,
      "dependencies": [0],
      "dependency_types": ["soft"],
      "file_artifacts": ["src/api/auth/register.py"],
      "provides": "POST /api/register returning {token, user}",
      "requires": "User model schema from Design phase"
    }
  ],
  "shared_conventions": {
    "base_path": "src/api/",
    "file_structure": "src/{component}/{feature}.py",
    "response_format": {
      "success": {"status": "success", "data": "..."},
      "error": {"status": "error", "message": "..."}
    },
    "naming_conventions": {
      "files": "snake_case",
      "classes": "PascalCase",
      "functions": "snake_case"
    }
  }
}
```
NOTE: Subtasks 1 and 2 both have "soft" dependencies on subtask 0, meaning they
can start in parallel using the Design phase's data model specification.
"""

    return prompt


def _get_decomposition_system_prompt(task_type: str = "implement") -> str:
    """Get system prompt for decomposition with type-specific constraints."""
    base_prompt = """You are an expert software architect specializing in
task decomposition and parallel work optimization.

Your goal is to break complex tasks into manageable, well-defined
subtasks that can be implemented by different agents IN PARALLEL.

Key principles:
1. **Maximize Parallelism**: Target 70%+ subtasks with 0-1 dependencies
2. **Clear Interfaces**: Each subtask must have clear inputs and outputs
3. **Interface-First**: Subtasks depend on Design specs, not each other
4. **Minimal Hard Dependencies**: Use contracts/mocks to enable parallel work
5. **File Ownership**: Each subtask should primarily work on its own files
6. **Consistent Patterns**: Use shared conventions to avoid integration issues

CRITICAL: Always prefer independent subtasks over sequential chains.
Break work by component boundaries (models/API/UI), not by sequence."""

    # Add type-specific constraints
    if task_type == "test":
        base_prompt += """
**CRITICAL CONSTRAINTS FOR TESTING TASKS:**
- ALL subtasks MUST be testing-related (writing tests, creating test data, etc.)
- NEVER create implementation subtasks (no "Implement X", "Build Y", "Create Z")
- NEVER create design subtasks (no "Design X", "Plan Y")
- Focus on: unit tests, integration tests, test fixtures, test documentation
- Each subtask should test a specific component or scenario
"""
    elif task_type == "design":
        base_prompt += """
**CRITICAL CONSTRAINTS FOR DESIGN TASKS:**
- ALL subtasks MUST be design/planning-related (research, documentation, specifications)
- NEVER create implementation subtasks (no "Implement X", "Build Y")
- NEVER create testing subtasks (no "Test X", "Write tests for Y")
- Focus on: research, wireframes, API specs, data models, architectural decisions
- Each subtask should produce documentation or design artifacts
"""
    elif task_type == "implement":
        base_prompt += """
**CRITICAL CONSTRAINTS FOR IMPLEMENTATION TASKS:**
- ALL subtasks MUST be implementation-related (building features, writing code)
- NEVER create testing subtasks (no "Test X", "Write tests for Y")
- NEVER create design subtasks (no "Design X", "Plan Y")
- Focus on: building features, creating models, implementing APIs, adding logic
- Each subtask should produce working code
"""

    base_prompt += """
CRITICAL: Respond ONLY with valid JSON. No markdown, no explanations,
just the JSON object."""

    return base_prompt


def _create_integration_subtask(
    task: Task, subtasks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Create a final integration subtask automatically.

    This subtask:
    - Integrates all components
    - Creates consolidated documentation
    - Runs integration tests
    - Validates all file outputs

    Parameters
    ----------
    task : Task
        The parent task
    subtasks : List[Dict[str, Any]]
        Previously created subtasks

    Returns
    -------
    Dict[str, Any]
        Final integration subtask definition
    """
    # Collect all file artifacts from previous subtasks
    all_artifacts = []
    for subtask in subtasks:
        all_artifacts.extend(subtask.get("file_artifacts", []))

    # Dependencies: all previous subtasks
    all_deps = list(range(len(subtasks)))
    # All dependencies for integration are hard (must complete before integration)
    all_dep_types = ["hard"] * len(all_deps)
    component_list = ", ".join([s["name"] for s in subtasks])

    integration_subtask = {
        "name": f"Integrate and validate {task.name}",
        "description": (
            f"Final integration step for {task.name}:\n"
            "1. Verify all components work together\n"
            "2. Run integration tests across all files\n"
            "3. Create consolidated documentation\n"
            "4. Validate all interfaces and file outputs\n"
            f"5. Ensure project meets original requirements"
        ),
        # 20% of total, capped at 1.5 hours
        "estimated_hours": min(1.5, task.estimated_hours * 0.2),
        "dependencies": all_deps,
        "dependency_types": all_dep_types,
        "file_artifacts": [
            "docs/integration_report.md",
            "tests/integration/test_integration.py",
        ],
        "provides": "Fully integrated and validated solution",
        "requires": f"All components: {component_list}",
    }

    return integration_subtask


def _validate_decomposition(decomposition: Dict[str, Any]) -> bool:
    """
    Validate decomposition structure.

    Checks:
    - Has subtasks
    - Each subtask has required fields
    - Dependencies are valid
    - Shared conventions exist

    Parameters
    ----------
    decomposition : Dict[str, Any]
        Decomposition to validate

    Returns
    -------
    bool
        True if valid
    """
    if "subtasks" not in decomposition or not decomposition["subtasks"]:
        logger.error("Decomposition missing subtasks")
        return False

    if "shared_conventions" not in decomposition:
        logger.warning("Decomposition missing shared_conventions")

    # Validate each subtask
    for idx, subtask in enumerate(decomposition["subtasks"]):
        required_fields = ["name", "description", "estimated_hours"]
        for field in required_fields:
            if field not in subtask:
                logger.error(f"Subtask {idx} missing required field: {field}")
                return False

        # Validate dependencies
        if "dependencies" in subtask:
            for dep_idx in subtask["dependencies"]:
                if not isinstance(dep_idx, int) or dep_idx >= idx:
                    logger.error(
                        f"Subtask {idx} has invalid dependency: {dep_idx} "
                        "(must be earlier subtask index)"
                    )
                    return False

    return True


def _analyze_parallelism(decomposition: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze parallelism potential of the decomposition.

    Calculates metrics about how parallelizable the subtasks are based on
    their dependencies and dependency types.

    Parameters
    ----------
    decomposition : Dict[str, Any]
        Decomposition with subtasks and dependencies

    Returns
    -------
    Dict[str, Any]
        Parallelism analysis with metrics:
        - parallelizable_percentage: % of subtasks with 0-1 dependencies
        - max_parallel_workers: Max subtasks that can run simultaneously
        - dependency_chain_depth: Longest sequential chain
        - soft_dependency_count: Number of soft dependencies
        - hard_dependency_count: Number of hard dependencies
        - parallelism_score: Overall score (0-100)
    """
    subtasks = decomposition.get("subtasks", [])
    if not subtasks:
        return {
            "parallelizable_percentage": 0.0,
            "max_parallel_workers": 0,
            "dependency_chain_depth": 0,
            "soft_dependency_count": 0,
            "hard_dependency_count": 0,
            "parallelism_score": 0.0,
        }

    # Count subtasks by dependency count
    zero_deps = sum(1 for st in subtasks if len(st.get("dependencies", [])) == 0)
    one_dep = sum(1 for st in subtasks if len(st.get("dependencies", [])) == 1)
    parallelizable = zero_deps + one_dep
    parallelizable_percentage = (parallelizable / len(subtasks)) * 100

    # Count dependency types
    soft_count = 0
    hard_count = 0
    for subtask in subtasks:
        dep_types = subtask.get("dependency_types", [])
        soft_count += sum(1 for dt in dep_types if dt == "soft")
        hard_count += sum(1 for dt in dep_types if dt == "hard")

    # Calculate max parallel workers (subtasks at each level)
    # Level 0: tasks with no dependencies
    # Level 1: tasks with only level 0 dependencies
    # etc.
    levels = _calculate_dependency_levels(subtasks)
    max_parallel = max((len(tasks) for tasks in levels.values()), default=0)

    # Calculate dependency chain depth (longest path)
    chain_depth = len(levels)

    # Calculate parallelism score (0-100)
    # Factors:
    # - 40% weight: parallelizable percentage (70%+ target)
    # - 30% weight: max parallel workers (higher is better)
    # - 20% weight: short chains (fewer levels is better)
    # - 10% weight: soft vs hard ratio (more soft is better)

    parallelizable_score = min(parallelizable_percentage / 70.0, 1.0) * 40
    parallel_worker_score = min(max_parallel / max(len(subtasks) * 0.5, 1), 1.0) * 30
    chain_score = (1 - min(chain_depth / max(len(subtasks), 1), 1.0)) * 20

    total_deps = soft_count + hard_count
    soft_ratio = soft_count / total_deps if total_deps > 0 else 0.5
    soft_score = soft_ratio * 10

    parallelism_score = (
        parallelizable_score + parallel_worker_score + chain_score + soft_score
    )

    return {
        "parallelizable_percentage": round(parallelizable_percentage, 1),
        "max_parallel_workers": max_parallel,
        "dependency_chain_depth": chain_depth,
        "soft_dependency_count": soft_count,
        "hard_dependency_count": hard_count,
        "parallelism_score": round(parallelism_score, 1),
    }


def _calculate_dependency_levels(
    subtasks: List[Dict[str, Any]],
) -> Dict[int, List[int]]:
    """
    Calculate dependency levels for subtasks.

    Level 0: No dependencies
    Level N: Depends only on tasks at level < N

    Parameters
    ----------
    subtasks : List[Dict[str, Any]]
        List of subtasks with dependencies

    Returns
    -------
    Dict[int, List[int]]
        Mapping of level -> list of subtask indices at that level
    """
    levels: Dict[int, List[int]] = {}
    task_levels: Dict[int, int] = {}

    # Iteratively assign levels
    max_iterations = len(subtasks)
    iteration = 0

    while len(task_levels) < len(subtasks) and iteration < max_iterations:
        iteration += 1

        for idx, subtask in enumerate(subtasks):
            if idx in task_levels:
                continue  # Already assigned

            deps = subtask.get("dependencies", [])

            if not deps:
                # No dependencies -> level 0
                task_levels[idx] = 0
                if 0 not in levels:
                    levels[0] = []
                levels[0].append(idx)
            else:
                # Check if all dependencies have been assigned levels
                dep_indices = []
                # Dependencies might be indices (int) during processing
                for dep in deps:
                    if isinstance(dep, int):
                        dep_indices.append(dep)

                if dep_indices and all(
                    dep_idx in task_levels for dep_idx in dep_indices
                ):
                    # All deps assigned -> this task's level is max(dep_levels) + 1
                    max_dep_level = max(task_levels[dep_idx] for dep_idx in dep_indices)
                    level = max_dep_level + 1
                    task_levels[idx] = level
                    if level not in levels:
                        levels[level] = []
                    levels[level].append(idx)

    return levels


def _adjust_subtask_dependencies(
    parent_task_id: str, decomposition: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Adjust subtask dependencies to use actual subtask IDs instead of indices.

    Converts integer dependency indices (0-based) to actual subtask IDs
    in format: {parent_task_id}_sub_{index+1}

    Parameters
    ----------
    parent_task_id : str
        ID of the parent task
    decomposition : Dict[str, Any]
        Decomposition with index-based dependencies

    Returns
    -------
    Dict[str, Any]
        Decomposition with actual subtask ID-based dependencies
    """
    subtasks = decomposition["subtasks"]

    # Create mapping of index -> actual subtask_id
    index_to_id = {
        idx: f"{parent_task_id}_sub_{idx + 1}" for idx in range(len(subtasks))
    }

    # Update dependencies in each subtask
    for idx, subtask in enumerate(subtasks):
        if "dependencies" in subtask and subtask["dependencies"]:
            new_deps = []
            for dep_idx in subtask["dependencies"]:
                if not isinstance(dep_idx, int):
                    logger.error(
                        f"Subtask {idx} has non-integer dependency: {dep_idx} "
                        f"(type: {type(dep_idx)}). Schema should enforce integer type."
                    )
                    continue

                if 0 <= dep_idx < len(subtasks):
                    new_deps.append(index_to_id[dep_idx])
                else:
                    logger.warning(
                        f"Subtask {idx} has invalid dependency index {dep_idx} "
                        f"(valid range: 0-{len(subtasks)-1})"
                    )

            subtask["dependencies"] = new_deps

    return decomposition
