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
                                    "items": {"type": "string"},
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

    # Add type-specific guidance
    if task_type == "test":
        prompt += """

**CRITICAL: This is a TESTING task. ALL subtasks MUST be testing-related:**

Break this TESTING task into 3-5 testing subtasks. Each subtask must focus on writing tests, NOT implementing features.

Valid testing subtask types:
- Write unit tests for specific components
- Create integration test scenarios
- Write end-to-end test cases
- Set up test fixtures and mock data
- Perform security/performance testing
- Create test documentation

INVALID subtask types (DO NOT create these):
- "Implement X" or "Build Y" or "Create Z" (these are implementation tasks)
- "Design X" (this is a design task)
- Any subtask that involves writing production code

"""
    elif task_type == "design":
        prompt += """

**CRITICAL: This is a DESIGN task. ALL subtasks MUST be design/planning-related:**

Break this DESIGN task into 3-5 design subtasks. Each subtask must focus on planning and documentation, NOT implementation.

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

**CRITICAL: This is an IMPLEMENTATION task. ALL subtasks MUST be implementation-related:**

Break this IMPLEMENTATION task into 3-5 implementation subtasks. Each subtask must focus on building features, NOT testing or design.

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

Break this task into 3-5 manageable subtasks that can be worked on independently or sequentially.  # noqa: E501

For each subtask, specify:
1. **name**: Clear, action-oriented name
2. **description**: Detailed description of what needs to be done
3. **estimated_hours**: Time estimate (0.5-3 hours per subtask)
4. **dependencies**: List of subtask indices that must complete first (use 0-based indexing)  # noqa: E501
5. **file_artifacts**: List of files this subtask will create/modify
6. **provides**: What interface/functionality this subtask provides for others
7. **requires**: What this subtask needs from dependencies

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
      "description": "Create unit tests for login, logout, and token validation functions",
      "estimated_hours": 2.0,
      "dependencies": [],
      "file_artifacts": ["tests/unit/test_auth.py"],
      "provides": "Unit test coverage for auth functions",
      "requires": "None"
    },
    {
      "name": "Create integration tests for auth API endpoints",
      "description": "Test POST /api/login and /api/logout endpoints with various scenarios",
      "estimated_hours": 2.5,
      "dependencies": [0],
      "file_artifacts": ["tests/integration/test_auth_endpoints.py"],
      "provides": "Integration tests for auth API",
      "requires": "Unit tests passing from subtask 1"
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
      "description": "Research OAuth2, JWT standards, and security best practices for authentication",
      "estimated_hours": 1.5,
      "dependencies": [],
      "file_artifacts": ["docs/research/auth_research.md"],
      "provides": "Research findings and recommendations",
      "requires": "None"
    },
    {
      "name": "Design authentication API specification",
      "description": "Define API endpoints, request/response formats, and error handling for auth system",
      "estimated_hours": 2.0,
      "dependencies": [0],
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
      "file_artifacts": ["src/models/user.py"],
      "provides": "User model with fields: id, email, password_hash",
      "requires": "None"
    },
    {
      "name": "Build login endpoint",
      "description": "Create POST /api/login endpoint that authenticates users",
      "estimated_hours": 2.5,
      "dependencies": [0],
      "file_artifacts": ["src/api/auth/login.py"],
      "provides": "POST /api/login returning {token, user}",
      "requires": "User model from subtask 1"
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
"""

    return prompt


def _get_decomposition_system_prompt(task_type: str = "implement") -> str:
    """Get system prompt for decomposition with type-specific constraints."""
    base_prompt = """You are an expert software architect specializing in task decomposition.

Your goal is to break complex tasks into manageable, well-defined subtasks that can be implemented by different agents.

Key principles:
1. **Clear Interfaces**: Each subtask must have clear inputs and outputs
2. **Minimal Dependencies**: Reduce coupling where possible
3. **Sequential When Needed**: Don't parallelize tightly coupled work
4. **File Ownership**: Each subtask should primarily work on its own files
5. **Consistent Patterns**: Use shared conventions to avoid integration issues
"""

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
CRITICAL: Respond ONLY with valid JSON. No markdown, no explanations, just the JSON object."""

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


def _adjust_subtask_dependencies(
    parent_task_id: str, decomposition: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Adjust subtask dependencies to use actual subtask IDs instead of indices.

    Parameters
    ----------
    parent_task_id : str
        ID of the parent task
    decomposition : Dict[str, Any]
        Decomposition with index-based dependencies

    Returns
    -------
    Dict[str, Any]
        Decomposition with ID-based dependencies
    """
    # Create mapping of index -> subtask_id
    index_to_id = {}
    for idx in range(len(decomposition["subtasks"])):
        index_to_id[idx] = f"{parent_task_id}_sub_{idx + 1}"

    # Update dependencies in each subtask
    for idx, subtask in enumerate(decomposition["subtasks"]):
        if "dependencies" in subtask and subtask["dependencies"]:
            subtask["dependencies"] = [
                index_to_id[dep_idx] for dep_idx in subtask["dependencies"]
            ]

    return decomposition
