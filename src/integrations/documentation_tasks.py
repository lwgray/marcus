"""
Documentation Task Generation for Marcus

Adds a final documentation task to projects that:
1. Reviews all logged decisions
2. Creates comprehensive PROJECT_SUCCESS.md
3. Verifies all instructions work
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from src.core.models import Priority, Task, TaskStatus

logger = logging.getLogger(__name__)


class DocumentationTaskGenerator:
    """Generates documentation tasks for projects"""

    @staticmethod
    def create_documentation_task(
        existing_tasks: List[Task], project_name: str = "Project"
    ) -> Optional[Task]:
        """
        Create a final documentation task that depends on all major implementation tasks

        Args:
            existing_tasks: List of all project tasks
            project_name: Name of the project

        Returns:
            Documentation task or None if no implementation tasks exist
        """
        # Find all implementation, testing, and deployment tasks using actual label format
        # Labels are generated with prefixes like "component:backend", "type:feature", etc.
        implementation_tasks = [
            t
            for t in existing_tasks
            if any(
                label in t.labels
                for label in [
                    "type:feature",  # Implementation tasks
                    "component:backend",
                    "component:frontend",
                    "component:api",
                    "component:database",
                    "component:authentication",
                    "component:ecommerce",
                ]
            )
            and t.priority in [Priority.HIGH, Priority.URGENT, Priority.MEDIUM]
        ]

        test_tasks = [
            t
            for t in existing_tasks
            if any(label in t.labels for label in ["type:testing"])
        ]

        deploy_tasks = [
            t
            for t in existing_tasks
            if any(
                label in t.labels
                for label in ["type:deployment", "component:deployment"]
            )
        ]

        # If no implementation tasks, don't add documentation
        if not implementation_tasks:
            logger.info("No implementation tasks found, skipping documentation task")
            return None

        # Documentation depends on all major tasks
        dependencies = (
            [t.id for t in implementation_tasks]
            + [t.id for t in test_tasks]
            + [t.id for t in deploy_tasks]
        )

        # Create the documentation task
        doc_task = Task(
            id=f"doc_final_{uuid.uuid4().hex[:8]}",
            name=f"Create {project_name} PROJECT_SUCCESS documentation",
            description=DocumentationTaskGenerator._generate_documentation_description(
                has_tests=bool(test_tasks), has_deployment=bool(deploy_tasks)
            ),
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["documentation", "final", "verification"],
            dependencies=dependencies,
            estimated_hours=4.0,  # Adjust based on project size
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        # Add acceptance criteria
        doc_task.acceptance_criteria = [
            "PROJECT_SUCCESS.md file created in project root",
            "All setup instructions tested and working",
            "Test commands verified and coverage documented",
            "Architecture clearly explained with key decisions",
            "All logged decisions incorporated into relevant sections",
        ]

        # Add subtasks
        doc_task.subtasks = [
            "Review all logged decisions from project history",
            "Document system architecture and data flow",
            "Test and document setup/installation process",
            "Verify and document how to run the application",
            "Test and document testing procedures",
            "Document deployment process (if applicable)",
            "Ensure all commands in documentation actually work",
        ]

        return doc_task

    @staticmethod
    def _generate_documentation_description(
        has_tests: bool = True, has_deployment: bool = False
    ) -> str:
        """Generate detailed description for documentation task"""

        base_description = """Create comprehensive PROJECT_SUCCESS.md documentation by:

1. **Gather Information**:
   - Review all logged decisions using `get_task_context` for each completed task
   - Examine the final codebase structure
   - Identify key architectural decisions and implementation details

2. **Document Core Sections**:
   - **How It Works**: System architecture, component interactions, data flow
   - **How to Run It**: Prerequisites, setup steps, configuration, startup commands
   - **How to Test It**: Test commands, expected output, coverage reports
"""

        if has_deployment:
            base_description += """   - **How to Deploy It**: Production setup, environment variables, deployment steps

"""

        base_description += """3. **Verify Everything**:
   - Test each command in the documentation
   - Ensure setup steps work from a clean environment
   - Verify the application runs as documented
   - Confirm tests pass as described

4. **Format for Success Measurement**:
   - Use clear markdown formatting
   - Include specific commands and expected outputs
   - Document any prerequisites or dependencies
   - Include troubleshooting for common issues

The documentation should be written so someone unfamiliar with the project can successfully set up, run, and test the application by following the instructions."""

        return base_description

    @staticmethod
    def should_add_documentation_task(
        project_description: str, task_count: int
    ) -> bool:
        """
        Determine if a documentation task should be added

        Args:
            project_description: Natural language description
            task_count: Number of tasks in project

        Returns:
            True if documentation should be added
        """
        # Skip for tiny projects
        if task_count < 3:
            return False

        # Skip for prototypes/experiments
        skip_keywords = [
            "prototype",
            "poc",
            "proof of concept",
            "demo",
            "experiment",
            "test",
        ]
        description_lower = project_description.lower()

        if any(keyword in description_lower for keyword in skip_keywords):
            return False

        return True


def enhance_project_with_documentation(
    tasks: List[Task], project_description: str, project_name: str = "Project"
) -> List[Task]:
    """
    Add documentation task to project if appropriate

    Args:
        tasks: Original project tasks
        project_description: Project description
        project_name: Name of the project

    Returns:
        Task list with documentation task added if appropriate
    """
    generator = DocumentationTaskGenerator()

    # Check if we should add documentation
    if not generator.should_add_documentation_task(project_description, len(tasks)):
        logger.info("Skipping documentation task for this project")
        return tasks

    # Create documentation task
    doc_task = generator.create_documentation_task(tasks, project_name)

    if doc_task:
        logger.info(f"Added documentation task: {doc_task.name}")
        return tasks + [doc_task]

    return tasks


# Template for PROJECT_SUCCESS.md
PROJECT_SUCCESS_TEMPLATE = """# PROJECT_SUCCESS.md

## Project: {project_name}

### How It Works

**Architecture Overview:**
{architecture_description}

**Key Components:**
{component_list}

**Data Flow:**
{data_flow_description}

**Key Technical Decisions:**
{decisions_summary}

### How to Run It

**Prerequisites:**
{prerequisites}

**Setup Steps:**
```bash
{setup_commands}
```

**Configuration:**
{config_instructions}

**Starting the Application:**
```bash
{run_commands}
```

**Verify It's Working:**
{verification_steps}

### How to Test It

**Running Tests:**
```bash
{test_commands}
```

**Expected Output:**
```
{expected_test_output}
```

**Test Coverage:**
{coverage_info}

### How to Deploy It

**Build for Production:**
```bash
{build_commands}
```

**Deployment Steps:**
{deployment_steps}

**Environment Variables:**
{env_vars}

**Health Check:**
{health_check_info}

### Troubleshooting

**Common Issues:**
{common_issues}

### Implementation Notes

**Logged Decisions:**
{all_logged_decisions}

---
*Documentation generated on {timestamp}*
"""
