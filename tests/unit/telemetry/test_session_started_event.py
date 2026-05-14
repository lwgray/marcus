"""Unit tests for the ``session_started`` telemetry event.

Stage 2 of #9.  Fires on Marcus startup with the runtime
environment fingerprint (version, OS, kanban + AI provider,
runner discriminator).  Properties per ``docs/telemetry.md``
§ Session events.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Per-test ``~``; clears env vars that influence the event."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv("MARCUS_TELEMETRY", raising=False)
    monkeypatch.delenv("MARCUS_POSTHOG_API_KEY", raising=False)
    monkeypatch.delenv("MARCUS_RUNNER", raising=False)
    return tmp_path


@pytest.fixture
def fake_config() -> Any:
    """A minimal config double matching ``MarcusConfig`` attribute access."""
    config = MagicMock()
    config.ai.provider = "anthropic"
    config.ai.model = "claude-sonnet-4-6"
    config.kanban.provider = "planka"
    return config


@pytest.fixture
def fake_server(fake_config: Any) -> Any:
    """A MarcusServer double with config + provider attributes."""
    server = MagicMock()
    server.config = fake_config
    server.provider = fake_config.kanban.provider
    return server


class TestBuildSessionStartedProperties:
    """``_build_session_started_properties`` returns the disclosure schema."""

    def test_returns_all_required_keys(
        self, isolated_home: Path, fake_server: Any
    ) -> None:
        """Every key promised by docs/telemetry.md § session_started exists.

        The disclosure is the contract; every key it lists must
        appear in the payload, or the disclosure is lying to users.
        """
        from src.marcus_mcp.server import _build_session_started_properties

        props = _build_session_started_properties(fake_server)

        required_keys = {
            "marcus_version",
            "python_version",
            "os",
            "kanban_provider",
            "ai_provider",
            "planner_model",
            "agent_model",
            "is_local_llm",
            "runner",
        }
        missing = required_keys - set(props.keys())
        assert not missing, (
            f"session_started payload missing keys promised in "
            f"docs/telemetry.md: {missing}"
        )

    def test_kanban_provider_from_config(
        self, isolated_home: Path, fake_server: Any
    ) -> None:
        """``kanban_provider`` reads from ``config.kanban.provider``."""
        from src.marcus_mcp.server import _build_session_started_properties

        fake_server.config.kanban.provider = "github"
        props = _build_session_started_properties(fake_server)

        assert props["kanban_provider"] == "github"

    def test_ai_provider_from_config(
        self, isolated_home: Path, fake_server: Any
    ) -> None:
        """``ai_provider`` reads from ``config.ai.provider``."""
        from src.marcus_mcp.server import _build_session_started_properties

        fake_server.config.ai.provider = "ollama"
        props = _build_session_started_properties(fake_server)

        assert props["ai_provider"] == "ollama"

    def test_is_local_llm_true_for_ollama(
        self, isolated_home: Path, fake_server: Any
    ) -> None:
        """``is_local_llm`` is True when ai_provider names a local stack."""
        from src.marcus_mcp.server import _build_session_started_properties

        fake_server.config.ai.provider = "ollama"
        props = _build_session_started_properties(fake_server)

        assert props["is_local_llm"] is True

    def test_is_local_llm_false_for_anthropic(
        self, isolated_home: Path, fake_server: Any
    ) -> None:
        """``is_local_llm`` is False for hosted providers."""
        from src.marcus_mcp.server import _build_session_started_properties

        fake_server.config.ai.provider = "anthropic"
        props = _build_session_started_properties(fake_server)

        assert props["is_local_llm"] is False

    def test_runner_defaults_to_mcp_direct(
        self, isolated_home: Path, fake_server: Any
    ) -> None:
        """MARCUS_RUNNER absent → ``runner`` is ``"mcp_direct"``."""
        from src.marcus_mcp.server import _build_session_started_properties

        props = _build_session_started_properties(fake_server)

        assert props["runner"] == "mcp_direct"

    def test_runner_reads_marcus_runner_env(
        self,
        isolated_home: Path,
        fake_server: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """MARCUS_RUNNER=meta_runner → ``runner`` is ``"meta_runner"``."""
        from src.marcus_mcp.server import _build_session_started_properties

        monkeypatch.setenv("MARCUS_RUNNER", "meta_runner")
        props = _build_session_started_properties(fake_server)

        assert props["runner"] == "meta_runner"

    def test_python_version_is_major_minor_only(
        self, isolated_home: Path, fake_server: Any
    ) -> None:
        """``python_version`` is the ``X.Y`` form, no patch level.

        Patch level is high-cardinality and rarely useful for
        cohort analysis; major.minor is the right granularity for
        compatibility tracking.
        """
        from src.marcus_mcp.server import _build_session_started_properties

        props = _build_session_started_properties(fake_server)

        # e.g. "3.12" — exactly one dot, both sides digits.
        version = props["python_version"]
        parts = version.split(".")
        assert len(parts) == 2
        assert all(p.isdigit() for p in parts)

    def test_no_secrets_in_payload(
        self, isolated_home: Path, fake_server: Any
    ) -> None:
        """No api_key, no auth token, no PII in the payload.

        Privacy regression net: even if the config has an
        anthropic_api_key, openai_api_key, etc., none of them
        may appear in the event.  The disclosure promises this.
        """
        from src.marcus_mcp.server import _build_session_started_properties

        # Pollute the config with secrets that MUST NOT ship.
        fake_server.config.ai.anthropic_api_key = "sk-ant-secret-key-xyz"
        fake_server.config.ai.openai_api_key = "sk-openai-secret-abc"

        props = _build_session_started_properties(fake_server)
        flat = " ".join(str(v) for v in props.values())

        assert "sk-ant-secret-key-xyz" not in flat
        assert "sk-openai-secret-abc" not in flat
        assert "api_key" not in props


class TestFireSessionStartedEvent:
    """``_fire_session_started_event`` calls the telemetry client."""

    def test_calls_capture_with_session_started(
        self,
        isolated_home: Path,
        fake_server: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The helper calls ``client.capture("session_started", props)``.

        Falsification recipe: remove the ``capture`` call from
        ``_fire_session_started_event`` and confirm this test
        fails because the mock was not called.
        """
        from src.marcus_mcp.server import _fire_session_started_event

        mock_client = MagicMock()
        monkeypatch.setattr(
            "src.marcus_mcp.server.get_telemetry_client", lambda: mock_client
        )

        _fire_session_started_event(fake_server)

        mock_client.capture.assert_called_once()
        args, kwargs = mock_client.capture.call_args
        assert args[0] == "session_started"
        assert isinstance(args[1], dict)
        assert "marcus_version" in args[1]

    def test_swallows_capture_errors(
        self,
        isolated_home: Path,
        fake_server: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Errors inside ``capture`` must not crash server startup.

        Telemetry is best-effort.  Even if the client itself fails
        (e.g. config layer corrupt), session startup must continue.
        """
        from src.marcus_mcp.server import _fire_session_started_event

        broken_client = MagicMock()
        broken_client.capture.side_effect = RuntimeError("simulated")
        monkeypatch.setattr(
            "src.marcus_mcp.server.get_telemetry_client", lambda: broken_client
        )

        # Must not raise.
        _fire_session_started_event(fake_server)

    def test_swallows_property_build_errors(
        self,
        isolated_home: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Property build errors (broken config) must not crash server startup."""
        from src.marcus_mcp.server import _fire_session_started_event

        # A server whose .config raises on attribute access.
        broken_server = MagicMock()
        broken_server.config = property(
            lambda _: (_ for _ in ()).throw(RuntimeError("broken config"))
        )

        mock_client = MagicMock()
        monkeypatch.setattr(
            "src.marcus_mcp.server.get_telemetry_client", lambda: mock_client
        )

        # Must not raise even if property gathering fails.
        _fire_session_started_event(broken_server)
