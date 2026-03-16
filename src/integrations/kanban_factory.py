"""Factory for creating kanban provider instances.

Simplifies the process of creating the right kanban provider
based on configuration.
"""

import os
from typing import Any, Dict, Optional

from src.config.marcus_config import get_config
from src.integrations.kanban_interface import KanbanInterface, KanbanProvider
from src.integrations.providers import GitHubKanban, LinearKanban, Planka


class KanbanFactory:
    """Factory for creating kanban provider instances."""

    @staticmethod
    def create(
        provider: str, config: Optional[Dict[str, Any]] = None
    ) -> KanbanInterface:
        """
        Create a kanban provider instance.

        Parameters
        ----------
        provider : str
            Provider name ('planka', 'linear', 'github')
        config : Optional[Dict[str, Any]]
            Optional configuration override

        Returns
        -------
        KanbanInterface
            KanbanInterface implementation

        Raises
        ------
        ValueError
            If provider is not supported
        """
        # Get centralized configuration
        marcus_config = get_config()

        provider_lower = provider.lower()

        if provider_lower == KanbanProvider.PLANKA.value:
            if not config:
                config = {
                    "project_name": os.getenv(
                        "PLANKA_PROJECT_NAME", "Task Master Test"
                    ),
                }
            # Use KanbanClient-based implementation
            return Planka(config)

        elif provider_lower == KanbanProvider.LINEAR.value:
            if not config:
                config = {
                    "api_key": marcus_config.kanban.linear_api_key
                    or os.getenv("LINEAR_API_KEY"),
                    "team_id": marcus_config.kanban.linear_team_id
                    or os.getenv("LINEAR_TEAM_ID"),
                    "project_id": os.getenv("LINEAR_PROJECT_ID"),
                }
            return LinearKanban(config)

        elif provider_lower == KanbanProvider.GITHUB.value:
            if not config:
                config = {
                    "token": marcus_config.kanban.github_token
                    or os.getenv("GITHUB_TOKEN"),
                    "owner": marcus_config.kanban.github_owner
                    or os.getenv("GITHUB_OWNER"),
                    "repo": marcus_config.kanban.github_repo
                    or os.getenv("GITHUB_REPO"),
                    "project_number": int(os.getenv("GITHUB_PROJECT_NUMBER", "1")),
                }
            return GitHubKanban(config)  # type: ignore[abstract]

        else:
            raise ValueError(f"Unsupported kanban provider: {provider}")

    @staticmethod
    def get_default_provider() -> str:
        """Get the default provider from configuration."""
        config = get_config()
        return config.kanban.provider or os.getenv("KANBAN_PROVIDER", "planka")

    @staticmethod
    def create_default(config: Optional[Dict[str, Any]] = None) -> KanbanInterface:
        """Create the default kanban provider."""
        provider = KanbanFactory.get_default_provider()
        return KanbanFactory.create(provider, config)
