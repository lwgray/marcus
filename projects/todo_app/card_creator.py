#!/usr/bin/env python3
"""
Todo App card creator using Marcus infrastructure.

This module provides the main card creation functionality for the Todo App,
leveraging Marcus's KanbanClient and error handling framework.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

from src.integrations.kanban_client import KanbanClient
from src.core.models import Task, TaskStatus, Priority
from src.core.error_framework import (
    KanbanIntegrationError,
    ErrorContext,
    error_context,
    with_retry,
    RetryConfig,
)
from src.logging import ConversationLogger

from .cards.constants import LABEL_COLORS, DEFAULT_TIME_ESTIMATE, DEFAULT_PRIORITY
from .cards.card_loader import load_card_data

# Set up logging
logger = logging.getLogger(__name__)


class TodoAppCardCreator:
    """
    Creates Todo App development cards using Marcus infrastructure.
    
    This class leverages Marcus's KanbanClient and error handling
    framework for robust card creation with the kanban-mcp server.
    """
    
    def __init__(self):
        """Initialize the Todo App card creator."""
        self.client = KanbanClient()
        self.conversation_logger = ConversationLogger()
        self.card_id_map: Dict[str, str] = {}
        self.created_count = 0
        self.label_ids: Dict[str, str] = {}
        
    async def initialize_session(self) -> ClientSession:
        """
        Initialize MCP session for direct kanban operations.
        
        Returns
        -------
        ClientSession
            Initialized MCP client session
        """
        server_params = StdioServerParameters(
            command="node",
            args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
            env=os.environ.copy(),
        )
        
        # Use stdio_client as context manager
        self.read, self.write = await stdio_client(server_params).__aenter__()
        session = ClientSession(self.read, self.write)
        await session.initialize()
        
        logger.info("✅ Connected to kanban-mcp")
        return session
    
    @with_retry(RetryConfig(max_attempts=3, base_delay=1.0))
    async def find_project(self, session: ClientSession, project_name: str = "Task Master Test") -> bool:
        """
        Find the project and board.
        
        Parameters
        ----------
        session : ClientSession
            MCP client session
        project_name : str
            Name of the project to find
            
        Returns
        -------
        bool
            True if found, False otherwise
        """
        with error_context("find_project", project_name=project_name):
            logger.info(f"📋 Finding {project_name} project...")
            
            result = await session.call_tool(
                "mcp_kanban_project_board_manager",
                {"action": "get_projects", "page": 1, "perPage": 25},
            )
            
            projects_data = json.loads(result.content[0].text)
            
            for project in projects_data["items"]:
                if project["name"] == project_name:
                    self.client.project_id = project["id"]
                    logger.info(f"✅ Found project: {project['name']} (ID: {self.client.project_id})")
                    
                    # Find the board
                    if "boards" in projects_data.get("included", {}):
                        for board in projects_data["included"]["boards"]:
                            if board["projectId"] == self.client.project_id:
                                self.client.board_id = board["id"]
                                logger.info(f"✅ Found board: {board['name']} (ID: {self.client.board_id})")
                                
                                self.conversation_logger.log_pm_thinking(
                                    f"Located project {project_name} for card creation"
                                )
                                return True
                                
            return False
    
    async def clear_existing_cards(self, session: ClientSession) -> None:
        """
        Clear existing cards from the board.
        
        Parameters
        ----------
        session : ClientSession
            MCP client session
        """
        with error_context("clear_cards", board_id=self.client.board_id):
            logger.info("🧹 Clearing existing cards...")
            
            try:
                # Get all lists first
                lists_result = await session.call_tool(
                    "mcp_kanban_list_manager",
                    {"action": "get_all", "boardId": self.client.board_id},
                )
                lists = json.loads(lists_result.content[0].text)
                
                # Get cards from each list and delete them
                for lst in lists:
                    try:
                        cards_result = await session.call_tool(
                            "mcp_kanban_card_manager",
                            {"action": "get_by_list", "listId": lst["id"]},
                        )
                        
                        if cards_result.content and cards_result.content[0].text:
                            cards = json.loads(cards_result.content[0].text)
                            if isinstance(cards, list):
                                for card in cards:
                                    await session.call_tool(
                                        "mcp_kanban_card_manager",
                                        {"action": "delete", "cardId": card["id"]},
                                    )
                                    logger.info(f"  ✅ Deleted: {card.get('name', 'Unnamed')}")
                    except:
                        pass
                        
            except Exception as e:
                logger.warning(f"  ⚠️  Error clearing cards: {str(e)}")
    
    async def get_backlog_list(self, session: ClientSession) -> Optional[Dict]:
        """
        Get the backlog list from the board.
        
        Parameters
        ----------
        session : ClientSession
            MCP client session
            
        Returns
        -------
        Optional[Dict]
            Backlog list data or None
        """
        logger.info("📋 Getting lists...")
        
        lists_result = await session.call_tool(
            "mcp_kanban_list_manager",
            {"action": "get_all", "boardId": self.client.board_id},
        )
        lists = json.loads(lists_result.content[0].text)
        
        for lst in lists:
            if "BACKLOG" in lst["name"].upper():
                logger.info(f"✅ Found list: {lst['name']} (ID: {lst['id']})")
                return lst
                
        return None
    
    async def create_labels(self, session: ClientSession) -> None:
        """
        Create or find labels for the cards.
        
        Parameters
        ----------
        session : ClientSession
            MCP client session
        """
        with error_context("create_labels"):
            logger.info("🏷️  Creating labels...")
            
            for label_name, color in LABEL_COLORS.items():
                try:
                    result = await session.call_tool(
                        "mcp_kanban_label_manager",
                        {
                            "action": "create",
                            "boardId": self.client.board_id,
                            "name": label_name,
                            "color": color,
                        },
                    )
                    label = json.loads(result.content[0].text)
                    self.label_ids[label_name] = label["id"]
                    logger.info(f"  ✅ Created label: {label_name}")
                except:
                    # Try to find existing label
                    try:
                        labels_result = await session.call_tool(
                            "mcp_kanban_label_manager",
                            {"action": "get_all", "boardId": self.client.board_id},
                        )
                        labels = json.loads(labels_result.content[0].text)
                        
                        for existing_label in labels:
                            if existing_label["name"] == label_name:
                                self.label_ids[label_name] = existing_label["id"]
                                logger.info(f"  ✅ Found existing label: {label_name}")
                                break
                    except:
                        logger.warning(f"  ❌ Could not create/find label: {label_name}")
    
    async def create_card(
        self,
        session: ClientSession,
        list_id: str,
        card_data: Dict,
        enhanced_data: Dict,
    ) -> Optional[str]:
        """
        Create a single card with all details.
        
        Parameters
        ----------
        session : ClientSession
            MCP client session
        list_id : str
            ID of the list to create card in
        card_data : Dict
            Basic card data from JSON
        enhanced_data : Dict
            Enhanced card data with full descriptions
            
        Returns
        -------
        Optional[str]
            Card ID if created, None otherwise
        """
        try:
            # Create the card
            result = await session.call_tool(
                "mcp_kanban_card_manager",
                {
                    "action": "create",
                    "listId": list_id,
                    "name": card_data["title"],
                    "description": enhanced_data.get("description", card_data["description"]),
                },
            )
            
            card = json.loads(result.content[0].text)
            card_id = card["id"]
            logger.info(f"  ✅ Created card ID: {card_id}")
            
            # Add labels
            for label_name in enhanced_data.get("labels", card_data.get("labels", [])):
                if label_name in self.label_ids:
                    try:
                        await session.call_tool(
                            "mcp_kanban_label_manager",
                            {
                                "action": "add_to_card",
                                "cardId": card_id,
                                "labelId": self.label_ids[label_name],
                            },
                        )
                        logger.info(f"  ✅ Added label: {label_name}")
                    except Exception as e:
                        logger.warning(f"  ❌ Could not add label {label_name}: {str(e)}")
            
            # Create subtasks
            subtasks = enhanced_data.get("subtasks", [])
            if subtasks:
                logger.info(f"  📋 Creating {len(subtasks)} subtasks...")
                for i, subtask_name in enumerate(subtasks[:10], 1):
                    try:
                        await session.call_tool(
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
                logger.info(f"  ✅ Created subtasks")
            
            # Add time estimate and details
            due_date_str = card_data.get("dueDate", "7 days")
            due_days = int(due_date_str.split()[0]) if " day" in due_date_str else 7
            due_date = datetime.now() + timedelta(days=due_days)
            
            time_estimate = enhanced_data.get("timeEstimate", DEFAULT_TIME_ESTIMATE)
            priority = enhanced_data.get("priority", DEFAULT_PRIORITY)
            
            details_comment = f"""📊 **Task Details**
⏱️ **Time Estimate**: {time_estimate} hours
📅 **Due Date**: {due_date.strftime('%B %d, %Y')}
🎯 **Priority**: {priority.capitalize()}
👥 **Team Size**: 1-2 developers"""
            
            await session.call_tool(
                "mcp_kanban_comment_manager",
                {
                    "action": "create",
                    "cardId": card_id,
                    "text": details_comment,
                },
            )
            
            # Log task assignment
            self.conversation_logger.log_task_assignment(
                task_id=card_id,
                worker_id="todo_app_creator",
                assignment_reason="Initial project setup",
                task_details={
                    "title": card_data["title"],
                    "priority": priority,
                    "effort": time_estimate,
                }
            )
            
            return card_id
            
        except Exception as e:
            logger.error(f"  ❌ Error creating card: {str(e)}")
            return None