"""
Simple MCP Kanban Client that follows the working pattern
"""

import asyncio
import json
import os
from typing import List, Dict, Optional, Any
from datetime import datetime
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.core.models import Task, TaskStatus, Priority


class SimpleMCPKanbanClient:
    """Simple client that follows the exact pattern of working scripts"""
    
    def __init__(self):
        # Load config
        self.board_id = None
        self.project_id = None
        self._load_config()
        
        # Set environment for Planka
        os.environ['PLANKA_BASE_URL'] = 'http://localhost:3333'
        os.environ['PLANKA_AGENT_EMAIL'] = 'demo@demo.demo'
        os.environ['PLANKA_AGENT_PASSWORD'] = 'demo'
    
    def _load_config(self):
        """Load configuration from config_pm_agent.json"""
        if os.path.exists('config_pm_agent.json'):
            with open('config_pm_agent.json', 'r') as f:
                config = json.load(f)
                self.project_id = config.get("project_id")
                self.board_id = config.get("board_id")
                print(f"✅ Loaded config: project_id={self.project_id}, board_id={self.board_id}")
    
    async def get_available_tasks(self) -> List[Task]:
        """Get all unassigned tasks from the board"""
        if not self.board_id:
            raise RuntimeError("Board ID not set")
        
        # Use the exact same pattern as working scripts
        server_params = StdioServerParameters(
            command="node",
            args=["../kanban-mcp/dist/index.js"],
            env=os.environ.copy()
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # First get all lists for the board
                lists_result = await session.call_tool(
                    "mcp_kanban_list_manager",
                    {
                        "action": "get_all",
                        "boardId": self.board_id
                    }
                )
                
                all_cards = []
                if lists_result and hasattr(lists_result, 'content') and lists_result.content:
                    lists_data = json.loads(lists_result.content[0].text)
                    lists = lists_data if isinstance(lists_data, list) else lists_data.get("items", [])
                    
                    # Get cards from each list
                    for lst in lists:
                        list_id = lst.get("id")
                        if list_id:
                            # Get cards for this list
                            cards_result = await session.call_tool(
                                "mcp_kanban_card_manager",
                                {
                                    "action": "get_all",
                                    "listId": list_id
                                }
                            )
                            
                            if cards_result and hasattr(cards_result, 'content') and cards_result.content:
                                cards_text = cards_result.content[0].text
                                if cards_text and cards_text.strip():
                                    cards_data = json.loads(cards_text)
                                    cards_list = cards_data if isinstance(cards_data, list) else cards_data.get("items", [])
                                    # Add list name to each card
                                    for card in cards_list:
                                        card["listName"] = lst.get("name", "")
                                        all_cards.append(card)
                
                result = None  # We'll use all_cards instead
                
                tasks = []
                
                # Use the all_cards we collected
                for card in all_cards:
                    task = self._card_to_task(card)
                    if not task.assigned_to and self._is_available_task(card):
                        tasks.append(task)
                
                return tasks
    
    async def assign_task(self, task_id: str, agent_id: str):
        """Assign a task to an agent"""
        server_params = StdioServerParameters(
            command="node",
            args=["../kanban-mcp/dist/index.js"],
            env=os.environ.copy()
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Add comment
                await session.call_tool(
                    "mcp_kanban_comment_manager",
                    {
                        "action": "create",
                        "cardId": task_id,
                        "text": f"📋 Task assigned to {agent_id} at {datetime.now().isoformat()}"
                    }
                )
                
                # Move to In Progress
                # First get lists
                lists_result = await session.call_tool(
                    "mcp_kanban_list_manager",
                    {
                        "action": "get_all",
                        "boardId": self.board_id
                    }
                )
                
                if lists_result and hasattr(lists_result, 'content'):
                    lists_data = json.loads(lists_result.content[0].text)
                    lists = lists_data if isinstance(lists_data, list) else lists_data.get("items", [])
                    
                    # Find In Progress list
                    in_progress_list = None
                    for lst in lists:
                        if "progress" in lst.get("name", "").lower():
                            in_progress_list = lst
                            break
                    
                    if in_progress_list:
                        # Move card
                        await session.call_tool(
                            "mcp_kanban_card_manager",
                            {
                                "action": "move",
                                "id": task_id,
                                "listId": in_progress_list["id"]
                            }
                        )
    
    async def get_board_summary(self) -> Dict[str, Any]:
        """Get summary statistics for the board"""
        if not self.board_id:
            raise RuntimeError("Board ID not set")
        
        server_params = StdioServerParameters(
            command="node",
            args=["../kanban-mcp/dist/index.js"],
            env=os.environ.copy()
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                result = await session.call_tool(
                    "mcp_kanban_project_board_manager",
                    {
                        "action": "get_board_summary",
                        "boardId": self.board_id,
                        "includeTaskDetails": False
                    }
                )
                
                if result and hasattr(result, 'content'):
                    return json.loads(result.content[0].text)
                
                return {}
    
    def _is_available_task(self, card: Dict[str, Any]) -> bool:
        """Check if a task is in an available state"""
        list_name = card.get("listName", "").upper()
        available_states = ["TODO", "TO DO", "BACKLOG", "READY"]
        return any(state in list_name for state in available_states)
    
    def _card_to_task(self, card: Dict[str, Any]) -> Task:
        """Convert a kanban card to a Task object"""
        task_name = card.get("name") or card.get("title", "")
        
        # Parse dates
        created_at = datetime.now()
        updated_at = datetime.now()
        
        # Determine status
        list_name = card.get("listName", "").upper()
        if "DONE" in list_name:
            status = TaskStatus.DONE
        elif "PROGRESS" in list_name:
            status = TaskStatus.IN_PROGRESS
        elif "BLOCKED" in list_name:
            status = TaskStatus.BLOCKED
        else:
            status = TaskStatus.TODO
        
        return Task(
            id=card.get("id", ""),
            name=task_name,
            description=card.get("description", ""),
            status=status,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=created_at,
            updated_at=updated_at,
            due_date=None,
            estimated_hours=0.0,
            actual_hours=0.0,
            dependencies=[],
            labels=[]
        )