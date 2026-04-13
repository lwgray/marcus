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
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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
        contract_file: Optional[str] = None,
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
        contract_file : Optional[str]
            Path to the shared contract artifact when contract-first
            decomposition is active (GH-320 PR 2). When set, the
            integration task description explicitly names this file
            and instructs the integration agent to treat it as
            authoritative — fix implementations that diverge, do NOT
            modify the contract. Without this instruction, an
            integration agent could silently "fix" a mismatch by
            editing the contract, breaking the invariant that made
            contract-first decomposition work in the first place.

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
            project_name, contract_file=contract_file
        )

        acceptance_criteria = [
            "Tests run with full terminal output captured",
            "Project dependencies installed successfully",
            "Project builds without errors",
            "Application actually starts (startup output captured)",
            "Key endpoints hit with curl, full response captured",
            "Missing components detected AND fixed",
            "App entry point renders/wires all specified components",
            "Cross-agent interface contracts verified "
            "(identifiers, data shapes, config values "
            "match across boundaries)",
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

        Skips for prototypes, demos, and POCs. Explicitly does NOT
        skip for the word "experiment" — Marcus experiments need
        integration verification so we can measure whether multi-
        agent coordination changes actually catch integration bugs
        at the merged-product level. See GH-320 PR 1 for context.

        The ``test`` POC marker is distinguished from testing
        *infrastructure* mentions (``test suite``, ``unit tests``,
        ``test-driven``, ``testing framework``, etc.) by scrubbing
        compound phrases before the word-boundary search so real
        projects that happen to mention their test strategy do not
        get their integration task suppressed.

        Parameters
        ----------
        project_description : str
            Natural language project description.

        Returns
        -------
        bool
            True if integration verification should be added.
        """
        description_lower = project_description.lower()

        # Unambiguous POC markers — matched with word boundaries so
        # ``contest``/``democracy``/etc. don't trip the rule, and with
        # optional plural ``s`` so ``pocs``/``demos``/``proof of
        # concepts`` still skip as expected (Codex P1 on PR #333).
        poc_patterns = [
            r"\bpocs?\b",
            r"\bproof of concepts?\b",
            r"\bdemos?\b",
        ]
        for pattern in poc_patterns:
            if re.search(pattern, description_lower):
                return False

        # ``test`` is ambiguous: "Quick test of the new encoder" is
        # POC intent, but "Build an app with a test suite" is not.
        # Scrub compound phrases that describe testing infrastructure
        # before running the word-boundary check.
        test_compound_patterns = [
            # "test suite", "test cases", "test coverage", etc.
            r"\btests?\s+"
            r"(suites?|cases?|coverage|harness|plan|plans|"
            r"frameworks?|beds?|runners?|infrastructure|infra|"
            r"strategy|strategies|approach|approaches)\b",
            # "unit tests", "integration test", "e2e tests", etc.
            r"\b(unit|integration|smoke|regression|acceptance|"
            r"e2e|end[- ]to[- ]end|functional|performance|load|"
            r"stress|api|contract|property|mutation|snapshot)"
            r"\s+tests?\b",
            # "test-driven", "tests-driven"
            r"\btests?[-\s]driven\b",
            # "testing framework/library/etc." — "testing" with a
            # compound noun is infrastructure, not POC intent.
            r"\btesting\s+"
            r"(framework|frameworks|library|libraries|"
            r"infrastructure|suite|suites|strategy|strategies|"
            r"approach|approaches|harness)\b",
        ]
        scrubbed = description_lower
        for pattern in test_compound_patterns:
            scrubbed = re.sub(pattern, " ", scrubbed)

        if re.search(r"\btest\b", scrubbed):
            return False

        return True

    @staticmethod
    def _generate_integration_description(
        project_name: str,
        contract_file: Optional[str] = None,
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
        contract_file : Optional[str]
            Path to the shared contract artifact when contract-first
            decomposition is active. When set, a contract-authority
            preamble is prepended to the description so the integration
            agent treats the contract as read-only.

        Returns
        -------
        str
            Detailed task description with verification steps.
        """
        preamble = ""
        if contract_file:
            preamble = (
                "**CONTRACT-FIRST PROJECT**: This project was decomposed "
                "using contract-first decomposition (GH-320). The shared "
                f"contract lives at:\n\n"
                f"    {contract_file}\n\n"
                "**The contract is AUTHORITATIVE**. Agents built their "
                "implementations against it. If any implementation "
                "diverges from the contract during your verification, "
                "FIX THE IMPLEMENTATION — do NOT modify the contract "
                "file. The contract was the agreed-upon interface "
                "boundary; silently editing it to match a broken "
                "implementation defeats the purpose of contract-first "
                "decomposition and will cause future regressions.\n\n"
                "Before starting Phase 1, `Read` the contract file so "
                "you know the authoritative interface shapes, "
                "identifiers, and configuration values. Use the "
                "contract as your reference when verifying cross-agent "
                "boundaries in step 9.\n\n---\n\n"
            )
        return preamble + f"""Verify that {project_name} actually builds, starts, \
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

9. **Verify ALL Interface Boundaries (cross-agent AND intra-agent)**:
   This is the most critical step. A boundary is any place where \
one chunk of code produces data that another chunk of code consumes — \
regardless of who wrote either side. You MUST trace data across \
every boundary where output becomes input.

   **Both kinds of boundaries are dangerous, but for different reasons**:

   - **Cross-agent boundaries** — different authors make independent \
assumptions about shared interfaces. Each side works in isolation, \
breaks when connected. These are the OBVIOUS boundaries.

   - **Intra-agent boundaries (SAME AUTHOR, SAME TASK)** — one agent \
builds BOTH a producer API and a consumer frontend (or service client, \
or caller module). Each piece works correctly in isolation, but the \
two halves are never actually wired together because the agent had a \
mental model of "I built this, it works" and never verified the \
handoff. **These are the LEAST VISIBLE boundaries and the MOST LIKELY \
to be broken**, because the author built both sides in the same head \
and had no reason to question the connection. Dashboard-v71 shipped a \
complete configuration API (PATCH /api/dashboard/widgets/{{id}}) \
written by the same agent that wrote the frontend — the frontend never \
called it, and the config API was functionally dead from the user's \
perspective. The integration verification agent missed it because \
they were the same person.

   **How to find ALL boundaries**: Do not filter by git author. Find \
boundaries by DATA FLOW, not by authorship:

   a. **Every HTTP route handler is a producer.** For every \
`@app.get`, `@app.post`, `@app.patch`, `@router.*`, Flask route, \
Django view, or similar, the handler's response is data that must be \
consumed by at least one caller. Grep the entire repo for the route's \
URL path (as a string literal). If no caller references it, that \
route is either dead code, an integration gap, or a public API. \
Investigate which and fix or document.

   b. **Every exported function/class/module is a producer.** \
Everything in an `__init__.py` exports list, a `module.exports`, \
or a named TypeScript/JavaScript export is producer surface. Check \
that consumers exist in the repo.

   c. **Every config file, environment variable, storage key, or \
event name is a boundary.** Each one has a producer (the module \
that writes it) and a consumer (the module that reads it). If they \
diverge on the string, the integration is broken even if both \
modules pass their own tests.

   d. **Every file written to disk by one module and read by \
another is a boundary.** Artifacts, caches, logs, intermediate build \
outputs — producer writes, consumer reads, and the filenames/schemas \
must match.

   **At each boundary, verify**:

   a. **Identifiers match**: If one module stores, emits, or sends \
data under a key/name/field, the consuming module must use the \
exact same key/name/field to retrieve it. Search for string \
literals, dictionary keys, storage keys, event names, column \
names, and environment variable names that appear on both sides \
of a boundary. If they differ, the integration is broken even \
though both modules work alone.

   b. **Data shapes match**: If one module produces a data \
structure (object, response, message, file format), the consuming \
module must expect that exact shape. Check return types against \
the caller's expectations. Check serialized output against the \
parser's assumptions. Check that array vs object, nested vs flat, \
and optional vs required fields agree.

   c. **Configuration is consistent**: Ports, hostnames, file \
paths, base URLs, timeout values, and protocol choices that are \
referenced by multiple modules must agree. Check config files, \
environment defaults, and hardcoded values across module \
boundaries.

   d. **Duplicate implementations are consolidated**: If multiple \
agents implemented the same concept (e.g., validation, hashing, \
formatting), identify which one is actually used at runtime and \
whether callers reference the correct one. Flag any where \
different callers use different implementations with different \
behavior.

   **How to verify**: For each boundary you find, write a short \
trace — follow a single piece of data from where it is produced \
to where it is consumed. If you can't prove the identifiers, \
shapes, and config values match at every step, that boundary is \
broken. Do not rely on tests passing — tests often exercise \
modules in isolation and will miss cross-boundary mismatches.

   **MANDATORY CONSUMER-CLOSURE CHECK**: Before you can pass this \
step, you MUST produce a list of every HTTP route handler in the \
project and, for each one, the exact grep/search command you ran \
to find its consumer(s) PLUS the filename:line of at least one \
call site. Routes with ZERO consumers are a critical finding and \
must be reported. Example format:

       Route: PATCH /api/dashboard/widgets/{{id}} \
(src/backend/main.py:122)
       Consumer search: grep -rn "dashboard/widgets/" src/frontend/src/
       Consumers found: src/frontend/src/hooks/useWidgets.ts:45
       Status: CONSUMED ✓

       Route: GET /api/dashboard/layout (src/backend/main.py:49)
       Consumer search: grep -rn "dashboard/layout" src/frontend/src/
       Consumers found: src/frontend/src/hooks/useDashboard.ts:50
       Status: CONSUMED ✓

   If you find a route with zero consumers, investigate: is it \
dead code (remove it), a public API (document it in README), or \
an integration gap (wire the consumer up)? Do not pass this step \
with unaccounted-for routes.

   **MARCUS-SIDE VERIFICATION (REQUIRED DECLARATION)**: \
When you mark this task complete, you MUST declare a \
``start_command`` parameter on the ``report_task_progress`` call. \
Marcus runs the declared command as an independent subprocess \
check AFTER you mark the task complete. It is how Marcus \
verifies — without trusting your self-report — that the \
deliverable actually starts. This is strictly enforced: \
integration-task completions that omit ``start_command`` are \
rejected.

   **How to declare it:**

   For a one-shot command (build, type check, CLI --help, etc.) \
— declare only ``start_command``. Marcus will run it with a 60s \
timeout and require exit code 0:

   ```python
   report_task_progress(
       task_id=task_id,
       status="completed",
       progress=100,
       message="integration verified",
       start_command="npm run build",
   )
   ```

   For a long-running server (uvicorn, flask, node server, etc.) \
— declare BOTH ``start_command`` (how to start it) AND \
``readiness_probe`` (how to detect it's actually serving). Marcus \
will start the server in the background, poll the probe once per \
second for up to 15 seconds, and pass when the probe returns exit \
0. Marcus always kills the background process afterward:

   ```python
   report_task_progress(
       task_id=task_id,
       status="completed",
       progress=100,
       message="integration verified",
       start_command="uvicorn main:app --port 8000",
       readiness_probe="curl -f http://localhost:8000/health",
   )
   ```

   **Choosing the right values**: the ``start_command`` is \
whatever YOU ran to verify the deliverable works. You already \
ran it during Phase 1 verification. Write the EXACT command \
that worked for you, including any flags. Marcus runs commands \
with ``CI=true`` set in the environment — if your command needs \
interactive prompts it will fail in Marcus's subprocess. Use \
non-interactive flags where needed.

   **What if there's no meaningful start_command?** There \
always is. Some examples by stack:

   - **Static HTML**: ``start_command="test -f index.html"`` \
(file existence check — Marcus runs it, exit 0 passes)
   - **Library with no entry point**: \
``start_command="python -c 'import mypackage'"`` (import smoke)
   - **Pure documentation project**: \
``start_command="test -d docs && test -f README.md"``
   - **Data pipeline with no server**: \
``start_command="python -m mypipeline --dry-run"``

   If you genuinely cannot think of a smoke command, that is a \
signal you don't have a clear definition of "done" for this \
deliverable — stop and ask yourself what "working" means, then \
write the command that proves it.

   **Fabrication check**: Marcus runs the command you declare. \
If you invent a command that sounds reasonable but doesn't \
actually work, Marcus will catch you. Declare the command you \
actually ran.

## PHASE 2: FIX

If ANY issues were found in Phase 1, fix them NOW:

10. **Fix Issues**:
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

11. **Re-verify After Fixes**:
    - Re-run the full verification (build, start, curl, tests)
    - Confirm your fixes resolved the issues
    - If new issues appear, fix those too (max 3 iterations)
    - Record the final verification state

## PHASE 4: LOG RESULTS

12. **Log Verification Results**:
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
      "interface_contracts": [
        {{
          "boundary": "producer_file -> consumer_file",
          "what_was_checked": "identifier/shape/config",
          "producer_value": "what the producing module uses",
          "consumer_value": "what the consuming module expects",
          "match": true,
          "fix_applied": null
        }}
      ],
      "overall_pass": true,
      "remediation_notes": null
    }}
    ```

    If a command fails, set success=false and paste the error output.
    Do NOT set success=true unless you have real output proving it.

13. **Log Remediation Record** (if you fixed anything):
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
          "| duplicate_code | config_error "
          "| interface_contract_mismatch",
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

14. **Complete the Task**:
    - Mark this task as DONE only after verification passes
    - If you could not fix all issues after 3 attempts, mark DONE
      anyway but set `overall_pass` to false with details on what
      remains broken and why you couldn't fix it
"""


def enhance_project_with_integration(
    tasks: List[Task],
    project_description: str,
    project_name: str = "Project",
    contract_file: Optional[str] = None,
    functional_requirements: Optional[List[Dict[str, Any]]] = None,
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
    contract_file : Optional[str]
        Path to the shared contract artifact when contract-first
        decomposition is active (GH-320 PR 2). Forwarded to the
        integration task generator so the verification agent treats
        the contract as read-only authoritative.
    functional_requirements : Optional[List[Dict[str, Any]]]
        PRD functional requirements from ``PRDAnalysis``. When
        provided (contract-first path, GH-320 task #64), each
        requirement's ``name`` is appended to the integration task's
        ``acceptance_criteria`` so the integration agent verifies
        the user's original intent was realized — not just that the
        code compiles and tests pass. This was the gap in Experiment
        4 v2 where both agents built clean plumbing but no visible
        UI because the integration agent had no reference back to
        the user's "display weather" ask.

    Returns
    -------
    List[Task]
        Task list with integration task added if appropriate.
    """
    if not IntegrationTaskGenerator.should_add_integration_task(project_description):
        logger.info("Skipping integration verification for this project")
        return tasks

    task = IntegrationTaskGenerator.create_integration_task(
        tasks, project_name, contract_file=contract_file
    )

    if task:
        # Intent preservation (GH-320 task #64): append functional
        # requirements as acceptance criteria so the integration agent
        # verifies the user's original ask, not just code correctness.
        if functional_requirements:
            for req in functional_requirements:
                req_name = req.get("name", "")
                if req_name:
                    task.acceptance_criteria.append(
                        f"User requirement verified: {req_name}"
                    )
            logger.info(
                f"Enriched integration task with "
                f"{len(functional_requirements)} functional "
                f"requirement(s) as acceptance criteria"
            )
        logger.info(f"Added integration verification task: {task.name}")
        return tasks + [task]

    return tasks
