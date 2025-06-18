#!/usr/bin/env python3
"""
Test script showing the complete conversation flow:
Worker ↔ PM Agent ↔ Kanban Board
"""

import asyncio
import sys
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text

# Add parent directory
sys.path.insert(0, '/Users/lwgray/dev/pm-agent')

from src.integrations.mcp_kanban_client_verbose import VerboseMCPKanbanClient

console = Console()


class ConversationSimulator:
    """Simulates the full conversation between Worker, PM Agent, and Kanban Board"""
    
    def __init__(self):
        self.kanban_client = VerboseMCPKanbanClient()
        
    def show_header(self):
        """Show demo header"""
        console.print(Panel.fit(
            "[bold cyan]Full Conversation Flow Demo[/bold cyan]\n"
            "Worker ↔ PM Agent ↔ Kanban Board",
            title="🔄 Three-Way Communication",
            border_style="cyan"
        ))
        
        console.print("\n[bold]Communication Channels:[/bold]")
        console.print("1. [blue]Worker → PM Agent[/blue]: Task requests, progress updates")
        console.print("2. [magenta]PM Agent → Kanban[/magenta]: Board queries, task updates")
        console.print("3. [green]Kanban → PM Agent[/green]: Board state, task data")
        console.print("4. [yellow]PM Agent → Worker[/yellow]: Task assignments, acknowledgments")
        console.print()
        
    async def simulate_worker_registration(self):
        """Simulate worker registration flow"""
        console.print(Panel("Worker Registration Flow", style="bold"))
        
        # Worker to PM
        console.print("\n[bold blue]💬 Worker → PM Agent:[/bold blue]")
        console.print("   Hello! I'm Claude Backend Dev with skills: python, api, database")
        
        await asyncio.sleep(1)
        
        # PM Agent processes
        console.print("\n[dim cyan]🧠 PM Agent thinking:[/dim cyan] New worker registration")
        console.print("   • Validating worker credentials")
        console.print("   • Checking skill requirements")
        console.print("   • Registering in worker pool")
        
        await asyncio.sleep(1)
        
        # PM to Worker
        console.print("\n[bold yellow]💬 PM Agent → Worker:[/bold yellow]")
        console.print("   Welcome! You're registered and ready for tasks")
        
    async def simulate_task_request(self):
        """Simulate task request flow"""
        console.print("\n" + "="*60)
        console.print(Panel("Task Request Flow", style="bold"))
        
        # Worker requests task
        console.print("\n[bold blue]💬 Worker → PM Agent:[/bold blue]")
        console.print("   I'm available for work. Any tasks for me?")
        
        await asyncio.sleep(1)
        
        # PM Agent thinking
        console.print("\n[dim cyan]🧠 PM Agent thinking:[/dim cyan] Worker requesting task")
        console.print("   • Worker skills: python, api, database")
        console.print("   • Need to check available tasks on board")
        
        await asyncio.sleep(1)
        
        # PM queries Kanban
        console.print("\n[bold green]🔌 PM Agent → Kanban Board:[/bold green]")
        console.print("   [cyan]Action:[/cyan] Get available tasks")
        console.print("   [cyan]Criteria:[/cyan] Unassigned, in Backlog or Ready")
        
        await asyncio.sleep(1)
        
        # Kanban processes
        console.print("\n[dim yellow]🤔 Kanban processing:[/dim yellow] Searching for available tasks")
        console.print("   1. Scanning Backlog column")
        console.print("   2. Scanning Ready column")
        console.print("   3. Filtering unassigned tasks")
        console.print("   4. Sorting by priority")
        
        await asyncio.sleep(1)
        
        # Kanban responds
        console.print("\n[bold magenta]📋 Kanban Board → PM Agent:[/bold magenta]")
        console.print("   [magenta]Found:[/magenta] 3 available tasks")
        console.print("   [dim]Tasks:[/dim]")
        console.print("      • Implement user authentication (High priority)")
        console.print("      • Create API documentation (Medium priority)")
        console.print("      • Setup CI/CD pipeline (High priority)")
        
        await asyncio.sleep(1)
        
        # PM Agent analyzes
        console.print("\n[dim cyan]🧠 PM Agent thinking:[/dim cyan] Analyzing task matches")
        console.print("   • Task 1: Good match (backend, security)")
        console.print("   • Task 2: Partial match (documentation)")
        console.print("   • Task 3: Partial match (devops)")
        console.print("   • Best match: Task 1 - High priority + skill match")
        
        await asyncio.sleep(1)
        
        # PM assigns task
        console.print("\n[bold yellow]📋 PM Decision:[/bold yellow]")
        console.print("   [yellow]Decision:[/yellow] Assign 'Implement user authentication'")
        console.print("   [dim]Reason:[/dim] High priority, perfect skill match")
        
        await asyncio.sleep(1)
        
        # PM updates Kanban
        console.print("\n[bold green]🔌 PM Agent → Kanban Board:[/bold green]")
        console.print("   [cyan]Action:[/cyan] Assign task to agent")
        console.print("   [cyan]Parameters:[/cyan]")
        console.print("      • task_id: task-1")
        console.print("      • agent_id: claude-backend-001")
        console.print("      • action: Move to In Progress")
        
        await asyncio.sleep(1)
        
        # Kanban updates
        console.print("\n[dim yellow]🤔 Kanban processing:[/dim yellow] Updating task assignment")
        console.print("   1. Setting assigned_to = claude-backend-001")
        console.print("   2. Moving card to 'In Progress' column")
        console.print("   3. Adding assignment timestamp")
        console.print("   4. Creating assignment comment")
        
        await asyncio.sleep(1)
        
        # Kanban confirms
        console.print("\n[bold magenta]📋 Kanban Board → PM Agent:[/bold magenta]")
        console.print("   [magenta]Result:[/magenta] Task successfully assigned")
        console.print("   [green]✓ Card moved to In Progress[/green]")
        
        await asyncio.sleep(1)
        
        # PM notifies worker
        console.print("\n[bold yellow]💬 PM Agent → Worker:[/bold yellow]")
        console.print("   I have a task for you: 'Implement user authentication'")
        console.print("   Priority: High, Estimated: 8 hours")
        console.print("   Instructions: Create secure login system with JWT")
        
    async def simulate_progress_update(self):
        """Simulate progress update flow"""
        console.print("\n" + "="*60)
        console.print(Panel("Progress Update Flow", style="bold"))
        
        # Worker reports progress
        console.print("\n[bold blue]💬 Worker → PM Agent:[/bold blue]")
        console.print("   Progress update: 50% complete")
        console.print("   Status: Core authentication logic implemented")
        
        await asyncio.sleep(1)
        
        # PM processes
        console.print("\n[dim cyan]🧠 PM Agent thinking:[/dim cyan] Processing progress update")
        console.print("   • Task on track")
        console.print("   • Need to update board")
        
        await asyncio.sleep(1)
        
        # PM updates Kanban
        console.print("\n[bold green]🔌 PM Agent → Kanban Board:[/bold green]")
        console.print("   [cyan]Action:[/cyan] Update task progress")
        console.print("   [cyan]Parameters:[/cyan]")
        console.print("      • task_id: task-1")
        console.print("      • progress: 50%")
        console.print("      • comment: Core authentication logic implemented")
        
        await asyncio.sleep(1)
        
        # Kanban updates
        console.print("\n[dim yellow]🤔 Kanban processing:[/dim yellow] Recording progress")
        console.print("   1. Adding progress comment")
        console.print("   2. Updating progress field to 50%")
        console.print("   3. Keeping in 'In Progress' column")
        
        await asyncio.sleep(1)
        
        # Kanban confirms
        console.print("\n[bold magenta]📋 Kanban Board → PM Agent:[/bold magenta]")
        console.print("   [magenta]Result:[/magenta] Progress updated successfully")
        
        # PM acknowledges
        console.print("\n[bold yellow]💬 PM Agent → Worker:[/bold yellow]")
        console.print("   Progress noted. Keep up the good work!")
        
    async def simulate_blocker(self):
        """Simulate blocker handling flow"""
        console.print("\n" + "="*60)
        console.print(Panel("Blocker Handling Flow", style="bold"))
        
        # Worker reports blocker
        console.print("\n[bold blue]💬 Worker → PM Agent:[/bold blue]")
        console.print("   🚫 BLOCKER: Missing OAuth provider credentials")
        console.print("   Severity: Medium")
        console.print("   Can't proceed with social login integration")
        
        await asyncio.sleep(1)
        
        # PM analyzes
        console.print("\n[dim cyan]🧠 PM Agent thinking:[/dim cyan] Blocker reported")
        console.print("   • Analyzing blocker type")
        console.print("   • Checking for solutions")
        console.print("   • Need to update board status")
        
        await asyncio.sleep(1)
        
        # PM updates Kanban
        console.print("\n[bold green]🔌 PM Agent → Kanban Board:[/bold green]")
        console.print("   [cyan]Action:[/cyan] Report blocker")
        console.print("   [cyan]Parameters:[/cyan]")
        console.print("      • task_id: task-1")
        console.print("      • blocker: Missing OAuth credentials")
        console.print("      • severity: medium")
        
        await asyncio.sleep(1)
        
        # Kanban updates
        console.print("\n[dim yellow]🤔 Kanban processing:[/dim yellow] Recording blocker")
        console.print("   1. Adding blocker comment")
        console.print("   2. Adding 'blocked' label")
        console.print("   3. Notifying watchers")
        
        await asyncio.sleep(1)
        
        # PM provides solutions
        console.print("\n[bold yellow]💬 PM Agent → Worker:[/bold yellow]")
        console.print("   Blocker noted. Suggestions:")
        console.print("   • Use mock OAuth for development")
        console.print("   • Implement local auth first")
        console.print("   • Request credentials from DevOps")
        
    async def simulate_completion(self):
        """Simulate task completion flow"""
        console.print("\n" + "="*60)
        console.print(Panel("Task Completion Flow", style="bold"))
        
        # Worker completes task
        console.print("\n[bold blue]💬 Worker → PM Agent:[/bold blue]")
        console.print("   Task completed! 100% done")
        console.print("   All tests passing, documentation updated")
        
        await asyncio.sleep(1)
        
        # PM processes completion
        console.print("\n[dim cyan]🧠 PM Agent thinking:[/dim cyan] Task reported complete")
        console.print("   • Validating completion criteria")
        console.print("   • Updating board status")
        console.print("   • Freeing agent for next task")
        
        await asyncio.sleep(1)
        
        # PM moves to Done
        console.print("\n[bold green]🔌 PM Agent → Kanban Board:[/bold green]")
        console.print("   [cyan]Action:[/cyan] Complete task")
        console.print("   [cyan]Parameters:[/cyan]")
        console.print("      • task_id: task-1")
        console.print("      • status: completed")
        console.print("      • move_to: Done column")
        
        await asyncio.sleep(1)
        
        # Kanban completes
        console.print("\n[dim yellow]🤔 Kanban processing:[/dim yellow] Completing task")
        console.print("   1. Moving card to 'Done' column")
        console.print("   2. Recording completion time")
        console.print("   3. Updating metrics")
        
        await asyncio.sleep(1)
        
        # PM gets metrics
        console.print("\n[bold green]🔌 PM Agent → Kanban Board:[/bold green]")
        console.print("   [cyan]Action:[/cyan] Get updated metrics")
        
        await asyncio.sleep(1)
        
        # Kanban provides metrics
        console.print("\n[bold magenta]📋 Kanban Board → PM Agent:[/bold magenta]")
        console.print("   [magenta]Metrics:[/magenta]")
        console.print("      • Total completed: 11/25 (44%)")
        console.print("      • Velocity: 2.8 tasks/day")
        console.print("      • Cycle time: 1.5 days")
        
        # PM congratulates
        console.print("\n[bold yellow]💬 PM Agent → Worker:[/bold yellow]")
        console.print("   Excellent work! Task completed successfully")
        console.print("   Ready for your next assignment?")
        
    async def run_simulation(self):
        """Run the complete simulation"""
        self.show_header()
        
        await asyncio.sleep(2)
        await self.simulate_worker_registration()
        
        await asyncio.sleep(2)
        await self.simulate_task_request()
        
        await asyncio.sleep(2)
        await self.simulate_progress_update()
        
        await asyncio.sleep(2)
        await self.simulate_blocker()
        
        await asyncio.sleep(2)
        await self.simulate_completion()
        
        console.print("\n" + "="*60)
        console.print(Panel(
            "[bold green]Simulation Complete![/bold green]\n\n"
            "This demonstrates the full conversation flow between:\n"
            "• Worker agents requesting and updating tasks\n"
            "• PM Agent making decisions and coordinating\n"
            "• Kanban board tracking all project state\n\n"
            "In production, these happen asynchronously with multiple workers!",
            title="✅ Demo Complete",
            border_style="green"
        ))


async def main():
    """Run the conversation simulator"""
    simulator = ConversationSimulator()
    await simulator.run_simulation()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Simulation interrupted[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")