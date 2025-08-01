"""
Server initialization and setup functionality.

This module handles the complex initialization process for the Marcus server,
including enhanced features, monitoring systems, and kanban client setup.
"""

import asyncio
import logging
import os
from pathlib import Path

from src.config.config_loader import get_config
from src.core.assignment_lease import AssignmentLeaseManager, LeaseMonitor
from src.core.context import Context
from src.core.events import Events
from src.core.models import TaskAssignment
from src.core.persistence import Persistence, SQLitePersistence
from src.integrations.github_provider import GitHubProvider
from src.integrations.planka_provider import PlankaProvider
from src.monitoring.assignment_monitor import AssignmentMonitor
from src.visualization.event_integrated_visualizer import EventIntegratedVisualizer

logger = logging.getLogger(__name__)


class ServerInitializer:
    """Handles server initialization and setup."""

    def __init__(self, server):
        """
        Initialize the ServerInitializer.

        Args:
        ----
            server: The MarcusServer instance to initialize
        """
        self.server = server
        self.config = get_config()

    async def initialize(self) -> None:
        """
        Initialize all server components.

        This includes:
        - Enhanced features (events, context, memory)
        - Monitoring systems
        - Kanban client
        - Project migration
        """
        logger.info("Starting Marcus server initialization...")

        # Initialize enhanced features
        await self._initialize_enhanced_features()

        # Initialize monitoring systems
        await self._initialize_monitoring_systems()

        # Initialize kanban client
        await self.initialize_kanban()

        # Migrate to multi-project if needed
        await self._migrate_to_multi_project()

        # Restore assignments
        await self._restore_assignments()

        logger.info("Server initialization complete")

    async def _initialize_enhanced_features(self) -> None:
        """Initialize enhanced features based on configuration."""
        # Get feature configurations
        events_config = self.config.get_feature_config("events")
        context_config = self.config.get_feature_config("context")
        memory_config = self.config.get_feature_config("memory")
        visibility_config = self.config.get_feature_config("visibility")

        # Initialize persistence if needed
        if any(
            cfg["enabled"] for cfg in [events_config, context_config, memory_config]
        ):
            persistence_path = self.config.get(
                "features.persistence_path", "./data/marcus.db"
            )
            self.server.persistence = Persistence(
                backend=SQLitePersistence(Path(persistence_path))
            )

        # Initialize events system
        if events_config["enabled"]:
            self.server.events = Events(
                store_history=events_config.get("store_history", True),
                persistence=self.server.persistence,
            )
            logger.info("Events system initialized")

        # Initialize context system
        if context_config["enabled"]:
            # Check hybrid inference configuration
            hybrid_config = self.config.get_hybrid_inference_config()
            use_hybrid = context_config.get("use_hybrid_inference", True)

            self.server.context = Context(
                events=self.server.events,
                persistence=self.server.persistence,
                use_hybrid_inference=use_hybrid and hybrid_config.enable_ai_inference,
                ai_engine=self.server.ai_engine if use_hybrid else None,
            )

            # Apply context-specific settings
            if "infer_dependencies" in context_config:
                self.server.context.default_infer_dependencies = context_config[
                    "infer_dependencies"
                ]
            logger.info("Context system initialized")

        # Initialize memory system
        if memory_config["enabled"]:
            if memory_config.get("use_v2_predictions", False):
                from src.core.memory_advanced import MemoryAdvanced

                self.server.memory = MemoryAdvanced(
                    events=self.server.events, persistence=self.server.persistence
                )
            else:
                from src.core.memory import Memory

                self.server.memory = Memory(
                    events=self.server.events, persistence=self.server.persistence
                )

            # Apply memory-specific settings
            if "learning_rate" in memory_config:
                self.server.memory.learning_rate = memory_config["learning_rate"]
            if "min_samples" in memory_config:
                self.server.memory.confidence_threshold = memory_config["min_samples"]
            logger.info("Memory system initialized")

        # Initialize event visualizer
        if events_config["enabled"] and visibility_config["enabled"]:
            self.server.event_visualizer = EventIntegratedVisualizer()
            logger.info("Event visualizer initialized")

    async def _initialize_monitoring_systems(self) -> None:
        """Initialize monitoring and lease management systems."""
        try:
            # Initialize assignment monitor
            self.server.assignment_monitor = AssignmentMonitor(
                server=self.server,
                comm_hub=self.server.comm_hub,
                check_interval=self.config.get("monitoring.check_interval", 300),
                alert_thresholds=self.config.get(
                    "monitoring.alert_thresholds",
                    {
                        "max_agent_idle_time": 1800,
                        "max_task_duration": 14400,
                        "min_completion_rate": 0.7,
                    },
                ),
            )

            # Initialize lease management
            lease_config = self.config.get("features.assignment_leasing", {})
            if lease_config.get("enabled", True):
                self.server.lease_manager = AssignmentLeaseManager(
                    default_duration=lease_config.get("default_duration_minutes", 60),
                    max_duration=lease_config.get("max_duration_minutes", 240),
                    grace_period=lease_config.get("grace_period_minutes", 15),
                )

                self.server.lease_monitor = LeaseMonitor(
                    lease_manager=self.server.lease_manager,
                    comm_hub=self.server.comm_hub,
                    check_interval=lease_config.get("check_interval_seconds", 60),
                )

                logger.info("Lease management system initialized")

            # Start monitoring
            asyncio.create_task(self.server.assignment_monitor.start())
            if self.server.lease_monitor:
                asyncio.create_task(self.server.lease_monitor.start())

            logger.info("Monitoring systems started")

        except Exception as e:
            logger.error(f"Failed to initialize monitoring systems: {e}")
            # Continue without monitoring rather than failing startup

    async def initialize_kanban(self) -> None:
        """Initialize and validate kanban client connection."""
        self._ensure_environment_config()

        try:
            # In multi-project mode, project manager handles kanban client
            if self.server.is_multi_project_mode:
                logger.info(
                    "Multi-project mode: kanban client managed by project manager"
                )
                # Set initial project if configured
                default_project = self.config.get("kanban.default_project")
                if default_project:
                    await self.server.project_manager.set_current_project(
                        default_project
                    )
                    self.server.kanban_client = (
                        self.server.project_manager.kanban_client
                    )
                return

            # Single project mode - create kanban client directly
            board_name = self.config.get("kanban.board_name")
            if not board_name:
                raise ValueError("No board name configured for single project mode")

            # Create kanban client based on provider
            if self.server.provider == "planka":
                base_url = os.getenv("PLANKA_BASE_URL")
                if not base_url:
                    raise ValueError("PLANKA_BASE_URL not set")

                kanban_client = PlankaProvider(
                    base_url=base_url,
                    email=os.getenv("PLANKA_EMAIL", ""),
                    password=os.getenv("PLANKA_PASSWORD", ""),
                )
                await kanban_client.initialize()

            elif self.server.provider == "github":
                token = os.getenv("GITHUB_TOKEN")
                if not token:
                    raise ValueError("GITHUB_TOKEN not set")

                repo = self.config.get("kanban.github_repo")
                if not repo:
                    raise ValueError("GitHub repository not configured")

                kanban_client = GitHubProvider(
                    token=token,
                    repo=repo,
                    project_number=self.config.get("kanban.github_project_number"),
                )
                await kanban_client.initialize()
            else:
                raise ValueError(f"Unsupported provider: {self.server.provider}")

            # Validate board exists
            await kanban_client.get_board(board_name)
            self.server.kanban_client = kanban_client

            logger.info(f"Kanban client initialized for board: {board_name}")

            # Initial state refresh
            await self.server.refresh_project_state()

        except Exception as e:
            logger.error(f"Failed to initialize kanban: {e}")
            raise RuntimeError(f"Kanban initialization failed: {e}")

    def _ensure_environment_config(self) -> None:
        """Ensure required environment variables are set."""
        # Load environment from config if available
        env_vars = self.config.get("environment", {})
        for key, value in env_vars.items():
            if value and not os.getenv(key):
                os.environ[key] = str(value)

        # Provider-specific validation
        if self.server.provider == "planka":
            # Try to load from various sources
            if not os.getenv("PLANKA_BASE_URL"):
                # Try config
                base_url = self.config.get("kanban.base_url")
                if base_url:
                    os.environ["PLANKA_BASE_URL"] = base_url
                else:
                    # Try common defaults
                    if os.path.exists("/.dockerenv"):
                        os.environ["PLANKA_BASE_URL"] = "http://planka:3000"
                    else:
                        os.environ["PLANKA_BASE_URL"] = "http://localhost:3000"

            # Load credentials from config if not in env
            if not os.getenv("PLANKA_EMAIL"):
                email = self.config.get("kanban.email", "demo@demo.demo")
                os.environ["PLANKA_EMAIL"] = email

            if not os.getenv("PLANKA_PASSWORD"):
                password = self.config.get("kanban.password", "demo")
                os.environ["PLANKA_PASSWORD"] = password

        elif self.server.provider == "github":
            if not os.getenv("GITHUB_TOKEN"):
                token = self.config.get("kanban.github_token")
                if token:
                    os.environ["GITHUB_TOKEN"] = token
                else:
                    logger.warning(
                        "GITHUB_TOKEN not found in environment or config. "
                        "GitHub operations will fail."
                    )

    async def _migrate_to_multi_project(self) -> None:
        """Migrate from single to multi-project mode if needed."""
        if not self.server.is_multi_project_mode:
            return

        # Check if we need to migrate existing config
        if self.config.get("kanban.board_name") and not self.config.get("projects"):
            logger.info("Migrating from single to multi-project configuration...")

            # Create default project from existing config
            default_project = {
                "name": "default",
                "board_name": self.config.get("kanban.board_name"),
                "description": "Default project (migrated from single-project mode)",
            }

            # This would need to be saved to config file
            logger.info(f"Created default project: {default_project}")

    async def _restore_assignments(self) -> None:
        """Restore persisted assignments on startup."""
        try:
            assignments = await self.server.assignment_persistence.load_assignments()
            for agent_id, task_data in assignments.items():
                self.server.agent_tasks[agent_id] = TaskAssignment(**task_data)
                task_id = task_data["task_id"]
                logger.info(f"Restored assignment for agent {agent_id}: task {task_id}")
        except Exception as e:
            logger.error(f"Failed to restore assignments: {e}")
            # Continue without restored assignments
