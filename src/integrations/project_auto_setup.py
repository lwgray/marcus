"""
Provider-agnostic project auto-setup for create_project.

This module extracts auto-creation logic from nlp_tools.py to support
multiple providers (Planka, GitHub, Linear) and provide cleaner
separation of concerns.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from src.core.project_registry import ProjectConfig

logger = logging.getLogger(__name__)


class ProjectAutoSetup:
    """
    Handles automatic project setup across different kanban providers.

    This class provides provider-agnostic project creation that:
    - Auto-creates Planka projects and boards
    - Registers projects in Marcus's ProjectRegistry
    - Returns standardized ProjectConfig objects
    - Supports future GitHub and Linear integration
    """

    async def setup_new_project(
        self,
        kanban_client: Any,
        provider: str,
        project_name: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> ProjectConfig:
        """
        Set up a new project with the specified provider.

        Dispatches to provider-specific setup methods and returns
        a ProjectConfig ready for registration.

        Parameters
        ----------
        kanban_client : Any
            Kanban client instance (already initialized)
        provider : str
            Provider type: "planka", "github", or "linear"
        project_name : str
            Name for the project
        options : Dict[str, Any], optional
            Provider-specific configuration options

        Returns
        -------
        ProjectConfig
            Project configuration ready for registry

        Raises
        ------
        ValueError
            If provider is not supported
        NotImplementedError
            If provider support is not yet implemented

        Examples
        --------
        >>> auto_setup = ProjectAutoSetup()
        >>> config = await auto_setup.setup_new_project(
        ...     kanban_client=client,
        ...     provider="planka",
        ...     project_name="MyAPI",
        ...     options={"planka_board_name": "Dev Board"}
        ... )
        >>> assert config.provider == "planka"
        """
        if options is None:
            options = {}

        if provider == "planka":
            return await self.setup_planka_project(
                kanban_client=kanban_client,
                project_name=project_name,
                options=options,
            )
        elif provider == "github":
            return await self.setup_github_project(
                project_name=project_name, options=options
            )
        elif provider == "linear":
            return await self.setup_linear_project(
                project_name=project_name, options=options
            )
        else:
            raise ValueError(
                f"Unsupported provider: {provider}. "
                f"Supported providers: planka, github, linear"
            )

    async def setup_planka_project(
        self,
        kanban_client: Any,
        project_name: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> ProjectConfig:
        """
        Create a new Planka project and board, return ProjectConfig.

        Parameters
        ----------
        kanban_client : Any
            Initialized Kanban client with auto_setup_project method
        project_name : str
            Name for the Marcus project
        options : Dict[str, Any], optional
            Planka-specific options:
            - planka_project_name: Override project name in Planka
            - planka_board_name: Name for the board (default: "Main Board")

        Returns
        -------
        ProjectConfig
            Project configuration with Planka IDs

        Raises
        ------
        Exception
            If Planka project/board creation fails

        Notes
        -----
        This method calls kanban_client.auto_setup_project which:
        - Creates a new Planka project if needed
        - Creates a new board within that project
        - Returns the project_id and board_id
        """
        if options is None:
            options = {}

        # Extract Planka-specific options with defaults
        planka_project_name = options.get("planka_project_name", project_name)
        planka_board_name = options.get("planka_board_name", "Main Board")

        logger.info(
            f"Auto-creating Planka project '{planka_project_name}' "
            f"with board '{planka_board_name}'"
        )

        # Check if kanban client supports auto_setup_project
        if not hasattr(kanban_client, "auto_setup_project"):
            raise AttributeError(
                "Kanban client does not support auto_setup_project. "
                "Please ensure you're using KanbanClientWithCreate."
            )

        # Call Planka auto-setup
        result = await kanban_client.auto_setup_project(
            project_name=planka_project_name, board_name=planka_board_name
        )

        logger.info(
            f"Created Planka project: {result['project_id']}, "
            f"board: {result['board_id']}"
        )

        # Create ProjectConfig for registry
        project_config = ProjectConfig(
            id="",  # Will be generated by registry
            name=project_name,
            provider="planka",
            provider_config={
                "project_id": result["project_id"],
                "board_id": result["board_id"],
            },
            created_at=datetime.now(),
            last_used=datetime.now(),
            tags=["auto-created"],
        )

        return project_config

    async def setup_github_project(
        self, project_name: str, options: Optional[Dict[str, Any]] = None
    ) -> ProjectConfig:
        """
        Create a new GitHub project, return ProjectConfig.

        Parameters
        ----------
        project_name : str
            Name for the project
        options : Dict[str, Any], optional
            GitHub-specific options:
            - github_owner: Repository owner
            - github_repo: Repository name
            - github_project_number: Project number (default: 1)

        Returns
        -------
        ProjectConfig
            Project configuration with GitHub details

        Raises
        ------
        NotImplementedError
            GitHub auto-setup not yet implemented

        Notes
        -----
        Future implementation will:
        - Create GitHub Project (beta API)
        - Set up columns (Todo, In Progress, Done)
        - Configure automation rules
        """
        raise NotImplementedError(
            "GitHub project auto-setup not yet implemented. "
            "Use add_project() to manually register an existing GitHub project."
        )

    async def setup_linear_project(
        self, project_name: str, options: Optional[Dict[str, Any]] = None
    ) -> ProjectConfig:
        """
        Create a new Linear project, return ProjectConfig.

        Parameters
        ----------
        project_name : str
            Name for the project
        options : Dict[str, Any], optional
            Linear-specific options:
            - linear_team_id: Team ID
            - linear_workspace_id: Workspace ID

        Returns
        -------
        ProjectConfig
            Project configuration with Linear details

        Raises
        ------
        NotImplementedError
            Linear auto-setup not yet implemented

        Notes
        -----
        Future implementation will:
        - Create Linear project
        - Set up workflow states
        - Configure issue templates
        """
        raise NotImplementedError(
            "Linear project auto-setup not yet implemented. "
            "Use add_project() to manually register an existing Linear project."
        )
