"""
Stub debt scanner for Marcus.

Detects placeholder/stub markers in source files so agents are
warned when they complete a task that still contains stubs.

Stub markers recognised
-----------------------
- ``data-stub="..."`` — JSX attribute on bootstrap placeholder components
- ``// REPLACE this stub`` — source comment marking a placeholder implementation
"""

import logging
import re
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

# Patterns that identify a stub / placeholder in source content.
_STUB_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'data-stub\s*=\s*["\']', re.IGNORECASE),
    re.compile(r"//\s*REPLACE\s+this\s+stub", re.IGNORECASE),
]


def scan_file_for_stubs(file_path: Path, content: str) -> List[str]:
    """
    Return a list of stub-marker descriptions found in *content*.

    Parameters
    ----------
    file_path : Path
        Path to the file (used only for context in the returned strings).
    content : str
        Full text content of the file.

    Returns
    -------
    List[str]
        Human-readable descriptions of each stub marker found.
        Empty list when the file is clean.
    """
    findings: List[str] = []
    for lineno, line in enumerate(content.splitlines(), start=1):
        for pattern in _STUB_PATTERNS:
            if pattern.search(line):
                findings.append(f"{file_path}:{lineno}: {line.strip()[:80]}")
    return findings


def scan_output_paths(
    output_paths: List[str],
    project_root: Path,
) -> Dict[str, List[str]]:
    """
    Scan each path in *output_paths* for stub markers.

    Files that do not exist are silently skipped (the file may not have
    been created yet, which is a separate problem).

    Parameters
    ----------
    output_paths : List[str]
        Relative file paths declared by the task (from ``Task.output_paths``).
    project_root : Path
        Absolute path to the project root; used to resolve relative paths.

    Returns
    -------
    Dict[str, List[str]]
        Mapping of relative path → list of stub marker descriptions.
        Only paths with at least one finding appear in the result.
    """
    result: Dict[str, List[str]] = {}
    for rel_path in output_paths:
        full_path = project_root / rel_path
        if not full_path.exists():
            logger.debug("scan_output_paths: %s does not exist, skipping", full_path)
            continue
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning("scan_output_paths: could not read %s: %s", full_path, exc)
            continue
        findings = scan_file_for_stubs(full_path, content)
        if findings:
            result[rel_path] = findings
    return result
