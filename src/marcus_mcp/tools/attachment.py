"""
Attachment management tools for design artifact sharing.

These tools allow agents to upload, download, and manage attachments
on kanban cards, enabling design artifacts to be shared between tasks.
"""

import base64
from pathlib import Path
from typing import Any, List, Optional, Union

from src.core.logging import get_logger
from src.marcus_mcp.tool_outputs import ToolResult

logger = get_logger(__name__)


async def upload_design_artifact(
    task_id: str,
    filename: str,
    content: Union[str, bytes],
    content_type: Optional[str] = None,
    description: Optional[str] = None,
    state: Any = None,
) -> ToolResult:
    """
    Upload a design artifact (file) to a task.

    This tool allows agents to attach design documents, API specifications,
    wireframes, data models, and other artifacts to tasks for dependent
    tasks to reference.

    Args:
        task_id: The task ID to attach the artifact to
        filename: Name for the attachment file
        content: File content as string or bytes (will be base64 encoded if string)
        content_type: MIME type of the content (e.g., 'application/json')
        description: Optional description of the artifact
        state: MCP state object

    Returns:
        ToolResult with attachment information
    """
    try:
        # Get kanban client from state
        kanban = state.kanban_client
        if not kanban:
            return ToolResult(
                success=False,
                error="Kanban client not available",
                data={"task_id": task_id},
            )

        # Find the task's card ID
        task = next((t for t in state.project_tasks if t.id == task_id), None)
        if not task:
            return ToolResult(
                success=False,
                error=f"Task {task_id} not found",
                data={"task_id": task_id},
            )

        if not task.kanban_card_id:
            return ToolResult(
                success=False,
                error=f"Task {task_id} has no associated kanban card",
                data={"task_id": task_id},
            )

        # Encode content to base64 if it's not already bytes
        if isinstance(content, str):
            # If it looks like it's already base64, use it as is
            try:
                base64.b64decode(content)
                encoded_content = content
            except Exception:
                # Otherwise encode it
                encoded_content = base64.b64encode(content.encode()).decode()
        else:
            encoded_content = base64.b64encode(content).decode()

        # Upload attachment
        result = await kanban.upload_attachment(
            card_id=task.kanban_card_id,
            filename=filename,
            content=encoded_content,
            content_type=content_type,
        )

        if not result.get("success", False):
            return ToolResult(
                success=False,
                error=result.get("error", "Failed to upload attachment"),
                data={"task_id": task_id, "filename": filename},
            )

        attachment = result.get("data", {})

        # Add comment describing the artifact if provided
        if description:
            await kanban.add_comment(
                card_id=task.kanban_card_id,
                text=f"📎 Uploaded design artifact: {filename}\n\n{description}",
            )

        logger.info(f"Successfully uploaded artifact {filename} to task {task_id}")

        return ToolResult(
            success=True,
            data={
                "task_id": task_id,
                "attachment_id": attachment.get("id"),
                "filename": filename,
                "url": attachment.get("url"),
                "size": len(encoded_content),
            },
        )

    except Exception as e:
        logger.error(f"Error uploading design artifact: {str(e)}")
        return ToolResult(
            success=False,
            error=f"Failed to upload artifact: {str(e)}",
            data={"task_id": task_id, "filename": filename},
        )


async def download_design_artifact(
    task_id: str,
    attachment_id: str,
    save_to_path: Optional[str] = None,
    state: Any = None,
) -> ToolResult:
    """
    Download a design artifact from a task.

    This tool allows agents to retrieve design documents and other
    artifacts that were uploaded by previous tasks.

    Args:
        task_id: The task ID to download from
        attachment_id: The attachment ID to download
        save_to_path: Optional local path to save the file
        state: MCP state object

    Returns:
        ToolResult with file content or save path
    """
    try:
        # Get kanban client from state
        kanban = state.kanban_client
        if not kanban:
            return ToolResult(
                success=False,
                error="Kanban client not available",
                data={"task_id": task_id},
            )

        # Find the task's card ID
        task = next((t for t in state.project_tasks if t.id == task_id), None)
        if not task:
            return ToolResult(
                success=False,
                error=f"Task {task_id} not found",
                data={"task_id": task_id},
            )

        if not task.kanban_card_id:
            return ToolResult(
                success=False,
                error=f"Task {task_id} has no associated kanban card",
                data={"task_id": task_id},
            )

        # Get attachment details first
        attachments = await kanban.get_attachments(card_id=task.kanban_card_id)
        attachment = next(
            (a for a in attachments.get("data", []) if a.get("id") == attachment_id),
            None,
        )

        if not attachment:
            return ToolResult(
                success=False,
                error=f"Attachment {attachment_id} not found on task {task_id}",
                data={"task_id": task_id, "attachment_id": attachment_id},
            )

        # Download the attachment
        result = await kanban.download_attachment(
            attachment_id=attachment_id, filename=attachment.get("name", "download")
        )

        if not result.get("success", False):
            return ToolResult(
                success=False,
                error=result.get("error", "Failed to download attachment"),
                data={"task_id": task_id, "attachment_id": attachment_id},
            )

        content = result.get("data", {}).get("content", "")
        filename = attachment.get("name", "download")

        # Save to file if path provided
        if save_to_path:
            save_path = Path(save_to_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)

            # Decode base64 content
            decoded_content = base64.b64decode(content)
            save_path.write_bytes(decoded_content)

            logger.info(
                f"Downloaded artifact {filename} from task {task_id} to {save_path}"
            )

            return ToolResult(
                success=True,
                data={
                    "task_id": task_id,
                    "attachment_id": attachment_id,
                    "filename": filename,
                    "saved_to": str(save_path),
                    "size": len(decoded_content),
                },
            )
        else:
            # Return content directly
            logger.info(f"Downloaded artifact {filename} from task {task_id}")

            return ToolResult(
                success=True,
                data={
                    "task_id": task_id,
                    "attachment_id": attachment_id,
                    "filename": filename,
                    "content": content,  # Base64 encoded
                    "size": len(base64.b64decode(content)),
                },
            )

    except Exception as e:
        logger.error(f"Error downloading design artifact: {str(e)}")
        return ToolResult(
            success=False,
            error=f"Failed to download artifact: {str(e)}",
            data={"task_id": task_id, "attachment_id": attachment_id},
        )


async def list_design_artifacts(
    task_id: str,
    state: Any = None,
) -> ToolResult:
    """
    List all design artifacts attached to a task.

    This tool allows agents to see what design documents and artifacts
    are available on a task.

    Args:
        task_id: The task ID to list artifacts for
        state: MCP state object

    Returns:
        ToolResult with list of attachments
    """
    try:
        # Get kanban client from state
        kanban = state.kanban_client
        if not kanban:
            return ToolResult(
                success=False,
                error="Kanban client not available",
                data={"task_id": task_id},
            )

        # Find the task's card ID
        task = next((t for t in state.project_tasks if t.id == task_id), None)
        if not task:
            return ToolResult(
                success=False,
                error=f"Task {task_id} not found",
                data={"task_id": task_id},
            )

        if not task.kanban_card_id:
            return ToolResult(
                success=False,
                error=f"Task {task_id} has no associated kanban card",
                data={"task_id": task_id},
            )

        # Get attachments
        result = await kanban.get_attachments(card_id=task.kanban_card_id)

        if not result.get("success", False):
            return ToolResult(
                success=False,
                error=result.get("error", "Failed to get attachments"),
                data={"task_id": task_id},
            )

        attachments = result.get("data", [])

        # Format attachment list
        artifact_list = []
        for attachment in attachments:
            artifact_list.append(
                {
                    "id": attachment.get("id"),
                    "filename": attachment.get("name"),
                    "url": attachment.get("url"),
                    "created_at": attachment.get("createdAt"),
                    "created_by": attachment.get("userId"),
                }
            )

        logger.info(f"Found {len(artifact_list)} artifacts on task {task_id}")

        return ToolResult(
            success=True,
            data={
                "task_id": task_id,
                "artifacts": artifact_list,
                "count": len(artifact_list),
            },
        )

    except Exception as e:
        logger.error(f"Error listing design artifacts: {str(e)}")
        return ToolResult(
            success=False,
            error=f"Failed to list artifacts: {str(e)}",
            data={"task_id": task_id},
        )


async def get_dependency_artifacts(
    task_id: str,
    artifact_types: Optional[List[str]] = None,
    state: Any = None,
) -> ToolResult:
    """
    Get all design artifacts from tasks that this task depends on.

    This tool helps agents discover and retrieve design documents
    from their dependency tasks, enabling them to understand the
    design context for their implementation.

    Args:
        task_id: The current task ID
        artifact_types: Optional list of file extensions to filter (e.g., ['json', 'yaml', 'md'])
        state: MCP state object

    Returns:
        ToolResult with artifacts from dependency tasks
    """
    try:
        # Get task
        task = next((t for t in state.project_tasks if t.id == task_id), None)
        if not task:
            return ToolResult(
                success=False,
                error=f"Task {task_id} not found",
                data={"task_id": task_id},
            )

        # Get all dependency tasks
        dependency_artifacts = []

        for dep_id in task.dependencies:
            # Get artifacts from dependency
            result = await list_design_artifacts(dep_id, state)

            if result.success:
                dep_task = next(
                    (t for t in state.project_tasks if t.id == dep_id), None
                )
                dep_name = dep_task.name if dep_task else dep_id

                artifacts = result.data.get("artifacts", [])

                # Filter by type if specified
                if artifact_types:
                    artifacts = [
                        a
                        for a in artifacts
                        if any(
                            a.get("filename", "").endswith(f".{ext}")
                            for ext in artifact_types
                        )
                    ]

                # Add dependency context to each artifact
                for artifact in artifacts:
                    artifact["dependency_task_id"] = dep_id
                    artifact["dependency_task_name"] = dep_name

                dependency_artifacts.extend(artifacts)

        logger.info(
            f"Found {len(dependency_artifacts)} artifacts from "
            f"{len(task.dependencies)} dependency tasks for task {task_id}"
        )

        return ToolResult(
            success=True,
            data={
                "task_id": task_id,
                "dependency_artifacts": dependency_artifacts,
                "total_count": len(dependency_artifacts),
                "dependency_count": len(task.dependencies),
            },
        )

    except Exception as e:
        logger.error(f"Error getting dependency artifacts: {str(e)}")
        return ToolResult(
            success=False,
            error=f"Failed to get dependency artifacts: {str(e)}",
            data={"task_id": task_id},
        )
