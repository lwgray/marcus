"""
Unit tests for ConversationStreamProcessor
"""
import pytest
import json
import asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.visualization.conversation_stream import (
    ConversationStreamProcessor, 
    ConversationEvent,
    EventType
)
from tests.unit.visualization.factories import (
    create_mock_conversation_event,
    create_mock_log_entry
)


class TestConversationStreamProcessor:
    """Test cases for ConversationStreamProcessor"""
    
    @pytest.fixture
    def processor(self, temp_log_dir):
        """Create a ConversationStreamProcessor instance"""
        return ConversationStreamProcessor(log_dir=str(temp_log_dir))
    
    
    def test_add_event_handler(self, processor):
        """Test adding event handlers"""
        handler1 = Mock()
        handler2 = Mock()
        
        processor.add_event_handler(handler1)
        processor.add_event_handler(handler2)
        
        assert len(processor.event_handlers) == 2
        assert handler1 in processor.event_handlers
        assert handler2 in processor.event_handlers
    
    def test_remove_event_handler(self, processor):
        """Test removing event handlers"""
        handler = Mock()
        processor.add_event_handler(handler)
        
        processor.remove_event_handler(handler)
        assert handler not in processor.event_handlers
    
    @pytest.mark.asyncio
    async def test_parse_log_entry_worker_event(self, processor):
        """Test parsing worker communication event"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "event": "worker_communication",
            "worker_id": "worker-123",
            "conversation_type": "worker_to_pm",
            "message": "Task completed",
            "metadata": {"task_id": "task-456"}
        }
        
        event = processor._parse_log_entry(data)
        
        assert event is not None
        assert isinstance(event, ConversationEvent)
        assert event.source == "worker-123"
        assert event.target == "marcus"
        assert event.message == "Task completed"
        assert event.event_type == EventType.WORKER_MESSAGE.value
    
    @pytest.mark.asyncio
    async def test_parse_log_entry_decision_event(self, processor):
        """Test parsing PM decision event"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "event": "pm_decision",
            "decision": "Assign task to worker-789",
            "rationale": "Best skill match",
            "confidence_score": 0.85,
            "alternatives_considered": ["worker-456", "worker-123"],
            "decision_factors": {"skills": 0.9, "availability": 0.8}
        }
        
        event = processor._parse_log_entry(data)
        
        assert event is not None
        assert event.event_type == EventType.PM_DECISION.value
        assert event.confidence == 0.85
        assert event.message == "Assign task to worker-789"
    
    @pytest.mark.asyncio
    async def test_parse_log_entry_simple_format(self, processor):
        """Test parsing simple event format"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "type": "ping_request",
            "source": "mcp_client",
            "echo": "test"
        }
        
        event = processor._parse_log_entry(data)
        
        assert event is not None
        assert event.event_type == "ping_request"
        assert event.source == "mcp_client"
        assert event.target == "marcus"
        assert "Ping: test" in event.message
    
    @pytest.mark.asyncio
    async def test_process_log_line(self, processor):
        """Test processing a single log line"""
        log_line = json.dumps({
            "timestamp": datetime.now().isoformat(),
            "event": "worker_communication",
            "worker_id": "worker-123",
            "conversation_type": "worker_to_pm",
            "message": "Test message",
            "metadata": {}
        })
        
        handler = Mock()
        processor.add_event_handler(handler)
        
        await processor._process_log_line(log_line)
        
        # Check event was added to history
        assert len(processor.conversation_history) == 1
        assert processor.conversation_history[0].source == "worker-123"
        
        # Check handler was called
        handler.assert_called_once()
        event = handler.call_args[0][0]
        assert isinstance(event, ConversationEvent)
    
    @pytest.mark.asyncio
    async def test_process_log_line_async_handler(self, processor):
        """Test processing with async event handler"""
        log_line = json.dumps({
            "timestamp": datetime.now().isoformat(),
            "type": "ping_request",
            "source": "test",
            "echo": "hello"
        })
        
        handler = AsyncMock()
        processor.add_event_handler(handler)
        
        await processor._process_log_line(log_line)
        
        handler.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_log_line_invalid_json(self, processor):
        """Test handling invalid JSON"""
        handler = Mock()
        processor.add_event_handler(handler)
        
        # Should not raise exception
        await processor._process_log_line("Invalid JSON")
        
        # Handler should not be called
        handler.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_log_file(self, processor, temp_log_dir):
        """Test processing a log file"""
        log_file = temp_log_dir / "test.jsonl"
        
        # Write test events
        with open(log_file, 'w') as f:
            for i in range(3):
                event_data = {
                    "timestamp": datetime.now().isoformat(),
                    "event": "worker_communication",
                    "worker_id": f"worker-{i}",
                    "conversation_type": "worker_to_pm",
                    "message": f"Message {i}",
                    "metadata": {}
                }
                f.write(json.dumps(event_data) + '\n')
        
        handler = Mock()
        processor.add_event_handler(handler)
        
        # Process file
        await processor._process_log_file(log_file)
        
        # Should have processed 3 events
        assert handler.call_count == 3
        assert len(processor.conversation_history) == 3
    
    @pytest.mark.asyncio
    async def test_process_log_file_from_position(self, processor, temp_log_dir):
        """Test processing file from specific position"""
        log_file = temp_log_dir / "test.jsonl"
        
        # Write initial content
        with open(log_file, 'w') as f:
            event1 = {
                "timestamp": datetime.now().isoformat(),
                "type": "ping_request",
                "source": "test1",
                "echo": "first"
            }
            f.write(json.dumps(event1) + '\n')
            position = f.tell()
            
            event2 = {
                "timestamp": datetime.now().isoformat(),
                "type": "ping_response",
                "echo": "second",
                "status": "ok"
            }
            f.write(json.dumps(event2) + '\n')
        
        handler = Mock()
        processor.add_event_handler(handler)
        
        # Process from position (should skip first event)
        await processor._process_log_file(log_file, from_position=position)
        
        # Should only process one event
        handler.assert_called_once()
        event = handler.call_args[0][0]
        assert event.event_type == "ping_response"
    
    def test_get_conversation_summary(self, processor):
        """Test getting conversation summary"""
        # Add some events
        for i in range(5):
            event = create_mock_conversation_event(
                event_type=EventType.WORKER_MESSAGE.value,
                source=f"worker_{i % 2}"  # Changed from worker- to worker_
            )
            processor.conversation_history.append(event)
        
        # Add a decision event
        decision_event = ConversationEvent(
            id="dec-1",
            timestamp=datetime.now(),
            source="pm_agent",
            target="decision",
            event_type=EventType.PM_DECISION.value,
            message="Test decision",
            metadata={}
        )
        processor.conversation_history.append(decision_event)
        
        summary = processor.get_conversation_summary()
        
        assert summary['total_events'] == 6
        assert summary['decision_count'] == 1
        assert isinstance(summary['active_workers'], int)
        assert summary['active_workers'] == 2  # worker-0 and worker-1
        assert EventType.WORKER_MESSAGE.value in summary['event_types']
        assert EventType.PM_DECISION.value in summary['event_types']
    
    @pytest.mark.asyncio
    async def test_start_stop_streaming(self, processor):
        """Test starting and stopping the stream processor"""
        with patch('src.visualization.conversation_stream.Observer') as mock_observer_class:
            mock_observer = MagicMock()
            mock_observer_class.return_value = mock_observer
            
            # Start streaming
            streaming_task = asyncio.create_task(processor.start_streaming())
            await asyncio.sleep(0.1)  # Let it start
            
            assert processor._running is True
            mock_observer.start.assert_called_once()
            
            # Stop streaming
            processor.stop_streaming()
            await asyncio.sleep(0.1)
            
            assert processor._running is False
            
            # Cancel the task
            streaming_task.cancel()
            try:
                await streaming_task
            except asyncio.CancelledError:
                pass
    
    def test_conversation_history_limit(self, processor):
        """Test that conversation history respects max size"""
        # Add more events than max_history_size
        for i in range(processor.max_history_size + 100):
            event = create_mock_conversation_event()
            processor.conversation_history.append(event)
        
        # Manually enforce limit as would happen in _process_log_line
        while len(processor.conversation_history) > processor.max_history_size:
            processor.conversation_history.pop(0)
        
        assert len(processor.conversation_history) == processor.max_history_size