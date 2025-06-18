#!/usr/bin/env python3
"""
Verbose Mock Claude Worker Agent for PM Agent Testing

This enhanced version shows detailed conversation between the worker and PM Agent,
including the worker's "thinking" process.
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
from rich.table import Table
from rich.live import Live

# Add parent directory to path for imports
sys.path.insert(0, '/Users/lwgray/dev/pm-agent')

from src.worker.mcp_client import WorkerMCPClient

# Initialize rich console for pretty output
console = Console()


class VerboseMockClaudeWorker:
    """Verbose Mock Claude worker agent for testing PM Agent"""
    
    def __init__(self, agent_id: str, agent_name: str, role: str, skills: list):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.role = role
        self.skills = skills
        self.current_task = None
        self.mcp_client = WorkerMCPClient()
        self.work_speed = random.uniform(0.5, 1.5)  # Randomize work speed
        
        # Worker personality traits for realistic behavior
        self.personality = {
            "thoroughness": random.uniform(0.7, 1.0),
            "communication": random.uniform(0.6, 1.0),
            "problem_solving": random.uniform(0.7, 1.0),
            "blocker_tendency": random.uniform(0.05, 0.15)
        }
        
    def _show_worker_profile(self):
        """Display worker profile card"""
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
        """Log worker's thinking process"""
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
        
    async def initialize(self):
        """Initialize MCP connection to PM Agent"""
        self._log_action("Initializing MCP connection")
        
        try:
            # Initialize MCP client connection to PM Agent
            self.mcp_client = SimpleMCPKanbanClient()
            await self.mcp_client.initialize()
            
            self._log_action("MCP connection established", "Ready to communicate with PM Agent")
            return True
            
        except Exception as e:
            self._log_action(f"Failed to initialize", f"Error: {e}")
            return False
            
    async def register(self):
        """Register with PM Agent"""
        self._log_thinking("Time to register with PM Agent and let them know my capabilities")
        
        self._log_communication("to_pm", 
            f"Hello PM Agent! I'm {self.agent_name}, a {self.role} with skills in: {', '.join(self.skills)}"
        )
        
        try:
            result = await self.mcp_client.call_tool(
                "register_agent",
                {
                    "agent_id": self.agent_id,
                    "name": self.agent_name,
                    "role": self.role,
                    "skills": self.skills
                }
            )
            
            if result.get("success"):
                self._log_communication("from_pm", 
                    f"Welcome {self.agent_name}! You're registered and ready to receive tasks."
                )
                self._log_thinking("Great! Registration successful. Ready to work!")
                return True
            else:
                self._log_communication("from_pm", 
                    f"Registration failed: {result.get('error', 'Unknown error')}"
                )
                return False
                
        except Exception as e:
            self._log_action(f"Registration failed", f"Error: {e}")
            return False
            
    async def request_task(self) -> Optional[Dict[str, Any]]:
        """Request next task from PM Agent"""
        self._log_thinking("Let me check if there's any work available for me")
        
        self._log_communication("to_pm", 
            "PM Agent, I'm available for work. Do you have any tasks that match my skills?"
        )
        
        try:
            result = await self.mcp_client.call_tool(
                "request_next_task",
                {"agent_id": self.agent_id}
            )
            
            if result.get("has_task"):
                task = result.get("task")
                self.current_task = task
                
                self._log_communication("from_pm", 
                    f"I have a perfect task for you: '{task['title']}'\n"
                    f"   Priority: {task['priority']}\n"
                    f"   Estimated: {task['estimated_hours']} hours\n"
                    f"   Instructions: {task.get('instructions', 'See description')}"
                )
                
                self._log_thinking(
                    f"This looks like a {task['priority']} priority task. "
                    f"Based on my estimation, I should complete it in "
                    f"{task['estimated_hours'] * self.work_speed:.1f} hours."
                )
                
                return task
            else:
                self._log_communication("from_pm", 
                    "No suitable tasks available right now. Check back in a moment."
                )
                self._log_thinking("No tasks available. I'll wait a bit and check again.")
                return None
                
        except Exception as e:
            self._log_action(f"Error requesting task", f"Error: {e}")
            return None
            
    async def work_on_task(self):
        """Simulate working on a task with detailed progress updates"""
        if not self.current_task:
            return
            
        task_id = self.current_task["id"]
        task_title = self.current_task["title"]
        estimated_hours = self.current_task.get("estimated_hours", 4)
        
        self._log_action(f"Starting work on task", f"'{task_title}'")
        self._log_thinking(
            f"Based on my thoroughness ({self.personality['thoroughness']:.1%}) "
            f"and work speed ({self.work_speed:.1f}x), I'll approach this methodically."
        )
        
        # Simulate work with progress updates
        progress_intervals = [
            (25, "Initial setup and understanding requirements"),
            (50, "Core implementation"),
            (75, "Testing and refinement"),
            (100, "Final review and completion")
        ]
        
        for progress, phase in progress_intervals:
            # Simulate work time (accelerated for demo)
            work_time = (estimated_hours * 0.25 * self.work_speed * 2)  # 2 seconds per hour for demo
            
            # Check for blocker
            if random.random() < self.personality['blocker_tendency'] and progress < 100:
                await self._handle_blocker()
                continue
            
            # Show work in progress
            self._log_action(f"Working on {phase}", f"Progress: {progress}%")
            
            # Simulate actual work with progress bar
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress_bar:
                task = progress_bar.add_task(f"[cyan]{phase}...", total=work_time)
                
                while not progress_bar.finished:
                    await asyncio.sleep(0.1)
                    progress_bar.update(task, advance=0.1)
            
            # Generate realistic progress message based on personality
            message = self._generate_progress_message(progress, phase)
            
            # Report progress to PM Agent
            self._log_communication("to_pm", 
                f"Progress update on '{task_title}':\n"
                f"   Status: {'completed' if progress == 100 else 'in_progress'}\n"
                f"   Progress: {progress}%\n"
                f"   Details: {message}"
            )
            
            try:
                result = await self.mcp_client.call_tool(
                    "report_task_progress",
                    {
                        "agent_id": self.agent_id,
                        "task_id": task_id,
                        "status": "completed" if progress == 100 else "in_progress",
                        "progress": progress,
                        "message": message
                    }
                )
                
                if result.get("success"):
                    self._log_communication("from_pm", 
                        "Progress update received. Keep up the good work!"
                    )
                    
            except Exception as e:
                self._log_action(f"Error reporting progress", f"Error: {e}")
        
        # Task completed
        self._log_thinking(f"Task '{task_title}' completed successfully!")
        self._log_action("Task completed", f"Ready for the next challenge")
        
        # Clear current task
        self.current_task = None
        
    async def _handle_blocker(self):
        """Handle a blocker situation"""
        blockers = [
            ("API credentials missing", "medium", "Need access to external service API"),
            ("Unclear requirements", "low", "Need clarification on acceptance criteria"),
            ("Dependency not available", "high", "Required library has breaking changes"),
            ("Database schema conflict", "medium", "Existing schema doesn't match requirements"),
            ("Environment setup issue", "low", "Development environment configuration problem")
        ]
        
        blocker, severity, details = random.choice(blockers)
        
        self._log_thinking(f"I've encountered an issue: {blocker}")
        self._log_action("Blocker encountered", f"{blocker} - Severity: {severity}")
        
        self._log_communication("to_pm",
            f"I've hit a blocker on task '{self.current_task['title']}':\n"
            f"   Issue: {blocker}\n"
            f"   Severity: {severity}\n"
            f"   Details: {details}\n"
            f"   Need assistance to proceed."
        )
        
        try:
            result = await self.mcp_client.call_tool(
                "report_blocker",
                {
                    "agent_id": self.agent_id,
                    "task_id": self.current_task["id"],
                    "blocker_description": f"{blocker} - {details}",
                    "severity": severity
                }
            )
            
            if result.get("success"):
                suggestions = result.get("suggestions", [])
                self._log_communication("from_pm",
                    f"I understand the blocker. Here are some suggestions:\n" +
                    "\n".join(f"   • {s}" for s in suggestions[:3])
                )
                
                # Simulate resolving the blocker
                self._log_thinking(
                    f"Let me try the first suggestion. "
                    f"With my problem-solving skills ({self.personality['problem_solving']:.1%}), "
                    f"I should be able to work around this."
                )
                
                await asyncio.sleep(3)  # Simulate resolution time
                self._log_action("Blocker resolved", "Found a workaround, continuing with task")
                
        except Exception as e:
            self._log_action(f"Error reporting blocker", f"Error: {e}")
        
    def _generate_progress_message(self, progress: int, phase: str) -> str:
        """Generate realistic progress messages based on personality"""
        if self.personality['communication'] > 0.8:
            # Detailed communicator
            messages = {
                25: [
                    f"Completed initial setup. {phase} went smoothly. Set up development environment and reviewed all requirements. Ready to start implementation.",
                    f"Finished {phase}. All dependencies are installed and configuration is complete. The requirements are clear and I have a solid plan."
                ],
                50: [
                    f"Core implementation is done. {phase} involved creating the main logic and ensuring it follows best practices. All primary features are working.",
                    f"Halfway through! {phase} is complete with clean, well-documented code. Running initial tests to verify functionality."
                ],
                75: [
                    f"Testing phase complete. {phase} included unit tests, integration tests, and edge case handling. Coverage is at 85%.",
                    f"Almost done! {phase} revealed a few minor issues which I've fixed. Performance is optimized and code is refactored."
                ],
                100: [
                    f"Task completed successfully! All tests are passing, documentation is updated, and code is ready for review. {phase} ensured everything meets quality standards.",
                    f"Finished! {phase} included final cleanup, code review prep, and verification of all acceptance criteria. Ready for deployment."
                ]
            }
        else:
            # Brief communicator
            messages = {
                25: ["Setup complete, starting main work", "Requirements understood, beginning implementation"],
                50: ["Core features implemented", "Main functionality complete"],
                75: ["Testing done, fixing minor issues", "Almost finished, polishing"],
                100: ["Task completed successfully", "All done, ready for review"]
            }
        
        return random.choice(messages.get(progress, [f"{phase} - making progress"]))
        
    async def check_project_status(self):
        """Occasionally check overall project status"""
        if random.random() < 0.3:  # 30% chance to check status
            self._log_thinking("Let me check how the overall project is going")
            
            self._log_communication("to_pm", 
                "PM Agent, could you give me a project status update?"
            )
            
            try:
                result = await self.mcp_client.call_tool("get_project_status", {})
                
                if result.get("success"):
                    metrics = result.get("metrics", {})
                    self._log_communication("from_pm",
                        f"Project Status Update:\n"
                        f"   Progress: {metrics.get('progress', 0)}%\n"
                        f"   Active Agents: {result.get('active_agents', 0)}\n"
                        f"   Risk Level: {metrics.get('risk_level', 'Unknown')}"
                    )
                    
                    self._log_thinking("Good to know the project context. Back to work!")
                    
            except Exception as e:
                self._log_action(f"Error checking status", f"Error: {e}")
    
    async def run(self):
        """Main worker loop"""
        # Show worker profile
        self._show_worker_profile()
        
        # Initialize and register
        console.print(f"\n[bold]Starting {self.agent_name}...[/bold]\n")
        
        if not await self.initialize():
            return
            
        await asyncio.sleep(1)
            
        if not await self.register():
            return
            
        await asyncio.sleep(2)
        
        # Work loop
        consecutive_no_task = 0
        
        while True:
            # Occasionally check project status
            await self.check_project_status()
            
            # Request a task
            task = await self.request_task()
            
            if task:
                consecutive_no_task = 0
                
                # Work on the task
                await self.work_on_task()
                
                # Brief pause between tasks
                self._log_thinking("Task complete. Let me take a brief moment before the next one.")
                await asyncio.sleep(2)
                
            else:
                consecutive_no_task += 1
                
                if consecutive_no_task >= 5:
                    self._log_thinking(
                        "No tasks available after multiple checks. "
                        "Seems like my work here is done for now."
                    )
                    self._log_communication("to_pm", 
                        "PM Agent, I'm signing off for now. Thanks for the coordination!"
                    )
                    break
                    
                # Wait before checking again
                wait_time = min(5 * consecutive_no_task, 20)  # Exponential backoff
                self._log_thinking(f"No tasks yet. I'll check again in {wait_time} seconds.")
                await asyncio.sleep(wait_time)
                
        # Cleanup
        if self.mcp_client:
            await self.mcp_client.close()
            
        console.print(Panel(
            f"[bold green]{self.agent_name} session complete[/bold green]\n"
            f"Thanks for watching!",
            border_style="green"
        ))


async def main():
    """Run verbose mock Claude workers"""
    
    # Define different worker personas
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
    
    # Show header
    console.print(Panel.fit(
        "[bold cyan]Verbose Mock Claude Worker Demo[/bold cyan]\n"
        "Watch the detailed conversation between workers and PM Agent",
        title="🤖 Worker Simulation",
        border_style="cyan"
    ))
    
    # Let user choose which worker to run
    console.print("\n[bold]Available workers:[/bold]")
    for i, worker in enumerate(workers):
        console.print(f"  {i+1}. {worker['agent_name']} ({worker['role']})")
        
    choice = console.input("\n[bold yellow]Select worker (1-3) or 'all' for all workers:[/bold yellow] ").strip()
    
    if choice.lower() == 'all':
        # Run all workers concurrently
        console.print("\n[bold green]Starting all workers concurrently...[/bold green]\n")
        tasks = []
        for worker_config in workers:
            worker = VerboseMockClaudeWorker(**worker_config)
            tasks.append(worker.run())
        await asyncio.gather(*tasks)
    else:
        # Run single worker
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(workers):
                worker = VerboseMockClaudeWorker(**workers[idx])
                await worker.run()
            else:
                console.print("[bold red]Invalid selection[/bold red]")
        except ValueError:
            console.print("[bold red]Invalid input[/bold red]")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Worker shutdown requested[/bold yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")