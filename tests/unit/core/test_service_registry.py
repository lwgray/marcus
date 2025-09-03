"""
Unit tests for service registry and security fixes.
"""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, mock_open, patch
import pytest
from src.core.service_registry import (
    MarcusServiceRegistry,
    get_service_registry,
    register_marcus_service,
    unregister_marcus_service,
)


class TestServiceRegistrySecurity:
    """Test security improvements in service registry error handling"""

    @patch('src.core.service_registry.psutil.pid_exists')
    def test_discover_services_handles_file_removal_errors_gracefully(self, mock_pid_exists):
        """Test that discover_services handles file removal errors gracefully"""
        mock_pid_exists.return_value = False  # Process not running
        
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_dir = Path(temp_dir) / ".marcus" / "services"
            registry_dir.mkdir(parents=True)
            
            # Create invalid service file
            invalid_file = registry_dir / "marcus_invalid.json"
            invalid_file.write_text("invalid json content")
            
            registry = MarcusServiceRegistry()
            registry.registry_dir = registry_dir
            
            # Mock unlink to raise PermissionError
            with patch.object(Path, 'unlink') as mock_unlink:
                mock_unlink.side_effect = PermissionError("Permission denied")
                
                # Should handle the error gracefully and return empty list
                with patch('src.core.service_registry.logging') as mock_logging:
                    mock_logger = Mock()
                    mock_logging.getLogger.return_value = mock_logger
                    
                    services = registry.discover_services()
                    assert services == []
                    
                    # Verify error was logged
                    mock_logger.debug.assert_called()
                    debug_call_args = mock_logger.debug.call_args[0][0]
                    assert "Could not remove invalid service file" in debug_call_args

    @patch('src.core.service_registry.psutil.pid_exists')
    def test_discover_services_handles_unexpected_errors_with_warning(self, mock_pid_exists):
        """Test that discover_services handles unexpected errors with warning log"""
        mock_pid_exists.return_value = False
        
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_dir = Path(temp_dir) / ".marcus" / "services"
            registry_dir.mkdir(parents=True)
            
            # Create invalid service file
            invalid_file = registry_dir / "marcus_invalid.json"
            invalid_file.write_text("invalid json content")
            
            registry = MarcusServiceRegistry()
            registry.registry_dir = registry_dir
            
            # Mock unlink to raise unexpected error
            with patch.object(Path, 'unlink') as mock_unlink:
                mock_unlink.side_effect = RuntimeError("Unexpected error")
                
                with patch('src.core.service_registry.logging') as mock_logging:
                    mock_logger = Mock()
                    mock_logging.getLogger.return_value = mock_logger
                    
                    services = registry.discover_services()
                    assert services == []
                    
                    # Verify warning was logged for unexpected error
                    mock_logger.warning.assert_called()
                    warning_call_args = mock_logger.warning.call_args[0][0]
                    assert "Unexpected error removing service file" in warning_call_args

    @patch('src.core.service_registry.psutil.pid_exists')
    def test_discover_services_continues_after_file_errors(self, mock_pid_exists):
        """Test that discover_services continues processing after file errors"""
        mock_pid_exists.return_value = True  # Simulate running process
        
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_dir = Path(temp_dir) / ".marcus" / "services"
            registry_dir.mkdir(parents=True)
            
            # Create one invalid file and one valid file
            invalid_file = registry_dir / "marcus_invalid.json"
            invalid_file.write_text("invalid json")
            
            valid_file = registry_dir / "marcus_valid.json"
            valid_service = {
                "instance_id": "marcus_valid",
                "pid": 12345,
                "status": "running",
                "started_at": "2023-01-01T00:00:00"
            }
            valid_file.write_text(json.dumps(valid_service))
            
            registry = MarcusServiceRegistry()
            registry.registry_dir = registry_dir
            
            # Mock unlink to raise error for invalid file cleanup
            original_unlink = Path.unlink
            def mock_unlink(self, *args, **kwargs):
                if "invalid" in str(self):
                    raise OSError("Cannot delete invalid file")
                # Call original unlink for other files
                return original_unlink(self, *args, **kwargs)
            
            with patch.object(Path, 'unlink', mock_unlink):
                
                services = registry.discover_services()
                
                # Should return the valid service despite error with invalid file
                assert len(services) == 1
                assert services[0]["instance_id"] == "marcus_valid"


class TestMarcusServiceRegistry:
    """Test basic service registry functionality"""

    def test_registry_initialization(self):
        """Test service registry initializes correctly"""
        registry = MarcusServiceRegistry("test_instance")
        assert registry.instance_id == "test_instance"
        assert registry.registry_file.name == "test_instance.json"

    def test_registry_initialization_with_default_id(self):
        """Test service registry uses PID-based ID by default"""
        with patch('os.getpid', return_value=12345):
            registry = MarcusServiceRegistry()
            assert registry.instance_id == "marcus_12345"

    @patch('platform.system', return_value='Darwin')
    def test_get_registry_dir_unix(self, mock_platform):
        """Test registry directory on Unix-like systems"""
        registry = MarcusServiceRegistry()
        expected_dir = Path.home() / ".marcus" / "services"
        assert registry.registry_dir == expected_dir

    @patch('platform.system', return_value='Windows')
    @patch.dict(os.environ, {'APPDATA': '/test/appdata'})
    def test_get_registry_dir_windows(self, mock_platform):
        """Test registry directory on Windows"""
        registry = MarcusServiceRegistry()
        expected_dir = Path("/test/appdata") / ".marcus" / "services"
        assert registry.registry_dir == expected_dir

    def test_register_service(self):
        """Test service registration creates correct info"""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = MarcusServiceRegistry("test_service")
            registry.registry_dir = Path(temp_dir)
            registry.registry_file = Path(temp_dir) / "test_service.json"
            
            service_info = registry.register_service(
                mcp_command="test_command",
                log_dir="/test/logs",
                project_name="test_project"
            )
            
            # Verify service info contains expected fields
            assert service_info["instance_id"] == "test_service"
            assert service_info["mcp_command"] == "test_command"
            assert service_info["log_dir"] == "/test/logs"
            assert service_info["project_name"] == "test_project"
            assert service_info["status"] == "running"
            assert "started_at" in service_info
            assert "last_heartbeat" in service_info
            
            # Verify file was created
            assert registry.registry_file.exists()
            
            # Verify file content
            with open(registry.registry_file) as f:
                saved_info = json.load(f)
            assert saved_info == service_info

    def test_update_heartbeat(self):
        """Test heartbeat update functionality"""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = MarcusServiceRegistry("test_service")
            registry.registry_dir = Path(temp_dir)
            registry.registry_file = Path(temp_dir) / "test_service.json"
            
            # First register a service
            original_info = registry.register_service(
                mcp_command="test_command",
                log_dir="/test/logs"
            )
            original_heartbeat = original_info["last_heartbeat"]
            
            # Update heartbeat with additional info
            registry.update_heartbeat(task_count=5, status="busy")
            
            # Verify updated info
            with open(registry.registry_file) as f:
                updated_info = json.load(f)
            
            assert updated_info["last_heartbeat"] != original_heartbeat
            assert updated_info["task_count"] == 5
            assert updated_info["status"] == "busy"

    def test_update_heartbeat_nonexistent_file(self):
        """Test heartbeat update handles nonexistent file gracefully"""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = MarcusServiceRegistry("test_service")
            registry.registry_file = Path(temp_dir) / "nonexistent.json"
            
            # Should not raise exception
            registry.update_heartbeat(status="running")

    def test_unregister_service(self):
        """Test service unregistration removes file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = MarcusServiceRegistry("test_service")
            registry.registry_dir = Path(temp_dir)
            registry.registry_file = Path(temp_dir) / "test_service.json"
            
            # Register service first
            registry.register_service(
                mcp_command="test_command",
                log_dir="/test/logs"
            )
            assert registry.registry_file.exists()
            
            # Unregister service
            registry.unregister_service()
            assert not registry.registry_file.exists()

    @patch('src.core.service_registry.psutil.pid_exists')
    def test_is_process_running(self, mock_pid_exists):
        """Test process running check"""
        mock_pid_exists.return_value = True
        assert MarcusServiceRegistry._is_process_running(12345) is True
        
        mock_pid_exists.return_value = False
        assert MarcusServiceRegistry._is_process_running(12345) is False
        
        # Test with None/0 PID
        assert MarcusServiceRegistry._is_process_running(None) is False
        assert MarcusServiceRegistry._is_process_running(0) is False

    @patch('src.core.service_registry.psutil.pid_exists')
    def test_is_process_running_handles_exceptions(self, mock_pid_exists):
        """Test process running check handles psutil exceptions"""
        mock_pid_exists.side_effect = Exception("psutil error")
        assert MarcusServiceRegistry._is_process_running(12345) is False


class TestGlobalServiceRegistry:
    """Test global service registry functions"""

    def test_get_service_registry_creates_singleton(self):
        """Test get_service_registry creates singleton instance"""
        # Clear any existing global instance
        import src.core.service_registry
        src.core.service_registry._service_registry = None
        
        registry1 = get_service_registry("test_id")
        registry2 = get_service_registry("different_id")  # Should use existing
        
        assert registry1 is registry2
        assert registry1.instance_id == "test_id"

    @patch.object(MarcusServiceRegistry, 'register_service')
    def test_register_marcus_service_convenience(self, mock_register):
        """Test register_marcus_service convenience function"""
        mock_register.return_value = {"status": "registered"}
        
        result = register_marcus_service(
            mcp_command="test_command",
            log_dir="/test/logs"
        )
        
        mock_register.assert_called_once_with(
            mcp_command="test_command",
            log_dir="/test/logs"
        )
        assert result == {"status": "registered"}

    @patch.object(MarcusServiceRegistry, 'unregister_service')
    def test_unregister_marcus_service_convenience(self, mock_unregister):
        """Test unregister_marcus_service convenience function"""
        unregister_marcus_service()
        mock_unregister.assert_called_once()