"""
Unit tests for the Events system
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.core.events import Event, Events, EventTypes


class TestEvent:
    """Test suite for Event dataclass"""
    
    def test_event_creation(self):
        """Test creating an event with all fields"""
        event = Event(
            event_id="test_123",
            timestamp=datetime.now(),
            event_type="test_event",
            source="test_source",
            data={"key": "value"},
            metadata={"confidence": 0.9}
        )
        
        assert event.event_id == "test_123"
        assert event.event_type == "test_event"
        assert event.source == "test_source"
        assert event.data == {"key": "value"}
        assert event.metadata == {"confidence": 0.9}
        
    def test_event_to_dict(self):
        """Test converting event to dictionary"""
        timestamp = datetime.now()
        event = Event(
            event_id="test_123",
            timestamp=timestamp,
            event_type="test_event",
            source="test_source",
            data={"key": "value"}
        )
        
        result = event.to_dict()
        
        assert result["event_id"] == "test_123"
        assert result["timestamp"] == timestamp.isoformat()
        assert result["event_type"] == "test_event"
        assert result["source"] == "test_source"
        assert result["data"] == {"key": "value"}
        
    def test_event_to_json(self):
        """Test converting event to JSON string"""
        event = Event(
            event_id="test_123",
            timestamp=datetime.now(),
            event_type="test_event",
            source="test_source",
            data={"key": "value"}
        )
        
        json_str = event.to_json()
        
        assert isinstance(json_str, str)
        assert "test_123" in json_str
        assert "test_event" in json_str


class TestEvents:
    """Test suite for Events system"""
    
    @pytest.fixture
    def events(self):
        """Create an Events instance for testing"""
        return Events(store_history=True)
        
    @pytest.fixture
    def events_no_history(self):
        """Create an Events instance without history"""
        return Events(store_history=False)
        
    def test_initialization(self, events):
        """Test Events system initialization"""
        assert events.subscribers == {}
        assert events.store_history is True
        assert events.history == []
        assert events._event_counter == 0
        
    def test_subscribe(self, events):
        """Test subscribing to events"""
        handler = Mock()
        
        events.subscribe("test_event", handler)
        
        assert "test_event" in events.subscribers
        assert handler in events.subscribers["test_event"]
        
    def test_subscribe_multiple_handlers(self, events):
        """Test subscribing multiple handlers to same event"""
        handler1 = Mock()
        handler2 = Mock()
        
        events.subscribe("test_event", handler1)
        events.subscribe("test_event", handler2)
        
        assert len(events.subscribers["test_event"]) == 2
        assert handler1 in events.subscribers["test_event"]
        assert handler2 in events.subscribers["test_event"]
        
    def test_unsubscribe(self, events):
        """Test unsubscribing from events"""
        handler1 = Mock()
        handler2 = Mock()
        
        events.subscribe("test_event", handler1)
        events.subscribe("test_event", handler2)
        events.unsubscribe("test_event", handler1)
        
        assert handler1 not in events.subscribers["test_event"]
        assert handler2 in events.subscribers["test_event"]
        
    @pytest.mark.asyncio
    async def test_publish_event(self, events):
        """Test publishing an event"""
        handler = AsyncMock()
        events.subscribe("test_event", handler)
        
        event = await events.publish(
            event_type="test_event",
            source="test",
            data={"message": "hello"}
        )
        
        assert event.event_type == "test_event"
        assert event.source == "test"
        assert event.data == {"message": "hello"}
        
        # Handler should be called with the event
        handler.assert_called_once()
        call_args = handler.call_args[0][0]
        assert call_args.event_type == "test_event"
        assert call_args.data == {"message": "hello"}
        
    @pytest.mark.asyncio
    async def test_publish_to_multiple_handlers(self, events):
        """Test publishing event to multiple handlers"""
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        
        events.subscribe("test_event", handler1)
        events.subscribe("test_event", handler2)
        
        await events.publish("test_event", "test", {"data": "value"})
        
        assert handler1.called
        assert handler2.called
        
    @pytest.mark.asyncio
    async def test_universal_subscriber(self, events):
        """Test universal subscriber receives all events"""
        universal_handler = AsyncMock()
        specific_handler = AsyncMock()
        
        events.subscribe("*", universal_handler)
        events.subscribe("specific_event", specific_handler)
        
        # Publish different event types
        await events.publish("specific_event", "test", {"type": "specific"})
        await events.publish("other_event", "test", {"type": "other"})
        
        # Universal handler should receive both
        assert universal_handler.call_count == 2
        
        # Specific handler should receive only one
        assert specific_handler.call_count == 1
        
    @pytest.mark.asyncio
    async def test_handler_error_isolation(self, events):
        """Test that one handler error doesn't affect others"""
        error_handler = AsyncMock(side_effect=Exception("Handler error"))
        good_handler = AsyncMock()
        
        events.subscribe("test_event", error_handler)
        events.subscribe("test_event", good_handler)
        
        # Should not raise exception
        await events.publish("test_event", "test", {})
        
        # Good handler should still be called
        assert good_handler.called
        
    def test_event_history(self, events):
        """Test event history storage"""
        async def run_test():
            await events.publish("event1", "source1", {"data": 1})
            await events.publish("event2", "source2", {"data": 2})
            
        asyncio.run(run_test())
        
        assert len(events.history) == 2
        assert events.history[0].event_type == "event1"
        assert events.history[1].event_type == "event2"
        
    def test_no_history_storage(self, events_no_history):
        """Test events without history storage"""
        async def run_test():
            await events_no_history.publish("event1", "source1", {})
            
        asyncio.run(run_test())
        
        assert len(events_no_history.history) == 0
        
    def test_history_limit(self, events):
        """Test that history is limited to prevent memory issues"""
        async def run_test():
            # Publish more than 1000 events
            for i in range(1100):
                await events.publish(f"event_{i}", "test", {"index": i})
                
        asyncio.run(run_test())
        
        # Should only keep last 1000
        assert len(events.history) == 1000
        # First event should be event_100
        assert events.history[0].data["index"] == 100
        
    def test_get_history_filtering(self, events):
        """Test getting filtered event history"""
        async def run_test():
            await events.publish("type1", "source1", {"data": 1})
            await events.publish("type2", "source1", {"data": 2})
            await events.publish("type1", "source2", {"data": 3})
            
        asyncio.run(run_test())
        
        # Filter by event type
        type1_events = events.get_history(event_type="type1")
        assert len(type1_events) == 2
        
        # Filter by source
        source1_events = events.get_history(source="source1")
        assert len(source1_events) == 2
        
        # Filter by both
        filtered = events.get_history(event_type="type1", source="source1")
        assert len(filtered) == 1
        assert filtered[0].data["data"] == 1
        
    def test_clear_history(self, events):
        """Test clearing event history"""
        async def run_test():
            await events.publish("event1", "test", {})
            await events.publish("event2", "test", {})
            
        asyncio.run(run_test())
        
        assert len(events.history) > 0
        
        events.clear_history()
        
        assert len(events.history) == 0
        
    @pytest.mark.asyncio
    async def test_wait_for_event(self, events):
        """Test waiting for a specific event"""
        # Schedule event publication after delay
        async def publish_later():
            await asyncio.sleep(0.1)
            await events.publish("awaited_event", "test", {"success": True})
            
        # Start waiting and publishing concurrently
        publish_task = asyncio.create_task(publish_later())
        result = await events.wait_for_event("awaited_event", timeout=1.0)
        
        assert result is not None
        assert result.event_type == "awaited_event"
        assert result.data["success"] is True
        
        await publish_task
        
    @pytest.mark.asyncio
    async def test_wait_for_event_timeout(self, events):
        """Test wait_for_event timeout"""
        result = await events.wait_for_event("never_happens", timeout=0.1)
        
        assert result is None
        
    @pytest.mark.asyncio
    async def test_event_metadata(self, events):
        """Test event metadata handling"""
        handler = AsyncMock()
        events.subscribe("meta_event", handler)
        
        await events.publish(
            "meta_event",
            "test",
            {"data": "value"},
            metadata={"confidence": 0.95, "source_version": "1.0"}
        )
        
        call_args = handler.call_args[0][0]
        assert call_args.metadata["confidence"] == 0.95
        assert call_args.metadata["source_version"] == "1.0"


class TestEventTypes:
    """Test suite for EventTypes constants"""
    
    def test_event_types_defined(self):
        """Test that all event types are defined"""
        # Task events
        assert EventTypes.TASK_REQUESTED == "task_requested"
        assert EventTypes.TASK_ASSIGNED == "task_assigned"
        assert EventTypes.TASK_COMPLETED == "task_completed"
        
        # Agent events
        assert EventTypes.AGENT_REGISTERED == "agent_registered"
        
        # Context events
        assert EventTypes.CONTEXT_UPDATED == "context_updated"
        assert EventTypes.DEPENDENCY_DETECTED == "dependency_detected"