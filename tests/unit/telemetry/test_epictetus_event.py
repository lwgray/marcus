"""Unit tests for the epictetus_result event + recommendation sanitizer.

Stage 5B of #9.  The Epictetus auditor produces free-text
recommendations after a post-run code grade.  Those recommendations
can leak file paths, code snippets, identifying text — anything the
auditor decided to write.  The sanitizer in
:func:`src.telemetry.events.sanitize_epictetus_recommendations` is
the privacy guard between the auditor's output and PostHog.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv("MARCUS_TELEMETRY", raising=False)
    return tmp_path


@pytest.fixture
def mock_client(monkeypatch: pytest.MonkeyPatch) -> Any:
    client = MagicMock()
    monkeypatch.setattr(
        "src.telemetry.events.get_telemetry_client", lambda: client
    )
    return client


class TestSanitizeEpictetusRecommendations:
    """Sanitizer scrubs identifying content before recommendations ship."""

    def test_strips_absolute_unix_paths(self) -> None:
        """``/Users/lwgray/...`` becomes ``<path>``."""
        from src.telemetry.events import sanitize_epictetus_recommendations

        out = sanitize_epictetus_recommendations(
            ["Refactor /Users/lwgray/dev/marcus/src/auth.py to use bcrypt"]
        )
        assert "/Users/lwgray" not in out[0]
        assert "<path>" in out[0]

    def test_strips_home_relative_paths(self) -> None:
        """``~/marcus/...`` becomes ``<path>``."""
        from src.telemetry.events import sanitize_epictetus_recommendations

        out = sanitize_epictetus_recommendations(
            ["Edit ~/marcus/src/api.py to add caching"]
        )
        assert "~/marcus" not in out[0]
        assert "<path>" in out[0]

    def test_strips_windows_paths(self) -> None:
        """``C:\\Users\\name\\...`` becomes ``<path>``."""
        from src.telemetry.events import sanitize_epictetus_recommendations

        out = sanitize_epictetus_recommendations(
            ["Update C:\\Users\\Bob\\marcus\\config.yaml"]
        )
        assert "C:\\Users" not in out[0]
        assert "Bob" not in out[0]
        assert "<path>" in out[0]

    def test_strips_code_blocks(self) -> None:
        """Triple-backtick code blocks become ``<code>``."""
        from src.telemetry.events import sanitize_epictetus_recommendations

        out = sanitize_epictetus_recommendations(
            ["Replace the auth flow with:\n```python\nfrom auth import "
             "MagicSecretKey  # don't share\n```\nThat's it."]
        )
        assert "MagicSecretKey" not in out[0]
        assert "<code>" in out[0]

    def test_strips_inline_backtick_code(self) -> None:
        """Single-backtick inline code becomes ``<code>``."""
        from src.telemetry.events import sanitize_epictetus_recommendations

        out = sanitize_epictetus_recommendations(
            ["Use `bcrypt.hashpw(secret_value)` for hashing"]
        )
        assert "bcrypt.hashpw(secret_value)" not in out[0]
        assert "<code>" in out[0]

    def test_truncates_each_rec_to_200_chars(self) -> None:
        """Recs longer than 200 chars are truncated with an ellipsis."""
        from src.telemetry.events import sanitize_epictetus_recommendations

        long_rec = "improve test coverage " * 30  # ~600 chars
        out = sanitize_epictetus_recommendations([long_rec])
        assert len(out[0]) <= 200

    def test_limits_to_max_5_recs(self) -> None:
        """No more than 5 recs make it through; extras are dropped."""
        from src.telemetry.events import sanitize_epictetus_recommendations

        out = sanitize_epictetus_recommendations(
            [f"rec {i}" for i in range(20)]
        )
        assert len(out) <= 5

    def test_handles_empty_input(self) -> None:
        from src.telemetry.events import sanitize_epictetus_recommendations

        assert sanitize_epictetus_recommendations([]) == []
        assert sanitize_epictetus_recommendations(None) == []  # type: ignore[arg-type]

    def test_handles_non_string_items(self) -> None:
        """Non-string items are coerced or dropped, never raise."""
        from src.telemetry.events import sanitize_epictetus_recommendations

        # Must not raise.
        out = sanitize_epictetus_recommendations(
            [42, None, "actual rec", ["nested"]]  # type: ignore[list-item]
        )
        # "actual rec" survives.  Others are at sanitizer's discretion.
        assert "actual rec" in out

    def test_combined_path_and_code_in_same_rec(self) -> None:
        """A rec with both path and code → both stripped."""
        from src.telemetry.events import sanitize_epictetus_recommendations

        out = sanitize_epictetus_recommendations(
            [
                "In /Users/secret/proj/auth.py replace "
                "`hashlib.md5(password)` with bcrypt"
            ]
        )
        assert "/Users/secret" not in out[0]
        assert "hashlib.md5(password)" not in out[0]


class TestFireEpictetusResult:
    """``fire_epictetus_result`` event helper applies the sanitizer."""

    def test_event_name_and_keys(
        self, isolated_home: Path, mock_client: Any
    ) -> None:
        from src.telemetry.events import fire_epictetus_result

        fire_epictetus_result(
            grade="B",
            recommendations=["improve test coverage", "add error handling"],
        )
        args, _ = mock_client.capture.call_args
        assert args[0] == "epictetus_result"
        assert args[1]["grade"] == "B"
        assert "improve test coverage" in args[1]["recommendations"]

    def test_recommendations_are_sanitized(
        self, isolated_home: Path, mock_client: Any
    ) -> None:
        """Sanitizer is applied to recommendations before they ship.

        Falsification recipe: change ``fire_epictetus_result`` to
        pass ``recommendations`` through without calling the
        sanitizer.  Confirm this test fails because the path leaks.
        """
        from src.telemetry.events import fire_epictetus_result

        fire_epictetus_result(
            grade="B",
            recommendations=[
                "Refactor /Users/secret/auth.py to add `bcrypt.hashpw(pw)`"
            ],
        )
        flat = " ".join(mock_client.capture.call_args[0][1]["recommendations"])
        assert "/Users/secret" not in flat
        assert "bcrypt.hashpw(pw)" not in flat

    def test_swallows_exceptions(
        self, isolated_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from src.telemetry.events import fire_epictetus_result

        broken = MagicMock()
        broken.capture.side_effect = RuntimeError("simulated")
        monkeypatch.setattr(
            "src.telemetry.events.get_telemetry_client", lambda: broken
        )
        fire_epictetus_result(grade="A", recommendations=[])  # Must not raise.
