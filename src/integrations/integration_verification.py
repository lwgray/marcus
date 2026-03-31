"""
Integration Verification Task Generation for Marcus.

Adds a verification task to projects that runs after implementation
completes. The integration agent inspects the project, figures out
how to build and start it, and reports whether the product actually
works end-to-end.

Phase 1: Visibility only — the task always completes (DONE) and
reports pass/fail as an artifact. It does not block the experiment.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from src.core.models import Priority, Task, TaskStatus

logger = logging.getLogger(__name__)


class IntegrationTaskGenerator:
    """Generate integration verification tasks for projects.

    Creates a task that runs after all implementation and testing tasks
    complete. The assigned agent inspects the project structure, figures
    out how to build/start it (regardless of language or framework),
    and reports whether the product actually works.

    Parameters
    ----------
    None

    Examples
    --------
    >>> generator = IntegrationTaskGenerator()
    >>> task = generator.create_integration_task(existing_tasks, "Dashboard")
    >>> if task:
    ...     tasks.append(task)
    """

    @staticmethod
    def create_integration_task(
        existing_tasks: List[Task],
        project_name: str = "Project",
    ) -> Optional[Task]:
        """
        Create an integration verification task.

        Depends on all non-documentation, non-integration tasks.
        Returns None if no implementation tasks exist.

        Parameters
        ----------
        existing_tasks : List[Task]
            List of all project tasks created so far.
        project_name : str
            Name of the project.

        Returns
        -------
        Optional[Task]
            Integration verification task, or None if no
            implementation tasks exist.
        """
        # Check for implementation tasks
        implementation_tasks = [
            t
            for t in existing_tasks
            if any(
                label in t.labels
                for label in [
                    "type:feature",
                    "component:backend",
                    "component:frontend",
                    "component:api",
                    "component:database",
                    "component:authentication",
                    "component:ecommerce",
                ]
            )
        ]

        if not implementation_tasks:
            logger.info(
                "No implementation tasks found, " "skipping integration verification"
            )
            return None

        # Depend on ALL non-documentation, non-integration tasks
        dependencies = [
            t.id
            for t in existing_tasks
            if "documentation" not in t.labels and "type:integration" not in t.labels
        ]

        logger.info(
            f"Integration verification task will depend on "
            f"{len(dependencies)} tasks"
        )

        description = IntegrationTaskGenerator._generate_integration_description(
            project_name
        )

        acceptance_criteria = [
            "Project dependencies installed successfully",
            "Project builds without errors",
            "Application starts and responds to requests",
            "Key endpoints/pages return expected content " "(not error HTML or 404)",
            "No missing components detected " "(all referenced APIs/modules exist)",
            "Results logged as integration_verification.json artifact",
        ]

        task = Task(
            id=f"integration_verify_{uuid.uuid4().hex[:8]}",
            name=(f"Integration verification for {project_name}"),
            description=description,
            status=TaskStatus.TODO,
            priority=Priority.URGENT,
            labels=["integration", "verification", "type:integration"],
            dependencies=dependencies,
            estimated_hours=1.0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            assigned_to=None,
            due_date=None,
            acceptance_criteria=acceptance_criteria,
        )

        return task

    @staticmethod
    def should_add_integration_task(
        project_description: str,
    ) -> bool:
        """
        Determine if an integration task should be added.

        Skips for prototypes, demos, experiments, and POCs.

        Parameters
        ----------
        project_description : str
            Natural language project description.

        Returns
        -------
        bool
            True if integration verification should be added.
        """
        skip_keywords = [
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

    @staticmethod
    def _generate_integration_description(
        project_name: str,
    ) -> str:
        """
        Generate the integration task description.

        The description instructs the agent to inspect the project
        and figure out how to verify it works, regardless of the
        language, framework, or project type.

        Parameters
        ----------
        project_name : str
            Name of the project.

        Returns
        -------
        str
            Detailed task description with verification steps.
        """
        return f"""Verify that {project_name} actually builds, starts, \
and works end-to-end.

**IMPORTANT**: This is a verification task, not an implementation task. \
Your job is to check whether the product works as built. Always mark \
this task as DONE when finished — report failures in the artifact, \
do NOT block the experiment.

1. **Read Context**:
   - Review design documents and architecture decisions
   - Check README.md for documented build/start commands
   - Use `get_task_context` for completed implementation tasks
   - Understand what the project is supposed to do

2. **Inspect the Project**:
   - Look at the project structure and files
   - Identify the language(s), framework(s), and build system
   - Find configuration files (package.json, pyproject.toml,
     Makefile, Dockerfile, Cargo.toml, go.mod, index.html, etc.)
   - Determine the appropriate build, install, and start commands

3. **Install Dependencies**:
   - Run the appropriate install command for the project
   - Log the exit code and any errors

4. **Build the Project**:
   - Run the appropriate build command
   - If no build step is needed (e.g., static HTML), skip this
   - Log the exit code and any errors

5. **Start the Application**:
   - Run the appropriate start command
   - Wait for the application to be ready
   - If the app is a static site, serve it with a simple server

6. **Verify the Application Works**:
   - Hit the main page/endpoint and check for a real response
   - Check that key features described in the design actually work
   - Look for error states (API calls returning HTML instead of
     JSON, missing backends, broken imports)
   - Verify that components built by different agents connect
     properly

7. **Check for Missing Components**:
   - Are there API calls to endpoints that don't exist?
   - Are there imports of modules that were never created?
   - Are there references to services that weren't built?
   - Does the design spec describe components that have no code?

8. **Log Results**:
   CRITICAL: Log verification results as an artifact:
   ```
   log_artifact(
       task_id="<current_task_id>",
       filename="integration_verification.json",
       content="<json results>",
       artifact_type="integration-verification",
       project_root="<project_root>",
       description="Integration verification results"
   )
   ```

   JSON format:
   ```json
   {{
     "project_name": "{project_name}",
     "install": {{
       "command": "...",
       "exit_code": 0,
       "success": true,
       "output": "..."
     }},
     "build": {{
       "command": "...",
       "exit_code": 0,
       "success": true,
       "output": "..."
     }},
     "start": {{
       "command": "...",
       "success": true,
       "output": "..."
     }},
     "health_check": {{
       "url": "...",
       "status_code": 200,
       "success": true,
       "response_type": "html/json/etc"
     }},
     "missing_components": [],
     "overall_pass": true,
     "remediation_notes": null
   }}
   ```

9. **Always Complete the Task**:
   - Mark this task as DONE regardless of pass/fail
   - Set `overall_pass` to false if verification failed
   - Include detailed `remediation_notes` describing what
     failed and why
"""


def enhance_project_with_integration(
    tasks: List[Task],
    project_description: str,
    project_name: str = "Project",
) -> List[Task]:
    """
    Add integration verification task to project if appropriate.

    Should be called BEFORE enhance_project_with_documentation()
    so that the documentation task depends on the integration task.

    Parameters
    ----------
    tasks : List[Task]
        Original project tasks.
    project_description : str
        Project description.
    project_name : str
        Name of the project.

    Returns
    -------
    List[Task]
        Task list with integration task added if appropriate.
    """
    if not IntegrationTaskGenerator.should_add_integration_task(project_description):
        logger.info("Skipping integration verification for this project")
        return tasks

    task = IntegrationTaskGenerator.create_integration_task(tasks, project_name)

    if task:
        logger.info(f"Added integration verification task: {task.name}")
        return tasks + [task]

    return tasks
