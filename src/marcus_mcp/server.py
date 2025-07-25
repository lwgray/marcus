#!/usr/bin/env python3
"""
Marcus MCP Server - Modularized Version

A lean MCP server implementation that delegates all tool logic
to specialized modules for better maintainability.
"""

import asyncio
import atexit
import json
import logging
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


import mcp.types as types  # noqa: E402
from mcp.server import Server  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402
from mcp.server.stdio import stdio_server  # noqa: E402

from src.communication.communication_hub import CommunicationHub  # noqa: E402
from src.config.config_loader import get_config  # noqa: E402
from src.config.settings import Settings  # noqa: E402

# Import for type annotations only
from src.core.assignment_lease import (  # noqa: E402
    AssignmentLeaseManager,
    LeaseMonitor,
)
from src.core.assignment_persistence import AssignmentPersistence  # noqa: E402
from src.core.code_analyzer import CodeAnalyzer  # noqa: E402
from src.core.context import Context  # noqa: E402
from src.core.event_loop_utils import EventLoopLockManager  # noqa: E402
from src.core.events import Events  # noqa: E402
from src.core.models import (  # noqa: E402
    ProjectState,
    RiskLevel,
    TaskAssignment,
    TaskStatus,
    WorkerStatus,
)
from src.core.project_context_manager import ProjectContextManager  # noqa: E402
from src.core.project_registry import ProjectConfig, ProjectRegistry  # noqa: E402
from src.core.service_registry import (  # noqa: E402
    register_marcus_service,
    unregister_marcus_service,
)
from src.cost_tracking.ai_usage_middleware import ai_usage_middleware  # noqa: E402
from src.cost_tracking.token_tracker import token_tracker  # noqa: E402
from src.integrations.ai_analysis_engine import AIAnalysisEngine  # noqa: E402
from src.integrations.kanban_factory import KanbanFactory  # noqa: E402
from src.integrations.kanban_interface import KanbanInterface  # noqa: E402
from src.marcus_mcp.handlers import handle_tool_call  # noqa: E402
from src.marcus_mcp.tool_groups import get_tools_for_endpoint  # noqa: E402
from src.monitoring.assignment_monitor import AssignmentMonitor  # noqa: E402
from src.monitoring.project_monitor import ProjectMonitor  # noqa: E402
from src.visualization.shared_pipeline_events import (  # noqa: E402
    SharedPipelineVisualizer,
)


class MarcusServer:
    """Marcus MCP Server with modularized architecture"""

    def __init__(self) -> None:
        """Initialize Marcus server instance"""
        # Config is already loaded by marcus.py, but ensure it's available
        self.config = get_config()
        self.settings = Settings()

        # Initialize project management components
        self.project_registry = ProjectRegistry()
        self.project_manager = ProjectContextManager(self.project_registry)

        # For backwards compatibility - get default provider
        self.provider = self.config.get("kanban.provider", "planka")

        # Check if in multi-project mode
        self.is_multi_project_mode = self.config.is_multi_project_mode()

        # Create realtime log with line buffering
        # Use absolute path based on Marcus root directory
        marcus_root = Path(__file__).parent.parent.parent
        log_dir = marcus_root / "logs" / "conversations"
        log_dir.mkdir(parents=True, exist_ok=True)
        self.realtime_log = open(
            log_dir / f"realtime_{datetime.now():%Y%m%d_%H%M%S}.jsonl",
            "a",
            buffering=1,  # Line buffering
        )
        atexit.register(self.realtime_log.close)
        atexit.register(unregister_marcus_service)

        # Core components
        self.kanban_client: Optional[KanbanInterface] = (
            None  # Will be set by project manager
        )
        self.ai_engine = AIAnalysisEngine()
        self.monitor = ProjectMonitor()
        self.comm_hub = CommunicationHub()

        # Token tracking for cost monitoring
        self.token_tracker = token_tracker

        # Code analyzer for GitHub
        self.code_analyzer = None
        if self.provider == "github":
            self.code_analyzer = CodeAnalyzer()

        # State tracking
        self.agent_tasks: Dict[str, TaskAssignment] = {}
        self.agent_status: Dict[str, WorkerStatus] = {}
        self.project_state: Optional[ProjectState] = None
        self.project_tasks: List[Any] = []

        # Assignment persistence and locking
        self.assignment_persistence = AssignmentPersistence()
        self._lock_manager = EventLoopLockManager()
        self.tasks_being_assigned: set[str] = set()

        # Assignment monitoring
        self.assignment_monitor: Optional[AssignmentMonitor] = None

        # Lease management
        self.lease_manager: Optional[AssignmentLeaseManager] = None
        self.lease_monitor: Optional[LeaseMonitor] = None

        # Pipeline flow visualization (shared between processes)
        self.pipeline_visualizer = SharedPipelineVisualizer()

        # Track active connections and cleanup state
        self._cleanup_done = False
        self._active_operations: Set[Any] = set()
        self._shutdown_event = asyncio.Event()

        # New enhancement systems (optional based on config)
        # Declare optional attributes
        self.events: Optional[Events] = None
        self.context: Optional[Context] = None
        self.memory: Any = None

        # Get feature configurations with granular settings
        config_loader = get_config()
        events_config = config_loader.get_feature_config("events")
        context_config = config_loader.get_feature_config("context")
        memory_config = config_loader.get_feature_config("memory")
        visibility_config = config_loader.get_feature_config("visibility")

        # Persistence layer (if any enhanced features are enabled)
        self.persistence = None
        if any(
            cfg["enabled"] for cfg in [events_config, context_config, memory_config]
        ):
            from src.core.persistence import Persistence, SQLitePersistence

            # Use SQLite for better performance
            persistence_path = self.config.get(
                "features.persistence_path", "./data/marcus.db"
            )
            self.persistence = Persistence(
                backend=SQLitePersistence(Path(persistence_path))
            )

        # Events system for loose coupling
        if events_config["enabled"]:
            self.events = Events(
                store_history=events_config.get("store_history", True),
                persistence=self.persistence,
            )
        else:
            self.events = None

        # Context system for rich task assignments
        if context_config["enabled"]:
            # Check if we should use hybrid inference
            hybrid_config = config_loader.get_hybrid_inference_config()
            use_hybrid = context_config.get("use_hybrid_inference", True)

            self.context = Context(
                events=self.events,
                persistence=self.persistence,
                use_hybrid_inference=use_hybrid and hybrid_config.enable_ai_inference,
                ai_engine=self.ai_engine if use_hybrid else None,
            )
            # Apply context-specific settings
            if "infer_dependencies" in context_config:
                self.context.default_infer_dependencies = context_config[
                    "infer_dependencies"
                ]
        else:
            self.context = None

        # Memory system for learning and prediction
        if memory_config["enabled"]:
            # Check if we should use enhanced memory
            if memory_config.get("use_v2_predictions", False):
                from src.core.memory_advanced import MemoryAdvanced

                self.memory = MemoryAdvanced(
                    events=self.events, persistence=self.persistence
                )
            else:
                from src.core.memory import Memory

                self.memory = Memory(events=self.events, persistence=self.persistence)

            # Apply memory-specific settings
            if "learning_rate" in memory_config:
                self.memory.learning_rate = memory_config["learning_rate"]
            if "min_samples" in memory_config:
                self.memory.confidence_threshold = memory_config["min_samples"]
        else:
            self.memory = None

        # Event-integrated visualization (if events and visibility enabled)
        self.event_visualizer = None
        if events_config["enabled"] and visibility_config["enabled"]:
            from src.visualization.event_integrated_visualizer import (
                EventIntegratedVisualizer,
            )

            self.event_visualizer = EventIntegratedVisualizer()

        # Log startup
        self.log_event(
            "server_startup",
            {"provider": self.provider, "timestamp": datetime.now().isoformat()},
        )

        # Create MCP server instance
        self.server = Server("marcus")

        # Register handlers
        self._register_handlers()

        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()

        # FastMCP instance for HTTP transport (created on demand)
        self._fastmcp: Optional[FastMCP] = None
        self._endpoint_apps: Dict[str, FastMCP] = {}

    @property
    def assignment_lock(self) -> asyncio.Lock:
        """Get assignment lock for the current event loop."""
        return self._lock_manager.get_lock()

    def _register_handlers(self) -> None:
        """Register MCP tool handlers"""

        @self.server.list_tools()  # type: ignore[no-untyped-call,misc]
        async def handle_list_tools() -> List[types.Tool]:
            """Return list of available tools based on client role"""
            # Import here to avoid circular dependency
            from src.marcus_mcp.tools.auth import get_tool_definitions_for_client

            # Get current client ID if available
            client_id = None
            if hasattr(self, "_current_client_id"):
                client_id = self._current_client_id

            # Get tools based on client access
            return get_tool_definitions_for_client(client_id, self)

        @self.server.call_tool()  # type: ignore[no-untyped-call,misc]
        async def handle_call_tool(
            name: str, arguments: Optional[Dict[str, Any]]
        ) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """Handle tool calls"""
            return await handle_tool_call(name, arguments, self)

        @self.server.list_prompts()  # type: ignore[no-untyped-call,misc]
        async def handle_list_prompts() -> List[types.Prompt]:
            """Return list of available prompts - not used by Marcus"""
            return []

        @self.server.list_resources()  # type: ignore[no-untyped-call,misc]
        async def handle_list_resources() -> List[types.Resource]:
            """Return list of available resources - not used by Marcus"""
            return []

        @self.server.read_resource()  # type: ignore[no-untyped-call,misc]
        async def handle_read_resource(uri: str) -> str:
            """Read a resource - Marcus doesn't use resources currently"""
            raise ValueError(f"Resource not found: {uri}")

        @self.server.get_prompt()  # type: ignore[no-untyped-call,misc]
        async def handle_get_prompt(
            name: str, arguments: Optional[Dict[str, str]] = None
        ) -> types.GetPromptResult:
            """Get a prompt - Marcus doesn't use prompts currently"""
            raise ValueError(f"Prompt not found: {name}")

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown"""

        def signal_handler(signum: int, frame: Any) -> None:
            """Handle interrupt signals gracefully"""
            print(f"\n⚠️  Received signal {signum}, initiating graceful shutdown...")
            # Set shutdown event
            self._shutdown_event.set()
            # Create task for async cleanup
            if asyncio.get_event_loop().is_running():
                asyncio.create_task(self._cleanup_on_shutdown())
            else:
                # If no event loop, do sync cleanup
                self._sync_cleanup()

        # Register handlers for common interruption signals
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _sync_cleanup(self) -> None:
        """Synchronous cleanup for when event loop is not available"""
        if self._cleanup_done:
            return

        self._cleanup_done = True

        try:
            print("🧹 Performing synchronous cleanup...")

            # Clean up tasks being assigned
            if self.tasks_being_assigned:
                print(
                    f"  Clearing {len(self.tasks_being_assigned)} pending task "
                    "assignments"
                )
                self.tasks_being_assigned.clear()

            # Close realtime log
            if hasattr(self, "realtime_log") and self.realtime_log:
                self.realtime_log.close()

            print("✅ Cleanup completed")

        except Exception as e:
            print(f"❌ Error during cleanup: {e}")

        # Force exit after cleanup
        os._exit(0)

    async def _cleanup_on_shutdown(self) -> None:
        """Clean up resources on shutdown"""
        if self._cleanup_done:
            return

        self._cleanup_done = True

        try:
            print("🧹 Cleaning up active operations...")

            # Clean up tasks being assigned
            if self.tasks_being_assigned:
                print(
                    f"  Clearing {len(self.tasks_being_assigned)} pending task "
                    "assignments"
                )
                self.tasks_being_assigned.clear()

            # Cancel active operations and clean up task assignments
            if self._active_operations:
                print(f"  Cancelling {len(self._active_operations)} active operations")
                for op in self._active_operations:
                    if isinstance(op, str) and op.startswith("task_assignment_"):
                        # Extract task ID and remove from being assigned
                        task_id = op.replace("task_assignment_", "")
                        if task_id in self.tasks_being_assigned:
                            self.tasks_being_assigned.discard(task_id)
                            print(f"    Cleaned up task assignment: {task_id}")
                    elif asyncio.iscoroutine(op) or asyncio.isfuture(op):
                        try:
                            op.cancel()  # type: ignore[union-attr]
                        except AttributeError:
                            pass

            # Stop assignment monitor if running
            if self.assignment_monitor and hasattr(self.assignment_monitor, "_running"):
                self.assignment_monitor._running = False

            # Stop lease monitor if running
            if self.lease_monitor:
                await self.lease_monitor.stop()

            # Close realtime log
            if hasattr(self, "realtime_log") and self.realtime_log:
                self.realtime_log.close()

            # Persist any pending state
            if self.assignment_persistence:
                await self.assignment_persistence.cleanup()

            print("✅ Cleanup completed")

        except Exception as e:
            print(f"❌ Error during cleanup: {e}")

        # Force exit after cleanup
        os._exit(0)

    async def initialize(self) -> None:
        """Initialize all Marcus server components"""
        # Initialize AI engine
        await self.ai_engine.initialize()

        # Initialize project management
        await self.project_manager.initialize()

        # CRITICAL: Force creation of all locks in the current event loop
        # This prevents "lock is bound to a different event loop" errors
        _ = self.assignment_lock  # Force lock creation
        if self.assignment_persistence:
            _ = self.assignment_persistence.lock  # Force lock creation
        if self.project_manager:
            _ = self.project_manager.lock  # Force lock creation

        # Check if we're in multi-project mode or legacy mode
        if self.config.is_multi_project_mode():
            # Get kanban client from project manager
            self.kanban_client = await self.project_manager.get_kanban_client()
            if self.kanban_client:
                await self.project_registry.get_active_project()
                # Initialize monitors and lease system even in multi-project mode
                await self._initialize_monitoring_systems()
        else:
            # Legacy mode - create kanban client directly
            await self.initialize_kanban()

            # Migrate to multi-project if needed
            await self._migrate_to_multi_project()

        # If still no kanban client, check if we need to sync config
        if not self.kanban_client and self.config.is_multi_project_mode():
            # Config might have been migrated but not synced to registry
            active_project_id = self.config.get_active_project_id()
            if active_project_id:
                # Check if project exists in registry
                project = await self.project_registry.get_project(active_project_id)
                if not project:
                    # Project is in config but not in registry - sync it
                    projects_config = self.config.get_projects_config()
                    if active_project_id in projects_config:
                        proj_data = projects_config[active_project_id]
                        project = ProjectConfig(
                            id=active_project_id,
                            name=proj_data.get("name", "Default Project"),
                            provider=proj_data.get("provider", "planka"),
                            provider_config=proj_data.get("config", {}),
                            tags=proj_data.get("tags", ["default"]),
                        )
                        await self.project_registry.add_project(project)
                        await self.project_registry.set_active_project(
                            active_project_id
                        )

                        # Now switch to the project
                        await self.project_manager.switch_project(active_project_id)
                        self.kanban_client = (
                            await self.project_manager.get_kanban_client()
                        )

                        # Initialize monitoring systems for the synced project
                        if self.kanban_client:
                            await self._initialize_monitoring_systems()

                        # Project synced - don't print as it interferes with MCP

        # Initialize event visualizer if available
        if self.event_visualizer:
            # EventIntegratedVisualizer doesn't have initialize method
            pass

        # Wrap AI engine for token tracking
        self.ai_engine = ai_usage_middleware.wrap_ai_provider(self.ai_engine)

        # Initialize pattern learning components for API
        from src.api.pattern_learning_init import init_pattern_learning_components

        try:
            init_pattern_learning_components(
                kanban_client=self.kanban_client, ai_engine=self.ai_engine
            )
            # Don't print during initialization - it interferes with MCP stdio
        except Exception:
            # Log error without printing to stderr during initialization
            pass  # nosec B110

        # Don't print during initialization - it interferes with MCP stdio

    async def _migrate_to_multi_project(self) -> None:
        """Migrate legacy configuration to multi-project format"""
        if self.kanban_client and not self.config.is_multi_project_mode():
            # Create a project from the legacy config
            config_data = getattr(self.config, "_config", None)
            if config_data is not None:
                project_id = await self.project_registry.create_from_legacy_config(
                    config_data
                )

            # Set it as active
            await self.project_registry.set_active_project(project_id)

            # Initialize project context with existing client
            await self.project_manager.switch_project(project_id)

            # Successfully migrated to multi-project mode

    async def _initialize_monitoring_systems(self) -> None:
        """Initialize assignment monitor and lease manager for current kanban client."""
        if not self.kanban_client:
            return

        # Initialize assignment monitor
        if self.assignment_monitor is None:
            self.assignment_monitor = AssignmentMonitor(
                self.assignment_persistence, self.kanban_client
            )
            await self.assignment_monitor.start()  # type: ignore[no-untyped-call]

        # Initialize lease management
        if self.lease_manager is None:
            from src.core.assignment_lease import (
                AssignmentLeaseManager,
                LeaseMonitor,
            )

            # Get lease configuration - project-specific or global
            lease_config = {}

            # Check for project-specific lease config
            if hasattr(self, "project_registry") and self.project_registry:
                active_project = await self.project_registry.get_active_project()
                if active_project and hasattr(active_project, "task_lease"):
                    lease_config = active_project.task_lease

            # Fall back to global config
            if not lease_config:
                lease_config = self.config.get("task_lease", {})

            self.lease_manager = AssignmentLeaseManager(
                self.kanban_client,
                self.assignment_persistence,
                default_lease_hours=lease_config.get("default_hours", 2.0),
                max_renewals=lease_config.get("max_renewals", 10),
                warning_threshold_hours=lease_config.get("warning_hours", 0.5),
                priority_multipliers=lease_config.get("priority_multipliers"),
                complexity_multipliers=lease_config.get("complexity_multipliers"),
                grace_period_minutes=lease_config.get("grace_period_minutes", 30),
                renewal_decay_factor=lease_config.get("renewal_decay_factor", 0.9),
                min_lease_hours=lease_config.get("min_lease_hours", 1.0),
                max_lease_hours=lease_config.get("max_lease_hours", 24.0),
                stuck_task_threshold_renewals=lease_config.get(
                    "stuck_threshold_renewals", 5
                ),
                enable_adaptive_leases=lease_config.get("enable_adaptive", True),
            )
            self.lease_monitor = LeaseMonitor(self.lease_manager)
            await self.lease_monitor.start()
            logger.info("Assignment lease system initialized")

    async def initialize_kanban(self) -> None:
        """Initialize kanban client if not already done"""
        from src.core.error_framework import ErrorContext, KanbanIntegrationError

        if not self.kanban_client:
            try:
                # Ensure configuration is loaded before creating kanban client
                self._ensure_environment_config()

                # Create kanban client
                self.kanban_client = KanbanFactory.create(self.provider)

                # Validate the client supports task creation
                if not hasattr(self.kanban_client, "create_task"):
                    raise KanbanIntegrationError(
                        board_name=self.provider,
                        operation="client_initialization",
                        context=ErrorContext(
                            operation="kanban_initialization",
                            integration_name="mcp_server",
                            custom_context={
                                "provider": self.provider,
                                "details": (
                                    f"Kanban client "
                                    f"{type(self.kanban_client).__name__} "
                                    f"does not support task creation. Expected "
                                    f"KanbanClientWithCreate or compatible."
                                ),
                            },
                        ),
                    )

                # Connect to the kanban board
                if hasattr(self.kanban_client, "connect"):
                    await self.kanban_client.connect()

                # Initialize monitoring systems
                await self._initialize_monitoring_systems()

                # Kanban client initialized successfully

            except Exception as e:
                if isinstance(e, KanbanIntegrationError):
                    raise
                raise KanbanIntegrationError(
                    board_name=self.provider,
                    operation="client_initialization",
                    context=ErrorContext(
                        operation="kanban_initialization",
                        integration_name="mcp_server",
                        custom_context={
                            "provider": self.provider,
                            "details": f"Failed to initialize kanban client: {str(e)}",
                        },
                    ),
                ) from e

    def _ensure_environment_config(self) -> None:
        """Ensure environment variables are set from config_marcus.json"""
        from src.core.error_framework import ConfigurationError, ErrorContext

        try:
            # Load from config_marcus.json if environment variables aren't set
            import json
            from pathlib import Path

            config_path = Path(__file__).parent.parent.parent / "config_marcus.json"
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = json.load(f)

                # Set Planka environment variables if not already set
                if "planka" in config:
                    planka_config = config["planka"]
                    if "PLANKA_BASE_URL" not in os.environ:
                        os.environ["PLANKA_BASE_URL"] = planka_config.get(
                            "base_url", "http://localhost:3333"
                        )
                    if "PLANKA_AGENT_EMAIL" not in os.environ:
                        os.environ["PLANKA_AGENT_EMAIL"] = planka_config.get(
                            "email", "demo@demo.demo"
                        )
                    if "PLANKA_AGENT_PASSWORD" not in os.environ:
                        os.environ["PLANKA_AGENT_PASSWORD"] = planka_config.get(
                            "password", "demo"
                        )
                    if "PLANKA_PROJECT_NAME" not in os.environ:
                        os.environ["PLANKA_PROJECT_NAME"] = config.get(
                            "project_name", "Task Master Test"
                        )

                # Support GitHub if configured in the future
                if "github" in config:
                    github_config = config["github"]
                    if "GITHUB_TOKEN" not in os.environ and github_config.get("token"):
                        os.environ["GITHUB_TOKEN"] = github_config["token"]
                    if "GITHUB_OWNER" not in os.environ and github_config.get("owner"):
                        os.environ["GITHUB_OWNER"] = github_config["owner"]
                    if "GITHUB_REPO" not in os.environ and github_config.get("repo"):
                        os.environ["GITHUB_REPO"] = github_config["repo"]

                # Support Linear if configured in the future
                if "linear" in config:
                    linear_config = config["linear"]
                    if "LINEAR_API_KEY" not in os.environ and linear_config.get(
                        "api_key"
                    ):
                        os.environ["LINEAR_API_KEY"] = linear_config["api_key"]
                    if "LINEAR_TEAM_ID" not in os.environ and linear_config.get(
                        "team_id"
                    ):
                        os.environ["LINEAR_TEAM_ID"] = linear_config["team_id"]

                # Configuration loaded successfully from config_marcus.json

        except FileNotFoundError as e:
            raise ConfigurationError(
                service_name="MCP Server",
                config_type="config_marcus.json",
                missing_field="configuration file",
                context=ErrorContext(
                    operation="environment_config_loading",
                    integration_name="mcp_server",
                ),
            ) from e
        except Exception as e:
            raise ConfigurationError(
                "Failed to load environment configuration for kanban integration",
                context=ErrorContext(
                    operation="environment_config_loading",
                    integration_name="mcp_server",
                    custom_context={
                        "service_name": "MCP Server",
                        "config_type": "environment variables",
                        "missing_field": "kanban configuration",
                        "error": str(e),
                    },
                ),
            ) from e

    def log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log events immediately to realtime log and optionally to Events system"""
        event = {"timestamp": datetime.now().isoformat(), "type": event_type, **data}
        self.realtime_log.write(json.dumps(event) + "\n")

        # Also publish to Events system if available
        if self.events:
            # Run async publish in a fire-and-forget manner
            asyncio.create_task(self._publish_event_async(event_type, data))

    async def _publish_event_async(self, event_type: str, data: Dict[str, Any]) -> None:
        """Helper to publish events asynchronously"""
        try:
            source = data.get("source", "marcus")
            if self.events:
                await self.events.publish(event_type, source, data)
        except Exception as e:
            # Don't let event publishing errors affect main flow
            print(f"Error publishing event: {e}", file=sys.stderr)

    async def refresh_project_state(self) -> None:
        """Refresh project state from kanban board"""
        if not self.kanban_client:
            await self.initialize_kanban()

        try:
            # Get all tasks from the board
            if self.kanban_client is not None:
                self.project_tasks = await self.kanban_client.get_all_tasks()

            # Update memory system with project tasks for cascade analysis
            if self.memory and self.project_tasks:
                self.memory.update_project_tasks(self.project_tasks)

            # Update project state
            if self.project_tasks:
                total_tasks = len(self.project_tasks)
                completed_tasks = len(
                    [t for t in self.project_tasks if t.status == TaskStatus.DONE]
                )
                in_progress_tasks = len(
                    [
                        t
                        for t in self.project_tasks
                        if t.status == TaskStatus.IN_PROGRESS
                    ]
                )

                board_id = getattr(self.kanban_client, "board_id", "unknown")
                self.project_state = ProjectState(
                    board_id=board_id,
                    project_name="Current Project",  # Would need to get from board
                    total_tasks=total_tasks,
                    completed_tasks=completed_tasks,
                    in_progress_tasks=in_progress_tasks,
                    blocked_tasks=0,  # Would need to track this separately
                    progress_percent=(
                        (completed_tasks / total_tasks * 100)
                        if total_tasks > 0
                        else 0.0
                    ),
                    overdue_tasks=[],  # Would need to check due dates
                    team_velocity=0.0,  # Would need to calculate
                    risk_level=RiskLevel.LOW,  # Simplified
                    last_updated=datetime.now(),
                )

            # Create a JSON-serializable version of project_state
            project_state_data = None
            if self.project_state:
                project_state_data = {
                    "board_id": self.project_state.board_id,
                    "project_name": self.project_state.project_name,
                    "total_tasks": self.project_state.total_tasks,
                    "completed_tasks": self.project_state.completed_tasks,
                    "in_progress_tasks": self.project_state.in_progress_tasks,
                    "blocked_tasks": self.project_state.blocked_tasks,
                    "progress_percent": self.project_state.progress_percent,
                    "team_velocity": self.project_state.team_velocity,
                    "risk_level": self.project_state.risk_level.value,  # Enum to str
                    "last_updated": self.project_state.last_updated.isoformat(),
                }

            self.log_event(
                "project_state_refreshed",
                {
                    "task_count": len(self.project_tasks),
                    "project_state": project_state_data,
                },
            )

        except Exception as e:
            self.log_event("project_state_refresh_error", {"error": str(e)})
            raise

    def _create_fastmcp(self) -> FastMCP:
        """Create and configure FastMCP instance with agent tools by default"""
        if self._fastmcp is None:
            # Check if we should use all tools or agent tools
            use_all_tools = "--all-tools" in sys.argv

            if use_all_tools:
                self._fastmcp = FastMCP(
                    "marcus",
                    instructions=(
                        "Marcus - Multi-Agent Resource Coordination and "
                        "Understanding System (All Tools)"
                    ),
                )
                # Register all tools with FastMCP
                self._register_fastmcp_tools()
            else:
                # Default to agent tools for new users
                self._fastmcp = FastMCP(
                    "marcus-agent",
                    instructions=(
                        "Marcus - Multi-Agent Resource Coordination and "
                        "Understanding System (Agent Mode)"
                    ),
                )
                # Register only agent tools
                self._register_endpoint_tools(self._fastmcp, "agent")

        return self._fastmcp

    def _create_endpoint_app(self, endpoint_type: str) -> FastMCP:
        """Create FastMCP instance for a specific endpoint type."""
        if endpoint_type not in self._endpoint_apps:
            # Create unique app name for each endpoint
            app_name = f"marcus-{endpoint_type}"
            instructions = {
                "human": "Marcus MCP Server - Human Developer Tools",
                "agent": "Marcus MCP Server - Autonomous Agent Tools",
                "analytics": "Marcus MCP Server - Analytics & Monitoring Tools",
            }.get(endpoint_type, "Marcus MCP Server")

            # Create FastMCP instance
            app = FastMCP(app_name, instructions=instructions)

            # Register only tools allowed for this endpoint
            self._register_endpoint_tools(app, endpoint_type)

            self._endpoint_apps[endpoint_type] = app

        return self._endpoint_apps[endpoint_type]

    def _register_fastmcp_tools(self) -> None:
        """Register all tools with FastMCP instance"""
        # Import only what we need for avoiding duplicates
        # Actual imports happen inside each function to avoid conflicts

        # Store reference to self for closures
        server = self

        # Register core tools with proper signatures
        @self._fastmcp.tool()
        async def ping(echo: str = "") -> Dict[str, Any]:
            """Check Marcus status and connectivity."""
            from .tools.system import ping as ping_impl

            return await ping_impl(echo=echo, state=server)

        @self._fastmcp.tool()
        async def register_agent(
            agent_id: str, name: str, role: str, skills: List[str] = []
        ) -> Dict[str, Any]:
            """Register a new agent with the Marcus system."""
            from .tools.agent import register_agent as impl

            return await impl(
                agent_id=agent_id, name=name, role=role, skills=skills, state=server
            )

        @self._fastmcp.tool()
        async def get_agent_status(agent_id: str) -> Dict[str, Any]:
            """Get status and current assignment for an agent."""
            from .tools.agent import get_agent_status as impl

            return await impl(agent_id=agent_id, state=server)

        @self._fastmcp.tool()
        async def request_next_task(agent_id: str) -> Dict[str, Any]:
            """Request the next optimal task assignment for an agent."""
            from .tools.task import request_next_task as impl

            return await impl(agent_id=agent_id, state=server)

        @self._fastmcp.tool()
        async def report_task_progress(
            agent_id: str,
            task_id: str,
            status: str,
            progress: int = 0,
            message: str = "",
        ) -> Dict[str, Any]:
            """Report progress on a task."""
            from .tools.task import report_task_progress as impl

            return await impl(
                agent_id=agent_id,
                task_id=task_id,
                status=status,
                progress=progress,
                message=message,
                state=server,
            )

        @self._fastmcp.tool()
        async def report_blocker(
            agent_id: str,
            task_id: str,
            blocker_description: str,
            severity: str = "medium",
        ) -> Dict[str, Any]:
            """Report a blocker on a task."""
            from .tools.task import report_blocker as impl

            return await impl(
                agent_id=agent_id,
                task_id=task_id,
                blocker_description=blocker_description,
                severity=severity,
                state=server,
            )

        @self._fastmcp.tool()
        async def get_project_status() -> Dict[str, Any]:
            """Get current project status and metrics."""
            from .tools.agent import get_project_status as impl

            return await impl(state=server)

        @self._fastmcp.tool()
        async def create_project(
            description: str,
            project_name: str,
            options: Optional[Dict[str, Any]] = None,
        ) -> Dict[str, Any]:
            """Create a complete project from natural language description."""
            from .tools.nlp import create_project as impl

            return await impl(
                description=description,
                project_name=project_name,
                options=options,
                state=server,
            )

    def _register_endpoint_tools(self, app: FastMCP, endpoint_type: str) -> None:
        """Register tools for a specific endpoint based on allowed tools."""
        # Get allowed tools for this endpoint
        allowed_tools = get_tools_for_endpoint(endpoint_type)

        # Store reference to self for closures
        server = self

        # Register each allowed tool
        if "ping" in allowed_tools:

            @app.tool()
            async def ping(echo: str = "") -> Dict[str, Any]:
                """Check Marcus status and connectivity."""
                from .tools.system import ping as ping_impl

                return await ping_impl(echo=echo, state=server)

        if "authenticate" in allowed_tools:

            @app.tool()
            async def authenticate(
                client_id: str,
                client_type: str,
                role: str,
                metadata: Optional[Dict[str, Any]] = None,
            ) -> Dict[str, Any]:
                """Authenticate a client with role-based access."""
                from .tools.auth import authenticate as auth_impl

                return await auth_impl(
                    client_id=client_id,
                    client_type=client_type,
                    role=role,
                    metadata=metadata,
                    state=server,
                )

        if "register_agent" in allowed_tools:

            @app.tool()
            async def register_agent(
                agent_id: str, name: str, role: str, skills: List[str] = []
            ) -> Dict[str, Any]:
                """Register a new agent with the Marcus system."""
                from .tools.agent import register_agent as impl

                return await impl(
                    agent_id=agent_id, name=name, role=role, skills=skills, state=server
                )

        if "get_agent_status" in allowed_tools:

            @app.tool()
            async def get_agent_status(agent_id: str) -> Dict[str, Any]:
                """Get status and current assignment for an agent."""
                from .tools.agent import get_agent_status as impl

                return await impl(agent_id=agent_id, state=server)

        if "request_next_task" in allowed_tools:

            @app.tool()
            async def request_next_task(agent_id: str) -> Dict[str, Any]:
                """Request the next optimal task assignment for an agent."""
                from .tools.task import request_next_task as impl

                return await impl(agent_id=agent_id, state=server)

        if "report_task_progress" in allowed_tools:

            @app.tool()
            async def report_task_progress(
                agent_id: str,
                task_id: str,
                status: str,
                progress: int = 0,
                message: str = "",
            ) -> Dict[str, Any]:
                """Report progress on a task."""
                from .tools.task import report_task_progress as impl

                return await impl(
                    agent_id=agent_id,
                    task_id=task_id,
                    status=status,
                    progress=progress,
                    message=message,
                    state=server,
                )

        if "report_blocker" in allowed_tools:

            @app.tool()
            async def report_blocker(
                agent_id: str,
                task_id: str,
                blocker_description: str,
                severity: str = "medium",
            ) -> Dict[str, Any]:
                """Report a blocker on a task."""
                from .tools.task import report_blocker as impl

                return await impl(
                    agent_id=agent_id,
                    task_id=task_id,
                    blocker_description=blocker_description,
                    severity=severity,
                    state=server,
                )

        if "get_project_status" in allowed_tools:

            @app.tool()
            async def get_project_status() -> Dict[str, Any]:
                """Get current project status and metrics."""
                from .tools.agent import get_project_status as impl

                return await impl(state=server)

        if "create_project" in allowed_tools:

            @app.tool()
            async def create_project(
                description: str,
                project_name: str,
                options: Optional[Dict[str, Any]] = None,
            ) -> Dict[str, Any]:
                """Create a complete project from natural language description."""
                from .tools.nlp import create_project as impl

                return await impl(
                    description=description,
                    project_name=project_name,
                    options=options,
                    state=server,
                )

        if "list_projects" in allowed_tools:

            @app.tool()
            async def list_projects() -> Dict[str, Any]:
                """List all available projects."""
                from .tools.project_management import list_projects as impl

                return await impl(state=server)

        if "switch_project" in allowed_tools:

            @app.tool()
            async def switch_project(project_name: str) -> Dict[str, Any]:
                """Switch to a different project."""
                from .tools.project_management import switch_project as impl

                return await impl(project_name=project_name, state=server)

        if "get_current_project" in allowed_tools:

            @app.tool()
            async def get_current_project() -> Dict[str, Any]:
                """Get the currently active project."""
                from .tools.project_management import get_current_project as impl

                return await impl(state=server)

        if "add_feature" in allowed_tools:

            @app.tool()
            async def add_feature(
                description: str,
                context: Optional[Dict[str, Any]] = None,
            ) -> Dict[str, Any]:
                """Add a feature to existing project using natural language."""
                from .tools.nlp import add_feature as impl

                return await impl(
                    description=description,
                    context=context or {},
                    state=server,
                )

        if "get_usage_report" in allowed_tools:

            @app.tool()
            async def get_usage_report(
                start_date: Optional[str] = None,
                end_date: Optional[str] = None,
                group_by: str = "day",
            ) -> Dict[str, Any]:
                """Generate usage analytics and audit reports."""
                from .tools.audit_tools import get_usage_report as impl

                return await impl(
                    start_date=start_date,
                    end_date=end_date,
                    group_by=group_by,
                    state=server,
                )

        if "get_task_context" in allowed_tools:

            @app.tool()
            async def get_task_context(task_id: str) -> Dict[str, Any]:
                """Get the full context for a specific task."""
                from .tools.context import get_task_context as impl

                return await impl(task_id=task_id, state=server)

        if "log_decision" in allowed_tools:

            @app.tool()
            async def log_decision(
                agent_id: str,
                task_id: str,
                decision: str,
            ) -> Dict[str, Any]:
                """Log an architectural decision."""
                from .tools.context import log_decision as impl

                return await impl(
                    agent_id=agent_id,
                    task_id=task_id,
                    decision=decision,
                    state=server,
                )

        if "log_artifact" in allowed_tools:

            @app.tool()
            async def log_artifact(
                task_id: str,
                filename: str,
                content: str,
                artifact_type: str,
                description: str = "",
                location: Optional[str] = None,
            ) -> Dict[str, Any]:
                """Store an artifact with smart location management."""
                from .tools.attachment import log_artifact as impl

                return await impl(
                    task_id=task_id,
                    filename=filename,
                    content=content,
                    artifact_type=artifact_type,
                    description=description,
                    location=location,
                    state=server,
                )

        if "check_task_dependencies" in allowed_tools:

            @app.tool()
            async def check_task_dependencies(task_id: str) -> Dict[str, Any]:
                """Check dependencies for a specific task."""
                from .tools.board_health import check_task_dependencies as impl

                return await impl(task_id=task_id, state=server)

        # TODO: Add remaining analytics tools for Seneca endpoint
        # This includes all pipeline analysis tools, board health tools, etc.

    async def run(self) -> None:
        """Run the MCP server."""
        try:
            # Force unbuffered output for immediate response delivery
            import os
            import sys

            # Set Python to use unbuffered output
            os.environ["PYTHONUNBUFFERED"] = "1"

            # Ensure stdout/stderr are unbuffered
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(line_buffering=True)
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(line_buffering=True)

            async with stdio_server() as (read_stream, write_stream):
                # Enable debug logging if requested
                if os.environ.get("MCP_DEBUG") == "1":
                    from .debug_stdio_simple import wrap_stdio_for_debug

                    read_stream, write_stream = wrap_stdio_for_debug(
                        read_stream, write_stream
                    )

                try:
                    await self.server.run(
                        read_stream,
                        write_stream,
                        self.server.create_initialization_options(),
                    )
                finally:
                    # Cancel all pending tasks to ensure clean shutdown
                    pending = asyncio.all_tasks() - {asyncio.current_task()}
                    for task in pending:
                        task.cancel()

                    # Wait briefly for cancellations
                    if pending:
                        await asyncio.gather(*pending, return_exceptions=True)
        except Exception as e:
            print(f"❌ MCP server error: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc(file=sys.stderr)
            raise


async def run_multi_endpoint_server(server: MarcusServer) -> None:
    """Run Marcus with multiple endpoints on different ports."""
    import argparse
    import asyncio

    import uvicorn

    # Parse command line arguments for port overrides
    parser = argparse.ArgumentParser()
    parser.add_argument("--multi", action="store_true")
    parser.add_argument("--human-port", type=int)
    parser.add_argument("--agent-port", type=int)
    parser.add_argument("--analytics-port", type=int)
    args, _ = parser.parse_known_args()

    # Get multi-endpoint config
    config = get_config()
    base_config = config.get(
        "multi_endpoint",
        {
            "human": {"port": 4298, "enabled": True},
            "agent": {"port": 4299, "enabled": True},
            "analytics": {"port": 4300, "enabled": True},
        },
    )

    # Override ports with command line arguments if provided
    multi_endpoint_config = {}
    for endpoint_type in ["human", "agent", "analytics"]:
        multi_endpoint_config[endpoint_type] = base_config.get(endpoint_type, {}).copy()

        # Check for command line override
        port_arg = getattr(args, f"{endpoint_type}_port", None)
        if port_arg:
            multi_endpoint_config[endpoint_type]["port"] = port_arg

    # Pretty output
    print("\n" + "=" * 70)
    print("    Marcus MCP Server (Multi-Endpoint Mode)")
    print("=" * 70)

    tasks = []

    async def run_endpoint(endpoint_type: str, endpoint_config: Dict[str, Any]) -> None:
        """Run a single endpoint."""
        port = int(endpoint_config.get("port", 4298))
        host = endpoint_config.get("host", "127.0.0.1")
        path = endpoint_config.get("path", "/mcp")

        # Create app for this endpoint
        app = server._create_endpoint_app(endpoint_type)

        print(f"\n[I] {endpoint_type.capitalize()} endpoint:")
        print(f"    URL: http://{host}:{port}{path}")
        print(f"    Tools: {len(get_tools_for_endpoint(endpoint_type))} available")

        # Create Starlette app
        starlette_app = app.streamable_http_app()

        # Configure uvicorn
        config = uvicorn.Config(
            app=starlette_app,
            host=host,
            port=port,
            log_level="error",  # Reduce noise
            access_log=False,
            loop="asyncio",
        )

        # Create and run server
        server_instance = uvicorn.Server(config)
        await server_instance.serve()

    # Start all endpoints
    for endpoint_type, endpoint_config in multi_endpoint_config.items():
        if endpoint_config.get("enabled", True):
            task = asyncio.create_task(run_endpoint(endpoint_type, endpoint_config))
            tasks.append(task)

    print("\n[I] All endpoints started successfully!")
    print("\n[I] Connection examples:")
    print(
        "    Human (Claude Code): "
        "claude mcp add -t http marcus-human http://localhost:4298/mcp"
    )
    print("    Agent workers:       Configure to connect to http://localhost:4299/mcp")
    print("    Seneca analytics:    Configure to connect to http://localhost:4300/mcp")
    print("\n[I] Press Ctrl+C to stop all endpoints")

    try:
        # Wait for all servers
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("\n⚠️  Shutting down all endpoints...")
        # Cancel all tasks
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        print("✅ All endpoints stopped")


async def main() -> None:
    """Run the Marcus MCP server."""
    # Get transport from config
    config = get_config()
    transport_config = config.get("transport", {})
    transport = transport_config.get("type", "stdio")

    # Command line overrides
    if "--http" in sys.argv:
        transport = "http"
    elif "--stdio" in sys.argv:
        transport = "stdio"
    elif "--multi" in sys.argv:
        transport = "multi"

    # Parse port argument for single endpoint mode
    if "--port" in sys.argv:
        # Port override is handled by CLI argument parsing
        pass

    try:
        server = MarcusServer()

        # Initialize server silently
        await server.initialize()

        # Get current project for service registration
        current_project = None
        if hasattr(server.project_manager, "get_current_project"):
            try:
                current_project = server.project_manager.get_current_project()
                current_project = current_project.name if current_project else None
            except Exception:
                pass  # nosec B110

        # Register service for discovery (silently)
        register_marcus_service(
            mcp_command=sys.executable + " " + " ".join(sys.argv),
            log_dir=str(Path(server.realtime_log.name).parent),
            project_name=current_project,
            provider=server.provider,
        )

        # Run server with selected transport
        if transport == "multi":
            # Run multi-endpoint mode
            await run_multi_endpoint_server(server)
        elif transport == "http":
            # Use FastMCP for HTTP transport
            fastmcp = server._create_fastmcp()

            # Get HTTP configuration from config file
            http_config = transport_config.get("http", {})
            host = http_config.get("host", "127.0.0.1")
            port = http_config.get("port", 4298)
            path = http_config.get("path", "/mcp")
            log_level = http_config.get("log_level", "info")

            # Pretty output similar to Jupyter
            print("\n" + "=" * 70)
            print("    Marcus MCP Server (HTTP Mode)")
            print("=" * 70)
            print(f"\n[I] Server URL:    http://{host}:{port}{path}")
            print("[I] Transport:     Streamable HTTP")
            print(f"[I] Log level:     {log_level}")
            print("\n[I] The Marcus server is running at:")
            print(f"    http://{host}:{port}{path}")
            print("\n[I] To connect Claude, use this configuration:")
            print(f'    {{"url": "http://{host}:{port}{path}"}}')

            # For HTTP transport, we need to run it differently
            # FastMCP uses "streamable-http" as the transport name
            import uvicorn

            # Create the Starlette app from FastMCP
            app = fastmcp.streamable_http_app()

            # Run with uvicorn
            uvicorn.run(app, host=host, port=port, log_level=log_level)
        else:
            # Use existing stdio transport
            await server.run()
    except Exception as e:
        # Log errors to stderr only in case of failure
        print(f"Failed to start Marcus MCP server: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        raise


if __name__ == "__main__":
    # Load config first to get transport settings
    config = get_config()

    # Get transport type from config, with command line override
    transport_config = config.get("transport", {})
    transport = transport_config.get("type", "stdio")

    # Command line arguments override config
    if "--http" in sys.argv:
        transport = "http"
    elif "--stdio" in sys.argv:
        transport = "stdio"
    elif "--multi" in sys.argv:
        transport = "multi"

    if transport == "multi":
        # For multi-endpoint mode, use asyncio.run
        asyncio.run(main())
    elif transport == "http":
        # For HTTP mode, run the async initialization first
        async def setup_http_server() -> None:
            """Setup HTTP server with async initialization."""
            server = MarcusServer()
            await server.initialize()

            # Register service for discovery
            current_project = None
            if hasattr(server.project_manager, "get_current_project"):
                try:
                    current_project = server.project_manager.get_current_project()
                    current_project = current_project.name if current_project else None
                except Exception:
                    pass  # nosec B110

            register_marcus_service(
                mcp_command=sys.executable + " " + " ".join(sys.argv),
                log_dir=str(Path(server.realtime_log.name).parent),
                project_name=current_project,
                provider=server.provider,
            )

            return server

        # Run the async setup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        server = loop.run_until_complete(setup_http_server())

        # Create FastMCP instance
        fastmcp = server._create_fastmcp()

        # Get HTTP configuration from config file
        http_config = transport_config.get("http", {})
        host = http_config.get("host", "127.0.0.1")
        port = http_config.get("port", 8080)
        path = http_config.get("path", "/mcp")
        log_level = http_config.get("log_level", "info")

        # Pretty output similar to Jupyter
        print("\n" + "=" * 70)
        print("    Marcus MCP Server (HTTP Mode)")
        print("=" * 70)
        print(f"\n[I] Server URL:    http://{host}:{port}{path}")
        print("[I] Transport:     Streamable HTTP")
        print(f"[I] Log level:     {log_level}")
        print("\n[I] The Marcus server is running at:")
        print(f"    http://{host}:{port}{path}")
        print("\n[I] To connect Claude, use this configuration:")
        print(f'    {{"url": "http://{host}:{port}{path}"}}')

        # Setup shutdown handler for HTTP mode
        def http_signal_handler(signum: int, frame: Any) -> None:
            """Handle shutdown for HTTP server."""
            print(f"\n⚠️  Received signal {signum}, initiating graceful shutdown...")

            # Run cleanup in the event loop
            if hasattr(server, "_shutdown_event"):
                server._shutdown_event.set()

            # Perform sync cleanup
            if hasattr(server, "_sync_cleanup"):
                server._sync_cleanup()

        # Register signal handlers
        signal.signal(signal.SIGINT, http_signal_handler)
        signal.signal(signal.SIGTERM, http_signal_handler)

        # Run with uvicorn directly
        import uvicorn

        app = fastmcp.streamable_http_app()

        # Configure uvicorn with graceful shutdown
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level=log_level,
            loop="asyncio",
            access_log=False,  # Reduce noise
        )

        server_instance = uvicorn.Server(config)

        # Run the server (this will handle shutdown gracefully)
        try:
            server_instance.run()
        except KeyboardInterrupt:
            print("\n✅ HTTP server shutdown complete")
    else:
        # For stdio mode, use the standard async run
        asyncio.run(main())
