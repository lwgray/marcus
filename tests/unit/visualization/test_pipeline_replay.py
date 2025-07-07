"""
Unit tests for Pipeline Replay functionality
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.visualization.pipeline_replay import PipelineReplayController


class TestPipelineReplayController:
    """Test suite for PipelineReplayController"""
    
    @pytest.fixture
    def mock_shared_events(self):
        """Create mock for SharedPipelineEvents"""
        mock = Mock()
        mock.get_flow_events.return_value = [
            {
                "event_id": "1",
                "timestamp": "2024-01-01T10:00:00",
                "event_type": "pipeline_started",
                "stage": "initialization",
                "data": {"project_name": "Test Project"}
            },
            {
                "event_id": "2",
                "timestamp": "2024-01-01T10:01:00",
                "event_type": "ai_prd_analysis",
                "stage": "analysis",
                "data": {"confidence": 0.85}
            },
            {
                "event_id": "3",
                "timestamp": "2024-01-01T10:02:00",
                "event_type": "tasks_generated",
                "stage": "generation",
                "data": {"task_count": 10}
            }
        ]
        return mock
    
    @patch('src.visualization.pipeline_replay.SharedPipelineEvents')
    def test_initialization(self, mock_events_class, mock_shared_events):
        """Test replay controller initialization"""
        mock_events_class.return_value = mock_shared_events
        
        controller = PipelineReplayController("test-flow-123")
        
        assert controller.flow_id == "test-flow-123"
        assert controller.current_position == 0
        assert controller.max_position == 3
        assert len(controller.events) == 3
        mock_shared_events.get_flow_events.assert_called_once_with("test-flow-123")
    
    @patch('src.visualization.pipeline_replay.SharedPipelineEvents')
    def test_step_forward(self, mock_events_class, mock_shared_events):
        """Test stepping forward through events"""
        mock_events_class.return_value = mock_shared_events
        
        controller = PipelineReplayController("test-flow-123")
        
        # First step
        success, state = controller.step_forward()
        assert success is True
        assert controller.current_position == 1
        assert state["current_event"]["event_id"] == "2"
        assert len(state["events_so_far"]) == 2
        
        # Second step
        success, state = controller.step_forward()
        assert success is True
        assert controller.current_position == 2
        assert state["current_event"]["event_id"] == "3"
        
        # Try to step beyond end
        success, state = controller.step_forward()
        assert success is False
        assert controller.current_position == 2
    
    @patch('src.visualization.pipeline_replay.SharedPipelineEvents')
    def test_step_backward(self, mock_events_class, mock_shared_events):
        """Test stepping backward through events"""
        mock_events_class.return_value = mock_shared_events
        
        controller = PipelineReplayController("test-flow-123")
        controller.current_position = 2
        
        # Step backward
        success, state = controller.step_backward()
        assert success is True
        assert controller.current_position == 1
        assert state["current_event"]["event_id"] == "2"
        
        # Step backward again
        success, state = controller.step_backward()
        assert success is True
        assert controller.current_position == 0
        
        # Try to step before beginning
        success, state = controller.step_backward()
        assert success is False
        assert controller.current_position == 0
    
    @patch('src.visualization.pipeline_replay.SharedPipelineEvents')
    def test_jump_to_position(self, mock_events_class, mock_shared_events):
        """Test jumping to specific position"""
        mock_events_class.return_value = mock_shared_events
        
        controller = PipelineReplayController("test-flow-123")
        
        # Valid jump
        success, state = controller.jump_to_position(2)
        assert success is True
        assert controller.current_position == 2
        assert state["current_event"]["event_id"] == "3"
        
        # Invalid jump (negative)
        success, state = controller.jump_to_position(-1)
        assert success is False
        assert controller.current_position == 2
        
        # Invalid jump (beyond end)
        success, state = controller.jump_to_position(5)
        assert success is False
        assert controller.current_position == 2
    
    @patch('src.visualization.pipeline_replay.SharedPipelineEvents')
    def test_get_current_state(self, mock_events_class, mock_shared_events):
        """Test getting current replay state"""
        mock_events_class.return_value = mock_shared_events
        
        controller = PipelineReplayController("test-flow-123")
        
        state = controller.get_current_state()
        assert state["position"] == 0
        assert state["total_events"] == 3
        assert state["current_event"]["event_id"] == "1"
        assert len(state["events_so_far"]) == 1
        assert state["timeline"]["start"] == "2024-01-01T10:00:00"
        assert state["timeline"]["current"] == "2024-01-01T10:00:00"
        assert state["timeline"]["end"] == "2024-01-01T10:02:00"
    
    @patch('src.visualization.pipeline_replay.SharedPipelineEvents')
    def test_empty_events(self, mock_events_class):
        """Test handling empty event list"""
        mock_shared = Mock()
        mock_shared.get_flow_events.return_value = []
        mock_events_class.return_value = mock_shared
        
        controller = PipelineReplayController("empty-flow")
        
        assert controller.max_position == 0
        assert controller.current_position == 0
        
        state = controller.get_current_state()
        assert state["current_event"] is None
        assert len(state["events_so_far"]) == 0
    
    @patch('src.visualization.pipeline_replay.SharedPipelineEvents')
    def test_state_accumulation(self, mock_events_class, mock_shared_events):
        """Test state accumulation as we move through events"""
        mock_events_class.return_value = mock_shared_events
        
        controller = PipelineReplayController("test-flow-123")
        
        # Jump to end
        controller.jump_to_position(2)
        state = controller.get_current_state()
        
        # Check accumulated state
        accumulated = state["accumulated_state"]
        assert accumulated["total_events"] == 3
        assert accumulated["stages_completed"] == ["initialization", "analysis", "generation"]
        assert accumulated["metrics"]["confidence"] == 0.85
        assert accumulated["metrics"]["task_count"] == 10