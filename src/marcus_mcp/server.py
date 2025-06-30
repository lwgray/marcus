#!/usr/bin/env python3
"""
Marcus MCP Server - Modularized Version

A lean MCP server implementation that delegates all tool logic
to specialized modules for better maintainability.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import atexit

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

from src.core.models import (
    TaskStatus, Priority, RiskLevel,
    ProjectState, WorkerStatus, TaskAssignment
)
from src.integrations.kanban_factory import KanbanFactory
from src.integrations.kanban_interface import KanbanInterface
from src.integrations.ai_analysis_engine_fixed import AIAnalysisEngine
from src.core.code_analyzer import CodeAnalyzer
from src.monitoring.project_monitor import ProjectMonitor
from src.communication.communication_hub import CommunicationHub
from src.config.settings import Settings
from src.logging.conversation_logger import conversation_logger
from src.core.assignment_persistence import AssignmentPersistence
from src.monitoring.assignment_monitor import AssignmentMonitor

from .handlers import get_tool_definitions, handle_tool_call


class MarcusServer:
    """Marcus MCP Server with modularized architecture"""
    
    def __init__(self):
        """Initialize Marcus server instance"""
        load_dotenv()
        self.settings = Settings()
        
        # Get kanban provider from environment
        self.provider = os.getenv('KANBAN_PROVIDER', 'planka')
        print(f"Initializing Marcus with {self.provider.upper()} kanban provider...")
        
        # Create realtime log with line buffering
        log_dir = Path("logs/conversations")
        log_dir.mkdir(parents=True, exist_ok=True)
        self.realtime_log = open(
            log_dir / f"realtime_{datetime.now():%Y%m%d_%H%M%S}.jsonl", 
            'a', 
            buffering=1  # Line buffering
        )
        atexit.register(self.realtime_log.close)
        
        # Core components
        self.kanban_client: Optional[KanbanInterface] = None
        self.ai_engine = AIAnalysisEngine()
        self.monitor = ProjectMonitor()
        self.comm_hub = CommunicationHub()
        
        # Code analyzer for GitHub
        self.code_analyzer = None
        if self.provider == 'github':
            self.code_analyzer = CodeAnalyzer()
        
        # State tracking
        self.agent_tasks: Dict[str, TaskAssignment] = {}
        self.agent_status: Dict[str, WorkerStatus] = {}
        self.project_state: Optional[ProjectState] = None
        self.project_tasks: List[Any] = []
        
        # Assignment persistence and locking
        self.assignment_persistence = AssignmentPersistence()
        self.assignment_lock = asyncio.Lock()
        self.tasks_being_assigned: set = set()
        
        # Assignment monitoring
        self.assignment_monitor = None
        
        # Log startup
        self.log_event("server_startup", {
            "provider": self.provider,
            "timestamp": datetime.now().isoformat()
        })
        
        # Create MCP server instance
        self.server = Server("marcus")
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register MCP tool handlers"""
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """Return list of available tools"""
            return get_tool_definitions()
        
        @self.server.call_tool()
        async def handle_call_tool(
            name: str, 
            arguments: Optional[Dict[str, Any]]
        ) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """Handle tool calls"""
            return await handle_tool_call(name, arguments, self)
    
    async def initialize_kanban(self):
        """Initialize kanban client if not already done"""
        if not self.kanban_client:
            self.kanban_client = KanbanFactory.create(self.provider)
            
            # Connect to the kanban board
            if hasattr(self.kanban_client, 'connect'):
                await self.kanban_client.connect()
            
            # Initialize assignment monitor
            if self.assignment_monitor is None:
                self.assignment_monitor = AssignmentMonitor(
                    self.assignment_persistence,
                    self.kanban_client
                )
                await self.assignment_monitor.start()
    
    def log_event(self, event_type: str, data: dict):
        """Log events immediately to realtime log"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            **data
        }
        self.realtime_log.write(json.dumps(event) + '\n')
    
    async def refresh_project_state(self):
        """Refresh project state from kanban board"""
        if not self.kanban_client:
            await self.initialize_kanban()
        
        try:
            # Get all tasks from the board
            self.project_tasks = await self.kanban_client.get_all_tasks()
            
            # Update project state
            if self.project_tasks:
                total_tasks = len(self.project_tasks)
                completed_tasks = len([t for t in self.project_tasks if t.status == TaskStatus.DONE])
                in_progress_tasks = len([t for t in self.project_tasks if t.status == TaskStatus.IN_PROGRESS])
                
                self.project_state = ProjectState(
                    board_id=self.kanban_client.board_id,
                    project_name="Current Project",  # Would need to get from board
                    total_tasks=total_tasks,
                    completed_tasks=completed_tasks,
                    in_progress_tasks=in_progress_tasks,
                    blocked_tasks=0,  # Would need to track this separately
                    progress_percent=(completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0,
                    overdue_tasks=[],  # Would need to check due dates
                    team_velocity=0.0,  # Would need to calculate
                    risk_level=RiskLevel.LOW,  # Simplified
                    last_updated=datetime.now()
                )
            
            self.log_event("project_state_refreshed", {
                "task_count": len(self.project_tasks),
                "project_state": self.project_state.__dict__ if self.project_state else None
            })
            
        except Exception as e:
            self.log_event("project_state_refresh_error", {"error": str(e)})
            raise
    
    async def run(self):
        """Run the MCP server"""
        print(f"\nMarcus MCP Server Running")
        print(f"Kanban Provider: {self.provider.upper()}")
        print(f"Logs: logs/conversations/")
        print("="*50)
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point"""
    server = MarcusServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())