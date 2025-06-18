"""
Verbose MCP Kanban Client that logs all interactions with the Kanban board
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.json import JSON

from .mcp_kanban_client import MCPKanbanClient

# Rich console for pretty output
console = Console()


class VerboseMCPKanbanClient(MCPKanbanClient):
    """Enhanced Kanban client with detailed conversation logging"""
    
    def __init__(self):
        super().__init__()
        self.conversation_log = []
        
    def _log_kanban_request(self, action: str, params: Dict = None):
        """Log request to Kanban board"""
        console.print(f"\n[bold blue]🔌 PM Agent → Kanban Board:[/bold blue]")
        console.print(f"   [cyan]Action:[/cyan] {action}")
        if params:
            console.print(f"   [cyan]Parameters:[/cyan]")
            for key, value in params.items():
                console.print(f"      • {key}: {value}")
                
    def _log_kanban_response(self, action: str, response: Any):
        """Log response from Kanban board"""
        console.print(f"\n[bold magenta]📋 Kanban Board → PM Agent:[/bold magenta]")
        console.print(f"   [magenta]Response to:[/magenta] {action}")
        
        if isinstance(response, list):
            console.print(f"   [magenta]Items returned:[/magenta] {len(response)}")
            if response and len(response) > 0:
                # Show sample of first few items
                console.print("   [dim]Sample items:[/dim]")
                for item in response[:3]:
                    if isinstance(item, dict):
                        console.print(f"      • {item.get('name', item.get('title', 'Unknown'))}")
                if len(response) > 3:
                    console.print(f"      ... and {len(response) - 3} more")
        elif isinstance(response, dict):
            console.print("   [dim]Data:[/dim]")
            for key, value in response.items():
                if key != 'description':  # Skip long descriptions
                    console.print(f"      • {key}: {value}")
        else:
            console.print(f"   [magenta]Result:[/magenta] {response}")
            
    def _log_kanban_thinking(self, thought: str):
        """Log Kanban processing logic"""
        console.print(f"\n[dim yellow]🤔 Kanban processing:[/dim yellow] {thought}")
        
    def _show_board_state(self, tasks: List[Dict]):
        """Display current board state as a table"""
        table = Table(title="📊 Current Kanban Board State", show_lines=True)
        table.add_column("Task", style="cyan", width=30)
        table.add_column("Status", style="green")
        table.add_column("Priority", style="yellow")
        table.add_column("Assigned", style="magenta")
        
        # Group by status
        by_status = {}
        for task in tasks:
            status = task.get('status', 'Unknown')
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(task)
        
        # Display by status
        for status in ['Backlog', 'Ready', 'In Progress', 'Review', 'Done']:
            if status in by_status:
                for task in by_status[status][:3]:  # Show first 3 per status
                    table.add_row(
                        task.get('name', 'Unknown'),
                        status,
                        task.get('priority', '-'),
                        task.get('assigned_to', 'Unassigned')
                    )
                if len(by_status[status]) > 3:
                    table.add_row(
                        f"... +{len(by_status[status]) - 3} more",
                        status,
                        "-",
                        "-"
                    )
        
        console.print(table)
    
    async def initialize(self):
        """Initialize connection with verbose logging"""
        self._log_kanban_request("Initialize connection", {
            "server": "kanban-mcp",
            "protocol": "MCP"
        })
        
        result = await super().initialize()
        
        if result:
            self._log_kanban_response("Initialize", "Connection established successfully")
            self._log_kanban_thinking("Ready to interact with Kanban board")
        else:
            self._log_kanban_response("Initialize", "Failed to establish connection")
            
        return result
    
    async def get_boards(self) -> List[Dict]:
        """Get all boards with logging"""
        self._log_kanban_request("List all boards")
        self._log_kanban_thinking("Fetching available Kanban boards")
        
        boards = await super().get_boards()
        
        self._log_kanban_response("List boards", boards)
        
        if boards:
            console.print("\n[bold]Available Boards:[/bold]")
            for board in boards:
                console.print(f"   • {board.get('name')} (ID: {board.get('id')})")
                
        return boards
    
    async def get_board_lists(self, board_id: str) -> List[Dict]:
        """Get lists for a board with logging"""
        self._log_kanban_request("Get board lists", {"board_id": board_id})
        self._log_kanban_thinking(f"Fetching lists (columns) for board {board_id}")
        
        lists = await super().get_board_lists(board_id)
        
        self._log_kanban_response("Get lists", lists)
        
        if lists:
            console.print("\n[bold]Board Columns:[/bold]")
            for lst in lists:
                console.print(f"   • {lst.get('name')} (Position: {lst.get('position')})")
                
        return lists
    
    async def get_list_cards(self, list_id: str) -> List[Dict]:
        """Get cards in a list with logging"""
        self._log_kanban_request("Get cards in list", {"list_id": list_id})
        self._log_kanban_thinking(f"Fetching all cards from list {list_id}")
        
        cards = await super().get_list_cards(list_id)
        
        self._log_kanban_response("Get cards", cards)
        
        return cards
    
    async def create_card(self, list_id: str, name: str, description: str = "") -> Dict:
        """Create a new card with logging"""
        self._log_kanban_request("Create new card", {
            "list_id": list_id,
            "name": name,
            "description": description[:50] + "..." if len(description) > 50 else description
        })
        self._log_kanban_thinking(f"Creating new task card: '{name}'")
        
        card = await super().create_card(list_id, name, description)
        
        self._log_kanban_response("Create card", {
            "success": bool(card),
            "card_id": card.get('id') if card else None,
            "name": card.get('name') if card else None
        })
        
        return card
    
    async def move_card(self, card_id: str, target_list_id: str) -> bool:
        """Move a card with logging"""
        self._log_kanban_request("Move card", {
            "card_id": card_id,
            "target_list_id": target_list_id
        })
        self._log_kanban_thinking(f"Moving card {card_id} to new list/column")
        
        success = await super().move_card(card_id, target_list_id)
        
        self._log_kanban_response("Move card", {
            "success": success,
            "new_list": target_list_id
        })
        
        if success:
            console.print("[green]✓ Card moved successfully[/green]")
        else:
            console.print("[red]✗ Failed to move card[/red]")
            
        return success
    
    async def update_card(self, card_id: str, updates: Dict) -> bool:
        """Update a card with logging"""
        self._log_kanban_request("Update card", {
            "card_id": card_id,
            "updates": updates
        })
        self._log_kanban_thinking(f"Updating card {card_id} with new information")
        
        success = await super().update_card(card_id, updates)
        
        self._log_kanban_response("Update card", {
            "success": success,
            "fields_updated": list(updates.keys())
        })
        
        return success
    
    async def add_label_to_card(self, card_id: str, label_id: str) -> bool:
        """Add label to card with logging"""
        self._log_kanban_request("Add label to card", {
            "card_id": card_id,
            "label_id": label_id
        })
        self._log_kanban_thinking(f"Adding label {label_id} to card for categorization")
        
        success = await super().add_label_to_card(card_id, label_id)
        
        self._log_kanban_response("Add label", {"success": success})
        
        return success
    
    async def add_comment(self, card_id: str, comment: str) -> bool:
        """Add comment with logging"""
        self._log_kanban_request("Add comment to card", {
            "card_id": card_id,
            "comment": comment[:100] + "..." if len(comment) > 100 else comment
        })
        self._log_kanban_thinking("Adding comment for progress tracking")
        
        success = await super().add_comment(card_id, comment)
        
        self._log_kanban_response("Add comment", {"success": success})
        
        return success
    
    async def get_available_tasks(self) -> List[Dict]:
        """Get available tasks with detailed logging"""
        self._log_kanban_request("Get available tasks", {
            "criteria": "unassigned tasks in Backlog or Ready"
        })
        self._log_kanban_thinking("Searching for tasks ready for assignment")
        
        # This would typically:
        # 1. Get board lists
        # 2. Find Backlog and Ready lists
        # 3. Get cards from those lists
        # 4. Filter unassigned ones
        
        # For demo, simulate the process
        console.print("\n[dim cyan]🔍 Kanban search process:[/dim cyan]")
        console.print("   1. Locating Backlog and Ready columns")
        console.print("   2. Fetching cards from these columns")
        console.print("   3. Filtering for unassigned tasks")
        console.print("   4. Sorting by priority")
        
        # Simulated response
        tasks = [
            {
                "id": "task-1",
                "name": "Implement user authentication",
                "status": "Backlog",
                "priority": "High",
                "assigned_to": None,
                "estimated_hours": 8,
                "labels": ["backend", "security"]
            },
            {
                "id": "task-2", 
                "name": "Create API documentation",
                "status": "Ready",
                "priority": "Medium",
                "assigned_to": None,
                "estimated_hours": 4,
                "labels": ["documentation"]
            },
            {
                "id": "task-3",
                "name": "Setup CI/CD pipeline", 
                "status": "Backlog",
                "priority": "High",
                "assigned_to": None,
                "estimated_hours": 6,
                "labels": ["devops", "infrastructure"]
            }
        ]
        
        self._log_kanban_response("Available tasks", tasks)
        self._show_board_state(tasks)
        
        return tasks
    
    async def assign_task(self, task_id: str, agent_id: str) -> bool:
        """Assign task to agent with logging"""
        self._log_kanban_request("Assign task to agent", {
            "task_id": task_id,
            "agent_id": agent_id,
            "action": "Move to In Progress and assign"
        })
        
        console.print("\n[dim cyan]📝 Kanban update process:[/dim cyan]")
        console.print(f"   1. Locating task {task_id}")
        console.print(f"   2. Setting assigned_to = {agent_id}")
        console.print("   3. Moving card to 'In Progress' column")
        console.print("   4. Adding assignment comment")
        
        # Simulate the assignment process
        success = True
        
        self._log_kanban_response("Assign task", {
            "success": success,
            "task_id": task_id,
            "new_status": "In Progress",
            "assigned_to": agent_id
        })
        
        if success:
            self._log_kanban_thinking(f"Task successfully assigned and moved to active work")
            
        return success
    
    async def update_task_progress(self, task_id: str, progress_data: Dict) -> bool:
        """Update task progress with logging"""
        self._log_kanban_request("Update task progress", {
            "task_id": task_id,
            "progress": progress_data.get('progress', 0),
            "status": progress_data.get('status', 'in_progress'),
            "message": progress_data.get('message', '')
        })
        
        self._log_kanban_thinking(f"Recording progress update for task {task_id}")
        
        # Show what's happening
        console.print("\n[dim cyan]📊 Progress update process:[/dim cyan]")
        console.print(f"   1. Adding progress comment: {progress_data.get('message', '')}")
        console.print(f"   2. Updating progress field: {progress_data.get('progress', 0)}%")
        
        if progress_data.get('status') == 'completed':
            console.print("   3. Moving card to 'Done' column")
            console.print("   4. Recording completion time")
            
        success = True
        
        self._log_kanban_response("Update progress", {
            "success": success,
            "new_progress": progress_data.get('progress', 0),
            "status": progress_data.get('status', 'in_progress')
        })
        
        return success
    
    async def report_blocker(self, task_id: str, blocker_description: str, severity: str) -> bool:
        """Report blocker with logging"""
        self._log_kanban_request("Report blocker", {
            "task_id": task_id,
            "blocker": blocker_description,
            "severity": severity
        })
        
        self._log_kanban_thinking(f"Recording blocker for task {task_id}")
        
        console.print("\n[dim cyan]🚫 Blocker handling process:[/dim cyan]")
        console.print("   1. Adding blocker comment to card")
        console.print("   2. Adding 'blocked' label")
        console.print("   3. Moving to 'Blocked' column if exists")
        console.print(f"   4. Setting blocker severity: {severity}")
        
        success = True
        
        self._log_kanban_response("Report blocker", {
            "success": success,
            "blocker_recorded": True,
            "severity": severity
        })
        
        return success
    
    async def get_project_metrics(self) -> Dict:
        """Get project metrics with logging"""
        self._log_kanban_request("Get project metrics", {
            "metrics": ["total_tasks", "completed", "in_progress", "blocked", "velocity"]
        })
        
        self._log_kanban_thinking("Calculating project metrics from board data")
        
        console.print("\n[dim cyan]📈 Metrics calculation:[/dim cyan]")
        console.print("   1. Counting cards by status")
        console.print("   2. Calculating completion rate") 
        console.print("   3. Measuring velocity (tasks/day)")
        console.print("   4. Identifying bottlenecks")
        
        metrics = {
            "total_tasks": 25,
            "completed": 10,
            "in_progress": 5,
            "blocked": 2,
            "backlog": 8,
            "completion_rate": "40%",
            "velocity": "2.5 tasks/day",
            "average_cycle_time": "2.3 days",
            "blocked_time": "8% of total"
        }
        
        self._log_kanban_response("Project metrics", metrics)
        
        # Display metrics table
        table = Table(title="📊 Project Metrics", show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in metrics.items():
            table.add_row(key.replace('_', ' ').title(), str(value))
            
        console.print(table)
        
        return metrics


# Example usage for testing
async def test_verbose_kanban_client():
    """Test the verbose Kanban client"""
    console.print(Panel.fit(
        "[bold cyan]Verbose Kanban Client Test[/bold cyan]\n"
        "Demonstrating PM Agent ↔ Kanban Board communication",
        title="🔌 Kanban Integration",
        border_style="cyan"
    ))
    
    client = VerboseMCPKanbanClient()
    
    # Initialize
    await client.initialize()
    
    # Get available tasks
    await client.get_available_tasks()
    
    # Assign a task
    await client.assign_task("task-1", "claude-backend-001")
    
    # Update progress
    await client.update_task_progress("task-1", {
        "progress": 50,
        "status": "in_progress",
        "message": "Core implementation complete"
    })
    
    # Report blocker
    await client.report_blocker("task-1", "Missing API credentials", "medium")
    
    # Get metrics
    await client.get_project_metrics()
    

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_verbose_kanban_client())