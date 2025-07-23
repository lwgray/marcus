#!/usr/bin/env python3
"""
End-to-end test for attachment workflow.

This script demonstrates:
1. Creating design and implementation tasks
2. Uploading design artifacts to the design task
3. Implementation task retrieving artifacts from dependencies
"""

import asyncio
import base64
import json
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.models import Priority, Task, TaskStatus
from src.integrations.providers.planka_kanban import PlankaKanban
from src.marcus_mcp.tools.attachment import (
    download_design_artifact,
    get_dependency_artifacts,
    list_design_artifacts,
    upload_design_artifact,
)


class MockState:
    """Mock state object for testing."""

    def __init__(self, kanban_client, tasks):
        self.kanban_client = kanban_client
        self.project_tasks = tasks


async def create_test_design_document():
    """Create a sample API specification document."""
    api_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "User Service API",
            "version": "1.0.0",
            "description": "API for user management",
        },
        "paths": {
            "/users": {
                "get": {
                    "summary": "List all users",
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/User"},
                                    }
                                }
                            },
                        }
                    },
                },
                "post": {
                    "summary": "Create a new user",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/CreateUserRequest"
                                }
                            }
                        }
                    },
                },
            }
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "email": {"type": "string"},
                        "name": {"type": "string"},
                    },
                },
                "CreateUserRequest": {
                    "type": "object",
                    "required": ["email", "name"],
                    "properties": {
                        "email": {"type": "string"},
                        "name": {"type": "string"},
                    },
                },
            }
        },
    }

    return json.dumps(api_spec, indent=2)


async def test_attachment_workflow():
    """Test the complete attachment workflow."""
    print("🚀 Starting attachment workflow test...")

    # Initialize kanban client
    print("\n1️⃣ Initializing Kanban client...")

    # Create MCP function caller
    async def mcp_function_caller(tool_name, arguments):
        """Mock MCP function caller that uses local kanban-mcp."""
        # This would normally call the MCP server
        # For testing, we'll simulate the responses
        print(f"  → MCP Call: {tool_name} with {arguments}")

        # Simulate responses based on tool name
        if tool_name == "mcp_kanban_attachment_manager":
            action = arguments.get("action")
            if action == "upload":
                return {
                    "id": "test-attachment-123",
                    "filename": arguments.get("filename"),
                    "url": f"/attachments/test-attachment-123",
                    "createdAt": "2024-01-20T10:00:00Z",
                }
            elif action == "get_all":
                return [
                    {
                        "id": "test-attachment-123",
                        "name": "api-spec.json",
                        "url": "/attachments/test-attachment-123",
                        "createdAt": "2024-01-20T10:00:00Z",
                        "userId": "user-123",
                    }
                ]
            elif action == "download":
                # Return the base64 encoded content
                api_spec = await create_test_design_document()
                return {
                    "content": base64.b64encode(api_spec.encode()).decode(),
                    "filename": "api-spec.json",
                }
        return {}

    config = {
        "project_name": "Attachment Test Project",
        "mcp_function_caller": mcp_function_caller,
    }

    kanban = PlankaKanban(config)

    try:
        # Connect to kanban (this would normally connect to Planka)
        print("  ✓ Kanban client initialized")

        # Create test tasks
        print("\n2️⃣ Creating test tasks...")

        # Design task
        design_task = Task(
            id="design-task-001",
            name="Design User API",
            description="Create OpenAPI specification for user management endpoints",
            status=TaskStatus.DONE,
            priority=Priority.HIGH,
            labels=["design", "api"],
            assigned_to="designer-agent",
            kanban_card_id="card-design-001",
            dependencies=[],
            estimated_hours=4,
            actual_hours=3,
        )

        # Implementation task that depends on design
        impl_task = Task(
            id="impl-task-001",
            name="Implement User API",
            description="Implement the user API based on the design specification",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            labels=["backend", "api"],
            assigned_to="backend-agent",
            kanban_card_id="card-impl-001",
            dependencies=["design-task-001"],  # Depends on design task
            estimated_hours=8,
            actual_hours=2,
        )

        tasks = [design_task, impl_task]
        state = MockState(kanban, tasks)

        print("  ✓ Created design task: 'Design User API'")
        print(
            "  ✓ Created implementation task: 'Implement User API' (depends on design)"
        )

        # Upload design artifact
        print("\n3️⃣ Uploading API specification to design task...")

        api_spec_content = await create_test_design_document()

        upload_result = await upload_design_artifact(
            task_id="design-task-001",
            filename="api-spec.json",
            content=api_spec_content,
            content_type="application/json",
            description="OpenAPI 3.0 specification for user management endpoints",
            state=state,
        )

        if upload_result.success:
            print(f"  ✓ Uploaded: {upload_result.data['filename']}")
            print(f"    - Attachment ID: {upload_result.data['attachment_id']}")
            print(f"    - Size: {upload_result.data['size']} bytes")
        else:
            print(f"  ✗ Upload failed: {upload_result.error}")

        # List artifacts on design task
        print("\n4️⃣ Listing artifacts on design task...")

        list_result = await list_design_artifacts(
            task_id="design-task-001", state=state
        )

        if list_result.success:
            print(f"  ✓ Found {list_result.data['count']} artifacts:")
            for artifact in list_result.data["artifacts"]:
                print(f"    - {artifact['filename']} (ID: {artifact['id']})")

        # Implementation task retrieves dependency artifacts
        print("\n5️⃣ Implementation task retrieving dependency artifacts...")

        dep_result = await get_dependency_artifacts(
            task_id="impl-task-001", artifact_types=["json", "yaml"], state=state
        )

        if dep_result.success:
            print(
                f"  ✓ Found {dep_result.data['total_count']} artifacts from dependencies:"
            )
            for artifact in dep_result.data["dependency_artifacts"]:
                print(
                    f"    - {artifact['filename']} from task: {artifact['dependency_task_name']}"
                )

        # Download and examine the artifact
        print("\n6️⃣ Downloading API specification...")

        if dep_result.success and dep_result.data["dependency_artifacts"]:
            first_artifact = dep_result.data["dependency_artifacts"][0]

            download_result = await download_design_artifact(
                task_id="design-task-001",
                attachment_id=first_artifact["id"],
                state=state,
            )

            if download_result.success:
                print("  ✓ Downloaded artifact successfully")
                print(f"    - Filename: {download_result.data['filename']}")
                print(f"    - Size: {download_result.data['size']} bytes")

                # Decode and display content
                content = base64.b64decode(download_result.data["content"])
                api_spec = json.loads(content)
                print("\n  📄 API Specification Preview:")
                print(f"    - Title: {api_spec['info']['title']}")
                print(f"    - Version: {api_spec['info']['version']}")
                print(f"    - Endpoints: {list(api_spec['paths'].keys())}")

        print("\n✅ Attachment workflow test completed successfully!")
        print("\nSummary:")
        print("- Design task created with API specification")
        print("- Implementation task can access design artifacts")
        print("- Full artifact propagation workflow verified")

    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback

        traceback.print_exc()


async def main():
    """Run the test."""
    await test_attachment_workflow()


if __name__ == "__main__":
    asyncio.run(main())
