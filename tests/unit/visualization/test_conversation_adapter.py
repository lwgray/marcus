#!/usr/bin/env python3
"""
Unit tests for ConversationAdapter

This module tests the conversation adapter functionality which converts
Marcus events to visualization-compatible conversation logs.
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock, call, ANY
from typing import Dict, Any, List

from src.visualization.conversation_adapter import (
    ConversationAdapter, 
    log_agent_event,
    conversation_adapter
)


class TestConversationAdapter:
    """Test suite for ConversationAdapter class"""

    def test_init_creates_log_directory(self):
        """Test that initialization creates the log directory"""
        with patch('src.visualization.conversation_adapter.Path') as mock_path:
            with patch('src.visualization.conversation_adapter.datetime'):
                mock_path_instance = Mock(spec=Path)
                mock_path_instance.mkdir = Mock()
                mock_path_instance.__truediv__ = Mock(return_value=Mock(spec=Path))
                mock_path.return_value = mock_path_instance
                
                adapter = ConversationAdapter("custom/log/dir")
                
                mock_path.assert_called_once_with("custom/log/dir")
                mock_path_instance.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_init_creates_conversation_file_with_timestamp(self):
        """Test that initialization creates conversation file with timestamp"""
        with patch('src.visualization.conversation_adapter.Path') as mock_path:
            with patch('src.visualization.conversation_adapter.datetime') as mock_datetime:
                mock_now = Mock()
                mock_now.strftime.return_value = "20240101_120000"
                mock_datetime.now.return_value = mock_now
                
                mock_path_instance = Mock(spec=Path)
                mock_file_path = Mock(spec=Path)
                # Properly mock the __truediv__ method
                mock_path_instance.__truediv__ = Mock(return_value=mock_file_path)
                mock_path.return_value = mock_path_instance
                
                adapter = ConversationAdapter()
                
                mock_path_instance.__truediv__.assert_called_once_with("realtime_20240101_120000.jsonl")
                assert adapter.conversation_file == mock_file_path

    def test_log_conversation_event_writes_to_file(self):
        """Test that log_conversation_event writes properly formatted JSON to file"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime') as mock_datetime:
                mock_now = Mock()
                mock_now.strftime.return_value = "20240101_120000"
                mock_now.isoformat.return_value = "2024-01-01T12:00:00"
                mock_datetime.now.return_value = mock_now
                
                adapter = ConversationAdapter()
                
                captured = []
                mock_file = mock_open()
                
                with patch('builtins.open', mock_file):
                    with patch('json.dump', side_effect=lambda d, f: captured.append(d)):
                        adapter.log_conversation_event(
                            source="worker1",
                            target="marcus",
                            message="Test message",
                            event_type="test_event",
                            metadata={"key": "value"}
                        )
                        
                        # Verify file was opened in append mode
                        mock_file.assert_called_once_with(adapter.conversation_file, 'a')
                        
                        # Check the captured JSON data
                        assert len(captured) == 1
                        json_data = captured[0]
                        
                        assert json_data["timestamp"] == "2024-01-01T12:00:00"
                        assert json_data["event"] == "test_event"
                        assert json_data["source"] == "worker1"
                        assert json_data["target"] == "marcus"
                        assert json_data["message"] == "Test message"
                        assert json_data["metadata"] == {"key": "value"}
                        assert json_data["conversation_type"] == "worker_to_pm"
                        
                        # Check newline was written
                        handle = mock_file()
                        handle.write.assert_called_with('\n')
                        
                        # Check flush was called
                        handle.flush.assert_called_once()

    def test_log_conversation_event_with_empty_metadata(self):
        """Test log_conversation_event with no metadata provided"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                
                captured = []
                with patch('builtins.open', mock_open()):
                    with patch('json.dump', side_effect=lambda d, f: captured.append(d)):
                        adapter.log_conversation_event(
                            source="marcus",
                            target="worker1",
                            message="Test message"
                        )
                        
                        json_data = captured[0]
                        assert json_data["metadata"] == {}
                        assert json_data["event"] == "message"  # Default event type

    def test_determine_conversation_type_worker_to_pm(self):
        """Test conversation type detection for worker to PM"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                assert adapter._determine_conversation_type("worker1", "marcus") == "worker_to_pm"
                assert adapter._determine_conversation_type("worker_123", "marcus") == "worker_to_pm"

    def test_determine_conversation_type_pm_to_worker(self):
        """Test conversation type detection for PM to worker"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                assert adapter._determine_conversation_type("marcus", "worker1") == "pm_to_worker"
                assert adapter._determine_conversation_type("marcus", "worker_abc") == "pm_to_worker"

    def test_determine_conversation_type_pm_to_kanban(self):
        """Test conversation type detection for PM to Kanban"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                assert adapter._determine_conversation_type("marcus", "kanban_board") == "pm_to_kanban"

    def test_determine_conversation_type_kanban_to_pm(self):
        """Test conversation type detection for Kanban to PM"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                assert adapter._determine_conversation_type("kanban_board", "marcus") == "kanban_to_pm"

    def test_determine_conversation_type_system_event(self):
        """Test conversation type detection for system events"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                assert adapter._determine_conversation_type("system", "marcus") == "system_event"
                assert adapter._determine_conversation_type("unknown", "unknown") == "system_event"
                assert adapter._determine_conversation_type("service1", "service2") == "system_event"

    def test_convert_worker_registration_complete(self):
        """Test worker registration conversion with all fields"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                
                captured = []
                with patch('builtins.open', mock_open()):
                    with patch('json.dump', side_effect=lambda d, f: captured.append(d)):
                        event_data = {
                            "worker_id": "worker1",
                            "name": "Test Worker",
                            "skills": ["python", "testing"],
                            "role": "developer"
                        }
                        
                        adapter.convert_worker_registration(event_data)
                        
                        # Should capture two events
                        assert len(captured) == 2
                        
                        # First event - worker registration
                        json_data1 = captured[0]
                        assert json_data1["source"] == "worker1"
                        assert json_data1["target"] == "marcus"
                        assert json_data1["message"] == "Worker Test Worker registering with skills: python, testing"
                        assert json_data1["event"] == "worker_registration"
                        assert json_data1["metadata"]["capabilities"] == ["python", "testing"]
                        assert json_data1["metadata"]["role"] == "developer"
                        
                        # Second event - acknowledgment
                        json_data2 = captured[1]
                        assert json_data2["source"] == "marcus"
                        assert json_data2["target"] == "worker1"
                        assert json_data2["message"] == "Registration confirmed for Test Worker"
                        assert json_data2["event"] == "registration_ack"
                        assert json_data2["metadata"]["status"] == "registered"

    def test_convert_worker_registration_minimal(self):
        """Test worker registration conversion with minimal fields"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                
                captured = []
                with patch('builtins.open', mock_open()):
                    with patch('json.dump', side_effect=lambda d, f: captured.append(d)):
                        event_data = {}
                        
                        adapter.convert_worker_registration(event_data)
                        
                        # First event with defaults
                        json_data1 = captured[0]
                        assert json_data1["source"] == "unknown_worker"
                        assert json_data1["message"] == "Worker unknown_worker registering with skills: "
                        assert json_data1["metadata"]["capabilities"] == []
                        assert json_data1["metadata"]["role"] == "worker"

    def test_convert_task_request(self):
        """Test task request conversion"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                
                captured = []
                with patch('builtins.open', mock_open()):
                    with patch('json.dump', side_effect=lambda d, f: captured.append(d)):
                        event_data = {"worker_id": "worker1"}
                        
                        adapter.convert_task_request(event_data)
                        
                        json_data = captured[0]
                        assert json_data["source"] == "worker1"
                        assert json_data["target"] == "marcus"
                        assert json_data["message"] == "Requesting next available task"
                        assert json_data["event"] == "task_request"

    def test_convert_task_request_no_worker_id(self):
        """Test task request conversion without worker ID"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                
                captured = []
                with patch('builtins.open', mock_open()):
                    with patch('json.dump', side_effect=lambda d, f: captured.append(d)):
                        event_data = {}
                        
                        adapter.convert_task_request(event_data)
                        
                        json_data = captured[0]
                        assert json_data["source"] == "unknown_worker"

    def test_convert_task_assignment_complete(self):
        """Test task assignment conversion with all fields"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                
                captured = []
                with patch('builtins.open', mock_open()):
                    with patch('json.dump', side_effect=lambda d, f: captured.append(d)):
                        task_data = {
                            "name": "Implement feature X",
                            "id": "task123",
                            "priority": "high",
                            "estimated_hours": 8
                        }
                        
                        adapter.convert_task_assignment("worker1", task_data)
                        
                        # Should capture two events
                        assert len(captured) == 2
                        
                        # First event - task assignment
                        json_data1 = captured[0]
                        assert json_data1["source"] == "marcus"
                        assert json_data1["target"] == "worker1"
                        assert json_data1["message"] == "Assigned task: Implement feature X"
                        assert json_data1["event"] == "task_assignment"
                        assert json_data1["metadata"]["task_id"] == "task123"
                        assert json_data1["metadata"]["priority"] == "high"
                        assert json_data1["metadata"]["estimated_hours"] == 8
                        
                        # Second event - kanban update
                        json_data2 = captured[1]
                        assert json_data2["source"] == "marcus"
                        assert json_data2["target"] == "kanban_board"
                        assert json_data2["message"] == "Moving task Implement feature X to In Progress"
                        assert json_data2["event"] == "kanban_interaction"
                        assert json_data2["metadata"]["task_id"] == "task123"
                        assert json_data2["metadata"]["from_status"] == "todo"
                        assert json_data2["metadata"]["to_status"] == "in_progress"
                        assert json_data2["metadata"]["assigned_to"] == "worker1"

    def test_convert_task_assignment_minimal(self):
        """Test task assignment conversion with minimal fields"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                
                captured = []
                with patch('builtins.open', mock_open()):
                    with patch('json.dump', side_effect=lambda d, f: captured.append(d)):
                        task_data = {}
                        
                        adapter.convert_task_assignment("worker1", task_data)
                        
                        json_data1 = captured[0]
                        assert json_data1["message"] == "Assigned task: Unknown Task"
                        assert json_data1["metadata"]["task_id"] == "unknown"
                        assert json_data1["metadata"]["priority"] == "medium"
                        assert json_data1["metadata"]["estimated_hours"] == 0

    def test_convert_progress_update_in_progress(self):
        """Test progress update conversion for in-progress task"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                
                captured = []
                with patch('builtins.open', mock_open()):
                    with patch('json.dump', side_effect=lambda d, f: captured.append(d)):
                        event_data = {
                            "agent_id": "worker1",
                            "task_id": "task123",
                            "status": "in_progress",
                            "progress": 50,
                            "message": "Halfway done"
                        }
                        
                        adapter.convert_progress_update(event_data)
                        
                        # Should only capture one event (no kanban update for in_progress)
                        assert len(captured) == 1
                        
                        json_data = captured[0]
                        assert json_data["source"] == "worker1"
                        assert json_data["target"] == "marcus"
                        assert json_data["message"] == "Task progress: 50% - Halfway done"
                        assert json_data["event"] == "progress_update"
                        assert json_data["metadata"]["task_id"] == "task123"
                        assert json_data["metadata"]["status"] == "in_progress"
                        assert json_data["metadata"]["progress"] == 50

    def test_convert_progress_update_completed(self):
        """Test progress update conversion for completed task"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                
                captured = []
                with patch('builtins.open', mock_open()):
                    with patch('json.dump', side_effect=lambda d, f: captured.append(d)):
                        event_data = {
                            "agent_id": "worker1",
                            "task_id": "task123",
                            "status": "completed",
                            "progress": 100,
                            "message": "Task completed"
                        }
                        
                        adapter.convert_progress_update(event_data)
                        
                        # Should capture two events
                        assert len(captured) == 2
                        
                        # Second event - kanban update
                        json_data2 = captured[1]
                        assert json_data2["source"] == "marcus"
                        assert json_data2["target"] == "kanban_board"
                        assert json_data2["message"] == "Moving task task123 to Done"
                        assert json_data2["event"] == "kanban_interaction"
                        assert json_data2["metadata"]["from_status"] == "in_progress"
                        assert json_data2["metadata"]["to_status"] == "done"

    def test_convert_progress_update_minimal(self):
        """Test progress update conversion with minimal fields"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                
                captured = []
                with patch('builtins.open', mock_open()):
                    with patch('json.dump', side_effect=lambda d, f: captured.append(d)):
                        event_data = {}
                        
                        adapter.convert_progress_update(event_data)
                        
                        json_data = captured[0]
                        assert json_data["source"] == "unknown_worker"
                        assert json_data["message"] == "Task progress: 0% - Progress update"
                        assert json_data["metadata"]["task_id"] == "unknown"
                        assert json_data["metadata"]["status"] == "unknown"
                        assert json_data["metadata"]["progress"] == 0

    def test_convert_ping_complete(self):
        """Test ping conversion with all fields"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                
                captured = []
                with patch('builtins.open', mock_open()):
                    with patch('json.dump', side_effect=lambda d, f: captured.append(d)):
                        event_data = {
                            "echo": "test-echo",
                            "source": "monitoring"
                        }
                        
                        adapter.convert_ping(event_data)
                        
                        # Should capture two events
                        assert len(captured) == 2
                        
                        # First event - ping
                        json_data1 = captured[0]
                        assert json_data1["source"] == "monitoring"
                        assert json_data1["target"] == "marcus"
                        assert json_data1["message"] == "Ping: test-echo"
                        assert json_data1["event"] == "ping"
                        assert json_data1["metadata"]["echo"] == "test-echo"
                        
                        # Second event - pong
                        json_data2 = captured[1]
                        assert json_data2["source"] == "marcus"
                        assert json_data2["target"] == "monitoring"
                        assert json_data2["message"] == "Pong: test-echo"
                        assert json_data2["event"] == "ping_response"
                        assert json_data2["metadata"]["echo"] == "test-echo"
                        assert json_data2["metadata"]["status"] == "online"

    def test_convert_ping_minimal(self):
        """Test ping conversion with minimal fields"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                
                captured = []
                with patch('builtins.open', mock_open()):
                    with patch('json.dump', side_effect=lambda d, f: captured.append(d)):
                        event_data = {}
                        
                        adapter.convert_ping(event_data)
                        
                        json_data1 = captured[0]
                        assert json_data1["source"] == "system"
                        assert json_data1["message"] == "Ping: ping"
                        assert json_data1["metadata"]["echo"] == "ping"


class TestLogAgentEvent:
    """Test suite for the log_agent_event function"""

    @patch('src.visualization.conversation_adapter.conversation_adapter')
    def test_log_agent_event_worker_registration(self, mock_adapter):
        """Test log_agent_event routes worker registration correctly"""
        event_data = {"worker_id": "worker1"}
        
        log_agent_event("worker_registration", event_data)
        
        mock_adapter.convert_worker_registration.assert_called_once_with(event_data)

    @patch('src.visualization.conversation_adapter.conversation_adapter')
    def test_log_agent_event_task_request(self, mock_adapter):
        """Test log_agent_event routes task request correctly"""
        event_data = {"worker_id": "worker1"}
        
        log_agent_event("task_request", event_data)
        
        mock_adapter.convert_task_request.assert_called_once_with(event_data)

    @patch('src.visualization.conversation_adapter.conversation_adapter')
    def test_log_agent_event_task_assignment(self, mock_adapter):
        """Test log_agent_event routes task assignment correctly"""
        event_data = {
            "worker_id": "worker1",
            "task": {"name": "Test Task"}
        }
        
        log_agent_event("task_assignment", event_data)
        
        mock_adapter.convert_task_assignment.assert_called_once_with(
            "worker1", 
            {"name": "Test Task"}
        )

    @patch('src.visualization.conversation_adapter.conversation_adapter')
    def test_log_agent_event_task_assignment_no_worker_id(self, mock_adapter):
        """Test log_agent_event handles missing worker_id in task assignment"""
        event_data = {"task": {"name": "Test Task"}}
        
        log_agent_event("task_assignment", event_data)
        
        mock_adapter.convert_task_assignment.assert_not_called()

    @patch('src.visualization.conversation_adapter.conversation_adapter')
    def test_log_agent_event_task_assignment_no_task_data(self, mock_adapter):
        """Test log_agent_event handles missing task data in assignment"""
        event_data = {"worker_id": "worker1"}
        
        log_agent_event("task_assignment", event_data)
        
        mock_adapter.convert_task_assignment.assert_called_once_with("worker1", {})

    @patch('src.visualization.conversation_adapter.conversation_adapter')
    def test_log_agent_event_progress_update(self, mock_adapter):
        """Test log_agent_event routes progress update correctly"""
        event_data = {"agent_id": "worker1", "progress": 50}
        
        log_agent_event("progress_update", event_data)
        
        mock_adapter.convert_progress_update.assert_called_once_with(event_data)

    @patch('src.visualization.conversation_adapter.conversation_adapter')
    def test_log_agent_event_ping_request(self, mock_adapter):
        """Test log_agent_event routes ping request correctly"""
        event_data = {"echo": "test"}
        
        log_agent_event("ping_request", event_data)
        
        mock_adapter.convert_ping.assert_called_once_with(event_data)

    @patch('src.visualization.conversation_adapter.conversation_adapter')
    def test_log_agent_event_unknown_type(self, mock_adapter):
        """Test log_agent_event ignores unknown event types"""
        event_data = {"data": "test"}
        
        log_agent_event("unknown_event", event_data)
        
        # No methods should be called
        mock_adapter.convert_worker_registration.assert_not_called()
        mock_adapter.convert_task_request.assert_not_called()
        mock_adapter.convert_task_assignment.assert_not_called()
        mock_adapter.convert_progress_update.assert_not_called()
        mock_adapter.convert_ping.assert_not_called()


class TestGlobalConversationAdapter:
    """Test suite for the global conversation_adapter instance"""

    def test_global_adapter_is_conversation_adapter_instance(self):
        """Test that conversation_adapter is an instance of ConversationAdapter"""
        from src.visualization.conversation_adapter import conversation_adapter, ConversationAdapter
        assert isinstance(conversation_adapter, ConversationAdapter)


class TestEdgeCasesAndErrorHandling:
    """Test suite for edge cases and error scenarios"""

    def test_log_conversation_event_handles_file_write_error(self):
        """Test that file write errors propagate correctly"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                
                with patch('builtins.open', side_effect=IOError("Disk full")):
                    with pytest.raises(IOError, match="Disk full"):
                        adapter.log_conversation_event("source", "target", "message")

    def test_log_conversation_event_handles_json_serialization_error(self):
        """Test handling of non-serializable metadata"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                
                # Create a non-serializable object
                class NonSerializable:
                    pass
                
                with patch('builtins.open', mock_open()):
                    with patch('json.dump', side_effect=TypeError("Object not serializable")):
                        with pytest.raises(TypeError, match="Object not serializable"):
                            adapter.log_conversation_event(
                                source="worker1",
                                target="marcus",
                                message="Test",
                                metadata={"bad": NonSerializable()}
                            )

    def test_convert_worker_registration_empty_skills_list(self):
        """Test worker registration with empty skills list"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                
                captured = []
                with patch('builtins.open', mock_open()):
                    with patch('json.dump', side_effect=lambda d, f: captured.append(d)):
                        event_data = {
                            "worker_id": "worker1",
                            "name": "Test Worker",
                            "skills": []
                        }
                        
                        adapter.convert_worker_registration(event_data)
                        
                        json_data = captured[0]
                        assert json_data["message"] == "Worker Test Worker registering with skills: "

    def test_convert_progress_update_zero_progress(self):
        """Test progress update with zero progress"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                
                captured = []
                with patch('builtins.open', mock_open()):
                    with patch('json.dump', side_effect=lambda d, f: captured.append(d)):
                        event_data = {
                            "agent_id": "worker1",
                            "task_id": "task123",
                            "status": "in_progress",
                            "progress": 0,
                            "message": "Just started"
                        }
                        
                        adapter.convert_progress_update(event_data)
                        
                        json_data = captured[0]
                        assert json_data["message"] == "Task progress: 0% - Just started"
                        assert json_data["metadata"]["progress"] == 0

    def test_determine_conversation_type_case_sensitivity(self):
        """Test that conversation type detection is case sensitive"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                
                # These should be system events due to case mismatch
                assert adapter._determine_conversation_type("Worker1", "marcus") == "system_event"
                assert adapter._determine_conversation_type("MARCUS", "worker1") == "system_event"
                assert adapter._determine_conversation_type("marcus", "Kanban_Board") == "system_event"

    def test_multiple_consecutive_writes(self):
        """Test multiple consecutive event logs"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                
                captured = []
                with patch('builtins.open', mock_open()) as mock_file:
                    with patch('json.dump', side_effect=lambda d, f: captured.append(d)):
                        # Log multiple events
                        for i in range(3):
                            adapter.log_conversation_event(
                                source=f"worker{i}",
                                target="marcus",
                                message=f"Message {i}"
                            )
                        
                        # Should open file 3 times (once per event)
                        assert mock_file.call_count == 3
                        
                        # Each call should be in append mode
                        for call in mock_file.call_args_list:
                            assert call[0] == (adapter.conversation_file, 'a')
                        
                        # Should have captured 3 JSON objects
                        assert len(captured) == 3
                        for i, json_data in enumerate(captured):
                            assert json_data["source"] == f"worker{i}"
                            assert json_data["message"] == f"Message {i}"

    def test_convert_worker_registration_with_special_characters(self):
        """Test worker registration with special characters in data"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                
                captured = []
                with patch('builtins.open', mock_open()):
                    with patch('json.dump', side_effect=lambda d, f: captured.append(d)):
                        event_data = {
                            "worker_id": "worker-1",
                            "name": "Test \"Worker\" <1>",
                            "skills": ["python/django", "node.js", "C++"],
                            "role": "full-stack developer"
                        }
                        
                        adapter.convert_worker_registration(event_data)
                        
                        json_data = captured[0]
                        assert json_data["source"] == "worker-1"
                        assert "Test \"Worker\" <1>" in json_data["message"]
                        assert json_data["metadata"]["capabilities"] == ["python/django", "node.js", "C++"]

    def test_convert_task_assignment_with_long_task_name(self):
        """Test task assignment with very long task name"""
        with patch('src.visualization.conversation_adapter.Path'):
            with patch('src.visualization.conversation_adapter.datetime'):
                adapter = ConversationAdapter()
                
                captured = []
                with patch('builtins.open', mock_open()):
                    with patch('json.dump', side_effect=lambda d, f: captured.append(d)):
                        long_name = "Implement " + "very " * 50 + "long feature"
                        task_data = {
                            "name": long_name,
                            "id": "task123"
                        }
                        
                        adapter.convert_task_assignment("worker1", task_data)
                        
                        json_data = captured[0]
                        assert json_data["message"] == f"Assigned task: {long_name}"

    def test_conversation_file_path_handling(self):
        """Test that conversation file path is properly constructed"""
        with patch('src.visualization.conversation_adapter.Path') as mock_path:
            with patch('src.visualization.conversation_adapter.datetime') as mock_datetime:
                mock_now = Mock()
                mock_now.strftime.return_value = "20240101_120000"
                mock_datetime.now.return_value = mock_now
                
                # Test with custom directory
                mock_path_instance = Mock(spec=Path)
                mock_path_instance.mkdir = Mock()
                mock_file = Mock(spec=Path)
                # Properly mock the __truediv__ method
                mock_path_instance.__truediv__ = Mock(return_value=mock_file)
                mock_path.return_value = mock_path_instance
                
                adapter = ConversationAdapter("/custom/path")
                
                mock_path.assert_called_once_with("/custom/path")
                mock_path_instance.__truediv__.assert_called_once_with("realtime_20240101_120000.jsonl")