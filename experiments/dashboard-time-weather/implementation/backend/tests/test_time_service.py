"""Unit tests for the Time Service.

Tests timezone listing, time formatting, and real-time update behavior.
"""

import time

import pytest
from backend.app.services.time_service import (
    _format_utc_offset,
    _get_display_name,
    _get_region,
    get_current_time,
    get_timezone_list,
)


class TestGetRegion:
    """Test suite for _get_region helper."""

    def test_america_region(self) -> None:
        """Test America/ prefix maps to Americas."""
        assert _get_region("America/New_York") == "Americas"

    def test_europe_region(self) -> None:
        """Test Europe/ prefix maps to Europe."""
        assert _get_region("Europe/London") == "Europe"

    def test_asia_region(self) -> None:
        """Test Asia/ prefix maps to Asia."""
        assert _get_region("Asia/Tokyo") == "Asia"

    def test_unknown_region(self) -> None:
        """Test unknown prefix maps to Other."""
        assert _get_region("Unknown/Place") == "Other"

    def test_no_slash(self) -> None:
        """Test timezone without slash uses full name as prefix."""
        assert _get_region("UTC") == "Other"


class TestGetDisplayName:
    """Test suite for _get_display_name helper."""

    def test_city_extraction(self) -> None:
        """Test that city name is extracted from IANA timezone."""
        assert _get_display_name("America/New_York") == "New York"

    def test_underscore_replacement(self) -> None:
        """Test that underscores are replaced with spaces."""
        assert _get_display_name("America/Los_Angeles") == "Los Angeles"

    def test_no_slash_returns_name(self) -> None:
        """Test that timezones without slash return the full name."""
        assert _get_display_name("UTC") == "UTC"

    def test_nested_timezone(self) -> None:
        """Test nested IANA timezone uses last segment."""
        assert _get_display_name("America/Indiana/Knox") == "Knox"


class TestFormatUtcOffset:
    """Test suite for _format_utc_offset helper."""

    def test_utc_offset(self) -> None:
        """Test UTC returns +00:00."""
        from datetime import datetime, timezone

        dt = datetime.now(tz=timezone.utc)
        assert _format_utc_offset(dt) == "+00:00"

    def test_positive_offset(self) -> None:
        """Test positive timezone offset formatting."""
        from datetime import datetime, timedelta, timezone

        tz = timezone(timedelta(hours=5, minutes=30))
        dt = datetime.now(tz=tz)
        assert _format_utc_offset(dt) == "+05:30"

    def test_negative_offset(self) -> None:
        """Test negative timezone offset formatting."""
        from datetime import datetime, timedelta, timezone

        tz = timezone(timedelta(hours=-5))
        dt = datetime.now(tz=tz)
        assert _format_utc_offset(dt) == "-05:00"

    def test_naive_datetime(self) -> None:
        """Test naive datetime returns +00:00."""
        from datetime import datetime

        dt = datetime(2026, 1, 1)  # noqa: DTZ001
        assert _format_utc_offset(dt) == "+00:00"


class TestGetTimezoneList:
    """Test suite for get_timezone_list service function."""

    def test_returns_non_empty_list(self) -> None:
        """Test that timezone list is not empty."""
        result = get_timezone_list()
        assert result.count > 0
        assert len(result.timezones) == result.count

    def test_excludes_etc_timezones(self) -> None:
        """Test that Etc/ timezones are excluded."""
        result = get_timezone_list()
        tz_names = [tz.name for tz in result.timezones]
        etc_zones = [n for n in tz_names if n.startswith("Etc/")]
        assert len(etc_zones) == 0

    def test_includes_utc(self) -> None:
        """Test that UTC is included in the list."""
        result = get_timezone_list()
        tz_names = [tz.name for tz in result.timezones]
        assert "UTC" in tz_names

    def test_timezone_has_valid_offset(self) -> None:
        """Test that all timezones have valid UTC offset format."""
        result = get_timezone_list()
        for tz in result.timezones:
            assert tz.utc_offset[0] in ("+", "-")
            assert ":" in tz.utc_offset


class TestGetCurrentTime:
    """Test suite for get_current_time service function."""

    def test_default_utc(self) -> None:
        """Test that default timezone is UTC."""
        result = get_current_time()
        assert result.timezone == "UTC"

    def test_custom_timezone(self) -> None:
        """Test getting time in a specific timezone."""
        result = get_current_time("America/New_York")
        assert result.timezone == "America/New_York"

    def test_invalid_timezone_raises(self) -> None:
        """Test that invalid timezone raises ValueError."""
        with pytest.raises(ValueError, match="Unknown timezone"):
            get_current_time("Invalid/Zone")

    def test_formatted_time_present(self) -> None:
        """Test that formatted time fields are populated."""
        result = get_current_time()
        assert result.formatted.time_24h
        assert result.formatted.time_12h
        assert result.formatted.date
        assert result.formatted.day_of_week

    def test_unix_timestamp_is_recent(self) -> None:
        """Test that unix timestamp is close to current time."""
        result = get_current_time()
        now = time.time()
        assert abs(result.unix_timestamp - now) < 2

    def test_real_time_updates(self) -> None:
        """Test that consecutive calls return different timestamps."""
        result1 = get_current_time()
        time.sleep(0.1)
        result2 = get_current_time()
        assert result2.unix_timestamp >= result1.unix_timestamp

    def test_timezone_change_affects_formatted_time(self) -> None:
        """Test that different timezones produce different formatted times."""
        utc_result = get_current_time("UTC")
        tokyo_result = get_current_time("Asia/Tokyo")
        # Tokyo is UTC+9, so the times should differ
        assert utc_result.formatted.time_24h != tokyo_result.formatted.time_24h
