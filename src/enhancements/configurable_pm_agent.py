"""
Enhanced Marcus with project/board configuration support.

This module provides a configurable Marcus that extends the base PMAgentMVP
with configuration file and environment variable support for project and board
management across different environments.

Examples
--------
>>> agent = ConfigurablePMAgent("config_marcus.json")
>>> await agent.start()

>>> # Using environment variables
>>> import os
>>> os.environ["MARCUS_PROJECT_ID"] = "project-123"
>>> agent = ConfigurablePMAgent()
>>> await agent.start()
"""

import json
import os
from typing import Any, Dict, Optional, Union

from src.legacy.marcus_mvp import MarcusMVP


class ConfigurablePMAgent(MarcusMVP):
    """Marcus with configuration file and environment variable support.

    This class extends MarcusMVP to provide flexible configuration management
    through JSON files and environment variables, enabling different deployment
    configurations for development, staging, and production environments.

    Parameters
    ----------
    config_file : Optional[str], default "config_marcus.json"
        Path to the JSON configuration file. If None, defaults to
        "config_marcus.json" in the current directory.

    Attributes
    ----------
    config_file : str
        Path to the configuration file being used.

    Examples
    --------
    >>> # Basic usage with default config file
    >>> agent = ConfigurablePMAgent()
    >>> await agent.start()

    >>> # Custom config file
    >>> agent = ConfigurablePMAgent("prod_config.json")
    >>> await agent.start()

    >>> # Configuration file format:
    >>> config = {
    ...     "project_id": "project-123",
    ...     "board_id": "board-456",
    ...     "project_name": "My Project",
    ...     "planka": {
    ...         "base_url": "https://planka.example.com",
    ...         "email": "agent@example.com",
    ...         "password": "secure_password"
    ...     }
    ... }
    """

    def __init__(self, config_file: Optional[str] = None) -> None:
        """Initialize ConfigurablePMAgent with optional configuration file.

        Parameters
        ----------
        config_file : Optional[str], default None
            Path to JSON configuration file. If None, uses "config_marcus.json".

        Examples
        --------
        >>> agent = ConfigurablePMAgent()
        >>> agent = ConfigurablePMAgent("/path/to/config.json")
        """
        super().__init__()
        self.config_file = config_file or "config_marcus.json"
        self._load_configuration()

    def _load_configuration(self) -> None:
        """Load configuration from file and environment variables.

        Loads configuration settings in the following priority order:
        1. Configuration file (if it exists)
        2. Environment variables (override file settings)

        Environment Variables
        ---------------------
        MARCUS_PROJECT_ID : str
            Project ID for the Marcus to work with.
        MARCUS_BOARD_ID : str
            Board ID within the project.

        Configuration File Format
        -------------------------
        {
            "project_id": "string",
            "board_id": "string",
            "project_name": "string",
            "planka": {
                "base_url": "string",
                "email": "string",
                "password": "string"
            }
        }

        Notes
        -----
        Environment variables take precedence over configuration file settings.
        Planka credentials from config file will update the kanban client's
        environment variables.

        Examples
        --------
        >>> # Configuration loaded automatically on init
        >>> agent = ConfigurablePMAgent("my_config.json")
        # Loads from my_config.json and environment variables
        """
        config = {}

        # Try to load from file
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f:
                config = json.load(f)
                print(f"📋 Loaded configuration from {self.config_file}")

        # Override with environment variables if present
        if os.getenv("MARCUS_PROJECT_ID"):
            config["project_id"] = os.getenv("MARCUS_PROJECT_ID")
        if os.getenv("MARCUS_BOARD_ID"):
            config["board_id"] = os.getenv("MARCUS_BOARD_ID")

        # Apply configuration
        if config.get("project_id"):
            self.kanban_client.project_id = config["project_id"]
            print(
                f"🎯 Configured for project: {config.get('project_name', config['project_id'])}"
            )

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
                self.kanban_client._env["PLANKA_AGENT_PASSWORD"] = planka_config[
                    "password"
                ]

    async def start(self) -> None:
        """Start the Marcus with automatic configuration and board discovery.

        Performs enhanced startup sequence that includes:
        1. Board discovery if project_id is set but board_id is not
        2. Standard MarcusMVP startup procedures

        Raises
        ------
        ConnectionError
            If unable to connect to the kanban system.
        ValueError
            If required configuration is missing or invalid.

        Examples
        --------
        >>> agent = ConfigurablePMAgent("config.json")
        >>> await agent.start()
        # 🔍 Finding board for project...
        # ✅ Found board: board-123
        # 🚀 Marcus started successfully!
        """
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

    async def _get_project_status(self) -> Dict[str, Any]:
        """Get enhanced project status including configuration information.

        Extends the base project status with additional configuration details
        about the current project, board, and config file being used.

        Returns
        -------
        Dict[str, Any]
            Project status dictionary with added configuration section.

            Structure:
            {
                "success": bool,
                "project_id": str,
                "board_id": str,
                "tasks": List[Task],
                "agents": List[Agent],
                "configuration": {
                    "project_id": str,
                    "board_id": str,
                    "config_file": str
                }
            }

        Examples
        --------
        >>> agent = ConfigurablePMAgent("config.json")
        >>> await agent.start()
        >>> status = await agent._get_project_status()
        >>> print(status["configuration"]["project_id"])
        'project-123'
        """
        result = await super()._get_project_status()

        # Add configuration info
        if result.get("success"):
            result["configuration"] = {
                "project_id": self.kanban_client.project_id,
                "board_id": self.kanban_client.board_id,
                "config_file": self.config_file,
            }

        return result


if __name__ == "__main__":
    import asyncio

    # Start with configuration file
    agent = ConfigurablePMAgent("config_marcus.json")
    asyncio.run(agent.start())
