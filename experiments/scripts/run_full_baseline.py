#!/usr/bin/env python3
"""
Full baseline experiment runner that orchestrates the complete workflow:
1. Start PM Agent (if needed)
2. Create project and tasks
3. Launch autonomous agents
4. Monitor progress
5. Collect results
"""

import os
import sys
import time
import asyncio
import subprocess
from pathlib import Path
from typing import List, Dict, Any
import json
from datetime import datetime

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from datasets import load_dataset
import aiohttp

console = Console()

class BaselineExperimentRunner:
    """Orchestrates the full baseline experiment"""
    
    def __init__(self, agent_count: int, task_count: int, pm_agent_url: str):
        self.agent_count = agent_count
        self.task_count = task_count
        self.pm_agent_url = pm_agent_url
        self.api_key = os.getenv("PM_AGENT_API_KEY", "")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.agents = []
        self.project_id = None
        self.task_ids = []
        self.start_time = None
        
    async def check_pm_agent_running(self) -> bool:
        """Check if PM Agent server is running"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.pm_agent_url}/health") as resp:
                    return resp.status == 200
        except:
            return False
    
    async def setup_project(self):
        """Create project and load tasks"""
        console.print("[bold blue]Setting up PM Agent project...[/bold blue]")
        
        async with aiohttp.ClientSession() as session:
            # Create project
            async with session.post(
                f"{self.pm_agent_url}/api/projects",
                json={
                    "name": f"SWE-bench Baseline {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "description": f"Baseline experiment with {self.agent_count} agents on {self.task_count} tasks"
                },
                headers={"Authorization": f"Bearer {self.api_key}"}
            ) as resp:
                data = await resp.json()
                self.project_id = data["project_id"]
                console.print(f"[green]✓[/green] Created project: {self.project_id}")
            
            # Load SWE-bench tasks
            console.print("Loading SWE-bench tasks...")
            tasks = self.load_swebench_tasks()
            
            # Create tasks in PM Agent
            with Progress() as progress:
                task = progress.add_task("Creating tasks...", total=len(tasks))
                
                for swe_task in tasks:
                    async with session.post(
                        f"{self.pm_agent_url}/api/projects/{self.project_id}/tasks",
                        json={
                            "title": f"Fix: {swe_task['instance_id']}",
                            "description": swe_task['problem_statement'],
                            "labels": ["swe-bench", swe_task['repo']],
                            "metadata": {
                                "instance_id": swe_task['instance_id'],
                                "base_commit": swe_task['base_commit'],
                                "FAIL_TO_PASS": swe_task['FAIL_TO_PASS'],
                                "PASS_TO_PASS": swe_task['PASS_TO_PASS'],
                                "repo": swe_task['repo']
                            }
                        },
                        headers={"Authorization": f"Bearer {self.api_key}"}
                    ) as resp:
                        task_data = await resp.json()
                        self.task_ids.append(task_data["task_id"])
                    
                    progress.update(task, advance=1)
            
            console.print(f"[green]✓[/green] Created {len(self.task_ids)} tasks")
    
    def load_swebench_tasks(self) -> List[Dict]:
        """Load tasks from SWE-bench dataset"""
        try:
            # Try loading from cache first
            cache_path = Path("./cache/swebench/swebench_lite.parquet")
            if cache_path.exists():
                import pandas as pd
                df = pd.read_parquet(cache_path)
                tasks = df.to_dict('records')[:self.task_count]
            else:
                # Load from Hugging Face
                dataset = load_dataset('princeton-nlp/SWE-bench_Lite', split='test')
                tasks = [dataset[i] for i in range(min(len(dataset), self.task_count))]
            
            return tasks
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load SWE-bench: {e}[/yellow]")
            console.print("Using synthetic tasks for testing")
            return self.create_synthetic_tasks()
    
    def create_synthetic_tasks(self) -> List[Dict]:
        """Create synthetic tasks for testing"""
        tasks = []
        for i in range(self.task_count):
            tasks.append({
                'instance_id': f'synthetic_{i:04d}',
                'problem_statement': f'Fix the validation error in user registration when email contains special characters',
                'repo': 'test_repo',
                'base_commit': 'abc123def456',
                'FAIL_TO_PASS': ['tests/test_user_registration.py::test_special_chars_email'],
                'PASS_TO_PASS': ['tests/test_user_registration.py::test_normal_email']
            })
        return tasks
    
    def launch_agent(self, agent_id: str, branch_name: str) -> subprocess.Popen:
        """Launch a single autonomous agent"""
        # Prepare the prompt with variables
        prompt_template = Path("prompts/swebench_agent.md").read_text()
        prompt = prompt_template.format(
            AGENT_ID=agent_id,
            BRANCH_NAME=branch_name,
            PM_AGENT_URL=self.pm_agent_url
        )
        
        # Create a temporary prompt file
        prompt_file = Path(f"/tmp/agent_{agent_id}_prompt.md")
        prompt_file.write_text(prompt)
        
        # Launch the agent using Claude
        cmd = [
            "claude-code",  # Assuming claude-code CLI is available
            "--mode", "autonomous",
            "--system-prompt", str(prompt_file),
            "--api-key", self.anthropic_key,
            "--pm-agent-url", self.pm_agent_url,
            "--log-file", f"logs/agent_{agent_id}.log"
        ]
        
        # For testing without claude-code, use a mock agent
        if not shutil.which("claude-code"):
            cmd = [
                sys.executable,
                "scripts/mock_agent.py",
                "--agent-id", agent_id,
                "--branch", branch_name,
                "--pm-agent-url", self.pm_agent_url,
                "--prompt", str(prompt_file)
            ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        return process
    
    async def launch_agents(self):
        """Launch all autonomous agents"""
        console.print(f"\n[bold blue]Launching {self.agent_count} agents...[/bold blue]")
        
        for i in range(self.agent_count):
            agent_id = f"baseline_agent_{i:03d}"
            branch_name = f"agent_{i:03d}_baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            process = self.launch_agent(agent_id, branch_name)
            self.agents.append({
                "id": agent_id,
                "branch": branch_name,
                "process": process,
                "status": "running"
            })
            
            console.print(f"[green]✓[/green] Launched {agent_id} on branch {branch_name}")
            
            # Small delay between launches
            await asyncio.sleep(2)
    
    async def monitor_progress(self):
        """Monitor experiment progress"""
        console.print("\n[bold blue]Monitoring experiment progress...[/bold blue]")
        
        async with aiohttp.ClientSession() as session:
            with Live(self.create_progress_table(), refresh_per_second=1) as live:
                while True:
                    # Get project status
                    async with session.get(
                        f"{self.pm_agent_url}/api/projects/{self.project_id}/status",
                        headers={"Authorization": f"Bearer {self.api_key}"}
                    ) as resp:
                        status = await resp.json()
                    
                    # Update live display
                    live.update(self.create_progress_table(status))
                    
                    # Check if all tasks are done
                    if status['tasks_completed'] + status['tasks_failed'] >= self.task_count:
                        break
                    
                    # Check agent health
                    for agent in self.agents:
                        if agent['process'].poll() is not None:
                            agent['status'] = 'stopped'
                    
                    await asyncio.sleep(5)
    
    def create_progress_table(self, status: Dict = None) -> Panel:
        """Create a rich progress display"""
        if not status:
            status = {
                'tasks_total': self.task_count,
                'tasks_completed': 0,
                'tasks_failed': 0,
                'tasks_in_progress': 0,
                'agents_active': 0
            }
        
        # Calculate metrics
        elapsed = time.time() - self.start_time if self.start_time else 0
        completion_rate = (status['tasks_completed'] / status['tasks_total'] * 100) if status['tasks_total'] > 0 else 0
        
        # Create table
        table = Table(title="Baseline Experiment Progress")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Elapsed Time", f"{elapsed:.0f}s")
        table.add_row("Total Tasks", str(status['tasks_total']))
        table.add_row("Completed", f"{status['tasks_completed']} ({completion_rate:.1f}%)")
        table.add_row("Failed", str(status['tasks_failed']))
        table.add_row("In Progress", str(status['tasks_in_progress']))
        table.add_row("Active Agents", f"{sum(1 for a in self.agents if a['status'] == 'running')}/{self.agent_count}")
        
        return Panel(table, title="[bold]SWE-bench Baseline Test[/bold]")
    
    async def collect_results(self) -> Dict:
        """Collect final experiment results"""
        console.print("\n[bold blue]Collecting results...[/bold blue]")
        
        async with aiohttp.ClientSession() as session:
            # Get final project status
            async with session.get(
                f"{self.pm_agent_url}/api/projects/{self.project_id}/status",
                headers={"Authorization": f"Bearer {self.api_key}"}
            ) as resp:
                final_status = await resp.json()
            
            # Get detailed task results
            task_results = []
            for task_id in self.task_ids:
                async with session.get(
                    f"{self.pm_agent_url}/api/tasks/{task_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                ) as resp:
                    task_results.append(await resp.json())
        
        # Calculate metrics
        completion_rate = (final_status['tasks_completed'] / final_status['tasks_total'] * 100)
        total_time = time.time() - self.start_time
        
        results = {
            "experiment": "baseline",
            "configuration": {
                "agents": self.agent_count,
                "tasks": self.task_count
            },
            "results": {
                "completion_rate": completion_rate,
                "total_tasks": final_status['tasks_total'],
                "completed_tasks": final_status['tasks_completed'],
                "failed_tasks": final_status['tasks_failed'],
                "total_time_seconds": total_time,
                "avg_time_per_task": total_time / final_status['tasks_total'],
                "tasks_per_hour": (final_status['tasks_completed'] / total_time) * 3600
            },
            "comparison": {
                "swe_bench_average": 25.0,
                "improvement": f"{(completion_rate / 25.0 - 1) * 100:.1f}%"
            },
            "task_details": task_results
        }
        
        return results
    
    def stop_agents(self):
        """Stop all running agents"""
        console.print("\n[bold yellow]Stopping agents...[/bold yellow]")
        for agent in self.agents:
            if agent['process'].poll() is None:
                agent['process'].terminate()
                console.print(f"[yellow]⚠[/yellow] Stopped {agent['id']}")
    
    async def run(self):
        """Run the complete experiment"""
        self.start_time = time.time()
        
        try:
            # Check PM Agent is running
            if not await self.check_pm_agent_running():
                console.print("[red]PM Agent is not running![/red]")
                console.print("Please start PM Agent with: python -m pm_agent.server")
                return
            
            # Setup project and tasks
            await self.setup_project()
            
            # Launch agents
            await self.launch_agents()
            
            # Monitor progress
            await self.monitor_progress()
            
            # Collect results
            results = await self.collect_results()
            
            # Save results
            results_file = Path(f"results/baseline/baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            results_file.parent.mkdir(parents=True, exist_ok=True)
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            # Display summary
            self.display_summary(results)
            
            console.print(f"\n[green]✓ Results saved to {results_file}[/green]")
            
        finally:
            # Clean up
            self.stop_agents()
    
    def display_summary(self, results: Dict):
        """Display experiment summary"""
        console.print("\n[bold green]Experiment Complete![/bold green]\n")
        
        table = Table(title="Baseline Experiment Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Task Completion Rate", f"{results['results']['completion_rate']:.1f}%")
        table.add_row("Tasks Completed", f"{results['results']['completed_tasks']}/{results['results']['total_tasks']}")
        table.add_row("Total Time", f"{results['results']['total_time_seconds']:.1f}s")
        table.add_row("Avg Time per Task", f"{results['results']['avg_time_per_task']:.1f}s")
        table.add_row("vs Industry Average", results['comparison']['improvement'])
        
        console.print(table)

@click.command()
@click.option('--agents', default=5, help='Number of agents to launch')
@click.option('--tasks', default=50, help='Number of tasks to test')
@click.option('--pm-agent-url', default='http://localhost:8000', help='PM Agent API URL')
def main(agents: int, tasks: int, pm_agent_url: str):
    """Run the full baseline experiment"""
    console.print(f"[bold]Starting SWE-bench Baseline Experiment[/bold]")
    console.print(f"Agents: {agents}, Tasks: {tasks}")
    
    runner = BaselineExperimentRunner(agents, tasks, pm_agent_url)
    asyncio.run(runner.run())

if __name__ == "__main__":
    import shutil
    main()