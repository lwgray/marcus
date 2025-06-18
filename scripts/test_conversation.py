#!/usr/bin/env python3
"""
Simple test to verify conversation logging between PM Agent and Worker
"""

import asyncio
import sys
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, '/Users/lwgray/dev/pm-agent')

# Simple console colors
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    END = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


def log_pm_thinking(message):
    """Log PM Agent thinking"""
    print(f"\n{Colors.DIM}{Colors.CYAN}🧠 PM Agent thinking:{Colors.END} {message}")


def log_pm_decision(decision, reason):
    """Log PM Agent decision"""
    print(f"\n{Colors.BOLD}{Colors.YELLOW}📋 PM Decision:{Colors.END}")
    print(f"   {Colors.YELLOW}Decision:{Colors.END} {decision}")
    print(f"   {Colors.DIM}Reason:{Colors.END} {reason}")


def log_worker_thinking(worker_name, message):
    """Log Worker thinking"""
    print(f"\n{Colors.DIM}{Colors.GREEN}💭 {worker_name} thinking:{Colors.END} {message}")


def log_conversation(sender, receiver, message, direction="→"):
    """Log conversation between agents"""
    if direction == "→":
        print(f"\n{Colors.BOLD}{Colors.BLUE}💬 {sender} → {receiver}:{Colors.END}")
    else:
        print(f"\n{Colors.BOLD}{Colors.MAGENTA}💬 {sender} ← {receiver}:{Colors.END}")
    print(f"   {message}")


# Simulate PM Agent side
class MockPMAgent:
    def __init__(self):
        self.agents = {}
        self.tasks = [
            {"id": "task-1", "title": "Implement user authentication", "priority": "high", "hours": 4},
            {"id": "task-2", "title": "Create API endpoints", "priority": "medium", "hours": 3},
            {"id": "task-3", "title": "Write unit tests", "priority": "medium", "hours": 2}
        ]
        self.assigned_tasks = set()
    
    async def handle_register(self, agent_data):
        """Handle agent registration"""
        agent_id = agent_data["agent_id"]
        log_conversation("Worker", "PM Agent", 
                        f"Hello! I'm {agent_data['name']}, a {agent_data['role']} with skills: {', '.join(agent_data['skills'])}")
        
        log_pm_thinking(f"New agent wants to register: {agent_data['name']}")
        log_pm_thinking(f"Skills assessment: {agent_data['skills']} - Good match for our tasks")
        
        self.agents[agent_id] = agent_data
        
        log_pm_decision(
            f"Register {agent_data['name']}",
            "Skills match project requirements, agent seems capable"
        )
        
        log_conversation("PM Agent", "Worker",
                        f"Welcome {agent_data['name']}! You're registered and ready to receive tasks.")
        
        return {"success": True}
    
    async def handle_task_request(self, agent_id):
        """Handle task request from agent"""
        agent = self.agents.get(agent_id, {})
        agent_name = agent.get("name", agent_id)
        
        log_conversation("Worker", "PM Agent",
                        "I'm available for work. Do you have any tasks that match my skills?")
        
        log_pm_thinking("Checking available tasks and agent skills match")
        log_pm_thinking(f"Available tasks: {len(self.tasks) - len(self.assigned_tasks)}")
        log_pm_thinking(f"Agent skills: {agent.get('skills', [])}")
        
        # Find unassigned task
        for task in self.tasks:
            if task["id"] not in self.assigned_tasks:
                self.assigned_tasks.add(task["id"])
                
                log_pm_decision(
                    f"Assign '{task['title']}' to {agent_name}",
                    f"Task priority: {task['priority']}, Good skill match, Agent available"
                )
                
                log_conversation("PM Agent", "Worker",
                    f"I have a perfect task for you: '{task['title']}'\n"
                    f"   Priority: {task['priority']}\n"
                    f"   Estimated: {task['hours']} hours")
                
                return {"has_task": True, "task": task}
        
        log_pm_decision(
            f"No task assigned to {agent_name}",
            "All tasks are currently assigned to other agents"
        )
        
        log_conversation("PM Agent", "Worker",
                        "No suitable tasks available right now. Check back soon.")
        
        return {"has_task": False}
    
    async def handle_progress(self, data):
        """Handle progress report"""
        agent_name = self.agents.get(data["agent_id"], {}).get("name", data["agent_id"])
        
        log_conversation("Worker", "PM Agent",
            f"Progress update on task:\n"
            f"   Status: {data['status']}\n"
            f"   Progress: {data['progress']}%\n"
            f"   Message: {data['message']}")
        
        log_pm_thinking(f"Progress looks good. {agent_name} is making steady progress.")
        
        if data["status"] == "completed":
            log_pm_decision(
                f"Mark task as completed",
                f"{agent_name} has finished the task successfully"
            )
            self.assigned_tasks.discard(data.get("task_id"))
        
        log_conversation("PM Agent", "Worker",
                        "Progress update received. Keep up the good work!")
        
        return {"success": True}


# Simulate Worker side
class MockWorker:
    def __init__(self, agent_id, name, role, skills):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.skills = skills
        self.current_task = None
        self.pm_agent = MockPMAgent()
    
    async def run(self):
        """Run worker simulation"""
        print(f"\n{Colors.BOLD}{Colors.GREEN}=== Starting {self.name} ==={Colors.END}")
        
        # Register
        log_worker_thinking(self.name, "Time to register with PM Agent")
        await self.pm_agent.handle_register({
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "skills": self.skills
        })
        
        await asyncio.sleep(1)
        
        # Request task
        log_worker_thinking(self.name, "Let me check if there's any work for me")
        result = await self.pm_agent.handle_task_request(self.agent_id)
        
        if result["has_task"]:
            self.current_task = result["task"]
            log_worker_thinking(self.name, 
                f"Great! I got a task: '{self.current_task['title']}'. "
                f"Should take about {self.current_task['hours']} hours.")
            
            # Work on task
            await asyncio.sleep(1)
            
            # Report progress
            for progress in [25, 50, 75, 100]:
                log_worker_thinking(self.name, f"Making progress... {progress}% done")
                
                messages = {
                    25: "Initial setup complete, starting implementation",
                    50: "Core functionality implemented",
                    75: "Adding tests and documentation",
                    100: "Task completed successfully!"
                }
                
                await self.pm_agent.handle_progress({
                    "agent_id": self.agent_id,
                    "task_id": self.current_task["id"],
                    "status": "completed" if progress == 100 else "in_progress",
                    "progress": progress,
                    "message": messages[progress]
                })
                
                await asyncio.sleep(1)
            
            log_worker_thinking(self.name, "Task complete! Ready for the next one.")
        else:
            log_worker_thinking(self.name, "No tasks available. I'll check again later.")


async def main():
    """Run conversation test"""
    print(f"{Colors.BOLD}{Colors.CYAN}PM Agent - Worker Conversation Test{Colors.END}")
    print("=" * 60)
    print("\nThis test simulates the conversation between PM Agent and Workers")
    print("Watch how they communicate and make decisions!\n")
    
    # Create a worker
    worker = MockWorker(
        agent_id="test-worker-1",
        name="Claude Test Worker",
        role="Backend Developer",
        skills=["python", "api", "testing"]
    )
    
    # Run simulation
    await worker.run()
    
    print(f"\n{Colors.BOLD}{Colors.GREEN}Test Complete!{Colors.END}")
    print("\nThe actual PM Agent will have more sophisticated decision-making")
    print("and will coordinate multiple workers simultaneously.")


if __name__ == "__main__":
    asyncio.run(main())