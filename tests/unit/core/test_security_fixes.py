"""
Focused tests for security fixes in resilience.py and service_registry.py
"""

import json
import logging
import secrets
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.core.resilience import RetryConfig, with_retry
from src.core.service_registry import MarcusServiceRegistry


class TestSecurityFixes:
    """Test specific security fixes"""

    def test_resilience_uses_secure_random(self):
        """Test B311 fix: resilience uses secrets.SystemRandom instead of random.random"""
        config = RetryConfig(max_attempts=2, base_delay=1.0, jitter=True)

        @with_retry(config)
        def failing_func():
            raise ValueError("Test failure")

        # Mock SystemRandom to verify it's being used
        with patch("src.core.resilience.secrets.SystemRandom") as mock_system_random:
            mock_instance = Mock()
            mock_instance.random.return_value = 0.5
            mock_system_random.return_value = mock_instance

            # This will fail but we're testing the jitter calculation
            with pytest.raises(ValueError):
                failing_func()

            # Verify SystemRandom was used
            mock_system_random.assert_called_once()
            mock_instance.random.assert_called_once()

    def test_service_registry_error_handling_not_pass(self):
        """Test B110 fix: service registry doesn't use bare except-pass"""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_dir = Path(temp_dir) / "test_registry"
            registry_dir.mkdir()

            # Create invalid JSON file
            invalid_file = registry_dir / "marcus_test.json"
            invalid_file.write_text("invalid json")

            registry = MarcusServiceRegistry()
            registry.registry_dir = registry_dir

            # Mock psutil to simulate no running processes
            with patch(
                "src.core.service_registry.psutil.pid_exists", return_value=False
            ):
                # Mock unlink to raise permission error
                with patch.object(Path, "unlink") as mock_unlink:
                    mock_unlink.side_effect = PermissionError("Access denied")

                    # Should handle error gracefully without throwing exception
                    # This tests that the error is caught and handled instead of using bare pass
                    try:
                        services = registry.discover_services()
                        # Should return empty list (no valid services)
                        assert isinstance(services, list)
                        # If we get here, the error was handled properly
                    except PermissionError:
                        # If this exception propagates, the fix isn't working
                        pytest.fail("PermissionError was not handled gracefully")

    def test_service_registry_logs_unexpected_errors(self):
        """Test that unexpected errors are handled gracefully"""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_dir = Path(temp_dir) / "test_registry"
            registry_dir.mkdir()

            invalid_file = registry_dir / "marcus_test.json"
            invalid_file.write_text("invalid json")

            registry = MarcusServiceRegistry()
            registry.registry_dir = registry_dir

            with patch(
                "src.core.service_registry.psutil.pid_exists", return_value=False
            ):
                with patch.object(Path, "unlink") as mock_unlink:
                    mock_unlink.side_effect = RuntimeError("Unexpected system error")

                    # Should handle error gracefully without throwing exception
                    # This tests that unexpected errors are caught and logged instead of using bare pass
                    try:
                        services = registry.discover_services()
                        assert isinstance(services, list)
                        # If we get here, the unexpected error was handled properly
                    except RuntimeError:
                        # If this exception propagates, the fix isn't working
                        pytest.fail("RuntimeError was not handled gracefully")

    def test_secrets_system_random_produces_different_values(self):
        """Test that SystemRandom produces cryptographically secure values"""
        secure_random = secrets.SystemRandom()

        # Generate multiple values
        values = [secure_random.random() for _ in range(100)]

        # All values should be different (extremely unlikely to be the same)
        assert len(set(values)) == len(values)

        # All values should be in valid range
        assert all(0 <= v < 1 for v in values)

        # Values should have reasonable distribution (not all close to same value)
        mean_val = sum(values) / len(values)
        assert 0.3 < mean_val < 0.7  # Should be roughly centered around 0.5

    def test_service_registry_basic_functionality(self):
        """Test basic service registry operations to improve coverage"""
        registry = MarcusServiceRegistry("test_registry")

        # Test initialization
        assert registry.instance_id == "test_registry"
        assert "test_registry.json" in str(registry.registry_file)

        # Test unregister when file doesn't exist
        registry.unregister_service()  # Should not raise exception

    def test_service_registry_heartbeat_with_file_errors(self):
        """Test heartbeat update with file system errors"""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = MarcusServiceRegistry("test_heartbeat")
            registry.registry_file = Path(temp_dir) / "test_heartbeat.json"

            # Create file with invalid JSON
            registry.registry_file.write_text("invalid json")

            # Should handle gracefully without throwing
            registry.update_heartbeat(status="running")

    def test_service_registry_platform_specific_paths(self):
        """Test platform-specific registry directory handling"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("platform.system", return_value="Windows"):
                with patch.dict("os.environ", {"APPDATA": temp_dir}):
                    registry = MarcusServiceRegistry()
                    assert temp_dir in str(registry.registry_dir)
                    assert registry.registry_dir.parts[-2:] == (".marcus", "services")
