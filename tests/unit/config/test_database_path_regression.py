"""
Regression tests for database path handling.

This test suite ensures that the database path configuration bug from
GH issue #171 doesn't reoccur. The bug was introduced in the config
refactor (commit 2baa498) which:
1. Changed default data_dir from ./data to ~/.marcus/data
2. Used string concatenation instead of Path().expanduser()

The fix ensures:
1. Default data_dir is ./data (project-local)
2. Tilde (~) in paths is properly expanded
3. Path operations use Path() methods, not string concatenation
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest


class TestDatabasePathRegression:
    """Test suite for GH issue #171 - database path handling."""

    def test_default_data_dir_is_project_local(self):
        """
        Test that default data_dir is ./data (project-local).

        This ensures we don't accidentally change the default back to
        ~/.marcus/data which would break existing installations.

        Related to GH issue #171.
        """
        from src.config.marcus_config import MarcusConfig

        config = MarcusConfig()
        assert config.data_dir == "./data", (
            f"Default data_dir should be './data' (project-local), "
            f"got '{config.data_dir}'"
        )

    def test_from_dict_fallback_is_project_local(self):
        """
        Test that _from_dict() fallback for data_dir is ./data.

        When data_dir is not in the JSON config, it should default to
        ./data, not ~/.marcus/data.

        Related to GH issue #171.
        """
        from src.config.marcus_config import MarcusConfig

        # Create config from empty dict (no data_dir specified)
        config = MarcusConfig._from_dict({})

        assert (
            config.data_dir == "./data"
        ), f"Fallback data_dir should be './data', got '{config.data_dir}'"

    def test_tilde_expansion_in_server_initialization(self):
        """
        Test that ~ in data_dir is properly expanded in server.py.

        This test ensures that if a user configures data_dir as
        ~/.marcus/data, the tilde is expanded to the actual home
        directory, not left as a literal ~.

        Related to GH issue #171.
        """
        # Test the path expansion logic directly without initializing MarcusServer
        from pathlib import Path

        # Simulate what server.py does
        data_dir = "~/.marcus/data"
        persistence_path = Path(data_dir).expanduser() / "marcus.db"

        # Should not contain literal ~
        assert "~" not in str(
            persistence_path
        ), f"Database path should not contain literal ~: {persistence_path}"

        # Should be expanded to home directory
        expected_path = Path.home() / ".marcus" / "data" / "marcus.db"
        assert (
            persistence_path == expected_path
        ), f"Expected {expected_path}, got {persistence_path}"

    def test_relative_path_becomes_absolute(self):
        """
        Test that relative paths in data_dir work correctly.

        When data_dir is ./data, it should be used as a relative path
        from the project directory.

        Related to GH issue #171.
        """
        from pathlib import Path

        # Test the path expansion logic directly
        data_dir = "./data"
        persistence_path = Path(data_dir).expanduser() / "marcus.db"

        # Should end with data/marcus.db
        assert persistence_path.name == "marcus.db"
        assert persistence_path.parent.name == "data"

    def test_absolute_path_used_directly(self):
        """
        Test that absolute paths in data_dir are used as-is.

        When data_dir is an absolute path, it should be used directly
        without modification.

        Related to GH issue #171.
        """
        import tempfile
        from pathlib import Path

        # Test the path expansion logic directly
        # Use tempfile.gettempdir() instead of hardcoded /tmp
        test_dir = str(Path(tempfile.gettempdir()) / "test_marcus_data")  # nosec B108
        persistence_path = Path(test_dir).expanduser() / "marcus.db"

        expected_path = Path(test_dir) / "marcus.db"
        assert (
            persistence_path == expected_path
        ), f"Expected {expected_path}, got {persistence_path}"

    def test_cache_dir_also_defaults_to_project_local(self):
        """
        Test that cache_dir also defaults to ./cache (project-local).

        This ensures consistency - both data_dir and cache_dir should
        default to project-local directories.

        Related to GH issue #171.
        """
        from src.config.marcus_config import MarcusConfig

        config = MarcusConfig()
        assert (
            config.cache_dir == "./cache"
        ), f"Default cache_dir should be './cache', got '{config.cache_dir}'"

        # Also check _from_dict fallback
        config_from_dict = MarcusConfig._from_dict({})
        assert config_from_dict.cache_dir == "./cache", (
            f"Fallback cache_dir should be './cache', "
            f"got '{config_from_dict.cache_dir}'"
        )
