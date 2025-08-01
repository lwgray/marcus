"""
Core Marcus MCP Server functionality.

This module contains the base MarcusServer class with essential components
and state management.
"""

import asyncio
import atexit
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from mcp.server import Server

from src.communication.communication_hub import CommunicationHub
from src.config.config_loader import get_config
from src.config.settings import Settings
from src.core.assignment_persistence import AssignmentPersistence
from src.core.code_analyzer import CodeAnalyzer
from src.core.event_loop_utils import EventLoopLockManager
from src.core.models import ProjectState, TaskAssignment, WorkerStatus
from src.core.project_context_manager import ProjectContextManager
from src.core.project_registry import ProjectRegistry
from src.core.service_registry import unregister_marcus_service
from src.cost_tracking.token_tracker import token_tracker
from src.integrations.ai_analysis_engine import AIAnalysisEngine
from src.integrations.kanban_interface import KanbanInterface
from src.monitoring.project_monitor import ProjectMonitor
from src.visualization.shared_pipeline_events import SharedPipelineVisualizer

logger = logging.getLogger(__name__)


class MarcusServer:
    """
    Core Marcus MCP Server class.

    This class provides the essential server functionality including:
    - Core component initialization
    - State management
    - Basic server lifecycle
    """

    def __init__(self) -> None:
        """Initialize Marcus server instance with core components."""
        # Configuration
        self.config = get_config()
        self.settings = Settings()

        # Project management
        self.project_registry = ProjectRegistry()
        self.project_manager = ProjectContextManager(self.project_registry)

        # Provider configuration
        self.provider = self.config.get("kanban.provider", "planka")
        self.is_multi_project_mode = self.config.is_multi_project_mode()

        # Setup logging
        self._setup_realtime_log()

        # Core components
        self.kanban_client: Optional[KanbanInterface] = None
        self.ai_engine = AIAnalysisEngine()
        self.monitor = ProjectMonitor()
        self.comm_hub = CommunicationHub()
        self.token_tracker = token_tracker

        # Code analyzer (GitHub-specific)
        self.code_analyzer = None
        if self.provider == "github":
            self.code_analyzer = CodeAnalyzer()

        # State tracking
        self.agent_tasks: Dict[str, TaskAssignment] = {}
        self.agent_status: Dict[str, WorkerStatus] = {}
        self.project_state: Optional[ProjectState] = None
        self.project_tasks: List[Any] = []

        # Assignment management
        self.assignment_persistence = AssignmentPersistence()
        self._lock_manager = EventLoopLockManager()
        self.tasks_being_assigned: Set[str] = set()

        # Monitoring components (initialized later)
        self.assignment_monitor: Optional[Any] = None
        self.lease_manager: Optional[Any] = None
        self.lease_monitor: Optional[Any] = None

        # Visualization
        self.pipeline_visualizer = SharedPipelineVisualizer()

        # Lifecycle tracking
        self._cleanup_done = False
        self._active_operations: Set[Any] = set()
        self._shutdown_event = asyncio.Event()

        # Enhanced features (initialized separately)
        self.events: Optional[Any] = None
        self.context: Optional[Any] = None
        self.memory: Optional[Any] = None
        self.persistence: Optional[Any] = None
        self.event_visualizer: Optional[Any] = None

        # MCP server instance
        self.server = Server("marcus")

        # Transport instances (created on demand)
        self._fastmcp: Optional[Any] = None
        self._endpoint_apps: Dict[str, Any] = {}

        # Log startup
        self.log_event(
            "server_startup",
            {"provider": self.provider, "timestamp": datetime.now().isoformat()},
        )

    def _setup_realtime_log(self) -> None:
        """Set up realtime logging file."""
        marcus_root = Path(__file__).parent.parent.parent.parent
        log_dir = marcus_root / "logs" / "conversations"
        log_dir.mkdir(parents=True, exist_ok=True)

        self.realtime_log = open(
            log_dir / f"realtime_{datetime.now():%Y%m%d_%H%M%S}.jsonl",
            "a",
            buffering=1,  # Line buffering
        )
        atexit.register(self.realtime_log.close)
        atexit.register(unregister_marcus_service)

    @property
    def assignment_lock(self) -> asyncio.Lock:
        """Get assignment lock for the current event loop."""
        return self._lock_manager.get_lock()

    def log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Log an event to the realtime log and event system.

        Args:
        ----
            event_type: Type of event
            data: Event data dictionary
        """
        # Write to realtime log immediately
        # For backward compatibility, include type and data at top level
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "type": event_type,  # Backward compatibility
            **data,  # Include data fields at top level
            "data": data,  # Also keep nested for new format
        }
        self.realtime_log.write(json.dumps(log_entry) + "\n")
        self.realtime_log.flush()

        # Also send to async event system if available
        if self.events:
            # Schedule async publish without blocking
            asyncio.create_task(self._publish_event_async(event_type, data))

    async def _publish_event_async(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Async helper to publish events.

        Args:
        ----
            event_type: Type of event
            data: Event data dictionary
        """
        try:
            if self.events:
                await self.events.publish(event_type, data)
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")

    async def initialize_kanban(self) -> None:
        """
        Initialize kanban client (backward compatibility).

        This method is provided for backward compatibility with tests.
        The actual implementation is in ServerInitializer.
        """
        from .initialization import ServerInitializer

        initializer = ServerInitializer(self)
        await initializer.initialize_kanban()

    def _ensure_environment_config(self) -> None:
        """
        Ensure environment config (backward compatibility).

        This method is provided for backward compatibility with tests.
        The actual implementation is in ServerInitializer.
        """
        from .initialization import ServerInitializer

        initializer = ServerInitializer(self)
        initializer._ensure_environment_config()

    async def run(self) -> None:
        """
        Run the server (backward compatibility).

        This method is provided for backward compatibility with tests.
        The actual implementation is in LifecycleManager.
        """
        from .lifecycle import LifecycleManager

        lifecycle = LifecycleManager(self)
        await lifecycle.run_stdio_server()

    async def refresh_project_state(self) -> None:
        """
        Refresh project state from kanban board.

        This method updates the internal project state by fetching
        the latest data from the kanban board.
        """
        if not self.kanban_client:
            logger.warning("No kanban client available for state refresh")
            return

        try:
            # Get project board name from config
            board_name = None
            if self.is_multi_project_mode:
                current_project = self.project_manager.get_current_project_name()
                if current_project:
                    project_config = self.config.get_project_config(current_project)
                    board_name = project_config.get("board_name")
            else:
                board_name = self.config.get("kanban.board_name")

            if not board_name:
                logger.error("No board name configured")
                return

            # Fetch board data
            board_data = await self.kanban_client.get_board(board_name)

            # Count tasks by status
            todo_count = 0
            in_progress_count = 0
            completed_count = 0

            for list_data in board_data.get("lists", []):
                list_name = list_data.get("name", "").lower()
                card_count = len(list_data.get("cards", []))

                if "to do" in list_name or "todo" in list_name:
                    todo_count += card_count
                elif "progress" in list_name:
                    in_progress_count += card_count
                elif "done" in list_name or "completed" in list_name:
                    completed_count += card_count

            # Update project state
            self.project_state = ProjectState(
                active_workers=len(self.agent_status),
                tasks_completed=completed_count,
                tasks_in_progress=in_progress_count,
                tasks_pending=todo_count,
                velocity=0.0,  # Would need historical data
                health_score=0.8,  # Basic health score
                updated_at=datetime.now(),
            )

            # Store all tasks for future reference
            self.project_tasks = []
            for list_data in board_data.get("lists", []):
                self.project_tasks.extend(list_data.get("cards", []))

            logger.info(
                f"Refreshed project state: {todo_count} todo, "
                f"{in_progress_count} in progress, {completed_count} completed"
            )

        except Exception as e:
            logger.error(f"Failed to refresh project state: {e}")
