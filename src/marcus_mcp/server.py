#!/usr/bin/env python3
"""
Marcus MCP Server - Modularized Version

A lean MCP server implementation that delegates all tool logic
to specialized modules for better maintainability.
"""

import asyncio
import atexit
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from src.communication.communication_hub import CommunicationHub
from src.config.config_loader import get_config
from src.config.settings import Settings
from src.core.assignment_persistence import AssignmentPersistence
from src.core.code_analyzer import CodeAnalyzer
from src.core.context import Context
from src.core.events import Events
from src.core.models import (
    ProjectState,
    RiskLevel,
    TaskAssignment,
    TaskStatus,
    WorkerStatus,
)
from src.core.project_context_manager import ProjectContextManager
from src.core.project_registry import ProjectRegistry
from src.cost_tracking.ai_usage_middleware import ai_usage_middleware
from src.cost_tracking.token_tracker import token_tracker
from src.integrations.ai_analysis_engine import AIAnalysisEngine
from src.integrations.kanban_factory import KanbanFactory
from src.integrations.kanban_interface import KanbanInterface
from src.marcus_mcp.handlers import get_tool_definitions, handle_tool_call
from src.monitoring.assignment_monitor import AssignmentMonitor
from src.monitoring.project_monitor import ProjectMonitor
from src.visualization.shared_pipeline_events import SharedPipelineVisualizer


class MarcusServer:
    """Marcus MCP Server with modularized architecture"""

    def __init__(self):
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
        if self.config.is_multi_project_mode():
            print(
                f"Initializing Marcus in multi-project mode...",
                file=sys.stderr,
            )
        else:
            print(
                f"Initializing Marcus with {self.provider.upper()} kanban provider...",
                file=sys.stderr,
            )

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
        self.tasks_being_assigned: set = set()

        # Assignment monitoring
        self.assignment_monitor = None

        # Pipeline flow visualization (shared between processes)
        self.pipeline_visualizer = SharedPipelineVisualizer()

        # New enhancement systems (optional based on config)
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

            self.event_visualizer = EventIntegratedVisualizer(events_system=self.events)

        # Log startup
        self.log_event(
            "server_startup",
            {"provider": self.provider, "timestamp": datetime.now().isoformat()},
        )

        # Create MCP server instance
        self.server = Server("marcus")

        # Register handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register MCP tool handlers"""

        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """Return list of available tools"""
            # Determine role based on client type
            # For now, we'll check if this is being called by an agent or human
            # Agents typically have "agent" in their client name or metadata
            # This can be enhanced with proper authentication/role detection
            role = "human"  # Default to human for full access

            # If we detect this is an agent client, limit tools
            # This would be enhanced with proper client identification
            # For now, we assume human users get full access

            return get_tool_definitions(role)

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Optional[Dict[str, Any]]
        ) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """Handle tool calls"""
            return await handle_tool_call(name, arguments, self)

        @self.server.list_prompts()
        async def handle_list_prompts() -> List[types.Prompt]:
            """Return list of available prompts - Marcus doesn't use prompts currently"""
            return []

        @self.server.list_resources()
        async def handle_list_resources() -> List[types.Resource]:
            """Return list of available resources - Marcus doesn't use resources currently"""
            return []

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read a resource - Marcus doesn't use resources currently"""
            raise ValueError(f"Resource not found: {uri}")

        @self.server.get_prompt()
        async def handle_get_prompt(
            name: str, arguments: Optional[Dict[str, str]] = None
        ) -> types.GetPromptResult:
            """Get a prompt - Marcus doesn't use prompts currently"""
            raise ValueError(f"Prompt not found: {name}")

    async def initialize(self):
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
                active_project = await self.project_registry.get_active_project()
                if active_project:
                    print(
                        f"✅ Active project: {active_project.name} ({active_project.provider})",
                        file=sys.stderr,
                    )
        else:
            # Legacy mode - create kanban client directly
            await self.initialize_kanban()

            # Migrate to multi-project if needed
            await self._migrate_to_multi_project()

        # Initialize event visualizer if available
        if self.event_visualizer:
            await self.event_visualizer.initialize()
            print("✅ Event-integrated visualization enabled", file=sys.stderr)

        # Wrap AI engine for token tracking
        self.ai_engine = ai_usage_middleware.wrap_ai_provider(self.ai_engine)

        # Initialize pattern learning components for API
        from src.api.pattern_learning_init import init_pattern_learning_components

        try:
            init_pattern_learning_components(
                kanban_client=self.kanban_client, ai_engine=self.ai_engine
            )
            print("✅ Pattern learning API initialized", file=sys.stderr)
        except Exception as e:
            print(f"⚠️ Pattern learning API initialization failed: {e}", file=sys.stderr)

        print("✅ Marcus server initialized", file=sys.stderr)

    async def _migrate_to_multi_project(self):
        """Migrate legacy configuration to multi-project format"""
        if self.kanban_client and not self.config.is_multi_project_mode():
            # Create a project from the legacy config
            project_id = await self.project_registry.create_from_legacy_config(
                self.config._config
            )

            # Set it as active
            await self.project_registry.set_active_project(project_id)

            # Initialize project context with existing client
            await self.project_manager.switch_project(project_id)

            print("✅ Migrated to multi-project mode", file=sys.stderr)

    async def initialize_kanban(self):
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
                                "details": f"Kanban client {type(self.kanban_client).__name__} does not support task creation. "
                                f"Expected KanbanClientWithCreate or compatible implementation.",
                            },
                        ),
                    )

                # Connect to the kanban board
                if hasattr(self.kanban_client, "connect"):
                    await self.kanban_client.connect()

                # Initialize assignment monitor
                if self.assignment_monitor is None:
                    self.assignment_monitor = AssignmentMonitor(
                        self.assignment_persistence, self.kanban_client
                    )
                    await self.assignment_monitor.start()

                print(
                    f"✅ Kanban client initialized: {type(self.kanban_client).__name__}",
                    file=sys.stderr,
                )

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

    def _ensure_environment_config(self):
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

                print(f"✅ Loaded configuration from {config_path}", file=sys.stderr)

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

    def log_event(self, event_type: str, data: dict):
        """Log events immediately to realtime log and optionally to Events system"""
        event = {"timestamp": datetime.now().isoformat(), "type": event_type, **data}
        self.realtime_log.write(json.dumps(event) + "\n")

        # Also publish to Events system if available
        if self.events:
            # Run async publish in a fire-and-forget manner
            asyncio.create_task(self._publish_event_async(event_type, data))

    async def _publish_event_async(self, event_type: str, data: dict):
        """Helper to publish events asynchronously"""
        try:
            source = data.get("source", "marcus")
            await self.events.publish(event_type, source, data)
        except Exception as e:
            # Don't let event publishing errors affect main flow
            print(f"Error publishing event: {e}", file=sys.stderr)

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

                self.project_state = ProjectState(
                    board_id=self.kanban_client.board_id,
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
                    "risk_level": self.project_state.risk_level.value,  # Convert enum to string
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

    async def run(self):
        """Run the MCP server"""

        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options(),
                )
        except Exception as e:
            print(f"❌ MCP server error: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc(file=sys.stderr)
            raise


async def main():
    """Main entry point"""
    try:
        server = MarcusServer()
        await server.initialize()
        await server.run()
    except Exception as e:
        print(f"❌ Failed to start Marcus MCP server: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        raise


if __name__ == "__main__":
    asyncio.run(main())
