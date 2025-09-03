"""
Project Workflow Manager.

Orchestrates the workflow from project creation to task assignment and execution
using Marcus MCP.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from src.marcus_mcp.client import SimpleMarcusClient
from src.visualization.pipeline_manager import PipelineFlowManager


class ProjectWorkflowManager:
    """Manages the complete workflow from project to execution using Marcus MCP."""

    def __init__(
        self, marcus_client: SimpleMarcusClient, flow_manager: PipelineFlowManager
    ):
        self.marcus_client = marcus_client
        self.flow_manager = flow_manager
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.agent_assignments: Dict[str, Dict[str, Any]] = {}

    async def start_project_workflow(
        self, project_id: str, flow_id: str, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Start the workflow for a project."""
        workflow_id = str(uuid.uuid4())

        workflow = {
            "id": workflow_id,
            "project_id": project_id,
            "flow_id": flow_id,
            "status": "running",
            "options": options,
            "started_at": datetime.now().isoformat(),
            "assigned_agents": [],
            "task_queue": [],
        }

        self.active_workflows[workflow_id] = workflow

        # Start workflow tasks
        if options.get("auto_assign"):
            asyncio.create_task(self._auto_assign_loop(workflow_id))

        if options.get("continuous_monitoring"):
            asyncio.create_task(self._monitor_workflow(workflow_id))

        # Add workflow event
        self.flow_manager.visualizer.add_event(
            flow_id,
            "workflow_initialized",
            data={
                "type": "workflow_initialized",
                "workflow_id": workflow_id,
                "options": options,
                "timestamp": datetime.now().isoformat(),
            },
        )

        return {"workflow_id": workflow_id, "status": "started"}

    async def _auto_assign_loop(self, workflow_id: str) -> None:
        """Auto-assign tasks to available agents using Marcus MCP."""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return

        while workflow["status"] == "running":
            try:
                # Get project status from Marcus
                project_status = await self.marcus_client.call_tool(
                    "get_project_status", {}
                )

                if project_status and "unassigned_tasks" in project_status:
                    unassigned_count = project_status.get("unassigned_tasks", 0)

                    if unassigned_count > 0:
                        # Get list of registered agents
                        agents_result = await self.marcus_client.call_tool(
                            "list_registered_agents", {}
                        )

                        if agents_result and "agents" in agents_result:
                            idle_agents = [
                                agent
                                for agent in agents_result["agents"]
                                if agent.get("status") == "idle"
                            ]

                            # Assign tasks to idle agents up to max_agents limit
                            max_agents = workflow["options"].get("max_agents", 3)
                            agents_to_use = idle_agents[
                                : min(max_agents, len(idle_agents))
                            ]

                            for agent in agents_to_use:
                                # Request task for this agent
                                task_result = await self.marcus_client.call_tool(
                                    "request_next_task", {"agent_id": agent["agent_id"]}
                                )

                                if task_result and "task" in task_result:
                                    task = task_result["task"]

                                    # Track assignment
                                    assignment = {
                                        "task_id": task["id"],
                                        "task_name": task["name"],
                                        "agent_id": agent["agent_id"],
                                        "agent_name": agent["name"],
                                        "assigned_at": datetime.now().isoformat(),
                                    }

                                    workflow["task_queue"].append(assignment)

                                    # Add assignment event
                                    self.flow_manager.visualizer.add_event(
                                        workflow["flow_id"],
                                        "task_assigned",
                                        data={
                                            "type": "task_assigned",
                                            "task_id": task["id"],
                                            "task_name": task["name"],
                                            "agent_id": agent["agent_id"],
                                            "agent_name": agent["name"],
                                            "timestamp": datetime.now().isoformat(),
                                        },
                                    )

                # Wait before next assignment check
                await asyncio.sleep(10)

            except Exception as e:
                import sys

                print(f"Error in auto-assign loop: {e}", file=sys.stderr)
                await asyncio.sleep(30)

    async def _monitor_workflow(self, workflow_id: str) -> None:
        """Monitor workflow progress using Marcus MCP."""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return

        while workflow["status"] == "running":
            try:
                # Get project status from Marcus
                project_status = await self.marcus_client.call_tool(
                    "get_project_status", {}
                )

                if project_status and "project_state" in project_status:
                    state = project_status["project_state"]

                    # Calculate metrics
                    metrics = {
                        "total_tasks": state.get("total_tasks", 0),
                        "completed_tasks": state.get("completed_tasks", 0),
                        "in_progress_tasks": state.get("in_progress_tasks", 0),
                        "blocked_tasks": state.get("blocked_tasks", 0),
                        "progress_percent": state.get("progress_percent", 0),
                    }

                    # Add monitoring event
                    self.flow_manager.visualizer.add_event(
                        workflow["flow_id"],
                        "workflow_metrics",
                        data={
                            "type": "workflow_metrics",
                            "metrics": metrics,
                            "timestamp": datetime.now().isoformat(),
                        },
                    )

                    # Check if workflow is complete
                    if metrics["progress_percent"] >= 100:
                        workflow["status"] = "completed"
                        self.flow_manager.visualizer.add_event(
                            workflow["flow_id"],
                            "workflow_completed",
                            data={
                                "type": "workflow_completed",
                                "timestamp": datetime.now().isoformat(),
                            },
                        )

                # Wait before next check
                await asyncio.sleep(30)

            except Exception as e:
                import sys

                print(f"Error in workflow monitoring: {e}", file=sys.stderr)
                await asyncio.sleep(60)

    def pause_workflow(self, workflow_id: str) -> bool:
        """Pause a workflow."""
        if workflow_id in self.active_workflows:
            self.active_workflows[workflow_id]["status"] = "paused"
            return True
        return False

    def stop_workflow(self, workflow_id: str) -> bool:
        """Stop a workflow."""
        if workflow_id in self.active_workflows:
            self.active_workflows[workflow_id]["status"] = "stopped"
            return True
        return False

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow status."""
        return self.active_workflows.get(workflow_id)
