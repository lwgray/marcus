"""
Causal analysis engine for understanding WHY project stalls happen.

Analyzes snapshot data to build causal chains explaining root causes.
"""

from typing import Any, Dict, List, Tuple


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
                        "explanation": "Tasks form a cycle where each depends on another, "
                        "making it impossible to complete any of them.",
                        "why": "Someone created dependencies that loop back on themselves. "
                        "This is a design error in task planning.",
                        "affected_tasks": issue.get("affected_count", 0),
                        "impact": "All tasks in the cycle are permanently blocked",
                    }
                )

            elif issue.get("type") == "bottleneck":
                root_causes.append(
                    {
                        "type": "critical_bottleneck",
                        "severity": "high",
                        "explanation": f"One task is blocking multiple others ({issue.get('affected_count', 0)} tasks)",
                        "why": "Task dependencies were modeled sequentially instead of in parallel. "
                        "Work that could happen concurrently is forced to wait.",
                        "affected_tasks": issue.get("affected_count", 0),
                        "impact": "Development velocity is severely limited",
                    }
                )

            elif issue.get("type") == "missing_dependency":
                root_causes.append(
                    {
                        "type": "missing_task",
                        "severity": "high",
                        "explanation": "Tasks reference dependencies that don't exist",
                        "why": "Either: (1) A task was deleted without updating dependents, "
                        "or (2) Task IDs were entered incorrectly during creation",
                        "affected_tasks": issue.get("affected_count", 0),
                        "impact": "Affected tasks can never be started",
                    }
                )

        # Analyze early completions
        early_completions = self.snapshot.get("early_completions", [])
        if early_completions:
            task_names = [ec.get("task_name") for ec in early_completions]
            root_causes.append(
                {
                    "type": "premature_completion",
                    "severity": "high",
                    "explanation": f"Critical tasks completed too early: {', '.join(task_names[:3])}",
                    "why": "Tasks were marked complete without dependencies being set correctly. "
                    "This suggests: (1) Dependencies weren't modeled, (2) Someone manually "
                    "marked tasks done, or (3) An agent completed tasks out of order.",
                    "affected_tasks": len(early_completions),
                    "impact": "Project appears complete but critical work is actually undone",
                }
            )

        # Analyze conversation patterns
        conversation = self.snapshot.get("conversation_history", [])

        # Count repeated "no task" requests
        no_task_events = [
            e for e in conversation if "no_task" in e.get("type", "").lower()
        ]
        if len(no_task_events) >= 5:
            root_causes.append(
                {
                    "type": "assignment_deadlock",
                    "severity": "critical",
                    "explanation": f"Agents requested tasks {len(no_task_events)} times but none were available",
                    "why": "All available tasks are blocked by dependencies. This is usually caused "
                    "by circular dependencies or missing tasks that were supposed to unlock work.",
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
                            "explanation": f"Task {task_id} failed {count} times in a row",
                            "why": "The task has a fundamental problem: unclear requirements, "
                            "missing dependencies, or technical blockers. The agent is stuck "
                            "retrying the same approach that doesn't work.",
                            "affected_tasks": 1,
                            "impact": "Agent resources wasted, no forward progress on this task",
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

        # Example chain: Circular dependency → All tasks blocked → No work possible
        root_causes = self._find_root_causes()

        for cause in root_causes:
            if cause["type"] == "circular_dependency":
                chains.append(
                    {
                        "root_cause": "Circular dependency created in task planning",
                        "chain": [
                            {
                                "step": 1,
                                "event": "Tasks A, B, C created with circular dependencies",
                                "why": "Task planner didn't validate dependency graph",
                            },
                            {
                                "step": 2,
                                "event": "All three tasks marked as TODO but blocked",
                                "why": "Each task waiting for another to complete first",
                            },
                            {
                                "step": 3,
                                "event": "Agents request tasks, get 'no tasks available'",
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
                chains.append(
                    {
                        "root_cause": "Final tasks completed before prerequisites",
                        "chain": [
                            {
                                "step": 1,
                                "event": f"{cause.get('affected_tasks', 1)} critical tasks completed early",
                                "why": "Dependencies not modeled or manually overridden",
                            },
                            {
                                "step": 2,
                                "event": "Remaining tasks appear blocked",
                                "why": "They depend on work that should have come after 'completion' tasks",
                            },
                            {
                                "step": 3,
                                "event": "Project shows as mostly complete but work remains",
                                "why": "Completion metrics don't reflect actual progress",
                            },
                            {
                                "step": 4,
                                "event": "Confusion about project state",
                                "why": "Dashboard shows success but agents report blockers",
                            },
                        ],
                        "final_impact": cause["impact"],
                    }
                )

            elif cause["type"] == "assignment_deadlock":
                chains.append(
                    {
                        "root_cause": "All available work paths blocked",
                        "chain": [
                            {
                                "step": 1,
                                "event": "Task dependencies create a blocking pattern",
                                "why": "No task exists that can be started independently",
                            },
                            {
                                "step": 2,
                                "event": "Agents repeatedly request work",
                                "why": "They're ready to work but nothing is available",
                            },
                            {
                                "step": 3,
                                "event": f"{len([e for e in self.snapshot.get('conversation_history', []) if 'no_task' in e.get('type', '').lower()])} failed assignment attempts",
                                "why": "System keeps trying but conditions never change",
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
        early_completions = self.snapshot.get("early_completions", [])

        # Check timeline for early signs
        if len(timeline) >= 3:
            # If "success" task completed before 80% of tasks
            for i, completed in enumerate(timeline):
                task_name = completed.get("task_name", "").lower()
                if any(
                    keyword in task_name
                    for keyword in ["success", "complete", "done", "deploy"]
                ):
                    completion_pct = ((i + 1) / len(timeline)) * 100
                    if completion_pct < 80:
                        interventions.append(
                            {
                                "timing": "Early in project",
                                "trigger": f"'{completed.get('task_name')}' completed at {completion_pct:.0f}%",
                                "action": "Review task dependencies before marking final tasks complete",
                                "prevention": "Would have caught missing dependencies before they blocked work",
                                "window": "Before task was marked complete",
                            }
                        )

        # Check for dependency issues
        diag_issues = self.snapshot.get("diagnostic_report", {}).get("issues", [])
        for issue in diag_issues:
            if issue.get("type") == "circular_dependency":
                interventions.append(
                    {
                        "timing": "During task creation",
                        "trigger": "Circular dependency introduced",
                        "action": "Validate dependency graph when tasks are created",
                        "prevention": "Automated validation would reject circular dependencies",
                        "window": "At task creation time",
                    }
                )

        # Check conversation for warning signs
        conversation = self.snapshot.get("conversation_history", [])
        no_task_count = len(
            [e for e in conversation if "no_task" in e.get("type", "").lower()]
        )

        if no_task_count >= 3:
            interventions.append(
                {
                    "timing": "After 3rd failed task request",
                    "trigger": f"Agent requested tasks {no_task_count} times with no success",
                    "action": "Automatically run diagnostics after N failed requests",
                    "prevention": "Would have identified blocking issues before complete stall",
                    "window": "After 3 failed requests (before it became critical)",
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
            decisions.append(
                {
                    "decision": "Marked final tasks as complete prematurely",
                    "when": "Early in project lifecycle",
                    "impact": f"{len(early_completions)} critical tasks completed out of order",
                    "why_problematic": "Broke the dependency chain, making other tasks appear blocked",
                    "alternative": "Wait until dependencies are complete, or restructure task graph",
                    "severity": "high",
                }
            )

        # Analyze task creation decisions
        diag_issues = self.snapshot.get("diagnostic_report", {}).get("issues", [])
        for issue in diag_issues:
            if issue.get("type") == "circular_dependency":
                decisions.append(
                    {
                        "decision": "Created circular task dependencies",
                        "when": "During project planning",
                        "impact": f"{issue.get('affected_count', 0)} tasks permanently blocked",
                        "why_problematic": "Makes it logically impossible to complete any task in the cycle",
                        "alternative": "Model dependencies as DAG (Directed Acyclic Graph)",
                        "severity": "critical",
                    }
                )

            elif issue.get("type") == "bottleneck":
                decisions.append(
                    {
                        "decision": "Modeled work as sequential instead of parallel",
                        "when": "During task dependency planning",
                        "impact": f"{issue.get('affected_count', 0)} tasks forced to wait unnecessarily",
                        "why_problematic": "Limits development velocity - could be working in parallel",
                        "alternative": "Identify truly independent tasks and remove false dependencies",
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
        narrative_parts.append(
            f"Development on {project_name} has completely stalled. Here's what happened:\n"
        )

        # Root cause explanation
        if root_causes:
            narrative_parts.append("\n🔍 ROOT CAUSE ANALYSIS:\n")
            for i, cause in enumerate(root_causes[:3], 1):  # Top 3
                narrative_parts.append(
                    f"\n{i}. {cause['type'].replace('_', ' ').title()} "
                    f"(Severity: {cause['severity']})\n"
                )
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
        narrative_parts.append(
            "\n💡 BOTTOM LINE:\n"
            "This stall was preventable. The root cause was introduced during task planning, "
            "and warning signs appeared early. With better validation and monitoring, "
            "this could have been caught before it blocked all development.\n"
        )

        return "".join(narrative_parts)


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
