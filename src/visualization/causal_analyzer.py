"""
Causal analysis engine for understanding WHY project stalls happen.

Analyzes snapshot data to build causal chains explaining root causes.
"""

from typing import Any, Dict, List


class CausalAnalyzer:
    """
    Analyzes stall snapshots to determine root causes and causal chains.

    Goes beyond "what happened" to explain "why it happened" by:
    - Tracing dependency chains back to root causes
    - Analyzing event sequences for cause-effect relationships
    - Identifying human decisions that led to the stall
    - Finding the earliest point where intervention could have prevented it
    """

    def __init__(self, snapshot: Dict[str, Any]):
        """
        Initialize causal analyzer.

        Parameters
        ----------
        snapshot : Dict[str, Any]
            Complete stall snapshot data
        """
        self.snapshot = snapshot

    def analyze(self) -> Dict[str, Any]:
        """
        Perform complete causal analysis.

        Returns
        -------
        Dict[str, Any]
            Causal analysis results with root causes, chains, and explanations
        """
        return {
            "root_causes": self._find_root_causes(),
            "causal_chains": self._build_causal_chains(),
            "intervention_points": self._find_intervention_points(),
            "human_decisions": self._analyze_human_decisions(),
            "narrative": self._build_narrative(),
            "system_failures": self._analyze_system_failures(),
            "actionable_fixes": self._generate_actionable_fixes(),
            "prevention_strategies": self._generate_prevention_strategies(),
        }

    def _find_root_causes(self) -> List[Dict[str, Any]]:
        """
        Find root causes - the ultimate reasons for the stall.

        Returns
        -------
        List[Dict[str, Any]]
            List of root causes with explanations
        """
        root_causes = []

        # Analyze dependency issues
        diag = self.snapshot.get("diagnostic_report", {})
        issues = diag.get("issues", [])

        for issue in issues:
            if issue.get("type") == "circular_dependency":
                root_causes.append(
                    {
                        "type": "circular_dependency",
                        "severity": "critical",
                        "explanation": (
                            "Tasks form a cycle where each depends on another, "
                            "making it impossible to complete any of them."
                        ),
                        "why": (
                            "Someone created dependencies that loop back on "
                            "themselves. This is a design error in task "
                            "planning."
                        ),
                        "affected_tasks": issue.get("affected_count", 0),
                        "impact": "All tasks in the cycle are permanently blocked",
                    }
                )

            elif issue.get("type") == "bottleneck":
                affected = issue.get("affected_count", 0)
                root_causes.append(
                    {
                        "type": "critical_bottleneck",
                        "severity": "high",
                        "explanation": (
                            f"One task is blocking multiple others "
                            f"({affected} tasks)"
                        ),
                        "why": (
                            "Task dependencies were modeled sequentially "
                            "instead of in parallel. Work that could happen "
                            "concurrently is forced to wait."
                        ),
                        "affected_tasks": affected,
                        "impact": "Development velocity is severely limited",
                    }
                )

            elif issue.get("type") == "missing_dependency":
                root_causes.append(
                    {
                        "type": "missing_task",
                        "severity": "high",
                        "explanation": (
                            "Tasks reference dependencies that don't exist"
                        ),
                        "why": (
                            "Either: (1) A task was deleted without updating "
                            "dependents, or (2) Task IDs were entered "
                            "incorrectly during creation"
                        ),
                        "affected_tasks": issue.get("affected_count", 0),
                        "impact": "Affected tasks can never be started",
                    }
                )

        # Analyze early completions
        early_completions = self.snapshot.get("early_completions", [])
        if early_completions:
            task_names = [ec.get("task_name") for ec in early_completions]
            names_str = ", ".join(task_names[:3])
            root_causes.append(
                {
                    "type": "premature_completion",
                    "severity": "high",
                    "explanation": (f"Critical tasks completed too early: {names_str}"),
                    "why": (
                        "Tasks were marked complete without dependencies "
                        "being set correctly. This suggests: (1) "
                        "Dependencies weren't modeled, (2) Someone manually "
                        "marked tasks done, or (3) An agent completed tasks "
                        "out of order."
                    ),
                    "affected_tasks": len(early_completions),
                    "impact": (
                        "Project appears complete but critical work is "
                        "actually undone"
                    ),
                }
            )

        # Analyze conversation patterns
        conversation = self.snapshot.get("conversation_history", [])

        # Count repeated "no task" requests
        no_task_events = [
            e for e in conversation if "no_task" in e.get("type", "").lower()
        ]
        if len(no_task_events) >= 5:
            no_task_count = len(no_task_events)
            root_causes.append(
                {
                    "type": "assignment_deadlock",
                    "severity": "critical",
                    "explanation": (
                        f"Agents requested tasks {no_task_count} times but "
                        f"none were available"
                    ),
                    "why": (
                        "All available tasks are blocked by dependencies. "
                        "This is usually caused by circular dependencies or "
                        "missing tasks that were supposed to unlock work."
                    ),
                    "affected_tasks": "all",
                    "impact": "No progress possible - complete development halt",
                }
            )

        # Count repeated failures
        failure_events = [
            e
            for e in conversation
            if "fail" in e.get("type", "").lower()
            or "error" in e.get("type", "").lower()
        ]
        if len(failure_events) >= 3:
            # Group by task
            failed_tasks: Dict[str, int] = {}
            for event in failure_events:
                task_id = event.get("data", {}).get("task_id")
                if task_id:
                    failed_tasks[task_id] = failed_tasks.get(task_id, 0) + 1

            for task_id, count in failed_tasks.items():
                if count >= 2:
                    root_causes.append(
                        {
                            "type": "task_failure_loop",
                            "severity": "high",
                            "explanation": (
                                f"Task {task_id} failed {count} times in a row"
                            ),
                            "why": (
                                "The task has a fundamental problem: unclear "
                                "requirements, missing dependencies, or "
                                "technical blockers. The agent is stuck "
                                "retrying the same approach that doesn't work."
                            ),
                            "affected_tasks": 1,
                            "impact": (
                                "Agent resources wasted, no forward progress "
                                "on this task"
                            ),
                        }
                    )

        return root_causes

    def _build_causal_chains(self) -> List[Dict[str, Any]]:
        """
        Build causal chains showing cause → effect relationships.

        Returns
        -------
        List[Dict[str, Any]]
            List of causal chains from root cause to final effect
        """
        chains = []

        # Example chain: Circular dependency → All tasks blocked
        root_causes = self._find_root_causes()

        for cause in root_causes:
            if cause["type"] == "circular_dependency":
                chains.append(
                    {
                        "root_cause": ("Circular dependency created in task planning"),
                        "chain": [
                            {
                                "step": 1,
                                "event": (
                                    "Tasks A, B, C created with circular "
                                    "dependencies"
                                ),
                                "why": (
                                    "Task planner didn't validate dependency " "graph"
                                ),
                            },
                            {
                                "step": 2,
                                "event": ("All three tasks marked as TODO but blocked"),
                                "why": (
                                    "Each task waiting for another to complete " "first"
                                ),
                            },
                            {
                                "step": 3,
                                "event": (
                                    "Agents request tasks, get 'no tasks " "available'"
                                ),
                                "why": "No task has its dependencies satisfied",
                            },
                            {
                                "step": 4,
                                "event": "Development completely halts",
                                "why": "No tasks can be assigned to any agent",
                            },
                        ],
                        "final_impact": cause["impact"],
                    }
                )

            elif cause["type"] == "premature_completion":
                affected = cause.get("affected_tasks", 1)
                chains.append(
                    {
                        "root_cause": ("Final tasks completed before prerequisites"),
                        "chain": [
                            {
                                "step": 1,
                                "event": (f"{affected} critical tasks completed early"),
                                "why": (
                                    "Dependencies not modeled or manually " "overridden"
                                ),
                            },
                            {
                                "step": 2,
                                "event": "Remaining tasks appear blocked",
                                "why": (
                                    "They depend on work that should have come "
                                    "after 'completion' tasks"
                                ),
                            },
                            {
                                "step": 3,
                                "event": (
                                    "Project shows as mostly complete but work "
                                    "remains"
                                ),
                                "why": (
                                    "Completion metrics don't reflect actual "
                                    "progress"
                                ),
                            },
                            {
                                "step": 4,
                                "event": "Confusion about project state",
                                "why": (
                                    "Dashboard shows success but agents report "
                                    "blockers"
                                ),
                            },
                        ],
                        "final_impact": cause["impact"],
                    }
                )

            elif cause["type"] == "assignment_deadlock":
                conversation = self.snapshot.get("conversation_history", [])
                no_task = [
                    e for e in conversation if "no_task" in e.get("type", "").lower()
                ]
                chains.append(
                    {
                        "root_cause": "All available work paths blocked",
                        "chain": [
                            {
                                "step": 1,
                                "event": (
                                    "Task dependencies create a blocking " "pattern"
                                ),
                                "why": (
                                    "No task exists that can be started "
                                    "independently"
                                ),
                            },
                            {
                                "step": 2,
                                "event": "Agents repeatedly request work",
                                "why": (
                                    "They're ready to work but nothing is " "available"
                                ),
                            },
                            {
                                "step": 3,
                                "event": (f"{len(no_task)} failed assignment attempts"),
                                "why": (
                                    "System keeps trying but conditions never " "change"
                                ),
                            },
                            {
                                "step": 4,
                                "event": "Complete development stall",
                                "why": "No mechanism to break the deadlock",
                            },
                        ],
                        "final_impact": "Zero velocity - no work possible",
                    }
                )

        return chains

    def _find_intervention_points(self) -> List[Dict[str, Any]]:
        """
        Find points where human intervention could have prevented the stall.

        Returns
        -------
        List[Dict[str, Any]]
            List of intervention opportunities with timing and actions
        """
        interventions = []

        timeline = self.snapshot.get("task_completion_timeline", [])

        # Check timeline for early signs
        if len(timeline) >= 3:
            # If "success" task completed before 80% of tasks
            for i, completed in enumerate(timeline):
                task_name = completed.get("task_name", "").lower()
                keywords = ["success", "complete", "done", "deploy"]
                if any(keyword in task_name for keyword in keywords):
                    completion_pct = ((i + 1) / len(timeline)) * 100
                    if completion_pct < 80:
                        task_name_str = completed.get("task_name")
                        interventions.append(
                            {
                                "timing": "Early in project",
                                "trigger": (
                                    f"'{task_name_str}' completed at "
                                    f"{completion_pct:.0f}%"
                                ),
                                "action": (
                                    "Review task dependencies before marking "
                                    "final tasks complete"
                                ),
                                "prevention": (
                                    "Would have caught missing dependencies "
                                    "before they blocked work"
                                ),
                                "window": "Before task was marked complete",
                            }
                        )

        # Check for dependency issues
        diag = self.snapshot.get("diagnostic_report", {})
        diag_issues = diag.get("issues", [])
        for issue in diag_issues:
            if issue.get("type") == "circular_dependency":
                interventions.append(
                    {
                        "timing": "During task creation",
                        "trigger": "Circular dependency introduced",
                        "action": (
                            "Validate dependency graph when tasks are " "created"
                        ),
                        "prevention": (
                            "Automated validation would reject circular " "dependencies"
                        ),
                        "window": "At task creation time",
                    }
                )

        # Check conversation for warning signs
        conversation = self.snapshot.get("conversation_history", [])
        no_task_events = [
            e for e in conversation if "no_task" in e.get("type", "").lower()
        ]
        no_task_count = len(no_task_events)

        if no_task_count >= 3:
            interventions.append(
                {
                    "timing": "After 3rd failed task request",
                    "trigger": (
                        f"Agent requested tasks {no_task_count} times with "
                        f"no success"
                    ),
                    "action": (
                        "Automatically run diagnostics after N failed " "requests"
                    ),
                    "prevention": (
                        "Would have identified blocking issues before " "complete stall"
                    ),
                    "window": ("After 3 failed requests (before it became critical)"),
                }
            )

        return interventions

    def _analyze_human_decisions(self) -> List[Dict[str, Any]]:
        """
        Identify human decisions that contributed to the stall.

        Returns
        -------
        List[Dict[str, Any]]
            List of decisions with impact analysis
        """
        decisions = []

        # Analyze early completions - likely manual overrides
        early_completions = self.snapshot.get("early_completions", [])
        if early_completions:
            early_count = len(early_completions)
            decisions.append(
                {
                    "decision": ("Marked final tasks as complete prematurely"),
                    "when": "Early in project lifecycle",
                    "impact": (
                        f"{early_count} critical tasks completed out of " f"order"
                    ),
                    "why_problematic": (
                        "Broke the dependency chain, making other tasks "
                        "appear blocked"
                    ),
                    "alternative": (
                        "Wait until dependencies are complete, or "
                        "restructure task graph"
                    ),
                    "severity": "high",
                }
            )

        # Analyze task creation decisions
        diag = self.snapshot.get("diagnostic_report", {})
        diag_issues = diag.get("issues", [])
        for issue in diag_issues:
            if issue.get("type") == "circular_dependency":
                affected = issue.get("affected_count", 0)
                decisions.append(
                    {
                        "decision": "Created circular task dependencies",
                        "when": "During project planning",
                        "impact": f"{affected} tasks permanently blocked",
                        "why_problematic": (
                            "Makes it logically impossible to complete any "
                            "task in the cycle"
                        ),
                        "alternative": (
                            "Model dependencies as DAG (Directed Acyclic " "Graph)"
                        ),
                        "severity": "critical",
                    }
                )

            elif issue.get("type") == "bottleneck":
                affected = issue.get("affected_count", 0)
                decisions.append(
                    {
                        "decision": ("Modeled work as sequential instead of parallel"),
                        "when": "During task dependency planning",
                        "impact": (f"{affected} tasks forced to wait unnecessarily"),
                        "why_problematic": (
                            "Limits development velocity - could be working "
                            "in parallel"
                        ),
                        "alternative": (
                            "Identify truly independent tasks and remove "
                            "false dependencies"
                        ),
                        "severity": "medium",
                    }
                )

        return decisions

    def _build_narrative(self) -> str:
        """
        Build human-readable narrative explaining what happened and why.

        Returns
        -------
        str
            Story of the stall from beginning to end
        """
        root_causes = self._find_root_causes()
        chains = self._build_causal_chains()
        interventions = self._find_intervention_points()

        narrative_parts = []

        # Opening
        project_name = self.snapshot.get("project_name", "this project")
        opening = (
            f"Development on {project_name} has completely stalled. "
            f"Here's what happened:\n"
        )
        narrative_parts.append(opening)

        # Root cause explanation
        if root_causes:
            narrative_parts.append("\n🔍 ROOT CAUSE ANALYSIS:\n")
            for i, cause in enumerate(root_causes[:3], 1):  # Top 3
                cause_type = cause["type"].replace("_", " ").title()
                severity = cause["severity"]
                narrative_parts.append(f"\n{i}. {cause_type} (Severity: {severity})\n")
                narrative_parts.append(f"   WHAT: {cause['explanation']}\n")
                narrative_parts.append(f"   WHY: {cause['why']}\n")
                narrative_parts.append(f"   IMPACT: {cause['impact']}\n")

        # Causal chain
        if chains:
            narrative_parts.append("\n⛓️  HOW IT UNFOLDED:\n")
            chain = chains[0]  # Show primary chain
            narrative_parts.append(f"\nStarting from: {chain['root_cause']}\n")
            for step in chain["chain"]:
                narrative_parts.append(
                    f"\n  Step {step['step']}: {step['event']}\n"
                    f"  → Because: {step['why']}\n"
                )
            narrative_parts.append(f"\n  Final Result: {chain['final_impact']}\n")

        # Intervention points
        if interventions:
            narrative_parts.append("\n🚨 WHERE WE COULD HAVE INTERVENED:\n")
            for i, intervention in enumerate(interventions[:3], 1):
                narrative_parts.append(
                    f"\n{i}. {intervention['timing']}\n"
                    f"   Trigger: {intervention['trigger']}\n"
                    f"   Action: {intervention['action']}\n"
                    f"   Would have: {intervention['prevention']}\n"
                )

        # Conclusion
        conclusion = (
            "\n💡 BOTTOM LINE:\n"
            "This stall was preventable. The root cause was introduced "
            "during task planning, and warning signs appeared early. With "
            "better validation and monitoring, this could have been caught "
            "before it blocked all development.\n"
        )
        narrative_parts.append(conclusion)

        return "".join(narrative_parts)

    def _analyze_system_failures(self) -> List[Dict[str, Any]]:
        """
        Analyze WHICH parts of Marcus failed and WHY.

        Returns
        -------
        List[Dict[str, Any]]
            List of system failures with technical details
        """
        failures = []

        early_completions = self.snapshot.get("early_completions", [])

        # FAILURE 1: PROJECT_SUCCESS task created WITHOUT proper dependencies
        if early_completions:
            for ec in early_completions:
                if "PROJECT_SUCCESS" in ec.get("task_name", ""):
                    pct = ec.get("completion_percentage", 0)
                    failures.append(
                        {
                            "system": "Task Creation / NLP Parser",
                            "failure": (
                                "PROJECT_SUCCESS task created with EMPTY or "
                                "INCOMPLETE dependencies"
                            ),
                            "evidence": (f"Task completed at {pct}% - should be last"),
                            "code_location": (
                                "src/integrations/documentation_tasks.py:89-96"
                            ),
                            "root_cause": (
                                "DocumentationTaskGenerator."
                                "create_documentation_task() creates "
                                "dependencies list by filtering "
                                "existing_tasks. If tasks don't have proper "
                                "labels (documentation/final/verification), OR "
                                "if this function is called BEFORE other tasks "
                                "are created, the dependencies list will be "
                                "EMPTY."
                            ),
                            "why_checks_failed": (
                                "Dependencies are set at task CREATION time. "
                                "If task ordering is wrong (PROJECT_SUCCESS "
                                "created too early in the flow), it has no "
                                "tasks to depend on. Circular dependency "
                                "checks only validate the GRAPH - they don't "
                                "check if final tasks are actually depending "
                                "on implementation tasks."
                            ),
                            "severity": "critical",
                        }
                    )

        # FAILURE 2: Task ordering/priority allows final tasks to jump
        diag = self.snapshot.get("diagnostic_report", {})
        if diag.get("issues"):
            for issue in diag.get("issues", []):
                if issue.get("type") == "bottleneck":
                    affected = issue.get("affected_count", 0)
                    failures.append(
                        {
                            "system": "Task Assignment / Priority Calculation",
                            "failure": (
                                "Task priority/ordering allows wrong tasks "
                                "to be assigned first"
                            ),
                            "evidence": (f"{affected} tasks blocked by bottleneck"),
                            "code_location": ("src/core/task.py (find_optimal_task)"),
                            "root_cause": (
                                "Priority calculation may not account for "
                                "task position in dependency DAG. Tasks with "
                                "HIGH priority but early in the chain (like "
                                "PROJECT_SUCCESS) can be assigned before "
                                "their prerequisites if dependency "
                                "enforcement is not strict enough."
                            ),
                            "why_checks_failed": (
                                "Dependency checks validate STRUCTURE but not "
                                "ENFORCEMENT. A task can have dependencies in "
                                "its data model but still be assigned if the "
                                "assignment logic doesn't properly block on "
                                "incomplete dependencies."
                            ),
                            "severity": "high",
                        }
                    )

        # FAILURE 3: Circular dependency detection EXISTS but isn't preventing
        if any(
            issue.get("type") == "circular_dependency"
            for issue in diag.get("issues", [])
        ):
            failures.append(
                {
                    "system": "Circular Dependency Validation",
                    "failure": (
                        "Circular dependency checks exist but are not "
                        "PREVENTING task creation"
                    ),
                    "evidence": ("Circular dependencies detected in completed project"),
                    "code_location": (
                        "src/core/task_diagnostics.py " "(detect_circular_dependencies)"
                    ),
                    "root_cause": (
                        "Validation is likely DIAGNOSTIC (detecting "
                        "problems after they exist) rather than "
                        "PREVENTATIVE (blocking bad task creation). The "
                        "checks run AFTER tasks are created, not DURING "
                        "creation."
                    ),
                    "why_checks_failed": (
                        "The validation code exists in task_diagnostics.py "
                        "but there's no enforcement layer that REJECTS "
                        "task creation when circular dependencies would be "
                        "introduced. It's a reporting tool, not a "
                        "gatekeeper."
                    ),
                    "severity": "critical",
                }
            )

        return failures

    def _generate_actionable_fixes(self) -> List[Dict[str, Any]]:
        """
        Generate SPECIFIC, ACTIONABLE fixes with file paths and code changes.

        Returns
        -------
        List[Dict[str, Any]]
            List of fixes to implement
        """
        fixes = []

        early_completions = self.snapshot.get("early_completions", [])

        # FIX 1: Enforce dependency checking at task creation time
        if early_completions:
            fixes.append(
                {
                    "priority": "P0 - Critical",
                    "title": "Add dependency validation BEFORE task creation",
                    "problem": (
                        "PROJECT_SUCCESS created with empty/wrong " "dependencies"
                    ),
                    "solution": (
                        "Modify task creation flow to validate dependencies "
                        "BEFORE committing tasks. Add validation that "
                        "ensures 'final' tasks depend on ALL implementation "
                        "tasks."
                    ),
                    "files_to_modify": [
                        "src/integrations/documentation_tasks.py",
                        (
                            "src/integrations/nlp_tools.py (or wherever "
                            "create_tasks_on_board is called)"
                        ),
                    ],
                    "specific_changes": [
                        {
                            "file": ("src/integrations/documentation_tasks.py:89"),
                            "change": (
                                "Add assertion: if len(dependencies) == 0 "
                                "and len(implementation_tasks) > 0: raise "
                                "ValueError('PROJECT_SUCCESS must depend on "
                                "implementation tasks')"
                            ),
                        },
                        {
                            "file": "src/integrations/nlp_tools.py",
                            "change": (
                                "Call DocumentationTaskGenerator."
                                "create_documentation_task() AFTER all other "
                                "tasks are created and have IDs assigned. "
                                "Currently might be called too early in the "
                                "flow."
                            ),
                        },
                    ],
                    "test_validation": (
                        "Add test: create project with implementation "
                        "tasks, verify PROJECT_SUCCESS has dependencies == "
                        "[all_impl_task_ids]"
                    ),
                    "estimated_time": "2-4 hours",
                }
            )

        # FIX 2: Add gatekeeper validation layer
        fixes.append(
            {
                "priority": "P0 - Critical",
                "title": "Add pre-commit validation for task graphs",
                "problem": "Tasks committed to Kanban without validation",
                "solution": (
                    "Create TaskGraphValidator that checks BEFORE pushing "
                    "to Kanban: (1) No circular dependencies, (2) Final "
                    "tasks depend on implementation tasks, (3) No orphaned "
                    "dependencies"
                ),
                "files_to_modify": [
                    "src/core/task_graph_validator.py (new file)",
                    (
                        "src/integrations/kanban_factory.py or wherever "
                        "tasks are pushed"
                    ),
                ],
                "specific_changes": [
                    {
                        "file": ("src/core/task_graph_validator.py (CREATE THIS)"),
                        "change": (
                            "class TaskGraphValidator:\\n"
                            "    @staticmethod\\n"
                            "    def validate_before_commit(tasks: "
                            "List[Task]) -> ValidationResult:\\n"
                            "        # Check 1: Circular dependencies\\n"
                            "        # Check 2: Final task dependencies\\n"
                            "        # Check 3: Orphaned references\\n"
                            "        # RAISE exception if invalid, don't "
                            "just log"
                        ),
                    },
                    {
                        "file": "Wherever tasks are pushed to Kanban",
                        "change": (
                            "Before kanban_client.create_tasks(tasks):\\n"
                            "    validation = TaskGraphValidator."
                            "validate_before_commit(tasks)\\n"
                            "    if not validation.is_valid:\\n"
                            "        raise TaskGraphInvalidError("
                            "validation.errors)"
                        ),
                    },
                ],
                "test_validation": (
                    "Add tests that try to create invalid graphs and "
                    "verify they are REJECTED"
                ),
                "estimated_time": "4-6 hours",
            }
        )

        # FIX 3: Fix task ordering to respect dependency depth
        diag = self.snapshot.get("diagnostic_report", {})
        has_bottleneck = any(
            issue.get("type") == "bottleneck" for issue in diag.get("issues", [])
        )
        if has_bottleneck:
            fixes.append(
                {
                    "priority": "P1 - High",
                    "title": "Fix task assignment to block on dependencies",
                    "problem": ("Tasks assigned even when dependencies incomplete"),
                    "solution": (
                        "Modify find_optimal_task() to strictly filter out "
                        "tasks with ANY incomplete dependencies. Don't rely "
                        "on priority alone - check dependency status."
                    ),
                    "files_to_modify": [
                        "src/core/task.py (find_optimal_task function)"
                    ],
                    "specific_changes": [
                        {
                            "file": "src/core/task.py:find_optimal_task",
                            "change": (
                                "Add explicit check:\\n"
                                "available_tasks = [t for t in tasks if "
                                "t.status == TODO and all(dep_task.status "
                                "== DONE for dep_task in "
                                "get_dependencies(t))]"
                            ),
                        }
                    ],
                    "test_validation": (
                        "Test: Create task B depending on task A "
                        "(incomplete). Verify find_optimal_task() returns "
                        "None for B."
                    ),
                    "estimated_time": "2-3 hours",
                }
            )

        return fixes

    def _generate_prevention_strategies(self) -> List[Dict[str, Any]]:
        """
        Generate long-term prevention strategies.

        Returns
        -------
        List[Dict[str, Any]]
            Prevention strategies for future
        """
        strategies = []

        strategies.append(
            {
                "category": "Architecture",
                "strategy": ("Implement invariant checking at system boundaries"),
                "description": (
                    "Add invariant validators at every point where "
                    "external data enters Marcus: NLP parsing, task "
                    "creation, Kanban sync. These validators should FAIL "
                    "FAST rather than log warnings."
                ),
                "benefits": [
                    "Catch bugs at creation time, not runtime",
                    "Impossible to commit invalid states to database",
                    "Clear error messages point to exact cause",
                ],
                "implementation": (
                    "1. Define TaskGraphInvariants class with validation "
                    "methods\\n"
                    "2. Wrap all task creation paths with validators\\n"
                    "3. Convert logging.warning() to raise exceptions\\n"
                    "4. Add comprehensive test suite for invalid inputs"
                ),
            }
        )

        strategies.append(
            {
                "category": "Testing",
                "strategy": ("Add integration tests for complete project lifecycles"),
                "description": (
                    "Current tests likely test individual components. Add "
                    "end-to-end tests that: (1) Create project via NLP, "
                    "(2) Verify task graph is valid, (3) Simulate agent "
                    "assignment, (4) Verify tasks complete in correct order."
                ),
                "benefits": [
                    "Catch ordering bugs before production",
                    "Document expected behavior clearly",
                    "Prevent regressions",
                ],
                "implementation": (
                    "tests/integration/e2e/test_project_lifecycle.py:\\n"
                    "  - test_project_success_task_is_last()\\n"
                    "  - test_no_circular_dependencies_in_generated_"
                    "projects()\\n"
                    "  - test_task_assignment_respects_dependencies()"
                ),
            }
        )

        strategies.append(
            {
                "category": "Monitoring",
                "strategy": "Add real-time validation hooks in production",
                "description": (
                    "Run diagnostic checks automatically after every N "
                    "task operations. Alert immediately if problems "
                    "detected rather than waiting for manual diagnosis."
                ),
                "benefits": [
                    "Catch problems within minutes, not hours/days",
                    "Automated alerts to humans",
                    "Historical data for pattern analysis",
                ],
                "implementation": (
                    "Add periodic task in server.py that runs "
                    "diagnose_project() every 10 minutes, logs results to "
                    "monitoring system, sends alerts on critical issues"
                ),
            }
        )

        return strategies


def analyze_why(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze WHY a stall happened, not just what happened.

    Parameters
    ----------
    snapshot : Dict[str, Any]
        Complete stall snapshot

    Returns
    -------
    Dict[str, Any]
        Causal analysis with root causes, chains, and narrative
    """
    analyzer = CausalAnalyzer(snapshot)
    return analyzer.analyze()
