#!/usr/bin/env python3
"""
Test attachment functionality using MCP client.

This demonstrates how Marcus agents would use attachments.
"""

import base64
import json
import subprocess
import sys
from pathlib import Path


def call_mcp_tool(tool_name, arguments):
    """Call an MCP tool via the kanban-mcp server."""
    # Format the MCP request
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
        "id": 1,
    }

    # Convert to JSON
    request_json = json.dumps(request)

    print(f"\n📤 Calling MCP tool: {tool_name}")
    print(f"   Arguments: {json.dumps(arguments, indent=2)}")

    # Note: In a real scenario, this would be sent to the MCP server
    # For now, we'll simulate the response
    return simulate_mcp_response(tool_name, arguments)


def simulate_mcp_response(tool_name, arguments):
    """Simulate MCP responses for testing."""
    if tool_name == "mcp_kanban_attachment_manager":
        action = arguments.get("action")

        if action == "upload":
            return {
                "id": "att-123",
                "filename": arguments.get("filename"),
                "url": "/attachments/att-123",
                "createdAt": "2024-01-20T10:00:00Z",
            }
        elif action == "get_all":
            return [
                {
                    "id": "att-123",
                    "name": "api-spec.json",
                    "url": "/attachments/att-123",
                    "createdAt": "2024-01-20T10:00:00Z",
                    "userId": "user-1",
                }
            ]
        elif action == "download":
            # Return the actual API spec that was uploaded
            api_spec = {
                "openapi": "3.0.0",
                "info": {
                    "title": "User Management API",
                    "version": "1.0.0",
                    "description": "RESTful API for user operations",
                },
                "paths": {
                    "/users": {
                        "get": {"summary": "List users"},
                        "post": {"summary": "Create user"},
                    }
                },
                "components": {
                    "schemas": {
                        "User": {"type": "object"},
                        "CreateUserRequest": {"type": "object"},
                    }
                },
            }
            return {
                "content": base64.b64encode(json.dumps(api_spec).encode()).decode(),
                "filename": "api-spec.json",
            }

    return {}


def test_attachment_workflow():
    """Test the attachment workflow as an agent would use it."""

    print("🤖 Marcus Agent Attachment Workflow Test")
    print("=" * 50)

    # Scenario: Design agent uploads API specification
    print("\n📐 DESIGN PHASE - Agent: API Designer")
    print("-" * 40)

    # Create API specification
    api_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "User Management API",
            "version": "1.0.0",
            "description": "RESTful API for user operations",
        },
        "servers": [{"url": "https://api.example.com/v1"}],
        "paths": {
            "/users": {
                "get": {
                    "summary": "List users",
                    "operationId": "listUsers",
                    "parameters": [
                        {
                            "name": "page",
                            "in": "query",
                            "schema": {"type": "integer", "default": 1},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "User list",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "users": {
                                                "type": "array",
                                                "items": {
                                                    "$ref": "#/components/schemas/User"
                                                },
                                            },
                                            "total": {"type": "integer"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                },
                "post": {
                    "summary": "Create user",
                    "operationId": "createUser",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/CreateUserRequest"
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "User created",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            },
                        }
                    },
                },
            }
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "required": ["id", "email", "name"],
                    "properties": {
                        "id": {"type": "string", "format": "uuid"},
                        "email": {"type": "string", "format": "email"},
                        "name": {"type": "string"},
                        "createdAt": {"type": "string", "format": "date-time"},
                    },
                },
                "CreateUserRequest": {
                    "type": "object",
                    "required": ["email", "name", "password"],
                    "properties": {
                        "email": {"type": "string", "format": "email"},
                        "name": {"type": "string"},
                        "password": {"type": "string", "minLength": 8},
                    },
                },
            }
        },
    }

    # Convert to JSON and encode
    api_spec_json = json.dumps(api_spec, indent=2)
    api_spec_base64 = base64.b64encode(api_spec_json.encode()).decode()

    # Upload the design document
    upload_result = call_mcp_tool(
        "mcp_kanban_attachment_manager",
        {
            "action": "upload",
            "cardId": "design-task-card-id",
            "filename": "user-api-spec.json",
            "content": api_spec_base64,
            "contentType": "application/json",
        },
    )

    print(f"\n✅ Uploaded design artifact: {upload_result['filename']}")
    print(f"   Attachment ID: {upload_result['id']}")

    # Scenario: Backend agent retrieves design artifacts
    print("\n\n💻 IMPLEMENTATION PHASE - Agent: Backend Developer")
    print("-" * 40)

    # List attachments on the dependency task
    list_result = call_mcp_tool(
        "mcp_kanban_attachment_manager",
        {"action": "get_all", "cardId": "design-task-card-id"},
    )

    print(f"\n📎 Found {len(list_result)} design artifact(s):")
    for att in list_result:
        print(f"   - {att['name']} (created: {att['createdAt']})")

    # Download the API specification
    if list_result:
        attachment = list_result[0]
        download_result = call_mcp_tool(
            "mcp_kanban_attachment_manager",
            {
                "action": "download",
                "id": attachment["id"],
                "filename": attachment["name"],
            },
        )

        # Decode the content
        content = base64.b64decode(download_result["content"]).decode()
        spec = json.loads(content)

        print(f"\n📥 Downloaded: {download_result['filename']}")
        print("\n🔍 Analyzing API specification...")
        print(f"   - API Title: {spec['info']['title']}")
        print(f"   - Version: {spec['info']['version']}")
        print(f"   - Endpoints to implement:")
        for path, methods in spec["paths"].items():
            for method, details in methods.items():
                print(f"     • {method.upper()} {path} - {details['summary']}")

        print("\n📝 Extracting implementation details...")
        print("   - Models to create:")
        for schema_name in spec["components"]["schemas"]:
            print(f"     • {schema_name}")

        print("\n🚀 Ready to implement based on design specification!")

    # Summary
    print("\n\n✨ WORKFLOW SUMMARY")
    print("=" * 50)
    print("1. Design agent created API specification")
    print("2. Uploaded as attachment to design task")
    print("3. Implementation agent retrieved the spec")
    print("4. Analyzed requirements from the design")
    print("5. Ready to implement with full context")

    print(
        "\n✅ Attachment workflow enables seamless handoff between design and implementation!"
    )


if __name__ == "__main__":
    test_attachment_workflow()
