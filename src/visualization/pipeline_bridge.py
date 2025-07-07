"""
Pipeline Bridge - Connects MCP server pipeline events to UI server

This module monitors the MCP server's real-time log and extracts
pipeline events to forward to the visualization server.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict

import aiofiles
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .pipeline_flow import PipelineFlowVisualizer, PipelineStage

logger = logging.getLogger(__name__)


class PipelineLogHandler(FileSystemEventHandler):
    """Watches MCP server logs for pipeline events"""

    def __init__(self, pipeline_visualizer: PipelineFlowVisualizer):
        self.pipeline_visualizer = pipeline_visualizer
        self.log_positions = {}  # Track position in each log file
        self.active_flows = {}  # Track flow mappings

    def on_modified(self, event):
        """Handle log file modifications"""
        if event.is_directory or not event.src_path.endswith(".jsonl"):
            return

        # Process new lines in the log file
        asyncio.create_task(self.process_log_file(event.src_path))

    async def process_log_file(self, file_path: str):
        """Process new lines in a log file"""
        try:
            # Get last read position
            last_position = self.log_positions.get(file_path, 0)

            async with aiofiles.open(file_path, "r") as f:
                # Seek to last position
                await f.seek(last_position)

                # Read new lines
                async for line in f:
                    if line.strip():
                        try:
                            event = json.loads(line)
                            await self.process_log_event(event)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in log: {line}")

                # Update position
                self.log_positions[file_path] = await f.tell()

        except Exception as e:
            logger.error(f"Error processing log file {file_path}: {e}")

    async def process_log_event(self, event: Dict[str, Any]):
        """Process a log event and extract pipeline information"""
        event_type = event.get("type", "")

        # Map log events to pipeline events
        if event_type == "create_project_started":
            flow_id = event.get("flow_id")
            project_name = event.get("project_name", "Unknown Project")
            if flow_id:
                self.pipeline_visualizer.start_flow(flow_id, project_name)
                self.active_flows[flow_id] = True

        elif event_type == "ai_analysis_started":
            flow_id = event.get("flow_id")
            if flow_id and flow_id in self.active_flows:
                self.pipeline_visualizer.add_event(
                    flow_id=flow_id,
                    stage=PipelineStage.AI_ANALYSIS,
                    event_type="ai_analysis_started",
                    data=event.get("data", {}),
                    status="in_progress",
                )

        elif event_type == "task_generated":
            flow_id = event.get("flow_id")
            if flow_id and flow_id in self.active_flows:
                self.pipeline_visualizer.add_event(
                    flow_id=flow_id,
                    stage=PipelineStage.TASK_GENERATION,
                    event_type="task_generated",
                    data=event.get("data", {}),
                    status="completed",
                )

        elif event_type == "task_created":
            flow_id = event.get("flow_id")
            if flow_id and flow_id in self.active_flows:
                self.pipeline_visualizer.add_event(
                    flow_id=flow_id,
                    stage=PipelineStage.TASK_CREATION,
                    event_type="task_created",
                    data=event.get("data", {}),
                    status="completed",
                )

        elif event_type == "pipeline_completed":
            flow_id = event.get("flow_id")
            if flow_id and flow_id in self.active_flows:
                self.pipeline_visualizer.complete_flow(flow_id)
                del self.active_flows[flow_id]


class PipelineBridge:
    """Bridges pipeline events from MCP server to UI visualization"""

    def __init__(self, pipeline_visualizer: PipelineFlowVisualizer):
        self.pipeline_visualizer = pipeline_visualizer
        self.observer = Observer()
        self.handler = PipelineLogHandler(pipeline_visualizer)
        self.watching = False

    async def start_monitoring(self, log_dir: Path = None):
        """Start monitoring MCP server logs"""
        if log_dir is None:
            # Use absolute path based on Marcus root directory
            marcus_root = Path(__file__).parent.parent.parent
            log_dir = marcus_root / "logs" / "conversations"

        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)

        # Watch the log directory
        self.observer.schedule(self.handler, str(log_dir), recursive=False)
        self.observer.start()
        self.watching = True

        logger.info(f"Started monitoring pipeline events in {log_dir}")

        # Process existing log files
        for log_file in log_dir.glob("realtime_*.jsonl"):
            await self.handler.process_log_file(str(log_file))

    def stop_monitoring(self):
        """Stop monitoring logs"""
        if self.watching:
            self.observer.stop()
            self.observer.join()
            self.watching = False
            logger.info("Stopped monitoring pipeline events")
