#!/usr/bin/env python3
"""
Script to add appropriate pytest markers to integration tests based on their content.

Classification logic:
- E2E tests → @pytest.mark.e2e + @pytest.mark.slow + @pytest.mark.external
- Tests using real AI → @pytest.mark.ai + @pytest.mark.external + @pytest.mark.slow
- Tests using real Kanban → @pytest.mark.kanban + @pytest.mark.external
- Tests using mocks → @pytest.mark.internal + @pytest.mark.fast
"""

import re
from pathlib import Path
from typing import List, Set


def analyze_test_file(file_path: Path) -> Set[str]:
    """
    Analyze test file content to determine appropriate markers.

    Parameters
    ----------
    file_path : Path
        Path to the test file

    Returns
    -------
    Set[str]
        Set of marker names to add
    """
    content = file_path.read_text()
    markers = set()

    # Base marker - all integration tests get this
    markers.add("integration")

    # Check if it's in e2e directory
    if "/e2e/" in str(file_path):
        markers.add("e2e")
        markers.add("slow")
        markers.add("external")
        return markers

    # Check for AI usage (expensive, slow)
    ai_patterns = [
        r"create_project_from_natural_language",
        r"add_feature_natural_language",
        r"ai_client",
        r"OpenAIProvider",
        r"AnthropicProvider",
        r"test.*real.*ai",
        r"test.*ai.*real",
    ]
    if any(re.search(pattern, content, re.IGNORECASE) for pattern in ai_patterns):
        markers.add("ai")
        markers.add("external")
        markers.add("slow")
        return markers

    # Check for real Kanban usage
    kanban_patterns = [
        r"KanbanFactory\.create\(",
        r"await.*kanban\.",
        r"test.*board.*integration",
        r"test.*planka",
        r"appears_on_board",
    ]
    has_kanban = any(
        re.search(pattern, content, re.IGNORECASE) for pattern in kanban_patterns
    )

    # Check for mocking (indicates internal integration)
    mock_patterns = [
        r"from unittest\.mock import",
        r"@patch",
        r"Mock\(\)",
        r"AsyncMock\(",
        r"mock_",
    ]
    has_mocks = any(re.search(pattern, content) for pattern in mock_patterns)

    if has_kanban and not has_mocks:
        # Real Kanban, no mocks = external integration
        markers.add("kanban")
        markers.add("external")
        # Moderate speed unless proven slow
    elif has_mocks:
        # Mocked external services = internal integration
        markers.add("internal")
        markers.add("fast")
    else:
        # Default: internal integration
        markers.add("internal")
        markers.add("fast")

    return markers


def get_existing_markers(content: str) -> List[str]:
    """Extract existing @pytest.mark markers from file content."""
    marker_pattern = r"@pytest\.mark\.(\w+)"
    return re.findall(marker_pattern, content)


def add_markers_to_class(content: str, markers: Set[str]) -> str:
    """
    Add markers to test classes that don't have them.

    Parameters
    ----------
    content : str
        File content
    markers : Set[str]
        Markers to add

    Returns
    -------
    str
        Updated content
    """
    lines = content.split("\n")
    updated_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this is a test class definition
        if re.match(r"^class Test\w+", line):
            # Look back to see if there are already markers
            existing_markers = []
            j = i - 1
            while j >= 0 and (
                lines[j].strip().startswith("@pytest.mark.") or lines[j].strip() == ""
            ):
                if lines[j].strip().startswith("@pytest.mark."):
                    marker_match = re.search(r"@pytest\.mark\.(\w+)", lines[j])
                    if marker_match:
                        existing_markers.append(marker_match.group(1))
                j -= 1

            # Determine which markers to add
            markers_to_add = markers - set(existing_markers) - {"asyncio", "anyio"}

            if markers_to_add:
                # Add missing markers before the class
                for marker in sorted(markers_to_add):
                    updated_lines.append(f"@pytest.mark.{marker}")

        updated_lines.append(line)
        i += 1

    return "\n".join(updated_lines)


def process_integration_tests() -> None:
    """Process all integration test files and add appropriate markers."""
    test_dir = Path("tests/integration")

    if not test_dir.exists():
        print(f"Test directory {test_dir} not found!")
        return

    files_updated = 0
    files_scanned = 0

    for test_file in test_dir.rglob("test_*.py"):
        files_scanned += 1
        print(f"\nAnalyzing: {test_file.relative_to(Path.cwd())}")

        # Analyze file to determine markers
        markers = analyze_test_file(test_file)
        print(f"  Suggested markers: {', '.join(sorted(markers))}")

        # Read current content
        content = test_file.read_text()
        existing_markers = set(get_existing_markers(content))
        print(f"  Existing markers: {', '.join(sorted(existing_markers)) or 'none'}")

        # Add missing markers
        new_markers = markers - existing_markers
        if new_markers:
            print(f"  Adding markers: {', '.join(sorted(new_markers))}")
            updated_content = add_markers_to_class(content, markers)
            test_file.write_text(updated_content)
            files_updated += 1
        else:
            print("  ✓ Already has all suggested markers")

    print(f"\n{'=' * 60}")
    print(f"Summary: Scanned {files_scanned} files, updated {files_updated} files")


if __name__ == "__main__":
    process_integration_tests()
