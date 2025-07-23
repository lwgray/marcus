#!/usr/bin/env python3
"""
Simple test to verify attachment functionality with kanban-mcp.

This tests the attachment operations directly using HTTP requests.
"""

import asyncio
import base64
import json
import os
from typing import Any, Dict

# Set environment variables if not already set
os.environ.setdefault("PLANKA_BASE_URL", "http://localhost:3333")
os.environ.setdefault("PLANKA_AGENT_EMAIL", "demo@demo.demo")
os.environ.setdefault("PLANKA_AGENT_PASSWORD", "demo")


async def test_kanban_mcp_attachments():
    """Test attachment functionality via kanban-mcp docker container."""

    print("🚀 Testing Attachment Functionality with kanban-mcp\n")

    # First, let's check if we can import and use kanban-mcp operations
    try:
        # Import the operations we need
        import sys

        sys.path.append("/Users/lwgray/dev/kanban-mcp")

        from operations.attachments import (
            createAttachment,
            downloadAttachment,
            getAttachments,
        )
        from operations.boards import getBoards
        from operations.cards import createCard, getCards
        from operations.lists import getLists
        from operations.projects import getProjects

        print("✅ Successfully imported kanban-mcp operations")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Note: This test should be run with kanban-mcp available")
        return

    try:
        # Get projects
        print("\n1️⃣ Getting projects...")
        projects_response = await getProjects(1, 10)

        if not projects_response or not projects_response.get("items"):
            print("  ❌ No projects found. Please ensure Planka has projects.")
            return

        project = projects_response["items"][0]
        print(f"  ✓ Using project: {project['name']}")

        # Get boards
        print("\n2️⃣ Getting boards...")
        boards = await getBoards(project["id"])

        if not boards:
            print("  ❌ No boards found in project.")
            return

        board = boards[0]
        print(f"  ✓ Using board: {board['name']}")

        # Get lists
        print("\n3️⃣ Getting lists...")
        lists = await getLists(board["id"])

        if not lists:
            print("  ❌ No lists found in board.")
            return

        list_obj = lists[0]
        print(f"  ✓ Using list: {list_obj['name']}")

        # Create a test card
        print("\n4️⃣ Creating test card...")
        card = await createCard(
            {
                "listId": list_obj["id"],
                "name": "Test Card with Attachments",
                "description": "Testing attachment functionality",
            }
        )
        print(f"  ✓ Created card: {card['name']} (ID: {card['id']})")

        # Create a test document
        print("\n5️⃣ Creating and uploading design document...")

        api_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/test": {
                    "get": {
                        "summary": "Test endpoint",
                        "responses": {"200": {"description": "Success"}},
                    }
                }
            },
        }

        # Convert to JSON string
        content = json.dumps(api_spec, indent=2)

        # Upload as attachment
        attachment = await createAttachment(
            card["id"],
            {
                "filename": "api-design.json",
                "content": content,  # Will be base64 encoded by the function
                "contentType": "application/json",
            },
        )

        print(f"  ✓ Uploaded attachment: {attachment['name']}")
        print(f"    - ID: {attachment['id']}")
        print(f"    - URL: {attachment.get('url', 'N/A')}")

        # List attachments
        print("\n6️⃣ Listing attachments...")
        attachments = await getAttachments(card["id"])

        print(f"  ✓ Found {len(attachments)} attachment(s):")
        for att in attachments:
            print(f"    - {att['name']} (ID: {att['id']})")

        # Download attachment
        print("\n7️⃣ Downloading attachment...")
        if attachments:
            first_attachment = attachments[0]

            downloaded = await downloadAttachment(
                first_attachment["id"], first_attachment["name"]
            )

            # The content is base64 encoded
            content_decoded = base64.b64decode(downloaded).decode("utf-8")
            downloaded_spec = json.loads(content_decoded)

            print(f"  ✓ Downloaded: {first_attachment['name']}")
            print(f"    - Title: {downloaded_spec['info']['title']}")
            print(f"    - Version: {downloaded_spec['info']['version']}")

        print("\n✅ Attachment test completed successfully!")
        print("\nThis demonstrates:")
        print("- ✓ Creating cards with attachments")
        print("- ✓ Uploading design documents")
        print("- ✓ Listing attachments")
        print("- ✓ Downloading and reading attachments")

    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback

        traceback.print_exc()


# Run the test
if __name__ == "__main__":
    asyncio.run(test_kanban_mcp_attachments())
