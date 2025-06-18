#!/usr/bin/env python3
"""
Mock Claude Worker Agent for PM Agent Testing

This script simulates a Claude worker that:
1. Registers with PM Agent
2. Requests tasks
3. Simulates work with progress updates
4. Reports completion
"""

import asyncio
import json
import random
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, '/Users/lwgray/dev/pm-agent')

from src.integrations.mcp_kanban_client import MCPKanbanClient


class MockClaudeWorker:
    """Mock Claude worker agent for testing PM Agent"""
    
    def __init__(self, agent_id: str, agent_name: str, role: str, skills: list):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.role = role
        self.skills = skills
        self.current_task = None
        self.mcp_client = None
        self.work_speed = random.uniform(0.5, 1.5)  # Randomize work speed
        
    async def initialize(self):
        """Initialize MCP connection to PM Agent"""
        try:
            # Initialize MCP client connection to PM Agent
            self.mcp_client = MCPKanbanClient()
            await self.mcp_client.initialize()
            print(f"[{self.agent_name}] Initialized MCP connection")
            return True
        except Exception as e:
            print(f"[{self.agent_name}] Failed to initialize: {e}")
            return False
            
    async def register(self):
        """Register with PM Agent"""
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
            print(f"[{self.agent_name}] Registered successfully: {result}")
            return True
        except Exception as e:
            print(f"[{self.agent_name}] Registration failed: {e}")
            return False
            
    async def request_task(self) -> Optional[Dict[str, Any]]:
        """Request next task from PM Agent"""
        try:
            result = await self.mcp_client.call_tool(
                "request_next_task",
                {"agent_id": self.agent_id}
            )
            
            if result and result.get("task"):
                self.current_task = result["task"]
                print(f"[{self.agent_name}] Received task: {self.current_task['title']}")
                return self.current_task
            else:
                print(f"[{self.agent_name}] No tasks available")
                return None
                
        except Exception as e:
            print(f"[{self.agent_name}] Error requesting task: {e}")
            return None
            
    async def work_on_task(self):
        """Simulate working on a task with progress updates"""
        if not self.current_task:
            return
            
        task_id = self.current_task["id"]
        estimated_hours = self.current_task.get("estimated_hours", 4)
        
        # Simulate work with progress updates
        progress_intervals = [25, 50, 75, 100]
        
        for progress in progress_intervals:
            # Simulate work time (accelerated for demo)
            work_time = (estimated_hours * 0.25 * self.work_speed * 2)  # 2 seconds per hour for demo
            print(f"[{self.agent_name}] Working on task... ({progress}%)")
            await asyncio.sleep(work_time)
            
            # Report progress
            status = "completed" if progress == 100 else "in_progress"
            message = self._generate_progress_message(progress)
            
            try:
                await self.mcp_client.call_tool(
                    "report_task_progress",
                    {
                        "agent_id": self.agent_id,
                        "task_id": task_id,
                        "status": status,
                        "progress": progress,
                        "message": message
                    }
                )
                print(f"[{self.agent_name}] Progress reported: {progress}% - {message}")
                
            except Exception as e:
                print(f"[{self.agent_name}] Error reporting progress: {e}")
                
        # Clear current task
        self.current_task = None
        
    def _generate_progress_message(self, progress: int) -> str:
        """Generate realistic progress messages"""
        messages = {
            25: [
                "Initial setup complete, beginning implementation",
                "Environment configured, starting development",
                "Requirements analyzed, coding started"
            ],
            50: [
                "Core functionality implemented, adding features",
                "Main logic complete, working on edge cases",
                "Basic implementation done, adding enhancements"
            ],
            75: [
                "Implementation complete, writing tests",
                "Features done, performing testing",
                "Code complete, running validation"
            ],
            100: [
                "Task completed successfully with all tests passing",
                "Implementation finished and validated",
                "All requirements met, ready for review"
            ]
        }
        
        return random.choice(messages.get(progress, ["Making progress..."]))
        
    async def report_blocker(self, blocker_description: str, severity: str = "medium"):
        """Report a blocker on current task"""
        if not self.current_task:
            return
            
        try:
            result = await self.mcp_client.call_tool(
                "report_blocker",
                {
                    "agent_id": self.agent_id,
                    "task_id": self.current_task["id"],
                    "blocker_description": blocker_description,
                    "severity": severity
                }
            )
            print(f"[{self.agent_name}] Blocker reported: {blocker_description}")
            
        except Exception as e:
            print(f"[{self.agent_name}] Error reporting blocker: {e}")
            
    async def run(self):
        """Main worker loop"""
        print(f"\n{'='*60}")
        print(f"Mock Claude Worker: {self.agent_name}")
        print(f"Role: {self.role}")
        print(f"Skills: {', '.join(self.skills)}")
        print(f"{'='*60}\n")
        
        # Initialize and register
        if not await self.initialize():
            return
            
        if not await self.register():
            return
            
        # Work loop
        consecutive_no_task = 0
        
        while True:
            # Request a task
            task = await self.request_task()
            
            if task:
                consecutive_no_task = 0
                
                # Simulate occasional blockers (10% chance)
                if random.random() < 0.1:
                    blocker = random.choice([
                        "Waiting for API credentials",
                        "Database schema needs clarification",
                        "Dependency not available",
                        "Requirement unclear"
                    ])
                    await self.report_blocker(blocker)
                    await asyncio.sleep(5)  # Wait a bit
                    continue
                    
                # Work on the task
                await self.work_on_task()
                
                # Brief pause between tasks
                await asyncio.sleep(2)
                
            else:
                consecutive_no_task += 1
                print(f"[{self.agent_name}] Waiting for tasks... ({consecutive_no_task})")
                
                # Exit after 5 consecutive no-task responses
                if consecutive_no_task >= 5:
                    print(f"[{self.agent_name}] No more tasks available. Shutting down.")
                    break
                    
                # Wait before checking again
                await asyncio.sleep(5)
                
        # Cleanup
        if self.mcp_client:
            await self.mcp_client.close()


async def main():
    """Run mock Claude workers"""
    
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
    
    # Let user choose which worker to run
    print("Available workers:")
    for i, worker in enumerate(workers):
        print(f"{i+1}. {worker['agent_name']} ({worker['role']})")
        
    choice = input("\nSelect worker (1-3) or 'all' for all workers: ").strip()
    
    if choice.lower() == 'all':
        # Run all workers concurrently
        tasks = []
        for worker_config in workers:
            worker = MockClaudeWorker(**worker_config)
            tasks.append(worker.run())
        await asyncio.gather(*tasks)
    else:
        # Run single worker
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(workers):
                worker = MockClaudeWorker(**workers[idx])
                await worker.run()
            else:
                print("Invalid selection")
        except ValueError:
            print("Invalid input")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nWorker shutdown requested")
    except Exception as e:
        print(f"\nError: {e}")