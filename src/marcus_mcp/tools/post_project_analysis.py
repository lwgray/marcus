"""
Post-Project Analysis tools for Marcus MCP.

This module provides MCP tools for running Phase 2 post-project analysis
on completed projects, including:
- Requirement divergence detection
- Decision impact tracing
- Instruction quality evaluation
- Failure diagnosis

Usage
-----
These tools are accessible via the Marcus MCP server to analyze
completed projects and generate insights for improvement.
"""

from typing import Any, Dict, List, Optional

from mcp.types import Tool

from ...analysis.aggregator import TaskHistory
from ...analysis.post_project_analyzer import (
    AnalysisScope,
    PostProjectAnalyzer,
)

# Tool definitions
ANALYZE_PROJECT_TOOL = Tool(
    name="analyze_project",
    description=(
        "Run comprehensive post-project analysis on a completed project. "
        "Analyzes requirement divergence, decision impacts, "
        "instruction quality, and failure diagnoses. "
        "Returns actionable insights for improvement. "
        "Use this after project completion to understand what went "
        "well and what didn't."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "ID of the project to analyze",
            },
            "scope": {
                "type": "object",
                "description": "Optional analysis scope to control which analyzers run",
                "properties": {
                    "requirement_divergence": {
                        "type": "boolean",
                        "description": (
                            "Analyze how implementation diverged " "from requirements"
                        ),
                        "default": True,
                    },
                    "decision_impact": {
                        "type": "boolean",
                        "description": (
                            "Trace how decisions cascaded through " "the project"
                        ),
                        "default": True,
                    },
                    "instruction_quality": {
                        "type": "boolean",
                        "description": (
                            "Evaluate clarity and completeness of " "task instructions"
                        ),
                        "default": True,
                    },
                    "failure_diagnosis": {
                        "type": "boolean",
                        "description": (
                            "Diagnose why tasks failed and suggest " "prevention"
                        ),
                        "default": True,
                    },
                },
            },
        },
        "required": ["project_id"],
    },
)


GET_REQUIREMENT_DIVERGENCE_TOOL = Tool(
    name="get_requirement_divergence",
    description=(
        "Analyze how much the implementation diverged from the original "
        "requirements for specific tasks. Returns fidelity scores and "
        "specific divergences found. Use this to understand where and "
        "why implementation didn't match specs."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "ID of the project containing the tasks",
            },
            "task_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Optional list of specific task IDs to analyze. "
                    "If omitted, analyzes all tasks."
                ),
            },
        },
        "required": ["project_id"],
    },
)


GET_DECISION_IMPACTS_TOOL = Tool(
    name="get_decision_impacts",
    description=(
        "Trace how architectural and technical decisions cascaded "
        "through the project. Shows direct and indirect impacts, "
        "unexpected consequences, and decision depth. Use this to "
        "understand the ripple effects of important decisions."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "ID of the project to analyze",
            },
            "decision_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Optional list of specific decision IDs to analyze. "
                    "If omitted, analyzes all decisions."
                ),
            },
        },
        "required": ["project_id"],
    },
)


GET_INSTRUCTION_QUALITY_TOOL = Tool(
    name="get_instruction_quality",
    description=(
        "Evaluate the quality of task instructions - clarity, "
        "completeness, and specificity. Identifies ambiguous requirements "
        "and correlates instruction quality with task outcomes. "
        "Use this to improve how you write task descriptions."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "ID of the project to analyze",
            },
            "task_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Optional list of specific task IDs to analyze. "
                    "If omitted, analyzes all tasks."
                ),
            },
        },
        "required": ["project_id"],
    },
)


GET_FAILURE_DIAGNOSES_TOOL = Tool(
    name="get_failure_diagnoses",
    description=(
        "Generate comprehensive diagnoses for failed tasks, explaining "
        "root causes, contributing factors, and prevention strategies. "
        "Categorizes failures as technical, requirements, process, or "
        "communication issues. Use this to learn from failures and "
        "prevent similar issues."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "ID of the project with failed tasks",
            },
            "task_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Optional list of specific failed task IDs. "
                    "If omitted, analyzes all failed tasks."
                ),
            },
        },
        "required": ["project_id"],
    },
)


async def analyze_project(
    project_id: str,
    scope: Optional[Dict[str, bool]] = None,
    state: Any = None,
) -> Dict[str, Any]:
    """
    Run comprehensive post-project analysis.

    Parameters
    ----------
    project_id : str
        ID of the project to analyze
    scope : Dict[str, bool], optional
        Which analyzers to run (requirement_divergence, decision_impact,
        instruction_quality, failure_diagnosis)
    state : Any
        Marcus server state

    Returns
    -------
    Dict[str, Any]
        Complete analysis results with:
        - requirement_divergences: list of divergence analyses
        - decision_impacts: list of impact analyses
        - instruction_quality_issues: list of quality analyses
        - failure_diagnoses: list of failure diagnoses
        - summary: executive summary text
        - metadata: analysis metadata
    """
    if not state:
        return {
            "success": False,
            "error": "Server state not available",
        }

    try:
        # Get project context
        context = state._project_contexts.get(project_id)
        if not context:
            return {
                "success": False,
                "error": f"Project {project_id} not found",
            }

        # Get project history to extract tasks and decisions
        if not hasattr(context, "project_history") or not context.project_history:
            return {
                "success": False,
                "error": f"No project history available for {project_id}",
            }

        # Convert tasks to TaskHistory format
        tasks = []
        for conversation in context.project_history.conversations:
            for task_data in conversation.tasks:
                # Extract task information
                tasks.append(
                    TaskHistory(
                        task_id=task_data.get("task_id", "unknown"),
                        name=task_data.get("name", "Unnamed task"),
                        description=task_data.get("description", ""),
                        status=task_data.get("status", "unknown"),
                        estimated_hours=task_data.get("estimated_hours", 0.0),
                        actual_hours=task_data.get("actual_hours", 0.0),
                    )
                )

        # Get all decisions
        decisions = context.project_history.get_all_decisions()

        if not tasks:
            return {
                "success": False,
                "error": f"No tasks found in project history for {project_id}",
            }

        # Create analysis scope
        analysis_scope = None
        if scope:
            analysis_scope = AnalysisScope(
                requirement_divergence=scope.get("requirement_divergence", True),
                decision_impact=scope.get("decision_impact", True),
                instruction_quality=scope.get("instruction_quality", True),
                failure_diagnosis=scope.get("failure_diagnosis", True),
            )

        # Run analysis
        analyzer = PostProjectAnalyzer()
        analysis = await analyzer.analyze_project(
            project_id=project_id,
            tasks=tasks,
            decisions=decisions,
            scope=analysis_scope,
        )

        # Format results for MCP response
        return {
            "success": True,
            "project_id": analysis.project_id,
            "analysis_timestamp": analysis.analysis_timestamp.isoformat(),
            "summary": analysis.summary,
            "requirement_divergences": [
                {
                    "task_id": div.task_id,
                    "fidelity_score": div.fidelity_score,
                    "divergences": [
                        {
                            "requirement": d.requirement,
                            "implementation": d.implementation,
                            "severity": d.severity,
                            "impact": d.impact,
                            "citation": d.citation,
                        }
                        for d in div.divergences
                    ],
                    "recommendations": div.recommendations,
                }
                for div in analysis.requirement_divergences
            ],
            "decision_impacts": [
                {
                    "decision_id": imp.decision_id,
                    "impact_chains": [
                        {
                            "decision_summary": chain.decision_summary,
                            "direct_impacts": chain.direct_impacts,
                            "indirect_impacts": chain.indirect_impacts,
                            "depth": chain.depth,
                            "citation": chain.citation,
                        }
                        for chain in imp.impact_chains
                    ],
                    "unexpected_impacts": [
                        {
                            "affected_task": ui.affected_task_name,
                            "anticipated": ui.anticipated,
                            "actual_impact": ui.actual_impact,
                            "severity": ui.severity,
                        }
                        for ui in imp.unexpected_impacts
                    ],
                    "recommendations": imp.recommendations,
                }
                for imp in analysis.decision_impacts
            ],
            "instruction_quality_issues": [
                {
                    "task_id": qual.task_id,
                    "quality_scores": {
                        "clarity": qual.quality_scores.clarity,
                        "completeness": qual.quality_scores.completeness,
                        "specificity": qual.quality_scores.specificity,
                        "overall": qual.quality_scores.overall,
                    },
                    "ambiguity_issues": [
                        {
                            "aspect": issue.ambiguous_aspect,
                            "evidence": issue.evidence,
                            "consequence": issue.consequence,
                            "severity": issue.severity,
                        }
                        for issue in qual.ambiguity_issues
                    ],
                    "recommendations": qual.recommendations,
                }
                for qual in analysis.instruction_quality_issues
            ],
            "failure_diagnoses": [
                {
                    "task_id": diag.task_id,
                    "failure_causes": [
                        {
                            "category": cause.category,
                            "root_cause": cause.root_cause,
                            "contributing_factors": cause.contributing_factors,
                            "evidence": cause.evidence,
                        }
                        for cause in diag.failure_causes
                    ],
                    "prevention_strategies": [
                        {
                            "strategy": strat.strategy,
                            "rationale": strat.rationale,
                            "effort": strat.effort,
                            "priority": strat.priority,
                        }
                        for strat in diag.prevention_strategies
                    ],
                    "lessons_learned": diag.lessons_learned,
                }
                for diag in analysis.failure_diagnoses
            ],
            "metadata": analysis.metadata,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Analysis failed: {str(e)}",
        }


async def get_requirement_divergence(
    project_id: str,
    task_ids: Optional[List[str]] = None,
    state: Any = None,
) -> Dict[str, Any]:
    """
    Analyze requirement divergence for specific tasks.

    Parameters
    ----------
    project_id : str
        ID of the project
    task_ids : List[str], optional
        Specific tasks to analyze. If None, analyzes all tasks.
    state : Any
        Marcus server state

    Returns
    -------
    Dict[str, Any]
        Requirement divergence analysis results
    """
    # Run full analysis with only requirement_divergence enabled
    scope = {
        "requirement_divergence": True,
        "decision_impact": False,
        "instruction_quality": False,
        "failure_diagnosis": False,
    }

    result = await analyze_project(project_id, scope=scope, state=state)

    # Filter to requested task_ids if specified
    if result.get("success") and task_ids:
        result["requirement_divergences"] = [
            div
            for div in result["requirement_divergences"]
            if div["task_id"] in task_ids
        ]

    return result


async def get_decision_impacts(
    project_id: str,
    decision_ids: Optional[List[str]] = None,
    state: Any = None,
) -> Dict[str, Any]:
    """
    Trace decision impacts for specific decisions.

    Parameters
    ----------
    project_id : str
        ID of the project
    decision_ids : List[str], optional
        Specific decisions to analyze. If None, analyzes all decisions.
    state : Any
        Marcus server state

    Returns
    -------
    Dict[str, Any]
        Decision impact analysis results
    """
    # Run full analysis with only decision_impact enabled
    scope = {
        "requirement_divergence": False,
        "decision_impact": True,
        "instruction_quality": False,
        "failure_diagnosis": False,
    }

    result = await analyze_project(project_id, scope=scope, state=state)

    # Filter to requested decision_ids if specified
    if result.get("success") and decision_ids:
        result["decision_impacts"] = [
            imp
            for imp in result["decision_impacts"]
            if imp["decision_id"] in decision_ids
        ]

    return result


async def get_instruction_quality(
    project_id: str,
    task_ids: Optional[List[str]] = None,
    state: Any = None,
) -> Dict[str, Any]:
    """
    Evaluate instruction quality for specific tasks.

    Parameters
    ----------
    project_id : str
        ID of the project
    task_ids : List[str], optional
        Specific tasks to analyze. If None, analyzes all tasks.
    state : Any
        Marcus server state

    Returns
    -------
    Dict[str, Any]
        Instruction quality analysis results
    """
    # Run full analysis with only instruction_quality enabled
    scope = {
        "requirement_divergence": False,
        "decision_impact": False,
        "instruction_quality": True,
        "failure_diagnosis": False,
    }

    result = await analyze_project(project_id, scope=scope, state=state)

    # Filter to requested task_ids if specified
    if result.get("success") and task_ids:
        result["instruction_quality_issues"] = [
            qual
            for qual in result["instruction_quality_issues"]
            if qual["task_id"] in task_ids
        ]

    return result


async def get_failure_diagnoses(
    project_id: str,
    task_ids: Optional[List[str]] = None,
    state: Any = None,
) -> Dict[str, Any]:
    """
    Generate failure diagnoses for failed tasks.

    Parameters
    ----------
    project_id : str
        ID of the project
    task_ids : List[str], optional
        Specific failed tasks to analyze. If None, analyzes all failed tasks.
    state : Any
        Marcus server state

    Returns
    -------
    Dict[str, Any]
        Failure diagnosis results
    """
    # Run full analysis with only failure_diagnosis enabled
    scope = {
        "requirement_divergence": False,
        "decision_impact": False,
        "instruction_quality": False,
        "failure_diagnosis": True,
    }

    result = await analyze_project(project_id, scope=scope, state=state)

    # Filter to requested task_ids if specified
    if result.get("success") and task_ids:
        result["failure_diagnoses"] = [
            diag for diag in result["failure_diagnoses"] if diag["task_id"] in task_ids
        ]

    return result
