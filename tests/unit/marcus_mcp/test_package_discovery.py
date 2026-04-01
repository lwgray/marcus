"""Unit tests for package discovery and import structure.

Verifies that marcus_mcp is importable as a top-level module
and that the CLI entry point is correctly configured.
"""

import importlib
import subprocess
import sys

import pytest


class TestPackageDiscovery:
    """Test suite for package import paths."""

    @pytest.mark.unit
    def test_marcus_mcp_importable_as_top_level(self) -> None:
        """Test that marcus_mcp can be imported as a top-level module."""
        spec = importlib.util.find_spec("marcus_mcp")
        assert spec is not None, (
            "marcus_mcp should be importable as a top-level module. "
            "Current config only exposes it as src.marcus_mcp."
        )

    @pytest.mark.unit
    def test_marcus_mcp_has_file_attribute(self) -> None:
        """Test that marcus_mcp.__file__ resolves to a real path."""
        import marcus_mcp

        assert marcus_mcp.__file__ is not None
        assert "marcus_mcp" in marcus_mcp.__file__

    @pytest.mark.unit
    def test_src_marcus_mcp_still_importable(self) -> None:
        """Test that src.marcus_mcp remains importable for backward compat."""
        spec = importlib.util.find_spec("src.marcus_mcp")
        assert (
            spec is not None
        ), "src.marcus_mcp should still be importable for backward compatibility."

    @pytest.mark.unit
    def test_cli_entry_point_resolves(self) -> None:
        """Test that the marcus CLI entry point module is importable."""
        result = subprocess.run(
            [sys.executable, "-c", "from src.marcus_mcp.server import main"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"CLI entry point src.marcus_mcp.server:main should be importable. "
            f"stderr: {result.stderr}"
        )
