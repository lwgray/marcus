"""Unit tests for WeatherCache."""

from datetime import datetime

import pytest
from app.models.weather import WeatherData
from app.services.weather_cache import WeatherCache


@pytest.fixture  # type: ignore[misc]
def cache() -> WeatherCache:
    """Create a WeatherCache with short TTL for testing.

    Returns
    -------
    WeatherCache
        A cache instance with 5-second TTL.
    """
    return WeatherCache(ttl_seconds=5)


@pytest.fixture  # type: ignore[misc]
def sample_weather() -> WeatherData:
    """Create sample WeatherData for testing.

    Returns
    -------
    WeatherData
        A valid weather data instance.
    """
    return WeatherData(
        city="New York",
        country="US",
        temperature=72.5,
        feels_like=70.1,
        temp_min=68.0,
        temp_max=75.0,
        humidity=55,
        pressure=1013,
        wind_speed=8.5,
        wind_direction=220,
        condition="clear sky",
        condition_code=800,
        icon="01d",
        icon_url="https://openweathermap.org/img/wn/01d@2x.png",
        visibility=10000,
        timestamp=datetime(2026, 3, 31, 20, 30, 0),
        sunrise=datetime(2026, 3, 31, 10, 45, 0),
        sunset=datetime(2026, 3, 31, 23, 15, 0),
    )


class TestWeatherCache:
    """Test suite for WeatherCache."""

    def test_get_missing_key(self, cache: WeatherCache) -> None:
        """Test that get returns None for missing keys."""
        assert cache.get("NonExistent", "imperial") is None

    def test_set_and_get(
        self,
        cache: WeatherCache,
        sample_weather: WeatherData,
    ) -> None:
        """Test setting and retrieving a cache entry."""
        cache.set("New York", "imperial", sample_weather)
        entry = cache.get("New York", "imperial")
        assert entry is not None
        assert entry.data.city == "New York"
        assert entry.is_expired is False

    def test_case_insensitive_keys(
        self,
        cache: WeatherCache,
        sample_weather: WeatherData,
    ) -> None:
        """Test that cache keys are case-insensitive."""
        cache.set("New York", "imperial", sample_weather)
        entry = cache.get("new york", "imperial")
        assert entry is not None
        assert entry.data.city == "New York"

    def test_different_units_separate_entries(
        self,
        cache: WeatherCache,
        sample_weather: WeatherData,
    ) -> None:
        """Test that different units create separate cache entries."""
        cache.set("New York", "imperial", sample_weather)
        assert cache.get("New York", "metric") is None

    def test_expired_entry_still_returned(
        self,
        sample_weather: WeatherData,
    ) -> None:
        """Test that expired entries are returned (for stale serving)."""
        cache = WeatherCache(ttl_seconds=0)
        cache.set("New York", "imperial", sample_weather)
        entry = cache.get("New York", "imperial")
        assert entry is not None
        assert entry.is_expired is True

    def test_whitespace_trimmed_in_key(
        self,
        cache: WeatherCache,
        sample_weather: WeatherData,
    ) -> None:
        """Test that whitespace is trimmed from city names."""
        cache.set("  New York  ", "imperial", sample_weather)
        entry = cache.get("New York", "imperial")
        assert entry is not None
