"""
Extended Kanban Client with Create Task Functionality

This module extends the SimpleMCPKanbanClient to add create_task functionality
for creating new tasks on the kanban board.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from src.integrations.mcp_kanban_client_simple import SimpleMCPKanbanClient
from src.core.models import Task, TaskStatus, Priority
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import os


class KanbanClientWithCreate(SimpleMCPKanbanClient):
    """
    Extended kanban client that adds create_task functionality.
    
    This client extends SimpleMCPKanbanClient to provide the ability to create
    new tasks on the kanban board, which is required for the natural language
    project creation features.
    """
    
    async def create_task(self, task_data: Dict[str, Any]) -> Task:
        """
        Create a new task on the kanban board.
        
        Parameters
        ----------
        task_data : Dict[str, Any]
            Dictionary containing task information:
            - name: Task title (required)
            - description: Task description
            - priority: Priority level (urgent, high, medium, low)
            - labels: List of labels/tags
            - estimated_hours: Time estimate
            - dependencies: List of task IDs this depends on
            
        Returns
        -------
        Task
            The created Task object with assigned ID
            
        Raises
        ------
        RuntimeError
            If board_id is not set or task creation fails
            
        Examples
        --------
        >>> task_data = {
        ...     "name": "Implement user authentication",
        ...     "description": "Add JWT-based auth to the API",
        ...     "priority": "high",
        ...     "labels": ["backend", "security"],
        ...     "estimated_hours": 16
        ... }
        >>> task = await client.create_task(task_data)
        >>> print(f"Created task: {task.name} with ID: {task.id}")
        """
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
                
                # First, find the appropriate list to add the task to
                # Default to "Backlog" or "TODO" list
                lists_result = await session.call_tool(
                    "mcp_kanban_list_manager",
                    {
                        "action": "get_all",
                        "boardId": self.board_id
                    }
                )
                
                target_list = None
                if lists_result and hasattr(lists_result, 'content') and lists_result.content:
                    lists_data = json.loads(lists_result.content[0].text)
                    lists = lists_data if isinstance(lists_data, list) else lists_data.get("items", [])
                    
                    # Look for Backlog or TODO list
                    for lst in lists:
                        list_name_lower = lst.get("name", "").lower()
                        if "backlog" in list_name_lower or "todo" in list_name_lower:
                            target_list = lst
                            break
                    
                    # If no backlog/todo list found, use the first list
                    if not target_list and lists:
                        target_list = lists[0]
                
                if not target_list:
                    raise RuntimeError("No suitable list found for new tasks")
                
                # Prepare card data
                card_name = task_data.get("name", "Untitled Task")
                card_description = task_data.get("description", "")
                
                # Create the card
                create_result = await session.call_tool(
                    "mcp_kanban_card_manager",
                    {
                        "action": "create",
                        "listId": target_list["id"],
                        "name": card_name,
                        "description": card_description,
                        "position": 65535  # Add at end of list
                    }
                )
                
                if not create_result or not hasattr(create_result, 'content'):
                    raise RuntimeError("Failed to create card")
                
                # Parse the created card
                created_card_data = json.loads(create_result.content[0].text)
                created_card = created_card_data if isinstance(created_card_data, dict) else created_card_data.get("item", {})
                
                # Add labels if provided
                if task_data.get("labels"):
                    await self._add_labels_to_card(session, created_card["id"], task_data["labels"])
                
                # Add subtasks/acceptance criteria if provided
                if task_data.get("acceptance_criteria") or task_data.get("subtasks"):
                    checklist_items = []
                    
                    # Add acceptance criteria as checklist items
                    if task_data.get("acceptance_criteria"):
                        print(f"DEBUG: Found {len(task_data['acceptance_criteria'])} acceptance criteria for task '{card_name}'")
                        for criteria in task_data["acceptance_criteria"]:
                            checklist_items.append(f"✓ {criteria}")
                    
                    # Add subtasks as checklist items
                    if task_data.get("subtasks"):
                        print(f"DEBUG: Found {len(task_data['subtasks'])} subtasks for task '{card_name}'")
                        for subtask in task_data["subtasks"]:
                            checklist_items.append(f"• {subtask}")
                    
                    if checklist_items:
                        print(f"DEBUG: Adding {len(checklist_items)} checklist items to card")
                        await self._add_checklist_items(session, created_card["id"], checklist_items)
                
                # Add initial comment with task metadata
                metadata_comment = self._build_metadata_comment(task_data)
                if metadata_comment:
                    await session.call_tool(
                        "mcp_kanban_comment_manager",
                        {
                            "action": "create",
                            "cardId": created_card["id"],
                            "text": metadata_comment
                        }
                    )
                
                # Convert the created card to a Task object
                created_card["listName"] = target_list.get("name", "")
                task = self._card_to_task(created_card)
                
                # Override with provided data
                if "priority" in task_data:
                    task.priority = self._parse_priority(task_data["priority"])
                if "estimated_hours" in task_data:
                    task.estimated_hours = float(task_data["estimated_hours"])
                if "labels" in task_data:
                    task.labels = task_data["labels"]
                if "dependencies" in task_data:
                    task.dependencies = task_data["dependencies"]
                
                return task
    
    def _parse_priority(self, priority_str: str) -> Priority:
        """
        Parse priority string to Priority enum.
        
        Parameters
        ----------
        priority_str : str
            Priority string (urgent, high, medium, low)
            
        Returns
        -------
        Priority
            Corresponding Priority enum value
        """
        priority_map = {
            "urgent": Priority.URGENT,
            "high": Priority.HIGH,
            "medium": Priority.MEDIUM,
            "low": Priority.LOW
        }
        return priority_map.get(priority_str.lower(), Priority.MEDIUM)
    
    def _build_metadata_comment(self, task_data: Dict[str, Any]) -> Optional[str]:
        """
        Build a metadata comment for the task.
        
        Parameters
        ----------
        task_data : Dict[str, Any]
            Task data containing metadata
            
        Returns
        -------
        Optional[str]
            Formatted metadata comment or None if no metadata
        """
        metadata_parts = []
        
        if task_data.get("estimated_hours"):
            metadata_parts.append(f"⏱️ Estimated: {task_data['estimated_hours']} hours")
        
        if task_data.get("priority"):
            priority_emoji = {
                "urgent": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢"
            }
            emoji = priority_emoji.get(task_data["priority"].lower(), "⚪")
            metadata_parts.append(f"{emoji} Priority: {task_data['priority'].upper()}")
        
        if task_data.get("dependencies"):
            deps = ", ".join(task_data["dependencies"])
            metadata_parts.append(f"🔗 Dependencies: {deps}")
        
        if metadata_parts:
            header = "📋 Task Metadata (Auto-generated)\n"
            return header + "\n".join(metadata_parts)
        
        return None
    
    async def _add_labels_to_card(self, session: Any, card_id: str, labels: List[str]) -> None:
        """
        Add labels to a card, creating them if necessary.
        
        Parameters
        ----------
        session : Any
            MCP client session
        card_id : str
            ID of the card to add labels to
        labels : List[str]
            List of label names to add
        """
        try:
            # Get board ID from the first list
            lists_result = await session.call_tool(
                "mcp_kanban_list_manager",
                {
                    "action": "get_all",
                    "boardId": self.board_id
                }
            )
            
            if not lists_result or not hasattr(lists_result, 'content') or not lists_result.content:
                return
                
            try:
                lists_data = json.loads(lists_result.content[0].text)
            except (json.JSONDecodeError, IndexError) as e:
                print(f"Failed to parse lists response: {e}")
                return
            lists = lists_data if isinstance(lists_data, list) else lists_data.get("items", [])
            
            if not lists:
                return
                
            board_id = lists[0].get("boardId")
            if not board_id:
                return
            
            # Get existing labels
            labels_result = await session.call_tool(
                "mcp_kanban_label_manager",
                {
                    "action": "get_all",
                    "boardId": board_id
                }
            )
            
            existing_labels = {}
            if labels_result and hasattr(labels_result, 'content') and labels_result.content:
                try:
                    labels_data = json.loads(labels_result.content[0].text)
                except (json.JSONDecodeError, IndexError) as e:
                    print(f"Failed to parse labels response: {e}")
                    labels_data = {}
                existing_list = labels_data if isinstance(labels_data, list) else labels_data.get("items", [])
                for label in existing_list:
                    existing_labels[label["name"].lower()] = label["id"]
            
            # Define label colors based on Planka's allowed color names
            label_colors = {
                'frontend': 'lagoon-blue',
                'backend': 'bright-moss',
                'database': 'berry-red',
                'api': 'egg-yellow',
                'testing': 'morning-sky',
                'bug': 'berry-red',
                'feature': 'bright-moss',
                'enhancement': 'lagoon-blue',
                'documentation': 'light-concrete',
                'high': 'berry-red',
                'medium': 'egg-yellow',
                'low': 'bright-moss',
                'setup': 'pink-tulip',
                'deployment': 'pumpkin-orange',
                'security': 'berry-red',
                'performance': 'coral-green',
                'ui': 'pink-tulip',
                'ux': 'pink-tulip',
                'devops': 'midnight-blue',
                'infrastructure': 'midnight-blue',
                'priority': 'berry-red',    # For priority tags
                'skill': 'lagoon-blue',     # For skill tags
                'complexity': 'light-concrete', # For complexity tags
                'component': 'bright-moss',     # For component tags
                'type': 'pumpkin-orange'        # For type tags
            }
            
            # Process each label
            for label_name in labels:
                label_lower = label_name.lower()
                label_id = None
                
                # Check if label exists
                if label_lower in existing_labels:
                    label_id = existing_labels[label_lower]
                else:
                    # Create new label
                    color = label_colors.get(label_lower, 'light-concrete')  # Default gray
                    
                    # Extract color from label taxonomy (e.g., "component:frontend" -> "frontend")
                    if ':' in label_name:
                        category, label_type = label_name.split(':', 1)
                        # First try the full label, then the type, then the category
                        color = label_colors.get(label_lower, 
                                label_colors.get(label_type.lower(), 
                                    label_colors.get(category.lower(), 'light-concrete')))
                    
                    try:
                        create_label_result = await session.call_tool(
                            "mcp_kanban_label_manager",
                            {
                                "action": "create",
                                "boardId": board_id,
                                "name": label_name,
                                "color": color
                            }
                        )
                        
                        if create_label_result and hasattr(create_label_result, 'content') and create_label_result.content:
                            try:
                                label_data = json.loads(create_label_result.content[0].text)
                                label_info = label_data if isinstance(label_data, dict) else label_data.get("item", {})
                            except (json.JSONDecodeError, IndexError) as e:
                                print(f"Failed to parse label creation response for '{label_name}': {e}")
                                continue
                            label_id = label_info.get("id")
                    except Exception as e:
                        print(f"Failed to create label '{label_name}': {e}")
                        continue
                
                # Add label to card
                if label_id:
                    try:
                        await session.call_tool(
                            "mcp_kanban_label_manager",
                            {
                                "action": "add_to_card",
                                "cardId": card_id,
                                "labelId": label_id
                            }
                        )
                    except Exception as e:
                        print(f"Failed to add label '{label_name}' to card: {e}")
                        
        except Exception as e:
            print(f"Error in _add_labels_to_card: {e}")
            # Don't fail task creation if labels fail
    
    async def _add_checklist_items(self, session: Any, card_id: str, items: List[str]) -> None:
        """
        Add checklist items (subtasks/acceptance criteria) to a card.
        
        Parameters
        ----------
        session : Any
            MCP client session
        card_id : str
            ID of the card to add items to
        items : List[str]
            List of checklist item names
        """
        try:
            position = 65536
            for item in items:
                try:
                    result = await session.call_tool(
                        "mcp_kanban_task_manager",
                        {
                            "action": "create",
                            "cardId": card_id,
                            "name": item,
                            "position": position
                        }
                    )
                    if result and hasattr(result, 'content'):
                        print(f"DEBUG: Created checklist item '{item[:30]}...' - response has content")
                    else:
                        print(f"DEBUG: Created checklist item '{item[:30]}...' - no response content")
                    position += 65536
                except Exception as e:
                    print(f"Failed to create checklist item '{item}': {e}")
                    
        except Exception as e:
            print(f"Error in _add_checklist_items: {e}")
            # Don't fail task creation if checklist fails
    
    async def create_tasks_batch(self, tasks_data: list[Dict[str, Any]]) -> list[Task]:
        """
        Create multiple tasks in batch.
        
        Parameters
        ----------
        tasks_data : list[Dict[str, Any]]
            List of task data dictionaries
            
        Returns
        -------
        list[Task]
            List of created Task objects
            
        Notes
        -----
        This method creates tasks sequentially to maintain order and
        handle dependencies properly.
        """
        created_tasks = []
        
        for task_data in tasks_data:
            try:
                task = await self.create_task(task_data)
                created_tasks.append(task)
            except Exception as e:
                print(f"Failed to create task '{task_data.get('name', 'Unknown')}': {str(e)}")
                # Continue with other tasks even if one fails
                continue
        
        return created_tasks