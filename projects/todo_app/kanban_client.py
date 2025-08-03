"""
Kanban client module for interacting with the MCP server.

This module provides the KanbanClient class for managing cards, labels,
and other kanban operations.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from mcp import ClientSession


class KanbanClient:
    """Client for interacting with the Kanban MCP server."""
    
    def __init__(self, session: ClientSession):
        """
        Initialize the Kanban client.
        
        Parameters
        ----------
        session : ClientSession
            The MCP client session
        """
        self.session = session
        self.project_id = None
        self.board_id = None
        self.label_ids = {}
        
    async def find_project(self, project_name: str) -> bool:
        """
        Find a project by name.
        
        Parameters
        ----------
        project_name : str
            Name of the project to find
            
        Returns
        -------
        bool
            True if project was found, False otherwise
        """
        print(f"\n📋 Finding {project_name} project...")
        
        result = await self.session.call_tool(
            "mcp_kanban_project_board_manager",
            {"action": "get_projects", "page": 1, "perPage": 25},
        )
        
        projects_data = json.loads(result.content[0].text)
        
        for project in projects_data["items"]:
            if project["name"] == project_name:
                self.project_id = project["id"]
                print(f"✅ Found project: {project['name']} (ID: {self.project_id})")
                
                # Find the board
                if "boards" in projects_data.get("included", {}):
                    for board in projects_data["included"]["boards"]:
                        if board["projectId"] == self.project_id:
                            self.board_id = board["id"]
                            print(f"✅ Found board: {board['name']} (ID: {self.board_id})")
                            return True
                            
        return False
    
    async def clear_existing_cards(self) -> None:
        """Clear all existing cards from the board."""
        print("\n🧹 Clearing existing cards...")
        
        try:
            # Get all lists first
            lists_result = await self.session.call_tool(
                "mcp_kanban_list_manager",
                {"action": "get_all", "boardId": self.board_id},
            )
            lists = json.loads(lists_result.content[0].text)
            
            # Get cards from each list
            for lst in lists:
                try:
                    cards_result = await self.session.call_tool(
                        "mcp_kanban_card_manager",
                        {"action": "get_by_list", "listId": lst["id"]},
                    )
                    
                    if cards_result.content and cards_result.content[0].text:
                        try:
                            cards = json.loads(cards_result.content[0].text)
                            if isinstance(cards, list):
                                for card in cards:
                                    await self.session.call_tool(
                                        "mcp_kanban_card_manager",
                                        {"action": "delete", "cardId": card["id"]},
                                    )
                                    print(f"  ✅ Deleted: {card.get('name', 'Unnamed')}")
                        except:
                            pass
                except:
                    pass
        except Exception as e:
            print(f"  ⚠️  Error clearing cards: {str(e)}")
    
    async def get_backlog_list(self) -> Optional[Dict[str, Any]]:
        """Get the backlog list from the board."""
        print("\n📋 Getting lists...")
        
        lists_result = await self.session.call_tool(
            "mcp_kanban_list_manager",
            {"action": "get_all", "boardId": self.board_id},
        )
        lists = json.loads(lists_result.content[0].text)
        
        for lst in lists:
            if "BACKLOG" in lst["name"].upper():
                print(f"✅ Found list: {lst['name']} (ID: {lst['id']})")
                return lst
                
        return None
    
    async def create_labels(self, label_colors: Dict[str, str]) -> None:
        """
        Create labels on the board.
        
        Parameters
        ----------
        label_colors : Dict[str, str]
            Mapping of label names to colors
        """
        print("\n🏷️  Creating labels...")
        
        for label_name, color in label_colors.items():
            try:
                # Try to create the label
                result = await self.session.call_tool(
                    "mcp_kanban_label_manager",
                    {
                        "action": "create",
                        "boardId": self.board_id,
                        "name": label_name,
                        "color": color,
                    },
                )
                label = json.loads(result.content[0].text)
                self.label_ids[label_name] = label["id"]
                print(f"  ✅ Created label: {label_name}")
            except:
                # Label might exist, try to get it
                try:
                    labels_result = await self.session.call_tool(
                        "mcp_kanban_label_manager",
                        {"action": "get_all", "boardId": self.board_id},
                    )
                    labels = json.loads(labels_result.content[0].text)
                    
                    for existing_label in labels:
                        if existing_label["name"] == label_name:
                            self.label_ids[label_name] = existing_label["id"]
                            print(f"  ✅ Found existing label: {label_name}")
                            break
                except:
                    print(f"  ❌ Could not create/find label: {label_name}")
    
    async def create_card(
        self,
        list_id: str,
        title: str,
        description: str,
        labels: List[str] = None,
        subtasks: List[str] = None,
        time_estimate: int = 8,
        priority: str = "medium",
        due_days: int = 7,
        dependencies: List[str] = None,
    ) -> Optional[str]:
        """
        Create a card with all its details.
        
        Parameters
        ----------
        list_id : str
            ID of the list to create the card in
        title : str
            Card title
        description : str
            Card description
        labels : List[str], optional
            Label names to apply
        subtasks : List[str], optional
            Subtask names to create
        time_estimate : int, optional
            Time estimate in hours
        priority : str, optional
            Priority level
        due_days : int, optional
            Days until due date
        dependencies : List[str], optional
            List of dependency card titles
            
        Returns
        -------
        Optional[str]
            Card ID if created successfully, None otherwise
        """
        try:
            # Create the card
            result = await self.session.call_tool(
                "mcp_kanban_card_manager",
                {
                    "action": "create",
                    "listId": list_id,
                    "name": title,
                    "description": description,
                },
            )
            
            card = json.loads(result.content[0].text)
            card_id = card["id"]
            print(f"  ✅ Created card ID: {card_id}")
            
            # Add labels
            if labels:
                for label_name in labels:
                    if label_name in self.label_ids:
                        try:
                            await self.session.call_tool(
                                "mcp_kanban_label_manager",
                                {
                                    "action": "add_to_card",
                                    "cardId": card_id,
                                    "labelId": self.label_ids[label_name],
                                },
                            )
                            print(f"  ✅ Added label: {label_name}")
                        except Exception as e:
                            print(f"  ❌ Could not add label {label_name}: {str(e)}")
            
            # Create subtasks
            if subtasks:
                print(f"  📋 Creating {len(subtasks)} subtasks...")
                for i, subtask_name in enumerate(subtasks[:10], 1):  # Limit to 10
                    try:
                        await self.session.call_tool(
                            "mcp_kanban_task_manager",
                            {
                                "action": "create",
                                "cardId": card_id,
                                "name": subtask_name,
                                "position": i,
                            },
                        )
                    except:
                        pass
                print(f"  ✅ Created subtasks")
            
            # Add time estimate and details
            due_date = datetime.now() + timedelta(days=due_days)
            details_comment = f"""📊 **Task Details**
⏱️ **Time Estimate**: {time_estimate} hours
📅 **Due Date**: {due_date.strftime('%B %d, %Y')}
🎯 **Priority**: {priority.capitalize()}
👥 **Team Size**: 1-2 developers"""
            
            await self.session.call_tool(
                "mcp_kanban_comment_manager",
                {
                    "action": "create",
                    "cardId": card_id,
                    "text": details_comment,
                },
            )
            
            # Add dependencies if any
            if dependencies:
                deps_comment = "🔗 **Dependencies**:\n" + "\n".join(
                    f"- {name}" for name in dependencies
                )
                await self.session.call_tool(
                    "mcp_kanban_comment_manager",
                    {
                        "action": "create",
                        "cardId": card_id,
                        "text": deps_comment,
                    },
                )
            
            return card_id
            
        except Exception as e:
            print(f"  ❌ Error creating card: {str(e)}")
            return None