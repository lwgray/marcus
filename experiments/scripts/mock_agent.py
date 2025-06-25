#!/usr/bin/env python3
"""
Mock agent for testing experiments without Claude API
Simulates an autonomous agent working through PM Agent
"""

import asyncio
import random
import time
import argparse
import json
from datetime import datetime
from pathlib import Path
import aiohttp

class MockAgent:
    """Simulates an autonomous agent for testing"""
    
    def __init__(self, agent_id: str, branch: str, pm_agent_url: str):
        self.agent_id = agent_id
        self.branch = branch
        self.pm_agent_url = pm_agent_url
        self.registered = False
        self.current_task = None
        
        # Simulate agent characteristics
        self.skill_level = random.uniform(0.3, 0.9)  # Affects success rate
        self.speed = random.uniform(0.8, 1.2)  # Affects task time
        
    async def register(self):
        """Register with PM Agent"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.pm_agent_url}/api/agents/register",
                json={
                    "name": self.agent_id,
                    "capabilities": ["python", "debugging", "testing", "git"],
                    "branch": self.branch
                }
            ) as resp:
                if resp.status == 200:
                    self.registered = True
                    print(f"[{self.agent_id}] Registered successfully")
                else:
                    print(f"[{self.agent_id}] Registration failed")
    
    async def request_task(self):
        """Request next task from PM Agent"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.pm_agent_url}/api/agents/{self.agent_id}/request-task"
            ) as resp:
                if resp.status == 200:
                    self.current_task = await resp.json()
                    print(f"[{self.agent_id}] Received task: {self.current_task['title']}")
                    return True
                else:
                    print(f"[{self.agent_id}] No tasks available")
                    return False
    
    async def work_on_task(self):
        """Simulate working on the current task"""
        if not self.current_task:
            return
        
        task_id = self.current_task['id']
        
        # Report 25% progress
        await self.report_progress(task_id, 25, "Analyzing the issue")
        await asyncio.sleep(random.uniform(5, 10) * self.speed)
        
        # Report 50% progress
        await self.report_progress(task_id, 50, "Implementing solution")
        await asyncio.sleep(random.uniform(10, 20) * self.speed)
        
        # Check for random blocker
        if random.random() < 0.1:  # 10% chance of blocker
            await self.report_blocker(task_id, "Cannot locate the failing test file")
            await asyncio.sleep(5)
        
        # Report 75% progress
        await self.report_progress(task_id, 75, "Running tests")
        await asyncio.sleep(random.uniform(5, 10) * self.speed)
        
        # Determine success based on skill level and task difficulty
        task_difficulty = self.estimate_difficulty()
        success_chance = self.skill_level * (1 - task_difficulty * 0.5)
        success = random.random() < success_chance
        
        if success:
            # Report completion
            await self.report_progress(
                task_id, 100, 
                f"Fixed issue. All tests passing. Committed to branch {self.branch}"
            )
            print(f"[{self.agent_id}] Completed task successfully")
        else:
            # Report failure
            await self.report_failure(
                task_id,
                "Tests still failing after implementation attempt"
            )
            print(f"[{self.agent_id}] Failed to complete task")
        
        self.current_task = None
    
    def estimate_difficulty(self) -> float:
        """Estimate task difficulty from description"""
        if not self.current_task:
            return 0.5
        
        description = self.current_task.get('description', '').lower()
        
        # Simple heuristic based on keywords
        if any(word in description for word in ['complex', 'refactor', 'architecture']):
            return 0.8
        elif any(word in description for word in ['fix', 'bug', 'error']):
            return 0.4
        else:
            return 0.5
    
    async def report_progress(self, task_id: str, progress: int, message: str):
        """Report progress to PM Agent"""
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{self.pm_agent_url}/api/tasks/{task_id}/progress",
                json={
                    "agent_id": self.agent_id,
                    "progress": progress,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                }
            )
    
    async def report_blocker(self, task_id: str, blocker: str):
        """Report a blocker"""
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{self.pm_agent_url}/api/tasks/{task_id}/blocker",
                json={
                    "agent_id": self.agent_id,
                    "blocker": blocker,
                    "timestamp": datetime.now().isoformat()
                }
            )
    
    async def report_failure(self, task_id: str, error: str):
        """Report task failure"""
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{self.pm_agent_url}/api/tasks/{task_id}/fail",
                json={
                    "agent_id": self.agent_id,
                    "error": error,
                    "timestamp": datetime.now().isoformat()
                }
            )
    
    async def run(self):
        """Main agent loop"""
        print(f"[{self.agent_id}] Starting mock agent (skill={self.skill_level:.2f}, speed={self.speed:.2f})")
        
        # Register with PM Agent
        await self.register()
        if not self.registered:
            print(f"[{self.agent_id}] Failed to register, exiting")
            return
        
        # Work loop
        consecutive_no_tasks = 0
        while consecutive_no_tasks < 5:  # Exit after 5 consecutive "no tasks"
            # Request a task
            if await self.request_task():
                consecutive_no_tasks = 0
                # Work on the task
                await self.work_on_task()
            else:
                consecutive_no_tasks += 1
                # Wait before trying again
                await asyncio.sleep(10)
        
        print(f"[{self.agent_id}] No more tasks available, shutting down")

def main():
    parser = argparse.ArgumentParser(description='Mock agent for PM Agent experiments')
    parser.add_argument('--agent-id', required=True, help='Agent identifier')
    parser.add_argument('--branch', required=True, help='Git branch name')
    parser.add_argument('--pm-agent-url', default='http://localhost:8000', help='PM Agent API URL')
    parser.add_argument('--prompt', help='Prompt file (ignored for mock)')
    
    args = parser.parse_args()
    
    agent = MockAgent(args.agent_id, args.branch, args.pm_agent_url)
    asyncio.run(agent.run())

if __name__ == "__main__":
    main()