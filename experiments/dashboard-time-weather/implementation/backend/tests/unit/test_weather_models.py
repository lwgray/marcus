"""Unit tests for weather Pydantic models."""

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from app.models.weather import (
    CacheEntry,
    CityResult,
    CitySearchResponse,
    ErrorDetail,
    ErrorResponse,
    WeatherData,
    WeatherResponse,
)
from pydantic import ValidationError


@pytest.fixture  # type: ignore[misc]
def sample_weather_data() -> dict[str, Any]:
    """Create sample weather data dict for testing.

    Returns
    -------
    dict[str, Any]
        A valid weather data dictionary.
    """
    return {
        "city": "New York",
        "country": "US",
        "temperature": 72.5,
        "feels_like": 70.1,
        "temp_min": 68.0,
        "temp_max": 75.0,
        "humidity": 55,
        "pressure": 1013,
        "wind_speed": 8.5,
        "wind_direction": 220,
        "condition": "clear sky",
        "condition_code": 800,
        "icon": "01d",
        "icon_url": "https://openweathermap.org/img/wn/01d@2x.png",
        "visibility": 10000,
        "timestamp": datetime(2026, 3, 31, 20, 30, 0),
        "sunrise": datetime(2026, 3, 31, 10, 45, 0),
        "sunset": datetime(2026, 3, 31, 23, 15, 0),
    }


class TestWeatherData:
    """Test suite for WeatherData model."""

    def test_valid_weather_data(self, sample_weather_data: dict[str, Any]) -> None:
        """Test creating WeatherData with valid data."""
        data = WeatherData(**sample_weather_data)
        assert data.city == "New York"
        assert data.temperature == 72.5
        assert data.humidity == 55

    def test_humidity_out_of_range(self, sample_weather_data: dict[str, Any]) -> None:
        """Test humidity validation rejects values > 100."""
        sample_weather_data["humidity"] = 101
        with pytest.raises(ValidationError):
            WeatherData(**sample_weather_data)

    def test_negative_humidity(self, sample_weather_data: dict[str, Any]) -> None:
        """Test humidity validation rejects negative values."""
        sample_weather_data["humidity"] = -1
        with pytest.raises(ValidationError):
            WeatherData(**sample_weather_data)

    def test_negative_wind_speed(self, sample_weather_data: dict[str, Any]) -> None:
        """Test wind_speed validation rejects negative values."""
        sample_weather_data["wind_speed"] = -5.0
        with pytest.raises(ValidationError):
            WeatherData(**sample_weather_data)

    def test_wind_direction_out_of_range(
        self, sample_weather_data: dict[str, Any]
    ) -> None:
        """Test wind_direction validation rejects > 360."""
        sample_weather_data["wind_direction"] = 361
        with pytest.raises(ValidationError):
            WeatherData(**sample_weather_data)

    def test_negative_visibility(self, sample_weather_data: dict[str, Any]) -> None:
        """Test visibility validation rejects negative values."""
        sample_weather_data["visibility"] = -1
        with pytest.raises(ValidationError):
            WeatherData(**sample_weather_data)

    def test_missing_required_field(self, sample_weather_data: dict[str, Any]) -> None:
        """Test that missing required fields raise ValidationError."""
        del sample_weather_data["city"]
        with pytest.raises(ValidationError):
            WeatherData(**sample_weather_data)


class TestWeatherResponse:
    """Test suite for WeatherResponse model."""

    def test_successful_response(self, sample_weather_data: dict[str, Any]) -> None:
        """Test creating a successful weather response."""
        data = WeatherData(**sample_weather_data)
        response = WeatherResponse(
            data=data,
            cached_at=datetime.now(timezone.utc),
        )
        assert response.success is True
        assert response.stale is False

    def test_stale_response(self, sample_weather_data: dict[str, Any]) -> None:
        """Test creating a stale weather response."""
        data = WeatherData(**sample_weather_data)
        response = WeatherResponse(
            data=data,
            stale=True,
            cached_at=datetime.now(timezone.utc),
        )
        assert response.stale is True


class TestErrorResponse:
    """Test suite for ErrorResponse model."""

    def test_error_response(self) -> None:
        """Test creating an error response."""
        response = ErrorResponse(
            error=ErrorDetail(
                code="CITY_NOT_FOUND",
                message="City not found",
            )
        )
        assert response.success is False
        assert response.error.code == "CITY_NOT_FOUND"


class TestCitySearchResponse:
    """Test suite for CitySearchResponse model."""

    def test_city_search_response(self) -> None:
        """Test creating a city search response."""
        response = CitySearchResponse(
            cities=[
                CityResult(name="New York", country="US", state="New York"),
                CityResult(name="New Delhi", country="IN"),
            ]
        )
        assert len(response.cities) == 2
        assert response.cities[0].state == "New York"
        assert response.cities[1].state is None


class TestCacheEntry:
    """Test suite for CacheEntry model."""

    def test_expired_entry(self, sample_weather_data: dict[str, Any]) -> None:
        """Test that an expired cache entry reports is_expired."""
        data = WeatherData(**sample_weather_data)
        entry = CacheEntry(
            data=data,
            cached_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        assert entry.is_expired is True

    def test_fresh_entry(self, sample_weather_data: dict[str, Any]) -> None:
        """Test that a fresh cache entry reports not expired."""
        data = WeatherData(**sample_weather_data)
        entry = CacheEntry(
            data=data,
            cached_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        assert entry.is_expired is False
