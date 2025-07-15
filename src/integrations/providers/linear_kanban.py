"""
Linear implementation of KanbanInterface

Uses Linear MCP Server to manage tasks and projects
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.models import Priority, Task, TaskStatus
from src.integrations.kanban_interface import KanbanInterface, KanbanProvider


class LinearKanban(KanbanInterface):
    """Linear kanban board implementation using MCP Server"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Linear MCP connection

        Args:
            config: Dictionary containing:
                - mcp_function_caller: Function to call MCP tools
                - team_id: Linear team ID
                - project_id: Optional Linear project ID
        """
        super().__init__(config)
        self.provider = KanbanProvider.LINEAR
        self.mcp_caller = config.get("mcp_function_caller")
        self.team_id = config.get("team_id")
        self.project_id = config.get("project_id")

        if not self.mcp_caller:
            raise ValueError(
                "mcp_function_caller is required for Linear MCP integration"
            )

    async def connect(self) -> bool:
        """Connect to Linear MCP Server"""
        try:
            # Test connection by getting teams
            result = await self.mcp_caller("linear.get_teams", {})
            return result.get("success", False)
        except Exception as e:
            print(f"Failed to connect to Linear MCP: {e}")
            return False

    async def disconnect(self):
        """Disconnect from Linear MCP"""
        # No persistent connection to close for MCP
        pass

    async def get_available_tasks(self) -> List[Task]:
        """Get unassigned tasks from backlog"""
        # Build search filter
        filter_obj = {
            "assignee": {"null": True},
            "state": {"type": {"in": ["backlog", "unstarted"]}},
        }

        if self.team_id:
            filter_obj["team"] = {"id": {"eq": self.team_id}}
        if self.project_id:
            filter_obj["project"] = {"id": {"eq": self.project_id}}

        result = await self.mcp_caller(
            "linear.search_issues",
            {
                "query": "",  # Empty query to get all matching filter
                "filter": filter_obj,
                "includeRelationships": True,
            },
        )

        tasks = []
        if result.get("issues"):
            for issue in result["issues"]:
                tasks.append(self._linear_issue_to_task(issue))

        return tasks

    def _linear_issue_to_task(self, issue: Dict[str, Any]) -> Task:
        """Convert Linear issue to Task model"""
        # Map Linear priority (0-4) to our Priority enum
        linear_priority = issue.get("priority", 3)
        priority_map = {
            1: Priority.URGENT,  # Urgent
            2: Priority.HIGH,  # High
            3: Priority.MEDIUM,  # Medium
            4: Priority.LOW,  # Low
            0: Priority.LOW,  # No priority
        }

        # Extract labels
        labels = issue.get("labels", [])
        if isinstance(labels, dict) and "nodes" in labels:
            labels = [label.get("name", "") for label in labels.get("nodes", [])]
        elif isinstance(labels, list):
            labels = [
                label if isinstance(label, str) else label.get("name", "")
                for label in labels
            ]

        # Map Linear state to TaskStatus
        state = issue.get("state", {})
        state_type = (
            state.get("type", "backlog") if isinstance(state, dict) else "backlog"
        )
        status_map = {
            "backlog": TaskStatus.BACKLOG,
            "unstarted": TaskStatus.READY,
            "started": TaskStatus.IN_PROGRESS,
            "completed": TaskStatus.DONE,
            "canceled": TaskStatus.DONE,
        }

        # Parse dates
        created_at = issue.get("createdAt", "")
        updated_at = issue.get("updatedAt", "")

        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        else:
            created_at = datetime.now()

        if updated_at and isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        else:
            updated_at = datetime.now()

        return Task(
            id=issue.get("id", ""),
            name=issue.get("title", "Untitled"),
            description=issue.get("description", ""),
            status=status_map.get(state_type, TaskStatus.BACKLOG),
            priority=priority_map.get(linear_priority, Priority.MEDIUM),
            labels=labels,
            estimated_hours=issue.get("estimate", 0) or 8,
            assigned_to=(
                issue.get("assignee", {}).get("id") if issue.get("assignee") else None
            ),
            dependencies=[],
            created_at=created_at,
            updated_at=updated_at,
        )

    async def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Get specific task by ID"""
        result = await self.mcp_caller(
            "linear.get_issue", {"issueId": task_id, "includeRelationships": True}
        )

        if not result.get("issue"):
            return None

        return self._linear_issue_to_task(result["issue"])

    async def create_task(self, task_data: Dict[str, Any]) -> Task:
        """Create new task in Linear"""
        # Map priority to Linear's scale
        priority = task_data.get("priority", Priority.MEDIUM)
        priority_map = {
            Priority.URGENT: 1,
            Priority.HIGH: 2,
            Priority.MEDIUM: 3,
            Priority.LOW: 4,
        }

        create_data = {
            "teamId": self.team_id,
            "title": task_data.get("name", "Untitled Task"),
            "description": task_data.get("description", ""),
            "priority": priority_map.get(priority, 3),
        }

        # Add optional fields
        if task_data.get("labels"):
            create_data["labelIds"] = task_data["labels"]

        result = await self.mcp_caller("linear.create_issue", create_data)

        if not result.get("issue"):
            raise Exception(
                f"Failed to create task: {result.get('error', 'Unknown error')}"
            )

        return self._linear_issue_to_task(result["issue"])

    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> Task:
        """Update existing task"""
        update_data = {"issueId": task_id}

        if "name" in updates:
            update_data["title"] = updates["name"]
        if "description" in updates:
            update_data["description"] = updates["description"]
        if "priority" in updates:
            priority_map = {
                Priority.URGENT: 1,
                Priority.HIGH: 2,
                Priority.MEDIUM: 3,
                Priority.LOW: 4,
            }
            update_data["priority"] = priority_map.get(updates["priority"], 3)

        result = await self.mcp_caller("linear.update_issue", update_data)

        if not result.get("issue"):
            raise Exception(
                f"Failed to update task: {result.get('error', 'Unknown error')}"
            )

        return self._linear_issue_to_task(result["issue"])

    async def assign_task(self, task_id: str, assignee_id: str) -> bool:
        """Assign task to user"""
        result = await self.mcp_caller(
            "linear.update_issue", {"issueId": task_id, "assigneeId": assignee_id}
        )

        return result.get("success", False)

    async def move_task_to_column(self, task_id: str, column_name: str) -> bool:
        """Move task to specific state"""
        # Map column names to Linear state names
        state_map = {
            "backlog": "Backlog",
            "todo": "Todo",
            "ready": "Ready",
            "in progress": "In Progress",
            "done": "Done",
            "completed": "Done",
            "blocked": "Blocked",
        }

        status_name = state_map.get(column_name.lower(), column_name)

        # Update issue with new status
        result = await self.mcp_caller(
            "linear.update_issue", {"issueId": task_id, "status": status_name}
        )

        return result.get("success", False)

    async def add_comment(self, task_id: str, comment: str) -> bool:
        """Add comment to task"""
        result = await self.mcp_caller(
            "linear.create_comment", {"issueId": task_id, "body": comment}
        )

        return result.get("success", False)

    async def get_project_metrics(self) -> Dict[str, Any]:
        """Get project metrics"""
        # Get counts for different states
        metrics = {
            "total_tasks": 0,
            "backlog_tasks": 0,
            "in_progress_tasks": 0,
            "completed_tasks": 0,
            "blocked_tasks": 0,
        }

        # Search for different states
        state_queries = [
            (["backlog", "unstarted"], "backlog_tasks"),
            (["started"], "in_progress_tasks"),
            (["completed", "canceled"], "completed_tasks"),
        ]

        for states, metric_key in state_queries:
            filter_obj = {"state": {"type": {"in": states}}}
            if self.team_id:
                filter_obj["team"] = {"id": {"eq": self.team_id}}
            if self.project_id:
                filter_obj["project"] = {"id": {"eq": self.project_id}}

            result = await self.mcp_caller(
                "linear.search_issues",
                {"query": "", "filter": filter_obj, "includeRelationships": False},
            )

            count = len(result.get("issues", []))
            metrics[metric_key] = count
            metrics["total_tasks"] += count

        return metrics

    async def report_blocker(
        self, task_id: str, blocker_description: str, severity: str = "medium"
    ) -> bool:
        """Report blocker on task"""
        # Add blocker comment
        comment = f"🚫 BLOCKER ({severity.upper()}): {blocker_description}"
        await self.add_comment(task_id, comment)

        # Add blocker label if possible
        mutation = """
            mutation AddLabel($issueId: String!, $labelName: String!) {
                issueLabelCreate(input: { issueId: $issueId, name: $labelName }) {
                    success
                }
            }
        """

        await self._graphql_request(
            mutation, {"issueId": task_id, "labelName": f"blocked-{severity}"}
        )

        return True

    async def update_task_progress(
        self, task_id: str, progress_data: Dict[str, Any]
    ) -> bool:
        """Update task progress"""
        progress = progress_data.get("progress", 0)
        status = progress_data.get("status", "")
        message = progress_data.get("message", "")

        # Add progress comment
        comment = f"📊 Progress: {progress}%"
        if message:
            comment += f" - {message}"

        await self.add_comment(task_id, comment)

        # Update state based on progress
        if progress >= 100:
            await self.move_task_to_column(task_id, "Done")
        elif progress > 0 and status == "in_progress":
            await self.move_task_to_column(task_id, "In Progress")

        return True
