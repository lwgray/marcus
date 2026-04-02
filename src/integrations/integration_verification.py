"""
Integration Verification & Remediation Task Generation for Marcus.

Adds an integration task to projects that runs after implementation
completes. The integration agent inspects the project, figures out
how to build and start it, verifies it works end-to-end, and — critically —
FIXES any issues it finds before re-verifying.

This is not a report-only task. The integration agent is the last line of
defense: it glues components together, fills gaps left by task decomposition,
and ensures the product actually works as a whole.

See: https://github.com/lwgray/marcus/issues/296
Related: #271, #267, #257
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from src.core.models import Priority, Task, TaskStatus
from src.integrations.nlp_task_utils import TaskType

logger = logging.getLogger(__name__)


class IntegrationTaskGenerator:
    """Generate integration verification tasks for projects.

    Creates a task that runs after all implementation and testing tasks
    complete. The assigned agent inspects the project structure, figures
    out how to build/start it (regardless of language or framework),
    verifies whether the product works, and fixes any issues found.

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
        # Check for implementation tasks using the classifier
        # (not hardcoded labels, which AI-generated tasks may not have)
        from src.integrations.enhanced_task_classifier import (
            EnhancedTaskClassifier,
        )

        classifier = EnhancedTaskClassifier()
        implementation_tasks = classifier.filter_by_type(
            existing_tasks, TaskType.IMPLEMENTATION
        )

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
            "Tests run with full terminal output captured",
            "Project dependencies installed successfully",
            "Project builds without errors",
            "Application actually starts (startup output captured)",
            "Key endpoints hit with curl, full response captured",
            "Missing components detected AND fixed",
            "App entry point renders/wires all specified components",
            "All results include raw command output as evidence",
            "integration_verification.json artifact logged",
            "integration_remediation.json artifact logged if fixes applied",
            "Re-verification passes after fixes",
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
and works end-to-end — and FIX any issues you find.

**IMPORTANT**: This is an integration AND remediation task. You verify \
the product works, and if it doesn't, YOU FIX IT. You are the last line \
of defense — you glue components together, fill gaps left by task \
decomposition, and ensure the product actually works as a whole. \
Do NOT just report problems. Fix them.

**CRITICAL RULE — EVIDENCE REQUIRED**: Every step below MUST include \
the actual command you ran AND its real stdout/stderr output. Do NOT \
summarize, paraphrase, or claim a command succeeded without showing \
the output. If you cannot run a command, say so explicitly. \
Fabricating output is worse than reporting a failure.

## PHASE 1: VERIFY

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
   - Verify the project's module/package structure is complete

3. **Install Dependencies**:
   - Run the appropriate install command for the project
   - Capture the FULL terminal output
   - Record: command, exit code, raw output

4. **Run Tests**:
   - Run the project's test suite (pytest, npm test, etc.)
   - Capture the FULL terminal output (not a summary)
   - Record: command, exit code, pass/fail counts, raw output
   - If tests fail, record the actual error messages

5. **Build the Project**:
   - Run the appropriate build command
   - If no build step is needed (e.g., static HTML), skip this
   - Capture the FULL terminal output
   - Record: command, exit code, raw output

6. **Start the Application**:
   - Run the appropriate start command
   - Wait for the application to be ready (5-10 seconds)
   - Capture any startup output or errors
   - If the app fails to start, record the exact error
   - If the app is a static site, serve it with a simple server

7. **Verify the Application Responds**:
   - Run `curl` against the main page/endpoint
   - Capture the FULL curl output including HTTP status
   - Check that key features described in the design work
   - Look for error states (API calls returning HTML instead of
     JSON, missing backends, broken imports)
   - Verify that components built by different agents connect
   - Record each curl command and its full response

8. **Check for Missing Components**:
   - Is the app entry point wired up? (e.g., does App.jsx import
     and render all the components that were built?)
   - Are there API calls to endpoints that don't exist?
   - Are there imports of modules that were never created?
   - Are there references to services that weren't built?
   - Does the design spec describe components that have no code?
   - Are there duplicate/conflicting implementations that need
     consolidation?

## PHASE 2: FIX

If ANY issues were found in Phase 1, fix them NOW:

9. **Fix Issues**:
   - **Missing wiring**: If the app entry point doesn't import/render
     built components, wire them in. This is the most common gap —
     agents build components in isolation but nobody assembles them.
   - **Missing endpoints**: If the frontend calls APIs that don't exist
     in the backend, create the backend routes.
   - **Missing dependencies**: If imports reference modules that weren't
     created, create them or fix the imports.
   - **Build failures**: Fix compilation errors, missing configs, etc.
   - **Duplicate structures**: If multiple agents created conflicting
     implementations, consolidate to the best one.
   - Commit each fix with a descriptive message.
   - You are a full-capability agent — write code, create files,
     modify configurations. Do whatever it takes.

## PHASE 3: RE-VERIFY

10. **Re-verify After Fixes**:
    - Re-run the full verification (build, start, curl, tests)
    - Confirm your fixes resolved the issues
    - If new issues appear, fix those too (max 3 iterations)
    - Record the final verification state

## PHASE 4: LOG RESULTS

11. **Log Verification Results**:
    CRITICAL: Log verification results as an artifact. Every field \
in the JSON below MUST contain real command output, not summaries.

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
      "tests": {{
        "command": "pytest tests/ -v",
        "exit_code": 0,
        "passed": 45,
        "failed": 0,
        "success": true,
        "raw_output": "<PASTE FULL TERMINAL OUTPUT HERE>"
      }},
      "install": {{
        "command": "pip install -r requirements.txt",
        "exit_code": 0,
        "success": true,
        "raw_output": "<PASTE FULL TERMINAL OUTPUT HERE>"
      }},
      "build": {{
        "command": "npm run build",
        "exit_code": 0,
        "success": true,
        "raw_output": "<PASTE FULL TERMINAL OUTPUT HERE>"
      }},
      "start": {{
        "command": "uvicorn src.backend.main:app",
        "success": true,
        "raw_output": "<PASTE STARTUP OUTPUT HERE>"
      }},
      "health_checks": [
        {{
          "url": "http://localhost:8000/api/health",
          "curl_command": "curl -s http://localhost:8000/api/health",
          "status_code": 200,
          "success": true,
          "raw_response": "<PASTE FULL CURL RESPONSE HERE>"
        }}
      ],
      "missing_components": [],
      "overall_pass": true,
      "remediation_notes": null
    }}
    ```

    If a command fails, set success=false and paste the error output.
    Do NOT set success=true unless you have real output proving it.

12. **Log Remediation Record** (if you fixed anything):
    If you applied fixes in Phase 2, log a separate remediation \
artifact for tracking purposes:

    ```
    log_artifact(
        task_id="<current_task_id>",
        filename="integration_remediation.json",
        content="<json results>",
        artifact_type="integration-remediation",
        project_root="<project_root>",
        description="Integration remediation record"
    )
    ```

    JSON format:
    ```json
    {{
      "project_name": "{project_name}",
      "remediation_applied": true,
      "issues_found": [
        {{
          "description": "What was wrong",
          "severity": "critical | major | minor",
          "category": "composition_gap | missing_endpoint "
          "| missing_module | build_failure "
          "| duplicate_code | config_error",
          "root_cause": "planning_gap | agent_oversight | dependency_error"
        }}
      ],
      "fixes_applied": [
        {{
          "description": "What you fixed",
          "files_modified": ["path/to/file.js"],
          "commit_hash": "abc1234"
        }}
      ],
      "verification_before_fix": {{
        "overall_pass": false,
        "failing_checks": ["app entry point not wired", "missing API endpoint"]
      }},
      "verification_after_fix": {{
        "overall_pass": true,
        "tests_pass": true,
        "app_starts": true,
        "endpoints_respond": true
      }},
      "planning_gap_detected": true
    }}
    ```

    The `planning_gap_detected` field is important: set it to true \
if the fix was needed because no task was created for this work \
(e.g., no task to wire components into the entry point, no task \
to create a backend route that the design spec called for). This \
helps Marcus improve task planning over time.

13. **Complete the Task**:
    - Mark this task as DONE only after verification passes
    - If you could not fix all issues after 3 attempts, mark DONE
      anyway but set `overall_pass` to false with details on what
      remains broken and why you couldn't fix it
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
