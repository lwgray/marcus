"""
Server lifecycle management.

This module handles server startup, shutdown, and cleanup operations.
"""

import asyncio
import logging
import signal
import sys
from typing import Any, Dict

from mcp.server.stdio import stdio_server

# Web server and snapshot manager imports removed - not in original server

logger = logging.getLogger(__name__)


class LifecycleManager:
    """Manages server lifecycle operations."""

    def __init__(self, server):
        """
        Initialize lifecycle manager.

        Args:
        ----
            server: The MarcusServer instance
        """
        self.server = server
        self._signal_handlers_setup = False

    def setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        if self._signal_handlers_setup:
            return

        def signal_handler(signum: int, frame: Any) -> None:
            """Handle shutdown signals."""
            logger.info(f"Received signal {signum}, initiating shutdown...")

            # Set shutdown event
            self.server._shutdown_event.set()

            # If no event loop, do sync cleanup
            try:
                asyncio.get_running_loop()
                # Schedule cleanup
                asyncio.create_task(self.cleanup_on_shutdown())
            except RuntimeError:
                # No event loop, do sync cleanup
                self._sync_cleanup()

            # Exit
            sys.exit(0)

        # Register handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        self._signal_handlers_setup = True
        logger.info("Signal handlers registered")

    def _sync_cleanup(self) -> None:
        """Perform synchronous cleanup when no event loop is available."""
        if self.server._cleanup_done:
            return

        try:
            logger.info("Performing synchronous cleanup...")

            # Close realtime log
            if hasattr(self.server, "realtime_log"):
                self.server.realtime_log.close()

            # Save assignments
            if self.server.assignment_persistence and self.server.agent_tasks:
                # Create a new event loop for async operations
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(
                        self.server.assignment_persistence.save_assignments(
                            self.server.agent_tasks
                        )
                    )
                finally:
                    loop.close()

            self.server._cleanup_done = True
            logger.info("Synchronous cleanup completed")

        except Exception as e:
            logger.error(f"Error during synchronous cleanup: {e}")

    async def cleanup_on_shutdown(self) -> None:
        """Cleanup resources on shutdown."""
        if self.server._cleanup_done:
            return

        try:
            logger.info("Starting graceful shutdown...")

            # Stop monitoring tasks
            if self.server.assignment_monitor:
                await self.server.assignment_monitor.stop()

            if self.server.lease_monitor:
                await self.server.lease_monitor.stop()

            # Wait for active operations with timeout
            if self.server._active_operations:
                num_ops = len(self.server._active_operations)
                logger.info(f"Waiting for {num_ops} active operations...")
                try:
                    await asyncio.wait_for(
                        asyncio.gather(
                            *self.server._active_operations, return_exceptions=True
                        ),
                        timeout=5.0,
                    )
                except asyncio.TimeoutError:
                    logger.warning("Some operations did not complete in time")

            # Save current assignments
            if self.server.assignment_persistence and self.server.agent_tasks:
                logger.info("Saving assignment state...")
                await self.server.assignment_persistence.save_assignments(
                    self.server.agent_tasks
                )

            # Close resources
            if hasattr(self.server, "realtime_log"):
                self.server.realtime_log.close()

            # Cleanup visualization
            if hasattr(self.server, "pipeline_visualizer"):
                self.server.pipeline_visualizer.cleanup()

            # Log final event
            self.server.log_event(
                "server_shutdown",
                {"reason": "graceful", "active_agents": len(self.server.agent_status)},
            )

            self.server._cleanup_done = True
            logger.info("Graceful shutdown completed")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
            self.server._cleanup_done = True

    async def run_stdio_server(self) -> None:
        """Run the server with stdio transport."""
        try:
            # Setup shutdown handling
            shutdown_task = asyncio.create_task(self.server._shutdown_event.wait())

            # Create server task
            async with stdio_server() as (read_stream, write_stream):
                server_task = asyncio.create_task(
                    self.server.server.run(
                        read_stream,
                        write_stream,
                        self.server.server.create_initialization_options(),
                    )
                )

                # Optional features removed - not in original server

                # Wait for shutdown or server completion
                done, pending = await asyncio.wait(
                    [shutdown_task, server_task], return_when=asyncio.FIRST_COMPLETED
                )

                # Cancel pending tasks
                for task in pending:
                    task.cancel()

                # Wait for cancellation
                await asyncio.gather(*pending, return_exceptions=True)

        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
            raise
        finally:
            await self.cleanup_on_shutdown()


async def run_multi_endpoint_server(server) -> None:
    """
    Run server with multiple HTTP endpoints.

    Args:
    ----
        server: The MarcusServer instance to run
    """
    from contextlib import asynccontextmanager

    import uvicorn

    # Get endpoint configuration
    endpoints_config = server.config.get("http_endpoints", {})
    if not endpoints_config:
        logger.warning("No HTTP endpoints configured")
        return

    # Lifecycle manager
    lifecycle = LifecycleManager(server)

    @asynccontextmanager
    async def lifespan(app):
        """Handle lifespan events for FastAPI."""
        # Startup
        logger.info("Starting multi-endpoint server...")
        from .initialization import ServerInitializer

        initializer = ServerInitializer(server)
        await initializer.initialize()

        # Register signal handlers
        lifecycle.setup_signal_handlers()

        yield

        # Shutdown
        await lifecycle.cleanup_on_shutdown()

    # Create tasks for each endpoint
    tasks = []

    async def run_endpoint(endpoint_type: str, endpoint_config: Dict[str, Any]) -> None:
        """Run a single endpoint."""
        try:
            # Import here to avoid circular dependency
            from .transport import TransportManager

            transport = TransportManager(server)

            # Create app for this endpoint
            app = transport.create_endpoint_app(endpoint_type)
            app.router.lifespan_context = lifespan

            # Configure server
            host = endpoint_config.get("host", "127.0.0.1")  # nosec B104
            port = endpoint_config.get("port", 8000)

            logger.info(f"Starting {endpoint_type} endpoint on {host}:{port}")

            # Create server config
            config = uvicorn.Config(
                app=app, host=host, port=port, log_level="info", lifespan="on"
            )

            # Create and run server
            server_instance = uvicorn.Server(config)
            await server_instance.serve()

        except Exception as e:
            logger.error(f"Error running {endpoint_type} endpoint: {e}")
            raise

    # Start all endpoints
    for endpoint_type, endpoint_config in endpoints_config.items():
        if endpoint_config.get("enabled", True):
            task = asyncio.create_task(run_endpoint(endpoint_type, endpoint_config))
            tasks.append(task)

    # Wait for all endpoints
    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f"Multi-endpoint server error: {e}")
        # Cancel all tasks
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
