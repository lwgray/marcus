"""Unit tests for the MARCUS_GOTCHA_ENUMERATION feature flag (issue #680).

Default is ON — opt-out via canonical falsy values for runs that need
the pre-#680 behavior (no gotcha criteria).
"""

from typing import Any

import pytest

from src.config.gotcha_enumeration_config import (
    ENV_VAR_NAME,
    is_gotcha_enumeration_enabled,
)

pytestmark = pytest.mark.unit


class TestGotchaEnumerationFlag:
    """Flag defaults to ON; only canonical falsy values disable it."""

    def test_default_on_when_env_unset(self, monkeypatch: Any) -> None:
        monkeypatch.delenv(ENV_VAR_NAME, raising=False)
        assert is_gotcha_enumeration_enabled() is True

    def test_default_on_when_env_empty(self, monkeypatch: Any) -> None:
        monkeypatch.setenv(ENV_VAR_NAME, "")
        assert is_gotcha_enumeration_enabled() is True

    @pytest.mark.parametrize("falsy", ["0", "false", "no", "off", "disabled", "FALSE"])
    def test_disabled_by_canonical_falsy(self, monkeypatch: Any, falsy: str) -> None:
        monkeypatch.setenv(ENV_VAR_NAME, falsy)
        assert is_gotcha_enumeration_enabled() is False

    def test_unknown_value_treated_as_on(self, monkeypatch: Any) -> None:
        monkeypatch.setenv(ENV_VAR_NAME, "yes")
        assert is_gotcha_enumeration_enabled() is True
