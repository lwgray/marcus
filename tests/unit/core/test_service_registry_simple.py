"""
Simple tests to understand service registry behavior before building complex scenarios.
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest
from src.core.service_registry import MarcusServiceRegistry


class TestServiceRegistrySimple:
    """Simple tests to discover actual behavior"""
    
    def test_simple_error_handling(self):
        """Test basic error handling in discover_services"""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_dir = Path(temp_dir) / "services" 
            registry_dir.mkdir(parents=True)
            
            # Create invalid JSON file
            invalid_file = registry_dir / "marcus_test.json"
            invalid_file.write_text("invalid json")
            
            registry = MarcusServiceRegistry()
            registry.registry_dir = registry_dir
            
            # This should handle the error gracefully
            services = registry.discover_services()
            
            # File should be cleaned up, so no services returned
            assert services == []
            # Invalid file should be removed
            assert not invalid_file.exists()
    
    def test_logging_import_behavior(self):
        """Test how logging import works in error handling"""  
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_dir = Path(temp_dir) / "services"
            registry_dir.mkdir(parents=True)
            
            invalid_file = registry_dir / "marcus_test.json"
            invalid_file.write_text("invalid json")
            
            registry = MarcusServiceRegistry()
            registry.registry_dir = registry_dir
            
            # Mock unlink to raise permission error
            with patch.object(Path, 'unlink') as mock_unlink:
                mock_unlink.side_effect = PermissionError("Permission denied")
                
                # Should handle gracefully without throwing
                services = registry.discover_services()
                assert services == []
                
                # Verify unlink was called (trying to clean up invalid file)
                mock_unlink.assert_called()
    
    def test_registry_directory_creation(self):
        """Test registry directory behavior"""
        registry = MarcusServiceRegistry("test")
        
        # Should create registry directory structure
        assert registry.registry_dir.exists()
        assert registry.registry_dir.name == "services"
        assert registry.registry_dir.parent.name == ".marcus"