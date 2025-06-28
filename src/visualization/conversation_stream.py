"""
Real-time conversation stream processor for visualization

Processes structured logs from ConversationLogger and prepares them
for real-time visualization in the UI.
"""

import asyncio
import logging
import queue
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import aiofiles
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent


@dataclass
class ConversationEvent:
    """Structured conversation event for visualization"""
    id: str
    timestamp: datetime
    source: str
    target: str
    event_type: str
    message: str
    metadata: Dict[str, Any]
    confidence: Optional[float] = None
    duration_ms: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class EventType(Enum):
    """Types of events in the conversation flow"""
    WORKER_MESSAGE = "worker_message"
    PM_THINKING = "pm_thinking"
    PM_DECISION = "pm_decision"
    KANBAN_REQUEST = "kanban_request"
    KANBAN_RESPONSE = "kanban_response"
    TASK_ASSIGNMENT = "task_assignment"
    PROGRESS_UPDATE = "progress_update"
    BLOCKER_REPORT = "blocker_report"
    SYSTEM_STATE = "system_state"


class ConversationStreamProcessor:
    """
    Processes conversation logs in real-time and streams events
    to visualization clients
    """
    
    def __init__(self, log_dir: str = "logs/conversations"):
        self.log_dir = Path(log_dir)
        self.event_handlers: List[Callable] = []
        self.conversation_history: List[ConversationEvent] = []
        self.max_history_size = 1000
        self._event_counter = 0
        self._file_positions: Dict[str, int] = {}
        self._running = False
        self._event_queue = queue.Queue()
        
    def add_event_handler(self, handler: Callable[[ConversationEvent], None]):
        """Add a handler to be called when new events are processed"""
        self.event_handlers.append(handler)
        
    def remove_event_handler(self, handler: Callable):
        """Remove an event handler"""
        if handler in self.event_handlers:
            self.event_handlers.remove(handler)
            
    
    async def _process_queue(self):
        """Process queued file change events"""
        try:
            while not self._event_queue.empty():
                file_path, last_position = self._event_queue.get_nowait()
                await self._process_log_file(file_path, from_position=last_position)
        except queue.Empty:
            pass
            
    async def start_streaming(self):
        """Start streaming conversation events from log files"""
        self._running = True
        logging.info(f"ConversationStreamProcessor: Starting streaming from {self.log_dir}")
        
        # Start file watcher for new log entries
        event_handler = LogFileHandler(self)
        observer = Observer()
        observer.schedule(event_handler, str(self.log_dir), recursive=False)
        observer.start()
        
        try:
            # Process existing log files
            logging.info("ConversationStreamProcessor: Processing existing logs...")
            await self._process_existing_logs()
            
            # Keep running until stopped
            while self._running:
                # Process queued file changes
                await self._process_queue()
                await asyncio.sleep(0.1)
                
        finally:
            observer.stop()
            observer.join()
            
    def stop_streaming(self):
        """Stop streaming events"""
        self._running = False
        
    async def _process_existing_logs(self):
        """Process all existing log files"""
        # Include both old format and new realtime logs
        log_files = list(self.log_dir.glob("conversations_*.jsonl"))
        log_files.extend(list(self.log_dir.glob("realtime_*.jsonl")))
        log_files.sort()  # Process in chronological order
        
        for log_file in log_files:
            await self._process_log_file(log_file)
            
    async def _process_log_file(self, file_path: Path, from_position: int = 0):
        """Process a single log file from given position"""
        try:
            async with aiofiles.open(file_path, 'r') as f:
                # Seek to last known position
                if from_position > 0:
                    await f.seek(from_position)
                    
                async for line in f:
                    if line.strip():
                        await self._process_log_line(line)
                        
                # Update file position
                self._file_positions[str(file_path)] = await f.tell()
                
        except Exception as e:
            print(f"Error processing log file {file_path}: {e}")
            
    async def _process_log_line(self, line: str):
        """Process a single log line and create event"""
        try:
            data = json.loads(line)
            event = self._parse_log_entry(data)
            
            if event:
                # Add to history
                self.conversation_history.append(event)
                if len(self.conversation_history) > self.max_history_size:
                    self.conversation_history.pop(0)
                    
                # Notify handlers
                for handler in self.event_handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(event)
                        else:
                            handler(event)
                    except Exception as e:
                        print(f"Error in event handler: {e}")
                        
        except json.JSONDecodeError:
            pass  # Skip invalid lines
            
    def _parse_log_entry(self, data: Dict[str, Any]) -> Optional[ConversationEvent]:
        """Parse log entry into ConversationEvent"""
        self._event_counter += 1
        
        # Extract common fields
        timestamp = datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat()))
        
        # Check for new simple format from realtime logs
        if 'type' in data and 'event' not in data:
            return self._parse_simple_event(data, timestamp)
        
        # Legacy format handling
        event_name = data.get('event', '')
        
        # Parse based on event type
        if event_name == 'worker_communication':
            return self._parse_worker_event(data, timestamp)
        elif event_name == 'pm_thinking':
            return self._parse_thinking_event(data, timestamp)
        elif event_name == 'pm_decision':
            return self._parse_decision_event(data, timestamp)
        elif event_name == 'kanban_interaction':
            return self._parse_kanban_event(data, timestamp)
        elif event_name == 'task_assignment':
            return self._parse_assignment_event(data, timestamp)
        elif event_name == 'progress_update':
            return self._parse_progress_event(data, timestamp)
        elif event_name == 'blocker_reported':
            return self._parse_blocker_event(data, timestamp)
        elif event_name == 'system_state':
            return self._parse_system_state_event(data, timestamp)
            
        return None
    
    def _parse_simple_event(self, data: Dict, timestamp: datetime) -> ConversationEvent:
        """Parse simple event format from realtime logs"""
        event_type = data.get('type', 'unknown')
        
        # Determine source and target based on event type
        if event_type == 'ping_request':
            source = data.get('source', 'mcp_client')
            target = 'marcus'
        elif event_type == 'ping_response':
            source = 'marcus'
            target = 'mcp_client'
        else:
            source = data.get('source', 'unknown')
            target = data.get('target', 'unknown')
        
        # Create message from data
        message = data.get('message', '')
        if not message:
            if event_type == 'ping_request':
                message = f"Ping: {data.get('echo', 'pong')}"
            elif event_type == 'ping_response':
                message = f"Pong: {data.get('echo', 'pong')} (Status: {data.get('status', 'unknown')})"
            else:
                message = json.dumps({k: v for k, v in data.items() if k not in ['timestamp', 'type']})
        
        return ConversationEvent(
            id=f"event_{self._event_counter}",
            timestamp=timestamp,
            source=source,
            target=target,
            event_type=event_type,
            message=message,
            metadata=data
        )
        
    def _parse_worker_event(self, data: Dict, timestamp: datetime) -> ConversationEvent:
        """Parse worker communication event"""
        worker_id = data.get('worker_id', 'unknown')
        conversation_type = data.get('conversation_type', '')
        
        if 'worker_to_pm' in conversation_type:
            source, target = worker_id, 'marcus'
        else:
            source, target = 'marcus', worker_id
            
        return ConversationEvent(
            id=f"event_{self._event_counter}",
            timestamp=timestamp,
            source=source,
            target=target,
            event_type=EventType.WORKER_MESSAGE.value,
            message=data.get('message', ''),
            metadata=data.get('metadata', {})
        )
        
    def _parse_thinking_event(self, data: Dict, timestamp: datetime) -> ConversationEvent:
        """Parse PM thinking event"""
        return ConversationEvent(
            id=f"event_{self._event_counter}",
            timestamp=timestamp,
            source='marcus',
            target='internal',
            event_type=EventType.PM_THINKING.value,
            message=data.get('thought', ''),
            metadata=data.get('context', {})
        )
        
    def _parse_decision_event(self, data: Dict, timestamp: datetime) -> ConversationEvent:
        """Parse PM decision event"""
        return ConversationEvent(
            id=f"event_{self._event_counter}",
            timestamp=timestamp,
            source='marcus',
            target='decision',
            event_type=EventType.PM_DECISION.value,
            message=data.get('decision', ''),
            metadata={
                'rationale': data.get('rationale', ''),
                'alternatives': data.get('alternatives_considered', []),
                'decision_factors': data.get('decision_factors', {}),
            },
            confidence=data.get('confidence_score')
        )
        
    def _parse_kanban_event(self, data: Dict, timestamp: datetime) -> ConversationEvent:
        """Parse Kanban interaction event"""
        direction = data.get('conversation_type', '')
        
        if 'pm_to_kanban' in direction:
            source, target = 'marcus', 'kanban_board'
            event_type = EventType.KANBAN_REQUEST
        else:
            source, target = 'kanban_board', 'marcus'
            event_type = EventType.KANBAN_RESPONSE
            
        return ConversationEvent(
            id=f"event_{self._event_counter}",
            timestamp=timestamp,
            source=source,
            target=target,
            event_type=event_type.value,
            message=data.get('action', ''),
            metadata={
                'data': data.get('data', {}),
                'processing_steps': data.get('processing_steps', [])
            }
        )
        
    def _parse_assignment_event(self, data: Dict, timestamp: datetime) -> ConversationEvent:
        """Parse task assignment event"""
        return ConversationEvent(
            id=f"event_{self._event_counter}",
            timestamp=timestamp,
            source='marcus',
            target=data.get('worker_id', 'unknown'),
            event_type=EventType.TASK_ASSIGNMENT.value,
            message=f"Task {data.get('task_id')} assigned",
            metadata={
                'task_details': data.get('task_details', {}),
                'assignment_score': data.get('assignment_score'),
                'dependency_analysis': data.get('dependency_analysis', {})
            }
        )
        
    def _parse_progress_event(self, data: Dict, timestamp: datetime) -> ConversationEvent:
        """Parse progress update event"""
        return ConversationEvent(
            id=f"event_{self._event_counter}",
            timestamp=timestamp,
            source=data.get('worker_id', 'unknown'),
            target='marcus',
            event_type=EventType.PROGRESS_UPDATE.value,
            message=f"{data.get('progress', 0)}% - {data.get('message', '')}",
            metadata={
                'task_id': data.get('task_id'),
                'status': data.get('status'),
                'metrics': data.get('metrics', {})
            }
        )
        
    def _parse_blocker_event(self, data: Dict, timestamp: datetime) -> ConversationEvent:
        """Parse blocker report event"""
        return ConversationEvent(
            id=f"event_{self._event_counter}",
            timestamp=timestamp,
            source=data.get('worker_id', 'unknown'),
            target='marcus',
            event_type=EventType.BLOCKER_REPORT.value,
            message=data.get('blocker_description', ''),
            metadata={
                'task_id': data.get('task_id'),
                'severity': data.get('severity'),
                'suggested_solutions': data.get('suggested_solutions', [])
            }
        )
        
    def _parse_system_state_event(self, data: Dict, timestamp: datetime) -> ConversationEvent:
        """Parse system state event"""
        return ConversationEvent(
            id=f"event_{self._event_counter}",
            timestamp=timestamp,
            source='marcus',
            target='system',
            event_type=EventType.SYSTEM_STATE.value,
            message="System state update",
            metadata={
                'active_workers': data.get('active_workers', 0),
                'tasks_in_progress': data.get('tasks_in_progress', 0),
                'tasks_completed': data.get('tasks_completed', 0),
                'tasks_blocked': data.get('tasks_blocked', 0),
                'system_metrics': data.get('system_metrics', {})
            }
        )
        
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of conversation patterns"""
        summary = {
            'total_events': len(self.conversation_history),
            'event_types': {},
            'active_workers': set(),
            'decision_count': 0,
            'blocker_count': 0,
            'completion_count': 0
        }
        
        for event in self.conversation_history:
            # Count event types
            event_type = event.event_type
            summary['event_types'][event_type] = summary['event_types'].get(event_type, 0) + 1
            
            # Track active workers
            if event.source.startswith('worker_') or event.source.startswith('agent'):
                summary['active_workers'].add(event.source)
            elif event.target.startswith('worker_') or event.target.startswith('agent'):
                summary['active_workers'].add(event.target)
                
            # Count specific events
            if event.event_type == EventType.PM_DECISION.value:
                summary['decision_count'] += 1
            elif event.event_type == EventType.BLOCKER_REPORT.value:
                summary['blocker_count'] += 1
            elif event.event_type == EventType.PROGRESS_UPDATE.value:
                if event.metadata.get('status') == 'completed':
                    summary['completion_count'] += 1
                    
        summary['active_workers'] = len(summary['active_workers'])
        return summary


class LogFileHandler(FileSystemEventHandler):
    """Handles file system events for log files"""
    
    def __init__(self, processor: ConversationStreamProcessor):
        self.processor = processor
        
    def on_modified(self, event):
        """Handle file modification events"""
        if isinstance(event, FileModifiedEvent) and event.src_path.endswith('.jsonl'):
            logging.info(f"ConversationStreamProcessor: File modified: {event.src_path}")
            file_path = Path(event.src_path)
            last_position = self.processor._file_positions.get(str(file_path), 0)
            
            # Queue the file for processing in the async context
            self.processor._event_queue.put((file_path, last_position))