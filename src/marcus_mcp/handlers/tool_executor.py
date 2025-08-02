"""
MCP Tool Executor.

This module handles the execution of MCP tool calls by routing them to the
appropriate tool functions.
"""

import json
import time
from typing import Any, Dict, List, Optional

import mcp.types as types

from ..audit import get_audit_logger
from ..tools import (  # Agent tools; Task tools; Project tools; System tools; NLP tools
    add_feature,
    check_assignment_health,
    create_project,
    get_agent_status,
    get_project_status,
    get_task_context,
    list_registered_agents,
    log_artifact,
    ping,
    register_agent,
    report_blocker,
    report_task_progress,
    request_next_task,
)
from ..tools.analytics import (  # Analytics tools
    get_agent_metrics,
    get_project_metrics,
    get_system_metrics,
    get_task_metrics,
)
from ..tools.audit_tools import (
    get_usage_report,
)
from ..tools.auth import (
    authenticate,
    get_client_tools,
)
from ..tools.board_health import (  # Board health tools
    check_board_health,
    check_task_dependencies,
)
from ..tools.code_metrics import (  # Code metrics tools
    get_code_metrics,
    get_code_quality_metrics,
    get_code_review_metrics,
    get_repository_metrics,
)
from ..tools.context import (  # Context tools
    log_decision,
)
from ..tools.pipeline import (  # Pipeline tools
    compare_pipelines,
    compare_what_if_scenarios,
    find_similar_flows,
    generate_report,
    get_live_dashboard,
    get_recommendations,
    predict_failure_risk,
    replay_jump_to,
    replay_step_backward,
    replay_step_forward,
    simulate_modification,
    start_replay,
    start_what_if_analysis,
    track_flow_progress,
)
from ..tools.predictions import (  # Prediction tools
    get_task_assignment_score,
    predict_blockage_probability,
    predict_cascade_effects,
    predict_completion_time,
    predict_task_outcome,
)
from ..tools.project_management import (  # Project management tools
    add_project,
    get_current_project,
    list_projects,
    remove_project,
    switch_project,
    update_project,
)


async def handle_tool_call(
    name: str, arguments: Optional[Dict[str, Any]], state: Any
) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool calls by routing to appropriate tool functions.

    Args:
        name: Name of the tool to call
        arguments: Tool arguments
        state: Marcus server state instance

    Returns
    -------
        List of MCP content objects with tool results
    """
    if arguments is None:
        arguments = {}

    # Track timing
    start_time = time.time()

    # Get client info if available
    client_id = None
    client_type = None
    if hasattr(state, "_current_client_id"):
        client_id = state._current_client_id
    if hasattr(state, "_registered_clients") and client_id:
        client_info = state._registered_clients.get(client_id, {})
        client_type = client_info.get("client_type")

    # Get audit logger
    audit_logger = get_audit_logger()

    # Check access control
    allowed_tools = get_client_tools(client_id, state)
    if name not in allowed_tools and "*" not in allowed_tools:
        # Audit access denied
        await audit_logger.log_access_denied(
            client_id=client_id,
            client_type=client_type,
            tool_name=name,
            reason=f"Tool '{name}' not allowed for client type '{client_type or 'unregistered'}'",
        )

        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Access denied: Tool '{name}' not available for your client type",
                        "client_type": client_type or "unregistered",
                        "allowed_tools": allowed_tools,
                    },
                    indent=2,
                ),
            )
        ]

    try:
        # Initialize result variable with proper type
        result: Any = None

        # Authentication tools (special handling)
        if name == "authenticate":
            result = await authenticate(
                client_id=arguments.get("client_id"),
                client_type=arguments.get("client_type"),
                role=arguments.get("role"),
                metadata=arguments.get("metadata"),
                state=state,
            )
            # Client has been registered, update tracking
            client_id = arguments.get("client_id")
            client_type = arguments.get("client_type")

        # Agent management tools
        elif name == "register_agent":
            agent_id = arguments.get("agent_id") if arguments else None
            agent_name = arguments.get("name") if arguments else None
            role = arguments.get("role") if arguments else None

            if not agent_id or not agent_name or not role:
                result = {"error": "agent_id, name, and role are required"}
            else:
                result = await register_agent(
                    agent_id=agent_id,
                    name=agent_name,
                    role=role,
                    skills=arguments.get("skills", []),
                    state=state,
                )

        elif name == "get_agent_status":
            agent_id = arguments.get("agent_id") if arguments else None
            if not agent_id:
                result = {"error": "agent_id is required"}
            else:
                result = await get_agent_status(agent_id=agent_id, state=state)

        elif name == "list_registered_agents":
            result = await list_registered_agents(state=state)

        # Task management tools
        elif name == "request_next_task":
            agent_id = arguments.get("agent_id") if arguments else None
            if not agent_id:
                result = {"error": "agent_id is required"}
            else:
                result = await request_next_task(agent_id=agent_id, state=state)

        elif name == "report_task_progress":
            agent_id = arguments.get("agent_id") if arguments else None
            task_id = arguments.get("task_id") if arguments else None
            status = arguments.get("status") if arguments else None

            if not agent_id or not task_id or not status:
                result = {"error": "agent_id, task_id, and status are required"}
            else:
                result = await report_task_progress(
                    agent_id=agent_id,
                    task_id=task_id,
                    status=status,
                    progress=arguments.get("progress", 0),
                    message=arguments.get("message", ""),
                    state=state,
                )

        elif name == "report_blocker":
            agent_id = arguments.get("agent_id") if arguments else None
            task_id = arguments.get("task_id") if arguments else None
            blocker_description = (
                arguments.get("blocker_description") if arguments else None
            )

            if not agent_id or not task_id or not blocker_description:
                result = {
                    "error": "agent_id, task_id, and blocker_description are required"
                }
            else:
                result = await report_blocker(
                    agent_id=agent_id,
                    task_id=task_id,
                    blocker_description=blocker_description,
                    severity=arguments.get("severity", "medium"),
                    state=state,
                )

        # Project monitoring tools
        elif name == "get_project_status":
            result = await get_project_status(state=state)

        # System health tools
        elif name == "ping":
            result = await ping(echo=arguments.get("echo", ""), state=state)

        elif name == "check_assignment_health":
            result = await check_assignment_health(state=state)

        elif name == "get_usage_report":
            days = arguments.get("days", 7) if arguments else 7
            result = await get_usage_report(days=days, state=state)

        elif name == "check_board_health":
            result = await check_board_health(state=state)

        elif name == "check_task_dependencies":
            task_id = arguments.get("task_id") if arguments else None
            if not task_id:
                result = {"error": "task_id is required"}
            else:
                result = await check_task_dependencies(task_id=task_id, state=state)

        # Natural language tools
        elif name == "create_project":
            # Log tool call start
            state.log_event(
                "mcp_tool_call_start",
                {
                    "tool": "create_project",
                    "project_name": arguments.get("project_name", "unknown"),
                },
            )

            description = arguments.get("description") if arguments else None
            project_name = arguments.get("project_name") if arguments else None

            if not description or not project_name:
                result = {"error": "description and project_name are required"}
            else:
                result = await create_project(
                    description=description,
                    project_name=project_name,
                    options=arguments.get("options"),
                    state=state,
                )

            # Log tool call complete
            state.log_event(
                "mcp_tool_call_complete",
                {
                    "tool": "create_project",
                    "project_name": arguments.get("project_name", "unknown"),
                    "success": (
                        result.get("success", False)
                        if isinstance(result, dict)
                        else False
                    ),
                },
            )

        elif name == "add_feature":
            feature_description = (
                arguments.get("feature_description") if arguments else None
            )

            if not feature_description:
                result = {"error": "feature_description is required"}
            else:
                result = await add_feature(
                    feature_description=feature_description,
                    integration_point=arguments.get("integration_point", "auto_detect"),
                    state=state,
                )

        # Context Tools
        elif name == "log_decision":
            agent_id = arguments.get("agent_id") if arguments else None
            task_id = arguments.get("task_id") if arguments else None
            decision = arguments.get("decision") if arguments else None

            if not agent_id or not task_id or not decision:
                result = {"error": "agent_id, task_id, and decision are required"}
            else:
                result = await log_decision(
                    agent_id=agent_id,
                    task_id=task_id,
                    decision=decision,
                    state=state,
                )

        elif name == "get_task_context":
            task_id = arguments.get("task_id") if arguments else None

            if not task_id:
                result = {"error": "task_id is required"}
            else:
                result = await get_task_context(task_id=task_id, state=state)

        elif name == "log_artifact":
            task_id = arguments.get("task_id") if arguments else None
            filename = arguments.get("filename") if arguments else None
            content = arguments.get("content") if arguments else None
            artifact_type = arguments.get("artifact_type") if arguments else None

            if not task_id or not filename or not content or not artifact_type:
                result = {
                    "error": "task_id, filename, content, and artifact_type are required"
                }
            else:
                result = await log_artifact(
                    task_id=task_id,
                    filename=filename,
                    content=content,
                    artifact_type=artifact_type,
                    description=arguments.get("description", ""),
                    location=arguments.get("location"),  # Optional override
                    state=state,
                )

        # Project Management Tools
        elif name == "list_projects":
            result = await list_projects(state, arguments)
        elif name == "switch_project":
            result = await switch_project(state, arguments)
        elif name == "get_current_project":
            result = await get_current_project(state, arguments)
        elif name == "add_project":
            result = await add_project(state, arguments)
        elif name == "remove_project":
            result = await remove_project(state, arguments)
        elif name == "update_project":
            result = await update_project(state, arguments)

        # Pipeline Enhancement Tools
        elif name == "pipeline_replay_start":
            result = await start_replay(state, arguments)

        elif name == "pipeline_replay_forward":
            result = await replay_step_forward(state, arguments)

        elif name == "pipeline_replay_backward":
            result = await replay_step_backward(state, arguments)

        elif name == "pipeline_replay_jump":
            result = await replay_jump_to(state, arguments)

        elif name == "what_if_start":
            result = await start_what_if_analysis(state, arguments)

        elif name == "what_if_simulate":
            result = await simulate_modification(state, arguments)

        elif name == "what_if_compare":
            result = await compare_what_if_scenarios(state, arguments)

        elif name == "pipeline_compare":
            result = await compare_pipelines(state, arguments)

        elif name == "pipeline_report":
            result = await generate_report(state, arguments)

        elif name == "pipeline_monitor_dashboard":
            result = await get_live_dashboard(state, arguments)

        elif name == "pipeline_monitor_flow":
            result = await track_flow_progress(state, arguments)

        elif name == "pipeline_predict_risk":
            result = await predict_failure_risk(state, arguments)

        elif name == "pipeline_recommendations":
            result = await get_recommendations(state, arguments)

        elif name == "pipeline_find_similar":
            result = await find_similar_flows(state, arguments)

        # Prediction and AI intelligence tools
        elif name == "predict_completion_time":
            result = await predict_completion_time(
                project_id=arguments.get("project_id"),
                include_confidence=arguments.get("include_confidence", True),
                state=state,
            )

        elif name == "predict_task_outcome":
            task_id = arguments.get("task_id") if arguments else None
            if not task_id:
                result = {"error": "task_id is required"}
            else:
                result = await predict_task_outcome(
                    task_id=task_id,
                    agent_id=arguments.get("agent_id"),
                    state=state,
                )

        elif name == "predict_blockage_probability":
            task_id = arguments.get("task_id") if arguments else None
            if not task_id:
                result = {"error": "task_id is required"}
            else:
                result = await predict_blockage_probability(
                    task_id=task_id,
                    include_mitigation=arguments.get("include_mitigation", True),
                    state=state,
                )

        elif name == "predict_cascade_effects":
            task_id = arguments.get("task_id") if arguments else None
            if not task_id:
                result = {"error": "task_id is required"}
            else:
                result = await predict_cascade_effects(
                    task_id=task_id,
                    delay_days=arguments.get("delay_days", 1),
                    state=state,
                )

        elif name == "get_task_assignment_score":
            task_id = arguments.get("task_id") if arguments else None
            agent_id = arguments.get("agent_id") if arguments else None
            if not task_id or not agent_id:
                result = {"error": "task_id and agent_id are required"}
            else:
                result = await get_task_assignment_score(
                    task_id=task_id,
                    agent_id=agent_id,
                    state=state,
                )

        # Analytics and metrics tools
        elif name == "get_system_metrics":
            result = await get_system_metrics(
                time_window=arguments.get("time_window", "1h"),
                state=state,
            )

        elif name == "get_agent_metrics":
            agent_id = arguments.get("agent_id") if arguments else None
            if not agent_id:
                result = {"error": "agent_id is required"}
            else:
                result = await get_agent_metrics(
                    agent_id=agent_id,
                    time_window=arguments.get("time_window", "7d"),
                    state=state,
                )

        elif name == "get_project_metrics":
            result = await get_project_metrics(
                project_id=arguments.get("project_id"),
                time_window=arguments.get("time_window", "7d"),
                state=state,
            )

        elif name == "get_task_metrics":
            result = await get_task_metrics(
                time_window=arguments.get("time_window", "30d"),
                group_by=arguments.get("group_by", "status"),
                state=state,
            )

        # Code production metrics tools
        elif name == "get_code_metrics":
            agent_id = arguments.get("agent_id") if arguments else None
            if not agent_id:
                result = {"error": "agent_id is required"}
            else:
                result = await get_code_metrics(
                    agent_id=agent_id,
                    start_date=arguments.get("start_date"),
                    end_date=arguments.get("end_date"),
                    state=state,
                )

        elif name == "get_repository_metrics":
            repository = arguments.get("repository") if arguments else None
            if not repository:
                result = {"error": "repository is required"}
            else:
                result = await get_repository_metrics(
                    repository=repository,
                    time_window=arguments.get("time_window", "7d"),
                    state=state,
                )

        elif name == "get_code_review_metrics":
            result = await get_code_review_metrics(
                agent_id=arguments.get("agent_id"),
                time_window=arguments.get("time_window", "7d"),
                state=state,
            )

        elif name == "get_code_quality_metrics":
            repository = arguments.get("repository") if arguments else None
            if not repository:
                result = {"error": "repository is required"}
            else:
                result = await get_code_quality_metrics(
                    repository=repository,
                    branch=arguments.get("branch", "main"),
                    state=state,
                )

        # Pattern Learning Tools removed - only accessible via visualization UI API
        elif name in [
            "get_similar_projects",
            "get_project_patterns",
            "assess_project_quality",
            "get_pattern_recommendations",
            "learn_from_completed_project",
            "get_quality_trends",
        ]:
            result = {
                "error": (
                    f"Pattern learning tool '{name}' is not available through MCP. "
                    "Please use the visualization UI API endpoints instead."
                ),
                "suggestion": (
                    "Pattern learning tools are now only accessible through "
                    "the web UI at http://localhost:8080"
                ),
            }

        else:
            result = {"error": f"Unknown tool: {name}"}

        # Log response creation
        state.log_event(
            "mcp_creating_response",
            {
                "tool": name,
                "has_result": result is not None,
                "result_type": type(result).__name__ if result else "None",
            },
        )

        response: List[
            types.TextContent | types.ImageContent | types.EmbeddedResource
        ] = [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        # Ensure stdio buffer is flushed for immediate response delivery
        import sys

        sys.stdout.flush()
        sys.stderr.flush()

        # Log response return
        state.log_event(
            "mcp_returning_response",
            {
                "tool": name,
                "response_length": (
                    len(response[0].text)
                    if response and isinstance(response[0], types.TextContent)
                    else 0
                ),
            },
        )

        # Audit successful tool call
        duration_ms = (time.time() - start_time) * 1000
        await audit_logger.log_tool_call(
            client_id=client_id,
            client_type=client_type,
            tool_name=name,
            arguments=arguments,
            result=result,
            duration_ms=duration_ms,
            success=True,
        )

        return response

    except Exception as e:
        # Audit failed tool call
        duration_ms = (time.time() - start_time) * 1000
        await audit_logger.log_tool_call(
            client_id=client_id,
            client_type=client_type,
            tool_name=name,
            arguments=arguments,
            result=None,
            duration_ms=duration_ms,
            success=False,
            error=str(e),
        )

        error_response: List[
            types.TextContent | types.ImageContent | types.EmbeddedResource
        ] = [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {"error": f"Tool execution failed: {str(e)}", "tool": name},
                    indent=2,
                ),
            )
        ]

        # Ensure stdio buffer is flushed for immediate error delivery
        import sys

        sys.stdout.flush()
        sys.stderr.flush()

        return error_response
