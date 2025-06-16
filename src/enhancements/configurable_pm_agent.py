"""
Enhanced PM Agent with project/board configuration support
"""

import json
import os
from typing import Optional, Dict, Any
from pm_agent_mvp_fixed import PMAgentMVP


class ConfigurablePMAgent(PMAgentMVP):
    """PM Agent with configuration file support"""
    
    def __init__(self, config_file: Optional[str] = None):
        super().__init__()
        self.config_file = config_file or "config_pm_agent.json"
        self._load_configuration()
    
    def _load_configuration(self):
        """Load configuration from file or environment"""
        config = {}
        
        # Try to load from file
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                print(f"📋 Loaded configuration from {self.config_file}")
        
        # Override with environment variables if present
        if os.getenv("PM_AGENT_PROJECT_ID"):
            config["project_id"] = os.getenv("PM_AGENT_PROJECT_ID")
        if os.getenv("PM_AGENT_BOARD_ID"):
            config["board_id"] = os.getenv("PM_AGENT_BOARD_ID")
        
        # Apply configuration
        if config.get("project_id"):
            self.kanban_client.project_id = config["project_id"]
            print(f"🎯 Configured for project: {config.get('project_name', config['project_id'])}")
        
        if config.get("board_id"):
            self.kanban_client.board_id = config["board_id"]
            print(f"📋 Configured for board: {config['board_id']}")
        
        # Update Planka credentials if provided
        if config.get("planka"):
            planka_config = config["planka"]
            if planka_config.get("base_url"):
                self.kanban_client._env["PLANKA_BASE_URL"] = planka_config["base_url"]
            if planka_config.get("email"):
                self.kanban_client._env["PLANKA_AGENT_EMAIL"] = planka_config["email"]
            if planka_config.get("password"):
                self.kanban_client._env["PLANKA_AGENT_PASSWORD"] = planka_config["password"]
    
    async def start(self):
        """Start with auto-configuration"""
        # If board_id not set but project_id is, try to find the board
        if self.kanban_client.project_id and not self.kanban_client.board_id:
            print("🔍 Finding board for project...")
            async with self.kanban_client.connect() as conn:
                # The connect method will auto-find the board
                if self.kanban_client.board_id:
                    print(f"✅ Found board: {self.kanban_client.board_id}")
                else:
                    print("⚠️  No board found, will need to create one")
        
        # Continue with normal startup
        await super().start()
    
    async def _get_project_status(self) -> dict:
        """Enhanced project status with configuration info"""
        result = await super()._get_project_status()
        
        # Add configuration info
        if result.get("success"):
            result["configuration"] = {
                "project_id": self.kanban_client.project_id,
                "board_id": self.kanban_client.board_id,
                "config_file": self.config_file
            }
        
        return result


if __name__ == "__main__":
    import asyncio
    
    # Start with configuration file
    agent = ConfigurablePMAgent("config_pm_agent.json")
    asyncio.run(agent.start())