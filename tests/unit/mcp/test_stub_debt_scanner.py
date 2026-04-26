"""
Unit tests for stub debt scanner.

When a task completes, any output_paths files that still contain
stub markers (data-stub=, // REPLACE this stub) are reported as
warnings in the completion response so agents can resolve them.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


class TestStubMarkerDetection:
    """scan_file_for_stubs detects known stub markers."""

    def _scan(self, content: str, path: str = "src/Foo.tsx") -> list[str]:
        from src.marcus_mcp.coordinator.stub_scanner import scan_file_for_stubs

        return scan_file_for_stubs(Path(path), content)

    def test_detects_data_stub_attribute(self) -> None:
        """data-stub= JSX attribute marks a placeholder component."""
        markers = self._scan('<div data-stub="WeatherCard" />')
        assert len(markers) == 1
        assert "data-stub" in markers[0]

    def test_detects_replace_comment(self) -> None:
        """// REPLACE this stub comment marks a placeholder implementation."""
        markers = self._scan("// REPLACE this stub with the real implementation.")
        assert len(markers) == 1
        assert "REPLACE" in markers[0]

    def test_detects_stub_in_multiline_content(self) -> None:
        """Stub marker embedded in longer file is still detected."""
        content = "import React from 'react'\n\n// REPLACE this stub\nexport function Foo() { return null }"
        markers = self._scan(content)
        assert len(markers) >= 1

    def test_no_markers_in_real_implementation(self) -> None:
        """Clean implementation file returns empty list."""
        content = (
            "export function Button({ label }) { return <button>{label}</button>; }"
        )
        markers = self._scan(content)
        assert markers == []

    def test_multiple_markers_counted(self) -> None:
        """File with two stub markers returns both."""
        content = '<div data-stub="A" />\n<span data-stub="B" />'
        markers = self._scan(content)
        assert len(markers) == 2


class TestScanOutputPaths:
    """scan_output_paths checks a list of files and returns stub findings."""

    def _scan_paths(
        self, files: dict[str, str], output_paths: list[str], project_root: Path
    ) -> dict[str, list[str]]:
        from src.marcus_mcp.coordinator.stub_scanner import scan_output_paths

        # Write the files to the tmp directory
        for rel_path, content in files.items():
            full = project_root / rel_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")

        return scan_output_paths(output_paths, project_root)

    def test_returns_empty_when_no_stubs(self, tmp_path: Path) -> None:
        """Clean files produce an empty result dict."""
        result = self._scan_paths(
            {"src/Button.tsx": "export function Button() { return null; }"},
            ["src/Button.tsx"],
            tmp_path,
        )
        assert result == {}

    def test_returns_findings_for_stubbed_file(self, tmp_path: Path) -> None:
        """Stubbed file appears in result with its markers."""
        result = self._scan_paths(
            {"src/Card.tsx": '<div data-stub="Card" />'},
            ["src/Card.tsx"],
            tmp_path,
        )
        assert "src/Card.tsx" in result
        assert len(result["src/Card.tsx"]) >= 1

    def test_missing_file_is_skipped_not_errored(self, tmp_path: Path) -> None:
        """Non-existent output_paths entry is silently skipped."""
        result = scan_output_paths_direct(["src/nonexistent.tsx"], tmp_path)
        assert result == {}

    def test_only_stubbed_files_appear_in_result(self, tmp_path: Path) -> None:
        """Mixed clean/stubbed: only stubbed paths in result."""
        result = self._scan_paths(
            {
                "src/A.tsx": "export function A() { return null; }",
                "src/B.tsx": "// REPLACE this stub",
            },
            ["src/A.tsx", "src/B.tsx"],
            tmp_path,
        )
        assert "src/A.tsx" not in result
        assert "src/B.tsx" in result


def scan_output_paths_direct(
    output_paths: list[str], project_root: Path
) -> dict[str, list[str]]:
    """Helper that bypasses file creation for missing-file test."""
    from src.marcus_mcp.coordinator.stub_scanner import scan_output_paths

    return scan_output_paths(output_paths, project_root)
