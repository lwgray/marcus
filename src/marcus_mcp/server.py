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
from src.marcus_mcp.handlers import get_tool_definitions, handle_tool_call  # noqa: E402
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
        self.assignment_lock = asyncio.Lock()
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

    def _register_handlers(self) -> None:
        """Register MCP tool handlers"""

        @self.server.list_tools()  # type: ignore[no-untyped-call,misc]
        async def handle_list_tools() -> List[types.Tool]:
            """Return list of available tools"""
            # Determine role based on client type
            # For now, we'll check if this is being called by an agent or human
            # Agents typically have "agent" in their client name or metadata
            # This can be enhanced with proper authentication/role detection
            role = "agent"  # Default to agent for limited tool access

            # If we detect this is an agent client, limit tools
            # This would be enhanced with proper client identification
            # For now, we assume all clients get agent-level access only

            return get_tool_definitions(role)

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
                    f"  Clearing {len(self.tasks_being_assigned)} pending task assignments"
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
                    f"  Clearing {len(self.tasks_being_assigned)} pending task assignments"
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
        """Initialize assignment monitor and lease manager for the current kanban client"""
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

    async def run(self) -> None:
        """Run the MCP server"""
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


async def main() -> None:
    """Run the Marcus MCP server."""
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

        # Now run the server with clean stdio
        await server.run()
    except Exception as e:
        # Log errors to stderr only in case of failure
        print(f"Failed to start Marcus MCP server: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        raise


if __name__ == "__main__":
    asyncio.run(main())
