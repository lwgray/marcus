#!/usr/bin/env python3
"""
Mock Claude Worker using proper MCP Client connection to PM Agent
"""

import asyncio
import json
import random
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add parent directory to path for imports
sys.path.insert(0, '/Users/lwgray/dev/pm-agent')

from src.worker.mcp_client import WorkerMCPClient

# Initialize rich console for pretty output
console = Console()


class MockClaudeMCPWorker:
    """Mock Claude worker that connects to PM Agent via MCP"""
    
    def __init__(self, agent_id: str, agent_name: str, role: str, skills: list):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.role = role
        self.skills = skills
        self.current_task = None
        self.mcp_client = WorkerMCPClient()
        self.work_speed = random.uniform(0.5, 1.5)
        
        # Worker personality
        self.personality = {
            "thoroughness": random.uniform(0.7, 1.0),
            "communication": random.uniform(0.6, 1.0),
            "problem_solving": random.uniform(0.7, 1.0),
            "blocker_tendency": random.uniform(0.05, 0.15)
        }
        
    def _show_worker_profile(self):
        """Display worker profile"""
        console.print(Panel(
            f"[bold cyan]Agent ID:[/bold cyan] {self.agent_id}\n"
            f"[bold cyan]Name:[/bold cyan] {self.agent_name}\n"
            f"[bold cyan]Role:[/bold cyan] {self.role}\n"
            f"[bold cyan]Skills:[/bold cyan] {', '.join(self.skills)}\n\n"
            f"[dim]Personality Traits:[/dim]\n"
            f"  • Thoroughness: {self.personality['thoroughness']:.1%}\n"
            f"  • Communication: {self.personality['communication']:.1%}\n"
            f"  • Problem Solving: {self.personality['problem_solving']:.1%}\n"
            f"  • Work Speed: {self.work_speed:.1f}x",
            title=f"🤖 {self.agent_name}",
            border_style="cyan"
        ))
        
    def _log_thinking(self, thought: str):
        """Log worker's thinking"""
        console.print(f"\n[dim yellow]💭 {self.agent_name} thinking:[/dim yellow] {thought}")
        
    def _log_action(self, action: str, details: str = None):
        """Log worker's action"""
        console.print(f"\n[bold green]🔧 {self.agent_name} action:[/bold green] {action}")
        if details:
            console.print(f"   [dim]{details}[/dim]")
            
    def _log_communication(self, direction: str, message: str):
        """Log communication with PM Agent"""
        icon = "📤" if direction == "to_pm" else "📥"
        color = "blue" if direction == "to_pm" else "magenta"
        console.print(f"\n{icon} [bold {color}]{self.agent_name} → PM Agent:[/bold {color}]" 
                     if direction == "to_pm" 
                     else f"\n{icon} [bold {color}]PM Agent → {self.agent_name}:[/bold {color}]")
        console.print(f"   {message}")
        
    async def run(self):
        """Main worker loop using MCP connection"""
        self._show_worker_profile()
        
        console.print(f"\n[bold]Starting {self.agent_name}...[/bold]\n")
        
        try:
            # Connect to PM Agent via MCP
            async with self.mcp_client.connect_to_pm_agent() as session:
                self._log_action("Connected to PM Agent via MCP")
                
                # Register with PM Agent
                self._log_thinking("Time to register with PM Agent and let them know my capabilities")
                self._log_communication("to_pm", 
                    f"Registering as {self.role} with skills: {', '.join(self.skills)}"
                )
                
                result = await self.mcp_client.register_agent(
                    self.agent_id,
                    self.agent_name,
                    self.role,
                    self.skills
                )
                
                if result.get("success"):
                    self._log_communication("from_pm", result.get("message", "Registration successful"))
                    self._log_thinking("Great! Registration successful. Ready to work!")
                else:
                    console.print(f"[red]Registration failed: {result.get('error')}[/red]")
                    return
                
                # Work loop
                consecutive_no_task = 0
                
                while consecutive_no_task < 5:
                    # Request task
                    self._log_thinking("Let me check if there's any work available for me")
                    self._log_communication("to_pm", "Requesting next task")
                    
                    task_result = await self.mcp_client.request_next_task(self.agent_id)
                    
                    if task_result.get("has_task"):
                        consecutive_no_task = 0
                        task = task_result.get("task", {})
                        self.current_task = task
                        
                        self._log_communication("from_pm", 
                            f"Task assigned: '{task.get('title', 'Unknown')}'\n"
                            f"   Priority: {task.get('priority', 'Unknown')}\n"
                            f"   Estimated: {task.get('estimated_hours', 0)} hours"
                        )
                        
                        # Work on task
                        await self._work_on_task()
                        
                        # Brief pause
                        await asyncio.sleep(2)
                        
                    else:
                        consecutive_no_task += 1
                        self._log_communication("from_pm", 
                            task_result.get("message", "No tasks available")
                        )
                        
                        wait_time = min(5 * consecutive_no_task, 20)
                        self._log_thinking(f"No tasks yet. I'll check again in {wait_time} seconds.")
                        await asyncio.sleep(wait_time)
                
                self._log_thinking("No more tasks available. Time to sign off.")
                self._log_communication("to_pm", "Signing off. Thanks for the coordination!")
                
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            import traceback
            traceback.print_exc()
            
        console.print(Panel(
            f"[bold green]{self.agent_name} session complete[/bold green]",
            border_style="green"
        ))
        
    async def _work_on_task(self):
        """Simulate working on a task"""
        if not self.current_task:
            return
            
        task_id = self.current_task.get("id")
        task_title = self.current_task.get("title", "Unknown Task")
        estimated_hours = self.current_task.get("estimated_hours", 4)
        
        self._log_action(f"Starting work on task", f"'{task_title}'")
        
        # Progress intervals
        progress_intervals = [
            (25, "Initial setup and understanding requirements"),
            (50, "Core implementation"),
            (75, "Testing and refinement"),
            (100, "Final review and completion")
        ]
        
        for progress, phase in progress_intervals:
            # Check for blocker
            if random.random() < self.personality['blocker_tendency'] and progress < 100:
                await self._handle_blocker()
                continue
            
            # Simulate work
            work_time = (estimated_hours * 0.25 * self.work_speed * 2)  # 2 seconds per hour
            
            self._log_action(f"Working on {phase}", f"Progress: {progress}%")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress_bar:
                task = progress_bar.add_task(f"[cyan]{phase}...", total=work_time)
                
                while not progress_bar.finished:
                    await asyncio.sleep(0.1)
                    progress_bar.update(task, advance=0.1)
            
            # Report progress
            message = self._generate_progress_message(progress, phase)
            
            self._log_communication("to_pm", 
                f"Progress update: {progress}% - {message}"
            )
            
            result = await self.mcp_client.report_task_progress(
                self.agent_id,
                task_id,
                "completed" if progress == 100 else "in_progress",
                progress,
                message
            )
            
            if result.get("success"):
                self._log_communication("from_pm", 
                    "Progress update received. Keep up the good work!"
                )
        
        self._log_thinking(f"Task '{task_title}' completed successfully!")
        self.current_task = None
        
    async def _handle_blocker(self):
        """Handle a blocker"""
        blockers = [
            ("API credentials missing", "medium", "Need access to external service"),
            ("Unclear requirements", "low", "Need clarification on acceptance criteria"),
            ("Dependency not available", "high", "Required library has breaking changes")
        ]
        
        blocker, severity, details = random.choice(blockers)
        
        self._log_thinking(f"I've encountered an issue: {blocker}")
        self._log_communication("to_pm",
            f"Reporting blocker: {blocker} (Severity: {severity})"
        )
        
        result = await self.mcp_client.report_blocker(
            self.agent_id,
            self.current_task.get("id"),
            f"{blocker} - {details}",
            severity
        )
        
        if result.get("success"):
            suggestions = result.get("suggestions", [])
            if suggestions:
                self._log_communication("from_pm",
                    "Suggestions received:\n" +
                    "\n".join(f"   • {s}" for s in suggestions[:3])
                )
                
            self._log_thinking("Let me try to work around this blocker...")
            await asyncio.sleep(3)
            self._log_action("Blocker resolved", "Found a workaround, continuing")
            
    def _generate_progress_message(self, progress: int, phase: str) -> str:
        """Generate progress message"""
        if self.personality['communication'] > 0.8:
            messages = {
                25: [f"Completed {phase}. Environment set up and requirements reviewed."],
                50: [f"{phase} complete. Core functionality implemented and working."],
                75: [f"{phase} done. All tests passing, performance optimized."],
                100: [f"Task fully complete! {phase} finished, ready for review."]
            }
        else:
            messages = {
                25: ["Setup complete"],
                50: ["Core implementation done"],
                75: ["Testing complete"],
                100: ["Task finished"]
            }
        
        return random.choice(messages.get(progress, [f"{phase} - {progress}% complete"]))


async def main():
    """Run mock worker with MCP connection"""
    
    workers = [
        {
            "agent_id": "claude-backend-001",
            "agent_name": "Claude Backend Dev",
            "role": "Backend Developer",
            "skills": ["python", "api", "database", "testing"]
        },
        {
            "agent_id": "claude-frontend-001", 
            "agent_name": "Claude Frontend Dev",
            "role": "Frontend Developer",
            "skills": ["react", "typescript", "ui", "testing"]
        },
        {
            "agent_id": "claude-fullstack-001",
            "agent_name": "Claude Fullstack Dev",
            "role": "Fullstack Developer", 
            "skills": ["python", "react", "api", "database", "ui"]
        }
    ]
    
    console.print(Panel.fit(
        "[bold cyan]Mock Claude Worker (MCP Client)[/bold cyan]\n"
        "Connects to PM Agent via MCP protocol",
        title="🤖 Worker Demo",
        border_style="cyan"
    ))
    
    console.print("\n[bold]Available workers:[/bold]")
    for i, worker in enumerate(workers):
        console.print(f"  {i+1}. {worker['agent_name']} ({worker['role']})")
        
    console.print("\n[bold yellow]Note:[/bold yellow] PM Agent must be running separately!")
    console.print("Run: python pm_agent_mcp_server.py")
    
    choice = console.input("\n[bold yellow]Select worker (1-3):[/bold yellow] ").strip()
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(workers):
            worker = MockClaudeMCPWorker(**workers[idx])
            await worker.run()
        else:
            console.print("[red]Invalid selection[/red]")
    except ValueError:
        console.print("[red]Invalid input[/red]")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Worker shutdown[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")