"""
PM Agent API Client for experiments
Provides interface to interact with PM Agent during experiments
"""

import os
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PMAgentClient:
    """Client for interacting with PM Agent API"""
    
    def __init__(self, num_agents: int = 1, parallel: bool = True):
        self.base_url = os.getenv("PM_AGENT_API_URL", "http://localhost:8000")
        self.api_key = os.getenv("PM_AGENT_API_KEY", "")
        self.num_agents = num_agents
        self.parallel = parallel
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def create_project(self, name: str, description: str) -> str:
        """Create a new project in PM Agent"""
        async with self.session.post(
            f"{self.base_url}/api/projects",
            json={
                "name": name,
                "description": description,
                "created_at": datetime.now().isoformat()
            }
        ) as response:
            data = await response.json()
            return data["project_id"]
    
    async def register_agents(self, count: int) -> List[str]:
        """Register multiple agents"""
        agent_ids = []
        for i in range(count):
            agent_id = await self.register_agent(
                name=f"experiment_agent_{i}",
                capabilities=["coding", "testing", "debugging"]
            )
            agent_ids.append(agent_id)
        return agent_ids
    
    async def register_agent(self, name: str, capabilities: List[str]) -> str:
        """Register a single agent"""
        async with self.session.post(
            f"{self.base_url}/api/agents/register",
            json={
                "name": name,
                "capabilities": capabilities,
                "status": "available"
            }
        ) as response:
            data = await response.json()
            return data["agent_id"]
    
    async def create_task(self, project_id: str, title: str, 
                         description: str, metadata: Dict = None) -> str:
        """Create a task in the project"""
        async with self.session.post(
            f"{self.base_url}/api/projects/{project_id}/tasks",
            json={
                "title": title,
                "description": description,
                "metadata": metadata or {},
                "status": "pending",
                "created_at": datetime.now().isoformat()
            }
        ) as response:
            data = await response.json()
            return data["task_id"]
    
    async def request_next_task(self, agent_id: str) -> Optional[Dict]:
        """Request next available task for agent"""
        async with self.session.post(
            f"{self.base_url}/api/agents/{agent_id}/request-task"
        ) as response:
            if response.status == 200:
                return await response.json()
            return None
    
    async def report_progress(self, task_id: str, agent_id: str, 
                            progress: int, message: str):
        """Report task progress"""
        async with self.session.post(
            f"{self.base_url}/api/tasks/{task_id}/progress",
            json={
                "agent_id": agent_id,
                "progress": progress,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
        ) as response:
            return response.status == 200
    
    async def report_completion(self, task_id: str, agent_id: str, 
                              result: str):
        """Report task completion"""
        async with self.session.post(
            f"{self.base_url}/api/tasks/{task_id}/complete",
            json={
                "agent_id": agent_id,
                "result": result,
                "completed_at": datetime.now().isoformat()
            }
        ) as response:
            return response.status == 200
    
    async def report_failure(self, task_id: str, agent_id: str, 
                           error: str):
        """Report task failure"""
        async with self.session.post(
            f"{self.base_url}/api/tasks/{task_id}/fail",
            json={
                "agent_id": agent_id,
                "error": error,
                "failed_at": datetime.now().isoformat()
            }
        ) as response:
            return response.status == 200
    
    async def report_blocker(self, task_id: str, agent_id: str, 
                           blocker: str) -> Dict:
        """Report a blocker and get suggestions"""
        async with self.session.post(
            f"{self.base_url}/api/tasks/{task_id}/blocker",
            json={
                "agent_id": agent_id,
                "blocker": blocker,
                "timestamp": datetime.now().isoformat()
            }
        ) as response:
            return await response.json()
    
    async def get_task_result(self, task_id: str) -> Dict:
        """Get final task result"""
        async with self.session.get(
            f"{self.base_url}/api/tasks/{task_id}"
        ) as response:
            return await response.json()
    
    async def get_project_status(self, project_id: str) -> Dict:
        """Get project status and metrics"""
        async with self.session.get(
            f"{self.base_url}/api/projects/{project_id}/status"
        ) as response:
            return await response.json()

# Singleton client instance
_client_instance = None

def get_pm_agent_client(num_agents: int = 1, parallel: bool = True) -> PMAgentClient:
    """Get or create PM Agent client instance"""
    global _client_instance
    if _client_instance is None:
        _client_instance = PMAgentClient(num_agents, parallel)
    return _client_instance