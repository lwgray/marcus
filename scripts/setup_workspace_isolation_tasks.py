#!/usr/bin/env python3
"""
Set up workspace isolation tasks on the kanban board
"""

import asyncio
import json
import sys
sys.path.insert(0, '.')

from src.integrations.mcp_kanban_client_refactored import MCPKanbanClient


async def setup_workspace_tasks():
    """Clean board and create workspace isolation tasks"""
    client = MCPKanbanClient()
    
    print("🧹 Setting up Workspace Isolation tasks...")
    print("=" * 60)
    
    async with client.connect() as conn:
        # First, let's get all existing cards to clean them
        print("\n📋 Getting existing cards...")
        result = await conn.call_tool("mcp_kanban_card_manager", {
            "action": "get_all",
            "boardId": client.board_id
        })
        
        if hasattr(result, 'content') and result.content:
            data = json.loads(result.content[0].text)
            cards = data if isinstance(data, list) else data.get("items", [])
            
            # Archive old TODO app cards
            print(f"\n🗑️  Archiving {len(cards)} old cards...")
            for card in cards:
                await conn.call_tool("mcp_kanban_card_manager", {
                    "action": "delete",
                    "id": card["id"]
                })
            
        # Get lists for creating new cards
        print("\n📑 Getting board lists...")
        lists_result = await conn.call_tool("mcp_kanban_list_manager", {
            "action": "get_all",
            "boardId": client.board_id
        })
        
        lists = {}
        if hasattr(lists_result, 'content') and lists_result.content:
            data = json.loads(lists_result.content[0].text)
            all_lists = data if isinstance(data, list) else data.get("items", [])
            
            for lst in all_lists:
                name = lst.get("name", "").upper()
                if "BACKLOG" in name or "TODO" in name:
                    lists["backlog"] = lst["id"]
                elif "PROGRESS" in name:
                    lists["in_progress"] = lst["id"]
                elif "REVIEW" in name:
                    lists["review"] = lst["id"]
                elif "DONE" in name:
                    lists["done"] = lst["id"]
        
        # Define our workspace isolation tasks with dependencies
        tasks = [
            # Phase 1: Analysis & Design
            {
                "name": "Analyze current client workspace behavior",
                "description": "- How do clients determine working directory\n- Document current security issues\n- Map all file access patterns",
                "labels": ["analysis", "security"],
                "listId": lists.get("backlog"),
                "position": 1
            },
            {
                "name": "Design portable workspace isolation architecture",
                "description": "- Dynamic PM Agent location detection\n- Project workspace configuration schema\n- Security boundaries definition\nDepends on: Analyze current behavior",
                "labels": ["design", "architecture"],
                "listId": lists.get("backlog"),
                "position": 2
            },
            
            # Phase 2: Core Implementation
            {
                "name": "Implement WorkspaceManager class",
                "description": "- Auto-detect PM Agent installation path\n- Manage forbidden paths dynamically\n- Handle multiple project workspaces\nDepends on: Design architecture",
                "labels": ["implementation", "core"],
                "listId": lists.get("backlog"),
                "position": 3
            },
            {
                "name": "Update configuration system",
                "description": "- Move config to ~/.config/pm-agent/\n- Add project workspace configuration\n- Support environment variables\nDepends on: Design architecture",
                "labels": ["implementation", "config"],
                "listId": lists.get("backlog"),
                "position": 4
            },
            {
                "name": "Modify task assignments to include workspace",
                "description": "- Add workspace_path to TaskAssignment\n- Include forbidden_paths in assignments\n- Update task allocation logic\nDepends on: WorkspaceManager",
                "labels": ["implementation", "core"],
                "listId": lists.get("backlog"),
                "position": 5
            },
            
            # Phase 3: Security & Validation
            {
                "name": "Implement client sandbox validation",
                "description": "- Validate all file operations\n- Reject access to forbidden paths\n- Log security violations\nDepends on: WorkspaceManager, Task assignments",
                "labels": ["security", "validation"],
                "listId": lists.get("backlog"),
                "position": 6
            },
            {
                "name": "Create workspace setup validation",
                "description": "- Check for path overlaps\n- Validate workspace accessibility\n- Ensure git worktree compatibility\nDepends on: WorkspaceManager",
                "labels": ["validation"],
                "listId": lists.get("backlog"),
                "position": 7
            },
            
            # Phase 4: Testing
            {
                "name": "Write workspace isolation tests",
                "description": "- Test forbidden path protection\n- Multi-agent workspace isolation\n- Configuration portability\nDepends on: All implementation tasks",
                "labels": ["testing"],
                "listId": lists.get("backlog"),
                "position": 8
            },
            
            # Phase 5: Documentation & Migration
            {
                "name": "Update documentation for new architecture",
                "description": "- Installation guide\n- Workspace configuration\n- Security model explanation\nDepends on: Implementation complete",
                "labels": ["documentation"],
                "listId": lists.get("backlog"),
                "position": 9
            },
            {
                "name": "Create migration script",
                "description": "- Migrate existing configs\n- Update MCP registration\n- Provide rollback option\nDepends on: Documentation",
                "labels": ["migration", "tooling"],
                "listId": lists.get("backlog"),
                "position": 10
            }
        ]
        
        # Create all tasks
        print(f"\n✨ Creating {len(tasks)} new tasks...")
        for task in tasks:
            result = await conn.call_tool("mcp_kanban_card_manager", {
                "action": "create",
                "listId": task["listId"],
                "name": task["name"],
                "description": task.get("description", ""),
                "position": task.get("position", 0)
            })
            
            if hasattr(result, 'content') and result.content:
                card_data = json.loads(result.content[0].text)
                print(f"   ✅ Created: {task['name']}")
                
                # Add labels if specified
                if "labels" in task and card_data.get("id"):
                    for label in task["labels"]:
                        # Note: Label creation might need different approach
                        pass
        
        print("\n🎯 Board setup complete!")
        print("   Tasks are ready in the Backlog")
        print("   Dependencies are noted in descriptions")


if __name__ == "__main__":
    asyncio.run(setup_workspace_tasks())