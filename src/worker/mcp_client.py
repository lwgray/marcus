"""
MCP Client for Worker Agents to connect to PM Agent Server
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
import subprocess
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class WorkerMCPClient:
    """MCP Client for workers to communicate with PM Agent"""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        
    @asynccontextmanager
    async def connect_to_pm_agent(self):
        """Connect to PM Agent MCP server"""
        # PM Agent server command
        server_cmd = [
            "python",
            os.path.join(os.path.dirname(__file__), "..", "..", "pm_agent_mcp_server.py")
        ]
        
        server_params = StdioServerParameters(
            command=server_cmd[0],
            args=server_cmd[1:],
            env=None
        )
        
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                self.session = session
                await session.initialize()
                
                # List available tools to verify connection
                tools = await session.list_tools()
                print(f"Connected to PM Agent. Available tools: {[t.name for t in tools]}")
                
                yield session
                
    async def register_agent(self, agent_id: str, name: str, role: str, skills: List[str]) -> Dict[str, Any]:
        """Register worker with PM Agent"""
        if not self.session:
            raise RuntimeError("Not connected to PM Agent")
            
        result = await self.session.call_tool(
            "register_agent",
            arguments={
                "agent_id": agent_id,
                "name": name,
                "role": role,
                "skills": skills
            }
        )
        
        return json.loads(result.content[0].text) if result.content else {}
        
    async def request_next_task(self, agent_id: str) -> Dict[str, Any]:
        """Request next task from PM Agent"""
        if not self.session:
            raise RuntimeError("Not connected to PM Agent")
            
        result = await self.session.call_tool(
            "request_next_task",
            arguments={"agent_id": agent_id}
        )
        
        return json.loads(result.content[0].text) if result.content else {}
        
    async def report_task_progress(
        self, 
        agent_id: str, 
        task_id: str, 
        status: str,
        progress: int = 0,
        message: str = ""
    ) -> Dict[str, Any]:
        """Report task progress to PM Agent"""
        if not self.session:
            raise RuntimeError("Not connected to PM Agent")
            
        result = await self.session.call_tool(
            "report_task_progress",
            arguments={
                "agent_id": agent_id,
                "task_id": task_id,
                "status": status,
                "progress": progress,
                "message": message
            }
        )
        
        return json.loads(result.content[0].text) if result.content else {}
        
    async def report_blocker(
        self,
        agent_id: str,
        task_id: str,
        blocker_description: str,
        severity: str = "medium"
    ) -> Dict[str, Any]:
        """Report blocker to PM Agent"""
        if not self.session:
            raise RuntimeError("Not connected to PM Agent")
            
        result = await self.session.call_tool(
            "report_blocker",
            arguments={
                "agent_id": agent_id,
                "task_id": task_id,
                "blocker_description": blocker_description,
                "severity": severity
            }
        )
        
        return json.loads(result.content[0].text) if result.content else {}
        
    async def get_project_status(self) -> Dict[str, Any]:
        """Get project status from PM Agent"""
        if not self.session:
            raise RuntimeError("Not connected to PM Agent")
            
        result = await self.session.call_tool(
            "get_project_status",
            arguments={}
        )
        
        return json.loads(result.content[0].text) if result.content else {}