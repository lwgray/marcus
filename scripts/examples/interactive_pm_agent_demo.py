#!/usr/bin/env python3
"""
Interactive PM Agent Demo Script
Allows users to experience PM Agent capabilities through guided examples
"""

import os
import sys
import time
import json
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import track

console = Console()

# Demo task templates
DEMO_TASKS = {
    "1": {
        "name": "Quick API Endpoint",
        "description": "Create a simple REST API endpoint",
        "tasks": [
            {
                "title": "Create Weather API Endpoint",
                "description": """Create a GET /api/weather endpoint that:
- Accepts a 'city' query parameter
- Returns mock weather data in JSON format
- Includes temperature, conditions, and humidity
- Has proper error handling for missing city parameter""",
                "labels": ["backend", "api", "quick-task"],
                "estimated_time": "5 minutes"
            }
        ]
    },
    "2": {
        "name": "CRUD System",
        "description": "Build a complete CRUD system with database",
        "tasks": [
            {
                "title": "Create Product Database Model",
                "description": "SQLAlchemy model for products with: id, name, price, description, stock_quantity",
                "labels": ["backend", "database"],
                "priority": "high"
            },
            {
                "title": "Build Product CRUD API",
                "description": "REST API with GET, POST, PUT, DELETE for products",
                "labels": ["backend", "api"],
                "depends_on": ["Create Product Database Model"]
            },
            {
                "title": "Add Product Search Endpoint",
                "description": "GET /products/search with query params for name and price range",
                "labels": ["backend", "api", "feature"],
                "depends_on": ["Build Product CRUD API"]
            },
            {
                "title": "Write Product API Tests",
                "description": "Pytest tests covering all CRUD operations and search",
                "labels": ["testing", "backend"],
                "depends_on": ["Build Product CRUD API", "Add Product Search Endpoint"]
            }
        ]
    },
    "3": {
        "name": "React Component",
        "description": "Create a reusable React component",
        "tasks": [
            {
                "title": "Create Button Component",
                "description": """React component with:
- Primary, secondary, and danger variants
- Disabled state
- Loading state with spinner
- Click handler
- TypeScript types
- Storybook story file""",
                "labels": ["frontend", "component", "react"],
                "estimated_time": "10 minutes"
            }
        ]
    },
    "4": {
        "name": "Real-time Chat",
        "description": "Build a real-time chat system",
        "tasks": [
            {
                "title": "Setup WebSocket Server",
                "description": "Socket.io server for real-time communication",
                "labels": ["backend", "realtime", "websocket"],
                "priority": "high"
            },
            {
                "title": "Create Chat Room Logic",
                "description": "Room creation, joining, leaving, and message broadcasting",
                "labels": ["backend", "feature", "chat"],
                "depends_on": ["Setup WebSocket Server"]
            },
            {
                "title": "Build Chat UI Components",
                "description": "React components: ChatRoom, MessageList, MessageInput, UserList",
                "labels": ["frontend", "component", "chat"]
            },
            {
                "title": "Connect Frontend to WebSocket",
                "description": "WebSocket client with reconnection logic",
                "labels": ["frontend", "realtime", "integration"],
                "depends_on": ["Build Chat UI Components", "Create Chat Room Logic"]
            }
        ]
    },
    "5": {
        "name": "Microservice",
        "description": "Create a standalone microservice",
        "tasks": [
            {
                "title": "Build Email Notification Service",
                "description": """Microservice that:
- Accepts email requests via REST API
- Queues emails for sending
- Supports templates
- Handles retries
- Includes health check endpoint
- Runs on port 3005""",
                "labels": ["backend", "microservice", "email"],
                "estimated_time": "15 minutes"
            }
        ]
    }
}


def display_welcome():
    """Display welcome message and introduction"""
    console.clear()
    welcome_text = """
# Welcome to PM Agent Interactive Demo! 🚀

This interactive demo will show you how PM Agent can manage AI workers to build real software projects.

## What you'll experience:
- Create tasks for AI workers
- Watch them build actual code
- See how workers handle dependencies
- Understand the PM Agent workflow

## How it works:
1. Choose a demo project
2. We'll create the necessary tasks
3. AI workers will start building
4. You can monitor progress in real-time

Let's get started!
"""
    console.print(Panel(Markdown(welcome_text), title="PM Agent Demo", border_style="cyan"))
    console.print()
    
    if not Confirm.ask("Ready to begin?", default=True):
        console.print("[yellow]Demo cancelled. Come back when you're ready![/yellow]")
        sys.exit(0)


def display_demo_options():
    """Display available demo options"""
    console.print("\n[bold cyan]Available Demo Projects:[/bold cyan]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Option", style="cyan", width=8)
    table.add_column("Project", style="green", width=20)
    table.add_column("Description", width=40)
    table.add_column("Tasks", justify="center", width=8)
    table.add_column("Time", width=12)
    
    for key, demo in DEMO_TASKS.items():
        total_time = sum(
            int(task.get("estimated_time", "10 minutes").split()[0]) 
            for task in demo["tasks"] 
            if "estimated_time" in task
        )
        time_str = f"~{total_time} min" if total_time > 0 else "~10-15 min"
        
        table.add_row(
            key,
            demo["name"],
            demo["description"],
            str(len(demo["tasks"])),
            time_str
        )
    
    console.print(table)
    console.print()


def create_tasks_visualization(tasks: List[Dict[str, Any]]):
    """Visualize the tasks that will be created"""
    console.print("\n[bold]Tasks to be created:[/bold]\n")
    
    for i, task in enumerate(tasks, 1):
        # Task header
        console.print(f"[bold cyan]Task {i}:[/bold cyan] {task['title']}")
        
        # Task details
        if task.get("description"):
            console.print(f"[dim]Description:[/dim] {task['description'][:100]}...")
        
        # Labels
        if task.get("labels"):
            labels = " ".join([f"[magenta]#{label}[/magenta]" for label in task["labels"]])
            console.print(f"[dim]Labels:[/dim] {labels}")
        
        # Dependencies
        if task.get("depends_on"):
            deps = ", ".join(task["depends_on"])
            console.print(f"[dim]Depends on:[/dim] [yellow]{deps}[/yellow]")
        
        console.print()


def simulate_task_creation(tasks: List[Dict[str, Any]]):
    """Simulate creating tasks with progress"""
    console.print("\n[bold green]Creating tasks...[/bold green]\n")
    
    for task in track(tasks, description="Creating tasks..."):
        time.sleep(0.5)  # Simulate API call
        console.print(f"✅ Created: [cyan]{task['title']}[/cyan]")
    
    console.print("\n[bold green]All tasks created successfully![/bold green]")


def show_monitoring_instructions():
    """Show instructions for monitoring progress"""
    monitoring_text = """
## Monitor Progress 📊

Your tasks have been created! Here's how to monitor progress:

### 1. Visualization Dashboard
Open your browser to: [link]http://localhost:4298[/link]

### 2. Command Line
```bash
# Watch logs in real-time
docker-compose logs -f pm-agent

# Check project status
docker-compose exec pm-agent pm-status

# View specific task
docker-compose exec pm-agent pm-task show <task-id>
```

### 3. Task Board
Check your configured task board (GitHub/Linear/Planka) to see tasks moving through columns.

### What to Watch For:
- Tasks moving from "Backlog" → "In Progress" → "Completed"
- Worker progress updates (25%, 50%, 75%, 100%)
- Generated code appearing in the output directory
- Workers handling dependencies automatically
"""
    console.print(Panel(Markdown(monitoring_text), title="Next Steps", border_style="green"))


def run_custom_task_wizard():
    """Wizard for creating a custom task"""
    console.print("\n[bold cyan]Create a Custom Task[/bold cyan]\n")
    
    title = Prompt.ask("Task title")
    description = Prompt.ask("Task description (what should be built?)")
    
    # Suggest labels based on description
    suggested_labels = []
    if any(word in description.lower() for word in ["api", "endpoint", "rest"]):
        suggested_labels.append("api")
    if any(word in description.lower() for word in ["database", "model", "schema"]):
        suggested_labels.append("database")
    if any(word in description.lower() for word in ["react", "component", "frontend"]):
        suggested_labels.append("frontend")
    if any(word in description.lower() for word in ["test", "pytest", "jest"]):
        suggested_labels.append("testing")
    
    if suggested_labels:
        console.print(f"\n[dim]Suggested labels: {', '.join(suggested_labels)}[/dim]")
    
    labels_input = Prompt.ask("Labels (comma-separated)", default=",".join(suggested_labels))
    labels = [label.strip() for label in labels_input.split(",") if label.strip()]
    
    priority = Prompt.ask("Priority", choices=["low", "normal", "high", "critical"], default="normal")
    
    custom_task = {
        "title": title,
        "description": description,
        "labels": labels,
        "priority": priority
    }
    
    console.print("\n[bold]Your custom task:[/bold]")
    create_tasks_visualization([custom_task])
    
    if Confirm.ask("Create this task?", default=True):
        simulate_task_creation([custom_task])
        show_monitoring_instructions()


def run_demo():
    """Main demo flow"""
    display_welcome()
    
    while True:
        display_demo_options()
        
        console.print("[bold]Options:[/bold]")
        console.print("  1-5: Choose a demo project")
        console.print("  C: Create a custom task")
        console.print("  Q: Quit demo")
        console.print()
        
        choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "5", "c", "C", "q", "Q"])
        
        if choice.lower() == "q":
            console.print("\n[yellow]Thanks for trying PM Agent! 👋[/yellow]")
            break
        
        if choice.lower() == "c":
            run_custom_task_wizard()
        else:
            demo = DEMO_TASKS[choice]
            console.print(f"\n[bold green]Selected: {demo['name']}[/bold green]")
            
            create_tasks_visualization(demo["tasks"])
            
            if Confirm.ask("Create these tasks?", default=True):
                simulate_task_creation(demo["tasks"])
                show_monitoring_instructions()
            else:
                console.print("[yellow]Task creation cancelled.[/yellow]")
        
        console.print("\n" + "="*60 + "\n")
        
        if not Confirm.ask("Try another demo?", default=True):
            console.print("\n[yellow]Thanks for using PM Agent! 👋[/yellow]")
            break


def check_pm_agent_running():
    """Check if PM Agent is running"""
    try:
        import docker
        client = docker.from_env()
        containers = client.containers.list()
        pm_agent_running = any("pm-agent" in c.name for c in containers)
        
        if not pm_agent_running:
            console.print("[bold red]⚠️  PM Agent doesn't appear to be running![/bold red]")
            console.print("\nPlease start PM Agent first:")
            console.print("[cyan]./start.sh full[/cyan]")
            return False
        return True
    except:
        # If we can't check, assume it's running
        return True


if __name__ == "__main__":
    try:
        if check_pm_agent_running():
            run_demo()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Demo interrupted. Goodbye! 👋[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        console.print("[dim]Please check that PM Agent is properly configured.[/dim]")