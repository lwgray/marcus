"""Unit tests for :mod:`src.telemetry.config`.

The config layer persists the user's opt-in/out choice for telemetry
at ``~/.marcus/config.yaml``.  It must:

- Default to enabled (opt-in by default — OSS dev-tool norm).
- Honor ``MARCUS_TELEMETRY=off`` as a one-shot override that does NOT
  modify the on-disk config.
- Round-trip ``set_telemetry_enabled(False)`` → ``is_telemetry_enabled()``.
- Preserve other keys in the YAML file when toggling telemetry —
  upsert one key, never rewrite the whole file.
- Survive a missing config file, a missing ``telemetry`` section, and
  a corrupt YAML file without crashing Marcus.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect ``~`` to ``tmp_path`` and clear MARCUS_TELEMETRY.

    Mirrors the fixture in ``test_first_run_notice.py`` so config
    tests get a clean ``~/.marcus/config.yaml`` per test.  Hard
    isolation guard fails fast if ``Path.home()`` ever stops
    honoring the patched ``HOME``.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv("MARCUS_TELEMETRY", raising=False)

    resolved_home = Path.home()
    assert resolved_home == tmp_path, (
        f"isolated_home fixture failed: Path.home() resolved to "
        f"{resolved_home!r}, expected {tmp_path!r}"
    )
    return tmp_path


class TestIsTelemetryEnabled:
    """``is_telemetry_enabled`` returns the effective on/off state."""

    def test_default_is_enabled(self, isolated_home: Path) -> None:
        """No config file present → telemetry is enabled (opt-in by default).

        This is the load-bearing default that implements the
        privacy contract documented in ``docs/telemetry.md``.
        Changing this default is a values decision that requires
        updating the disclosure document.

        Falsification recipe: change the ``return True`` fallback
        in ``is_telemetry_enabled`` to ``return False`` and confirm
        this test fails.
        """
        from src.telemetry.config import is_telemetry_enabled

        assert is_telemetry_enabled() is True

    def test_explicitly_disabled_in_config(self, isolated_home: Path) -> None:
        """``telemetry.enabled: false`` in config returns False."""
        from src.telemetry.config import (
            is_telemetry_enabled,
            set_telemetry_enabled,
        )

        set_telemetry_enabled(False)
        assert is_telemetry_enabled() is False

    def test_explicitly_enabled_in_config(self, isolated_home: Path) -> None:
        """``telemetry.enabled: true`` in config returns True."""
        from src.telemetry.config import (
            is_telemetry_enabled,
            set_telemetry_enabled,
        )

        set_telemetry_enabled(False)
        set_telemetry_enabled(True)
        assert is_telemetry_enabled() is True

    def test_env_var_off_overrides_config(
        self, isolated_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MARCUS_TELEMETRY=off beats config.yaml `enabled: true`.

        The env var is a one-shot suppression switch.  Even with
        telemetry enabled in the config, the env var disables it
        for the session.
        """
        from src.telemetry.config import (
            is_telemetry_enabled,
            set_telemetry_enabled,
        )

        set_telemetry_enabled(True)
        monkeypatch.setenv("MARCUS_TELEMETRY", "off")

        assert is_telemetry_enabled() is False

    def test_env_var_off_does_not_modify_config(
        self, isolated_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MARCUS_TELEMETRY=off is in-memory only — config stays as is.

        Critical: env-var override must not write to the config
        file.  Otherwise a user who runs ``MARCUS_TELEMETRY=off
        marcus`` once would have telemetry permanently disabled —
        the opposite of the env var's intent (one-shot suppression).
        """
        from src.telemetry.config import (
            get_config_path,
            is_telemetry_enabled,
            set_telemetry_enabled,
        )

        set_telemetry_enabled(True)
        config_before = get_config_path().read_text()

        monkeypatch.setenv("MARCUS_TELEMETRY", "off")
        is_telemetry_enabled()  # triggers the read path

        config_after = get_config_path().read_text()
        assert config_before == config_after, (
            "MARCUS_TELEMETRY=off must NOT modify config.yaml; "
            "otherwise re-enabling telemetry is silently broken."
        )

    def test_case_insensitive_env_var(
        self, isolated_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MARCUS_TELEMETRY=OFF / Off / oFf all suppress."""
        from src.telemetry.config import (
            is_telemetry_enabled,
            set_telemetry_enabled,
        )

        set_telemetry_enabled(True)
        for value in ("OFF", "Off", "oFf"):
            monkeypatch.setenv("MARCUS_TELEMETRY", value)
            assert (
                is_telemetry_enabled() is False
            ), f"MARCUS_TELEMETRY={value!r} should disable"


class TestSetTelemetryEnabled:
    """``set_telemetry_enabled`` writes a YAML upsert that preserves other keys."""

    def test_disable_writes_false_to_config(self, isolated_home: Path) -> None:
        """``set_telemetry_enabled(False)`` persists the choice on disk."""
        from src.telemetry.config import get_config_path, set_telemetry_enabled

        set_telemetry_enabled(False)
        assert get_config_path().exists()
        # The file must contain ``enabled: false`` under ``telemetry``.
        # We don't pin the exact YAML format to allow library
        # implementation flexibility (PyYAML emits ``false``, ruamel
        # may emit ``False`` — both acceptable).
        text = get_config_path().read_text().lower()
        assert "telemetry" in text
        assert "enabled" in text
        assert "false" in text

    def test_enable_writes_true_to_config(self, isolated_home: Path) -> None:
        """``set_telemetry_enabled(True)`` persists True."""
        from src.telemetry.config import get_config_path, set_telemetry_enabled

        set_telemetry_enabled(False)
        set_telemetry_enabled(True)
        text = get_config_path().read_text().lower()
        assert "true" in text

    def test_preserves_unrelated_keys(self, isolated_home: Path) -> None:
        """Toggling telemetry does NOT clobber other config sections.

        Marcus's ``~/.marcus/config.yaml`` carries many sections
        beyond telemetry (ai, kanban, etc.).  ``set_telemetry_enabled``
        must perform a true upsert — read-modify-write — rather than
        overwriting the file.

        Falsification recipe: implement ``set_telemetry_enabled``
        with ``yaml.dump({"telemetry": {"enabled": value}})`` and
        confirm this test fails when an unrelated ``ai`` section is
        clobbered.
        """
        import yaml

        from src.telemetry.config import get_config_path, set_telemetry_enabled

        # Pre-seed config with unrelated content.
        get_config_path().parent.mkdir(parents=True, exist_ok=True)
        get_config_path().write_text(
            yaml.safe_dump(
                {
                    "ai": {"provider": "anthropic", "model": "claude-sonnet-4-6"},
                    "kanban": {"provider": "planka"},
                }
            )
        )

        set_telemetry_enabled(False)

        loaded = yaml.safe_load(get_config_path().read_text())
        assert loaded["ai"]["provider"] == "anthropic"
        assert loaded["ai"]["model"] == "claude-sonnet-4-6"
        assert loaded["kanban"]["provider"] == "planka"
        assert loaded["telemetry"]["enabled"] is False

    def test_creates_config_dir_if_missing(self, isolated_home: Path) -> None:
        """``~/.marcus/`` is created if it does not already exist.

        First-run scenario: user installs Marcus and immediately
        runs ``marcus telemetry disable`` before any other Marcus
        command.  ``~/.marcus/`` doesn't exist yet.  The function
        must create it.
        """
        from src.telemetry.config import get_config_path, set_telemetry_enabled

        assert not get_config_path().parent.exists()
        set_telemetry_enabled(False)
        assert get_config_path().parent.exists()
        assert get_config_path().exists()


class TestErrorPaths:
    """Config layer survives missing files, corrupt YAML, missing sections."""

    def test_missing_config_returns_default(self, isolated_home: Path) -> None:
        """No config file → enabled (opt-in default)."""
        from src.telemetry.config import get_config_path, is_telemetry_enabled

        assert not get_config_path().exists()
        assert is_telemetry_enabled() is True

    def test_config_missing_telemetry_section(self, isolated_home: Path) -> None:
        """Config exists but no ``telemetry`` section → enabled (opt-in default).

        A user who has a Marcus config from before v0.3.7 won't
        have a ``telemetry`` section.  They get the default.
        """
        import yaml

        from src.telemetry.config import get_config_path, is_telemetry_enabled

        get_config_path().parent.mkdir(parents=True, exist_ok=True)
        get_config_path().write_text(yaml.safe_dump({"ai": {"provider": "anthropic"}}))

        assert is_telemetry_enabled() is True

    def test_corrupt_yaml_returns_default(self, isolated_home: Path) -> None:
        """Unparseable YAML → enabled (opt-in default), no crash.

        A truncated or hand-edited config that fails to parse must
        not crash Marcus.  Best behavior: fall back to the default
        and log a warning (warning is implementation detail; the
        no-crash invariant is what this test pins).
        """
        from src.telemetry.config import get_config_path, is_telemetry_enabled

        get_config_path().parent.mkdir(parents=True, exist_ok=True)
        get_config_path().write_text("not: valid: yaml: [unbalanced\n")

        # Must not raise.
        assert is_telemetry_enabled() is True
